"""Unit tests for Dashboard 6 — Issue Performance metrics."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from veri_kalitesi.dashboard.analytics_models import AnalyticsFilterParams
from veri_kalitesi.dashboard.errors import DashboardValidationError
from veri_kalitesi.dashboard.issue_performance import IssuePerformanceQueryService, _percentile
from veri_kalitesi.dashboard.postgresql_insights import ANALYTICS_ROW_LIMIT
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
        roles=frozenset({"DATA_ENGINEER"}),
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
        self.issues: list[Any] = []
        self.history: list[Any] = []
        self.relationships: list[Any] = []

    def list_issues_for_scopes(self, **_: Any) -> list[Any]:
        return self.issues

    def list_history_for_issues(self, **_: Any) -> list[Any]:
        return self.history

    def list_issue_relationships(self, **_: Any) -> list[Any]:
        return self.relationships


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
def service(reader: FakeReader) -> IssuePerformanceQueryService:
    return IssuePerformanceQueryService(
        reader=reader,
        authorization_service=FakeAuthService(_make_actor()),
    )


def test_open_issues_counted(service: IssuePerformanceQueryService, reader: FakeReader) -> None:
    now = datetime.now(timezone.utc)
    reader.issues = [
        SimpleNamespace(
            issue_id="i-1",
            scope_type="DATASET",
            scope_id="ds-1",
            status="NEW",
            priority="HIGH",
            trigger_type="QUALITY_THRESHOLD",
            occurrence_count=1,
            created_at=now,
            updated_at=now,
        ),
        SimpleNamespace(
            issue_id="i-2",
            scope_type="DATASET",
            scope_id="ds-1",
            status="RESOLVED",
            priority="MEDIUM",
            trigger_type="MANUAL",
            occurrence_count=1,
            created_at=now,
            updated_at=now,
        ),
    ]
    result = service.get_issue_performance(_make_actor(), _make_params())
    assert result.summary["open_issue_count"] == 1


def test_mtta_from_history(service: IssuePerformanceQueryService, reader: FakeReader) -> None:
    now = datetime.now(timezone.utc)
    created = now - timedelta(hours=2)
    reader.issues = [
        SimpleNamespace(
            issue_id="i-1",
            scope_type="DATASET",
            scope_id="ds-1",
            status="INVESTIGATING",
            priority="HIGH",
            trigger_type="QUALITY_THRESHOLD",
            occurrence_count=1,
            created_at=created,
            updated_at=now,
        ),
    ]
    reader.history = [
        SimpleNamespace(
            issue_id="i-1", action="ISSUE_CREATED", new_status="NEW", occurred_at=created
        ),
        SimpleNamespace(
            issue_id="i-1",
            action="ISSUE_INVESTIGATION_STARTED",
            new_status="INVESTIGATING",
            occurred_at=created + timedelta(hours=1),
        ),
    ]
    result = service.get_issue_performance(_make_actor(), _make_params())
    assert result.summary["mtta_sample_count"] == 1
    assert result.summary["mtta_p50"] is not None
    assert abs(result.summary["mtta_p50"] - 3600) < 1  # ~1 hour in seconds


def test_unresolved_not_in_mttr(service: IssuePerformanceQueryService, reader: FakeReader) -> None:
    now = datetime.now(timezone.utc)
    reader.issues = [
        SimpleNamespace(
            issue_id="i-1",
            scope_type="DATASET",
            scope_id="ds-1",
            status="NEW",
            priority="HIGH",
            trigger_type="QUALITY_THRESHOLD",
            occurrence_count=1,
            created_at=now,
            updated_at=now,
        ),
    ]
    result = service.get_issue_performance(_make_actor(), _make_params())
    assert result.summary["unresolved_count"] == 1
    assert result.summary["mttr_sample_count"] == 0
    assert result.summary["mttr_p50"] is None


def test_percentile_single_value() -> None:
    assert _percentile([100.0], 50) == 100.0
    assert _percentile([100.0], 95) == 100.0


def test_percentile_empty_returns_none() -> None:
    assert _percentile([], 50) is None
    assert _percentile([], 95) is None


def test_percentile_multiple_values() -> None:
    values = [10.0, 20.0, 30.0, 40.0, 50.0]
    p50 = _percentile(values, 50)
    assert p50 is not None
    assert abs(p50 - 30.0) < 0.01


def test_window_over_365_days_raises(service: IssuePerformanceQueryService) -> None:
    params = AnalyticsFilterParams(
        start_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end_at=datetime(2026, 7, 31, tzinfo=timezone.utc),
    )
    with pytest.raises(DashboardValidationError, match="365"):
        service.get_issue_performance(_make_actor(), params)


# ----------------------------------------------------------------------
# F-09: limitsiz analytics sorgusu tavana baglanir, kesilme raporlanir
# ----------------------------------------------------------------------


def _bulk_issues(count: int) -> list[Any]:
    now = datetime.now(timezone.utc)
    return [
        SimpleNamespace(
            issue_id=f"i-{index}",
            scope_type="DATASET",
            scope_id="ds-1",
            status="NEW",
            priority="HIGH",
            trigger_type="QUALITY_THRESHOLD",
            occurrence_count=1,
            created_at=now,
            updated_at=now,
        )
        for index in range(count)
    ]


def test_result_is_not_marked_truncated_under_the_limit(
    service: IssuePerformanceQueryService, reader: FakeReader
) -> None:
    reader.issues = _bulk_issues(10)

    result = service.get_issue_performance(_make_actor(), _make_params())

    assert result.summary["result_truncated"] is False
    assert result.summary["result_row_limit"] == ANALYTICS_ROW_LIMIT
    assert result.summary["open_issue_count"] == 10


def test_exceeding_the_row_limit_is_reported_not_silently_trimmed(
    service: IssuePerformanceQueryService, reader: FakeReader
) -> None:
    """Depo tavanin bir fazlasini dondururse metrikler kesik olarak isaretlenir."""

    reader.issues = _bulk_issues(ANALYTICS_ROW_LIMIT + 1)

    result = service.get_issue_performance(_make_actor(), _make_params())

    assert result.summary["result_truncated"] is True
    assert result.summary["open_issue_count"] == ANALYTICS_ROW_LIMIT
