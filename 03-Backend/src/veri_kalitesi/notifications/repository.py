"""SQLite persistence for in-app notifications."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from threading import RLock

from veri_kalitesi.audit import PreparedAuditEvent, SQLiteTransactionalAudit
from veri_kalitesi.notifications.errors import (
    NotificationConflictError,
    NotificationNotFoundError,
    NotificationValidationError,
)
from veri_kalitesi.notifications.models import (
    Notification,
    NotificationEventType,
    NotificationScopeType,
    NotificationStatus,
)


class SQLiteNotificationRepository:
    def __init__(self, database: str = ":memory:") -> None:
        self.connection = sqlite3.connect(database, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self._lock = RLock()
        self._create_schema()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS notifications (
                notification_id TEXT PRIMARY KEY,
                recipient_user_id TEXT NOT NULL,
                source_event_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                scope_type TEXT NOT NULL,
                scope_id TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('UNREAD', 'READ')),
                deduplication_key_digest TEXT NOT NULL,
                payload_digest TEXT NOT NULL,
                occurrence_count INTEGER NOT NULL CHECK (occurrence_count >= 1),
                created_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                read_at TEXT,
                UNIQUE (recipient_user_id, deduplication_key_digest)
            );

            CREATE INDEX IF NOT EXISTS idx_notifications_recipient_status_time
            ON notifications(recipient_user_id, status, created_at DESC);
            """
        )
        self.connection.commit()

    def add_or_increment(
        self,
        notifications: tuple[Notification, ...],
        *,
        payload_digest: str,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> tuple[Notification, ...]:
        self._require_shared_audit_transaction(audit_outbox)
        notification_ids: list[str] = []
        with self._lock, self.connection:
            for notification in notifications:
                existing = self.connection.execute(
                    """
                    SELECT notification_id, payload_digest
                    FROM notifications
                    WHERE recipient_user_id = ? AND deduplication_key_digest = ?
                    """,
                    (
                        notification.recipient_user_id,
                        notification.deduplication_key_digest,
                    ),
                ).fetchone()
                if existing is not None:
                    if existing["payload_digest"] != payload_digest:
                        raise NotificationConflictError(
                            "Deduplication key was reused with a different notification payload."
                        )
                    self.connection.execute(
                        """
                        UPDATE notifications
                        SET occurrence_count = occurrence_count + 1,
                            last_seen_at = ?, source_event_id = ?
                        WHERE notification_id = ?
                        """,
                        (
                            notification.last_seen_at.isoformat(),
                            notification.source_event_id,
                            existing["notification_id"],
                        ),
                    )
                    notification_ids.append(existing["notification_id"])
                    continue
                self.connection.execute(
                    """
                    INSERT INTO notifications (
                        notification_id, recipient_user_id, source_event_id,
                        event_type, scope_type, scope_id, title, body, status,
                        deduplication_key_digest, payload_digest, occurrence_count,
                        created_at, last_seen_at, read_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        notification.notification_id,
                        notification.recipient_user_id,
                        notification.source_event_id,
                        notification.event_type.value,
                        notification.scope_type.value,
                        notification.scope_id,
                        notification.title,
                        notification.body,
                        notification.status.value,
                        notification.deduplication_key_digest,
                        payload_digest,
                        notification.occurrence_count,
                        notification.created_at.isoformat(),
                        notification.last_seen_at.isoformat(),
                        None,
                    ),
                )
                notification_ids.append(notification.notification_id)
            audit_outbox.stage(audit_event)
        return tuple(self.get(notification_id) for notification_id in notification_ids)

    def get(self, notification_id: str) -> Notification:
        with self._lock:
            row = self.connection.execute(
                "SELECT * FROM notifications WHERE notification_id = ?",
                (notification_id,),
            ).fetchone()
        if row is None:
            raise NotificationNotFoundError("Notification not found.")
        return _row_to_notification(row)

    def list_for_recipient(self, recipient_user_id: str) -> tuple[Notification, ...]:
        with self._lock:
            rows = self.connection.execute(
                """
                SELECT * FROM notifications
                WHERE recipient_user_id = ?
                ORDER BY created_at DESC, notification_id
                """,
                (recipient_user_id,),
            ).fetchall()
        return tuple(_row_to_notification(row) for row in rows)

    def mark_read(
        self,
        notification_id: str,
        recipient_user_id: str,
        read_at: datetime,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> Notification:
        self._require_shared_audit_transaction(audit_outbox)
        with self._lock, self.connection:
            row = self.connection.execute(
                "SELECT * FROM notifications WHERE notification_id = ?",
                (notification_id,),
            ).fetchone()
            if row is None:
                raise NotificationNotFoundError("Notification not found.")
            if row["recipient_user_id"] != recipient_user_id:
                raise NotificationNotFoundError("Notification not found.")
            if row["status"] == NotificationStatus.READ.value:
                return _row_to_notification(row)
            self.connection.execute(
                """
                UPDATE notifications
                SET status = 'READ', read_at = ?
                WHERE notification_id = ?
                """,
                (read_at.isoformat(), notification_id),
            )
            audit_outbox.stage(audit_event)
        return self.get(notification_id)

    def count(self) -> int:
        with self._lock:
            return self.connection.execute("SELECT COUNT(*) FROM notifications").fetchone()[0]

    def _require_shared_audit_transaction(self, audit_outbox: SQLiteTransactionalAudit) -> None:
        if audit_outbox.connection is not self.connection:
            raise NotificationValidationError(
                "Audit outbox must share the notification transaction."
            )


def _row_to_notification(row: sqlite3.Row) -> Notification:
    return Notification(
        notification_id=row["notification_id"],
        recipient_user_id=row["recipient_user_id"],
        source_event_id=row["source_event_id"],
        event_type=NotificationEventType(row["event_type"]),
        scope_type=NotificationScopeType(row["scope_type"]),
        scope_id=row["scope_id"],
        title=row["title"],
        body=row["body"],
        status=NotificationStatus(row["status"]),
        deduplication_key_digest=row["deduplication_key_digest"],
        occurrence_count=row["occurrence_count"],
        created_at=datetime.fromisoformat(row["created_at"]),
        last_seen_at=datetime.fromisoformat(row["last_seen_at"]),
        read_at=datetime.fromisoformat(row["read_at"]) if row["read_at"] else None,
    )
