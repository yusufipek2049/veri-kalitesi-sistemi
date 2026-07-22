"""Tamamen yapay ve deterministik Golden ilişkisel veri üreticisi."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import hashlib

from veri_kalitesi.synthetic_data.canonical import build_golden_canonical_payload
from veri_kalitesi.synthetic_data.errors import (
    SyntheticDataTechnicalError,
    SyntheticDataValidationError,
)
from veri_kalitesi.synthetic_data.models import (
    GoldenObservationRecord,
    GoldenRelationalDataset,
    GoldenStructuralValidation,
    GoldenSubjectRecord,
    SyntheticGenerationRun,
    SyntheticProfile,
    SyntheticRunStatus,
    SyntheticScenario,
)
from veri_kalitesi.synthetic_data.repository import SQLiteSyntheticDataRepository


GOLDEN_GENERATOR_VERSION = "GOLDEN_RELATIONAL_GENERATOR_V1"
GOLDEN_SCHEMA_VERSION = "GOLDEN_RELATIONAL_SCHEMA_V1"
GOLDEN_CONFIGURATION_VERSION = "GOLDEN_RELATIONAL_CONFIG_V1"
FULLY_ARTIFICIAL_PRIVACY_PROFILE = "FULLY_ARTIFICIAL_V1"
_SYNTHETIC_SOURCE_CODE = "SYNTHETIC_SOURCE"
_SYNTHETIC_CURRENCY_CODE = "SYN"
_SEGMENT_CODES = ("SEGMENT_A", "SEGMENT_B", "SEGMENT_C")
_SEGMENT_STATUS_TRANSITIONS = (
    ("NEW", "ACTIVE"),
    ("ACTIVE", "ACTIVE"),
    ("ACTIVE", "CLOSED"),
)
_STATUS_BY_SEGMENT = dict(zip(_SEGMENT_CODES, _SEGMENT_STATUS_TRANSITIONS, strict=True))
_BASE_DATE = date(2000, 1, 1)
_BASE_TIME = datetime(2000, 1, 1, tzinfo=timezone.utc)


class GoldenRelationalGenerator:
    """Kayıtlı run metadata'sından dış bağımlılıksız Golden çıktı üretir."""

    def __init__(self, repository: SQLiteSyntheticDataRepository) -> None:
        self.repository = repository

    def generate(self, generation_run_id: str) -> GoldenRelationalDataset:
        run = self.repository.get_run(generation_run_id)
        scenario = self.repository.get_scenario(run.scenario_id, run.scenario_version)
        _validate_generation_contract(run, scenario)

        subjects: list[GoldenSubjectRecord] = []
        observations: list[GoldenObservationRecord] = []
        for index in range(run.requested_record_count):
            subject_id = _synthetic_id(run.random_seed, "subject", index)
            segment_index = _entropy(run.random_seed, "segment", index) % len(_SEGMENT_CODES)
            segment_code = _SEGMENT_CODES[segment_index]
            previous_status, current_status = _SEGMENT_STATUS_TRANSITIONS[segment_index]
            effective_date = _BASE_DATE + timedelta(
                days=_entropy(run.random_seed, "effective-date", index) % 3650
            )
            subjects.append(
                GoldenSubjectRecord(
                    subject_id=subject_id,
                    segment_code=segment_code,
                    previous_status=previous_status,
                    current_status=current_status,
                    source_system_code=_SYNTHETIC_SOURCE_CODE,
                    effective_date=effective_date,
                )
            )

            event_time = _BASE_TIME + timedelta(
                days=_entropy(run.random_seed, "event-day", index) % 3650,
                seconds=_entropy(run.random_seed, "event-second", index) % 86400,
            )
            observations.append(
                GoldenObservationRecord(
                    observation_id=_synthetic_id(run.random_seed, "observation", index),
                    subject_id=subject_id,
                    amount=_amount(run.random_seed, index),
                    currency_code=_SYNTHETIC_CURRENCY_CODE,
                    event_time=event_time,
                    source_created_at=event_time - timedelta(minutes=5),
                    source_updated_at=event_time - timedelta(minutes=1),
                )
            )

        subject_tuple = tuple(subjects)
        observation_tuple = tuple(observations)
        validation = _validate_output(run, subject_tuple, observation_tuple)
        payload = build_golden_canonical_payload(
            run,
            scenario,
            subject_tuple,
            observation_tuple,
        )
        digest = hashlib.sha256(payload).hexdigest()
        return GoldenRelationalDataset(
            generation_run_id=run.generation_run_id,
            dataset_id=run.dataset_id,
            scenario_id=run.scenario_id,
            scenario_version=run.scenario_version,
            generator_version=run.generator_version,
            configuration_version=run.configuration_version,
            schema_version=run.schema_version,
            policy_version=run.policy_version,
            random_seed=run.random_seed,
            requested_record_count=run.requested_record_count,
            synthetic_origin=True,
            subjects=subject_tuple,
            observations=observation_tuple,
            validation=validation,
            canonical_payload=payload,
            canonical_sha256=digest,
            output_reference=f"sha256:{digest}",
        )


