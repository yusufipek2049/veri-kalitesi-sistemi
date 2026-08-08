"""Merkezi exception-handler kaydı — problem-details (RFC 7807) yanıtları."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from veri_kalitesi.api.data_source_commands import DataSourceCommandError
from veri_kalitesi.api.errors import (
    ApiAuthenticationError,
    ApiSessionUnavailableError,
)
from veri_kalitesi.audit.errors import (
    AuditQueryAuthorizationError,
    AuditQueryTechnicalError,
    AuditQueryValidationError,
)
from veri_kalitesi.dashboard import (
    DashboardAuthorizationError,
    DashboardQueryError,
    DashboardValidationError,
)
from veri_kalitesi.data_sources.query import (
    DataSourceConflictError,
    DataSourceNotFoundError,
    DataSourceQueryAuthorizationError,
    DataSourceQueryTechnicalError,
    DataSourceQueryValidationError,
)
from veri_kalitesi.data_sources.errors import (
    AuthorizationError as DataSourceAuthorizationError,
    ConflictError as DataSourceConflictDomainError,
    NotFoundError as DataSourceNotFoundErrorDomain,
    TechnicalError as DataSourceTechnicalError,
    ValidationError as DataSourceDomainValidationError,
)
from veri_kalitesi.executions.errors import (
    ExecutionConflictError,
    ExecutionNotFoundError,
)
from veri_kalitesi.executions.query import (
    ExecutionQueryAuthorizationError,
    ExecutionQueryError,
    ExecutionQueryTechnicalError,
)
from veri_kalitesi.executions.query import (
    ExecutionNotFoundError as ExecutionScopeNotFoundError,
)
from veri_kalitesi.issues import (
    IssueAssignmentError,
    IssueAuthorizationError,
    IssueConflictError,
    IssueNotFoundError,
    IssueNotificationConfigurationError,
    IssueNotificationTechnicalError,
    IssueQueryAuthorizationError,
    IssueQueryTechnicalError,
    IssueTechnicalError,
    IssueValidationError,
)
from veri_kalitesi.reporting import (
    ReportAuthorizationError,
    ReportExportDeniedError,
    ReportExpiredError,
    ReportNotFoundError,
    ReportNotReadyError,
    ReportTechnicalError,
    ReportValidationError,
)
from veri_kalitesi.scoring.errors import (
    ScoreNotFoundError,
    ScorePublicationError,
    ScoreReproductionError,
    ScoringAuthorizationError,
    ScoringConflictError,
    ScoringValidationError,
)
from veri_kalitesi.rules import (
    RuleQueryAuthorizationError,
    RuleQueryTechnicalError,
)


# ── Problem-details helpers ──────────────────────────────────────────


def problem(
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


def command_problem(
    request: Request,
    *,
    status: int,
    code: str,
    detail: str,
    correlation_id: str,
) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        media_type="application/problem+json",
        content={
            "type": "about:blank",
            "title": "Data source command failed",
            "status": status,
            "code": code,
            "detail": detail,
            "instance": request.url.path,
            "correlation_id": correlation_id,
        },
        headers={"X-Correlation-ID": correlation_id, "Cache-Control": "no-store"},
    )


# ── Data-driven handler table ────────────────────────────────────────
# Each entry: (ExceptionClass, status_code, title, detail)
# ``detail`` may be a fixed string or ``None`` to use ``str(error)``.
# ``correlation_id`` is read from ``error.correlation_id`` when available,
# otherwise from ``request.state.correlation_id``.

_SIMPLE_HANDLERS: list[tuple[type[Exception], int, str, str | None]] = [
    # Cross-cutting
    (ApiAuthenticationError, 401, "Authentication required", "A trusted user session is required."),
    (
        ApiSessionUnavailableError,
        503,
        "Session temporarily unavailable",
        "The session request could not be completed.",
    ),
    # Dashboard
    (
        DashboardAuthorizationError,
        403,
        "Access denied",
        "The requested dashboard scope is not available.",
    ),
    (
        DashboardValidationError,
        400,
        "Invalid request",
        "The dashboard request could not be validated.",
    ),
    (
        DashboardQueryError,
        503,
        "Dashboard temporarily unavailable",
        "The dashboard query could not be completed.",
    ),
    # Data sources — query
    (
        DataSourceQueryAuthorizationError,
        403,
        "Access denied",
        "The requested data source scope is not available.",
    ),
    (
        DataSourceQueryTechnicalError,
        503,
        "Data sources temporarily unavailable",
        "The data source query could not be completed.",
    ),
    (
        DataSourceQueryValidationError,
        400,
        "Invalid request",
        "The profile comparison request could not be validated.",
    ),
    (
        DataSourceNotFoundError,
        404,
        "Data source not found",
        "The requested data source is not available.",
    ),
    (
        DataSourceConflictError,
        409,
        "Data source conflict",
        "The data source is not in a state that allows this action.",
    ),
    # Data sources — domain
    (
        DataSourceAuthorizationError,
        403,
        "Access denied",
        "The requested metadata action is not permitted.",
    ),
    (DataSourceNotFoundErrorDomain, 404, "Not found", "The requested resource was not found."),
    (DataSourceConflictDomainError, 409, "Conflict", "The resource state has changed."),
    (
        DataSourceDomainValidationError,
        422,
        "Validation failed",
        "The request failed domain validation.",
    ),
    (
        DataSourceTechnicalError,
        503,
        "Service temporarily unavailable",
        "The service is temporarily unavailable.",
    ),
    # Rules
    (
        RuleQueryAuthorizationError,
        403,
        "Access denied",
        "The requested rule scope is not available.",
    ),
    (
        RuleQueryTechnicalError,
        503,
        "Rules temporarily unavailable",
        "The rule query could not be completed.",
    ),
    # Executions
    (
        ExecutionQueryAuthorizationError,
        403,
        "Access denied",
        "The requested execution scope is not available.",
    ),
    (
        ExecutionQueryTechnicalError,
        503,
        "Executions temporarily unavailable",
        "The execution query could not be completed.",
    ),
    (
        ExecutionNotFoundError,
        404,
        "Execution not found",
        "The requested execution is not available.",
    ),
    (
        ExecutionScopeNotFoundError,
        404,
        "Execution not found",
        "The requested execution is not available.",
    ),
    (
        ExecutionQueryError,
        503,
        "Execution query failed",
        "The execution query could not be completed.",
    ),
    (
        ExecutionConflictError,
        409,
        "Execution conflict",
        "The execution is no longer in a state that allows this action.",
    ),
    # Issues — query
    (
        IssueQueryAuthorizationError,
        403,
        "Access denied",
        "The requested issue scope is not available.",
    ),
    (
        IssueQueryTechnicalError,
        503,
        "Issues temporarily unavailable",
        "The issue query could not be completed.",
    ),
    # Issues — mutation
    (
        IssueAuthorizationError,
        403,
        "Issue action denied",
        "The requested issue action is not available.",
    ),
    (IssueNotFoundError, 404, "Issue not found", "The requested issue is not available."),
    (
        IssueConflictError,
        409,
        "Issue changed",
        "The issue was changed by another operation. Reload and try again.",
    ),
    (
        IssueValidationError,
        409,
        "Issue action unavailable",
        "The issue is no longer in a state that allows this action.",
    ),
    (
        IssueAssignmentError,
        409,
        "Issue assignment unavailable",
        "The selected assignee is not available for this issue.",
    ),
    (
        IssueNotificationTechnicalError,
        503,
        "Issue notification delayed",
        "The assignment was saved, but its notification could not be completed.",
    ),
    (
        IssueNotificationConfigurationError,
        503,
        "Issue notification unavailable",
        "The assignment was saved, but its notification policy is unavailable.",
    ),
    (
        IssueTechnicalError,
        503,
        "Issue action temporarily unavailable",
        "The issue action could not be completed.",
    ),
    # Reports
    (
        ReportAuthorizationError,
        403,
        "Access denied",
        "The requested report scope is not available.",
    ),
    (
        ReportTechnicalError,
        503,
        "Reports temporarily unavailable",
        "The report preview could not be completed.",
    ),
    (
        ReportValidationError,
        503,
        "Reports temporarily unavailable",
        "The report preview could not be completed.",
    ),
    (ReportNotFoundError, 404, "Report not found", "The requested report does not exist."),
    (ReportExportDeniedError, 403, "Export denied", "Report export denied by policy."),
    (ReportExpiredError, 410, "Report expired", "The report download link has expired."),
    # Audit
    (
        AuditQueryAuthorizationError,
        403,
        "Access denied",
        "The requested audit scope is not available.",
    ),
    (
        AuditQueryTechnicalError,
        503,
        "Audit records temporarily unavailable",
        "The audit query could not be completed.",
    ),
    (AuditQueryValidationError, 400, "Invalid request", "The audit query could not be validated."),
    # Scores
    (ScoreNotFoundError, 404, "Score not found", "The requested score is not available."),
    (
        ScoringAuthorizationError,
        403,
        "Access denied",
        "The requested score scope is not available.",
    ),
    (ScoringConflictError, 409, "Score conflict", None),
    (ScorePublicationError, 422, "Score publication failed", None),
    (ScoreReproductionError, 422, "Score reproduction failed", None),
    (ScoringValidationError, 400, "Invalid request", None),
]


def _correlation_id(error: Exception, request: Request) -> str:
    return getattr(error, "correlation_id", None) or request.state.correlation_id


def register_exception_handlers(app: FastAPI) -> None:
    """Register all domain exception handlers on *app*."""

    # ── Simple problem-details handlers ──
    for exc_cls, status, title, fixed_detail in _SIMPLE_HANDLERS:

        def _make_handler(
            _status: int,
            _title: str,
            _fixed_detail: str | None,
        ):
            async def _handler(request: Request, error: Exception) -> JSONResponse:
                detail = _fixed_detail if _fixed_detail is not None else str(error)
                return problem(
                    request,
                    status=_status,
                    title=_title,
                    detail=detail,
                    correlation_id=_correlation_id(error, request),
                )

            return _handler

        app.exception_handler(exc_cls)(
            _make_handler(status, title, fixed_detail),
        )

    # ── ReportNotReadyError (uses error.status in detail) ──
    @app.exception_handler(ReportNotReadyError)
    async def handle_report_not_ready(request: Request, error: ReportNotReadyError) -> JSONResponse:
        return problem(
            request,
            status=409,
            title="Report not ready",
            detail=f"The report is {error.status}.",
            correlation_id=_correlation_id(error, request),
        )

    # ── DataSourceCommandError (uses _command_problem with code lookup) ──
    @app.exception_handler(DataSourceCommandError)
    async def handle_data_source_command_error(
        request: Request, error: DataSourceCommandError
    ) -> JSONResponse:
        status_by_category = {
            "authorization": 403,
            "not_found": 404,
            "conflict": 409,
            "validation": 422,
            "technical": 503,
        }
        safe_detail_by_code = {
            "DATA_SOURCE_PERMISSION_DENIED": (
                "You are not allowed to perform this data source action."
            ),
            "DATA_SOURCE_MAKER_CHECKER_VIOLATION": (
                "The requester cannot decide the same activation request."
            ),
            "DATA_SOURCE_NOT_FOUND": "The requested data source was not found.",
            "ACTIVATION_REQUEST_NOT_FOUND": "The activation request was not found.",
            "DATA_SOURCE_STATE_CONFLICT": ("The data source state no longer allows this action."),
            "DATA_SOURCE_REVISION_CONFLICT": ("The data source revision has changed."),
            "DATA_SOURCE_DECISION_CONFLICT": (
                "The activation request already has a different decision."
            ),
            "DATA_SOURCE_PENDING_ACTIVATION_EXISTS": (
                "A pending activation request already exists."
            ),
            "DATA_SOURCE_POLICY_CONFLICT": ("The data source command policy has changed."),
            "DATA_SOURCE_ACTIVATION_EXPIRED": "The activation request has expired.",
            "DATA_SOURCE_DOMAIN_VALIDATION_FAILED": (
                "The data source request violates a domain rule."
            ),
            "DATA_SOURCE_PERSISTENCE_UNAVAILABLE": (
                "The data source store is temporarily unavailable."
            ),
            "DATA_SOURCE_SERVICE_UNAVAILABLE": (
                "The data source service is temporarily unavailable."
            ),
            "DATA_SOURCE_SECRET_UNAVAILABLE": (
                "The referenced credential is temporarily unavailable."
            ),
            "DATA_SOURCE_AUDIT_UNAVAILABLE": ("The audit record could not be completed."),
        }
        status = status_by_category.get(error.category, 503)
        return command_problem(
            request,
            status=status,
            code=error.code,
            detail=safe_detail_by_code.get(
                error.code,
                "The data source action could not be completed safely.",
            ),
            correlation_id=_correlation_id(error, request),
        )

    # ── RequestValidationError (path-dependent) ──
    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        if request.url.path.startswith("/api/v1/data-source"):
            return command_problem(
                request,
                status=422,
                code="DATA_SOURCE_INPUT_INVALID",
                detail="The data source request fields are invalid.",
                correlation_id=request.state.correlation_id,
            )
        return JSONResponse(
            status_code=422,
            content={"detail": error.errors()},
            headers={"X-Correlation-ID": request.state.correlation_id},
        )
