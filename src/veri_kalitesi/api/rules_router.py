"""Kural alanı HTTP route kayıtları."""

from __future__ import annotations

from typing import Any, Protocol

from fastapi import FastAPI, HTTPException, Request, Response

from veri_kalitesi.api.models import (
    RuleActivationRequest,
    RuleApprovalDecisionRequest,
    RuleApprovalRequestPayload,
    RuleApprovalWithdrawRequest,
    RuleCreateRequest,
    RuleDetailResponse,
    RuleListItemResponse,
    RuleListResponse,
    RuleMutationResponse,
    RulePassivationRequest,
    RuleTestRequest,
    RuleTestResultResponse,
    RuleVersionCreateRequest,
)
from veri_kalitesi.identity import ActorContext
from veri_kalitesi.rules import (
    QualityRule,
    RuleApprovalRequest,
    RuleQueryService,
    RuleQueryTechnicalError,
    RuleQueryAuthorizationError,
    RuleTestResult,
    RuleVersion,
)


class RuleCreatorService(Protocol):
    def create_rule(
        self,
        *,
        actor_id: str,
        code: str,
        name: str,
        dataset_id: str,
        rule_type: str,
        primary_dimension: str,
        threshold: float,
        weight: float,
        criticality: str,
        owner_user_id: str,
        parameters: dict,
        correlation_id: str | None = None,
        actor_context: ActorContext | None = None,
    ) -> tuple[QualityRule, RuleVersion]: ...


class RuleMutationService(Protocol):
    """Kural mutasyonlari icin tek protokol.

    Her metod domain mutasyonunu gerceklestirir ve HTTP yaniti icin
    hem guncel QualityRule hem de en son RuleVersion dondurur.
    """

    def create_version(
        self,
        *,
        actor_id: str,
        quality_rule_id: str,
        parameters: dict,
        threshold: float,
        weight: float,
        criticality: str,
        correlation_id: str | None = None,
        actor_context: ActorContext | None = None,
    ) -> tuple[QualityRule, RuleVersion]: ...

    def test_rule(
        self,
        *,
        actor_id: str,
        rule_version_id: str,
        options: Any | None = None,
        correlation_id: str | None = None,
        actor_context: ActorContext | None = None,
    ) -> RuleTestResult: ...

    def activate_rule(
        self,
        *,
        actor_id: str,
        quality_rule_id: str,
        correlation_id: str | None = None,
        actor_context: ActorContext | None = None,
    ) -> tuple[QualityRule, RuleVersion]: ...

    def request_rule_approval(
        self,
        *,
        actor_context: ActorContext | None,
        quality_rule_id: str,
    ) -> tuple[QualityRule, RuleVersion, RuleApprovalRequest]: ...

    def decide_rule_approval(
        self,
        *,
        actor_context: ActorContext | None,
        approval_request_id: str,
        decision: str,
        reason_code: str,
    ) -> tuple[QualityRule, RuleVersion]: ...

    def withdraw_rule_approval(
        self,
        *,
        actor_context: ActorContext | None,
        approval_request_id: str,
        reason_code: str,
    ) -> tuple[QualityRule, RuleVersion]: ...

    def passivate_rule(
        self,
        *,
        quality_rule_id: str,
        correlation_id: str | None = None,
        actor_context: ActorContext | None = None,
    ) -> tuple[QualityRule, RuleVersion]: ...


class _Resolver(Protocol):
    def resolve(self, request: Request) -> ActorContext | None: ...


