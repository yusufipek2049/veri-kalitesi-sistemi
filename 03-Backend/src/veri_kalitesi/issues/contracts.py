"""Issue kalıcılığı ve atomik audit için repository sözleşmesi."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, TypeVar

from veri_kalitesi.audit import AuditEventInput, AuditOutboxStatus, PreparedAuditEvent
from veri_kalitesi.issues.models import (
    DataQualityIssue,
    IssueHistoryEntry,
    IssuePriority,
    IssueRelationship,
    IssueResolutionRecord,
    IssueStatus,
    IssueVerificationRecord,
)


class IssueTransactionalAudit(Protocol):
    def prepare(self, event: AuditEventInput) -> PreparedAuditEvent: ...

    def publish_pending(self, *, limit: int = 100) -> AuditOutboxStatus: ...


AuditT = TypeVar("AuditT", bound=IssueTransactionalAudit)
AuditRepoT = TypeVar("AuditRepoT", bound=IssueTransactionalAudit, contravariant=True)


class IssueRepository(Protocol[AuditRepoT]):
    def add_or_increment(
        self,
        issue: DataQualityIssue,
        history: IssueHistoryEntry,
        *,
        payload_digest: str,
        source_event_occurred_at: datetime,
        relationship: IssueRelationship | None,
        relationship_history: IssueHistoryEntry | None,
        audit_event: PreparedAuditEvent,
        reopen_audit_event: PreparedAuditEvent,
        relationship_audit_event: PreparedAuditEvent | None,
        audit_outbox: AuditRepoT,
    ) -> DataQualityIssue: ...

    def transition_status(
        self,
        issue_id: str,
        expected_status: IssueStatus,
        target_status: IssueStatus,
        updated_at: datetime,
        history: IssueHistoryEntry,
        *,
        expected_version: int,
        audit_event: PreparedAuditEvent,
        audit_outbox: AuditRepoT,
    ) -> DataQualityIssue: ...

    def update_assignment(
        self,
        issue_id: str,
        *,
        expected_status: IssueStatus,
        expected_assignee_user_id: str,
        expected_priority: IssuePriority,
        assignee_user_id: str,
        priority: IssuePriority,
        updated_at: datetime,
        history: IssueHistoryEntry,
        audit_event: PreparedAuditEvent,
        audit_outbox: AuditRepoT,
    ) -> DataQualityIssue: ...

    def resolve(
        self,
        issue_id: str,
        *,
        expected_status: IssueStatus,
        expected_assignee_user_id: str,
        resolution: IssueResolutionRecord,
        updated_at: datetime,
        history: IssueHistoryEntry,
        audit_event: PreparedAuditEvent,
        audit_outbox: AuditRepoT,
    ) -> DataQualityIssue: ...

    def record_verification(
        self,
        issue_id: str,
        *,
        expected_status: IssueStatus,
        target_status: IssueStatus,
        verification: IssueVerificationRecord,
        updated_at: datetime,
        history: IssueHistoryEntry,
        audit_event: PreparedAuditEvent,
        audit_outbox: AuditRepoT,
    ) -> DataQualityIssue: ...

    def get(self, issue_id: str) -> DataQualityIssue: ...

    def get_latest_resolution(self, issue_id: str) -> IssueResolutionRecord: ...

    def get_latest_verification(self, issue_id: str) -> IssueVerificationRecord: ...
