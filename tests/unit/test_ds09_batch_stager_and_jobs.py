"""DS-09 batch stager and job payload unit tests."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from veri_kalitesi.notifications.contracts import PreparedNotificationBatch
from veri_kalitesi.notifications.jobs import (
    NotificationDeliveryJobPayload,
    notification_delivery_idempotency_key,
)
from veri_kalitesi.jobs.worker import PermanentJobError


# ---------------------------------------------------------------------------
# PreparedNotificationBatch
# ---------------------------------------------------------------------------


class TestPreparedNotificationBatch:
    def test_empty_batch(self) -> None:
        batch = PreparedNotificationBatch()
        assert batch.is_empty is True

    def test_batch_with_event_not_empty(self) -> None:
        from veri_kalitesi.notifications.contracts import _StagedEvent

        event = _StagedEvent(
            event_id=str(uuid4()),
            event_type="QUALITY_THRESHOLD",
            scope_type="RULE",
            scope_id="rule-01",
            source_ref="ISSUE.rule-01",
            deduplication_key_digest="abc123",
            payload_digest="def456",
            payload={},
            correlation_id=str(uuid4()),
            policy_version="DS09_EVENT_POLICY_V1",
            occurred_at=datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc),
            published_at=datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc),
        )
        batch = PreparedNotificationBatch(events=(event,))
        assert batch.is_empty is False


# ---------------------------------------------------------------------------
# NotificationDeliveryJobPayload
# ---------------------------------------------------------------------------


class TestNotificationDeliveryJobPayload:
    def test_to_dict(self) -> None:
        payload = NotificationDeliveryJobPayload(
            delivery_id="delivery-01",
            event_id="event-01",
        )
        d = payload.to_dict()
        assert d["delivery_id"] == "delivery-01"
        assert d["event_id"] == "event-01"

    def test_from_dict(self) -> None:
        payload = NotificationDeliveryJobPayload.from_dict(
            {"delivery_id": "delivery-01", "event_id": "event-01"}
        )
        assert payload.delivery_id == "delivery-01"
        assert payload.event_id == "event-01"

    def test_from_dict_missing_delivery_id(self) -> None:
        with pytest.raises(PermanentJobError):
            NotificationDeliveryJobPayload.from_dict({"event_id": "event-01"})

    def test_from_dict_missing_event_id(self) -> None:
        with pytest.raises(PermanentJobError):
            NotificationDeliveryJobPayload.from_dict({"delivery_id": "delivery-01"})

    def test_from_dict_empty_delivery_id(self) -> None:
        with pytest.raises(PermanentJobError):
            NotificationDeliveryJobPayload.from_dict({"delivery_id": "", "event_id": "event-01"})


# ---------------------------------------------------------------------------
# Idempotency key
# ---------------------------------------------------------------------------


class TestIdempotencyKey:
    def test_deterministic(self) -> None:
        key1 = notification_delivery_idempotency_key("delivery-01")
        key2 = notification_delivery_idempotency_key("delivery-01")
        assert key1 == key2

    def test_unique_per_delivery(self) -> None:
        key1 = notification_delivery_idempotency_key("delivery-01")
        key2 = notification_delivery_idempotency_key("delivery-02")
        assert key1 != key2

    def test_format(self) -> None:
        key = notification_delivery_idempotency_key("delivery-01")
        assert key == "notif-delivery:delivery-01"
