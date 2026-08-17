"""Data-minimum in-app notification domain models.

DS-09: Canonical event, channel, subscription ve delivery modelleri.
Bounded string ID doğrulaması (UUID zorunlu değil).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from veri_kalitesi.identity import ActorType
from veri_kalitesi.notifications.errors import NotificationValidationError


_CODE_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,199}")
_BOUNDED_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}")
_FORBIDDEN_TEXT = (
    "password",
    "passwd",
    "secret",
    "token",
    "credential",
    "authorization",
)
_SENSITIVE_PAYLOAD_KEYS = frozenset(
    {
        "password",
        "secret",
        "token",
        "credential",
        "connection_string",
        "sample_value",
        "field_value",
        "rule_definition",
    }
)


# ---------------------------------------------------------------------------
# Event / scope type enum'ları
# ---------------------------------------------------------------------------


class NotificationEventType(str, Enum):
    QUALITY_THRESHOLD = "QUALITY_THRESHOLD"
    CRITICAL_RULE_FAILURE = "CRITICAL_RULE_FAILURE"
    TECHNICAL_ERROR = "TECHNICAL_ERROR"
    ISSUE_ASSIGNED = "ISSUE_ASSIGNED"
    RULE_APPROVAL_REQUESTED = "RULE_APPROVAL_REQUESTED"
    RULE_APPROVAL_DECIDED = "RULE_APPROVAL_DECIDED"
    RULE_APPROVAL_WITHDRAWN = "RULE_APPROVAL_WITHDRAWN"
    RULE_APPROVAL_EXPIRED = "RULE_APPROVAL_EXPIRED"
    GOVERNANCE_APPROVAL_REQUESTED = "GOVERNANCE_APPROVAL_REQUESTED"
    GOVERNANCE_APPROVAL_DECIDED = "GOVERNANCE_APPROVAL_DECIDED"
    GOVERNANCE_APPROVAL_REJECTED = "GOVERNANCE_APPROVAL_REJECTED"
    GOVERNANCE_APPROVAL_WITHDRAWN = "GOVERNANCE_APPROVAL_WITHDRAWN"


class NotificationScopeType(str, Enum):
    RULE = "RULE"
    DATASET = "DATASET"
    SOURCE = "SOURCE"
    EXECUTION = "EXECUTION"
    ISSUE_ASSIGNMENT = "ISSUE_ASSIGNMENT"
    GOVERNANCE = "GOVERNANCE"


# ---------------------------------------------------------------------------
# Delivery state-machine (ST-NotificationDelivery)
# ---------------------------------------------------------------------------


class NotificationDeliveryStatus(str, Enum):
    PENDING = "PENDING"
    SENDING = "SENDING"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    UNDELIVERABLE = "UNDELIVERABLE"
    REROUTED = "REROUTED"
    READ = "READ"


# Yasak geçişler: (mevcut_durum) → {izin_verilmeyen_hedefler}
_DELIVERY_FORBIDDEN_TRANSITIONS: dict[
    NotificationDeliveryStatus, frozenset[NotificationDeliveryStatus]
] = {
    NotificationDeliveryStatus.PENDING: frozenset({NotificationDeliveryStatus.DELIVERED}),
    NotificationDeliveryStatus.DELIVERED: frozenset({NotificationDeliveryStatus.FAILED}),
    NotificationDeliveryStatus.UNDELIVERABLE: frozenset({NotificationDeliveryStatus.DELIVERED}),
    NotificationDeliveryStatus.READ: frozenset({NotificationDeliveryStatus.FAILED}),
}

# İzin verilen geçişler
_DELIVERY_ALLOWED_TRANSITIONS: dict[
    NotificationDeliveryStatus, frozenset[NotificationDeliveryStatus]
] = {
    NotificationDeliveryStatus.PENDING: frozenset({NotificationDeliveryStatus.SENDING}),
    NotificationDeliveryStatus.SENDING: frozenset(
        {NotificationDeliveryStatus.DELIVERED, NotificationDeliveryStatus.FAILED}
    ),
    NotificationDeliveryStatus.FAILED: frozenset(
        {NotificationDeliveryStatus.SENDING, NotificationDeliveryStatus.UNDELIVERABLE}
    ),
    NotificationDeliveryStatus.UNDELIVERABLE: frozenset({NotificationDeliveryStatus.REROUTED}),
    NotificationDeliveryStatus.DELIVERED: frozenset({NotificationDeliveryStatus.READ}),
    NotificationDeliveryStatus.REROUTED: frozenset(),
    NotificationDeliveryStatus.READ: frozenset(),
}


# Legacy inbox projection (UNREAD/READ)
class NotificationStatus(str, Enum):
    UNREAD = "UNREAD"
    READ = "READ"


# ---------------------------------------------------------------------------
# Channel status
# ---------------------------------------------------------------------------


class NotificationChannelStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class NotificationSubscriptionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


# ---------------------------------------------------------------------------
# Severity mapping
# ---------------------------------------------------------------------------


class NotificationSeverity(str, Enum):
    INFO = "INFO"
    ACTION_REQUIRED = "ACTION_REQUIRED"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


EVENT_SEVERITY: dict[NotificationEventType, NotificationSeverity] = {
    NotificationEventType.QUALITY_THRESHOLD: NotificationSeverity.WARNING,
    NotificationEventType.CRITICAL_RULE_FAILURE: NotificationSeverity.CRITICAL,
    NotificationEventType.TECHNICAL_ERROR: NotificationSeverity.CRITICAL,
    NotificationEventType.ISSUE_ASSIGNED: NotificationSeverity.ACTION_REQUIRED,
    NotificationEventType.RULE_APPROVAL_REQUESTED: NotificationSeverity.ACTION_REQUIRED,
    NotificationEventType.RULE_APPROVAL_DECIDED: NotificationSeverity.ACTION_REQUIRED,
    NotificationEventType.RULE_APPROVAL_WITHDRAWN: NotificationSeverity.ACTION_REQUIRED,
    NotificationEventType.RULE_APPROVAL_EXPIRED: NotificationSeverity.ACTION_REQUIRED,
    NotificationEventType.GOVERNANCE_APPROVAL_REQUESTED: NotificationSeverity.ACTION_REQUIRED,
    NotificationEventType.GOVERNANCE_APPROVAL_DECIDED: NotificationSeverity.ACTION_REQUIRED,
    NotificationEventType.GOVERNANCE_APPROVAL_REJECTED: NotificationSeverity.ACTION_REQUIRED,
    NotificationEventType.GOVERNANCE_APPROVAL_WITHDRAWN: NotificationSeverity.ACTION_REQUIRED,
}


# ---------------------------------------------------------------------------
# Zorunlu (mandatory) event tipleri — abonelikle kapatılamaz
# ---------------------------------------------------------------------------

MANDATORY_EVENT_TYPES: frozenset[NotificationEventType] = frozenset(
    {NotificationEventType.ISSUE_ASSIGNED}
)


# ---------------------------------------------------------------------------
# Domain modeller
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NotificationEvent:
    """Canonical iş olayı — delivery sonucu değildir, yayımlandıktan sonra değişmez."""

    event_type: NotificationEventType
    scope_type: NotificationScopeType
    scope_id: str
    deduplication_key: str
    occurred_at: datetime
    correlation_id: str
    source_ref: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    policy_version: str = "DS09_EVENT_POLICY_V1"
    event_id: str = field(default_factory=lambda: str(uuid4()))
    payload_digest: str = ""
    deduplication_key_digest: str = ""
    published_at: datetime | None = None


@dataclass(frozen=True)
class NotificationChannel:
    """Kanal yapılandırması — secret değeri değil secret_ref saklar."""

    channel_id: str
    name: str
    channel_type: str
    target_config: dict[str, Any]
    allowed_event_types: tuple[str, ...]
    status: NotificationChannelStatus
    policy_version: str
    version: int
    created_by: str
    created_at: datetime
    updated_at: datetime
    secret_ref: str | None = None


@dataclass(frozen=True)
class NotificationSubscription:
    """Kullanıcı tercih/abonelik kaydı."""

    subscription_id: str
    user_id: str
    event_type: NotificationEventType
    channel_id: str
    status: NotificationSubscriptionStatus
    policy_version: str
    version: int
    created_at: datetime
    updated_at: datetime
    scope_type: NotificationScopeType | None = None
    scope_id: str | None = None


@dataclass(frozen=True)
class NotificationDelivery:
    """Teslimat durum makinesi kaydı (ST-NotificationDelivery)."""

    delivery_id: str
    event_id: str
    recipient_user_id: str
    channel_id: str
    status: NotificationDeliveryStatus
    attempt_count: int
    version: int
    created_at: datetime
    updated_at: datetime
    last_error_class: str | None = None
    last_attempt_at: datetime | None = None
    next_attempt_at: datetime | None = None
    delivered_at: datetime | None = None
    read_at: datetime | None = None
    rerouted_to_channel_id: str | None = None


@dataclass(frozen=True)
class Notification:
    """Inbox projection — event + delivery join'inden üretilir."""

    recipient_user_id: str
    source_event_id: str
    event_type: NotificationEventType
    scope_type: NotificationScopeType
    scope_id: str
    title: str
    body: str
    status: NotificationStatus
    deduplication_key_digest: str
    occurrence_count: int
    created_at: datetime
    last_seen_at: datetime
    read_at: datetime | None = None
    notification_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(frozen=True)
