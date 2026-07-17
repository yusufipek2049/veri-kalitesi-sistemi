"""Trusted recipient and data-minimum in-app notification service."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from typing import Callable, Protocol

from veri_kalitesi.audit import (
    AuditEventInput,
    AuditResult,
    PreparedAuditEvent,
    SQLiteTransactionalAudit,
)
from veri_kalitesi.identity import ActorContext, ActorType, is_trusted_actor_context
from veri_kalitesi.notifications.errors import (
    NotificationAuthorizationError,
    NotificationConflictError,
    NotificationError,
    NotificationRecipientError,
    NotificationTechnicalError,
    NotificationValidationError,
)
from veri_kalitesi.notifications.models import (
    Notification,
    NotificationAccessPolicy,
    NotificationEvent,
    NotificationEventType,
    NotificationStatus,
    validate_access_policy,
    validate_notification_event,
    validate_recipient_id,
)
from veri_kalitesi.notifications.repository import SQLiteNotificationRepository


_TEMPLATES = {
    NotificationEventType.QUALITY_THRESHOLD: (
        "Data quality threshold alert",
        "A data quality score requires review in the authorized notification center.",
    ),
    NotificationEventType.CRITICAL_RULE_FAILURE: (
        "Critical data quality rule alert",
        "A critical data quality rule requires review in the authorized notification center.",
    ),
    NotificationEventType.TECHNICAL_ERROR: (
        "Technical processing alert",
        "A technical processing failure requires review by the responsible technical role.",
    ),
    NotificationEventType.ISSUE_ASSIGNED: (
        "Data quality issue assigned",
        "A data quality issue has been assigned for review in the authorized issue center.",
    ),
}


class NotificationRecipientResolver(Protocol):
    def resolve_recipients(self, event: NotificationEvent) -> tuple[str, ...]: ...


class NotificationService:
    def __init__(
        self,
        repository: SQLiteNotificationRepository,
        recipient_resolver: NotificationRecipientResolver,
        transactional_audit: SQLiteTransactionalAudit,
        access_policy: NotificationAccessPolicy,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        validate_access_policy(access_policy)
        self.repository = repository
        self.recipient_resolver = recipient_resolver
        self.transactional_audit = transactional_audit
        self.access_policy = access_policy
        self.clock = clock

    def create_for_event(
        self,
        event: NotificationEvent,
        actor_context: ActorContext | None,
    ) -> tuple[Notification, ...]:
        validate_notification_event(event)
        context = self._authorize_actor(
            actor_context,
            self.access_policy.allowed_producer_actor_types,
            "produce notifications",
        )
        now = self._now()
        if event.occurred_at > now:
            raise NotificationValidationError("Notification event cannot be in the future.")
        try:
            recipient_ids = tuple(sorted(set(self.recipient_resolver.resolve_recipients(event))))
        except NotificationError:
            raise
        except Exception as exc:
            raise NotificationTechnicalError(
                "Notification recipient resolution failed.", event.correlation_id
            ) from exc
        if not recipient_ids:
            raise NotificationRecipientError("No trusted notification recipient was resolved.")
        for recipient_id in recipient_ids:
            validate_recipient_id(recipient_id)

        title, body = _TEMPLATES[event.event_type]
        deduplication_digest = _digest_text(event.deduplication_key)
        payload_digest = _payload_digest(event)
        notifications = tuple(
            Notification(
                recipient_user_id=recipient_id,
                source_event_id=event.event_id,
                event_type=event.event_type,
                scope_type=event.scope_type,
                scope_id=event.scope_id,
                title=title,
                body=body,
                status=NotificationStatus.UNREAD,
                deduplication_key_digest=deduplication_digest,
                occurrence_count=1,
                created_at=now,
                last_seen_at=now,
            )
            for recipient_id in recipient_ids
        )
        audit_event = self._prepare_audit(
            AuditEventInput(
                actor_id=context.actor_id,
                actor_type=context.actor_type.value,
                correlation_id=event.correlation_id,
                action="NOTIFICATION_CREATED",
                object_type="NotificationEvent",
                object_id=event.event_id,
                result=AuditResult.SUCCESS,
                reason_code=event.event_type.value,
                old_values={},
                new_values={
                    "event_type": event.event_type.value,
                    "recipient_count": len(recipient_ids),
                    "status": NotificationStatus.UNREAD.value,
                    "scope_id": event.scope_id,
                    "deduplication_key": event.deduplication_key,
                },
                occurred_at=now,
                session_id=context.session_id,
            ),
            event.correlation_id,
        )
        try:
            stored = self.repository.add_or_increment(
                notifications,
                payload_digest=payload_digest,
                audit_event=audit_event,
                audit_outbox=self.transactional_audit,
            )
        except NotificationConflictError:
            raise
        except (sqlite3.Error, OSError) as exc:
            raise NotificationTechnicalError(
                "Notification could not be persisted.", event.correlation_id
            ) from exc
        self.transactional_audit.publish_pending()
        return stored

    def list_my_notifications(self, actor_context: ActorContext | None) -> tuple[Notification, ...]:
        context = self._authorize_actor(
            actor_context,
            self.access_policy.allowed_reader_actor_types,
            "access notifications",
        )
        try:
            return self.repository.list_for_recipient(context.actor_id)
        except (sqlite3.Error, OSError) as exc:
            raise NotificationTechnicalError(
                "Notifications could not be read.", context.correlation_id
            ) from exc

    def mark_read(
        self,
        notification_id: str,
        actor_context: ActorContext | None,
    ) -> Notification:
        context = self._authorize_actor(
            actor_context,
            self.access_policy.allowed_reader_actor_types,
            "access notifications",
        )
        now = self._now()
        audit_event = self._prepare_audit(
            AuditEventInput(
                actor_id=context.actor_id,
                actor_type=context.actor_type.value,
                correlation_id=context.correlation_id,
                action="NOTIFICATION_READ",
                object_type="Notification",
                object_id=notification_id,
                result=AuditResult.SUCCESS,
                reason_code="RECIPIENT_MARKED_READ",
                old_values={"status": NotificationStatus.UNREAD.value},
                new_values={
                    "status": NotificationStatus.READ.value,
                    "session_id": context.session_id,
                },
                occurred_at=now,
                session_id=context.session_id,
            ),
            context.correlation_id,
        )
        try:
            stored = self.repository.mark_read(
                notification_id,
                context.actor_id,
                now,
                audit_event=audit_event,
                audit_outbox=self.transactional_audit,
            )
        except (sqlite3.Error, OSError) as exc:
            raise NotificationTechnicalError(
                "Notification status could not be updated.", context.correlation_id
            ) from exc
        self.transactional_audit.publish_pending()
        return stored

    def _authorize_actor(
        self,
        context: ActorContext | None,
        allowed_actor_types: frozenset[ActorType],
        operation: str,
    ) -> ActorContext:
        now = self._now()
        if not is_trusted_actor_context(context):
            raise NotificationAuthorizationError("Trusted actor context is required.")
        assert context is not None
        if context.issued_at > now or context.expires_at <= now:
            raise NotificationAuthorizationError("Actor context is not currently valid.")
        if context.policy_version != self.access_policy.actor_policy_version:
            raise NotificationAuthorizationError("Actor context policy version is not accepted.")
        if context.actor_type not in allowed_actor_types:
            raise NotificationAuthorizationError(f"Actor type cannot {operation}.")
        if context.privileged:
            raise NotificationAuthorizationError(
                "Privileged context cannot use the standard notification center."
            )
        return context

    def _now(self) -> datetime:
        now = self.clock()
        if now.tzinfo is None or now.utcoffset() is None:
            raise NotificationValidationError("Notification clock must be timezone-aware.")
        return now.astimezone(timezone.utc)

    def _prepare_audit(self, event: AuditEventInput, correlation_id: str) -> PreparedAuditEvent:
        try:
            return self.transactional_audit.prepare(event)
        except Exception as exc:
            raise NotificationTechnicalError(
                "Notification audit event could not be prepared.", correlation_id
            ) from exc


def _payload_digest(event: NotificationEvent) -> str:
    payload = {
        "event_type": event.event_type.value,
        "scope_type": event.scope_type.value,
        "scope_id": event.scope_id,
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
