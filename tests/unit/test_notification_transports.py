from __future__ import annotations

from contextlib import nullcontext
from dataclasses import replace
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Any, Mapping

import pytest

from veri_kalitesi.notifications.delivery_service import NotificationDeliveryService
from veri_kalitesi.notifications.errors import (
    NotificationDeliveryError,
    PermanentNotificationTransportError,
    TemporaryNotificationTransportError,
)
from veri_kalitesi.notifications.models import (
    NotificationChannel,
    NotificationChannelStatus,
    NotificationDelivery,
    NotificationDeliveryStatus,
    NotificationEvent,
    NotificationEventType,
    NotificationScopeType,
)
from veri_kalitesi.notifications.transports import (
    SMTPNotificationAdapter,
    WebhookNotificationAdapter,
)

NOW = datetime(2026, 8, 14, 8, 0, tzinfo=timezone.utc)


class FakeSession:
    def begin(self) -> nullcontext[None]:
        return nullcontext()

    def close(self) -> None:
        return None


class FakeRepository:
    def __init__(
        self,
        delivery: NotificationDelivery,
        event: NotificationEvent,
        channel: NotificationChannel,
    ) -> None:
        self.delivery = delivery
        self.event = event
        self.channel = channel
        self.transitions: list[NotificationDeliveryStatus] = []
        self._session_factory = FakeSession

    def get_delivery(self, delivery_id: str) -> NotificationDelivery:
        assert delivery_id == self.delivery.delivery_id
        return self.delivery

    def get_event(self, event_id: str) -> NotificationEvent:
        assert event_id == self.event.event_id
        return self.event

    def get_channel(self, channel_id: str) -> NotificationChannel:
        assert channel_id == self.channel.channel_id
        return self.channel

    def transition_delivery_status(
        self,
        session: object,
        delivery_id: str,
        *,
        expected_status: NotificationDeliveryStatus,
        target_status: NotificationDeliveryStatus,
        expected_version: int,
        updated_at: datetime,
        **values: Any,
    ) -> NotificationDelivery:
        assert delivery_id == self.delivery.delivery_id
        if self.delivery.status is not expected_status or self.delivery.version != expected_version:
            raise NotificationDeliveryError("concurrent modification")
        self.delivery = replace(
            self.delivery,
            status=target_status,
            version=self.delivery.version + 1,
            updated_at=updated_at,
            **values,
        )
        self.transitions.append(target_status)
        return self.delivery


class FakeSecretResolver:
    def __init__(self, values: Mapping[str, str]) -> None:
        self.values = values
        self.references: list[str] = []

    def resolve(self, secret_reference: str) -> Mapping[str, str]:
        self.references.append(secret_reference)
        return self.values


class FakeSMTPClient:
    def __init__(self) -> None:
        self.messages: list[EmailMessage] = []
        self.login_values: tuple[str, str] | None = None
        self.starttls_called = False

    def starttls(self, *, context: object) -> None:
        self.starttls_called = True

    def login(self, user: str, password: str) -> None:
        self.login_values = (user, password)

    def send_message(self, message: EmailMessage) -> Mapping[str, object]:
        self.messages.append(message)
        return {}

    def quit(self) -> None:
        return None

    def close(self) -> None:
        return None


class FakeSMTPFactory:
    def __init__(self) -> None:
        self.client = FakeSMTPClient()
        self.call: tuple[str, int, float, bool] | None = None

    def __call__(
        self, host: str, port: int, *, timeout: float, use_ssl: bool
    ) -> FakeSMTPClient:
        self.call = (host, port, timeout, use_ssl)
        return self.client


class FakeHttpClient:
    def __init__(self, status: int = 204) -> None:
        self.status = status
        self.calls: list[tuple[str, str, bytes, Mapping[str, str], float]] = []

    def post(
        self,
        url: str,
        *,
        resolved_address: str,
        body: bytes,
        headers: Mapping[str, str],
        timeout: float,
    ) -> int:
        self.calls.append((url, resolved_address, body, headers, timeout))
        return self.status


class RaisingAdapter:
    def __init__(self, error: Exception) -> None:
        self.error = error
        self.calls = 0

    def deliver(self, event: object, delivery: object, channel: object) -> bool:
        self.calls += 1
        raise self.error


class RecordingAdapter:
    def __init__(self) -> None:
        self.calls = 0

    def deliver(self, event: object, delivery: object, channel: object) -> bool:
        self.calls += 1
        return True


