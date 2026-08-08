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
from veri_kalitesi.audit.models import (
    AuditFailureMode,
    AuditFailurePolicy,
    AuditRedactionPolicy,
)
from veri_kalitesi.audit.redaction import AuditRedactor
from veri_kalitesi.audit.repository import SQLiteAuditRepository
from veri_kalitesi.audit.service import AuditService
from veri_kalitesi.dashboard import DashboardQueryService
from veri_kalitesi.identity import (
    ActorContext,
    ActorType,
    DashboardAuthorizationPolicy,
    PolicyAuthorizationService,
)
from veri_kalitesi.lineage import StoredLineageSnapshot
from veri_kalitesi.scoring.models import (
    QualityScore,
    ScoreLevel,
    ScoreScopeType,
    ScoreStatus,
)
from veri_kalitesi.scoring.repository import SQLiteScoreRepository

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
    indicators = payload["operational_indicators"]
    assert indicators["measurement_qualification"] == {
        "status": "VALIDATION_REQUIRED",
        "evaluated_scope_count": 1,
        "reason_codes": ["QUALIFICATION_POLICY_UNAVAILABLE"],
        "policy_version": None,
    }
    assert indicators["critical_controls"] == {
        "status": "NOT_AVAILABLE",
        "reason_code": "CRITICAL_RULE_RESULT_NOT_AVAILABLE",
        "passed_count": None,
        "failed_count": None,
        "not_evaluated_count": None,
    }
    assert indicators["technical_errors"]["observation_count"] == 0
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-correlation-id"] == payload["correlation_id"]


def test_fr_054_fr_056_ac_030_technical_failure_is_not_zero_quality() -> None:
    repository = SQLiteScoreRepository()
    repository.add_or_get(
        _score(
            "technical-run",
            ScoreScopeType.SOURCE,
            "source-a",
            None,
            status=ScoreStatus.NOT_CALCULATED_TECHNICAL_ERROR,
            calculated_at=NOW - timedelta(hours=1),
        )
    )
    client = TestClient(_app(repository, source_ids=frozenset({"source-a"})))

    response = client.get("/api/v1/dashboard/summary")

    assert response.status_code == 200
    payload = response.json()
    observations = [item for period in payload["periods"] for item in period["observations"]]
    assert observations[0]["score_value"] is None
    assert observations[0]["score_status"] == "NOT_CALCULATED_TECHNICAL_ERROR"
    indicators = payload["operational_indicators"]
    assert indicators["measurement_qualification"]["status"] == "TECHNICAL_FAILURE"
    assert indicators["technical_errors"] == {
        "observation_count": 1,
        "execution_count": 1,
        "affected_source_count": 1,
        "last_occurred_at": "2026-07-22T11:00:00Z",
    }


def test_fr_054_uc_010_empty_scope_does_not_fabricate_operational_counts() -> None:
    client = TestClient(_app(SQLiteScoreRepository()))

    response = client.get("/api/v1/dashboard/summary")

    assert response.status_code == 200
    indicators = response.json()["operational_indicators"]
    assert indicators["measurement_qualification"] == {
        "status": "NO_DATA",
        "evaluated_scope_count": 0,
        "reason_codes": ["NO_AUTHORIZED_MEASUREMENT"],
        "policy_version": None,
    }
    assert indicators["technical_errors"] == {
        "observation_count": 0,
        "execution_count": 0,
        "affected_source_count": 0,
        "last_occurred_at": None,
    }


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
    lineage_repo: object | None = None,
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
        lineage_evidence_repository=lineage_repo,
    )


class _FakeLineageRepository:
    """Salt okunur lineage endpoint'i için minimum repository double'ı."""

    def get(self, snapshot_id: str) -> StoredLineageSnapshot | None:
        if snapshot_id == "snap-1":
            return StoredLineageSnapshot(
                snapshot_id="snap-1",
                snapshot_kind="GOVERNANCE_PROFILE",
                subject_ref="source-a",
                version_label="1",
                digest="sha256:" + "a" * 64,
                payload={"profile_contract_version": "DQ_GOVERNANCE_PROFILE_V1"},
                created_at=NOW,
            )
        if snapshot_id == "snap-outside":
            return StoredLineageSnapshot(
                snapshot_id="snap-outside",
                snapshot_kind="GOVERNANCE_PROFILE",
                subject_ref="source-outside",
                version_label="1",
                digest="sha256:" + "b" * 64,
                payload={"profile_contract_version": "DQ_GOVERNANCE_PROFILE_V1"},
                created_at=NOW,
            )
        return None


