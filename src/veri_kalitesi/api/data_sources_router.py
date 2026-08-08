"""Veri kaynağı ve profil alanı HTTP route kayıtları."""

from __future__ import annotations

from typing import Any, Protocol

from fastapi import FastAPI, Request, Response

from veri_kalitesi.api.data_source_commands import DataSourceCommandResult
from veri_kalitesi.api.identity import DevelopmentActorContextResolver
from veri_kalitesi.api.models_data_sources import (
    DataSourceActivationDecisionRequest,
    DataSourceCreateRequest,
    DataSourceListItemResponse,
    DataSourceListResponse,
    DataSourceMutationResponse,
    DataSourcePassivationRequest,
)
from veri_kalitesi.api.bff import CSRF_HEADER_NAME
from veri_kalitesi.data_sources.query import (
    DataSourceQueryService,
    DataSourceQueryTechnicalError,
)
from veri_kalitesi.identity import ActorContext


class DataSourceMutationService(Protocol):
    """Veri kaynağı mutasyonları için protokol."""

    def create(
        self,
        *,
        payload: DataSourceCreateRequest,
        actor_context: ActorContext | None,
    ) -> DataSourceCommandResult: ...

    def test_connection(
        self, *, data_source_id: str, actor_context: ActorContext | None
    ) -> DataSourceCommandResult: ...

    def request_activation(
        self, *, data_source_id: str, actor_context: ActorContext | None
    ) -> DataSourceCommandResult: ...

    def decide_activation(
        self,
        *,
        activation_request_id: str,
        decision: str,
        reason_code: str,
        actor_context: ActorContext | None,
    ) -> DataSourceCommandResult: ...

    def passivate(
        self,
        *,
        data_source_id: str,
        reason_code: str,
        actor_context: ActorContext | None,
    ) -> DataSourceCommandResult: ...


class _Resolver(Protocol):
    def resolve(self, request: Request) -> Any: ...


def register_data_sources_routes(
    app: FastAPI,
    *,
    data_source_query_service: DataSourceQueryService | None,
    data_source_mutation_service: DataSourceMutationService | None,
    resolver: _Resolver,
    data_origin: str,
) -> None:
    """Veri kaynağı ve profil alanının route'larını FastAPI uygulamasına kaydeder."""

    # ── Sorgu route'ları ──

    @app.get(
        "/api/v1/data-sources",
        response_model=DataSourceListResponse,
        tags=["data-sources"],
    )
    async def get_data_sources(request: Request, response: Response) -> DataSourceListResponse:
        if data_source_query_service is None:
            raise DataSourceQueryTechnicalError(
                "Data source service is unavailable.", request.state.correlation_id
            )
        actor_context = resolver.resolve(request)
        sources = data_source_query_service.list_views_for_actor(actor_context)
        response.headers["Cache-Control"] = "no-store"
        if isinstance(resolver, DevelopmentActorContextResolver):
            response.headers[CSRF_HEADER_NAME] = resolver.request_proof
        return DataSourceListResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            items=tuple(DataSourceListItemResponse.from_view(source) for source in sources),
        )

    # ── Mutasyon route'ları ──

    @app.post(
        "/api/v1/data-sources",
        response_model=DataSourceMutationResponse,
        status_code=201,
        tags=["data-sources"],
    )
    async def create_data_source(
        payload: DataSourceCreateRequest,
        request: Request,
        response: Response,
    ) -> DataSourceMutationResponse:
        if data_source_mutation_service is None:
            raise DataSourceQueryTechnicalError(
                "Data source mutation service is unavailable.", request.state.correlation_id
            )
        actor_context = getattr(request.state, "actor_context", None)
        result = data_source_mutation_service.create(
            payload=payload,
            actor_context=actor_context,
        )
        response.headers["Cache-Control"] = "no-store"
        return DataSourceMutationResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            item=DataSourceListItemResponse.from_view(result.view),
        )

    @app.post(
        "/api/v1/data-sources/{data_source_id}/test",
        response_model=DataSourceMutationResponse,
        tags=["data-sources"],
    )
    async def test_data_source(
        data_source_id: str,
        request: Request,
        response: Response,
    ) -> DataSourceMutationResponse:
        if data_source_mutation_service is None:
            raise DataSourceQueryTechnicalError(
                "Data source mutation service is unavailable.", request.state.correlation_id
            )
        actor_context = getattr(request.state, "actor_context", None)
        result = data_source_mutation_service.test_connection(
            data_source_id=data_source_id,
            actor_context=actor_context,
        )
        response.headers["Cache-Control"] = "no-store"
        return DataSourceMutationResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            item=DataSourceListItemResponse.from_view(result.view),
        )

    @app.post(
        "/api/v1/data-sources/{data_source_id}/activation",
        response_model=DataSourceMutationResponse,
        tags=["data-sources"],
    )
    async def request_data_source_activation(
        data_source_id: str,
        request: Request,
        response: Response,
    ) -> DataSourceMutationResponse:
        if data_source_mutation_service is None:
            raise DataSourceQueryTechnicalError(
                "Data source mutation service is unavailable.", request.state.correlation_id
            )
        actor_context = getattr(request.state, "actor_context", None)
        result = data_source_mutation_service.request_activation(
            data_source_id=data_source_id,
            actor_context=actor_context,
        )
        response.status_code = 201
        response.headers["Cache-Control"] = "no-store"
        return DataSourceMutationResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            item=DataSourceListItemResponse.from_view(result.view),
            activation_request_status=(
                result.activation_request.status.value
                if result.activation_request is not None
                else None
            ),
        )

    @app.post(
        "/api/v1/data-source-activation-requests/{activation_request_id}/decision",
        response_model=DataSourceMutationResponse,
        tags=["data-sources"],
    )
    async def decide_data_source_activation(
        activation_request_id: str,
        payload: DataSourceActivationDecisionRequest,
        request: Request,
        response: Response,
    ) -> DataSourceMutationResponse:
        if data_source_mutation_service is None:
            raise DataSourceQueryTechnicalError(
                "Data source mutation service is unavailable.", request.state.correlation_id
            )
        actor_context = getattr(request.state, "actor_context", None)
        result = data_source_mutation_service.decide_activation(
            activation_request_id=activation_request_id,
            decision=payload.decision,
            reason_code=payload.reason_code,
            actor_context=actor_context,
        )
        response.headers["Cache-Control"] = "no-store"
        return DataSourceMutationResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            item=DataSourceListItemResponse.from_view(result.view),
            activation_request_status=(
                result.activation_request.status.value
                if result.activation_request is not None
                else None
            ),
            replayed=result.replayed,
        )

    @app.post(
        "/api/v1/data-sources/{data_source_id}/passivation",
        response_model=DataSourceMutationResponse,
        tags=["data-sources"],
    )
    async def passivate_data_source(
        data_source_id: str,
        payload: DataSourcePassivationRequest,
        request: Request,
        response: Response,
    ) -> DataSourceMutationResponse:
        if data_source_mutation_service is None:
            raise DataSourceQueryTechnicalError(
                "Data source mutation service is unavailable.", request.state.correlation_id
            )
        actor_context = getattr(request.state, "actor_context", None)
        result = data_source_mutation_service.passivate(
            data_source_id=data_source_id,
            reason_code=payload.reason_code,
            actor_context=actor_context,
        )
        response.headers["Cache-Control"] = "no-store"
        return DataSourceMutationResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            item=DataSourceListItemResponse.from_view(result.view),
        )
