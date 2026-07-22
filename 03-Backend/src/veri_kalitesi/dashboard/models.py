"""Dashboard salt okunur gorunum modelleri."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum

from veri_kalitesi.scoring.models import ScoreLevel, ScoreScopeType, ScoreStatus


@dataclass(frozen=True)
class DashboardAccessScope:
    """Internal read scope; external callers must use ActorContext."""

    allowed_source_ids: frozenset[str] = field(default_factory=frozenset)
    can_view_enterprise: bool = False


@dataclass(frozen=True)
class DashboardScoreNode:
    quality_score_id: str
    scope_type: ScoreScopeType
    scope_id: str | None
    score_value: Decimal | None
    score_status: ScoreStatus
    level: ScoreLevel | None
    calculated_at: datetime


@dataclass(frozen=True)
class DashboardScoreTree:
    execution_id: str
    enterprise: DashboardScoreNode | None
    sources: tuple[DashboardScoreNode, ...]

    @property
    def has_data(self) -> bool:
        return self.enterprise is not None or bool(self.sources)


@dataclass(frozen=True)
class DashboardTrendPeriod:
    period_start: datetime
    period_end: datetime
    observations: tuple[DashboardScoreNode, ...]

    @property
    def has_data(self) -> bool:
        return bool(self.observations)


@dataclass(frozen=True)
class DashboardScoreTrend:
    as_of: datetime
    periods: tuple[DashboardTrendPeriod, ...]

    @property
    def has_data(self) -> bool:
        return any(period.has_data for period in self.periods)


class MeasurementQualificationIndicatorStatus(str, Enum):
    NO_DATA = "NO_DATA"
    VALIDATION_REQUIRED = "VALIDATION_REQUIRED"
    TECHNICAL_FAILURE = "TECHNICAL_FAILURE"


class CriticalControlIndicatorStatus(str, Enum):
    NOT_AVAILABLE = "NOT_AVAILABLE"


@dataclass(frozen=True)
class DashboardMeasurementQualificationIndicator:
    status: MeasurementQualificationIndicatorStatus
    evaluated_scope_count: int
    reason_codes: tuple[str, ...]
    policy_version: str | None = None


@dataclass(frozen=True)
class DashboardCriticalControlIndicator:
    status: CriticalControlIndicatorStatus
    reason_code: str
    passed_count: int | None = None
    failed_count: int | None = None
    not_evaluated_count: int | None = None


@dataclass(frozen=True)
class DashboardTechnicalErrorIndicator:
    observation_count: int
    execution_count: int
    affected_source_count: int
    last_occurred_at: datetime | None


@dataclass(frozen=True)
class DashboardOperationalIndicators:
    measurement_qualification: DashboardMeasurementQualificationIndicator
    critical_controls: DashboardCriticalControlIndicator
    technical_errors: DashboardTechnicalErrorIndicator


@dataclass(frozen=True)
class DashboardOverview:
    trend: DashboardScoreTrend
    operational_indicators: DashboardOperationalIndicators
