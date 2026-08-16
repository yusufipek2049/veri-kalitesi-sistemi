"""Unit tests for Dashboard 7 — Scoring Policy Impact metrics."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from veri_kalitesi.dashboard.analytics_models import AnalyticsFilterParams
from veri_kalitesi.dashboard.errors import (
    DashboardAuthorizationError,
    DashboardNotFoundError,
    DashboardValidationError,
)
from veri_kalitesi.dashboard.scoring_policy_impact import (
    ScoringPolicyImpactQueryService,
    _compute_level,
)
from veri_kalitesi.identity import ActorContext, ActorContextIssuer
from veri_kalitesi.identity.models import ActorType


_ISSUER = ActorContextIssuer()
_NOW = datetime(2026, 7, 15, tzinfo=timezone.utc)


def _make_actor(enterprise: bool = True) -> ActorContext:
    return _ISSUER.issue(
        actor_id="test-user",
        actor_type=ActorType.USER,
        authentication_source="test",
        session_id="test-session",
        roles=frozenset({"DATA_GOVERNANCE_SPECIALIST"}),
        permitted_source_ids=frozenset({"src-1"}),
        permitted_dataset_ids=frozenset({"ds-1"}),
        can_view_enterprise=enterprise,
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


class FakeConfigReader:
    def __init__(self) -> None:
        self.configs: list[Any] = []

    def list_configurations(self) -> list[Any]:
        return self.configs

    def get_configuration_by_id(self, configuration_id: str) -> Any | None:
        return next((c for c in self.configs if c.configuration_id == configuration_id), None)

    def get_active_configuration(self) -> Any | None:
        return next((c for c in self.configs if c.is_active), None)


class FakeScoreReader:
    def __init__(self) -> None:
        self.scores: list[Any] = []
        self.graphs: list[Any] = []

    def list_scores_by_policy_version(self, **_: Any) -> list[Any]:
        return self.scores

    def list_contribution_graphs(self, **_: Any) -> list[Any]:
        return self.graphs


class FakeAuthService:
    def __init__(self, actor: ActorContext) -> None:
        self._actor = actor

    def authorize_dashboard(self, actor_context: Any) -> Any:
        return SimpleNamespace(
            permitted_source_ids=self._actor.permitted_source_ids,
            permitted_dataset_ids=self._actor.permitted_dataset_ids,
            can_view_enterprise=self._actor.can_view_enterprise,
        )


def _make_config(
    version: str,
    is_active: bool = False,
    *,
    dim_weights: dict[str, float] | None = None,
    crit_weights: dict[str, float] | None = None,
) -> Any:
    return SimpleNamespace(
        configuration_id=f"cfg-{version}",
        version=version,
        threshold_version="THRESHOLDS_V1",
        critical_upper_exclusive=50.0,
        risky_upper_exclusive=75.0,
        acceptable_upper_exclusive=90.0,
        dimension_weights=dim_weights or {"COMPLETENESS": 1.0, "ACCURACY": 1.0},
        criticality_weights=crit_weights or {"LOW": 1.0, "HIGH": 1.0},
        is_active=is_active,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture()
def config_reader() -> FakeConfigReader:
    return FakeConfigReader()


@pytest.fixture()
def score_reader() -> FakeScoreReader:
    return FakeScoreReader()


@pytest.fixture()
def service(
    config_reader: FakeConfigReader,
    score_reader: FakeScoreReader,
) -> ScoringPolicyImpactQueryService:
    return ScoringPolicyImpactQueryService(
        reader=config_reader,
        score_reader=score_reader,
        authorization_service=FakeAuthService(_make_actor()),
    )


def test_enterprise_required(service: ScoringPolicyImpactQueryService) -> None:
    non_enterprise_service = ScoringPolicyImpactQueryService(
        reader=FakeConfigReader(),
        score_reader=FakeScoreReader(),
        authorization_service=FakeAuthService(_make_actor(enterprise=False)),
    )
    with pytest.raises(DashboardAuthorizationError):
        non_enterprise_service.get_scoring_policy_impact(
            _make_actor(enterprise=False), _make_params()
        )


def test_no_configurations_raises(
    config_reader: FakeConfigReader,
    score_reader: FakeScoreReader,
) -> None:
    svc = ScoringPolicyImpactQueryService(
        reader=config_reader,
        score_reader=score_reader,
        authorization_service=FakeAuthService(_make_actor()),
    )
    with pytest.raises(DashboardNotFoundError):
        svc.get_scoring_policy_impact(_make_actor(), _make_params())


def test_baseline_candidate_same_produces_zero_delta(
    service: ScoringPolicyImpactQueryService,
    config_reader: FakeConfigReader,
    score_reader: FakeScoreReader,
) -> None:
    config = _make_config("V1", is_active=True)
    config_reader.configs = [config]
    result = service.get_scoring_policy_impact(
        _make_actor(),
        _make_params(),
        baseline_version="V1",
        candidate_version="V1",
    )
    assert result.summary["baseline_version"] == "V1"
    assert result.summary["candidate_version"] == "V1"


def test_compute_level() -> None:
    assert _compute_level(30.0, 50.0, 75.0, 90.0) == "CRITICAL"
    assert _compute_level(60.0, 50.0, 75.0, 90.0) == "RISKY"
    assert _compute_level(80.0, 50.0, 75.0, 90.0) == "ACCEPTABLE"
    assert _compute_level(95.0, 50.0, 75.0, 90.0) == "GOOD"


def test_window_over_365_days_raises(
    service: ScoringPolicyImpactQueryService,
    config_reader: FakeConfigReader,
) -> None:
    config_reader.configs = [_make_config("V1", is_active=True)]
    params = AnalyticsFilterParams(
        start_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end_at=datetime(2026, 7, 31, tzinfo=timezone.utc),
    )
    with pytest.raises(DashboardValidationError, match="365"):
        service.get_scoring_policy_impact(_make_actor(), params)
