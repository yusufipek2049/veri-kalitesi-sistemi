"""PostgreSQL üzerinde atomik claim ve lease destekli kalıcı iş kuyruğu."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from collections.abc import Mapping
from typing import Any, cast
from uuid import uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    and_,
    func,
    insert,
    or_,
    select,
    update,
)
from sqlalchemy.engine import CursorResult, RowMapping
from sqlalchemy.exc import IntegrityError

from veri_kalitesi.audit import (
    AuditEventInput,
    AuditResult,
    PostgreSQLTransactionalAudit,
    PreparedAuditEvent,
)
from veri_kalitesi.jobs.errors import (
    JobConcurrencyError,
    JobConflictError,
    JobIdempotencyConflictError,
    JobLeaseError,
    JobNotFoundError,
    JobValidationError,
)
from veri_kalitesi.jobs.models import (
    BackgroundJob,
    DeadLetterRecord,
    DeadLetterStatus,
    JobCompletionOutcome,
    JobFailureKind,
    JobLeasePolicy,
    JobRetryPolicy,
    JobStatus,
    payload_to_json,
)
from veri_kalitesi.persistence import DEFAULT_SCHEMA_NAME, SessionFactory, transactional_session
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class JobTables:
    background_jobs: Table
    dead_letters: Table


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
        Column("completion_outcome", String(30)),
        Column("completed_at", DateTime(timezone=True)),
        Column("cancel_requested_at", DateTime(timezone=True)),
        Column("cancel_requested_by", String(128)),
        Column("cancel_reason_code", String(100)),
        UniqueConstraint(
            "job_type",
            "idempotency_key",
            name="uq_background_jobs_type_idempotency",
        ),
        CheckConstraint(
            "status IN ('QUEUED', 'RUNNING', 'CANCEL_REQUESTED', 'SUCCESS', "
            "'TECHNICAL_ERROR', 'TIMEOUT', 'CANCELLED')",
            name="ck_background_jobs_status",
        ),
        CheckConstraint(
            "completion_outcome IS NULL OR completion_outcome IN ('SUCCESS', 'QUALITY_FAILURE')",
            name="ck_background_jobs_completion_outcome",
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
    dead_letters = Table(
        "job_dead_letters",
        metadata,
        Column("dead_letter_id", String(36), primary_key=True),
        Column(
            "job_id",
            String(36),
            ForeignKey(f"{schema}.background_jobs.job_id" if schema else "background_jobs.job_id"),
            nullable=False,
        ),
        Column("error_class", String(200), nullable=False),
        Column("attempt_count", Integer, nullable=False),
        Column("status", String(20), nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("reprocessed_at", DateTime(timezone=True)),
        Column("reprocessed_by", String(128)),
        Column("audit_event_id", String(36)),
        CheckConstraint(
            "status IN ('OPEN', 'REPROCESSED')",
            name="ck_job_dead_letters_status",
        ),
        CheckConstraint("attempt_count > 0", name="ck_job_dead_letters_attempt_count"),
    )
    Index(
        "ix_dq_job_dead_letters_open",
        dead_letters.c.status,
        dead_letters.c.created_at,
        dead_letters.c.dead_letter_id,
    )
    Index("ix_dq_job_dead_letters_job", dead_letters.c.job_id)
    return JobTables(background_jobs=jobs, dead_letters=dead_letters)


class PostgreSQLJobQueueRepository:
    def __init__(
        self,
        session_factory: SessionFactory,
        *,
        schema: str = DEFAULT_SCHEMA_NAME,
    ) -> None:
        self._session_factory = session_factory
        self._tables = job_tables(schema)

    @property
    def session_factory(self) -> SessionFactory:
        return self._session_factory

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
        *,
        session: Session | None = None,
        for_update: bool = False,
    ) -> BackgroundJob | None:
        def _get(active_session: Session) -> BackgroundJob | None:
            t = self._tables.background_jobs
            statement = select(t).where(
                t.c.job_type == job_type,
                t.c.idempotency_key == idempotency_key,
            )
            if for_update:
                statement = statement.with_for_update()
            row = active_session.execute(statement).mappings().one_or_none()
            return _row_to_job(row) if row is not None else None

        if session is not None:
            return _get(session)
        with self._session_factory() as active_session:
            return _get(active_session)

    def enqueue(
        self,
        job: BackgroundJob,
        *,
        audit_event: PreparedAuditEvent | None = None,
        audit_outbox: PostgreSQLTransactionalAudit | None = None,
        session: Session | None = None,
    ) -> tuple[BackgroundJob, bool]:
        if (audit_event is None) != (audit_outbox is None):
            raise JobValidationError("Audit event and audit outbox must be provided together.")

        def _enqueue(active_session: Session) -> tuple[BackgroundJob, bool]:
            t = self._tables.background_jobs
            if job.idempotency_key is not None:
                existing = (
                    active_session.execute(
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
                with active_session.begin_nested():
                    active_session.execute(insert(t).values(_job_values(job)))
                    if audit_outbox is not None and audit_event is not None:
                        audit_outbox.stage(audit_event, session=active_session)
            except IntegrityError as exc:
                if job.idempotency_key is None:
                    raise JobConflictError("BackgroundJob could not be enqueued.") from exc
                existing = (
                    active_session.execute(
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

        if session is not None:
            return _enqueue(session)
        with transactional_session(self._session_factory) as active_session:
            return _enqueue(active_session)

    def claim_next(
        self,
        worker_id: str,
        lease_policy: JobLeasePolicy,
        *,
        now: datetime | None = None,
        max_running: int | None = None,
        source_limits: Mapping[str, int] | None = None,
        default_source_limit: int | None = None,
    ) -> BackgroundJob | None:
        _validate_worker_id(worker_id)
        if max_running is not None and max_running <= 0:
            raise JobValidationError("Job max_running must be positive.")
        if default_source_limit is not None and default_source_limit <= 0:
            raise JobValidationError("Job default_source_limit must be positive.")
        resolved_source_limits = dict(source_limits or {})
        if any(
            not isinstance(source_id, str)
            or not source_id.strip()
            or isinstance(limit, bool)
            or not isinstance(limit, int)
            or limit <= 0
            for source_id, limit in resolved_source_limits.items()
        ):
            raise JobValidationError("Job source limits must be positive.")
        claimed_at = _aware_now(now)
        lease_expires_at = claimed_at + lease_policy.duration
        t = self._tables.background_jobs

        with transactional_session(self._session_factory) as session:
            quota_controlled = (
                max_running is not None
                or default_source_limit is not None
                or bool(resolved_source_limits)
            )
            if quota_controlled:
                session.execute(
                    select(func.pg_advisory_xact_lock(func.hashtext("dq_background_jobs_claim")))
                )
            active_rows: tuple[RowMapping, ...] = ()
            if quota_controlled:
                active_rows = tuple(
                    session.execute(
                        select(t.c.payload).where(
                            t.c.status.in_(
                                (
                                    JobStatus.RUNNING.value,
                                    JobStatus.CANCEL_REQUESTED.value,
                                )
                            ),
                            t.c.lease_expires_at > claimed_at,
                        )
                    )
                    .mappings()
                    .all()
                )
            if max_running is not None and len(active_rows) >= max_running:
                return None
            source_counts: dict[str, int] = {}
            for active in active_rows:
                for source_id in _payload_source_ids(active["payload"]):
                    source_counts[source_id] = source_counts.get(source_id, 0) + 1
            candidates = (
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
                    .with_for_update(skip_locked=True)
                )
                .mappings()
                .all()
            )
            row = next(
                (
                    candidate
                    for candidate in candidates
                    if _source_quota_allows(
                        _payload_source_ids(candidate["payload"]),
                        source_counts,
                        resolved_source_limits,
                        default_source_limit,
                    )
                ),
                None,
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
            if cast(CursorResult[Any], result).rowcount == 0:
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
                    t.c.status.in_(
                        (
                            JobStatus.RUNNING.value,
                            JobStatus.CANCEL_REQUESTED.value,
                        )
                    ),
                    t.c.lease_expires_at > heartbeat_at,
                )
                .values(
                    last_heartbeat_at=heartbeat_at,
                    lease_expires_at=heartbeat_at + lease_policy.duration,
                    version=t.c.version + 1,
                    updated_at=heartbeat_at,
                )
            )
            if cast(CursorResult[Any], result).rowcount == 0:
                current = (
                    session.execute(select(t).where(t.c.job_id == job_id)).mappings().one_or_none()
                )
                if current is None:
                    raise JobNotFoundError("BackgroundJob not found.")
                if (
                    current["status"]
                    not in (
                        JobStatus.RUNNING.value,
                        JobStatus.CANCEL_REQUESTED.value,
                    )
                    or current["claimed_by"] != worker_id
                    or current["lease_expires_at"] is None
                    or current["lease_expires_at"] <= heartbeat_at
                ):
                    raise JobLeaseError("BackgroundJob lease is not active for this worker.")
                raise JobConcurrencyError("BackgroundJob heartbeat version conflict.")
            updated = session.execute(select(t).where(t.c.job_id == job_id)).mappings().one()
            return _row_to_job(updated)

    def complete(
        self,
        job_id: str,
        worker_id: str,
        expected_version: int,
        outcome: JobCompletionOutcome,
        *,
        now: datetime | None = None,
        audit_event: PreparedAuditEvent | None = None,
        audit_outbox: PostgreSQLTransactionalAudit | None = None,
    ) -> BackgroundJob:
        _require_audit(audit_event, audit_outbox)
        completed_at = _aware_now(now)
        return self._finish_owned_job(
            job_id,
            worker_id,
            expected_version,
            status=JobStatus.SUCCESS,
            completed_at=completed_at,
            completion_outcome=outcome,
            error_class=None,
            audit_event=audit_event,
            audit_outbox=audit_outbox,
        )

    def record_failure(
        self,
        job_id: str,
        worker_id: str,
        expected_version: int,
        *,
        error_class: str,
        kind: JobFailureKind,
        retry_policy: JobRetryPolicy,
        now: datetime | None = None,
        audit_event: PreparedAuditEvent | None = None,
        audit_outbox: PostgreSQLTransactionalAudit | None = None,
    ) -> BackgroundJob:
        _validate_code("error_class", error_class)
        failed_at = _aware_now(now)
        _validate_audit_pair(audit_event, audit_outbox)
        jobs = self._tables.background_jobs
        dead_letters = self._tables.dead_letters
        with transactional_session(self._session_factory) as session:
            current = (
                session.execute(select(jobs).where(jobs.c.job_id == job_id).with_for_update())
                .mappings()
                .one_or_none()
            )
            self._require_owned_active(current, worker_id, expected_version, failed_at)
            assert current is not None
            should_retry = (
                kind is JobFailureKind.RETRYABLE_TECHNICAL
                and current["attempt_count"] <= retry_policy.retry_count
            )
            if not should_retry:
                _require_audit(audit_event, audit_outbox)
            if should_retry:
                status = JobStatus.QUEUED
                available_at = failed_at + retry_policy.delay_for_attempt(current["attempt_count"])
                completed_at = None
            else:
                status = (
                    JobStatus.TIMEOUT
                    if kind is JobFailureKind.TIMEOUT
                    else JobStatus.TECHNICAL_ERROR
                )
                available_at = current["available_at"]
                completed_at = failed_at
            session.execute(
                update(jobs)
                .where(
                    jobs.c.job_id == job_id,
                    jobs.c.version == expected_version,
                )
                .values(
                    status=status.value,
                    available_at=available_at,
                    claimed_by=None,
                    lease_expires_at=None,
                    last_heartbeat_at=None,
                    last_error_class=error_class,
                    completion_outcome=None,
                    completed_at=completed_at,
                    version=jobs.c.version + 1,
                    updated_at=failed_at,
                )
            )
            if not should_retry and kind is JobFailureKind.RETRYABLE_TECHNICAL:
                session.execute(
                    insert(dead_letters).values(
                        dead_letter_id=str(uuid4()),
                        job_id=job_id,
                        error_class=error_class,
                        attempt_count=current["attempt_count"],
                        status=DeadLetterStatus.OPEN.value,
                        created_at=failed_at,
                    )
                )
            if audit_event is not None and audit_outbox is not None:
                audit_outbox.stage(audit_event, session=session)
            updated = session.execute(select(jobs).where(jobs.c.job_id == job_id)).mappings().one()
        return _row_to_job(updated)

    def request_cancel(
        self,
        job_id: str,
        expected_version: int,
        *,
        requested_by: str,
        reason_code: str,
        now: datetime | None = None,
        audit_event: PreparedAuditEvent | None = None,
        audit_outbox: PostgreSQLTransactionalAudit | None = None,
        session: Session | None = None,
    ) -> BackgroundJob:
        _require_audit(audit_event, audit_outbox)
        _validate_worker_id(requested_by)
        _validate_code("cancellation reason_code", reason_code)
        requested_at = _aware_now(now)
        _validate_audit_pair(audit_event, audit_outbox)
        t = self._tables.background_jobs

        def _request_cancel(active_session: Session) -> BackgroundJob:
            row = (
                active_session.execute(select(t).where(t.c.job_id == job_id).with_for_update())
                .mappings()
                .one_or_none()
            )
            if row is None:
                raise JobNotFoundError("BackgroundJob not found.")
            if row["version"] != expected_version:
                raise JobConcurrencyError("BackgroundJob cancellation version conflict.")
            if row["status"] not in {JobStatus.QUEUED.value, JobStatus.RUNNING.value}:
                raise JobConflictError("BackgroundJob cannot be cancelled in its current status.")
            queued = row["status"] == JobStatus.QUEUED.value
            active_session.execute(
                update(t)
                .where(t.c.job_id == job_id, t.c.version == expected_version)
                .values(
                    status=(
                        JobStatus.CANCELLED.value if queued else JobStatus.CANCEL_REQUESTED.value
                    ),
                    cancel_requested_at=requested_at,
                    cancel_requested_by=requested_by,
                    cancel_reason_code=reason_code,
                    completed_at=requested_at if queued else None,
                    claimed_by=None if queued else row["claimed_by"],
                    lease_expires_at=None if queued else row["lease_expires_at"],
                    last_heartbeat_at=None if queued else row["last_heartbeat_at"],
                    version=t.c.version + 1,
                    updated_at=requested_at,
                )
            )
            if audit_event is not None and audit_outbox is not None:
                audit_outbox.stage(audit_event, session=active_session)
            updated = active_session.execute(select(t).where(t.c.job_id == job_id)).mappings().one()
            return _row_to_job(updated)

        if session is not None:
            return _request_cancel(session)
        with transactional_session(self._session_factory) as active_session:
            return _request_cancel(active_session)

    def complete_cancelled(
        self,
        job_id: str,
        worker_id: str,
        expected_version: int,
        *,
        now: datetime | None = None,
        audit_event: PreparedAuditEvent | None = None,
        audit_outbox: PostgreSQLTransactionalAudit | None = None,
    ) -> BackgroundJob:
        _require_audit(audit_event, audit_outbox)
        completed_at = _aware_now(now)
        return self._finish_owned_job(
            job_id,
            worker_id,
            expected_version,
            status=JobStatus.CANCELLED,
            completed_at=completed_at,
            completion_outcome=None,
            error_class=None,
            allowed_statuses=(JobStatus.CANCEL_REQUESTED,),
            audit_event=audit_event,
            audit_outbox=audit_outbox,
        )

    def list_dead_letters(
        self,
        *,
        status: DeadLetterStatus = DeadLetterStatus.OPEN,
    ) -> tuple[DeadLetterRecord, ...]:
        t = self._tables.dead_letters
        with self._session_factory() as session:
            rows = (
                session.execute(
                    select(t)
                    .where(t.c.status == status.value)
                    .order_by(t.c.created_at, t.c.dead_letter_id)
                )
                .mappings()
                .all()
            )
        return tuple(_row_to_dead_letter(row) for row in rows)

    def reprocess_dead_letter(
        self,
        dead_letter_id: str,
        *,
        actor_id: str,
        now: datetime | None = None,
        audit_event: PreparedAuditEvent,
        audit_outbox: PostgreSQLTransactionalAudit,
    ) -> BackgroundJob:
        _validate_worker_id(actor_id)
        reprocessed_at = _aware_now(now)
        jobs = self._tables.background_jobs
        dead_letters = self._tables.dead_letters
        with transactional_session(self._session_factory) as session:
            letter = (
                session.execute(
                    select(dead_letters)
                    .where(dead_letters.c.dead_letter_id == dead_letter_id)
                    .with_for_update()
                )
                .mappings()
                .one_or_none()
            )
            if letter is None:
                raise JobNotFoundError("Job dead-letter record not found.")
            if letter["status"] != DeadLetterStatus.OPEN.value:
                raise JobConflictError("Job dead-letter record was already reprocessed.")
            requeue_result = session.execute(
                update(jobs)
                .where(
                    jobs.c.job_id == letter["job_id"],
                    jobs.c.status == JobStatus.TECHNICAL_ERROR.value,
                )
                .values(
                    status=JobStatus.QUEUED.value,
                    available_at=reprocessed_at,
                    completed_at=None,
                    last_error_class=None,
                    attempt_count=0,
                    version=jobs.c.version + 1,
                    updated_at=reprocessed_at,
                )
            )
            if cast(CursorResult[Any], requeue_result).rowcount == 0:
                raise JobConflictError("Dead-letter job is not in a reprocessable status.")
            session.execute(
                update(dead_letters)
                .where(dead_letters.c.dead_letter_id == dead_letter_id)
                .values(
                    status=DeadLetterStatus.REPROCESSED.value,
                    reprocessed_at=reprocessed_at,
                    reprocessed_by=actor_id,
                    audit_event_id=audit_event.event_id,
                )
            )
            audit_outbox.stage(audit_event, session=session)
            updated = (
                session.execute(select(jobs).where(jobs.c.job_id == letter["job_id"]))
                .mappings()
                .one()
            )
        return _row_to_job(updated)

    def _finish_owned_job(
        self,
        job_id: str,
        worker_id: str,
        expected_version: int,
        *,
        status: JobStatus,
        completed_at: datetime,
        completion_outcome: JobCompletionOutcome | None,
        error_class: str | None,
        allowed_statuses: tuple[JobStatus, ...] = (JobStatus.RUNNING,),
        audit_event: PreparedAuditEvent | None,
        audit_outbox: PostgreSQLTransactionalAudit | None,
    ) -> BackgroundJob:
        _validate_audit_pair(audit_event, audit_outbox)
        t = self._tables.background_jobs
        with transactional_session(self._session_factory) as session:
            current = (
                session.execute(select(t).where(t.c.job_id == job_id).with_for_update())
                .mappings()
                .one_or_none()
            )
            self._require_owned_active(
                current,
                worker_id,
                expected_version,
                completed_at,
                allowed_statuses=allowed_statuses,
            )
            session.execute(
                update(t)
                .where(t.c.job_id == job_id, t.c.version == expected_version)
                .values(
                    status=status.value,
                    claimed_by=None,
                    lease_expires_at=None,
                    last_heartbeat_at=None,
                    last_error_class=error_class,
                    completion_outcome=(
                        completion_outcome.value if completion_outcome is not None else None
                    ),
                    completed_at=completed_at,
                    version=t.c.version + 1,
                    updated_at=completed_at,
                )
            )
            if audit_event is not None and audit_outbox is not None:
                audit_outbox.stage(audit_event, session=session)
            updated = session.execute(select(t).where(t.c.job_id == job_id)).mappings().one()
        return _row_to_job(updated)

    @staticmethod
    def _require_owned_active(
        current: RowMapping | None,
        worker_id: str,
        expected_version: int,
        at: datetime,
        *,
        allowed_statuses: tuple[JobStatus, ...] = (JobStatus.RUNNING,),
    ) -> None:
        _validate_worker_id(worker_id)
        if current is None:
            raise JobNotFoundError("BackgroundJob not found.")
        if current["version"] != expected_version:
            raise JobConcurrencyError("BackgroundJob completion version conflict.")
        if (
            current["status"] not in {item.value for item in allowed_statuses}
            or current["claimed_by"] != worker_id
            or current["lease_expires_at"] is None
            or current["lease_expires_at"] <= at
        ):
            raise JobLeaseError("BackgroundJob lease is not active for this worker.")

    def release_expired_claims(
        self,
        *,
        now: datetime | None = None,
        job_id: str | None = None,
        audit_outbox: PostgreSQLTransactionalAudit | None = None,
        actor_id: str = "job-lease-reaper",
    ) -> int:
        released_at = _aware_now(now)
        t = self._tables.background_jobs
        cancel_conditions = [
            t.c.status == JobStatus.CANCEL_REQUESTED.value,
            t.c.lease_expires_at <= released_at,
        ]
        conditions = [
            t.c.status == JobStatus.RUNNING.value,
            t.c.lease_expires_at <= released_at,
        ]
        if job_id is not None:
            cancel_conditions.append(t.c.job_id == job_id)
            conditions.append(t.c.job_id == job_id)
        with transactional_session(self._session_factory) as session:
            expiring_cancellations = (
                session.execute(select(t).where(*cancel_conditions).with_for_update())
                .mappings()
                .all()
            )
            if expiring_cancellations and audit_outbox is None:
                raise JobValidationError("Lease-expiry cancellation requires transactional audit.")
            cancelled = session.execute(
                update(t)
                .where(*cancel_conditions)
                .values(
                    status=JobStatus.CANCELLED.value,
                    claimed_by=None,
                    lease_expires_at=None,
                    last_heartbeat_at=None,
                    completed_at=released_at,
                    version=t.c.version + 1,
                    updated_at=released_at,
                )
            )
            if audit_outbox is not None:
                for row in expiring_cancellations:
                    audit_outbox.stage(
                        audit_outbox.prepare(
                            AuditEventInput(
                                actor_id=actor_id,
                                actor_type="SERVICE",
                                correlation_id=row["job_id"],
                                action="JOB_CANCELLED",
                                object_type="BackgroundJob",
                                object_id=row["job_id"],
                                result=AuditResult.SUCCESS,
                                reason_code="CANCELLED_AFTER_LEASE_EXPIRY",
                                old_values={"status": JobStatus.CANCEL_REQUESTED.value},
                                new_values={"status": JobStatus.CANCELLED.value},
                                occurred_at=released_at,
                            )
                        ),
                        session=session,
                    )
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
            return int(cast(CursorResult[Any], cancelled).rowcount or 0) + int(
                cast(CursorResult[Any], result).rowcount or 0
            )


def _require_audit(
    audit_event: PreparedAuditEvent | None,
    audit_outbox: PostgreSQLTransactionalAudit | None,
) -> None:
    _validate_audit_pair(audit_event, audit_outbox)
    if audit_event is None:
        raise JobValidationError(
            "Terminal and cancellation transitions require transactional audit."
        )


def _resolve_idempotent_job(
    row: RowMapping,
    candidate: BackgroundJob,
) -> tuple[BackgroundJob, bool]:
    if dict(row["payload"]) != payload_to_json(candidate.payload):
        raise JobIdempotencyConflictError(
            "Idempotency key was already used with a different payload."
        )
    return _row_to_job(row), False


def _payload_source_ids(payload: object) -> tuple[str, ...]:
    if not isinstance(payload, Mapping):
        return ()
    value = payload.get("source_ids")
    if not isinstance(value, list | tuple):
        return ()
    return tuple(
        source_id for source_id in value if isinstance(source_id, str) and source_id.strip()
    )


def _source_quota_allows(
    source_ids: tuple[str, ...],
    source_counts: Mapping[str, int],
    source_limits: Mapping[str, int],
    default_source_limit: int | None,
) -> bool:
    return all(
        source_counts.get(source_id, 0)
        < source_limits.get(
            source_id,
            default_source_limit
            if default_source_limit is not None
            else source_counts.get(source_id, 0) + 1,
        )
        for source_id in set(source_ids)
    )


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
        "completion_outcome": (
            job.completion_outcome.value if job.completion_outcome is not None else None
        ),
        "completed_at": job.completed_at,
        "cancel_requested_at": job.cancel_requested_at,
        "cancel_requested_by": job.cancel_requested_by,
        "cancel_reason_code": job.cancel_reason_code,
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
        completion_outcome=(
            JobCompletionOutcome(row["completion_outcome"])
            if row["completion_outcome"] is not None
            else None
        ),
        completed_at=row["completed_at"],
        cancel_requested_at=row["cancel_requested_at"],
        cancel_requested_by=row["cancel_requested_by"],
        cancel_reason_code=row["cancel_reason_code"],
    )


def _row_to_dead_letter(row: RowMapping) -> DeadLetterRecord:
    return DeadLetterRecord(
        dead_letter_id=row["dead_letter_id"],
        job_id=row["job_id"],
        error_class=row["error_class"],
        attempt_count=row["attempt_count"],
        status=DeadLetterStatus(row["status"]),
        created_at=row["created_at"],
        reprocessed_at=row["reprocessed_at"],
        reprocessed_by=row["reprocessed_by"],
        audit_event_id=row["audit_event_id"],
    )


def _validate_audit_pair(
    audit_event: PreparedAuditEvent | None,
    audit_outbox: PostgreSQLTransactionalAudit | None,
) -> None:
    if (audit_event is None) != (audit_outbox is None):
        raise JobValidationError("Audit event and audit outbox must be provided together.")


def _validate_worker_id(worker_id: str) -> None:
    if not isinstance(worker_id, str) or not worker_id.strip():
        raise JobValidationError("Worker id must not be blank.")


def _validate_code(field_name: str, value: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Z][A-Z0-9_.-]{0,99}", value):
        raise JobValidationError(f"Job {field_name} must be a bounded non-sensitive code.")


def _aware_now(value: datetime | None) -> datetime:
    result = value or datetime.now(timezone.utc)
    if result.tzinfo is None or result.utcoffset() is None:
        raise JobValidationError("Job operation time must be timezone-aware.")
    return result
