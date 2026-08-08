"""Dashboard HTTP yanıt modelleri."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict

from veri_kalitesi.dashboard import DashboardOverview


class DashboardTrendComponentsResponse(BaseModel):
    """DQ-SCR-027 trend bilesenleri yanit modeli."""

    model_config = ConfigDict(frozen=True)

    moving_average: Decimal | None = None
    consecutive_deterioration_count: int | None = None
    sudden_deterioration: bool | None = None
    time_below_threshold_periods: int | None = None
    improvement_persistence: int | None = None
    version_boundary: bool = False
    policy_version: str | None = None


class DashboardObservationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    quality_score_id: str
    scope_type: str
    scope_id: str | None
    score_value: Decimal | None
    score_status: str
    level: str | None
    calculated_at: datetime
    comparison_status: str
    comparison_reason_codes: tuple[str, ...]
    change: Decimal | None
    contribution_graph: dict[str, Any] | None
    trend: DashboardTrendComponentsResponse | None = None


class DashboardTrendPeriodResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    period_start: datetime
    period_end: datetime
    observations: tuple[DashboardObservationResponse, ...]


class DashboardMeasurementQualificationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    evaluated_scope_count: int
    reason_codes: tuple[str, ...]
    policy_version: str | None


class DashboardCriticalControlResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    reason_code: str
    passed_count: int | None
    failed_count: int | None
    not_evaluated_count: int | None


class DashboardTechnicalErrorResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    observation_count: int
    execution_count: int
    affected_source_count: int
    last_occurred_at: datetime | None


class DashboardOperationalIndicatorsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    measurement_qualification: DashboardMeasurementQualificationResponse
    critical_controls: DashboardCriticalControlResponse
    technical_errors: DashboardTechnicalErrorResponse


class AppliedDashboardFiltersResponse(BaseModel):
    """AC-07: Yanıtta yansıtılan uygulanmış filtreler."""

    model_config = ConfigDict(frozen=True)

    window_start: datetime
    window_end: datetime
    scope_type: str | None = None
    scope_id: str | None = None
    score_status: str | None = None
    level: str | None = None


class DashboardSummaryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    as_of: datetime
    has_data: bool
    periods: tuple[DashboardTrendPeriodResponse, ...]
    operational_indicators: DashboardOperationalIndicatorsResponse
    role_view: str
    applied_filters: AppliedDashboardFiltersResponse | None = None

    @classmethod
    def from_domain(
        cls,
        overview: DashboardOverview,
        *,
        correlation_id: str,
        data_origin: str,
    ) -> "DashboardSummaryResponse":
        return cls(
            data_origin=data_origin,
            correlation_id=correlation_id,
            as_of=overview.trend.as_of,
            has_data=overview.trend.has_data,
            role_view=overview.role_view,
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
                            comparison_status=item.comparison_status,
                            comparison_reason_codes=item.comparison_reason_codes,
                            change=item.change,
                            contribution_graph=(
                                dict(item.contribution_graph)
                                if item.contribution_graph is not None
                                else None
                            ),
                            trend=(
                                DashboardTrendComponentsResponse(
                                    moving_average=item.trend.moving_average,
                                    consecutive_deterioration_count=item.trend.consecutive_deterioration_count,
                                    sudden_deterioration=item.trend.sudden_deterioration,
                                    time_below_threshold_periods=item.trend.time_below_threshold_periods,
                                    improvement_persistence=item.trend.improvement_persistence,
                                    version_boundary=item.trend.version_boundary,
                                    policy_version=item.trend.policy_version,
                                )
                                if item.trend is not None
                                else None
                            ),
                        )
                        for item in period.observations
                    ),
                )
                for period in overview.trend.periods
            ),
            operational_indicators=DashboardOperationalIndicatorsResponse(
                measurement_qualification=DashboardMeasurementQualificationResponse(
                    status=(overview.operational_indicators.measurement_qualification.status.value),
                    evaluated_scope_count=(
                        overview.operational_indicators.measurement_qualification.evaluated_scope_count
                    ),
                    reason_codes=(
                        overview.operational_indicators.measurement_qualification.reason_codes
                    ),
                    policy_version=(
                        overview.operational_indicators.measurement_qualification.policy_version
                    ),
                ),
                critical_controls=DashboardCriticalControlResponse(
                    status=overview.operational_indicators.critical_controls.status.value,
                    reason_code=overview.operational_indicators.critical_controls.reason_code,
                    passed_count=overview.operational_indicators.critical_controls.passed_count,
                    failed_count=overview.operational_indicators.critical_controls.failed_count,
                    not_evaluated_count=(
                        overview.operational_indicators.critical_controls.not_evaluated_count
                    ),
                ),
                technical_errors=DashboardTechnicalErrorResponse(
                    observation_count=(
                        overview.operational_indicators.technical_errors.observation_count
                    ),
                    execution_count=(
                        overview.operational_indicators.technical_errors.execution_count
                    ),
                    affected_source_count=(
                        overview.operational_indicators.technical_errors.affected_source_count
                    ),
                    last_occurred_at=(
                        overview.operational_indicators.technical_errors.last_occurred_at
                    ),
                ),
            ),
            applied_filters=(
                AppliedDashboardFiltersResponse(
                    window_start=overview.applied_filters.window_start,
                    window_end=overview.applied_filters.window_end,
                    scope_type=overview.applied_filters.scope_type,
                    scope_id=overview.applied_filters.scope_id,
                    score_status=overview.applied_filters.score_status,
                    level=overview.applied_filters.level,
                )
                if overview.applied_filters is not None
                else None
            ),
        )
