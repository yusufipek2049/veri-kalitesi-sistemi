from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import sqlite3
from typing import Any

import pytest

from veri_kalitesi.audit import (
    AuditEvent,
    AuditRedactor,
    PreparedAuditEvent,
    SQLiteAuditRepository,
    SQLiteTransactionalAudit,
    build_default_redaction_policy,
)
from veri_kalitesi.data_sources import Dataset
from veri_kalitesi.data_sources.models import Criticality
from veri_kalitesi.executions import (
    ExecutionStatus,
    MeasurementStatus,
    RuleExecution,
    RuleExecutionResult,
    SQLiteExecutionRepository,
)
from veri_kalitesi.identity import ActorContext, ActorContextIssuer, ActorType
from veri_kalitesi.rules import (
    QualityDimension,
    QualityRule,
    RuleCriticality,
    RuleStatus,
    RuleType,
    RuleVersion,
)
from veri_kalitesi.scoring import (
    DATASET_FORMULA_VERSION,
    DatasetPartialScorePolicy,
    DatasetPartialScorePolicyService,
    DIMENSION_FORMULA_VERSION,
    ENTERPRISE_FORMULA_VERSION,
    DEFAULT_THRESHOLD_SET,
    QualityScore,
    PartialExecutionFacts,
    PartialScorePolicyStatus,
    ScoreLevel,
    ScoreScopeType,
    FORMULA_VERSION,
    SOURCE_FORMULA_VERSION,
    ScoreStatus,
    ScoringApprovalPolicy,
    ScoringApprovalStatus,
    ScoringAuthorizationError,
    ScoringService,
    ScoringTechnicalError,
    ScoringConfigurationService,
    ScoringValidationError,
    SQLiteScoreRepository,
    SQLiteDatasetPartialScorePolicyRepository,
    ThresholdSet,
    calculate_rule_score,
    calculate_weighted_score,
    classify_score,
    default_dimension_weights,
    default_criticality_weights,
)


SCORING_ACTOR_POLICY_VERSION = "BANK_SCORING_ACTOR_POLICY_V1"


@dataclass
class FakeRuleCatalog:
    version: RuleVersion

    def get_version(self, rule_version_id: str) -> RuleVersion:
        assert rule_version_id == self.version.rule_version_id
        return self.version

    def get_rule(self, quality_rule_id: str) -> QualityRule:
        raise AssertionError(f"Unexpected rule lookup: {quality_rule_id}")


@dataclass
class FakeAggregateRuleCatalog:
    versions: dict[str, RuleVersion]
    rules: dict[str, QualityRule]

    def get_version(self, rule_version_id: str) -> RuleVersion:
        return self.versions[rule_version_id]

    def get_rule(self, quality_rule_id: str) -> QualityRule:
        return self.rules[quality_rule_id]


def _configuration_service(
    repository: SQLiteScoreRepository,
    *,
    audit_repository: Any | None = None,
    clock: Any | None = None,
) -> ScoringConfigurationService:
    transactional_audit = SQLiteTransactionalAudit(
        repository.connection,
        AuditRedactor(build_default_redaction_policy()),
        audit_repository or SQLiteAuditRepository(),
        policy_version="AUDIT_OUTBOX_TEST_V1",
    )
    kwargs: dict[str, Any] = {"transactional_audit": transactional_audit}
    kwargs["approval_policy"] = ScoringApprovalPolicy(
        version="SCORING_APPROVAL_POLICY_V1",
        actor_policy_version=SCORING_ACTOR_POLICY_VERSION,
        maker_roles=frozenset({"SCORING_MAKER"}),
        checker_roles=frozenset({"SCORING_CHECKER"}),
    )
    if clock is not None:
        kwargs["clock"] = clock
    return ScoringConfigurationService(repository, **kwargs)


def _create_and_approve_configuration(
    service: ScoringConfigurationService,
    *,
    version: str,
    threshold_set: ThresholdSet,
    dimension_weights: dict[QualityDimension, Decimal],
    criticality_weights: dict[Criticality, Decimal] | None = None,
    maker_id: str = "scoring-maker",
    checker_id: str = "scoring-checker",
    maker_correlation: str = "correlation-scoring-maker",
    checker_correlation: str = "correlation-scoring-checker",
) -> Any:
    now = service.clock()
    configuration, approval = service.create_and_submit(
        actor_context=_scoring_context(
            maker_id,
            {"SCORING_MAKER"},
            now=now,
            correlation_id=maker_correlation,
        ),
        version=version,
        threshold_set=threshold_set,
        dimension_weights=dimension_weights,
        criticality_weights=criticality_weights,
    )
    assert configuration.is_active is False
    active, decided = service.decide_configuration_approval(
        actor_context=_scoring_context(
            checker_id,
            {"SCORING_CHECKER"},
            now=now,
            correlation_id=checker_correlation,
        ),
        approval_id=approval.approval_id,
        decision="APPROVE",
        reason_code="SCORING.CONFIGURATION.REVIEWED",
    )
    assert decided.status is ScoringApprovalStatus.APPROVED
    return active


def _scoring_context(
    actor_id: str,
    roles: set[str],
    *,
    now: datetime,
    correlation_id: str | None = None,
    can_view_enterprise: bool = True,
    actor_type: ActorType = ActorType.USER,
    expires_at: datetime | None = None,
    privileged: bool = False,
) -> ActorContext:
    return ActorContextIssuer().issue(
        actor_id=actor_id,
        actor_type=actor_type,
        authentication_source="synthetic-identity-adapter",
        session_id=f"session-{actor_id}",
        roles=frozenset(roles),
        permitted_source_ids=frozenset(),
        permitted_dataset_ids=frozenset(),
        can_view_enterprise=can_view_enterprise,
        privileged=privileged,
        issued_at=now - timedelta(minutes=5),
        expires_at=expires_at or now + timedelta(hours=1),
        policy_version=SCORING_ACTOR_POLICY_VERSION,
        correlation_id=correlation_id or f"correlation-{actor_id}",
    )


def _configuration_audit_events(service: ScoringConfigurationService) -> list[AuditEvent]:
    repository = service.transactional_audit.repository
    assert isinstance(repository, SQLiteAuditRepository)
    return repository.list_events()


class FailingScoringAuditRepository:
    def append(self, prepared: PreparedAuditEvent) -> AuditEvent:
        raise sqlite3.OperationalError("synthetic audit outage")


class FailingScoringStageAudit(SQLiteTransactionalAudit):
    def stage(self, prepared: PreparedAuditEvent) -> None:
        raise sqlite3.OperationalError("synthetic outbox write failure")


@dataclass
class FakeSourceCatalog:
    datasets: dict[str, Dataset]

    def get_dataset(self, dataset_id: str) -> Dataset:
        return self.datasets[dataset_id]


def test_fr_047_uc_009_rule_score_uses_decimal_half_up_rounding() -> None:
    assert calculate_rule_score(100, 125) == Decimal("80.00")
    assert calculate_rule_score(2, 3) == Decimal("66.67")


def test_fr_046_fr_047_ac_009_successful_result_persists_explainable_score() -> None:
    service, score_repository, execution_repository, version = _service()
    execution = _execution(version)
    execution_repository.create_or_get(execution)
    completed = execution_repository.complete_success(
        execution.execution_id,
        (_result(execution, checked=125, passed=100, failed=25),),
        datetime(2026, 7, 16, 9, 5, tzinfo=timezone.utc),
    )

    scores = service.calculate_execution(completed.execution_id)

    assert len(scores) == 1
    score = scores[0]
    assert score.score_status is ScoreStatus.CALCULATED
    assert score.measurement_status is MeasurementStatus.FAILED
    assert score.score_value == Decimal("80.00")
    assert score.level is ScoreLevel.ACCEPTABLE
    assert score.rule_version_id == version.rule_version_id
    assert score.scope_id == version.quality_rule_id
    assert score.calculation_details["formula_version"] == FORMULA_VERSION
    assert score.calculation_details["counts"] == {
        "population": 125,
        "eligible": 125,
        "evaluated": 125,
        "passed": 100,
        "failed": 25,
        "excluded": 0,
        "technical_error": 0,
        "unknown": 0,
    }
    assert score.calculation_details["rates"] == {
        "passed": 80.0,
        "failed": 20.0,
    }
    assert score.calculation_details["included_in_official_aggregation"] is True
    assert score_repository.get(score.quality_score_id) == score


def test_fr_046_fr_047_ac_039_conditional_universe_uses_only_evaluated_denominator() -> None:
    service, score_repository, execution_repository, version = _service()
    execution = _execution(version)
    execution_repository.create_or_get(execution)
    execution_repository.complete_success(
        execution.execution_id,
        (
            RuleExecutionResult(
                execution_id=execution.execution_id,
                rule_version_id=version.rule_version_id,
                population_count=150,
                eligible_count=130,
                evaluated_count=125,
                passed_count=100,
                failed_count=25,
                excluded_count=15,
                technical_error_count=5,
                unknown_count=5,
                measurement_status=MeasurementStatus.WARNING,
            ),
        ),
        datetime(2026, 7, 16, 9, 5, tzinfo=timezone.utc),
    )

    score = service.calculate_execution(execution.execution_id)[0]

    assert score.score_value == Decimal("80.00")
    assert score.measurement_status is MeasurementStatus.WARNING
    assert score.calculation_details["formula"] == ("passed_count / evaluated_count * 100")
    assert score.calculation_details["counts"] == {
        "population": 150,
        "eligible": 130,
        "evaluated": 125,
        "passed": 100,
        "failed": 25,
        "excluded": 15,
        "technical_error": 5,
        "unknown": 5,
    }
    assert score_repository.get(score.quality_score_id).measurement_status is (
        MeasurementStatus.WARNING
    )


