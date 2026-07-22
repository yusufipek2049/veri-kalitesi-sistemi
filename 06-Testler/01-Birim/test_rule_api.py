from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from veri_kalitesi.api import DevelopmentActorContextResolver, create_dashboard_api
from veri_kalitesi.api.development import create_development_app
from veri_kalitesi.audit import (
    AuditFailureMode,
    AuditFailurePolicy,
    AuditRedactionPolicy,
    AuditRedactor,
    AuditService,
    SQLiteAuditRepository,
)
from veri_kalitesi.dashboard import DashboardQueryService
from veri_kalitesi.identity import DashboardAuthorizationPolicy, PolicyAuthorizationService
from veri_kalitesi.rules import (
    QualityDimension,
    QualityRule,
    RuleCriticality,
    RuleQueryService,
    RuleStatus,
    RuleType,
    RuleVersion,
)
from veri_kalitesi.scoring import SQLiteScoreRepository

NOW = datetime(2026, 7, 22, 12, 0, tzinfo=timezone.utc)
POLICY_VERSION = "RULE_API_TEST_V1"


def test_fr_023_rule_list_is_dataset_scoped_and_data_minimum() -> None:
    reader = FakeRuleReader((_rule("rule-a", "dataset-a"), _rule("rule-b", "dataset-b")))
    client = TestClient(_app(reader, frozenset({"dataset-a"})))

    response = client.get(
        "/api/v1/rules",
        headers={"X-Dataset-IDs": "dataset-b", "X-Roles": "ADMIN"},
    )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["items"] == [
        {
            "quality_rule_id": "rule-a",
            "code": "DQ_RULE_A",
            "name": "Kural rule-a",
            "dataset_id": "dataset-a",
            "primary_dimension": "COMPLETENESS",
            "status": "ACTIVE",
            "rule_version_id": "version-rule-a",
            "version_no": 2,
            "rule_type": "REQUIRED",
            "criticality": "HIGH",
            "created_at": "2026-07-22T12:00:00Z",
        }
    ]
    for protected_field in (
        "definition",
        "threshold",
        "weight",
        "owner_user_id",
        "prepared_by_actor_id",
        "field_ids",
        "must-not-leak",
    ):
        assert protected_field not in response.text


def test_fr_023_empty_dataset_scope_does_not_become_unscoped_query() -> None:
    reader = FakeRuleReader((_rule("rule-a", "dataset-a"),))
    response = TestClient(_app(reader, frozenset())).get("/api/v1/rules")

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert reader.last_allowed_ids == frozenset()


def test_fr_023_repository_failure_returns_safe_technical_error() -> None:
    response = TestClient(_app(FailingRuleReader(), frozenset({"dataset-a"}))).get("/api/v1/rules")

    assert response.status_code == 503
    assert response.json()["title"] == "Rules temporarily unavailable"
    assert "database contains secret" not in response.text


def test_development_api_exposes_only_synthetic_rule_projection() -> None:
    response = TestClient(create_development_app()).get("/api/v1/rules")

    assert response.status_code == 200
    assert len(response.json()["items"]) == 5
    assert response.json()["data_origin"] == "synthetic-development"
    assert "development-maker" not in response.text
    assert "development-owner" not in response.text


class FakeRuleReader:
    def __init__(self, rules: tuple[tuple[QualityRule, RuleVersion], ...]) -> None:
        self.rules = rules
        self.last_allowed_ids: frozenset[str] | None = None

    def list_rules_with_latest_version(
        self, allowed_dataset_ids: frozenset[str]
    ) -> list[tuple[QualityRule, RuleVersion]]:
        self.last_allowed_ids = allowed_dataset_ids
        return [item for item in self.rules if item[0].dataset_id in allowed_dataset_ids]


class FailingRuleReader:
    def list_rules_with_latest_version(
        self, allowed_dataset_ids: frozenset[str]
    ) -> list[tuple[QualityRule, RuleVersion]]:
        raise sqlite3.OperationalError("database contains secret")


def _rule(rule_id: str, dataset_id: str) -> tuple[QualityRule, RuleVersion]:
    return (
        QualityRule(
            quality_rule_id=rule_id,
            code=f"DQ_{rule_id.upper().replace('-', '_')}",
            name=f"Kural {rule_id}",
            dataset_id=dataset_id,
            field_ids=("field-must-not-leak",),
            primary_dimension=QualityDimension.COMPLETENESS,
            owner_user_id="owner-must-not-leak",
            status=RuleStatus.ACTIVE,
        ),
        RuleVersion(
            rule_version_id=f"version-{rule_id}",
            quality_rule_id=rule_id,
            version_no=2,
            rule_type=RuleType.REQUIRED,
            definition={"custom_sql": "must-not-leak"},
            threshold=95,
            weight=2,
            criticality=RuleCriticality.HIGH,
            prepared_by_actor_id="maker-must-not-leak",
            created_at=NOW,
        ),
    )


def _app(
    reader: FakeRuleReader | FailingRuleReader,
    dataset_ids: frozenset[str],
):
    audit_service = AuditService(
        SQLiteAuditRepository(),
        AuditRedactor(
            AuditRedactionPolicy(
                version="RULE_API_REDACTION_V1",
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
        AuditFailurePolicy("RULE_API_AUDIT_V1", AuditFailureMode.FAIL_CLOSED),
    )
    authorization = PolicyAuthorizationService(
        DashboardAuthorizationPolicy(version=POLICY_VERSION),
        audit_service,
        clock=lambda: NOW,
    )
    resolver = DevelopmentActorContextResolver(
        runtime_environment="development",
        policy_version=POLICY_VERSION,
        permitted_source_ids=frozenset(),
        permitted_dataset_ids=dataset_ids,
        can_view_enterprise=False,
        clock=lambda: NOW,
    )
    dashboard = DashboardQueryService(SQLiteScoreRepository(), authorization, clock=lambda: NOW)
    return create_dashboard_api(
        dashboard,
        actor_context_resolver=resolver,
        rule_query_service=RuleQueryService(reader, authorization),
        data_origin="synthetic-test",
    )
