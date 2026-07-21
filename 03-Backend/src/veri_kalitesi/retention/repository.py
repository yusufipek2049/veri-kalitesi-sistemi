"""Append-only SQLite persistence for legal hold lifecycle events."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from threading import RLock

from veri_kalitesi.audit import PreparedAuditEvent, SQLiteTransactionalAudit
from veri_kalitesi.retention.errors import (
    RetentionConflictError,
    RetentionNotFoundError,
    RetentionValidationError,
)
from veri_kalitesi.retention.models import (
    LegalHold,
    LegalHoldEvent,
    LegalHoldEventType,
    RetentionRecordClass,
    RetentionRecordReference,
    RetentionScopeType,
)


class SQLiteLegalHoldRepository:
    def __init__(self, database: str = ":memory:") -> None:
        self.connection = sqlite3.connect(database, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self._lock = RLock()
        self._create_schema()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS legal_hold_events (
                event_sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                hold_reference_id TEXT NOT NULL,
                event_type TEXT NOT NULL CHECK (event_type IN ('PLACED', 'RELEASED')),
                record_reference_id TEXT NOT NULL,
                record_class TEXT NOT NULL,
                policy_version TEXT NOT NULL,
                scope_type TEXT NOT NULL CHECK (scope_type IN ('SOURCE', 'DATASET', 'ENTERPRISE')),
                scope_id TEXT,
                actor_id TEXT NOT NULL,
                actor_role TEXT NOT NULL,
                reason_code TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE (hold_reference_id, event_type)
            );

            CREATE INDEX IF NOT EXISTS idx_legal_hold_active_record
            ON legal_hold_events(record_reference_id, record_class, event_type);

            CREATE TRIGGER IF NOT EXISTS legal_hold_events_no_update
            BEFORE UPDATE ON legal_hold_events
            BEGIN
                SELECT RAISE(ABORT, 'legal hold history is append-only');
            END;

            CREATE TRIGGER IF NOT EXISTS legal_hold_events_no_delete
            BEFORE DELETE ON legal_hold_events
            BEGIN
                SELECT RAISE(ABORT, 'legal hold history is append-only');
            END;
            """
        )
        self.connection.commit()

    def place(
        self,
        event: LegalHoldEvent,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> LegalHold:
        self._require_shared_audit_transaction(audit_outbox)
        if event.event_type is not LegalHoldEventType.PLACED:
            raise RetentionValidationError("Legal hold placement event type is invalid.")
        try:
            with self._lock, self.connection:
                self._insert_event(event)
                audit_outbox.stage(audit_event)
        except sqlite3.IntegrityError as exc:
            raise RetentionConflictError("Legal hold event conflicts with stored history.") from exc
        return self.get(event.hold_reference_id)

    def release(
        self,
        event: LegalHoldEvent,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> LegalHold:
        self._require_shared_audit_transaction(audit_outbox)
        if event.event_type is not LegalHoldEventType.RELEASED:
            raise RetentionValidationError("Legal hold release event type is invalid.")
        try:
            with self._lock, self.connection:
                hold = self.get(event.hold_reference_id)
                if hold.released_at is not None:
                    raise RetentionConflictError("Legal hold is already released.")
                if (
                    event.record_reference_id != hold.record_reference_id
                    or event.record_class is not hold.record_class
                    or event.policy_version != hold.policy_version
                    or event.scope_type is not hold.scope_type
                    or event.scope_id != hold.scope_id
                ):
                    raise RetentionValidationError("Legal hold release identity is invalid.")
                self._insert_event(event)
                audit_outbox.stage(audit_event)
        except sqlite3.IntegrityError as exc:
            raise RetentionConflictError("Legal hold event conflicts with stored history.") from exc
        return self.get(event.hold_reference_id)

    def get(self, hold_reference_id: str) -> LegalHold:
        with self._lock:
            rows = self.connection.execute(
                """
                SELECT * FROM legal_hold_events
                WHERE hold_reference_id = ?
                ORDER BY event_sequence
                """,
                (hold_reference_id,),
            ).fetchall()
        if not rows:
            raise RetentionNotFoundError("Legal hold not found.")
        return _rows_to_hold(rows)

    def list_history(self, hold_reference_id: str) -> tuple[LegalHoldEvent, ...]:
        with self._lock:
            rows = self.connection.execute(
                """
                SELECT * FROM legal_hold_events
                WHERE hold_reference_id = ?
                ORDER BY event_sequence
                """,
                (hold_reference_id,),
            ).fetchall()
        if not rows:
            raise RetentionNotFoundError("Legal hold not found.")
        return tuple(_row_to_event(row) for row in rows)

    def list_active_holds(
        self,
        record_reference: RetentionRecordReference,
        *,
        as_of: datetime,
    ) -> tuple[LegalHold, ...]:
        with self._lock:
            rows = self.connection.execute(
                """
                SELECT placed.*
                FROM legal_hold_events AS placed
                WHERE placed.event_type = 'PLACED'
                  AND placed.record_reference_id = ?
                  AND placed.record_class = ?
                  AND placed.created_at <= ?
                  AND NOT EXISTS (
                      SELECT 1 FROM legal_hold_events AS released
                      WHERE released.hold_reference_id = placed.hold_reference_id
                        AND released.event_type = 'RELEASED'
                        AND released.created_at <= ?
                  )
                ORDER BY placed.event_sequence
                """,
                (
                    record_reference.record_reference_id,
                    record_reference.record_class.value,
                    _serialize_time(as_of),
                    _serialize_time(as_of),
                ),
            ).fetchall()
        return tuple(_rows_to_hold([row]) for row in rows)

    def count_events(self) -> int:
        with self._lock:
            return self.connection.execute("SELECT COUNT(*) FROM legal_hold_events").fetchone()[0]

    def _insert_event(self, event: LegalHoldEvent) -> None:
        self.connection.execute(
            """
            INSERT INTO legal_hold_events (
                event_id, hold_reference_id, event_type, record_reference_id,
                record_class, policy_version, scope_type, scope_id, actor_id,
                actor_role, reason_code, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.hold_reference_id,
                event.event_type.value,
                event.record_reference_id,
                event.record_class.value,
                event.policy_version,
                event.scope_type.value,
                event.scope_id,
                event.actor_id,
                event.actor_role,
                event.reason_code,
                _serialize_time(event.created_at),
            ),
        )

    def _require_shared_audit_transaction(self, audit_outbox: SQLiteTransactionalAudit) -> None:
        if audit_outbox.connection is not self.connection:
            raise RetentionValidationError("Audit outbox must share the legal hold transaction.")


def _rows_to_hold(rows: list[sqlite3.Row]) -> LegalHold:
    placed = rows[0]
    released = rows[1] if len(rows) > 1 else None
    return LegalHold(
        hold_reference_id=placed["hold_reference_id"],
        record_reference_id=placed["record_reference_id"],
        record_class=RetentionRecordClass(placed["record_class"]),
        policy_version=placed["policy_version"],
        decision_owner_role=placed["actor_role"],
        effective_at=_parse_time(placed["created_at"]),
        released_at=_parse_time(released["created_at"]) if released is not None else None,
        placed_by_actor_id=placed["actor_id"],
        released_by_actor_id=released["actor_id"] if released is not None else None,
        release_owner_role=released["actor_role"] if released is not None else None,
        scope_type=RetentionScopeType(placed["scope_type"]),
        scope_id=placed["scope_id"],
    )


def _row_to_event(row: sqlite3.Row) -> LegalHoldEvent:
    return LegalHoldEvent(
        event_id=row["event_id"],
        hold_reference_id=row["hold_reference_id"],
        event_type=LegalHoldEventType(row["event_type"]),
        record_reference_id=row["record_reference_id"],
        record_class=RetentionRecordClass(row["record_class"]),
        policy_version=row["policy_version"],
        scope_type=RetentionScopeType(row["scope_type"]),
        scope_id=row["scope_id"],
        actor_id=row["actor_id"],
        actor_role=row["actor_role"],
        reason_code=row["reason_code"],
        created_at=_parse_time(row["created_at"]),
    )


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _serialize_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()
