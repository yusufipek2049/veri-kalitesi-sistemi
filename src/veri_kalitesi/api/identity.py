"""HTTP isteğini güvenilir aktör bağlamına dönüştüren adaptör sınırı."""

from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True)
class DevelopmentUser:
    """Geliştirme ortamında kullanılabilecek sentetik kullanıcı profili."""

    user_id: str
    display_name: str
    roles: frozenset[str]
    permitted_source_ids: frozenset[str]
    permitted_dataset_ids: frozenset[str]
    can_view_enterprise: bool = False
    privileged: bool = False
    actor_id: str | None = None

    @property
    def effective_actor_id(self) -> str:
        """Domain kayıtlarında kullanılan kanonik kullanıcı kimliği."""

        return self.actor_id or self.user_id


class DevelopmentUserRegistry:
    """Geliştirme ortamında kullanılabilecek kullanıcıları tutar.

    Yalnız development ortamında kullanılır. Gerçek IdP/LDAP bağlantısı değildir.
    """

    def __init__(self, users: list[DevelopmentUser] | None = None) -> None:
        self._users: dict[str, DevelopmentUser] = {}
        self._users_by_actor_id: dict[str, DevelopmentUser] = {}
        self._active_user_id: str | None = None
        if users:
            for user in users:
                self._users[user.user_id] = user
                self._users_by_actor_id[user.effective_actor_id] = user

    def register(self, user: DevelopmentUser) -> None:
        self._users[user.user_id] = user
        self._users_by_actor_id[user.effective_actor_id] = user

    def list_users(self) -> list[DevelopmentUser]:
        return list(self._users.values())

    def get_user(self, user_id: str) -> DevelopmentUser | None:
        return self._users.get(user_id) or self._users_by_actor_id.get(user_id)

    def set_active_user(self, user_id: str) -> DevelopmentUser | None:
        if user_id in self._users:
            self._active_user_id = user_id
            return self._users[user_id]
        return None

    def get_active_user(self) -> DevelopmentUser | None:
        if self._active_user_id:
            return self._users.get(self._active_user_id)
        return None

    def available_users(self) -> list[dict[str, str]]:
        return [
            {
                "user_id": u.user_id,
                "display_name": u.display_name,
                "roles": " / ".join(sorted(u.roles)),
            }
            for u in self._users.values()
        ]


def build_default_development_users() -> list[DevelopmentUser]:
    """Varsayılan geliştirme kullanıcılarını oluşturur.

    Her kullanıcı farklı rol ve kapsam kombinasyonuna sahiptir,
    böylece yetki farklılıkları test edilebilir.
    """
    all_source_ids = frozenset(
        {
            "source-core-banking",
            "source-customer-file",
            "source-risk-mart",
            "source-regulatory-api",
        }
    )
    all_dataset_ids = frozenset(
        {
            "dataset-customer",
            "dataset-account",
            "dataset-risk",
            "dataset-transaction",
        }
    )
    limited_sources = frozenset({"source-core-banking", "source-customer-file"})
    limited_datasets = frozenset({"dataset-customer", "dataset-account"})

    return [
        DevelopmentUser(
            user_id="dev-data-viewer",
            display_name="Veri Görüntüleyici (DATA_VIEWER)",
            roles=frozenset({"DATA_VIEWER"}),
            permitted_source_ids=all_source_ids,
            permitted_dataset_ids=all_dataset_ids,
            can_view_enterprise=True,
            actor_id="33333333-3333-4333-8333-333333333333",
        ),
        DevelopmentUser(
            user_id="dev-data-steward",
            display_name="Data Steward (DATA_STEWARD)",
            roles=frozenset({"DATA_VIEWER", "DATA_STEWARD"}),
            permitted_source_ids=all_source_ids,
            permitted_dataset_ids=all_dataset_ids,
            can_view_enterprise=True,
            actor_id="11111111-1111-4111-8111-111111111111",
        ),
        DevelopmentUser(
            user_id="dev-data-owner",
            display_name="Data Owner (DATA_OWNER)",
            roles=frozenset({"DATA_VIEWER", "DATA_OWNER"}),
            permitted_source_ids=all_source_ids,
            permitted_dataset_ids=all_dataset_ids,
            can_view_enterprise=True,
            actor_id="22222222-2222-4222-8222-222222222222",
        ),
        DevelopmentUser(
            user_id="dev-data-steward-owner",
            display_name="Maker/Checker Negatif Test (DATA_STEWARD / DATA_OWNER)",
            roles=frozenset({"DATA_VIEWER", "DATA_STEWARD", "DATA_OWNER"}),
            permitted_source_ids=all_source_ids,
            permitted_dataset_ids=all_dataset_ids,
            can_view_enterprise=True,
            actor_id="66666666-6666-4666-8666-666666666666",
        ),
        DevelopmentUser(
            user_id="dev-data-governance",
            display_name="Veri Yönetişim Uzmanı (DATA_GOVERNANCE_SPECIALIST)",
            roles=frozenset({"DATA_VIEWER", "DATA_GOVERNANCE_SPECIALIST"}),
            permitted_source_ids=all_source_ids,
            permitted_dataset_ids=all_dataset_ids,
            can_view_enterprise=True,
            actor_id="44444444-4444-4444-8444-444444444444",
        ),
        DevelopmentUser(
            user_id="dev-data-engineer",
            display_name="Veri Mühendisi (DATA_ENGINEER)",
            roles=frozenset({"DATA_VIEWER", "DATA_ENGINEER"}),
            permitted_source_ids=all_source_ids,
            permitted_dataset_ids=all_dataset_ids,
            can_view_enterprise=True,
            actor_id="55555555-5555-4555-8555-555555555555",
        ),
        DevelopmentUser(
            user_id="dev-audit-viewer",
            display_name="Denetim Görüntüleyici (AUDIT_VIEWER)",
            roles=frozenset({"DATA_VIEWER", "AUDIT_VIEWER"}),
            permitted_source_ids=all_source_ids,
            permitted_dataset_ids=all_dataset_ids,
            # Denetçi salt okunur görünüm için kurumsal kapsama sahiptir;
            # karar/uygulama rolleri verilmez.
            can_view_enterprise=True,
            actor_id="77777777-7777-4777-8777-777777777777",
        ),
        DevelopmentUser(
            user_id="dev-limited-steward",
            display_name="Sınırlı Data Steward (sadece 2 kaynak)",
            roles=frozenset({"DATA_VIEWER", "DATA_STEWARD"}),
            permitted_source_ids=limited_sources,
            permitted_dataset_ids=limited_datasets,
            can_view_enterprise=False,
            actor_id="88888888-8888-4888-8888-888888888888",
        ),
        DevelopmentUser(
            user_id="dev-privileged-user",
            display_name="Ayrıcalıklı Kullanıcı (privileged)",
            roles=frozenset({"DATA_VIEWER", "DATA_STEWARD"}),
            permitted_source_ids=all_source_ids,
            permitted_dataset_ids=all_dataset_ids,
            can_view_enterprise=True,
            privileged=True,
            actor_id="99999999-9999-4999-8999-999999999999",
        ),
    ]


