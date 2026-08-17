"""Skorlama konfigürasyonu maker-checker endpoint'leri HTTP testleri.

Maker önerisi → checker kararı akışını, CSRF korumasını, rol ve
enterprise kapsam yetkilendirmesini doğrular.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from veri_kalitesi.api import DevelopmentActorContextResolver, create_dashboard_api
from veri_kalitesi.api.bff import CSRF_HEADER_NAME
from veri_kalitesi.api.errors import ApiCsrfError
from veri_kalitesi.api.identity import DevelopmentUser, DevelopmentUserRegistry
from veri_kalitesi.api.service_groups import (
    ActorResolverIdentity,
    ApiOptions,
    ScoringConfigurationServices,
)
from veri_kalitesi.audit.outbox import SQLiteTransactionalAudit
from veri_kalitesi.audit.policies import build_default_redaction_policy
from veri_kalitesi.audit.redaction import AuditRedactor
from veri_kalitesi.audit.repository import SQLiteAuditRepository
from veri_kalitesi.identity import ActorContext
from veri_kalitesi.scoring.models import ScoringApprovalPolicy
from veri_kalitesi.scoring.repository import SQLiteScoreRepository
from veri_kalitesi.scoring.service import ScoringConfigurationService

NOW = datetime(2026, 8, 17, 12, 0, tzinfo=timezone.utc)
ACTOR_POLICY_VERSION = "SCORING_CFG_API_POLICY_V1"
CSRF_PROOF = "test-csrf-proof"


class _ScoringResolver(DevelopmentActorContextResolver):
    """CSRF kanıtını basitleştirilmiş biçimde denetleyen test resolver'ı."""

    def protect_state_changing(self, request) -> ActorContext:  # type: ignore[no-untyped-def]
        if request.headers.get(CSRF_HEADER_NAME) != CSRF_PROOF:
            raise ApiCsrfError("rejected", request.state.correlation_id)
        return self.resolve(request)


def _policy() -> ScoringApprovalPolicy:
    return ScoringApprovalPolicy(
        version="SCORING_APPROVAL_POLICY_V1",
        actor_policy_version=ACTOR_POLICY_VERSION,
        maker_roles=frozenset({"DATA_STEWARD", "DATA_GOVERNANCE_SPECIALIST"}),
        checker_roles=frozenset({"DATA_OWNER"}),
    )


def _app():
    registry = DevelopmentUserRegistry(
        [
            DevelopmentUser(
                user_id="maker-user",
                display_name="Veri Uzmanı",
                roles=frozenset({"DATA_STEWARD"}),
                permitted_source_ids=frozenset(),
                permitted_dataset_ids=frozenset(),
                can_view_enterprise=True,
            ),
            DevelopmentUser(
                user_id="checker-user",
                display_name="Veri Sahibi",
                roles=frozenset({"DATA_OWNER"}),
                permitted_source_ids=frozenset(),
                permitted_dataset_ids=frozenset(),
                can_view_enterprise=True,
            ),
            DevelopmentUser(
                user_id="limited-maker",
                display_name="Kapsam Dışı Uzman",
                roles=frozenset({"DATA_STEWARD"}),
                permitted_source_ids=frozenset(),
                permitted_dataset_ids=frozenset(),
                can_view_enterprise=False,
            ),
            DevelopmentUser(
                user_id="viewer-user",
                display_name="İzleyici",
                roles=frozenset({"DASHBOARD_VIEWER"}),
                permitted_source_ids=frozenset(),
                permitted_dataset_ids=frozenset(),
                can_view_enterprise=True,
            ),
        ]
    )
    resolver = _ScoringResolver(
        runtime_environment="development",
        policy_version=ACTOR_POLICY_VERSION,
        permitted_source_ids=frozenset(),
        permitted_dataset_ids=frozenset(),
        can_view_enterprise=False,
        user_registry=registry,
        clock=lambda: NOW,
    )
    repository = SQLiteScoreRepository()
    transactional_audit = SQLiteTransactionalAudit(
        repository.connection,
        AuditRedactor(build_default_redaction_policy()),
        SQLiteAuditRepository(),
        policy_version="AUDIT_OUTBOX_API_TEST_V1",
    )
    service = ScoringConfigurationService(
        repository,
        transactional_audit=transactional_audit,
        approval_policy=_policy(),
        clock=lambda: NOW,
    )
    app = create_dashboard_api(
        identity=ActorResolverIdentity(resolver),
        options=ApiOptions(data_origin="synthetic-test"),
        scoring_configurations=ScoringConfigurationServices(command=service, reader=repository),
    )
    return TestClient(app)


def _headers(user_id: str) -> dict[str, str]:
    return {CSRF_HEADER_NAME: CSRF_PROOF, "X-Development-User-Id": user_id}


