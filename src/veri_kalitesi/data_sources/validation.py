"""Data source validation functions.

Pure validation logic extracted from the service module.  Every function
here is stateless and depends only on domain models and error types.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import datetime
from typing import Any, Protocol
from uuid import uuid4

from veri_kalitesi.data_sources.errors import ValidationError
from veri_kalitesi.data_sources.models import (
    DataSourceActivationPolicy,
    DataSourceActivationStatus,
    DataField,
    ErrorClass,
    MetadataDiscoveryOptions,
    ProfileMethod,
    ProfileOptions,
    SourceType,
)
from veri_kalitesi.data_sources.postgresql import is_read_only_sql

_FORBIDDEN_CONFIG_KEYS = {"password", "passwd", "token", "secret", "private_key", "api_key"}
_POSTGRESQL_SSL_MODES = {"require", "verify-ca", "verify-full"}


class BusinessCalendar(Protocol):
    @property
    def version(self) -> str: ...

    def add_business_days(self, start_at: datetime, business_days: int) -> datetime: ...


def _parse_source_type(source_type: str) -> SourceType:
    try:
        return SourceType(source_type.upper())
    except ValueError as exc:
        raise ValidationError("Unsupported source type.") from exc


def _resolve_correlation_id(correlation_id: str | None) -> str:
    if correlation_id is None:
        return str(uuid4())
    if not correlation_id.strip():
        raise ValidationError("correlation_id must not be blank.")
    return correlation_id


def _error_reason(error_class: ErrorClass | None) -> str:
    return error_class.value if error_class is not None else "UNKNOWN_TECHNICAL_ERROR"


def _parse_activation_decision(decision: str) -> DataSourceActivationStatus:
    normalized = decision.strip().upper()
    if normalized == "APPROVE":
        return DataSourceActivationStatus.APPROVED
    if normalized == "REJECT":
        return DataSourceActivationStatus.REJECTED
    raise ValidationError("Activation decision must be APPROVE or REJECT.")


def _validate_activation_policy(policy: DataSourceActivationPolicy) -> None:
    if not policy.version.strip() or not policy.actor_policy_version.strip():
        raise ValidationError("Data source activation policy versions are required.")
    if not policy.maker_roles or not policy.checker_roles:
        raise ValidationError("Data source activation maker and checker roles are required.")
    if any(
        not role.strip()
        for role in (
            *policy.creator_roles,
            *policy.connection_tester_roles,
            *policy.maker_roles,
            *policy.checker_roles,
            *policy.deactivator_roles,
        )
    ):
        raise ValidationError("Data source activation roles must not be blank.")
    if not policy.allowed_actor_types or not policy.allowed_actor_types <= {"USER", "SERVICE"}:
        raise ValidationError("Data source activation actor types are invalid.")
    timing = (
        policy.target_business_days,
        policy.expiration_business_days,
        policy.business_calendar_version,
    )
    if any(value is not None for value in timing) and not all(
        value is not None for value in timing
    ):
        raise ValidationError("Data source activation timing policy must be complete.")
    if policy.expiration_business_days is not None:
        target = policy.target_business_days
        expiration = policy.expiration_business_days
        if (
            isinstance(target, bool)
            or isinstance(expiration, bool)
            or not isinstance(target, int)
            or not isinstance(expiration, int)
            or target < 1
            or expiration <= target
        ):
            raise ValidationError("Data source activation business-day limits are invalid.")
        if not policy.business_calendar_version or not policy.business_calendar_version.strip():
            raise ValidationError("Data source activation business calendar version is required.")
        if not policy.expiry_service_roles or any(
            not role.strip() for role in policy.expiry_service_roles
        ):
            raise ValidationError("Data source activation expiry service roles are required.")


def _validate_activation_calendar(
    policy: DataSourceActivationPolicy, calendar: BusinessCalendar | None
) -> None:
    if policy.expiration_business_days is None:
        return
    if calendar is None:
        raise ValidationError("Data source activation business calendar is required.")
    if calendar.version != policy.business_calendar_version:
        raise ValidationError(
            "Data source activation business calendar version does not match policy."
        )


def _require_aware_time(value: datetime, label: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValidationError(f"{label} must be timezone-aware.")


def _validate_name(name: str) -> None:
    if not name or not name.strip():
        raise ValidationError("DataSource name is required.")
    if len(name.strip()) > 200:
        raise ValidationError("DataSource name must be at most 200 characters.")


def _validate_secret_reference(secret_reference: str) -> None:
    if not secret_reference or not secret_reference.startswith("secret://"):
        raise ValidationError("Secret reference must use the secret:// scheme.")


def _validate_connection_config(source_type: SourceType, config: Mapping[str, Any]) -> None:
    if not isinstance(config, Mapping):
        raise ValidationError("Connection config must be an object.")
    _reject_raw_secrets(config)
    if source_type is SourceType.CSV:
        file_path = config.get("file_path")
        if not file_path or not isinstance(file_path, str):
            raise ValidationError("CSV file_path is required.")
        delimiter = config.get("delimiter", ",")
        if not isinstance(delimiter, str) or len(delimiter) != 1:
            raise ValidationError("CSV delimiter must be a single character.")
        encoding = config.get("encoding", "utf-8")
        if not isinstance(encoding, str) or not encoding:
            raise ValidationError("CSV encoding must be a non-empty string.")
    elif source_type is SourceType.POSTGRESQL:
        _validate_postgresql_config(config)


def _reject_raw_secrets(config: Mapping[str, Any]) -> None:
    for key, value in config.items():
        key_normalized = str(key).lower()
        if key_normalized in _FORBIDDEN_CONFIG_KEYS:
            raise ValidationError("Connection config must not contain raw secret fields.")
        if isinstance(value, Mapping):
            _reject_raw_secrets(value)


def _validate_postgresql_config(config: Mapping[str, Any]) -> None:
    host = config.get("host")
    if not host or not isinstance(host, str):
        raise ValidationError("PostgreSQL host is required.")

    port = config.get("port")
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValidationError("PostgreSQL port must be an integer between 1 and 65535.")

    database = config.get("database")
    if not database or not isinstance(database, str):
        raise ValidationError("PostgreSQL database is required.")

    ssl_mode = config.get("ssl_mode")
    if ssl_mode not in _POSTGRESQL_SSL_MODES:
        raise ValidationError("PostgreSQL ssl_mode must require TLS verification.")

    connect_timeout_seconds = config.get("connect_timeout_seconds", 5)
    if (
        isinstance(connect_timeout_seconds, bool)
        or not isinstance(connect_timeout_seconds, int)
        or not 1 <= connect_timeout_seconds <= 60
    ):
        raise ValidationError("PostgreSQL connect_timeout_seconds must be between 1 and 60.")

    statement_timeout_ms = config.get("statement_timeout_ms", 5000)
    if (
        isinstance(statement_timeout_ms, bool)
        or not isinstance(statement_timeout_ms, int)
        or not 1 <= statement_timeout_ms <= 600_000
    ):
        raise ValidationError("PostgreSQL statement_timeout_ms must be between 1 and 600000.")

    test_query = config.get("test_query")
    if test_query is not None and (
        not isinstance(test_query, str) or not is_read_only_sql(test_query)
    ):
        raise ValidationError("PostgreSQL test_query must be a single read-only statement.")


def _validate_metadata_options(options: MetadataDiscoveryOptions) -> None:
    if options.page_size < 1 or options.page_size > 10_000:
        raise ValidationError("Metadata discovery page_size must be between 1 and 10000.")
    if options.max_objects < 1 or options.max_objects > 100_000:
        raise ValidationError("Metadata discovery max_objects must be between 1 and 100000.")
    if options.timeout_seconds < 1 or options.timeout_seconds > 3600:
        raise ValidationError("Metadata discovery timeout_seconds must be between 1 and 3600.")


def _validate_profile_options(options: ProfileOptions) -> None:
    if options.method is ProfileMethod.SAMPLE:
        if options.sample_ratio is None or not 0 < options.sample_ratio <= 1:
            raise ValidationError("Sample profile requires 0 < sample_ratio <= 1.")
    elif options.sample_ratio is not None and not 0 < options.sample_ratio <= 1:
        raise ValidationError("Profile sample_ratio must satisfy 0 < sample_ratio <= 1.")
    if options.method is not ProfileMethod.SAMPLE and options.sample_ratio is not None:
        raise ValidationError("sample_ratio is only valid for SAMPLE profile method.")


def _validate_profile_field_selection(
    options: ProfileOptions, fields: tuple[DataField, ...]
) -> None:
    field_names = {field.name for field in fields}
    missing_fields = set(options.field_names) - field_names
    if missing_fields:
        raise ValidationError("Profile selected fields must exist in metadata.")
    missing_key_fields = set(options.key_field_names) - field_names
    if missing_key_fields:
        raise ValidationError("Profile key fields must exist in metadata.")


def validate_discovery_pattern(pattern: str) -> str:
    """Normalize and validate a discovery scope glob pattern.

    Returns the canonical pattern string. Raises ``ValidationError`` with
    ``DISCOVERY_SCOPE_PATTERN_INVALID`` on any violation.
    """
    if not isinstance(pattern, str):
        raise ValidationError(
            "Discovery scope pattern must be a string.",
            code="DISCOVERY_SCOPE_PATTERN_INVALID",
        )
    canonical = pattern.strip()
    if not canonical:
        raise ValidationError(
            "Discovery scope pattern must not be empty.",
            code="DISCOVERY_SCOPE_PATTERN_INVALID",
        )
    if len(canonical) > 255:
        raise ValidationError(
            "Discovery scope pattern must not exceed 255 characters.",
            code="DISCOVERY_SCOPE_PATTERN_INVALID",
        )
    for char in canonical:
        if ord(char) < 0x20:
            raise ValidationError(
                "Discovery scope pattern must not contain control characters.",
                code="DISCOVERY_SCOPE_PATTERN_INVALID",
            )
    if ".." in canonical or "/" in canonical or "\\" in canonical:
        raise ValidationError(
            "Discovery scope pattern must not contain '..', '/' or '\\'.",
            code="DISCOVERY_SCOPE_PATTERN_INVALID",
        )
    if "--" in canonical or ";" in canonical:
        raise ValidationError(
            "Discovery scope pattern must not contain SQL comment or statement separators.",
            code="DISCOVERY_SCOPE_PATTERN_INVALID",
        )
    for segment in canonical.split("."):
        if not segment:
            raise ValidationError(
                "Discovery scope pattern must not have empty segments.",
                code="DISCOVERY_SCOPE_PATTERN_INVALID",
            )
        if not re.match(r"^[a-zA-Z0-9_*?]+$", segment):
            raise ValidationError(
                "Discovery scope pattern segments support only literal characters, '*' and '?'.",
                code="DISCOVERY_SCOPE_PATTERN_INVALID",
            )
    return canonical
