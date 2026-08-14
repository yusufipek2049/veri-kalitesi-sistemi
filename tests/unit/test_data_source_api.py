from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from veri_kalitesi.api import DevelopmentActorContextResolver, create_dashboard_api
from veri_kalitesi.api.service_groups import (
    ActorResolverIdentity,
    ApiOptions,
    DataSourceServices,
)
from veri_kalitesi.api.bff import CSRF_HEADER_NAME
from veri_kalitesi.api.data_source_commands import (
    DataSourceCommandError,
    DataSourceCommandResult,
)
from veri_kalitesi.api.development import create_development_app
from veri_kalitesi.audit.models import (
    AuditFailureMode,
    AuditFailurePolicy,
    AuditRedactionPolicy,
)
from veri_kalitesi.audit.redaction import AuditRedactor
from veri_kalitesi.audit.repository import SQLiteAuditRepository
from veri_kalitesi.audit.service import AuditService
from veri_kalitesi.dashboard import DashboardQueryService
from veri_kalitesi.data_sources.models import (
    DataSource,
    DataSourceStatus,
    Dataset,
    ProfileComparison,
    ProfileComparisonStatus,
    SourceType,
)
from veri_kalitesi.data_sources.query import (
    DataSourceQueryService,
    DataSourceView,
    ProfileComparisonCommandService,
)
from veri_kalitesi.data_sources.errors import ValidationError
from veri_kalitesi.identity import DashboardAuthorizationPolicy, PolicyAuthorizationService
from veri_kalitesi.scoring.repository import SQLiteScoreRepository

NOW = datetime(2026, 7, 22, 12, 0, tzinfo=timezone.utc)
POLICY_VERSION = "DATA_SOURCE_API_TEST_V1"


def test_fr_007_data_source_list_is_scope_filtered_and_data_minimum() -> None:
    reader = FakeDataSourceReader(
        (_source("source-a", "Kaynak A"), _source("source-b", "Kaynak B"))
    )
    client = TestClient(_app(reader, frozenset({"source-a"})))

    response = client.get(
        "/api/v1/data-sources",
        headers={"X-Source-IDs": "source-b", "X-Roles": "ADMIN"},
    )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["items"] == [
        {
            "data_source_id": "source-a",
            "name": "Kaynak A",
            "source_type": "POSTGRESQL",
            "status": "ACTIVE",
            "last_test_at": None,
            "available_actions": [],
            "pending_activation_request_id": None,
            "pending_activation_maker_actor_id": None,
            "pending_activation_requested_at": None,
            "pending_activation_expires_at": None,
            "pending_deactivation_request_id": None,
            "pending_deactivation_maker_actor_id": None,
            "pending_deactivation_requested_at": None,
        }
    ]
    assert "secret_reference" not in response.text
    assert "connection_config" not in response.text
    assert "owner_user_id" not in response.text


def test_fr_007_empty_scope_returns_empty_list_without_unscoped_query() -> None:
    reader = FakeDataSourceReader((_source("source-a", "Kaynak A"),))
    client = TestClient(_app(reader, frozenset()))

    response = client.get("/api/v1/data-sources")

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert reader.last_allowed_ids == frozenset()


def test_fr_007_repository_failure_returns_safe_technical_error() -> None:
    client = TestClient(_app(FailingDataSourceReader(), frozenset({"source-a"})))

    response = client.get("/api/v1/data-sources")

    assert response.status_code == 503
    assert response.json()["title"] == "Data sources temporarily unavailable"
    assert "database contains secret" not in response.text


def test_development_api_exposes_only_synthetic_data_source_projection() -> None:
    response = TestClient(create_development_app()).get("/api/v1/data-sources")

    assert response.status_code == 200
    assert len(response.json()["items"]) == 4
    assert response.json()["data_origin"] == "synthetic-development"
    assert "development-reference-only" not in response.text


