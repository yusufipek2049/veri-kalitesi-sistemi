"""DS-09 notification repository ve batch staging sözleşmeleri.

Bu modül generic unit-of-work veya event bus değildir.
``PreparedNotificationBatch`` yalnız iş repository'sinin mevcut session'ına
notification event/delivery/job staging aktarabilmek için dar transaction
sözleşmesidir.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, Sequence

from veri_kalitesi.audit.models import PreparedAuditEvent
from veri_kalitesi.notifications.models import (
    NotificationDelivery,
    NotificationDeliveryStatus,
    NotificationEvent,
)


# ---------------------------------------------------------------------------
# Prepared notification batch — issue transaction'ında staging için
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PreparedNotificationBatch:
    """Issue mutation ile aynı transaction'da stage edilecek bildirim kayıtları.

    Bu nesne immutable'dır; ``stage_batch`` çağrıldığında session'a yazılır.
    Batch boş olabilir (abone yok, mandatory event yok vs.) — bu durumda
    stage no-op olur ve issue transaction'ı devam eder.
    """

    events: tuple[_StagedEvent, ...] = ()
    deliveries: tuple[_StagedDelivery, ...] = ()
    delivery_jobs: tuple[_StagedDeliveryJob, ...] = ()
    audit_events: tuple[PreparedAuditEvent, ...] = ()

    @property
    def is_empty(self) -> bool:
        return not self.events and not self.deliveries and not self.delivery_jobs


@dataclass(frozen=True)
class _StagedEvent:
    """Stage edilecek canonical notification event verisi."""

    event_id: str
    event_type: str
    scope_type: str
    scope_id: str
    source_ref: str
    deduplication_key_digest: str
    payload_digest: str
    payload: dict[str, Any]
    correlation_id: str
    policy_version: str
    occurred_at: datetime
    published_at: datetime


@dataclass(frozen=True)
class _StagedDelivery:
    """Stage edilecek notification delivery verisi."""

    delivery_id: str
    event_id: str
    recipient_user_id: str
    channel_id: str
    status: NotificationDeliveryStatus
    created_at: datetime


@dataclass(frozen=True)
class _StagedDeliveryJob:
    """Stage edilecek notification delivery job verisi."""

    job_type: str = "NOTIFICATION_DELIVERY"
    idempotency_key: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    correlation_id: str = ""
    scheduled_at: datetime | None = None


# ---------------------------------------------------------------------------
# Repository protokolü
# ---------------------------------------------------------------------------


class NotificationRepository(Protocol):
    """Notification event/channel/subscription/delivery kalıcılık protokolü."""

    def stage_event(
        self,
        session: Any,
        *,
        event_id: str,
        event_type: str,
        scope_type: str,
        scope_id: str,
        source_ref: str,
        deduplication_key_digest: str,
        payload_digest: str,
        payload: dict[str, Any],
        correlation_id: str,
        policy_version: str,
        occurred_at: datetime,
        published_at: datetime,
    ) -> None: ...

    def stage_delivery(
        self,
        session: Any,
        *,
        delivery_id: str,
        event_id: str,
        recipient_user_id: str,
        channel_id: str,
        status: NotificationDeliveryStatus,
        created_at: datetime,
    ) -> None: ...

    def stage_batch(
        self,
        session: Any,
        batch: PreparedNotificationBatch,
        *,
        audit_events: Sequence[PreparedAuditEvent] = (),
    ) -> None: ...

    def get_delivery(self, delivery_id: str) -> NotificationDelivery: ...

    def list_for_recipient(
        self,
        recipient_user_id: str,
        *,
        status: NotificationDeliveryStatus | None = None,
        event_type: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
    ) -> tuple[NotificationDelivery, ...]: ...

    def count_unread(self, recipient_user_id: str) -> int: ...

    def transition_delivery_status(
        self,
        session: Any,
        delivery_id: str,
        *,
        expected_status: NotificationDeliveryStatus,
        target_status: NotificationDeliveryStatus,
        expected_version: int,
        updated_at: datetime,
        attempt_count: int | None = None,
        last_error_class: str | None = None,
        last_attempt_at: datetime | None = None,
        next_attempt_at: datetime | None = None,
        delivered_at: datetime | None = None,
        read_at: datetime | None = None,
        rerouted_to_channel_id: str | None = None,
    ) -> NotificationDelivery: ...


# ---------------------------------------------------------------------------
# Batch stager protokolü
# ---------------------------------------------------------------------------


class NotificationBatchStager(Protocol):
    """Issue mutation öncesi notification batch hazırlama protokolü.

    Issue service bu protokolü kullanarak event/delivery/job verisini
    hazırlar; issue repository aynı session'da stage eder.
    """

    def prepare_batch(
        self,
        event: NotificationEvent,
        *,
        recipient_user_ids: tuple[str, ...],
        channel_id: str,
        actor_id: str,
        correlation_id: str,
    ) -> PreparedNotificationBatch: ...
