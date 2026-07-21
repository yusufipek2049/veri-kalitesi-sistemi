"""Surumlu ve fail-closed ortam baslangic kapisi."""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from veri_kalitesi.environment_security.errors import (
    EnvironmentConfigurationTechnicalError,
    EnvironmentConfigurationValidationError,
    EnvironmentPolicyBlockedError,
)
from veri_kalitesi.environment_security.models import (
    ENVIRONMENT_POLICY_VERSION,
    TRUSTED_CONFIGURATION_SOURCE_CONTRACT,
    DataOrigin,
    EnvironmentConfiguration,
    EnvironmentStartupEvidence,
    RuntimeEnvironment,
    SecretScope,
    TrustedEnvironmentConfigurationProvider,
)


_REVISION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_SECRET_PATH_PATTERN = re.compile(r"^/[A-Za-z0-9][A-Za-z0-9._/-]{0,255}$")
_SECRET_SCOPE_BY_HOST = {
    "local": SecretScope.LOCAL,
    "development": SecretScope.DEVELOPMENT,
    "test": SecretScope.TEST,
    "acceptance": SecretScope.ACCEPTANCE,
    "production": SecretScope.PRODUCTION,
}
_EXPECTED_SECRET_SCOPE = {
    RuntimeEnvironment.LOCAL: SecretScope.LOCAL,
    RuntimeEnvironment.DEVELOPMENT: SecretScope.DEVELOPMENT,
    RuntimeEnvironment.TEST: SecretScope.TEST,
    RuntimeEnvironment.ACCEPTANCE: SecretScope.ACCEPTANCE,
    RuntimeEnvironment.PRODUCTION: SecretScope.PRODUCTION,
}
_NON_PRODUCTION_ENVIRONMENTS = frozenset(
    {
        RuntimeEnvironment.LOCAL,
        RuntimeEnvironment.DEVELOPMENT,
        RuntimeEnvironment.TEST,
        RuntimeEnvironment.ACCEPTANCE,
    }
)
_ALLOWED_DATA_ORIGINS = {
    RuntimeEnvironment.LOCAL: frozenset({DataOrigin.SYNTHETIC}),
    RuntimeEnvironment.DEVELOPMENT: frozenset({DataOrigin.SYNTHETIC, DataOrigin.ANONYMIZED}),
    RuntimeEnvironment.TEST: frozenset(
        {DataOrigin.SYNTHETIC, DataOrigin.ANONYMIZED, DataOrigin.MASKED_APPROVED}
    ),
    RuntimeEnvironment.ACCEPTANCE: frozenset(
        {DataOrigin.SYNTHETIC, DataOrigin.ANONYMIZED, DataOrigin.MASKED_APPROVED}
    ),
    RuntimeEnvironment.PRODUCTION: frozenset(DataOrigin),
}


