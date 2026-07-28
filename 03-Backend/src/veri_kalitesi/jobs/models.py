"""Kalıcı iş kuyruğu domain modelleri ve güvenli payload sözleşmesi."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4

from veri_kalitesi.audit.redaction import _contains_sensitive_text, _is_forbidden_key
from veri_kalitesi.jobs.errors import JobValidationError


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    TECHNICAL_ERROR = "TECHNICAL_ERROR"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class JobLeasePolicy:
    """Worker tarafından seçilen teknik lease süresi."""

    duration: timedelta = timedelta(minutes=5)

    def __post_init__(self) -> None:
        if self.duration <= timedelta(0):
            raise JobValidationError("Job lease duration must be positive.")


@dataclass(frozen=True)
class BackgroundJob:
    job_type: str
    payload: Mapping[str, Any]
    idempotency_key: str | None = None
    priority: int = 0
    available_at: datetime = field(default_factory=utc_now)
    job_id: str = field(default_factory=lambda: str(uuid4()))
    status: JobStatus = JobStatus.QUEUED
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    claimed_by: str | None = None
    lease_expires_at: datetime | None = None
    last_heartbeat_at: datetime | None = None
    attempt_count: int = 0
    version: int = 0
    last_error_class: str | None = None

    def __post_init__(self) -> None:
        _validate_identifier("job_type", self.job_type)
        _validate_identifier("job_id", self.job_id)
        if self.idempotency_key is not None:
            _validate_identifier("idempotency_key", self.idempotency_key)
        if self.claimed_by is not None:
            _validate_identifier("claimed_by", self.claimed_by)
        if self.priority < 0:
            raise JobValidationError("Job priority must not be negative.")
        if self.attempt_count < 0:
            raise JobValidationError("Job attempt_count must not be negative.")
        if self.version < 0:
            raise JobValidationError("Job version must not be negative.")
        for field_name, value in (
            ("available_at", self.available_at),
            ("created_at", self.created_at),
            ("updated_at", self.updated_at),
            ("lease_expires_at", self.lease_expires_at),
            ("last_heartbeat_at", self.last_heartbeat_at),
        ):
            if value is not None and (value.tzinfo is None or value.utcoffset() is None):
                raise JobValidationError(f"Job {field_name} must be timezone-aware.")
        safe_payload = dict(self.payload)
        _validate_payload(safe_payload)
        object.__setattr__(self, "payload", _freeze_payload(safe_payload))

    def claim_sort_key(self) -> tuple[int, datetime, datetime, str]:
        """Veritabanındaki deterministik claim sırasının Python karşılığı."""

        return (-self.priority, self.available_at, self.created_at, self.job_id)


def _validate_identifier(field_name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise JobValidationError(f"Job {field_name} must not be blank.")


def _validate_payload(value: Any, *, field_path: str = "payload") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if not isinstance(key, str):
                raise JobValidationError(f"Job payload field {field_path} has a non-string key.")
            nested_path = f"{field_path}.{key}"
            if _is_forbidden_key(key):
                raise JobValidationError(f"Job payload field {nested_path} is forbidden.")
            _validate_payload(nested, field_path=nested_path)
        return
    if isinstance(value, list | tuple):
        for index, nested in enumerate(value):
            _validate_payload(nested, field_path=f"{field_path}[{index}]")
        return
    if value is None or isinstance(value, bool | int | float):
        return
    if isinstance(value, str):
        if _contains_sensitive_text(value):
            raise JobValidationError(
                f"Job payload field {field_path} contains forbidden sensitive text."
            )
        return
    raise JobValidationError(f"Job payload field {field_path} is not JSON-compatible.")


def _freeze_payload(value: Any) -> Any:
    """JSON payload'ını dış mutable referanslardan recursive olarak ayır."""

    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze_payload(nested) for key, nested in value.items()})
    if isinstance(value, list | tuple):
        return tuple(_freeze_payload(nested) for nested in value)
    return value


def payload_to_json(value: Any) -> Any:
    """Frozen payload için persistence'a özel, paylaşılmayan JSON kopyası üret."""

    if isinstance(value, Mapping):
        return {key: payload_to_json(nested) for key, nested in value.items()}
    if isinstance(value, list | tuple):
        return [payload_to_json(nested) for nested in value]
    return value
