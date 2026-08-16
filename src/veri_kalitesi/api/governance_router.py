"""Yönetişim görev merkezi HTTP route kayıtları.

Ortak onay listesi ve detayının yanı sıra merkezi karar (onayla/reddet),
geri çekme ve uygulama aksiyonlarını sunar. Karar ve uygulama ayrı
işlemlerdir; güvenlik kontrolleri backend komut servisinde fail-closed
uygulanır.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request, Response

from veri_kalitesi.api.models import (
    GovernanceApprovalCreateRequest,
    GovernanceApprovalDecisionRequest,
    GovernanceApprovalDetailResponse,
    GovernanceApprovalItemResponse,
    GovernanceApprovalListResponse,
    GovernanceApprovalWithdrawRequest,
)
from veri_kalitesi.governance import (
    GovernanceApprovalCommandService,
    GovernanceApprovalQueryService,
    GovernanceDomain,
    GovernanceQueryTechnicalError,
    GovernanceView,
    center_request_to_item,
)
from veri_kalitesi.identity import ActorContext, is_trusted_actor_context


class _Resolver:
    def resolve(self, request: Request) -> ActorContext | None: ...


def register_governance_routes(
    app: FastAPI,
    *,
    governance_query_service: GovernanceApprovalQueryService | None,
    governance_command_service: GovernanceApprovalCommandService | None = None,
    resolver: _Resolver,
    data_origin: str,
) -> None:
    """Yönetişim görev merkezinin route'larını FastAPI uygulamasına kaydeder."""

    @app.get(
        "/api/v1/governance/approval-requests",
        response_model=GovernanceApprovalListResponse,
        tags=["governance"],
    )
    async def list_governance_approval_requests(
        request: Request,
        response: Response,
        view: str = "ALL",
        domain: str | None = None,
    ) -> GovernanceApprovalListResponse:
        if governance_query_service is None:
            raise GovernanceQueryTechnicalError(
                "Governance service is unavailable.", request.state.correlation_id
            )
        try:
            governance_view = GovernanceView(view.strip().upper())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Governance view is invalid.") from exc
        domain_filter: GovernanceDomain | None = None
        if domain is not None:
            try:
                domain_filter = GovernanceDomain(domain.strip().upper())
            except ValueError as exc:
                raise HTTPException(
                    status_code=400, detail="Governance domain filter is invalid."
                ) from exc
        actor_context = resolver.resolve(request)
        items = governance_query_service.list_for_actor(actor_context, view=governance_view)
        if domain_filter is not None:
            items = tuple(item for item in items if item.domain is domain_filter)
        response.headers["Cache-Control"] = "no-store"
        return GovernanceApprovalListResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            view=governance_view.value,
            items=tuple(GovernanceApprovalItemResponse.from_domain(item) for item in items),
        )

    @app.get(
        "/api/v1/governance/approval-requests/{approval_request_id}",
        response_model=GovernanceApprovalDetailResponse,
        tags=["governance"],
    )
    async def get_governance_approval_detail(
        approval_request_id: str, request: Request, response: Response
    ) -> GovernanceApprovalDetailResponse:
        stored = _command(governance_command_service, request).repository.get(
            approval_request_id
        )
        actor_context = resolver.resolve(request)
        if not is_trusted_actor_context(actor_context):
            raise HTTPException(status_code=404, detail="Governance request not found.")
        assert actor_context is not None
        if stored.scope_type == "DATASET":
            if stored.scope_id not in actor_context.permitted_dataset_ids:
                raise HTTPException(status_code=404, detail="Governance request not found.")
        elif stored.scope_type == "DATA_SOURCE":
            if (
                not actor_context.can_view_enterprise
                and stored.scope_id not in actor_context.permitted_source_ids
            ):
                raise HTTPException(status_code=404, detail="Governance request not found.")
        response.headers["Cache-Control"] = "no-store"
        return GovernanceApprovalDetailResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            item=GovernanceApprovalItemResponse.from_domain(center_request_to_item(stored)),
        )

    @app.post(
        "/api/v1/governance/approval-requests",
        response_model=GovernanceApprovalDetailResponse,
        status_code=201,
        tags=["governance"],
    )
    async def create_governance_approval_request(
        payload: GovernanceApprovalCreateRequest,
        request: Request,
        response: Response,
    ) -> GovernanceApprovalDetailResponse:
        command_service = _command(governance_command_service, request)
        actor_context = _mutation_actor(request, resolver)
        stored = command_service.submit_request(
            actor_context=actor_context,
            request_type=payload.request_type,
            object_id=payload.object_id,
            reason_code=payload.reason_code,
            new_owner_user_id=payload.new_owner_user_id,
            proposed_changes=payload.proposed_changes,
        )
        response.headers["Cache-Control"] = "no-store"
        return GovernanceApprovalDetailResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            item=GovernanceApprovalItemResponse.from_domain(center_request_to_item(stored)),
        )

    @app.post(
        "/api/v1/governance/approval-requests/{approval_request_id}/decision",
        response_model=GovernanceApprovalDetailResponse,
        tags=["governance"],
    )
    async def decide_governance_approval_request(
        approval_request_id: str,
        payload: GovernanceApprovalDecisionRequest,
        request: Request,
        response: Response,
    ) -> GovernanceApprovalDetailResponse:
        command_service = _command(governance_command_service, request)
        actor_context = _mutation_actor(request, resolver)
        stored = command_service.decide_request(
            actor_context=actor_context,
            approval_request_id=approval_request_id,
            decision=payload.decision,
            reason_code=payload.reason_code,
        )
        response.headers["Cache-Control"] = "no-store"
        return GovernanceApprovalDetailResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            item=GovernanceApprovalItemResponse.from_domain(center_request_to_item(stored)),
        )

    @app.post(
        "/api/v1/governance/approval-requests/{approval_request_id}/withdraw",
        response_model=GovernanceApprovalDetailResponse,
        tags=["governance"],
    )
    async def withdraw_governance_approval_request(
        approval_request_id: str,
        payload: GovernanceApprovalWithdrawRequest,
        request: Request,
        response: Response,
    ) -> GovernanceApprovalDetailResponse:
        command_service = _command(governance_command_service, request)
        actor_context = _mutation_actor(request, resolver)
        stored = command_service.withdraw_request(
            actor_context=actor_context,
            approval_request_id=approval_request_id,
            reason_code=payload.reason_code,
        )
        response.headers["Cache-Control"] = "no-store"
        return GovernanceApprovalDetailResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            item=GovernanceApprovalItemResponse.from_domain(center_request_to_item(stored)),
        )

    @app.post(
        "/api/v1/governance/approval-requests/{approval_request_id}/apply",
        response_model=GovernanceApprovalDetailResponse,
        tags=["governance"],
    )
    async def apply_governance_approval_request(
        approval_request_id: str,
        request: Request,
        response: Response,
    ) -> GovernanceApprovalDetailResponse:
        command_service = _command(governance_command_service, request)
        actor_context = _mutation_actor(request, resolver)
        stored = command_service.apply_request(
            actor_context=actor_context,
            approval_request_id=approval_request_id,
        )
        response.headers["Cache-Control"] = "no-store"
        return GovernanceApprovalDetailResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            item=GovernanceApprovalItemResponse.from_domain(center_request_to_item(stored)),
        )


def _command(
    governance_command_service: GovernanceApprovalCommandService | None,
    request: Request,
) -> GovernanceApprovalCommandService:
    if governance_command_service is None:
        raise GovernanceQueryTechnicalError(
            "Governance service is unavailable.", request.state.correlation_id
        )
    return governance_command_service


def _mutation_actor(request: Request, resolver: _Resolver) -> ActorContext | None:
    actor_context = getattr(request.state, "actor_context", None)
    if actor_context is None:
        actor_context = resolver.resolve(request)
    return actor_context