@pytest.mark.parametrize(
    ("measurement_status", "counts", "expected_score_status"),
    [
        (
            MeasurementStatus.NOT_APPLICABLE,
            (10, 0, 0, 0, 0, 10, 0, 0),
            ScoreStatus.NOT_CALCULATED,
        ),
        (
            MeasurementStatus.NOT_MEASURED,
            (0, 0, 0, 0, 0, 0, 0, 0),
            ScoreStatus.NOT_CALCULATED,
        ),
        (
            MeasurementStatus.NO_DATA,
            (0, 0, 0, 0, 0, 0, 0, 0),
            ScoreStatus.NO_DATA,
        ),
        (
            MeasurementStatus.TECHNICAL_ERROR,
            (1, 1, 0, 0, 0, 0, 1, 0),
            ScoreStatus.NOT_CALCULATED_TECHNICAL_ERROR,
        ),
        (
            MeasurementStatus.SUPPRESSED_BY_EXCEPTION,
            (10, 0, 0, 0, 0, 10, 0, 0),
            ScoreStatus.NOT_CALCULATED,
        ),
    ],
)
def test_fr_048_dq_scr_006_zero_denominator_statuses_never_produce_zero_score(
    measurement_status: MeasurementStatus,
    counts: tuple[int, int, int, int, int, int, int, int],
    expected_score_status: ScoreStatus,
) -> None:
    service, _, execution_repository, version = _service()
    execution = _execution(version)
    execution_repository.create_or_get(execution)
    execution_repository.complete_success(
        execution.execution_id,
        (
            RuleExecutionResult(
                execution_id=execution.execution_id,
                rule_version_id=version.rule_version_id,
                population_count=counts[0],
                eligible_count=counts[1],
                evaluated_count=counts[2],
                passed_count=counts[3],
                failed_count=counts[4],
                excluded_count=counts[5],
                technical_error_count=counts[6],
                unknown_count=counts[7],
                measurement_status=measurement_status,
            ),
        ),
        datetime(2026, 7, 16, 9, 5, tzinfo=timezone.utc),
    )

    score = service.calculate_execution(execution.execution_id)[0]

    assert score.score_value is None
    assert score.measurement_status is measurement_status
    assert score.score_status is expected_score_status
    assert score.calculation_details["excluded_reason"] == expected_score_status.value


def test_rule_011_repeated_scoring_is_idempotent_for_execution_and_version() -> None:
    service, score_repository, execution_repository, version = _service()
    execution = _execution(version)
    execution_repository.create_or_get(execution)
    execution_repository.complete_success(
        execution.execution_id,
        (_result(execution, checked=10, passed=9, failed=1),),
        datetime(2026, 7, 16, 9, 5, tzinfo=timezone.utc),
    )

    first = service.calculate_execution(execution.execution_id)
    repeated = service.calculate_execution(execution.execution_id)

    assert repeated == first
    assert score_repository.list_for_execution(execution.execution_id) == list(first)


def test_fr_048_ac_011_zero_records_produce_no_data_without_numeric_score() -> None:
    service, _, execution_repository, version = _service()
    execution = _execution(version)
    execution_repository.create_or_get(execution)
    execution_repository.complete_success(
        execution.execution_id,
        (_result(execution, checked=0, passed=0, failed=0),),
        datetime(2026, 7, 16, 9, 5, tzinfo=timezone.utc),
    )

    score = service.calculate_execution(execution.execution_id)[0]

    assert score.score_status is ScoreStatus.NO_DATA
    assert score.measurement_status is MeasurementStatus.NO_DATA
    assert score.score_value is None
    assert score.calculation_details["included_in_official_aggregation"] is False


@pytest.mark.parametrize(
    "execution_status",
    [ExecutionStatus.TECHNICAL_ERROR, ExecutionStatus.TIMEOUT],
)
def test_fr_048_rule_003_ac_010_technical_end_has_no_zero_score(
    execution_status: ExecutionStatus,
) -> None:
    service, _, execution_repository, version = _service()
    execution = _execution(version, status=execution_status)
    execution_repository.create_or_get(execution)

    score = service.calculate_execution(execution.execution_id)[0]

    assert score.score_status is ScoreStatus.NOT_CALCULATED_TECHNICAL_ERROR
    assert score.measurement_status is MeasurementStatus.TECHNICAL_ERROR
    assert score.score_value is None
    assert score.rule_result_id is None
    assert score.calculation_details["excluded_reason"] == ("NOT_CALCULATED_TECHNICAL_ERROR")


def test_fr_048_ac_012_partial_result_is_excluded_from_official_score() -> None:
    service, _, execution_repository, version = _service()
    execution = _execution(version)
    execution_repository.create_or_get(execution)
    result = _result(
        execution,
        checked=50,
        passed=45,
        failed=5,
        eligible_for_official_scoring=False,
        completed_partitions=("2026-01", "2026-02"),
    )
    execution_repository.complete_timeout(
        execution.execution_id,
        "QUERY_TIMEOUT",
        (result,),
        datetime(2026, 7, 16, 9, 5, tzinfo=timezone.utc),
    )

    score = service.calculate_execution(execution.execution_id)[0]

    assert score.score_status is ScoreStatus.PARTIAL
    assert score.score_value is None
    assert score.calculation_details["completed_partitions"] == ("2026-01", "2026-02")
    assert score.calculation_details["included_in_official_aggregation"] is False


def test_fr_048_fr_049_fr_050_official_partial_score_propagates_to_all_aggregates() -> None:
    service, _, execution_repository, versions, _ = _source_service()
    policy_repository = SQLiteDatasetPartialScorePolicyRepository()
    for dataset_id, rule_id in (
        ("dataset-high", "source-rule-1"),
        ("dataset-low", "source-rule-2"),
    ):
        policy_repository.save(_partial_policy(dataset_id, rule_id))
    service.partial_score_policy_service = DatasetPartialScorePolicyService(policy_repository)
    execution = _source_execution(versions)
    execution_repository.create_or_get(execution)
    execution_repository.complete_timeout(
        execution.execution_id,
        "QUERY_TIMEOUT",
        tuple(
            _version_result(execution, version, checked=10, passed=9, failed=1)
            for version in versions
        ),
        datetime(2026, 7, 16, 12, 5, tzinfo=timezone.utc),
    )
    facts = {
        dataset_id: _partial_facts(dataset_id, rule_id)
        for dataset_id, rule_id in (
            ("dataset-high", "source-rule-1"),
            ("dataset-low", "source-rule-2"),
        )
    }

    rule_scores = service.calculate_execution(
        execution.execution_id,
        partial_facts_by_dataset=facts,
    )
    dataset_scores = tuple(
        service.calculate_dataset_score(execution.execution_id, dataset_id)
        for dataset_id in ("dataset-high", "dataset-low")
    )
    dimension_score = service.calculate_dimension_score(
        execution.execution_id,
        QualityDimension.COMPLETENESS,
    )
    source_score = service.calculate_source_score(execution.execution_id, "source-main")
    enterprise_score = service.calculate_enterprise_score(execution.execution_id)

    assert all(score.score_status is ScoreStatus.PARTIAL for score in rule_scores)
    assert all(score.score_value == Decimal("90.00") for score in rule_scores)
    assert all(
        score.calculation_details["included_in_official_aggregation"] is True
        for score in rule_scores
    )
    assert rule_scores[0].calculation_details["score_eligibility"] == "OFFICIAL"
    assert rule_scores[0].calculation_details["coverage_ratio"] == "1"
    assert rule_scores[0].calculation_details["working_rule_count"] == 1
    assert rule_scores[0].calculation_details["non_working_rule_count"] == 0
    assert rule_scores[0].calculation_details["missing_partitions"] == ()
    assert rule_scores[0].calculation_details["partial_score_policy_version"] == (
        "DATASET_PARTIAL_V1"
    )
    assert rule_scores[0].calculation_details["eligibility_reason_codes"] == (
        "ALL_POLICY_CONDITIONS_MET",
    )
    assert all(score.score_status is ScoreStatus.PARTIAL for score in dataset_scores)
    assert all(score.score_value == Decimal("90.00") for score in dataset_scores)
    assert dimension_score.score_status is ScoreStatus.PARTIAL
    assert dimension_score.score_value == Decimal("90.00")
    assert source_score.score_status is ScoreStatus.PARTIAL
    assert source_score.score_value == Decimal("90.00")
    assert enterprise_score.score_status is ScoreStatus.PARTIAL
    assert enterprise_score.score_value == Decimal("90.00")
    assert enterprise_score.calculation_details["included_in_official_aggregation"] is True