def _validate_generation_contract(
    run: SyntheticGenerationRun,
    scenario: SyntheticScenario,
) -> None:
    if run.status is not SyntheticRunStatus.REQUESTED:
        raise SyntheticDataValidationError("Synthetic run is not ready for generation.")
    if run.output_reference is not None or run.validation_reference is not None:
        raise SyntheticDataValidationError("Synthetic run already contains output metadata.")
    if run.generator_version != GOLDEN_GENERATOR_VERSION:
        raise SyntheticDataValidationError("Golden generator version is not supported.")
    if run.schema_version != GOLDEN_SCHEMA_VERSION:
        raise SyntheticDataValidationError("Golden schema version is not supported.")
    if run.configuration_version != GOLDEN_CONFIGURATION_VERSION:
        raise SyntheticDataValidationError("Golden configuration version is not supported.")
    if (
        scenario.dataset_id != run.dataset_id
        or scenario.scenario_id != run.scenario_id
        or scenario.scenario_version != run.scenario_version
        or scenario.schema_version != run.schema_version
        or scenario.configuration_version != run.configuration_version
    ):
        raise SyntheticDataValidationError("Synthetic scenario and run lineage do not match.")
    if scenario.synthetic_profile is not SyntheticProfile.GOLDEN:
        raise SyntheticDataValidationError("Only the Golden synthetic profile is supported.")
    if scenario.privacy_profile != FULLY_ARTIFICIAL_PRIVACY_PROFILE:
        raise SyntheticDataValidationError("Golden generation must be fully artificial.")
    if scenario.volume_profile != "FUNCTIONAL_V1":
        raise SyntheticDataValidationError("Golden generation requires the functional profile.")
    if scenario.distribution_profile != "ARTIFICIAL_DISTRIBUTION_V1":
        raise SyntheticDataValidationError(
            "Golden generation requires the artificial distribution profile."
        )
    if scenario.missingness_profile != "NO_MISSINGNESS_V1":
        raise SyntheticDataValidationError("Golden generation cannot inject missingness.")
    if scenario.defect_injection_profile != "NO_DEFECTS_V1":
        raise SyntheticDataValidationError("Golden generation cannot inject defects.")


def _validate_output(
    run: SyntheticGenerationRun,
    subjects: tuple[GoldenSubjectRecord, ...],
    observations: tuple[GoldenObservationRecord, ...],
) -> GoldenStructuralValidation:
    subject_ids = {record.subject_id for record in subjects}
    observation_ids = {record.observation_id for record in observations}
    primary_keys_unique = len(subject_ids) == len(subjects) and len(observation_ids) == len(
        observations
    )
    foreign_keys_valid = all(record.subject_id in subject_ids for record in observations)
    status_transitions_valid = all(
        (record.previous_status, record.current_status)
        == _STATUS_BY_SEGMENT.get(record.segment_code)
        for record in subjects
    )
    reference_codes_valid = all(
        record.segment_code in _SEGMENT_CODES
        and record.source_system_code == _SYNTHETIC_SOURCE_CODE
        for record in subjects
    ) and all(
        record.currency_code == _SYNTHETIC_CURRENCY_CODE and record.amount >= Decimal("0.00")
        for record in observations
    )
    temporal_order_valid = all(
        record.source_created_at <= record.source_updated_at <= record.event_time
        for record in observations
    )
    counts_valid = (
        len(subjects) == run.requested_record_count
        and len(observations) == run.requested_record_count
    )
    passed = all(
        (
            counts_valid,
            primary_keys_unique,
            foreign_keys_valid,
            status_transitions_valid,
            reference_codes_valid,
            temporal_order_valid,
        )
    )
    if not passed:
        raise SyntheticDataTechnicalError(
            "Golden generator produced output that violates its structural contract."
        )
    return GoldenStructuralValidation(
        subject_count=len(subjects),
        observation_count=len(observations),
        primary_keys_unique=primary_keys_unique,
        foreign_keys_valid=foreign_keys_valid,
        status_transitions_valid=status_transitions_valid,
        reference_codes_valid=reference_codes_valid,
        temporal_order_valid=temporal_order_valid,
        passed=True,
    )


def _entropy(seed: int, label: str, index: int) -> int:
    value = f"{seed}:{label}:{index}".encode()
    return int.from_bytes(hashlib.sha256(value).digest()[:8], "big")


def _synthetic_id(seed: int, label: str, index: int) -> str:
    digest = hashlib.sha256(f"{seed}:{label}:{index}".encode()).hexdigest()[:20]
    return f"SYN-{digest.upper()}"


def _amount(seed: int, index: int) -> Decimal:
    cents = _entropy(seed, "amount", index) % 10_000_000
    return (Decimal(cents) / Decimal(100)).quantize(Decimal("0.01"))
