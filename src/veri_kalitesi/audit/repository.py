"""SQLite append-only audit zinciri ve butunluk dogrulamasi."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime
from threading import RLock
from typing import Any, Mapping

from veri_kalitesi.audit.errors import AuditValidationError
from veri_kalitesi.audit.models import (
    AuditEvent,
    AuditIntegrityResult,
    AuditQuery,
    AuditResult,
    PreparedAuditEvent,
)

GENESIS_HASH = "0" * 64


class SQLiteAuditRepository:
    def __init__(self, database: str = ":memory:") -> None:
        self.connection = sqlite3.connect(database, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self._lock = RLock()
        self._create_schema()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS audit_events (
                sequence_no INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                event_version TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                actor_type TEXT,
                session_id_digest TEXT,
                correlation_id TEXT NOT NULL,
                action TEXT NOT NULL,
                object_type TEXT NOT NULL,
                object_id TEXT,
                result TEXT NOT NULL,
                reason_code TEXT NOT NULL,
                old_value_summary TEXT NOT NULL,
                new_value_summary TEXT NOT NULL,
                old_value_digest TEXT NOT NULL,
                new_value_digest TEXT NOT NULL,
                redacted_fields TEXT NOT NULL,
                redaction_policy_version TEXT NOT NULL,
                previous_event_hash TEXT NOT NULL,
                event_hash TEXT NOT NULL UNIQUE
            );

            CREATE INDEX IF NOT EXISTS idx_audit_events_time
            ON audit_events(occurred_at, sequence_no);

            CREATE INDEX IF NOT EXISTS idx_audit_events_correlation
            ON audit_events(correlation_id, sequence_no);
            """
        )
        self.connection.commit()

    def append(self, prepared: PreparedAuditEvent) -> AuditEvent:
        with self._lock, self.connection:
            existing = self.connection.execute(
                "SELECT * FROM audit_events WHERE event_id = ?", (prepared.event_id,)
            ).fetchone()
            if existing is not None:
                existing_event = _row_to_event(existing)
                if _event_to_prepared(existing_event) != prepared:
                    raise AuditValidationError(
                        "Audit event_id cannot be reused with different content."
                    )
                return existing_event
            previous = self.connection.execute(
                "SELECT event_hash FROM audit_events ORDER BY sequence_no DESC LIMIT 1"
            ).fetchone()
            previous_hash = previous["event_hash"] if previous else GENESIS_HASH
            event_hash = compute_event_hash(prepared, previous_hash)
            cursor = self.connection.execute(
                """
                INSERT INTO audit_events (
                    event_id, event_version, occurred_at, actor_id, actor_type,
                    session_id_digest, correlation_id, action, object_type, object_id,
                    result, reason_code, old_value_summary, new_value_summary,
                    old_value_digest, new_value_digest, redacted_fields,
                    redaction_policy_version, previous_event_hash, event_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                _insert_values(prepared, previous_hash, event_hash),
            )
            if cursor.lastrowid is None:
                raise AuditValidationError("Audit event sequence could not be assigned.")
            sequence_no = cursor.lastrowid
        return _to_event(prepared, sequence_no, previous_hash, event_hash)

    def list_events(self) -> list[AuditEvent]:
        with self._lock:
            rows = self.connection.execute(
                "SELECT * FROM audit_events ORDER BY sequence_no"
            ).fetchall()
        return [_row_to_event(row) for row in rows]

    def find_event(self, event_id: str) -> AuditEvent | None:
        with self._lock:
            row = self.connection.execute(
                "SELECT * FROM audit_events WHERE event_id = ?", (event_id,)
            ).fetchone()
        return _row_to_event(row) if row is not None else None

    def query_events(self, query: AuditQuery) -> tuple[tuple[AuditEvent, ...], bool]:
        clauses = [
            "sequence_no > ?",
            "julianday(occurred_at) >= julianday(?)",
            "julianday(occurred_at) <= julianday(?)",
        ]
        parameters: list[object] = [
            query.after_sequence_no,
            query.start_at.isoformat(),
            query.end_at.isoformat(),
        ]
        if query.through_sequence_no is not None:
            clauses.append("sequence_no <= ?")
            parameters.append(query.through_sequence_no)
        optional_filters = (
            ("actor_id", query.actor_id),
            ("action", query.action),
            ("object_type", query.object_type),
            ("object_id", query.object_id),
            ("correlation_id", query.correlation_id),
            ("result", query.result.value if query.result is not None else None),
        )
        for column, value in optional_filters:
            if value is not None:
                clauses.append(f"{column} = ?")
                parameters.append(value)
        parameters.append(query.page_size + 1)
        statement = f"""
            SELECT * FROM audit_events
            WHERE {" AND ".join(clauses)}
            ORDER BY sequence_no
            LIMIT ?
        """
        with self._lock:
            rows = self.connection.execute(statement, parameters).fetchall()
        has_more = len(rows) > query.page_size
        return tuple(_row_to_event(row) for row in rows[: query.page_size]), has_more

    def latest_sequence_no(self) -> int:
        with self._lock:
            row = self.connection.execute(
                "SELECT COALESCE(MAX(sequence_no), 0) FROM audit_events"
            ).fetchone()
        return int(row[0])

    def verify_integrity(self) -> AuditIntegrityResult:
        with self._lock:
            rows = self.connection.execute(
                "SELECT * FROM audit_events ORDER BY sequence_no"
            ).fetchall()
        previous_hash = GENESIS_HASH
        for index, row in enumerate(rows, start=1):
            try:
                event = _row_to_event(row)
                prepared = _event_to_prepared(event)
                expected_hash = compute_event_hash(prepared, previous_hash)
            except (ValueError, TypeError, json.JSONDecodeError):
                return AuditIntegrityResult(False, index, row["event_id"])
            if event.previous_event_hash != previous_hash or event.event_hash != expected_hash:
                return AuditIntegrityResult(False, index, event.event_id)
            previous_hash = event.event_hash
        return AuditIntegrityResult(True, len(rows))


def compute_event_hash(prepared: PreparedAuditEvent, previous_hash: str) -> str:
    payload = {
        "event_id": prepared.event_id,
        "event_version": prepared.event_version,
        "occurred_at": prepared.occurred_at.isoformat(),
        "actor_id": prepared.actor_id,
        "actor_type": prepared.actor_type,
        "session_id_digest": prepared.session_id_digest,
        "correlation_id": prepared.correlation_id,
        "action": prepared.action,
        "object_type": prepared.object_type,
        "object_id": prepared.object_id,
        "result": prepared.result.value,
        "reason_code": prepared.reason_code,
        "old_value_summary": dict(prepared.old_value_summary),
        "new_value_summary": dict(prepared.new_value_summary),
        "old_value_digest": prepared.old_value_digest,
        "new_value_digest": prepared.new_value_digest,
        "redacted_fields": list(prepared.redacted_fields),
        "redaction_policy_version": prepared.redaction_policy_version,
        "previous_event_hash": previous_hash,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _insert_values(
    prepared: PreparedAuditEvent,
    previous_hash: str,
    event_hash: str,
) -> tuple[Any, ...]:
    return (
        prepared.event_id,
        prepared.event_version,
        prepared.occurred_at.isoformat(),
        prepared.actor_id,
        prepared.actor_type,
        prepared.session_id_digest,
        prepared.correlation_id,
        prepared.action,
        prepared.object_type,
        prepared.object_id,
        prepared.result.value,
        prepared.reason_code,
        _json(prepared.old_value_summary),
        _json(prepared.new_value_summary),
        prepared.old_value_digest,
        prepared.new_value_digest,
        json.dumps(prepared.redacted_fields),
        prepared.redaction_policy_version,
        previous_hash,
        event_hash,
    )


def _to_event(
    prepared: PreparedAuditEvent,
    sequence_no: int,
    previous_hash: str,
    event_hash: str,
) -> AuditEvent:
    return AuditEvent(
        sequence_no=sequence_no,
        event_id=prepared.event_id,
        event_version=prepared.event_version,
        occurred_at=prepared.occurred_at,
        actor_id=prepared.actor_id,
        actor_type=prepared.actor_type,
        session_id_digest=prepared.session_id_digest,
        correlation_id=prepared.correlation_id,
        action=prepared.action,
        object_type=prepared.object_type,
        object_id=prepared.object_id,
        result=prepared.result,
        reason_code=prepared.reason_code,
        old_value_summary=prepared.old_value_summary,
        new_value_summary=prepared.new_value_summary,
        old_value_digest=prepared.old_value_digest,
        new_value_digest=prepared.new_value_digest,
        redacted_fields=prepared.redacted_fields,
        redaction_policy_version=prepared.redaction_policy_version,
        previous_event_hash=previous_hash,
        event_hash=event_hash,
    )


def _row_to_event(row: sqlite3.Row) -> AuditEvent:
    return AuditEvent(
        sequence_no=row["sequence_no"],
        event_id=row["event_id"],
        event_version=row["event_version"],
        occurred_at=datetime.fromisoformat(row["occurred_at"]),
        actor_id=row["actor_id"],
        actor_type=row["actor_type"],
        session_id_digest=row["session_id_digest"],
        correlation_id=row["correlation_id"],
        action=row["action"],
        object_type=row["object_type"],
        object_id=row["object_id"],
        result=AuditResult(row["result"]),
        reason_code=row["reason_code"],
        old_value_summary=json.loads(row["old_value_summary"]),
        new_value_summary=json.loads(row["new_value_summary"]),
        old_value_digest=row["old_value_digest"],
        new_value_digest=row["new_value_digest"],
        redacted_fields=tuple(json.loads(row["redacted_fields"])),
        redaction_policy_version=row["redaction_policy_version"],
        previous_event_hash=row["previous_event_hash"],
        event_hash=row["event_hash"],
    )


def _event_to_prepared(event: AuditEvent) -> PreparedAuditEvent:
    return PreparedAuditEvent(
        event_id=event.event_id,
        event_version=event.event_version,
        occurred_at=event.occurred_at,
        actor_id=event.actor_id,
        actor_type=event.actor_type,
        session_id_digest=event.session_id_digest,
        correlation_id=event.correlation_id,
        action=event.action,
        object_type=event.object_type,
        object_id=event.object_id,
        result=event.result,
        reason_code=event.reason_code,
        old_value_summary=event.old_value_summary,
        new_value_summary=event.new_value_summary,
        old_value_digest=event.old_value_digest,
        new_value_digest=event.new_value_digest,
        redacted_fields=event.redacted_fields,
        redaction_policy_version=event.redaction_policy_version,
    )


def _json(value: Mapping[str, Any]) -> str:
    return json.dumps(dict(value), sort_keys=True, separators=(",", ":"))
