from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from veri_kalitesi.api import DevelopmentActorContextResolver, create_dashboard_api
from veri_kalitesi.api.development import create_development_app
from veri_kalitesi.audit import (
    AuditAccessPolicy,
    AuditEventInput,
    AuditFailureMode,
    AuditFailurePolicy,
    AuditQueryService,
    AuditRedactor,
    AuditResult,
    AuditService,
    SQLiteAuditRepository,
    build_default_redaction_policy,
)
from veri_kalitesi.dashboard import DashboardQueryService
from veri_kalitesi.identity import DashboardAuthorizationPolicy, PolicyAuthorizationService
from veri_kalitesi.scoring import SQLiteScoreRepository

NOW = datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc)
POLICY_VERSION = "AUDIT_API_TEST_V1"


def test_fr_078_uc_016_audit_events_are_filtered_paginated_and_data_minimum() -> None:
    repository, audit_service = _audit_components()
    visible = audit_service.append(_event("event-visible", "RULE_ACTIVATION", AuditResult.SUCCESS))
    audit_service.append(_event("event-hidden", "IDENTITY_SESSION", AuditResult.FAILURE))
    assert visible is not None
    response = TestClient(_app(repository, audit_service)).get(
        "/api/v1/audit/events",
        params={"action": "RULE_ACTIVATION", "result": "SUCCESS", "page_size": 1},
        headers={"X-Roles": "ADMIN", "X-Actor-ID": "forged-user"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert response.headers["cache-control"] == "no-store"
    assert payload["integrity_valid"] is True
    assert payload["integrity_checked_count"] == 2
    assert payload["through_sequence_no"] == 2
    assert payload["page_size"] == 1
    assert [item["event_id"] for item in payload["items"]] == [visible.event_id]
    for protected_field in (
        "old_value_summary",
        "new_value_summary",
        "old_value_digest",
        "new_value_digest",
        "session_id_digest",
        "event_hash",
        "previous_event_hash",
        "first_invalid_event_id",
        "must-not-leak",
    ):
        assert protected_field not in response.text
    assert "forged-user" not in response.text


def test_fr_078_nfr_sec_001_audit_role_is_required() -> None:
    repository, audit_service = _audit_components()
    audit_service.append(_event("event-denied", "RULE_ACTIVATION", AuditResult.SUCCESS))

    response = TestClient(_app(repository, audit_service, roles=frozenset({"DATA_VIEWER"}))).get(
        "/api/v1/audit/events"
    )

    assert response.status_code == 403
    assert response.json()["title"] == "Access denied"
    assert "event-denied" not in response.text


def test_fr_078_uc_016_invalid_action_returns_safe_validation_error() -> None:
    repository, audit_service = _audit_components()

    response = TestClient(_app(repository, audit_service)).get(
        "/api/v1/audit/events",
        params={"action": "INVALID ACTION"},
    )

    assert response.status_code == 400
    assert response.json()["title"] == "Invalid request"
    assert "INVALID ACTION" not in response.text


def test_fr_078_uc_016_future_snapshot_period_is_rejected() -> None:
    repository, audit_service = _audit_components()

    response = TestClient(_app(repository, audit_service)).get(
        "/api/v1/audit/events",
        params={"period_end": (NOW + timedelta(seconds=1)).isoformat()},
    )

    assert response.status_code == 400
    assert response.json()["title"] == "Invalid request"
    assert "period end" not in response.text.lower()


def test_uc_016_closed_audit_repository_returns_safe_technical_error() -> None:
    repository, audit_service = _audit_components()
    repository.connection.close()

    response = TestClient(_app(repository, audit_service)).get("/api/v1/audit/events")

    assert response.status_code == 503
    assert response.json()["title"] == "Audit records temporarily unavailable"
    assert "sqlite" not in response.text.lower()


def test_development_api_exposes_integrity_checked_synthetic_audit_events() -> None:
    response = TestClient(create_development_app()).get("/api/v1/audit/events")

    assert response.status_code == 200
    payload = response.json()
    assert payload["integrity_valid"] is True
    assert payload["integrity_checked_count"] == 6
    assert len(payload["items"]) == 6
    assert {item["result"] for item in payload["items"]} == {
        "SUCCESS",
        "FAILURE",
        "DENIED",
    }
    assert "synthetic-expired-session" in response.text
    assert "development-reference-only" not in response.text


def _audit_components() -> tuple[SQLiteAuditRepository, AuditService]:
    repository = SQLiteAuditRepository()
    service = AuditService(
        repository,
        AuditRedactor(build_default_redaction_policy()),
        AuditFailurePolicy(
            version="AUDIT_API_FAILURE_V1",
            default_mode=AuditFailureMode.FAIL_CLOSED,
        ),
    )
    return repository, service


def _app(
    repository: SQLiteAuditRepository,
    audit_service: AuditService,
    *,
    roles: frozenset[str] = frozenset({"AUDIT_VIEWER"}),
):
    authorization = PolicyAuthorizationService(
        DashboardAuthorizationPolicy(version=POLICY_VERSION),
        audit_service,
        clock=lambda: NOW,
    )
    resolver = DevelopmentActorContextResolver(
        runtime_environment="development",
        policy_version=POLICY_VERSION,
        permitted_source_ids=frozenset(),
        can_view_enterprise=False,
        roles=roles,
        clock=lambda: NOW,
    )
    return create_dashboard_api(
        DashboardQueryService(
            SQLiteScoreRepository(),
            authorization,
            clock=lambda: NOW,
        ),
        actor_context_resolver=resolver,
        audit_query_service=AuditQueryService(
            repository,
            audit_service,
            AuditAccessPolicy(
                version="AUDIT_ACCESS_TEST_V1",
                context_policy_version=POLICY_VERSION,
            ),
            clock=lambda: NOW,
        ),
        data_origin="synthetic-test",
        clock=lambda: NOW,
    )


def _event(event_id: str, action: str, result: AuditResult) -> AuditEventInput:
    return AuditEventInput(
        actor_id="synthetic-audit-user",
        actor_type="USER",
        correlation_id=f"correlation-{event_id}",
        action=action,
        object_type="QualityRule",
        object_id="synthetic-object",
        result=result,
        reason_code="SYNTHETIC_REASON",
        old_values={"secret": "must-not-leak"},
        new_values={},
        occurred_at=NOW - timedelta(hours=1),
        session_id="must-not-leak",
    )
