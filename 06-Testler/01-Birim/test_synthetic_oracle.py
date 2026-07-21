"""FR-092, UC-017 ve RULE-016 Golden bağımsız oracle testleri."""

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
    FULLY_ARTIFICIAL_PRIVACY_PROFILE,
    GOLDEN_CONFIGURATION_VERSION,
    GOLDEN_GENERATOR_VERSION,
    GOLDEN_GROUND_TRUTH_VERSION,
    GOLDEN_SCHEMA_VERSION,
    GoldenRelationalDataset,
    GoldenRelationalGenerator,
    GoldenStructuralOracle,
    SQLiteSyntheticDataRepository,
    SyntheticDataAuthorizationError,
    SyntheticDataConflictError,
    SyntheticDataTechnicalError,
    SyntheticDatasetPolicy,
    SyntheticGenerationRegistryService,
    SyntheticPolicyStatus,
    SyntheticProfile,
    SyntheticRunAccessPolicy,
    SyntheticScenario,
    SyntheticValidationStatus,
)


NOW = datetime(2026, 7, 21, 14, 0, tzinfo=timezone.utc)
DATASET_ID = "dataset-golden-oracle"
ACTOR_POLICY_VERSION = "SYNTHETIC_ACTOR_POLICY_V1"


class FailingSyntheticAudit(SQLiteTransactionalAudit):
    def stage(self, prepared: Any) -> None:
        raise sqlite3.OperationalError("synthetic validation audit outage")


def test_fr_092_ac_052_ground_truth_is_independent_and_persisted_append_only() -> None:
    oracle, repository, audit_repository, context, output = _setup()
    ignored_generator_validation = replace(output.validation, passed=False)

    ground_truth, validation = oracle.validate_and_record(
        actor_context=context,
        output=replace(output, validation=ignored_generator_validation),
    )

    assert ground_truth.ground_truth_version == GOLDEN_GROUND_TRUTH_VERSION
    assert ground_truth.expected_subject_count == output.requested_record_count
    assert ground_truth.expected_observation_count == output.requested_record_count
    assert ground_truth.expected_rule_result == "PASS"
    assert ground_truth.expected_severity == "NONE"
    assert ground_truth.expected_dataset_score is None
    assert ground_truth.expected_notification is False
    assert ground_truth.expected_escalation is False
    assert validation.status is SyntheticValidationStatus.PASS
    assert validation.reason_codes == ()
    assert validation.audit_reference == ground_truth.audit_reference
    events = audit_repository.list_events()
    assert len(events) == 2
    assert events[-1].action == "SYNTHETIC_GOLDEN_VALIDATION_RECORDED"
    assert events[-1].new_value_summary["score_tolerance_applied"] is False
    assert "canonical_payload" not in repr(events[-1])
    assert "random_seed" not in repr(events[-1])

    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        repository.connection.execute(
            "UPDATE synthetic_ground_truth SET expected_rule_result = 'FAIL'"
        )
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        repository.connection.execute("DELETE FROM synthetic_validation_results")


def test_fr_092_ac_052_structural_difference_is_blocked_not_technical_error() -> None:
    oracle, _, _, context, output = _setup(record_count=3)
    duplicate_subjects = (output.subjects[0], output.subjects[0], output.subjects[2])

    _, validation = oracle.validate_and_record(
        actor_context=context,
        output=replace(output, subjects=duplicate_subjects),
    )

    assert validation.status is SyntheticValidationStatus.BLOCKED
    assert "PRIMARY_KEY_VIOLATION" in validation.reason_codes
    assert "FOREIGN_KEY_VIOLATION" in validation.reason_codes
    assert validation.actual_primary_keys_unique is False


