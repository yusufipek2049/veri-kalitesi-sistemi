"""Audit alanı HTTP route kayıtları."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Annotated, Protocol

from fastapi import FastAPI, Query as FastApiQuery, Request, Response

from veri_kalitesi.api.models import AuditEventListResponse
from veri_kalitesi.audit.errors import (
    AuditQueryTechnicalError,
    AuditQueryValidationError,
)
from veri_kalitesi.audit.models import AuditQuery, AuditResult
from veri_kalitesi.audit.service import AuditQueryService
from veri_kalitesi.identity import ActorContext


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

    @app.get(
        "/api/v1/audit/events",
        response_model=AuditEventListResponse,
        tags=["audit"],
    )
    async def get_audit_events(
        request: Request,
        response: Response,
        days: Annotated[int, FastApiQuery(ge=1, le=31)] = 7,
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
        now = clock()
        if now.tzinfo is None or now.utcoffset() is None:
            raise AuditQueryTechnicalError(request.state.correlation_id)
        now = now.astimezone(timezone.utc)
        effective_period_end = period_end or now
        if (
            effective_period_end.tzinfo is None
            or effective_period_end.utcoffset() is None
            or effective_period_end > now
        ):
            raise AuditQueryValidationError("Audit period end is invalid.")
        effective_period_end = effective_period_end.astimezone(timezone.utc)
        period_start = effective_period_end - timedelta(days=days)
        page = audit_query_service.query(
            AuditQuery(
                start_at=period_start,
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
            period_start=period_start.astimezone(timezone.utc),
            period_end=effective_period_end,
            page_size=page_size,
            correlation_id=request.state.correlation_id,
            data_origin=data_origin,
        )
