from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, cast

import pytest

from veri_kalitesi.environment_security import (
    ENVIRONMENT_POLICY_VERSION,
    TRUSTED_CONFIGURATION_SOURCE_CONTRACT,
    DataOrigin,
    EnvironmentConfiguration,
    EnvironmentConfigurationTechnicalError,
    EnvironmentConfigurationValidationError,
    EnvironmentPolicyBlockedError,
    EnvironmentStartupGate,
    RuntimeEnvironment,
    SecretScope,
)


@dataclass
class FakeTrustedProvider:
    configuration: object
    trust_contract_version: str = TRUSTED_CONFIGURATION_SOURCE_CONTRACT
    error: Exception | None = None
    call_count: int = 0

    def load_verified(self) -> EnvironmentConfiguration:
        self.call_count += 1
        if self.error is not None:
            raise self.error
        return cast(EnvironmentConfiguration, self.configuration)


def _configuration(
    *,
    environment: RuntimeEnvironment = RuntimeEnvironment.DEVELOPMENT,
    data_origin: DataOrigin = DataOrigin.SYNTHETIC,
    secret_reference: str = "secret://development/application",
    policy_version: str = ENVIRONMENT_POLICY_VERSION,
    configuration_revision: str = "release-27A.1",
) -> EnvironmentConfiguration:
    return EnvironmentConfiguration(
        policy_version=policy_version,
        configuration_revision=configuration_revision,
        environment=environment,
        data_origin=data_origin,
        secret_reference=secret_reference,
    )


@pytest.mark.parametrize(
    ("environment", "data_origin", "secret_reference", "expected_scope"),
    [
        (
            RuntimeEnvironment.LOCAL,
            DataOrigin.SYNTHETIC,
            "secret://local/application",
            SecretScope.LOCAL,
        ),
        (
            RuntimeEnvironment.DEVELOPMENT,
            DataOrigin.ANONYMIZED,
            "secret://development/application",
            SecretScope.DEVELOPMENT,
        ),
        (
            RuntimeEnvironment.TEST,
            DataOrigin.MASKED_APPROVED,
            "secret://test/application",
            SecretScope.TEST,
        ),
        (
            RuntimeEnvironment.ACCEPTANCE,
            DataOrigin.MASKED_APPROVED,
            "secret://acceptance/application",
            SecretScope.ACCEPTANCE,
        ),
        (
            RuntimeEnvironment.PRODUCTION,
            DataOrigin.BANK_PRODUCTION,
            "secret://production/application",
            SecretScope.PRODUCTION,
        ),
    ],
)
def test_bfr_ops_001_allows_environment_matched_startup(
    environment: RuntimeEnvironment,
    data_origin: DataOrigin,
    secret_reference: str,
    expected_scope: SecretScope,
) -> None:
    provider = FakeTrustedProvider(
        _configuration(
            environment=environment,
            data_origin=data_origin,
            secret_reference=secret_reference,
        )
    )

    evidence = EnvironmentStartupGate(provider).verify()

    assert evidence.status == "PASSED"
    assert evidence.environment is environment
    assert evidence.data_origin is data_origin
    assert evidence.secret_scope is expected_scope
    assert evidence.policy_version == ENVIRONMENT_POLICY_VERSION
    assert provider.call_count == 1


def test_brule_005_startup_evidence_and_repr_exclude_secret_reference() -> None:
    secret_reference = "secret://development/non-public-path"
    configuration = _configuration(secret_reference=secret_reference)

    evidence = EnvironmentStartupGate(FakeTrustedProvider(configuration)).verify()

    assert secret_reference not in repr(configuration)
    assert secret_reference not in repr(evidence)
    assert "secret_reference" not in asdict(evidence)
    assert evidence.checks == (
        "TRUSTED_CONFIGURATION_SOURCE_VERIFIED",
        "ENVIRONMENT_IDENTITY_VERIFIED",
        "DATA_ORIGIN_POLICY_VERIFIED",
        "SECRET_SCOPE_POLICY_VERIFIED",
    )


@pytest.mark.parametrize(
    "environment",
    [
        RuntimeEnvironment.LOCAL,
        RuntimeEnvironment.DEVELOPMENT,
        RuntimeEnvironment.TEST,
        RuntimeEnvironment.ACCEPTANCE,
    ],
)
def test_bfr_ops_002_rejects_bank_production_data_outside_production(
    environment: RuntimeEnvironment,
) -> None:
    provider = FakeTrustedProvider(
        _configuration(
            environment=environment,
            data_origin=DataOrigin.BANK_PRODUCTION,
            secret_reference=f"secret://{environment.value.lower()}/application",
        )
    )

    with pytest.raises(EnvironmentPolicyBlockedError) as error:
        EnvironmentStartupGate(provider).verify()

    assert error.value.reason_code == "BANK_PRODUCTION_DATA_FORBIDDEN_OUTSIDE_PRODUCTION"


@pytest.mark.parametrize(
    ("environment", "data_origin", "secret_reference"),
    [
        (
            RuntimeEnvironment.LOCAL,
            DataOrigin.ANONYMIZED,
            "secret://local/application",
        ),
        (
            RuntimeEnvironment.DEVELOPMENT,
            DataOrigin.MASKED_APPROVED,
            "secret://development/application",
        ),
    ],
)
def test_bfr_ops_001_rejects_data_origin_outside_environment_matrix(
    environment: RuntimeEnvironment,
    data_origin: DataOrigin,
    secret_reference: str,
) -> None:
    provider = FakeTrustedProvider(
        _configuration(
            environment=environment,
            data_origin=data_origin,
            secret_reference=secret_reference,
        )
    )

    with pytest.raises(EnvironmentPolicyBlockedError) as error:
        EnvironmentStartupGate(provider).verify()

    assert error.value.reason_code == "DATA_ORIGIN_ENVIRONMENT_MISMATCH"


