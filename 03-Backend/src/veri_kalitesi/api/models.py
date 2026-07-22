"""Dashboard HTTP yanıt modelleri."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from veri_kalitesi.dashboard import DashboardScoreTrend


class DashboardObservationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    quality_score_id: str
    scope_type: str
    scope_id: str | None
    score_value: Decimal | None
    score_status: str
    level: str | None
    calculated_at: datetime


class DashboardTrendPeriodResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    period_start: datetime
    period_end: datetime
    observations: tuple[DashboardObservationResponse, ...]


class DashboardSummaryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    as_of: datetime
    has_data: bool
    periods: tuple[DashboardTrendPeriodResponse, ...]

    @classmethod
    def from_domain(
        cls,
        trend: DashboardScoreTrend,
        *,
        correlation_id: str,
        data_origin: str,
    ) -> "DashboardSummaryResponse":
        return cls(
            data_origin=data_origin,
            correlation_id=correlation_id,
            as_of=trend.as_of,
            has_data=trend.has_data,
            periods=tuple(
                DashboardTrendPeriodResponse(
                    period_start=period.period_start,
                    period_end=period.period_end,
                    observations=tuple(
                        DashboardObservationResponse(
                            quality_score_id=item.quality_score_id,
                            scope_type=item.scope_type.value,
                            scope_id=item.scope_id,
                            score_value=item.score_value,
                            score_status=item.score_status.value,
                            level=item.level.value if item.level is not None else None,
                            calculated_at=item.calculated_at,
                        )
                        for item in period.observations
                    ),
                )
                for period in trend.periods
            ),
        )
