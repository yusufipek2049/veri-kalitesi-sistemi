"""Ortak governance_approval_requests tablosu PostgreSQL deposu.

Yazma işlemleri optimistic concurrency (version CAS) ile korunur; karar ve
uygulama ayrı satır güncellemeleri ve ayrı audit olaylarıdır.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    JSON,
    MetaData,
    String,
    Table,
    insert,
    or_,
    select,
    update,
)
from sqlalchemy.exc import IntegrityError

from veri_kalitesi.audit.models import PreparedAuditEvent
from veri_kalitesi.audit.postgresql_outbox import PostgreSQLTransactionalAudit
from veri_kalitesi.governance.errors import (
    GovernanceConflictError,
    GovernanceNotFoundError,
    GovernanceValidationError,
)
from veri_kalitesi.governance.models import (
    GovernanceApprovalRequest,
    GovernanceApprovalStatus,
    GovernanceRequestType,
)
from veri_kalitesi.persistence import DEFAULT_SCHEMA_NAME, SessionFactory, transactional_session


@dataclass(frozen=True)
class GovernanceTables:
    approval_requests: Table


def governance_tables(schema: str = DEFAULT_SCHEMA_NAME) -> GovernanceTables:
    metadata = MetaData(schema=schema)
    approval_requests = Table(
        "governance_approval_requests",
        metadata,
        Column("approval_request_id", String(36), primary_key=True),
        Column("request_type", String(40), nullable=False),
        Column("object_type", String(40), nullable=False),
        Column("object_id", String(36), nullable=False),
        Column("scope_type", String(40), nullable=False),
        Column("scope_id", String(36), nullable=False),
        Column("scope_version", Integer, nullable=False),
        Column("maker_actor_id", String(128), nullable=False),
        Column("maker_roles", JSON, nullable=False),
        Column("checker_actor_id", String(128)),
        Column("checker_role", String(40)),
        Column("status", String(30), nullable=False),
        Column("reason_code", String(120)),
        Column("change_summary", JSON, nullable=False),
        Column("before_snapshot_reference", String(500)),
        Column("after_snapshot_reference", String(500)),
        Column("evidence_references", JSON, nullable=False),
        Column("policy_version", String(40), nullable=False),
        Column("requested_at", DateTime(timezone=True), nullable=False),
        Column("expires_at", DateTime(timezone=True)),
        Column("decided_at", DateTime(timezone=True)),
        Column("applied_at", DateTime(timezone=True)),
        Column("correlation_id", String(64), nullable=False),
        Column("version", Integer, nullable=False),
    )
    return GovernanceTables(approval_requests=approval_requests)


class PostgreSQLGovernanceApprovalRepository:
    """Ortak yönetişim taleplerini atomik audit outbox ile saklar."""

    def __init__(
        self,
        session_factory: SessionFactory,
        tables: GovernanceTables | None = None,
        *,
        schema: str = DEFAULT_SCHEMA_NAME,
    ) -> None:
        self.session_factory = session_factory
        self.tables = tables or governance_tables(schema)

    # ------------------------------------------------------------------
    # Read methods
    # ------------------------------------------------------------------

    def get(self, approval_request_id: str) -> GovernanceApprovalRequest:
        with self.session_factory() as session:
            row = (
                session.execute(
                    select(self.tables.approval_requests).where(
                        self.tables.approval_requests.c.approval_request_id
                        == approval_request_id
                    )
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            raise GovernanceNotFoundError("GovernanceApprovalRequest not found.")
        return _row_to_request(row)

    def list_for_scope(
        self,
        *,
        dataset_ids: frozenset[str],
        source_ids: frozenset[str],
    ) -> list[GovernanceApprovalRequest]:
        """DATASET ve DATA_SOURCE kapsamlarındaki talepleri bounded döner."""
        if not dataset_ids and not source_ids:
            return []
        table = self.tables.approval_requests
        scope_conditions = []
        if dataset_ids:
            scope_conditions.append(
                (table.c.scope_type == "DATASET")
                & (table.c.scope_id.in_(sorted(dataset_ids)))
            )
        if source_ids:
            scope_conditions.append(
                (table.c.scope_type == "DATA_SOURCE")
                & (table.c.scope_id.in_(sorted(source_ids)))
            )
        with self.session_factory() as session:
            rows = (
                session.execute(
                    select(table)
                    .where(or_(*scope_conditions))
                    .order_by(table.c.requested_at.desc(), table.c.approval_request_id.desc())
                    .limit(500)
                )
                .mappings()
                .all()
            )
        return [_row_to_request(row) for row in rows]

    # ------------------------------------------------------------------
    # Write methods
    # ------------------------------------------------------------------

    def add(
        self,
        request: GovernanceApprovalRequest,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: PostgreSQLTransactionalAudit,
    ) -> GovernanceApprovalRequest:
        self._require_postgresql_audit(audit_outbox)
        with transactional_session(self.session_factory) as session:
            try:
                session.execute(
                    insert(self.tables.approval_requests).values(
                        **_request_to_values(request)
                    )
                )
            except IntegrityError as exc:
                raise GovernanceConflictError(
                    "Object already has a pending governance approval request."
                ) from exc
            audit_outbox.stage(audit_event, session=session)
        return request

    def transition(
        self,
        request: GovernanceApprovalRequest,
        *,
        expected_version: int,
        expected_status: GovernanceApprovalStatus,
        audit_event: PreparedAuditEvent,
        audit_outbox: PostgreSQLTransactionalAudit,
    ) -> GovernanceApprovalRequest:
        """Durum geçişini version CAS ile idempotent ve eşzamanlılık güvenli uygular."""
        self._require_postgresql_audit(audit_outbox)
        table = self.tables.approval_requests
        with transactional_session(self.session_factory) as session:
            result = session.execute(
                update(table)
                .where(
                    table.c.approval_request_id == request.approval_request_id,
                    table.c.status == expected_status.value,
                    table.c.version == expected_version,
                )
                .values(
                    status=request.status.value,
                    checker_actor_id=request.checker_actor_id,
                    checker_role=request.checker_role,
                    reason_code=request.reason_code,
                    decided_at=request.decided_at,
                    applied_at=request.applied_at,
                    version=expected_version + 1,
                )
            )
            self._require_single_update(result)
            audit_outbox.stage(audit_event, session=session)
        return self.get(request.approval_request_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_postgresql_audit(
        self, audit_outbox: PostgreSQLTransactionalAudit
    ) -> None:
        if not isinstance(audit_outbox, PostgreSQLTransactionalAudit):
            raise GovernanceValidationError("PostgreSQL audit outbox is required.")

    def _require_single_update(self, result: Any) -> None:
        if result.rowcount != 1:
            raise GovernanceConflictError(
                "Governance approval request was decided concurrently or superseded."
            )


def _request_to_values(request: GovernanceApprovalRequest) -> dict:
    return {
        "approval_request_id": request.approval_request_id,
        "request_type": request.request_type.value,
        "object_type": request.object_type,
        "object_id": request.object_id,
        "scope_type": request.scope_type,
        "scope_id": request.scope_id,
        "scope_version": request.scope_version,
        "maker_actor_id": request.maker_actor_id,
        "maker_roles": list(request.maker_roles),
        "checker_actor_id": request.checker_actor_id,
        "checker_role": request.checker_role,
        "status": request.status.value,
        "reason_code": request.reason_code,
        "change_summary": dict(request.change_summary),
        "before_snapshot_reference": request.before_snapshot_reference,
        "after_snapshot_reference": request.after_snapshot_reference,
        "evidence_references": list(request.evidence_references),
        "policy_version": request.policy_version,
        "requested_at": request.requested_at,
        "expires_at": request.expires_at,
        "decided_at": request.decided_at,
        "applied_at": request.applied_at,
        "correlation_id": request.correlation_id,
        "version": request.version,
    }


def _row_to_request(row) -> GovernanceApprovalRequest:
    return GovernanceApprovalRequest(
        approval_request_id=row["approval_request_id"],
        request_type=GovernanceRequestType(row["request_type"]),
        object_type=row["object_type"],
        object_id=row["object_id"],
        scope_type=row["scope_type"],
        scope_id=row["scope_id"],
        scope_version=row["scope_version"],
        maker_actor_id=row["maker_actor_id"],
        maker_roles=tuple(row["maker_roles"]),
        checker_actor_id=row["checker_actor_id"],
        checker_role=row["checker_role"],
        status=GovernanceApprovalStatus(row["status"]),
        reason_code=row["reason_code"],
        change_summary=dict(row["change_summary"] or {}),
        before_snapshot_reference=row["before_snapshot_reference"],
        after_snapshot_reference=row["after_snapshot_reference"],
        evidence_references=tuple(row["evidence_references"] or ()),
        policy_version=row["policy_version"],
        requested_at=row["requested_at"],
        expires_at=row["expires_at"],
        decided_at=row["decided_at"],
        applied_at=row["applied_at"],
        correlation_id=row["correlation_id"],
        version=row["version"],
    )
