"""PostgreSQL notification event/channel/subscription/delivery repository."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Sequence

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    and_,
    func,
    insert,
    or_,
    select,
    text,
    update,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import IntegrityError

from veri_kalitesi.audit.models import PreparedAuditEvent
from veri_kalitesi.notifications.contracts import (
    PreparedNotificationBatch,
)
from veri_kalitesi.notifications.errors import (
    NotificationConflictError,
    NotificationDeliveryError,
    NotificationNotFoundError,
)
from veri_kalitesi.notifications.models import (
    NotificationChannel,
    NotificationChannelStatus,
    NotificationDelivery,
    NotificationDeliveryStatus,
    NotificationEvent,
    NotificationEventType,
    NotificationScopeType,
    NotificationSubscription,
    NotificationSubscriptionStatus,
    validate_delivery_transition,
)
from veri_kalitesi.persistence import DEFAULT_SCHEMA_NAME, SessionFactory


# ---------------------------------------------------------------------------
# Table definitions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NotificationTables:
    notification_channels: Table
    notification_events: Table
    notification_subscriptions: Table
    notification_deliveries: Table


def notification_tables(schema: str = DEFAULT_SCHEMA_NAME) -> NotificationTables:
    metadata = MetaData(schema=schema)

    notification_channels = Table(
        "notification_channels",
        metadata,
        Column("channel_id", String(36), primary_key=True),
        Column("name", String(120), nullable=False),
        Column("channel_type", String(24), nullable=False),
        Column("target_config", JSONB, nullable=False, server_default="{}"),
        Column("secret_ref", String(255), nullable=True),
        Column("allowed_event_types", JSONB, nullable=False),
        Column("status", String(24), nullable=False, server_default="ACTIVE"),
        Column("policy_version", String(80), nullable=False),
        Column("version", Integer, nullable=False, server_default="1"),
        Column("created_by", String(128), nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("updated_at", DateTime(timezone=True), nullable=False),
    )

    notification_events = Table(
        "notification_events",
        metadata,
        Column("event_id", String(36), primary_key=True),
        Column("event_type", String(40), nullable=False),
        Column("scope_type", String(30), nullable=False),
        Column("scope_id", String(128), nullable=False),
        Column("source_ref", String(200), nullable=False),
        Column("deduplication_key_digest", String(64), nullable=False),
        Column("payload_digest", String(64), nullable=False),
        Column("payload", JSONB, nullable=False),
        Column("correlation_id", String(128), nullable=False),
        Column("policy_version", String(80), nullable=False),
        Column("occurred_at", DateTime(timezone=True), nullable=False),
        Column("published_at", DateTime(timezone=True), nullable=False),
    )

    notification_subscriptions = Table(
        "notification_subscriptions",
        metadata,
        Column("subscription_id", String(36), primary_key=True),
        Column("user_id", String(128), nullable=False),
        Column("event_type", String(40), nullable=False),
        Column("scope_type", String(30), nullable=True),
        Column("scope_id", String(128), nullable=True),
        Column("channel_id", String(36), nullable=False),
        Column("status", String(24), nullable=False, server_default="ACTIVE"),
        Column("policy_version", String(80), nullable=False),
        Column("version", Integer, nullable=False, server_default="1"),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("updated_at", DateTime(timezone=True), nullable=False),
    )

    notification_deliveries = Table(
        "notification_deliveries",
        metadata,
        Column("delivery_id", String(36), primary_key=True),
        Column("event_id", String(36), nullable=False),
        Column("recipient_user_id", String(128), nullable=False),
        Column("channel_id", String(36), nullable=False),
        Column("status", String(24), nullable=False),
        Column("attempt_count", Integer, nullable=False, server_default="0"),
        Column("last_error_class", String(80), nullable=True),
        Column("last_attempt_at", DateTime(timezone=True), nullable=True),
        Column("next_attempt_at", DateTime(timezone=True), nullable=True),
        Column("delivered_at", DateTime(timezone=True), nullable=True),
        Column("read_at", DateTime(timezone=True), nullable=True),
        Column("rerouted_to_channel_id", String(36), nullable=True),
        Column("version", Integer, nullable=False, server_default="1"),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("updated_at", DateTime(timezone=True), nullable=False),
    )

    return NotificationTables(
        notification_channels=notification_channels,
        notification_events=notification_events,
        notification_subscriptions=notification_subscriptions,
        notification_deliveries=notification_deliveries,
    )


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------


class PostgreSQLNotificationRepository:
    """PostgreSQL notification event/channel/subscription/delivery repository."""

    def __init__(
        self,
        session_factory: SessionFactory,
        *,
        schema: str = DEFAULT_SCHEMA_NAME,
    ) -> None:
        self._session_factory = session_factory
        self._schema = schema
        self._tables = notification_tables(schema)

    # ── Batch staging (called from issue transaction) ──────────────────

    def stage_batch(
        self,
        session: Any,
        batch: PreparedNotificationBatch,
        *,
        audit_events: Sequence[PreparedAuditEvent] = (),
    ) -> None:
        """Stage notification events, deliveries, and audit events in a session.

        This method is called from within the issue repository's transaction.
        The session must be the same session used by the issue mutation.
        """
        if batch.is_empty and not audit_events:
            return
        for staged in batch.events:
            self._insert_event(session, staged)
        for staged_delivery in batch.deliveries:
            self._insert_delivery(session, staged_delivery)
        # audit events are staged by the caller (issue repository)

    def _insert_event(self, session: Any, staged: Any) -> None:
        t = self._tables.notification_events
        try:
            session.execute(
                insert(t).values(
                    event_id=staged.event_id,
                    event_type=staged.event_type,
                    scope_type=staged.scope_type,
                    scope_id=staged.scope_id,
                    source_ref=staged.source_ref,
                    deduplication_key_digest=staged.deduplication_key_digest,
                    payload_digest=staged.payload_digest,
                    payload=staged.payload,
                    correlation_id=staged.correlation_id,
                    policy_version=staged.policy_version,
                    occurred_at=staged.occurred_at,
                    published_at=staged.published_at,
                )
            )
        except IntegrityError as exc:
            raise NotificationConflictError(
                f"Notification event {staged.event_id} already exists."
            ) from exc

    def _insert_delivery(self, session: Any, staged: Any) -> None:
        t = self._tables.notification_deliveries
        try:
            session.execute(
                insert(t).values(
                    delivery_id=staged.delivery_id,
                    event_id=staged.event_id,
                    recipient_user_id=staged.recipient_user_id,
                    channel_id=staged.channel_id,
                    status=staged.status.value,
                    attempt_count=0,
                    version=1,
                    created_at=staged.created_at,
                    updated_at=staged.created_at,
                )
            )
        except IntegrityError as exc:
            raise NotificationConflictError(
                f"Notification delivery {staged.delivery_id} already exists."
            ) from exc

    # ── Read methods ───────────────────────────────────────────────────

    def get_delivery(self, delivery_id: str) -> NotificationDelivery:
        t = self._tables.notification_deliveries
        with self._session_factory() as session:
            row = (
                session.execute(select(t).where(t.c.delivery_id == delivery_id))
                .mappings()
                .one_or_none()
            )
        if row is None:
            raise NotificationNotFoundError(f"Notification delivery {delivery_id} not found.")
        return _row_to_delivery(row)

    def get_event(self, event_id: str) -> NotificationEvent:
        t = self._tables.notification_events
        with self._session_factory() as session:
            row = (
                session.execute(select(t).where(t.c.event_id == event_id)).mappings().one_or_none()
            )
        if row is None:
            raise NotificationNotFoundError(f"Notification event {event_id} not found.")
        return _row_to_event(row)

    def get_events_by_ids(self, event_ids: list[str]) -> dict[str, NotificationEvent]:
        """Batch-lookup events by their IDs. Returns {event_id: event} map."""
        if not event_ids:
            return {}
        t = self._tables.notification_events
        with self._session_factory() as session:
            rows = session.execute(select(t).where(t.c.event_id.in_(event_ids))).mappings().all()
        return {row["event_id"]: _row_to_event(row) for row in rows}

    def list_for_recipient(
        self,
        recipient_user_id: str,
        *,
        status: NotificationDeliveryStatus | None = None,
        event_type: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
    ) -> tuple[NotificationDelivery, ...]:
        t = self._tables.notification_deliveries
        conditions: list[Any] = [t.c.recipient_user_id == recipient_user_id]
        if status is not None:
            conditions.append(t.c.status == status.value)
        if event_type is not None:
            evt = self._tables.notification_events
            conditions.append(
                t.c.event_id.in_(select(evt.c.event_id).where(evt.c.event_type == event_type))
            )
        if cursor is not None:
            conditions.append(t.c.delivery_id < cursor)
        with self._session_factory() as session:
            rows = (
                session.execute(
                    select(t)
                    .where(and_(*conditions))
                    .order_by(t.c.created_at.desc(), t.c.delivery_id.desc())
                    .limit(limit)
                )
                .mappings()
                .all()
            )
        return tuple(_row_to_delivery(r) for r in rows)

    def count_unread(self, recipient_user_id: str) -> int:
        t = self._tables.notification_deliveries
        with self._session_factory() as session:
            result = session.scalar(
                select(func.count(t.c.delivery_id)).where(
                    and_(
                        t.c.recipient_user_id == recipient_user_id,
                        t.c.status.in_(
                            [
                                NotificationDeliveryStatus.PENDING.value,
                                NotificationDeliveryStatus.SENDING.value,
                                NotificationDeliveryStatus.DELIVERED.value,
                                NotificationDeliveryStatus.FAILED.value,
                            ]
                        ),
                    )
                )
            )
        return int(result or 0)

    def count_failed(self, recipient_user_id: str) -> int:
        """Count FAILED + UNDELIVERABLE deliveries for a recipient."""
        t = self._tables.notification_deliveries
        with self._session_factory() as session:
            result = session.scalar(
                select(func.count(t.c.delivery_id)).where(
                    and_(
                        t.c.recipient_user_id == recipient_user_id,
                        t.c.status.in_(
                            [
                                NotificationDeliveryStatus.FAILED.value,
                                NotificationDeliveryStatus.UNDELIVERABLE.value,
                            ]
                        ),
                    )
                )
            )
        return int(result or 0)

    def count_today(self, recipient_user_id: str, today_start: datetime) -> int:
        """Count deliveries created since today_start for a recipient."""
        t = self._tables.notification_deliveries
        with self._session_factory() as session:
            result = session.scalar(
                select(func.count(t.c.delivery_id)).where(
                    and_(
                        t.c.recipient_user_id == recipient_user_id,
                        t.c.created_at >= today_start,
                    )
                )
            )
        return int(result or 0)

    def mark_all_read_for_recipient(
        self,
        session: Any,
        recipient_user_id: str,
        *,
        now: datetime,
    ) -> int:
        """Transition all DELIVERED items to READ for a recipient. Returns count."""
        t = self._tables.notification_deliveries
        result = session.execute(
            update(t)
            .where(
                and_(
                    t.c.recipient_user_id == recipient_user_id,
                    t.c.status == NotificationDeliveryStatus.DELIVERED.value,
                )
            )
            .values(
                status=NotificationDeliveryStatus.READ.value,
                version=t.c.version + 1,
                updated_at=now,
                read_at=now,
            )
        )
        return int(result.rowcount)

    def list_pending_retry(
        self,
        *,
        limit: int = 50,
        now: datetime | None = None,
    ) -> tuple[NotificationDelivery, ...]:
        """List deliveries eligible for retry (PENDING or FAILED with next_attempt_at <= now)."""
        t = self._tables.notification_deliveries
        ref_time = now or datetime.now(timezone.utc)
        with self._session_factory() as session:
            rows = (
                session.execute(
                    select(t)
                    .where(
                        and_(
                            t.c.status.in_(
                                [
                                    NotificationDeliveryStatus.PENDING.value,
                                    NotificationDeliveryStatus.FAILED.value,
                                ]
                            ),
                            or_(
                                t.c.next_attempt_at.is_(None),
                                t.c.next_attempt_at <= ref_time,
                            ),
                        )
                    )
                    .order_by(t.c.created_at.asc())
                    .limit(limit)
                )
                .mappings()
                .all()
            )
        return tuple(_row_to_delivery(r) for r in rows)

    # ── Channel read methods ───────────────────────────────────────────

    def get_channel(self, channel_id: str) -> NotificationChannel:
        t = self._tables.notification_channels
        with self._session_factory() as session:
            row = (
                session.execute(select(t).where(t.c.channel_id == channel_id))
                .mappings()
                .one_or_none()
            )
        if row is None:
            raise NotificationNotFoundError(f"Notification channel {channel_id} not found.")
        return _row_to_channel(row)

    def get_active_channel(self, channel_type: str) -> NotificationChannel:
        """İstenen tipteki ilk aktif kanalı döndürür."""
        t = self._tables.notification_channels
        with self._session_factory() as session:
            row = (
                session.execute(
                    select(t)
                    .where(
                        and_(
                            t.c.channel_type == channel_type,
                            t.c.status == "ACTIVE",
                        )
                    )
                    .limit(1)
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            raise NotificationNotFoundError(
                f"No active {channel_type} notification channel found."
            )
        return _row_to_channel(row)

    def list_channels(
        self,
        *,
        status: str | None = None,
        channel_type: str | None = None,
    ) -> tuple[NotificationChannel, ...]:
        t = self._tables.notification_channels
        conditions = []
        if status is not None:
            conditions.append(t.c.status == status)
        if channel_type is not None:
            conditions.append(t.c.channel_type == channel_type)
        query = select(t)
        for cond in conditions:
            query = query.where(cond)
        query = query.order_by(t.c.created_at.desc())
        with self._session_factory() as session:
            rows = session.execute(query).mappings().all()
        return tuple(_row_to_channel(r) for r in rows)

    # ── Subscription read methods ──────────────────────────────────────

    def list_subscriptions(
        self,
        *,
        user_id: str | None = None,
        event_type: str | None = None,
        status: NotificationSubscriptionStatus | None = None,
    ) -> tuple[NotificationSubscription, ...]:
        t = self._tables.notification_subscriptions
        conditions: list[Any] = []
        if user_id is not None:
            conditions.append(t.c.user_id == user_id)
        if event_type is not None:
            conditions.append(t.c.event_type == event_type)
        if status is not None:
            conditions.append(t.c.status == status.value)
        with self._session_factory() as session:
            rows = (
                session.execute(select(t).where(and_(*conditions) if conditions else text("true")))
                .mappings()
                .all()
            )
        return tuple(_row_to_subscription(r) for r in rows)

    # ── Delivery state transitions ─────────────────────────────────────

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
    ) -> NotificationDelivery:
        validate_delivery_transition(expected_status, target_status)
        t = self._tables.notification_deliveries
        values: dict[str, Any] = {
            "status": target_status.value,
            "version": t.c.version + 1,
            "updated_at": updated_at,
        }
        if attempt_count is not None:
            values["attempt_count"] = attempt_count
        if last_error_class is not None:
            values["last_error_class"] = last_error_class
        if last_attempt_at is not None:
            values["last_attempt_at"] = last_attempt_at
        if next_attempt_at is not None:
            values["next_attempt_at"] = next_attempt_at
        if delivered_at is not None:
            values["delivered_at"] = delivered_at
        if read_at is not None:
            values["read_at"] = read_at
        if rerouted_to_channel_id is not None:
            values["rerouted_to_channel_id"] = rerouted_to_channel_id
        result = session.execute(
            update(t)
            .where(
                and_(
                    t.c.delivery_id == delivery_id,
                    t.c.status == expected_status.value,
                    t.c.version == expected_version,
                )
            )
            .values(**values)
        )
        if result.rowcount == 0:
            raise NotificationDeliveryError(
                f"Delivery {delivery_id} concurrent modification or not found."
            )
        return self.get_delivery(delivery_id)


# ---------------------------------------------------------------------------
# Row mappers
# ---------------------------------------------------------------------------


def _row_to_delivery(row: RowMapping) -> NotificationDelivery:
    return NotificationDelivery(
        delivery_id=str(row["delivery_id"]),
        event_id=str(row["event_id"]),
        recipient_user_id=str(row["recipient_user_id"]),
        channel_id=str(row["channel_id"]),
        status=NotificationDeliveryStatus(str(row["status"])),
        attempt_count=int(row["attempt_count"]),
        version=int(row["version"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        last_error_class=str(row["last_error_class"]) if row["last_error_class"] else None,
        last_attempt_at=row["last_attempt_at"],
        next_attempt_at=row["next_attempt_at"],
        delivered_at=row["delivered_at"],
        read_at=row["read_at"],
        rerouted_to_channel_id=(
            str(row["rerouted_to_channel_id"]) if row["rerouted_to_channel_id"] else None
        ),
    )


def _row_to_event(row: RowMapping) -> NotificationEvent:
    return NotificationEvent(
        event_id=str(row["event_id"]),
        event_type=NotificationEventType(str(row["event_type"])),
        scope_type=NotificationScopeType(str(row["scope_type"])),
        scope_id=str(row["scope_id"]),
        source_ref=str(row["source_ref"]),
        deduplication_key=str(row["deduplication_key_digest"]),
        deduplication_key_digest=str(row["deduplication_key_digest"]),
        payload_digest=str(row["payload_digest"]),
        payload=dict(row["payload"]),
        correlation_id=str(row["correlation_id"]),
        policy_version=str(row["policy_version"]),
        occurred_at=row["occurred_at"],
        published_at=row["published_at"],
    )


def _row_to_channel(row: RowMapping) -> NotificationChannel:
    allowed = row["allowed_event_types"]
    return NotificationChannel(
        channel_id=str(row["channel_id"]),
        name=str(row["name"]),
        channel_type=str(row["channel_type"]),
        target_config=dict(row["target_config"]),
        secret_ref=str(row["secret_ref"]) if row["secret_ref"] else None,
        allowed_event_types=tuple(allowed) if isinstance(allowed, (list, tuple)) else (),
        status=NotificationChannelStatus(str(row["status"])),
        policy_version=str(row["policy_version"]),
        version=int(row["version"]),
        created_by=str(row["created_by"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_subscription(row: RowMapping) -> NotificationSubscription:
    return NotificationSubscription(
        subscription_id=str(row["subscription_id"]),
        user_id=str(row["user_id"]),
        event_type=NotificationEventType(str(row["event_type"])),
        channel_id=str(row["channel_id"]),
        status=NotificationSubscriptionStatus(str(row["status"])),
        policy_version=str(row["policy_version"]),
        version=int(row["version"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        scope_type=(NotificationScopeType(str(row["scope_type"])) if row["scope_type"] else None),
        scope_id=str(row["scope_id"]) if row["scope_id"] else None,
    )
