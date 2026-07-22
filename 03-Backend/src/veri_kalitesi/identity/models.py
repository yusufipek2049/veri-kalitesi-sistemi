"""Guvenilir aktor ve yetkilendirme domain modelleri."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ActorType(str, Enum):
    USER = "USER"
    SERVICE = "SERVICE"
    BREAK_GLASS = "BREAK_GLASS"


_CONTEXT_TRUST_MARKER = object()


@dataclass(frozen=True)
class ActorContext:
    actor_id: str
    actor_type: ActorType
    authentication_source: str
    session_id: str
    roles: frozenset[str]
    permitted_source_ids: frozenset[str]
    permitted_dataset_ids: frozenset[str]
    can_view_enterprise: bool
    privileged: bool
    issued_at: datetime
    expires_at: datetime
    policy_version: str
    correlation_id: str
    _trust_marker: object = field(repr=False, compare=False)


@dataclass(frozen=True)
class DashboardAuthorizationDecision:
    permitted_source_ids: frozenset[str]
    permitted_dataset_ids: frozenset[str]
    can_view_enterprise: bool
    policy_version: str


@dataclass(frozen=True)
class DashboardAuthorizationPolicy:
    version: str
    allowed_actor_types: frozenset[ActorType] = field(
        default_factory=lambda: frozenset({ActorType.USER})
    )


def _create_trusted_context(
    *,
    actor_id: str,
    actor_type: ActorType,
    authentication_source: str,
    session_id: str,
    roles: frozenset[str],
    permitted_source_ids: frozenset[str],
    permitted_dataset_ids: frozenset[str],
    can_view_enterprise: bool,
    privileged: bool,
    issued_at: datetime,
    expires_at: datetime,
    policy_version: str,
    correlation_id: str,
) -> ActorContext:
    return ActorContext(
        actor_id=actor_id,
        actor_type=actor_type,
        authentication_source=authentication_source,
        session_id=session_id,
        roles=roles,
        permitted_source_ids=permitted_source_ids,
        permitted_dataset_ids=permitted_dataset_ids,
        can_view_enterprise=can_view_enterprise,
        privileged=privileged,
        issued_at=issued_at,
        expires_at=expires_at,
        policy_version=policy_version,
        correlation_id=correlation_id,
        _trust_marker=_CONTEXT_TRUST_MARKER,
    )


def _is_trusted_context(context: object) -> bool:
    return isinstance(context, ActorContext) and context._trust_marker is _CONTEXT_TRUST_MARKER


def is_trusted_actor_context(context: object) -> bool:
    """Context'in guvenilir issuer tarafindan uretildigini dogrula."""
    return _is_trusted_context(context)
