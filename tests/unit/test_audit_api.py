from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from veri_kalitesi.api import DevelopmentActorContextResolver, create_dashboard_api
from veri_kalitesi.api.service_groups import ActorResolverIdentity, ApiOptions, AuditServices
from veri_kalitesi.api.development import create_synthetic_development_app
from veri_kalitesi.audit.models import (
    AuditAccessPolicy,
    AuditEventInput,
    AuditFailureMode,
    AuditFailurePolicy,
    AuditResult,
)
from veri_kalitesi.audit.policies import build_default_redaction_policy
from veri_kalitesi.audit.redaction import AuditRedactor
from veri_kalitesi.audit.repository import SQLiteAuditRepository
from veri_kalitesi.audit.service import (
    AuditQueryService,
    AuditService,
)
from veri_kalitesi.identity import DashboardAuthorizationPolicy, PolicyAuthorizationService

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
        "old_value_digest",
        "new_value_digest",
        "session_id_digest",
        "must-not-leak",
    ):
        assert protected_field not in response.text
    # Iterasyon 37A: detay alanlari interaktif API'de gorunur
    # (veri-minimum yalnizca disa aktarmayi kapsar).
    for detail_field in (
        "old_value_summary",
        "new_value_summary",
        "event_hash",
        "previous_event_hash",
        "first_invalid_event_id",
    ):
        assert detail_field in response.text
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


def test_fr_078_uc_016_period_start_uses_custom_range_instead_of_days() -> None:
    repository, audit_service = _audit_components()
    audit_service.append(
        _event(
            "event-custom-range",
            "RULE_ACTIVATION",
            AuditResult.SUCCESS,
            occurred_at=NOW - timedelta(days=3),
        )
    )
    audit_service.append(_event("event-recent", "RULE_ACTIVATION", AuditResult.SUCCESS))

    response = TestClient(_app(repository, audit_service)).get(
        "/api/v1/audit/events",
        params={
            "days": 1,
            "period_start": (NOW - timedelta(days=4)).isoformat(),
            "period_end": (NOW - timedelta(days=2)).isoformat(),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert [item["correlation_id"] for item in payload["items"]] == [
        "correlation-event-custom-range"
    ]
    assert _parse_api_datetime(payload["period_start"]) == NOW - timedelta(days=4)
    assert _parse_api_datetime(payload["period_end"]) == NOW - timedelta(days=2)


def test_fr_078_uc_016_audit_summary_returns_filtered_distributions() -> None:
    repository, audit_service = _audit_components()
    audit_service.append(_event("summary-1", "RULE_ACTIVATION", AuditResult.SUCCESS))
    audit_service.append(_event("summary-2", "RULE_ACTIVATION", AuditResult.FAILURE))
    audit_service.append(_event("summary-3", "IDENTITY_SESSION", AuditResult.DENIED))

    response = TestClient(_app(repository, audit_service)).get(
        "/api/v1/audit/summary",
        params={"action": "RULE_ACTIVATION"},
    )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    payload = response.json()
    assert _parse_api_datetime(payload.pop("period_start")) == NOW - timedelta(days=7)
    assert _parse_api_datetime(payload.pop("period_end")) == NOW
    assert payload == {
        "total_count": 2,
        "result_distribution": {"SUCCESS": 1, "FAILURE": 1, "DENIED": 0},
        "action_distribution": {"RULE_ACTIVATION": 2},
        "top_actors": [{"actor_id": "synthetic-audit-user", "count": 2}],
    }


def test_uc_016_closed_audit_repository_returns_safe_technical_error() -> None:
    repository, audit_service = _audit_components()
    repository.connection.close()

    response = TestClient(_app(repository, audit_service)).get("/api/v1/audit/events")

    assert response.status_code == 503
    assert response.json()["title"] == "Audit records temporarily unavailable"
    assert "sqlite" not in response.text.lower()


def test_development_api_exposes_integrity_checked_synthetic_audit_events() -> None:
    response = TestClient(create_synthetic_development_app()).get("/api/v1/audit/events")

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
    PolicyAuthorizationService(
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
        identity=ActorResolverIdentity(resolver),
        audit=AuditServices(
            query=AuditQueryService(
                repository,
                audit_service,
                AuditAccessPolicy(
                    version="AUDIT_ACCESS_TEST_V1",
                    context_policy_version=POLICY_VERSION,
                ),
                clock=lambda: NOW,
            ),
        ),
        options=ApiOptions(data_origin="synthetic-test", clock=lambda: NOW),
    )


def _event(
    event_id: str,
    action: str,
    result: AuditResult,
    *,
    occurred_at: datetime | None = None,
) -> AuditEventInput:
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
        occurred_at=occurred_at or NOW - timedelta(hours=1),
        session_id="must-not-leak",
    )


def _parse_api_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
