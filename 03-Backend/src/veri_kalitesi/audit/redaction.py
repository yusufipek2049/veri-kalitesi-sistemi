"""Allowlist tabanli audit veri minimizasyonu."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping

from veri_kalitesi.audit.errors import AuditValidationError
from veri_kalitesi.audit.models import (
    AuditEventInput,
    AuditRedactionPolicy,
    AuditResult,
    PreparedAuditEvent,
)


_CODE_PATTERN = re.compile(r"[A-Z0-9_.-]{1,120}")
_FORBIDDEN_KEY_PARTS = (
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "private_key",
    "authorization",
    "credential",
)
_FORBIDDEN_TEXT_PARTS = (
    "secret://",
    "password=",
    "passwd=",
    "token=",
    "authorization:",
    "private_key",
)


class AuditRedactor:
    def __init__(self, policy: AuditRedactionPolicy) -> None:
        if not policy.version.strip():
            raise AuditValidationError("Redaction policy version is required.")
        if any(not _CODE_PATTERN.fullmatch(action) for action in policy.allowed_fields_by_action):
            raise AuditValidationError("Redaction policy action is invalid.")
        self.policy = policy

    def prepare(self, event: AuditEventInput) -> PreparedAuditEvent:
        _validate_event(event)
        allowed_fields = self.policy.allowed_fields_by_action.get(event.action, frozenset())
        old_summary, old_redacted = _redact_mapping("old_values", event.old_values, allowed_fields)
        new_summary, new_redacted = _redact_mapping("new_values", event.new_values, allowed_fields)
        return PreparedAuditEvent(
            actor_id=event.actor_id,
            actor_type=event.actor_type,
            correlation_id=event.correlation_id,
            action=event.action,
            object_type=event.object_type,
            object_id=event.object_id,
            result=event.result,
            reason_code=event.reason_code,
            old_value_summary=old_summary,
            new_value_summary=new_summary,
            old_value_digest=_digest(old_summary),
            new_value_digest=_digest(new_summary),
            redacted_fields=tuple(sorted((*old_redacted, *new_redacted))),
            occurred_at=event.occurred_at,
            session_id_digest=(
                _digest_text(event.session_id) if event.session_id is not None else None
            ),
            redaction_policy_version=self.policy.version,
            event_version=event.event_version,
        )


def _validate_event(event: AuditEventInput) -> None:
    required = (
        event.actor_id,
        event.correlation_id,
        event.action,
        event.object_type,
        event.reason_code,
        event.event_version,
    )
    if any(not value.strip() for value in required):
        raise AuditValidationError("Audit event identifiers must not be blank.")
    persisted_text = (
        event.actor_id,
        event.correlation_id,
        event.action,
        event.object_type,
        event.object_id,
        event.reason_code,
        event.event_version,
    )
    if any(_contains_sensitive_text(value) for value in persisted_text if value is not None):
        raise AuditValidationError("Audit event envelope contains sensitive text.")
    if not _CODE_PATTERN.fullmatch(event.action):
        raise AuditValidationError("Audit action is invalid.")
    if event.occurred_at.tzinfo is None or event.occurred_at.utcoffset() is None:
        raise AuditValidationError("Audit event time must be timezone-aware.")
    if not isinstance(event.result, AuditResult):
        raise AuditValidationError("Audit result is invalid.")


def _redact_mapping(
    prefix: str,
    values: Mapping[str, Any],
    allowed_fields: frozenset[str],
) -> tuple[dict[str, Any], list[str]]:
    summary: dict[str, Any] = {}
    redacted: list[str] = []
    for key, value in values.items():
        field_path = f"{prefix}.{key}"
        if (
            key not in allowed_fields
            or _is_forbidden_key(key)
            or not _is_safe_scalar(value)
            or _contains_sensitive_text(value)
        ):
            redacted.append(field_path)
            continue
        summary[key] = value
    return summary, redacted


def _is_forbidden_key(key: str) -> bool:
    normalized = key.lower()
    return any(part in normalized for part in _FORBIDDEN_KEY_PARTS)


def _is_safe_scalar(value: Any) -> bool:
    return value is None or (
        isinstance(value, str | int | float | bool) and not isinstance(value, bytes)
    )


def _contains_sensitive_text(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    normalized = value.lower()
    return any(part in normalized for part in _FORBIDDEN_TEXT_PARTS)


def _digest(value: Mapping[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