def test_fr_048_missing_policy_keeps_partial_result_provisional() -> None:
    service, score_repository, execution_repository, versions = _aggregate_service(weights=(1, 1))
    service.partial_score_policy_service = DatasetPartialScorePolicyService(
        SQLiteDatasetPartialScorePolicyRepository()
    )
    execution = _aggregate_execution(versions)
    execution_repository.create_or_get(execution)
    execution_repository.complete_timeout(
        execution.execution_id,
        "QUERY_TIMEOUT",
        (_version_result(execution, versions[0], checked=10, passed=9, failed=1),),
        datetime(2026, 7, 16, 10, 5, tzinfo=timezone.utc),
    )

    scores = service.calculate_execution(
        execution.execution_id,
        partial_facts_by_dataset={
            "dataset-main": _partial_facts("dataset-main", "rule-1", total_rule_count=2)
        },
    )

    assert scores[0].score_status is ScoreStatus.PARTIAL
    assert scores[0].score_value is None
    assert scores[0].calculation_details["score_eligibility"] == "PROVISIONAL"
    assert scores[0].calculation_details["eligibility_reason_codes"] == ("POLICY_NOT_FOUND",)
    assert all(
        score.score_value is None
        for score in score_repository.list_for_execution(execution.execution_id)
    )


def test_fr_048_partial_policy_storage_failure_writes_no_scores() -> None:
    service, score_repository, execution_repository, versions = _aggregate_service(weights=(1, 1))
    policy_repository = SQLiteDatasetPartialScorePolicyRepository()
    policy_repository.connection.close()
    service.partial_score_policy_service = DatasetPartialScorePolicyService(policy_repository)
    execution = _aggregate_execution(versions)
    execution_repository.create_or_get(execution)
    execution_repository.complete_timeout(
        execution.execution_id,
        "QUERY_TIMEOUT",
        (_version_result(execution, versions[0], checked=10, passed=9, failed=1),),
        datetime(2026, 7, 16, 10, 5, tzinfo=timezone.utc),
    )

    with pytest.raises(ScoringTechnicalError):
        service.calculate_execution(
            execution.execution_id,
            partial_facts_by_dataset={
                "dataset-main": _partial_facts("dataset-main", "rule-1", total_rule_count=2)
            },
        )

    assert score_repository.list_for_execution(execution.execution_id) == []


def test_fr_046_rule_004_inconsistent_counts_are_rejected_without_score() -> None:
    service, score_repository, execution_repository, version = _service()
    execution = _execution(version)
    execution_repository.create_or_get(execution)
    execution_repository.complete_success(
        execution.execution_id,
        (_result(execution, checked=10, passed=8, failed=1),),
        datetime(2026, 7, 16, 9, 5, tzinfo=timezone.utc),
    )

    with pytest.raises(ScoringValidationError, match="inconsistent"):
        service.calculate_execution(execution.execution_id)

    assert score_repository.list_for_execution(execution.execution_id) == []


def test_fr_046_ac_039_unknown_technical_counter_remains_null_and_is_not_scored() -> None:
    service, score_repository, execution_repository, version = _service()
    execution = _execution(version)
    execution_repository.create_or_get(execution)
    execution_repository.complete_success(
        execution.execution_id,
        (
            RuleExecutionResult(
                execution_id=execution.execution_id,
                rule_version_id=version.rule_version_id,
                population_count=125,
                eligible_count=125,
                evaluated_count=125,
                passed_count=100,
                failed_count=25,
                excluded_count=0,
                technical_error_count=None,
                unknown_count=0,
                measurement_status=MeasurementStatus.FAILED,
            ),
        ),
        datetime(2026, 7, 16, 9, 5, tzinfo=timezone.utc),
    )

    stored = execution_repository.list_results(execution.execution_id)[0]

    assert stored.technical_error_count is None
    with pytest.raises(ScoringValidationError, match="non-negative integers"):
        service.calculate_execution(execution.execution_id)
    assert score_repository.list_for_execution(execution.execution_id) == []


def test_fr_049_uc_009_ac_013_weighted_dataset_score_is_explainable() -> None:
    service, score_repository, execution_repository, versions = _aggregate_service(weights=(2, 1))
    execution = _aggregate_execution(versions)
    execution_repository.create_or_get(execution)
    execution_repository.complete_success(
        execution.execution_id,
        (
            _version_result(execution, versions[0], checked=10, passed=8, failed=2),
            _version_result(execution, versions[1], checked=10, passed=10, failed=0),
        ),
        datetime(2026, 7, 16, 10, 5, tzinfo=timezone.utc),
    )
    service.calculate_execution(execution.execution_id)

    dataset_score = service.calculate_dataset_score(execution.execution_id, "dataset-main")

    assert dataset_score.scope_type is ScoreScopeType.DATASET
    assert dataset_score.rule_version_id is None
    assert dataset_score.score_status is ScoreStatus.CALCULATED
    assert dataset_score.score_value == Decimal("86.67")
    assert dataset_score.level is ScoreLevel.ACCEPTABLE
    assert dataset_score.calculation_details["formula_version"] == (DATASET_FORMULA_VERSION)
    assert dataset_score.calculation_details["weight_sum"] == "3"
    assert [
        item["weight"] for item in dataset_score.calculation_details["included_components"]
    ] == ["2", "1"]
    assert dataset_score.calculation_details["excluded_components"] == ()
    assert score_repository.get(dataset_score.quality_score_id) == dataset_score


def test_fr_049_rule_004_uncalculated_child_is_excluded_from_denominator() -> None:
    service, _, execution_repository, versions = _aggregate_service(weights=(2, 1))
    execution = _aggregate_execution(versions)
    execution_repository.create_or_get(execution)
    execution_repository.complete_success(
        execution.execution_id,
        (
            _version_result(execution, versions[0], checked=0, passed=0, failed=0),
            _version_result(execution, versions[1], checked=10, passed=10, failed=0),
        ),
        datetime(2026, 7, 16, 10, 5, tzinfo=timezone.utc),
    )
    service.calculate_execution(execution.execution_id)

    dataset_score = service.calculate_dataset_score(execution.execution_id, "dataset-main")

    assert dataset_score.score_value == Decimal("100.00")
    assert dataset_score.calculation_details["weight_sum"] == "1"
    excluded = dataset_score.calculation_details["excluded_components"]
    assert len(excluded) == 1
    assert excluded[0]["status"] == "NO_DATA"


def test_fr_049_rule_004_all_no_data_children_produce_no_numeric_dataset_score() -> None:
    service, _, execution_repository, versions = _aggregate_service(weights=(2, 1))
    execution = _aggregate_execution(versions)
    execution_repository.create_or_get(execution)
    execution_repository.complete_success(
        execution.execution_id,
        tuple(
            _version_result(execution, version, checked=0, passed=0, failed=0)
            for version in versions
        ),
        datetime(2026, 7, 16, 10, 5, tzinfo=timezone.utc),
    )
    service.calculate_execution(execution.execution_id)

    dataset_score = service.calculate_dataset_score(execution.execution_id, "dataset-main")

    assert dataset_score.score_status is ScoreStatus.NO_DATA
    assert dataset_score.score_value is None
    assert dataset_score.level is None


def test_fr_049_rule_005_zero_weight_produces_config_error_without_score() -> None:
    service, _, execution_repository, versions = _aggregate_service(weights=(0, 1))
    execution = _aggregate_execution(versions)
    execution_repository.create_or_get(execution)
    execution_repository.complete_success(
        execution.execution_id,
        tuple(
            _version_result(execution, version, checked=10, passed=8, failed=2)
            for version in versions
        ),
        datetime(2026, 7, 16, 10, 5, tzinfo=timezone.utc),
    )
    service.calculate_execution(execution.execution_id)

    dataset_score = service.calculate_dataset_score(execution.execution_id, "dataset-main")

    assert dataset_score.score_status is ScoreStatus.CONFIG_ERROR
    assert dataset_score.score_value is None
    assert dataset_score.calculation_details["invalid_weight_rule_versions"] == ("version-1",)


def test_fr_051_ac_014_default_levels_cover_boundaries_without_gaps() -> None:
    thresholds = ThresholdSet(version="thresholds-v1")

    assert classify_score(Decimal("0.00"), thresholds) is ScoreLevel.CRITICAL
    assert classify_score(Decimal("49.99"), thresholds) is ScoreLevel.CRITICAL
    assert classify_score(Decimal("50.00"), thresholds) is ScoreLevel.RISKY
    assert classify_score(Decimal("75.00"), thresholds) is ScoreLevel.ACCEPTABLE
    assert classify_score(Decimal("80.00"), thresholds) is ScoreLevel.ACCEPTABLE
    assert classify_score(Decimal("90.00"), thresholds) is ScoreLevel.GOOD
    assert classify_score(Decimal("100.00"), thresholds) is ScoreLevel.GOOD

    with pytest.raises(ScoringValidationError, match="without gaps or overlaps"):
        _aggregate_service(
            weights=(1, 1),
            threshold_set=ThresholdSet(
                version="invalid",
                critical_upper_exclusive=Decimal("75"),
                risky_upper_exclusive=Decimal("50"),
            ),
        )


