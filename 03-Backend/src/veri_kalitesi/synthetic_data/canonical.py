"""Golden sentetik çıktı için kanonik serileştirme sözleşmesi."""

from __future__ import annotations

import json

from veri_kalitesi.synthetic_data.models import (
    GoldenObservationRecord,
    GoldenSubjectRecord,
    SyntheticGenerationRun,
    SyntheticScenario,
    SyntheticTemporalProfile,
    TemporalObservationRecord,
)


def build_golden_canonical_payload(
    run: SyntheticGenerationRun,
    scenario: SyntheticScenario,
    subjects: tuple[GoldenSubjectRecord, ...],
    observations: tuple[GoldenObservationRecord, ...],
) -> bytes:
    document = {
        "lineage": {
            "configuration_version": run.configuration_version,
            "dataset_id": run.dataset_id,
            "generator_version": run.generator_version,
            "policy_version": run.policy_version,
            "random_seed": run.random_seed,
            "requested_record_count": run.requested_record_count,
            "scenario_id": scenario.scenario_id,
            "scenario_version": scenario.scenario_version,
            "schema_version": run.schema_version,
            "synthetic_origin": True,
        },
        "observations": [
            {
                "amount": format(record.amount, ".2f"),
                "currency_code": record.currency_code,
                "event_time": record.event_time.isoformat(),
                "observation_id": record.observation_id,
                "source_created_at": record.source_created_at.isoformat(),
                "source_updated_at": record.source_updated_at.isoformat(),
                "subject_id": record.subject_id,
            }
            for record in observations
        ],
        "subjects": [
            {
                "current_status": record.current_status,
                "effective_date": record.effective_date.isoformat(),
                "previous_status": record.previous_status,
                "segment_code": record.segment_code,
                "source_system_code": record.source_system_code,
                "subject_id": record.subject_id,
            }
            for record in subjects
        ],
    }
    return json.dumps(
        document,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def build_temporal_canonical_payload(
    run: SyntheticGenerationRun,
    scenario: SyntheticScenario,
    profile: SyntheticTemporalProfile,
    observations: tuple[TemporalObservationRecord, ...],
) -> bytes:
    document = {
        "lineage": {
            "configuration_version": run.configuration_version,
            "dataset_id": run.dataset_id,
            "generator_version": run.generator_version,
            "policy_version": run.policy_version,
            "random_seed": run.random_seed,
            "requested_record_count": run.requested_record_count,
            "scenario_id": scenario.scenario_id,
            "scenario_version": scenario.scenario_version,
            "schema_version": run.schema_version,
            "synthetic_origin": True,
            "temporal_profile_version": profile.profile_version,
        },
        "observations": [
            {
                "event_time": record.event_time.isoformat(),
                "ingestion_time": record.ingestion_time.isoformat(),
                "observation_id": record.observation_id,
                "period_index": record.period_index,
                "processing_time": record.processing_time.isoformat(),
                "quality_check_time": record.quality_check_time.isoformat(),
                "source_created_at": record.source_created_at.isoformat(),
                "source_updated_at": record.source_updated_at.isoformat(),
            }
            for record in observations
        ],
        "temporal_profile": {
            "base_time": profile.base_time.isoformat(),
            "ingestion_delay_seconds": profile.ingestion_delay_seconds,
            "period_count": profile.period_count,
            "period_duration_seconds": profile.period_duration_seconds,
            "processing_delay_seconds": profile.processing_delay_seconds,
            "quality_check_delay_seconds": profile.quality_check_delay_seconds,
            "source_created_delay_seconds": profile.source_created_delay_seconds,
            "source_updated_delay_seconds": profile.source_updated_delay_seconds,
        },
    }
    return json.dumps(
        document,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