def test_ac_09_lineage_endpoints_are_fail_closed_without_evidence_repository() -> None:
    client = TestClient(_app(SQLiteScoreRepository()))

    snapshot_response = client.get("/api/v1/lineage/snapshots/snap-1")
    projection_response = client.get("/api/v1/governance/source-a/projection")

    assert snapshot_response.status_code == 503
    assert snapshot_response.json()["status"] == 503
    assert snapshot_response.headers["cache-control"] == "no-store"
    assert projection_response.status_code == 503
    assert projection_response.json()["status"] == 503


def test_ac_02_lineage_snapshot_endpoint_serves_stored_evidence() -> None:
    client = TestClient(_app(SQLiteScoreRepository(), lineage_repo=_FakeLineageRepository()))

    response = client.get("/api/v1/lineage/snapshots/snap-1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["snapshot_id"] == "snap-1"
    assert payload["snapshot_kind"] == "GOVERNANCE_PROFILE"
    assert payload["subject_ref"] == "source-a"
    assert payload["version_label"] == "1"
    assert payload["digest"] == "sha256:" + "a" * 64
    assert payload["data_origin"] == "test"
    assert response.headers["cache-control"] == "no-store"


def test_ac_02_lineage_snapshot_endpoint_returns_404_for_unknown_snapshot() -> None:
    client = TestClient(_app(SQLiteScoreRepository(), lineage_repo=_FakeLineageRepository()))

    response = client.get("/api/v1/lineage/snapshots/missing")

    assert response.status_code == 404
    assert response.json()["status"] == 404


def test_lineage_snapshot_unauthenticated_request_is_rejected() -> None:
    client = TestClient(
        _app(
            SQLiteScoreRepository(),
            use_development_resolver=False,
            lineage_repo=_FakeLineageRepository(),
        )
    )

    response = client.get("/api/v1/lineage/snapshots/snap-1")

    assert response.status_code == 401
    assert response.json()["status"] == 401


def test_lineage_snapshot_outside_actor_scope_is_denied() -> None:
    client = TestClient(_app(SQLiteScoreRepository(), lineage_repo=_FakeLineageRepository()))

    response = client.get("/api/v1/lineage/snapshots/snap-outside")

    assert response.status_code == 403
    assert response.json()["status"] == 403


def test_governance_projection_outside_actor_scope_is_denied() -> None:
    client = TestClient(_app(SQLiteScoreRepository(), lineage_repo=_FakeLineageRepository()))

    response = client.get("/api/v1/governance/source-outside/projection")

    assert response.status_code == 403
    assert response.json()["status"] == 403


# ---------------------------------------------------------------------------
# BE-01: FR-057 API-level filtre testleri
# ---------------------------------------------------------------------------


def test_be01_ac_05_no_filters_backward_compatible_applied_filters_echo() -> None:
    """Parametresiz istek: 30 gün, applied_filters varsayılanları taşır."""
    repository = SQLiteScoreRepository()
    repository.add_or_get(_score("exec", ScoreScopeType.SOURCE, "source-a", "80.00"))
    client = TestClient(_app(repository, source_ids=frozenset({"source-a"})))

    response = client.get("/api/v1/dashboard/summary")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["periods"]) == 30
    af = payload["applied_filters"]
    assert af is not None
    assert af["scope_type"] is None
    assert af["scope_id"] is None
    assert af["score_status"] is None
    assert af["level"] is None
    assert "window_start" in af
    assert "window_end" in af


