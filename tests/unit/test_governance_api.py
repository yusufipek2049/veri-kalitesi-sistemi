"""Yönetişim görev merkezi API testleri."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from veri_kalitesi.api import DevelopmentActorContextResolver, create_dashboard_api
from veri_kalitesi.api.service_groups import ActorResolverIdentity, ApiOptions, GovernanceServices
from veri_kalitesi.audit.models import (
    AuditFailureMode,
    AuditFailurePolicy,
    AuditRedactionPolicy,
)
from veri_kalitesi.audit.redaction import AuditRedactor
from veri_kalitesi.audit.repository import SQLiteAuditRepository
from veri_kalitesi.audit.service import AuditService
from veri_kalitesi.data_sources.models import (
    DataSource,
    DataSourceActivationRequest,
    DataSourceActivationStatus,
    SourceType,
)
from veri_kalitesi.governance import GovernanceApprovalQueryService
from veri_kalitesi.identity import DashboardAuthorizationPolicy, PolicyAuthorizationService
from veri_kalitesi.rules.models import (
    QualityDimension,
    QualityRule,
    RuleApprovalRequest,
    RuleApprovalStatus,
    RuleCriticality,
    RuleStatus,
    RuleType,
    RuleVersion,
)

NOW = datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc)
POLICY_VERSION = "GOVERNANCE_API_TEST_V1"


def test_governance_lists_rule_and_source_requests_in_scope() -> None:
    client = TestClient(_app())

    response = client.get("/api/v1/governance/approval-requests")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    payload = response.json()
    assert payload["view"] == "ALL"
    ids = [item["approval_request_id"] for item in payload["items"]]
    assert ids == ["apr-source-1", "apr-rule-1", "apr-rule-decided-1"]
    rule_item = payload["items"][1]
    assert rule_item["domain"] == "QUALITY_RULE"
    assert rule_item["request_type"] == "RULE_APPROVAL"
    assert rule_item["object_type"] == "QualityRule"
    assert rule_item["object_id"] == "rule-a"
    assert rule_item["scope_type"] == "DATASET"
    assert rule_item["scope_id"] == "dataset-a"
    source_item = payload["items"][0]
    assert source_item["domain"] == "DATA_SOURCE"
    assert source_item["request_type"] == "SOURCE_ACTIVATION"
    assert source_item["object_type"] == "DataSource"
    assert source_item["scope_id"] == "source-a"


def test_governance_pending_view_excludes_own_requests() -> None:
    client = TestClient(_app())

    pending = client.get("/api/v1/governance/approval-requests", params={"view": "PENDING"})
    assert pending.status_code == 200
    pending_makers = {item["maker_actor_id"] for item in pending.json()["items"]}
    assert "development-dashboard-user" not in pending_makers
    assert all(item["status"] == "PENDING" for item in pending.json()["items"])

    mine = client.get("/api/v1/governance/approval-requests", params={"view": "MINE"})
    assert mine.status_code == 200
    assert {item["approval_request_id"] for item in mine.json()["items"]} == {"apr-source-1"}


def test_governance_decided_and_expired_views() -> None:
    client = TestClient(_app())

    decided = client.get("/api/v1/governance/approval-requests", params={"view": "DECIDED"})
    assert decided.status_code == 200
    assert {item["approval_request_id"] for item in decided.json()["items"]} == {
        "apr-rule-decided-1"
    }

    expired = client.get("/api/v1/governance/approval-requests", params={"view": "EXPIRED"})
    assert expired.status_code == 200
    assert expired.json()["items"] == []


def test_governance_domain_filter_and_invalid_parameters() -> None:
    client = TestClient(_app())

    filtered = client.get("/api/v1/governance/approval-requests", params={"domain": "QUALITY_RULE"})
    assert filtered.status_code == 200
    assert all(item["domain"] == "QUALITY_RULE" for item in filtered.json()["items"])

    assert (
        client.get("/api/v1/governance/approval-requests", params={"view": "WRONG"}).status_code
        == 400
    )
    assert (
        client.get("/api/v1/governance/approval-requests", params={"domain": "WRONG"}).status_code
        == 400
    )


def test_governance_out_of_scope_requests_are_hidden() -> None:
    client = TestClient(
        _app(
            permitted_dataset_ids=frozenset({"dataset-other"}),
            permitted_source_ids=frozenset({"source-other"}),
        )
    )

    response = client.get("/api/v1/governance/approval-requests")

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_governance_repository_failure_returns_safe_technical_error() -> None:
    client = TestClient(_app(rule_reader=FailingGovernanceRuleReader()))

    response = client.get("/api/v1/governance/approval-requests")

    assert response.status_code == 503
    assert response.json()["title"] == "Governance tasks temporarily unavailable"
    assert "database contains secret" not in response.text


def test_governance_unavailable_service_returns_503() -> None:
    app = create_dashboard_api(
        identity=ActorResolverIdentity(_resolver()),
        options=ApiOptions(data_origin="synthetic-test"),
        governance=GovernanceServices(query=None),
    )

    response = TestClient(app).get("/api/v1/governance/approval-requests")

    assert response.status_code == 503


class FakeGovernanceRuleReader:
    def __init__(self) -> None:
        self.rule = QualityRule(
            quality_rule_id="rule-a",
            code="DQ_RULE_A",
            name="Kural A",
            dataset_id="dataset-a",
            field_ids=(),
            primary_dimension=QualityDimension.COMPLETENESS,
            owner_user_id="owner-a",
            status=RuleStatus.DRAFT,
        )
        self.version = RuleVersion(
            rule_version_id="version-rule-a",
            quality_rule_id="rule-a",
            version_no=1,
            rule_type=RuleType.REQUIRED,
            definition={},
            threshold=95,
            weight=1,
            criticality=RuleCriticality.CRITICAL,
            created_at=NOW,
        )

    def list_rules_with_latest_version(
        self, allowed_dataset_ids: frozenset[str]
    ) -> list[tuple[QualityRule, RuleVersion]]:
        if self.rule.dataset_id not in allowed_dataset_ids:
            return []
        return [(self.rule, self.version)]

    def list_approval_requests_for_datasets(
        self, dataset_ids: frozenset[str]
    ) -> list[RuleApprovalRequest]:
        requests = [
            RuleApprovalRequest(
                approval_request_id="apr-rule-1",
                rule_version_id="version-rule-a",
                maker_actor_id="maker-1",
                policy_version=POLICY_VERSION,
                requested_at=NOW - timedelta(hours=1),
            ),
            RuleApprovalRequest(
                approval_request_id="apr-rule-decided-1",
                rule_version_id="version-rule-a",
                maker_actor_id="maker-1",
                checker_actor_id="checker-1",
                policy_version=POLICY_VERSION,
                status=RuleApprovalStatus.APPROVED,
                decision_reason_code="RULE.TEST.PASSED",
                requested_at=NOW - timedelta(days=2),
                decided_at=NOW - timedelta(days=1),
            ),
            RuleApprovalRequest(
                approval_request_id="apr-rule-outside-scope",
                rule_version_id="version-other",
                maker_actor_id="maker-2",
                policy_version=POLICY_VERSION,
                requested_at=NOW - timedelta(hours=3),
            ),
        ]
        return requests if "dataset-a" in dataset_ids else []


class FailingGovernanceRuleReader:
    def list_rules_with_latest_version(
        self, allowed_dataset_ids: frozenset[str]
    ) -> list[tuple[QualityRule, RuleVersion]]:
        raise sqlite3.OperationalError("database contains secret")

    def list_approval_requests_for_datasets(
        self, dataset_ids: frozenset[str]
    ) -> list[RuleApprovalRequest]:
        raise sqlite3.OperationalError("database contains secret")


class FakeGovernanceSourceReader:
    def list_data_sources(self, allowed_source_ids: frozenset[str]) -> list[DataSource]:
        return [source for source in _sources() if source.data_source_id in allowed_source_ids]

    def list_all_data_sources(self) -> list[DataSource]:
        return _sources()

    def list_activation_requests_for_sources(
        self, source_ids: frozenset[str]
    ) -> list[DataSourceActivationRequest]:
        request = DataSourceActivationRequest(
            activation_request_id="apr-source-1",
            data_source_id="source-a",
            data_source_revision=1,
            maker_actor_id="development-dashboard-user",
            policy_version=POLICY_VERSION,
            status=DataSourceActivationStatus.PENDING,
            requested_at=NOW,
        )
        return [request] if "source-a" in source_ids else []


def _sources() -> list[DataSource]:
    return [
        DataSource(
            data_source_id="source-a",
            name="Kaynak A",
            source_type=SourceType.POSTGRESQL,
            connection_config={},
            secret_reference="secret-a",
        )
    ]


def _audit_service() -> AuditService:
    return AuditService(
        SQLiteAuditRepository(),
        AuditRedactor(
            AuditRedactionPolicy(
                version="GOVERNANCE_API_REDACTION_V1",
                allowed_fields_by_action={
                    "DASHBOARD_SCOPE_AUTHORIZATION": frozenset(
                        {
                            "policy_version",
                            "permitted_source_count",
                            "can_view_enterprise",
                            "reason_code",
                        }
                    )
                },
            )
        ),
        AuditFailurePolicy("GOVERNANCE_API_AUDIT_V1", AuditFailureMode.FAIL_CLOSED),
    )


def _resolver(
    *,
    permitted_dataset_ids: frozenset[str] = frozenset({"dataset-a"}),
    permitted_source_ids: frozenset[str] = frozenset({"source-a"}),
) -> DevelopmentActorContextResolver:
    return DevelopmentActorContextResolver(
        runtime_environment="development",
        policy_version=POLICY_VERSION,
        permitted_source_ids=permitted_source_ids,
        permitted_dataset_ids=permitted_dataset_ids,
        can_view_enterprise=False,
        roles=frozenset({"DATA_OWNER"}),
        clock=lambda: NOW,
    )


def _app(
    *,
    rule_reader: object | None = None,
    permitted_dataset_ids: frozenset[str] = frozenset({"dataset-a"}),
    permitted_source_ids: frozenset[str] = frozenset({"source-a"}),
):
    authorization = PolicyAuthorizationService(
        DashboardAuthorizationPolicy(version=POLICY_VERSION),
        _audit_service(),
        clock=lambda: NOW,
    )
    resolver = _resolver(
        permitted_dataset_ids=permitted_dataset_ids,
        permitted_source_ids=permitted_source_ids,
    )
    query_service = GovernanceApprovalQueryService(
        rule_reader if rule_reader is not None else FakeGovernanceRuleReader(),
        FakeGovernanceSourceReader(),
        authorization,
    )
    return create_dashboard_api(
        identity=ActorResolverIdentity(resolver),
        options=ApiOptions(data_origin="synthetic-test"),
        governance=GovernanceServices(query=query_service),
    )
