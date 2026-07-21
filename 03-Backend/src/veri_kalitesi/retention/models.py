"""Data-minimum retention and legal hold domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from veri_kalitesi.identity import ActorType


class RetentionRecordClass(str, Enum):
    BANKING_RECORD = "BANKING_RECORD"
    REGULATORY_LOG = "REGULATORY_LOG"
    ERASURE_EVIDENCE = "ERASURE_EVIDENCE"
    OPERATIONAL_RECORD = "OPERATIONAL_RECORD"
    TRANSIENT_RECORD = "TRANSIENT_RECORD"
    EXPORT_ARTIFACT = "EXPORT_ARTIFACT"


class DisposalMethod(str, Enum):
    CONTROLLED_DESTRUCTION = "CONTROLLED_DESTRUCTION"
    SECURE_DELETION = "SECURE_DELETION"
    CRYPTOGRAPHIC_ERASURE = "CRYPTOGRAPHIC_ERASURE"


class RetentionReviewStatus(str, Enum):
    COMPLIANCE_REVIEW_REQUIRED = "ComplianceReviewRequired"
    APPROVED_BY_BANK = "ApprovedByBank"


class RetentionDisposition(str, Enum):
    RETAIN = "RETAIN"
    LEGAL_HOLD = "LEGAL_HOLD"
    COMPLIANCE_REVIEW_REQUIRED = "COMPLIANCE_REVIEW_REQUIRED"
    ELIGIBLE_FOR_DISPOSAL = "ELIGIBLE_FOR_DISPOSAL"


class RetentionScopeType(str, Enum):
    SOURCE = "SOURCE"
    DATASET = "DATASET"
    ENTERPRISE = "ENTERPRISE"


class LegalHoldEventType(str, Enum):
    PLACED = "PLACED"
    RELEASED = "RELEASED"


@dataclass(frozen=True)
class CalendarDuration:
    years: int = 0
    days: int = 0


@dataclass(frozen=True)
class RetentionPolicy:
    code: str
    record_class: RetentionRecordClass
    duration: CalendarDuration
    disposal_method: DisposalMethod
    version: str
    review_status: RetentionReviewStatus
    approval_reference: str | None = None


@dataclass(frozen=True)
class RetentionPolicyCatalog:
    version: str
    policies: tuple[RetentionPolicy, ...]
    maximum_disposal_interval_days: int


@dataclass(frozen=True)
class RetentionRecordReference:
    record_reference_id: str
    record_class: RetentionRecordClass
    retention_trigger_at: datetime


@dataclass(frozen=True)
class LegalHoldTarget:
    record_reference_id: str
    record_class: RetentionRecordClass
    scope_type: RetentionScopeType
    scope_id: str | None


@dataclass(frozen=True)
class LegalHoldAccessPolicy:
    version: str
    actor_policy_version: str
    placement_roles: frozenset[str]
    release_roles: frozenset[str]
    placement_reason_codes: frozenset[str]
    release_reason_codes: frozenset[str]
    allowed_actor_types: frozenset[ActorType] = field(
        default_factory=lambda: frozenset({ActorType.USER})
    )


@dataclass(frozen=True)
class LegalHold:
    hold_reference_id: str
    record_reference_id: str
    record_class: RetentionRecordClass
    policy_version: str
    decision_owner_role: str
    effective_at: datetime
    released_at: datetime | None = None
    placed_by_actor_id: str | None = None
    released_by_actor_id: str | None = None
    release_owner_role: str | None = None
    scope_type: RetentionScopeType | None = None
    scope_id: str | None = None


@dataclass(frozen=True)
class LegalHoldEvent:
    event_id: str
    hold_reference_id: str
    event_type: LegalHoldEventType
    record_reference_id: str
    record_class: RetentionRecordClass
    policy_version: str
    scope_type: RetentionScopeType
    scope_id: str | None
    actor_id: str
    actor_role: str
    reason_code: str
    created_at: datetime


@dataclass(frozen=True)
class RetentionEvaluation:
    record_reference_id: str
    record_class: RetentionRecordClass
    policy_code: str
    policy_version: str
    retention_until: datetime
    disposition: RetentionDisposition
    legal_hold_count: int = 0
