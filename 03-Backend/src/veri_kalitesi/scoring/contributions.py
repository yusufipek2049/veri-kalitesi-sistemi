"""Yeniden üretilebilir skor katkı grafiği ve karşılaştırma sözleşmesi."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
import re
from typing import Any, Mapping

from veri_kalitesi.scoring.models import QualityScore, is_official_score


CONTRIBUTION_GRAPH_VERSION = "DQ_SCORE_CONTRIBUTION_GRAPH_V1"
CANONICAL_COUNT_KEYS = (
    "population",
    "eligible",
    "evaluated",
    "passed",
    "failed",
    "excluded",
    "technical_error",
    "unknown",
)
_SAFE_REFERENCE = re.compile(r"[A-Za-z0-9_.:/-]{1,256}")
_SAFE_STATUS = re.compile(r"[A-Z0-9_.-]{1,120}")


class ComparisonStatus(str, Enum):
    COMPARABLE = "COMPARABLE"
    NOT_COMPARABLE = "NOT_COMPARABLE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ScoreComparison:
    status: ComparisonStatus
    reason_codes: tuple[str, ...]
    delta: Decimal | None = None


def contribution_graph(score: QualityScore) -> dict[str, Any]:
    """Mevcut hesap ayrıntısından veri-minimum, deterministik grafik üretir."""

    details = score.calculation_details
    included = tuple(details.get("included_components", ()))
    excluded = tuple(details.get("excluded_components", ()))
    counts = details.get("counts")
    weight_sum = _decimal_or_none(details.get("weight_sum"))
    nodes: list[dict[str, Any]] = []
    for component in included:
        if not isinstance(component, Mapping):
            continue
        component_score = _decimal_or_none(component.get("score"))
        weight = _decimal_or_none(
            component.get("weight", component.get("quality_weight"))
        )
        contribution = None
        if component_score is not None and weight is not None and weight_sum:
            contribution = component_score * weight / weight_sum
        nodes.append(
            {
                "component_ref": _component_ref(component),
                "component_type": _component_type(score.scope_type),
                **_component_references(component),
                "included": True,
                "score": _text(component_score),
                "weight": _text(weight),
                "contribution": _text(contribution),
                "exclusion_reason": None,
            }
        )
    for component in excluded:
        if not isinstance(component, Mapping):
            continue
        nodes.append(
            {
                "component_ref": _component_ref(component),
                "component_type": _component_type(score.scope_type),
                **_component_references(component),
                "included": False,
                "score": None,
                "weight": None,
                "contribution": None,
                "exclusion_reason": _status(component.get("status")),
            }
        )
    if score.scope_type.value == "RULE":
        nodes.append(
            {
                "component_ref": _reference(score.rule_version_id),
                "component_type": "RULE",
                "quality_score_id": score.quality_score_id,
                "rule_version_id": _reference(score.rule_version_id),
                "dataset_id": None,
                "data_source_id": None,
                "dimension": None,
                "included": score.score_value is not None,
                "score": _text(score.score_value),
                "weight": None,
                "contribution": _text(score.score_value),
                "exclusion_reason": (
                    None
                    if score.score_value is not None
                    else _status(details.get("excluded_reason"))
                ),
            }
        )

    versions = {
        "rule_version": _string_or_none(
            score.rule_version_id or details.get("rule_set_version")
        ),
        "score_model_version": _string_or_none(details.get("formula_version")),
        "policy_version": _string_or_none(details.get("configuration_version")),
        "threshold_version": _string_or_none(details.get("threshold_version")),
        "qualification_policy_version": _string_or_none(
            details.get("qualification_policy_version")
            or details.get("partial_score_policy_version")
        ),
        "profile_version": _string_or_none(details.get("profile_version")),
        "governance_version": _string_or_none(details.get("governance_version")),
    }
    return {
        "graph_version": CONTRIBUTION_GRAPH_VERSION,
        "quality_score_id": score.quality_score_id,
        "execution_id": score.execution_id,
        "scope": {"type": score.scope_type.value, "id": score.scope_id},
        "official": is_official_score(score),
        "raw_quality_score": _text(score.score_value),
        "technical_status": _status(details.get("execution_status")),
        "measurement_qualification": _status(details.get("measurement_status")),
        "critical_rule_status": _status(details.get("critical_rule_status")),
        "critical_veto": (
            details.get("critical_veto")
            if isinstance(details.get("critical_veto"), bool)
            else None
        ),
        "critical_asset_status": _status(details.get("critical_asset_status")),
        "risk_status": _status(details.get("risk_status")),
        "sla_status": _status(details.get("sla_status")),
        "usage_decision": _status(details.get("usage_decision")),
        "coverage_status": _status(details.get("coverage_status")),
        "canonical_counts": _canonical_counts(counts),
        "evidence_references": _safe_references(
            details.get("evidence_references")
        ),
        "diagnosis_status": _status(details.get("diagnosis_status")),
        "diagnosis_evidence_ref": _reference(
            details.get("diagnosis_evidence_ref"),
            unknown=None,
        ),
        "versions": versions,
        "components": nodes,
    }


def compare_scores(current: QualityScore, previous: QualityScore) -> ScoreComparison:
    """Yalnız resmî ve aynı kapsam/model/politika snapshot'larını karşılaştırır."""

    current_graph = contribution_graph(current)
    previous_graph = contribution_graph(previous)
    if not current_graph["official"] or not previous_graph["official"]:
        return ScoreComparison(
            ComparisonStatus.NOT_COMPARABLE, ("NON_OFFICIAL_RESULT",)
        )
    if (
        current.scope_type is not previous.scope_type
        or current.scope_id != previous.scope_id
    ):
        return ScoreComparison(ComparisonStatus.NOT_COMPARABLE, ("SCOPE_CHANGED",))

    required = (
        "rule_version",
        "score_model_version",
        "policy_version",
        "qualification_policy_version",
        "profile_version",
        "governance_version",
    )
    current_versions = current_graph["versions"]
    previous_versions = previous_graph["versions"]
    missing = tuple(
        f"MISSING_{name.upper()}"
        for name in required
        if not current_versions[name] or not previous_versions[name]
    )
    if missing:
        return ScoreComparison(ComparisonStatus.UNKNOWN, missing)
    changed = tuple(
        f"{name.upper()}_CHANGED"
        for name in required
        if current_versions[name] != previous_versions[name]
    )
    if changed:
        return ScoreComparison(ComparisonStatus.NOT_COMPARABLE, changed)
    if current.score_value is None or previous.score_value is None:
        return ScoreComparison(ComparisonStatus.UNKNOWN, ("SCORE_VALUE_MISSING",))
    return ScoreComparison(
        ComparisonStatus.COMPARABLE,
        (),
        current.score_value - previous.score_value,
    )


