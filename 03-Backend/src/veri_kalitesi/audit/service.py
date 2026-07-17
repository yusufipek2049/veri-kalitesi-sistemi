"""Merkezi audit yazma siniri ve acik hata politikasi."""

from __future__ import annotations

from typing import Protocol

from veri_kalitesi.audit.errors import AuditValidationError, AuditWriteError
from veri_kalitesi.audit.models import (
    AuditEvent,
    AuditEventInput,
    AuditFailureMode,
    AuditFailurePolicy,
    PreparedAuditEvent,
)
from veri_kalitesi.audit.redaction import AuditRedactor


class AuditEventRepository(Protocol):
    def append(self, prepared: PreparedAuditEvent) -> AuditEvent: ...


class DurableAuditBuffer(Protocol):
    def append(self, prepared: PreparedAuditEvent) -> None: ...


class AuditSink(Protocol):
    def append(self, event: AuditEventInput) -> AuditEvent | None: ...


class AuditService:
    def __init__(
        self,
        repository: AuditEventRepository,
        redactor: AuditRedactor,
        failure_policy: AuditFailurePolicy,
        *,
        durable_buffer: DurableAuditBuffer | None = None,
    ) -> None:
        if not failure_policy.version.strip():
            raise AuditValidationError("Audit failure policy version is required.")
        if (
            failure_policy.default_mode is AuditFailureMode.DURABLE_BUFFER
            or AuditFailureMode.DURABLE_BUFFER in failure_policy.action_modes.values()
        ) and durable_buffer is None:
            raise AuditValidationError("Durable audit mode requires a configured durable buffer.")
        self.repository = repository
        self.redactor = redactor
        self.failure_policy = failure_policy
        self.durable_buffer = durable_buffer

    def append(self, event: AuditEventInput) -> AuditEvent | None:
        prepared = self.redactor.prepare(event)
        try:
            return self.repository.append(prepared)
        except Exception as exc:
            mode = self.failure_policy.mode_for(event.action)
            if mode is AuditFailureMode.FAIL_CLOSED:
                raise AuditWriteError("Critical audit event could not be written.") from exc
            assert self.durable_buffer is not None
            try:
                self.durable_buffer.append(prepared)
            except Exception as buffer_exc:
                raise AuditWriteError(
                    "Audit event could not be written or buffered."
                ) from buffer_exc
            return None
