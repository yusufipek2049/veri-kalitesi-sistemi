"""Dashboard overview HTTP route kayıtları."""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Annotated, Any, Protocol

from fastapi import FastAPI, Query as FastApiQuery, Request

from veri_kalitesi.dashboard import (
    DashboardFilterLevel,
    DashboardFilterParams,
    DashboardFilterScoreStatus,
    DashboardFilterScopeType,
    DashboardOverview,
    DashboardQueryError,
    DashboardQueryService,
    DashboardScoreNode,
    DashboardScoreTrend,
)
from veri_kalitesi.identity import ActorContext


class _Resolver(Protocol):
    def resolve(self, request: Request) -> ActorContext | None: ...


def _decimal_to_float(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _date_boundary(value: date | datetime | None, *, end: bool) -> datetime | None:
    """Date-only UI filters cover the complete selected day in UTC."""
    if value is None or isinstance(value, datetime):
        return value
    return datetime.combine(value, time.max if end else time.min, tzinfo=timezone.utc)


def _serialize_node(node: DashboardScoreNode) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "quality_score_id": node.quality_score_id,
        "scope_type": node.scope_type.value,
        "scope_id": node.scope_id,
        "score_value": _decimal_to_float(node.score_value),
        "score_status": node.score_status.value,
        "level": node.level.value if node.level else None,
        "calculated_at": node.calculated_at.isoformat(),
        "comparison_status": node.comparison_status,
        "comparison_reason_codes": list(node.comparison_reason_codes),
        "change": _decimal_to_float(node.change),
    }
    if node.contribution_graph is not None:
        payload["contribution_graph"] = dict(node.contribution_graph)
    if node.trend is not None:
        payload["trend"] = {
            "moving_average": _decimal_to_float(node.trend.moving_average),
            "consecutive_deterioration_count": node.trend.consecutive_deterioration_count,
            "sudden_deterioration": node.trend.sudden_deterioration,
            "time_below_threshold_periods": node.trend.time_below_threshold_periods,
            "improvement_persistence": node.trend.improvement_persistence,
        }
        payload["version_boundary"] = node.trend.version_boundary
        payload["policy_version"] = node.trend.policy_version
    return payload


def _serialize_trend(
    trend: DashboardScoreTrend,
    *,
    threshold_value: Decimal | None,
) -> dict[str, Any]:
    periods: list[dict[str, Any]] = []
    for period in trend.periods:
        periods.append(
            {
                "period_start": period.period_start.isoformat(),
                "period_end": period.period_end.isoformat(),
                "observations": [_serialize_node(obs) for obs in period.observations],
            }
        )
    return {
        "as_of": trend.as_of.isoformat(),
        "periods": periods,
        "has_data": trend.has_data,
        "threshold_value": _decimal_to_float(threshold_value),
    }


def _serialize_overview(
    overview: DashboardOverview,
    *,
    threshold_value: Decimal | None,
) -> dict[str, Any]:
    indicators = overview.operational_indicators
    payload: dict[str, Any] = {
        "trend": _serialize_trend(overview.trend, threshold_value=threshold_value),
        "operational_indicators": {
            "measurement_qualification": {
                "status": indicators.measurement_qualification.status.value,
                "evaluated_scope_count": indicators.measurement_qualification.evaluated_scope_count,
                "reason_codes": list(indicators.measurement_qualification.reason_codes),
            },
            "critical_controls": {
                "status": indicators.critical_controls.status.value,
                "reason_code": indicators.critical_controls.reason_code,
            },
            "technical_errors": {
                "observation_count": indicators.technical_errors.observation_count,
                "execution_count": indicators.technical_errors.execution_count,
                "affected_source_count": indicators.technical_errors.affected_source_count,
                "last_occurred_at": (
                    indicators.technical_errors.last_occurred_at.isoformat()
                    if indicators.technical_errors.last_occurred_at
                    else None
                ),
            },
        },
        "role_view": overview.role_view,
    }
    if overview.applied_filters is not None:
        filters = overview.applied_filters
        payload["applied_filters"] = {
            "window_start": filters.window_start.isoformat(),
            "window_end": filters.window_end.isoformat(),
            "scope_type": filters.scope_type,
            "scope_id": filters.scope_id,
            "score_status": filters.score_status,
            "level": filters.level,
        }
    else:
        payload["applied_filters"] = None
    return payload


def register_dashboard_routes(
    app: FastAPI,
    *,
    dashboard_query_service: DashboardQueryService | None,
    resolver: _Resolver,
    data_origin: str,
) -> None:
    """Dashboard overview route'larını FastAPI uygulamasına kaydeder."""

    @app.get("/api/v1/dashboard/overview", tags=["dashboard"])
    async def get_dashboard_overview(
        request: Request,
        start_date: Annotated[date | datetime | None, FastApiQuery()] = None,
        end_date: Annotated[date | datetime | None, FastApiQuery()] = None,
        scope_type: Annotated[DashboardFilterScopeType | None, FastApiQuery()] = None,
        scope_id: Annotated[str | None, FastApiQuery(min_length=1, max_length=200)] = None,
        score_status: Annotated[DashboardFilterScoreStatus | None, FastApiQuery()] = None,
        level: Annotated[DashboardFilterLevel | None, FastApiQuery()] = None,
    ) -> dict[str, Any]:
        if dashboard_query_service is None:
            raise DashboardQueryError(
                "Dashboard query service is not available.",
                request.state.correlation_id,
            )
        actor_context = resolver.resolve(request)
        filters = DashboardFilterParams(
            start_date=_date_boundary(start_date, end=False),
            end_date=_date_boundary(end_date, end=True),
            scope_type=scope_type,
            scope_id=scope_id,
            score_status=score_status,
            level=level,
        )
        overview = dashboard_query_service.get_overview(
            actor_context,
            filters=filters if filters.has_any_filter else None,
        )
        trend_policy = dashboard_query_service.trend_policy
        return {
            "api_version": "v1",
            "data_origin": data_origin,
            "correlation_id": request.state.correlation_id,
            **_serialize_overview(
                overview,
                threshold_value=(trend_policy.below_threshold_value if trend_policy else None),
            ),
        }
