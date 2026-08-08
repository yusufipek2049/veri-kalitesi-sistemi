"""DS-09 concrete notification batch stager.

Resolves recipients from subscriptions, creates staged events/deliveries/jobs,
and returns a PreparedNotificationBatch for issue transaction staging.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Callable
from uuid import uuid4

from veri_kalitesi.notifications.contracts import (
    PreparedNotificationBatch,
    _StagedDelivery,
    _StagedDeliveryJob,
    _StagedEvent,
)
from veri_kalitesi.notifications.models import (
    NotificationDeliveryStatus,
    NotificationEvent,
    NotificationSubscriptionStatus,
    validate_notification_event,
    validate_payload_safety,
)
from veri_kalitesi.notifications.postgresql_repository import (
    PostgreSQLNotificationRepository,
)


class DefaultNotificationBatchStager:
    """Concrete batch stager for production use.

    Resolves recipients from subscriptions, creates staged events/deliveries,
    and returns a PreparedNotificationBatch.
    """

    def __init__(
        self,
        repository: PostgreSQLNotificationRepository,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self._repository = repository
        self._clock = clock

    def prepare_batch(
        self,
        event: NotificationEvent,
        *,
        recipient_user_ids: tuple[str, ...],
        channel_id: str,
        actor_id: str,
        correlation_id: str,
    ) -> PreparedNotificationBatch:
        """Prepare a notification batch for transaction staging.

        1. Validates event and payload
        2. Resolves recipients from subscriptions (or uses provided IDs)
        3. Creates staged events, deliveries, and delivery jobs
        4. Returns PreparedNotificationBatch
        """
        now = self._clock()
        validate_notification_event(event)
        if event.payload:
            validate_payload_safety(event.payload)

        # Compute digests
        payload_bytes = json.dumps(event.payload, sort_keys=True, default=str).encode()
        payload_digest = hashlib.sha256(payload_bytes).hexdigest()
        dedup_digest = hashlib.sha256(event.deduplication_key.encode()).hexdigest()

        # Fill in defaults
        source_ref = event.source_ref or f"ISSUE.{event.scope_id}"
        published_at = event.published_at or now

        staged_event = _StagedEvent(
            event_id=event.event_id,
            event_type=event.event_type.value,
            scope_type=event.scope_type.value,
            scope_id=event.scope_id,
            source_ref=source_ref,
            deduplication_key_digest=dedup_digest,
            payload_digest=payload_digest,
            payload=event.payload,
            correlation_id=event.correlation_id,
            policy_version=event.policy_version,
            occurred_at=event.occurred_at,
            published_at=published_at,
        )

        # Resolve recipients
        recipients = self._resolve_recipients(event, recipient_user_ids)

        # Create deliveries and jobs
        staged_deliveries: list[_StagedDelivery] = []
        staged_jobs: list[_StagedDeliveryJob] = []

        for recipient_id in recipients:
            delivery_id = str(uuid4())
            staged_deliveries.append(
                _StagedDelivery(
                    delivery_id=delivery_id,
                    event_id=event.event_id,
                    recipient_user_id=recipient_id,
                    channel_id=channel_id,
                    status=NotificationDeliveryStatus.PENDING,
                    created_at=now,
                )
            )
            staged_jobs.append(
                _StagedDeliveryJob(
                    job_type="NOTIFICATION_DELIVERY",
                    idempotency_key=f"notif-delivery:{delivery_id}",
                    payload={
                        "delivery_id": delivery_id,
                        "event_id": event.event_id,
                    },
                    correlation_id=correlation_id,
                )
            )

        return PreparedNotificationBatch(
            events=(staged_event,),
            deliveries=tuple(staged_deliveries),
            delivery_jobs=tuple(staged_jobs),
        )

    def _resolve_recipients(
        self,
        event: NotificationEvent,
        provided_ids: tuple[str, ...],
    ) -> tuple[str, ...]:
        """Resolve recipients from subscriptions or provided IDs.

        For ISSUE_ASSIGNED events (mandatory), the provided IDs are used directly.
        For other events, subscriptions are queried.
        """
        if provided_ids:
            return provided_ids

        # For mandatory events without explicit recipients, return empty
        # (the event is still created but no deliveries)
        subscriptions = self._repository.list_subscriptions(
            event_type=event.event_type.value,
            status=NotificationSubscriptionStatus.ACTIVE,
        )
        return tuple(s.user_id for s in subscriptions)