class NotificationAccessPolicy:
    version: str
    actor_policy_version: str
    allowed_reader_actor_types: frozenset[ActorType] = field(
        default_factory=lambda: frozenset({ActorType.USER})
    )
    allowed_producer_actor_types: frozenset[ActorType] = field(
        default_factory=lambda: frozenset({ActorType.SERVICE})
    )


# ---------------------------------------------------------------------------
# Validator'lar
# ---------------------------------------------------------------------------


def validate_notification_event(event: NotificationEvent) -> None:
    if not isinstance(event.event_type, NotificationEventType):
        raise NotificationValidationError("event_type is invalid.")
    if not isinstance(event.scope_type, NotificationScopeType):
        raise NotificationValidationError("scope_type is invalid.")
    _validate_bounded_id("event_id", event.event_id)
    _validate_bounded_id("scope_id", event.scope_id)
    _validate_code("deduplication_key", event.deduplication_key)
    _validate_code("correlation_id", event.correlation_id)
    if not _is_aware(event.occurred_at):
        raise NotificationValidationError("occurred_at must be timezone-aware.")
    if event.source_ref:
        _validate_bounded_ref("source_ref", event.source_ref)
    _validate_code("policy_version", event.policy_version)


def validate_recipient_id(recipient_user_id: str) -> None:
    """DS-10 öncesi bounded string ID doğrulaması (UUID zorunlu değil)."""
    _validate_bounded_id("recipient_user_id", recipient_user_id)


