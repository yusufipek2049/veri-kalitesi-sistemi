"""Jobs (zamanlayıcı) HTTP rota testleri.

Nitelik bazlı öneri uç noktasını, bant içi/dışı oluşturma akışını,
yönetişim 409 problem kodunu ve aktif/pasif yönetimini doğrular.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from veri_kalitesi.api import DevelopmentActorContextResolver, create_dashboard_api
from veri_kalitesi.api.bff import CSRF_HEADER_NAME
from veri_kalitesi.api.service_groups import (
    ActorResolverIdentity,
    ApiOptions,
    CatalogServices,
    ScheduleServices,
)
from veri_kalitesi.audit.outbox import SQLiteTransactionalAudit
from veri_kalitesi.audit.policies import build_default_redaction_policy
from veri_kalitesi.audit.redaction import AuditRedactor
from veri_kalitesi.audit.repository import SQLiteAuditRepository
from veri_kalitesi.data_sources.models import Dataset, TimelinessNature
from veri_kalitesi.executions.errors import ExecutionValidationError
from veri_kalitesi.executions.scheduling import (
    SQLiteScheduleRepository,
    SchedulingService,
)

NOW = datetime(2026, 8, 17, 12, 0, tzinfo=timezone.utc)
POLICY_VERSION = "SCHEDULES_API_TEST_V1"
NEAR_DATASET_ID = "dataset-near"
BATCH_DATASET_ID = "dataset-batch"
PLAIN_DATASET_ID = "dataset-plain"


class FakeDatasetReader:
    def __init__(self) -> None:
        self.datasets = {
            NEAR_DATASET_ID: _dataset(NEAR_DATASET_ID, TimelinessNature.NEAR_TIME),
            BATCH_DATASET_ID: _dataset(BATCH_DATASET_ID, TimelinessNature.BATCH_TIME),
            PLAIN_DATASET_ID: _dataset(PLAIN_DATASET_ID, None),
        }

    def get_dataset(self, dataset_id: str) -> Dataset:
        if dataset_id not in self.datasets:
            raise KeyError(dataset_id)
        return self.datasets[dataset_id]


class FakeCatalogQuery:
    def __init__(self) -> None:
        self.reader = FakeDatasetReader()


class FakeExecutionBridge:
    """API katmanı köprüsü: yalnız doğrulama yapar, tetikleme worker'dadır."""

    def __init__(self, *, failing: bool = False) -> None:
        self.failing = failing

    def validate_rule_versions(self, rule_version_ids: tuple[str, ...]) -> tuple[str, ...]:
        if self.failing:
            raise ExecutionValidationError("Rule version is not active.")
        return tuple(rule_version_ids)

    def start_scheduled(self, **kwargs: object):
        raise ExecutionValidationError("Scheduled triggering runs in the worker process.")


def _dataset(dataset_id: str, nature: TimelinessNature | None) -> Dataset:
    return Dataset(
        data_source_id="source-1",
        namespace="core",
        name=f"Tablo {dataset_id}",
        owner_user_id="owner-1",
        timeliness_nature=nature,
        dataset_id=dataset_id,
        version=1,
    )


def _schedule_audit(repository: SQLiteScheduleRepository) -> SQLiteTransactionalAudit:
    return SQLiteTransactionalAudit(
        repository.connection,
        AuditRedactor(build_default_redaction_policy()),
        SQLiteAuditRepository(),
        policy_version="AUDIT_OUTBOX_TEST_V1",
    )


def _app(*, failing_bridge: bool = False):
    resolver = DevelopmentActorContextResolver(
        runtime_environment="development",
        policy_version=POLICY_VERSION,
        permitted_source_ids=frozenset({"source-1"}),
        can_view_enterprise=False,
        allowed_origins=frozenset({"https://dq.test"}),
        clock=lambda: NOW,
    )
    repository = SQLiteScheduleRepository()
    scheduling_service = SchedulingService(
        repository,
        FakeExecutionBridge(failing=failing_bridge),
        transactional_audit=_schedule_audit(repository),
        clock=lambda: NOW,
    )
    app = create_dashboard_api(
        identity=ActorResolverIdentity(resolver),
        options=ApiOptions(data_origin="synthetic-test"),
        catalog=CatalogServices(
            metadata_command=None,
            query=FakeCatalogQuery(),  # type: ignore[arg-type]
            score_query=None,
            dashboard_query=None,
        ),
        schedules=ScheduleServices(scheduling=scheduling_service),
    )
    return TestClient(app), repository


def _headers() -> dict[str, str]:
    return {
        CSRF_HEADER_NAME: "development-request-proof-v1",
        "Origin": "https://dq.test",
        "Referer": "https://dq.test/jobs",
        "Sec-Fetch-Site": "same-origin",
    }


def _create_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": "Yakın zamanlı job",
        "dataset_id": NEAR_DATASET_ID,
        "schedule_type": "INTERVAL",
        "timezone_name": "Europe/Istanbul",
        "rule_version_ids": ["rv-1"],
        "interval_minutes": 10,
    }
    payload.update(overrides)
    return payload


def test_in_band_interval_job_is_created_with_preview() -> None:
    client, repository = _app()

    response = client.post("/api/v1/schedules", json=_create_payload(), headers=_headers())

    assert response.status_code == 201, response.text
    body = response.json()
    assert response.headers["cache-control"] == "no-store"
    assert body["schedule_type"] == "INTERVAL"
    assert body["interval_minutes"] == 10
    assert body["is_active"] is True
    assert body["next_run_at"] is not None
    assert len(body["preview_runs"]) == 5
    assert body["data_origin"] == "synthetic-test"
    assert len(repository.list_all()) == 1


def test_out_of_band_interval_returns_governance_problem_code() -> None:
    client, repository = _app()

    response = client.post(
        "/api/v1/schedules",
        json=_create_payload(interval_minutes=30),
        headers=_headers(),
    )

    assert response.status_code == 409, response.text
    body = response.json()
    assert body["code"] == "EXECUTION_GOVERNANCE_APPROVAL_REQUIRED"
    assert body["governance_request_type"] == "SCHEDULE_INTERVAL_EXCEPTION"
    assert repository.list_all() == []


def test_dataset_without_nature_blocks_job_creation() -> None:
    client, repository = _app()

    response = client.post(
        "/api/v1/schedules",
        json=_create_payload(dataset_id=PLAIN_DATASET_ID),
        headers=_headers(),
    )

    assert response.status_code == 422, response.text
    assert "timeliness nature" in response.json()["detail"]
    assert repository.list_all() == []


def test_unknown_dataset_returns_not_found() -> None:
    client, _repository = _app()

    response = client.post(
        "/api/v1/schedules",
        json=_create_payload(dataset_id="dataset-missing"),
        headers=_headers(),
    )

    assert response.status_code == 404


def test_batch_time_daily_job_is_in_band_but_interval_is_not() -> None:
    client, repository = _app()

    daily = client.post(
        "/api/v1/schedules",
        json=_create_payload(
            name="Günlük batch job",
            dataset_id=BATCH_DATASET_ID,
            schedule_type="DAILY",
            local_time="06:00",
            interval_minutes=None,
        ),
        headers=_headers(),
    )
    assert daily.status_code == 201, daily.text

    interval = client.post(
        "/api/v1/schedules",
        json=_create_payload(
            dataset_id=BATCH_DATASET_ID, schedule_type="INTERVAL", interval_minutes=5
        ),
        headers=_headers(),
    )
    assert interval.status_code == 409
    assert interval.json()["governance_request_type"] == "SCHEDULE_INTERVAL_EXCEPTION"
    assert len(repository.list_all()) == 1


def test_invalid_rule_version_maps_to_validation_error() -> None:
    client, repository = _app(failing_bridge=True)

    response = client.post("/api/v1/schedules", json=_create_payload(), headers=_headers())

    assert response.status_code == 422, response.text
    assert "not active" in response.json()["detail"]
    assert repository.list_all() == []


def test_schedule_proposals_follow_timeliness_nature() -> None:
    client, _repository = _app()

    near = client.get(f"/api/v1/datasets/{NEAR_DATASET_ID}/schedule-proposals", headers=_headers())
    assert near.status_code == 200
    body = near.json()
    assert body["timeliness_nature"] == "NEAR_TIME"
    assert body["band"] == "INTERVAL 5-15 dakika"
    assert [p["interval_minutes"] for p in body["proposals"]] == [5, 10, 15]
    assert all(p["schedule_type"] == "INTERVAL" for p in body["proposals"])

    batch = client.get(
        f"/api/v1/datasets/{BATCH_DATASET_ID}/schedule-proposals", headers=_headers()
    )
    assert batch.status_code == 200
    assert [p["schedule_type"] for p in batch.json()["proposals"]] == [
        "DAILY",
        "WEEKLY",
        "MONTHLY",
    ]


def test_schedule_proposals_without_nature_returns_empty_list() -> None:
    client, _repository = _app()

    response = client.get(
        f"/api/v1/datasets/{PLAIN_DATASET_ID}/schedule-proposals", headers=_headers()
    )

    assert response.status_code == 200
    body = response.json()
    assert body["timeliness_nature"] is None
    assert body["band"] is None
    assert body["proposals"] == []


def test_schedule_proposals_for_unknown_dataset_returns_not_found() -> None:
    client, _repository = _app()

    response = client.get("/api/v1/datasets/dataset-missing/schedule-proposals", headers=_headers())

    assert response.status_code == 404


def test_activate_and_deactivate_toggle_schedule_state() -> None:
    client, repository = _app()
    created = client.post("/api/v1/schedules", json=_create_payload(), headers=_headers())
    schedule_id = created.json()["schedule_id"]

    deactivated = client.post(f"/api/v1/schedules/{schedule_id}/deactivate", headers=_headers())
    assert deactivated.status_code == 200, deactivated.text
    assert deactivated.json()["is_active"] is False
    assert deactivated.json()["next_run_at"] is None

    activated = client.post(f"/api/v1/schedules/{schedule_id}/activate", headers=_headers())
    assert activated.status_code == 200
    assert activated.json()["is_active"] is True
    assert activated.json()["next_run_at"] is not None
    assert repository.get(schedule_id).is_active is True


def test_activating_unknown_schedule_returns_not_found() -> None:
    client, _repository = _app()

    response = client.post("/api/v1/schedules/missing/activate", headers=_headers())

    assert response.status_code == 404


def test_schedule_list_returns_created_jobs() -> None:
    client, _repository = _app()
    client.post("/api/v1/schedules", json=_create_payload(), headers=_headers())

    response = client.get("/api/v1/schedules", headers=_headers())

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["name"] == "Yakın zamanlı job"
    assert body["items"][0]["rule_version_ids"] == ["rv-1"]