def _component_ref(component: Mapping[str, Any]) -> str:
    for key in (
        "rule_version_id",
        "dataset_id",
        "data_source_id",
        "dimension",
        "quality_score_id",
    ):
        value = component.get(key)
        reference = _reference(value)
        if reference != "UNKNOWN":
            return reference
    return "UNKNOWN"


def _component_references(component: Mapping[str, Any]) -> dict[str, str | None]:
    return {
        key: (_reference(component.get(key), unknown=None))
        for key in (
            "quality_score_id",
            "rule_version_id",
            "dataset_id",
            "data_source_id",
            "dimension",
        )
    }


def _component_type(scope_type: object) -> str:
    value = getattr(scope_type, "value", scope_type)
    return {
        "ENTERPRISE": "SOURCE",
        "SOURCE": "DATASET",
        "DATASET": "RULE",
        "DIMENSION": "RULE",
        "RULE": "RULE",
    }.get(value, "UNKNOWN")


def _canonical_counts(value: object) -> dict[str, int | None] | None:
    if not isinstance(value, Mapping):
        return None
    return {
        key: (
            item
            if isinstance((item := value.get(key)), int)
            and not isinstance(item, bool)
            and item >= 0
            else None
        )
        for key in CANONICAL_COUNT_KEYS
    }


def _decimal_or_none(value: object) -> Decimal | None:
    try:
        return Decimal(str(value)) if value is not None else None
    except Exception:
        return None


def _text(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def _string_or_none(value: object) -> str | None:
    return _reference(value, unknown=None)


def _reference(value: object, *, unknown: str | None = "UNKNOWN") -> str | None:
    if isinstance(value, str):
        normalized = value.strip()
        if _SAFE_REFERENCE.fullmatch(normalized):
            return normalized
    return unknown


def _status(value: object) -> str:
    if isinstance(value, str):
        normalized = value.strip().upper()
        if _SAFE_STATUS.fullmatch(normalized):
            return normalized
    return "UNKNOWN"


def _safe_references(value: object) -> list[str]:
    if not isinstance(value, list | tuple):
        return []
    return [
        reference
        for item in value
        if (reference := _reference(item, unknown=None)) is not None
    ]
