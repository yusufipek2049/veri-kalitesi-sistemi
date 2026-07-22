"""Guvenilir aktor uretimi ve deny-by-default yetkilendirme."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Protocol

from veri_kalitesi.audit import AuditEventInput, AuditResult, AuditSink
from veri_kalitesi.identity.errors import (
    ActorContextValidationError,
    AuthorizationDeniedError,
    AuthorizationUnavailableError,
)
from veri_kalitesi.identity.models import (
    ActorContext,
    ActorType,
    DashboardAuthorizationDecision,
    DashboardAuthorizationPolicy,
    _create_trusted_context,
    _is_trusted_context,
)


class AuthorizationService(Protocol):
    def authorize_dashboard(
        self, context: ActorContext | None
    ) -> DashboardAuthorizationDecision: ...


class ActorContextIssuer:
    """Authentication adapter sinirinda guvenilir context uretir."""

    def issue(
        self,
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
        values = (
            actor_id,
            authentication_source,
            session_id,
            policy_version,
            correlation_id,
        )
        if any(not value.strip() for value in values):
            raise ActorContextValidationError("Actor context identifiers must not be blank.")
        if not isinstance(actor_type, ActorType):
            raise ActorContextValidationError("actor_type is invalid.")
        if not _is_aware(issued_at) or not _is_aware(expires_at):
            raise ActorContextValidationError("Actor context timestamps must be UTC-aware.")
        if issued_at >= expires_at:
            raise ActorContextValidationError("Actor context expiry must follow issuance.")
        if any(not value.strip() for value in roles):
            raise ActorContextValidationError("Actor roles must not be blank.")
        if any(not value.strip() for value in permitted_source_ids):
            raise ActorContextValidationError("Permitted source IDs must not be blank.")
        if any(not value.strip() for value in permitted_dataset_ids):
            raise ActorContextValidationError("Permitted dataset IDs must not be blank.")
        if actor_type is ActorType.BREAK_GLASS and not privileged:
            raise ActorContextValidationError("Break-glass context must be privileged.")
        return _create_trusted_context(
            actor_id=actor_id,
            actor_type=actor_type,
            authentication_source=authentication_source,
            session_id=session_id,
            roles=frozenset(roles),
            permitted_source_ids=frozenset(permitted_source_ids),
            permitted_dataset_ids=frozenset(permitted_dataset_ids),
            can_view_enterprise=can_view_enterprise,
            privileged=privileged,
            issued_at=issued_at,
            expires_at=expires_at,
            policy_version=policy_version,
            correlation_id=correlation_id,
        )


class PolicyAuthorizationService:
    def __init__(
        self,
        policy: DashboardAuthorizationPolicy,
        audit_sink: AuditSink,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        if not policy.version.strip():
            raise ActorContextValidationError("Authorization policy version is required.")
        if not policy.allowed_actor_types:
            raise ActorContextValidationError(
                "Authorization policy must allow at least one actor type."
            )
        self.policy = policy
        self.audit_sink = audit_sink
        self.clock = clock

    def authorize_dashboard(self, context: ActorContext | None) -> DashboardAuthorizationDecision:
        now = self.clock()
        if not _is_aware(now):
            raise ActorContextValidationError("Authorization clock must be UTC-aware.")
        if not _is_trusted_context(context):
            self._deny(None, "UNTRUSTED_CONTEXT", now)
        assert context is not None
        if context.issued_at > now:
            self._deny(context, "CONTEXT_NOT_YET_VALID", now)
        if context.expires_at <= now:
            self._deny(context, "CONTEXT_EXPIRED", now)
        if context.policy_version != self.policy.version:
            self._deny(context, "POLICY_VERSION_MISMATCH", now)
        if context.actor_type not in self.policy.allowed_actor_types:
            self._deny(context, "ACTOR_TYPE_NOT_ALLOWED", now)

        self._record(context, "ALLOW", "POLICY_MATCH", now)
        return DashboardAuthorizationDecision(
            permitted_source_ids=context.permitted_source_ids,
            permitted_dataset_ids=context.permitted_dataset_ids,
            can_view_enterprise=context.can_view_enterprise,
            policy_version=self.policy.version,
        )

    def _deny(
        self,
        context: ActorContext | None,
        reason_code: str,
        now: datetime,
    ) -> None:
        trusted_context = context if _is_trusted_context(context) else None
        self._record(trusted_context, "DENY", reason_code, now)
        raise AuthorizationDeniedError(
            reason_code,
            trusted_context.correlation_id
            if trusted_context is not None
            else "authorization-denied",
        )

    def _record(
        self,
        context: ActorContext | None,
        result: str,
        reason_code: str,
        now: datetime,
    ) -> None:
        event = AuditEventInput(
            actor_id=context.actor_id if context is not None else "UNKNOWN",
            actor_type=context.actor_type.value if context is not None else None,
            correlation_id=(
                context.correlation_id if context is not None else "authorization-denied"
            ),
            action="DASHBOARD_SCOPE_AUTHORIZATION",
            object_type="AuthorizationDecision",
            object_id=context.actor_id if context is not None else None,
            result=(AuditResult.SUCCESS if result == "ALLOW" else AuditResult.DENIED),
            reason_code=reason_code,
            old_values={},
            new_values={
                "policy_version": self.policy.version,
                "permitted_source_count": (
                    len(context.permitted_source_ids) if context is not None else 0
                ),
                "can_view_enterprise": (
                    context.can_view_enterprise if context is not None else False
                ),
                "reason_code": reason_code,
                "authentication_source": (
                    context.authentication_source if context is not None else None
                ),
                "roles": sorted(context.roles) if context is not None else [],
                "permitted_source_ids": (
                    sorted(context.permitted_source_ids) if context is not None else []
                ),
                "permitted_dataset_ids": (
                    sorted(context.permitted_dataset_ids) if context is not None else []
                ),
            },
            occurred_at=now,
            session_id=context.session_id if context is not None else None,
        )
        try:
            self.audit_sink.append(event)
        except Exception as exc:
            raise AuthorizationUnavailableError(event.correlation_id) from exc


def _is_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None