class EnvironmentStartupGate:
    """Guvenilir ortam kaynagini dogrular ve guvenli baslangic kaniti uretir."""

    def __init__(self, provider: TrustedEnvironmentConfigurationProvider) -> None:
        self._provider = provider

    def verify(self) -> EnvironmentStartupEvidence:
        try:
            trust_contract_version = getattr(self._provider, "trust_contract_version", None)
        except Exception as exc:
            raise EnvironmentConfigurationTechnicalError(
                "ENVIRONMENT_CONFIGURATION_SOURCE_UNAVAILABLE"
            ) from exc
        if trust_contract_version != TRUSTED_CONFIGURATION_SOURCE_CONTRACT:
            raise EnvironmentConfigurationValidationError("TRUSTED_CONFIGURATION_SOURCE_REQUIRED")

        try:
            configuration = self._provider.load_verified()
        except Exception as exc:
            raise EnvironmentConfigurationTechnicalError(
                "ENVIRONMENT_CONFIGURATION_SOURCE_UNAVAILABLE"
            ) from exc

        self._validate_configuration(configuration)
        secret_scope = self._secret_scope(configuration.secret_reference)
        self._enforce_policy(configuration, secret_scope)

        return EnvironmentStartupEvidence(
            policy_version=configuration.policy_version,
            configuration_revision=configuration.configuration_revision,
            environment=configuration.environment,
            data_origin=configuration.data_origin,
            secret_scope=secret_scope,
            checks=(
                "TRUSTED_CONFIGURATION_SOURCE_VERIFIED",
                "ENVIRONMENT_IDENTITY_VERIFIED",
                "DATA_ORIGIN_POLICY_VERIFIED",
                "SECRET_SCOPE_POLICY_VERIFIED",
            ),
        )

    def _validate_configuration(self, configuration: object) -> None:
        if not isinstance(configuration, EnvironmentConfiguration):
            raise EnvironmentConfigurationValidationError("ENVIRONMENT_CONFIGURATION_TYPE_INVALID")
        if configuration.policy_version != ENVIRONMENT_POLICY_VERSION:
            raise EnvironmentConfigurationValidationError("ENVIRONMENT_POLICY_VERSION_UNSUPPORTED")
        if not _REVISION_PATTERN.fullmatch(configuration.configuration_revision):
            raise EnvironmentConfigurationValidationError(
                "ENVIRONMENT_CONFIGURATION_REVISION_INVALID"
            )
        if not isinstance(configuration.environment, RuntimeEnvironment):
            raise EnvironmentConfigurationValidationError("ENVIRONMENT_IDENTITY_INVALID")
        if not isinstance(configuration.data_origin, DataOrigin):
            raise EnvironmentConfigurationValidationError("DATA_ORIGIN_INVALID")

    def _secret_scope(self, secret_reference: str) -> SecretScope:
        if not isinstance(secret_reference, str):
            raise EnvironmentConfigurationValidationError("SECRET_REFERENCE_INVALID")
        try:
            parsed = urlsplit(secret_reference)
            hostname = parsed.hostname
            port = parsed.port
        except ValueError as exc:
            raise EnvironmentConfigurationValidationError("SECRET_REFERENCE_INVALID") from exc
        if (
            parsed.scheme != "secret"
            or parsed.username is not None
            or parsed.password is not None
            or port is not None
            or parsed.query
            or parsed.fragment
            or not hostname
            or not _SECRET_PATH_PATTERN.fullmatch(parsed.path)
            or any(segment in {".", ".."} for segment in parsed.path.split("/"))
        ):
            raise EnvironmentConfigurationValidationError("SECRET_REFERENCE_INVALID")
        try:
            return _SECRET_SCOPE_BY_HOST[hostname]
        except KeyError as exc:
            raise EnvironmentConfigurationValidationError("SECRET_REFERENCE_SCOPE_UNKNOWN") from exc

    def _enforce_policy(
        self,
        configuration: EnvironmentConfiguration,
        secret_scope: SecretScope,
    ) -> None:
        if (
            configuration.environment in _NON_PRODUCTION_ENVIRONMENTS
            and configuration.data_origin is DataOrigin.BANK_PRODUCTION
        ):
            raise EnvironmentPolicyBlockedError("BANK_PRODUCTION_DATA_FORBIDDEN_OUTSIDE_PRODUCTION")
        if configuration.data_origin not in _ALLOWED_DATA_ORIGINS[configuration.environment]:
            raise EnvironmentPolicyBlockedError("DATA_ORIGIN_ENVIRONMENT_MISMATCH")
        if secret_scope is SecretScope.PRODUCTION and (
            configuration.environment in _NON_PRODUCTION_ENVIRONMENTS
        ):
            raise EnvironmentPolicyBlockedError("PRODUCTION_SECRET_FORBIDDEN_OUTSIDE_PRODUCTION")
        if secret_scope is not _EXPECTED_SECRET_SCOPE[configuration.environment]:
            raise EnvironmentPolicyBlockedError("SECRET_SCOPE_ENVIRONMENT_MISMATCH")
