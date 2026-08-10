"""Çalıştırma/executions alanı HTTP route kayıtları."""

from __future__ import annotations

from typing import Protocol

from fastapi import FastAPI, Request, Response

from veri_kalitesi.api.bff import CSRF_HEADER_NAME
from veri_kalitesi.api.identity import DevelopmentActorContextResolver
from veri_kalitesi.api.models import (
    ExecutionCancelRequest,
    ExecutionDetailResponse,
    ExecutionListResponse,
    ExecutionListItemResponse,
    ExecutionStartRequest,
    ExecutionStartResponse,
)
from veri_kalitesi.executions.models import ExecutionMode, RuleExecution
from veri_kalitesi.executions.query import (
    ExecutionQueryService,
    ExecutionQueryTechnicalError,
)
from veri_kalitesi.identity import ActorContext


class ExecutionStartService(Protocol):
    def start_manual(
        self,
        *,
        rule_version_ids: tuple[str, ...],
        source_ids: tuple[str, ...],
        idempotency_key: str,
        actor_context: ActorContext,
        execution_mode: ExecutionMode = ExecutionMode.OFFICIAL,
    ) -> RuleExecution: ...


class ExecutionCancelService(Protocol):
    def cancel(
        self,
        execution_id: str,
        *,
        reason: str,
        actor_context: ActorContext,
    ) -> RuleExecution: ...


class _Resolver(Protocol):
    def resolve(self, request: Request) -> ActorContext | None: ...


def register_executions_routes(
    app: FastAPI,
    *,
    execution_query_service: ExecutionQueryService | None,
    execution_start_service: ExecutionStartService | None,
    execution_cancel_service: ExecutionCancelService | None,
    resolver: _Resolver,
    data_origin: str,
) -> None:
    """Çalıştırma alanının route'larını FastAPI uygulamasına kaydeder."""

    @app.get(
        "/api/v1/executions",
        response_model=ExecutionListResponse,
        tags=["executions"],
    )
    async def get_executions(request: Request, response: Response) -> ExecutionListResponse:
        if execution_query_service is None:
            raise ExecutionQueryTechnicalError(
                "Execution service is unavailable.", request.state.correlation_id
            )
        actor_context = resolver.resolve(request)
        executions = execution_query_service.list_for_actor(actor_context)
        response.headers["Cache-Control"] = "no-store"
        return ExecutionListResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            limit=execution_query_service.page_limit,
            items=tuple(
                ExecutionListItemResponse.from_domain(execution) for execution in executions
            ),
        )

    @app.get(
        "/api/v1/executions/{execution_id}",
        response_model=ExecutionDetailResponse,
        tags=["executions"],
    )
    async def get_execution_detail(
        execution_id: str,
        request: Request,
        response: Response,
    ) -> ExecutionDetailResponse:
        if execution_query_service is None:
            raise ExecutionQueryTechnicalError(
                "Execution service is unavailable.", request.state.correlation_id
            )
        actor_context = getattr(request.state, "actor_context", None)
        if actor_context is None:
            actor_context = resolver.resolve(request)
        execution, results = execution_query_service.get_detail_for_actor(
            execution_id, actor_context
        )
        response.headers["Cache-Control"] = "no-store"
        if isinstance(resolver, DevelopmentActorContextResolver):
            response.headers[CSRF_HEADER_NAME] = resolver.request_proof
        return ExecutionDetailResponse.from_domain(
            execution,
            results,
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
        )

    @app.post(
        "/api/v1/executions",
        response_model=ExecutionStartResponse,
        status_code=201,
        tags=["executions"],
    )
    async def start_manual_execution(
        payload: ExecutionStartRequest,
        request: Request,
        response: Response,
    ) -> ExecutionStartResponse:
        if execution_start_service is None:
            raise ExecutionQueryTechnicalError(
                "Execution start service is unavailable.", request.state.correlation_id
            )
        actor_context = getattr(request.state, "actor_context", None)
        if actor_context is None:
            actor_context = resolver.resolve(request)
        assert actor_context is not None  # narrowed after resolver
        execution = execution_start_service.start_manual(
            rule_version_ids=payload.rule_version_ids,
            source_ids=payload.source_ids,
            idempotency_key=payload.idempotency_key,
            actor_context=actor_context,
            execution_mode=ExecutionMode(payload.execution_mode),
        )
        response.headers["Cache-Control"] = "no-store"
        return ExecutionStartResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            item=ExecutionListItemResponse.from_domain(execution),
        )

    @app.post(
        "/api/v1/executions/{execution_id}/cancel",
        response_model=ExecutionStartResponse,
        tags=["executions"],
    )
    async def cancel_execution(
        execution_id: str,
        payload: ExecutionCancelRequest,
        request: Request,
        response: Response,
    ) -> ExecutionStartResponse:
        if execution_cancel_service is None:
            raise ExecutionQueryTechnicalError(
                "Execution cancel service is unavailable.", request.state.correlation_id
            )
        actor_context = getattr(request.state, "actor_context", None)
        if actor_context is None:
            actor_context = resolver.resolve(request)
        assert actor_context is not None  # narrowed after resolver
        execution = execution_cancel_service.cancel(
            execution_id,
            reason=payload.reason,
            actor_context=actor_context,
        )
        response.headers["Cache-Control"] = "no-store"
        return ExecutionStartResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            item=ExecutionListItemResponse.from_domain(execution),
        )