def test_fr_049_weighted_formula_rejects_empty_or_invalid_components() -> None:
    assert calculate_weighted_score(
        ((Decimal("80"), Decimal("2")), (Decimal("100"), Decimal("1")))
    ) == Decimal("86.67")
    with pytest.raises(ScoringValidationError, match="At least one"):
        calculate_weighted_score(())
    with pytest.raises(ScoringValidationError, match="outside allowed"):
        calculate_weighted_score(((Decimal("80"), Decimal("0")),))


def test_score_repository_migrates_rule_only_schema_for_dataset_scores(
    tmp_path: Any,
) -> None:
    database = tmp_path / "old-scores.sqlite"
    connection = sqlite3.connect(database)
    connection.execute(
        """
        CREATE TABLE quality_scores (
            quality_score_id TEXT PRIMARY KEY,
            execution_id TEXT NOT NULL,
            rule_result_id TEXT,
            rule_version_id TEXT NOT NULL,
            scope_type TEXT NOT NULL,
            scope_id TEXT NOT NULL,
            score_value TEXT,
            score_status TEXT NOT NULL,
            calculation_details TEXT NOT NULL,
            calculated_at TEXT NOT NULL,
            UNIQUE (execution_id, rule_version_id)
        )
        """
    )
    connection.execute(
        """
        INSERT INTO quality_scores VALUES (
            'score-old', 'execution-old', 'result-old', 'version-old',
            'RULE', 'rule-old', '80.00', 'CALCULATED', '{}',
            '2026-07-16T10:00:00+00:00'
        )
        """
    )
    connection.commit()
    connection.close()

    repository = SQLiteScoreRepository(str(database))
    columns = {
        row["name"]: row
        for row in repository.connection.execute("PRAGMA table_info(quality_scores)").fetchall()
    }

    assert columns["rule_version_id"]["notnull"] == 0
    assert columns["scope_id"]["notnull"] == 0
    assert "level" in columns
    assert repository.get("score-old").score_value == Decimal("80.00")
    assert repository.get_active_configuration().version == "DEFAULT_SCORING_V1"
    enterprise = QualityScore(
        execution_id="execution-old",
        rule_version_id=None,
        scope_type=ScoreScopeType.ENTERPRISE,
        scope_id=None,
        score_value=Decimal("80.00"),
        score_status=ScoreStatus.CALCULATED,
        calculation_details={"formula_version": ENTERPRISE_FORMULA_VERSION},
    )
    first, created = repository.add_or_get(enterprise)
    repeated, repeated_created = repository.add_or_get(enterprise)
    assert created is True
    assert repeated_created is False
    assert repeated == first


def test_fr_051_bfr_sod_001_002_scoring_configuration_requires_separate_checker() -> None:
    repository = SQLiteScoreRepository()
    now = repository.get_active_configuration().created_at.replace(year=2027)
    service = _configuration_service(repository, clock=lambda: now)
    weights = default_dimension_weights()
    weights[QualityDimension.COMPLETENESS] = Decimal("2.5")

    configuration, approval = service.create_and_submit(
        actor_context=_scoring_context(
            "scoring-maker",
            {"SCORING_MAKER"},
            now=now,
            correlation_id="correlation-scoring-request",
        ),
        version="SCORING_V2",
        threshold_set=ThresholdSet(
            version="THRESHOLDS_V2",
            critical_upper_exclusive=Decimal("40"),
            risky_upper_exclusive=Decimal("70"),
            acceptable_upper_exclusive=Decimal("85"),
        ),
        dimension_weights=weights,
    )
    assert configuration.is_active is False
    assert repository.get_active_configuration().version == "DEFAULT_SCORING_V1"

    active, decided = service.decide_configuration_approval(
        actor_context=_scoring_context(
            "scoring-checker",
            {"SCORING_CHECKER"},
            now=now,
            correlation_id="correlation-scoring-decision",
        ),
        approval_id=approval.approval_id,
        decision="APPROVE",
        reason_code="SCORING.CONFIGURATION.REVIEWED",
    )

    configurations = repository.list_configurations()
    assert decided.status is ScoringApprovalStatus.APPROVED
    assert decided.maker_actor_id == "scoring-maker"
    assert decided.checker_actor_id == "scoring-checker"
    assert active.is_active is True
    assert active.activated_at == now
    assert repository.get_active_configuration() == active
    assert [item.version for item in configurations] == [
        "DEFAULT_SCORING_V1",
        "SCORING_V2",
    ]
    assert [item.is_active for item in configurations] == [False, True]
    audits = _configuration_audit_events(service)
    assert [audit.action for audit in audits] == [
        "SCORING_CONFIGURATION_APPROVAL_REQUESTED",
        "SCORING_CONFIGURATION_APPROVAL_DECIDED",
    ]
    assert audits[0].correlation_id == "correlation-scoring-request"
    assert audits[1].correlation_id == "correlation-scoring-decision"
    assert audits[1].old_value_summary["version"] == "DEFAULT_SCORING_V1"
    assert audits[1].new_value_summary["version"] == "SCORING_V2"
    assert audits[1].new_value_summary["dimension_completeness_weight"] == "2.5"
    assert audits[1].new_value_summary["critical_upper_exclusive"] == "40"
    assert audits[1].new_value_summary["status"] == "APPROVED"
    assert "SCORING.CONFIGURATION.REVIEWED" not in str(audits)
    assert audits[1].session_id_digest is not None
    assert service.transactional_audit.list_pending() == []


def test_fr_077_bfr_aud_004_scoring_activation_is_buffered_on_audit_outage() -> None:
    repository = SQLiteScoreRepository()
    service = _configuration_service(
        repository,
        audit_repository=FailingScoringAuditRepository(),
    )

    active = _create_and_approve_configuration(
        service,
        version="SCORING_BUFFERED_V2",
        threshold_set=DEFAULT_THRESHOLD_SET,
        dimension_weights=default_dimension_weights(),
        maker_correlation="correlation-buffered-scoring-request",
        checker_correlation="correlation-buffered-scoring-decision",
    )

    pending = service.transactional_audit.list_pending()
    assert repository.get_active_configuration() == active
    assert len(pending) == 2
    assert [event.action for event in pending] == [
        "SCORING_CONFIGURATION_APPROVAL_REQUESTED",
        "SCORING_CONFIGURATION_APPROVAL_DECIDED",
    ]
    assert pending[-1].correlation_id == "correlation-buffered-scoring-decision"
    assert pending[-1].new_value_summary["version"] == "SCORING_BUFFERED_V2"


def test_bfr_aud_004_outbox_failure_rolls_back_scoring_activation() -> None:
    repository = SQLiteScoreRepository()
    central_repository = SQLiteAuditRepository()
    service = _configuration_service(repository)
    now = service.clock()
    _, approval = service.create_and_submit(
        actor_context=_scoring_context("scoring-maker", {"SCORING_MAKER"}, now=now),
        version="SCORING_ATOMIC_V2",
        threshold_set=DEFAULT_THRESHOLD_SET,
        dimension_weights=default_dimension_weights(),
    )
    service.transactional_audit = FailingScoringStageAudit(
        repository.connection,
        AuditRedactor(build_default_redaction_policy()),
        central_repository,
        policy_version="AUDIT_OUTBOX_TEST_V1",
    )

    with pytest.raises(sqlite3.OperationalError, match="outbox write failure"):
        service.decide_configuration_approval(
            actor_context=_scoring_context("scoring-checker", {"SCORING_CHECKER"}, now=now),
            approval_id=approval.approval_id,
            decision="APPROVE",
            reason_code="SCORING.CONFIGURATION.REVIEWED",
        )

    assert repository.get_active_configuration().version == "DEFAULT_SCORING_V1"
    assert [item.version for item in repository.list_configurations()] == [
        "DEFAULT_SCORING_V1",
        "SCORING_ATOMIC_V2",
    ]
    assert repository.get_configuration_approval(approval.approval_id).status is (
        ScoringApprovalStatus.PENDING
    )
    assert central_repository.list_events() == []


def test_br_rule_001_scoring_configuration_rejects_missing_trusted_context() -> None:
    repository = SQLiteScoreRepository()
    service = _configuration_service(repository)

    with pytest.raises(ScoringAuthorizationError, match="Trusted actor context"):
        service.create_and_submit(
            actor_context=None,
            version="SCORING_NO_CORRELATION_V2",
            threshold_set=DEFAULT_THRESHOLD_SET,
            dimension_weights=default_dimension_weights(),
        )

    assert repository.get_active_configuration().version == "DEFAULT_SCORING_V1"


