"""PostgreSQL-only source usage policy persistence with transactional audit.

Iteration 36F — Execution politika ve worker dayanıklılığı.
PostgreSQLExecutionRepository ve postgresql_repository.py sablonunu izler.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType

from sqlalchemy import (
    Column,
    Float,
    Integer,
    JSON,
    MetaData,
    String,
    Table,
    select,
    update,
)
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from veri_kalitesi.audit import PostgreSQLTransactionalAudit, PreparedAuditEvent
from veri_kalitesi.executions.errors import (
    SourceUsagePolicyConflictError,
    SourceUsagePolicyTechnicalError,
    SourceUsagePolicyUnavailableError,
)
from veri_kalitesi.executions.models import ConcurrencyPolicy
from veri_kalitesi.executions.source_usage_policies import (
    ResolvedSourceUsagePolicy,
    SourceUsagePolicy,
    SourceUsagePolicyStatus,
    _effective_source_limit,
    _policy_allows_at,
    _runtime_policy,
    _validate_evaluation_time,
    _validate_source_usage_policy,
    _window_from_value,
    _window_values,
)
from veri_kalitesi.persistence import DEFAULT_SCHEMA_NAME, SessionFactory, transactional_session


@dataclass(frozen=True)
class SourceUsageTables:
    policies: Table


def source_usage_tables(schema: str = DEFAULT_SCHEMA_NAME) -> SourceUsageTables:
    metadata = MetaData(schema=schema)
    policies = Table(
        "source_usage_policies",
        metadata,
        Column("policy_id", String(36), primary_key=True),
        Column("policy_version", Integer, nullable=False),
        Column("status", String(20), nullable=False),
        Column("source_id", String(36)),
        Column("source_type", String(40)),
        Column("max_concurrent_queries", Integer, nullable=False),
        Column("max_workers", Integer, nullable=False),
        Column("connection_timeout_seconds", Integer, nullable=False),
        Column("query_timeout_seconds", Integer, nullable=False),
        Column("total_job_timeout_seconds", Integer, nullable=False),
        Column("retry_count", Integer, nullable=False),
        Column("retry_delay_seconds", Float, nullable=False),
        Column("rate_limit", JSON, nullable=False),
        Column("allowed_windows", JSON, nullable=False),
        Column("blocked_windows", JSON, nullable=False),
        Column("cpu_limit_percent", Float),
        Column("io_limit_percent", Float),
        Column("peak_hours_behavior", String(20), nullable=False),
        Column("timeout_cancel_behavior", String(20), nullable=False),
        Column("approved_by", String(128)),
        Column("audit_reference", String(200)),
        schema=schema,
    )
    return SourceUsageTables(policies=policies)


class PostgreSQLSourceUsagePolicyRepository:
    """PostgreSQL tabanli kaynak kullanim politikasi repository.

    SourceUsagePolicyResolver protocol'ünü gerçekler.
    SQLiteSourceUsagePolicyRepository ile ayni public API'ye sahiptir.
    """

    def __init__(
        self,
        session_factory: SessionFactory,
        *,
        schema: str = DEFAULT_SCHEMA_NAME,
        source_types_by_id: Mapping[str, str] | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._tables = source_usage_tables(schema)
        self.source_types_by_id = MappingProxyType(dict(source_types_by_id or {}))

    def save(
        self,
        policy: SourceUsagePolicy,
        *,
        audit_event: PreparedAuditEvent | None = None,
        audit_outbox: PostgreSQLTransactionalAudit | None = None,
    ) -> SourceUsagePolicy:
        _validate_source_usage_policy(policy)
        try:
            with transactional_session(self._session_factory) as session:
                t = self._tables.policies
                if policy.status is SourceUsagePolicyStatus.ACTIVE:
                    self._retire_active_scope(session, policy)
                session.execute(
                    t.insert().values(
                        policy_id=policy.policy_id,
                        policy_version=policy.policy_version,
                        status=policy.status.value,
                        source_id=policy.source_id,
                        source_type=policy.source_type,
                        max_concurrent_queries=policy.max_concurrent_queries,
                        max_workers=policy.max_workers,
                        connection_timeout_seconds=policy.connection_timeout_seconds,
                        query_timeout_seconds=policy.query_timeout_seconds,
                        total_job_timeout_seconds=policy.total_job_timeout_seconds,
                        retry_count=policy.retry_count,
                        retry_delay_seconds=policy.retry_delay_seconds,
                        rate_limit=dict(policy.rate_limit),
                        allowed_windows=[_window_values(w) for w in policy.allowed_windows],
                        blocked_windows=[_window_values(w) for w in policy.blocked_windows],
                        cpu_limit_percent=policy.cpu_limit_percent,
                        io_limit_percent=policy.io_limit_percent,
                        peak_hours_behavior=policy.peak_hours_behavior,
                        timeout_cancel_behavior=policy.timeout_cancel_behavior,
                        approved_by=policy.approved_by,
                        audit_reference=policy.audit_reference,
                    )
                )
                if audit_outbox is not None and audit_event is not None:
                    audit_outbox.stage(audit_event, session=session)
        except IntegrityError as exc:
            raise SourceUsagePolicyConflictError(
                "Source usage policy identity or version conflicts."
            ) from exc
        return policy

    def list_policies(self) -> list[SourceUsagePolicy]:
        t = self._tables.policies
        try:
            with self._session_factory() as session:
                rows = (
                    session.execute(
                        select(t).order_by(t.c.policy_version, t.c.policy_id)
                    )
                    .mappings()
                    .all()
                )
        except Exception as exc:
            raise SourceUsagePolicyTechnicalError(
                "Source usage policies could not be read."
            ) from exc
        return [_row_to_policy(row) for row in rows]

    def resolve_concurrency_policy(self, *, at: datetime) -> ConcurrencyPolicy:
        return self.resolve_policy(at=at).concurrency_policy

    def resolve_policy(self, *, at: datetime) -> ResolvedSourceUsagePolicy:
        _validate_evaluation_time(at)
        t = self._tables.policies
        try:
            with self._session_factory() as session:
                rows = (
                    session.execute(
                        select(t)
                        .where(t.c.status == SourceUsagePolicyStatus.ACTIVE.value)
                        .order_by(t.c.policy_version.desc(), t.c.policy_id)
                    )
                    .mappings()
                    .all()
                )
        except Exception as exc:
            raise SourceUsagePolicyTechnicalError(
                "Active source usage policies could not be read."
            ) from exc

        policies = [_row_to_policy(row) for row in rows]
        global_policy = next(
            (
                policy
                for policy in policies
                if policy.source_id is None and policy.source_type is None
            ),
            None,
        )
        if global_policy is None:
            raise SourceUsagePolicyUnavailableError(
                "Active global source usage policy is required."
            )

        by_source = {
            policy.source_id: policy for policy in policies if policy.source_id is not None
        }
        by_type = {
            policy.source_type: policy for policy in policies if policy.source_type is not None
        }
        resolved_limits = {
            source_id: _effective_source_limit(policy)
            for source_id, policy in by_source.items()
        }
        resolved_allowed = {
            source_id: _policy_allows_at(policy, at)
            for source_id, policy in by_source.items()
        }
        resolved_runtime = {
            source_id: _runtime_policy(policy)
            for source_id, policy in by_source.items()
        }
        for source_id, source_type in self.source_types_by_id.items():
            override = by_source.get(source_id) or by_type.get(source_type)
            if override is not None:
                resolved_limits[source_id] = _effective_source_limit(override)
                resolved_allowed[source_id] = _policy_allows_at(override, at)
                resolved_runtime[source_id] = _runtime_policy(override)

        global_worker_limit = global_policy.max_workers
        global_source_limit = _effective_source_limit(global_policy)
        return ResolvedSourceUsagePolicy(
            concurrency_policy=ConcurrencyPolicy(
                max_total=global_worker_limit,
                max_heavy=global_worker_limit,
                max_light=global_worker_limit,
                default_source_limit=global_source_limit,
                default_heavy_source_limit=global_source_limit,
                default_source_allowed=_policy_allows_at(global_policy, at),
                per_source_limits=resolved_limits,
                per_source_heavy_limits=resolved_limits,
                per_source_allowed=resolved_allowed,
            ),
            default_runtime_policy=_runtime_policy(global_policy),
            per_source_runtime_policies=resolved_runtime,
        )

    def _retire_active_scope(self, session: Session, policy: SourceUsagePolicy) -> None:
        t = self._tables.policies
        session.execute(
            update(t)
            .where(
                t.c.status == SourceUsagePolicyStatus.ACTIVE.value,
                t.c.source_id.is_(policy.source_id),
                t.c.source_type.is_(policy.source_type),
            )
            .values(status=SourceUsagePolicyStatus.RETIRED.value)
        )


def _row_to_policy(row: RowMapping) -> SourceUsagePolicy:
    return SourceUsagePolicy(
        policy_id=row["policy_id"],
        policy_version=row["policy_version"],
        status=SourceUsagePolicyStatus(row["status"]),
        source_id=row["source_id"],
        source_type=row["source_type"],
        max_concurrent_queries=row["max_concurrent_queries"],
        max_workers=row["max_workers"],
        connection_timeout_seconds=row["connection_timeout_seconds"],
        query_timeout_seconds=row["query_timeout_seconds"],
        total_job_timeout_seconds=row["total_job_timeout_seconds"],
        retry_count=row["retry_count"],
        retry_delay_seconds=row["retry_delay_seconds"],
        rate_limit=dict(_from_json(row["rate_limit"])),
        allowed_windows=tuple(
            _window_from_value(value) for value in _from_json(row["allowed_windows"])
        ),
        blocked_windows=tuple(
            _window_from_value(value) for value in _from_json(row["blocked_windows"])
        ),
        cpu_limit_percent=row["cpu_limit_percent"],
        io_limit_percent=row["io_limit_percent"],
        peak_hours_behavior=row["peak_hours_behavior"],
        timeout_cancel_behavior=row["timeout_cancel_behavior"],
        approved_by=row["approved_by"],
        audit_reference=row["audit_reference"],
    )


def _from_json(value: object) -> object:
    """JSON column değerini Python objesine dönüştürür."""
    import json

    if isinstance(value, str):
        return json.loads(value)
    return value
