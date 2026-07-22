"""Golden çıktı için runtime'dan bağımsız yapısal ground truth oracle'ı."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Callable

from veri_kalitesi.audit import AuditEventInput, AuditResult, SQLiteTransactionalAudit
from veri_kalitesi.identity import ActorContext
from veri_kalitesi.synthetic_data.authorization import (
    authorize_synthetic_actor,
    validate_synthetic_access_policy,
)
from veri_kalitesi.synthetic_data.errors import SyntheticDataValidationError
from veri_kalitesi.synthetic_data.models import (
    GoldenRelationalDataset,
    SyntheticGroundTruth,
    SyntheticProfile,
    SyntheticRunAccessPolicy,
    SyntheticValidationResult,
    SyntheticValidationStatus,
    utc_now,
)
from veri_kalitesi.synthetic_data.repository import SQLiteSyntheticDataRepository


GOLDEN_GROUND_TRUTH_VERSION = "GOLDEN_STRUCTURAL_ORACLE_V1"
GOLDEN_VALIDATION_CLASS = "STRUCTURAL_GOLDEN_V1"
_SUPPORTED_GENERATOR_VERSION = "GOLDEN_RELATIONAL_GENERATOR_V1"
_SUPPORTED_SCHEMA_VERSION = "GOLDEN_RELATIONAL_SCHEMA_V1"
_SUPPORTED_CONFIGURATION_VERSION = "GOLDEN_RELATIONAL_CONFIG_V1"
_EXPECTED_SOURCE_SYSTEM = "SYNTHETIC_SOURCE"
_EXPECTED_CURRENCY = "SYN"
_EXPECTED_STATUS_BY_SEGMENT = {
    "SEGMENT_A": ("NEW", "ACTIVE"),
    "SEGMENT_B": ("ACTIVE", "ACTIVE"),
    "SEGMENT_C": ("ACTIVE", "CLOSED"),
}


class GoldenStructuralOracle:
    """Golden sözleşmesini üretici doğrulamasına güvenmeden değerlendirir."""

    def __init__(
        self,
        repository: SQLiteSyntheticDataRepository,
        *,
        transactional_audit: SQLiteTransactionalAudit,
        access_policy: SyntheticRunAccessPolicy,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self.repository = repository
        self.transactional_audit = transactional_audit
        self.access_policy = access_policy
        self.clock = clock
        validate_synthetic_access_policy(access_policy)

    def validate_and_record(
        self,
        *,
        actor_context: ActorContext | None,
        output: GoldenRelationalDataset,
    ) -> tuple[SyntheticGroundTruth, SyntheticValidationResult]:
        now = self.clock()
        _validate_aware_time(now)
        context = authorize_synthetic_actor(
            actor_context,
            dataset_id=output.dataset_id,
            at=now,
            access_policy=self.access_policy,
            operation="validation",
        )
        run = self.repository.get_run(output.generation_run_id)
        context = authorize_synthetic_actor(
            context,
            dataset_id=run.dataset_id,
            at=now,
            access_policy=self.access_policy,
            operation="validation",
        )
        scenario = self.repository.get_scenario(run.scenario_id, run.scenario_version)
        _validate_oracle_contract(run, scenario)

        ground_truth = SyntheticGroundTruth(
            generation_run_id=run.generation_run_id,
            dataset_id=run.dataset_id,
            scenario_id=run.scenario_id,
            scenario_version=run.scenario_version,
            generator_version=run.generator_version,
            random_seed=run.random_seed,
            source_system=_EXPECTED_SOURCE_SYSTEM,
            expected_subject_count=run.requested_record_count,
            expected_observation_count=run.requested_record_count,
            expected_primary_keys_unique=True,
            expected_foreign_keys_valid=True,
            expected_status_transitions_valid=True,
            expected_reference_codes_valid=True,
            expected_temporal_order_valid=True,
            expected_rule_result="PASS",
            expected_severity="NONE",
            expected_dataset_score=None,
            expected_notification=False,
            expected_escalation=False,
            ground_truth_version=GOLDEN_GROUND_TRUTH_VERSION,
            audit_reference="pending",
            created_at=now,
        )
        validation = _compare(output, ground_truth, created_at=now)
        event = AuditEventInput(
            actor_id=context.actor_id,
            actor_type=context.actor_type.value,
            correlation_id=context.correlation_id,
            action="SYNTHETIC_GOLDEN_VALIDATION_RECORDED",
            object_type="SyntheticValidationResult",
            object_id=validation.validation_result_id,
            result=AuditResult.SUCCESS,
            reason_code="SYNTHETIC_GOLDEN_VALIDATION_RECORDED",
            old_values={},
            new_values={
                "dataset_id": ground_truth.dataset_id,
                "generation_run_id": ground_truth.generation_run_id,
                "ground_truth_version": ground_truth.ground_truth_version,
                "validation_class": validation.validation_class,
                "validation_status": validation.status.value,
                "reason_codes": list(validation.reason_codes),
                "expected_subject_count": ground_truth.expected_subject_count,
                "expected_observation_count": ground_truth.expected_observation_count,
                "actual_subject_count": validation.actual_subject_count,
                "actual_observation_count": validation.actual_observation_count,
                "score_tolerance_applied": False,
                "synthetic_origin": True,
                "access_policy_version": self.access_policy.version,
            },
            occurred_at=now,
            session_id=context.session_id,
        )
        prepared = self.transactional_audit.prepare(event)
        stored = self.repository.add_ground_truth_and_validation_with_audit(
            replace(ground_truth, audit_reference=prepared.event_id),
            replace(validation, audit_reference=prepared.event_id),
            audit_event=prepared,
            audit_outbox=self.transactional_audit,
        )
        self.transactional_audit.publish_pending()
        return stored


def _validate_oracle_contract(run: object, scenario: object) -> None:
    required_run = (
        getattr(run, "generator_version", None) == _SUPPORTED_GENERATOR_VERSION,
        getattr(run, "schema_version", None) == _SUPPORTED_SCHEMA_VERSION,
        getattr(run, "configuration_version", None) == _SUPPORTED_CONFIGURATION_VERSION,
    )
    required_scenario = (
        getattr(scenario, "synthetic_profile", None) is SyntheticProfile.GOLDEN,
        getattr(scenario, "defect_injection_profile", None) == "NO_DEFECTS_V1",
        getattr(scenario, "missingness_profile", None) == "NO_MISSINGNESS_V1",
        getattr(scenario, "privacy_profile", None) == "FULLY_ARTIFICIAL_V1",
    )
    if not all((*required_run, *required_scenario)):
        raise SyntheticDataValidationError(
            "Golden structural oracle does not support the run or scenario contract."
        )


def _compare(
    output: GoldenRelationalDataset,
    expected: SyntheticGroundTruth,
    *,
    created_at: datetime,
) -> SyntheticValidationResult:
    subject_ids = {record.subject_id for record in output.subjects}
    observation_ids = {record.observation_id for record in output.observations}
    primary_keys_unique = len(subject_ids) == len(output.subjects) and len(observation_ids) == len(
        output.observations
    )
    foreign_keys_valid = all(record.subject_id in subject_ids for record in output.observations)
    status_transitions_valid = all(
        (record.previous_status, record.current_status)
        == _EXPECTED_STATUS_BY_SEGMENT.get(record.segment_code)
        for record in output.subjects
    )
    reference_codes_valid = all(
        record.source_system_code == _EXPECTED_SOURCE_SYSTEM
        and record.segment_code in _EXPECTED_STATUS_BY_SEGMENT
        for record in output.subjects
    ) and all(_valid_observation_reference(record) for record in output.observations)
    temporal_order_valid = all(_valid_temporal_order(record) for record in output.observations)

    checks = (
        ("LINEAGE_MISMATCH", _lineage_matches(output, expected)),
        ("SUBJECT_COUNT_MISMATCH", len(output.subjects) == expected.expected_subject_count),
        (
            "OBSERVATION_COUNT_MISMATCH",
            len(output.observations) == expected.expected_observation_count,
        ),
        ("PRIMARY_KEY_VIOLATION", primary_keys_unique),
        ("FOREIGN_KEY_VIOLATION", foreign_keys_valid),
        ("STATUS_TRANSITION_VIOLATION", status_transitions_valid),
        ("REFERENCE_CODE_VIOLATION", reference_codes_valid),
        ("TEMPORAL_ORDER_VIOLATION", temporal_order_valid),
    )
    reason_codes = tuple(code for code, passed in checks if not passed)
    status = (
        SyntheticValidationStatus.PASS if not reason_codes else SyntheticValidationStatus.BLOCKED
    )
    return SyntheticValidationResult(
        generation_run_id=expected.generation_run_id,
        synthetic_record_id=expected.synthetic_record_id,
        ground_truth_version=expected.ground_truth_version,
        validation_class=GOLDEN_VALIDATION_CLASS,
        status=status,
        reason_codes=reason_codes,
        actual_subject_count=len(output.subjects),
        actual_observation_count=len(output.observations),
        actual_primary_keys_unique=primary_keys_unique,
        actual_foreign_keys_valid=foreign_keys_valid,
        actual_status_transitions_valid=status_transitions_valid,
        actual_reference_codes_valid=reference_codes_valid,
        actual_temporal_order_valid=temporal_order_valid,
        actual_output_reference=output.output_reference,
        audit_reference="pending",
        created_at=created_at,
    )


def _lineage_matches(
    output: GoldenRelationalDataset,
    expected: SyntheticGroundTruth,
) -> bool:
    return (
        output.synthetic_origin
        and output.generation_run_id == expected.generation_run_id
        and output.dataset_id == expected.dataset_id
        and output.scenario_id == expected.scenario_id
        and output.scenario_version == expected.scenario_version
        and output.generator_version == expected.generator_version
        and output.random_seed == expected.random_seed
    )


def _valid_observation_reference(record: object) -> bool:
    amount = getattr(record, "amount", None)
    try:
        amount_valid = (
            isinstance(amount, Decimal) and amount.is_finite() and amount >= Decimal("0.00")
        )
    except InvalidOperation:
        amount_valid = False
    return getattr(record, "currency_code", None) == _EXPECTED_CURRENCY and amount_valid


def _valid_temporal_order(record: object) -> bool:
    try:
        return bool(
            getattr(record, "source_created_at")
            <= getattr(record, "source_updated_at")
            <= getattr(record, "event_time")
        )
    except (AttributeError, TypeError):
        return False


def _validate_aware_time(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise SyntheticDataValidationError("Synthetic validation time must be timezone-aware.")
