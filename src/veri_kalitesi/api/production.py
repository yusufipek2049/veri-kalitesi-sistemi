"""Production-capable ASGI factory; trusted identity and secrets are injected."""

from __future__ import annotations

from veri_kalitesi.api.bff import BffSessionBoundary
from veri_kalitesi.api.composition import PhaseBProviders, create_application
from veri_kalitesi.api.settings import ApplicationSettings
from veri_kalitesi.data_sources.secrets import SecretResolver


def create_production_app(
    *,
    identity_provider: BffSessionBoundary,
    secret_resolver: SecretResolver,
    phase_b_providers: PhaseBProviders,
    settings: ApplicationSettings | None = None,
):
    effective_settings = settings or ApplicationSettings.from_environment(
        runtime_environment="production"
    )
    if effective_settings.runtime_environment != "production":
        raise ValueError("Production app requires production settings.")
    return create_application(
        effective_settings,
        identity_provider,
        secret_resolver=secret_resolver,
        phase_b_providers=phase_b_providers,
    )
