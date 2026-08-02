"""Kaynaklı etki değerlendirmesi ve kök neden hipotezi sözleşmesi.

`OPEN-027` gereği her etki bileşeni `Observed/Calculated/Estimated/Unknown`
durumunu, kaynağını, formülünü, veri zamanını ve güvenini taşır; desteklenmeyen
bileşenler tek bir toplam etki sayısında birleştirilmez. `OPEN-029` gereği yalnız
`DeterministicRule`, `IncidentSimilarity` ve auditli `ExpertInput` mekanizmaları
etkindir; `LLMAssisted` kapalıdır. Korelasyon doğrulanmış neden sayılmaz ve
insan tarafından girilen kök neden makine hipoteziyle değiştirilmez.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from enum import Enum
import re
from typing import Any, Iterable, Mapping, Sequence

from veri_kalitesi.lineage.errors import LineageValidationError
from veri_kalitesi.lineage.governance import canonical_digest


IMPACT_ASSESSMENT_VERSION = "DQ_SOURCED_IMPACT_V1"
ROOT_CAUSE_HYPOTHESIS_VERSION = "DQ_ROOT_CAUSE_HYPOTHESIS_V1"

MONETARY_COMPONENT_CODES = frozenset({"FINANCIAL", "RESOLUTION_COST"})
_SAFE_REFERENCE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@#=-]{0,255}")
_SAFE_CODE = re.compile(r"[A-Z][A-Z0-9_]{0,63}")


class ImpactEvidenceStatus(str, Enum):
    OBSERVED = "OBSERVED"
    CALCULATED = "CALCULATED"
    ESTIMATED = "ESTIMATED"
    UNKNOWN = "UNKNOWN"


SUPPORTED_AGGREGATION_STATUSES = (
    ImpactEvidenceStatus.OBSERVED,
    ImpactEvidenceStatus.CALCULATED,
)


class CausalityStatus(str, Enum):
    """`VerifiedCause` üretilmez; korelasyon yalnız hipotez doğurur."""

    HYPOTHESIS = "HYPOTHESIS"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    UNKNOWN = "UNKNOWN"


class RecommendationMechanism(str, Enum):
    DETERMINISTIC_RULE = "DETERMINISTIC_RULE"
    INCIDENT_SIMILARITY = "INCIDENT_SIMILARITY"
    EXPERT_INPUT = "EXPERT_INPUT"
    LLM_ASSISTED = "LLM_ASSISTED"


ENABLED_RECOMMENDATION_MECHANISMS = frozenset(
    {
        RecommendationMechanism.DETERMINISTIC_RULE,
        RecommendationMechanism.INCIDENT_SIMILARITY,
        RecommendationMechanism.EXPERT_INPUT,
    }
)


@dataclass(frozen=True)
class ImpactComponent:
    component_code: str
    status: ImpactEvidenceStatus
    value: Decimal | None = None
    unit: str | None = None
    source_ref: str | None = None
    formula_ref: str | None = None
    data_time: datetime | None = None
    confidence_ref: str | None = None


@dataclass(frozen=True)
class ImpactSourcePolicy:
    """Otoriter parasal kaynak ve onaylı formül referansları politikadan gelir."""

    version: str
    authoritative_monetary_source_refs: frozenset[str] = frozenset()
    approved_formula_refs: frozenset[str] = frozenset()


@dataclass(frozen=True)
class TimelineEvent:
    event_code: str
    occurred_at: datetime
    evidence_ref: str
    dataset_ref: str | None = None
    deterioration_observed: bool = False


@dataclass(frozen=True)
class SimilarIncident:
    incident_ref: str
    similarity_evidence_ref: str


@dataclass(frozen=True)
class Recommendation:
    recommendation_code: str
    mechanism: RecommendationMechanism
    mechanism_version: str | None
    evidence_refs: tuple[str, ...] = ()
    counter_evidence_refs: tuple[str, ...] = ()
    confidence_ref: str | None = None
    audit_event_ref: str | None = None


@dataclass(frozen=True)
class RecommendationPolicy:
    version: str
    minimum_evidence_count: int
    require_counter_evidence: bool = True


@dataclass(frozen=True)
class HumanRootCauseRecord:
    """`issues` modülündeki insan kaydı; hipotezle değiştirilmez."""

    issue_id: str
    recorded: bool
    evidence_reference_id: str | None = None


def assess_impact(
    components: Iterable[ImpactComponent],
    *,
    policy: ImpactSourcePolicy | None,
) -> dict[str, Any]:
    """Her bileşeni kaynak/formül/zaman/güvenle sınıflar, toplamayı ayırır."""

    normalized: list[dict[str, Any]] = []
    for component in components:
        _validate_component(component)
        normalized.append(_normalized_component(component, policy))
    document: dict[str, Any] = {
        "assessment_contract_version": IMPACT_ASSESSMENT_VERSION,
        "impact_policy_version": policy.version if policy is not None else None,
        "components": sorted(normalized, key=lambda item: item["component_code"]),
        "supported_totals_by_unit": _supported_totals(normalized),
        "estimated_component_codes": sorted(
            item["component_code"]
            for item in normalized
            if item["status"] == ImpactEvidenceStatus.ESTIMATED.value
        ),
        "unknown_component_codes": sorted(
            item["component_code"]
            for item in normalized
            if item["status"] == ImpactEvidenceStatus.UNKNOWN.value
        ),
        "total_impact_value": None,
        "total_impact_reason_code": "UNSUPPORTED_COMPONENTS_NOT_AGGREGATED",
    }
    document["digest"] = f"sha256:{canonical_digest(document)}"
    return document


def root_cause_hypothesis(
    *,
    subject_ref: str,
    timeline: Sequence[TimelineEvent],
    lineage_snapshot: Mapping[str, Any] | None,
    impact_assessment: Mapping[str, Any] | None,
    recommendations: Sequence[Recommendation] = (),
    recommendation_policy: RecommendationPolicy | None = None,
    human_root_cause: HumanRootCauseRecord | None = None,
    upstream_dataset_refs: Sequence[str] = (),
    downstream_dataset_refs: Sequence[str] = (),
    similar_incidents: Sequence[SimilarIncident] = (),
) -> dict[str, Any]:
    """Zaman çizgisi, lineage ve benzer olaylardan yalnız hipotez üretir."""

    _require_reference("subject_ref", subject_ref)
    ordered = sorted(timeline, key=lambda item: (item.occurred_at, item.event_code))
    for event in ordered:
        _require_code("timeline.event_code", event.event_code)
        _require_reference("timeline.evidence_ref", event.evidence_ref)
        _require_aware("timeline.occurred_at", event.occurred_at)
        if event.dataset_ref is not None:
            _require_reference("timeline.dataset_ref", event.dataset_ref)
    first_deterioration = next((event for event in ordered if event.deterioration_observed), None)
    accepted, rejected = _filter_recommendations(recommendations, recommendation_policy)
    coverage_status = (
        str(lineage_snapshot.get("coverage_status")) if lineage_snapshot is not None else "UNKNOWN"
    )
    reason_codes: list[str] = []
    if recommendation_policy is None:
        reason_codes.append("MISSING_RECOMMENDATION_POLICY")
    if first_deterioration is None:
        reason_codes.append("NO_OBSERVED_DETERIORATION")
    if lineage_snapshot is None:
        reason_codes.append("NO_LINEAGE_SNAPSHOT")
    elif coverage_status != "COMPLETE":
        reason_codes.append(f"LINEAGE_COVERAGE_{coverage_status}")
    if not accepted:
        reason_codes.append("NO_ELIGIBLE_RECOMMENDATION")
    status = _causality_status(
        policy=recommendation_policy,
        first_deterioration=first_deterioration,
        accepted_count=len(accepted),
    )
    document: dict[str, Any] = {
        "hypothesis_contract_version": ROOT_CAUSE_HYPOTHESIS_VERSION,
        "subject_ref": subject_ref,
        "causality_status": status.value,
        "causality_reason_codes": sorted(set(reason_codes)),
        "correlation_is_not_verified_cause": True,
        "first_observed_deterioration": (
            {
                "event_code": first_deterioration.event_code,
                "occurred_at": first_deterioration.occurred_at.isoformat(),
                "evidence_ref": first_deterioration.evidence_ref,
                "dataset_ref": first_deterioration.dataset_ref,
            }
            if first_deterioration is not None
            else None
        ),
        "timeline": [
            {
                "event_code": event.event_code,
                "occurred_at": event.occurred_at.isoformat(),
                "evidence_ref": event.evidence_ref,
                "dataset_ref": event.dataset_ref,
                "deterioration_observed": event.deterioration_observed,
            }
            for event in ordered
        ],
        "lineage_coverage_status": coverage_status,
        "lineage_snapshot_digest": (
            lineage_snapshot.get("digest") if lineage_snapshot is not None else None
        ),
        "upstream_dataset_refs": sorted(set(upstream_dataset_refs)),
        "downstream_dataset_refs": sorted(set(downstream_dataset_refs)),
        "similar_incidents": [
            {
                "incident_ref": incident.incident_ref,
                "similarity_evidence_ref": incident.similarity_evidence_ref,
            }
            for incident in sorted(similar_incidents, key=lambda item: item.incident_ref)
        ],
        "impact_assessment_digest": (
            impact_assessment.get("digest") if impact_assessment is not None else None
        ),
        "recommendation_policy_version": (
            recommendation_policy.version if recommendation_policy is not None else None
        ),
        "recommendations": accepted,
        "rejected_recommendations": rejected,
        "human_recorded_root_cause": {
            "issue_id": human_root_cause.issue_id,
            "recorded": human_root_cause.recorded,
            "evidence_reference_id": human_root_cause.evidence_reference_id,
            "overwritten_by_machine": False,
        }
        if human_root_cause is not None
        else None,
        "llm_assisted_enabled": False,
    }
    document["digest"] = f"sha256:{canonical_digest(document)}"
    return document


def _causality_status(
    *,
    policy: RecommendationPolicy | None,
    first_deterioration: TimelineEvent | None,
    accepted_count: int,
) -> CausalityStatus:
    if policy is None:
        return CausalityStatus.UNKNOWN
    if first_deterioration is None:
        return CausalityStatus.INSUFFICIENT_EVIDENCE
    if accepted_count == 0:
        return CausalityStatus.INSUFFICIENT_EVIDENCE
    return CausalityStatus.HYPOTHESIS


def _filter_recommendations(
    recommendations: Sequence[Recommendation],
    policy: RecommendationPolicy | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for recommendation in sorted(recommendations, key=lambda item: item.recommendation_code):
        _require_code("recommendation_code", recommendation.recommendation_code)
        reason_codes: list[str] = []
        if recommendation.mechanism not in ENABLED_RECOMMENDATION_MECHANISMS:
            reason_codes.append("MECHANISM_DISABLED")
        if policy is None:
            reason_codes.append("MISSING_RECOMMENDATION_POLICY")
        if not recommendation.mechanism_version:
            reason_codes.append("MISSING_MECHANISM_VERSION")
        if not recommendation.confidence_ref:
            reason_codes.append("MISSING_CONFIDENCE_REFERENCE")
        evidence = tuple(dict.fromkeys(recommendation.evidence_refs))
        for reference in (*evidence, *recommendation.counter_evidence_refs):
            _require_reference("recommendation.evidence_ref", reference)
        if policy is not None and len(evidence) < policy.minimum_evidence_count:
            reason_codes.append("INSUFFICIENT_MINIMUM_EVIDENCE")
        if (
            policy is not None
            and policy.require_counter_evidence
            and not recommendation.counter_evidence_refs
        ):
            reason_codes.append("MISSING_COUNTER_EVIDENCE")
        if (
            recommendation.mechanism is RecommendationMechanism.EXPERT_INPUT
            and not recommendation.audit_event_ref
        ):
            reason_codes.append("MISSING_AUDIT_REFERENCE")
        document = {
            "recommendation_code": recommendation.recommendation_code,
            "mechanism": recommendation.mechanism.value,
            "mechanism_version": recommendation.mechanism_version,
            "evidence_refs": list(evidence),
            "counter_evidence_refs": list(dict.fromkeys(recommendation.counter_evidence_refs)),
            "confidence_ref": recommendation.confidence_ref,
            "audit_event_ref": recommendation.audit_event_ref,
        }
        if reason_codes:
            rejected.append({**document, "rejection_reason_codes": sorted(set(reason_codes))})
        else:
            accepted.append(document)
    return accepted, rejected


def _normalized_component(
    component: ImpactComponent,
    policy: ImpactSourcePolicy | None,
) -> dict[str, Any]:
    status = component.status
    reason_codes: list[str] = []
    if component.value is None and status is not ImpactEvidenceStatus.UNKNOWN:
        status = ImpactEvidenceStatus.UNKNOWN
        reason_codes.append("MISSING_VALUE")
    if status is not ImpactEvidenceStatus.UNKNOWN:
        if not component.source_ref:
            status = ImpactEvidenceStatus.UNKNOWN
            reason_codes.append("MISSING_SOURCE")
        if component.data_time is None:
            status = ImpactEvidenceStatus.UNKNOWN
            reason_codes.append("MISSING_DATA_TIME")
        if not component.confidence_ref:
            status = ImpactEvidenceStatus.UNKNOWN
            reason_codes.append("MISSING_CONFIDENCE_REFERENCE")
    if status is ImpactEvidenceStatus.CALCULATED and component.formula_ref is None:
        status = ImpactEvidenceStatus.UNKNOWN
        reason_codes.append("MISSING_FORMULA")
    if component.component_code in MONETARY_COMPONENT_CODES:
        if policy is None:
            status = ImpactEvidenceStatus.UNKNOWN
            reason_codes.append("MISSING_IMPACT_POLICY")
        elif not _monetary_supported(component, policy):
            status = ImpactEvidenceStatus.UNKNOWN
            reason_codes.append("NO_AUTHORITATIVE_MONETARY_SOURCE")
    return {
        "component_code": component.component_code,
        "status": status.value,
        "declared_status": component.status.value,
        "value": (
            str(component.value)
            if status is not ImpactEvidenceStatus.UNKNOWN and component.value is not None
            else None
        ),
        "unit": component.unit if status is not ImpactEvidenceStatus.UNKNOWN else None,
        "source_ref": component.source_ref,
        "formula_ref": component.formula_ref,
        "data_time": (component.data_time.isoformat() if component.data_time is not None else None),
        "confidence_ref": component.confidence_ref,
        "reason_codes": sorted(set(reason_codes)),
    }


def _monetary_supported(
    component: ImpactComponent,
    policy: ImpactSourcePolicy,
) -> bool:
    if component.source_ref in policy.authoritative_monetary_source_refs:
        return True
    return component.formula_ref in policy.approved_formula_refs


def _supported_totals(
    components: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    supported_statuses = {status.value for status in SUPPORTED_AGGREGATION_STATUSES}
    totals: dict[str, dict[str, Any]] = {}
    for component in components:
        if component["status"] not in supported_statuses:
            continue
        unit = component["unit"]
        value = component["value"]
        if unit is None or value is None:
            continue
        bucket = totals.setdefault(
            unit,
            {"total": Decimal("0"), "component_codes": []},
        )
        bucket["total"] += Decimal(value)
        bucket["component_codes"].append(component["component_code"])
    return {
        unit: {
            "total": str(bucket["total"]),
            "component_codes": sorted(bucket["component_codes"]),
            "aggregated_statuses": sorted(supported_statuses),
        }
        for unit, bucket in sorted(totals.items())
    }


def _validate_component(component: ImpactComponent) -> None:
    _require_code("component_code", component.component_code)
    if not isinstance(component.status, ImpactEvidenceStatus):
        raise LineageValidationError("Impact component status is not supported.")
    if component.value is not None:
        if not isinstance(component.value, Decimal):
            raise LineageValidationError("Impact component value must be Decimal.")
        try:
            Decimal(str(component.value))
        except InvalidOperation as exc:  # pragma: no cover - defensive
            raise LineageValidationError("Impact component value is invalid.") from exc
    if component.unit is not None:
        _require_code("unit", component.unit)
    for field_name, value in (
        ("source_ref", component.source_ref),
        ("formula_ref", component.formula_ref),
        ("confidence_ref", component.confidence_ref),
    ):
        if value is not None:
            _require_reference(field_name, value)
    if component.data_time is not None:
        _require_aware("data_time", component.data_time)


def _require_aware(field_name: str, value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise LineageValidationError(f"{field_name} must be timezone-aware.")


def _require_reference(field_name: str, value: str) -> None:
    if not isinstance(value, str) or not _SAFE_REFERENCE.fullmatch(value):
        raise LineageValidationError(f"{field_name} must be a safe evidence reference.")


def _require_code(field_name: str, value: str) -> None:
    if not isinstance(value, str) or not _SAFE_CODE.fullmatch(value):
        raise LineageValidationError(f"{field_name} must be an upper-case code.")
