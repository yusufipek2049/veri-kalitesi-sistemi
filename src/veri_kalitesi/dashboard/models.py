"""Dashboard salt okunur gorunum modelleri."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Mapping

from veri_kalitesi.scoring.models import ScoreLevel, ScoreScopeType, ScoreStatus


class DashboardFilterScopeType(str, Enum):
    """FR-057 kapsam filtresi değeri."""

    SOURCE = "SOURCE"
    ENTERPRISE = "ENTERPRISE"


class DashboardFilterScoreStatus(str, Enum):
    """FR-057 skor durumu filtresi değeri."""

    CALCULATED = "CALCULATED"
    NOT_CALCULATED = "NOT_CALCULATED"
    NO_DATA = "NO_DATA"
    PARTIAL = "PARTIAL"
    NOT_CALCULATED_TECHNICAL_ERROR = "NOT_CALCULATED_TECHNICAL_ERROR"
    CONFIG_ERROR = "CONFIG_ERROR"


class DashboardFilterLevel(str, Enum):
    """FR-057 kalite seviyesi filtresi değeri."""

    GOOD = "GOOD"
    ACCEPTABLE = "ACCEPTABLE"
    RISKY = "RISKY"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class DashboardFilterParams:
    """FR-057 filtre parametreleri; None olan alan uygulanmaz."""

    start_date: datetime | None = None
    end_date: datetime | None = None
    scope_type: DashboardFilterScopeType | None = None
    scope_id: str | None = None
    score_status: DashboardFilterScoreStatus | None = None
    level: DashboardFilterLevel | None = None

    @property
    def has_any_filter(self) -> bool:
        return any(
            (
                self.start_date is not None,
                self.end_date is not None,
                self.scope_type is not None,
                self.scope_id is not None,
                self.score_status is not None,
                self.level is not None,
            )
        )


@dataclass(frozen=True)
class AppliedDashboardFilters:
    """Yanıtta yansıtılan uygulanmış filtreler (AC-07)."""

    window_start: datetime
    window_end: datetime
    scope_type: str | None = None
    scope_id: str | None = None
    score_status: str | None = None
    level: str | None = None


@dataclass(frozen=True)
class DashboardAccessScope:
    """Internal read scope; external callers must use ActorContext."""

    allowed_source_ids: frozenset[str] = field(default_factory=frozenset)
    allowed_dataset_ids: frozenset[str] = field(default_factory=frozenset)
    can_view_enterprise: bool = False


@dataclass(frozen=True)
class DashboardTrendComponents:
    """DQ-SCR-027 trend bilesenleri; None alanlar Unknown/yetersiz gecmis."""

    moving_average: Decimal | None = None
    consecutive_deterioration_count: int | None = None
    sudden_deterioration: bool | None = None
    time_below_threshold_periods: int | None = None
    improvement_persistence: int | None = None
    version_boundary: bool = False
    policy_version: str | None = None


@dataclass(frozen=True)
class DashboardScoreNode:
    quality_score_id: str
    scope_type: ScoreScopeType
    scope_id: str | None
    score_value: Decimal | None
    score_status: ScoreStatus
    level: ScoreLevel | None
    calculated_at: datetime
    comparison_status: str = "UNKNOWN"
    comparison_reason_codes: tuple[str, ...] = ()
    change: Decimal | None = None
    contribution_graph: Mapping[str, Any] | None = None
    trend: DashboardTrendComponents | None = None


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
    role_view: str = "EXECUTIVE"
    applied_filters: AppliedDashboardFilters | None = None
