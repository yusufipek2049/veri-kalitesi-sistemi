"""Sentetik dataset politika, senaryo ve üretim çalışması modelleri."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from uuid import uuid4

from veri_kalitesi.identity import ActorType


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SyntheticPolicyStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"


class SyntheticProfile(str, Enum):
    GOLDEN = "GOLDEN"
    NORMAL_OPERATION = "NORMAL_OPERATION"
    DEGRADED = "DEGRADED"
    STRESS = "STRESS"
    DRIFT = "DRIFT"
    SCHEMA_CHANGE = "SCHEMA_CHANGE"
    RARE_EVENT = "RARE_EVENT"
    PRIVACY_TEST = "PRIVACY_TEST"
    INCIDENT_MANAGEMENT = "INCIDENT_MANAGEMENT"


class SyntheticRunStatus(str, Enum):
    REQUESTED = "REQUESTED"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    TECHNICAL_ERROR = "TECHNICAL_ERROR"


class SyntheticValidationStatus(str, Enum):
    PASS = "PASS"
    BLOCKED = "BLOCKED"
    TECHNICAL_ERROR = "TECHNICAL_ERROR"


@dataclass(frozen=True)
class SyntheticRunAccessPolicy:
    version: str
    actor_policy_version: str
    requester_roles: frozenset[str]
    allowed_actor_types: frozenset[ActorType] = field(
        default_factory=lambda: frozenset({ActorType.USER})
    )


@dataclass(frozen=True)
class SyntheticDatasetPolicy:
    dataset_id: str
    synthetic_generation_allowed: bool
    synthetic_profile: SyntheticProfile
    volume_profile: str
    distribution_profile: str
    missingness_profile: str
    defect_injection_profile: str
    privacy_profile: str
    retention_policy_id: str
    ground_truth_enabled: bool
    seed_strategy: str
    expected_score_tolerance: Decimal | None
    criticality_profile_id: str
    notification_test_enabled: bool
    schema_version: str
    policy_version: str
    effective_from: datetime
    effective_to: datetime | None
    approved_by: str | None
    approval_status: SyntheticPolicyStatus
    audit_reference: str | None
    policy_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class SyntheticScenario:
    scenario_id: str
    dataset_id: str
    scenario_version: str
    schema_version: str
    configuration_version: str
    synthetic_profile: SyntheticProfile
    volume_profile: str
    distribution_profile: str
    missingness_profile: str
    defect_injection_profile: str
    privacy_profile: str
    scenario_record_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class SyntheticGenerationRun:
    dataset_id: str
    scenario_id: str
    scenario_version: str
    generator_version: str
    configuration_version: str
    schema_version: str
    policy_version: str
    random_seed: int
    requested_record_count: int
    requested_by: str
    audit_reference: str
    status: SyntheticRunStatus = SyntheticRunStatus.REQUESTED
    output_reference: str | None = None
    validation_reference: str | None = None
    generation_run_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class GoldenSubjectRecord:
    subject_id: str
    segment_code: str
    previous_status: str
    current_status: str
    source_system_code: str
    effective_date: date


@dataclass(frozen=True)
class GoldenObservationRecord:
    observation_id: str
    subject_id: str
    amount: Decimal
    currency_code: str
    event_time: datetime
    source_created_at: datetime
    source_updated_at: datetime


@dataclass(frozen=True)
class GoldenStructuralValidation:
    subject_count: int
    observation_count: int
    primary_keys_unique: bool
    foreign_keys_valid: bool
    status_transitions_valid: bool
    reference_codes_valid: bool
    temporal_order_valid: bool
    passed: bool


@dataclass(frozen=True)
class GoldenRelationalDataset:
    generation_run_id: str
    dataset_id: str
    scenario_id: str
    scenario_version: str
    generator_version: str
    configuration_version: str
    schema_version: str
    policy_version: str
    random_seed: int
    requested_record_count: int
    synthetic_origin: bool
    subjects: tuple[GoldenSubjectRecord, ...]
    observations: tuple[GoldenObservationRecord, ...]
    validation: GoldenStructuralValidation
    canonical_payload: bytes
    canonical_sha256: str
    output_reference: str


@dataclass(frozen=True)
class SyntheticGroundTruth:
    generation_run_id: str
    dataset_id: str
    scenario_id: str
    scenario_version: str
    generator_version: str
    random_seed: int
    source_system: str
    expected_subject_count: int
    expected_observation_count: int
    expected_primary_keys_unique: bool
    expected_foreign_keys_valid: bool
    expected_status_transitions_valid: bool
    expected_reference_codes_valid: bool
    expected_temporal_order_valid: bool
    expected_rule_result: str
    expected_severity: str
    expected_dataset_score: Decimal | None
    expected_notification: bool
    expected_escalation: bool
    ground_truth_version: str
    audit_reference: str
    synthetic_record_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class SyntheticValidationResult:
    generation_run_id: str
    synthetic_record_id: str
    ground_truth_version: str
    validation_class: str
    status: SyntheticValidationStatus
    reason_codes: tuple[str, ...]
    actual_subject_count: int
    actual_observation_count: int
    actual_primary_keys_unique: bool
    actual_foreign_keys_valid: bool
    actual_status_transitions_valid: bool
    actual_reference_codes_valid: bool
    actual_temporal_order_valid: bool
    actual_output_reference: str
    audit_reference: str
    validation_result_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class SyntheticRunCompletion:
    generation_run_id: str
    status: SyntheticRunStatus
    output_reference: str
    canonical_sha256: str
    payload_byte_count: int
    subject_count: int
    observation_count: int
    validation_result_id: str
    validation_status: SyntheticValidationStatus
    retention_policy_id: str
    audit_reference: str
    completion_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=utc_now)