class DevelopmentActorContextResolver:
    """Yalnız yerel geliştirme/test için sunucu taraflı sentetik aktör üretir.

    Çok kullanıcılı geliştirme modu: DevelopmentUserRegistry üzerinden
    kullanıcı seçimi yapılabilir.
    """

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
        user_registry: DevelopmentUserRegistry | None = None,
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
        self.user_registry = user_registry
        self._enterprise_source_scope_provider: Callable[[], frozenset[str]] | None = None
        self._enterprise_dataset_scope_provider: Callable[[], frozenset[str]] | None = None

    def bind_enterprise_source_scope_provider(self, provider: Callable[[], frozenset[str]]) -> None:
        """Dev IdP benzetiminde enterprise profillerine güncel açık scope üretir."""

        if self._enterprise_source_scope_provider is not None:
            raise ApiConfigurationError(
                "Development source scope provider is already bound.",
                "api-startup",
            )
        self._enterprise_source_scope_provider = provider

    def bind_enterprise_dataset_scope_provider(
        self, provider: Callable[[], frozenset[str]]
    ) -> None:
        """Enterprise dev kullanıcıları için güncel dataset kapsamı bağlar."""

        if self._enterprise_dataset_scope_provider is not None:
            raise ApiConfigurationError(
                "Development dataset scope provider is already bound.",
                "api-startup",
            )
        self._enterprise_dataset_scope_provider = provider

    def _resolve_user(
        self, request: Request
    ) -> tuple[str, frozenset[str], frozenset[str], frozenset[str], bool, bool]:
        """İstekteki kullanıcıyı belirler.

        Eğer X-Development-User-Id header'ı varsa ve kayıtlı bir kullanıcıysa
        o kullanıcının bilgilerini kullanır. Yoksa varsayılan yapılandırmayı kullanır.
        """
        dev_user_id = request.headers.get("X-Development-User-Id")
        if dev_user_id and self.user_registry:
            user = self.user_registry.get_user(dev_user_id)
            if user:
                source_ids = user.permitted_source_ids
                dataset_ids = user.permitted_dataset_ids
                if user.can_view_enterprise and self._enterprise_source_scope_provider:
                    source_ids = source_ids | self._enterprise_source_scope_provider()
                if user.can_view_enterprise and self._enterprise_dataset_scope_provider:
                    dataset_ids = dataset_ids | self._enterprise_dataset_scope_provider()
                return (
                    user.effective_actor_id,
                    user.roles,
                    source_ids,
                    dataset_ids,
                    user.can_view_enterprise,
                    user.privileged,
                )
        return (
            "development-dashboard-user",
            self.roles,
            self.permitted_source_ids,
            self.permitted_dataset_ids,
            self.can_view_enterprise,
            False,
        )

    def resolve(self, request: Request) -> ActorContext:
        issued_at = self.clock().astimezone(timezone.utc)
        (
            actor_id,
            roles,
            source_ids,
            dataset_ids,
            can_view_enterprise,
            privileged,
        ) = self._resolve_user(request)
        return self.issuer.issue(
            actor_id=actor_id,
            actor_type=ActorType.USER,
            authentication_source="development-only-adapter",
            session_id="development-only-session",
            roles=roles,
            permitted_source_ids=source_ids,
            permitted_dataset_ids=dataset_ids,
            can_view_enterprise=can_view_enterprise,
            privileged=privileged,
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
