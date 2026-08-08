"""PostgreSQL-only executable development ASGI composition."""

from __future__ import annotations

from veri_kalitesi.api.composition import PhaseBProviders, create_application
from veri_kalitesi.api.identity import (
    DevelopmentActorContextResolver,
    DevelopmentUserRegistry,
    build_default_development_users,
)
from veri_kalitesi.api.settings import ApplicationSettings
from veri_kalitesi.data_sources.secrets import MountedFileSecretResolver


def create_development_app(
    *,
    settings: ApplicationSettings | None = None,
    user_registry: DevelopmentUserRegistry | None = None,
    phase_b_providers: PhaseBProviders | None = None,
):
    """Ortak PostgreSQL composition'ını yalnız dev identity/resolver ile kurar."""

    effective_settings = settings or ApplicationSettings.from_environment(
        runtime_environment="development"
    )
    if effective_settings.runtime_environment != "development":
        raise ValueError("Persistent development app requires development settings.")
    if effective_settings.local_secret_dir is None:
        raise RuntimeError("DATA_QUALITY_LOCAL_SECRET_DIR is required for development runtime.")
    effective_registry = user_registry or DevelopmentUserRegistry(build_default_development_users())
    resolver = DevelopmentActorContextResolver(
        runtime_environment="development",
        policy_version=effective_settings.actor_policy_version,
        permitted_source_ids=frozenset(),
        permitted_dataset_ids=frozenset(),
        roles=frozenset({"DATA_VIEWER"}),
        allowed_origins=frozenset(effective_settings.allowed_origins),
        can_view_enterprise=False,
        user_registry=effective_registry,
    )
    return create_application(
        effective_settings,
        resolver,
        secret_resolver=MountedFileSecretResolver(effective_settings.local_secret_dir),
        development_user_registry=effective_registry,
        phase_b_providers=phase_b_providers,
    )
