from datetime import datetime, timezone
from decimal import Decimal

from veri_kalitesi.scoring import (
    ComparisonStatus,
    QualityScore,
    ScoreScopeType,
    ScoreStatus,
    compare_scores,
    contribution_graph,
)


NOW = datetime(2026, 7, 30, tzinfo=timezone.utc)


def test_dq_cap_005_graph_preserves_included_excluded_counts_and_contribution() -> None:
    score = _score(
        "88.00",
        {
            **_versions(),
            "weight_sum": "4",
            "counts": {
                "population": 12,
                "eligible": 10,
                "evaluated": 9,
                "passed": 8,
                "failed": 1,
                "excluded": 1,
                "technical_error": 1,
                "unknown": 1,
                "raw_customer_value": "must-not-leak",
            },
            "included_components": [
                {
                    "rule_version_id": "rule-v1",
                    "score": "80",
                    "weight": "2",
                }
            ],
            "excluded_components": [
                {"rule_version_id": "rule-v2", "status": "NO_DATA"}
            ],
            "critical_rule_status": "FAILED",
            "critical_veto": True,
            "evidence_references": [
                "evidence:rule-v1",
                "SELECT raw_secret FROM customer",
            ],
            "diagnosis_status": "OBSERVED",
            "diagnosis_evidence_ref": "diagnosis:rule-v1",
        },
    )

    graph = contribution_graph(score)

    assert graph["raw_quality_score"] == "88.00"
    assert graph["critical_veto"] is True
    assert graph["components"][0]["contribution"] == "40"
    assert graph["components"][0]["component_type"] == "DATASET"
    assert graph["components"][0]["rule_version_id"] == "rule-v1"
    assert graph["components"][1]["exclusion_reason"] == "NO_DATA"
    assert graph["canonical_counts"]["evaluated"] == 9
    assert "raw_customer_value" not in graph["canonical_counts"]
    assert graph["critical_asset_status"] == "UNKNOWN"
    assert graph["sla_status"] == "UNKNOWN"
    assert graph["evidence_references"] == ["evidence:rule-v1"]
    assert graph["diagnosis_status"] == "OBSERVED"
    assert graph["diagnosis_evidence_ref"] == "diagnosis:rule-v1"
    assert graph["usage_decision"] == "UNKNOWN"


def test_dq_cap_011_only_same_official_contract_is_comparable() -> None:
    previous = _score("80.00", _versions())
    current = _score("85.00", _versions())

    result = compare_scores(current, previous)

    assert result.status is ComparisonStatus.COMPARABLE
    assert result.delta == Decimal("5.00")


def test_dq_cap_011_missing_or_changed_contract_fails_closed() -> None:
    previous = _score("80.00", _versions())
    missing = _score("85.00", {**_versions(), "profile_version": None})
    changed = _score(
        "85.00", {**_versions(), "governance_version": "governance-v2"}
    )
    changed_rules = _score(
        "85.00", {**_versions(), "rule_set_version": "rule-set-v2"}
    )
    provisional = _score(
        "85.00", {**_versions(), "included_in_official_aggregation": False}
    )

    assert compare_scores(missing, previous).status is ComparisonStatus.UNKNOWN
    assert (
        compare_scores(changed, previous).status
        is ComparisonStatus.NOT_COMPARABLE
    )
    assert compare_scores(changed_rules, previous).reason_codes == (
        "RULE_VERSION_CHANGED",
    )
    assert (
        compare_scores(provisional, previous).reason_codes
        == ("NON_OFFICIAL_RESULT",)
    )


def _versions() -> dict[str, object]:
    return {
        "included_in_official_aggregation": True,
        "rule_set_version": "rule-set-v1",
        "formula_version": "model-v1",
        "configuration_version": "policy-v1",
        "qualification_policy_version": "qualification-v1",
        "profile_version": "profile-v1",
        "governance_version": "governance-v1",
    }


def _score(value: str, details: dict[str, object]) -> QualityScore:
    return QualityScore(
        execution_id="execution-1",
        rule_version_id=None,
        scope_type=ScoreScopeType.SOURCE,
        scope_id="source-1",
        score_value=Decimal(value),
        score_status=ScoreStatus.CALCULATED,
        calculation_details=details,
        calculated_at=NOW,
    )
