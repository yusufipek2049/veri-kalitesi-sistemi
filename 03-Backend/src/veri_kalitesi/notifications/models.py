"""Data-minimum in-app notification domain models."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from veri_kalitesi.identity import ActorType
from veri_kalitesi.notifications.errors import NotificationValidationError


_CODE_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,199}")
_FORBIDDEN_TEXT = (
    "password",
    "passwd",
    "secret",
    "token",
    "credential",
    "authorization",
)


class NotificationEventType(str, Enum):
    QUALITY_THRESHOLD = "QUALITY_THRESHOLD"
    CRITICAL_RULE_FAILURE = "CRITICAL_RULE_FAILURE"
    TECHNICAL_ERROR = "TECHNICAL_ERROR"
    ISSUE_ASSIGNED = "ISSUE_ASSIGNED"


class NotificationScopeType(str, Enum):
    RULE = "RULE"
    DATASET = "DATASET"
    SOURCE = "SOURCE"
    EXECUTION = "EXECUTION"
    ISSUE_ASSIGNMENT = "ISSUE_ASSIGNMENT"


class NotificationStatus(str, Enum):
    UNREAD = "UNREAD"
    READ = "READ"


@dataclass(frozen=True)
class NotificationEvent:
    event_type: NotificationEventType
    scope_type: NotificationScopeType
    scope_id: str
    deduplication_key: str
    occurred_at: datetime
    correlation_id: str
    event_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(frozen=True)
class Notification:
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


def validate_notification_event(event: NotificationEvent) -> None:
    if not isinstance(event.event_type, NotificationEventType):
        raise NotificationValidationError("event_type is invalid.")
    if not isinstance(event.scope_type, NotificationScopeType):
        raise NotificationValidationError("scope_type is invalid.")
    _validate_uuid("event_id", event.event_id)
    _validate_uuid("scope_id", event.scope_id)
    _validate_code("deduplication_key", event.deduplication_key)
    _validate_code("correlation_id", event.correlation_id)
    if not _is_aware(event.occurred_at):
        raise NotificationValidationError("occurred_at must be timezone-aware.")


def validate_recipient_id(recipient_user_id: str) -> None:
    _validate_uuid("recipient_user_id", recipient_user_id)


def validate_access_policy(policy: NotificationAccessPolicy) -> None:
    _validate_code("policy.version", policy.version)
    _validate_code("policy.actor_policy_version", policy.actor_policy_version)
    if not policy.allowed_reader_actor_types or not policy.allowed_producer_actor_types:
        raise NotificationValidationError("Access policy must allow reader and producer types.")


def _validate_uuid(field_name: str, value: str) -> None:
    try:
        UUID(value)
    except (AttributeError, TypeError, ValueError) as exc:
        raise NotificationValidationError(f"{field_name} must be a UUID.") from exc


def _validate_code(field_name: str, value: str) -> None:
    if not isinstance(value, str) or not _CODE_PATTERN.fullmatch(value):
        raise NotificationValidationError(f"{field_name} is invalid.")
    normalized = value.lower()
    if any(part in normalized for part in _FORBIDDEN_TEXT):
        raise NotificationValidationError(f"{field_name} contains forbidden content.")


def _is_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None
