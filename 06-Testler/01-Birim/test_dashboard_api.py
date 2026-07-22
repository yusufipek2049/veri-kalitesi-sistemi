from __future__ import annotations

import sqlite3
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from veri_kalitesi.api import (
    ActorContextResolver,
    DevelopmentActorContextResolver,
    create_dashboard_api,
)
from veri_kalitesi.audit import (
    AuditFailureMode,
    AuditFailurePolicy,
    AuditRedactionPolicy,
    AuditRedactor,
    AuditService,
    SQLiteAuditRepository,
)
from veri_kalitesi.dashboard import DashboardQueryService
from veri_kalitesi.identity import (
    ActorContext,
    ActorType,
    DashboardAuthorizationPolicy,
    PolicyAuthorizationService,
)
from veri_kalitesi.scoring import (
    QualityScore,
    ScoreLevel,
    ScoreScopeType,
    ScoreStatus,
    SQLiteScoreRepository,
)

NOW = datetime(2026, 7, 22, 12, 0, tzinfo=timezone.utc)
POLICY_VERSION = "DASHBOARD_API_POLICY_V1"


def test_fr_054_uc_010_dashboard_summary_returns_only_authorized_data() -> None:
    repository = SQLiteScoreRepository()
    repository.add_or_get(_score("authorized", ScoreScopeType.SOURCE, "source-a", "84.20"))
    repository.add_or_get(_score("forbidden", ScoreScopeType.SOURCE, "source-b", "99.90"))
    client = TestClient(_app(repository, source_ids=frozenset({"source-a"})))

    response = client.get(
        "/api/v1/dashboard/summary",
        headers={
            "X-Actor-ID": "forged-user",
            "X-Roles": "ADMIN",
            "X-Source-IDs": "source-b",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    observations = [item for period in payload["periods"] for item in period["observations"]]
    assert payload["api_version"] == "v1"
    assert payload["has_data"] is True
    assert len(payload["periods"]) == 30
    assert [item["scope_id"] for item in observations] == ["source-a"]
    assert observations[0]["score_value"] == "84.20"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-correlation-id"] == payload["correlation_id"]


def test_fr_081_missing_production_session_fails_closed_before_query() -> None:
    reader = CountingReader()
    client = TestClient(_app(reader, use_development_resolver=False))

    response = client.get("/api/v1/dashboard/summary")

    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["correlation_id"] == response.headers["x-correlation-id"]
    assert reader.calls == 0


def test_fr_081_untrusted_context_returns_403_without_scope_disclosure() -> None:
    reader = CountingReader()
    client = TestClient(_app(reader, context_resolver=ForgedContextResolver()))

    response = client.get("/api/v1/dashboard/summary")

    assert response.status_code == 403
    assert response.json()["detail"] == "The requested dashboard scope is not available."
    assert "source-forged" not in response.text
    assert reader.calls == 0


def test_uc_010_query_failure_returns_safe_503_problem_detail() -> None:
    client = TestClient(_app(FailingReader()))

    response = client.get("/api/v1/dashboard/summary")

    assert response.status_code == 503
    assert response.json()["title"] == "Dashboard temporarily unavailable"
    assert "database unavailable" not in response.text
    assert response.json()["correlation_id"] == response.headers["x-correlation-id"]


def test_fr_082_invalid_dashboard_clock_returns_safe_400() -> None:
    client = TestClient(
        _app(SQLiteScoreRepository(), dashboard_clock=lambda: datetime(2026, 7, 22))
    )

    response = client.get("/api/v1/dashboard/summary")

    assert response.status_code == 400
    assert response.json()["title"] == "Invalid request"
    assert "timezone-aware" not in response.text


def test_api_012_cors_allows_only_approved_development_origin() -> None:
    client = TestClient(_app(SQLiteScoreRepository()))

    allowed = client.options(
        "/api/v1/dashboard/summary",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    denied = client.options(
        "/api/v1/dashboard/summary",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
    assert "access-control-allow-origin" not in denied.headers


class CountingReader:
    def __init__(self) -> None:
        self.calls = 0

    def list_for_execution(self, execution_id: str) -> list[QualityScore]:
        self.calls += 1
        return []

    def list_for_dashboard_trend(
        self,
        start_at: datetime,
        end_at: datetime,
        allowed_source_ids: frozenset[str],
        include_enterprise: bool,
    ) -> list[QualityScore]:
        self.calls += 1
        return []


class FailingReader(CountingReader):
    def list_for_dashboard_trend(
        self,
        start_at: datetime,
        end_at: datetime,
        allowed_source_ids: frozenset[str],
        include_enterprise: bool,
    ) -> list[QualityScore]:
        raise sqlite3.OperationalError("database unavailable: secret detail")


class ForgedContextResolver:
    def resolve(self, request: Request) -> ActorContext:
        return ActorContext(
            actor_id="forged-user",
            actor_type=ActorType.USER,
            authentication_source="forged-header",
            session_id="forged-session",
            roles=frozenset({"ADMIN"}),
            permitted_source_ids=frozenset({"source-forged"}),
            permitted_dataset_ids=frozenset(),
            can_view_enterprise=True,
            privileged=True,
            issued_at=NOW - timedelta(minutes=1),
            expires_at=NOW + timedelta(minutes=10),
            policy_version=POLICY_VERSION,
            correlation_id=request.state.correlation_id,
            _trust_marker=object(),
        )


def _app(
    reader: SQLiteScoreRepository | CountingReader | FailingReader,
    *,
    source_ids: frozenset[str] = frozenset({"source-a"}),
    use_development_resolver: bool = True,
    context_resolver: ForgedContextResolver | None = None,
    dashboard_clock: Callable[[], datetime] = lambda: NOW,
) -> FastAPI:
    audit_repository = SQLiteAuditRepository()
    audit_service = AuditService(
        audit_repository,
        AuditRedactor(
            AuditRedactionPolicy(
                version="DASHBOARD_API_REDACTION_V1",
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
        AuditFailurePolicy(
            version="DASHBOARD_API_AUDIT_FAILURE_V1",
            default_mode=AuditFailureMode.FAIL_CLOSED,
        ),
    )
    authorization = PolicyAuthorizationService(
        DashboardAuthorizationPolicy(version=POLICY_VERSION),
        audit_service,
        clock=lambda: NOW,
    )
    service = DashboardQueryService(reader, authorization, clock=dashboard_clock)
    resolver: ActorContextResolver | None = context_resolver
    if resolver is None and use_development_resolver:
        resolver = DevelopmentActorContextResolver(
            runtime_environment="development",
            policy_version=POLICY_VERSION,
            permitted_source_ids=source_ids,
            can_view_enterprise=False,
            clock=lambda: NOW,
        )
    return create_dashboard_api(
        service,
        actor_context_resolver=resolver,
        allowed_origins=("http://127.0.0.1:5173",),
        data_origin="test",
    )


def _score(
    execution_id: str,
    scope_type: ScoreScopeType,
    scope_id: str | None,
    value: str,
) -> QualityScore:
    return QualityScore(
        execution_id=execution_id,
        rule_version_id=None,
        scope_type=scope_type,
        scope_id=scope_id,
        score_value=Decimal(value),
        score_status=ScoreStatus.CALCULATED,
        level=ScoreLevel.ACCEPTABLE,
        calculation_details={"included_in_official_aggregation": True},
        calculated_at=NOW - timedelta(days=1),
    )
