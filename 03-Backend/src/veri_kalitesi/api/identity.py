"""HTTP isteğini güvenilir aktör bağlamına dönüştüren adaptör sınırı."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Callable, Protocol

from fastapi import Request

from veri_kalitesi.api.errors import ApiAuthenticationError, ApiConfigurationError
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
        self.policy_version = policy_version
        self.permitted_source_ids = permitted_source_ids
        self.permitted_dataset_ids = permitted_dataset_ids
        self.can_view_enterprise = can_view_enterprise
        self.clock = clock
        self.issuer = ActorContextIssuer()

    def resolve(self, request: Request) -> ActorContext:
        issued_at = self.clock().astimezone(timezone.utc)
        return self.issuer.issue(
            actor_id="development-dashboard-user",
            actor_type=ActorType.USER,
            authentication_source="development-only-adapter",
            session_id="development-only-session",
            roles=frozenset({"DATA_VIEWER"}),
            permitted_source_ids=self.permitted_source_ids,
            permitted_dataset_ids=self.permitted_dataset_ids,
            can_view_enterprise=self.can_view_enterprise,
            privileged=False,
            issued_at=issued_at,
            expires_at=issued_at + timedelta(minutes=15),
            policy_version=self.policy_version,
            correlation_id=request.state.correlation_id,
        )
