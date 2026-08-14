"""Data-minimum security incident and breach suspicion models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class IncidentSource(str, Enum):
    APPLICATION = "APPLICATION"
    WORKER = "WORKER"
    SCHEDULER = "SCHEDULER"
    INTEGRATION = "INTEGRATION"
    IDENTITY = "IDENTITY"
    AUDIT = "AUDIT"


class IncidentSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IncidentScopeType(str, Enum):
    SOURCE = "SOURCE"
    DATASET = "DATASET"
    ENTERPRISE = "ENTERPRISE"


class BreachOrigin(str, Enum):
    DATA_CONTROLLER = "DATA_CONTROLLER"
    DATA_PROCESSOR = "DATA_PROCESSOR"


class PersonalDataCategory(str, Enum):
    PERSONAL_DATA = "PERSONAL_DATA"
    SPECIAL_CATEGORY_PERSONAL_DATA = "SPECIAL_CATEGORY_PERSONAL_DATA"


class BreachAssessmentStatus(str, Enum):
    ASSESSMENT_PENDING = "ASSESSMENT_PENDING"
    NOTIFICATION_DECIDED = "NOTIFICATION_DECIDED"


class BreachNotificationDecision(str, Enum):
    AUTHORITY_NOTIFICATION_REQUIRED = "AUTHORITY_NOTIFICATION_REQUIRED"
    AUTHORITY_NOTIFICATION_NOT_REQUIRED = "AUTHORITY_NOTIFICATION_NOT_REQUIRED"


class IncidentTimelineEventType(str, Enum):
    SECURITY_INCIDENT_RECORDED = "SECURITY_INCIDENT_RECORDED"
    BREACH_SUSPICION_RECORDED = "BREACH_SUSPICION_RECORDED"
    CONTAINMENT_RECORDED = "CONTAINMENT_RECORDED"
    PROCESSOR_NOTICE_EVIDENCE_RECORDED = "PROCESSOR_NOTICE_EVIDENCE_RECORDED"
    NOTIFICATION_DECISION_RECORDED = "NOTIFICATION_DECISION_RECORDED"


class BreachDeadlineStatus(str, Enum):
    ASSESSMENT_PENDING = "ASSESSMENT_PENDING"
    ASSESSMENT_OVERDUE = "ASSESSMENT_OVERDUE"
    DECIDED_ON_TIME = "DECIDED_ON_TIME"
    DECIDED_OVERDUE = "DECIDED_OVERDUE"


@dataclass(frozen=True)
class IncidentResponseAccessPolicy:
    version: str
    actor_policy_version: str
    incident_roles: frozenset[str] = field(
        default_factory=lambda: frozenset({"SECURITY_INCIDENT_RESPONDER"})
    )
    privacy_roles: frozenset[str] = field(
        default_factory=lambda: frozenset({"PRIVACY_INCIDENT_REVIEWER"})
    )


@dataclass(frozen=True)
class SecurityIncidentDraft:
    source_event_reference_id: str
    detected_at: datetime
    source: IncidentSource
    severity: IncidentSeverity
    event_code: str
    scope_type: IncidentScopeType
    scope_id: str | None
    evidence_reference_id: str


@dataclass(frozen=True)
class SecurityIncident:
    incident_id: str
    source_event_reference_id: str
    detected_at: datetime
    source: IncidentSource
    severity: IncidentSeverity
    event_code: str
    scope_type: IncidentScopeType
    scope_id: str | None
    evidence_reference_id: str
    recorded_by: str
    recorded_at: datetime


@dataclass(frozen=True)
class SecurityIncidentScope:
    incident_id: str
    scope_type: IncidentScopeType
    scope_id: str | None


@dataclass(frozen=True)
class BreachSuspicionDraft:
    incident_id: str
    learned_at: datetime
    origin: BreachOrigin
    data_categories: frozenset[PersonalDataCategory]
    affected_scope_code: str
    containment_action_code: str
    evidence_reference_id: str
    processor_notification_evidence_id: str | None = None


@dataclass(frozen=True)
class PersonalDataBreachSuspicion:
    breach_id: str
    incident_id: str
    learned_at: datetime
    evaluation_deadline_at: datetime
    origin: BreachOrigin
    data_categories: frozenset[PersonalDataCategory]
    affected_scope_code: str
    containment_action_code: str
    evidence_reference_id: str
    processor_notification_evidence_id: str | None
    status: BreachAssessmentStatus
    recorded_by: str
    recorded_at: datetime


@dataclass(frozen=True)
class BreachDecisionDraft:
    breach_id: str
    decision: BreachNotificationDecision
    decided_at: datetime
    reason_code: str
    evidence_reference_id: str


@dataclass(frozen=True)
class BreachNotificationDecisionRecord:
    decision_id: str
    breach_id: str
    decision: BreachNotificationDecision
    decided_at: datetime
    reason_code: str
    evidence_reference_id: str
    decided_by: str
    recorded_at: datetime
    external_notification_dispatched: bool = False


@dataclass(frozen=True)
class IncidentTimelineEntry:
    timeline_id: str
    incident_id: str
    breach_id: str | None
    event_type: IncidentTimelineEventType
    event_at: datetime
    actor_id: str
    reason_code: str
    evidence_reference_id: str


@dataclass(frozen=True)
class BreachTimelineQuery:
    breach_id: str
    reason_code: str


@dataclass(frozen=True)
class BreachTimelineEventView:
    event_type: IncidentTimelineEventType
    event_at: datetime
    reason_code: str


@dataclass(frozen=True)
class BreachTimelineView:
    breach_id: str
    learned_at: datetime
    evaluation_deadline_at: datetime
    assessment_status: BreachAssessmentStatus
    deadline_status: BreachDeadlineStatus
    origin: BreachOrigin
    data_category_count: int
    affected_scope_code: str
    containment_action_code: str
    processor_notification_evidence_present: bool
    decision: BreachNotificationDecision | None
    decided_at: datetime | None
    decision_reason_code: str | None
    external_notification_dispatched: bool
    timeline: tuple[BreachTimelineEventView, ...]
    created_at: datetime
    policy_version: str
