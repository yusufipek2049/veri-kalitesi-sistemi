"""DQ-CAP-009: Canonical notification channel adapters (fake/sandbox).

Sistem içi bildirim otoriter kalır; harici kanal adaptörleri aynı veri-minimum
olayı tüketir. Idempotency key, dedup/suppression penceresi, routing, SLA ve
escalation sürümlü politikadan gelir. Gerçek kanal hatası kalite sonucunu
değiştirmez.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Callable, Mapping, Protocol

from veri_kalitesi.notifications.errors import (
    NotificationTechnicalError,
    NotificationValidationError,
)
from veri_kalitesi.notifications.models import NotificationEvent, NotificationEventType


# ---------------------------------------------------------------------------
# Policy models
# ---------------------------------------------------------------------------


class ChannelKind(str, Enum):
    EMAIL = "EMAIL"
    MESSAGING = "MESSAGING"
    SERVICENOW = "SERVICENOW"
    JIRA = "JIRA"


class EscalationLevel(str, Enum):
    NONE = "NONE"
    FIRST = "FIRST"
    SECOND = "SECOND"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class ChannelRoute:
    """Tek bir kanal yönlendirme kuralı."""

    channel: ChannelKind
    event_types: frozenset[NotificationEventType]
    escalation_level: EscalationLevel = EscalationLevel.NONE
    sla_seconds: int | None = None


@dataclass(frozen=True)
class NotificationChannelPolicy:
    """Sürümlü bildirim kanal politikası.

    Idempotency, dedup/suppression, routing ve SLA/escalation bu politikadan
    çözülür. Politika yoksa kanal işlemi yapılmaz (fail-closed).
    """

    version: str
    routes: tuple[ChannelRoute, ...]
    dedup_window_seconds: int = 300
    suppression_window_seconds: int = 0
    max_delivery_attempts: int = 1

    def __post_init__(self) -> None:
        if not self.version or not self.version.strip():
            raise NotificationValidationError("Channel policy version is required.")
        if self.dedup_window_seconds < 0:
            raise NotificationValidationError("Dedup window must be non-negative.")
        if self.suppression_window_seconds < 0:
            raise NotificationValidationError("Suppression window must be non-negative.")
        if self.max_delivery_attempts < 1:
            raise NotificationValidationError("Delivery attempts must be positive.")


# ---------------------------------------------------------------------------
# Adapter protocol and results
# ---------------------------------------------------------------------------


class ChannelDeliveryStatus(str, Enum):
    DELIVERED = "DELIVERED"
    SUPPRESSED = "SUPPRESSED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class ChannelDeliveryResult:
    channel: ChannelKind
    event_id: str
    status: ChannelDeliveryStatus
    idempotency_key: str
    attempt: int = 1


class NotificationChannelAdapter(Protocol):
    """Harici kanal adaptörü sözleşmesi (fake/sandbox)."""

    @property
    def channel_kind(self) -> ChannelKind: ...

    def deliver(self, event: NotificationEvent, *, idempotency_key: str) -> bool:
        """Veri-minimum olayı kanala iletir. Başarı True, hata False."""
        ...


# ---------------------------------------------------------------------------
# Fake/sandbox adapters
# ---------------------------------------------------------------------------


@dataclass
class FakeChannelAdapter:
    """Sentetik kanal adaptörü — gerçek kanal hatası kalite sonucunu değiştirmez.

    Yalnız sandbox/test ortamında kullanılır. İletim her zaman başarılıdır
    (kanal erişilebilir kabul edilir) ancak adaptör etkin değilse False döner.
    """

    _channel_kind: ChannelKind
    _enabled: bool = True
    _delivered_log: list[tuple[str, str]] = field(default_factory=list)

    @property
    def channel_kind(self) -> ChannelKind:
        return self._channel_kind

    def deliver(self, event: NotificationEvent, *, idempotency_key: str) -> bool:
        if not self._enabled:
            return False
        self._delivered_log.append((event.event_id, idempotency_key))
        return True

    @property
    def delivered_log(self) -> tuple[tuple[str, str], ...]:
        return tuple(self._delivered_log)


# ---------------------------------------------------------------------------
# Dispatcher (idempotency + dedup/suppression + routing)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DispatchOutcome:
    """Tek bir olayın tüm kanallara dağıtım sonucu."""

    event_id: str
    results: tuple[ChannelDeliveryResult, ...]
    suppressed: bool = False


class NotificationChannelDispatcher:
    """Canonical event'i politika kontrollü kanallara dağıtır.

    - Idempotency: aynı event_id + channel için tekrar iletim yapılmaz.
    - Dedup/suppression: politika penceresi içinde aynı dedup key baskılanır.
    - Routing: olay tipi → kanal eşlemesi politikadan gelir.
    - Kanal hatası kalite sonucunu değiştirmez; FAILED olarak kaydedilir.
    """

    def __init__(
        self,
        policy: NotificationChannelPolicy,
        adapters: Mapping[ChannelKind, NotificationChannelAdapter],
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        if not policy.routes:
            raise NotificationValidationError("Channel policy must define at least one route.")
        self._policy = policy
        self._adapters = dict(adapters)
        self._clock = clock
        # idempotency: (event_id, channel) → result
        self._idempotency_log: dict[tuple[str, ChannelKind], ChannelDeliveryResult] = {}
        # dedup/suppression: dedup_key → last_seen_at
        self._dedup_log: dict[str, datetime] = {}

    @property
    def policy(self) -> NotificationChannelPolicy:
        return self._policy

    def dispatch(self, event: NotificationEvent) -> DispatchOutcome:
        """Politika kurallarına göre olayı uygun kanallara dağıt."""
        now = self._clock()
        if now.tzinfo is None:
            raise NotificationValidationError("Dispatcher clock must be timezone-aware.")

        # Dedup/suppression check
        if self._is_suppressed(event.deduplication_key, now):
            return DispatchOutcome(event_id=event.event_id, results=(), suppressed=True)

        # Record dedup key
        self._dedup_log[event.deduplication_key] = now

        # Resolve routes for this event type
        matching_routes = tuple(
            route
            for route in self._policy.routes
            if event.event_type in route.event_types
        )
        if not matching_routes:
            return DispatchOutcome(event_id=event.event_id, results=())

        results: list[ChannelDeliveryResult] = []
        for route in matching_routes:
            result = self._deliver_to_channel(event, route.channel)
            results.append(result)

        return DispatchOutcome(event_id=event.event_id, results=tuple(results))

    def _is_suppressed(self, dedup_key: str, now: datetime) -> bool:
        last_seen = self._dedup_log.get(dedup_key)
        if last_seen is None:
            return False
        window = timedelta(seconds=self._policy.dedup_window_seconds)
        suppression = timedelta(seconds=self._policy.suppression_window_seconds)
        effective_window = max(window, suppression)
        return (now - last_seen) < effective_window

    def _deliver_to_channel(
        self, event: NotificationEvent, channel: ChannelKind
    ) -> ChannelDeliveryResult:
        idempotency_key = f"{event.event_id}:{channel.value}"

        # Idempotency check
        existing = self._idempotency_log.get((event.event_id, channel))
        if existing is not None:
            return existing

        adapter = self._adapters.get(channel)
        if adapter is None:
            result = ChannelDeliveryResult(
                channel=channel,
                event_id=event.event_id,
                status=ChannelDeliveryStatus.FAILED,
                idempotency_key=idempotency_key,
            )
            self._idempotency_log[(event.event_id, channel)] = result
            return result

        try:
            success = adapter.deliver(event, idempotency_key=idempotency_key)
        except Exception:
            success = False

        status = ChannelDeliveryStatus.DELIVERED if success else ChannelDeliveryStatus.FAILED
        result = ChannelDeliveryResult(
            channel=channel,
            event_id=event.event_id,
            status=status,
            idempotency_key=idempotency_key,
        )
        self._idempotency_log[(event.event_id, channel)] = result
        return result
