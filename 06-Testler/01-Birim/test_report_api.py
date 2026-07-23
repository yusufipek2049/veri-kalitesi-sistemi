from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from veri_kalitesi.api import DevelopmentActorContextResolver, create_dashboard_api
from veri_kalitesi.api.development import create_development_app
from veri_kalitesi.audit import (
    AuditFailureMode,
    AuditFailurePolicy,
    AuditRedactor,
    AuditService,
    SQLiteAuditRepository,
    build_default_redaction_policy,
)
from veri_kalitesi.dashboard import DashboardQueryService
from veri_kalitesi.identity import DashboardAuthorizationPolicy, PolicyAuthorizationService
from veri_kalitesi.reporting import (
    ReportPreviewAccessPolicy,
    ReportPreviewService,
    ReportScoreObservation,
)
from veri_kalitesi.scoring import SQLiteScoreRepository

NOW = datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc)
POLICY_VERSION = "REPORT_API_TEST_V1"


def test_fr_072_uc_015_report_summary_is_scope_filtered_and_data_minimum() -> None:
    reader = RecordingReader()
    response = TestClient(_app(reader)).get(
        "/api/v1/reports/summary",
        headers={"X-Source-IDs": "source-forged", "X-Roles": "ADMIN"},
    )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "api_version": "v1",
        "data_origin": "synthetic-test",
        "correlation_id": response.headers["x-correlation-id"],
        "report_type": "SUMMARY",
        "created_at": "2026-07-23T12:00:00Z",
        "period_start": "2026-06-23T12:00:00Z",
        "period_end": "2026-07-23T12:00:00Z",
        "source_count": 0,
        "calculated_source_count": 0,
        "average_score": None,
        "policy_version": "REPORT_PREVIEW_TEST_V1",
        "masking_mode": "AGGREGATED_ONLY",
        "rows": [],
    }
    assert reader.allowed_source_ids == frozenset({"source-a"})
    assert "source-forged" not in response.text
    assert "actor_id" not in response.text
    assert "reason_code" not in response.text


def test_ac_021_report_role_is_required_before_reader_access() -> None:
    reader = RecordingReader()
    response = TestClient(_app(reader, roles=frozenset({"DATA_VIEWER"}))).get(
        "/api/v1/reports/summary"
    )

    assert response.status_code == 403
    assert response.json()["title"] == "Access denied"
    assert reader.allowed_source_ids is None


def test_nfr_prv_002_development_report_keeps_no_data_and_technical_error_distinct() -> None:
    response = TestClient(create_development_app()).get("/api/v1/reports/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_count"] == 4
    assert payload["calculated_source_count"] == 2
    assert payload["average_score"] == "87.10"
    rows = {row["source_id"]: row for row in payload["rows"]}
    assert rows["source-risk-mart"]["score_status"] == "NO_DATA"
    assert rows["source-risk-mart"]["score_value"] is None
    assert rows["source-regulatory-api"]["score_status"] == "NOT_CALCULATED_TECHNICAL_ERROR"
    assert rows["source-regulatory-api"]["score_value"] is None
    assert "development-reference-only" not in response.text


class RecordingReader:
    def __init__(self) -> None:
        self.allowed_source_ids: frozenset[str] | None = None

    def latest_source_scores(
        self,
        start_at: datetime,
        end_at: datetime,
        allowed_source_ids: frozenset[str],
    ) -> tuple[ReportScoreObservation, ...]:
        self.allowed_source_ids = allowed_source_ids
        return ()


def _app(
    reader: RecordingReader,
    *,
    roles: frozenset[str] = frozenset({"DATA_OWNER"}),
):
    audit_service = AuditService(
        SQLiteAuditRepository(),
        AuditRedactor(build_default_redaction_policy()),
        AuditFailurePolicy(
            version="REPORT_API_AUDIT_V1",
            default_mode=AuditFailureMode.FAIL_CLOSED,
        ),
    )
    resolver = DevelopmentActorContextResolver(
        runtime_environment="development",
        policy_version=POLICY_VERSION,
        permitted_source_ids=frozenset({"source-a"}),
        can_view_enterprise=False,
        roles=roles,
        clock=lambda: NOW,
    )
    report_service = ReportPreviewService(
        reader,
        audit_service,
        ReportPreviewAccessPolicy(
            version="REPORT_PREVIEW_TEST_V1",
            actor_policy_version=POLICY_VERSION,
        ),
        clock=lambda: NOW,
    )
    return create_dashboard_api(
        DashboardQueryService(
            SQLiteScoreRepository(),
            _unused_authorization(audit_service),
            clock=lambda: NOW,
        ),
        actor_context_resolver=resolver,
        report_preview_service=report_service,
        data_origin="synthetic-test",
        clock=lambda: NOW,
    )


def _unused_authorization(audit_service: AuditService) -> PolicyAuthorizationService:
    return PolicyAuthorizationService(
        DashboardAuthorizationPolicy(version=POLICY_VERSION),
        audit_service,
        clock=lambda: NOW,
    )