@pytest.mark.parametrize(
    ("actor_type", "roles", "can_view_enterprise", "privileged", "expired"),
    [
        (ActorType.USER, {"SCORING_MAKER"}, True, False, True),
        (ActorType.USER, {"DATA_VIEWER"}, True, True, False),
        (ActorType.USER, {"SCORING_MAKER"}, False, False, False),
        (ActorType.SERVICE, {"SCORING_MAKER"}, True, False, False),
    ],
    ids=("expired", "privileged-without-role", "outside-scope", "service-account"),
)
def test_br_rule_001_bfr_sod_003_unauthorized_maker_cannot_submit_configuration(
    actor_type: ActorType,
    roles: set[str],
    can_view_enterprise: bool,
    privileged: bool,
    expired: bool,
) -> None:
    repository = SQLiteScoreRepository()
    service = _configuration_service(repository)
    now = service.clock()
    context = _scoring_context(
        "unauthorized-maker",
        roles,
        now=now,
        actor_type=actor_type,
        can_view_enterprise=can_view_enterprise,
        privileged=privileged,
        expires_at=now - timedelta(seconds=1) if expired else None,
    )

    with pytest.raises(ScoringAuthorizationError):
        service.create_and_submit(
            actor_context=context,
            version="SCORING_UNAUTHORIZED_V2",
            threshold_set=DEFAULT_THRESHOLD_SET,
            dimension_weights=default_dimension_weights(),
        )

    assert repository.get_active_configuration().version == "DEFAULT_SCORING_V1"
    assert repository.list_configurations() == [repository.get_active_configuration()]


def test_bfr_sod_001_maker_cannot_decide_own_scoring_configuration() -> None:
    repository = SQLiteScoreRepository()
    service = _configuration_service(repository)
    now = service.clock()
    _, approval = service.create_and_submit(
        actor_context=_scoring_context(
            "dual-role-actor",
            {"SCORING_MAKER", "SCORING_CHECKER"},
            now=now,
        ),
        version="SCORING_SELF_APPROVAL_V2",
        threshold_set=DEFAULT_THRESHOLD_SET,
        dimension_weights=default_dimension_weights(),
    )

    with pytest.raises(ScoringAuthorizationError, match="Maker cannot"):
        service.decide_configuration_approval(
            actor_context=_scoring_context(
                "dual-role-actor",
                {"SCORING_MAKER", "SCORING_CHECKER"},
                now=now,
            ),
            approval_id=approval.approval_id,
            decision="APPROVE",
            reason_code="SCORING.CONFIGURATION.REVIEWED",
        )

    assert repository.get_configuration_approval(approval.approval_id).status is (
        ScoringApprovalStatus.PENDING
    )
    assert repository.get_active_configuration().version == "DEFAULT_SCORING_V1"


@pytest.mark.parametrize(
    ("actor_type", "roles", "can_view_enterprise", "privileged", "expired"),
    [
        (ActorType.USER, {"SCORING_CHECKER"}, True, False, True),
        (ActorType.USER, {"DATA_VIEWER"}, True, True, False),
        (ActorType.USER, {"SCORING_CHECKER"}, False, False, False),
        (ActorType.SERVICE, {"SCORING_CHECKER"}, True, False, False),
    ],
    ids=("expired", "privileged-without-role", "outside-scope", "service-account"),
)
def test_br_rule_001_bfr_sod_003_unauthorized_checker_cannot_decide_configuration(
    actor_type: ActorType,
    roles: set[str],
    can_view_enterprise: bool,
    privileged: bool,
    expired: bool,
) -> None:
    repository = SQLiteScoreRepository()
    service = _configuration_service(repository)
    now = service.clock()
    _, approval = service.create_and_submit(
        actor_context=_scoring_context("scoring-maker", {"SCORING_MAKER"}, now=now),
        version="SCORING_UNAUTHORIZED_CHECKER_V2",
        threshold_set=DEFAULT_THRESHOLD_SET,
        dimension_weights=default_dimension_weights(),
    )
    context = _scoring_context(
        "unauthorized-checker",
        roles,
        now=now,
        actor_type=actor_type,
        can_view_enterprise=can_view_enterprise,
        privileged=privileged,
        expires_at=now - timedelta(seconds=1) if expired else None,
    )

    with pytest.raises(ScoringAuthorizationError):
        service.decide_configuration_approval(
            actor_context=context,
            approval_id=approval.approval_id,
            decision="APPROVE",
            reason_code="SCORING.CONFIGURATION.REVIEWED",
        )

    assert repository.get_configuration_approval(approval.approval_id).status is (
        ScoringApprovalStatus.PENDING
    )
    assert repository.get_active_configuration().version == "DEFAULT_SCORING_V1"


def test_bfr_sod_002_rejected_scoring_configuration_remains_inactive() -> None:
    repository = SQLiteScoreRepository()
    service = _configuration_service(repository)
    now = service.clock()
    configuration, approval = service.create_and_submit(
        actor_context=_scoring_context("scoring-maker", {"SCORING_MAKER"}, now=now),
        version="SCORING_REJECTED_V2",
        threshold_set=DEFAULT_THRESHOLD_SET,
        dimension_weights=default_dimension_weights(),
    )

    rejected_configuration, rejected = service.decide_configuration_approval(
        actor_context=_scoring_context("scoring-checker", {"SCORING_CHECKER"}, now=now),
        approval_id=approval.approval_id,
        decision="REJECT",
        reason_code="SCORING.CONFIGURATION.REJECTED",
    )

    assert rejected.status is ScoringApprovalStatus.REJECTED
    assert rejected.checker_actor_id == "scoring-checker"
    assert rejected_configuration.configuration_id == configuration.configuration_id
    assert rejected_configuration.is_active is False
    assert repository.get_active_configuration().version == "DEFAULT_SCORING_V1"
    audit = _configuration_audit_events(service)[-1]
    assert audit.new_value_summary["status"] == "REJECTED"
    assert "SCORING.CONFIGURATION.REJECTED" not in str(audit)


def test_bfr_sod_002_stale_scoring_configuration_cannot_be_approved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = SQLiteScoreRepository()
    service = _configuration_service(repository)
    now = service.clock()
    _, stale_approval = service.create_and_submit(
        actor_context=_scoring_context("scoring-maker", {"SCORING_MAKER"}, now=now),
        version="SCORING_STALE_V2",
        threshold_set=DEFAULT_THRESHOLD_SET,
        dimension_weights=default_dimension_weights(),
    )
    service.create_and_submit(
        actor_context=_scoring_context("scoring-maker", {"SCORING_MAKER"}, now=now),
        version="SCORING_LATEST_V3",
        threshold_set=DEFAULT_THRESHOLD_SET,
        dimension_weights=default_dimension_weights(),
    )
    monkeypatch.setattr(
        repository,
        "get_latest_configuration",
        lambda: repository.get_configuration("SCORING_STALE_V2"),
    )

    with pytest.raises(ScoringValidationError, match="latest"):
        service.decide_configuration_approval(
            actor_context=_scoring_context("scoring-checker", {"SCORING_CHECKER"}, now=now),
            approval_id=stale_approval.approval_id,
            decision="APPROVE",
            reason_code="SCORING.CONFIGURATION.REVIEWED",
        )

    assert repository.get_configuration_approval(stale_approval.approval_id).status is (
        ScoringApprovalStatus.PENDING
    )
    assert repository.get_active_configuration().version == "DEFAULT_SCORING_V1"


def test_bfr_aud_004_outbox_failure_rolls_back_scoring_submission() -> None:
    repository = SQLiteScoreRepository()
    service = _configuration_service(repository)
    service.transactional_audit = FailingScoringStageAudit(
        repository.connection,
        AuditRedactor(build_default_redaction_policy()),
        SQLiteAuditRepository(),
        policy_version="AUDIT_OUTBOX_TEST_V1",
    )
    now = service.clock()

    with pytest.raises(sqlite3.OperationalError, match="outbox write failure"):
        service.create_and_submit(
            actor_context=_scoring_context("scoring-maker", {"SCORING_MAKER"}, now=now),
            version="SCORING_ATOMIC_REQUEST_V2",
            threshold_set=DEFAULT_THRESHOLD_SET,
            dimension_weights=default_dimension_weights(),
        )

    assert [item.version for item in repository.list_configurations()] == ["DEFAULT_SCORING_V1"]


def test_fr_051_rule_005_invalid_or_duplicate_configuration_keeps_active_version() -> None:
    repository = SQLiteScoreRepository()
    service = _configuration_service(repository)
    weights = default_dimension_weights()
    _create_and_approve_configuration(
        service,
        version="SCORING_V2",
        threshold_set=DEFAULT_THRESHOLD_SET,
        dimension_weights=weights,
    )
    now = service.clock()

    with pytest.raises(ScoringValidationError, match="every quality dimension"):
        service.create_and_submit(
            actor_context=_scoring_context("scoring-maker", {"SCORING_MAKER"}, now=now),
            version="SCORING_V3",
            threshold_set=DEFAULT_THRESHOLD_SET,
            dimension_weights={QualityDimension.COMPLETENESS: Decimal("1")},
        )
    with pytest.raises(ScoringValidationError, match="version must be unique"):
        service.create_and_submit(
            actor_context=_scoring_context("scoring-maker", {"SCORING_MAKER"}, now=now),
            version="SCORING_V2",
            threshold_set=DEFAULT_THRESHOLD_SET,
            dimension_weights=weights,
        )

    assert repository.get_active_configuration().version == "SCORING_V2"
    assert len(repository.list_configurations()) == 2


