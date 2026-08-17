"""Jobs (zamanlayıcı) rotaları: nitelik bazlı öneri, bant denetimi ve yönetim.

Bant dışı aralık talepleri 409 + SCHEDULE_INTERVAL_EXCEPTION ile yönetişim
onay merkezine yönlendirilir; bant içi tanımlar doğrudan oluşturulur.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from veri_kalitesi.api.identity import ActorContextResolver
from veri_kalitesi.api.service_groups import CatalogDatasetReader
from veri_kalitesi.data_sources.errors import NotFoundError as DataSourceNotFoundError
from veri_kalitesi.executions.errors import (
    ExecutionValidationError,
    ScheduleGovernanceApprovalRequiredError,
)
from veri_kalitesi.executions.schedule_policy import (
    band_description,
    is_within_band,
    recommend_for,
)
from veri_kalitesi.executions.scheduling import (
    Schedule,
    ScheduleType,
    SchedulingService,
)


class ScheduleCreateRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1, max_length=200)
    dataset_id: str = Field(min_length=1)
    schedule_type: str = Field(min_length=1)
    timezone_name: str = Field(min_length=1)
    rule_version_ids: tuple[str, ...] = Field(min_length=1)
    local_time: str | None = None
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    day_of_month: int | None = Field(default=None, ge=1, le=31)
    interval_minutes: int | None = Field(default=None, ge=1, le=43200)


class ScheduleResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    schedule_id: str
    name: str
    schedule_type: str
    timezone_name: str
    rule_version_ids: tuple[str, ...]
    created_by: str
    local_time: str | None = None
    day_of_week: int | None = None
    day_of_month: int | None = None
    interval_minutes: int | None = None
    is_active: bool
    next_run_at: datetime | None = None
    created_at: datetime
    last_triggered_at: datetime | None = None


class ScheduleListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    items: tuple[ScheduleResponse, ...]


class ScheduleCreatedResponse(ScheduleResponse):
    preview_runs: tuple[datetime, ...] = ()


class ScheduleProposalItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    schedule_type: str
    interval_minutes: int | None = None
    label: str


class ScheduleProposalResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    dataset_id: str
    timeliness_nature: str | None = None
    band: str | None = None
    proposals: tuple[ScheduleProposalItem, ...] = ()


def _schedule_body(schedule: Schedule) -> dict[str, object]:
    return {
        "schedule_id": schedule.schedule_id,
        "name": schedule.name,
        "schedule_type": schedule.schedule_type.value,
        "timezone_name": schedule.timezone_name,
        "rule_version_ids": schedule.rule_version_ids,
        "created_by": schedule.created_by,
        "local_time": schedule.local_time.isoformat() if schedule.local_time else None,
        "day_of_week": schedule.day_of_week,
        "day_of_month": schedule.day_of_month,
        "interval_minutes": schedule.interval_minutes,
        "is_active": schedule.is_active,
        "next_run_at": schedule.next_run_at,
        "created_at": schedule.created_at,
        "last_triggered_at": schedule.last_triggered_at,
    }


def register_schedules_routes(
    app: FastAPI,
    *,
    scheduling_service: SchedulingService | None,
    dataset_reader: CatalogDatasetReader | None,
    resolver: ActorContextResolver,
    data_origin: str,
) -> None:
    """Zamanlayıcı (jobs) rotalarını *app* üzerine kaydeder."""

    @app.get("/api/v1/schedules", tags=["schedules"])
    async def list_schedules(request: Request, response: Response) -> ScheduleListResponse:
        if scheduling_service is None:
            raise HTTPException(status_code=503, detail="Schedule service is unavailable.")
        resolver.resolve(request)
        schedules = scheduling_service.repository.list_all()
        response.headers["Cache-Control"] = "no-store"
        return ScheduleListResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            items=tuple(
                ScheduleResponse(
                    data_origin=data_origin,
                    correlation_id=request.state.correlation_id,
                    **_schedule_body(s),  # type: ignore[arg-type]
                )
                for s in schedules
            ),
        )

    @app.get(
        "/api/v1/datasets/{dataset_id}/schedule-proposals",
        tags=["schedules"],
    )
    async def get_schedule_proposals(
        dataset_id: str, request: Request, response: Response
    ) -> ScheduleProposalResponse:
        if dataset_reader is None:
            raise HTTPException(status_code=503, detail="Schedule service is unavailable.")
        resolver.resolve(request)
        try:
            dataset = dataset_reader.get_dataset(dataset_id)
        except (DataSourceNotFoundError, KeyError) as exc:
            raise HTTPException(status_code=404, detail="Dataset not found.") from exc
        response.headers["Cache-Control"] = "no-store"
        nature = dataset.timeliness_nature
        return ScheduleProposalResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            dataset_id=dataset.dataset_id,
            timeliness_nature=nature.value if nature else None,
            band=band_description(nature) if nature else None,
            proposals=tuple(
                ScheduleProposalItem(
                    schedule_type=p.schedule_type.value,
                    interval_minutes=p.interval_minutes,
                    label=p.label,
                )
                for p in (recommend_for(nature) if nature else ())
            ),
        )

    @app.post("/api/v1/schedules", status_code=201, tags=["schedules"])
    async def create_schedule(
        payload: ScheduleCreateRequest, request: Request, response: Response
    ) -> ScheduleCreatedResponse:
        if scheduling_service is None or dataset_reader is None:
            raise HTTPException(status_code=503, detail="Schedule service is unavailable.")
        actor_context = resolver.resolve(request)
        assert actor_context is not None  # narrowed after resolver
        try:
            dataset = dataset_reader.get_dataset(payload.dataset_id)
        except (DataSourceNotFoundError, KeyError) as exc:
            raise HTTPException(status_code=404, detail="Dataset not found.") from exc
        if dataset.timeliness_nature is None:
            raise HTTPException(
                status_code=422,
                detail=("Dataset timeliness nature must be assigned before a job can be defined."),
            )
        try:
            schedule_type = ScheduleType(payload.schedule_type.strip().upper())
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Schedule type is invalid.") from exc
        if not is_within_band(dataset.timeliness_nature, schedule_type, payload.interval_minutes):
            raise ScheduleGovernanceApprovalRequiredError()
        try:
            schedule, preview = scheduling_service.create_schedule(
                actor_id=actor_context.actor_id,
                name=payload.name,
                schedule_type=payload.schedule_type,
                timezone_name=payload.timezone_name,
                rule_version_ids=payload.rule_version_ids,
                local_time=payload.local_time,
                day_of_week=payload.day_of_week,
                day_of_month=payload.day_of_month,
                interval_minutes=payload.interval_minutes,
                correlation_id=request.state.correlation_id,
            )
        except ExecutionValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        response.headers["Cache-Control"] = "no-store"
        return ScheduleCreatedResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            preview_runs=preview,
            **_schedule_body(schedule),  # type: ignore[arg-type]
        )

    @app.post("/api/v1/schedules/{schedule_id}/activate", tags=["schedules"])
    async def activate_schedule(
        schedule_id: str, request: Request, response: Response
    ) -> ScheduleResponse:
        return await _set_active(schedule_id, request, response, is_active=True)

    @app.post("/api/v1/schedules/{schedule_id}/deactivate", tags=["schedules"])
    async def deactivate_schedule(
        schedule_id: str, request: Request, response: Response
    ) -> ScheduleResponse:
        return await _set_active(schedule_id, request, response, is_active=False)

    async def _set_active(
        schedule_id: str, request: Request, response: Response, *, is_active: bool
    ) -> ScheduleResponse:
        if scheduling_service is None:
            raise HTTPException(status_code=503, detail="Schedule service is unavailable.")
        actor_context = resolver.resolve(request)
        assert actor_context is not None  # narrowed after resolver
        try:
            schedule = scheduling_service.set_active(
                schedule_id,
                actor_id=actor_context.actor_id,
                is_active=is_active,
                correlation_id=request.state.correlation_id,
            )
        except ExecutionValidationError as exc:
            if str(exc) == "Schedule not found.":
                raise HTTPException(status_code=404, detail="Schedule not found.") from exc
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        response.headers["Cache-Control"] = "no-store"
        return ScheduleResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            **_schedule_body(schedule),  # type: ignore[arg-type]
        )
