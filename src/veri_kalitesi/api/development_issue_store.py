"""Geliştirme ortamı sorun (issue) bellek içi deposu."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from threading import RLock
from uuid import uuid4

from veri_kalitesi.api.development_fixtures import (
    DEVELOPMENT_ASSIGNEE_OPTIONS,
    DEVELOPMENT_ISSUES,
)
from veri_kalitesi.api.models import IssueAssigneeOptionResponse
from veri_kalitesi.identity import ActorContext
from veri_kalitesi.issues import (
    DataQualityIssue,
    IssueAssignment,
    IssueAuthorizationError,
    IssueConflictError,
    IssueEvidenceRecord,
    IssueNotFoundError,
    IssueResolutionDraft,
    IssueScopeType,
    IssueStatus,
    IssueValidationError,
)
from veri_kalitesi.issues.evidence_files import IssueEvidenceFileRecord


class DevelopmentIssueStore:
    def __init__(self) -> None:
        self._issues = {issue.issue_id: issue for issue in DEVELOPMENT_ISSUES}
        self._evidence: dict[str, IssueEvidenceRecord] = {}
        self._evidence_files: dict[str, IssueEvidenceFileRecord] = {}
        self._resolution_evidence_ids: set[str] = set()
        self._lock = RLock()

    def get(self, issue_id: str) -> DataQualityIssue:
        with self._lock:
            issue = self._issues.get(issue_id)
        if issue is None:
            raise IssueNotFoundError("Development issue was not found.")
        return issue

    # ── Kanıt defteri (geliştirme içi, üretimdeki issue_evidence tablosunun karşılığı) ──

    def list_evidence(self, issue_id: str) -> list[IssueEvidenceRecord]:
        with self._lock:
            return [record for record in self._evidence.values() if record.issue_id == issue_id]

    def get_evidence(self, evidence_id: str) -> IssueEvidenceRecord | None:
        with self._lock:
            return self._evidence.get(evidence_id)

    def add_evidence(self, record: IssueEvidenceRecord) -> IssueEvidenceRecord:
        with self._lock:
            existing = next(
                (
                    item
                    for item in self._evidence.values()
                    if item.issue_id == record.issue_id
                    and item.source_digest == record.source_digest
                ),
                None,
            )
            if existing is not None:
                return existing
            self._evidence[record.evidence_id] = record
            return record

    def add_uploaded_evidence(
        self, evidence: IssueEvidenceRecord, file: IssueEvidenceFileRecord
    ) -> tuple[IssueEvidenceRecord, IssueEvidenceFileRecord]:
        with self._lock:
            existing = next(
                (
                    item
                    for item in self._evidence_files.values()
                    if item.idempotency_digest == file.idempotency_digest
                    and self._evidence[item.evidence_id].issue_id == evidence.issue_id
                ),
                None,
            )
            if existing:
                return self._evidence[existing.evidence_id], existing
            self._evidence[evidence.evidence_id] = evidence
            self._evidence_files[evidence.evidence_id] = file
            return evidence, file

    def get_evidence_file(self, evidence_id: str) -> IssueEvidenceFileRecord | None:
        with self._lock:
            return self._evidence_files.get(evidence_id)

    def list_evidence_files(self, issue_id: str) -> list[IssueEvidenceFileRecord]:
        with self._lock:
            return [
                file
                for evidence_id, file in self._evidence_files.items()
                if self._evidence[evidence_id].issue_id == issue_id
            ]

    def update_evidence_file(self, file: IssueEvidenceFileRecord) -> None:
        with self._lock:
            self._evidence_files[file.evidence_id] = file

    def evidence_is_referenced(self, evidence_id: str) -> bool:
        return evidence_id in self._resolution_evidence_ids

    def list_issues_for_scopes(
        self,
        allowed_source_ids: frozenset[str],
        allowed_dataset_ids: frozenset[str],
        *,
        limit: int = 100,
    ) -> list[DataQualityIssue]:
        return sorted(
            (
                issue
                for issue in self._issues.values()
                if (
                    issue.scope_type is IssueScopeType.SOURCE
                    and issue.scope_id in allowed_source_ids
                )
                or (
                    issue.scope_type is IssueScopeType.DATASET
                    and issue.scope_id in allowed_dataset_ids
                )
            ),
            key=lambda issue: (issue.updated_at, issue.issue_id),
            reverse=True,
        )[:limit]

    def start_investigation(
        self,
        issue_id: str,
        expected_version: int,
        actor_context: ActorContext | None,
    ) -> DataQualityIssue:
        if actor_context is None:
            raise IssueAuthorizationError("Development actor is required.")
        with self._lock:
            issue = self._issues.get(issue_id)
            if issue is None:
                raise IssueValidationError("Development issue was not found.")
            has_scope = (
                issue.scope_id in actor_context.permitted_source_ids
                if issue.scope_type is IssueScopeType.SOURCE
                else issue.scope_id in actor_context.permitted_dataset_ids
            )
            if issue.assignee_user_id != actor_context.actor_id or not has_scope:
                raise IssueAuthorizationError("Development actor cannot investigate issue.")
            if issue.version != expected_version:
                raise IssueConflictError("Development issue version changed.")
            if issue.status is not IssueStatus.ASSIGNED:
                raise IssueValidationError("Development issue is not assigned.")
            updated = replace(
                issue,
                status=IssueStatus.INVESTIGATING,
                updated_at=datetime.now(timezone.utc),
                version=issue.version + 1,
            )
            self._issues[issue_id] = updated
            return updated

    def list_assignment_options(
        self,
        issue_id: str,
        actor_context: ActorContext | None,
    ) -> tuple[IssueAssigneeOptionResponse, ...]:
        if actor_context is None:
            raise IssueAuthorizationError("Development actor is required.")
        with self._lock:
            issue = self._issues.get(issue_id)
            if issue is None:
                raise IssueValidationError("Development issue was not found.")
            self._authorize_assignment(issue, actor_context)
            return DEVELOPMENT_ASSIGNEE_OPTIONS

    def reassign(
        self,
        issue_id: str,
        assignment: IssueAssignment,
        expected_version: int,
        actor_context: ActorContext | None,
    ) -> DataQualityIssue:
        if actor_context is None:
            raise IssueAuthorizationError("Development actor is required.")
        with self._lock:
            issue = self._issues.get(issue_id)
            if issue is None:
                raise IssueValidationError("Development issue was not found.")
            self._authorize_assignment(issue, actor_context)
            if issue.version != expected_version:
                raise IssueConflictError("Development issue version changed.")
            allowed_ids = {str(option.user_id) for option in DEVELOPMENT_ASSIGNEE_OPTIONS}
            if assignment.assignee_user_id not in allowed_ids:
                raise IssueAuthorizationError("Development assignee is not available.")
            if (
                issue.assignee_user_id == assignment.assignee_user_id
                and issue.priority is assignment.priority
            ):
                raise IssueValidationError("Development assignment must change.")
            updated = replace(
                issue,
                assignee_user_id=assignment.assignee_user_id,
                priority=assignment.priority,
                status=IssueStatus.ASSIGNED,
                updated_at=datetime.now(timezone.utc),
                version=issue.version + 1,
            )
            self._issues[issue_id] = updated
            return updated

    def resolve(
        self,
        issue_id: str,
        draft: IssueResolutionDraft,
        expected_version: int,
        actor_context: ActorContext | None,
    ) -> DataQualityIssue:
        if actor_context is None:
            raise IssueAuthorizationError("Development actor is required.")
        with self._lock:
            issue = self._issues.get(issue_id)
            if issue is None:
                raise IssueValidationError("Development issue was not found.")
            if issue.version != expected_version:
                raise IssueConflictError("Development issue version changed.")
            has_scope = (
                issue.scope_id in actor_context.permitted_source_ids
                if issue.scope_type is IssueScopeType.SOURCE
                else issue.scope_id in actor_context.permitted_dataset_ids
            )
            if issue.assignee_user_id != actor_context.actor_id or not has_scope:
                raise IssueAuthorizationError("Development actor cannot resolve issue.")
            if issue.status not in {IssueStatus.INVESTIGATING, IssueStatus.WAITING_FOR_RESOLUTION}:
                raise IssueValidationError("Development issue is not in a resolvable state.")
            if draft.completed_at > datetime.now(timezone.utc):
                raise IssueValidationError("Development resolution completed_at is in the future.")
            evidence = self._evidence.get(draft.evidence_reference_id)
            if evidence is None:
                raise IssueValidationError(
                    "evidence_reference_id does not match a stored evidence."
                )
            if evidence.issue_id != issue_id:
                raise IssueValidationError("evidence_reference_id belongs to another issue.")
            file = self._evidence_files.get(draft.evidence_reference_id)
            if file is not None and file.scan_status.value != "AVAILABLE":
                raise IssueValidationError("Uploaded evidence is not available.")
            self._resolution_evidence_ids.add(draft.evidence_reference_id)
            updated = replace(
                issue,
                status=IssueStatus.RESOLVED,
                updated_at=datetime.now(timezone.utc),
                version=issue.version + 1,
            )
            self._issues[issue_id] = updated
            return updated

    def record_verification_result(
        self,
        issue_id: str,
        verification_reference_id: str,
        actor_context: ActorContext | None,
    ) -> DataQualityIssue:
        if actor_context is None:
            raise IssueAuthorizationError("Development actor is required.")
        with self._lock:
            issue = self._issues.get(issue_id)
            if issue is None:
                raise IssueValidationError("Development issue was not found.")
            has_scope = (
                issue.scope_id in actor_context.permitted_source_ids
                if issue.scope_type is IssueScopeType.SOURCE
                else issue.scope_id in actor_context.permitted_dataset_ids
            )
            if issue.assignee_user_id == actor_context.actor_id or not has_scope:
                raise IssueAuthorizationError("Development actor cannot verify this issue.")
            if not actor_context.roles.intersection({"DATA_STEWARD", "DATA_GOVERNANCE_SPECIALIST"}):
                raise IssueAuthorizationError("Development actor cannot verify issues.")
            if issue.status is not IssueStatus.RESOLVED:
                raise IssueValidationError("Development issue is not resolved.")
            updated = replace(
                issue,
                status=IssueStatus.VERIFIED,
                updated_at=datetime.now(timezone.utc),
                version=issue.version + 1,
            )
            self._issues[issue_id] = updated
            return updated

    def close(
        self,
        issue_id: str,
        actor_context: ActorContext | None,
    ) -> DataQualityIssue:
        if actor_context is None:
            raise IssueAuthorizationError("Development actor is required.")
        with self._lock:
            issue = self._issues.get(issue_id)
            if issue is None:
                raise IssueValidationError("Development issue was not found.")
            has_scope = (
                issue.scope_id in actor_context.permitted_source_ids
                if issue.scope_type is IssueScopeType.SOURCE
                else issue.scope_id in actor_context.permitted_dataset_ids
            )
            if not has_scope:
                raise IssueAuthorizationError("Development actor cannot close this issue.")
            if not actor_context.roles.intersection({"DATA_OWNER", "DATA_STEWARD"}):
                raise IssueAuthorizationError("Development actor cannot close issues.")
            if issue.status is not IssueStatus.VERIFIED:
                raise IssueValidationError("Development issue is not verified.")
            updated = replace(
                issue,
                status=IssueStatus.CLOSED,
                updated_at=datetime.now(timezone.utc),
                version=issue.version + 1,
            )
            self._issues[issue_id] = updated
            return updated

    def create_manual(
        self,
        draft: object,
        actor_context: ActorContext | None,
    ) -> DataQualityIssue:
        """Development-only manual issue creation."""
        from veri_kalitesi.issues import (
            ManualIssueDraft,
            IssueSourceEventType,
            IssueTriggerType,
            IssueStatus,
            validate_manual_issue_draft,
        )

        if not isinstance(draft, ManualIssueDraft):
            raise IssueValidationError("Development create_manual requires ManualIssueDraft.")
        validate_manual_issue_draft(draft)
        if actor_context is None:
            raise IssueAuthorizationError("Development actor is required.")
        now = datetime.now(timezone.utc)
        issue_id = str(uuid4())
        issue = DataQualityIssue(
            issue_id=issue_id,
            issue_no=f"DQI-{issue_id.replace('-', '')[:12].upper()}",
            source_event_id=draft.correlation_id,
            source_event_type=IssueSourceEventType.MANUAL,
            trigger_type=IssueTriggerType.MANUAL,
            scope_type=draft.scope_type,
            scope_id=draft.scope_id,
            status=IssueStatus.ASSIGNED,
            priority=draft.priority,
            assignee_user_id=draft.creator_user_id,
            deduplication_key_digest=draft.idempotency_key[:128],
            occurrence_count=1,
            created_at=now,
            updated_at=now,
            last_seen_at=now,
            title=draft.title,
        )
        with self._lock:
            self._issues[issue_id] = issue
        return issue

    def _authorize_assignment(
        self,
        issue: DataQualityIssue,
        actor_context: ActorContext,
    ) -> None:
        has_scope = (
            issue.scope_id in actor_context.permitted_source_ids
            if issue.scope_type is IssueScopeType.SOURCE
            else issue.scope_id in actor_context.permitted_dataset_ids
        )
        if (
            actor_context.privileged
            or not actor_context.roles.intersection({"DATA_STEWARD", "DATA_GOVERNANCE_SPECIALIST"})
            or not has_scope
            or issue.status not in {IssueStatus.ASSIGNED, IssueStatus.INVESTIGATING}
        ):
            raise IssueAuthorizationError("Development actor cannot assign issue.")