def test_be01_ac_04_invalid_scope_type_returns_400() -> None:
    """Geçersiz scope_type enum değeri fail-closed 400 hatası."""
    client = TestClient(_app(SQLiteScoreRepository()))

    response = client.get(
        "/api/v1/dashboard/summary",
        params={"scope_type": "INVALID_SCOPE"},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["status"] == 400
    assert len(body["detail"]) > 0


def test_be01_ac_04_invalid_score_status_returns_400() -> None:
    """Geçersiz score_status enum değeri fail-closed 400 hatası."""
    client = TestClient(_app(SQLiteScoreRepository()))

    response = client.get(
        "/api/v1/dashboard/summary",
        params={"score_status": "BOGUS_STATUS"},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["status"] == 400


def test_be01_ac_04_invalid_level_returns_400() -> None:
    """Geçersiz level enum değeri fail-closed 400 hatası."""
    client = TestClient(_app(SQLiteScoreRepository()))

    response = client.get(
        "/api/v1/dashboard/summary",
        params={"level": "NOT_A_LEVEL"},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["status"] == 400


def test_be01_ac_03_unauthorized_scope_id_returns_403() -> None:
    """Yetkisiz scope_id 403 hatası döner, veri sızdırmaz."""
    repository = SQLiteScoreRepository()
    repository.add_or_get(_score("exec", ScoreScopeType.SOURCE, "source-a", "80.00"))
    client = TestClient(_app(repository, source_ids=frozenset({"source-a"})))

    response = client.get(
        "/api/v1/dashboard/summary",
        params={"scope_id": "source-forbidden"},
    )

    assert response.status_code == 403


def test_be01_ac_01_scope_filter_echoed_in_response() -> None:
    """scope_type ve scope_id yanıtta yansıtılır."""
    repository = SQLiteScoreRepository()
    repository.add_or_get(_score("exec", ScoreScopeType.SOURCE, "source-a", "80.00"))
    client = TestClient(_app(repository, source_ids=frozenset({"source-a"})))

    response = client.get(
        "/api/v1/dashboard/summary",
        params={"scope_type": "SOURCE", "scope_id": "source-a"},
    )

    assert response.status_code == 200
    af = response.json()["applied_filters"]
    assert af["scope_type"] == "SOURCE"
    assert af["scope_id"] == "source-a"


def test_be01_ac_01_score_status_filter_echoed_in_response() -> None:
    """score_status filtresi yanıtta yansıtılır."""
    repository = SQLiteScoreRepository()
    repository.add_or_get(_score("exec", ScoreScopeType.SOURCE, "source-a", "80.00"))
    client = TestClient(_app(repository, source_ids=frozenset({"source-a"})))

    response = client.get(
        "/api/v1/dashboard/summary",
        params={"score_status": "CALCULATED"},
    )

    assert response.status_code == 200
    af = response.json()["applied_filters"]
    assert af["score_status"] == "CALCULATED"


def test_be01_ac_01_level_filter_echoed_in_response() -> None:
    """level filtresi yanıtta yansıtılır."""
    repository = SQLiteScoreRepository()
    repository.add_or_get(_score("exec", ScoreScopeType.SOURCE, "source-a", "80.00"))
    client = TestClient(_app(repository, source_ids=frozenset({"source-a"})))

    response = client.get(
        "/api/v1/dashboard/summary",
        params={"level": "ACCEPTABLE"},
    )

    assert response.status_code == 200
    af = response.json()["applied_filters"]
    assert af["level"] == "ACCEPTABLE"


def test_be01_ac_04_blank_scope_id_returns_400() -> None:
    """Boş scope_id fail-closed 400 hatası."""
    client = TestClient(_app(SQLiteScoreRepository()))

    response = client.get(
        "/api/v1/dashboard/summary",
        params={"scope_id": "   "},
    )

    assert response.status_code == 400


def _score(
    execution_id: str,
    scope_type: ScoreScopeType,
    scope_id: str | None,
    value: str | None,
    *,
    status: ScoreStatus = ScoreStatus.CALCULATED,
    calculated_at: datetime = NOW - timedelta(days=1),
) -> QualityScore:
    return QualityScore(
        execution_id=execution_id,
        rule_version_id=None,
        scope_type=scope_type,
        scope_id=scope_id,
        score_value=Decimal(value) if value is not None else None,
        score_status=status,
        level=ScoreLevel.ACCEPTABLE if value is not None else None,
        calculation_details={"included_in_official_aggregation": value is not None},
        calculated_at=calculated_at,
    )
