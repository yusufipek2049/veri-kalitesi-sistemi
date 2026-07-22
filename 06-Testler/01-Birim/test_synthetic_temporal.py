"""FR-090/094, UC-017, RULE-016 ve AC/TS-054 temporal üretici testleri."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import sqlite3
from typing import Callable

import pytest

from veri_kalitesi.audit import (
    AuditRedactor,
    SQLiteAuditRepository,
    SQLiteTransactionalAudit,
    build_default_redaction_policy,
)
from veri_kalitesi.identity import ActorContextIssuer, ActorType
from veri_kalitesi.synthetic_data import (
    FULLY_ARTIFICIAL_PRIVACY_PROFILE,
    TEMPORAL_CONFIGURATION_VERSION,
    TEMPORAL_GENERATOR_VERSION,
    TEMPORAL_SCHEMA_VERSION,
    DeterministicTemporalGenerator,
    SQLiteSyntheticDataRepository,
    SyntheticDataTechnicalError,
    SyntheticDataValidationError,
    SyntheticDatasetPolicy,
    SyntheticGenerationRegistryService,
    SyntheticPolicyStatus,
    SyntheticProfile,
    SyntheticRunAccessPolicy,
    SyntheticScenario,
    SyntheticTemporalProfile,
    TemporalSemanticValidator,
)


NOW = datetime(2026, 7, 22, 12, 0, tzinfo=timezone.utc)
BASE_TIME = datetime(2000, 1, 1, tzinfo=timezone.utc)
DATASET_ID = "dataset-fully-artificial-temporal"
TEMPORAL_PROFILE_VERSION = "ARTIFICIAL_TEMPORAL_PROFILE_V1"
ACTOR_POLICY_VERSION = "SYNTHETIC_ACTOR_POLICY_V1"


def test_fr_090_ac_054_preserves_six_time_meanings_across_multiple_periods() -> None:
    service, repository = _registry()
    run = _request(service, random_seed=42, requested_record_count=20)

    output = DeterministicTemporalGenerator(repository).generate(run.generation_run_id)

    assert output.validation.passed is True
    assert output.validation.record_count == 20
    assert output.validation.period_count == 4
    assert output.validation.all_periods_present is True
    assert output.validation.period_assignment_valid is True
    assert output.validation.semantic_order_valid is True
    assert output.validation.utc_valid is True
    assert {record.period_index for record in output.observations} == {0, 1, 2, 3}
    for record in output.observations:
        assert (
            record.event_time
            <= record.source_created_at
            <= record.source_updated_at
            <= record.ingestion_time
            <= record.processing_time
            <= record.quality_check_time
        )
        assert record.event_time.utcoffset() == timedelta(0)


def test_ac_054_independent_validator_detects_period_and_semantic_tampering() -> None:
    service, repository = _registry()
    run = _request(service, random_seed=42, requested_record_count=8)
    output = DeterministicTemporalGenerator(repository).generate(run.generation_run_id)
    profile = repository.get_temporal_profile(TEMPORAL_PROFILE_VERSION)
    validator = TemporalSemanticValidator()

    period_tampered = (
        replace(output.observations[0], period_index=3),
        *output.observations[1:],
    )
    period_result = validator.validate(
        expected_record_count=8,
        profile=profile,
        observations=period_tampered,
    )
    semantic_tampered = (
        replace(
            output.observations[0],
            ingestion_time=output.observations[0].event_time,
        ),
        *output.observations[1:],
    )
    semantic_result = validator.validate(
        expected_record_count=8,
        profile=profile,
        observations=semantic_tampered,
    )

    assert period_result.passed is False
    assert period_result.period_assignment_valid is False
    assert semantic_result.passed is False
    assert semantic_result.semantic_order_valid is False


def test_rule_016_temporal_replay_is_byte_equivalent_and_seed_sensitive() -> None:
    service, repository = _registry()
    first_run = _request(service, random_seed=100)
    replay_run = _request(service, random_seed=100)
    changed_run = _request(service, random_seed=101)
    generator = DeterministicTemporalGenerator(repository)

    first = generator.generate(first_run.generation_run_id)
    replay = generator.generate(replay_run.generation_run_id)
    changed = generator.generate(changed_run.generation_run_id)

    assert first.generation_run_id != replay.generation_run_id
    assert first.observations == replay.observations
    assert first.canonical_payload == replay.canonical_payload
    assert first.canonical_sha256 == replay.canonical_sha256
    assert first.canonical_sha256 != changed.canonical_sha256
    assert first.observations != changed.observations


def test_fr_093_temporal_payload_contains_lineage_without_actor_or_run_identity() -> None:
    service, repository = _registry()
    run = _request(service, random_seed=77, requested_record_count=8)

    output = DeterministicTemporalGenerator(repository).generate(run.generation_run_id)
    payload = json.loads(output.canonical_payload)

    assert payload["lineage"]["temporal_profile_version"] == TEMPORAL_PROFILE_VERSION
    assert payload["lineage"]["generator_version"] == TEMPORAL_GENERATOR_VERSION
    assert payload["lineage"]["requested_record_count"] == 8
    assert len(payload["observations"]) == 8
    assert set(payload["observations"][0]) == {
        "event_time",
        "ingestion_time",
        "observation_id",
        "period_index",
        "processing_time",
        "quality_check_time",
        "source_created_at",
        "source_updated_at",
    }
    assert run.generation_run_id.encode() not in output.canonical_payload
    assert b"synthetic-requester" not in output.canonical_payload
    assert b"synthetic-session-sensitive" not in output.canonical_payload


def test_rule_016_temporal_profile_is_append_only() -> None:
    _, repository = _registry()

    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        repository.connection.execute("UPDATE synthetic_temporal_profiles SET period_count = 9")
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        repository.connection.execute("DELETE FROM synthetic_temporal_profiles")


@pytest.mark.parametrize(
    ("change_profile", "expected_message"),
    [
        (lambda profile: replace(profile, base_time=datetime(2000, 1, 1)), "timezone-aware"),
        (lambda profile: replace(profile, period_count=1), "multiple periods"),
        (
            lambda profile: replace(profile, period_duration_seconds=0),
            "duration must be positive",
        ),
        (lambda profile: replace(profile, ingestion_delay_seconds=30), "processing order"),
    ],
)
def test_ac_054_invalid_temporal_profile_fails_before_run(
    change_profile: Callable[[SyntheticTemporalProfile], SyntheticTemporalProfile],
    expected_message: str,
) -> None:
    repository = SQLiteSyntheticDataRepository()

    with pytest.raises(SyntheticDataValidationError, match=expected_message):
        repository.add_temporal_profile(change_profile(_temporal_profile()))


def test_ac_054_requires_at_least_one_record_per_period() -> None:
    service, repository = _registry()
    run = _request(service, random_seed=42, requested_record_count=3)

    with pytest.raises(SyntheticDataValidationError, match="one record per period"):
        DeterministicTemporalGenerator(repository).generate(run.generation_run_id)


def test_fr_090_missing_temporal_profile_fails_closed() -> None:
    service, repository = _registry(add_temporal_profile=False)
    run = _request(service, random_seed=42)

    with pytest.raises(SyntheticDataValidationError, match="profile was not found"):
        DeterministicTemporalGenerator(repository).generate(run.generation_run_id)


def test_fr_093_unsupported_temporal_generator_version_fails_closed() -> None:
    service, repository = _registry()
    run = _request(service, random_seed=42, generator_version="UNKNOWN_TEMPORAL_V1")

    with pytest.raises(SyntheticDataValidationError, match="version is not supported"):
        DeterministicTemporalGenerator(repository).generate(run.generation_run_id)


@pytest.mark.parametrize(
    ("profile_case", "expected_message"),
    [
        ("golden", "normal operation"),
        ("production-profile", "fully artificial"),
        ("missingness", "cannot inject missingness"),
        ("defects", "cannot inject defects"),
    ],
)
def test_fr_090_open_024_behaviors_remain_fail_closed(
    profile_case: str,
    expected_message: str,
) -> None:
    service, repository = _registry(profile_case=profile_case)
    run = _request(service, random_seed=42)

    with pytest.raises(SyntheticDataValidationError, match=expected_message):
        DeterministicTemporalGenerator(repository).generate(run.generation_run_id)


def test_ac_054_repository_outage_is_a_technical_error() -> None:
    service, repository = _registry()
    run = _request(service, random_seed=42)
    repository.connection.close()

    with pytest.raises(SyntheticDataTechnicalError, match="could not be read"):
        DeterministicTemporalGenerator(repository).generate(run.generation_run_id)


def _registry(
    *,
    add_temporal_profile: bool = True,
    profile_case: str | None = None,
) -> tuple[SyntheticGenerationRegistryService, SQLiteSyntheticDataRepository]:
    repository = SQLiteSyntheticDataRepository()
    profile = SyntheticProfile.NORMAL_OPERATION
    privacy_profile = FULLY_ARTIFICIAL_PRIVACY_PROFILE
    missingness_profile = "NO_MISSINGNESS_V1"
    defect_profile = "NO_DEFECTS_V1"
    if profile_case == "golden":
        profile = SyntheticProfile.GOLDEN
    elif profile_case == "production-profile":
        privacy_profile = "PRODUCTION_PROFILE_V1"
    elif profile_case == "missingness":
        missingness_profile = "ARTIFICIAL_MISSINGNESS_V1"
    elif profile_case == "defects":
        defect_profile = "ARTIFICIAL_DEFECTS_V1"
    elif profile_case is not None:
        raise AssertionError(f"Unknown profile case: {profile_case}")

    repository.add_policy(
        SyntheticDatasetPolicy(
            policy_id="policy-temporal-v1",
            dataset_id=DATASET_ID,
            synthetic_generation_allowed=True,
            synthetic_profile=profile,
            volume_profile="FUNCTIONAL_V1",
            distribution_profile=TEMPORAL_PROFILE_VERSION,
            missingness_profile=missingness_profile,
            defect_injection_profile=defect_profile,
            privacy_profile=privacy_profile,
            retention_policy_id="retention-synthetic-v1",
            ground_truth_enabled=True,
            seed_strategy="CALLER_SUPPLIED_V1",
            expected_score_tolerance=None,
            criticality_profile_id="criticality-synthetic-v1",
            notification_test_enabled=False,
            schema_version=TEMPORAL_SCHEMA_VERSION,
            policy_version="SYNTHETIC_TEMPORAL_POLICY_V1",
            effective_from=NOW - timedelta(days=1),
            effective_to=None,
            approved_by="synthetic-policy-checker",
            approval_status=SyntheticPolicyStatus.APPROVED,
            audit_reference="audit-policy-approved",
            created_at=NOW - timedelta(days=2),
        )
    )
    repository.add_scenario(
        SyntheticScenario(
            scenario_record_id="scenario-temporal-record-v1",
            scenario_id="scenario-temporal-multi-period",
            dataset_id=DATASET_ID,
            scenario_version="TEMPORAL_SCENARIO_V1",
            schema_version=TEMPORAL_SCHEMA_VERSION,
            configuration_version=TEMPORAL_CONFIGURATION_VERSION,
            synthetic_profile=profile,
            volume_profile="FUNCTIONAL_V1",
            distribution_profile=TEMPORAL_PROFILE_VERSION,
            missingness_profile=missingness_profile,
            defect_injection_profile=defect_profile,
            privacy_profile=privacy_profile,
            created_at=NOW - timedelta(hours=1),
        )
    )
    if add_temporal_profile:
        repository.add_temporal_profile(_temporal_profile())
    audit = SQLiteTransactionalAudit(
        repository.connection,
        AuditRedactor(build_default_redaction_policy()),
        SQLiteAuditRepository(),
        policy_version="SYNTHETIC_AUDIT_OUTBOX_V1",
    )
    return (
        SyntheticGenerationRegistryService(
            repository,
            transactional_audit=audit,
            access_policy=SyntheticRunAccessPolicy(
                version="SYNTHETIC_RUN_ACCESS_V1",
                actor_policy_version=ACTOR_POLICY_VERSION,
                requester_roles=frozenset({"SYNTHETIC_REQUESTER"}),
            ),
            clock=lambda: NOW,
        ),
        repository,
    )


def _temporal_profile() -> SyntheticTemporalProfile:
    return SyntheticTemporalProfile(
        profile_version=TEMPORAL_PROFILE_VERSION,
        base_time=BASE_TIME,
        period_count=4,
        period_duration_seconds=86_400,
        source_created_delay_seconds=60,
        source_updated_delay_seconds=120,
        ingestion_delay_seconds=180,
        processing_delay_seconds=240,
        quality_check_delay_seconds=300,
        created_at=NOW - timedelta(hours=2),
    )


def _request(
    service: SyntheticGenerationRegistryService,
    *,
    random_seed: int,
    requested_record_count: int = 12,
    generator_version: str = TEMPORAL_GENERATOR_VERSION,
):
    context = ActorContextIssuer().issue(
        actor_id="synthetic-requester",
        actor_type=ActorType.USER,
        authentication_source="synthetic-identity-adapter",
        session_id="synthetic-session-sensitive",
        roles=frozenset({"SYNTHETIC_REQUESTER"}),
        permitted_source_ids=frozenset(),
        permitted_dataset_ids=frozenset({DATASET_ID}),
        can_view_enterprise=False,
        privileged=False,
        issued_at=NOW - timedelta(minutes=5),
        expires_at=NOW + timedelta(hours=1),
        policy_version=ACTOR_POLICY_VERSION,
        correlation_id=f"correlation-{random_seed}",
    )
    return service.request_run(
        actor_context=context,
        dataset_id=DATASET_ID,
        scenario_id="scenario-temporal-multi-period",
        scenario_version="TEMPORAL_SCENARIO_V1",
        generator_version=generator_version,
        configuration_version=TEMPORAL_CONFIGURATION_VERSION,
        random_seed=random_seed,
        requested_record_count=requested_record_count,
    )
