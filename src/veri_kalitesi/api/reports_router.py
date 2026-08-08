"""Rapor/reports alanı HTTP route kayıtları."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Protocol

from fastapi import FastAPI, Query as FastApiQuery, Request, Response

from veri_kalitesi.api.models import (
    ReportCreateRequest,
    ReportCreateResponse,
    ReportListResponse,
    ReportRequestResponse,
    ReportScheduleCreateRequest as ApiReportScheduleCreateRequest,
    ReportScheduleCreateResponse,
    ReportScheduleDeleteResponse,
    ReportScheduleItemResponse,
    ReportScheduleListResponse,
    ReportScheduleTriggerResponse,
    ReportSummaryResponse,
)
from veri_kalitesi.identity import ActorContext
from veri_kalitesi.reporting import (
    ReportPreviewRequest,
    ReportPreviewService,
    ReportRequest,
    ReportScheduleService,
    ReportService,
    ReportTechnicalError,
    ReportValidationError,
)
from veri_kalitesi.reporting.models import ReportFormat, ReportType


class _Resolver(Protocol):
    def resolve(self, request: Request) -> ActorContext | None: ...


def register_reports_routes(
    app: FastAPI,
    *,
    report_preview_service: ReportPreviewService | None,
    report_service: ReportService | None,
    report_schedule_service: ReportScheduleService | None,
    resolver: _Resolver,
    data_origin: str,
    clock: Callable[[], datetime],
) -> None:
    """Rapor alanının route'larını FastAPI uygulamasına kaydeder."""

    @app.get(
        "/api/v1/reports/summary",
        response_model=ReportSummaryResponse,
        tags=["reports"],
    )
    async def get_report_summary(request: Request, response: Response) -> ReportSummaryResponse:
        if report_preview_service is None:
            raise ReportTechnicalError(request.state.correlation_id)
        actor_context = resolver.resolve(request)
        period_end = clock()
        if period_end.tzinfo is None or period_end.utcoffset() is None:
            raise ReportValidationError("Report API clock must be timezone-aware.")
        period_end = period_end.astimezone(timezone.utc)
        preview = report_preview_service.preview_summary(
            ReportPreviewRequest(
                start_at=period_end - timedelta(days=30),
                end_at=period_end,
                reason_code="INTERACTIVE_PREVIEW",
            ),
            actor_context,
        )
        response.headers["Cache-Control"] = "no-store"
        return ReportSummaryResponse.from_domain(
            preview,
            correlation_id=request.state.correlation_id,
            data_origin=data_origin,
        )

    @app.post(
        "/api/v1/reports/",
        response_model=ReportCreateResponse,
        status_code=202,
        tags=["reports"],
    )
    async def create_report(
        request: Request,
        response: Response,
        body: ReportCreateRequest,
    ) -> ReportCreateResponse:
        if report_service is None:
            raise ReportTechnicalError(request.state.correlation_id)
        actor_context = resolver.resolve(request)
        domain_request = ReportRequest(
            report_type=ReportType(body.report_type),
            format=ReportFormat(body.format),
            parameters=body.parameters,
            reason_code=body.reason_code,
            sensitivity_level=body.sensitivity_level,
        )
        report = report_service.request_report(domain_request, actor_context)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Report-ID"] = report.report_id
        return ReportCreateResponse(
            api_version="v1",
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            report=ReportRequestResponse.from_domain(report),
        )

    @app.get(
        "/api/v1/reports/",
        response_model=ReportListResponse,
        tags=["reports"],
    )
    async def list_reports(
        request: Request,
        response: Response,
        limit: Annotated[int, FastApiQuery(ge=1, le=100)] = 50,
        offset: Annotated[int, FastApiQuery(ge=0)] = 0,
    ) -> ReportListResponse:
        if report_service is None:
            raise ReportTechnicalError(request.state.correlation_id)
        actor_context = resolver.resolve(request)
        reports = report_service.list_reports(actor_context, limit=limit, offset=offset)
        response.headers["Cache-Control"] = "no-store"
        return ReportListResponse(
            api_version="v1",
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            items=tuple(ReportRequestResponse.from_domain(r) for r in reports),
        )

    @app.get(
        "/api/v1/reports/{report_id}",
        response_model=ReportCreateResponse,
        tags=["reports"],
    )
    async def get_report(
        request: Request,
        response: Response,
        report_id: str,
    ) -> ReportCreateResponse:
        if report_service is None:
            raise ReportTechnicalError(request.state.correlation_id)
        actor_context = resolver.resolve(request)
        report = report_service.get_report(report_id, actor_context)
        response.headers["Cache-Control"] = "no-store"
        return ReportCreateResponse(
            api_version="v1",
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            report=ReportRequestResponse.from_domain(report),
        )

    @app.get(
        "/api/v1/reports/{report_id}/download",
        tags=["reports"],
    )
    async def download_report(
        request: Request,
        response: Response,
        report_id: str,
    ) -> Response:
        if report_service is None:
            raise ReportTechnicalError(request.state.correlation_id)
        actor_context = resolver.resolve(request)
        report = report_service.download_report(report_id, actor_context)
        if report.online_file_reference is None:
            raise ReportTechnicalError(request.state.correlation_id)
        file_path = Path(report.online_file_reference)
        if not file_path.exists():
            raise ReportTechnicalError(request.state.correlation_id)
        content = file_path.read_bytes()
        mime_map = {
            "PDF": "application/pdf",
            "XLSX": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "CSV": "text/csv; charset=utf-8",
        }
        media_type = mime_map.get(report.format.value, "application/octet-stream")
        filename = f"report-{report.report_id[:8]}.{report.format.value.lower()}"
        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(content)),
                "Cache-Control": "no-store",
            },
        )

    @app.get(
        "/api/v1/report-schedules",
        response_model=ReportScheduleListResponse,
        tags=["reports"],
    )
    async def list_report_schedules(
        request: Request,
        response: Response,
    ) -> ReportScheduleListResponse:
        if report_schedule_service is None:
            raise ReportTechnicalError(request.state.correlation_id)
        schedules = report_schedule_service.list_schedules()
        response.headers["Cache-Control"] = "no-store"
        return ReportScheduleListResponse(
            api_version="v1",
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            items=tuple(ReportScheduleItemResponse.from_domain(s) for s in schedules),
        )

    @app.post(
        "/api/v1/report-schedules",
        response_model=ReportScheduleCreateResponse,
        status_code=201,
        tags=["reports"],
    )
    async def create_report_schedule(
        request: Request,
        response: Response,
        body: ApiReportScheduleCreateRequest,
    ) -> ReportScheduleCreateResponse:
        if report_schedule_service is None:
            raise ReportTechnicalError(request.state.correlation_id)
        actor_context = getattr(request.state, "actor_context", None)
        if actor_context is None:
            actor_context = resolver.resolve(request)
        from veri_kalitesi.reporting.scheduling import ReportScheduleCreateRequest as DomainRequest

        domain_request = DomainRequest(
            name=body.name,
            report_type=ReportType(body.report_type),
            format=ReportFormat(body.format),
            parameters=body.parameters,
            sensitivity_level=body.sensitivity_level,
            recipients=body.recipients,
            schedule_type=body.schedule_type,
            timezone_name=body.timezone_name,
            local_time=body.local_time,
            once_at=body.once_at,
            day_of_week=body.day_of_week,
            day_of_month=body.day_of_month,
        )
        schedule, preview = report_schedule_service.create_schedule(
            domain_request,
            created_by=actor_context.actor_id if actor_context else "system",
        )
        response.headers["Cache-Control"] = "no-store"
        return ReportScheduleCreateResponse(
            api_version="v1",
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            item=ReportScheduleItemResponse.from_domain(schedule),
            preview=tuple(p.isoformat() for p in preview),
        )

    @app.delete(
        "/api/v1/report-schedules/{schedule_id}",
        response_model=ReportScheduleDeleteResponse,
        tags=["reports"],
    )
    async def delete_report_schedule(
        schedule_id: str,
        request: Request,
        response: Response,
    ) -> ReportScheduleDeleteResponse:
        if report_schedule_service is None:
            raise ReportTechnicalError(request.state.correlation_id)
        report_schedule_service.delete_schedule(schedule_id)
        response.headers["Cache-Control"] = "no-store"
        return ReportScheduleDeleteResponse(
            api_version="v1",
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
        )

    @app.post(
        "/api/v1/report-schedules/trigger-due",
        response_model=ReportScheduleTriggerResponse,
        tags=["reports"],
    )
    async def trigger_due_report_schedules(
        request: Request,
        response: Response,
    ) -> ReportScheduleTriggerResponse:
        if report_schedule_service is None:
            raise ReportTechnicalError(request.state.correlation_id)
        triggered = report_schedule_service.trigger_due()
        response.headers["Cache-Control"] = "no-store"
        return ReportScheduleTriggerResponse(
            api_version="v1",
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            triggered_report_ids=triggered,
            triggered_count=len(triggered),
        )