class FakeDataSourceReader:
    def __init__(self, sources: tuple[DataSource, ...]) -> None:
        self.sources = sources
        self.last_allowed_ids: frozenset[str] | None = None

    def list_data_sources(self, allowed_source_ids: frozenset[str]) -> list[DataSource]:
        self.last_allowed_ids = allowed_source_ids
        return [source for source in self.sources if source.data_source_id in allowed_source_ids]

    def list_all_data_sources(self) -> list[DataSource]:
        return list(self.sources)

    def get_data_source(self, data_source_id: str) -> DataSource:
        return next(source for source in self.sources if source.data_source_id == data_source_id)

    def latest_pending_activation_request(self, data_source_id: str):  # type: ignore[no-untyped-def]
        return None


class FailingDataSourceReader:
    def list_data_sources(self, allowed_source_ids: frozenset[str]) -> list[DataSource]:
        raise sqlite3.OperationalError("database contains secret")

    def list_all_data_sources(self) -> list[DataSource]:
        raise sqlite3.OperationalError("database contains secret")

    def get_data_source(self, data_source_id: str) -> DataSource:
        raise sqlite3.OperationalError("database contains secret")

    def latest_pending_activation_request(self, data_source_id: str):  # type: ignore[no-untyped-def]
        raise sqlite3.OperationalError("database contains secret")


class FakeProfileComparisonService:
    def __init__(self) -> None:
        self.actor_context = None

    def compare(self, **values):  # type: ignore[no-untyped-def]
        self.actor_context = values["actor_context"]
        return ProfileComparison(
            comparison_id="comparison-1",
            dataset_id=values["dataset_id"],
            baseline_profile_id=values["baseline_profile_id"],
            current_profile_id=values["current_profile_id"],
            status=ProfileComparisonStatus.CONFIGURATION_ERROR,
            anomaly_candidate=None,
            result={"configuration_error": "ACTIVE_PROFILE_POLICY_MISSING", "signals": []},
            message="Anomaly verdict was not produced.",
            created_at=NOW,
        )


class FakeComparisonRepository:
    def get_dataset(self, dataset_id: str) -> Dataset:
        return Dataset(
            dataset_id=dataset_id,
            data_source_id="source-a",
            namespace="public",
            name="orders",
        )


class FakeComparisonDomainService:
    def __init__(self, failure: str) -> None:
        self.repository = FakeComparisonRepository()
        self.failure = failure

    def compare_profiles(self, **values):  # type: ignore[no-untyped-def]
        if self.failure == "validation":
            raise ValidationError("unknown profile contains secret")
        raise sqlite3.OperationalError("database contains secret")


def _source(source_id: str, name: str) -> DataSource:
    return DataSource(
        data_source_id=source_id,
        name=name,
        source_type=SourceType.POSTGRESQL,
        connection_config={"host": "must-not-leak"},
        secret_reference="secret/must-not-leak",
        owner_user_id="owner-must-not-leak",
        status=DataSourceStatus.ACTIVE,
    )


