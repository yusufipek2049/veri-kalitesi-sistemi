"""Sürümlü FastAPI dashboard taşıma katmanı."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from veri_kalitesi.api.bff import BffSessionBoundary, CSRF_HEADER_NAME
from veri_kalitesi.api.errors import (
    ApiAuthenticationError,
    ApiCsrfError,
    ApiSessionUnavailableError,
)
from veri_kalitesi.api.identity import ActorContextResolver, UnavailableActorContextResolver
from veri_kalitesi.api.models import DashboardSummaryResponse
from veri_kalitesi.dashboard import (
    DashboardAuthorizationError,
    DashboardQueryError,
    DashboardQueryService,
    DashboardValidationError,
)


def create_dashboard_api(
    dashboard_service: DashboardQueryService,
    *,
    actor_context_resolver: ActorContextResolver | None = None,
    bff_session_boundary: BffSessionBoundary | None = None,
    allowed_origins: Sequence[str] = (),
    data_origin: str = "runtime",
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