def _submit(client: TestClient, *, version: str = "SCORING_CFG_V2") -> dict:
    response = client.post(
        "/api/v1/scoring-configurations",
        json={"version": version},
        headers=_headers("maker-user"),
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_full_maker_checker_flow_over_http() -> None:
    client = _app()

    created = _submit(client)
    assert created["configuration"]["is_active"] is False
    assert created["approval"]["status"] == "PENDING"
    default_configuration_id = created["configuration"]["configuration_id"]

    listed = client.get("/api/v1/scoring-configurations", headers=_headers("checker-user"))
    assert listed.status_code == 200
    payload = listed.json()
    assert payload["pending_approval"] is not None
    assert payload["pending_approval"]["approval_id"] == created["approval"]["approval_id"]
    assert payload["active_configuration_id"] != default_configuration_id

    decision = client.post(
        f"/api/v1/scoring-configurations/approvals/{created['approval']['approval_id']}/decision",
        json={"decision": "APPROVE", "reason_code": "SCORING.CONFIGURATION.REVIEWED"},
        headers=_headers("checker-user"),
    )
    assert decision.status_code == 200, decision.text
    body = decision.json()
    assert body["approval"]["status"] == "APPROVED"
    assert body["configuration"]["is_active"] is True

    refreshed = client.get("/api/v1/scoring-configurations", headers=_headers("viewer-user"))
    assert refreshed.status_code == 200
    assert refreshed.json()["active_configuration_id"] == default_configuration_id
    assert refreshed.json()["pending_approval"] is None


def test_maker_cannot_decide_own_submission() -> None:
    client = _app()
    created = _submit(client)

    response = client.post(
        f"/api/v1/scoring-configurations/approvals/{created['approval']['approval_id']}/decision",
        json={"decision": "APPROVE", "reason_code": "SCORING.CONFIGURATION.REVIEWED"},
        headers=_headers("maker-user"),
    )
    assert response.status_code == 403


def test_rejection_keeps_existing_configuration_active() -> None:
    client = _app()
    listed_before = client.get("/api/v1/scoring-configurations", headers=_headers("checker-user"))
    active_before = listed_before.json()["active_configuration_id"]

    created = _submit(client)
    response = client.post(
        f"/api/v1/scoring-configurations/approvals/{created['approval']['approval_id']}/decision",
        json={"decision": "REJECT", "reason_code": "SCORING.CONFIGURATION.REJECTED"},
        headers=_headers("checker-user"),
    )
    assert response.status_code == 200, response.text
    assert response.json()["approval"]["status"] == "REJECTED"
    assert response.json()["configuration"]["is_active"] is False

    listed_after = client.get("/api/v1/scoring-configurations", headers=_headers("checker-user"))
    assert listed_after.json()["active_configuration_id"] == active_before


def test_submission_requires_maker_role_and_enterprise_scope() -> None:
    client = _app()

    response = client.post(
        "/api/v1/scoring-configurations",
        json={"version": "SCORING_CFG_V2"},
        headers=_headers("viewer-user"),
    )
    assert response.status_code == 403

    response = client.post(
        "/api/v1/scoring-configurations",
        json={"version": "SCORING_CFG_V2"},
        headers=_headers("limited-maker"),
    )
    assert response.status_code == 403


def test_submission_without_csrf_proof_is_rejected() -> None:
    client = _app()
    response = client.post(
        "/api/v1/scoring-configurations",
        json={"version": "SCORING_CFG_V2"},
        headers={"X-Development-User-Id": "maker-user"},
    )
    assert response.status_code == 403


def test_list_requires_trusted_actor_context() -> None:
    client = _app()
    response = client.get("/api/v1/scoring-configurations")
    assert response.status_code == 403

    response = client.get("/api/v1/scoring-configurations", headers=_headers("limited-maker"))
    assert response.status_code == 403


def test_invalid_threshold_values_are_rejected() -> None:
    client = _app()
    response = client.post(
        "/api/v1/scoring-configurations",
        json={"version": "SCORING_CFG_V2", "critical_upper_exclusive": "not-a-number"},
        headers=_headers("maker-user"),
    )
    assert response.status_code == 400


def test_threshold_overrides_are_stored() -> None:
    client = _app()
    created = _submit_with_thresholds(client)
    thresholds = created["configuration"]["threshold_set"]
    assert thresholds["version"] == "THRESHOLDS_V2"
    assert thresholds["critical_upper_exclusive"] == "60.00"

    approved = _approve(client, created["approval"]["approval_id"])
    assert approved["configuration"]["threshold_set"]["risky_upper_exclusive"] == "80.00"


def _submit_with_thresholds(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/scoring-configurations",
        json={
            "version": "SCORING_CFG_V2",
            "threshold_version": "THRESHOLDS_V2",
            "critical_upper_exclusive": "60.00",
            "risky_upper_exclusive": "80.00",
        },
        headers=_headers("maker-user"),
    )
    assert response.status_code == 201, response.text
    return response.json()


def _approve(client: TestClient, approval_id: str) -> dict:
    response = client.post(
        f"/api/v1/scoring-configurations/approvals/{approval_id}/decision",
        json={"decision": "APPROVE", "reason_code": "SCORING.CONFIGURATION.REVIEWED"},
        headers=_headers("checker-user"),
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_routes_return_503_when_service_is_unavailable() -> None:
    client = TestClient(create_dashboard_api())
    response = client.get("/api/v1/scoring-configurations")
    assert response.status_code == 503


def test_dataset_scoped_configuration_creation_and_listing() -> None:
    client = _app()

    # Dataset-scoped configuration submission
    response = client.post(
        "/api/v1/scoring-configurations",
        json={"version": "SCORING_CFG_DATASET_V1", "dataset_id": "test-dataset-001"},
        headers=_headers("maker-user"),
    )
    assert response.status_code == 201, response.text
    created = response.json()
    assert created["configuration"]["dataset_id"] == "test-dataset-001"
    assert created["configuration"]["is_active"] is False

    # Listing with dataset filter
    listed = client.get(
        "/api/v1/scoring-configurations",
        params={"dataset_id": "test-dataset-001"},
        headers=_headers("checker-user"),
    )
    assert listed.status_code == 200
    payload = listed.json()
    dataset_configs = [
        item for item in payload["items"]
        if item["configuration"]["dataset_id"] == "test-dataset-001"
    ]
    assert len(dataset_configs) >= 1

    # Listing without filter includes both global and dataset-scoped
    all_listed = client.get("/api/v1/scoring-configurations", headers=_headers("checker-user"))
    assert all_listed.status_code == 200
    all_payload = all_listed.json()
    assert len(all_payload["items"]) >= 2  # default + dataset-scoped
