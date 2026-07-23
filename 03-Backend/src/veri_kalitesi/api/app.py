"""Sürümlü FastAPI dashboard taşıma katmanı."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import uuid4

from fastapi import FastAPI, Query as FastApiQuery, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from veri_kalitesi.api.bff import BffSessionBoundary, CSRF_HEADER_NAME
from veri_kalitesi.api.errors import (
    ApiAuthenticationError,
    ApiCsrfError,
    ApiSessionUnavailableError,
)
from veri_kalitesi.api.identity import ActorContextResolver, UnavailableActorContextResolver
from veri_kalitesi.api.models import (
    AuditEventListResponse,
    DashboardSummaryResponse,
    DataSourceListItemResponse,
    DataSourceListResponse,
    ExecutionListItemResponse,
    ExecutionListResponse,
    IssueListItemResponse,
    IssueListResponse,
    ReportSummaryResponse,
    RuleListItemResponse,
    RuleListResponse,
)
from veri_kalitesi.audit import (
    AuditQuery,
    AuditQueryAuthorizationError,
    AuditQueryService,
    AuditQueryTechnicalError,
    AuditQueryValidationError,
    AuditResult,
)
from veri_kalitesi.data_sources import (
    DataSourceQueryAuthorizationError,
    DataSourceQueryService,
    DataSourceQueryTechnicalError,
)
from veri_kalitesi.dashboard import (
    DashboardAuthorizationError,
    DashboardQueryError,
    DashboardQueryService,
    DashboardValidationError,
)
from veri_kalitesi.executions import (
    ExecutionQueryAuthorizationError,
    ExecutionQueryService,
    ExecutionQueryTechnicalError,
)
from veri_kalitesi.issues import (
    IssueQueryAuthorizationError,
    IssueQueryService,
    IssueQueryTechnicalError,
)
from veri_kalitesi.rules import (
    RuleQueryAuthorizationError,
    RuleQueryService,
    RuleQueryTechnicalError,
)
from veri_kalitesi.reporting import (
    ReportAuthorizationError,
    ReportPreviewRequest,
    ReportPreviewService,
    ReportTechnicalError,
    ReportValidationError,
)


def create_dashboard_api(
    dashboard_service: DashboardQueryService,
    *,
    actor_context_resolver: ActorContextResolver | None = None,
    bff_session_boundary: BffSessionBoundary | None = None,
    allowed_origins: Sequence[str] = (),
    data_origin: str = "runtime",
    data_source_query_service: DataSourceQueryService | None = None,
    rule_query_service: RuleQueryService | None = None,
    execution_query_service: ExecutionQueryService | None = None,
    issue_query_service: IssueQueryService | None = None,
    report_preview_service: ReportPreviewService | None = None,
    audit_query_service: AuditQueryService | None = None,
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
            if bff_session_boundary is None:
                return _problem(
                    request,
                    status=401,
                    title="Authentication required",
                    detail="A trusted user session is required.",
                    correlation_id=request.state.correlation_id,
                )
            try:
                bff_session_boundary.protect_state_changing(request)
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

    @app.exception_handler(ApiAuthenticationError)
    async def handle_authentication_error(
        request: Request, error: ApiAuthenticationError
    ) -> JSONResponse:
        return _problem(
            request,
            status=401,
            title="Authentication required",
            detail="A trusted user session is required.",
            correlation_id=error.correlation_id,
        )

    @app.exception_handler(DashboardAuthorizationError)
    async def handle_authorization_error(
        request: Request, error: DashboardAuthorizationError
    ) -> JSONResponse:
        return _problem(
            request,
            status=403,
            title="Access denied",
            detail="The requested dashboard scope is not available.",
            correlation_id=error.correlation_id,
        )

    @app.exception_handler(DataSourceQueryAuthorizationError)
    async def handle_data_source_authorization_error(
        request: Request, error: DataSourceQueryAuthorizationError
    ) -> JSONResponse:
        return _problem(
            request,
            status=403,
            title="Access denied",
            detail="The requested data source scope is not available.",
            correlation_id=error.correlation_id,
        )

    @app.exception_handler(DataSourceQueryTechnicalError)
    async def handle_data_source_query_error(
        request: Request, error: DataSourceQueryTechnicalError
    ) -> JSONResponse:
        return _problem(
            request,
            status=503,
            title="Data sources temporarily unavailable",
            detail="The data source query could not be completed.",
            correlation_id=error.correlation_id,
        )

    @app.exception_handler(RuleQueryAuthorizationError)
    async def handle_rule_authorization_error(
        request: Request, error: RuleQueryAuthorizationError
    ) -> JSONResponse:
        return _problem(
            request,
            status=403,
            title="Access denied",
            detail="The requested rule scope is not available.",
            correlation_id=error.correlation_id,
        )

    @app.exception_handler(RuleQueryTechnicalError)
    async def handle_rule_query_error(
        request: Request, error: RuleQueryTechnicalError
    ) -> JSONResponse:
        return _problem(
            request,
            status=503,
            title="Rules temporarily unavailable",
            detail="The rule query could not be completed.",
            correlation_id=error.correlation_id,
        )

    @app.exception_handler(ExecutionQueryAuthorizationError)
    async def handle_execution_authorization_error(
        request: Request, error: ExecutionQueryAuthorizationError
    ) -> JSONResponse:
        return _problem(
            request,
            status=403,
            title="Access denied",
            detail="The requested execution scope is not available.",
            correlation_id=error.correlation_id,
        )

    @app.exception_handler(ExecutionQueryTechnicalError)
    async def handle_execution_query_error(
        request: Request, error: ExecutionQueryTechnicalError
    ) -> JSONResponse:
        return _problem(
            request,
            status=503,
            title="Executions temporarily unavailable",
            detail="The execution query could not be completed.",
            correlation_id=error.correlation_id,
        )

    @app.exception_handler(IssueQueryAuthorizationError)
    async def handle_issue_authorization_error(
        request: Request, error: IssueQueryAuthorizationError
    ) -> JSONResponse:
        return _problem(
            request,
            status=403,
            title="Access denied",
            detail="The requested issue scope is not available.",
            correlation_id=error.correlation_id,
        )

    @app.exception_handler(IssueQueryTechnicalError)
    async def handle_issue_query_error(
        request: Request, error: IssueQueryTechnicalError
    ) -> JSONResponse:
        return _problem(
            request,
            status=503,
            title="Issues temporarily unavailable",
            detail="The issue query could not be completed.",
            correlation_id=error.correlation_id,
        )

    @app.exception_handler(ReportAuthorizationError)
    async def handle_report_authorization_error(
        request: Request, error: ReportAuthorizationError
    ) -> JSONResponse:
        return _problem(
            request,
            status=403,
            title="Access denied",
            detail="The requested report scope is not available.",
            correlation_id=error.correlation_id,
        )

    @app.exception_handler(ReportTechnicalError)
    async def handle_report_technical_error(
        request: Request, error: ReportTechnicalError
    ) -> JSONResponse:
        return _problem(
            request,
            status=503,
            title="Reports temporarily unavailable",
            detail="The report preview could not be completed.",
            correlation_id=error.correlation_id,
        )

    @app.exception_handler(ReportValidationError)
    async def handle_report_validation_error(
        request: Request, error: ReportValidationError
    ) -> JSONResponse:
        return _problem(
            request,
            status=503,
            title="Reports temporarily unavailable",
            detail="The report preview could not be completed.",
            correlation_id=request.state.correlation_id,
        )

    @app.exception_handler(AuditQueryAuthorizationError)
    async def handle_audit_authorization_error(
        request: Request, error: AuditQueryAuthorizationError
    ) -> JSONResponse:
        return _problem(
            request,
            status=403,
            title="Access denied",
            detail="The requested audit scope is not available.",
            correlation_id=error.correlation_id,
        )

    @app.exception_handler(AuditQueryTechnicalError)
    async def handle_audit_technical_error(
        request: Request, error: AuditQueryTechnicalError
    ) -> JSONResponse:
        return _problem(
            request,
            status=503,
            title="Audit records temporarily unavailable",
            detail="The audit query could not be completed.",
            correlation_id=error.correlation_id,
        )

    @app.exception_handler(AuditQueryValidationError)
    async def handle_audit_validation_error(
        request: Request, error: AuditQueryValidationError
    ) -> JSONResponse:
        return _problem(
            request,
            status=400,
            title="Invalid request",
            detail="The audit query could not be validated.",
            correlation_id=request.state.correlation_id,
        )

    @app.exception_handler(ApiSessionUnavailableError)
    async def handle_session_unavailable_error(
        request: Request, error: ApiSessionUnavailableError
    ) -> JSONResponse:
        return _problem(
            request,
            status=503,
            title="Session temporarily unavailable",
            detail="The session request could not be completed.",
            correlation_id=error.correlation_id,
        )

    @app.exception_handler(DashboardValidationError)
    async def handle_validation_error(
        request: Request, error: DashboardValidationError
    ) -> JSONResponse:
        return _problem(
            request,
            status=400,
            title="Invalid request",
            detail="The dashboard request could not be validated.",
            correlation_id=request.state.correlation_id,
        )

    @app.exception_handler(DashboardQueryError)
    async def handle_query_error(request: Request, error: DashboardQueryError) -> JSONResponse:
        return _problem(
            request,
            status=503,
            title="Dashboard temporarily unavailable",
            detail="The dashboard query could not be completed.",
            correlation_id=error.correlation_id,
        )

    @app.get(
        "/api/v1/dashboard/summary",
        response_model=DashboardSummaryResponse,
        tags=["dashboard"],
    )
    async def get_dashboard_summary(
        request: Request, response: Response
    ) -> DashboardSummaryResponse:
        actor_context = resolver.resolve(request)
        overview = dashboard_service.get_overview(actor_context)
        response.headers["Cache-Control"] = "no-store"
        return DashboardSummaryResponse.from_domain(
            overview,
            correlation_id=request.state.correlation_id,
            data_origin=data_origin,
        )

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
        sources = data_source_query_service.list_for_actor(actor_context)
        response.headers["Cache-Control"] = "no-store"
        return DataSourceListResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            items=tuple(DataSourceListItemResponse.from_domain(source) for source in sources),
        )

    @app.get(
        "/api/v1/rules",
        response_model=RuleListResponse,
        tags=["rules"],
    )
    async def get_rules(request: Request, response: Response) -> RuleListResponse:
        if rule_query_service is None:
            raise RuleQueryTechnicalError(
                "Rule service is unavailable.", request.state.correlation_id
            )
        actor_context = resolver.resolve(request)
        rules = rule_query_service.list_for_actor(actor_context)
        response.headers["Cache-Control"] = "no-store"
        return RuleListResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            items=tuple(RuleListItemResponse.from_domain(rule, version) for rule, version in rules),
        )

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
        "/api/v1/issues",
        response_model=IssueListResponse,
        tags=["issues"],
    )
    async def get_issues(request: Request, response: Response) -> IssueListResponse:
        if issue_query_service is None:
            raise IssueQueryTechnicalError(
                "Issue service is unavailable.", request.state.correlation_id
            )
        actor_context = resolver.resolve(request)
        issues = issue_query_service.list_for_actor(actor_context)
        response.headers["Cache-Control"] = "no-store"
        return IssueListResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            limit=issue_query_service.page_limit,
            items=tuple(IssueListItemResponse.from_domain(issue) for issue in issues),
        )

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

    @app.post("/api/v1/session/logout", status_code=204, tags=["session"])
    async def logout(request: Request, response: Response) -> Response:
        if bff_session_boundary is None:
            raise ApiAuthenticationError(
                "Authenticated session could not be established.",
                request.state.correlation_id,
            )
        bff_session_boundary.logout(request, response)
        response.status_code = 204
        return response

    return app


def _problem(
    request: Request,
    *,
    status: int,
    title: str,
    detail: str,
    correlation_id: str,
) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        media_type="application/problem+json",
        content={
            "type": "about:blank",
            "title": title,
            "status": status,
            "detail": detail,
            "instance": request.url.path,
            "correlation_id": correlation_id,
        },
        headers={"X-Correlation-ID": correlation_id, "Cache-Control": "no-store"},
    )