def test_email_delivery_routes_to_smtp_with_secret_ref_and_timeout() -> None:
    repository = _repository(
        "EMAIL",
        {
            "host": "smtp.example.com",
            "port": 465,
            "from_address": "alerts@example.com",
            "to_address": "owner@example.com",
            "use_ssl": True,
            "starttls": False,
        },
        secret_ref="secret://local/notification-smtp",
    )
    secrets = FakeSecretResolver({"username": "mailer", "password": "runtime-only"})
    factory = FakeSMTPFactory()
    adapter = SMTPNotificationAdapter(secrets, client_factory=factory, timeout_seconds=7.0)

    result = NotificationDeliveryService(
        repository, adapters={"EMAIL": adapter}, clock=lambda: NOW
    ).attempt_delivery("delivery-1")

    assert result.status is NotificationDeliveryStatus.DELIVERED
    assert factory.call == ("smtp.example.com", 465, 7.0, True)
    assert factory.client.login_values == ("mailer", "runtime-only")
    assert len(factory.client.messages) == 1
    assert secrets.references == ["secret://local/notification-smtp"]
    assert "runtime-only" not in str(repository.channel.target_config)


def test_webhook_delivery_routes_to_http_post_with_timeout_and_idempotency_key() -> None:
    repository = _repository("WEBHOOK", {"url": "https://hooks.example.com/dq"})
    client = FakeHttpClient()
    adapter = WebhookNotificationAdapter(
        FakeSecretResolver({}),
        http_client=client,
        address_resolver=lambda host, port: ("93.184.216.34",),
        timeout_seconds=4.0,
    )

    result = NotificationDeliveryService(
        repository, adapters={"WEBHOOK": adapter}, clock=lambda: NOW
    ).attempt_delivery("delivery-1")

    assert result.status is NotificationDeliveryStatus.DELIVERED
    assert len(client.calls) == 1
    url, resolved_address, body, headers, timeout = client.calls[0]
    assert url == "https://hooks.example.com/dq"
    assert resolved_address == "93.184.216.34"
    assert timeout == 4.0
    assert headers["Idempotency-Key"] == "delivery-1"
    assert b'"event_type":"QUALITY_THRESHOLD"' in body
    assert repository.event.scope_id.encode() not in body


def test_in_app_default_behavior_remains_successful() -> None:
    repository = _repository("IN_APP", {})

    result = NotificationDeliveryService(repository, clock=lambda: NOW).attempt_delivery(
        "delivery-1"
    )

    assert result.status is NotificationDeliveryStatus.DELIVERED


def test_unknown_channel_type_is_explicitly_undeliverable() -> None:
    repository = _repository("CARRIER_PIGEON", {})

    result = NotificationDeliveryService(repository, clock=lambda: NOW).attempt_delivery(
        "delivery-1"
    )

    assert result.status is NotificationDeliveryStatus.UNDELIVERABLE
    assert result.error_class == "UNSUPPORTED_CHANNEL_TYPE"
    assert repository.transitions[-2:] == [
        NotificationDeliveryStatus.FAILED,
        NotificationDeliveryStatus.UNDELIVERABLE,
    ]


def test_temporary_transport_error_schedules_retry_with_error_class() -> None:
    repository = _repository("EMAIL", {})
    adapter = RaisingAdapter(TemporaryNotificationTransportError("SMTP_TEMPORARY_ERROR"))

    result = NotificationDeliveryService(
        repository, adapters={"EMAIL": adapter}, clock=lambda: NOW
    ).attempt_delivery("delivery-1")

    assert result.status is NotificationDeliveryStatus.FAILED
    assert result.next_attempt_at == NOW
    assert result.error_class == "SMTP_TEMPORARY_ERROR"
    assert repository.delivery.last_error_class == "SMTP_TEMPORARY_ERROR"


def test_permanent_webhook_4xx_skips_retry_and_becomes_undeliverable() -> None:
    repository = _repository("WEBHOOK", {"url": "https://hooks.example.com/dq"})
    adapter = WebhookNotificationAdapter(
        FakeSecretResolver({}),
        http_client=FakeHttpClient(status=400),
        address_resolver=lambda host, port: ("93.184.216.34",),
    )

    result = NotificationDeliveryService(
        repository, adapters={"WEBHOOK": adapter}, clock=lambda: NOW
    ).attempt_delivery("delivery-1")

    assert result.status is NotificationDeliveryStatus.UNDELIVERABLE
    assert result.next_attempt_at is None
    assert result.error_class == "WEBHOOK_CLIENT_ERROR"


