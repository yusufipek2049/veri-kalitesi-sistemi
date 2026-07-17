"""SQLite persistence for idempotent ServiceNow ticket links."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from threading import RLock

from veri_kalitesi.audit import PreparedAuditEvent, SQLiteTransactionalAudit
from veri_kalitesi.servicenow.errors import (
    ServiceNowConflictError,
    ServiceNowValidationError,
)
from veri_kalitesi.servicenow.models import (
    ServiceNowTicketHistoryEntry,
    ServiceNowTicketLink,
    ServiceNowTicketStatus,
)


class SQLiteServiceNowRepository:
    def __init__(self, database: str = ":memory:") -> None:
        self.connection = sqlite3.connect(database, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self._lock = RLock()
        self._create_schema()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS servicenow_ticket_links (
                link_id TEXT PRIMARY KEY,
                issue_id TEXT NOT NULL UNIQUE,
                external_ticket_id TEXT NOT NULL UNIQUE,
                ticket_number TEXT NOT NULL UNIQUE,
                idempotency_key_digest TEXT NOT NULL UNIQUE,
                payload_digest TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('CREATED')),
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS servicenow_ticket_history (
                sequence_no INTEGER PRIMARY KEY AUTOINCREMENT,
                history_id TEXT NOT NULL UNIQUE,
                link_id TEXT NOT NULL,
                issue_id TEXT NOT NULL,
                action TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                old_status TEXT CHECK (old_status IS NULL OR old_status IN ('CREATED')),
                new_status TEXT NOT NULL CHECK (new_status IN ('CREATED')),
                occurred_at TEXT NOT NULL,
                FOREIGN KEY (link_id) REFERENCES servicenow_ticket_links(link_id)
            );

            CREATE INDEX IF NOT EXISTS idx_servicenow_history_link_time
            ON servicenow_ticket_history(link_id, sequence_no);
            """
        )
        self.connection.commit()

    def resolve_existing(
        self,
        issue_id: str,
        idempotency_key_digest: str,
        payload_digest: str,
    ) -> ServiceNowTicketLink | None:
        with self._lock:
            rows = self.connection.execute(
                """
                SELECT * FROM servicenow_ticket_links
                WHERE issue_id = ? OR idempotency_key_digest = ?
                """,
                (issue_id, idempotency_key_digest),
            ).fetchall()
        if not rows:
            return None
        if len({row["link_id"] for row in rows}) != 1 or any(
            row["payload_digest"] != payload_digest for row in rows
        ):
            raise ServiceNowConflictError(
                "Issue or idempotency key was reused with a different ticket payload."
            )
        return _row_to_link(rows[0])

    def add(
        self,
        link: ServiceNowTicketLink,
        history: ServiceNowTicketHistoryEntry,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> ServiceNowTicketLink:
        self._require_shared_audit_transaction(audit_outbox)
        with self._lock, self.connection:
            existing_rows = self.connection.execute(
                """
                SELECT * FROM servicenow_ticket_links
                WHERE issue_id = ? OR idempotency_key_digest = ?
                """,
                (link.issue_id, link.idempotency_key_digest),
            ).fetchall()
            if existing_rows:
                if len({row["link_id"] for row in existing_rows}) != 1 or any(
                    row["payload_digest"] != link.payload_digest for row in existing_rows
                ):
                    raise ServiceNowConflictError(
                        "Issue or idempotency key was reused with a different ticket payload."
                    )
                return _row_to_link(existing_rows[0])
            self.connection.execute(
                """
                INSERT INTO servicenow_ticket_links (
                    link_id, issue_id, external_ticket_id, ticket_number,
                    idempotency_key_digest, payload_digest, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    link.link_id,
                    link.issue_id,
                    link.external_ticket_id,
                    link.ticket_number,
                    link.idempotency_key_digest,
                    link.payload_digest,
                    link.status.value,
                    link.created_at.isoformat(),
                ),
            )
            self.connection.execute(
                """
                INSERT INTO servicenow_ticket_history (
                    history_id, link_id, issue_id, action, actor_id,
                    old_status, new_status, occurred_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    history.history_id,
                    history.link_id,
                    history.issue_id,
                    history.action,
                    history.actor_id,
                    history.old_status.value if history.old_status else None,
                    history.new_status.value,
                    history.occurred_at.isoformat(),
                ),
            )
            audit_outbox.stage(audit_event)
        return self.get(link.link_id)

    def get(self, link_id: str) -> ServiceNowTicketLink:
        with self._lock:
            row = self.connection.execute(
                "SELECT * FROM servicenow_ticket_links WHERE link_id = ?",
                (link_id,),
            ).fetchone()
        if row is None:
            raise ServiceNowValidationError("ServiceNow ticket link was not found.")
        return _row_to_link(row)

    def list_history(self, link_id: str) -> tuple[ServiceNowTicketHistoryEntry, ...]:
        with self._lock:
            rows = self.connection.execute(
                """
                SELECT * FROM servicenow_ticket_history
                WHERE link_id = ?
                ORDER BY sequence_no
                """,
                (link_id,),
            ).fetchall()
        return tuple(_row_to_history(row) for row in rows)

    def count(self) -> int:
        with self._lock:
            return self.connection.execute(
                "SELECT COUNT(*) FROM servicenow_ticket_links"
            ).fetchone()[0]

    def _require_shared_audit_transaction(self, audit_outbox: SQLiteTransactionalAudit) -> None:
        if audit_outbox.connection is not self.connection:
            raise ServiceNowValidationError("Audit outbox must share the ServiceNow transaction.")


def _row_to_link(row: sqlite3.Row) -> ServiceNowTicketLink:
    return ServiceNowTicketLink(
        link_id=row["link_id"],
        issue_id=row["issue_id"],
        external_ticket_id=row["external_ticket_id"],
        ticket_number=row["ticket_number"],
        idempotency_key_digest=row["idempotency_key_digest"],
        payload_digest=row["payload_digest"],
        status=ServiceNowTicketStatus(row["status"]),
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def _row_to_history(row: sqlite3.Row) -> ServiceNowTicketHistoryEntry:
    return ServiceNowTicketHistoryEntry(
        history_id=row["history_id"],
        link_id=row["link_id"],
        issue_id=row["issue_id"],
        action=row["action"],
        actor_id=row["actor_id"],
        old_status=(ServiceNowTicketStatus(row["old_status"]) if row["old_status"] else None),
        new_status=ServiceNowTicketStatus(row["new_status"]),
        occurred_at=datetime.fromisoformat(row["occurred_at"]),
    )
