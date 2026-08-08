"""DS-09 notification query service — read-only inbox/delivery queries.

Permission: recipient_user_id must match the requesting actor.
"""

from __future__ import annotations

from dataclasses import dataclass

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


@dataclass(frozen=True)
class InboxPage:
    """Paginated inbox result."""

    deliveries: tuple[NotificationDelivery, ...]
    total_unread: int
    cursor: str | None = None
    has_more: bool = False


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
        return InboxPage(
            deliveries=page,
            total_unread=total_unread,
            cursor=next_cursor,
            has_more=has_more,
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

    def _require_self_access(
        self,
        target_user_id: str,
        actor_user_id: str,
    ) -> None:
        if target_user_id != actor_user_id:
            raise NotificationAuthorizationError(
                f"Actor {actor_user_id} cannot access data for {target_user_id}."
            )
