"""Faz 9 rapor listeleme/getirme HTTP yüzeyi testleri."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from veri_kalitesi.api.app import create_dashboard_api
from veri_kalitesi.api.service_groups import ActorResolverIdentity, ReportingServices
from veri_kalitesi.identity import ActorContextIssuer, ActorType
from veri_kalitesi.reporting.errors import ReportNotFoundError
from veri_kalitesi.reporting.models import Report, ReportFormat, ReportStatus, ReportType
from veri_kalitesi.reporting.service import ReportQueryService


class _Resolver:
    def __init__(self, actor_id: str) -> None:
        self.actor_id = actor_id
        self.issuer = ActorContextIssuer()

    def resolve(self, request):  # type: ignore[no-untyped-def]
        now = datetime.now(timezone.utc)
        return self.issuer.issue(
            actor_id=self.actor_id,
            actor_type=ActorType.USER,
            authentication_source="report-api-test",
            session_id=f"session-{self.actor_id}",
            roles=frozenset({"DATA_VIEWER"}),
            permitted_source_ids=frozenset(),
            permitted_dataset_ids=frozenset(),
            can_view_enterprise=False,
            privileged=False,
            issued_at=now,
            expires_at=now + timedelta(minutes=5),
            policy_version="REPORT_API_TEST_V1",
            correlation_id=request.state.correlation_id,
        )


class _Repository:
    def __init__(self, reports: tuple[Report, ...]) -> None:
        self.reports = reports

    def get_report(self, report_id: str) -> Report:
        for report in self.reports:
            if report.report_id == report_id:
                return report
        raise ReportNotFoundError(report_id)

    def list_reports_by_user(
        self,
        requested_by: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Report, ...]:
        owned = tuple(item for item in self.reports if item.requested_by == requested_by)
        return owned[offset : offset + limit]


class _AuditSink:
    def __init__(self) -> None:
        self.events = []

    def append(self, event):  # type: ignore[no-untyped-def]
        self.events.append(event)
        return None


def _report(report_id: str, owner: str) -> Report:
    return Report(
        report_id=report_id,
        report_type=ReportType.SUMMARY,
        format=ReportFormat.CSV,
        requested_by=owner,
        parameters={"personal_filter": "must-not-leak"},
        status=ReportStatus.READY,
        online_file_reference="/private/report.csv",
        failure_reason="private backend detail",
        created_at=datetime(2026, 8, 14, tzinfo=timezone.utc),
    )


def _client(actor_id: str = "user-a") -> tuple[TestClient, _AuditSink]:
    audit = _AuditSink()
    service = ReportQueryService(
        _Repository((_report("report-a", "user-a"), _report("report-b", "user-b"))),
        audit,
    )
    app = create_dashboard_api(
        identity=ActorResolverIdentity(_Resolver(actor_id)),
        reporting=ReportingServices(query=service),
    )
    return TestClient(app), audit


def test_report_list_and_get_are_owner_scoped_audited_and_data_minimum() -> None:
    client, audit = _client()

    listing = client.get("/api/v1/reports")
    detail = client.get("/api/v1/reports/report-a")

    assert listing.status_code == 200
    assert [item["report_id"] for item in listing.json()["items"]] == ["report-a"]
    assert detail.status_code == 200
    assert "parameters" not in detail.json()["item"]
    assert "online_file_reference" not in detail.json()["item"]
    assert "failure_reason" not in detail.json()["item"]
    assert [event.action for event in audit.events] == ["REPORT_LIST_VIEWED", "REPORT_VIEWED"]
    assert listing.headers["cache-control"] == "no-store"
    assert listing.headers["x-correlation-id"]


def test_report_get_hides_another_users_report_and_audits_denial() -> None:
    client, audit = _client()

    response = client.get("/api/v1/reports/report-b")

    assert response.status_code == 404
    assert response.json()["detail"] == "The requested report is not available."
    assert audit.events[-1].action == "REPORT_ACCESS_DENIED"
    assert audit.events[-1].result.value == "DENIED"


def test_report_routes_fail_closed_without_identity() -> None:
    service = ReportQueryService(_Repository((_report("report-a", "user-a"),)), _AuditSink())
    app = create_dashboard_api(reporting=ReportingServices(query=service))

    response = TestClient(app).get("/api/v1/reports")

    assert response.status_code == 401
