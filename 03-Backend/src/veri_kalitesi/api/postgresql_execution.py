"""PostgreSQL-backed execution start/cancel adapters for the API protocol.

Iteration 36E — Execution PostgreSQL migration.
Replaces DevelopmentExecutionStore in production by implementing
ExecutionStartService and ExecutionCancelService protocols
against PostgreSQLExecutionRepository with audit outbox support.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import datetime, timezone
from uuid import uuid4

from veri_kalitesi.audit import (
    AuditEventInput,
    AuditResult,
    PreparedAuditEvent,
)
from veri_kalitesi.audit.postgresql_outbox import PostgreSQLTransactionalAudit
from veri_kalitesi.executions import (
    ExecutionConflictError,
    ExecutionNotFoundError,
    ExecutionStatus,
    ExecutionType,
    RuleExecution,
    WorkloadClass,
)
from veri_kalitesi.executions.postgresql_repository import (
    PostgreSQLExecutionRepository,
)


class PostgreSQLExecutionStartService:
    """ExecutionStartService protocol'ünü PostgreSQLExecutionRepository ile gerçekler.

    Her start_manual çağrısı:
    - Benzersiz idempotency_key_hash ve payload_hash üretir
    - RuleExecution domain objesi oluşturup repository.create_or_get() ile saklar
    - Audit event'ini aynı transaction'da outbox'a yazar
    """

    def __init__(
        self,
        repository: PostgreSQLExecutionRepository,
        transactional_audit: PostgreSQLTransactionalAudit | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self._repository = repository
        self._transactional_audit = transactional_audit
        self._clock = clock

    def start_manual(
        self,
        *,
        rule_version_ids: tuple[str, ...],
        source_ids: tuple[str, ...],
        triggered_by: str,
    ) -> RuleExecution:
        now = self._clock()
        execution_id = uuid4().hex
        correlation_id = uuid4().hex
        idempotency_key = f"manual-{execution_id}"
        scope: dict = {}
        payload_hash = self._hash_payload(rule_version_ids, scope)

        execution = RuleExecution(
            execution_id=execution_id,
            idempotency_key_hash=self._hash_text(idempotency_key),
            payload_hash=payload_hash,
            rule_version_ids=rule_version_ids,
            scope=scope,
            triggered_by=triggered_by,
            correlation_id=correlation_id,
            source_ids=source_ids,
            workload_class=WorkloadClass.LIGHT,
            execution_type=ExecutionType.MANUAL,
            status=ExecutionStatus.QUEUED,
            created_at=now,
        )

        audit_event: PreparedAuditEvent | None = None
        audit_outbox = self._transactional_audit
        if audit_outbox is not None:
            audit_event = audit_outbox.prepare(
                AuditEventInput(
                    actor_id=triggered_by,
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
                    },
                    occurred_at=now,
                )
            )

        stored, _ = self._repository.create_or_get(
            execution,
            audit_event=audit_event,
            audit_outbox=audit_outbox,
        )
        return stored

    @staticmethod
    def _hash_payload(version_ids: tuple[str, ...], scope: dict) -> str:
        serialized = json.dumps(
            {"rule_version_ids": list(version_ids), "scope": scope},
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @staticmethod
    def _hash_text(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()


class PostgreSQLExecutionCancelService:
    """ExecutionCancelService protocol'ünü PostgreSQLExecutionRepository ile gerçekler.

    Her cancel çağrısı:
    - repository.request_cancel() ile iptal isteğini kaydeder
    - Audit event'ini aynı transaction'da outbox'a yazar
    - Terminal durumdaki execution'lar için 409 döndürür
    """

    def __init__(
        self,
        repository: PostgreSQLExecutionRepository,
        transactional_audit: PostgreSQLTransactionalAudit | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self._repository = repository
        self._transactional_audit = transactional_audit
        self._clock = clock

    def cancel(
        self,
        execution_id: str,
        *,
        reason: str,
        requested_by: str,
    ) -> RuleExecution:
        now = self._clock()

        # Mevcut durumu kontrol et
        try:
            previous = self._repository.get(execution_id)
        except ExecutionNotFoundError:
            raise ExecutionNotFoundError(f"Execution {execution_id} not found.")

        # Terminal durumda iptal reddedilir
        if previous.status in {
            ExecutionStatus.SUCCESS,
            ExecutionStatus.TECHNICAL_ERROR,
            ExecutionStatus.CANCELLED,
            ExecutionStatus.TIMEOUT,
        }:
            raise ExecutionConflictError(
                f"Cannot cancel execution in {previous.status.value} status."
            )

        audit_event: PreparedAuditEvent | None = None
        audit_outbox = self._transactional_audit
        if audit_outbox is not None:
            audit_event = audit_outbox.prepare(
                AuditEventInput(
                    actor_id=requested_by,
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
                        "status": ExecutionStatus.CANCEL_REQUESTED.value,
                        "cancel_reason": reason,
                    },
                    occurred_at=now,
                )
            )

        return self._repository.request_cancel(
            execution_id,
            actor_id=requested_by,
            reason=reason,
            requested_at=now,
            audit_event=audit_event,
            audit_outbox=audit_outbox,
        )