def test_temporary_webhook_5xx_schedules_retry() -> None:
    repository = _repository("WEBHOOK", {"url": "https://hooks.example.com/dq"})
    adapter = WebhookNotificationAdapter(
        FakeSecretResolver({}),
        http_client=FakeHttpClient(status=503),
        address_resolver=lambda host, port: ("93.184.216.34",),
    )

    result = NotificationDeliveryService(
        repository, adapters={"WEBHOOK": adapter}, clock=lambda: NOW
    ).attempt_delivery("delivery-1")

    assert result.status is NotificationDeliveryStatus.FAILED
    assert result.error_class == "WEBHOOK_SERVER_ERROR"
    assert result.next_attempt_at == NOW


def test_maximum_attempts_preserve_max_retries_exceeded_behavior() -> None:
    repository = _repository("EMAIL", {}, attempt_count=4)
    adapter = RaisingAdapter(TemporaryNotificationTransportError("SMTP_TEMPORARY_ERROR"))

    result = NotificationDeliveryService(
        repository, adapters={"EMAIL": adapter}, clock=lambda: NOW
    ).attempt_delivery("delivery-1")

    assert result.status is NotificationDeliveryStatus.UNDELIVERABLE
    assert result.attempt_count == 5
    assert result.error_class == "MAX_RETRIES_EXCEEDED"
    assert repository.transitions[-2:] == [
        NotificationDeliveryStatus.FAILED,
        NotificationDeliveryStatus.UNDELIVERABLE,
    ]


def test_delivered_id_is_not_sent_to_external_adapter_twice() -> None:
    repository = _repository("EMAIL", {})
    adapter = RecordingAdapter()
    service = NotificationDeliveryService(
        repository, adapters={"EMAIL": adapter}, clock=lambda: NOW
    )
    service.attempt_delivery("delivery-1")

    with pytest.raises(NotificationDeliveryError):
        service.attempt_delivery("delivery-1")

    assert adapter.calls == 1


def test_webhook_rejects_private_network_target_before_http_call() -> None:
    channel = _channel("WEBHOOK", {"url": "https://internal.example/dq"})
    client = FakeHttpClient()
    adapter = WebhookNotificationAdapter(
        FakeSecretResolver({}),
        http_client=client,
        address_resolver=lambda host, port: ("10.0.0.8",),
    )

    with pytest.raises(PermanentNotificationTransportError) as error:
        adapter.deliver(_event(), _delivery(), channel)

    assert error.value.error_class == "WEBHOOK_TARGET_FORBIDDEN"
    assert client.calls == []


def test_plaintext_secret_in_channel_config_is_rejected() -> None:
    channel = _channel(
        "EMAIL",
        {
            "host": "smtp.example.com",
            "from_address": "alerts@example.com",
            "to_address": "owner@example.com",
            "password": "must-not-be-stored",
        },
    )

    with pytest.raises(PermanentNotificationTransportError) as error:
        SMTPNotificationAdapter(FakeSecretResolver({})).deliver(
            _event(), _delivery(), channel
        )

    assert error.value.error_class == "PLAINTEXT_SECRET_FORBIDDEN"


def _repository(
    channel_type: str,
    target_config: dict[str, object],
    *,
    secret_ref: str | None = None,
    attempt_count: int = 0,
) -> FakeRepository:
    return FakeRepository(
        _delivery(attempt_count=attempt_count),
        _event(),
        _channel(channel_type, target_config, secret_ref=secret_ref),
    )


def _event() -> NotificationEvent:
    return NotificationEvent(
        event_id="event-1",
        event_type=NotificationEventType.QUALITY_THRESHOLD,
        scope_type=NotificationScopeType.DATASET,
        scope_id="sensitive-scope-reference",
        deduplication_key="dedup-1",
        occurred_at=NOW,
        correlation_id="correlation-1",
    )


def _delivery(*, attempt_count: int = 0) -> NotificationDelivery:
    return NotificationDelivery(
        delivery_id="delivery-1",
        event_id="event-1",
        recipient_user_id="recipient-1",
        channel_id="channel-1",
        status=NotificationDeliveryStatus.PENDING,
        attempt_count=attempt_count,
        version=1,
        created_at=NOW,
        updated_at=NOW,
    )


def _channel(
    channel_type: str,
    target_config: dict[str, object],
    *,
    secret_ref: str | None = None,
) -> NotificationChannel:
    return NotificationChannel(
        channel_id="channel-1",
        name="Test channel",
        channel_type=channel_type,
        target_config=target_config,
        allowed_event_types=(NotificationEventType.QUALITY_THRESHOLD.value,),
        status=NotificationChannelStatus.ACTIVE,
        policy_version="CHANNEL_POLICY_V1",
        version=1,
        created_by="test-suite",
        created_at=NOW,
        updated_at=NOW,
        secret_ref=secret_ref,
    )
