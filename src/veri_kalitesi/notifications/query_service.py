"""DS-09 notification query service — read-only inbox/delivery queries.

Permission: recipient_user_id must match the requesting actor.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from veri_kalitesi.notifications.errors import (
    NotificationAuthorizationError,
)
from veri_kalitesi.notifications.models import (
    NotificationChannel,
    NotificationDelivery,
    NotificationDeliveryStatus,
    NotificationEvent,
    NotificationSubscription,
    validate_recipient_id,
)
from veri_kalitesi.notifications.postgresql_repository import (
    PostgreSQLNotificationRepository,
)
from veri_kalitesi.persistence import transactional_session


@dataclass(frozen=True)
class InboxPage:
    """Paginated inbox result."""

    deliveries: tuple[NotificationDelivery, ...]
    total_unread: int
    cursor: str | None = None
    has_more: bool = False
    failed_count: int = 0
    today_count: int = 0


class NotificationQueryService:
    """Read-only notification query service.

    Inbox listing, unread count, delivery detail, and subscription queries.
    All queries validate that the requesting actor matches the recipient.
    """

    def __init__(self, repository: PostgreSQLNotificationRepository) -> None:
        self._repository = repository

    def get_inbox(
        self,
        *,
        recipient_user_id: str,
        actor_user_id: str,
        status: NotificationDeliveryStatus | None = None,
        event_type: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
    ) -> InboxPage:
        """Paginated inbox for a recipient. Actor must match recipient."""
        self._require_self_access(recipient_user_id, actor_user_id)
        validate_recipient_id(recipient_user_id)
        deliveries = self._repository.list_for_recipient(
            recipient_user_id,
            status=status,
            event_type=event_type,
            limit=limit + 1,
            cursor=cursor,
        )
        has_more = len(deliveries) > limit
        page = deliveries[:limit]
        next_cursor = page[-1].delivery_id if has_more and page else None
        total_unread = self._repository.count_unread(recipient_user_id)
        failed_count = self._repository.count_failed(recipient_user_id)
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = self._repository.count_today(recipient_user_id, today_start)
        return InboxPage(
            deliveries=page,
            total_unread=total_unread,
            cursor=next_cursor,
            has_more=has_more,
            failed_count=failed_count,
            today_count=today_count,
        )

    def count_unread(
        self,
        *,
        recipient_user_id: str,
        actor_user_id: str,
    ) -> int:
        """Count unread deliveries for a recipient."""
        self._require_self_access(recipient_user_id, actor_user_id)
        validate_recipient_id(recipient_user_id)
        return self._repository.count_unread(recipient_user_id)

    def get_delivery(
        self,
        delivery_id: str,
        *,
        actor_user_id: str,
    ) -> NotificationDelivery:
        """Get a single delivery detail. Actor must be the recipient."""
        delivery = self._repository.get_delivery(delivery_id)
        if delivery.recipient_user_id != actor_user_id:
            raise NotificationAuthorizationError(
                f"Actor {actor_user_id} cannot access delivery {delivery_id}."
            )
        return delivery

    def get_event(
        self,
        event_id: str,
        *,
        actor_user_id: str,
    ) -> NotificationEvent:
        """Get event detail. Actor must be a recipient of a delivery for this event."""
        event = self._repository.get_event(event_id)
        # Verify actor is a recipient of at least one delivery for this event
        deliveries = self._repository.list_for_recipient(
            actor_user_id,
            limit=1000,
        )
        if not any(d.event_id == event_id for d in deliveries):
            raise NotificationAuthorizationError(
                f"Actor {actor_user_id} cannot access event {event_id}."
            )
        return event

    def get_events_by_ids(self, event_ids: list[str]) -> dict:
        """Batch-lookup events by IDs. No auth check — caller must verify access."""
        return self._repository.get_events_by_ids(event_ids)

    def list_subscriptions(
        self,
        *,
        user_id: str,
        actor_user_id: str,
        event_type: str | None = None,
    ) -> tuple[NotificationSubscription, ...]:
        """List subscriptions for a user. Actor must match user."""
        self._require_self_access(user_id, actor_user_id)
        return self._repository.list_subscriptions(
            user_id=user_id,
            event_type=event_type,
        )

    def list_channels(
        self,
        *,
        status: str | None = None,
        channel_type: str | None = None,
    ) -> tuple[NotificationChannel, ...]:
        """List notification channels with optional filters."""
        return self._repository.list_channels(status=status, channel_type=channel_type)

    def mark_all_read(
        self,
        *,
        recipient_user_id: str,
        actor_user_id: str,
    ) -> int:
        """Mark all DELIVERED items as READ for a recipient. Returns count."""
        self._require_self_access(recipient_user_id, actor_user_id)
        validate_recipient_id(recipient_user_id)
        now = datetime.now(timezone.utc)
        with transactional_session(self._repository._session_factory) as session:
            return self._repository.mark_all_read_for_recipient(
                session,
                recipient_user_id,
                now=now,
            )

    def _require_self_access(
        self,
        target_user_id: str,
        actor_user_id: str,
    ) -> None:
        if target_user_id != actor_user_id:
            raise NotificationAuthorizationError(
                f"Actor {actor_user_id} cannot access data for {target_user_id}."
            )
