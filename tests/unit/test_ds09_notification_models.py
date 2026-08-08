"""DS-09 notification domain model unit tests."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from veri_kalitesi.notifications.models import (
    MANDATORY_EVENT_TYPES,
    NotificationDeliveryStatus,
    NotificationEvent,
    NotificationEventType,
    NotificationScopeType,
    validate_delivery_transition,
    validate_notification_event,
    validate_payload_safety,
    validate_recipient_id,
)
from veri_kalitesi.notifications.errors import NotificationValidationError


# ---------------------------------------------------------------------------
# Bounded string ID validation
# ---------------------------------------------------------------------------


class TestBoundedIdValidation:
    def test_valid_bounded_id(self) -> None:
        validate_recipient_id("user-data-steward-01")
        validate_recipient_id("11111111-1111-4111-8111-111111111111")
        validate_recipient_id("worker-01")

    def test_empty_id_rejected(self) -> None:
        with pytest.raises(NotificationValidationError):
            validate_recipient_id("")

    def test_too_long_id_rejected(self) -> None:
        with pytest.raises(NotificationValidationError):
            validate_recipient_id("x" * 129)

    def test_special_chars_rejected(self) -> None:
        with pytest.raises(NotificationValidationError):
            validate_recipient_id("user with spaces")


# ---------------------------------------------------------------------------
# Notification event validation
# ---------------------------------------------------------------------------


class TestNotificationEventValidation:
    def _make_event(self, **overrides: object) -> NotificationEvent:
        defaults = dict(
            event_id=str(uuid4()),
            event_type=NotificationEventType.QUALITY_THRESHOLD,
            scope_type=NotificationScopeType.RULE,
            scope_id="rule-01",
            deduplication_key=f"ISSUE.test-{uuid4()}",
            occurred_at=datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc),
            correlation_id=str(uuid4()),
        )
        defaults.update(overrides)
        return NotificationEvent(**defaults)  # type: ignore[arg-type]

    def test_valid_event(self) -> None:
        event = self._make_event()
        validate_notification_event(event)

    def test_naive_occurred_at_rejected(self) -> None:
        event = self._make_event(occurred_at=datetime(2026, 8, 6, 12, 0))
        with pytest.raises(NotificationValidationError, match="timezone-aware"):
            validate_notification_event(event)

    def test_empty_deduplication_key_rejected(self) -> None:
        event = self._make_event(deduplication_key="")
        with pytest.raises(NotificationValidationError):
            validate_notification_event(event)


# ---------------------------------------------------------------------------
# Delivery state machine
# ---------------------------------------------------------------------------


class TestDeliveryStateMachine:
    def test_pending_to_sending(self) -> None:
        validate_delivery_transition(
            NotificationDeliveryStatus.PENDING,
            NotificationDeliveryStatus.SENDING,
        )

    def test_sending_to_delivered(self) -> None:
        validate_delivery_transition(
            NotificationDeliveryStatus.SENDING,
            NotificationDeliveryStatus.DELIVERED,
        )

    def test_sending_to_failed(self) -> None:
        validate_delivery_transition(
            NotificationDeliveryStatus.SENDING,
            NotificationDeliveryStatus.FAILED,
        )

    def test_pending_to_delivered_forbidden(self) -> None:
        with pytest.raises(NotificationValidationError, match="forbidden"):
            validate_delivery_transition(
                NotificationDeliveryStatus.PENDING,
                NotificationDeliveryStatus.DELIVERED,
            )

    def test_delivered_to_failed_forbidden(self) -> None:
        with pytest.raises(NotificationValidationError, match="forbidden"):
            validate_delivery_transition(
                NotificationDeliveryStatus.DELIVERED,
                NotificationDeliveryStatus.FAILED,
            )

    def test_delivered_to_read(self) -> None:
        validate_delivery_transition(
            NotificationDeliveryStatus.DELIVERED,
            NotificationDeliveryStatus.READ,
        )

    def test_read_to_failed_forbidden(self) -> None:
        with pytest.raises(NotificationValidationError, match="forbidden"):
            validate_delivery_transition(
                NotificationDeliveryStatus.READ,
                NotificationDeliveryStatus.FAILED,
            )

    def test_failed_to_sending(self) -> None:
        validate_delivery_transition(
            NotificationDeliveryStatus.FAILED,
            NotificationDeliveryStatus.SENDING,
        )

    def test_failed_to_undeliverable(self) -> None:
        validate_delivery_transition(
            NotificationDeliveryStatus.FAILED,
            NotificationDeliveryStatus.UNDELIVERABLE,
        )

    def test_undeliverable_to_rerouted(self) -> None:
        validate_delivery_transition(
            NotificationDeliveryStatus.UNDELIVERABLE,
            NotificationDeliveryStatus.REROUTED,
        )


# ---------------------------------------------------------------------------
# Payload safety
# ---------------------------------------------------------------------------


class TestPayloadSafety:
    def test_safe_payload(self) -> None:
        validate_payload_safety({"rule_id": "rule-01", "score": 42.5})

    def test_forbidden_key_rejected(self) -> None:
        with pytest.raises(NotificationValidationError, match="forbidden"):
            validate_payload_safety({"password": "secret123"})

    def test_nested_forbidden_key_rejected(self) -> None:
        with pytest.raises(NotificationValidationError, match="forbidden"):
            validate_payload_safety({"data": {"token": "abc123"}})


# ---------------------------------------------------------------------------
# Mandatory event types
# ---------------------------------------------------------------------------


class TestMandatoryEventTypes:
    def test_issue_assigned_is_mandatory(self) -> None:
        assert NotificationEventType.ISSUE_ASSIGNED in MANDATORY_EVENT_TYPES

    def test_quality_threshold_not_mandatory(self) -> None:
        assert NotificationEventType.QUALITY_THRESHOLD not in MANDATORY_EVENT_TYPES
