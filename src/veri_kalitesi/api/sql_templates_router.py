"""Adlandırılmış SQL şablonu HTTP route kayıtları.

Çalıştırma ekranındaki özel SQL akışı bu şablonları listeler, kaydeder ve
siler. Şablon adı, üretilen CUSTOM_SQL kuralının adı olarak kullanılır.
"""

from __future__ import annotations

from typing import Protocol

from fastapi import FastAPI, Request, Response

from veri_kalitesi.api.models_sql_templates import (
    SqlTemplateCreateRequest,
    SqlTemplateDetailResponse,
    SqlTemplateItemResponse,
    SqlTemplateListResponse,
    SqlTemplateUpdateRequest,
)
from veri_kalitesi.identity import ActorContext
from veri_kalitesi.sql_templates import SqlTemplateService, SqlTemplateTechnicalError


class _Resolver(Protocol):
    """Aktor cozumleyici yuzeyi; ActorContextResolver bunu karsilar."""

    def resolve(self, request: Request) -> ActorContext | None: ...


def register_sql_template_routes(
    app: FastAPI,
    *,
    sql_template_service: SqlTemplateService | None,
    resolver: _Resolver,
    data_origin: str,
) -> None:
    """SQL şablonu route'larını FastAPI uygulamasına kaydeder."""

    @app.get(
        "/api/v1/sql-templates",
        response_model=SqlTemplateListResponse,
        tags=["sql-templates"],
    )
    async def list_sql_templates(request: Request, response: Response) -> SqlTemplateListResponse:
        service = _service(sql_template_service, request)
        items = service.list_templates(resolver.resolve(request))
        response.headers["Cache-Control"] = "no-store"
        return SqlTemplateListResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            items=tuple(SqlTemplateItemResponse.from_domain(item) for item in items),
        )

    @app.post(
        "/api/v1/sql-templates",
        response_model=SqlTemplateDetailResponse,
        status_code=201,
        tags=["sql-templates"],
    )
    async def create_sql_template(
        payload: SqlTemplateCreateRequest, request: Request, response: Response
    ) -> SqlTemplateDetailResponse:
        service = _service(sql_template_service, request)
        template = service.create_template(
            _mutation_actor(request, resolver),
            name=payload.name,
            sql_text=payload.sql_text,
            description=payload.description,
            default_timeout_seconds=payload.default_timeout_seconds,
            default_row_limit=payload.default_row_limit,
        )
        response.headers["Cache-Control"] = "no-store"
        return SqlTemplateDetailResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            item=SqlTemplateItemResponse.from_domain(template),
        )

    @app.patch(
        "/api/v1/sql-templates/{template_id}",
        response_model=SqlTemplateDetailResponse,
        tags=["sql-templates"],
    )
    async def update_sql_template(
        template_id: str,
        payload: SqlTemplateUpdateRequest,
        request: Request,
        response: Response,
    ) -> SqlTemplateDetailResponse:
        service = _service(sql_template_service, request)
        template = service.update_template(
            _mutation_actor(request, resolver),
            template_id,
            name=payload.name,
            sql_text=payload.sql_text,
            description=payload.description,
            default_timeout_seconds=payload.default_timeout_seconds,
            default_row_limit=payload.default_row_limit,
        )
        response.headers["Cache-Control"] = "no-store"
        return SqlTemplateDetailResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            item=SqlTemplateItemResponse.from_domain(template),
        )

    @app.delete(
        "/api/v1/sql-templates/{template_id}",
        status_code=204,
        tags=["sql-templates"],
    )
    async def delete_sql_template(
        template_id: str, request: Request, response: Response
    ) -> Response:
        service = _service(sql_template_service, request)
        service.delete_template(_mutation_actor(request, resolver), template_id)
        return Response(status_code=204, headers={"Cache-Control": "no-store"})


def _service(
    sql_template_service: SqlTemplateService | None, request: Request
) -> SqlTemplateService:
    if sql_template_service is None:
        raise SqlTemplateTechnicalError("SQL template service is unavailable.")
    return sql_template_service


def _mutation_actor(request: Request, resolver: _Resolver) -> ActorContext | None:
    actor_context = getattr(request.state, "actor_context", None)
    if actor_context is None:
        actor_context = resolver.resolve(request)
    return actor_context
