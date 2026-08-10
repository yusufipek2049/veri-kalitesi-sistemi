"""İhlal/issue alanı HTTP route kayıtları."""

from __future__ import annotations

from typing import Any, Protocol

from fastapi import FastAPI, Request, Response

from veri_kalitesi.api.bff import CSRF_HEADER_NAME
from veri_kalitesi.api.identity import DevelopmentActorContextResolver
from veri_kalitesi.api.models import (
    InvestigationEvidenceResponse,
    IssueAssigneeOptionResponse,
    IssueAssigneeOptionsResponse,
    IssueCreateRequest,
    IssueListItemResponse,
    IssueListResponse,
    IssueMutationRequest,
    IssueMutationResponse,
    IssueReassignmentRequest,
    IssueResolutionDraftRequest,
    IssueVerificationRequest,
)
from veri_kalitesi.identity import ActorContext
from veri_kalitesi.issues import (
    DataQualityIssue,
    IssueAssignment,
    IssueAuthorizationError,
    IssueConflictError,
    IssueError,
    IssueInvestigationEvidenceService,
    IssueQueryService,
    IssueQueryTechnicalError,
    IssueResolutionDraft,
    IssueTechnicalError,
    IssueValidationError,
)


class IssueInvestigationService(Protocol):
    def start_investigation(
        self,
        issue_id: str,
        expected_version: int,
        actor_context: ActorContext | None,
    ) -> DataQualityIssue: ...


class IssueAssignmentService(Protocol):
    def reassign(
        self,
        issue_id: str,
        assignment: IssueAssignment,
        expected_version: int,
        actor_context: ActorContext | None,
    ) -> DataQualityIssue: ...


class IssueAssigneeOptionProvider(Protocol):
    def list_assignment_options(
        self,
        issue_id: str,
        actor_context: ActorContext | None,
    ) -> tuple[IssueAssigneeOptionResponse, ...]: ...


class IssueResolutionService(Protocol):
    def resolve(
        self,
        issue_id: str,
        draft: IssueResolutionDraft,
        expected_version: int,
        actor_context: ActorContext | None,
    ) -> DataQualityIssue: ...


class IssueVerificationService(Protocol):
    def record_verification_result(
        self,
        issue_id: str,
        verification_reference_id: str,
        actor_context: ActorContext | None,
    ) -> DataQualityIssue: ...


class IssueClosureService(Protocol):
    def close(
        self,
        issue_id: str,
        actor_context: ActorContext | None,
    ) -> DataQualityIssue: ...


class IssueCreationService(Protocol):
    def create_manual(
        self,
        draft: Any,
        actor_context: ActorContext | None,
    ) -> DataQualityIssue: ...


class _Resolver(Protocol):
    def resolve(self, request: Request) -> ActorContext | None: ...


