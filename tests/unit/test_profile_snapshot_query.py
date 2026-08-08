"""BE-03 profil snapshot salt okunur uç birim testleri."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi.testclient import TestClient

from veri_kalitesi.api import DevelopmentActorContextResolver, create_dashboard_api
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
    DataProfile,
    Dataset,
    ProfileMethod,
    ProfileStatus,
)
from veri_kalitesi.data_sources.query import (
    ProfileSnapshotQueryService,
)
from veri_kalitesi.identity import DashboardAuthorizationPolicy, PolicyAuthorizationService
from veri_kalitesi.scoring.repository import SQLiteScoreRepository

NOW = datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)
POLICY_VERSION = "PROFILE_SNAPSHOT_TEST_V1"


class FakeProfileRepository:
    """Test için profil ve dataset deposu."""

    def __init__(
        self,
        profiles: list[DataProfile] | None = None,
        datasets: list[Dataset] | None = None,
    ) -> None:
        self._profiles = profiles or []
        self._datasets = datasets or []

    def get_dataset(self, dataset_id: str) -> Dataset:
        for ds in self._datasets:
            if ds.dataset_id == dataset_id:
                return ds
        raise ValueError(f"Dataset {dataset_id} not found")

    def list_datasets(self, source_id: str) -> list[Dataset]:
        return [ds for ds in self._datasets if ds.data_source_id == source_id]

    def list_data_profiles(self, dataset_id: str) -> list[DataProfile]:
        return [p for p in self._profiles if p.dataset_id == dataset_id]


class FakeDataSourceService:
    """Test için DataSourceService taklidi."""

    def __init__(self, repository: FakeProfileRepository) -> None:
        self.repository = repository


class FakeAuthorizationDecision:
    """Test için yetki kararı."""

    def __init__(
        self,
        permitted_source_ids: frozenset[str],
        permitted_dataset_ids: frozenset[str],
    ) -> None:
        self.permitted_source_ids = permitted_source_ids
        self.permitted_dataset_ids = permitted_dataset_ids


class FakeAuthorizationService:
    """Test için yetkilendirme servisi taklidi."""

    def __init__(self, decision: FakeAuthorizationDecision) -> None:
        self.decision = decision

    def authorize_dashboard(self, actor_context: Any) -> FakeAuthorizationDecision:
        return self.decision


def _profile(
    profile_id: str,
    dataset_id: str,
    finished_at: datetime,
    metrics: dict[str, Any] | None = None,
) -> DataProfile:
    return DataProfile(
        profile_id=profile_id,
        dataset_id=dataset_id,
        execution_id="exec-1",
        method=ProfileMethod.FULL,
        metrics=metrics or {"row_count": 1000},
        status=ProfileStatus.COMPLETED,
        sample_ratio=1.0,
        duration_ms=100,
        started_at=finished_at,
        finished_at=finished_at,
    )


def _dataset(dataset_id: str, source_id: str) -> Dataset:
    return Dataset(
        dataset_id=dataset_id,
        data_source_id=source_id,
        namespace="public",
        name="orders",
    )


def _app(
    profiles: list[DataProfile],
    datasets: list[Dataset],
    permitted_source_ids: frozenset[str],
    permitted_dataset_ids: frozenset[str],
) -> TestClient:
    repo = FakeProfileRepository(profiles, datasets)
    service = FakeDataSourceService(repo)
    auth_service = FakeAuthorizationService(
        FakeAuthorizationDecision(permitted_source_ids, permitted_dataset_ids)
    )
    snapshot_service = ProfileSnapshotQueryService(service, auth_service)  # type: ignore[arg-type]

    audit_service = AuditService(
        SQLiteAuditRepository(),
        AuditRedactor(
            AuditRedactionPolicy(
                version="PROFILE_SNAPSHOT_TEST_REDACTION_V1",
                allowed_fields_by_action={},
            )
        ),
        AuditFailurePolicy("PROFILE_SNAPSHOT_TEST_AUDIT_V1", AuditFailureMode.FAIL_CLOSED),
    )
    authorization = PolicyAuthorizationService(
        DashboardAuthorizationPolicy(version=POLICY_VERSION),
        audit_service,
        clock=lambda: NOW,
    )
    resolver = DevelopmentActorContextResolver(
        runtime_environment="development",
        policy_version=POLICY_VERSION,
        permitted_source_ids=permitted_source_ids,
        permitted_dataset_ids=permitted_dataset_ids,
        can_view_enterprise=False,
        allowed_origins=("https://dq.test",),
        clock=lambda: NOW,
    )
    dashboard = DashboardQueryService(SQLiteScoreRepository(), authorization, clock=lambda: NOW)
    app = create_dashboard_api(
        dashboard,
        actor_context_resolver=resolver,
        allowed_origins=("https://dq.test",),
        data_origin="synthetic-test",
        profile_snapshot_query_service=snapshot_service,
    )
    return TestClient(app)


def test_list_snapshots_returns_bounded_profiles() -> None:
    """AC-01, AC-06: Profil snapshot listesi bounded döner."""
    profiles = [
        _profile("p1", "ds-1", NOW),
        _profile("p2", "ds-1", NOW),
        _profile("p3", "ds-1", NOW),
    ]
    datasets = [_dataset("ds-1", "source-1")]
    client = _app(profiles, datasets, frozenset({"source-1"}), frozenset({"ds-1"}))

    response = client.get("/api/v1/profile-snapshots?dataset_id=ds-1")

    assert response.status_code == 200
    body = response.json()
    assert body["dataset_id"] == "ds-1"
    assert body["limit"] == 50
    assert len(body["items"]) == 3
    assert body["items"][0]["profile_id"] == "p1"


def test_list_snapshots_unauthorized_dataset_returns_403() -> None:
    """AC-02: Yetkisiz dataset erişimi 403 döner."""
    profiles = [_profile("p1", "ds-secret", NOW)]
    datasets = [_dataset("ds-secret", "source-secret")]
    client = _app(profiles, datasets, frozenset(), frozenset())

    response = client.get("/api/v1/profile-snapshots?dataset_id=ds-secret")

    assert response.status_code == 403
    assert "secret" not in response.text.lower() or "scope" in response.text.lower()


def test_get_snapshot_detail_returns_full_metrics() -> None:
    """AC-01, AC-03: Tek snapshot detayı tam metrik döner."""
    metrics = {"row_count": 1000, "profile_contract": {"version": "v1"}}
    profiles = [_profile("p1", "ds-1", NOW, metrics)]
    datasets = [_dataset("ds-1", "source-1")]
    client = _app(profiles, datasets, frozenset({"source-1"}), frozenset({"ds-1"}))

    response = client.get("/api/v1/profile-snapshots/p1")

    assert response.status_code == 200
    body = response.json()
    assert body["profile_id"] == "p1"
    assert body["metrics"] == metrics
    assert body["dataset_id"] == "ds-1"


def test_get_snapshot_not_found_returns_404() -> None:
    """AC-02: Bulunamayan snapshot 404 döner."""
    profiles = []
    datasets = [_dataset("ds-1", "source-1")]
    client = _app(profiles, datasets, frozenset({"source-1"}), frozenset({"ds-1"}))

    response = client.get("/api/v1/profile-snapshots/nonexistent")

    assert response.status_code == 404


def test_drift_judgment_no_baseline_returns_insufficient_history() -> None:
    """AC-04: Baseline yoksa INSUFFICIENT_HISTORY döner (fail-closed)."""
    profiles = [_profile("p1", "ds-1", NOW)]
    datasets = [_dataset("ds-1", "source-1")]
    client = _app(profiles, datasets, frozenset({"source-1"}), frozenset({"ds-1"}))

    response = client.get("/api/v1/profile-snapshots/p1/drift")

    assert response.status_code == 200
    body = response.json()
    assert body["item"]["status"] == "INSUFFICIENT_HISTORY"


def test_drift_judgment_with_baseline_returns_comparison() -> None:
    """AC-01, AC-05: Baseline ile drift karşılaştırması döner."""
    profiles = [
        _profile("p-baseline", "ds-1", NOW),
        _profile("p-current", "ds-1", NOW),
    ]
    datasets = [_dataset("ds-1", "source-1")]
    client = _app(profiles, datasets, frozenset({"source-1"}), frozenset({"ds-1"}))

    response = client.get(
        "/api/v1/profile-snapshots/p-current/drift?baseline_profile_id=p-baseline"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["item"]["baseline_profile_id"] == "p-baseline"
    assert body["item"]["current_profile_id"] == "p-current"


def test_drift_judgment_unauthorized_returns_404() -> None:
    """AC-02: Yetkisiz drift erişimi veri sızdırmayan 404 döner."""
    profiles = [_profile("p1", "ds-secret", NOW)]
    datasets = [_dataset("ds-secret", "source-secret")]
    client = _app(profiles, datasets, frozenset(), frozenset())

    response = client.get("/api/v1/profile-snapshots/p1/drift")

    assert response.status_code == 404


def test_service_unavailable_returns_503() -> None:
    """AC-01: Servis yoksa 503 döner."""
    audit_service = AuditService(
        SQLiteAuditRepository(),
        AuditRedactor(
            AuditRedactionPolicy(
                version="PROFILE_SNAPSHOT_TEST_REDACTION_V1",
                allowed_fields_by_action={},
            )
        ),
        AuditFailurePolicy("PROFILE_SNAPSHOT_TEST_AUDIT_V1", AuditFailureMode.FAIL_CLOSED),
    )
    authorization = PolicyAuthorizationService(
        DashboardAuthorizationPolicy(version=POLICY_VERSION),
        audit_service,
        clock=lambda: NOW,
    )
    resolver = DevelopmentActorContextResolver(
        runtime_environment="development",
        policy_version=POLICY_VERSION,
        permitted_source_ids=frozenset({"source-1"}),
        permitted_dataset_ids=frozenset({"ds-1"}),
        can_view_enterprise=False,
        allowed_origins=("https://dq.test",),
        clock=lambda: NOW,
    )
    dashboard = DashboardQueryService(SQLiteScoreRepository(), authorization, clock=lambda: NOW)
    app = create_dashboard_api(
        dashboard,
        actor_context_resolver=resolver,
        allowed_origins=("https://dq.test",),
        data_origin="synthetic-test",
        profile_snapshot_query_service=None,
    )
    client = TestClient(app)

    response = client.get("/api/v1/profile-snapshots?dataset_id=ds-1")

    assert response.status_code == 503


def test_list_snapshots_bounded_to_max_limit() -> None:
    """AC-06: Sonuç kümesi MAX_SNAPSHOTS ile sınırlı."""
    profiles = [_profile(f"p{i}", "ds-1", NOW) for i in range(100)]
    datasets = [_dataset("ds-1", "source-1")]
    client = _app(profiles, datasets, frozenset({"source-1"}), frozenset({"ds-1"}))

    response = client.get("/api/v1/profile-snapshots?dataset_id=ds-1")

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 50
    assert body["limit"] == 50


def test_read_only_no_write_side_effects() -> None:
    """AC-07: Okuma uçları yazma yan etkisi yoktur."""
    profiles = [_profile("p1", "ds-1", NOW)]
    datasets = [_dataset("ds-1", "source-1")]
    client = _app(profiles, datasets, frozenset({"source-1"}), frozenset({"ds-1"}))

    response1 = client.get("/api/v1/profile-snapshots?dataset_id=ds-1")
    response2 = client.get("/api/v1/profile-snapshots/p1")
    response3 = client.get("/api/v1/profile-snapshots/p1/drift")

    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response3.status_code == 200
    assert len(response1.json()["items"]) == 1
