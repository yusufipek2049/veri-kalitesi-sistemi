"""Append-only SQLite persistence for disposal jobs and result evidence."""

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
    DisposalJob,
    DisposalJobResult,
    DisposalJobStatus,
    DisposalMethod,
    RetentionRecordClass,
    RetentionScopeType,
)


class SQLiteDisposalJobRepository:
    def __init__(self, database: str = ":memory:") -> None:
        self.connection = sqlite3.connect(database, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self._lock = RLock()
        self._create_schema()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS disposal_jobs (
                job_id TEXT PRIMARY KEY,
                idempotency_key_digest TEXT NOT NULL UNIQUE,
                payload_digest TEXT NOT NULL,
                record_reference_digest TEXT NOT NULL,
                record_class TEXT NOT NULL,
                policy_code TEXT NOT NULL,
                policy_version TEXT NOT NULL,
                disposal_method TEXT NOT NULL,
                scope_type TEXT NOT NULL CHECK (scope_type IN ('SOURCE', 'DATASET', 'ENTERPRISE')),
                scope_digest TEXT,
                approval_reference TEXT NOT NULL,
                reason_code TEXT NOT NULL,
                prepared_by_actor_id TEXT NOT NULL,
                prepared_by_role TEXT NOT NULL,
                prepared_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS disposal_job_results (
                result_id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL UNIQUE REFERENCES disposal_jobs(job_id),
                status TEXT NOT NULL CHECK (status IN ('SUCCEEDED', 'FAILED_TECHNICAL')),
                affected_record_count INTEGER NOT NULL CHECK (affected_record_count >= 0),
                failed_record_count INTEGER NOT NULL CHECK (failed_record_count >= 0),
                evidence_reference TEXT NOT NULL,
                technical_error_code TEXT,
                result_digest TEXT NOT NULL,
                recorded_by_actor_id TEXT NOT NULL,
                recorded_by_role TEXT NOT NULL,
                recorded_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_disposal_jobs_policy_time
            ON disposal_jobs(policy_version, prepared_at, job_id);

            CREATE INDEX IF NOT EXISTS idx_disposal_jobs_scope
            ON disposal_jobs(scope_type, scope_digest, prepared_at);

            CREATE TRIGGER IF NOT EXISTS disposal_jobs_no_update
            BEFORE UPDATE ON disposal_jobs
            BEGIN
                SELECT RAISE(ABORT, 'disposal job history is append-only');
            END;

            CREATE TRIGGER IF NOT EXISTS disposal_jobs_no_delete
            BEFORE DELETE ON disposal_jobs
            BEGIN
                SELECT RAISE(ABORT, 'disposal job history is append-only');
            END;

            CREATE TRIGGER IF NOT EXISTS disposal_job_results_no_update
            BEFORE UPDATE ON disposal_job_results
            BEGIN
                SELECT RAISE(ABORT, 'disposal result history is append-only');
            END;

            CREATE TRIGGER IF NOT EXISTS disposal_job_results_no_delete
            BEFORE DELETE ON disposal_job_results
            BEGIN
                SELECT RAISE(ABORT, 'disposal result history is append-only');
            END;
            """
        )
        self.connection.commit()

    def create(
        self,
        job: DisposalJob,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> DisposalJob:
        self._require_shared_audit_transaction(audit_outbox)
        with self._lock, self.connection:
            existing = self._find_by_idempotency_digest(job.idempotency_key_digest)
            if existing is not None:
                if existing.payload_digest != job.payload_digest:
                    raise RetentionConflictError(
                        "Disposal idempotency key was reused with a different payload."
                    )
                return existing
            try:
                self.connection.execute(
                    """
                    INSERT INTO disposal_jobs (
                        job_id, idempotency_key_digest, payload_digest,
                        record_reference_digest, record_class, policy_code,
                        policy_version, disposal_method, scope_type, scope_digest,
                        approval_reference, reason_code, prepared_by_actor_id,
                        prepared_by_role, prepared_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    _job_values(job),
                )
                audit_outbox.stage(audit_event)
            except sqlite3.IntegrityError as exc:
                raise RetentionConflictError("Disposal job conflicts with stored history.") from exc
        return job

    def record_result(
        self,
        result: DisposalJobResult,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> DisposalJob:
        self._require_shared_audit_transaction(audit_outbox)
        with self._lock, self.connection:
            job = self.get(result.job_id)
            if job.result is not None:
                if job.result.result_digest != result.result_digest:
                    raise RetentionConflictError(
                        "Disposal job already has a different terminal result."
                    )
                return job
            try:
                self.connection.execute(
                    """
                    INSERT INTO disposal_job_results (
                        result_id, job_id, status, affected_record_count,
                        failed_record_count, evidence_reference,
                        technical_error_code, result_digest, recorded_by_actor_id,
                        recorded_by_role, recorded_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    _result_values(result),
                )
                audit_outbox.stage(audit_event)
            except sqlite3.IntegrityError as exc:
                raise RetentionConflictError(
                    "Disposal result conflicts with stored history."
                ) from exc
        return self.get(result.job_id)

    def get(self, job_id: str) -> DisposalJob:
        with self._lock:
            row = self.connection.execute(
                """
                SELECT jobs.*, results.result_id, results.status,
                       results.affected_record_count, results.failed_record_count,
                       results.evidence_reference, results.technical_error_code,
                       results.result_digest, results.recorded_by_actor_id,
                       results.recorded_by_role, results.recorded_at
                FROM disposal_jobs AS jobs
                LEFT JOIN disposal_job_results AS results ON results.job_id = jobs.job_id
                WHERE jobs.job_id = ?
                """,
                (job_id,),
            ).fetchone()
        if row is None:
            raise RetentionNotFoundError("Disposal job not found.")
        return _row_to_job(row)

    def get_by_idempotency_digest(self, digest: str) -> DisposalJob | None:
        with self._lock:
            return self._find_by_idempotency_digest(digest)

    def count_jobs(self) -> int:
        with self._lock:
            return self.connection.execute("SELECT COUNT(*) FROM disposal_jobs").fetchone()[0]

    def count_results(self) -> int:
        with self._lock:
            return self.connection.execute("SELECT COUNT(*) FROM disposal_job_results").fetchone()[
                0
            ]

    def _find_by_idempotency_digest(self, digest: str) -> DisposalJob | None:
        row = self.connection.execute(
            "SELECT job_id FROM disposal_jobs WHERE idempotency_key_digest = ?",
            (digest,),
        ).fetchone()
        if row is None:
            return None
        return self.get(row["job_id"])

    def _require_shared_audit_transaction(self, audit_outbox: SQLiteTransactionalAudit) -> None:
        if audit_outbox.connection is not self.connection:
            raise RetentionValidationError("Audit outbox must share the disposal transaction.")


def _job_values(job: DisposalJob) -> tuple[object, ...]:
    return (
        job.job_id,
        job.idempotency_key_digest,
        job.payload_digest,
        job.record_reference_digest,
        job.record_class.value,
        job.policy_code,
        job.policy_version,
        job.disposal_method.value,
        job.scope_type.value,
        job.scope_digest,
        job.approval_reference,
        job.reason_code,
        job.prepared_by_actor_id,
        job.prepared_by_role,
        _serialize_time(job.prepared_at),
    )


def _result_values(result: DisposalJobResult) -> tuple[object, ...]:
    return (
        result.result_id,
        result.job_id,
        result.status.value,
        result.affected_record_count,
        result.failed_record_count,
        result.evidence_reference,
        result.technical_error_code,
        result.result_digest,
        result.recorded_by_actor_id,
        result.recorded_by_role,
        _serialize_time(result.recorded_at),
    )


def _row_to_job(row: sqlite3.Row) -> DisposalJob:
    result = None
    if row["result_id"] is not None:
        result = DisposalJobResult(
            result_id=row["result_id"],
            job_id=row["job_id"],
            status=DisposalJobStatus(row["status"]),
            affected_record_count=row["affected_record_count"],
            failed_record_count=row["failed_record_count"],
            evidence_reference=row["evidence_reference"],
            technical_error_code=row["technical_error_code"],
            result_digest=row["result_digest"],
            recorded_by_actor_id=row["recorded_by_actor_id"],
            recorded_by_role=row["recorded_by_role"],
            recorded_at=_parse_time(row["recorded_at"]),
        )
    return DisposalJob(
        job_id=row["job_id"],
        idempotency_key_digest=row["idempotency_key_digest"],
        payload_digest=row["payload_digest"],
        record_reference_digest=row["record_reference_digest"],
        record_class=RetentionRecordClass(row["record_class"]),
        policy_code=row["policy_code"],
        policy_version=row["policy_version"],
        disposal_method=DisposalMethod(row["disposal_method"]),
        scope_type=RetentionScopeType(row["scope_type"]),
        scope_digest=row["scope_digest"],
        approval_reference=row["approval_reference"],
        reason_code=row["reason_code"],
        prepared_by_actor_id=row["prepared_by_actor_id"],
        prepared_by_role=row["prepared_by_role"],
        prepared_at=_parse_time(row["prepared_at"]),
        result=result,
    )


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _serialize_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()
