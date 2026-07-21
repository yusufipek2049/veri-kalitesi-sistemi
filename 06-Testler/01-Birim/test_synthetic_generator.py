"""FR-089/090/093, UC-017 ve AC-048/049 Golden üretici testleri."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json

import pytest

from veri_kalitesi.audit import (
    AuditRedactor,
    SQLiteAuditRepository,
    SQLiteTransactionalAudit,
    build_default_redaction_policy,
)
from veri_kalitesi.identity import ActorContextIssuer, ActorType
from veri_kalitesi.synthetic_data import (
    GOLDEN_CONFIGURATION_VERSION,
    GOLDEN_GENERATOR_VERSION,
    GOLDEN_SCHEMA_VERSION,
    GoldenRelationalGenerator,
    SQLiteSyntheticDataRepository,
    SyntheticDataValidationError,
    SyntheticDatasetPolicy,
    SyntheticGenerationRun,
    SyntheticGenerationRegistryService,
    SyntheticPolicyStatus,
    SyntheticProfile,
    SyntheticRunAccessPolicy,
    SyntheticScenario,
)


NOW = datetime(2026, 7, 21, 12, 0, tzinfo=timezone.utc)
DATASET_ID = "dataset-fully-artificial-golden"
ACTOR_POLICY_VERSION = "SYNTHETIC_ACTOR_POLICY_V1"


def test_fr_093_ac_049_replays_are_byte_equivalent_but_keep_distinct_run_ids() -> None:
    service, repository = _registry()
    first_run = _request(service, random_seed=424242)
    second_run = _request(service, random_seed=424242)
    generator = GoldenRelationalGenerator(repository)

    first = generator.generate(first_run.generation_run_id)
    second = generator.generate(second_run.generation_run_id)

    assert first.generation_run_id != second.generation_run_id
    assert first.canonical_payload == second.canonical_payload
    assert first.canonical_sha256 == second.canonical_sha256
    assert first.output_reference == second.output_reference
    assert first.synthetic_origin is True
    assert first.generation_run_id.encode() not in first.canonical_payload
    assert second.generation_run_id.encode() not in second.canonical_payload
    assert b"synthetic-requester" not in first.canonical_payload
    assert b"synthetic-session-sensitive" not in first.canonical_payload


def test_fr_089_ac_048_golden_output_preserves_relational_and_business_constraints() -> None:
    service, repository = _registry()
    run = _request(service, random_seed=11, requested_record_count=24)

    output = GoldenRelationalGenerator(repository).generate(run.generation_run_id)

    assert output.validation.passed is True
    assert output.validation.subject_count == 24
    assert output.validation.observation_count == 24
    assert output.validation.primary_keys_unique is True
    assert output.validation.foreign_keys_valid is True
    assert output.validation.status_transitions_valid is True
    assert output.validation.reference_codes_valid is True
    assert output.validation.temporal_order_valid is True
    subject_ids = {record.subject_id for record in output.subjects}
    assert len(subject_ids) == 24
    assert {record.subject_id for record in output.observations} == subject_ids
    assert all(record.source_system_code == "SYNTHETIC_SOURCE" for record in output.subjects)
    expected_transitions = {
        "SEGMENT_A": ("NEW", "ACTIVE"),
        "SEGMENT_B": ("ACTIVE", "ACTIVE"),
        "SEGMENT_C": ("ACTIVE", "CLOSED"),
    }
    assert all(
        (record.previous_status, record.current_status) == expected_transitions[record.segment_code]
        for record in output.subjects
    )
    assert all(record.currency_code == "SYN" for record in output.observations)
    assert all(record.amount.as_tuple().exponent == -2 for record in output.observations)
    assert all(
        record.source_created_at <= record.source_updated_at <= record.event_time
        for record in output.observations
    )


def test_fr_090_rule_016_artificial_profile_is_deterministic_and_seed_sensitive() -> None:
    service, repository = _registry()
    first_run = _request(service, random_seed=100)
    replay_run = _request(service, random_seed=100)
    changed_seed_run = _request(service, random_seed=101)

    first = GoldenRelationalGenerator(repository).generate(first_run.generation_run_id)
    replay = GoldenRelationalGenerator(repository).generate(replay_run.generation_run_id)
    changed = GoldenRelationalGenerator(repository).generate(changed_seed_run.generation_run_id)

    assert first.subjects == replay.subjects
    assert first.observations == replay.observations
    assert first.canonical_sha256 == replay.canonical_sha256
    assert first.canonical_sha256 != changed.canonical_sha256
    assert first.subjects != changed.subjects
    assert first.observations != changed.observations


def test_fr_093_canonical_payload_contains_complete_data_lineage() -> None:
    service, repository = _registry()
    run = _request(service, random_seed=77, requested_record_count=3)

    output = GoldenRelationalGenerator(repository).generate(run.generation_run_id)
    payload = json.loads(output.canonical_payload)

    assert payload["lineage"] == {
        "configuration_version": GOLDEN_CONFIGURATION_VERSION,
        "dataset_id": DATASET_ID,
        "generator_version": GOLDEN_GENERATOR_VERSION,
        "policy_version": "SYNTHETIC_POLICY_V1",
        "random_seed": 77,
        "requested_record_count": 3,
        "scenario_id": "scenario-golden-relational",
        "scenario_version": "SCENARIO_V1",
        "schema_version": GOLDEN_SCHEMA_VERSION,
        "synthetic_origin": True,
    }
    assert len(payload["subjects"]) == len(payload["observations"]) == 3


@pytest.mark.parametrize(
    ("profile_case", "expected_message"),
    [
        ("normal-profile", "Only the Golden"),
        ("production-profile", "fully artificial"),
        ("missingness", "cannot inject missingness"),
        ("defects", "cannot inject defects"),
    ],
)
def test_fr_089_rule_016_non_golden_or_non_artificial_profiles_fail_closed(
    profile_case: str,
    expected_message: str,
) -> None:
    service, repository = _registry(profile_case=profile_case)
    run = _request(service, random_seed=42)

    with pytest.raises(SyntheticDataValidationError, match=expected_message):
        GoldenRelationalGenerator(repository).generate(run.generation_run_id)


def test_fr_093_unsupported_generator_version_fails_before_output() -> None:
    service, repository = _registry()
    run = _request(service, random_seed=42, generator_version="UNKNOWN_GENERATOR_V1")

    with pytest.raises(SyntheticDataValidationError, match="version is not supported"):
        GoldenRelationalGenerator(repository).generate(run.generation_run_id)


def _registry(
    *,
    profile_case: str | None = None,
) -> tuple[SyntheticGenerationRegistryService, SQLiteSyntheticDataRepository]:
    repository = SQLiteSyntheticDataRepository()
    policy = SyntheticDatasetPolicy(
        policy_id="policy-golden-v1",
        dataset_id=DATASET_ID,
        synthetic_generation_allowed=True,
        synthetic_profile=SyntheticProfile.GOLDEN,
        volume_profile="FUNCTIONAL_V1",
        distribution_profile="ARTIFICIAL_DISTRIBUTION_V1",
        missingness_profile="NO_MISSINGNESS_V1",
        defect_injection_profile="NO_DEFECTS_V1",
        privacy_profile="FULLY_ARTIFICIAL_V1",
        retention_policy_id="retention-synthetic-v1",
        ground_truth_enabled=True,
        seed_strategy="CALLER_SUPPLIED_V1",
        expected_score_tolerance=None,
        criticality_profile_id="criticality-synthetic-v1",
        notification_test_enabled=False,
        schema_version=GOLDEN_SCHEMA_VERSION,
        policy_version="SYNTHETIC_POLICY_V1",
        effective_from=NOW - timedelta(days=1),
        effective_to=None,
        approved_by="synthetic-policy-checker",
        approval_status=SyntheticPolicyStatus.APPROVED,
        audit_reference="audit-policy-approved",
        created_at=NOW - timedelta(days=2),
    )
    scenario = SyntheticScenario(
        scenario_record_id="scenario-record-v1",
        scenario_id="scenario-golden-relational",
        dataset_id=DATASET_ID,
        scenario_version="SCENARIO_V1",
        schema_version=GOLDEN_SCHEMA_VERSION,
        configuration_version=GOLDEN_CONFIGURATION_VERSION,
        synthetic_profile=SyntheticProfile.GOLDEN,
        volume_profile="FUNCTIONAL_V1",
        distribution_profile="ARTIFICIAL_DISTRIBUTION_V1",
        missingness_profile="NO_MISSINGNESS_V1",
        defect_injection_profile="NO_DEFECTS_V1",
        privacy_profile="FULLY_ARTIFICIAL_V1",
        created_at=NOW - timedelta(hours=1),
    )
    if profile_case == "normal-profile":
        policy = replace(policy, synthetic_profile=SyntheticProfile.NORMAL_OPERATION)
        scenario = replace(scenario, synthetic_profile=SyntheticProfile.NORMAL_OPERATION)
    elif profile_case == "production-profile":
        policy = replace(policy, privacy_profile="PRODUCTION_PROFILE_V1")
        scenario = replace(scenario, privacy_profile="PRODUCTION_PROFILE_V1")
    elif profile_case == "missingness":
        policy = replace(policy, missingness_profile="ARTIFICIAL_MISSINGNESS_V1")
        scenario = replace(scenario, missingness_profile="ARTIFICIAL_MISSINGNESS_V1")
    elif profile_case == "defects":
        policy = replace(policy, defect_injection_profile="ARTIFICIAL_DEFECTS_V1")
        scenario = replace(scenario, defect_injection_profile="ARTIFICIAL_DEFECTS_V1")
    elif profile_case is not None:
        raise AssertionError(f"Unknown test profile case: {profile_case}")
    repository.add_policy(policy)
    repository.add_scenario(scenario)
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


def _request(
    service: SyntheticGenerationRegistryService,
    *,
    random_seed: int,
    requested_record_count: int = 12,
    generator_version: str = GOLDEN_GENERATOR_VERSION,
) -> SyntheticGenerationRun:
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
        scenario_id="scenario-golden-relational",
        scenario_version="SCENARIO_V1",
        generator_version=generator_version,
        configuration_version=GOLDEN_CONFIGURATION_VERSION,
        random_seed=random_seed,
        requested_record_count=requested_record_count,
    )
