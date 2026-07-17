"""Dashboard salt okunur gorunum modelleri."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

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
