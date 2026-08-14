"""PostgreSQL-backed execution start/cancel adapters for the API protocol.

DS-03 — ActorContext geçişi ve istemci idempotency anahtarı.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import datetime, timezone
from uuid import uuid4

from veri_kalitesi.audit.models import (
    AuditEventInput,
    AuditResult,
)
from veri_kalitesi.audit.postgresql_outbox import PostgreSQLTransactionalAudit
from veri_kalitesi.executions.errors import (
    ExecutionConflictError,
    ExecutionNotFoundError,
    ExecutionValidationError,
)
from veri_kalitesi.executions.models import (
    ExecutionMode,
    ExecutionStatus,
    ExecutionType,
    RuleExecution,
    WorkloadClass,
)
from veri_kalitesi.executions.strategy_engine import ExecutionStrategyEngine
from veri_kalitesi.executions.postgresql_repository import (
    PostgreSQLExecutionRepository,
)
from veri_kalitesi.identity import ActorContext
from veri_kalitesi.jobs import BackgroundJob, PostgreSQLJobQueueRepository
from veri_kalitesi.persistence import transactional_session


class PostgreSQLExecutionStartService:
    """ExecutionStartService protocol'ünü PostgreSQLExecutionRepository ile gerçekler.

    DS-03: Trusted ActorContext alır; istemci idempotency anahtarı kullanır.
    Replay aynı execution'ı döndürür.
    """

    def __init__(
        self,
        repository: PostgreSQLExecutionRepository,
        *,
        job_queue: PostgreSQLJobQueueRepository,
        transactional_audit: PostgreSQLTransactionalAudit,
        strategy_engine: ExecutionStrategyEngine | None = None,
        rule_catalog: object | None = None,
        source_catalog: object | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self._repository = repository
        self._job_queue = job_queue
        self._transactional_audit = transactional_audit
        self._strategy_engine = strategy_engine
        self._rule_catalog = rule_catalog
        self._source_catalog = source_catalog
        self._clock = clock

    def start_manual(
        self,
        *,
        rule_version_ids: tuple[str, ...],
        source_ids: tuple[str, ...],
        idempotency_key: str,
        actor_context: ActorContext,
        execution_mode: ExecutionMode = ExecutionMode.OFFICIAL,
    ) -> RuleExecution:
        self._validate_execution_request(
            rule_version_ids=rule_version_ids,
            source_ids=source_ids,
            actor_context=actor_context,
        )
        now = self._clock()
        execution_id = uuid4().hex
        correlation_id = uuid4().hex
        scope: dict = {}
        payload_hash = self._hash_payload(rule_version_ids, source_ids, scope, execution_mode)

        execution = RuleExecution(
            execution_id=execution_id,
            idempotency_key_hash=self._hash_text(idempotency_key),
            payload_hash=payload_hash,
            rule_version_ids=rule_version_ids,
            scope=scope,
            triggered_by=actor_context.actor_id,
            correlation_id=correlation_id,
            source_ids=source_ids,
            workload_class=WorkloadClass.LIGHT,
            execution_type=ExecutionType.MANUAL,
            execution_mode=execution_mode,
            status=ExecutionStatus.QUEUED,
            created_at=now,
        )

        audit_outbox = self._transactional_audit
        audit_event = audit_outbox.prepare(
            AuditEventInput(
                actor_id=actor_context.actor_id,
                actor_type="USER",
                correlation_id=correlation_id,
                action="EXECUTION_START",
                object_type="RuleExecution",
                object_id=execution_id,
                result=AuditResult.SUCCESS,
                reason_code="MANUAL_START",
                old_values={},
                new_values={
                    "rule_version_ids": list(rule_version_ids),
                    "source_ids": list(source_ids),
                    "status": ExecutionStatus.QUEUED.value,
                    "execution_mode": execution_mode.value,
                },
                occurred_at=now,
            )
        )
        enqueue_event = audit_outbox.prepare(
            AuditEventInput(
                actor_id=actor_context.actor_id,
                actor_type="USER",
                correlation_id=correlation_id,
                action="JOB_ENQUEUED",
                object_type="BackgroundJob",
                object_id=execution_id,
                result=AuditResult.SUCCESS,
                reason_code="EXECUTION_REQUESTED",
                old_values={},
                new_values={"job_type": "EXECUTION", "execution_id": execution_id},
                occurred_at=now,
            )
        )

        with transactional_session(self._repository.session_factory) as session:
            stored, _ = self._repository.create_or_get(
                execution,
                audit_event=audit_event,
                audit_outbox=audit_outbox,
                session=session,
            )
            self._job_queue.enqueue(
                BackgroundJob(
                    job_id=execution_id,
                    job_type="EXECUTION",
                    payload={
                        "execution_id": execution_id,
                        "source_ids": list(source_ids),
                    },
                    idempotency_key=execution_id,
                    available_at=now,
                    created_at=now,
                    updated_at=now,
                ),
                audit_event=enqueue_event,
                audit_outbox=audit_outbox,
                session=session,
            )
        return stored

    @staticmethod
    def _hash_payload(
        version_ids: tuple[str, ...],
        source_ids: tuple[str, ...],
        scope: dict,
        execution_mode: ExecutionMode,
    ) -> str:
        serialized = json.dumps(
            {
                "rule_version_ids": list(version_ids),
                "source_ids": list(source_ids),
                "scope": scope,
                "execution_mode": execution_mode.value,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @staticmethod
    def _hash_text(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def _validate_execution_request(
        self,
        *,
        rule_version_ids: tuple[str, ...],
        source_ids: tuple[str, ...],
        actor_context: ActorContext,
    ) -> None:
        """Validate actor authorization, rule version integrity, and source scope."""
        if not rule_version_ids:
            raise ExecutionValidationError("At least one rule_version_id is required.")
        if not source_ids:
            raise ExecutionValidationError("At least one source_id is required.")

        # Check actor has execution role
        execution_roles = {"DATA_STEWARD", "DATA_OWNER", "DATA_VIEWER", "PLATFORM_ADMIN"}
        if not actor_context.roles.intersection(execution_roles):
            raise ExecutionValidationError(
                "Actor lacks the required role to start an execution."
            )

        # Check source scope
        if actor_context.permitted_source_ids:
            for sid in source_ids:
                if sid not in actor_context.permitted_source_ids:
                    raise ExecutionValidationError(
                        f"Source '{sid}' is outside the actor's permitted scope."
                    )

        # Validate rule versions are active and match the requested sources
        if self._rule_catalog is not None and self._source_catalog is not None:
            resolved_source_ids: set[str] = set()
            for vid in rule_version_ids:
                try:
                    version = self._rule_catalog.get_version(vid)
                except Exception as exc:
                    raise ExecutionValidationError(
                        f"Rule version '{vid}' not found."
                    ) from exc
                if version is None:
                    raise ExecutionValidationError(
                        f"Rule version '{vid}' not found."
                    )
                try:
                    rule = self._rule_catalog.get_rule(version.quality_rule_id)
                except Exception as exc:
                    raise ExecutionValidationError(
                        f"Quality rule '{version.quality_rule_id}' not found."
                    ) from exc
                if rule is None or rule.status.value != "ACTIVE":
                    raise ExecutionValidationError(
                        f"Rule '{version.quality_rule_id}' is not active."
                    )
                # Verify this is the latest version
                try:
                    all_versions = self._rule_catalog.list_versions(version.quality_rule_id)
                except Exception:
                    all_versions = []
                if all_versions:
                    latest = max(all_versions, key=lambda v: v.version_no)
                    if version.rule_version_id != latest.rule_version_id:
                        raise ExecutionValidationError(
                            f"Rule version '{vid}' is not the latest active version."
                        )
                # Resolve the data source for this rule
                try:
                    dataset = self._source_catalog.get_dataset(rule.dataset_id)
                    if dataset is not None:
                        resolved_source_ids.add(dataset.data_source_id)
                except Exception:
                    pass

            # Verify client source_ids match the rules' actual sources
            if resolved_source_ids:
                requested = set(source_ids)
                if not resolved_source_ids.issubset(requested):
                    extra = resolved_source_ids - requested
                    raise ExecutionValidationError(
                        f"Rule definitions require sources {sorted(extra)} which are not"
                        f" included in the request."
                    )


class PostgreSQLExecutionCancelService:
    """ExecutionCancelService protocol'ünü PostgreSQLExecutionRepository ile gerçekler.

    DS-03: Trusted ActorContext alır; execution source scope doğrulaması yapar.
    """

    def __init__(
        self,
        repository: PostgreSQLExecutionRepository,
        transactional_audit: PostgreSQLTransactionalAudit,
        job_queue: PostgreSQLJobQueueRepository,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self._repository = repository
        self._transactional_audit = transactional_audit
        self._job_queue = job_queue
        self._clock = clock

    def cancel(
        self,
        execution_id: str,
        *,
        reason: str,
        actor_context: ActorContext,
    ) -> RuleExecution:
        now = self._clock()
        audit_outbox = self._transactional_audit
        with transactional_session(self._repository.session_factory) as session:
            try:
                previous = self._repository.get(
                    execution_id,
                    session=session,
                    for_update=True,
                )
            except ExecutionNotFoundError:
                raise ExecutionNotFoundError(f"Execution {execution_id} not found.") from None

            if previous.status in {
                ExecutionStatus.SUCCESS,
                ExecutionStatus.TECHNICAL_ERROR,
                ExecutionStatus.CANCELLED,
                ExecutionStatus.TIMEOUT,
            }:
                raise ExecutionConflictError(
                    f"Cannot cancel execution in {previous.status.value} status."
                )

            if not all(sid in actor_context.permitted_source_ids for sid in previous.source_ids):
                raise ExecutionConflictError(
                    "Execution source scope is outside the actor's permitted scope."
                )

            job = self._job_queue.get_by_idempotency_key(
                "EXECUTION",
                execution_id,
                session=session,
                for_update=True,
            )
            if job is None:
                raise ExecutionConflictError("Execution has no persistent background job.")

            execution_target = (
                ExecutionStatus.CANCELLED
                if previous.status is ExecutionStatus.QUEUED
                else ExecutionStatus.CANCEL_REQUESTED
            )
            audit_event = audit_outbox.prepare(
                AuditEventInput(
                    actor_id=actor_context.actor_id,
                    actor_type="USER",
                    correlation_id=previous.correlation_id,
                    action="EXECUTION_CANCEL",
                    object_type="RuleExecution",
                    object_id=execution_id,
                    result=AuditResult.SUCCESS,
                    reason_code="MANUAL_CANCEL",
                    old_values={
                        "status": previous.status.value,
                    },
                    new_values={
                        "status": execution_target.value,
                        "cancel_reason": reason,
                    },
                    occurred_at=now,
                )
            )
            cancelled = self._repository.request_cancel(
                execution_id,
                actor_id=actor_context.actor_id,
                reason=reason,
                requested_at=now,
                audit_event=audit_event,
                audit_outbox=audit_outbox,
                session=session,
            )
            if job is not None and job.status.value in {"QUEUED", "RUNNING"}:
                job_audit = audit_outbox.prepare(
                    AuditEventInput(
                        actor_id=actor_context.actor_id,
                        actor_type="USER",
                        correlation_id=previous.correlation_id,
                        action="JOB_CANCEL_REQUESTED",
                        object_type="BackgroundJob",
                        object_id=job.job_id,
                        result=AuditResult.SUCCESS,
                        reason_code="MANUAL_CANCEL",
                        old_values={"status": job.status.value},
                        new_values={"execution_id": execution_id},
                        occurred_at=now,
                    )
                )
                self._job_queue.request_cancel(
                    job.job_id,
                    job.version,
                    requested_by=actor_context.actor_id,
                    reason_code="USER_REQUEST",
                    now=now,
                    audit_event=job_audit,
                    audit_outbox=audit_outbox,
                    session=session,
                )
        return cancelled
