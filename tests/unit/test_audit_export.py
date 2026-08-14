from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from starlette.requests import Request

from veri_kalitesi.api import DevelopmentActorContextResolver, create_dashboard_api
from veri_kalitesi.api.service_groups import ActorResolverIdentity, ApiOptions, AuditServices
from veri_kalitesi.audit.export import EXPORT_COLUMNS, AuditEventExporter
from veri_kalitesi.audit.models import (
    AuditAccessPolicy,
    AuditEventInput,
    AuditFailureMode,
    AuditFailurePolicy,
    AuditQuery,
    AuditResult,
)
from veri_kalitesi.audit.policies import build_default_redaction_policy
from veri_kalitesi.audit.redaction import AuditRedactor
from veri_kalitesi.audit.repository import SQLiteAuditRepository
from veri_kalitesi.audit.service import AuditQueryService, AuditService

NOW = datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc)
CONTEXT_POLICY = "AUDIT_EXPORT_CONTEXT_V1"


def test_exporter_serializes_csv_and_json_without_value_summaries() -> None:
    repository, audit_service, query_service = _components()
    audit_service.append(_event())
    page = query_service.export(_query(), _resolver().resolve(_request()), export_format="csv")

    csv_rows = list(csv.DictReader(io.StringIO(AuditEventExporter(page).to_csv())))
    json_rows = json.loads(AuditEventExporter(page).to_json())

    assert tuple(csv_rows[0]) == EXPORT_COLUMNS
    assert csv_rows[0]["action"] == "RULE_ACTIVATION"
    assert json_rows[0]["redacted_field_count"] == 1
    assert "old_values" not in csv_rows[0]
    assert "new_values" not in json_rows[0]


def test_empty_export_contains_csv_header_and_empty_json_array() -> None:
    _repository, _audit_service, query_service = _components()
    page = query_service.export(_query(), _resolver().resolve(_request()), export_format="json")
    exporter = AuditEventExporter(page)

    assert exporter.to_csv() == ",".join(EXPORT_COLUMNS) + "\n"
    assert exporter.to_json() == "[]"


def test_export_endpoint_requires_audit_viewer_role() -> None:
    repository, audit_service, query_service = _components()
    response = TestClient(
        _app(repository, audit_service, query_service, roles=frozenset({"DATA_VIEWER"}))
    ).get("/api/v1/audit/events/export")

    assert response.status_code == 403
    assert "attachment" not in response.headers


def test_export_endpoint_returns_download_headers_and_records_audit_event() -> None:
    repository, audit_service, query_service = _components()
    audit_service.append(_event())
    response = TestClient(_app(repository, audit_service, query_service)).get(
        "/api/v1/audit/events/export", params={"format": "json"}
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["content-disposition"] == (
        'attachment; filename="audit-export-2026-08-11.json"'
    )
    assert len(response.json()) == 1
    export_event = repository.list_events()[-1]
    assert export_event.action == "AUDIT_EXPORT_COMPLETED"
    assert export_event.object_type == "AuditExport"
    assert export_event.new_value_summary["exported_count"] == 1


def test_actions_endpoint_returns_turkish_labels() -> None:
    repository, audit_service, query_service = _components()
    response = TestClient(_app(repository, audit_service, query_service)).get(
        "/api/v1/audit/actions"
    )

    assert response.status_code == 200
    assert {"action": "RULE_ACTIVATION", "label": "Kural aktivasyonu"} in response.json()["items"]


def _components() -> tuple[SQLiteAuditRepository, AuditService, AuditQueryService]:
    repository = SQLiteAuditRepository()
    audit_service = AuditService(
        repository,
        AuditRedactor(build_default_redaction_policy()),
        AuditFailurePolicy(
            version="AUDIT_EXPORT_FAILURE_V1",
            default_mode=AuditFailureMode.FAIL_CLOSED,
        ),
    )
    query_service = AuditQueryService(
        repository,
        audit_service,
        AuditAccessPolicy(
            version="AUDIT_EXPORT_ACCESS_V1",
            context_policy_version=CONTEXT_POLICY,
        ),
        clock=lambda: NOW,
    )
    return repository, audit_service, query_service


def _app(
    repository: SQLiteAuditRepository,
    audit_service: AuditService,
    query_service: AuditQueryService,
    *,
    roles: frozenset[str] = frozenset({"AUDIT_VIEWER"}),
):
    del repository, audit_service
    return create_dashboard_api(
        identity=ActorResolverIdentity(_resolver(roles)),
        audit=AuditServices(query=query_service),
        options=ApiOptions(clock=lambda: NOW),
    )


def _resolver(
    roles: frozenset[str] = frozenset({"AUDIT_VIEWER"}),
) -> DevelopmentActorContextResolver:
    return DevelopmentActorContextResolver(
        runtime_environment="development",
        policy_version=CONTEXT_POLICY,
        permitted_source_ids=frozenset(),
        can_view_enterprise=False,
        roles=roles,
        clock=lambda: NOW,
    )


def _request() -> Request:
    request = Request({"type": "http", "headers": []})
    request.state.correlation_id = "audit-export-test"
    return request


def _query() -> AuditQuery:
    return AuditQuery(
        start_at=NOW - timedelta(days=7),
        end_at=NOW,
        reason_code="AUDIT_EXPORT",
        page_size=10000,
    )


def _event() -> AuditEventInput:
    return AuditEventInput(
        actor_id="audit-user",
        actor_type="USER",
        correlation_id="audit-export-source",
        action="RULE_ACTIVATION",
        object_type="QualityRule",
        object_id="rule-1",
        result=AuditResult.SUCCESS,
        reason_code="APPROVED",
        old_values={"secret": "must-not-leak"},
        new_values={},
        occurred_at=NOW - timedelta(hours=1),
    )
