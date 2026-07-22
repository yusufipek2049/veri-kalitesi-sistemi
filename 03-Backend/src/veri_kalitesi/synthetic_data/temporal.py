"""Deterministik çok dönemli sentetik zaman semantiği üreticisi."""

from __future__ import annotations

from datetime import timedelta
import hashlib

from veri_kalitesi.synthetic_data.canonical import build_temporal_canonical_payload
from veri_kalitesi.synthetic_data.errors import (
    SyntheticDataTechnicalError,
    SyntheticDataValidationError,
)
from veri_kalitesi.synthetic_data.generator import FULLY_ARTIFICIAL_PRIVACY_PROFILE
from veri_kalitesi.synthetic_data.models import (
    SyntheticGenerationRun,
    SyntheticProfile,
    SyntheticRunStatus,
    SyntheticScenario,
    SyntheticTemporalProfile,
    TemporalObservationRecord,
    TemporalSyntheticDataset,
    TemporalValidation,
)
from veri_kalitesi.synthetic_data.repository import SQLiteSyntheticDataRepository


TEMPORAL_GENERATOR_VERSION = "TEMPORAL_MULTI_PERIOD_GENERATOR_V1"
TEMPORAL_SCHEMA_VERSION = "TEMPORAL_OBSERVATION_SCHEMA_V1"
TEMPORAL_CONFIGURATION_VERSION = "TEMPORAL_MULTI_PERIOD_CONFIG_V1"


class DeterministicTemporalGenerator:
    """Kayıtlı run ve temporal profilden dış bağımlılıksız zaman verisi üretir."""

    def __init__(self, repository: SQLiteSyntheticDataRepository) -> None:
        self.repository = repository

    def generate(self, generation_run_id: str) -> TemporalSyntheticDataset:
        run = self.repository.get_run(generation_run_id)
        scenario = self.repository.get_scenario(run.scenario_id, run.scenario_version)
        profile = self.repository.get_temporal_profile(scenario.distribution_profile)
        _validate_generation_contract(run, scenario, profile)

        observations = tuple(
            _build_observation(run, profile, index) for index in range(run.requested_record_count)
        )
        validation = TemporalSemanticValidator().validate(
            expected_record_count=run.requested_record_count,
            profile=profile,
            observations=observations,
        )
        if not validation.passed:
            raise SyntheticDataTechnicalError(
                "Temporal generator produced output that violates its contract."
            )
        payload = build_temporal_canonical_payload(run, scenario, profile, observations)
        digest = hashlib.sha256(payload).hexdigest()
        return TemporalSyntheticDataset(
            generation_run_id=run.generation_run_id,
            dataset_id=run.dataset_id,
            scenario_id=run.scenario_id,
            scenario_version=run.scenario_version,
            generator_version=run.generator_version,
            configuration_version=run.configuration_version,
            schema_version=run.schema_version,
            policy_version=run.policy_version,
            temporal_profile_version=profile.profile_version,
            random_seed=run.random_seed,
            requested_record_count=run.requested_record_count,
            synthetic_origin=True,
            observations=observations,
            validation=validation,
            canonical_payload=payload,
            canonical_sha256=digest,
            output_reference=f"sha256:{digest}",
        )


class TemporalSemanticValidator:
    """Üretim algoritmasından bağımsız zaman alanı ve dönem doğrulayıcısı."""

    def validate(
        self,
        *,
        expected_record_count: int,
        profile: SyntheticTemporalProfile,
        observations: tuple[TemporalObservationRecord, ...],
    ) -> TemporalValidation:
        represented_periods = {record.period_index for record in observations}
        all_periods_present = represented_periods == set(range(profile.period_count))
        period_assignment_valid = all(
            profile.base_time
            + timedelta(seconds=record.period_index * profile.period_duration_seconds)
            <= record.event_time
            < profile.base_time
            + timedelta(seconds=(record.period_index + 1) * profile.period_duration_seconds)
            for record in observations
        )
        semantic_order_valid = all(
            record.event_time
            <= record.source_created_at
            <= record.source_updated_at
            <= record.ingestion_time
            <= record.processing_time
            <= record.quality_check_time
            for record in observations
        )
        utc_valid = all(
            value.utcoffset() == timedelta(0)
            for record in observations
            for value in (
                record.event_time,
                record.source_created_at,
                record.source_updated_at,
                record.ingestion_time,
                record.processing_time,
                record.quality_check_time,
            )
        )
        counts_valid = len(observations) == expected_record_count
        return TemporalValidation(
            record_count=len(observations),
            period_count=profile.period_count,
            all_periods_present=all_periods_present,
            period_assignment_valid=period_assignment_valid,
            semantic_order_valid=semantic_order_valid,
            utc_valid=utc_valid,
            passed=(
                counts_valid
                and all_periods_present
                and period_assignment_valid
                and semantic_order_valid
                and utc_valid
            ),
        )


