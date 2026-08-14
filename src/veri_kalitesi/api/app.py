"""Sürümlü FastAPI dashboard taşıma katmanı."""

from __future__ import annotations

import logging
from typing import cast
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from veri_kalitesi.api.bff import CSRF_HEADER_NAME
from veri_kalitesi.api.errors import (
    ApiAuthenticationError,
    ApiCsrfError,
    ApiSessionUnavailableError,
)
from veri_kalitesi.api.exception_handlers import problem as _problem, register_exception_handlers
from veri_kalitesi.api.identity import (
    DevelopmentActorContextResolver,
    UnavailableActorContextResolver,
)
from veri_kalitesi.api.models import DevelopmentUserInfoResponse, DevelopmentUserListResponse
from veri_kalitesi.api.data_sources_router import register_data_sources_routes
from veri_kalitesi.api.catalog_router import register_catalog_routes
from veri_kalitesi.api.rules_router import register_rules_routes
from veri_kalitesi.api.issues_router import register_issues_routes
from veri_kalitesi.api.executions_router import register_executions_routes
from veri_kalitesi.api.scores_router import register_scores_routes
from veri_kalitesi.api.dashboard_router import register_dashboard_routes
from veri_kalitesi.api.audit_router import register_audit_routes
from veri_kalitesi.api.notifications_router import register_notifications_routes
from veri_kalitesi.api.health import register_health_routes
from veri_kalitesi.api.reporting_router import register_reporting_routes
from veri_kalitesi.operational_logging import bind_correlation_id, reset_correlation_id
from veri_kalitesi.api.service_groups import (
    ActorResolverIdentity,
    ApiIdentity,
    ApiOptions,
    AuditServices,
    BffSessionIdentity,
    CatalogDatasetReader,
    CatalogServices,
    DataSourceServices,
    ExecutionServices,
    IssueServices,
    JobQueueReader,
    NotificationServices,
    ReportingServices,
    RuleServices,
    StateChangeBoundary,
)

CORS_ALLOWED_METHODS = ("GET", "POST", "PATCH", "PUT")
logger = logging.getLogger(__name__)


class CatalogDatasetResolver:
    """CatalogReader'yi DatasetResolver protokolune uyarlayan adapter.

    CatalogReader'dan get_data_source ve list_datasets cagirilarak
    execution source_ids'inin dataset/kaynak isimlerine cozumlenmesini saglar.
    """

    def __init__(self, reader: CatalogDatasetReader) -> None:
        self._reader = reader

    def get_data_source_name(self, data_source_id: str) -> str | None:
        try:
            source = self._reader.get_data_source(data_source_id)
            return str(source.name)
        except Exception:
            return None

    def list_datasets_for_source(self, data_source_id: str) -> list[dict[str, str]]:
        try:
            datasets = self._reader.list_datasets(data_source_id)
            return [
                {
                    "dataset_id": ds.dataset_id,
                    "name": ds.name,
                    "namespace": ds.namespace,
                }
                for ds in datasets
            ]
        except Exception:
            return []


class JobQueueInfoResolver:
    """Job queue repository'yi JobInfoResolver protokolune uyarlayan adapter.

    execution_id = job_id iliskisi uzerinden job detaylarini getirir.
    """

    def __init__(self, repository: JobQueueReader) -> None:
        self._repository = repository

    def get_job_info(self, job_id: str) -> dict | None:
        try:
            job = self._repository.get_by_id(job_id)
        except Exception:
            return None
        if job is None:
            return None
        return {
            "job_id": job.job_id,
            "status": job.status.value,
            "worker_id": job.claimed_by,
            "leased_until": job.lease_expires_at,
            "attempt_count": job.attempt_count,
            "last_error_class": job.last_error_class,
            "completed_at": job.completed_at,
            "completion_outcome": (
                job.completion_outcome.value if job.completion_outcome else None
            ),
        }