def test_fr_092_lineage_difference_is_recorded_without_changing_ground_truth() -> None:
    oracle, _, _, context, output = _setup()

    ground_truth, validation = oracle.validate_and_record(
        actor_context=context,
        output=replace(output, scenario_version="FORGED_SCENARIO_V2"),
    )

    assert ground_truth.scenario_version == "SCENARIO_V1"
    assert validation.status is SyntheticValidationStatus.BLOCKED
    assert validation.reason_codes == ("LINEAGE_MISMATCH",)


def test_fr_092_run_dataset_scope_cannot_be_forged_from_output() -> None:
    oracle, repository, audit_repository, _, output = _setup()
    forged_context = _context(dataset_ids=frozenset({"dataset-forged"}))

    with pytest.raises(SyntheticDataAuthorizationError, match="dataset scope"):
        oracle.validate_and_record(
            actor_context=forged_context,
            output=replace(output, dataset_id="dataset-forged"),
        )

    assert _table_count(repository, "synthetic_ground_truth") == 0
    assert _table_count(repository, "synthetic_validation_results") == 0
    assert len(audit_repository.list_events()) == 1


@pytest.mark.parametrize("context_case", ["missing", "wrong-role", "wrong-scope"])
def test_fr_092_uc_017_unauthorized_context_writes_no_ground_truth(
    context_case: str,
) -> None:
    oracle, repository, audit_repository, _, output = _setup()
    contexts = {
        "missing": None,
        "wrong-role": _context(roles={"VIEWER"}),
        "wrong-scope": _context(dataset_ids=frozenset()),
    }

    with pytest.raises(SyntheticDataAuthorizationError):
        oracle.validate_and_record(actor_context=contexts[context_case], output=output)

    assert _table_count(repository, "synthetic_ground_truth") == 0
    assert _table_count(repository, "synthetic_validation_results") == 0
    assert len(audit_repository.list_events()) == 1


def test_fr_092_same_run_and_oracle_version_cannot_replace_ground_truth() -> None:
    oracle, repository, audit_repository, context, output = _setup()
    oracle.validate_and_record(actor_context=context, output=output)

    with pytest.raises(SyntheticDataConflictError):
        oracle.validate_and_record(actor_context=context, output=output)

    assert _table_count(repository, "synthetic_ground_truth") == 1
    assert _table_count(repository, "synthetic_validation_results") == 1
    assert len(audit_repository.list_events()) == 2


def test_fr_092_audit_failure_rolls_back_ground_truth_and_validation() -> None:
    _, repository, audit_repository, context, output = _setup()
    failing_audit = FailingSyntheticAudit(
        repository.connection,
        AuditRedactor(build_default_redaction_policy()),
        audit_repository,
        policy_version="SYNTHETIC_AUDIT_OUTBOX_V1",
    )
    oracle = GoldenStructuralOracle(
        repository,
        transactional_audit=failing_audit,
        access_policy=_access_policy(),
        clock=lambda: NOW,
    )

    with pytest.raises(SyntheticDataTechnicalError, match="ground truth"):
        oracle.validate_and_record(actor_context=context, output=output)

    assert _table_count(repository, "synthetic_ground_truth") == 0
    assert _table_count(repository, "synthetic_validation_results") == 0
    assert len(audit_repository.list_events()) == 1


def test_fr_092_repository_outage_is_technical_not_validation_failure() -> None:
    oracle, repository, _, context, output = _setup()
    repository.connection.close()

    with pytest.raises(SyntheticDataTechnicalError, match="run could not be read"):
        oracle.validate_and_record(actor_context=context, output=output)


