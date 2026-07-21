"""Append-only SQLite persistence for archive recall requests and decisions."""

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
    ArchiveRecallDecision,
    ArchiveRecallDecisionType,
    ArchiveRecallRequest,
    ArchiveRecordType,
    RetentionScopeType,
)


class SQLiteArchiveRecallRepository:
    def __init__(self, database: str = ":memory:") -> None:
        self.connection = sqlite3.connect(database, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self._lock = RLock()
        self._create_schema()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS archive_recall_requests (
                request_id TEXT PRIMARY KEY,
                idempotency_key_digest TEXT NOT NULL UNIQUE,
                payload_digest TEXT NOT NULL,
                archive_reference_digest TEXT NOT NULL,
                record_type TEXT NOT NULL CHECK (record_type IN ('AUDIT_LOG', 'QUALITY_SCORE')),
                scope_type TEXT NOT NULL CHECK (scope_type IN ('SOURCE', 'DATASET', 'ENTERPRISE')),
                scope_digest TEXT,
                purpose_code TEXT NOT NULL,
                requested_by_actor_id TEXT NOT NULL,
                requested_by_role TEXT NOT NULL,
                requested_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS archive_recall_decisions (
                decision_id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL UNIQUE REFERENCES archive_recall_requests(request_id),
                decision TEXT NOT NULL CHECK (decision IN ('APPROVED', 'REJECTED')),
                reason_code TEXT NOT NULL,
                decided_by_actor_id TEXT NOT NULL,
                decided_by_role TEXT NOT NULL,
                decided_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_archive_recall_request_time
            ON archive_recall_requests(requested_at, request_id);

            CREATE INDEX IF NOT EXISTS idx_archive_recall_scope
            ON archive_recall_requests(scope_type, scope_digest, requested_at);

            CREATE TRIGGER IF NOT EXISTS archive_recall_requests_no_update
            BEFORE UPDATE ON archive_recall_requests
            BEGIN
                SELECT RAISE(ABORT, 'archive recall request history is append-only');
            END;

            CREATE TRIGGER IF NOT EXISTS archive_recall_requests_no_delete
            BEFORE DELETE ON archive_recall_requests
            BEGIN
                SELECT RAISE(ABORT, 'archive recall request history is append-only');
            END;

            CREATE TRIGGER IF NOT EXISTS archive_recall_decisions_no_update
            BEFORE UPDATE ON archive_recall_decisions
            BEGIN
                SELECT RAISE(ABORT, 'archive recall decision history is append-only');
            END;

            CREATE TRIGGER IF NOT EXISTS archive_recall_decisions_no_delete
            BEFORE DELETE ON archive_recall_decisions
            BEGIN
                SELECT RAISE(ABORT, 'archive recall decision history is append-only');
            END;
            """
        )
        self.connection.commit()

    def create(
        self,
        request: ArchiveRecallRequest,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> ArchiveRecallRequest:
        self._require_shared_audit_transaction(audit_outbox)
        with self._lock, self.connection:
            existing = self._find_by_idempotency_digest(request.idempotency_key_digest)
            if existing is not None:
                if existing.payload_digest != request.payload_digest:
                    raise RetentionConflictError(
                        "Archive recall idempotency key was reused with a different payload."
                    )
                return existing
            try:
                self.connection.execute(
                    """
                    INSERT INTO archive_recall_requests (
                        request_id, idempotency_key_digest, payload_digest,
                        archive_reference_digest, record_type, scope_type,
                        scope_digest, purpose_code, requested_by_actor_id,
                        requested_by_role, requested_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    _request_values(request),
                )
                audit_outbox.stage(audit_event)
            except sqlite3.IntegrityError as exc:
                raise RetentionConflictError(
                    "Archive recall request conflicts with stored history."
                ) from exc
        return request

    def decide(
        self,
        decision: ArchiveRecallDecision,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> ArchiveRecallRequest:
        self._require_shared_audit_transaction(audit_outbox)
        with self._lock, self.connection:
            request = self.get(decision.request_id)
            if request.decision is not None:
                if (
                    request.decision.decision is not decision.decision
                    or request.decision.reason_code != decision.reason_code
                    or request.decision.decided_by_actor_id != decision.decided_by_actor_id
                ):
                    raise RetentionConflictError(
                        "Archive recall request already has a different decision."
                    )
                return request
            try:
                self.connection.execute(
                    """
                    INSERT INTO archive_recall_decisions (
                        decision_id, request_id, decision, reason_code,
                        decided_by_actor_id, decided_by_role, decided_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    _decision_values(decision),
                )
                audit_outbox.stage(audit_event)
            except sqlite3.IntegrityError as exc:
                raise RetentionConflictError(
                    "Archive recall decision conflicts with stored history."
                ) from exc
        return self.get(decision.request_id)

    def get(self, request_id: str) -> ArchiveRecallRequest:
        with self._lock:
            row = self.connection.execute(
                """
                SELECT requests.*, decisions.decision_id, decisions.decision,
                       decisions.reason_code, decisions.decided_by_actor_id,
                       decisions.decided_by_role, decisions.decided_at
                FROM archive_recall_requests AS requests
                LEFT JOIN archive_recall_decisions AS decisions
                  ON decisions.request_id = requests.request_id
                WHERE requests.request_id = ?
                """,
                (request_id,),
            ).fetchone()
        if row is None:
            raise RetentionNotFoundError("Archive recall request not found.")
        return _row_to_request(row)

    def get_by_idempotency_digest(self, digest: str) -> ArchiveRecallRequest | None:
        with self._lock:
            return self._find_by_idempotency_digest(digest)

    def count_requests(self) -> int:
        with self._lock:
            return self.connection.execute(
                "SELECT COUNT(*) FROM archive_recall_requests"
            ).fetchone()[0]

    def count_decisions(self) -> int:
        with self._lock:
            return self.connection.execute(
                "SELECT COUNT(*) FROM archive_recall_decisions"
            ).fetchone()[0]

    def _find_by_idempotency_digest(self, digest: str) -> ArchiveRecallRequest | None:
        row = self.connection.execute(
            "SELECT request_id FROM archive_recall_requests WHERE idempotency_key_digest = ?",
            (digest,),
        ).fetchone()
        if row is None:
            return None
        return self.get(row["request_id"])

    def _require_shared_audit_transaction(self, audit_outbox: SQLiteTransactionalAudit) -> None:
        if audit_outbox.connection is not self.connection:
            raise RetentionValidationError("Audit outbox must share the recall transaction.")


def _request_values(request: ArchiveRecallRequest) -> tuple[object, ...]:
    return (
        request.request_id,
        request.idempotency_key_digest,
        request.payload_digest,
        request.archive_reference_digest,
        request.record_type.value,
        request.scope_type.value,
        request.scope_digest,
        request.purpose_code,
        request.requested_by_actor_id,
        request.requested_by_role,
        _serialize_time(request.requested_at),
    )


def _decision_values(decision: ArchiveRecallDecision) -> tuple[object, ...]:
    return (
        decision.decision_id,
        decision.request_id,
        decision.decision.value,
        decision.reason_code,
        decision.decided_by_actor_id,
        decision.decided_by_role,
        _serialize_time(decision.decided_at),
    )


def _row_to_request(row: sqlite3.Row) -> ArchiveRecallRequest:
    decision = None
    if row["decision_id"] is not None:
        decision = ArchiveRecallDecision(
            decision_id=row["decision_id"],
            request_id=row["request_id"],
            decision=ArchiveRecallDecisionType(row["decision"]),
            reason_code=row["reason_code"],
            decided_by_actor_id=row["decided_by_actor_id"],
            decided_by_role=row["decided_by_role"],
            decided_at=_parse_time(row["decided_at"]),
        )
    return ArchiveRecallRequest(
        request_id=row["request_id"],
        idempotency_key_digest=row["idempotency_key_digest"],
        payload_digest=row["payload_digest"],
        archive_reference_digest=row["archive_reference_digest"],
        record_type=ArchiveRecordType(row["record_type"]),
        scope_type=RetentionScopeType(row["scope_type"]),
        scope_digest=row["scope_digest"],
        purpose_code=row["purpose_code"],
        requested_by_actor_id=row["requested_by_actor_id"],
        requested_by_role=row["requested_by_role"],
        requested_at=_parse_time(row["requested_at"]),
        decision=decision,
    )


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _serialize_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()