def validate_access_policy(policy: NotificationAccessPolicy) -> None:
    _validate_code("policy.version", policy.version)
    _validate_code("policy.actor_policy_version", policy.actor_policy_version)
    if not policy.allowed_reader_actor_types or not policy.allowed_producer_actor_types:
        raise NotificationValidationError("Access policy must allow reader and producer types.")


def validate_delivery_transition(
    current: NotificationDeliveryStatus,
    target: NotificationDeliveryStatus,
) -> None:
    """ST-NotificationDelivery geçiş doğrulaması."""
    forbidden = _DELIVERY_FORBIDDEN_TRANSITIONS.get(current, frozenset())
    if target in forbidden:
        raise NotificationValidationError(
            f"Delivery transition {current.value} → {target.value} is forbidden."
        )
    allowed = _DELIVERY_ALLOWED_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise NotificationValidationError(
            f"Delivery transition {current.value} → {target.value} is not allowed."
        )


def validate_payload_safety(payload: dict[str, Any]) -> None:
    """Hassas payload fail-closed reddi."""
    if not isinstance(payload, dict):
        raise NotificationValidationError("Payload must be a JSON object.")
    _check_sensitive_keys(payload)


def _check_sensitive_keys(obj: Any, path: str = "") -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            full_key = f"{path}.{key}" if path else key
            if key.lower() in _SENSITIVE_PAYLOAD_KEYS:
                raise NotificationValidationError(f"Payload contains forbidden key: {full_key}")
            _check_sensitive_keys(value, full_key)
    elif isinstance(obj, (list, tuple)):
        for i, item in enumerate(obj):
            _check_sensitive_keys(item, f"{path}[{i}]")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _validate_bounded_id(field_name: str, value: str) -> None:
    if not isinstance(value, str) or not _BOUNDED_ID_PATTERN.fullmatch(value):
        raise NotificationValidationError(
            f"{field_name} must be a bounded reference string (max 128 chars, alphanumeric/._:-)."
        )


def _validate_bounded_ref(field_name: str, value: str) -> None:
    if not isinstance(value, str) or len(value) > 200 or not value.strip():
        raise NotificationValidationError(
            f"{field_name} must be a non-empty string of at most 200 characters."
        )


def _validate_code(field_name: str, value: str) -> None:
    if not isinstance(value, str) or not _CODE_PATTERN.fullmatch(value):
        raise NotificationValidationError(f"{field_name} is invalid.")
    normalized = value.lower()
    if any(part in normalized for part in _FORBIDDEN_TEXT):
        raise NotificationValidationError(f"{field_name} contains forbidden content.")


def _is_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None
