"""LDAP kimlik iddiasini surumlu yerel yetkiye donusturen guven siniri."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Callable, Mapping, NoReturn, Protocol

from veri_kalitesi.audit import AuditEventInput, AuditResult, AuditSink
from veri_kalitesi.identity.errors import (
    ActorContextValidationError,
    AuthenticationDeniedError,
    AuthenticationThrottleTechnicalError,
    AuthenticationUnavailableError,
    LdapAdapterTechnicalError,
    LdapCredentialsRejectedError,
    SessionUnavailableError,
)
from veri_kalitesi.identity.models import ActorType
from veri_kalitesi.identity.service import ActorContextIssuer
from veri_kalitesi.identity.sessions import SessionGrant, SessionService
from veri_kalitesi.identity.throttling import (
    AuthenticationThrottleDecision,
    AuthenticationThrottleKeyProvider,
    AuthenticationThrottleService,
)


@dataclass(frozen=True)
class LdapIdentityAssertion:
    subject_id: str
    group_ids: frozenset[str]
    actor_type: ActorType
    active: bool
    authenticated_at: datetime


@dataclass(frozen=True)
class LdapGroupGrant:
    roles: frozenset[str]
    permitted_source_ids: frozenset[str] = field(default_factory=frozenset)
    permitted_dataset_ids: frozenset[str] = field(default_factory=frozenset)
    can_view_enterprise: bool = False


@dataclass(frozen=True)
class LdapGroupRoleScopePolicy:
    version: str
    group_grants: Mapping[str, LdapGroupGrant]
    allowed_actor_types: frozenset[ActorType] = field(
        default_factory=lambda: frozenset({ActorType.USER})
    )

    def __post_init__(self) -> None:
        object.__setattr__(self, "group_grants", MappingProxyType(dict(self.group_grants)))


class LdapIdentityAdapter(Protocol):
    adapter_id: str

    def authenticate(
        self,
        *,
        principal: str,
        credential: bytes,
    ) -> LdapIdentityAssertion: ...


class LdapAuthenticationService:
    def __init__(
        self,
        adapter: LdapIdentityAdapter,
        policy: LdapGroupRoleScopePolicy,
        audit_sink: AuditSink,
        throttle: AuthenticationThrottleService,
        throttle_key_provider: AuthenticationThrottleKeyProvider,
        session_service: SessionService,
        *,
        issuer: ActorContextIssuer | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        _validate_policy(policy)
        if not adapter.adapter_id.strip():
            raise ActorContextValidationError("LDAP adapter ID is required.")
        self.adapter = adapter
        self.policy = policy
        self.audit_sink = audit_sink
        if not throttle_key_provider.version.strip():
            raise ActorContextValidationError("Throttle key policy version is required.")
        self.throttle = throttle
        self.throttle_key_provider = throttle_key_provider
        self.session_service = session_service
        self.issuer = issuer or ActorContextIssuer()
        self.clock = clock

    def authenticate(
        self,
        *,
        principal: str,
        credential: bytes,
        client_reference: str,
        correlation_id: str,
    ) -> SessionGrant:
        now = self.clock()
        if not _is_aware(now):
            raise ActorContextValidationError("LDAP authentication time must be UTC-aware.")
        if not correlation_id.strip():
            raise ActorContextValidationError("LDAP authentication correlation ID is required.")
        if (
            not principal.strip()
            or not isinstance(credential, bytes)
            or not credential
            or not client_reference.strip()
        ):
            self._deny("INVALID_CREDENTIAL_INPUT", correlation_id, now)

        try:
            throttle_keys = self.throttle_key_provider.derive(
                principal=principal,
                client_reference=client_reference,
            )
            throttle_decision = self.throttle.evaluate(throttle_keys, now)
        except (AuthenticationThrottleTechnicalError, ActorContextValidationError):
            self._unavailable("THROTTLE_TECHNICAL_ERROR", correlation_id, now)
        except Exception:
            self._unavailable("THROTTLE_UNEXPECTED_ERROR", correlation_id, now)
        if throttle_decision.blocked:
            self._deny(
                "AUTHENTICATION_THROTTLED",
                correlation_id,
                now,
                throttle_decision=throttle_decision,
            )

        try:
            assertion = self.adapter.authenticate(
                principal=principal,
                credential=credential,
            )
        except LdapCredentialsRejectedError:
            try:
                throttle_decision = self.throttle.record_failure(throttle_keys, now)
            except AuthenticationThrottleTechnicalError:
                self._unavailable("THROTTLE_TECHNICAL_ERROR", correlation_id, now)
            except Exception:
                self._unavailable("THROTTLE_UNEXPECTED_ERROR", correlation_id, now)
            self._deny(
                "CREDENTIALS_REJECTED",
                correlation_id,
                now,
                throttle_decision=throttle_decision,
            )
        except LdapAdapterTechnicalError:
            self._unavailable("LDAP_TECHNICAL_ERROR", correlation_id, now)
        except Exception:
            self._unavailable("LDAP_UNEXPECTED_ERROR", correlation_id, now)

        try:
            _validate_assertion(assertion, now)
        except ActorContextValidationError:
            self._unavailable("LDAP_INVALID_ASSERTION", correlation_id, now)
        if not assertion.active:
            self._deny(
                "LDAP_IDENTITY_INACTIVE",
                correlation_id,
                now,
                actor_id=assertion.subject_id,
                actor_type=assertion.actor_type.value,
            )
        if assertion.actor_type not in self.policy.allowed_actor_types:
            self._deny(
                "LDAP_ACTOR_TYPE_NOT_ALLOWED",
                correlation_id,
                now,
                actor_id=assertion.subject_id,
                actor_type=assertion.actor_type.value,
            )

        grants = tuple(
            self.policy.group_grants[group_id]
            for group_id in assertion.group_ids
            if group_id in self.policy.group_grants
        )
        roles = frozenset(role for grant in grants for role in grant.roles)
        if not grants or not roles:
            self._deny(
                "LDAP_GROUP_NOT_MAPPED",
                correlation_id,
                now,
                actor_id=assertion.subject_id,
                actor_type=assertion.actor_type.value,
            )

        source_ids = frozenset(
            source_id for grant in grants for source_id in grant.permitted_source_ids
        )
        dataset_ids = frozenset(
            dataset_id for grant in grants for dataset_id in grant.permitted_dataset_ids
        )
        can_view_enterprise = any(grant.can_view_enterprise for grant in grants)
        try:
            self.throttle.reset(throttle_keys, now)
        except AuthenticationThrottleTechnicalError:
            self._unavailable("THROTTLE_TECHNICAL_ERROR", correlation_id, now)
        except Exception:
            self._unavailable("THROTTLE_UNEXPECTED_ERROR", correlation_id, now)
        self._record(
            actor_id=assertion.subject_id,
            actor_type=assertion.actor_type.value,
            session_id=None,
            correlation_id=correlation_id,
            result=AuditResult.SUCCESS,
            reason_code="LDAP_AUTHENTICATED",
            mapped_role_count=len(roles),
            mapped_source_count=len(source_ids),
            mapped_dataset_count=len(dataset_ids),
            can_view_enterprise=can_view_enterprise,
            throttle_decision=throttle_decision,
            now=now,
        )
        try:
            authenticated_context = self.issuer.issue(
                actor_id=assertion.subject_id,
                actor_type=assertion.actor_type,
                authentication_source=f"LDAP:{self.adapter.adapter_id}",
                session_id=f"authentication:{correlation_id}",
                roles=roles,
                permitted_source_ids=source_ids,
                permitted_dataset_ids=dataset_ids,
                can_view_enterprise=can_view_enterprise,
                privileged=False,
                issued_at=now,
                expires_at=now + self.session_service.policy.idle_timeout,
                policy_version=self.policy.version,
                correlation_id=correlation_id,
            )
            return self.session_service.open_authenticated_session(
                authenticated_context=authenticated_context,
                correlation_id=correlation_id,
            )
        except SessionUnavailableError:
            self._unavailable("SESSION_TECHNICAL_ERROR", correlation_id, now)
        except Exception:
            self._unavailable("SESSION_UNEXPECTED_ERROR", correlation_id, now)

    def _deny(
        self,
        reason_code: str,
        correlation_id: str,
        now: datetime,
        *,
        actor_id: str = "UNKNOWN",
        actor_type: str | None = None,
        throttle_decision: AuthenticationThrottleDecision | None = None,
    ) -> NoReturn:
        self._record(
            actor_id=actor_id,
            actor_type=actor_type,
            session_id=None,
            correlation_id=correlation_id,
            result=AuditResult.DENIED,
            reason_code=reason_code,
            throttle_decision=throttle_decision,
            now=now,
        )
        raise AuthenticationDeniedError(reason_code, correlation_id)

    def _unavailable(self, reason_code: str, correlation_id: str, now: datetime) -> NoReturn:
        self._record(
            actor_id="UNKNOWN",
            actor_type=None,
            session_id=None,
            correlation_id=correlation_id,
            result=AuditResult.FAILURE,
            reason_code=reason_code,
            now=now,
        )
        raise AuthenticationUnavailableError(correlation_id)

    def _record(
        self,
        *,
        actor_id: str,
        actor_type: str | None,
        session_id: str | None,
        correlation_id: str,
        result: AuditResult,
        reason_code: str,
        now: datetime,
        mapped_role_count: int = 0,
        mapped_source_count: int = 0,
        mapped_dataset_count: int = 0,
        can_view_enterprise: bool = False,
        throttle_decision: AuthenticationThrottleDecision | None = None,
    ) -> None:
        event = AuditEventInput(
            actor_id=actor_id,
            actor_type=actor_type,
            correlation_id=correlation_id,
            action="LDAP_AUTHENTICATION",
            object_type="IdentityAuthentication",
            object_id=actor_id if actor_id != "UNKNOWN" else None,
            result=result,
            reason_code=reason_code,
            old_values={},
            new_values={
                "mapping_policy_version": self.policy.version,
                "mapped_role_count": mapped_role_count,
                "mapped_source_count": mapped_source_count,
                "mapped_dataset_count": mapped_dataset_count,
                "can_view_enterprise": can_view_enterprise,
                "throttle_policy_version": self.throttle.policy.version,
                "throttle_key_policy_version": self.throttle_key_provider.version,
                "failure_count": (
                    throttle_decision.failure_count if throttle_decision is not None else 0
                ),
                "blocked": throttle_decision.blocked if throttle_decision is not None else False,
                "blocked_scope_count": (
                    throttle_decision.blocked_scope_count if throttle_decision is not None else 0
                ),
                "reason_code": reason_code,
            },
            occurred_at=now,
            session_id=session_id,
        )
        try:
            self.audit_sink.append(event)
        except Exception as exc:
            raise AuthenticationUnavailableError(correlation_id) from exc


def _validate_policy(policy: LdapGroupRoleScopePolicy) -> None:
    if not policy.version.strip():
        raise ActorContextValidationError("LDAP mapping policy version is required.")
    if not policy.allowed_actor_types:
        raise ActorContextValidationError("LDAP mapping policy actor types are required.")
    if any(not group_id.strip() for group_id in policy.group_grants):
        raise ActorContextValidationError("LDAP mapping group IDs must not be blank.")
    for grant in policy.group_grants.values():
        values = (*grant.roles, *grant.permitted_source_ids, *grant.permitted_dataset_ids)
        if not grant.roles or any(not value.strip() for value in values):
            raise ActorContextValidationError("LDAP group grants must contain valid roles.")


def _validate_assertion(assertion: LdapIdentityAssertion, now: datetime) -> None:
    if not assertion.subject_id.strip():
        raise ActorContextValidationError("LDAP assertion subject is required.")
    if not isinstance(assertion.actor_type, ActorType):
        raise ActorContextValidationError("LDAP assertion actor type is invalid.")
    if not _is_aware(assertion.authenticated_at) or assertion.authenticated_at > now:
        raise ActorContextValidationError("LDAP assertion time is invalid.")
    if any(not group_id.strip() for group_id in assertion.group_ids):
        raise ActorContextValidationError("LDAP assertion group IDs must not be blank.")


def _is_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None
