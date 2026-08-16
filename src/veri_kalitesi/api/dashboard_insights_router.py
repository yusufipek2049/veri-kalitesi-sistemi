"""Dashboard insights HTTP route kayitlari — 4 analytics endpoint."""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Annotated, Any, Protocol

from fastapi import FastAPI, Query as FastApiQuery, Request, Response

from veri_kalitesi.dashboard.analytics_models import AnalyticsEnvelope, AnalyticsFilterParams
from veri_kalitesi.dashboard.errors import (
    DashboardQueryError,
)
from veri_kalitesi.identity import ActorContext


class _Resolver(Protocol):
    def resolve(self, request: Request) -> ActorContext | None: ...


def _date_boundary(value: date | datetime | None, *, end: bool) -> datetime | None:
    """Date-only UI filters cover the complete selected day in UTC."""
    if value is None or isinstance(value, datetime):
        return value
    return datetime.combine(value, time.max if end else time.min, tzinfo=timezone.utc)


def _default_window(
    start_date: date | datetime | None,
    end_date: date | datetime | None,
) -> AnalyticsFilterParams:
    now = datetime.now(timezone.utc)
    start = _date_boundary(start_date, end=False)
    end = _date_boundary(end_date, end=True)
    if start is None:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0) - __import__(
            "datetime"
        ).timedelta(days=29)
    if end is None:
        end = now
    return AnalyticsFilterParams(start_at=start, end_at=end)