def register_rules_routes(
    app: FastAPI,
    *,
    rule_query_service: RuleQueryService | None,
    rule_creator_service: RuleCreatorService | None,
    rule_mutation_service: RuleMutationService | None,
    resolver: _Resolver,
    data_origin: str,
) -> None:
    """Kural alanının route'larını FastAPI uygulamasına kaydeder."""

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
        assert actor_context is not None
        rules = rule_query_service.list_for_actor(actor_context)
        pending_approvals = rule_query_service.pending_approval_requests_for_versions(
            frozenset(version.rule_version_id for _rule, version in rules)
        )
        response.headers["Cache-Control"] = "no-store"
        return RuleListResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            items=tuple(
                RuleListItemResponse.from_domain(
                    rule,
                    version,
                    available_actions=_rule_actions(
                        rule,
                        version,
                        actor_context,
                        pending_approval=pending_approvals.get(version.rule_version_id),
                    ),
                    pending_approval_request_id=(
                        pending_approvals[version.rule_version_id].approval_request_id
                        if version.rule_version_id in pending_approvals
                        else None
                    ),
                )
                for rule, version in rules
            ),
        )

    @app.get(
        "/api/v1/rules/{rule_id}",
        response_model=RuleDetailResponse,
        tags=["rules"],
    )
    async def get_rule_detail(
        rule_id: str, request: Request, response: Response
    ) -> RuleDetailResponse:
        if rule_query_service is None:
            raise RuleQueryTechnicalError(
                "Rule service is unavailable.", request.state.correlation_id
            )
        actor_context = resolver.resolve(request)
        if actor_context is None:
            raise HTTPException(status_code=401, detail="Authentication is required.")
        try:
            rule, version = rule_query_service.get_rule_with_latest_version(rule_id, actor_context)
        except RuleQueryAuthorizationError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except (KeyError, Exception) as exc:
            if "not found" in str(exc).lower():
                raise HTTPException(status_code=404, detail="Rule not found.") from exc
            raise
        response.headers["Cache-Control"] = "no-store"
        pending_approvals = rule_query_service.pending_approval_requests_for_versions(
            frozenset({version.rule_version_id})
        )
        pending_approval = pending_approvals.get(version.rule_version_id)
        item = RuleListItemResponse.from_domain(
            rule,
            version,
            available_actions=_rule_actions(
                rule, version, actor_context, pending_approval=pending_approval
            ),
            pending_approval_request_id=(
                pending_approval.approval_request_id if pending_approval else None
            ),
        )
        return RuleDetailResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            item=item,
            definition=dict(version.definition),
        )

    @app.post(
        "/api/v1/rules",
        response_model=RuleMutationResponse,
        status_code=201,
        tags=["rules"],
    )
    async def create_rule(
        payload: RuleCreateRequest,
        request: Request,
        response: Response,
    ) -> RuleMutationResponse:
        if rule_creator_service is None:
            raise RuleQueryTechnicalError(
                "Rule creator service is unavailable.", request.state.correlation_id
            )
        actor_context = getattr(request.state, "actor_context", None)
        if actor_context is None:
            actor_context = resolver.resolve(request)
        rule, version = rule_creator_service.create_rule(
            actor_id=actor_context.actor_id if actor_context else "unknown",
            code=payload.code,
            name=payload.name,
            dataset_id=payload.dataset_id,
            rule_type=payload.rule_type,
            primary_dimension=payload.primary_dimension,
            threshold=payload.threshold,
            weight=payload.weight,
            criticality=payload.criticality,
            owner_user_id=payload.owner_user_id,
            parameters=payload.parameters,
            correlation_id=request.state.correlation_id,
            actor_context=actor_context,
        )
        response.headers["Cache-Control"] = "no-store"
        return RuleMutationResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            item=RuleListItemResponse.from_domain(rule, version, available_actions=()),
        )

    @app.post(
        "/api/v1/rules/{quality_rule_id}/versions",
        response_model=RuleMutationResponse,
        status_code=201,
        tags=["rules"],
    )
    async def create_rule_version(
        quality_rule_id: str,
        payload: RuleVersionCreateRequest,
        request: Request,
        response: Response,
    ) -> RuleMutationResponse:
        if rule_mutation_service is None:
            raise RuleQueryTechnicalError(
                "Rule mutation service is unavailable.", request.state.correlation_id
            )
        actor_context = getattr(request.state, "actor_context", None)
        if actor_context is None:
            actor_context = resolver.resolve(request)
        rule, version = rule_mutation_service.create_version(
            actor_id=actor_context.actor_id if actor_context else "unknown",
            quality_rule_id=quality_rule_id,
            parameters=payload.parameters,
            threshold=payload.threshold,
            weight=payload.weight,
            criticality=payload.criticality,
            actor_context=actor_context,
        )
        response.headers["Cache-Control"] = "no-store"
        return RuleMutationResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            item=RuleListItemResponse.from_domain(rule, version, available_actions=()),
        )

    @app.post(
        "/api/v1/rules/{quality_rule_id}/test",
        response_model=RuleTestResultResponse,
        status_code=201,
        tags=["rules"],
    )
    async def test_rule(
        quality_rule_id: str,
        payload: RuleTestRequest,
        request: Request,
        response: Response,
    ) -> RuleTestResultResponse:
        if rule_mutation_service is None:
            raise RuleQueryTechnicalError(
                "Rule mutation service is unavailable.", request.state.correlation_id
            )
        actor_context = getattr(request.state, "actor_context", None)
        if actor_context is None:
            actor_context = resolver.resolve(request)
        from veri_kalitesi.rules.models import RuleTestOptions

        options = RuleTestOptions(limit=payload.limit)
        result = rule_mutation_service.test_rule(
            actor_id=actor_context.actor_id if actor_context else "unknown",
            rule_version_id=payload.rule_version_id,
            options=options,
            correlation_id=request.state.correlation_id,
            actor_context=actor_context,
        )
        response.headers["Cache-Control"] = "no-store"
        return RuleTestResultResponse.from_domain(result)

    @app.post(
        "/api/v1/rules/{quality_rule_id}/activation",
        response_model=RuleMutationResponse,
        tags=["rules"],
    )
    async def activate_rule(
        quality_rule_id: str,
        payload: RuleActivationRequest,
        request: Request,
        response: Response,
    ) -> RuleMutationResponse:
        if rule_mutation_service is None:
            raise RuleQueryTechnicalError(
                "Rule mutation service is unavailable.", request.state.correlation_id
            )
        actor_context = getattr(request.state, "actor_context", None)
        if actor_context is None:
            actor_context = resolver.resolve(request)
        rule, version = rule_mutation_service.activate_rule(
            quality_rule_id=quality_rule_id,
            actor_id=actor_context.actor_id if actor_context else "unknown",
            correlation_id=request.state.correlation_id,
            actor_context=actor_context,
        )
        response.headers["Cache-Control"] = "no-store"
        return RuleMutationResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            item=RuleListItemResponse.from_domain(rule, version, available_actions=()),
        )

    @app.post(
        "/api/v1/rules/{quality_rule_id}/approval",
        response_model=RuleMutationResponse,
        status_code=201,
        tags=["rules"],
    )
    async def request_rule_approval(
        quality_rule_id: str,
        payload: RuleApprovalRequestPayload,
        request: Request,
        response: Response,
    ) -> RuleMutationResponse:
        if rule_mutation_service is None:
            raise RuleQueryTechnicalError(
                "Rule mutation service is unavailable.", request.state.correlation_id
            )
        actor_context = getattr(request.state, "actor_context", None)
        if actor_context is None:
            actor_context = resolver.resolve(request)
        rule, version, approval_request = rule_mutation_service.request_rule_approval(
            actor_context=actor_context,
            quality_rule_id=quality_rule_id,
        )
        response.headers["Cache-Control"] = "no-store"
        return RuleMutationResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            item=RuleListItemResponse.from_domain(
                rule,
                version,
                available_actions=(),
                pending_approval_request_id=approval_request.approval_request_id,
            ),
        )

    @app.post(
        "/api/v1/rules/approval/{approval_request_id}/decide",
        response_model=RuleMutationResponse,
        tags=["rules"],
    )
    async def decide_rule_approval(
        approval_request_id: str,
        payload: RuleApprovalDecisionRequest,
        request: Request,
        response: Response,
    ) -> RuleMutationResponse:
        if rule_mutation_service is None:
            raise RuleQueryTechnicalError(
                "Rule mutation service is unavailable.", request.state.correlation_id
            )
        actor_context = getattr(request.state, "actor_context", None)
        if actor_context is None:
            actor_context = resolver.resolve(request)
        rule, version = rule_mutation_service.decide_rule_approval(
            actor_context=actor_context,
            approval_request_id=approval_request_id,
            decision=payload.decision,
            reason_code=payload.reason_code,
        )
        response.headers["Cache-Control"] = "no-store"
        return RuleMutationResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            item=RuleListItemResponse.from_domain(rule, version, available_actions=()),
        )

    @app.post(
        "/api/v1/rules/approval/{approval_request_id}/withdraw",
        response_model=RuleMutationResponse,
        tags=["rules"],
    )
    async def withdraw_rule_approval(
        approval_request_id: str,
        payload: RuleApprovalWithdrawRequest,
        request: Request,
        response: Response,
    ) -> RuleMutationResponse:
        if rule_mutation_service is None:
            raise RuleQueryTechnicalError(
                "Rule mutation service is unavailable.", request.state.correlation_id
            )
        actor_context = getattr(request.state, "actor_context", None)
        if actor_context is None:
            actor_context = resolver.resolve(request)
        rule, version = rule_mutation_service.withdraw_rule_approval(
            actor_context=actor_context,
            approval_request_id=approval_request_id,
            reason_code=payload.reason_code,
        )
        response.headers["Cache-Control"] = "no-store"
        return RuleMutationResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            item=RuleListItemResponse.from_domain(rule, version, available_actions=()),
        )

    @app.post(
        "/api/v1/rules/{quality_rule_id}/passivation",
        response_model=RuleMutationResponse,
        tags=["rules"],
    )
    async def passivate_rule(
        quality_rule_id: str,
        payload: RulePassivationRequest,
        request: Request,
        response: Response,
    ) -> RuleMutationResponse:
        if rule_mutation_service is None:
            raise RuleQueryTechnicalError(
                "Rule mutation service is unavailable.", request.state.correlation_id
            )
        actor_context = getattr(request.state, "actor_context", None)
        if actor_context is None:
            actor_context = resolver.resolve(request)
        rule, version = rule_mutation_service.passivate_rule(
            quality_rule_id=quality_rule_id,
            actor_context=actor_context,
        )
        response.headers["Cache-Control"] = "no-store"
        return RuleMutationResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            item=RuleListItemResponse.from_domain(rule, version, available_actions=()),
        )


