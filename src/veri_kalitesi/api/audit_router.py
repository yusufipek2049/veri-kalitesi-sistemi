"""Audit alanı HTTP route kayıtları."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal, Protocol

from fastapi import FastAPI, Query as FastApiQuery, Request, Response
from fastapi.responses import StreamingResponse

from veri_kalitesi.api.models import (
    AuditEventGroupedResponse,
    AuditEventListResponse,
    AuditSummaryResponse,
)
from veri_kalitesi.audit.export import AuditEventExporter
from veri_kalitesi.audit.errors import (
    AuditQueryTechnicalError,
    AuditQueryValidationError,
)
from veri_kalitesi.audit.models import AuditQuery, AuditResult
from veri_kalitesi.audit.service import AuditQueryService
from veri_kalitesi.identity import ActorContext


AUDIT_ACTIONS = (
    ("LDAP_AUTHENTICATION", "Kimlik doğrulama"),
    ("DATA_SOURCE_CONNECTION_TEST", "Bağlantı testi"),
    ("RULE_ACTIVATION", "Kural aktivasyonu"),
    ("SCORING_CONFIGURATION_ACTIVATION", "Skor politikası aktivasyonu"),
    ("REPORT_PREVIEW_VIEWED", "Rapor önizleme"),
    ("IDENTITY_SESSION", "Oturum olayı"),
    ("AUDIT_RECORDS_VIEWED", "Denetim kaydı görüntüleme"),
    ("AUDIT_EXPORT_COMPLETED", "Denetim kaydı dışa aktarma"),
)


class _Resolver(Protocol):
    def resolve(self, request: Request) -> ActorContext | None: ...


def register_audit_routes(
    app: FastAPI,
    *,
    audit_query_service: AuditQueryService | None,
    resolver: _Resolver,
    data_origin: str,
    clock: Callable[[], datetime],
) -> None:
    """Audit alanının route'larını FastAPI uygulamasına kaydeder."""

    @app.get("/api/v1/audit/actions", tags=["audit"])
    async def get_audit_actions(response: Response) -> dict[str, object]:
        response.headers["Cache-Control"] = "no-store"
        return {"items": [{"action": action, "label": label} for action, label in AUDIT_ACTIONS]}

    @app.get("/api/v1/audit/events/export", tags=["audit"])
    async def export_audit_events(
        request: Request,
        days: Annotated[int, FastApiQuery(ge=1, le=31)] = 7,
        period_start: datetime | None = None,
        actor_id: Annotated[str | None, FastApiQuery(min_length=1, max_length=120)] = None,
        action: Annotated[str | None, FastApiQuery(min_length=1, max_length=120)] = None,
        object_type: Annotated[str | None, FastApiQuery(min_length=1, max_length=120)] = None,
        result: AuditResult | None = None,
        correlation_id: Annotated[str | None, FastApiQuery(min_length=1, max_length=200)] = None,
        period_end: datetime | None = None,
        format: Literal["csv", "json"] = "csv",
    ) -> StreamingResponse:
        if audit_query_service is None:
            raise AuditQueryTechnicalError(request.state.correlation_id)
        actor_context = resolver.resolve(request)
        now = _utc_now(clock, request)
        effective_period_start, effective_period_end = _resolve_period(
            now, period_start, period_end, days
        )
        page = audit_query_service.export(
            AuditQuery(
                start_at=effective_period_start,
                end_at=effective_period_end,
                reason_code="AUDIT_EXPORT",
                actor_id=actor_id,
                action=action,
                object_type=object_type,
                result=result,
                correlation_id=correlation_id,
                page_size=audit_query_service.policy.max_export_size,
            ),
            actor_context,
            export_format=format,
        )
        extension = format
        media_type = "text/csv" if format == "csv" else "application/json"
        filename = f"audit-export-{now.date().isoformat()}.{extension}"
        return StreamingResponse(
            AuditEventExporter(page).export(format),
            media_type=media_type,
            headers={
                "Cache-Control": "no-store",
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )

    @app.get(
        "/api/v1/audit/events/grouped",
        response_model=AuditEventGroupedResponse,
        tags=["audit"],
    )
    async def get_grouped_audit_events(
        request: Request,
        response: Response,
        correlation_id: Annotated[str, FastApiQuery(min_length=1, max_length=200)],
        days: Annotated[int, FastApiQuery(ge=1, le=31)] = 7,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
        page_size: Annotated[int, FastApiQuery(ge=1, le=500)] = 500,
    ) -> AuditEventGroupedResponse:
        if audit_query_service is None:
            raise AuditQueryTechnicalError(request.state.correlation_id)
        now = _utc_now(clock, request)
        effective_period_start, effective_period_end = _resolve_period(
            now, period_start, period_end, days
        )
        page = audit_query_service.query(
            AuditQuery(
                start_at=effective_period_start,
                end_at=effective_period_end,
                reason_code="INTERACTIVE_REVIEW",
                correlation_id=correlation_id,
                page_size=page_size,
            ),
            resolver.resolve(request),
            max_page_size=500,
        )
        response.headers["Cache-Control"] = "no-store"
        base_response = AuditEventListResponse.from_domain(
            page,
            period_start=effective_period_start,
            period_end=effective_period_end,
            page_size=page_size,
            correlation_id=request.state.correlation_id,
            data_origin=data_origin,
        )
        grouped_response = AuditEventGroupedResponse(
            **base_response.model_dump(),
        )
        return grouped_response.model_copy(
            update={
                "items": tuple(sorted(grouped_response.items, key=lambda item: item.occurred_at))
            }
        )

    @app.get(
        "/api/v1/audit/events",
        response_model=AuditEventListResponse,
        tags=["audit"],
    )
    async def get_audit_events(
        request: Request,
        response: Response,
        days: Annotated[int, FastApiQuery(ge=1, le=31)] = 7,
        period_start: datetime | None = None,
        actor_id: Annotated[str | None, FastApiQuery(min_length=1, max_length=120)] = None,
        action: Annotated[str | None, FastApiQuery(min_length=1, max_length=120)] = None,
        object_type: Annotated[str | None, FastApiQuery(min_length=1, max_length=120)] = None,
        result: AuditResult | None = None,
        correlation_id: Annotated[str | None, FastApiQuery(min_length=1, max_length=200)] = None,
        period_end: datetime | None = None,
        after_sequence_no: Annotated[int, FastApiQuery(ge=0)] = 0,
        through_sequence_no: Annotated[int | None, FastApiQuery(ge=0)] = None,
        page_size: Annotated[int, FastApiQuery(ge=1, le=100)] = 50,
    ) -> AuditEventListResponse:
        if audit_query_service is None:
            raise AuditQueryTechnicalError(request.state.correlation_id)
        actor_context = resolver.resolve(request)
        now = _utc_now(clock, request)
        effective_period_start, effective_period_end = _resolve_period(
            now, period_start, period_end, days
        )
        page = audit_query_service.query(
            AuditQuery(
                start_at=effective_period_start,
                end_at=effective_period_end,
                reason_code="INTERACTIVE_REVIEW",
                actor_id=actor_id,
                action=action,
                object_type=object_type,
                result=result,
                correlation_id=correlation_id,
                after_sequence_no=after_sequence_no,
                through_sequence_no=through_sequence_no,
                page_size=page_size,
            ),
            actor_context,
        )
        response.headers["Cache-Control"] = "no-store"
        return AuditEventListResponse.from_domain(
            page,
            period_start=effective_period_start,
            period_end=effective_period_end,
            page_size=page_size,
            correlation_id=request.state.correlation_id,
            data_origin=data_origin,
        )

    @app.get(
        "/api/v1/audit/summary",
        response_model=AuditSummaryResponse,
        tags=["audit"],
    )
    async def get_audit_summary(
        request: Request,
        response: Response,
        days: Annotated[int, FastApiQuery(ge=1, le=31)] = 7,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
        actor_id: Annotated[str | None, FastApiQuery(min_length=1, max_length=120)] = None,
        action: Annotated[str | None, FastApiQuery(min_length=1, max_length=120)] = None,
        object_type: Annotated[str | None, FastApiQuery(min_length=1, max_length=120)] = None,
        result: AuditResult | None = None,
    ) -> AuditSummaryResponse:
        if audit_query_service is None:
            raise AuditQueryTechnicalError(request.state.correlation_id)
        now = _utc_now(clock, request)
        effective_period_start, effective_period_end = _resolve_period(
            now, period_start, period_end, days
        )
        summary = audit_query_service.summary(
            AuditQuery(
                start_at=effective_period_start,
                end_at=effective_period_end,
                reason_code="AUDIT_SUMMARY_REVIEW",
                actor_id=actor_id,
                action=action,
                object_type=object_type,
                result=result,
            ),
            resolver.resolve(request),
        )
        response.headers["Cache-Control"] = "no-store"
        return AuditSummaryResponse.from_domain(summary)


def _utc_now(
    clock: Callable[[], datetime],
    request: Request,
) -> datetime:
    now = clock()
    if now.tzinfo is None or now.utcoffset() is None:
        raise AuditQueryTechnicalError(request.state.correlation_id)
    return now.astimezone(timezone.utc)


def _resolve_period(
    now: datetime,
    period_start: datetime | None,
    period_end: datetime | None,
    days: int,
) -> tuple[datetime, datetime]:
    effective_period_end = period_end or now
    if (
        effective_period_end.tzinfo is None
        or effective_period_end.utcoffset() is None
        or effective_period_end > now
    ):
        raise AuditQueryValidationError("Audit period end is invalid.")
    effective_period_end = effective_period_end.astimezone(timezone.utc)
    if period_start is None:
        return effective_period_end - timedelta(days=days), effective_period_end
    if period_start.tzinfo is None or period_start.utcoffset() is None:
        raise AuditQueryValidationError("Audit period start is invalid.")
    return period_start.astimezone(timezone.utc), effective_period_end