def register_issues_routes(
    app: FastAPI,
    *,
    issue_query_service: IssueQueryService | None,
    issue_investigation_service: IssueInvestigationService | None,
    issue_investigation_evidence_service: IssueInvestigationEvidenceService | None,
    issue_assignment_service: IssueAssignmentService | None,
    issue_assignee_option_provider: IssueAssigneeOptionProvider | None,
    issue_resolution_service: IssueResolutionService | None,
    issue_verification_service: IssueVerificationService | None,
    issue_closure_service: IssueClosureService | None,
    issue_creation_service: IssueCreationService | None,
    resolver: _Resolver,
    data_origin: str,
) -> None:
    """İhlal alanının route'larını FastAPI uygulamasına kaydeder."""

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
        assert actor_context is not None
        issues = issue_query_service.list_for_actor(actor_context)
        response.headers["Cache-Control"] = "no-store"
        if isinstance(resolver, DevelopmentActorContextResolver):
            response.headers[CSRF_HEADER_NAME] = resolver.request_proof
        page_actions: list[str] = []
        if issue_creation_service is not None and _can_create_manual_issue(actor_context):
            page_actions.append("CREATE_ISSUE")
        return IssueListResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            limit=issue_query_service.page_limit,
            items=tuple(
                IssueListItemResponse.from_domain(
                    issue,
                    available_actions=_issue_actions(issue, actor_context),
                )
                for issue in issues
            ),
        )

    @app.post(
        "/api/v1/issues",
        response_model=IssueMutationResponse,
        status_code=201,
        tags=["issues"],
    )
    async def create_issue(
        payload: IssueCreateRequest,
        request: Request,
        response: Response,
    ) -> IssueMutationResponse:
        if issue_creation_service is None:
            raise IssueTechnicalError(
                "Issue creation service is unavailable.",
                request.state.correlation_id,
            )
        actor_context = getattr(request.state, "actor_context", None)
        if actor_context is None:
            actor_context = resolver.resolve(request)
        assert actor_context is not None
        from veri_kalitesi.issues import (
            ManualIssueDraft,
            IssueScopeType,
            IssuePriority,
        )

        try:
            draft = ManualIssueDraft(
                title=payload.title,
                scope_type=IssueScopeType(payload.scope_type),
                scope_id=payload.scope_id,
                priority=IssuePriority(payload.priority),
                idempotency_key=payload.idempotency_key,
                creator_user_id=actor_context.actor_id,
                correlation_id=request.state.correlation_id,
            )
        except (ValueError, TypeError) as exc:
            raise IssueValidationError(
                f"Invalid issue create payload: {exc}", request.state.correlation_id
            ) from exc
        try:
            issue = issue_creation_service.create_manual(draft, actor_context)
        except IssueConflictError:
            raise
        except IssueAuthorizationError:
            raise
        except IssueValidationError:
            raise
        except IssueError:
            raise
        response.headers["Cache-Control"] = "no-store"
        if isinstance(resolver, DevelopmentActorContextResolver):
            response.headers[CSRF_HEADER_NAME] = resolver.request_proof
        return IssueMutationResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            item=IssueListItemResponse.from_domain(issue),
        )

    @app.post(
        "/api/v1/issues/{issue_id}/investigation",
        response_model=IssueMutationResponse,
        tags=["issues"],
    )
    async def start_issue_investigation(
        issue_id: str,
        payload: IssueMutationRequest,
        request: Request,
        response: Response,
    ) -> IssueMutationResponse:
        if issue_investigation_service is None:
            raise IssueTechnicalError(
                "Issue investigation service is unavailable.",
                request.state.correlation_id,
            )
        actor_context = getattr(request.state, "actor_context", None)
        if actor_context is None:
            actor_context = resolver.resolve(request)
        assert actor_context is not None
        issue = issue_investigation_service.start_investigation(
            issue_id,
            payload.version,
            actor_context,
        )
        response.headers["Cache-Control"] = "no-store"
        return IssueMutationResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            item=IssueListItemResponse.from_domain(
                issue,
                available_actions=_issue_actions(issue, actor_context),
            ),
        )

    @app.get(
        "/api/v1/issues/{issue_id}/investigation/evidence",
        response_model=InvestigationEvidenceResponse,
        tags=["issues"],
    )
    async def get_issue_investigation_evidence(
        issue_id: str,
        request: Request,
        response: Response,
    ) -> InvestigationEvidenceResponse:
        """BE-04: Salt okunur ihlal inceleme kaniti."""
        if issue_investigation_evidence_service is None:
            raise IssueTechnicalError(
                "Issue investigation evidence service is unavailable.",
                request.state.correlation_id,
            )
        actor_context = getattr(request.state, "actor_context", None)
        if actor_context is None:
            actor_context = resolver.resolve(request)
        evidence = issue_investigation_evidence_service.get_investigation_evidence(
            issue_id=issue_id,
            actor_context=actor_context,
        )
        response.headers["Cache-Control"] = "no-store"
        return InvestigationEvidenceResponse.from_domain(
            evidence,
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
        )

    @app.get(
        "/api/v1/issues/{issue_id}/assignment-options",
        response_model=IssueAssigneeOptionsResponse,
        tags=["issues"],
    )
    async def get_issue_assignment_options(
        issue_id: str,
        request: Request,
        response: Response,
    ) -> IssueAssigneeOptionsResponse:
        if issue_assignee_option_provider is None:
            raise IssueTechnicalError(
                "Issue assignment options are unavailable.",
                request.state.correlation_id,
            )
        actor_context = resolver.resolve(request)
        options = issue_assignee_option_provider.list_assignment_options(
            issue_id,
            actor_context,
        )
        response.headers["Cache-Control"] = "no-store"
        return IssueAssigneeOptionsResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            items=options,
        )

    @app.post(
        "/api/v1/issues/{issue_id}/assignment",
        response_model=IssueMutationResponse,
        tags=["issues"],
    )
    async def reassign_issue(
        issue_id: str,
        payload: IssueReassignmentRequest,
        request: Request,
        response: Response,
    ) -> IssueMutationResponse:
        if issue_assignment_service is None:
            raise IssueTechnicalError(
                "Issue assignment service is unavailable.",
                request.state.correlation_id,
            )
        actor_context = getattr(request.state, "actor_context", None)
        if actor_context is None:
            actor_context = resolver.resolve(request)
        assert actor_context is not None
        issue = issue_assignment_service.reassign(
            issue_id,
            IssueAssignment(
                assignee_user_id=str(payload.assignee_user_id),
                priority=payload.priority,
            ),
            payload.version,
            actor_context,
        )
        response.headers["Cache-Control"] = "no-store"
        return IssueMutationResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            item=IssueListItemResponse.from_domain(
                issue,
                available_actions=_issue_actions(issue, actor_context),
            ),
        )

    @app.post(
        "/api/v1/issues/{issue_id}/resolution",
        response_model=IssueMutationResponse,
        tags=["issues"],
    )
    async def resolve_issue(
        issue_id: str,
        payload: IssueResolutionDraftRequest,
        request: Request,
        response: Response,
    ) -> IssueMutationResponse:
        if issue_resolution_service is None:
            raise IssueTechnicalError(
                "Issue resolution service is unavailable.",
                request.state.correlation_id,
            )
        actor_context = getattr(request.state, "actor_context", None)
        if actor_context is None:
            actor_context = resolver.resolve(request)
        assert actor_context is not None
        draft = IssueResolutionDraft(
            root_cause=payload.root_cause,
            corrective_action=payload.corrective_action,
            evidence_reference_id=str(payload.evidence_reference_id),
            completed_at=payload.completed_at,
        )
        issue = issue_resolution_service.resolve(
            issue_id,
            draft,
            payload.version,
            actor_context,
        )
        response.headers["Cache-Control"] = "no-store"
        return IssueMutationResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            item=IssueListItemResponse.from_domain(
                issue,
                available_actions=_issue_actions(issue, actor_context),
            ),
        )

    @app.post(
        "/api/v1/issues/{issue_id}/verification",
        response_model=IssueMutationResponse,
        tags=["issues"],
    )
    async def verify_issue(
        issue_id: str,
        payload: IssueVerificationRequest,
        request: Request,
        response: Response,
    ) -> IssueMutationResponse:
        if issue_verification_service is None:
            raise IssueTechnicalError(
                "Issue verification service is unavailable.",
                request.state.correlation_id,
            )
        actor_context = getattr(request.state, "actor_context", None)
        if actor_context is None:
            actor_context = resolver.resolve(request)
        assert actor_context is not None
        issue = issue_verification_service.record_verification_result(
            issue_id,
            str(payload.verification_reference_id),
            actor_context,
        )
        response.headers["Cache-Control"] = "no-store"
        return IssueMutationResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            item=IssueListItemResponse.from_domain(
                issue,
                available_actions=_issue_actions(issue, actor_context),
            ),
        )

    @app.post(
        "/api/v1/issues/{issue_id}/closure",
        response_model=IssueMutationResponse,
        tags=["issues"],
    )
    async def close_issue(
        issue_id: str,
        payload: IssueMutationRequest,
        request: Request,
        response: Response,
    ) -> IssueMutationResponse:
        if issue_closure_service is None:
            raise IssueTechnicalError(
                "Issue closure service is unavailable.",
                request.state.correlation_id,
            )
        actor_context = getattr(request.state, "actor_context", None)
        if actor_context is None:
            actor_context = resolver.resolve(request)
        assert actor_context is not None
        issue = issue_closure_service.close(
            issue_id,
            actor_context,
        )
        response.headers["Cache-Control"] = "no-store"
        return IssueMutationResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            item=IssueListItemResponse.from_domain(
                issue,
                available_actions=_issue_actions(issue, actor_context),
            ),
        )


