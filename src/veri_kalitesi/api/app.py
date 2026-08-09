"""Sürümlü FastAPI dashboard taşıma katmanı."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from veri_kalitesi.api.bff import BffSessionBoundary, CSRF_HEADER_NAME
from veri_kalitesi.api.errors import (
    ApiAuthenticationError,
    ApiCsrfError,
    ApiSessionUnavailableError,
)
from veri_kalitesi.api.exception_handlers import problem as _problem, register_exception_handlers
from veri_kalitesi.api.identity import (
    ActorContextResolver,
    DevelopmentActorContextResolver,
    DevelopmentUserRegistry,
    UnavailableActorContextResolver,
)
from veri_kalitesi.api.models import DevelopmentUserInfoResponse, DevelopmentUserListResponse
from veri_kalitesi.api.data_sources_router import (
    DataSourceMutationService,
    register_data_sources_routes,
)
from veri_kalitesi.api.catalog_router import (
    CatalogQueryService as CatalogService,
    MetadataCommandService,
    register_catalog_routes,
)
from veri_kalitesi.api.rules_router import (
    RuleCreatorService,
    RuleMutationService,
    register_rules_routes,
)
from veri_kalitesi.api.issues_router import (
    IssueAssignmentService,
    IssueAssigneeOptionProvider,
    IssueClosureService,
    IssueCreationService,
    IssueInvestigationService,
    IssueResolutionService,
    IssueVerificationService,
    register_issues_routes,
)
from veri_kalitesi.api.executions_router import (
    ExecutionCancelService,
    ExecutionStartService,
    register_executions_routes,
)
from veri_kalitesi.api.scores_router import register_scores_routes
from veri_kalitesi.api.audit_router import register_audit_routes
from veri_kalitesi.api.notifications_router import register_notifications_routes
from veri_kalitesi.audit.service import AuditQueryService
from veri_kalitesi.data_sources.query import DataSourceQueryService
from veri_kalitesi.executions.query import ExecutionQueryService
from veri_kalitesi.identity import ActorContext
from veri_kalitesi.issues import IssueInvestigationEvidenceService, IssueQueryService
from veri_kalitesi.rules import RuleQueryService
from veri_kalitesi.scoring.query import ScoreQueryService


class StateChangeBoundary(Protocol):
    def protect_state_changing(self, request: Request) -> ActorContext | None: ...


def create_dashboard_api(
    *,
    actor_context_resolver: ActorContextResolver | None = None,
    bff_session_boundary: BffSessionBoundary | None = None,
    allowed_origins: Sequence[str] = (),
    data_origin: str = "runtime",
    data_source_query_service: DataSourceQueryService | None = None,
    data_source_mutation_service: DataSourceMutationService | None = None,
    execution_start_service: ExecutionStartService | None = None,
    execution_cancel_service: ExecutionCancelService | None = None,
    development_user_registry: DevelopmentUserRegistry | None = None,
    rule_query_service: RuleQueryService | None = None,
    execution_query_service: ExecutionQueryService | None = None,
    issue_query_service: IssueQueryService | None = None,
    issue_investigation_service: IssueInvestigationService | None = None,
    issue_investigation_evidence_service: IssueInvestigationEvidenceService | None = None,
    issue_assignment_service: IssueAssignmentService | None = None,
    issue_assignee_option_provider: IssueAssigneeOptionProvider | None = None,
    issue_resolution_service: IssueResolutionService | None = None,
    issue_verification_service: IssueVerificationService | None = None,
    issue_closure_service: IssueClosureService | None = None,
    issue_creation_service: IssueCreationService | None = None,
    rule_creator_service: RuleCreatorService | None = None,
    rule_mutation_service: RuleMutationService | None = None,
    audit_query_service: AuditQueryService | None = None,
    metadata_command_service: MetadataCommandService | None = None,
    catalog_query_service: CatalogService | None = None,
    score_query_service: ScoreQueryService | None = None,
    notification_query_service: object | None = None,
    notification_delivery_service: object | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> FastAPI:
    """Bağımlılıkları dışarıdan verilen, varsayılanı fail-closed API üretir."""

    if any(origin == "*" or not origin.strip() for origin in allowed_origins):
        raise ValueError("CORS origins must be explicit non-blank values.")
    if actor_context_resolver is not None and bff_session_boundary is not None:
        raise ValueError("Only one actor context resolver may be configured.")
    resolver = actor_context_resolver or bff_session_boundary or UnavailableActorContextResolver()
    app = FastAPI(
        title="Veri Kalitesi API",
        version="1.0.0",
        docs_url=None,
        redoc_url=None,
        openapi_url="/api/v1/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(allowed_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Accept", "Content-Type", CSRF_HEADER_NAME],
        expose_headers=["X-Correlation-ID", CSRF_HEADER_NAME],
    )

    @app.middleware("http")
    async def add_correlation_id(request: Request, call_next):  # type: ignore[no-untyped-def]
        request.state.correlation_id = str(uuid4())
        if request.method.upper() not in {"GET", "HEAD", "OPTIONS"}:
            state_change_boundary: StateChangeBoundary | None = bff_session_boundary
            if state_change_boundary is None and isinstance(
                resolver,
                DevelopmentActorContextResolver,
            ):
                state_change_boundary = resolver
            if state_change_boundary is None:
                return _problem(
                    request,
                    status=401,
                    title="Authentication required",
                    detail="A trusted user session is required.",
                    correlation_id=request.state.correlation_id,
                )
            try:
                actor_context = state_change_boundary.protect_state_changing(request)
                request.state.actor_context = actor_context
            except ApiCsrfError:
                return _problem(
                    request,
                    status=403,
                    title="Request rejected",
                    detail="The state-changing request could not be verified.",
                    correlation_id=request.state.correlation_id,
                )
            except ApiAuthenticationError:
                return _problem(
                    request,
                    status=401,
                    title="Authentication required",
                    detail="A trusted user session is required.",
                    correlation_id=request.state.correlation_id,
                )
            except ApiSessionUnavailableError:
                return _problem(
                    request,
                    status=503,
                    title="Session temporarily unavailable",
                    detail="The session request could not be completed.",
                    correlation_id=request.state.correlation_id,
                )
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = request.state.correlation_id
        return response

    register_exception_handlers(app)

    register_rules_routes(
        app,
        rule_query_service=rule_query_service,
        rule_creator_service=rule_creator_service,
        rule_mutation_service=rule_mutation_service,
        resolver=resolver,
        data_origin=data_origin,
    )
    register_issues_routes(
        app,
        issue_query_service=issue_query_service,
        issue_investigation_service=issue_investigation_service,
        issue_investigation_evidence_service=issue_investigation_evidence_service,
        issue_assignment_service=issue_assignment_service,
        issue_assignee_option_provider=issue_assignee_option_provider,
        issue_resolution_service=issue_resolution_service,
        issue_verification_service=issue_verification_service,
        issue_closure_service=issue_closure_service,
        issue_creation_service=issue_creation_service,
        resolver=resolver,
        data_origin=data_origin,
    )
    register_executions_routes(
        app,
        execution_query_service=execution_query_service,
        execution_start_service=execution_start_service,
        execution_cancel_service=execution_cancel_service,
        resolver=resolver,
        data_origin=data_origin,
    )
    register_scores_routes(
        app,
        score_query_service=score_query_service,
        resolver=resolver,
        data_origin=data_origin,
    )
    register_data_sources_routes(
        app,
        data_source_query_service=data_source_query_service,
        data_source_mutation_service=data_source_mutation_service,
        resolver=resolver,
        data_origin=data_origin,
    )
    register_audit_routes(
        app,
        audit_query_service=audit_query_service,
        resolver=resolver,
        data_origin=data_origin,
        clock=clock,
    )
    register_notifications_routes(
        app,
        notification_query_service=notification_query_service,
        notification_delivery_service=notification_delivery_service,
        resolver=resolver,
        data_origin=data_origin,
    )
    # ██████ Geliştirme Kullanıcıları ██████

    @app.get(
        "/api/v1/development/users",
        response_model=DevelopmentUserListResponse,
        tags=["development"],
    )
    async def list_development_users(request: Request) -> DevelopmentUserListResponse:
        if development_user_registry is None:
            return DevelopmentUserListResponse(
                correlation_id=request.state.correlation_id,
                items=(),
            )
        users = development_user_registry.available_users()
        return DevelopmentUserListResponse(
            correlation_id=request.state.correlation_id,
            items=tuple(
                DevelopmentUserInfoResponse(
                    user_id=u["user_id"],
                    display_name=u["display_name"],
                    roles=u["roles"],
                )
                for u in users
            ),
        )

    register_catalog_routes(
        app,
        metadata_command_service=metadata_command_service,
        catalog_query_service=catalog_query_service,
        resolver=resolver,
        data_origin=data_origin,
    )

    return app
