"""HTTP isteğini güvenilir aktör bağlamına dönüştüren adaptör sınırı."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Callable, Protocol

from fastapi import Request

from veri_kalitesi.api.bff import CSRF_HEADER_NAME
from veri_kalitesi.api.errors import (
    ApiAuthenticationError,
    ApiConfigurationError,
    ApiCsrfError,
)
from veri_kalitesi.identity import ActorContext, ActorContextIssuer, ActorType


class ActorContextResolver(Protocol):
    def resolve(self, request: Request) -> ActorContext: ...


class UnavailableActorContextResolver:
    """Üretim oturum adaptörü bağlı değilken varsayılan olarak erişimi reddeder."""

    def resolve(self, request: Request) -> ActorContext:
        raise ApiAuthenticationError(
            "Authenticated session could not be established.",
            request.state.correlation_id,
        )


class DevelopmentActorContextResolver:
    """Yalnız yerel geliştirme/test için sunucu taraflı sentetik aktör üretir."""

    def __init__(
        self,
        *,
        runtime_environment: str,
        policy_version: str,
        permitted_source_ids: frozenset[str],
        can_view_enterprise: bool,
        permitted_dataset_ids: frozenset[str] = frozenset(),
        roles: frozenset[str] = frozenset({"DATA_VIEWER"}),
        allowed_origins: frozenset[str] = frozenset(),
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        if runtime_environment != "development":
            raise ApiConfigurationError(
                "Development actor resolver is restricted to development.",
                "api-startup",
            )
        if not policy_version.strip():
            raise ApiConfigurationError("Policy version is required.", "api-startup")
        if any(not source_id.strip() for source_id in permitted_source_ids):
            raise ApiConfigurationError(
                "Development source identifiers must not be blank.",
                "api-startup",
            )
        if any(not dataset_id.strip() for dataset_id in permitted_dataset_ids):
            raise ApiConfigurationError(
                "Development dataset identifiers must not be blank.",
                "api-startup",
            )
        if not roles or any(not role.strip() for role in roles):
            raise ApiConfigurationError(
                "Development roles must not be empty or blank.",
                "api-startup",
            )
        self.policy_version = policy_version
        self.permitted_source_ids = permitted_source_ids
        self.permitted_dataset_ids = permitted_dataset_ids
        self.roles = roles
        self.allowed_origins = allowed_origins
        self.can_view_enterprise = can_view_enterprise
        self.clock = clock
        self.issuer = ActorContextIssuer()
        self.request_proof = "development-request-proof-v1"

    def resolve(self, request: Request) -> ActorContext:
        issued_at = self.clock().astimezone(timezone.utc)
        return self.issuer.issue(
            actor_id="development-dashboard-user",
            actor_type=ActorType.USER,
            authentication_source="development-only-adapter",
            session_id="development-only-session",
            roles=self.roles,
            permitted_source_ids=self.permitted_source_ids,
            permitted_dataset_ids=self.permitted_dataset_ids,
            can_view_enterprise=self.can_view_enterprise,
            privileged=False,
            issued_at=issued_at,
            expires_at=issued_at + timedelta(minutes=15),
            policy_version=self.policy_version,
            correlation_id=request.state.correlation_id,
        )

    def protect_state_changing(self, request: Request) -> ActorContext:
        origin = request.headers.get("Origin")
        referer = request.headers.get("Referer")
        fetch_site = request.headers.get("Sec-Fetch-Site")
        proof = request.headers.get(CSRF_HEADER_NAME)
        if (
            not self.allowed_origins
            or origin not in self.allowed_origins
            or referer is None
            or not referer.startswith(f"{origin}/")
            or fetch_site not in {"same-origin", "same-site"}
            or proof != self.request_proof
        ):
            raise ApiCsrfError(
                "Development state-changing request could not be verified.",
                request.state.correlation_id,
            )
        context = self.resolve(request)
        request.state.actor_context = context
        return context
