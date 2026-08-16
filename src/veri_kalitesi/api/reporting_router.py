"""Rapor metadatası için veri-minimum HTTP okuma yüzeyi."""

from __future__ import annotations

from typing import Protocol

from fastapi import FastAPI, Query as FastApiQuery, Request, Response
from pydantic import BaseModel, ConfigDict

from veri_kalitesi.identity import ActorContext
from veri_kalitesi.reporting.models import Report
from veri_kalitesi.reporting.errors import ReportTechnicalError
from veri_kalitesi.reporting.service import ReportQueryService


class _Resolver(Protocol):
    def resolve(self, request: Request) -> ActorContext | None: ...


class ReportItemResponse(BaseModel):
    """Dosya yolu, parametre ve hata ayrıntısı taşımayan rapor özeti."""

    model_config = ConfigDict(frozen=True)

    report_id: str
    report_type: str
    format: str
    status: str
    sensitivity_level: str | None
    file_size: int | None
    expires_at: str | None
    created_at: str
    completed_at: str | None

    @classmethod
    def from_domain(cls, report: Report) -> "ReportItemResponse":
        return cls(
            report_id=report.report_id,
            report_type=report.report_type.value,
            format=report.format.value,
            status=report.status.value,
            sensitivity_level=report.sensitivity_level,
            file_size=report.file_size,
            expires_at=report.expires_at.isoformat() if report.expires_at else None,
            created_at=report.created_at.isoformat(),
            completed_at=report.completed_at.isoformat() if report.completed_at else None,
        )


class ReportListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    items: tuple[ReportItemResponse, ...]


class ReportDetailResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    item: ReportItemResponse


def register_reporting_routes(
    app: FastAPI,
    *,
    report_query_service: ReportQueryService | None,
    resolver: _Resolver,
    data_origin: str,
) -> None:
    """Sahiplik kontrollü rapor rotalarını sabit bir HTTP yüzeyiyle kaydeder."""

    @app.get("/api/v1/reports", response_model=ReportListResponse, tags=["reports"])
    async def list_reports(
        request: Request,
        response: Response,
        limit: int = FastApiQuery(default=50, ge=1, le=100),
        offset: int = FastApiQuery(default=0, ge=0),
    ) -> ReportListResponse:
        if report_query_service is None:
            raise ReportTechnicalError(request.state.correlation_id)
        reports = report_query_service.list_reports(
            resolver.resolve(request),
            limit=limit,
            offset=offset,
        )
        response.headers["Cache-Control"] = "no-store"
        return ReportListResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            items=tuple(ReportItemResponse.from_domain(item) for item in reports),
        )

    @app.get(
        "/api/v1/reports/{report_id}",
        response_model=ReportDetailResponse,
        tags=["reports"],
    )
    async def get_report(
        report_id: str,
        request: Request,
        response: Response,
    ) -> ReportDetailResponse:
        if report_query_service is None:
            raise ReportTechnicalError(request.state.correlation_id)
        report = report_query_service.get_report(report_id, resolver.resolve(request))
        response.headers["Cache-Control"] = "no-store"
        return ReportDetailResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            item=ReportItemResponse.from_domain(report),
        )