def test_fr_051_rule_007_new_configuration_does_not_rewrite_past_scores() -> None:
    service, score_repository, execution_repository, versions = _aggregate_service(weights=(1, 1))
    first_execution = _aggregate_execution(versions, execution_id="execution-before")
    execution_repository.create_or_get(first_execution)
    execution_repository.complete_success(
        first_execution.execution_id,
        tuple(
            _version_result(first_execution, version, checked=10, passed=8, failed=2)
            for version in versions
        ),
        datetime(2026, 7, 16, 11, 5, tzinfo=timezone.utc),
    )
    first_scores = service.calculate_execution(first_execution.execution_id)

    _create_and_approve_configuration(
        _configuration_service(score_repository),
        version="SCORING_V2",
        threshold_set=ThresholdSet(
            version="THRESHOLDS_V2",
            critical_upper_exclusive=Decimal("40"),
            risky_upper_exclusive=Decimal("60"),
            acceptable_upper_exclusive=Decimal("80"),
        ),
        dimension_weights=default_dimension_weights(),
    )
    second_execution = _aggregate_execution(versions, execution_id="execution-after")
    execution_repository.create_or_get(second_execution)
    execution_repository.complete_success(
        second_execution.execution_id,
        tuple(
            _version_result(second_execution, version, checked=10, passed=8, failed=2)
            for version in versions
        ),
        datetime(2026, 7, 16, 11, 15, tzinfo=timezone.utc),
    )
    second_scores = service.calculate_execution(second_execution.execution_id)

    assert all(score.level is ScoreLevel.ACCEPTABLE for score in first_scores)
    assert all(
        score.calculation_details["configuration_version"] == "DEFAULT_SCORING_V1"
        for score in first_scores
    )
    assert all(score.level is ScoreLevel.GOOD for score in second_scores)
    assert all(
        score.calculation_details["configuration_version"] == "SCORING_V2"
        for score in second_scores
    )
    assert score_repository.list_for_execution(first_execution.execution_id) == list(first_scores)


def test_fr_050_uc_009_dimension_score_groups_rules_and_explains_components() -> None:
    service, score_repository, execution_repository, versions = _aggregate_service(weights=(2, 1))
    config_weights = default_dimension_weights()
    config_weights[QualityDimension.COMPLETENESS] = Decimal("3")
    _create_and_approve_configuration(
        _configuration_service(score_repository),
        version="SCORING_DIMENSION_V1",
        threshold_set=DEFAULT_THRESHOLD_SET,
        dimension_weights=config_weights,
    )
    execution = _aggregate_execution(versions)
    execution_repository.create_or_get(execution)
    execution_repository.complete_success(
        execution.execution_id,
        (
            _version_result(execution, versions[0], checked=10, passed=8, failed=2),
            _version_result(execution, versions[1], checked=10, passed=10, failed=0),
        ),
        datetime(2026, 7, 16, 11, 5, tzinfo=timezone.utc),
    )
    service.calculate_execution(execution.execution_id)

    score = service.calculate_dimension_score(execution.execution_id, QualityDimension.COMPLETENESS)

    assert score.scope_type is ScoreScopeType.DIMENSION
    assert score.scope_id == "COMPLETENESS"
    assert score.score_value == Decimal("86.67")
    assert score.level is ScoreLevel.ACCEPTABLE
    assert score.calculation_details["formula_version"] == DIMENSION_FORMULA_VERSION
    assert score.calculation_details["configuration_version"] == ("SCORING_DIMENSION_V1")
    assert score.calculation_details["configured_dimension_weight"] == "3"
    assert len(score.calculation_details["included_components"]) == 2
    assert score.calculation_details["excluded_components"] == ()


def test_fr_050_rule_004_dimension_score_excludes_no_data_child() -> None:
    service, _, execution_repository, versions = _aggregate_service(weights=(2, 1))
    execution = _aggregate_execution(versions)
    execution_repository.create_or_get(execution)
    execution_repository.complete_success(
        execution.execution_id,
        (
            _version_result(execution, versions[0], checked=0, passed=0, failed=0),
            _version_result(execution, versions[1], checked=10, passed=10, failed=0),
        ),
        datetime(2026, 7, 16, 11, 5, tzinfo=timezone.utc),
    )
    service.calculate_execution(execution.execution_id)

    score = service.calculate_dimension_score(execution.execution_id, QualityDimension.COMPLETENESS)

    assert score.score_value == Decimal("100.00")
    assert score.calculation_details["weight_sum"] == "1"
    assert score.calculation_details["excluded_components"][0]["status"] == "NO_DATA"


def test_fr_050_dimension_without_rule_score_is_rejected_without_record() -> None:
    service, score_repository, execution_repository, versions = _aggregate_service(weights=(1, 1))
    execution = _aggregate_execution(versions)
    execution_repository.create_or_get(execution)
    execution_repository.complete_success(
        execution.execution_id,
        tuple(
            _version_result(execution, version, checked=10, passed=10, failed=0)
            for version in versions
        ),
        datetime(2026, 7, 16, 11, 5, tzinfo=timezone.utc),
    )
    service.calculate_execution(execution.execution_id)

    with pytest.raises(ScoringValidationError, match="no rule scores"):
        service.calculate_dimension_score(execution.execution_id, QualityDimension.ACCURACY)

    assert all(
        score.scope_type is not ScoreScopeType.DIMENSION
        for score in score_repository.list_for_execution(execution.execution_id)
    )


def test_fr_050_uc_009_source_score_uses_dataset_criticality_weights() -> None:
    (
        service,
        score_repository,
        execution_repository,
        versions,
        _,
    ) = _source_service()
    criticality_weights = default_criticality_weights()
    criticality_weights[Criticality.HIGH] = Decimal("2")
    _create_and_approve_configuration(
        _configuration_service(score_repository),
        version="SOURCE_SCORING_V1",
        threshold_set=DEFAULT_THRESHOLD_SET,
        dimension_weights=default_dimension_weights(),
        criticality_weights=criticality_weights,
    )
    execution = _source_execution(versions)
    execution_repository.create_or_get(execution)
    execution_repository.complete_success(
        execution.execution_id,
        (
            _version_result(execution, versions[0], checked=10, passed=8, failed=2),
            _version_result(execution, versions[1], checked=10, passed=10, failed=0),
        ),
        datetime(2026, 7, 16, 12, 5, tzinfo=timezone.utc),
    )

    score = service.calculate_source_score(execution.execution_id, "source-main")
    repeated = service.calculate_source_score(execution.execution_id, "source-main")

    assert score.scope_type is ScoreScopeType.SOURCE
    assert score.scope_id == "source-main"
    assert score.score_value == Decimal("86.67")
    assert score.level is ScoreLevel.ACCEPTABLE
    assert score.calculation_details["formula_version"] == SOURCE_FORMULA_VERSION
    assert score.calculation_details["configuration_version"] == "SOURCE_SCORING_V1"
    assert score.calculation_details["weight_sum"] == "3.0"
    included = score.calculation_details["included_components"]
    assert [item["dataset_id"] for item in included] == ["dataset-high", "dataset-low"]
    assert [item["weight"] for item in included] == ["2", "1.0"]
    assert score.calculation_details["excluded_components"] == ()
    assert repeated == score


def test_fr_050_rule_004_source_score_excludes_no_data_dataset() -> None:
    service, _, execution_repository, versions, _ = _source_service()
    execution = _source_execution(versions)
    execution_repository.create_or_get(execution)
    execution_repository.complete_success(
        execution.execution_id,
        (
            _version_result(execution, versions[0], checked=0, passed=0, failed=0),
            _version_result(execution, versions[1], checked=10, passed=10, failed=0),
        ),
        datetime(2026, 7, 16, 12, 5, tzinfo=timezone.utc),
    )

    score = service.calculate_source_score(execution.execution_id, "source-main")

    assert score.score_value == Decimal("100.00")
    assert score.calculation_details["weight_sum"] == "1.0"
    excluded = score.calculation_details["excluded_components"]
    assert len(excluded) == 1
    assert excluded[0]["dataset_id"] == "dataset-high"
    assert excluded[0]["status"] == "NO_DATA"


def test_fr_050_rule_004_technical_datasets_produce_no_numeric_source_score() -> None:
    service, _, execution_repository, versions, _ = _source_service()
    execution = _source_execution(versions)
    execution = RuleExecution(
        execution_id=execution.execution_id,
        idempotency_key_hash=execution.idempotency_key_hash,
        payload_hash=execution.payload_hash,
        rule_version_ids=execution.rule_version_ids,
        scope=execution.scope,
        triggered_by=execution.triggered_by,
        correlation_id=execution.correlation_id,
        status=ExecutionStatus.TECHNICAL_ERROR,
        error_class="NETWORK",
        started_at=execution.started_at,
        finished_at=datetime(2026, 7, 16, 12, 5, tzinfo=timezone.utc),
    )
    execution_repository.create_or_get(execution)

    score = service.calculate_source_score(execution.execution_id, "source-main")

    assert score.score_status is ScoreStatus.NOT_CALCULATED_TECHNICAL_ERROR
    assert score.score_value is None
    assert score.level is None
    assert len(score.calculation_details["excluded_components"]) == 2