def _rule_actions(
    rule: QualityRule,
    version: RuleVersion,
    actor_context: ActorContext,
    *,
    pending_approval: RuleApprovalRequest | None = None,
) -> tuple[str, ...]:
    """Kuralin mevcut durumu ve aktor yetkisine gore kullanilabilir eylemleri hesaplar."""
    has_dataset_scope = rule.dataset_id in actor_context.permitted_dataset_ids
    is_steward_or_governance = bool(
        actor_context.roles.intersection({"DATA_STEWARD", "DATA_GOVERNANCE_SPECIALIST"})
    )
    is_owner = bool(actor_context.roles.intersection({"DATA_OWNER"}))
    is_normal = not actor_context.privileged
    status = rule.status.value
    criticality = version.criticality.value if version else "LOW"

    actions: list[str] = []

    if status in {"DRAFT", "ACTIVE", "PASSIVE"} and has_dataset_scope and is_normal:
        actions.append("CREATE_VERSION")

    if status == "DRAFT" and has_dataset_scope and is_normal:
        actions.append("TEST_RULE")

    if status == "DRAFT" and criticality != "CRITICAL" and has_dataset_scope and is_normal:
        actions.append("ACTIVATE")

    if (
        status == "DRAFT"
        and criticality == "CRITICAL"
        and pending_approval is None
        and is_steward_or_governance
        and has_dataset_scope
        and is_normal
    ):
        actions.append("REQUEST_APPROVAL")

    if (
        status in {"DRAFT", "REVIEW_REQUIRED"}
        and pending_approval is not None
        and has_dataset_scope
        and is_normal
    ):
        if pending_approval.maker_actor_id == actor_context.actor_id:
            actions.append("WITHDRAW_APPROVAL")
        elif is_steward_or_governance or is_owner:
            actions.append("DECIDE_APPROVAL")

    if (
        status == "ACTIVE"
        and (is_steward_or_governance or is_owner)
        and has_dataset_scope
        and is_normal
    ):
        actions.append("PASSIVATE")

    return tuple(actions)
