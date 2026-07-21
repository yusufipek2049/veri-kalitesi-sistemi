"""Fail-closed ortam kimligi icin veri-minimum modeller."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol


ENVIRONMENT_POLICY_VERSION = "27A-v1"
TRUSTED_CONFIGURATION_SOURCE_CONTRACT = "27A-trusted-source-v1"


class RuntimeEnvironment(str, Enum):
    LOCAL = "LOCAL"
    DEVELOPMENT = "DEVELOPMENT"
    TEST = "TEST"
    ACCEPTANCE = "ACCEPTANCE"
    PRODUCTION = "PRODUCTION"


class DataOrigin(str, Enum):
    SYNTHETIC = "SYNTHETIC"
    ANONYMIZED = "ANONYMIZED"
    MASKED_APPROVED = "MASKED_APPROVED"
    BANK_PRODUCTION = "BANK_PRODUCTION"


class SecretScope(str, Enum):
    LOCAL = "LOCAL"
    DEVELOPMENT = "DEVELOPMENT"
    TEST = "TEST"
    ACCEPTANCE = "ACCEPTANCE"
    PRODUCTION = "PRODUCTION"


@dataclass(frozen=True)
class EnvironmentConfiguration:
    policy_version: str
    configuration_revision: str
    environment: RuntimeEnvironment
    data_origin: DataOrigin
    secret_reference: str = field(repr=False)


class TrustedEnvironmentConfigurationProvider(Protocol):
    trust_contract_version: str

    def load_verified(self) -> EnvironmentConfiguration:
        """Guvenilir dagitim konfigurasyonundan dogrulanmis ortam bilgisini yukle."""


@dataclass(frozen=True)
class EnvironmentStartupEvidence:
    policy_version: str
    configuration_revision: str
    environment: RuntimeEnvironment
    data_origin: DataOrigin
    secret_scope: SecretScope
    checks: tuple[str, ...]
    status: str = "PASSED"