def test_fr_050_source_scope_or_catalog_error_creates_no_source_score() -> None:
    service, score_repository, execution_repository, versions, catalog = _source_service()
    execution = _source_execution(versions)
    execution_repository.create_or_get(execution)
    execution_repository.complete_success(
        execution.execution_id,
        tuple(
            _version_result(execution, version, checked=10, passed=10, failed=0)
            for version in versions
        ),
        datetime(2026, 7, 16, 12, 5, tzinfo=timezone.utc),
    )

    with pytest.raises(ScoringValidationError, match="no datasets"):
        service.calculate_source_score(execution.execution_id, "source-other")
    service_without_catalog = ScoringService(
        score_repository,
        execution_repository,
        catalog,
    )
    with pytest.raises(ScoringValidationError, match="Source catalog is required"):
        service_without_catalog.calculate_source_score(execution.execution_id, "source-main")

    assert all(
        score.scope_type is not ScoreScopeType.SOURCE
        for score in score_repository.list_for_execution(execution.execution_id)
    )


def test_fr_050_uc_009_enterprise_score_equally_aggregates_sources() -> None:
    service, score_repository, execution_repository, versions, _ = _source_service(
        data_source_ids=("source-a", "source-b")
    )
    execution = _source_execution(versions)
    execution_repository.create_or_get(execution)
    execution_repository.complete_success(
        execution.execution_id,
        (
            _version_result(execution, versions[0], checked=10, passed=8, failed=2),
            _version_result(execution, versions[1], checked=10, passed=10, failed=0),
        ),
        datetime(2026, 7, 16, 13, 5, tzinfo=timezone.utc),
    )

    score = service.calculate_enterprise_score(execution.execution_id)
    repeated = service.calculate_enterprise_score(execution.execution_id)

    assert score.scope_type is ScoreScopeType.ENTERPRISE
    assert score.scope_id is None
    assert score.score_value == Decimal("90.00")
    assert score.level is ScoreLevel.GOOD
    assert score.calculation_details["formula_version"] == (ENTERPRISE_FORMULA_VERSION)
    assert score.calculation_details["configuration_version"] == ("DEFAULT_SCORING_V1")
    assert score.calculation_details["weight_policy"] == "EQUAL_SOURCE_WEIGHT"
    assert score.calculation_details["weight_sum"] == "2"
    included = score.calculation_details["included_components"]
    assert [item["data_source_id"] for item in included] == [
        "source-a",
        "source-b",
    ]
    assert [item["weight"] for item in included] == ["1", "1"]
    assert score.calculation_details["excluded_components"] == ()
    assert repeated == score
    enterprise_scores = [
        item
        for item in score_repository.list_for_execution(execution.execution_id)
        if item.scope_type is ScoreScopeType.ENTERPRISE
    ]
    assert enterprise_scores == [score]


def test_fr_050_rule_004_enterprise_score_excludes_no_data_source() -> None:
    service, _, execution_repository, versions, _ = _source_service(
        data_source_ids=("source-a", "source-b")
    )
    execution = _source_execution(versions)
    execution_repository.create_or_get(execution)
    execution_repository.complete_success(
        execution.execution_id,
        (
            _version_result(execution, versions[0], checked=0, passed=0, failed=0),
            _version_result(execution, versions[1], checked=10, passed=10, failed=0),
        ),
        datetime(2026, 7, 16, 13, 5, tzinfo=timezone.utc),
    )

    score = service.calculate_enterprise_score(execution.execution_id)

    assert score.score_value == Decimal("100.00")
    assert score.calculation_details["weight_sum"] == "1"
    assert score.calculation_details["included_components"][0]["data_source_id"] == "source-b"
    excluded = score.calculation_details["excluded_components"]
    assert len(excluded) == 1
    assert excluded[0]["data_source_id"] == "source-a"
    assert excluded[0]["status"] == "NO_DATA"


def test_fr_050_rule_004_technical_sources_produce_no_enterprise_number() -> None:
    service, _, execution_repository, versions, _ = _source_service(
        data_source_ids=("source-a", "source-b")
    )
    execution = _source_execution(versions)
    technical_execution = RuleExecution(
        execution_id=execution.execution_id,
        idempotency_key_hash=execution.idempotency_key_hash,
        payload_hash=execution.payload_hash,
        rule_version_ids=execution.rule_version_ids,
        scope=execution.scope,
        triggered_by=execution.triggered_by,
        correlation_id=execution.correlation_id,
        status=ExecutionStatus.TECHNICAL_ERROR,
        error_class="NETWORK",
        started_at=execution.started_at,
        finished_at=datetime(2026, 7, 16, 13, 5, tzinfo=timezone.utc),
    )
    execution_repository.create_or_get(technical_execution)

    score = service.calculate_enterprise_score(execution.execution_id)

    assert score.score_status is ScoreStatus.NOT_CALCULATED_TECHNICAL_ERROR
    assert score.score_value is None
    assert score.level is None
    assert score.calculation_details["included_components"] == ()
    assert len(score.calculation_details["excluded_components"]) == 2


def test_fr_050_enterprise_scoring_requires_source_catalog() -> None:
    service, score_repository, execution_repository, versions, catalog = _source_service()
    execution = _source_execution(versions)
    execution_repository.create_or_get(execution)
    service_without_catalog = ScoringService(
        score_repository,
        execution_repository,
        catalog,
    )

    with pytest.raises(ScoringValidationError, match="enterprise scoring"):
        service_without_catalog.calculate_enterprise_score(execution.execution_id)

    assert all(
        score.scope_type is not ScoreScopeType.ENTERPRISE
        for score in score_repository.list_for_execution(execution.execution_id)
    )


def test_rule_005_criticality_weights_must_be_complete_and_positive() -> None:
    repository = SQLiteScoreRepository()
    service = _configuration_service(repository)

    with pytest.raises(ScoringValidationError, match="every dataset criticality"):
        service.create_and_submit(
            actor_context=_scoring_context("scoring-maker", {"SCORING_MAKER"}, now=service.clock()),
            version="INVALID_SOURCE_CONFIG",
            threshold_set=DEFAULT_THRESHOLD_SET,
            dimension_weights=default_dimension_weights(),
            criticality_weights={Criticality.HIGH: Decimal("1")},
        )
    invalid = default_criticality_weights()
    invalid[Criticality.CRITICAL] = Decimal("0")
    with pytest.raises(ScoringValidationError, match="positive finite"):
        service.create_and_submit(
            actor_context=_scoring_context("scoring-maker", {"SCORING_MAKER"}, now=service.clock()),
            version="INVALID_SOURCE_WEIGHT",
            threshold_set=DEFAULT_THRESHOLD_SET,
            dimension_weights=default_dimension_weights(),
            criticality_weights=invalid,
        )

    assert repository.get_active_configuration().version == "DEFAULT_SCORING_V1"


