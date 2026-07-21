"""FR-088/093, UC-017 ve AC-049 sentetik kayıt çekirdeği testleri."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import sqlite3
from typing import Any

import pytest

from veri_kalitesi.audit import (
    AuditRedactor,
    SQLiteAuditRepository,
    SQLiteTransactionalAudit,
    build_default_redaction_policy,
)
from veri_kalitesi.identity import ActorContext, ActorContextIssuer, ActorType
from veri_kalitesi.synthetic_data import (
    SQLiteSyntheticDataRepository,
    SyntheticDataAuthorizationError,
    SyntheticDataConflictError,
    SyntheticDataTechnicalError,
    SyntheticDataValidationError,
    SyntheticDatasetPolicy,
    SyntheticGenerationRun,
    SyntheticGenerationRegistryService,
    SyntheticPolicyStatus,
    SyntheticProfile,
    SyntheticRunAccessPolicy,
    SyntheticRunStatus,
    SyntheticScenario,
)


NOW = datetime(2026, 7, 21, 10, 0, tzinfo=timezone.utc)
DATASET_ID = "dataset-synthetic-main"
ACTOR_POLICY_VERSION = "SYNTHETIC_ACTOR_POLICY_V1"


class FailingSyntheticAudit(SQLiteTransactionalAudit):
    def stage(self, prepared: Any) -> None:
        raise sqlite3.OperationalError("synthetic audit staging outage")


def test_fr_088_fr_093_ac_049_same_lineage_creates_distinct_immutable_runs() -> None:
    service, repository, audit_repository = _service()
    context = _context("synthetic-requester", {"SYNTHETIC_REQUESTER"})

    first = _request(service, context)
    second = _request(service, context)

    assert first.generation_run_id != second.generation_run_id
    assert first.status is SyntheticRunStatus.REQUESTED
    assert first.random_seed == second.random_seed == 424242
    assert first.policy_version == second.policy_version == "SYNTHETIC_POLICY_V1"
    assert first.scenario_version == second.scenario_version == "SCENARIO_V1"
    assert first.generator_version == second.generator_version == "GENERATOR_V1"
    assert first.configuration_version == second.configuration_version == "CONFIG_V1"
    assert first.schema_version == second.schema_version == "SCHEMA_V1"
    assert first.requested_record_count == second.requested_record_count == 1000
    assert first.output_reference is None
    assert first.validation_reference is None
    assert len(repository.list_runs(DATASET_ID)) == 2
    events = audit_repository.list_events()
    assert len(events) == 2
    assert events[0].action == "SYNTHETIC_GENERATION_RUN_REQUESTED"
    assert events[0].new_value_summary["seed_present"] is True
    assert "random_seed" not in events[0].new_value_summary
    assert "synthetic-session" not in repr(events[0])

    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        repository.connection.execute(
            "UPDATE synthetic_generation_runs SET status = 'CHANGED' WHERE generation_run_id = ?",
            (first.generation_run_id,),
        )


def test_fr_088_uc_017_missing_policy_fails_closed_without_run_or_audit() -> None:
    service, repository, audit_repository = _service(add_policy=False)

    with pytest.raises(SyntheticDataValidationError, match="Active approved"):
        _request(service, _context("requester", {"SYNTHETIC_REQUESTER"}))

    assert repository.list_runs(DATASET_ID) == []
    assert audit_repository.list_events() == []


def test_fr_088_overlapping_effective_policies_fail_closed() -> None:
    repository = SQLiteSyntheticDataRepository()
    repository.add_policy(_policy())
    repository.add_policy(
        replace(
            _policy(),
            policy_id="policy-synthetic-v2",
            policy_version="SYNTHETIC_POLICY_V2",
        )
    )
    repository.add_scenario(_scenario())
    service, _, audit_repository = _service(repository=repository, add_inputs=False)

    with pytest.raises(SyntheticDataConflictError, match="Multiple effective"):
        _request(service, _context("requester", {"SYNTHETIC_REQUESTER"}))

    assert repository.list_runs(DATASET_ID) == []
    assert audit_repository.list_events() == []


@pytest.mark.parametrize(
    "policy_change",
    [
        {"synthetic_generation_allowed": False},
        {"ground_truth_enabled": False},
        {"effective_to": NOW},
        {"approval_status": SyntheticPolicyStatus.PENDING, "approved_by": None},
    ],
)
def test_fr_088_rule_016_inactive_or_incomplete_policy_fails_closed(
    policy_change: dict[str, Any],
) -> None:
    repository = SQLiteSyntheticDataRepository()
    repository.add_policy(replace(_policy(), **policy_change))
    repository.add_scenario(_scenario())
    service, _, audit_repository = _service(repository=repository, add_inputs=False)

    with pytest.raises(SyntheticDataValidationError):
        _request(service, _context("requester", {"SYNTHETIC_REQUESTER"}))

    assert repository.list_runs(DATASET_ID) == []
    assert audit_repository.list_events() == []


@pytest.mark.parametrize(
    "context_case",
    [
        "missing",
        "wrong-role",
        "wrong-scope",
        "service-actor",
        "privileged",
    ],
)
def test_fr_088_uc_017_untrusted_or_unauthorized_context_is_rejected_before_write(
    context_case: str,
) -> None:
    service, repository, audit_repository = _service()
    contexts = {
        "missing": None,
        "wrong-role": _context("wrong-role", {"VIEWER"}),
        "wrong-scope": _context("wrong-scope", {"SYNTHETIC_REQUESTER"}, dataset_ids=frozenset()),
        "service-actor": _context(
            "service-actor",
            {"SYNTHETIC_REQUESTER"},
            actor_type=ActorType.SERVICE,
        ),
        "privileged": _context("privileged", {"SYNTHETIC_REQUESTER"}, privileged=True),
    }

    with pytest.raises(SyntheticDataAuthorizationError):
        _request(service, contexts[context_case])

    assert repository.list_runs(DATASET_ID) == []
    assert audit_repository.list_events() == []


def test_fr_093_rule_016_scenario_policy_version_mismatch_is_rejected() -> None:
    repository = SQLiteSyntheticDataRepository()
    repository.add_policy(_policy())
    repository.add_scenario(replace(_scenario(), schema_version="SCHEMA_V2"))
    service, _, audit_repository = _service(repository=repository, add_inputs=False)

    with pytest.raises(SyntheticDataValidationError, match="does not match"):
        _request(service, _context("requester", {"SYNTHETIC_REQUESTER"}))

    assert repository.list_runs(DATASET_ID) == []
    assert audit_repository.list_events() == []


@pytest.mark.parametrize(
    ("generator_version", "random_seed", "requested_record_count"),
    [
        ("", 42, 10),
        ("GENERATOR_V1", True, 10),
        ("GENERATOR_V1", 42, 0),
    ],
)
def test_fr_093_missing_lineage_or_invalid_volume_is_rejected(
    generator_version: str,
    random_seed: Any,
    requested_record_count: int,
) -> None:
    service, repository, audit_repository = _service()

    with pytest.raises(SyntheticDataValidationError):
        service.request_run(
            actor_context=_context("requester", {"SYNTHETIC_REQUESTER"}),
            dataset_id=DATASET_ID,
            scenario_id="scenario-golden-main",
            scenario_version="SCENARIO_V1",
            generator_version=generator_version,
            configuration_version="CONFIG_V1",
            random_seed=random_seed,
            requested_record_count=requested_record_count,
        )

    assert repository.list_runs(DATASET_ID) == []
    assert audit_repository.list_events() == []


def test_fr_088_audit_outbox_failure_rolls_back_run() -> None:
    repository = SQLiteSyntheticDataRepository()
    repository.add_policy(_policy())
    repository.add_scenario(_scenario())
    audit_repository = SQLiteAuditRepository()
    audit = FailingSyntheticAudit(
        repository.connection,
        AuditRedactor(build_default_redaction_policy()),
        audit_repository,
        policy_version="SYNTHETIC_AUDIT_OUTBOX_V1",
    )
    service = SyntheticGenerationRegistryService(
        repository,
        transactional_audit=audit,
        access_policy=_access_policy(),
        clock=lambda: NOW,
    )

    with pytest.raises(SyntheticDataTechnicalError, match="run and audit"):
        _request(service, _context("requester", {"SYNTHETIC_REQUESTER"}))

    assert repository.list_runs(DATASET_ID) == []
    assert audit_repository.list_events() == []


def test_fr_088_repository_failure_is_technical_not_quality_failure() -> None:
    service, repository, _ = _service()
    repository.connection.close()

    with pytest.raises(SyntheticDataTechnicalError, match="policy could not be read"):
        _request(service, _context("requester", {"SYNTHETIC_REQUESTER"}))


def test_rule_016_policy_and_scenario_versions_are_append_only() -> None:
    repository = SQLiteSyntheticDataRepository()
    policy = _policy()
    scenario = _scenario()
    repository.add_policy(policy)
    repository.add_scenario(scenario)

    with pytest.raises(SyntheticDataConflictError):
        repository.add_policy(replace(policy, policy_id="different-policy-id"))
    with pytest.raises(SyntheticDataConflictError):
        repository.add_scenario(replace(scenario, scenario_record_id="different-record-id"))


def _service(
    *,
    repository: SQLiteSyntheticDataRepository | None = None,
    add_policy: bool = True,
    add_inputs: bool = True,
) -> tuple[
    SyntheticGenerationRegistryService,
    SQLiteSyntheticDataRepository,
    SQLiteAuditRepository,
]:
    repository = repository or SQLiteSyntheticDataRepository()
    if add_inputs:
        if add_policy:
            repository.add_policy(_policy())
        repository.add_scenario(_scenario())
    audit_repository = SQLiteAuditRepository()
    audit = SQLiteTransactionalAudit(
        repository.connection,
        AuditRedactor(build_default_redaction_policy()),
        audit_repository,
        policy_version="SYNTHETIC_AUDIT_OUTBOX_V1",
    )
    service = SyntheticGenerationRegistryService(
        repository,
        transactional_audit=audit,
        access_policy=_access_policy(),
        clock=lambda: NOW,
    )
    return service, repository, audit_repository


def _policy() -> SyntheticDatasetPolicy:
    return SyntheticDatasetPolicy(
        policy_id="policy-synthetic-v1",
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
        schema_version="SCHEMA_V1",
        policy_version="SYNTHETIC_POLICY_V1",
        effective_from=NOW - timedelta(days=1),
        effective_to=None,
        approved_by="synthetic-policy-checker",
        approval_status=SyntheticPolicyStatus.APPROVED,
        audit_reference="audit-policy-approved",
        created_at=NOW - timedelta(days=2),
    )


def _scenario() -> SyntheticScenario:
    return SyntheticScenario(
        scenario_record_id="scenario-record-v1",
        scenario_id="scenario-golden-main",
        dataset_id=DATASET_ID,
        scenario_version="SCENARIO_V1",
        schema_version="SCHEMA_V1",
        configuration_version="CONFIG_V1",
        synthetic_profile=SyntheticProfile.GOLDEN,
        volume_profile="FUNCTIONAL_V1",
        distribution_profile="ARTIFICIAL_DISTRIBUTION_V1",
        missingness_profile="NO_MISSINGNESS_V1",
        defect_injection_profile="NO_DEFECTS_V1",
        privacy_profile="FULLY_ARTIFICIAL_V1",
        created_at=NOW - timedelta(hours=1),
    )


def _access_policy() -> SyntheticRunAccessPolicy:
    return SyntheticRunAccessPolicy(
        version="SYNTHETIC_RUN_ACCESS_V1",
        actor_policy_version=ACTOR_POLICY_VERSION,
        requester_roles=frozenset({"SYNTHETIC_REQUESTER"}),
    )


def _context(
    actor_id: str,
    roles: set[str],
    *,
    dataset_ids: frozenset[str] = frozenset({DATASET_ID}),
    actor_type: ActorType = ActorType.USER,
    privileged: bool = False,
) -> ActorContext:
    return ActorContextIssuer().issue(
        actor_id=actor_id,
        actor_type=actor_type,
        authentication_source="synthetic-identity-adapter",
        session_id="synthetic-session-sensitive",
        roles=frozenset(roles),
        permitted_source_ids=frozenset(),
        permitted_dataset_ids=dataset_ids,
        can_view_enterprise=False,
        privileged=privileged,
        issued_at=NOW - timedelta(minutes=5),
        expires_at=NOW + timedelta(hours=1),
        policy_version=ACTOR_POLICY_VERSION,
        correlation_id=f"correlation-{actor_id}",
    )


def _request(
    service: SyntheticGenerationRegistryService,
    context: ActorContext | None,
) -> SyntheticGenerationRun:
    return service.request_run(
        actor_context=context,
        dataset_id=DATASET_ID,
        scenario_id="scenario-golden-main",
        scenario_version="SCENARIO_V1",
        generator_version="GENERATOR_V1",
        configuration_version="CONFIG_V1",
        random_seed=424242,
        requested_record_count=1000,
    )