def _can_create_manual_issue(actor_context: ActorContext | None) -> bool:
    """USER actor with DATA_STEWARD/DATA_OWNER rol ve non-privileged scope."""
    if actor_context is None:
        return False
    if actor_context.actor_type.value != "USER":
        return False
    if actor_context.privileged:
        return False
    if not actor_context.roles.intersection({"DATA_STEWARD", "DATA_OWNER"}):
        return False
    return bool(actor_context.permitted_source_ids or actor_context.permitted_dataset_ids)


def _issue_actions(
    issue: DataQualityIssue,
    actor_context: ActorContext,
) -> tuple[str, ...]:
    has_scope = (
        issue.scope_id in actor_context.permitted_source_ids
        if issue.scope_type.value == "SOURCE"
        else issue.scope_id in actor_context.permitted_dataset_ids
    )
    actions: list[str] = []
    if (
        issue.status.value == "ASSIGNED"
        and issue.assignee_user_id == actor_context.actor_id
        and has_scope
        and not actor_context.privileged
    ):
        actions.append("START_INVESTIGATION")
    if (
        issue.status.value in {"ASSIGNED", "INVESTIGATING"}
        and actor_context.roles.intersection({"DATA_STEWARD", "DATA_GOVERNANCE_SPECIALIST"})
        and has_scope
        and not actor_context.privileged
    ):
        actions.append("REASSIGN")
    if (
        issue.status.value in {"INVESTIGATING", "WAITING_FOR_RESOLUTION"}
        and issue.assignee_user_id == actor_context.actor_id
        and has_scope
        and not actor_context.privileged
    ):
        actions.append("RESOLVE")
    if (
        issue.status.value == "RESOLVED"
        and issue.assignee_user_id != actor_context.actor_id
        and actor_context.roles.intersection({"DATA_STEWARD", "DATA_GOVERNANCE_SPECIALIST"})
        and has_scope
        and not actor_context.privileged
    ):
        actions.append("VERIFY")
    if (
        issue.status.value == "VERIFIED"
        and actor_context.roles.intersection({"DATA_OWNER", "DATA_STEWARD"})
        and has_scope
        and not actor_context.privileged
    ):
        actions.append("CLOSE")
    return tuple(actions)
