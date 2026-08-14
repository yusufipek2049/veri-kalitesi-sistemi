"""DS-09 notification delivery service.

Teslimat durum makinesi (ST-NotificationDelivery) geçişlerini yönetir.
IN_APP kanal için teslimat no-op'tur; veri zaten veritabanındadır.
Harici kanallar için retry ve reroute semantiği uygulanır.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Protocol

from veri_kalitesi.notifications.errors import (
    NotificationDeliveryError,
)
from veri_kalitesi.notifications.models import (
    NotificationDelivery,
    NotificationDeliveryStatus,
    NotificationEvent,
)
from veri_kalitesi.notifications.postgresql_repository import (
    PostgreSQLNotificationRepository,
)
from veri_kalitesi.notifications.stream_hub import get_stream_hub
from veri_kalitesi.persistence import transactional_session

logger = logging.getLogger(__name__)

# Retry backoff: (attempt_number → delay_seconds)
_RETRY_BACKOFF_SECONDS = (0, 60, 300, 1800, 7200)
_MAX_RETRY_ATTEMPTS = len(_RETRY_BACKOFF_SECONDS)


class InAppChannelAdapter(Protocol):
    """IN_APP kanal adaptörü — veri zaten veritabanında, sadece onayla."""

    def deliver(self, event: NotificationEvent, delivery: NotificationDelivery) -> bool: ...


class DefaultInAppAdapter:
    """IN_APP kanal için varsayılan adaptör — her zaman başarılı."""

    def deliver(self, event: NotificationEvent, delivery: NotificationDelivery) -> bool:
        return True


@dataclass(frozen=True)
class DeliveryAttemptResult:
    """Tek bir teslimat denemesinin sonucu."""

    delivery_id: str
    status: NotificationDeliveryStatus
    attempt_count: int
    next_attempt_at: datetime | None = None
    delivered_at: datetime | None = None
    error_class: str | None = None


class NotificationDeliveryService:
    """Teslimat durum makinesi yöneticisi.

    PENDING → SENDING → DELIVERED | FAILED → UNDELIVERABLE | REROUTED
    DELIVERED → READ
    """

    def __init__(
        self,
        repository: PostgreSQLNotificationRepository,
        *,
        inapp_adapter: InAppChannelAdapter | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self._repository = repository
        self._inapp_adapter = inapp_adapter or DefaultInAppAdapter()
        self._clock = clock

    def attempt_delivery(
        self,
        delivery_id: str,
        *,
        event: NotificationEvent | None = None,
    ) -> DeliveryAttemptResult:
        """Tek bir teslimat denemesi yapar.

        1. Delivery'yi yükler
        2. PENDING → SENDING geçişi
        3. Kanal adaptörünü çağırır (IN_APP için no-op)
        4. Başarı → DELIVERED, hata → FAILED + retry planı
        """
        now = self._clock()
        delivery = self._repository.get_delivery(delivery_id)

        if delivery.status not in (
            NotificationDeliveryStatus.PENDING,
            NotificationDeliveryStatus.FAILED,
        ):
            raise NotificationDeliveryError(
                f"Delivery {delivery_id} is in status {delivery.status.value}, "
                "cannot attempt delivery."
            )

        # Transition to SENDING
        with transactional_session(self._repository._session_factory) as session:
            delivery = self._repository.transition_delivery_status(
                session,
                delivery_id,
                expected_status=delivery.status,
                target_status=NotificationDeliveryStatus.SENDING,
                expected_version=delivery.version,
                updated_at=now,
                attempt_count=delivery.attempt_count + 1,
                last_attempt_at=now,
            )

        # Perform delivery
        if event is None:
            event = self._repository.get_event(delivery.event_id)

        success = self._deliver(delivery, event)
        now = self._clock()

        with transactional_session(self._repository._session_factory) as session:
            if success:
                delivery = self._repository.transition_delivery_status(
                    session,
                    delivery_id,
                    expected_status=NotificationDeliveryStatus.SENDING,
                    target_status=NotificationDeliveryStatus.DELIVERED,
                    expected_version=delivery.version,
                    updated_at=now,
                    delivered_at=now,
                )
                # Publish SSE event to the stream hub
                try:
                    hub = get_stream_hub()
                    hub.publish(
                        delivery.recipient_user_id,
                        "new_delivery",
                        {
                            "delivery_id": delivery.delivery_id,
                            "event_id": delivery.event_id,
                            "event_type": event.event_type.value,
                            "scope_type": event.scope_type.value,
                            "scope_id": event.scope_id,
                            "created_at": delivery.created_at.isoformat(),
                        },
                    )
                except Exception:
                    logger.debug("SSE hub publish failed (non-fatal)")
                return DeliveryAttemptResult(
                    delivery_id=delivery_id,
                    status=NotificationDeliveryStatus.DELIVERED,
                    attempt_count=delivery.attempt_count,
                    delivered_at=now,
                )
            else:
                return self._handle_failure(session, delivery, now)

    def mark_read(
        self,
        delivery_id: str,
        *,
        actor_user_id: str,
    ) -> NotificationDelivery:
        """DELIVERED → READ geçişi."""
        now = self._clock()
        delivery = self._repository.get_delivery(delivery_id)
        if delivery.recipient_user_id != actor_user_id:
            raise NotificationDeliveryError(
                f"Actor {actor_user_id} cannot mark delivery "
                f"for recipient {delivery.recipient_user_id}."
            )
        if delivery.status != NotificationDeliveryStatus.DELIVERED:
            raise NotificationDeliveryError(
                f"Delivery {delivery_id} is in status {delivery.status.value}, "
                "only DELIVERED can be marked as READ."
            )
        with transactional_session(self._repository._session_factory) as session:
            return self._repository.transition_delivery_status(
                session,
                delivery_id,
                expected_status=NotificationDeliveryStatus.DELIVERED,
                target_status=NotificationDeliveryStatus.READ,
                expected_version=delivery.version,
                updated_at=now,
                read_at=now,
            )

    def process_retry_queue(
        self,
        *,
        limit: int = 50,
    ) -> tuple[DeliveryAttemptResult, ...]:
        """PENDING/FAILED retry kuyruğunu işler."""
        now = self._clock()
        pending = self._repository.list_pending_retry(limit=limit, now=now)
        results: list[DeliveryAttemptResult] = []
        for delivery in pending:
            try:
                result = self.attempt_delivery(delivery.delivery_id)
                results.append(result)
            except Exception:
                logger.exception("Failed to attempt delivery %s", delivery.delivery_id)
        return tuple(results)

    def _deliver(
        self,
        delivery: NotificationDelivery,
        event: NotificationEvent,
    ) -> bool:
        """Kanal adaptörünü çağırır. IN_APP için her zaman başarılı."""
        try:
            return self._inapp_adapter.deliver(event, delivery)
        except Exception:
            logger.exception("IN_APP adapter failed for delivery %s", delivery.delivery_id)
            return False

    def _handle_failure(
        self,
        session: object,
        delivery: NotificationDelivery,
        now: datetime,
    ) -> DeliveryAttemptResult:
        """Başarısız deneme sonrası retry planı veya UNDELIVERABLE."""
        if delivery.attempt_count >= _MAX_RETRY_ATTEMPTS:
            delivery = self._repository.transition_delivery_status(
                session,
                delivery.delivery_id,
                expected_status=NotificationDeliveryStatus.SENDING,
                target_status=NotificationDeliveryStatus.UNDELIVERABLE,
                expected_version=delivery.version,
                updated_at=now,
                last_error_class="MAX_RETRIES_EXCEEDED",
            )
            return DeliveryAttemptResult(
                delivery_id=delivery.delivery_id,
                status=NotificationDeliveryStatus.UNDELIVERABLE,
                attempt_count=delivery.attempt_count,
                error_class="MAX_RETRIES_EXCEEDED",
            )

        delay_index = min(delivery.attempt_count - 1, len(_RETRY_BACKOFF_SECONDS) - 1)
        delay = timedelta(seconds=_RETRY_BACKOFF_SECONDS[max(0, delay_index)])
        next_attempt = now + delay

        delivery = self._repository.transition_delivery_status(
            session,
            delivery.delivery_id,
            expected_status=NotificationDeliveryStatus.SENDING,
            target_status=NotificationDeliveryStatus.FAILED,
            expected_version=delivery.version,
            updated_at=now,
            last_error_class="DELIVERY_FAILED",
            next_attempt_at=next_attempt,
        )
        return DeliveryAttemptResult(
            delivery_id=delivery.delivery_id,
            status=NotificationDeliveryStatus.FAILED,
            attempt_count=delivery.attempt_count,
            next_attempt_at=next_attempt,
            error_class="DELIVERY_FAILED",
        )
