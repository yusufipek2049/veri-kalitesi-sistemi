from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from veri_kalitesi.scoring import (
    DatasetPartialScorePolicy,
    DatasetPartialScorePolicyService,
    PartialExecutionFacts,
    PartialScoreEligibility,
    PartialScorePolicyStatus,
    ScoringTechnicalError,
    ScoringValidationError,
    SQLiteDatasetPartialScorePolicyRepository,
)


AT = datetime(2026, 7, 21, 10, 0, tzinfo=timezone.utc)


def _policy(
    *,
    policy_version: str = "DATASET_PARTIAL_V1",
    effective_from: datetime = AT,
    allow_official_partial_score: bool = True,
) -> DatasetPartialScorePolicy:
    return DatasetPartialScorePolicy(
        policy_id=f"policy-{policy_version}",
        dataset_id="dataset-main",
        policy_version=policy_version,
        allow_official_partial_score=allow_official_partial_score,
        minimum_coverage_ratio=Decimal("0.90"),
        required_critical_rule_ids=("rule-critical",),
        required_partitions=("partition-required",),
        maximum_missing_record_ratio=Decimal("0.05"),
        maximum_technical_error_ratio=Decimal("0.10"),
        minimum_successful_rule_ratio=Decimal("0.75"),
        effective_from=effective_from,
        approval_status=PartialScorePolicyStatus.APPROVED,
        created_by="maker-1",
        approved_by="checker-1",
        audit_reference=f"audit-{policy_version}",
        created_at=effective_from,
    )


def _facts() -> PartialExecutionFacts:
    return PartialExecutionFacts(
        dataset_id="dataset-main",
        coverage_ratio=Decimal("0.95"),
        executed_rule_ids=("rule-critical", "rule-2", "rule-3", "rule-4"),
        technical_error_rule_ids=(),
        completed_partitions=("partition-required", "partition-optional"),
        missing_record_ratio=Decimal("0.01"),
        total_rule_count=4,
    )


def test_fr_048_open_018_approved_policy_is_versioned_and_effective_by_time() -> None:
    repository = SQLiteDatasetPartialScorePolicyRepository()
    first = _policy(effective_from=AT - timedelta(days=1))
    second = _policy(
        policy_version="DATASET_PARTIAL_V2",
        effective_from=AT + timedelta(hours=1),
    )

    repository.save(first)
    repository.save(second)

    assert repository.list_policies("dataset-main") == [first, second]
    assert repository.resolve_effective("dataset-main", at=AT) == first
    assert repository.resolve_effective("dataset-main", at=AT + timedelta(hours=2)) == second


def test_fr_048_uc_009_all_partial_policy_conditions_allow_official_score() -> None:
    repository = SQLiteDatasetPartialScorePolicyRepository()
    repository.save(_policy())
    service = DatasetPartialScorePolicyService(repository)

    decision = service.evaluate(_facts(), at=AT)

    assert decision.eligibility is PartialScoreEligibility.OFFICIAL
    assert decision.reason_codes == ("ALL_POLICY_CONDITIONS_MET",)
    assert decision.policy_version == "DATASET_PARTIAL_V1"
    assert decision.executed_rule_count == 4
    assert decision.not_executed_rule_count == 0
    assert decision.missing_partitions == ()


@pytest.mark.parametrize(
    ("policy", "facts", "reason_code"),
    [
        (
            _policy(allow_official_partial_score=False),
            _facts(),
            "OFFICIAL_PARTIAL_DISABLED",
        ),
        (
            _policy(),
            replace(_facts(), coverage_ratio=Decimal("0.89")),
            "COVERAGE_BELOW_MINIMUM",
        ),
        (
            _policy(),
            replace(
                _facts(),
                executed_rule_ids=("rule-2", "rule-3", "rule-4"),
            ),
            "REQUIRED_CRITICAL_RULE_MISSING",
        ),
        (
            _policy(),
            replace(_facts(), completed_partitions=("partition-optional",)),
            "REQUIRED_PARTITION_MISSING",
        ),
        (
            _policy(),
            replace(_facts(), missing_record_ratio=Decimal("0.06")),
            "MISSING_RECORD_RATIO_EXCEEDED",
        ),
        (
            _policy(),
            replace(
                _facts(),
                executed_rule_ids=("rule-critical", "rule-2", "rule-3"),
                technical_error_rule_ids=("rule-4",),
            ),
            "TECHNICAL_ERROR_RATIO_EXCEEDED",
        ),
        (
            _policy(),
            replace(
                _facts(),
                executed_rule_ids=("rule-critical", "rule-2"),
            ),
            "SUCCESSFUL_RULE_RATIO_BELOW_MINIMUM",
        ),
    ],
)
def test_fr_048_open_018_any_failed_condition_is_provisional(
    policy: DatasetPartialScorePolicy,
    facts: PartialExecutionFacts,
    reason_code: str,
) -> None:
    repository = SQLiteDatasetPartialScorePolicyRepository()
    repository.save(policy)
    service = DatasetPartialScorePolicyService(repository)

    decision = service.evaluate(facts, at=AT)

    assert decision.eligibility is PartialScoreEligibility.PROVISIONAL
    assert reason_code in decision.reason_codes


def test_fr_048_open_018_missing_policy_fails_closed_as_provisional() -> None:
    service = DatasetPartialScorePolicyService(SQLiteDatasetPartialScorePolicyRepository())

    decision = service.evaluate(_facts(), at=AT)

    assert decision.eligibility is PartialScoreEligibility.PROVISIONAL
    assert decision.reason_codes == ("POLICY_NOT_FOUND",)
    assert decision.policy_version is None


def test_fr_048_open_012_unapproved_policy_is_not_effective() -> None:
    repository = SQLiteDatasetPartialScorePolicyRepository()
    repository.save(
        replace(
            _policy(),
            approval_status=PartialScorePolicyStatus.PENDING,
            approved_by=None,
            audit_reference=None,
        )
    )
    service = DatasetPartialScorePolicyService(repository)

    decision = service.evaluate(_facts(), at=AT)

    assert decision.eligibility is PartialScoreEligibility.PROVISIONAL
    assert decision.reason_codes == ("POLICY_NOT_FOUND",)


def test_fr_048_open_012_creator_cannot_approve_same_partial_policy() -> None:
    repository = SQLiteDatasetPartialScorePolicyRepository()
    policy = replace(_policy(), approved_by="maker-1")

    with pytest.raises(ScoringValidationError, match="creator cannot approve"):
        repository.save(policy)

    assert repository.list_policies("dataset-main") == []


def test_fr_048_partial_execution_facts_reject_conflicting_rule_outcomes() -> None:
    repository = SQLiteDatasetPartialScorePolicyRepository()
    repository.save(_policy())
    service = DatasetPartialScorePolicyService(repository)
    facts = replace(
        _facts(),
        technical_error_rule_ids=("rule-critical",),
    )

    with pytest.raises(ScoringValidationError, match="must be disjoint"):
        service.evaluate(facts, at=AT)


def test_fr_048_partial_policy_repository_failure_is_technical_error() -> None:
    repository = SQLiteDatasetPartialScorePolicyRepository()
    repository.connection.close()

    with pytest.raises(ScoringTechnicalError):
        repository.resolve_effective("dataset-main", at=AT)
