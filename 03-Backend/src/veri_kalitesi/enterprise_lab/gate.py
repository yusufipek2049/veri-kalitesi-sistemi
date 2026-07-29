"""ENTERPRISE-LAB-01 icin veri-minimum, fail-closed baslangic kapisi."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit

from veri_kalitesi.environment_security import (
    ENVIRONMENT_POLICY_VERSION,
    DataOrigin,
    EnvironmentConfiguration,
    EnvironmentStartupGate,
    RuntimeEnvironment,
)
from veri_kalitesi.environment_security.errors import EnvironmentSecurityError


ENTERPRISE_LAB_POLICY_VERSION = "ENTERPRISE-LAB-01-v1"
_CLASSIFICATION = "PrototypeVerified"
_LAB_ID_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9-]{0,63}$")
_EXPECTED_ENDPOINTS = {
    "identity": ("http", "keycloak", 8080),
    "secret_manager": ("http", "local-secret-manager", 8080),
    "postgres_primary": ("postgresql", "postgres-primary", 5432),
    "postgres_standby": ("postgresql", "postgres-standby", 5432),
    "message_broker": ("amqp", "rabbitmq", 5672),
    "servicenow": ("http", "fake-servicenow", 8080),
    "siem": ("http", "siem-collector", 8080),
    "evidence_store": ("http", "evidence-store", 8080),
}
_REQUIRED_ENDPOINTS = frozenset(_EXPECTED_ENDPOINTS)
_ALLOWED_SCHEMES = frozenset(endpoint[0] for endpoint in _EXPECTED_ENDPOINTS.values())
_ALLOWED_HOSTS = frozenset(endpoint[1] for endpoint in _EXPECTED_ENDPOINTS.values())
_ALLOWED_PORTS = frozenset(endpoint[2] for endpoint in _EXPECTED_ENDPOINTS.values())
_EXACT_FIELDS = frozenset(
    {
        "schema_version",
        "lab_id",
        "policy_version",
        "classification",
        "trust_contract_version",
        "environment",
        "data_origin",
        "secret_reference",
        "endpoints",
    }
)


class EnterpriseLabConfigurationError(Exception):
    """Lab konfigurasyonu gecersiz veya politika tarafindan engellendi."""

    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


@dataclass(frozen=True)
class EnterpriseLabEvidence:
    lab_id: str
    policy_version: str
    classification: str
    environment: str
    data_origin: str
    endpoint_count: int
    checks: tuple[str, ...]
    status: str = "PASSED"


@dataclass(frozen=True)
class _PinnedFileProvider:
    configuration: EnvironmentConfiguration
    trust_contract_version: str

    def load_verified(self) -> EnvironmentConfiguration:
        return self.configuration


def verify_enterprise_lab_configuration(path: Path) -> EnterpriseLabEvidence:
    payload = _load_payload(path)
    if frozenset(payload) != _EXACT_FIELDS:
        raise EnterpriseLabConfigurationError("LAB_CONFIGURATION_FIELDS_INVALID")
    if payload.get("schema_version") != 1:
        raise EnterpriseLabConfigurationError("LAB_SCHEMA_VERSION_UNSUPPORTED")
    if payload.get("policy_version") != ENTERPRISE_LAB_POLICY_VERSION:
        raise EnterpriseLabConfigurationError("LAB_POLICY_VERSION_UNSUPPORTED")
    if payload.get("classification") != _CLASSIFICATION:
        raise EnterpriseLabConfigurationError("LAB_CLASSIFICATION_INVALID")

    lab_id = payload.get("lab_id")
    if not isinstance(lab_id, str) or not _LAB_ID_PATTERN.fullmatch(lab_id):
        raise EnterpriseLabConfigurationError("LAB_ID_INVALID")

    environment = _enum_value(
        RuntimeEnvironment,
        payload.get("environment"),
        "LAB_ENVIRONMENT_INVALID",
    )
    if environment is RuntimeEnvironment.PRODUCTION:
        raise EnterpriseLabConfigurationError("PRODUCTION_ENVIRONMENT_FORBIDDEN")

    data_origin = _enum_value(DataOrigin, payload.get("data_origin"), "LAB_DATA_ORIGIN_INVALID")
    if data_origin is not DataOrigin.SYNTHETIC:
        raise EnterpriseLabConfigurationError("NON_SYNTHETIC_DATA_FORBIDDEN")

    provider = _PinnedFileProvider(
        configuration=EnvironmentConfiguration(
            policy_version=ENVIRONMENT_POLICY_VERSION,
            configuration_revision=ENTERPRISE_LAB_POLICY_VERSION,
            environment=environment,
            data_origin=data_origin,
            secret_reference=_required_string(payload, "secret_reference"),
        ),
        trust_contract_version=_required_string(payload, "trust_contract_version"),
    )
    try:
        EnvironmentStartupGate(provider).verify()
    except EnvironmentSecurityError as exc:
        raise EnterpriseLabConfigurationError(exc.reason_code) from exc

    endpoints = payload.get("endpoints")
    if not isinstance(endpoints, dict) or frozenset(endpoints) != _REQUIRED_ENDPOINTS:
        raise EnterpriseLabConfigurationError("LAB_ENDPOINT_SET_INVALID")
    for endpoint_name, endpoint in endpoints.items():
        _validate_internal_endpoint(endpoint_name, endpoint)

    return EnterpriseLabEvidence(
        lab_id=lab_id,
        policy_version=ENTERPRISE_LAB_POLICY_VERSION,
        classification=_CLASSIFICATION,
        environment=environment.value,
        data_origin=data_origin.value,
        endpoint_count=len(endpoints),
        checks=(
            "PINNED_CONFIGURATION_VERIFIED",
            "NON_PRODUCTION_ENVIRONMENT_VERIFIED",
            "SYNTHETIC_DATA_ORIGIN_VERIFIED",
            "LOCAL_SECRET_SCOPE_VERIFIED",
            "INTERNAL_ENDPOINT_ALLOWLIST_VERIFIED",
        ),
    )


def evidence_as_json(evidence: EnterpriseLabEvidence) -> str:
    return json.dumps(asdict(evidence), ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _load_payload(path: Path) -> Mapping[str, Any]:
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 64 * 1024:
            raise EnterpriseLabConfigurationError("LAB_CONFIGURATION_FILE_INVALID")
        payload = json.loads(path.read_text(encoding="utf-8"))
    except EnterpriseLabConfigurationError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EnterpriseLabConfigurationError("LAB_CONFIGURATION_UNAVAILABLE") from exc
    if not isinstance(payload, dict):
        raise EnterpriseLabConfigurationError("LAB_CONFIGURATION_TYPE_INVALID")
    return payload


def _enum_value(enum_type: type[Any], value: Any, reason_code: str) -> Any:
    if not isinstance(value, str):
        raise EnterpriseLabConfigurationError(reason_code)
    try:
        return enum_type(value)
    except ValueError as exc:
        raise EnterpriseLabConfigurationError(reason_code) from exc


def _required_string(payload: Mapping[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str):
        raise EnterpriseLabConfigurationError("LAB_CONFIGURATION_FIELD_INVALID")
    return value


def _validate_internal_endpoint(endpoint_name: str, endpoint: Any) -> None:
    if not isinstance(endpoint, str):
        raise EnterpriseLabConfigurationError("LAB_ENDPOINT_INVALID")
    try:
        parsed = urlsplit(endpoint)
        port = parsed.port
    except ValueError as exc:
        raise EnterpriseLabConfigurationError("LAB_ENDPOINT_INVALID") from exc
    if (
        parsed.scheme not in _ALLOWED_SCHEMES
        or parsed.hostname not in _ALLOWED_HOSTS
        or port not in _ALLOWED_PORTS
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise EnterpriseLabConfigurationError("EXTERNAL_OR_SECRET_ENDPOINT_FORBIDDEN")
    if (parsed.scheme, parsed.hostname, port) != _EXPECTED_ENDPOINTS[endpoint_name]:
        raise EnterpriseLabConfigurationError("LAB_ENDPOINT_ROLE_MISMATCH")