@pytest.mark.parametrize(
    "environment",
    [
        RuntimeEnvironment.LOCAL,
        RuntimeEnvironment.DEVELOPMENT,
        RuntimeEnvironment.TEST,
        RuntimeEnvironment.ACCEPTANCE,
    ],
)
def test_nfr_sec_005_rejects_production_secret_outside_production(
    environment: RuntimeEnvironment,
) -> None:
    provider = FakeTrustedProvider(
        _configuration(
            environment=environment,
            secret_reference="secret://production/application",
        )
    )

    with pytest.raises(EnvironmentPolicyBlockedError) as error:
        EnvironmentStartupGate(provider).verify()

    assert error.value.reason_code == "PRODUCTION_SECRET_FORBIDDEN_OUTSIDE_PRODUCTION"


def test_bfr_ops_001_rejects_cross_environment_secret_scope() -> None:
    provider = FakeTrustedProvider(_configuration(secret_reference="secret://test/application"))

    with pytest.raises(EnvironmentPolicyBlockedError) as error:
        EnvironmentStartupGate(provider).verify()

    assert error.value.reason_code == "SECRET_SCOPE_ENVIRONMENT_MISMATCH"


def test_bfr_ops_001_rejects_provider_without_trusted_contract_before_read() -> None:
    provider = FakeTrustedProvider(_configuration(), trust_contract_version="untrusted-v1")

    with pytest.raises(EnvironmentConfigurationValidationError) as error:
        EnvironmentStartupGate(provider).verify()

    assert error.value.reason_code == "TRUSTED_CONFIGURATION_SOURCE_REQUIRED"
    assert provider.call_count == 0


def test_bfr_ops_001_rejects_direct_configuration_as_untrusted_input() -> None:
    gate = EnvironmentStartupGate(cast(Any, _configuration()))

    with pytest.raises(EnvironmentConfigurationValidationError) as error:
        gate.verify()

    assert error.value.reason_code == "TRUSTED_CONFIGURATION_SOURCE_REQUIRED"


def test_bfr_ops_001_separates_configuration_source_technical_error() -> None:
    provider = FakeTrustedProvider(
        _configuration(),
        error=RuntimeError("secret://production/must-not-leak"),
    )

    with pytest.raises(EnvironmentConfigurationTechnicalError) as error:
        EnvironmentStartupGate(provider).verify()

    assert error.value.reason_code == "ENVIRONMENT_CONFIGURATION_SOURCE_UNAVAILABLE"
    assert "production" not in str(error.value)


def test_nfr_sec_008_redacts_provider_validation_error() -> None:
    provider = FakeTrustedProvider(
        _configuration(),
        error=EnvironmentConfigurationValidationError("secret://production/must-not-leak"),
    )

    with pytest.raises(EnvironmentConfigurationTechnicalError) as error:
        EnvironmentStartupGate(provider).verify()

    assert error.value.reason_code == "ENVIRONMENT_CONFIGURATION_SOURCE_UNAVAILABLE"
    assert "production" not in str(error.value)


@pytest.mark.parametrize(
    ("configuration", "reason_code"),
    [
        (object(), "ENVIRONMENT_CONFIGURATION_TYPE_INVALID"),
        (
            _configuration(policy_version="27A-unknown"),
            "ENVIRONMENT_POLICY_VERSION_UNSUPPORTED",
        ),
        (
            _configuration(configuration_revision="invalid revision"),
            "ENVIRONMENT_CONFIGURATION_REVISION_INVALID",
        ),
        (
            _configuration(environment=cast(Any, "DEVELOPMENT")),
            "ENVIRONMENT_IDENTITY_INVALID",
        ),
        (
            _configuration(data_origin=cast(Any, "SYNTHETIC")),
            "DATA_ORIGIN_INVALID",
        ),
    ],
)
def test_bfr_ops_001_rejects_invalid_environment_configuration(
    configuration: object,
    reason_code: str,
) -> None:
    with pytest.raises(EnvironmentConfigurationValidationError) as error:
        EnvironmentStartupGate(FakeTrustedProvider(configuration)).verify()

    assert error.value.reason_code == reason_code


@pytest.mark.parametrize(
    ("secret_reference", "reason_code"),
    [
        ("plaintext", "SECRET_REFERENCE_INVALID"),
        ("secret://development", "SECRET_REFERENCE_INVALID"),
        ("secret://user@development/application", "SECRET_REFERENCE_INVALID"),
        ("secret://development/application?token=value", "SECRET_REFERENCE_INVALID"),
        ("secret://development:bad/application", "SECRET_REFERENCE_INVALID"),
        ("secret://development/../application", "SECRET_REFERENCE_INVALID"),
        ("secret://development/application name", "SECRET_REFERENCE_INVALID"),
        ("secret://unknown/application", "SECRET_REFERENCE_SCOPE_UNKNOWN"),
    ],
)
def test_nfr_sec_005_rejects_invalid_or_unknown_secret_reference(
    secret_reference: str,
    reason_code: str,
) -> None:
    with pytest.raises(EnvironmentConfigurationValidationError) as error:
        EnvironmentStartupGate(
            FakeTrustedProvider(_configuration(secret_reference=secret_reference))
        ).verify()

    assert error.value.reason_code == reason_code
    assert secret_reference not in str(error.value)
