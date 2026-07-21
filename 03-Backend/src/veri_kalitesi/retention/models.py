"""Data-minimum retention and legal hold domain models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


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
class LegalHold:
    hold_reference_id: str
    record_reference_id: str
    record_class: RetentionRecordClass
    policy_version: str
    decision_owner_role: str
    effective_at: datetime
    released_at: datetime | None = None


@dataclass(frozen=True)
class RetentionEvaluation:
    record_reference_id: str
    record_class: RetentionRecordClass
    policy_code: str
    policy_version: str
    retention_until: datetime
    disposition: RetentionDisposition
    legal_hold_count: int = 0
