"""SQLite transaction sinirinda redakte audit outbox'i."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from collections.abc import Mapping, Sequence
from typing import Any, Protocol, cast

from veri_kalitesi.audit.models import AuditEvent, AuditEventInput, AuditResult, PreparedAuditEvent
from veri_kalitesi.audit.redaction import AuditRedactor


class PreparedAuditRepository(Protocol):
    def append(self, prepared: PreparedAuditEvent) -> AuditEvent: ...


@dataclass(frozen=True)
class AuditOutboxStatus:
    pending_count: int
    published_count: int
    failed_count: int


class SQLiteTransactionalAudit:
    def __init__(
        self,
        connection: sqlite3.Connection,
        redactor: AuditRedactor,
        repository: PreparedAuditRepository,
        *,
        policy_version: str,
    ) -> None:
        if not policy_version.strip():
            raise ValueError("Audit outbox policy version is required.")
        self.connection = connection
        self.redactor = redactor
        self.repository = repository
        self.policy_version = policy_version
        self._create_schema()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS audit_outbox (
                event_id TEXT PRIMARY KEY,
                prepared_event TEXT NOT NULL,
                policy_version TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('PENDING', 'PUBLISHED')),
                attempt_count INTEGER NOT NULL DEFAULT 0,
                last_error_code TEXT,
                created_at TEXT NOT NULL,
                published_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_audit_outbox_pending
            ON audit_outbox(status, created_at, event_id);
            """
        )
        self.connection.commit()

    def prepare(self, event: AuditEventInput) -> PreparedAuditEvent:
        return self.redactor.prepare(event)

    def stage(self, prepared: PreparedAuditEvent) -> None:
        self.connection.execute(
            """
            INSERT INTO audit_outbox (
                event_id, prepared_event, policy_version, status, created_at
            ) VALUES (?, ?, ?, 'PENDING', ?)
            """,
            (
                prepared.event_id,
                prepared_audit_to_json(prepared),
                self.policy_version,
                datetime.now(timezone.utc).isoformat(),
            ),
        )

    def publish_pending(self, *, limit: int = 100) -> AuditOutboxStatus:
        rows = self.connection.execute(
            """
            SELECT event_id, prepared_event
            FROM audit_outbox
            WHERE status = 'PENDING'
            ORDER BY created_at, event_id
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        published = 0
        failed = 0
        for row in rows:
            try:
                self.repository.append(prepared_audit_from_json(row["prepared_event"]))
            except Exception:
                failed += 1
                with self.connection:
                    self.connection.execute(
                        """
                        UPDATE audit_outbox
                        SET attempt_count = attempt_count + 1,
                            last_error_code = 'AUDIT_REPOSITORY_UNAVAILABLE'
                        WHERE event_id = ? AND status = 'PENDING'
                        """,
                        (row["event_id"],),
                    )
                continue
            with self.connection:
                self.connection.execute(
                    """
                    UPDATE audit_outbox
                    SET status = 'PUBLISHED', attempt_count = attempt_count + 1,
                        last_error_code = NULL, published_at = ?
                    WHERE event_id = ? AND status = 'PENDING'
                    """,
                    (datetime.now(timezone.utc).isoformat(), row["event_id"]),
                )
            published += 1
        pending = self.connection.execute(
            "SELECT COUNT(*) FROM audit_outbox WHERE status = 'PENDING'"
        ).fetchone()[0]
        return AuditOutboxStatus(pending, published, failed)

    def list_pending(self) -> list[PreparedAuditEvent]:
        rows = self.connection.execute(
            """
            SELECT prepared_event FROM audit_outbox
            WHERE status = 'PENDING'
            ORDER BY created_at, event_id
            """
        ).fetchall()
        return [prepared_audit_from_json(row["prepared_event"]) for row in rows]


def prepared_audit_to_document(prepared: PreparedAuditEvent) -> dict[str, object]:
    return {
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
    }


def prepared_audit_to_json(prepared: PreparedAuditEvent) -> str:
    return json.dumps(
        prepared_audit_to_document(prepared),
        sort_keys=True,
        separators=(",", ":"),
    )


def prepared_audit_from_json(payload: str) -> PreparedAuditEvent:
    return prepared_audit_from_document(json.loads(payload))


def prepared_audit_from_document(value: dict[str, object]) -> PreparedAuditEvent:
    return PreparedAuditEvent(
        event_id=str(value["event_id"]),
        event_version=str(value["event_version"]),
        occurred_at=datetime.fromisoformat(str(value["occurred_at"])),
        actor_id=str(value["actor_id"]),
        actor_type=_optional_str(value["actor_type"]),
        session_id_digest=(
            str(value["session_id_digest"]) if value["session_id_digest"] is not None else None
        ),
        correlation_id=str(value["correlation_id"]),
        action=str(value["action"]),
        object_type=str(value["object_type"]),
        object_id=str(value["object_id"]) if value["object_id"] is not None else None,
        result=AuditResult(str(value["result"])),
        reason_code=str(value["reason_code"]),
        old_value_summary=dict(cast(Mapping[str, Any], value["old_value_summary"])),
        new_value_summary=dict(cast(Mapping[str, Any], value["new_value_summary"])),
        old_value_digest=str(value["old_value_digest"]),
        new_value_digest=str(value["new_value_digest"]),
        redacted_fields=tuple(
            str(item) for item in cast(Sequence[object], value["redacted_fields"])
        ),
        redaction_policy_version=str(value["redaction_policy_version"]),
    )


def _optional_str(value: object) -> str | None:
    return str(value) if value is not None else None