def _setup(
    *,
    record_count: int = 4,
) -> tuple[
    GoldenStructuralOracle,
    SQLiteSyntheticDataRepository,
    SQLiteAuditRepository,
    ActorContext,
    GoldenRelationalDataset,
]:
    repository = SQLiteSyntheticDataRepository()
    repository.add_policy(_policy())
    repository.add_scenario(_scenario())
    audit_repository = SQLiteAuditRepository()
    audit = SQLiteTransactionalAudit(
        repository.connection,
        AuditRedactor(build_default_redaction_policy()),
        audit_repository,
        policy_version="SYNTHETIC_AUDIT_OUTBOX_V1",
    )
    registry = SyntheticGenerationRegistryService(
        repository,
        transactional_audit=audit,
        access_policy=_access_policy(),
        clock=lambda: NOW,
    )
    context = _context()
    run = registry.request_run(
        actor_context=context,
        dataset_id=DATASET_ID,
        scenario_id="scenario-golden-oracle",
        scenario_version="SCENARIO_V1",
        generator_version=GOLDEN_GENERATOR_VERSION,
        configuration_version=GOLDEN_CONFIGURATION_VERSION,
        random_seed=20260721,
        requested_record_count=record_count,
    )
    output = GoldenRelationalGenerator(repository).generate(run.generation_run_id)
    oracle = GoldenStructuralOracle(
        repository,
        transactional_audit=audit,
        access_policy=_access_policy(),
        clock=lambda: NOW,
    )
    return oracle, repository, audit_repository, context, output


def _policy() -> SyntheticDatasetPolicy:
    return SyntheticDatasetPolicy(
        policy_id="policy-golden-oracle-v1",
        dataset_id=DATASET_ID,
        synthetic_generation_allowed=True,
        synthetic_profile=SyntheticProfile.GOLDEN,
        volume_profile="FUNCTIONAL_V1",
        distribution_profile="ARTIFICIAL_DISTRIBUTION_V1",
        missingness_profile="NO_MISSINGNESS_V1",
        defect_injection_profile="NO_DEFECTS_V1",
        privacy_profile=FULLY_ARTIFICIAL_PRIVACY_PROFILE,
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


def _scenario() -> SyntheticScenario:
    return SyntheticScenario(
        scenario_record_id="scenario-record-oracle-v1",
        scenario_id="scenario-golden-oracle",
        dataset_id=DATASET_ID,
        scenario_version="SCENARIO_V1",
        schema_version=GOLDEN_SCHEMA_VERSION,
        configuration_version=GOLDEN_CONFIGURATION_VERSION,
        synthetic_profile=SyntheticProfile.GOLDEN,
        volume_profile="FUNCTIONAL_V1",
        distribution_profile="ARTIFICIAL_DISTRIBUTION_V1",
        missingness_profile="NO_MISSINGNESS_V1",
        defect_injection_profile="NO_DEFECTS_V1",
        privacy_profile=FULLY_ARTIFICIAL_PRIVACY_PROFILE,
        created_at=NOW - timedelta(hours=1),
    )


def _access_policy() -> SyntheticRunAccessPolicy:
    return SyntheticRunAccessPolicy(
        version="SYNTHETIC_RUN_ACCESS_V1",
        actor_policy_version=ACTOR_POLICY_VERSION,
        requester_roles=frozenset({"SYNTHETIC_REQUESTER"}),
    )


def _context(
    *,
    roles: set[str] = {"SYNTHETIC_REQUESTER"},
    dataset_ids: frozenset[str] = frozenset({DATASET_ID}),
) -> ActorContext:
    return ActorContextIssuer().issue(
        actor_id="synthetic-oracle-user",
        actor_type=ActorType.USER,
        authentication_source="synthetic-identity-adapter",
        session_id="synthetic-session-sensitive",
        roles=frozenset(roles),
        permitted_source_ids=frozenset(),
        permitted_dataset_ids=dataset_ids,
        can_view_enterprise=False,
        privileged=False,
        issued_at=NOW - timedelta(minutes=5),
        expires_at=NOW + timedelta(hours=1),
        policy_version=ACTOR_POLICY_VERSION,
        correlation_id="correlation-synthetic-oracle",
    )


def _table_count(repository: SQLiteSyntheticDataRepository, table: str) -> int:
    row = repository.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
    assert row is not None
    return int(row[0])