def _validate_generation_contract(
    run: SyntheticGenerationRun,
    scenario: SyntheticScenario,
    profile: SyntheticTemporalProfile,
) -> None:
    if run.status is not SyntheticRunStatus.REQUESTED:
        raise SyntheticDataValidationError("Synthetic run is not ready for generation.")
    if run.output_reference is not None or run.validation_reference is not None:
        raise SyntheticDataValidationError("Synthetic run already contains output metadata.")
    if run.generator_version != TEMPORAL_GENERATOR_VERSION:
        raise SyntheticDataValidationError("Temporal generator version is not supported.")
    if run.schema_version != TEMPORAL_SCHEMA_VERSION:
        raise SyntheticDataValidationError("Temporal schema version is not supported.")
    if run.configuration_version != TEMPORAL_CONFIGURATION_VERSION:
        raise SyntheticDataValidationError("Temporal configuration version is not supported.")
    if (
        scenario.dataset_id != run.dataset_id
        or scenario.scenario_id != run.scenario_id
        or scenario.scenario_version != run.scenario_version
        or scenario.schema_version != run.schema_version
        or scenario.configuration_version != run.configuration_version
    ):
        raise SyntheticDataValidationError("Synthetic scenario and run lineage do not match.")
    if scenario.synthetic_profile is not SyntheticProfile.NORMAL_OPERATION:
        raise SyntheticDataValidationError(
            "Temporal generation requires the normal operation profile."
        )
    if scenario.distribution_profile != profile.profile_version:
        raise SyntheticDataValidationError("Temporal profile and scenario do not match.")
    if scenario.privacy_profile != FULLY_ARTIFICIAL_PRIVACY_PROFILE:
        raise SyntheticDataValidationError("Temporal generation must be fully artificial.")
    if scenario.volume_profile != "FUNCTIONAL_V1":
        raise SyntheticDataValidationError("Temporal generation requires the functional profile.")
    if scenario.missingness_profile != "NO_MISSINGNESS_V1":
        raise SyntheticDataValidationError(
            "Temporal generation cannot inject missingness in this iteration."
        )
    if scenario.defect_injection_profile != "NO_DEFECTS_V1":
        raise SyntheticDataValidationError(
            "Temporal generation cannot inject defects in this iteration."
        )
    if run.requested_record_count < profile.period_count:
        raise SyntheticDataValidationError(
            "Temporal generation requires at least one record per period."
        )


def _build_observation(
    run: SyntheticGenerationRun,
    profile: SyntheticTemporalProfile,
    index: int,
) -> TemporalObservationRecord:
    period_index = index % profile.period_count
    event_offset = _entropy(run.random_seed, "temporal-event", index) % (
        profile.period_duration_seconds
    )
    event_time = profile.base_time + timedelta(
        seconds=period_index * profile.period_duration_seconds + event_offset
    )
    return TemporalObservationRecord(
        observation_id=_synthetic_id(run.random_seed, index),
        period_index=period_index,
        event_time=event_time,
        source_created_at=event_time + timedelta(seconds=profile.source_created_delay_seconds),
        source_updated_at=event_time + timedelta(seconds=profile.source_updated_delay_seconds),
        ingestion_time=event_time + timedelta(seconds=profile.ingestion_delay_seconds),
        processing_time=event_time + timedelta(seconds=profile.processing_delay_seconds),
        quality_check_time=event_time + timedelta(seconds=profile.quality_check_delay_seconds),
    )


def _entropy(seed: int, label: str, index: int) -> int:
    value = f"{seed}:{label}:{index}".encode()
    return int.from_bytes(hashlib.sha256(value).digest()[:8], "big")


def _synthetic_id(seed: int, index: int) -> str:
    digest = hashlib.sha256(f"{seed}:temporal-observation:{index}".encode()).hexdigest()[:20]
    return f"SYN-T-{digest.upper()}"
