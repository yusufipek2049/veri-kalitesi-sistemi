"""Yetki kapsamlı, salt okunur yönetişim onay merkezi sorgusu.

Domain yazma davranışlarına dokunmaz; kural ve veri kaynağı onay
tablolarından adaptör okuyucular üzerinden ortak görev listesi üretir.
Kapsam dışındaki kayıtlar fail-closed şekilde elenir.
"""

from __future__ import annotations

import sqlite3
from enum import Enum
from typing import Protocol

from sqlalchemy.exc import SQLAlchemyError

from veri_kalitesi.data_sources.models import (
    DataSource,
    DataSourceActivationRequest,
)
from veri_kalitesi.governance.models import (
    GOVERNANCE_REQUEST_DOMAINS,
    GovernanceApprovalItem,
    GovernanceApprovalPolicy,
    GovernanceApprovalRequest,
    GovernanceApprovalStatus,
    GovernanceDomain,
    GovernanceRequestStatus,
    GovernanceRequestType,
)
from veri_kalitesi.identity import ActorContext, AuthorizationService, IdentityError
from veri_kalitesi.rules.models import QualityRule, RuleApprovalRequest, RuleVersion


class GovernanceRuleApprovalReader(Protocol):
    def list_rules_with_latest_version(
        self, allowed_dataset_ids: frozenset[str]
    ) -> list[tuple[QualityRule, RuleVersion]]: ...

    def list_approval_requests_for_datasets(
        self, dataset_ids: frozenset[str]
    ) -> list[RuleApprovalRequest]: ...


class GovernanceSourceApprovalReader(Protocol):
    def list_data_sources(self, allowed_source_ids: frozenset[str]) -> list[DataSource]: ...

    def list_all_data_sources(self) -> list[DataSource]: ...

    def list_activation_requests_for_sources(
        self, source_ids: frozenset[str]
    ) -> list[DataSourceActivationRequest]: ...


class GovernanceCenterReader(Protocol):
    """Ortak governance_approval_requests tablosunun okuma yüzeyi."""

    def list_for_scope(
        self,
        *,
        dataset_ids: frozenset[str],
        source_ids: frozenset[str],
    ) -> list[GovernanceApprovalRequest]: ...


class GovernanceView(str, Enum):
    ALL = "ALL"
    PENDING = "PENDING"
    MINE = "MINE"
    DECIDED = "DECIDED"
    EXPIRED = "EXPIRED"


class GovernanceQueryError(Exception):
    def __init__(self, message: str, correlation_id: str) -> None:
        super().__init__(message)
        self.correlation_id = correlation_id


class GovernanceQueryAuthorizationError(GovernanceQueryError):
    """Güvenilir yönetişim kapsamı üretilemedi."""


class GovernanceQueryTechnicalError(GovernanceQueryError):
    """Yönetişim sorgusu teknik nedenle tamamlanamadı."""