def create_dashboard_api(
    *,
    identity: ApiIdentity | None = None,
    options: ApiOptions = ApiOptions(),
    data_sources: DataSourceServices | None = None,
    executions: ExecutionServices | None = None,
    rules: RuleServices | None = None,
    issues: IssueServices | None = None,
    catalog: CatalogServices | None = None,
    audit: AuditServices | None = None,
    notifications: NotificationServices | None = None,
    reporting: ReportingServices | None = None,
) -> FastAPI:
    """Bağımlılıkları dışarıdan verilen, varsayılanı fail-closed API üretir."""

    if any(origin == "*" or not origin.strip() for origin in options.allowed_origins):
        raise ValueError("CORS origins must be explicit non-blank values.")
    if isinstance(identity, ActorResolverIdentity):
        resolver = identity.resolver
        bff_session_boundary: StateChangeBoundary | None = None
    elif isinstance(identity, BffSessionIdentity):
        resolver = identity.boundary
        bff_session_boundary = identity.boundary
    else:
        resolver = UnavailableActorContextResolver()
        bff_session_boundary = None
    app = FastAPI(
        title="Veri Kalitesi API",
        version="1.0.0",
        docs_url=None,
        redoc_url=None,
        openapi_url="/api/v1/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(options.allowed_origins),
        allow_credentials=True,
        allow_methods=CORS_ALLOWED_METHODS,
        allow_headers=["Accept", "Content-Type", CSRF_HEADER_NAME],
        expose_headers=["X-Correlation-ID", CSRF_HEADER_NAME],
    )

    @app.middleware("http")
    async def add_correlation_id(request: Request, call_next):  # type: ignore[no-untyped-def]
        request.state.correlation_id = str(uuid4())
        token = bind_correlation_id(request.state.correlation_id)
        status_code = 500
        logger.info(
            "Request started",
            extra={"event": "request_started", "method": request.method, "path": request.url.path},
        )
        try:
            if request.method.upper() not in {"GET", "HEAD", "OPTIONS"}:
                state_change_boundary: StateChangeBoundary | None = bff_session_boundary
                if state_change_boundary is None and isinstance(
                    resolver,
                    DevelopmentActorContextResolver,
                ):
                    state_change_boundary = resolver
                if state_change_boundary is None:
                    response = _problem(
                        request,
                        status=401,
                        title="Authentication required",
                        detail="A trusted user session is required.",
                        correlation_id=request.state.correlation_id,
                    )
                else:
                    try:
                        actor_context = state_change_boundary.protect_state_changing(request)
                        request.state.actor_context = actor_context
                    except ApiCsrfError:
                        response = _problem(
                            request,
                            status=403,
                            title="Request rejected",
                            detail="The state-changing request could not be verified.",
                            correlation_id=request.state.correlation_id,
                        )
                    except ApiAuthenticationError:
                        response = _problem(
                            request,
                            status=401,
                            title="Authentication required",
                            detail="A trusted user session is required.",
                            correlation_id=request.state.correlation_id,
                        )
                    except ApiSessionUnavailableError:
                        response = _problem(
                            request,
                            status=503,
                            title="Session temporarily unavailable",
                            detail="The session request could not be completed.",
                            correlation_id=request.state.correlation_id,
                        )
                    else:
                        response = await call_next(request)
            else:
                response = await call_next(request)
            if request.method.upper() in {"GET", "HEAD"} and isinstance(
                resolver, DevelopmentActorContextResolver
            ):
                response.headers[CSRF_HEADER_NAME] = resolver.request_proof
            response.headers["X-Correlation-ID"] = request.state.correlation_id
            status_code = response.status_code
            return response
        finally:
            logger.info(
                "Request completed",
                extra={
                    "event": "request_completed",
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                },
            )
            reset_correlation_id(token)

    register_exception_handlers(app)
    register_health_routes(app, readiness_check=options.readiness_check)

    register_rules_routes(
        app,
        rule_query_service=rules.query if rules is not None else None,
        rule_creator_service=rules.creator if rules is not None else None,
        rule_mutation_service=rules.mutation if rules is not None else None,
        resolver=resolver,
        data_origin=options.data_origin,
    )
    _catalog_reader = cast(
        CatalogDatasetReader | None,
        getattr(catalog.query, "reader", None) if catalog is not None and catalog.query else None,
    )
    register_issues_routes(
        app,
        issue_query_service=issues.query if issues is not None else None,
        issue_investigation_service=issues.investigation if issues is not None else None,
        issue_investigation_evidence_service=(
            issues.investigation_evidence if issues is not None else None
        ),
        issue_assignment_service=issues.assignment if issues is not None else None,
        issue_assignee_option_provider=issues.assignee_options if issues is not None else None,
        issue_resolution_service=issues.resolution if issues is not None else None,
        issue_verification_service=issues.verification if issues is not None else None,
        issue_closure_service=issues.closure if issues is not None else None,
        issue_creation_service=issues.creation if issues is not None else None,
        resolver=resolver,
        data_origin=options.data_origin,
        catalog_reader=_catalog_reader,
    )
    register_executions_routes(
        app,
        execution_query_service=executions.query if executions is not None else None,
        execution_start_service=executions.start if executions is not None else None,
        execution_cancel_service=executions.cancel if executions is not None else None,
        rule_version_catalog=rules.query if rules is not None else None,
        dataset_resolver=(
            CatalogDatasetResolver(_catalog_reader) if _catalog_reader is not None else None
        ),
        job_info_resolver=(
            JobQueueInfoResolver(executions.job_queue)
            if executions is not None and executions.job_queue is not None
            else None
        ),
        resolver=resolver,
        data_origin=options.data_origin,
    )
    register_scores_routes(
        app,
        score_query_service=catalog.score_query if catalog is not None else None,
        resolver=resolver,
        data_origin=options.data_origin,
        catalog_reader=_catalog_reader,
        rule_version_reader=rules.query if rules is not None else None,
    )
    register_dashboard_routes(
        app,
        dashboard_query_service=catalog.dashboard_query if catalog is not None else None,
        resolver=resolver,
        data_origin=options.data_origin,
    )
    register_data_sources_routes(
        app,
        data_source_query_service=data_sources.query if data_sources is not None else None,
        data_source_mutation_service=data_sources.mutation if data_sources is not None else None,
        resolver=resolver,
        data_origin=options.data_origin,
    )
    register_audit_routes(
        app,
        audit_query_service=audit.query if audit is not None else None,
        resolver=resolver,
        data_origin=options.data_origin,
        clock=options.clock,
    )
    register_notifications_routes(
        app,
        notification_query_service=notifications.query if notifications is not None else None,
        notification_delivery_service=(
            notifications.delivery if notifications is not None else None
        ),
        resolver=resolver,
        data_origin=options.data_origin,
    )
    register_reporting_routes(
        app,
        report_query_service=reporting.query if reporting is not None else None,
        resolver=resolver,
        data_origin=options.data_origin,
    )
    # ██████ Geliştirme Kullanıcıları ██████

    @app.get(
        "/api/v1/development/users",
        response_model=DevelopmentUserListResponse,
        tags=["development"],
    )
    async def list_development_users(request: Request) -> DevelopmentUserListResponse:
        if options.development_user_registry is None:
            return DevelopmentUserListResponse(
                correlation_id=request.state.correlation_id,
                items=(),
            )
        users = options.development_user_registry.available_users()
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
        metadata_command_service=catalog.metadata_command if catalog is not None else None,
        catalog_query_service=catalog.query if catalog is not None else None,
        resolver=resolver,
        data_origin=options.data_origin,
        score_query_service=catalog.score_query if catalog is not None else None,
    )

    return app
