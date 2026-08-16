"""Unit tests for Dashboard 4 — Rule Health metrics."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from veri_kalitesi.dashboard.analytics_models import AnalyticsFilterParams, MetricRatio
from veri_kalitesi.dashboard.errors import DashboardValidationError
from veri_kalitesi.dashboard.rule_health import RuleHealthQueryService
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
        permitted_dataset_ids=frozenset({"ds-1", "ds-2"}),
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
        self.rules: list[Any] = []
        self.versions: list[Any] = []
        self.scores: list[Any] = []

    def list_active_datasets(self, **_: Any) -> list[Any]:
        return self.datasets

    def list_active_fields(self, **_: Any) -> list[Any]:
        return self.fields

    def list_active_rules(self, **_: Any) -> list[Any]:
        return self.rules

    def list_latest_versions(self, **_: Any) -> list[Any]:
        return self.versions

    def list_scores_for_rules(self, **_: Any) -> list[Any]:
        return self.scores


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
def actor() -> ActorContext:
    return _make_actor()


@pytest.fixture()
def reader() -> FakeReader:
    return FakeReader()


@pytest.fixture()
def service(reader: FakeReader, actor: ActorContext) -> RuleHealthQueryService:
    return RuleHealthQueryService(reader=reader, authorization_service=FakeAuthService(actor))


def test_empty_datasets_returns_zero_coverage(service: RuleHealthQueryService) -> None:
    result = service.get_rule_health(_make_actor(), _make_params())
    summary = result.summary
    assert summary["dataset_coverage"]["denominator"] == 0
    assert summary["dataset_coverage"]["ratio"] is None
    assert summary["dataset_coverage"]["reason_code"] == "NO_ELIGIBLE_ITEMS"


def test_dataset_coverage_ratio(service: RuleHealthQueryService, reader: FakeReader) -> None:
    reader.datasets = [
        SimpleNamespace(
            dataset_id="ds-1",
            data_source_id="src-1",
            name="D1",
            namespace="ns",
            criticality="MEDIUM",
            owner_user_id="u1",
            status="ACTIVE",
            updated_at=datetime.now(timezone.utc),
        ),
        SimpleNamespace(
            dataset_id="ds-2",
            data_source_id="src-1",
            name="D2",
            namespace="ns",
            criticality="HIGH",
            owner_user_id="u1",
            status="ACTIVE",
            updated_at=datetime.now(timezone.utc),
        ),
    ]
    reader.rules = [
        SimpleNamespace(
            quality_rule_id="r-1",
            code="R1",
            name="Rule 1",
            dataset_id="ds-1",
            field_ids=("f1",),
            primary_dimension="COMPLETENESS",
            status="ACTIVE",
        ),
    ]
    reader.versions = [
        SimpleNamespace(
            rule_version_id="rv-1",
            quality_rule_id="r-1",
            version_no=1,
            rule_type="THRESHOLD",
            threshold=0.9,
            criticality="MEDIUM",
            created_at=datetime.now(timezone.utc),
        ),
    ]
    result = service.get_rule_health(_make_actor(), _make_params())
    coverage = result.summary["dataset_coverage"]
    assert coverage["numerator"] == 1
    assert coverage["denominator"] == 2


def test_never_executed_rules_counted(service: RuleHealthQueryService, reader: FakeReader) -> None:
    reader.datasets = [
        SimpleNamespace(
            dataset_id="ds-1",
            data_source_id="src-1",
            name="D1",
            namespace="ns",
            criticality="MEDIUM",
            owner_user_id="u1",
            status="ACTIVE",
            updated_at=datetime.now(timezone.utc),
        ),
    ]
    reader.rules = [
        SimpleNamespace(
            quality_rule_id="r-1",
            code="R1",
            name="Rule 1",
            dataset_id="ds-1",
            field_ids=("f1",),
            primary_dimension="COMPLETENESS",
            status="ACTIVE",
        ),
    ]
    reader.versions = [
        SimpleNamespace(
            rule_version_id="rv-1",
            quality_rule_id="r-1",
            version_no=1,
            rule_type="THRESHOLD",
            threshold=0.9,
            criticality="MEDIUM",
            created_at=datetime.now(timezone.utc),
        ),
    ]
    # No scores at all
    result = service.get_rule_health(_make_actor(), _make_params())
    assert result.summary["never_executed_count"] == 1


def test_window_over_365_days_raises_validation(service: RuleHealthQueryService) -> None:
    params = AnalyticsFilterParams(
        start_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end_at=datetime(2026, 7, 31, tzinfo=timezone.utc),
    )
    with pytest.raises(DashboardValidationError, match="365"):
        service.get_rule_health(_make_actor(), params)


def test_metric_ratio_zero_denominator() -> None:
    ratio = MetricRatio(numerator=5, denominator=0)
    assert ratio.ratio is None


def test_metric_ratio_normal() -> None:
    ratio = MetricRatio(numerator=3, denominator=10)
    assert ratio.ratio is not None
    assert abs(float(ratio.ratio) - 0.3) < 0.001
