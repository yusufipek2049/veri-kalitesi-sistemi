"""Rule kalıcılığı ve atomik audit için repository sözleşmesi.

İterasyon 36C0 — Rules PostgreSQL migration.
Issues/contracts.py şablonunu izler.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, TypeVar

from veri_kalitesi.audit import AuditEventInput, AuditOutboxStatus, PreparedAuditEvent
from veri_kalitesi.rules.models import (
    QualityRule,
    RuleApprovalRequest,
    RuleStatus,
    RuleTestResult,
    RuleVersion,
)


class RuleTransactionalAudit(Protocol):
    """Rule domaini için transactional audit outbox sözleşmesi."""

    def prepare(self, event: AuditEventInput) -> PreparedAuditEvent: ...

    def publish_pending(self, *, limit: int = 100) -> AuditOutboxStatus: ...


AuditT = TypeVar("AuditT", bound=RuleTransactionalAudit)
AuditRepoT = TypeVar("AuditRepoT", bound=RuleTransactionalAudit, contravariant=True)


class RuleRepository(Protocol[AuditRepoT]):
    """Rule domaini için repository sözleşmesi (generic audit outbox ile).

    SQLiteRuleRepository ve PostgreSQLRuleRepository bu sözleşmeyi uygular.
    """

    def add_rule_with_version(
        self,
        rule: QualityRule,
        version: RuleVersion,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: AuditRepoT,
    ) -> None: ...

    def add_version(
        self,
        version: RuleVersion,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: AuditRepoT,
    ) -> None: ...

    def get_rule(self, quality_rule_id: str) -> QualityRule: ...

    def get_version(self, rule_version_id: str) -> RuleVersion: ...

    def list_versions(self, quality_rule_id: str) -> list[RuleVersion]: ...

    def list_rules_with_latest_version(
        self,
        allowed_dataset_ids: frozenset[str],
    ) -> list[tuple[QualityRule, RuleVersion]]: ...

    def update_rule_status(
        self,
        quality_rule_id: str,
        status: RuleStatus,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: AuditRepoT,
    ) -> QualityRule: ...

    def add_test_result(
        self,
        result: RuleTestResult,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: AuditRepoT,
    ) -> None: ...

    def list_test_results(self, rule_version_id: str) -> list[RuleTestResult]: ...

    def latest_test_result(self, rule_version_id: str) -> RuleTestResult | None: ...

    def add_approval_request(
        self,
        request: RuleApprovalRequest,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: AuditRepoT,
    ) -> RuleApprovalRequest: ...

    def get_approval_request(
        self,
        approval_request_id: str,
    ) -> RuleApprovalRequest: ...

    def list_due_approval_requests(
        self,
        as_of: datetime,
    ) -> list[RuleApprovalRequest]: ...

    def decide_approval_request(
        self,
        request: RuleApprovalRequest,
        *,
        quality_rule_id: str,
        activate_rule: bool,
        audit_event: PreparedAuditEvent,
        audit_outbox: AuditRepoT,
    ) -> RuleApprovalRequest: ...

    def withdraw_approval_request(
        self,
        request: RuleApprovalRequest,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: AuditRepoT,
    ) -> RuleApprovalRequest: ...

    def expire_approval_request(
        self,
        request: RuleApprovalRequest,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: AuditRepoT,
    ) -> RuleApprovalRequest: ...