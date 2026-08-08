"""Dashboard alanı HTTP route kayıtları."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Protocol

from fastapi import FastAPI, Query as FastApiQuery, Request, Response

from veri_kalitesi.api.models_dashboard import DashboardSummaryResponse
from veri_kalitesi.dashboard import (
    DashboardFilterLevel,
    DashboardFilterParams,
    DashboardFilterScoreStatus,
    DashboardFilterScopeType,
    DashboardQueryService,
    DashboardValidationError,
)


class _Resolver(Protocol):
    def resolve(self, request: Request) -> Any: ...


def build_dashboard_filters(
    *,
    start_date: datetime | None,
    end_date: datetime | None,
    scope_type: str | None,
    scope_id: str | None,
    score_status: str | None,
    level: str | None,
) -> DashboardFilterParams | None:
    """FR-057: API sorgu parametrelerini DashboardFilterParams'a dönüştürür.

    Geçersiz enum değerleri fail-closed doğrulama hatasıdır (AC-04).
    """
    if all(v is None for v in (start_date, end_date, scope_type, scope_id, score_status, level)):
        return None

    parsed_scope_type: DashboardFilterScopeType | None = None
    if scope_type is not None:
        try:
            parsed_scope_type = DashboardFilterScopeType(scope_type)
        except ValueError:
            raise DashboardValidationError(
                f"Invalid scope_type filter: {scope_type!r}. Must be SOURCE or ENTERPRISE."
            )

    parsed_score_status: DashboardFilterScoreStatus | None = None
    if score_status is not None:
        try:
            parsed_score_status = DashboardFilterScoreStatus(score_status)
        except ValueError:
            raise DashboardValidationError(f"Invalid score_status filter: {score_status!r}.")

    parsed_level: DashboardFilterLevel | None = None
    if level is not None:
        try:
            parsed_level = DashboardFilterLevel(level)
        except ValueError:
            raise DashboardValidationError(f"Invalid level filter: {level!r}.")

    if scope_id is not None and not scope_id.strip():
        raise DashboardValidationError("scope_id filter must not be blank.")

    return DashboardFilterParams(
        start_date=start_date,
        end_date=end_date,
        scope_type=parsed_scope_type,
        scope_id=scope_id,
        score_status=parsed_score_status,
        level=parsed_level,
    )


def register_dashboard_routes(
    app: FastAPI,
    *,
    dashboard_service: DashboardQueryService,
    resolver: _Resolver,
    data_origin: str,
) -> None:
    """Dashboard alanının route'larını FastAPI uygulamasına kaydeder."""

    @app.get(
        "/api/v1/dashboard/summary",
        response_model=DashboardSummaryResponse,
        tags=["dashboard"],
    )
    async def get_dashboard_summary(
        request: Request,
        response: Response,
        start_date: Annotated[
            datetime | None,
            FastApiQuery(description="FR-057 filtre: başlangıç tarihi (ISO-8601, timezone-aware)"),
        ] = None,
        end_date: Annotated[
            datetime | None,
            FastApiQuery(description="FR-057 filtre: bitiş tarihi (ISO-8601, timezone-aware)"),
        ] = None,
        scope_type: Annotated[
            str | None, FastApiQuery(description="FR-057 filtre: SOURCE veya ENTERPRISE")
        ] = None,
        scope_id: Annotated[
            str | None, FastApiQuery(description="FR-057 filtre: kapsam kimliği")
        ] = None,
        score_status: Annotated[
            str | None, FastApiQuery(description="FR-057 filtre: skor durumu enum değeri")
        ] = None,
        level: Annotated[
            str | None, FastApiQuery(description="FR-057 filtre: kalite seviyesi enum değeri")
        ] = None,
    ) -> DashboardSummaryResponse:
        actor_context = resolver.resolve(request)
        filters = build_dashboard_filters(
            start_date=start_date,
            end_date=end_date,
            scope_type=scope_type,
            scope_id=scope_id,
            score_status=score_status,
            level=level,
        )
        overview = dashboard_service.get_overview(actor_context, filters=filters)
        response.headers["Cache-Control"] = "no-store"
        return DashboardSummaryResponse.from_domain(
            overview,
            correlation_id=request.state.correlation_id,
            data_origin=data_origin,
        )