class GovernanceApprovalQueryService:
    MAX_ITEMS = 200

    def __init__(
        self,
        rule_reader: GovernanceRuleApprovalReader | None,
        source_reader: GovernanceSourceApprovalReader | None,
        authorization_service: AuthorizationService,
        *,
        center_reader: GovernanceCenterReader | None = None,
        center_policy: GovernanceApprovalPolicy | None = None,
    ) -> None:
        self.rule_reader = rule_reader
        self.source_reader = source_reader
        self.authorization_service = authorization_service
        self.center_reader = center_reader
        self.center_policy = center_policy

    def list_for_actor(
        self,
        actor_context: ActorContext | None,
        *,
        view: GovernanceView = GovernanceView.ALL,
    ) -> tuple[GovernanceApprovalItem, ...]:
        correlation_id = (
            actor_context.correlation_id if actor_context is not None else "authorization-denied"
        )
        try:
            decision = self.authorization_service.authorize_dashboard(actor_context)
        except IdentityError as exc:
            raise GovernanceQueryAuthorizationError(
                "Governance scope is not available.", correlation_id
            ) from exc
        try:
            items = [
                *self._rule_items(decision.permitted_dataset_ids),
                *self._source_items(decision.permitted_source_ids, decision.can_view_enterprise),
                *self._center_items(decision, actor_context),
            ]
        except (sqlite3.Error, SQLAlchemyError, OSError) as exc:
            raise GovernanceQueryTechnicalError(
                "Governance query could not be completed.", correlation_id
            ) from exc
        items = _apply_view(items, view, actor_context)
        items.sort(key=lambda item: (item.requested_at, item.approval_request_id), reverse=True)
        return tuple(items[: self.MAX_ITEMS])

    def _rule_items(self, permitted_dataset_ids: frozenset[str]) -> list[GovernanceApprovalItem]:
        if self.rule_reader is None or not permitted_dataset_ids:
            return []
        scoped_versions = {
            version.rule_version_id: rule
            for rule, version in self.rule_reader.list_rules_with_latest_version(
                permitted_dataset_ids
            )
        }
        items: list[GovernanceApprovalItem] = []
        for request in self.rule_reader.list_approval_requests_for_datasets(permitted_dataset_ids):
            rule = scoped_versions.get(request.rule_version_id)
            if rule is None or rule.dataset_id not in permitted_dataset_ids:
                continue
            items.append(
                GovernanceApprovalItem(
                    approval_request_id=request.approval_request_id,
                    domain=GovernanceDomain.QUALITY_RULE,
                    request_type=GovernanceRequestType.RULE_APPROVAL,
                    status=GovernanceRequestStatus(request.status.value),
                    object_type="QualityRule",
                    object_id=rule.quality_rule_id,
                    object_name=f"{rule.code} — {rule.name}",
                    scope_type="DATASET",
                    scope_id=rule.dataset_id,
                    maker_actor_id=request.maker_actor_id,
                    checker_actor_id=request.checker_actor_id,
                    reason_code=request.decision_reason_code,
                    requested_at=request.requested_at,
                    decided_at=request.decided_at,
                    expires_at=request.expires_at,
                    policy_version=request.policy_version,
                )
            )
        return items

    def _source_items(
        self, permitted_source_ids: frozenset[str], can_view_enterprise: bool
    ) -> list[GovernanceApprovalItem]:
        if self.source_reader is None:
            return []
        sources = (
            self.source_reader.list_all_data_sources()
            if can_view_enterprise
            else self.source_reader.list_data_sources(permitted_source_ids)
        )
        scoped_sources = {
            source.data_source_id: source
            for source in sources
            if can_view_enterprise or source.data_source_id in permitted_source_ids
        }
        if not scoped_sources:
            return []
        items: list[GovernanceApprovalItem] = []
        for request in self.source_reader.list_activation_requests_for_sources(
            frozenset(scoped_sources)
        ):
            source = scoped_sources.get(request.data_source_id)
            if source is None:
                continue
            request_type = (
                GovernanceRequestType.SOURCE_DEACTIVATION
                if request.request_type == "DEACTIVATION"
                else GovernanceRequestType.SOURCE_ACTIVATION
            )
            items.append(
                GovernanceApprovalItem(
                    approval_request_id=request.activation_request_id,
                    domain=GovernanceDomain.DATA_SOURCE,
                    request_type=request_type,
                    status=GovernanceRequestStatus(request.status.value),
                    object_type="DataSource",
                    object_id=source.data_source_id,
                    object_name=source.name,
                    scope_type="DATA_SOURCE",
                    scope_id=source.data_source_id,
                    maker_actor_id=request.maker_actor_id,
                    checker_actor_id=request.checker_actor_id,
                    reason_code=request.decision_reason_code,
                    requested_at=request.requested_at,
                    decided_at=request.decided_at,
                    expires_at=request.expires_at,
                    policy_version=request.policy_version,
                )
            )
        return items

    def _center_items(
        self,
        decision: object,
        actor_context: ActorContext | None,
    ) -> list[GovernanceApprovalItem]:
        if self.center_reader is None:
            return []
        permitted_dataset_ids: frozenset[str] = getattr(
            decision, "permitted_dataset_ids", frozenset()
        )
        permitted_source_ids: frozenset[str] = getattr(
            decision, "permitted_source_ids", frozenset()
        )
        if not permitted_dataset_ids and not permitted_source_ids:
            return []
        items: list[GovernanceApprovalItem] = []
        for request in self.center_reader.list_for_scope(
            dataset_ids=permitted_dataset_ids, source_ids=permitted_source_ids
        ):
            if request.status is GovernanceApprovalStatus.DRAFT:
                continue
            status = _center_status(request.status)
            items.append(
                center_request_to_item(
                    request,
                    available_actions=self._center_actions(
                        request, status, actor_context, permitted_dataset_ids
                    ),
                )
            )
        return items

    def _center_actions(
        self,
        request: GovernanceApprovalRequest,
        status: GovernanceRequestStatus,
        actor_context: ActorContext | None,
        permitted_dataset_ids: frozenset[str],
    ) -> tuple[str, ...]:
        policy = self.center_policy
        if policy is None or actor_context is None or actor_context.privileged:
            return ()
        if request.scope_type == "DATASET" and request.scope_id not in permitted_dataset_ids:
            return ()
        if status is GovernanceRequestStatus.PENDING:
            if request.maker_actor_id == actor_context.actor_id:
                return ("WITHDRAW_APPROVAL",)
            if not actor_context.roles.isdisjoint(policy.checker_roles):
                return ("DECIDE_APPROVAL",)
            return ()
        if status is GovernanceRequestStatus.APPROVED and policy.applier_roles:
            if not actor_context.roles.isdisjoint(policy.applier_roles):
                return ("APPLY",)
        return ()


