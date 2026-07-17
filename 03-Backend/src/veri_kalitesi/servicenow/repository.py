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
    ServiceNowRetryJob,
    ServiceNowRetryJobStatus,
    ServiceNowTicketHistoryEntry,
    ServiceNowTicketLink,
    ServiceNowTicketRequest,
    ServiceNowTicketStatus,
    validate_retry_job,
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

            CREATE TABLE IF NOT EXISTS servicenow_retry_jobs (
                job_id TEXT PRIMARY KEY,
                issue_id TEXT NOT NULL UNIQUE,
                client_request_id TEXT NOT NULL UNIQUE,
                payload_digest TEXT NOT NULL,
                issue_reference TEXT NOT NULL,
                source_event_type TEXT NOT NULL,
                priority TEXT NOT NULL,
                detail_reference_id TEXT NOT NULL,
                correlation_id TEXT NOT NULL,
                status TEXT NOT NULL CHECK (
                    status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'DEAD_LETTER')
                ),
                attempt_count INTEGER NOT NULL CHECK (attempt_count >= 0),
                next_attempt_at TEXT NOT NULL,
                last_error_kind TEXT NOT NULL,
                link_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (link_id) REFERENCES servicenow_ticket_links(link_id)
            );

            CREATE INDEX IF NOT EXISTS idx_servicenow_retry_claim
            ON servicenow_retry_jobs(status, next_attempt_at, created_at);
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

    def resolve_retry_job(
        self,
        issue_id: str,
        client_request_id: str,
        payload_digest: str,
    ) -> ServiceNowRetryJob | None:
        with self._lock:
            rows = self.connection.execute(
                """
                SELECT * FROM servicenow_retry_jobs
                WHERE issue_id = ? OR client_request_id = ?
                """,
                (issue_id, client_request_id),
            ).fetchall()
        if not rows:
            return None
        if len({row["job_id"] for row in rows}) != 1 or any(
            row["payload_digest"] != payload_digest for row in rows
        ):
            raise ServiceNowConflictError(
                "Issue or idempotency key was reused with a different retry payload."
            )
        return _row_to_retry_job(rows[0])

    def enqueue_retry(
        self,
        job: ServiceNowRetryJob,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> ServiceNowRetryJob:
        validate_retry_job(job)
        self._require_shared_audit_transaction(audit_outbox)
        with self._lock, self.connection:
            existing_rows = self.connection.execute(
                """
                SELECT * FROM servicenow_retry_jobs
                WHERE issue_id = ? OR client_request_id = ?
                """,
                (job.issue_id, job.request.client_request_id),
            ).fetchall()
            if existing_rows:
                if len({row["job_id"] for row in existing_rows}) != 1 or any(
                    row["payload_digest"] != job.payload_digest for row in existing_rows
                ):
                    raise ServiceNowConflictError(
                        "Issue or idempotency key was reused with a different retry payload."
                    )
                return _row_to_retry_job(existing_rows[0])
            self.connection.execute(
                """
                INSERT INTO servicenow_retry_jobs (
                    job_id, issue_id, client_request_id, payload_digest,
                    issue_reference, source_event_type, priority, detail_reference_id,
                    correlation_id, status, attempt_count, next_attempt_at,
                    last_error_kind, link_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.job_id,
                    job.issue_id,
                    job.request.client_request_id,
                    job.payload_digest,
                    job.request.issue_reference,
                    job.request.source_event_type,
                    job.request.priority,
                    job.request.detail_reference_id,
                    job.request.correlation_id,
                    job.status.value,
                    job.attempt_count,
                    job.next_attempt_at.isoformat(),
                    job.last_error_kind,
                    job.link_id,
                    job.created_at.isoformat(),
                    job.updated_at.isoformat(),
                ),
            )
            audit_outbox.stage(audit_event)
        return self.get_retry_job(job.job_id)

    def claim_next_retry(self, now: datetime) -> ServiceNowRetryJob | None:
        with self._lock, self.connection:
            row = self.connection.execute(
                """
                SELECT * FROM servicenow_retry_jobs
                WHERE status = 'PENDING' AND next_attempt_at <= ?
                ORDER BY next_attempt_at, created_at, job_id
                LIMIT 1
                """,
                (now.isoformat(),),
            ).fetchone()
            if row is None:
                return None
            updated = self.connection.execute(
                """
                UPDATE servicenow_retry_jobs
                SET status = 'PROCESSING', attempt_count = attempt_count + 1,
                    updated_at = ?
                WHERE job_id = ? AND status = 'PENDING'
                """,
                (now.isoformat(), row["job_id"]),
            )
            if updated.rowcount != 1:
                return None
        return self.get_retry_job(row["job_id"])

    def record_retry_failure(
        self,
        job_id: str,
        *,
        status: ServiceNowRetryJobStatus,
        next_attempt_at: datetime,
        error_kind: str,
        updated_at: datetime,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> ServiceNowRetryJob:
        if status not in {
            ServiceNowRetryJobStatus.PENDING,
            ServiceNowRetryJobStatus.DEAD_LETTER,
        }:
            raise ServiceNowValidationError("Retry failure target status is invalid.")
        self._require_shared_audit_transaction(audit_outbox)
        with self._lock, self.connection:
            updated = self.connection.execute(
                """
                UPDATE servicenow_retry_jobs
                SET status = ?, next_attempt_at = ?, last_error_kind = ?, updated_at = ?
                WHERE job_id = ? AND status = 'PROCESSING'
                """,
                (
                    status.value,
                    next_attempt_at.isoformat(),
                    error_kind,
                    updated_at.isoformat(),
                    job_id,
                ),
            )
            if updated.rowcount != 1:
                raise ServiceNowValidationError("Retry job is not processing.")
            audit_outbox.stage(audit_event)
        return self.get_retry_job(job_id)

    def release_retry_claim(self, job_id: str, released_at: datetime) -> None:
        with self._lock, self.connection:
            self.connection.execute(
                """
                UPDATE servicenow_retry_jobs
                SET status = 'PENDING', attempt_count = attempt_count - 1,
                    next_attempt_at = ?, updated_at = ?
                WHERE job_id = ? AND status = 'PROCESSING' AND attempt_count > 0
                """,
                (released_at.isoformat(), released_at.isoformat(), job_id),
            )

    def complete_retry(
        self,
        job: ServiceNowRetryJob,
        link: ServiceNowTicketLink,
        history: ServiceNowTicketHistoryEntry,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> tuple[ServiceNowRetryJob, ServiceNowTicketLink]:
        self._require_shared_audit_transaction(audit_outbox)
        with self._lock, self.connection:
            current = self.connection.execute(
                "SELECT status FROM servicenow_retry_jobs WHERE job_id = ?",
                (job.job_id,),
            ).fetchone()
            if current is None or current["status"] != ServiceNowRetryJobStatus.PROCESSING.value:
                raise ServiceNowValidationError("Retry job is not processing.")
            existing = self.connection.execute(
                """
                SELECT * FROM servicenow_ticket_links
                WHERE issue_id = ? OR idempotency_key_digest = ?
                """,
                (link.issue_id, link.idempotency_key_digest),
            ).fetchone()
            if existing is None:
                self._insert_link_and_history(link, history)
                stored_link = link
            else:
                if existing["payload_digest"] != link.payload_digest:
                    raise ServiceNowConflictError(
                        "Issue or idempotency key was reused with a different ticket payload."
                    )
                stored_link = _row_to_link(existing)
            self.connection.execute(
                """
                UPDATE servicenow_retry_jobs
                SET status = 'COMPLETED', link_id = ?, last_error_kind = 'NONE',
                    updated_at = ?
                WHERE job_id = ?
                """,
                (stored_link.link_id, link.created_at.isoformat(), job.job_id),
            )
            audit_outbox.stage(audit_event)
        return self.get_retry_job(job.job_id), stored_link

    def requeue_dead_letter(
        self,
        job_id: str,
        *,
        requeued_at: datetime,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> ServiceNowRetryJob:
        self._require_shared_audit_transaction(audit_outbox)
        with self._lock, self.connection:
            updated = self.connection.execute(
                """
                UPDATE servicenow_retry_jobs
                SET status = 'PENDING', attempt_count = 0, next_attempt_at = ?,
                    last_error_kind = 'REQUEUED', updated_at = ?
                WHERE job_id = ? AND status = 'DEAD_LETTER'
                """,
                (requeued_at.isoformat(), requeued_at.isoformat(), job_id),
            )
            if updated.rowcount != 1:
                raise ServiceNowValidationError("Only dead-letter jobs can be requeued.")
            audit_outbox.stage(audit_event)
        return self.get_retry_job(job_id)

    def get_retry_job(self, job_id: str) -> ServiceNowRetryJob:
        with self._lock:
            row = self.connection.execute(
                "SELECT * FROM servicenow_retry_jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
        if row is None:
            raise ServiceNowValidationError("ServiceNow retry job was not found.")
        return _row_to_retry_job(row)

    def count_retry_jobs(self, status: ServiceNowRetryJobStatus | None = None) -> int:
        with self._lock:
            if status is None:
                row = self.connection.execute(
                    "SELECT COUNT(*) FROM servicenow_retry_jobs"
                ).fetchone()
            else:
                row = self.connection.execute(
                    "SELECT COUNT(*) FROM servicenow_retry_jobs WHERE status = ?",
                    (status.value,),
                ).fetchone()
        return row[0]

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

    def _insert_link_and_history(
        self,
        link: ServiceNowTicketLink,
        history: ServiceNowTicketHistoryEntry,
    ) -> None:
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


def _row_to_retry_job(row: sqlite3.Row) -> ServiceNowRetryJob:
    return ServiceNowRetryJob(
        job_id=row["job_id"],
        issue_id=row["issue_id"],
        request=ServiceNowTicketRequest(
            client_request_id=row["client_request_id"],
            issue_reference=row["issue_reference"],
            source_event_type=row["source_event_type"],
            priority=row["priority"],
            detail_reference_id=row["detail_reference_id"],
            correlation_id=row["correlation_id"],
        ),
        payload_digest=row["payload_digest"],
        status=ServiceNowRetryJobStatus(row["status"]),
        attempt_count=row["attempt_count"],
        next_attempt_at=datetime.fromisoformat(row["next_attempt_at"]),
        last_error_kind=row["last_error_kind"],
        link_id=row["link_id"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )
