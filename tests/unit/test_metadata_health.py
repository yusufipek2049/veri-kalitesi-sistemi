"""Unit tests for Dashboard 5 — Metadata Health metrics."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from veri_kalitesi.dashboard.analytics_models import AnalyticsFilterParams
from veri_kalitesi.dashboard.errors import DashboardValidationError
from veri_kalitesi.dashboard.metadata_health import MetadataHealthQueryService
from veri_kalitesi.identity import ActorContext, ActorContextIssuer
from veri_kalitesi.identity.models import ActorType


_ISSUER = ActorContextIssuer()
_NOW = datetime(2026, 7, 15, tzinfo=timezone.utc)


def _make_actor() -> ActorContext:
    return _ISSUER.issue(
        actor_id="test-user",
        actor_type=ActorType.USER,
        authentication_source="test",
        session_id="test-session",
        roles=frozenset({"DATA_STEWARD"}),
        permitted_source_ids=frozenset({"src-1"}),
        permitted_dataset_ids=frozenset({"ds-1"}),
        can_view_enterprise=False,
        privileged=False,
        issued_at=_NOW - timedelta(minutes=5),
        expires_at=_NOW + timedelta(hours=1),
        policy_version="TEST_POLICY_V1",
        correlation_id="test-corr",
    )


def _make_params(**overrides: Any) -> AnalyticsFilterParams:
    defaults = {
        "start_at": datetime(2026, 7, 1, tzinfo=timezone.utc),
        "end_at": datetime(2026, 7, 31, tzinfo=timezone.utc),
    }
    defaults.update(overrides)
    return AnalyticsFilterParams(**defaults)


class FakeReader:
    def __init__(self) -> None:
        self.datasets: list[Any] = []
        self.fields: list[Any] = []

    def list_active_datasets(self, **_: Any) -> list[Any]:
        return self.datasets

    def list_active_fields(self, **_: Any) -> list[Any]:
        return self.fields


class FakeAuthService:
    def __init__(self, actor: ActorContext) -> None:
        self._actor = actor

    def authorize_dashboard(self, actor_context: Any) -> Any:
        return SimpleNamespace(
            permitted_source_ids=self._actor.permitted_source_ids,
            permitted_dataset_ids=self._actor.permitted_dataset_ids,
            can_view_enterprise=self._actor.can_view_enterprise,
        )


@pytest.fixture()
def reader() -> FakeReader:
    return FakeReader()


@pytest.fixture()
def service(reader: FakeReader) -> MetadataHealthQueryService:
    return MetadataHealthQueryService(
        reader=reader,
        authorization_service=FakeAuthService(_make_actor()),
        stale_after_days=30,
        classification_policy_version="CLASSIFICATION_POLICY_V1",
    )


def test_ownership_completeness(service: MetadataHealthQueryService, reader: FakeReader) -> None:
    reader.datasets = [
        SimpleNamespace(dataset_id="ds-1", data_source_id="src-1", name="D1",
                       namespace="ns", criticality="MEDIUM", owner_user_id="user-1",
                       status="ACTIVE", updated_at=datetime.now(timezone.utc)),
        SimpleNamespace(dataset_id="ds-2", data_source_id="src-1", name="D2",
                       namespace="ns", criticality="HIGH", owner_user_id=None,
                       status="ACTIVE", updated_at=datetime.now(timezone.utc)),
    ]
    result = service.get_metadata_health(_make_actor(), _make_params())
    ownership = result.summary["ownership_completeness"]
    assert ownership["numerator"] == 1
    assert ownership["denominator"] == 2


def test_unclassified_fields_counted(service: MetadataHealthQueryService, reader: FakeReader) -> None:
    reader.datasets = [
        SimpleNamespace(dataset_id="ds-1", data_source_id="src-1", name="D1",
                       namespace="ns", criticality="HIGH", owner_user_id="user-1",
                       status="ACTIVE", updated_at=datetime.now(timezone.utc)),
    ]
    reader.fields = [
        SimpleNamespace(data_field_id="f1", dataset_id="ds-1", name="col1",
                       is_sensitive=False, classification="UNCLASSIFIED",
                       classification_policy_version="CLASSIFICATION_POLICY_V1",
                       status="ACTIVE", updated_at=datetime.now(timezone.utc)),
        SimpleNamespace(data_field_id="f2", dataset_id="ds-1", name="col2",
                       is_sensitive=False, classification="PUBLIC",
                       classification_policy_version="CLASSIFICATION_POLICY_V1",
                       status="ACTIVE", updated_at=datetime.now(timezone.utc)),
    ]
    result = service.get_metadata_health(_make_actor(), _make_params())
    classification = result.summary["classification_completeness"]
    assert classification["numerator"] == 1  # only PUBLIC is classified
    assert classification["denominator"] == 2


def test_classification_flag_mismatch_detected(service: MetadataHealthQueryService, reader: FakeReader) -> None:
    reader.datasets = [
        SimpleNamespace(dataset_id="ds-1", data_source_id="src-1", name="D1",
                       namespace="ns", criticality="HIGH", owner_user_id="user-1",
                       status="ACTIVE", updated_at=datetime.now(timezone.utc)),
    ]
    reader.fields = [
        SimpleNamespace(data_field_id="f1", dataset_id="ds-1", name="col1",
                       is_sensitive=True, classification="PUBLIC",
                       classification_policy_version="CLASSIFICATION_POLICY_V1",
                       status="ACTIVE", updated_at=datetime.now(timezone.utc)),
    ]
    result = service.get_metadata_health(_make_actor(), _make_params())
    # Should find CLASSIFICATION_FLAG_MISMATCH
    mismatch_items = [i for i in result.items if i["reason_code"] == "CLASSIFICATION_FLAG_MISMATCH"]
    assert len(mismatch_items) == 1


def test_stale_threshold_from_config(service: MetadataHealthQueryService, reader: FakeReader) -> None:
    # end_at is July 31, stale_cutoff = July 31 - 30 = July 1
    # dataset updated_at must be before July 1 to be stale
    reader.datasets = [
        SimpleNamespace(dataset_id="ds-1", data_source_id="src-1", name="D1",
                       namespace="ns", criticality="MEDIUM", owner_user_id="user-1",
                       status="ACTIVE",
                       updated_at=datetime(2026, 6, 15, tzinfo=timezone.utc)),
    ]
    result = service.get_metadata_health(_make_actor(), _make_params())
    assert result.summary["stale_dataset_count"] == 1
    assert result.summary["stale_after_days"] == 30


def test_window_over_365_days_raises(service: MetadataHealthQueryService) -> None:
    params = AnalyticsFilterParams(
        start_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end_at=datetime(2026, 7, 31, tzinfo=timezone.utc),
    )
    with pytest.raises(DashboardValidationError, match="365"):
        service.get_metadata_health(_make_actor(), params)
