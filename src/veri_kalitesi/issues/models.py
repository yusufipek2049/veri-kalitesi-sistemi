"""Data-minimum issue and state transition models."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from veri_kalitesi.identity import ActorType
from veri_kalitesi.issues.errors import IssueValidationError


_CODE_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,199}")
_FORBIDDEN_TEXT = (
    "password",
    "passwd",
    "secret",
    "token",
    "credential",
    "authorization",
)


class IssueTriggerType(str, Enum):
    QUALITY_THRESHOLD = "QUALITY_THRESHOLD"
    CRITICAL_RULE_FAILURE = "CRITICAL_RULE_FAILURE"
    TECHNICAL_ERROR = "TECHNICAL_ERROR"
    MANUAL = "MANUAL"


class IssueSourceEventType(str, Enum):
    QUALITY = "QUALITY"
    TECHNICAL = "TECHNICAL"
    MANUAL = "MANUAL"


class IssueScopeType(str, Enum):
    DATASET = "DATASET"
    SOURCE = "SOURCE"


class IssuePriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IssueStatus(str, Enum):
    NEW = "NEW"
    ASSIGNED = "ASSIGNED"
    INVESTIGATING = "INVESTIGATING"
    WAITING_FOR_RESOLUTION = "WAITING_FOR_RESOLUTION"
    RESOLVED = "RESOLVED"
    VERIFIED = "VERIFIED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class IssueVerificationOutcome(str, Enum):
    QUALITY_FAILED = "QUALITY_FAILED"
    PARTIAL = "PARTIAL"
    TECHNICAL_ERROR = "TECHNICAL_ERROR"
    QUALITY_PASSED = "QUALITY_PASSED"


class IssueRelationshipType(str, Enum):
    RECURRENCE = "RECURRENCE"


@dataclass(frozen=True)
class IssueTrigger:
    trigger_type: IssueTriggerType
    scope_type: IssueScopeType
    scope_id: str
    deduplication_key: str
    occurred_at: datetime
    correlation_id: str
    event_id: str = field(default_factory=lambda: str(uuid4()))
    title: str = ""
    execution_id: str | None = None
    rule_version_id: str | None = None
    eligible_for_auto_issue: bool = False
    failed_count: int | None = None
    measurement_status: str | None = None


@dataclass(frozen=True)
class IssueAssignment:
    assignee_user_id: str
    priority: IssuePriority


@dataclass(frozen=True)
class IssueAssigneeProfile:
    user_id: str
    active: bool
    permitted_source_ids: frozenset[str]
    permitted_dataset_ids: frozenset[str]


@dataclass(frozen=True)
class IssueResolutionDraft:
    root_cause: str
    corrective_action: str
    evidence_reference_id: str
    completed_at: datetime


@dataclass(frozen=True)
class ProtectedIssueResolution:
    root_cause: str
    corrective_action: str
    evidence_reference_id: str
    completed_at: datetime
    protection_policy_version: str


@dataclass(frozen=True)
class IssueResolutionRecord:
    issue_id: str
    root_cause: str
    corrective_action: str
    evidence_reference_id: str
    completed_at: datetime
    protection_policy_version: str
    created_by: str
    created_at: datetime
    resolution_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(frozen=True)
class TrustedIssueVerificationResult:
    verification_reference_id: str
    execution_id: str
    score_id: str | None
    scope_type: IssueScopeType
    scope_id: str
    outcome: IssueVerificationOutcome
    completed_at: datetime


@dataclass(frozen=True)
class IssueVerificationRecord:
    issue_id: str
    verification_reference_id: str
    execution_id: str
    score_id: str | None
    scope_type: IssueScopeType
    scope_id: str
    outcome: IssueVerificationOutcome
    completed_at: datetime
    recorded_by: str
    recorded_at: datetime
    verification_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(frozen=True)
class IssueRelationship:
    predecessor_issue_id: str
    successor_issue_id: str
    relationship_type: IssueRelationshipType
    created_at: datetime
    relationship_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(frozen=True)
class DataQualityIssue:
    issue_no: str
    source_event_id: str
    source_event_type: IssueSourceEventType
    trigger_type: IssueTriggerType
    scope_type: IssueScopeType
    scope_id: str
    status: IssueStatus
    priority: IssuePriority
    assignee_user_id: str
    deduplication_key_digest: str
    occurrence_count: int
    created_at: datetime
    updated_at: datetime
    last_seen_at: datetime
    title: str = ""
    issue_id: str = field(default_factory=lambda: str(uuid4()))
    version: int = 1
    source_execution_id: str | None = None
    source_rule_version_id: str | None = None


@dataclass(frozen=True)
class IssueHistoryEntry:
    issue_id: str
    action: str
    actor_id: str
    old_status: IssueStatus | None
    new_status: IssueStatus
    occurred_at: datetime
    old_assignee_user_id: str | None = None
    new_assignee_user_id: str | None = None
    old_priority: IssuePriority | None = None
    new_priority: IssuePriority | None = None
    resolution_id: str | None = None
    verification_id: str | None = None
    history_id: str = field(default_factory=lambda: str(uuid4()))
    source_event_id: str | None = None
    source_event_occurred_at: datetime | None = None
    source_event_payload_digest: str | None = None


@dataclass(frozen=True)
class IssueAccessPolicy:
    version: str
    actor_policy_version: str
    allowed_reader_actor_types: frozenset[ActorType] = field(
        default_factory=lambda: frozenset({ActorType.USER})
    )
    allowed_producer_actor_types: frozenset[ActorType] = field(
        default_factory=lambda: frozenset({ActorType.SERVICE})
    )
    manual_creator_actor_types: frozenset[ActorType] = field(
        default_factory=lambda: frozenset({ActorType.USER})
    )


@dataclass(frozen=True)
class ManualIssueDraft:
    title: str
    scope_type: IssueScopeType
    scope_id: str
    priority: IssuePriority
    idempotency_key: str
    creator_user_id: str
    correlation_id: str = field(default_factory=lambda: str(uuid4()))


def validate_issue_trigger(trigger: IssueTrigger) -> None:
    if not isinstance(trigger.trigger_type, IssueTriggerType):
        raise IssueValidationError("trigger_type is invalid.")
    if not isinstance(trigger.scope_type, IssueScopeType):
        raise IssueValidationError("scope_type is invalid.")
    _validate_uuid("event_id", trigger.event_id)
    _validate_uuid("scope_id", trigger.scope_id)
    _validate_code("deduplication_key", trigger.deduplication_key)
    _validate_code("correlation_id", trigger.correlation_id)
    if not _is_aware(trigger.occurred_at):
        raise IssueValidationError("occurred_at must be timezone-aware.")


def validate_assignment(assignment: IssueAssignment) -> None:
    _validate_uuid("assignee_user_id", assignment.assignee_user_id)
    if not isinstance(assignment.priority, IssuePriority):
        raise IssueValidationError("priority is invalid.")


def validate_assignee_profile(profile: IssueAssigneeProfile) -> None:
    _validate_uuid("profile.user_id", profile.user_id)
    if not isinstance(profile.active, bool):
        raise IssueValidationError("profile.active is invalid.")
    for scope_id in profile.permitted_source_ids | profile.permitted_dataset_ids:
        _validate_uuid("profile.scope_id", scope_id)


def validate_resolution_draft(draft: IssueResolutionDraft) -> None:
    _validate_resolution_text("root_cause", draft.root_cause, allow_markup=True)
    _validate_resolution_text("corrective_action", draft.corrective_action, allow_markup=True)
    _validate_uuid("evidence_reference_id", draft.evidence_reference_id)
    if not _is_aware(draft.completed_at):
        raise IssueValidationError("completed_at must be timezone-aware.")


def validate_protected_resolution(resolution: ProtectedIssueResolution) -> None:
    _validate_resolution_text("root_cause", resolution.root_cause, allow_markup=False)
    _validate_resolution_text("corrective_action", resolution.corrective_action, allow_markup=False)
    _validate_uuid("evidence_reference_id", resolution.evidence_reference_id)
    if not _is_aware(resolution.completed_at):
        raise IssueValidationError("completed_at must be timezone-aware.")
    _validate_code("protection_policy_version", resolution.protection_policy_version)


def validate_trusted_verification_result(result: TrustedIssueVerificationResult) -> None:
    _validate_uuid("verification_reference_id", result.verification_reference_id)
    _validate_uuid("execution_id", result.execution_id)
    if result.score_id is not None:
        _validate_uuid("score_id", result.score_id)
    if not isinstance(result.scope_type, IssueScopeType):
        raise IssueValidationError("verification scope_type is invalid.")
    _validate_uuid("verification scope_id", result.scope_id)
    if not isinstance(result.outcome, IssueVerificationOutcome):
        raise IssueValidationError("verification outcome is invalid.")
    if result.outcome is IssueVerificationOutcome.TECHNICAL_ERROR:
        if result.score_id is not None:
            raise IssueValidationError("Technical verification cannot have a quality score.")
    elif result.score_id is None:
        raise IssueValidationError("Quality verification must have a score reference.")
    if not _is_aware(result.completed_at):
        raise IssueValidationError("verification completed_at must be timezone-aware.")


def validate_access_policy(policy: IssueAccessPolicy) -> None:
    _validate_code("policy.version", policy.version)
    _validate_code("policy.actor_policy_version", policy.actor_policy_version)
    if not policy.allowed_reader_actor_types or not policy.allowed_producer_actor_types:
        raise IssueValidationError("Access policy must allow reader and producer types.")
    if not policy.manual_creator_actor_types:
        raise IssueValidationError("Access policy must allow manual creator types.")


def validate_manual_issue_draft(draft: ManualIssueDraft) -> None:
    _validate_title(draft.title)
    if not isinstance(draft.scope_type, IssueScopeType):
        raise IssueValidationError("scope_type is invalid.")
    _validate_uuid("scope_id", draft.scope_id)
    if not isinstance(draft.priority, IssuePriority):
        raise IssueValidationError("priority is invalid.")
    _validate_uuid("creator_user_id", draft.creator_user_id)
    _validate_code("idempotency_key", draft.idempotency_key)


def issue_source_event_type(trigger_type: IssueTriggerType) -> IssueSourceEventType:
    if trigger_type is IssueTriggerType.TECHNICAL_ERROR:
        return IssueSourceEventType.TECHNICAL
    if trigger_type is IssueTriggerType.MANUAL:
        return IssueSourceEventType.MANUAL
    return IssueSourceEventType.QUALITY


def _validate_uuid(field_name: str, value: str) -> None:
    try:
        UUID(value)
    except (AttributeError, TypeError, ValueError) as exc:
        raise IssueValidationError(f"{field_name} must be a UUID.") from exc


def _validate_code(field_name: str, value: str) -> None:
    if not isinstance(value, str) or not _CODE_PATTERN.fullmatch(value):
        raise IssueValidationError(f"{field_name} is invalid.")
    normalized = value.lower()
    if any(part in normalized for part in _FORBIDDEN_TEXT):
        raise IssueValidationError(f"{field_name} contains forbidden content.")


def _validate_resolution_text(field_name: str, value: str, *, allow_markup: bool) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > 2000:
        raise IssueValidationError(f"{field_name} is invalid.")
    if not allow_markup and ("<" in value or ">" in value):
        raise IssueValidationError(f"{field_name} contains unsafe markup.")
    normalized = value.lower()
    if not allow_markup and any(part in normalized for part in _FORBIDDEN_TEXT):
        raise IssueValidationError(f"{field_name} contains forbidden content.")


def _is_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None


def _validate_title(value: str) -> None:
    stripped = value.strip()
    if not stripped or len(stripped) > 200:
        raise IssueValidationError("title must be 1-200 characters.")
    if any(ord(ch) < 32 and ch not in ("\n",) for ch in stripped):
        raise IssueValidationError("title contains control characters.")
    if "<" in stripped or ">" in stripped:
        raise IssueValidationError("title contains unsafe markup.")


def digest_idempotency_key(key: str) -> str:
    return hashlib.sha256(key.strip().encode("utf-8")).hexdigest()
