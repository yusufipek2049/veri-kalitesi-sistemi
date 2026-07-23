from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from veri_kalitesi.api import DevelopmentActorContextResolver, create_dashboard_api
from veri_kalitesi.api.development import create_development_app
from veri_kalitesi.audit import (
    AuditFailureMode,
    AuditFailurePolicy,
    AuditRedactionPolicy,
    AuditRedactor,
    AuditService,
    SQLiteAuditRepository,
)
from veri_kalitesi.dashboard import DashboardQueryService
from veri_kalitesi.executions import (
    ExecutionQueryService,
    ExecutionStatus,
    ExecutionType,
    RuleExecution,
    WorkloadClass,
)
from veri_kalitesi.identity import DashboardAuthorizationPolicy, PolicyAuthorizationService
from veri_kalitesi.scoring import SQLiteScoreRepository

NOW = datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc)
POLICY_VERSION = "EXECUTION_API_TEST_V1"


def test_fr_043_execution_list_is_source_scoped_and_data_minimum() -> None:
    reader = FakeExecutionReader(
        (
            _execution("execution-a", ("source-a",)),
            _execution("execution-mixed", ("source-a", "source-b")),
            _execution("execution-legacy", ()),
        )
    )
    client = TestClient(_app(reader, frozenset({"source-a"})))

    response = client.get(
        "/api/v1/executions",
        headers={"X-Source-IDs": "source-b", "X-Roles": "ADMIN"},
    )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["limit"] == 100
    assert response.json()["items"] == [
        {
            "execution_id": "execution-a",
            "execution_type": "MANUAL",
            "status": "TECHNICAL_ERROR",
            "workload_class": "HEAVY",
            "rule_count": 2,
            "source_count": 1,
            "attempt_count": 3,
            "error_class": "CONNECTION_UNAVAILABLE",
            "created_at": "2026-07-23T12:00:00Z",
            "started_at": "2026-07-23T12:00:00Z",
            "finished_at": "2026-07-23T12:00:00Z",
        }
    ]
    for protected_field in (
        "idempotency_key_hash",
        "payload_hash",
        "rule_version_ids",
        "scope",
        "triggered_by",
        "source_ids",
        "cancel_requested_by",
        "cancel_reason",
        "must-not-leak",
    ):
        assert protected_field not in response.text


def test_fr_043_empty_source_scope_does_not_become_unscoped_query() -> None:
    reader = FakeExecutionReader((_execution("execution-a", ("source-a",)),))
    response = TestClient(_app(reader, frozenset())).get("/api/v1/executions")

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert reader.last_allowed_ids == frozenset()


def test_fr_044_repository_failure_returns_safe_technical_error() -> None:
    response = TestClient(_app(FailingExecutionReader(), frozenset({"source-a"}))).get(
        "/api/v1/executions"
    )

    assert response.status_code == 503
    assert response.json()["title"] == "Executions temporarily unavailable"
    assert "database contains sensitive detail" not in response.text


def test_development_api_exposes_all_synthetic_execution_states() -> None:
    response = TestClient(create_development_app()).get("/api/v1/executions")

    assert response.status_code == 200
    assert len(response.json()["items"]) == 8
    assert {item["status"] for item in response.json()["items"]} == {
        "QUEUED",
        "RUNNING",
        "CANCEL_REQUESTED",
        "SUCCESS",
        "PARTIAL",
        "TECHNICAL_ERROR",
        "TIMEOUT",
        "CANCELLED",
    }
    assert response.json()["data_origin"] == "synthetic-development"
    assert "development-user" not in response.text
    assert "development-reason" not in response.text


class FakeExecutionReader:
    def __init__(self, executions: tuple[RuleExecution, ...]) -> None:
        self.executions = executions
        self.last_allowed_ids: frozenset[str] | None = None

    def list_executions_for_sources(
        self,
        allowed_source_ids: frozenset[str],
        *,
        limit: int = 100,
    ) -> list[RuleExecution]:
        self.last_allowed_ids = allowed_source_ids
        return [
            execution
            for execution in self.executions
            if execution.source_ids and set(execution.source_ids).issubset(allowed_source_ids)
        ][:limit]


class FailingExecutionReader:
    def list_executions_for_sources(
        self,
        allowed_source_ids: frozenset[str],
        *,
        limit: int = 100,
    ) -> list[RuleExecution]:
        raise sqlite3.OperationalError("database contains sensitive detail")


def _execution(execution_id: str, source_ids: tuple[str, ...]) -> RuleExecution:
    return RuleExecution(
        execution_id=execution_id,
        idempotency_key_hash="synthetic",
        payload_hash="synthetic",
        rule_version_ids=("version-a", "version-b"),
        scope={"private": "must-not-leak"},
        triggered_by="actor-must-not-leak",
        correlation_id="correlation-domain-must-not-leak",
        source_ids=source_ids,
        workload_class=WorkloadClass.HEAVY,
        execution_type=ExecutionType.MANUAL,
        status=ExecutionStatus.TECHNICAL_ERROR,
        error_class="CONNECTION_UNAVAILABLE",
        attempt_count=3,
        created_at=NOW,
        started_at=NOW,
        finished_at=NOW,
        cancel_requested_by="actor-must-not-leak",
        cancel_reason="must-not-leak",
    )


def _app(
    reader: FakeExecutionReader | FailingExecutionReader,
    source_ids: frozenset[str],
):
    audit_service = AuditService(
        SQLiteAuditRepository(),
        AuditRedactor(
            AuditRedactionPolicy(
                version="EXECUTION_API_REDACTION_V1",
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
        AuditFailurePolicy("EXECUTION_API_AUDIT_V1", AuditFailureMode.FAIL_CLOSED),
    )
    authorization = PolicyAuthorizationService(
        DashboardAuthorizationPolicy(version=POLICY_VERSION),
        audit_service,
        clock=lambda: NOW,
    )
    resolver = DevelopmentActorContextResolver(
        runtime_environment="development",
        policy_version=POLICY_VERSION,
        permitted_source_ids=source_ids,
        can_view_enterprise=False,
        clock=lambda: NOW,
    )
    dashboard = DashboardQueryService(SQLiteScoreRepository(), authorization, clock=lambda: NOW)
    return create_dashboard_api(
        dashboard,
        actor_context_resolver=resolver,
        execution_query_service=ExecutionQueryService(reader, authorization),
        data_origin="synthetic-test",
    )