def _center_status(status: GovernanceApprovalStatus) -> GovernanceRequestStatus:
    if status is GovernanceApprovalStatus.SUBMITTED:
        return GovernanceRequestStatus.PENDING
    return GovernanceRequestStatus(status.value)


def center_request_to_item(
    request: GovernanceApprovalRequest,
    *,
    available_actions: tuple[str, ...] = (),
) -> GovernanceApprovalItem:
    """Ortak tablo talebini görev merkezi izdüşümüne dönüştürür."""
    return GovernanceApprovalItem(
        approval_request_id=request.approval_request_id,
        domain=GOVERNANCE_REQUEST_DOMAINS.get(
            request.request_type, GovernanceDomain.DATA_OWNERSHIP
        ),
        request_type=request.request_type,
        status=_center_status(request.status),
        object_type=request.object_type,
        object_id=request.object_id,
        object_name=request.object_id,
        scope_type=request.scope_type,
        scope_id=request.scope_id,
        maker_actor_id=request.maker_actor_id,
        checker_actor_id=request.checker_actor_id,
        reason_code=request.reason_code,
        requested_at=request.requested_at,
        decided_at=request.decided_at,
        expires_at=request.expires_at,
        policy_version=request.policy_version,
        available_actions=available_actions,
        change_summary=request.change_summary,
    )


def _apply_view(
    items: list[GovernanceApprovalItem],
    view: GovernanceView,
    actor_context: ActorContext | None,
) -> list[GovernanceApprovalItem]:
    if view is GovernanceView.ALL:
        return items
    if view is GovernanceView.PENDING:
        return [
            item
            for item in items
            if item.status is GovernanceRequestStatus.PENDING
            and (actor_context is None or item.maker_actor_id != actor_context.actor_id)
        ]
    if view is GovernanceView.MINE:
        if actor_context is None:
            return []
        return [item for item in items if item.maker_actor_id == actor_context.actor_id]
    if view is GovernanceView.DECIDED:
        return [item for item in items if item.status is not GovernanceRequestStatus.PENDING]
    if view is GovernanceView.EXPIRED:
        return [item for item in items if item.status is GovernanceRequestStatus.EXPIRED]
    return items
