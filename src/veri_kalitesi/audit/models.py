"""Merkezi ve surumlu audit olay modelleri."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4


class AuditResult(str, Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    DENIED = "DENIED"


class AuditFailureMode(str, Enum):
    FAIL_CLOSED = "FAIL_CLOSED"
    DURABLE_BUFFER = "DURABLE_BUFFER"


@dataclass(frozen=True)
class AuditEventInput:
    actor_id: str
    actor_type: str | None
    correlation_id: str
    action: str
    object_type: str
    object_id: str | None
    result: AuditResult
    reason_code: str
    old_values: Mapping[str, Any]
    new_values: Mapping[str, Any]
    occurred_at: datetime
    session_id: str | None = None
    event_version: str = "AUDIT_EVENT_V1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "old_values", MappingProxyType(dict(self.old_values)))
        object.__setattr__(self, "new_values", MappingProxyType(dict(self.new_values)))


@dataclass(frozen=True)
class AuditRedactionPolicy:
    version: str
    allowed_fields_by_action: Mapping[str, frozenset[str]]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "allowed_fields_by_action",
            MappingProxyType(
                {
                    action: frozenset(fields)
                    for action, fields in self.allowed_fields_by_action.items()
                }
            ),
        )


@dataclass(frozen=True)
class AuditFailurePolicy:
    version: str
    default_mode: AuditFailureMode
    action_modes: Mapping[str, AuditFailureMode] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "action_modes",
            MappingProxyType(dict(self.action_modes)),
        )

    def mode_for(self, action: str) -> AuditFailureMode:
        return self.action_modes.get(action, self.default_mode)


@dataclass(frozen=True)
class PreparedAuditEvent:
    actor_id: str
    actor_type: str | None
    correlation_id: str
    action: str
    object_type: str
    object_id: str | None
    result: AuditResult
    reason_code: str
    old_value_summary: Mapping[str, Any]
    new_value_summary: Mapping[str, Any]
    old_value_digest: str
    new_value_digest: str
    redacted_fields: tuple[str, ...]
    occurred_at: datetime
    session_id_digest: str | None
    redaction_policy_version: str
    event_version: str
    event_id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "old_value_summary",
            MappingProxyType(dict(self.old_value_summary)),
        )
        object.__setattr__(
            self,
            "new_value_summary",
            MappingProxyType(dict(self.new_value_summary)),
        )


@dataclass(frozen=True)
class AuditEvent:
    sequence_no: int
    event_id: str
    event_version: str
    occurred_at: datetime
    actor_id: str
    actor_type: str | None
    session_id_digest: str | None
    correlation_id: str
    action: str
    object_type: str
    object_id: str | None
    result: AuditResult
    reason_code: str
    old_value_summary: Mapping[str, Any]
    new_value_summary: Mapping[str, Any]
    old_value_digest: str
    new_value_digest: str
    redacted_fields: tuple[str, ...]
    redaction_policy_version: str
    previous_event_hash: str
    event_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "old_value_summary",
            MappingProxyType(dict(self.old_value_summary)),
        )
        object.__setattr__(
            self,
            "new_value_summary",
            MappingProxyType(dict(self.new_value_summary)),
        )


@dataclass(frozen=True)
class AuditIntegrityResult:
    valid: bool
    checked_count: int
    first_invalid_event_id: str | None = None


@dataclass(frozen=True)
class AuditAccessPolicy:
    version: str
    context_policy_version: str
    required_role: str = "AUDIT_VIEWER"
    max_sync_window_days: int = 31
    max_page_size: int = 100


@dataclass(frozen=True)
class AuditQuery:
    start_at: datetime
    end_at: datetime
    reason_code: str
    actor_id: str | None = None
    action: str | None = None
    object_type: str | None = None
    object_id: str | None = None
    result: AuditResult | None = None
    correlation_id: str | None = None
    after_sequence_no: int = 0
    through_sequence_no: int | None = None
    page_size: int = 50


@dataclass(frozen=True)
class AuditQueryPage:
    events: tuple[AuditEvent, ...]
    integrity: AuditIntegrityResult
    next_after_sequence_no: int | None
    through_sequence_no: int
    policy_version: str
