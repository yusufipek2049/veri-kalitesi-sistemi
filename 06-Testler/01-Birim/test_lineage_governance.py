"""DQ-CAP-PROTOTYPE-04 sentetik lineage, sahiplik profili ve etki hipotezi."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from veri_kalitesi.data_protection.inventory import DataProcessingInventory
from veri_kalitesi.data_sources.models import Criticality, Dataset
from veri_kalitesi.lineage import (
    CausalityStatus,
    ColumnLineageEdge,
    GovernanceAssetKind,
    GovernanceAttributeStatus,
    GovernanceProfileStatus,
    GovernanceReference,
    GovernanceRoutingPolicy,
    HumanRootCauseRecord,
    ImpactComponent,
    ImpactEvidenceStatus,
    ImpactSourcePolicy,
    LineageCoverageStatus,
    LineageDatasetRef,
    LineageEvent,
    LineageEventType,
    LineageValidationError,
    Recommendation,
    RecommendationMechanism,
    RecommendationPolicy,
    RoutingStatus,
    SimilarIncident,
    TimelineEvent,
    assess_impact,
    build_governance_profile,
    dataset_criticality_reference,
    dataset_owner_reference,
    downstream_dataset_refs,
    governance_profile_snapshot,
    governance_projection,
    inventory_owner_reference,
    inventory_retention_reference,
    lineage_snapshot,
    openlineage_document,
    prov_mapping,
    resolve_active_profile,
    resolve_attribute_references,
    root_cause_hypothesis,
    routing_decision,
    unknown_reference,
    upstream_dataset_refs,
)


NOW = datetime(2026, 7, 30, 12, 0, tzinfo=timezone.utc)
EARLIER = NOW - timedelta(days=30)


# --- A. Sürümlü yönetişim profili (DQ-CAP-010) -------------------------------


def test_ac_01_versioned_profile_carries_effectivity_range() -> None:
    first = _profile(version_number=1, effective_from=EARLIER, effective_to=NOW)
    second = _profile(version_number=2, effective_from=NOW, effective_to=None)

    assert resolve_active_profile((first, second), NOW).profile is second
    assert (
        resolve_active_profile((first, second), NOW - timedelta(days=1)).profile
        is first
    )
    snapshot = governance_profile_snapshot(second)
    assert snapshot["profile_contract_version"] == "DQ_ASSET_GOVERNANCE_PROFILE_V1"
    assert snapshot["version_number"] == 2
    assert snapshot["effective_from"] == NOW.isoformat()
    assert snapshot["effective_to"] is None
    assert snapshot["digest"] == governance_profile_snapshot(second)["digest"]


def test_ac_01_overlapping_or_absent_effectivity_fails_closed() -> None:
    overlapping = (
        _profile(version_number=1, effective_from=EARLIER, effective_to=None),
        _profile(version_number=2, effective_from=NOW, effective_to=None),
    )

    overlap = resolve_active_profile(overlapping, NOW)
    absent = resolve_active_profile(overlapping, EARLIER - timedelta(days=1))

    assert overlap.status is GovernanceProfileStatus.AMBIGUOUS_EFFECTIVITY
    assert overlap.reason_codes == ("OVERLAPPING_EFFECTIVITY_RANGE",)
    assert absent.status is GovernanceProfileStatus.NO_ACTIVE_PROFILE
    assert routing_decision(overlap.profile, _routing_policy()).status is (
        RoutingStatus.FAIL_CLOSED
    )


def test_ac_01_routing_is_fail_closed_without_policy_or_required_field() -> None:
    profile = _profile(version_number=1, effective_from=EARLIER)
    without_business_unit = build_governance_profile(
        asset_ref="dataset-1",
        asset_kind=GovernanceAssetKind.DATASET,
        version_number=1,
        effective_from=EARLIER,
        attributes={
            "data_owner": dataset_owner_reference(_dataset()),
            "technical_owner": GovernanceReference(
                source_system="SYNTHETIC_GOVERNANCE_REGISTRY",
                field_path="synthetic_registry.technical_owner",
                value="tech-owner-1",
            ),
            "business_unit": unknown_reference(
                "SYNTHETIC_GOVERNANCE_REGISTRY",
                "synthetic_registry.business_unit",
            ),
        },
    )

    assert routing_decision(profile, None).reason_codes == ("MISSING_ROUTING_POLICY",)
    assert routing_decision(None, _routing_policy()).reason_codes == (
        "NO_ACTIVE_GOVERNANCE_PROFILE",
    )
    missing = routing_decision(without_business_unit, _routing_policy())
    assert missing.status is RoutingStatus.FAIL_CLOSED
    assert missing.assignee_ref is None
    assert missing.reason_codes == ("MISSING_BUSINESS_UNIT",)
    assert routing_decision(profile, _unsupported_routing_policy()).reason_codes == (
        "ASSIGNEE_ATTRIBUTE_NOT_REQUIRED_BY_POLICY",
        "UNSUPPORTED_ROUTING_ATTRIBUTE_INVENTED_FIELD",
    )

    assigned = routing_decision(profile, _routing_policy())
    assert assigned.status is RoutingStatus.ASSIGNED
    assert assigned.assignee_ref == "owner-1"
    assert assigned.policy_version == "ROUTING_POLICY_V1"


def test_ac_02_existing_owner_surfaces_are_referenced_not_copied() -> None:
    dataset = _dataset()
    inventory = _inventory(data_owner_id="owner-1")

    dataset_reference = dataset_owner_reference(dataset)
    inventory_reference = inventory_owner_reference(inventory)
    resolution = resolve_attribute_references(
        (dataset_reference, inventory_reference)
    )

    assert dataset_reference.field_path == "data_sources.Dataset.owner_user_id"
    assert inventory_reference.field_path == (
        "data_protection.DataProcessingInventory.data_owner_id"
    )
    assert (
        inventory_retention_reference(inventory).field_path
        == "data_protection.DataProcessingInventory.retention_policy_id"
    )
    assert resolution.status is GovernanceAttributeStatus.REFERENCED
    assert resolution.reference is dataset_reference


def test_ac_02_conflicting_owner_records_do_not_create_second_owner() -> None:
    conflicting = (
        dataset_owner_reference(_dataset()),
        inventory_owner_reference(_inventory(data_owner_id="owner-2")),
    )
    profile = build_governance_profile(
        asset_ref="dataset-1",
        asset_kind=GovernanceAssetKind.DATASET,
        version_number=1,
        effective_from=EARLIER,
        attributes={
            "data_owner": conflicting,
            "technical_owner": GovernanceReference(
                source_system="SYNTHETIC_GOVERNANCE_REGISTRY",
                field_path="synthetic_registry.technical_owner",
                value="tech-owner-1",
            ),
            "business_unit": GovernanceReference(
                source_system="SYNTHETIC_GOVERNANCE_REGISTRY",
                field_path="synthetic_registry.business_unit",
                value="unit-1",
            ),
        },
    )

    resolution = resolve_attribute_references(conflicting)
    snapshot = governance_profile_snapshot(profile)

    assert resolution.status is GovernanceAttributeStatus.CONFLICT
    assert resolution.reference is None
    assert resolution.conflicting_field_paths == (
        "data_protection.DataProcessingInventory.data_owner_id",
        "data_sources.Dataset.owner_user_id",
    )
    assert snapshot["attributes"]["data_owner"]["status"] == "CONFLICT"
    assert snapshot["attributes"]["data_owner"]["value"] is None
    assert snapshot["attributes"]["data_owner"]["conflicting_field_paths"] == [
        "data_protection.DataProcessingInventory.data_owner_id",
        "data_sources.Dataset.owner_user_id",
    ]
    assert routing_decision(profile, _routing_policy()).reason_codes == (
        "CONFLICTING_DATA_OWNER",
    )


def test_ac_09_profile_rejects_secret_and_unsupported_attributes() -> None:
    with pytest.raises(LineageValidationError, match="secret"):
        build_governance_profile(
            asset_ref="dataset-1",
            asset_kind=GovernanceAssetKind.DATASET,
            version_number=1,
            effective_from=EARLIER,
            attributes={
                "data_owner": GovernanceReference(
                    source_system="SYNTHETIC_GOVERNANCE_REGISTRY",
                    field_path="synthetic_registry.data_owner",
                    value="secret://vault/owner",
                )
            },
        )
    with pytest.raises(LineageValidationError, match="Unsupported"):
        build_governance_profile(
            asset_ref="dataset-1",
            asset_kind=GovernanceAssetKind.DATASET,
            version_number=1,
            effective_from=EARLIER,
            attributes={"invented_weight": unknown_reference("X", "y")},
        )
    with pytest.raises(LineageValidationError, match="increasing"):
        build_governance_profile(
            asset_ref="dataset-1",
            asset_kind=GovernanceAssetKind.DATASET,
            version_number=1,
            effective_from=NOW,
            effective_to=EARLIER,
            attributes={},
        )


def test_ac_09_projection_keeps_unsourced_fields_unknown() -> None:
    dataset = _dataset()
    with_criticality = build_governance_profile(
        asset_ref="dataset-1",
        asset_kind=GovernanceAssetKind.DATASET,
        version_number=3,
        effective_from=EARLIER,
        attributes={"criticality": dataset_criticality_reference(dataset)},
    )

    projection = governance_projection(
        resolve_active_profile((with_criticality,), NOW)
    )
    empty = governance_projection(resolve_active_profile((), NOW))

    assert projection["critical_asset_status"] == "HIGH"
    assert projection["risk_status"] == "UNKNOWN"
    assert projection["sla_status"] == "UNKNOWN"
    assert projection["governance_version"] == (
        "DQ_ASSET_GOVERNANCE_PROFILE_V1:dataset-1:3"
    )
    assert empty["critical_asset_status"] == "UNKNOWN"
    assert empty["governance_reason_codes"] == ["NO_ACTIVE_GOVERNANCE_PROFILE"]


# --- B. Lineage olayı ve kapsama (DQ-CAP-007) -------------------------------


def test_ac_03_openlineage_document_and_prov_mapping_are_deterministic() -> None:
    event = _event()

    document = openlineage_document(event)
    prov = prov_mapping((event,))

    assert document["eventType"] == "COMPLETE"
    assert document["run"] == {"runId": "run-1"}
    assert document["job"] == {"namespace": "synthetic", "name": "load-customer"}
    assert document["inputs"] == [{"namespace": "synthetic", "name": "raw.customer"}]
    assert document["outputs"][0]["facets"]["columnLineage"]["fields"] == {
        "customer_id": {
            "inputFields": [
                {
                    "namespace": "synthetic",
                    "name": "raw.customer",
                    "field": "id",
                    "transformation": "transform:identity",
                }
            ]
        }
    }
    assert document["contractVersion"] == "DQ_LINEAGE_EVENT_V1"
    assert prov["activities"] == ["run:run-1"]
    assert "dataset:synthetic:curated.customer" in prov["entities"]
    assert ["dataset:synthetic:curated.customer", "run:run-1"] in prov["wasGeneratedBy"]
    assert prov["wasDerivedFrom"] == [
        [
            "column:synthetic:curated.customer#customer_id",
            "column:synthetic:raw.customer#id",
        ]
    ]


def test_ac_03_snapshot_is_immutable_and_records_complete_coverage() -> None:
    snapshot = lineage_snapshot(
        (_event(),),
        as_of=NOW,
        freshness_limit=timedelta(days=1),
        freshness_policy_version="LINEAGE_FRESHNESS_V1",
    )

    assert snapshot["coverage_status"] == LineageCoverageStatus.COMPLETE.value
    assert snapshot["coverage_reason_codes"] == []
    assert snapshot["freshness_policy_version"] == "LINEAGE_FRESHNESS_V1"
    assert snapshot["digest"].startswith("sha256:")
    assert snapshot["digest"] == lineage_snapshot(
        (_event(),),
        as_of=NOW,
        freshness_limit=timedelta(days=1),
        freshness_policy_version="LINEAGE_FRESHNESS_V1",
    )["digest"]
    assert upstream_dataset_refs(snapshot, "synthetic:curated.customer") == (
        "synthetic:raw.customer",
    )
    assert downstream_dataset_refs(snapshot, "synthetic:raw.customer") == (
        "synthetic:curated.customer",
    )


def test_ac_03_missing_or_stale_coverage_is_recorded_not_hidden() -> None:
    without_columns = _event(column_edges=())
    stale = _event(observed_at=NOW - timedelta(days=10))

    incomplete = lineage_snapshot(
        (without_columns,), as_of=NOW, freshness_limit=timedelta(days=1)
    )
    stale_snapshot = lineage_snapshot(
        (stale,), as_of=NOW, freshness_limit=timedelta(days=1)
    )
    without_policy = lineage_snapshot((_event(),), as_of=NOW, freshness_limit=None)
    empty = lineage_snapshot((), as_of=NOW, freshness_limit=timedelta(days=1))

    assert incomplete["coverage_status"] == LineageCoverageStatus.INCOMPLETE.value
    assert incomplete["coverage_reason_codes"] == ["MISSING_COLUMN_LINEAGE"]
    assert stale_snapshot["coverage_status"] == LineageCoverageStatus.STALE.value
    assert "STALE_LINEAGE_COVERAGE" in stale_snapshot["coverage_reason_codes"]
    assert without_policy["coverage_status"] == LineageCoverageStatus.UNKNOWN.value
    assert without_policy["coverage_reason_codes"] == ["MISSING_FRESHNESS_POLICY"]
    assert empty["coverage_reason_codes"] == [
        "NO_LINEAGE_EVENT",
    ]


def test_ac_03_event_validation_rejects_unsafe_or_undeclared_references() -> None:
    with pytest.raises(LineageValidationError, match="URI"):
        openlineage_document(_event(producer="not-a-uri"))
    with pytest.raises(LineageValidationError, match="declared as an event output"):
        openlineage_document(
            _event(
                outputs=(LineageDatasetRef("synthetic", "other.customer"),),
            )
        )


# --- Kaynaklı etki (OPEN-027) ----------------------------------------------


def test_ac_05_impact_components_carry_source_formula_time_and_confidence() -> None:
    assessment = assess_impact(
        (
            ImpactComponent(
                component_code="RECORD_COUNT",
                status=ImpactEvidenceStatus.OBSERVED,
                value=Decimal("1200"),
                unit="RECORDS",
                source_ref="execution:exec-1",
                data_time=NOW,
                confidence_ref="confidence:observed-v1",
            ),
            ImpactComponent(
                component_code="DOWNSTREAM_ASSET",
                status=ImpactEvidenceStatus.CALCULATED,
                value=Decimal("3"),
                unit="RECORDS",
                source_ref="lineage:snapshot-1",
                formula_ref="formula:downstream-count-v1",
                data_time=NOW,
                confidence_ref="confidence:calculated-v1",
            ),
            ImpactComponent(
                component_code="CUSTOMER",
                status=ImpactEvidenceStatus.ESTIMATED,
                value=Decimal("40"),
                unit="RECORDS",
                source_ref="estimate:panel-v1",
                data_time=NOW,
                confidence_ref="confidence:estimated-v1",
            ),
            ImpactComponent(
                component_code="REGULATORY",
                status=ImpactEvidenceStatus.UNKNOWN,
            ),
        ),
        policy=_impact_policy(),
    )

    by_code = {item["component_code"]: item for item in assessment["components"]}
    assert by_code["RECORD_COUNT"]["status"] == "OBSERVED"
    assert by_code["DOWNSTREAM_ASSET"]["formula_ref"] == "formula:downstream-count-v1"
    assert by_code["CUSTOMER"]["status"] == "ESTIMATED"
    assert by_code["REGULATORY"]["status"] == "UNKNOWN"
    assert assessment["supported_totals_by_unit"]["RECORDS"]["total"] == "1203"
    assert assessment["supported_totals_by_unit"]["RECORDS"]["component_codes"] == [
        "DOWNSTREAM_ASSET",
        "RECORD_COUNT",
    ]
    assert assessment["estimated_component_codes"] == ["CUSTOMER"]
    assert assessment["unknown_component_codes"] == ["REGULATORY"]
    assert assessment["total_impact_value"] is None
    assert assessment["total_impact_reason_code"] == (
        "UNSUPPORTED_COMPONENTS_NOT_AGGREGATED"
    )


def test_ac_05_monetary_value_without_authority_or_formula_is_unknown() -> None:
    unsourced = assess_impact(
        (
            ImpactComponent(
                component_code="FINANCIAL",
                status=ImpactEvidenceStatus.CALCULATED,
                value=Decimal("100000"),
                unit="TRY",
                source_ref="spreadsheet:local",
                formula_ref="formula:guess",
                data_time=NOW,
                confidence_ref="confidence:calculated-v1",
            ),
        ),
        policy=_impact_policy(),
    )
    without_policy = assess_impact(
        (
            ImpactComponent(
                component_code="FINANCIAL",
                status=ImpactEvidenceStatus.OBSERVED,
                value=Decimal("100000"),
                unit="TRY",
                source_ref="finance:authoritative-v1",
                data_time=NOW,
                confidence_ref="confidence:observed-v1",
            ),
        ),
        policy=None,
    )
    authoritative = assess_impact(
        (
            ImpactComponent(
                component_code="FINANCIAL",
                status=ImpactEvidenceStatus.OBSERVED,
                value=Decimal("100000"),
                unit="TRY",
                source_ref="finance:authoritative-v1",
                data_time=NOW,
                confidence_ref="confidence:observed-v1",
            ),
        ),
        policy=_impact_policy(),
    )

    assert unsourced["components"][0]["status"] == "UNKNOWN"
    assert unsourced["components"][0]["value"] is None
    assert unsourced["components"][0]["reason_codes"] == [
        "NO_AUTHORITATIVE_MONETARY_SOURCE"
    ]
    assert without_policy["components"][0]["reason_codes"] == ["MISSING_IMPACT_POLICY"]
    assert authoritative["components"][0]["status"] == "OBSERVED"
    assert authoritative["supported_totals_by_unit"]["TRY"]["total"] == "100000"


def test_ac_05_component_without_confidence_or_data_time_is_unknown() -> None:
    assessment = assess_impact(
        (
            ImpactComponent(
                component_code="OPERATIONAL",
                status=ImpactEvidenceStatus.OBSERVED,
                value=Decimal("5"),
                unit="HOURS",
                source_ref="execution:exec-1",
            ),
        ),
        policy=_impact_policy(),
    )

    component = assessment["components"][0]
    assert component["status"] == "UNKNOWN"
    assert component["declared_status"] == "OBSERVED"
    assert component["reason_codes"] == [
        "MISSING_CONFIDENCE_REFERENCE",
        "MISSING_DATA_TIME",
    ]
    assert assessment["supported_totals_by_unit"] == {}


# --- Kök neden hipotezi ve öneri (OPEN-029) --------------------------------


def test_ac_04_root_cause_stays_hypothesis_and_keeps_human_record() -> None:
    snapshot = lineage_snapshot(
        (_event(),), as_of=NOW, freshness_limit=timedelta(days=1)
    )

    hypothesis = root_cause_hypothesis(
        subject_ref="issue-1",
        timeline=(
            TimelineEvent(
                event_code="DEPLOY",
                occurred_at=NOW - timedelta(hours=3),
                evidence_ref="deploy:release-1",
            ),
            TimelineEvent(
                event_code="SCORE_DROP",
                occurred_at=NOW - timedelta(hours=2),
                evidence_ref="score:score-1",
                dataset_ref="synthetic:curated.customer",
                deterioration_observed=True,
            ),
        ),
        lineage_snapshot=snapshot,
        impact_assessment=None,
        recommendations=(_recommendation(),),
        recommendation_policy=_recommendation_policy(),
        human_root_cause=HumanRootCauseRecord(
            issue_id="issue-1",
            recorded=True,
            evidence_reference_id="evidence-1",
        ),
        upstream_dataset_refs=upstream_dataset_refs(
            snapshot, "synthetic:curated.customer"
        ),
        downstream_dataset_refs=(),
        similar_incidents=(
            SimilarIncident(
                incident_ref="issue-0",
                similarity_evidence_ref="similarity:profile-v1",
            ),
        ),
    )

    assert hypothesis["causality_status"] == CausalityStatus.HYPOTHESIS.value
    assert hypothesis["correlation_is_not_verified_cause"] is True
    assert "VERIFIED" not in hypothesis["causality_status"]
    assert hypothesis["first_observed_deterioration"]["event_code"] == "SCORE_DROP"
    assert hypothesis["upstream_dataset_refs"] == ["synthetic:raw.customer"]
    assert hypothesis["human_recorded_root_cause"] == {
        "issue_id": "issue-1",
        "recorded": True,
        "evidence_reference_id": "evidence-1",
        "overwritten_by_machine": False,
    }
    assert hypothesis["llm_assisted_enabled"] is False
    assert hypothesis["lineage_snapshot_digest"] == snapshot["digest"]
    assert hypothesis["digest"].startswith("sha256:")


def test_ac_04_missing_deterioration_or_policy_never_produces_hypothesis() -> None:
    without_policy = root_cause_hypothesis(
        subject_ref="issue-1",
        timeline=(),
        lineage_snapshot=None,
        impact_assessment=None,
        recommendations=(_recommendation(),),
        recommendation_policy=None,
    )
    without_deterioration = root_cause_hypothesis(
        subject_ref="issue-1",
        timeline=(
            TimelineEvent(
                event_code="DEPLOY",
                occurred_at=NOW,
                evidence_ref="deploy:release-1",
            ),
        ),
        lineage_snapshot=None,
        impact_assessment=None,
        recommendations=(_recommendation(),),
        recommendation_policy=_recommendation_policy(),
    )

    assert without_policy["causality_status"] == CausalityStatus.UNKNOWN.value
    assert "MISSING_RECOMMENDATION_POLICY" in without_policy["causality_reason_codes"]
    assert without_policy["recommendations"] == []
    assert (
        without_deterioration["causality_status"]
        == CausalityStatus.INSUFFICIENT_EVIDENCE.value
    )
    assert (
        "NO_OBSERVED_DETERIORATION"
        in without_deterioration["causality_reason_codes"]
    )
    assert "NO_LINEAGE_SNAPSHOT" in without_deterioration["causality_reason_codes"]


def test_ac_06_only_enabled_mechanisms_with_full_evidence_are_published() -> None:
    hypothesis = root_cause_hypothesis(
        subject_ref="issue-1",
        timeline=(
            TimelineEvent(
                event_code="SCORE_DROP",
                occurred_at=NOW,
                evidence_ref="score:score-1",
                deterioration_observed=True,
            ),
        ),
        lineage_snapshot=None,
        impact_assessment=None,
        recommendations=(
            _recommendation(),
            _recommendation(
                recommendation_code="LLM_SUGGESTION",
                mechanism=RecommendationMechanism.LLM_ASSISTED,
            ),
            _recommendation(
                recommendation_code="EXPERT_NO_AUDIT",
                mechanism=RecommendationMechanism.EXPERT_INPUT,
                audit_event_ref=None,
            ),
            _recommendation(
                recommendation_code="THIN_EVIDENCE",
                evidence_refs=("evidence:one",),
                counter_evidence_refs=(),
                confidence_ref=None,
                mechanism_version=None,
            ),
        ),
        recommendation_policy=_recommendation_policy(),
    )

    accepted = [item["recommendation_code"] for item in hypothesis["recommendations"]]
    rejected = {
        item["recommendation_code"]: item["rejection_reason_codes"]
        for item in hypothesis["rejected_recommendations"]
    }

    assert accepted == ["DETERMINISTIC_FIX"]
    assert hypothesis["recommendations"][0]["mechanism_version"] == "RULE_MECHANISM_V1"
    assert hypothesis["recommendations"][0]["counter_evidence_refs"] == [
        "counter:profile-stable-v1"
    ]
    assert rejected["LLM_SUGGESTION"] == ["MECHANISM_DISABLED"]
    assert rejected["EXPERT_NO_AUDIT"] == ["MISSING_AUDIT_REFERENCE"]
    assert rejected["THIN_EVIDENCE"] == [
        "INSUFFICIENT_MINIMUM_EVIDENCE",
        "MISSING_CONFIDENCE_REFERENCE",
        "MISSING_COUNTER_EVIDENCE",
        "MISSING_MECHANISM_VERSION",
    ]


def test_ac_06_incident_similarity_mechanism_requires_full_evidence() -> None:
    """IncidentSimilarity mekanizması kabul edilir; kanıt eksikse reddedilir."""
    accepted_hypothesis = root_cause_hypothesis(
        subject_ref="issue-1",
        timeline=(
            TimelineEvent(
                event_code="SCORE_DROP",
                occurred_at=NOW,
                evidence_ref="score:score-1",
                deterioration_observed=True,
            ),
        ),
        lineage_snapshot=None,
        impact_assessment=None,
        recommendations=(
            _recommendation(
                recommendation_code="SIMILAR_INCIDENT_FIX",
                mechanism=RecommendationMechanism.INCIDENT_SIMILARITY,
                mechanism_version="SIMILARITY_MECHANISM_V1",
                evidence_refs=("evidence:incident-v1", "evidence:profile-v1"),
                counter_evidence_refs=("counter:no-recurrence-v1",),
                confidence_ref="confidence:similarity-v1",
            ),
        ),
        recommendation_policy=_recommendation_policy(),
    )
    rejected_hypothesis = root_cause_hypothesis(
        subject_ref="issue-1",
        timeline=(
            TimelineEvent(
                event_code="SCORE_DROP",
                occurred_at=NOW,
                evidence_ref="score:score-1",
                deterioration_observed=True,
            ),
        ),
        lineage_snapshot=None,
        impact_assessment=None,
        recommendations=(
            _recommendation(
                recommendation_code="SIMILAR_NO_COUNTER",
                mechanism=RecommendationMechanism.INCIDENT_SIMILARITY,
                mechanism_version="SIMILARITY_MECHANISM_V1",
                evidence_refs=("evidence:incident-v1", "evidence:profile-v1"),
                counter_evidence_refs=(),
                confidence_ref="confidence:similarity-v1",
            ),
        ),
        recommendation_policy=_recommendation_policy(),
    )

    assert [
        item["recommendation_code"]
        for item in accepted_hypothesis["recommendations"]
    ] == ["SIMILAR_INCIDENT_FIX"]
    assert accepted_hypothesis["recommendations"][0]["mechanism"] == "INCIDENT_SIMILARITY"
    assert rejected_hypothesis["recommendations"] == []
    assert rejected_hypothesis["rejected_recommendations"][0]["rejection_reason_codes"] == [
        "MISSING_COUNTER_EVIDENCE"
    ]


def test_ac_06_expert_input_requires_audit_event_ref() -> None:
    """ExpertInput mekanizması audit_event_ref ile kabul edilir; yoksa reddedilir."""
    with_audit = root_cause_hypothesis(
        subject_ref="issue-1",
        timeline=(
            TimelineEvent(
                event_code="SCORE_DROP",
                occurred_at=NOW,
                evidence_ref="score:score-1",
                deterioration_observed=True,
            ),
        ),
        lineage_snapshot=None,
        impact_assessment=None,
        recommendations=(
            _recommendation(
                recommendation_code="EXPERT_REVIEW",
                mechanism=RecommendationMechanism.EXPERT_INPUT,
                mechanism_version="EXPERT_MECHANISM_V1",
                evidence_refs=("evidence:expert-v1", "evidence:profile-v1"),
                counter_evidence_refs=("counter:expert-stable-v1",),
                confidence_ref="confidence:expert-v1",
                audit_event_ref="audit:expert-event-1",
            ),
        ),
        recommendation_policy=_recommendation_policy(),
    )
    without_audit = root_cause_hypothesis(
        subject_ref="issue-1",
        timeline=(
            TimelineEvent(
                event_code="SCORE_DROP",
                occurred_at=NOW,
                evidence_ref="score:score-1",
                deterioration_observed=True,
            ),
        ),
        lineage_snapshot=None,
        impact_assessment=None,
        recommendations=(
            _recommendation(
                recommendation_code="EXPERT_NO_AUDIT",
                mechanism=RecommendationMechanism.EXPERT_INPUT,
                mechanism_version="EXPERT_MECHANISM_V1",
                evidence_refs=("evidence:expert-v1", "evidence:profile-v1"),
                counter_evidence_refs=("counter:expert-stable-v1",),
                confidence_ref="confidence:expert-v1",
                audit_event_ref=None,
            ),
        ),
        recommendation_policy=_recommendation_policy(),
    )

    assert [
        item["recommendation_code"] for item in with_audit["recommendations"]
    ] == ["EXPERT_REVIEW"]
    assert with_audit["recommendations"][0]["audit_event_ref"] == "audit:expert-event-1"
    assert without_audit["recommendations"] == []
    assert without_audit["rejected_recommendations"][0]["rejection_reason_codes"] == [
        "MISSING_AUDIT_REFERENCE"
    ]


# --- yardımcılar ------------------------------------------------------------


def _dataset() -> Dataset:
    return Dataset(
        data_source_id="source-1",
        namespace="synthetic",
        name="customer",
        criticality=Criticality.HIGH,
        owner_user_id="owner-1",
        dataset_id="dataset-1",
    )


def _inventory(*, data_owner_id: str) -> DataProcessingInventory:
    return DataProcessingInventory(
        data_field_id="field-1",
        version_number=1,
        processing_purpose="quality-monitoring",
        legal_basis_reference="legal:contract-v1",
        data_owner_id=data_owner_id,
        retention_policy_id="retention:policy-v1",
        access_role_codes=("DATA_OWNER",),
        cross_border_transfer=False,
        recorded_at=NOW,
    )


def _profile(
    *,
    version_number: int,
    effective_from: datetime,
    effective_to: datetime | None = None,
):
    return build_governance_profile(
        asset_ref="dataset-1",
        asset_kind=GovernanceAssetKind.DATASET,
        version_number=version_number,
        effective_from=effective_from,
        effective_to=effective_to,
        attributes={
            "data_owner": dataset_owner_reference(_dataset()),
            "technical_owner": GovernanceReference(
                source_system="SYNTHETIC_GOVERNANCE_REGISTRY",
                field_path="synthetic_registry.technical_owner",
                value="tech-owner-1",
            ),
            "business_unit": GovernanceReference(
                source_system="SYNTHETIC_GOVERNANCE_REGISTRY",
                field_path="synthetic_registry.business_unit",
                value="unit-1",
            ),
            "criticality": dataset_criticality_reference(_dataset()),
            "retention": inventory_retention_reference(
                _inventory(data_owner_id="owner-1")
            ),
        },
        related_asset_refs=("dataset-2",),
    )


def _routing_policy() -> GovernanceRoutingPolicy:
    return GovernanceRoutingPolicy(
        version="ROUTING_POLICY_V1",
        required_attribute_keys=("data_owner", "technical_owner", "business_unit"),
        assignee_attribute_key="data_owner",
    )


def _unsupported_routing_policy() -> GovernanceRoutingPolicy:
    return GovernanceRoutingPolicy(
        version="ROUTING_POLICY_V1",
        required_attribute_keys=("invented_field",),
        assignee_attribute_key="data_owner",
    )


def _impact_policy() -> ImpactSourcePolicy:
    return ImpactSourcePolicy(
        version="IMPACT_POLICY_V1",
        authoritative_monetary_source_refs=frozenset({"finance:authoritative-v1"}),
        approved_formula_refs=frozenset({"formula:approved-loss-v1"}),
    )


def _recommendation_policy() -> RecommendationPolicy:
    return RecommendationPolicy(
        version="RECOMMENDATION_POLICY_V1",
        minimum_evidence_count=2,
        require_counter_evidence=True,
    )


def _recommendation(
    *,
    recommendation_code: str = "DETERMINISTIC_FIX",
    mechanism: RecommendationMechanism = RecommendationMechanism.DETERMINISTIC_RULE,
    mechanism_version: str | None = "RULE_MECHANISM_V1",
    evidence_refs: tuple[str, ...] = ("evidence:rule-v1", "evidence:profile-v1"),
    counter_evidence_refs: tuple[str, ...] = ("counter:profile-stable-v1",),
    confidence_ref: str | None = "confidence:deterministic-v1",
    audit_event_ref: str | None = "audit:event-1",
) -> Recommendation:
    return Recommendation(
        recommendation_code=recommendation_code,
        mechanism=mechanism,
        mechanism_version=mechanism_version,
        evidence_refs=evidence_refs,
        counter_evidence_refs=counter_evidence_refs,
        confidence_ref=confidence_ref,
        audit_event_ref=audit_event_ref,
    )


def _event(
    *,
    producer: str = "https://veri-kalitesi.local/synthetic-lineage/producer",
    observed_at: datetime = NOW,
    outputs: tuple[LineageDatasetRef, ...] | None = None,
    column_edges: tuple[ColumnLineageEdge, ...] | None = None,
) -> LineageEvent:
    curated = LineageDatasetRef("synthetic", "curated.customer")
    raw = LineageDatasetRef("synthetic", "raw.customer")
    default_edges = (
        ColumnLineageEdge(
            output_dataset=curated,
            output_field="customer_id",
            input_dataset=raw,
            input_field="id",
            transformation_ref="transform:identity",
        ),
    )
    return LineageEvent(
        event_type=LineageEventType.COMPLETE,
        event_time=NOW - timedelta(hours=1),
        run_id="run-1",
        job_namespace="synthetic",
        job_name="load-customer",
        producer=producer,
        schema_url="https://openlineage.io/spec/RunEvent.json",
        source_authority="SYNTHETIC_LINEAGE_REGISTRY",
        observed_at=observed_at,
        inputs=(raw,),
        outputs=outputs if outputs is not None else (curated,),
        column_edges=default_edges if column_edges is None else column_edges,
    )
