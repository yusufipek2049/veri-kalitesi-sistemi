from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from veri_kalitesi.api import DevelopmentActorContextResolver, create_dashboard_api
from veri_kalitesi.api.bff import CSRF_HEADER_NAME
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
from veri_kalitesi.data_sources import (
    DataSource,
    DataSourceQueryService,
    DataSourceStatus,
    Dataset,
    ProfileComparison,
    ProfileComparisonCommandService,
    ProfileComparisonStatus,
    SourceType,
)
from veri_kalitesi.data_sources.errors import ValidationError
from veri_kalitesi.identity import DashboardAuthorizationPolicy, PolicyAuthorizationService
from veri_kalitesi.scoring import SQLiteScoreRepository

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


def test_dq_cap_006_profile_comparison_api_preserves_non_verdict_configuration_state() -> None:
    service = FakeProfileComparisonService()
    client = TestClient(
        _app(
            FakeDataSourceReader((_source("source-a", "Kaynak A"),)),
            frozenset({"source-a"}),
            profile_comparison_service=service,
        )
    )

    response = client.post(
        "/api/v1/profile-comparisons",
        headers={
            CSRF_HEADER_NAME: "development-request-proof-v1",
            "Origin": "https://dq.test",
            "Referer": "https://dq.test/profiles",
            "Sec-Fetch-Site": "same-origin",
        },
        json={
            "dataset_id": "dataset-a",
            "baseline_profile_id": "profile-1",
            "current_profile_id": "profile-2",
            "policy_version": None,
        },
    )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["item"]["status"] == "CONFIGURATION_ERROR"
    assert response.json()["item"]["anomaly_candidate"] is None
    assert service.actor_context is not None


@pytest.mark.parametrize(
    ("baseline_profile_id", "current_profile_id"),
    (("unknown-profile", "profile-2"), ("profile-1", "unknown-profile")),
)
def test_profile_comparison_api_maps_unknown_profile_ids_to_validation_response(
    baseline_profile_id: str,
    current_profile_id: str,
) -> None:
    client = TestClient(
        _app(
            FakeDataSourceReader((_source("source-a", "Kaynak A"),)),
            frozenset({"source-a"}),
            profile_domain_service=FakeComparisonDomainService("validation"),
        )
    )

    response = client.post(
        "/api/v1/profile-comparisons",
        headers=_command_headers(),
        json={
            "dataset_id": "dataset-a",
            "baseline_profile_id": baseline_profile_id,
            "current_profile_id": current_profile_id,
            "policy_version": None,
        },
    )

    assert response.status_code == 400
    assert response.json()["title"] == "Invalid request"
    assert response.json()["detail"] == (
        "The profile comparison request could not be validated."
    )
    assert "unknown profile contains secret" not in response.text


def test_profile_comparison_api_preserves_technical_error_classification() -> None:
    client = TestClient(
        _app(
            FakeDataSourceReader((_source("source-a", "Kaynak A"),)),
            frozenset({"source-a"}),
            profile_domain_service=FakeComparisonDomainService("technical"),
        )
    )

    response = client.post(
        "/api/v1/profile-comparisons",
        headers=_command_headers(),
        json={
            "dataset_id": "dataset-a",
            "baseline_profile_id": "profile-1",
            "current_profile_id": "profile-2",
            "policy_version": None,
        },
    )

    assert response.status_code == 503
    assert response.json()["title"] == "Data sources temporarily unavailable"
    assert "database contains secret" not in response.text


class FakeDataSourceReader:
    def __init__(self, sources: tuple[DataSource, ...]) -> None:
        self.sources = sources
        self.last_allowed_ids: frozenset[str] | None = None

    def list_data_sources(self, allowed_source_ids: frozenset[str]) -> list[DataSource]:
        self.last_allowed_ids = allowed_source_ids
        return [source for source in self.sources if source.data_source_id in allowed_source_ids]


class FailingDataSourceReader:
    def list_data_sources(self, allowed_source_ids: frozenset[str]) -> list[DataSource]:
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
    dashboard = DashboardQueryService(SQLiteScoreRepository(), authorization, clock=lambda: NOW)
    if profile_domain_service is not None:
        profile_comparison_service = ProfileComparisonCommandService(
            profile_domain_service,  # type: ignore[arg-type]
            authorization,
        )
    return create_dashboard_api(
        dashboard,
        actor_context_resolver=resolver,
        allowed_origins=("https://dq.test",),
        data_source_query_service=DataSourceQueryService(reader, authorization),
        profile_comparison_service=profile_comparison_service,
        data_origin="synthetic-test",
    )


def _command_headers() -> dict[str, str]:
    return {
        CSRF_HEADER_NAME: "development-request-proof-v1",
        "Origin": "https://dq.test",
        "Referer": "https://dq.test/profiles",
        "Sec-Fetch-Site": "same-origin",
    }
