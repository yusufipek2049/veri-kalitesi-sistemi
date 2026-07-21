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


class DisposalJobStatus(str, Enum):
    PREPARED = "PREPARED"
    SUCCEEDED = "SUCCEEDED"
    FAILED_TECHNICAL = "FAILED_TECHNICAL"


class ArchiveRecordType(str, Enum):
    AUDIT_LOG = "AUDIT_LOG"
    QUALITY_SCORE = "QUALITY_SCORE"


class ArchiveRecallStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ArchiveRecallDecisionType(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


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
class DisposalJobAccessPolicy:
    version: str
    actor_policy_version: str
    preparation_roles: frozenset[str]
    result_roles: frozenset[str]
    preparation_reason_codes: frozenset[str]
    technical_error_codes: frozenset[str]
    allowed_preparer_types: frozenset[ActorType] = field(
        default_factory=lambda: frozenset({ActorType.USER})
    )
    allowed_result_actor_types: frozenset[ActorType] = field(
        default_factory=lambda: frozenset({ActorType.SERVICE})
    )


@dataclass(frozen=True)
class ArchiveRecallAccessPolicy:
    version: str
    actor_policy_version: str
    request_roles: frozenset[str]
    decision_roles: frozenset[str]
    purpose_codes: frozenset[str]
    approval_reason_codes: frozenset[str]
    rejection_reason_codes: frozenset[str]
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


@dataclass(frozen=True)
class DisposalJobResult:
    result_id: str
    job_id: str
    status: DisposalJobStatus
    affected_record_count: int
    failed_record_count: int
    evidence_reference: str
    technical_error_code: str | None
    result_digest: str
    recorded_by_actor_id: str
    recorded_by_role: str
    recorded_at: datetime


@dataclass(frozen=True)
class DisposalJob:
    job_id: str
    idempotency_key_digest: str
    payload_digest: str
    record_reference_digest: str
    record_class: RetentionRecordClass
    policy_code: str
    policy_version: str
    disposal_method: DisposalMethod
    scope_type: RetentionScopeType
    scope_digest: str | None
    approval_reference: str
    reason_code: str
    prepared_by_actor_id: str
    prepared_by_role: str
    prepared_at: datetime
    result: DisposalJobResult | None = None

    @property
    def status(self) -> DisposalJobStatus:
        if self.result is None:
            return DisposalJobStatus.PREPARED
        return self.result.status


@dataclass(frozen=True)
class ArchiveRecallDecision:
    decision_id: str
    request_id: str
    decision: ArchiveRecallDecisionType
    reason_code: str
    decided_by_actor_id: str
    decided_by_role: str
    decided_at: datetime


@dataclass(frozen=True)
class ArchiveRecallRequest:
    request_id: str
    idempotency_key_digest: str
    payload_digest: str
    archive_reference_digest: str
    record_type: ArchiveRecordType
    scope_type: RetentionScopeType
    scope_digest: str | None
    purpose_code: str
    requested_by_actor_id: str
    requested_by_role: str
    requested_at: datetime
    decision: ArchiveRecallDecision | None = None

    @property
    def status(self) -> ArchiveRecallStatus:
        if self.decision is None:
            return ArchiveRecallStatus.PENDING
        return ArchiveRecallStatus(self.decision.decision.value)
