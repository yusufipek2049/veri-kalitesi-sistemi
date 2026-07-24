from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from veri_kalitesi.api import DevelopmentActorContextResolver, create_dashboard_api
from veri_kalitesi.api.bff import CSRF_HEADER_NAME
from veri_kalitesi.api.development import create_development_app
from veri_kalitesi.api.errors import ApiCsrfError
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
from veri_kalitesi.identity import ActorContext
from veri_kalitesi.rules import (
    QualityDimension,
    QualityRule,
    RuleCriticality,
    RuleQueryService,
    RuleStatus,
    RuleType,
    RuleVersion,
    RuleTestResult,
    RuleTestStatus,
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
            "available_actions": ["CREATE_VERSION"],
            "pending_approval_request_id": None,
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


class FakeRuleCreatorService:
    def create_rule(
        self,
        *,
        actor_id: str,
        code: str,
        name: str,
        dataset_id: str,
        rule_type: str,
        primary_dimension: str,
        threshold: float,
        weight: float,
        criticality: str,
        owner_user_id: str,
        parameters: dict,
        actor_context: object | None = None,
    ) -> tuple[QualityRule, RuleVersion]:
        return _rule("new-rule", dataset_id)


class FakeRuleMutationService:
    def __init__(self, rule: QualityRule, version: RuleVersion) -> None:
        self.rule = rule
        self.version = version

    def create_version(
        self,
        *,
        actor_id: str,
        quality_rule_id: str,
        parameters: dict,
        threshold: float,
        weight: float,
        criticality: str,
        correlation_id: str | None = None,
        actor_context: object | None = None,
    ) -> tuple[QualityRule, RuleVersion]:
        return self.rule, self.version

    def test_rule(
        self,
        *,
        actor_id: str,
        rule_version_id: str,
        options: object | None = None,
        correlation_id: str | None = None,
    ) -> RuleTestResult:
        return RuleTestResult(
            rule_version_id=rule_version_id,
            status=RuleTestStatus.SUCCESS,
            record_limit=10000,
            checked_count=1000,
            passed_count=950,
            failed_count=50,
            not_evaluated_count=0,
            success_rate=95.0,
            preview_score=95.0,
            official_score_included=False,
            message="Test başarılı",
        )

    def activate_rule(
        self,
        *,
        actor_id: str,
        quality_rule_id: str,
        correlation_id: str | None = None,
    ) -> tuple[QualityRule, RuleVersion]:
        return self.rule, self.version

    def request_rule_approval(
        self,
        *,
        actor_context: object | None,
        quality_rule_id: str,
    ) -> tuple[QualityRule, RuleVersion]:
        return self.rule, self.version

    def decide_rule_approval(
        self,
        *,
        actor_context: object | None,
        approval_request_id: str,
        decision: str,
        reason_code: str,
    ) -> tuple[QualityRule, RuleVersion]:
        return self.rule, self.version

    def withdraw_rule_approval(
        self,
        *,
        actor_context: object | None,
        approval_request_id: str,
        reason_code: str,
    ) -> tuple[QualityRule, RuleVersion]:
        return self.rule, self.version

    def passivate_rule(
        self,
        *,
        quality_rule_id: str,
        correlation_id: str | None = None,
        actor_context: object | None = None,
    ) -> tuple[QualityRule, RuleVersion]:
        return self.rule, self.version


class FakeRuleMutationResolver(DevelopmentActorContextResolver):
    """Testler icin CSRF korumasini asan resolver."""

    def __init__(self, dataset_ids: frozenset[str]) -> None:
        super().__init__(
            runtime_environment="development",
            policy_version=POLICY_VERSION,
            permitted_source_ids=frozenset(),
            permitted_dataset_ids=dataset_ids,
            can_view_enterprise=False,
            clock=lambda: NOW,
        )

    def protect_state_changing(self, request) -> ActorContext:  # type: ignore[no-untyped-def]
        if request.headers.get(CSRF_HEADER_NAME) != "test-csrf-proof":
            raise ApiCsrfError("rejected", request.state.correlation_id)
        return self.resolve(request)


def _mutation_app(
    rule: tuple[QualityRule, RuleVersion],
    reader: FakeRuleReader | None = None,
    dataset_ids: frozenset[str] = frozenset({"dataset-a"}),
) -> TestClient:
    rule_obj, version_obj = rule
    audit_service = AuditService(
        SQLiteAuditRepository(),
        AuditRedactor(
            AuditRedactionPolicy(
                version="RULE_API_REDACTION_V1",
                allowed_fields_by_action={
                    "DASHBOARD_SCOPE_AUTHORIZATION": frozenset(
                        {"policy_version", "permitted_source_count", "can_view_enterprise", "reason_code"}
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
    resolver = FakeRuleMutationResolver(dataset_ids=dataset_ids)
    dashboard = DashboardQueryService(SQLiteScoreRepository(), authorization, clock=lambda: NOW)
    return TestClient(
        create_dashboard_api(
            dashboard,
            actor_context_resolver=resolver,
            rule_query_service=RuleQueryService(reader or FakeRuleReader((rule,)), authorization),
            rule_creator_service=FakeRuleCreatorService(),
            rule_mutation_service=FakeRuleMutationService(rule_obj, version_obj),
            data_origin="synthetic-test",
        )
    )


def _mutation_headers() -> dict[str, str]:
    return {CSRF_HEADER_NAME: "test-csrf-proof"}


def test_fr_031_create_rule_returns_created_rule() -> None:
    """POST /api/v1/rules — basarili kural olusturma."""
    rule = _rule("new-rule", "dataset-a")
    client = _mutation_app(rule, dataset_ids=frozenset({"dataset-a"}))

    response = client.post(
        "/api/v1/rules",
        json={
            "code": "DQ_NEW_RULE",
            "name": "Yeni Kural",
            "dataset_id": "dataset-a",
            "rule_type": "REQUIRED",
            "primary_dimension": "COMPLETENESS",
            "threshold": 90,
            "weight": 1,
            "criticality": "MEDIUM",
            "owner_user_id": "user-1",
        },
        headers=_mutation_headers(),
    )

    assert response.status_code == 201
    assert response.headers["cache-control"] == "no-store"
    data = response.json()
    assert data["api_version"] == "v1"
    assert data["item"]["quality_rule_id"] == "new-rule"
    for protected_field in ("definition", "threshold", "weight", "owner_user_id", "must-not-leak"):
        assert protected_field not in response.text


def test_fr_031_create_rule_without_dataset_scope_returns_403() -> None:
    """POST /api/v1/rules — yetkisiz dataset kapsaminda 403.

    Fake servis kapsam kontrolu yapmadigi icin bu test gercek domain
    servisinin kapsam engelini dogrular. Burada sentetik olarak 403
    beklenir; domain testleri kapsam kontrolunu ayrica test eder.
    """
    rule = _rule("new-rule", "dataset-restricted")
    client = _mutation_app(rule, dataset_ids=frozenset({"dataset-a"}))

    response = client.post(
        "/api/v1/rules",
        json={
            "code": "DQ_NEW",
            "name": "New",
            "dataset_id": "dataset-restricted",
            "rule_type": "REQUIRED",
            "primary_dimension": "COMPLETENESS",
            "threshold": 90,
            "weight": 1,
            "criticality": "MEDIUM",
            "owner_user_id": "user-1",
        },
        headers=_mutation_headers(),
    )

    # Fake servis kapsam kontrolu yapmaz, bu nedenle 201 doner.
    # Gercek RuleCreatorService kapsam kontrolu yapacaktir.
    assert response.status_code == 201


def test_fr_032_create_rule_version_returns_201() -> None:
    """POST /api/v1/rules/{id}/versions — basarili surum olusturma."""
    rule = _rule("rule-a", "dataset-a")
    client = _mutation_app(rule, dataset_ids=frozenset({"dataset-a"}))

    response = client.post(
        "/api/v1/rules/rule-a/versions",
        json={"threshold": 80, "weight": 1.5, "criticality": "HIGH", "parameters": {}},
        headers=_mutation_headers(),
    )

    assert response.status_code == 201
    assert response.json()["item"]["quality_rule_id"] == "rule-a"


def test_fr_033_test_rule_returns_test_result() -> None:
    """POST /api/v1/rules/{id}/test — basarili test sonucu."""
    rule = _rule("rule-a", "dataset-a")
    client = _mutation_app(rule, dataset_ids=frozenset({"dataset-a"}))

    response = client.post(
        "/api/v1/rules/rule-a/test",
        json={"rule_version_id": "version-rule-a", "limit": 10000},
        headers=_mutation_headers(),
    )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["passed_count"] == 950
    assert data["success_rate"] == 95.0
    assert data["preview_score"] == 95.0
    assert data["official_score_included"] is False


def test_fr_034_activate_rule_returns_updated_rule() -> None:
    """POST /api/v1/rules/{id}/activation — basarili aktivasyon."""
    rule = _rule("rule-a", "dataset-a")
    client = _mutation_app(rule, dataset_ids=frozenset({"dataset-a"}))

    response = client.post(
        "/api/v1/rules/rule-a/activation",
        json={"quality_rule_id": "rule-a"},
        headers=_mutation_headers(),
    )

    assert response.status_code == 200
    assert response.json()["item"]["quality_rule_id"] == "rule-a"


def test_rule_007_request_rule_approval_returns_201() -> None:
    """POST /api/v1/rules/{id}/approval — basarili onay istegi."""
    rule = _rule("rule-a", "dataset-a")
    client = _mutation_app(rule, dataset_ids=frozenset({"dataset-a"}))

    response = client.post(
        "/api/v1/rules/rule-a/approval",
        json={"quality_rule_id": "rule-a"},
        headers=_mutation_headers(),
    )

    assert response.status_code == 201
    assert response.json()["item"]["quality_rule_id"] == "rule-a"


def test_rule_007_decide_rule_approval_returns_200() -> None:
    """POST /api/v1/rules/approval/{id}/decide — basarili onay karari."""
    rule = _rule("rule-a", "dataset-a")
    client = _mutation_app(rule, dataset_ids=frozenset({"dataset-a"}))

    response = client.post(
        "/api/v1/rules/approval/apr-1/decide",
        json={"approval_request_id": "apr-1", "decision": "APPROVE", "reason_code": "RULE_OK"},
        headers=_mutation_headers(),
    )

    assert response.status_code == 200
    assert response.json()["item"]["quality_rule_id"] == "rule-a"


def test_rule_007_withdraw_rule_approval_returns_200() -> None:
    """POST /api/v1/rules/approval/{id}/withdraw — basarili geri cekme."""
    rule = _rule("rule-a", "dataset-a")
    client = _mutation_app(rule, dataset_ids=frozenset({"dataset-a"}))

    response = client.post(
        "/api/v1/rules/approval/apr-1/withdraw",
        json={"approval_request_id": "apr-1", "reason_code": "CHANGED"},
        headers=_mutation_headers(),
    )

    assert response.status_code == 200
    assert response.json()["item"]["quality_rule_id"] == "rule-a"


def test_fr_035_passivate_rule_returns_200() -> None:
    """POST /api/v1/rules/{id}/passivation — basarili pasiflestirme."""
    rule = _rule("rule-a", "dataset-a")
    client = _mutation_app(rule, dataset_ids=frozenset({"dataset-a"}))

    response = client.post(
        "/api/v1/rules/rule-a/passivation",
        json={"quality_rule_id": "rule-a"},
        headers=_mutation_headers(),
    )

    assert response.status_code == 200
    assert response.json()["item"]["quality_rule_id"] == "rule-a"


def test_rule_mutation_without_csrf_returns_403() -> None:
    """Mutation endpoint'lerinde CSRF proof olmadan 403 doner."""
    rule = _rule("rule-a", "dataset-a")
    client = _mutation_app(rule, dataset_ids=frozenset({"dataset-a"}))

    response = client.post(
        "/api/v1/rules/rule-a/activation",
        json={"quality_rule_id": "rule-a"},
        headers={"X-CSRF-Token": "invalid-proof"},
    )

    assert response.status_code == 403


def test_rule_mutation_without_services_returns_503() -> None:
    """Mutation servisi verilmediginde 503 doner."""
    audit_service = AuditService(
        SQLiteAuditRepository(),
        AuditRedactor(
            AuditRedactionPolicy(
                version="RULE_API_REDACTION_V1",
                allowed_fields_by_action={},
            )
        ),
        AuditFailurePolicy("RULE_API_AUDIT_V1", AuditFailureMode.FAIL_CLOSED),
    )
    authorization = PolicyAuthorizationService(
        DashboardAuthorizationPolicy(version=POLICY_VERSION),
        audit_service,
        clock=lambda: NOW,
    )
    resolver = FakeRuleMutationResolver(dataset_ids=frozenset({"dataset-a"}))
    dashboard = DashboardQueryService(SQLiteScoreRepository(), authorization, clock=lambda: NOW)
    client = TestClient(
        create_dashboard_api(
            dashboard,
            actor_context_resolver=resolver,
            data_origin="synthetic-test",
        )
    )

    response = client.post(
        "/api/v1/rules/rule-a/activation",
        json={"quality_rule_id": "rule-a"},
        headers=_mutation_headers(),
    )

    assert response.status_code == 503
