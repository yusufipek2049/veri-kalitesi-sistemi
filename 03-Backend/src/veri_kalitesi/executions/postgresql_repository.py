"""PostgreSQL-only execution persistence with immutable execution history.

Iteration 36E — Execution PostgreSQL migration.
Issues/postgresql_repository.py, rules/postgresql_repository.py ve
data_sources/postgresql_repository.py sablonunu izler.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    and_,
    func,
    insert,
    select,
    update,
)
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from veri_kalitesi.audit import PostgreSQLTransactionalAudit, PreparedAuditEvent
from veri_kalitesi.executions.errors import (
    ExecutionConflictError,
    ExecutionNotFoundError,
    ExecutionValidationError,
    IdempotencyConflictError,
)
from veri_kalitesi.executions.models import (
    ConcurrencyPolicy,
    ExecutionAttempt,
    ExecutionStatus,
    ExecutionType,
    MeasurementStatus,
    RuleExecution,
    RuleExecutionResult,
    WorkloadClass,
)
from veri_kalitesi.persistence import DEFAULT_SCHEMA_NAME, SessionFactory, transactional_session


@dataclass(frozen=True)
class ExecutionTables:
    executions: Table
    attempts: Table
    results: Table


def execution_tables(schema: str = DEFAULT_SCHEMA_NAME) -> ExecutionTables:
    metadata = MetaData(schema=schema)
    executions = Table(
        "rule_executions",
        metadata,
        Column("execution_id", String(36), primary_key=True),
        Column("execution_type", String(20), nullable=False),
        Column("status", String(30), nullable=False),
        Column("idempotency_key_hash", String(64), nullable=False, unique=True),
        Column("payload_hash", String(64), nullable=False),
        Column("rule_version_ids", JSON, nullable=False),
        Column("scope", JSON, nullable=False),
        Column("triggered_by", String(128), nullable=False),
        Column("correlation_id", String(36), nullable=False),
        Column("source_ids", JSON, nullable=False),
        Column("workload_class", String(20), nullable=False),
        Column("error_class", String(200)),
        Column("attempt_count", Integer, nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("started_at", DateTime(timezone=True)),
        Column("finished_at", DateTime(timezone=True)),
        Column("cancel_requested_at", DateTime(timezone=True)),
        Column("cancel_requested_by", String(128)),
        Column("cancel_reason", String(500)),
        Column("cancelled_at", DateTime(timezone=True)),
        CheckConstraint(
            "execution_type IN ('MANUAL', 'SCHEDULED')",
            name="ck_execution_type",
        ),
        CheckConstraint(
            "status IN ('QUEUED', 'RUNNING', 'CANCEL_REQUESTED', 'SUCCESS', "
            "'PARTIAL', 'TECHNICAL_ERROR', 'TIMEOUT', 'CANCELLED')",
            name="ck_execution_status",
        ),
        CheckConstraint(
            "workload_class IN ('HEAVY', 'LIGHT')",
            name="ck_execution_workload_class",
        ),
    )
    attempts = Table(
        "execution_attempts",
        metadata,
        Column("attempt_id", String(36), primary_key=True),
        Column(
            "execution_id",
            String(36),
            ForeignKey(f"{schema}.rule_executions.execution_id"),
            nullable=False,
        ),
        Column("attempt_no", Integer, nullable=False),
        Column("status", String(30), nullable=False),
        Column("error_class", String(200)),
        Column("retryable", Integer, nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
        UniqueConstraint("execution_id", "attempt_no", name="uq_exec_attempts_exec_attempt"),
        CheckConstraint(
            "status IN ('QUEUED', 'RUNNING', 'CANCEL_REQUESTED', 'SUCCESS', "
            "'PARTIAL', 'TECHNICAL_ERROR', 'TIMEOUT', 'CANCELLED')",
            name="ck_attempt_status",
        ),
    )
    results = Table(
        "rule_execution_results",
        metadata,
        Column("rule_result_id", String(36), primary_key=True),
        Column(
            "execution_id",
            String(36),
            ForeignKey(f"{schema}.rule_executions.execution_id"),
            nullable=False,
        ),
        Column("rule_version_id", String(36), nullable=False),
        Column("population_count", Integer),
        Column("eligible_count", Integer),
        Column("evaluated_count", Integer),
        Column("passed_count", Integer),
        Column("failed_count", Integer),
        Column("excluded_count", Integer),
        Column("technical_error_count", Integer),
        Column("unknown_count", Integer),
        Column("measurement_status", String(30)),
        Column("completed_partitions", JSON, nullable=False),
        Column("eligible_for_official_scoring", Integer, nullable=False),
        UniqueConstraint("execution_id", "rule_version_id", name="uq_exec_results_exec_rule"),
    )
    return ExecutionTables(executions=executions, attempts=attempts, results=results)


class PostgreSQLExecutionRepository:
    """Execution yasam dongusunu PostgreSQL ve atomik audit outbox ile saklar."""

    def __init__(
        self,
        session_factory: SessionFactory,
        *,
        schema: str = DEFAULT_SCHEMA_NAME,
    ) -> None:
        self._session_factory = session_factory
        self._tables = execution_tables(schema)

    # ------------------------------------------------------------------
    # Read methods
    # ------------------------------------------------------------------

    def get(self, execution_id: str) -> RuleExecution:
        with self._session_factory() as session:
            row = (
                session.execute(
                    select(self._tables.executions).where(
                        self._tables.executions.c.execution_id == execution_id
                    )
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            raise ExecutionNotFoundError("RuleExecution not found.")
        return _row_to_execution(row)

    def list_executions_for_sources(
        self,
        allowed_source_ids: frozenset[str],
        *,
        limit: int = 100,
    ) -> list[RuleExecution]:
        if not 1 <= limit <= 100:
            raise ExecutionValidationError("Execution query limit must be between 1 and 100.")
        if not allowed_source_ids:
            return []
        t = self._tables.executions
        with self._session_factory() as session:
            rows = (
                session.execute(
                    select(t)
                    .where(
                        and_(
                            func.json_array_length(t.c.source_ids) > 0,
                            t.c.status.in_(_ACTIVE_STATUSES),
                        )
                    )
                    .order_by(t.c.created_at.desc(), t.c.execution_id.desc())
                    .limit(limit)
                )
                .mappings()
                .all()
            )
        # Filtreleme: yalnız tamamı yetkili kaynaklara bağlı çalıştırmalar
        result: list[RuleExecution] = []
        for row in rows:
            exec_source_ids = set(json.loads(row["source_ids"]))
            if exec_source_ids and exec_source_ids.issubset(allowed_source_ids):
                result.append(_row_to_execution(row))
        return result

    def list_cancel_requested(self) -> list[RuleExecution]:
        with self._session_factory() as session:
            rows = (
                session.execute(
                    select(self._tables.executions)
                    .where(self._tables.executions.c.status == ExecutionStatus.CANCEL_REQUESTED.value)
                    .order_by(self._tables.executions.c.started_at, self._tables.executions.c.execution_id)
                )
                .mappings()
                .all()
            )
        return [_row_to_execution(row) for row in rows]

    def list_attempts(self, execution_id: str) -> list[ExecutionAttempt]:
        with self._session_factory() as session:
            rows = (
                session.execute(
                    select(self._tables.attempts)
                    .where(self._tables.attempts.c.execution_id == execution_id)
                    .order_by(self._tables.attempts.c.attempt_no)
                )
                .mappings()
                .all()
            )
        return [_row_to_attempt(row) for row in rows]

    def list_results(self, execution_id: str) -> list[RuleExecutionResult]:
        with self._session_factory() as session:
            rows = (
                session.execute(
                    select(self._tables.results)
                    .where(self._tables.results.c.execution_id == execution_id)
                    .order_by(self._tables.results.c.rule_version_id)
                )
                .mappings()
                .all()
            )
        return [_row_to_result(row) for row in rows]

    # ------------------------------------------------------------------
    # Write methods
    # ------------------------------------------------------------------

    def create_or_get(
        self,
        execution: RuleExecution,
        *,
        audit_event: PreparedAuditEvent | None = None,
        audit_outbox: PostgreSQLTransactionalAudit | None = None,
    ) -> tuple[RuleExecution, bool]:
        # Check for existing execution first (read-only)
        with self._session_factory() as session:
            existing = (
                session.execute(
                    select(self._tables.executions).where(
                        self._tables.executions.c.idempotency_key_hash == execution.idempotency_key_hash
                    )
                )
                .mappings()
                .one_or_none()
            )
        if existing is not None:
            if existing["payload_hash"] != execution.payload_hash:
                raise IdempotencyConflictError(
                    "Idempotency key was already used with a different payload."
                )
            return _row_to_execution(existing), False

        # Create new execution with audit
        with transactional_session(self._session_factory) as session:
            try:
                session.execute(
                    insert(self._tables.executions).values(
                        execution_id=execution.execution_id,
                        execution_type=execution.execution_type.value,
                        status=execution.status.value,
                        idempotency_key_hash=execution.idempotency_key_hash,
                        payload_hash=execution.payload_hash,
                        rule_version_ids=json.dumps(execution.rule_version_ids, sort_keys=True),
                        scope=json.dumps(dict(execution.scope), sort_keys=True),
                        triggered_by=execution.triggered_by,
                        correlation_id=execution.correlation_id,
                        source_ids=json.dumps(execution.source_ids, sort_keys=True),
                        workload_class=execution.workload_class.value,
                        error_class=execution.error_class,
                        attempt_count=execution.attempt_count,
                        created_at=execution.created_at,
                        started_at=execution.started_at,
                        finished_at=execution.finished_at,
                        cancel_requested_at=execution.cancel_requested_at,
                        cancel_requested_by=execution.cancel_requested_by,
                        cancel_reason=execution.cancel_reason,
                        cancelled_at=execution.cancelled_at,
                    )
                )
                if audit_outbox is not None and audit_event is not None:
                    audit_outbox.stage(audit_event, session=session)
            except IntegrityError as exc:
                raise ExecutionConflictError(
                    "Execution could not be created due to a conflict."
                ) from exc
        return execution, True

    def claim_next(
        self,
        started_at: datetime,
        policy: ConcurrencyPolicy | None = None,
    ) -> RuleExecution | None:
        policy = policy or ConcurrencyPolicy()
        with transactional_session(self._session_factory) as session:
            t = self._tables.executions
            # Find next QUEUED execution
            queued_row = (
                session.execute(
                    select(t)
                    .where(t.c.status == ExecutionStatus.QUEUED.value)
                    .order_by(t.c.created_at, t.c.execution_id)
                    .limit(1)
                )
                .mappings()
                .one_or_none()
            )
            if queued_row is None:
                return None

            execution = _row_to_execution(queued_row)

            # Check running executions for concurrency policy
            running_rows = (
                session.execute(
                    select(t).where(t.c.status == ExecutionStatus.RUNNING.value)
                )
                .mappings()
                .all()
            )
            running = [_row_to_execution(row) for row in running_rows]
            heavy_count = sum(item.workload_class is WorkloadClass.HEAVY for item in running)
            light_count = sum(item.workload_class is WorkloadClass.LIGHT for item in running)
            source_counts: dict[str, int] = {}
            heavy_source_counts: dict[str, int] = {}
            for item in running:
                for source_id in item.source_ids:
                    source_counts[source_id] = source_counts.get(source_id, 0) + 1
                    if item.workload_class is WorkloadClass.HEAVY:
                        heavy_source_counts[source_id] = heavy_source_counts.get(source_id, 0) + 1

            if not _fits_policy(
                execution,
                policy,
                heavy_count,
                light_count,
                source_counts,
                heavy_source_counts,
            ):
                return None

            # Claim the execution
            result = session.execute(
                update(t)
                .where(
                    and_(
                        t.c.execution_id == execution.execution_id,
                        t.c.status == ExecutionStatus.QUEUED.value,
                    )
                )
                .values(
                    status=ExecutionStatus.RUNNING.value,
                    started_at=started_at,
                )
            )
            if result.rowcount == 0:  # type: ignore[attr-defined]
                return None

        return self.get(execution.execution_id)

    def add_attempt(
        self,
        attempt: ExecutionAttempt,
        *,
        audit_event: PreparedAuditEvent | None = None,
        audit_outbox: PostgreSQLTransactionalAudit | None = None,
    ) -> None:
        with transactional_session(self._session_factory) as session:
            try:
                session.execute(
                    insert(self._tables.attempts).values(
                        attempt_id=attempt.attempt_id,
                        execution_id=attempt.execution_id,
                        attempt_no=attempt.attempt_no,
                        status=attempt.status.value,
                        error_class=attempt.error_class,
                        retryable=1 if attempt.retryable else 0,
                        created_at=attempt.created_at,
                    )
                )
                session.execute(
                    update(self._tables.executions)
                    .where(self._tables.executions.c.execution_id == attempt.execution_id)
                    .values(attempt_count=attempt.attempt_no)
                )
                if audit_outbox is not None and audit_event is not None:
                    audit_outbox.stage(audit_event, session=session)
            except IntegrityError as exc:
                raise ExecutionConflictError(
                    "Execution attempt could not be recorded."
                ) from exc

    def complete_success(
        self,
        execution_id: str,
        results: tuple[RuleExecutionResult, ...],
        finished_at: datetime,
        *,
        audit_event: PreparedAuditEvent | None = None,
        audit_outbox: PostgreSQLTransactionalAudit | None = None,
    ) -> RuleExecution:
        with transactional_session(self._session_factory) as session:
            t = self._tables.executions
            current = session.execute(
                select(t.c.status).where(t.c.execution_id == execution_id)
            ).scalar()
            if current == ExecutionStatus.CANCEL_REQUESTED.value:
                return self._write_cancelled(session, execution_id, finished_at)

            for result in results:
                session.execute(
                    insert(self._tables.results).values(
                        rule_result_id=result.rule_result_id,
                        execution_id=result.execution_id,
                        rule_version_id=result.rule_version_id,
                        population_count=result.population_count,
                        eligible_count=result.eligible_count,
                        evaluated_count=result.evaluated_count,
                        passed_count=result.passed_count,
                        failed_count=result.failed_count,
                        excluded_count=result.excluded_count,
                        technical_error_count=result.technical_error_count,
                        unknown_count=result.unknown_count,
                        measurement_status=(
                            result.measurement_status.value
                            if result.measurement_status is not None
                            else None
                        ),
                        completed_partitions=json.dumps(result.completed_partitions, sort_keys=True),
                        eligible_for_official_scoring=1 if result.eligible_for_official_scoring else 0,
                    )
                )
            session.execute(
                update(t)
                .where(t.c.execution_id == execution_id)
                .values(
                    status=ExecutionStatus.SUCCESS.value,
                    error_class=None,
                    finished_at=finished_at,
                )
            )
            if audit_outbox is not None and audit_event is not None:
                audit_outbox.stage(audit_event, session=session)
        return self.get(execution_id)

    def complete_timeout(
        self,
        execution_id: str,
        error_class: str,
        results: tuple[RuleExecutionResult, ...],
        finished_at: datetime,
        *,
        audit_event: PreparedAuditEvent | None = None,
        audit_outbox: PostgreSQLTransactionalAudit | None = None,
    ) -> RuleExecution:
        status = ExecutionStatus.PARTIAL if results else ExecutionStatus.TIMEOUT
        with transactional_session(self._session_factory) as session:
            t = self._tables.executions
            current = session.execute(
                select(t.c.status).where(t.c.execution_id == execution_id)
            ).scalar()
            if current == ExecutionStatus.CANCEL_REQUESTED.value:
                return self._write_cancelled(session, execution_id, finished_at)

            for result in results:
                session.execute(
                    insert(self._tables.results).values(
                        rule_result_id=result.rule_result_id,
                        execution_id=result.execution_id,
                        rule_version_id=result.rule_version_id,
                        population_count=result.population_count,
                        eligible_count=result.eligible_count,
                        evaluated_count=result.evaluated_count,
                        passed_count=result.passed_count,
                        failed_count=result.failed_count,
                        excluded_count=result.excluded_count,
                        technical_error_count=result.technical_error_count,
                        unknown_count=result.unknown_count,
                        measurement_status=(
                            result.measurement_status.value
                            if result.measurement_status is not None
                            else None
                        ),
                        completed_partitions=json.dumps(result.completed_partitions, sort_keys=True),
                        eligible_for_official_scoring=0,
                    )
                )
            session.execute(
                update(t)
                .where(t.c.execution_id == execution_id)
                .values(
                    status=status.value,
                    error_class=error_class,
                    finished_at=finished_at,
                )
            )
            if audit_outbox is not None and audit_event is not None:
                audit_outbox.stage(audit_event, session=session)
        return self.get(execution_id)

    def complete_technical_error(
        self,
        execution_id: str,
        error_class: str,
        finished_at: datetime,
        *,
        audit_event: PreparedAuditEvent | None = None,
        audit_outbox: PostgreSQLTransactionalAudit | None = None,
    ) -> RuleExecution:
        with transactional_session(self._session_factory) as session:
            t = self._tables.executions
            current = session.execute(
                select(t.c.status).where(t.c.execution_id == execution_id)
            ).scalar()
            if current == ExecutionStatus.CANCEL_REQUESTED.value:
                return self._write_cancelled(session, execution_id, finished_at)

            session.execute(
                update(t)
                .where(t.c.execution_id == execution_id)
                .values(
                    status=ExecutionStatus.TECHNICAL_ERROR.value,
                    error_class=error_class,
                    finished_at=finished_at,
                )
            )
            if audit_outbox is not None and audit_event is not None:
                audit_outbox.stage(audit_event, session=session)
        return self.get(execution_id)

    def request_cancel(
        self,
        execution_id: str,
        *,
        actor_id: str,
        reason: str,
        requested_at: datetime,
        audit_event: PreparedAuditEvent | None = None,
        audit_outbox: PostgreSQLTransactionalAudit | None = None,
    ) -> RuleExecution:
        with transactional_session(self._session_factory) as session:
            t = self._tables.executions
            current = session.execute(
                select(t.c.status).where(t.c.execution_id == execution_id)
            ).mappings().one_or_none()
            if current is None:
                raise ExecutionNotFoundError("RuleExecution not found.")

            current_status = ExecutionStatus(current["status"])
            if current_status is ExecutionStatus.CANCEL_REQUESTED:
                return _row_to_execution(current)
            if current_status is ExecutionStatus.CANCELLED and current["cancel_requested_at"] is not None:
                return _row_to_execution(current)

            if current_status is ExecutionStatus.QUEUED:
                new_status = ExecutionStatus.CANCELLED
                cancelled_at = requested_at
                finished_at = requested_at
            elif current_status is ExecutionStatus.RUNNING:
                new_status = ExecutionStatus.CANCEL_REQUESTED
                cancelled_at = None
                finished_at = None
            else:
                raise ExecutionValidationError(
                    "Only queued or running executions can be cancelled."
                )

            session.execute(
                update(t)
                .where(t.c.execution_id == execution_id)
                .values(
                    status=new_status.value,
                    cancel_requested_at=requested_at,
                    cancel_requested_by=actor_id,
                    cancel_reason=reason,
                    cancelled_at=cancelled_at,
                    finished_at=finished_at,
                )
            )
            if audit_outbox is not None and audit_event is not None:
                audit_outbox.stage(audit_event, session=session)
        return self.get(execution_id)

    def complete_cancelled(
        self,
        execution_id: str,
        cancelled_at: datetime,
        *,
        audit_event: PreparedAuditEvent | None = None,
        audit_outbox: PostgreSQLTransactionalAudit | None = None,
    ) -> RuleExecution:
        with transactional_session(self._session_factory) as session:
            current = session.execute(
                select(self._tables.executions.c.status).where(
                    self._tables.executions.c.execution_id == execution_id
                )
            ).scalar()
            if current != ExecutionStatus.CANCEL_REQUESTED.value:
                raise ExecutionValidationError(
                    "Only cancellation-requested executions can be closed."
                )
            result = self._write_cancelled(session, execution_id, cancelled_at)
            if audit_outbox is not None and audit_event is not None:
                audit_outbox.stage(audit_event, session=session)
        return result

    def _write_cancelled(self, session: Session, execution_id: str, cancelled_at: datetime) -> RuleExecution:
        session.execute(
            update(self._tables.executions)
            .where(self._tables.executions.c.execution_id == execution_id)
            .values(
                status=ExecutionStatus.CANCELLED.value,
                error_class=None,
                cancelled_at=cancelled_at,
                finished_at=cancelled_at,
            )
        )
        return self.get(execution_id)


# ------------------------------------------------------------------
# Row conversion helpers
# ------------------------------------------------------------------

_ACTIVE_STATUSES = frozenset({
    ExecutionStatus.QUEUED.value,
    ExecutionStatus.RUNNING.value,
    ExecutionStatus.CANCEL_REQUESTED.value,
    ExecutionStatus.SUCCESS.value,
    ExecutionStatus.PARTIAL.value,
    ExecutionStatus.TECHNICAL_ERROR.value,
    ExecutionStatus.TIMEOUT.value,
    ExecutionStatus.CANCELLED.value,
})


def _row_to_execution(row: RowMapping) -> RuleExecution:
    return RuleExecution(
        execution_id=row["execution_id"],
        execution_type=ExecutionType(row["execution_type"]),
        status=ExecutionStatus(row["status"]),
        idempotency_key_hash=row["idempotency_key_hash"],
        payload_hash=row["payload_hash"],
        rule_version_ids=tuple(json.loads(row["rule_version_ids"])),
        scope=json.loads(row["scope"]),
        triggered_by=row["triggered_by"],
        correlation_id=row["correlation_id"],
        source_ids=tuple(json.loads(row["source_ids"])),
        workload_class=WorkloadClass(row["workload_class"]),
        error_class=row["error_class"],
        attempt_count=row["attempt_count"],
        created_at=row["created_at"],
        started_at=row["started_at"],
        finished_at=row["finished_at"],
        cancel_requested_at=row["cancel_requested_at"],
        cancel_requested_by=row["cancel_requested_by"],
        cancel_reason=row["cancel_reason"],
        cancelled_at=row["cancelled_at"],
    )


def _row_to_attempt(row: RowMapping) -> ExecutionAttempt:
    return ExecutionAttempt(
        attempt_id=row["attempt_id"],
        execution_id=row["execution_id"],
        attempt_no=row["attempt_no"],
        status=ExecutionStatus(row["status"]),
        error_class=row["error_class"],
        retryable=bool(row["retryable"]),
        created_at=row["created_at"],
    )


def _row_to_result(row: RowMapping) -> RuleExecutionResult:
    return RuleExecutionResult(
        rule_result_id=row["rule_result_id"],
        execution_id=row["execution_id"],
        rule_version_id=row["rule_version_id"],
        population_count=row["population_count"],
        eligible_count=row["eligible_count"],
        evaluated_count=row["evaluated_count"],
        passed_count=row["passed_count"],
        failed_count=row["failed_count"],
        excluded_count=row["excluded_count"],
        technical_error_count=row["technical_error_count"],
        unknown_count=row["unknown_count"],
        measurement_status=(
            MeasurementStatus(row["measurement_status"])
            if row["measurement_status"] is not None
            else None
        ),
        completed_partitions=tuple(json.loads(row["completed_partitions"])),
        eligible_for_official_scoring=bool(row["eligible_for_official_scoring"]),
    )


def _fits_policy(
    execution: RuleExecution,
    policy: ConcurrencyPolicy,
    heavy_count: int,
    light_count: int,
    source_counts: dict[str, int],
    heavy_source_counts: dict[str, int],
) -> bool:
    if any(not policy.source_allowed(source_id) for source_id in execution.source_ids):
        return False
    if heavy_count + light_count >= policy.max_total:
        return False
    if execution.workload_class is WorkloadClass.HEAVY and heavy_count >= policy.max_heavy:
        return False
    if execution.workload_class is WorkloadClass.LIGHT and light_count >= policy.max_light:
        return False
    if execution.workload_class is WorkloadClass.HEAVY and any(
        heavy_source_counts.get(source_id, 0) >= policy.heavy_source_limit(source_id)
        for source_id in execution.source_ids
    ):
        return False
    return all(
        source_counts.get(source_id, 0) < policy.source_limit(source_id)
        for source_id in execution.source_ids
    )