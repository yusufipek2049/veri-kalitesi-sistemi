"""Execution kalıcılığı ve atomik audit için repository sözleşmesi.

İterasyon 36E — Execution PostgreSQL migration.
Issues/contracts.py, rules/contracts.py ve data_sources/contracts.py şablonunu izler.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, TypeVar

from veri_kalitesi.audit import AuditEventInput, AuditOutboxStatus, PreparedAuditEvent
from veri_kalitesi.executions.models import (
    ConcurrencyPolicy,
    ExecutionAttempt,
    RuleExecution,
    RuleExecutionResult,
)


class ExecutionTransactionalAudit(Protocol):
    """Execution domaini için transactional audit outbox sözleşmesi."""

    def prepare(self, event: AuditEventInput) -> PreparedAuditEvent: ...

    def publish_pending(self, *, limit: int = 100) -> AuditOutboxStatus: ...


AuditT = TypeVar("AuditT", bound=ExecutionTransactionalAudit)
AuditRepoT = TypeVar("AuditRepoT", bound=ExecutionTransactionalAudit, contravariant=True)


class ExecutionRepository(Protocol[AuditRepoT]):
    """Execution domaini için repository sözleşmesi (generic audit outbox ile).

    SQLiteExecutionRepository ve PostgreSQLExecutionRepository bu sözleşmeyi uygular.
    """

    # --- Read methods ---

    def get(self, execution_id: str) -> RuleExecution: ...

    def list_executions_for_sources(
        self,
        allowed_source_ids: frozenset[str],
        *,
        limit: int = 100,
    ) -> list[RuleExecution]: ...

    def list_cancel_requested(self) -> list[RuleExecution]: ...

    def list_attempts(self, execution_id: str) -> list[ExecutionAttempt]: ...

    def list_results(self, execution_id: str) -> list[RuleExecutionResult]: ...

    # --- Write methods (with audit) ---

    def create_or_get(
        self,
        execution: RuleExecution,
        *,
        audit_event: PreparedAuditEvent | None = None,
        audit_outbox: AuditRepoT | None = None,
    ) -> tuple[RuleExecution, bool]: ...

    def claim_next(
        self,
        started_at: datetime,
        policy: ConcurrencyPolicy | None = None,
    ) -> RuleExecution | None: ...

    def add_attempt(
        self,
        attempt: ExecutionAttempt,
        *,
        audit_event: PreparedAuditEvent | None = None,
        audit_outbox: AuditRepoT | None = None,
    ) -> None: ...

    def complete_success(
        self,
        execution_id: str,
        results: tuple[RuleExecutionResult, ...],
        finished_at: datetime,
        *,
        audit_event: PreparedAuditEvent | None = None,
        audit_outbox: AuditRepoT | None = None,
    ) -> RuleExecution: ...

    def complete_timeout(
        self,
        execution_id: str,
        error_class: str,
        results: tuple[RuleExecutionResult, ...],
        finished_at: datetime,
        *,
        audit_event: PreparedAuditEvent | None = None,
        audit_outbox: AuditRepoT | None = None,
    ) -> RuleExecution: ...

    def complete_technical_error(
        self,
        execution_id: str,
        error_class: str,
        finished_at: datetime,
        *,
        audit_event: PreparedAuditEvent | None = None,
        audit_outbox: AuditRepoT | None = None,
    ) -> RuleExecution: ...

    def request_cancel(
        self,
        execution_id: str,
        *,
        actor_id: str,
        reason: str,
        requested_at: datetime,
        audit_event: PreparedAuditEvent | None = None,
        audit_outbox: AuditRepoT | None = None,
    ) -> RuleExecution: ...

    def complete_cancelled(
        self,
        execution_id: str,
        cancelled_at: datetime,
        *,
        audit_event: PreparedAuditEvent | None = None,
        audit_outbox: AuditRepoT | None = None,
    ) -> RuleExecution: ...