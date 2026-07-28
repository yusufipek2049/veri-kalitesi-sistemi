"""PostgreSQL üzerinde atomik claim ve lease destekli kalıcı iş kuyruğu."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    DateTime,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    and_,
    insert,
    or_,
    select,
    update,
)
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import IntegrityError

from veri_kalitesi.audit import PostgreSQLTransactionalAudit, PreparedAuditEvent
from veri_kalitesi.jobs.errors import (
    JobConcurrencyError,
    JobConflictError,
    JobIdempotencyConflictError,
    JobLeaseError,
    JobNotFoundError,
    JobValidationError,
)
from veri_kalitesi.jobs.models import BackgroundJob, JobLeasePolicy, JobStatus, payload_to_json
from veri_kalitesi.persistence import DEFAULT_SCHEMA_NAME, SessionFactory, transactional_session


@dataclass(frozen=True)
class JobTables:
    background_jobs: Table


def job_tables(schema: str = DEFAULT_SCHEMA_NAME) -> JobTables:
    metadata = MetaData(schema=schema)
    jobs = Table(
        "background_jobs",
        metadata,
        Column("job_id", String(36), primary_key=True),
        Column("job_type", String(100), nullable=False),
        Column("payload", JSON, nullable=False),
        Column("status", String(30), nullable=False),
        Column("priority", Integer, nullable=False),
        Column("idempotency_key", String(200)),
        Column("available_at", DateTime(timezone=True), nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("updated_at", DateTime(timezone=True), nullable=False),
        Column("claimed_by", String(128)),
        Column("lease_expires_at", DateTime(timezone=True)),
        Column("last_heartbeat_at", DateTime(timezone=True)),
        Column("attempt_count", Integer, nullable=False),
        Column("version", Integer, nullable=False),
        Column("last_error_class", String(200)),
        UniqueConstraint(
            "job_type",
            "idempotency_key",
            name="uq_background_jobs_type_idempotency",
        ),
        CheckConstraint(
            "status IN ('QUEUED', 'RUNNING', 'SUCCESS', 'TECHNICAL_ERROR', 'TIMEOUT', 'CANCELLED')",
            name="ck_background_jobs_status",
        ),
        CheckConstraint("priority >= 0", name="ck_background_jobs_priority"),
        CheckConstraint("attempt_count >= 0", name="ck_background_jobs_attempt_count"),
        CheckConstraint("version >= 0", name="ck_background_jobs_version"),
    )
    Index(
        "ix_dq_background_jobs_claim",
        jobs.c.status,
        jobs.c.priority.desc(),
        jobs.c.available_at,
        jobs.c.created_at,
        jobs.c.job_id,
    )
    Index(
        "ix_dq_background_jobs_lease",
        jobs.c.status,
        jobs.c.lease_expires_at,
    )
    Index("ix_dq_background_jobs_job_type", jobs.c.job_type)
    return JobTables(background_jobs=jobs)


class PostgreSQLJobQueueRepository:
    def __init__(
        self,
        session_factory: SessionFactory,
        *,
        schema: str = DEFAULT_SCHEMA_NAME,
    ) -> None:
        self._session_factory = session_factory
        self._tables = job_tables(schema)

    def get_by_id(self, job_id: str) -> BackgroundJob | None:
        with self._session_factory() as session:
            row = (
                session.execute(
                    select(self._tables.background_jobs).where(
                        self._tables.background_jobs.c.job_id == job_id
                    )
                )
                .mappings()
                .one_or_none()
            )
        return _row_to_job(row) if row is not None else None

    def require_by_id(self, job_id: str) -> BackgroundJob:
        job = self.get_by_id(job_id)
        if job is None:
            raise JobNotFoundError("BackgroundJob not found.")
        return job

    def get_by_idempotency_key(
        self,
        job_type: str,
        idempotency_key: str,
    ) -> BackgroundJob | None:
        t = self._tables.background_jobs
        with self._session_factory() as session:
            row = (
                session.execute(
                    select(t).where(
                        t.c.job_type == job_type,
                        t.c.idempotency_key == idempotency_key,
                    )
                )
                .mappings()
                .one_or_none()
            )
        return _row_to_job(row) if row is not None else None

    def enqueue(
        self,
        job: BackgroundJob,
        *,
        audit_event: PreparedAuditEvent | None = None,
        audit_outbox: PostgreSQLTransactionalAudit | None = None,
    ) -> tuple[BackgroundJob, bool]:
        if (audit_event is None) != (audit_outbox is None):
            raise JobValidationError("Audit event and audit outbox must be provided together.")

        t = self._tables.background_jobs
        with transactional_session(self._session_factory) as session:
            if job.idempotency_key is not None:
                existing = (
                    session.execute(
                        select(t).where(
                            t.c.job_type == job.job_type,
                            t.c.idempotency_key == job.idempotency_key,
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
                if existing is not None:
                    return _resolve_idempotent_job(existing, job)

            try:
                with session.begin_nested():
                    session.execute(insert(t).values(_job_values(job)))
                    if audit_outbox is not None and audit_event is not None:
                        audit_outbox.stage(audit_event, session=session)
            except IntegrityError as exc:
                if job.idempotency_key is None:
                    raise JobConflictError("BackgroundJob could not be enqueued.") from exc
                existing = (
                    session.execute(
                        select(t).where(
                            t.c.job_type == job.job_type,
                            t.c.idempotency_key == job.idempotency_key,
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
                if existing is None:
                    raise JobConflictError("BackgroundJob could not be enqueued.") from exc
                return _resolve_idempotent_job(existing, job)
        return job, True

    def claim_next(
        self,
        worker_id: str,
        lease_policy: JobLeasePolicy,
        *,
        now: datetime | None = None,
    ) -> BackgroundJob | None:
        _validate_worker_id(worker_id)
        claimed_at = _aware_now(now)
        lease_expires_at = claimed_at + lease_policy.duration
        t = self._tables.background_jobs

        with transactional_session(self._session_factory) as session:
            row = (
                session.execute(
                    select(t)
                    .where(
                        or_(
                            and_(
                                t.c.status == JobStatus.QUEUED.value,
                                t.c.available_at <= claimed_at,
                            ),
                            and_(
                                t.c.status == JobStatus.RUNNING.value,
                                t.c.lease_expires_at <= claimed_at,
                            ),
                        )
                    )
                    .order_by(
                        t.c.priority.desc(),
                        t.c.available_at,
                        t.c.created_at,
                        t.c.job_id,
                    )
                    .limit(1)
                    .with_for_update(skip_locked=True)
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                return None
            result = session.execute(
                update(t)
                .where(
                    t.c.job_id == row["job_id"],
                    t.c.version == row["version"],
                )
                .values(
                    status=JobStatus.RUNNING.value,
                    claimed_by=worker_id,
                    lease_expires_at=lease_expires_at,
                    last_heartbeat_at=claimed_at,
                    attempt_count=t.c.attempt_count + 1,
                    version=t.c.version + 1,
                    updated_at=claimed_at,
                )
            )
            if result.rowcount == 0:
                raise JobConcurrencyError("BackgroundJob claim version conflict.")
            updated = session.execute(select(t).where(t.c.job_id == row["job_id"])).mappings().one()
            return _row_to_job(updated)

    def heartbeat(
        self,
        job_id: str,
        worker_id: str,
        expected_version: int,
        lease_policy: JobLeasePolicy,
        *,
        now: datetime | None = None,
    ) -> BackgroundJob:
        return self._renew_active_lease(
            job_id,
            worker_id,
            expected_version,
            lease_policy,
            now=now,
        )

    def renew_lease(
        self,
        job_id: str,
        worker_id: str,
        expected_version: int,
        lease_policy: JobLeasePolicy,
        *,
        now: datetime | None = None,
    ) -> BackgroundJob:
        return self._renew_active_lease(
            job_id,
            worker_id,
            expected_version,
            lease_policy,
            now=now,
        )

    def _renew_active_lease(
        self,
        job_id: str,
        worker_id: str,
        expected_version: int,
        lease_policy: JobLeasePolicy,
        *,
        now: datetime | None,
    ) -> BackgroundJob:
        _validate_worker_id(worker_id)
        heartbeat_at = _aware_now(now)
        t = self._tables.background_jobs
        with transactional_session(self._session_factory) as session:
            result = session.execute(
                update(t)
                .where(
                    t.c.job_id == job_id,
                    t.c.claimed_by == worker_id,
                    t.c.version == expected_version,
                    t.c.status == JobStatus.RUNNING.value,
                    t.c.lease_expires_at > heartbeat_at,
                )
                .values(
                    last_heartbeat_at=heartbeat_at,
                    lease_expires_at=heartbeat_at + lease_policy.duration,
                    version=t.c.version + 1,
                    updated_at=heartbeat_at,
                )
            )
            if result.rowcount == 0:
                current = (
                    session.execute(select(t).where(t.c.job_id == job_id)).mappings().one_or_none()
                )
                if current is None:
                    raise JobNotFoundError("BackgroundJob not found.")
                if (
                    current["status"] != JobStatus.RUNNING.value
                    or current["claimed_by"] != worker_id
                    or current["lease_expires_at"] is None
                    or current["lease_expires_at"] <= heartbeat_at
                ):
                    raise JobLeaseError("BackgroundJob lease is not active for this worker.")
                raise JobConcurrencyError("BackgroundJob heartbeat version conflict.")
            updated = session.execute(select(t).where(t.c.job_id == job_id)).mappings().one()
            return _row_to_job(updated)

    def release_expired_claims(
        self,
        *,
        now: datetime | None = None,
        job_id: str | None = None,
    ) -> int:
        released_at = _aware_now(now)
        t = self._tables.background_jobs
        conditions = [
            t.c.status == JobStatus.RUNNING.value,
            t.c.lease_expires_at <= released_at,
        ]
        if job_id is not None:
            conditions.append(t.c.job_id == job_id)
        with transactional_session(self._session_factory) as session:
            result = session.execute(
                update(t)
                .where(*conditions)
                .values(
                    status=JobStatus.QUEUED.value,
                    claimed_by=None,
                    lease_expires_at=None,
                    last_heartbeat_at=None,
                    version=t.c.version + 1,
                    updated_at=released_at,
                )
            )
            return int(result.rowcount or 0)


def _resolve_idempotent_job(
    row: RowMapping,
    candidate: BackgroundJob,
) -> tuple[BackgroundJob, bool]:
    if dict(row["payload"]) != payload_to_json(candidate.payload):
        raise JobIdempotencyConflictError(
            "Idempotency key was already used with a different payload."
        )
    return _row_to_job(row), False


def _job_values(job: BackgroundJob) -> dict[str, Any]:
    return {
        "job_id": job.job_id,
        "job_type": job.job_type,
        "payload": payload_to_json(job.payload),
        "status": job.status.value,
        "priority": job.priority,
        "idempotency_key": job.idempotency_key,
        "available_at": job.available_at,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "claimed_by": job.claimed_by,
        "lease_expires_at": job.lease_expires_at,
        "last_heartbeat_at": job.last_heartbeat_at,
        "attempt_count": job.attempt_count,
        "version": job.version,
        "last_error_class": job.last_error_class,
    }


def _row_to_job(row: RowMapping) -> BackgroundJob:
    return BackgroundJob(
        job_id=row["job_id"],
        job_type=row["job_type"],
        payload=dict(row["payload"]),
        status=JobStatus(row["status"]),
        priority=row["priority"],
        idempotency_key=row["idempotency_key"],
        available_at=row["available_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        claimed_by=row["claimed_by"],
        lease_expires_at=row["lease_expires_at"],
        last_heartbeat_at=row["last_heartbeat_at"],
        attempt_count=row["attempt_count"],
        version=row["version"],
        last_error_class=row["last_error_class"],
    )


def _validate_worker_id(worker_id: str) -> None:
    if not worker_id.strip():
        raise JobValidationError("Worker id must not be blank.")


def _aware_now(value: datetime | None) -> datetime:
    result = value or datetime.now(timezone.utc)
    if result.tzinfo is None or result.utcoffset() is None:
        raise JobValidationError("Job operation time must be timezone-aware.")
    return result
