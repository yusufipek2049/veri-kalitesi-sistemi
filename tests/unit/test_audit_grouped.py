from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from veri_kalitesi.api import DevelopmentActorContextResolver, create_dashboard_api
from veri_kalitesi.api.service_groups import ActorResolverIdentity, ApiOptions, AuditServices
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
from veri_kalitesi.audit.service import AuditQueryService, AuditService
from veri_kalitesi.identity import DashboardAuthorizationPolicy, PolicyAuthorizationService

NOW = datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc)
POLICY_VERSION = "AUDIT_GROUPED_TEST_V1"


def test_grouped_endpoint_requires_correlation_id() -> None:
    client, _audit_service = _client()

    response = client.get("/api/v1/audit/events/grouped")

    assert response.status_code == 422


def test_grouped_endpoint_returns_only_correlation_events_chronologically() -> None:
    client, audit_service = _client()
    audit_service.append(_event("target", "late", NOW - timedelta(hours=1)))
    audit_service.append(_event("other", "unrelated", NOW - timedelta(hours=2)))
    audit_service.append(_event("target", "early", NOW - timedelta(hours=3)))

    response = client.get(
        "/api/v1/audit/events/grouped",
        params={"correlation_id": "target", "page_size": 500},
    )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    payload = response.json()
    assert payload["grouped_by"] == "correlation_id"
    assert payload["page_size"] == 500
    assert [item["object_id"] for item in payload["items"]] == ["early", "late"]
    assert {item["correlation_id"] for item in payload["items"]} == {"target"}


def _client() -> tuple[TestClient, AuditService]:
    repository = SQLiteAuditRepository()
    audit_service = AuditService(
        repository,
        AuditRedactor(build_default_redaction_policy()),
        AuditFailurePolicy(
            version="AUDIT_GROUPED_FAILURE_V1",
            default_mode=AuditFailureMode.FAIL_CLOSED,
        ),
    )
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
        roles=frozenset({"AUDIT_VIEWER"}),
        clock=lambda: NOW,
    )
    app = create_dashboard_api(
        identity=ActorResolverIdentity(resolver),
        audit=AuditServices(
            query=AuditQueryService(
                repository,
                audit_service,
                AuditAccessPolicy(
                    version="AUDIT_GROUPED_ACCESS_V1",
                    context_policy_version=POLICY_VERSION,
                ),
                clock=lambda: NOW,
            ),
        ),
        options=ApiOptions(data_origin="synthetic-test", clock=lambda: NOW),
    )
    return TestClient(app), audit_service


def _event(correlation_id: str, object_id: str, occurred_at: datetime) -> AuditEventInput:
    return AuditEventInput(
        actor_id="audit-user",
        actor_type="USER",
        correlation_id=correlation_id,
        action="RULE_ACTIVATION",
        object_type="QualityRule",
        object_id=object_id,
        result=AuditResult.SUCCESS,
        reason_code="APPROVED",
        old_values={},
        new_values={},
        occurred_at=occurred_at,
        session_id="synthetic-session",
    )