def _app(
    reader: FakeDataSourceReader | FailingDataSourceReader,
    source_ids: frozenset[str],
    *,
    profile_comparison_service: FakeProfileComparisonService | None = None,
    profile_domain_service: FakeComparisonDomainService | None = None,
    data_source_mutation_service=None,  # type: ignore[no-untyped-def]
):
    audit_service = AuditService(
        SQLiteAuditRepository(),
        AuditRedactor(
            AuditRedactionPolicy(
                version="DATA_SOURCE_API_REDACTION_V1",
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
        AuditFailurePolicy("DATA_SOURCE_API_AUDIT_V1", AuditFailureMode.FAIL_CLOSED),
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
        allowed_origins=("https://dq.test",),
        clock=lambda: NOW,
    )
    DashboardQueryService(SQLiteScoreRepository(), authorization, clock=lambda: NOW)
    if profile_domain_service is not None:
        ProfileComparisonCommandService(
            profile_domain_service,  # type: ignore[arg-type]
            authorization,
        )
    return create_dashboard_api(
        identity=ActorResolverIdentity(resolver),
        options=ApiOptions(
            allowed_origins=("https://dq.test",),
            data_origin="synthetic-test",
        ),
        data_sources=DataSourceServices(
            query=DataSourceQueryService(reader, authorization),
            mutation=data_source_mutation_service,
        ),
    )


def _command_headers() -> dict[str, str]:
    return {
        CSRF_HEADER_NAME: "development-request-proof-v1",
        "Origin": "https://dq.test",
        "Referer": "https://dq.test/profiles",
        "Sec-Fetch-Site": "same-origin",
    }


# ── Veri kaynağı komut endpoint sözleşmesi ──

_DEV_ORIGIN = "http://127.0.0.1:5173"


def _dev_command_headers() -> dict[str, str]:
    return {
        CSRF_HEADER_NAME: "development-request-proof-v1",
        "Origin": _DEV_ORIGIN,
        "Referer": f"{_DEV_ORIGIN}/data-sources",
        "Sec-Fetch-Site": "same-origin",
    }


class FakeDataSourceCommands:
    def __init__(self) -> None:
        self.decision_values = None

    def decide_activation(self, **values):  # type: ignore[no-untyped-def]
        self.decision_values = values
        source = _source("source-a", "Kaynak A")
        return DataSourceCommandResult(DataSourceView(source))


def test_data_source_decision_uses_request_id_path_and_approve_value() -> None:
    commands = FakeDataSourceCommands()
    client = TestClient(
        _app(
            FakeDataSourceReader((_source("source-a", "Kaynak A"),)),
            frozenset({"source-a"}),
            data_source_mutation_service=commands,
        )
    )
    response = client.post(
        "/api/v1/data-source-activation-requests/request-a/decision",
        headers=_command_headers(),
        json={"decision": "APPROVE", "reason_code": "VALIDATED"},
    )
    assert response.status_code == 200
    assert commands.decision_values["activation_request_id"] == "request-a"
    assert commands.decision_values["decision"] == "APPROVE"
    assert commands.decision_values["actor_context"] is not None


@pytest.mark.parametrize("decision", ["APPROVED", "REJECTED", "INVALID"])
def test_data_source_decision_rejects_non_command_values(decision: str) -> None:
    commands = FakeDataSourceCommands()
    client = TestClient(
        _app(
            FakeDataSourceReader((_source("source-a", "Kaynak A"),)),
            frozenset({"source-a"}),
            data_source_mutation_service=commands,
        )
    )
    response = client.post(
        "/api/v1/data-source-activation-requests/request-a/decision",
        headers=_command_headers(),
        json={"decision": decision, "reason_code": "VALIDATED"},
    )
    assert response.status_code == 422
    assert commands.decision_values is None


def test_data_source_decision_requires_reason_code() -> None:
    commands = FakeDataSourceCommands()
    client = TestClient(
        _app(
            FakeDataSourceReader((_source("source-a", "Kaynak A"),)),
            frozenset({"source-a"}),
            data_source_mutation_service=commands,
        )
    )

    response = client.post(
        "/api/v1/data-source-activation-requests/request-a/decision",
        headers=_command_headers(),
        json={"decision": "APPROVE"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "DATA_SOURCE_INPUT_INVALID"
    assert commands.decision_values is None


@pytest.mark.parametrize(
    ("category", "code", "expected_status"),
    [
        ("authorization", "DATA_SOURCE_PERMISSION_DENIED", 403),
        ("not_found", "ACTIVATION_REQUEST_NOT_FOUND", 404),
        ("conflict", "DATA_SOURCE_STATE_CONFLICT", 409),
        ("validation", "DATA_SOURCE_DOMAIN_VALIDATION_FAILED", 422),
        ("technical", "DATA_SOURCE_PERSISTENCE_UNAVAILABLE", 503),
    ],
)
def test_data_source_command_errors_have_stable_http_contract(
    category: str,
    code: str,
    expected_status: int,
) -> None:
    class _FailingCommands(FakeDataSourceCommands):
        def decide_activation(self, **values):  # type: ignore[no-untyped-def]
            del values
            raise DataSourceCommandError(code, "correlation-command", category=category)

    client = TestClient(
        _app(
            FakeDataSourceReader((_source("source-a", "Kaynak A"),)),
            frozenset({"source-a"}),
            data_source_mutation_service=_FailingCommands(),
        )
    )

    response = client.post(
        "/api/v1/data-source-activation-requests/request-a/decision",
        headers=_command_headers(),
        json={"decision": "APPROVE", "reason_code": "VALIDATED"},
    )

    assert response.status_code == expected_status
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == code
    assert response.json()["correlation_id"] == "correlation-command"
    assert "query unavailable" not in response.text