def test_score_repository_migrates_existing_configuration_criticality_weights(
    tmp_path: Any,
) -> None:
    database = tmp_path / "old-scoring-config.sqlite"
    connection = sqlite3.connect(database)
    connection.execute(
        """
        CREATE TABLE scoring_configurations (
            configuration_id TEXT PRIMARY KEY,
            version TEXT NOT NULL UNIQUE,
            threshold_version TEXT NOT NULL,
            critical_upper_exclusive TEXT NOT NULL,
            risky_upper_exclusive TEXT NOT NULL,
            acceptable_upper_exclusive TEXT NOT NULL,
            dimension_weights TEXT NOT NULL,
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL,
            is_active INTEGER NOT NULL,
            activated_at TEXT
        )
        """
    )
    connection.execute(
        """
        INSERT INTO scoring_configurations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "config-old",
            "SCORING_OLD",
            "THRESHOLDS_OLD",
            "50",
            "75",
            "90",
            (
                '{"COMPLETENESS":"1","ACCURACY":"1","VALIDITY":"1",'
                '"CONSISTENCY":"1","UNIQUENESS":"1","TIMELINESS":"1",'
                '"INTEGRITY":"1"}'
            ),
            "system",
            "2026-07-16T12:00:00+00:00",
            1,
            "2026-07-16T12:00:00+00:00",
        ),
    )
    connection.commit()
    connection.close()

    repository = SQLiteScoreRepository(str(database))
    active = repository.get_active_configuration()
    columns = {
        row["name"]
        for row in repository.connection.execute(
            "PRAGMA table_info(scoring_configurations)"
        ).fetchall()
    }
    approval_columns = {
        row["name"]
        for row in repository.connection.execute(
            "PRAGMA table_info(scoring_configuration_approvals)"
        ).fetchall()
    }

    assert "criticality_weights" in columns
    assert {
        "approval_id",
        "configuration_id",
        "maker_actor_id",
        "checker_actor_id",
        "policy_version",
        "status",
    }.issubset(approval_columns)
    assert active.version == "SCORING_OLD"
    assert active.criticality_weights == default_criticality_weights()


def _service() -> tuple[
    ScoringService,
    SQLiteScoreRepository,
    SQLiteExecutionRepository,
    RuleVersion,
]:
    version = RuleVersion(
        rule_version_id="version-main",
        quality_rule_id="rule-main",
        version_no=1,
        rule_type=RuleType.REQUIRED,
        definition={"field_id": "field-main", "operator": "IS_NOT_NULL"},
        threshold=90,
        weight=1,
        criticality=RuleCriticality.HIGH,
    )
    score_repository = SQLiteScoreRepository()
    execution_repository = SQLiteExecutionRepository()
    service = ScoringService(
        score_repository,
        execution_repository,
        FakeRuleCatalog(version),
        clock=lambda: datetime(2026, 7, 16, 9, 10, tzinfo=timezone.utc),
    )
    return service, score_repository, execution_repository, version


def _aggregate_service(
    *,
    weights: tuple[float, float],
    threshold_set: ThresholdSet | None = None,
) -> tuple[
    ScoringService,
    SQLiteScoreRepository,
    SQLiteExecutionRepository,
    tuple[RuleVersion, RuleVersion],
]:
    rules = tuple(
        QualityRule(
            quality_rule_id=f"rule-{index}",
            code=f"DQ_RULE_{index}",
            name=f"Kural {index}",
            dataset_id="dataset-main",
            field_ids=(f"field-{index}",),
            primary_dimension=QualityDimension.COMPLETENESS,
            owner_user_id="owner-1",
            status=RuleStatus.ACTIVE,
        )
        for index in (1, 2)
    )
    versions = tuple(
        RuleVersion(
            rule_version_id=f"version-{index}",
            quality_rule_id=rule.quality_rule_id,
            version_no=1,
            rule_type=RuleType.REQUIRED,
            definition={"field_id": f"field-{index}", "operator": "IS_NOT_NULL"},
            threshold=90,
            weight=weights[index - 1],
            criticality=RuleCriticality.HIGH,
        )
        for index, rule in enumerate(rules, start=1)
    )
    score_repository = SQLiteScoreRepository()
    execution_repository = SQLiteExecutionRepository()
    kwargs: dict[str, Any] = {}
    if threshold_set is not None:
        kwargs["threshold_set"] = threshold_set
    service = ScoringService(
        score_repository,
        execution_repository,
        FakeAggregateRuleCatalog(
            {version.rule_version_id: version for version in versions},
            {rule.quality_rule_id: rule for rule in rules},
        ),
        clock=lambda: datetime(2026, 7, 16, 10, 10, tzinfo=timezone.utc),
        **kwargs,
    )
    return service, score_repository, execution_repository, (versions[0], versions[1])


def _aggregate_execution(
    versions: tuple[RuleVersion, RuleVersion],
    *,
    execution_id: str = "execution-aggregate",
) -> RuleExecution:
    return RuleExecution(
        execution_id=execution_id,
        idempotency_key_hash=f"key-{execution_id}",
        payload_hash=f"payload-{execution_id}",
        rule_version_ids=tuple(version.rule_version_id for version in versions),
        scope={"dataset_id": "dataset-main"},
        triggered_by="system",
        correlation_id=f"correlation-{execution_id}",
        status=ExecutionStatus.RUNNING,
        started_at=datetime(2026, 7, 16, 10, 0, tzinfo=timezone.utc),
    )


def _source_service(
    *,
    data_source_ids: tuple[str, str] = ("source-main", "source-main"),
) -> tuple[
    ScoringService,
    SQLiteScoreRepository,
    SQLiteExecutionRepository,
    tuple[RuleVersion, RuleVersion],
    FakeAggregateRuleCatalog,
]:
    rules = tuple(
        QualityRule(
            quality_rule_id=f"source-rule-{index}",
            code=f"DQ_SOURCE_RULE_{index}",
            name=f"Kaynak kuralı {index}",
            dataset_id=dataset_id,
            field_ids=(f"source-field-{index}",),
            primary_dimension=QualityDimension.COMPLETENESS,
            owner_user_id="owner-1",
            status=RuleStatus.ACTIVE,
        )
        for index, dataset_id in enumerate(("dataset-high", "dataset-low"), start=1)
    )
    versions = tuple(
        RuleVersion(
            rule_version_id=f"source-version-{index}",
            quality_rule_id=rule.quality_rule_id,
            version_no=1,
            rule_type=RuleType.REQUIRED,
            definition={"field_id": f"source-field-{index}"},
            threshold=90,
            weight=1,
            criticality=RuleCriticality.HIGH,
        )
        for index, rule in enumerate(rules, start=1)
    )
    datasets = {
        "dataset-high": Dataset(
            dataset_id="dataset-high",
            data_source_id=data_source_ids[0],
            namespace="public",
            name="high_priority",
            criticality=Criticality.HIGH,
        ),
        "dataset-low": Dataset(
            dataset_id="dataset-low",
            data_source_id=data_source_ids[1],
            namespace="public",
            name="low_priority",
            criticality=Criticality.LOW,
        ),
    }
    catalog = FakeAggregateRuleCatalog(
        {version.rule_version_id: version for version in versions},
        {rule.quality_rule_id: rule for rule in rules},
    )
    score_repository = SQLiteScoreRepository()
    execution_repository = SQLiteExecutionRepository()
    service = ScoringService(
        score_repository,
        execution_repository,
        catalog,
        source_catalog=FakeSourceCatalog(datasets),
        clock=lambda: datetime(2026, 7, 16, 12, 10, tzinfo=timezone.utc),
    )
    return (
        service,
        score_repository,
        execution_repository,
        (versions[0], versions[1]),
        catalog,
    )


def _source_execution(
    versions: tuple[RuleVersion, RuleVersion],
) -> RuleExecution:
    return RuleExecution(
        execution_id="execution-source",
        idempotency_key_hash="key-source",
        payload_hash="payload-source",
        rule_version_ids=tuple(version.rule_version_id for version in versions),
        scope={"data_source_id": "source-main"},
        triggered_by="system",
        correlation_id="correlation-source",
        status=ExecutionStatus.RUNNING,
        started_at=datetime(2026, 7, 16, 12, 0, tzinfo=timezone.utc),
    )


def _version_result(
    execution: RuleExecution,
    version: RuleVersion,
    *,
    checked: int,
    passed: int,
    failed: int,
) -> RuleExecutionResult:
    return RuleExecutionResult(
        execution_id=execution.execution_id,
        rule_version_id=version.rule_version_id,
        population_count=checked,
        eligible_count=checked,
        evaluated_count=checked,
        passed_count=passed,
        failed_count=failed,
        excluded_count=0,
        technical_error_count=0,
        unknown_count=0,
        measurement_status=(
            MeasurementStatus.NO_DATA
            if checked == 0
            else MeasurementStatus.PASSED
            if failed == 0
            else MeasurementStatus.FAILED
        ),
    )


def _execution(
    version: RuleVersion,
    *,
    status: ExecutionStatus = ExecutionStatus.RUNNING,
) -> RuleExecution:
    return RuleExecution(
        execution_id="execution-main",
        idempotency_key_hash="key-main",
        payload_hash="payload-main",
        rule_version_ids=(version.rule_version_id,),
        scope={"dataset_id": "dataset-main"},
        triggered_by="system",
        correlation_id="correlation-main",
        status=status,
        started_at=datetime(2026, 7, 16, 9, 0, tzinfo=timezone.utc),
    )


def _result(
    execution: RuleExecution,
    *,
    checked: int,
    passed: int,
    failed: int,
    eligible_for_official_scoring: bool = True,
    completed_partitions: tuple[str, ...] = (),
) -> RuleExecutionResult:
    return RuleExecutionResult(
        execution_id=execution.execution_id,
        rule_version_id=execution.rule_version_ids[0],
        population_count=checked,
        eligible_count=checked,
        evaluated_count=checked,
        passed_count=passed,
        failed_count=failed,
        excluded_count=0,
        technical_error_count=0,
        unknown_count=0,
        measurement_status=(
            MeasurementStatus.NO_DATA
            if checked == 0
            else MeasurementStatus.PASSED
            if failed == 0
            else MeasurementStatus.FAILED
        ),
        completed_partitions=completed_partitions,
        eligible_for_official_scoring=eligible_for_official_scoring,
    )


def _partial_policy(dataset_id: str, required_rule_id: str) -> DatasetPartialScorePolicy:
    now = datetime(2026, 7, 16, 10, 0, tzinfo=timezone.utc)
    return DatasetPartialScorePolicy(
        policy_id=f"policy-{dataset_id}",
        dataset_id=dataset_id,
        policy_version="DATASET_PARTIAL_V1",
        allow_official_partial_score=True,
        minimum_coverage_ratio=Decimal("0.90"),
        required_critical_rule_ids=(required_rule_id,),
        required_partitions=("partition-required",),
        maximum_missing_record_ratio=Decimal("0.05"),
        maximum_technical_error_ratio=Decimal("0.10"),
        minimum_successful_rule_ratio=Decimal("0.75"),
        effective_from=now,
        approval_status=PartialScorePolicyStatus.APPROVED,
        created_by="maker-1",
        approved_by="checker-1",
        audit_reference=f"audit-{dataset_id}",
        created_at=now,
    )


def _partial_facts(
    dataset_id: str,
    executed_rule_id: str,
    *,
    total_rule_count: int = 1,
) -> PartialExecutionFacts:
    return PartialExecutionFacts(
        dataset_id=dataset_id,
        coverage_ratio=Decimal("1"),
        executed_rule_ids=(executed_rule_id,),
        technical_error_rule_ids=(),
        completed_partitions=("partition-required",),
        missing_record_ratio=Decimal("0"),
        total_rule_count=total_rule_count,
    )