def register_dashboard_insights_routes(
    app: FastAPI,
    *,
    rule_health_service: Any | None,
    metadata_health_service: Any | None,
    issue_performance_service: Any | None,
    scoring_policy_impact_service: Any | None,
    resolver: _Resolver,
    data_origin: str,
) -> None:
    """4 analytics endpoint'ini FastAPI uygulamasina kaydeder."""

    @app.get("/api/v1/dashboard/rule-health", tags=["dashboard"])
    async def get_rule_health(
        request: Request,
        response: Response,
        start_date: Annotated[date | datetime | None, FastApiQuery()] = None,
        end_date: Annotated[date | datetime | None, FastApiQuery()] = None,
        source_id: Annotated[str | None, FastApiQuery(min_length=1, max_length=200)] = None,
        dataset_id: Annotated[str | None, FastApiQuery(min_length=1, max_length=200)] = None,
        dimension: Annotated[str | None, FastApiQuery(min_length=1, max_length=40)] = None,
        criticality: Annotated[str | None, FastApiQuery(min_length=1, max_length=20)] = None,
        rule_status: Annotated[str | None, FastApiQuery(min_length=1, max_length=30)] = None,
    ) -> dict[str, Any]:
        if rule_health_service is None:
            raise DashboardQueryError(
                "Rule health service is not available.",
                request.state.correlation_id,
            )
        actor_context = resolver.resolve(request)
        params = _default_window(start_date, end_date)
        params = AnalyticsFilterParams(
            start_at=params.start_at,
            end_at=params.end_at,
            source_id=source_id,
            dataset_id=dataset_id,
        )
        envelope: AnalyticsEnvelope = rule_health_service.get_rule_health(
            actor_context,
            params,
            dimension=dimension,
            criticality=criticality,
            rule_status=rule_status,
        )
        response.headers["Cache-Control"] = "no-store"
        return envelope.to_dict(
            api_version="v1",
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            as_of=datetime.now(timezone.utc),
            applied_filters={
                "start_at": params.start_at.isoformat(),
                "end_at": params.end_at.isoformat(),
                "source_id": source_id,
                "dataset_id": dataset_id,
                "dimension": dimension,
                "criticality": criticality,
                "rule_status": rule_status,
            },
        )

    @app.get("/api/v1/dashboard/metadata-health", tags=["dashboard"])
    async def get_metadata_health(
        request: Request,
        response: Response,
        start_date: Annotated[date | datetime | None, FastApiQuery()] = None,
        end_date: Annotated[date | datetime | None, FastApiQuery()] = None,
        source_id: Annotated[str | None, FastApiQuery(min_length=1, max_length=200)] = None,
        dataset_id: Annotated[str | None, FastApiQuery(min_length=1, max_length=200)] = None,
        classification: Annotated[str | None, FastApiQuery(min_length=1, max_length=40)] = None,
        criticality: Annotated[str | None, FastApiQuery(min_length=1, max_length=20)] = None,
        ownership_status: Annotated[str | None, FastApiQuery(min_length=1, max_length=20)] = None,
    ) -> dict[str, Any]:
        if metadata_health_service is None:
            raise DashboardQueryError(
                "Metadata health service is not available.",
                request.state.correlation_id,
            )
        actor_context = resolver.resolve(request)
        params = _default_window(start_date, end_date)
        params = AnalyticsFilterParams(
            start_at=params.start_at,
            end_at=params.end_at,
            source_id=source_id,
            dataset_id=dataset_id,
        )
        envelope: AnalyticsEnvelope = metadata_health_service.get_metadata_health(
            actor_context,
            params,
            classification=classification,
            criticality=criticality,
            ownership_status=ownership_status,
        )
        response.headers["Cache-Control"] = "no-store"
        return envelope.to_dict(
            api_version="v1",
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            as_of=datetime.now(timezone.utc),
            applied_filters={
                "start_at": params.start_at.isoformat(),
                "end_at": params.end_at.isoformat(),
                "source_id": source_id,
                "dataset_id": dataset_id,
                "classification": classification,
                "criticality": criticality,
                "ownership_status": ownership_status,
            },
        )

    @app.get("/api/v1/dashboard/issue-performance", tags=["dashboard"])
    async def get_issue_performance(
        request: Request,
        response: Response,
        start_date: Annotated[date | datetime | None, FastApiQuery()] = None,
        end_date: Annotated[date | datetime | None, FastApiQuery()] = None,
        source_id: Annotated[str | None, FastApiQuery(min_length=1, max_length=200)] = None,
        dataset_id: Annotated[str | None, FastApiQuery(min_length=1, max_length=200)] = None,
        priority: Annotated[str | None, FastApiQuery(min_length=1, max_length=20)] = None,
        status: Annotated[str | None, FastApiQuery(min_length=1, max_length=30)] = None,
        trigger_type: Annotated[str | None, FastApiQuery(min_length=1, max_length=40)] = None,
    ) -> dict[str, Any]:
        if issue_performance_service is None:
            raise DashboardQueryError(
                "Issue performance service is not available.",
                request.state.correlation_id,
            )
        actor_context = resolver.resolve(request)
        params = _default_window(start_date, end_date)
        params = AnalyticsFilterParams(
            start_at=params.start_at,
            end_at=params.end_at,
            source_id=source_id,
            dataset_id=dataset_id,
        )
        envelope: AnalyticsEnvelope = issue_performance_service.get_issue_performance(
            actor_context,
            params,
            priority=priority,
            status=status,
            trigger_type=trigger_type,
        )
        response.headers["Cache-Control"] = "no-store"
        return envelope.to_dict(
            api_version="v1",
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            as_of=datetime.now(timezone.utc),
            applied_filters={
                "start_at": params.start_at.isoformat(),
                "end_at": params.end_at.isoformat(),
                "source_id": source_id,
                "dataset_id": dataset_id,
                "priority": priority,
                "status": status,
                "trigger_type": trigger_type,
            },
        )

    @app.get("/api/v1/dashboard/scoring-policy-impact", tags=["dashboard"])
    async def get_scoring_policy_impact(
        request: Request,
        response: Response,
        start_date: Annotated[date | datetime | None, FastApiQuery()] = None,
        end_date: Annotated[date | datetime | None, FastApiQuery()] = None,
        source_id: Annotated[str | None, FastApiQuery(min_length=1, max_length=200)] = None,
        dataset_id: Annotated[str | None, FastApiQuery(min_length=1, max_length=200)] = None,
        baseline_version: Annotated[str | None, FastApiQuery(min_length=1, max_length=80)] = None,
        candidate_version: Annotated[str | None, FastApiQuery(min_length=1, max_length=80)] = None,
    ) -> dict[str, Any]:
        if scoring_policy_impact_service is None:
            raise DashboardQueryError(
                "Scoring policy impact service is not available.",
                request.state.correlation_id,
            )
        actor_context = resolver.resolve(request)
        params = _default_window(start_date, end_date)
        params = AnalyticsFilterParams(
            start_at=params.start_at,
            end_at=params.end_at,
            source_id=source_id,
            dataset_id=dataset_id,
        )
        envelope: AnalyticsEnvelope = scoring_policy_impact_service.get_scoring_policy_impact(
            actor_context,
            params,
            baseline_version=baseline_version,
            candidate_version=candidate_version,
        )
        response.headers["Cache-Control"] = "no-store"
        return envelope.to_dict(
            api_version="v1",
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            as_of=datetime.now(timezone.utc),
            applied_filters={
                "start_at": params.start_at.isoformat(),
                "end_at": params.end_at.isoformat(),
                "source_id": source_id,
                "dataset_id": dataset_id,
                "baseline_version": baseline_version,
                "candidate_version": candidate_version,
            },
        )
