"""Trusted issue creation, notification, and basic state transition service."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from typing import Callable, Generic, Protocol
from uuid import UUID, uuid5

from sqlalchemy.exc import SQLAlchemyError

from veri_kalitesi.audit import (
    AuditEventInput,
    AuditResult,
    PreparedAuditEvent,
)
from veri_kalitesi.identity import ActorContext, ActorType, is_trusted_actor_context
from veri_kalitesi.issues.contracts import AuditT, IssueRepository
from veri_kalitesi.issues.errors import (
    IssueAssignmentError,
    IssueAuthorizationError,
    IssueConflictError,
    IssueError,
    IssueNotFoundError,
    IssueNotificationConfigurationError,
    IssueNotificationTechnicalError,
    IssueRelationshipError,
    IssueTechnicalError,
    IssueValidationError,
)
from veri_kalitesi.issues.models import (
    DataQualityIssue,
    IssueAccessPolicy,
    IssueAssignment,
    IssueAssigneeProfile,
    IssueHistoryEntry,
    IssueResolutionDraft,
    IssueResolutionRecord,
    IssueRelationship,
    IssueRelationshipType,
    IssueScopeType,
    IssueSourceEventType,
    IssueStatus,
    IssueTrigger,
    IssueTriggerType,
    IssueVerificationOutcome,
    IssueVerificationRecord,
    ProtectedIssueResolution,
    TrustedIssueVerificationResult,
    issue_source_event_type,
    validate_access_policy,
    validate_assignment,
    validate_assignee_profile,
    validate_issue_trigger,
    validate_protected_resolution,
    validate_resolution_draft,
    validate_trusted_verification_result,
)
from veri_kalitesi.notifications import (
    NotificationAuthorizationError,
    NotificationConflictError,
    NotificationEvent,
    NotificationEventType,
    NotificationRecipientError,
    NotificationScopeType,
    NotificationTechnicalError,
    NotificationValidationError,
)


class IssueAssignmentResolver(Protocol):
    def resolve_assignment(self, trigger: IssueTrigger) -> IssueAssignment: ...


class IssueAssigneeDirectory(Protocol):
    def get_assignee_profile(self, user_id: str) -> IssueAssigneeProfile | None: ...


class IssueResolutionProtector(Protocol):
    def protect_resolution(
        self,
        draft: IssueResolutionDraft,
    ) -> ProtectedIssueResolution: ...


class IssueVerificationResolver(Protocol):
    def resolve_verification(
        self,
        verification_reference_id: str,
    ) -> TrustedIssueVerificationResult | None: ...


class IssueRelationshipResolver(Protocol):
    def resolve_predecessor(self, trigger: IssueTrigger) -> str | None: ...


class IssueNotificationPublisher(Protocol):
    def create_for_event(
        self,
        event: NotificationEvent,
        actor_context: ActorContext | None,
    ) -> tuple[object, ...]: ...


_PERSISTENCE_ERRORS = (sqlite3.Error, SQLAlchemyError, OSError)


class IssueService(Generic[AuditT]):
    def __init__(
        self,
        repository: IssueRepository[AuditT],
        assignment_resolver: IssueAssignmentResolver,
        notification_publisher: IssueNotificationPublisher,
        transactional_audit: AuditT,
        access_policy: IssueAccessPolicy,
        *,
        assignee_directory: IssueAssigneeDirectory | None = None,
        resolution_protector: IssueResolutionProtector | None = None,
        verification_resolver: IssueVerificationResolver | None = None,
        relationship_resolver: IssueRelationshipResolver | None = None,
        notification_actor_context_provider: Callable[[], ActorContext] | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        validate_access_policy(access_policy)
        self.repository = repository
        self.assignment_resolver = assignment_resolver
        self.notification_publisher = notification_publisher
        self.transactional_audit = transactional_audit
        self.access_policy = access_policy
        self.assignee_directory = assignee_directory
        self.resolution_protector = resolution_protector
        self.verification_resolver = verification_resolver
        self.relationship_resolver = relationship_resolver
        self.notification_actor_context_provider = notification_actor_context_provider
        self.clock = clock

    def create_for_trigger(
        self,
        trigger: IssueTrigger,
        actor_context: ActorContext | None,
    ) -> DataQualityIssue:
        validate_issue_trigger(trigger)
        context = self._authorize_actor(
            actor_context,
            self.access_policy.allowed_producer_actor_types,
            "create issues",
        )
        now = self._now()
        if trigger.occurred_at > now:
            raise IssueValidationError("Issue trigger cannot be in the future.")
        try:
            assignment = self.assignment_resolver.resolve_assignment(trigger)
        except IssueError:
            raise
        except Exception as exc:
            raise IssueTechnicalError(
                "Issue assignment resolution failed.", trigger.correlation_id
            ) from exc
        if assignment is None:
            raise IssueAssignmentError("No trusted issue assignment was resolved.")
        validate_assignment(assignment)

        issue_id = str(uuid5(_ISSUE_NAMESPACE, _digest_text(trigger.deduplication_key)))
        predecessor_issue_id = self._resolve_predecessor(trigger)
        issue = DataQualityIssue(
            issue_id=issue_id,
            issue_no=f"DQI-{issue_id.replace('-', '')[:12].upper()}",
            source_event_id=trigger.event_id,
            source_event_type=issue_source_event_type(trigger.trigger_type),
            trigger_type=trigger.trigger_type,
            scope_type=trigger.scope_type,
            scope_id=trigger.scope_id,
            status=IssueStatus.ASSIGNED,
            priority=assignment.priority,
            assignee_user_id=assignment.assignee_user_id,
            deduplication_key_digest=_digest_text(trigger.deduplication_key),
            occurrence_count=1,
            created_at=now,
            updated_at=now,
            last_seen_at=now,
        )
        history = IssueHistoryEntry(
            issue_id=issue.issue_id,
            action="ISSUE_CREATED_AND_ASSIGNED",
            actor_id=context.actor_id,
            old_status=None,
            new_status=IssueStatus.ASSIGNED,
            occurred_at=now,
        )
        relationship = (
            IssueRelationship(
                predecessor_issue_id=predecessor_issue_id,
                successor_issue_id=issue.issue_id,
                relationship_type=IssueRelationshipType.RECURRENCE,
                created_at=now,
            )
            if predecessor_issue_id is not None
            else None
        )
        relationship_history = (
            IssueHistoryEntry(
                issue_id=predecessor_issue_id,
                action="ISSUE_LINKED_TO_NEW_QUALITY_FAILURE",
                actor_id=context.actor_id,
                old_status=IssueStatus.CLOSED,
                new_status=IssueStatus.CLOSED,
                occurred_at=now,
            )
            if predecessor_issue_id is not None
            else None
        )
        audit_event = self._prepare_audit(
            AuditEventInput(
                actor_id=context.actor_id,
                actor_type=context.actor_type.value,
                correlation_id=trigger.correlation_id,
                action="DATA_QUALITY_ISSUE_TRIGGER_PROCESSED",
                object_type="DataQualityIssue",
                object_id=issue.issue_id,
                result=AuditResult.SUCCESS,
                reason_code=trigger.trigger_type.value,
                old_values={},
                new_values={
                    "source_event_type": issue.source_event_type.value,
                    "trigger_type": issue.trigger_type.value,
                    "status": issue.status.value,
                    "priority": issue.priority.value,
                    "assignee_user_id": issue.assignee_user_id,
                    "scope_id": issue.scope_id,
                    "deduplication_key": trigger.deduplication_key,
                },
                occurred_at=now,
                session_id=context.session_id,
            ),
            trigger.correlation_id,
        )
        reopen_audit_event = self._prepare_audit(
            AuditEventInput(
                actor_id=context.actor_id,
                actor_type=context.actor_type.value,
                correlation_id=trigger.correlation_id,
                action="DATA_QUALITY_ISSUE_REOPENED",
                object_type="DataQualityIssue",
                object_id=issue.issue_id,
                result=AuditResult.SUCCESS,
                reason_code="RECURRING_QUALITY_FAILURE",
                old_values={"status": IssueStatus.CLOSED.value},
                new_values={
                    "status": IssueStatus.WAITING_FOR_RESOLUTION.value,
                    "source_event_type": issue.source_event_type.value,
                    "trigger_type": issue.trigger_type.value,
                },
                occurred_at=now,
                session_id=context.session_id,
            ),
            trigger.correlation_id,
        )
        relationship_audit_event = (
            self._prepare_audit(
                AuditEventInput(
                    actor_id=context.actor_id,
                    actor_type=context.actor_type.value,
                    correlation_id=trigger.correlation_id,
                    action="DATA_QUALITY_ISSUE_LINKED",
                    object_type="DataQualityIssue",
                    object_id=issue.issue_id,
                    result=AuditResult.SUCCESS,
                    reason_code="NEW_RELATED_QUALITY_FAILURE",
                    old_values={},
                    new_values={
                        "relationship_type": IssueRelationshipType.RECURRENCE.value,
                        "source_event_type": issue.source_event_type.value,
                        "status": issue.status.value,
                    },
                    occurred_at=now,
                    session_id=context.session_id,
                ),
                trigger.correlation_id,
            )
            if relationship is not None
            else None
        )
        try:
            stored = self.repository.add_or_increment(
                issue,
                history,
                payload_digest=_payload_digest(trigger, assignment),
                source_event_occurred_at=trigger.occurred_at,
                relationship=relationship,
                relationship_history=relationship_history,
                audit_event=audit_event,
                reopen_audit_event=reopen_audit_event,
                relationship_audit_event=relationship_audit_event,
                audit_outbox=self.transactional_audit,
            )
        except IssueConflictError:
            raise
        except _PERSISTENCE_ERRORS as exc:
            raise IssueTechnicalError(
                "Issue could not be persisted.", trigger.correlation_id
            ) from exc
        self.transactional_audit.publish_pending()
        self._publish_notification(trigger, context, stored)
        return stored

    def _resolve_predecessor(self, trigger: IssueTrigger) -> str | None:
        if (
            issue_source_event_type(trigger.trigger_type) is not IssueSourceEventType.QUALITY
            or self.relationship_resolver is None
        ):
            return None
        try:
            predecessor_issue_id = self.relationship_resolver.resolve_predecessor(trigger)
        except IssueError:
            raise
        except Exception as exc:
            raise IssueTechnicalError(
                "Issue relationship resolution failed.", trigger.correlation_id
            ) from exc
        if predecessor_issue_id is None:
            return None
        try:
            UUID(predecessor_issue_id)
        except (AttributeError, TypeError, ValueError) as exc:
            raise IssueRelationshipError("Trusted predecessor issue ID is invalid.") from exc
        return predecessor_issue_id

    def start_investigation(
        self,
        issue_id: str,
        actor_context: ActorContext | None,
    ) -> DataQualityIssue:
        context = self._authorize_actor(
            actor_context,
            self.access_policy.allowed_reader_actor_types,
            "investigate issues",
        )
        now = self._now()
        try:
            issue = self.repository.get(issue_id)
        except _PERSISTENCE_ERRORS as exc:
            raise IssueTechnicalError("Issue could not be read.", context.correlation_id) from exc
        if issue.assignee_user_id != context.actor_id or not _has_scope(context, issue):
            raise IssueAuthorizationError("Actor cannot investigate this issue.")
        if issue.status is not IssueStatus.ASSIGNED:
            raise IssueValidationError("Only an assigned issue can enter investigation.")

        history = IssueHistoryEntry(
            issue_id=issue.issue_id,
            action="ISSUE_INVESTIGATION_STARTED",
            actor_id=context.actor_id,
            old_status=IssueStatus.ASSIGNED,
            new_status=IssueStatus.INVESTIGATING,
            occurred_at=now,
        )
        audit_event = self._prepare_audit(
            AuditEventInput(
                actor_id=context.actor_id,
                actor_type=context.actor_type.value,
                correlation_id=context.correlation_id,
                action="DATA_QUALITY_ISSUE_STATUS_CHANGED",
                object_type="DataQualityIssue",
                object_id=issue.issue_id,
                result=AuditResult.SUCCESS,
                reason_code="INVESTIGATION_STARTED",
                old_values={"status": IssueStatus.ASSIGNED.value},
                new_values={
                    "status": IssueStatus.INVESTIGATING.value,
                    "assignee_user_id": issue.assignee_user_id,
                    "scope_id": issue.scope_id,
                },
                occurred_at=now,
                session_id=context.session_id,
            ),
            context.correlation_id,
        )
        try:
            stored = self.repository.transition_status(
                issue.issue_id,
                IssueStatus.ASSIGNED,
                IssueStatus.INVESTIGATING,
                now,
                history,
                audit_event=audit_event,
                audit_outbox=self.transactional_audit,
            )
        except _PERSISTENCE_ERRORS as exc:
            raise IssueTechnicalError(
                "Issue status could not be updated.", context.correlation_id
            ) from exc
        self.transactional_audit.publish_pending()
        return stored

    def reassign(
        self,
        issue_id: str,
        assignment: IssueAssignment,
        actor_context: ActorContext | None,
    ) -> DataQualityIssue:
        validate_assignment(assignment)
        context = self._authorize_actor(
            actor_context,
            self.access_policy.allowed_reader_actor_types,
            "assign issues",
        )
        if not context.roles.intersection(_ASSIGNER_ROLES):
            raise IssueAuthorizationError("Actor cannot assign issues.")
        now = self._now()
        try:
            issue = self.repository.get(issue_id)
        except _PERSISTENCE_ERRORS as exc:
            raise IssueTechnicalError("Issue could not be read.", context.correlation_id) from exc
        if not _has_scope(context, issue):
            raise IssueAuthorizationError("Actor cannot assign this issue.")
        if issue.status not in {IssueStatus.ASSIGNED, IssueStatus.INVESTIGATING}:
            raise IssueValidationError("Only assigned or investigating issues can be reassigned.")
        if (
            issue.assignee_user_id == assignment.assignee_user_id
            and issue.priority is assignment.priority
        ):
            raise IssueValidationError("Issue assignment must change.")

        profile = self._resolve_assignee_profile(assignment.assignee_user_id, context)
        if not profile.active or not _profile_has_scope(profile, issue):
            raise IssueAssignmentError("Assignee is inactive or outside the issue scope.")

        history = IssueHistoryEntry(
            issue_id=issue.issue_id,
            action="ISSUE_REASSIGNED",
            actor_id=context.actor_id,
            old_status=issue.status,
            new_status=IssueStatus.ASSIGNED,
            occurred_at=now,
            old_assignee_user_id=issue.assignee_user_id,
            new_assignee_user_id=assignment.assignee_user_id,
            old_priority=issue.priority,
            new_priority=assignment.priority,
        )
        audit_event = self._prepare_audit(
            AuditEventInput(
                actor_id=context.actor_id,
                actor_type=context.actor_type.value,
                correlation_id=context.correlation_id,
                action="DATA_QUALITY_ISSUE_ASSIGNED",
                object_type="DataQualityIssue",
                object_id=issue.issue_id,
                result=AuditResult.SUCCESS,
                reason_code="AUTHORIZED_REASSIGNMENT",
                old_values={
                    "status": issue.status.value,
                    "priority": issue.priority.value,
                    "assignee_user_id": issue.assignee_user_id,
                },
                new_values={
                    "status": IssueStatus.ASSIGNED.value,
                    "priority": assignment.priority.value,
                    "assignee_user_id": assignment.assignee_user_id,
                    "scope_id": issue.scope_id,
                },
                occurred_at=now,
                session_id=context.session_id,
            ),
            context.correlation_id,
        )
        try:
            stored = self.repository.update_assignment(
                issue.issue_id,
                expected_status=issue.status,
                expected_assignee_user_id=issue.assignee_user_id,
                expected_priority=issue.priority,
                assignee_user_id=assignment.assignee_user_id,
                priority=assignment.priority,
                updated_at=now,
                history=history,
                audit_event=audit_event,
                audit_outbox=self.transactional_audit,
            )
        except _PERSISTENCE_ERRORS as exc:
            raise IssueTechnicalError(
                "Issue assignment could not be updated.", context.correlation_id
            ) from exc
        self.transactional_audit.publish_pending()
        self._publish_assignment_notification(stored, history, context)
        return stored

    def resolve(
        self,
        issue_id: str,
        draft: IssueResolutionDraft,
        actor_context: ActorContext | None,
    ) -> DataQualityIssue:
        validate_resolution_draft(draft)
        context = self._authorize_actor(
            actor_context,
            self.access_policy.allowed_reader_actor_types,
            "resolve issues",
        )
        if not context.roles.intersection(_RESOLVER_ROLES):
            raise IssueAuthorizationError("Actor cannot resolve issues.")
        now = self._now()
        try:
            issue = self.repository.get(issue_id)
        except _PERSISTENCE_ERRORS as exc:
            raise IssueTechnicalError("Issue could not be read.", context.correlation_id) from exc
        if issue.assignee_user_id != context.actor_id or not _has_scope(context, issue):
            raise IssueAuthorizationError("Actor cannot resolve this issue.")
        if issue.status not in {
            IssueStatus.INVESTIGATING,
            IssueStatus.WAITING_FOR_RESOLUTION,
        }:
            raise IssueValidationError(
                "Only investigating or waiting-for-resolution issues can be resolved."
            )
        if draft.completed_at < issue.created_at or draft.completed_at > now:
            raise IssueValidationError("completed_at is outside the issue lifetime.")

        protected = self._protect_resolution(draft, context)
        if (
            protected.evidence_reference_id != draft.evidence_reference_id
            or protected.completed_at != draft.completed_at
        ):
            raise IssueValidationError(
                "Resolution protector changed immutable resolution references."
            )
        resolution = IssueResolutionRecord(
            issue_id=issue.issue_id,
            root_cause=protected.root_cause,
            corrective_action=protected.corrective_action,
            evidence_reference_id=protected.evidence_reference_id,
            completed_at=protected.completed_at,
            protection_policy_version=protected.protection_policy_version,
            created_by=context.actor_id,
            created_at=now,
        )
        history = IssueHistoryEntry(
            issue_id=issue.issue_id,
            action="ISSUE_RESOLVED",
            actor_id=context.actor_id,
            old_status=issue.status,
            new_status=IssueStatus.RESOLVED,
            occurred_at=now,
            resolution_id=resolution.resolution_id,
        )
        audit_event = self._prepare_audit(
            AuditEventInput(
                actor_id=context.actor_id,
                actor_type=context.actor_type.value,
                correlation_id=context.correlation_id,
                action="DATA_QUALITY_ISSUE_RESOLVED",
                object_type="DataQualityIssue",
                object_id=issue.issue_id,
                result=AuditResult.SUCCESS,
                reason_code="RESOLUTION_RECORDED",
                old_values={"status": issue.status.value},
                new_values={
                    "status": IssueStatus.RESOLVED.value,
                    "resolution_fields_complete": True,
                    "protection_policy_version": protected.protection_policy_version,
                    "root_cause": protected.root_cause,
                    "corrective_action": protected.corrective_action,
                    "evidence_reference_id": protected.evidence_reference_id,
                    "scope_id": issue.scope_id,
                },
                occurred_at=now,
                session_id=context.session_id,
            ),
            context.correlation_id,
        )
        try:
            stored = self.repository.resolve(
                issue.issue_id,
                expected_status=issue.status,
                expected_assignee_user_id=issue.assignee_user_id,
                resolution=resolution,
                updated_at=now,
                history=history,
                audit_event=audit_event,
                audit_outbox=self.transactional_audit,
            )
        except _PERSISTENCE_ERRORS as exc:
            raise IssueTechnicalError(
                "Issue resolution could not be persisted.", context.correlation_id
            ) from exc
        self.transactional_audit.publish_pending()
        return stored

    def record_verification_result(
        self,
        issue_id: str,
        verification_reference_id: str,
        actor_context: ActorContext | None,
    ) -> DataQualityIssue:
        _validate_uuid_reference("verification_reference_id", verification_reference_id)
        context = self._authorize_actor(
            actor_context,
            self.access_policy.allowed_reader_actor_types,
            "verify issues",
        )
        if not context.roles.intersection(_VERIFIER_ROLES):
            raise IssueAuthorizationError("Actor cannot verify issues.")
        now = self._now()
        try:
            issue = self.repository.get(issue_id)
        except _PERSISTENCE_ERRORS as exc:
            raise IssueTechnicalError("Issue could not be read.", context.correlation_id) from exc
        if not _has_scope(context, issue):
            raise IssueAuthorizationError("Actor cannot verify this issue.")
        if issue.status is not IssueStatus.RESOLVED:
            raise IssueValidationError("Only a resolved issue can receive verification results.")

        result = self._resolve_verification(verification_reference_id, context)
        if result.verification_reference_id != verification_reference_id:
            raise IssueValidationError("Verification resolver returned a different reference.")
        if result.scope_type is not issue.scope_type or result.scope_id != issue.scope_id:
            raise IssueAuthorizationError("Verification result is outside the issue scope.")
        if result.completed_at < issue.updated_at or result.completed_at > now:
            raise IssueValidationError("Verification completion is outside the resolved lifetime.")
        if result.outcome is IssueVerificationOutcome.QUALITY_PASSED:
            try:
                resolution = self.repository.get_latest_resolution(issue.issue_id)
            except _PERSISTENCE_ERRORS as exc:
                raise IssueTechnicalError(
                    "Issue resolution could not be read.", context.correlation_id
                ) from exc
            if resolution.created_by == context.actor_id:
                raise IssueAuthorizationError(
                    "Resolution creator cannot verify the same issue resolution."
                )

        target_status = {
            IssueVerificationOutcome.QUALITY_PASSED: IssueStatus.VERIFIED,
            IssueVerificationOutcome.TECHNICAL_ERROR: IssueStatus.RESOLVED,
            IssueVerificationOutcome.QUALITY_FAILED: IssueStatus.WAITING_FOR_RESOLUTION,
            IssueVerificationOutcome.PARTIAL: IssueStatus.WAITING_FOR_RESOLUTION,
        }[result.outcome]
        verification = IssueVerificationRecord(
            issue_id=issue.issue_id,
            verification_reference_id=result.verification_reference_id,
            execution_id=result.execution_id,
            score_id=result.score_id,
            scope_type=result.scope_type,
            scope_id=result.scope_id,
            outcome=result.outcome,
            completed_at=result.completed_at,
            recorded_by=context.actor_id,
            recorded_at=now,
        )
        history = IssueHistoryEntry(
            issue_id=issue.issue_id,
            action={
                IssueVerificationOutcome.QUALITY_PASSED: "ISSUE_VERIFIED",
                IssueVerificationOutcome.TECHNICAL_ERROR: "ISSUE_VERIFICATION_TECHNICAL_ERROR",
                IssueVerificationOutcome.QUALITY_FAILED: "ISSUE_VERIFICATION_FAILED",
                IssueVerificationOutcome.PARTIAL: "ISSUE_VERIFICATION_FAILED",
            }[result.outcome],
            actor_id=context.actor_id,
            old_status=IssueStatus.RESOLVED,
            new_status=target_status,
            occurred_at=now,
            verification_id=verification.verification_id,
        )
        audit_event = self._prepare_audit(
            AuditEventInput(
                actor_id=context.actor_id,
                actor_type=context.actor_type.value,
                correlation_id=context.correlation_id,
                action="DATA_QUALITY_ISSUE_VERIFICATION_RECORDED",
                object_type="DataQualityIssue",
                object_id=issue.issue_id,
                result=AuditResult.SUCCESS,
                reason_code=result.outcome.value,
                old_values={"status": IssueStatus.RESOLVED.value},
                new_values={
                    "status": target_status.value,
                    "verification_outcome": result.outcome.value,
                    "has_score_reference": result.score_id is not None,
                },
                occurred_at=now,
                session_id=context.session_id,
            ),
            context.correlation_id,
        )
        try:
            stored = self.repository.record_verification(
                issue.issue_id,
                expected_status=IssueStatus.RESOLVED,
                target_status=target_status,
                verification=verification,
                updated_at=now,
                history=history,
                audit_event=audit_event,
                audit_outbox=self.transactional_audit,
            )
        except _PERSISTENCE_ERRORS as exc:
            raise IssueTechnicalError(
                "Issue verification could not be persisted.", context.correlation_id
            ) from exc
        self.transactional_audit.publish_pending()
        return stored

    def close(
        self,
        issue_id: str,
        actor_context: ActorContext | None,
    ) -> DataQualityIssue:
        context = self._authorize_actor(
            actor_context,
            self.access_policy.allowed_reader_actor_types,
            "close issues",
        )
        if not context.roles.intersection(_CLOSER_ROLES):
            raise IssueAuthorizationError("Actor cannot close issues.")
        now = self._now()
        try:
            issue = self.repository.get(issue_id)
        except _PERSISTENCE_ERRORS as exc:
            raise IssueTechnicalError("Issue could not be read.", context.correlation_id) from exc
        if not _has_scope(context, issue):
            raise IssueAuthorizationError("Actor cannot close this issue.")
        if issue.status is not IssueStatus.VERIFIED:
            raise IssueValidationError("Only a verified issue can be closed.")

        try:
            verification = self.repository.get_latest_verification(issue.issue_id)
        except IssueNotFoundError as exc:
            raise IssueValidationError(
                "Verified issue must have a persisted verification result."
            ) from exc
        except _PERSISTENCE_ERRORS as exc:
            raise IssueTechnicalError(
                "Issue verification could not be read.", context.correlation_id
            ) from exc
        if (
            verification.outcome is not IssueVerificationOutcome.QUALITY_PASSED
            or verification.score_id is None
        ):
            raise IssueValidationError(
                "Issue closure requires a successful scored verification result."
            )

        history = IssueHistoryEntry(
            issue_id=issue.issue_id,
            action="ISSUE_CLOSED",
            actor_id=context.actor_id,
            old_status=IssueStatus.VERIFIED,
            new_status=IssueStatus.CLOSED,
            occurred_at=now,
            verification_id=verification.verification_id,
        )
        audit_event = self._prepare_audit(
            AuditEventInput(
                actor_id=context.actor_id,
                actor_type=context.actor_type.value,
                correlation_id=context.correlation_id,
                action="DATA_QUALITY_ISSUE_CLOSED",
                object_type="DataQualityIssue",
                object_id=issue.issue_id,
                result=AuditResult.SUCCESS,
                reason_code="SUCCESSFUL_VERIFICATION_CONFIRMED",
                old_values={"status": IssueStatus.VERIFIED.value},
                new_values={
                    "status": IssueStatus.CLOSED.value,
                    "verification_outcome": verification.outcome.value,
                },
                occurred_at=now,
                session_id=context.session_id,
            ),
            context.correlation_id,
        )
        try:
            stored = self.repository.transition_status(
                issue.issue_id,
                IssueStatus.VERIFIED,
                IssueStatus.CLOSED,
                now,
                history,
                audit_event=audit_event,
                audit_outbox=self.transactional_audit,
            )
        except _PERSISTENCE_ERRORS as exc:
            raise IssueTechnicalError(
                "Issue closure could not be persisted.", context.correlation_id
            ) from exc
        self.transactional_audit.publish_pending()
        return stored

    def _resolve_verification(
        self,
        verification_reference_id: str,
        context: ActorContext,
    ) -> TrustedIssueVerificationResult:
        if self.verification_resolver is None:
            raise IssueValidationError("Trusted verification resolver is not configured.")
        try:
            result = self.verification_resolver.resolve_verification(verification_reference_id)
        except IssueError:
            raise
        except Exception as exc:
            raise IssueTechnicalError(
                "Issue verification lookup failed.", context.correlation_id
            ) from exc
        if result is None:
            raise IssueValidationError("Verification result was not found.")
        validate_trusted_verification_result(result)
        return result

    def _protect_resolution(
        self,
        draft: IssueResolutionDraft,
        context: ActorContext,
    ) -> ProtectedIssueResolution:
        if self.resolution_protector is None:
            raise IssueValidationError("Resolution protection policy is not configured.")
        try:
            protected = self.resolution_protector.protect_resolution(draft)
        except IssueError:
            raise
        except Exception as exc:
            raise IssueTechnicalError(
                "Issue resolution protection failed.", context.correlation_id
            ) from exc
        if protected is None:
            raise IssueValidationError("Resolution protection returned no result.")
        validate_protected_resolution(protected)
        return protected

    def _resolve_assignee_profile(
        self,
        user_id: str,
        context: ActorContext,
    ) -> IssueAssigneeProfile:
        if self.assignee_directory is None:
            raise IssueAssignmentError("Trusted assignee directory is not configured.")
        try:
            profile = self.assignee_directory.get_assignee_profile(user_id)
        except IssueError:
            raise
        except Exception as exc:
            raise IssueTechnicalError(
                "Assignee directory lookup failed.", context.correlation_id
            ) from exc
        if profile is None or profile.user_id != user_id:
            raise IssueAssignmentError("Assignee was not found in the trusted directory.")
        validate_assignee_profile(profile)
        return profile

    def _publish_notification(
        self,
        trigger: IssueTrigger,
        context: ActorContext,
        issue: DataQualityIssue,
    ) -> None:
        event_type = {
            IssueTriggerType.QUALITY_THRESHOLD: NotificationEventType.QUALITY_THRESHOLD,
            IssueTriggerType.CRITICAL_RULE_FAILURE: (NotificationEventType.CRITICAL_RULE_FAILURE),
            IssueTriggerType.TECHNICAL_ERROR: NotificationEventType.TECHNICAL_ERROR,
        }[trigger.trigger_type]
        try:
            self.notification_publisher.create_for_event(
                NotificationEvent(
                    event_type=event_type,
                    scope_type=NotificationScopeType(trigger.scope_type.value),
                    scope_id=trigger.scope_id,
                    deduplication_key=f"ISSUE.{trigger.deduplication_key}",
                    occurred_at=trigger.occurred_at,
                    correlation_id=trigger.correlation_id,
                ),
                context,
            )
        except NotificationTechnicalError as exc:
            raise IssueNotificationTechnicalError(
                "Issue persisted but notification failed technically.",
                issue.issue_id,
                trigger.correlation_id,
            ) from exc
        except (
            NotificationAuthorizationError,
            NotificationConflictError,
            NotificationRecipientError,
            NotificationValidationError,
        ) as exc:
            raise IssueNotificationConfigurationError(
                "Issue persisted but notification policy could not be completed.",
                issue.issue_id,
                trigger.correlation_id,
            ) from exc
        except Exception as exc:
            raise IssueNotificationTechnicalError(
                "Issue persisted but notification failed technically.",
                issue.issue_id,
                trigger.correlation_id,
            ) from exc

    def _publish_assignment_notification(
        self,
        issue: DataQualityIssue,
        history: IssueHistoryEntry,
        context: ActorContext,
    ) -> None:
        try:
            if self.notification_actor_context_provider is None:
                raise NotificationAuthorizationError(
                    "Trusted notification producer is not configured."
                )
            producer_context = self.notification_actor_context_provider()
            self.notification_publisher.create_for_event(
                NotificationEvent(
                    event_type=NotificationEventType.ISSUE_ASSIGNED,
                    scope_type=NotificationScopeType.ISSUE_ASSIGNMENT,
                    scope_id=history.history_id,
                    deduplication_key=f"ISSUE.ASSIGNMENT.{history.history_id}",
                    occurred_at=history.occurred_at,
                    correlation_id=context.correlation_id,
                ),
                producer_context,
            )
        except NotificationTechnicalError as exc:
            raise IssueNotificationTechnicalError(
                "Issue persisted but notification failed technically.",
                issue.issue_id,
                context.correlation_id,
            ) from exc
        except (
            NotificationAuthorizationError,
            NotificationConflictError,
            NotificationRecipientError,
            NotificationValidationError,
        ) as exc:
            raise IssueNotificationConfigurationError(
                "Issue persisted but notification policy could not be completed.",
                issue.issue_id,
                context.correlation_id,
            ) from exc
        except Exception as exc:
            raise IssueNotificationTechnicalError(
                "Issue persisted but notification failed technically.",
                issue.issue_id,
                context.correlation_id,
            ) from exc

    def _authorize_actor(
        self,
        context: ActorContext | None,
        allowed_actor_types: frozenset[ActorType],
        operation: str,
    ) -> ActorContext:
        now = self._now()
        if not is_trusted_actor_context(context):
            raise IssueAuthorizationError("Trusted actor context is required.")
        assert context is not None
        if context.issued_at > now or context.expires_at <= now:
            raise IssueAuthorizationError("Actor context is not currently valid.")
        if context.policy_version != self.access_policy.actor_policy_version:
            raise IssueAuthorizationError("Actor context policy version is not accepted.")
        if context.actor_type not in allowed_actor_types:
            raise IssueAuthorizationError(f"Actor type cannot {operation}.")
        if context.privileged:
            raise IssueAuthorizationError("Privileged context cannot use standard issue flows.")
        return context

    def _now(self) -> datetime:
        now = self.clock()
        if now.tzinfo is None or now.utcoffset() is None:
            raise IssueValidationError("Issue clock must be timezone-aware.")
        return now.astimezone(timezone.utc)

    def _prepare_audit(self, event: AuditEventInput, correlation_id: str) -> PreparedAuditEvent:
        try:
            return self.transactional_audit.prepare(event)
        except Exception as exc:
            raise IssueTechnicalError(
                "Issue audit event could not be prepared.", correlation_id
            ) from exc


def _has_scope(context: ActorContext, issue: DataQualityIssue) -> bool:
    if issue.scope_type is IssueScopeType.DATASET:
        return issue.scope_id in context.permitted_dataset_ids
    return issue.scope_id in context.permitted_source_ids


def _profile_has_scope(profile: IssueAssigneeProfile, issue: DataQualityIssue) -> bool:
    if issue.scope_type is IssueScopeType.DATASET:
        return issue.scope_id in profile.permitted_dataset_ids
    return issue.scope_id in profile.permitted_source_ids


def _payload_digest(trigger: IssueTrigger, assignment: IssueAssignment) -> str:
    payload = {
        "trigger_type": trigger.trigger_type.value,
        "scope_type": trigger.scope_type.value,
        "scope_id": trigger.scope_id,
        "assignee_user_id": assignment.assignee_user_id,
        "priority": assignment.priority.value,
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _validate_uuid_reference(field_name: str, value: str) -> None:
    try:
        UUID(value)
    except (AttributeError, TypeError, ValueError) as exc:
        raise IssueValidationError(f"{field_name} must be a UUID.") from exc


_ISSUE_NAMESPACE = UUID("7f1f9e1e-fd18-47f1-900c-a3060efbbeca")
_ASSIGNER_ROLES = frozenset({"DATA_STEWARD", "DATA_GOVERNANCE_SPECIALIST"})
_RESOLVER_ROLES = frozenset({"DATA_STEWARD", "DATA_ENGINEER"})
_VERIFIER_ROLES = frozenset({"DATA_OWNER", "DATA_STEWARD"})
_CLOSER_ROLES = frozenset({"DATA_OWNER", "DATA_STEWARD"})
