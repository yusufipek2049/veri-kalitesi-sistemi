"""Politika kontrollü kalıcı iş worker yaşam döngüsü."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from multiprocessing import get_context
from multiprocessing.connection import Connection
from multiprocessing.process import BaseProcess
from threading import Event
from time import monotonic
from types import MappingProxyType
from typing import Protocol, cast
import logging

from veri_kalitesi.audit.models import (
    AuditEventInput,
    AuditResult,
)
from veri_kalitesi.audit.postgresql_outbox import PostgreSQLTransactionalAudit
from veri_kalitesi.executions.source_usage_policies import SourceUsagePolicyResolver
from veri_kalitesi.jobs.models import (
    BackgroundJob,
    JobCompletionOutcome,
    JobFailureKind,
    JobLeasePolicy,
    JobRetryPolicy,
    JobStatus,
    WorkerRegistration,
    WorkerState,
)
from veri_kalitesi.jobs.errors import JobConcurrencyError
from veri_kalitesi.jobs.postgresql_repository import PostgreSQLJobQueueRepository

_CANCELLATION_GRACE_SECONDS = 0.2
_BLOCKED_DELAY_SECONDS = 60
logger = logging.getLogger(__name__)


class JobHandler(Protocol):
    def __call__(
        self,
        job: BackgroundJob,
        *,
        connection_timeout_seconds: int,
        query_timeout_seconds: int,
        total_timeout_seconds: int,
        cancellation_event: Event,
        progress_callback: Callable[[int], None] = lambda _percent: None,
    ) -> JobCompletionOutcome: ...


class ScheduleTrigger(Protocol):
    def trigger_due(self) -> tuple[object, ...]: ...


class RetryableJobError(Exception):
    def __init__(self, error_class: str) -> None:
        super().__init__(error_class)
        self.error_class = error_class


class PermanentJobError(Exception):
    def __init__(self, error_class: str) -> None:
        super().__init__(error_class)
        self.error_class = error_class


class JobTimeoutError(Exception):
    def __init__(self, error_class: str = "QUERY_TIMEOUT") -> None:
        super().__init__(error_class)
        self.error_class = error_class


@dataclass(frozen=True)
class PersistentJobWorker:
    repository: PostgreSQLJobQueueRepository
    policy_resolver: SourceUsagePolicyResolver
    handlers: Mapping[str, JobHandler]
    transactional_audit: PostgreSQLTransactionalAudit
    worker_id: str
    lease_policy: JobLeasePolicy
    hostname: str = "localhost"
    capacity: int = 1
    schedule_triggers: tuple[ScheduleTrigger, ...] = ()
    schedule_trigger_interval_seconds: float = 5.0
    clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)
    monotonic_clock: Callable[[], float] = monotonic

    def __post_init__(self) -> None:
        if self.schedule_trigger_interval_seconds <= 0:
            raise ValueError("Schedule trigger interval must be positive.")
        object.__setattr__(self, "handlers", MappingProxyType(dict(self.handlers)))
        object.__setattr__(self, "schedule_triggers", tuple(self.schedule_triggers))

    @property
    def supported_job_types(self) -> tuple[str, ...]:
        return tuple(sorted(self.handlers.keys()))

    def register(self) -> WorkerRegistration:
        """Worker'ı workers tablosuna kaydet veya mevcut kaydı RUNNING yap."""

        now = self.clock()
        return self.repository.register_worker(
            WorkerRegistration(
                worker_id=self.worker_id,
                hostname=self.hostname,
                capacity=self.capacity,
                supported_job_types=self.supported_job_types,
                state=WorkerState.STARTING,
                started_at=now,
                last_seen_at=now,
            )
        )

    def run_forever(
        self,
        stop_event: Event,
        *,
        idle_wait_seconds: float = 0.5,
    ) -> None:
        """Kontrollü kapatılabilen production poll yaşam döngüsünü çalıştır."""

        if idle_wait_seconds <= 0:
            raise ValueError("Worker idle wait must be positive.")
        registration = self.register()
        worker_version = registration.version
        last_worker_heartbeat = self.monotonic_clock()
        last_schedule_trigger = (
            self.monotonic_clock() - self.schedule_trigger_interval_seconds
        )
        worker_heartbeat_interval = max(1.0, self.lease_policy.duration.total_seconds() / 6)
        while not stop_event.is_set():
            released_count = self.repository.release_expired_claims(
                now=self.clock(),
                audit_outbox=self.transactional_audit,
                actor_id=f"{self.worker_id}-lease-reaper",
            )
            if released_count:
                logger.warning(
                    "Expired job leases released",
                    extra={
                        "event": "job_lease_expired",
                        "worker_id": self.worker_id,
                        "released_count": released_count,
                    },
                )
            now_mono = self.monotonic_clock()
            if now_mono - last_schedule_trigger >= self.schedule_trigger_interval_seconds:
                for trigger in self.schedule_triggers:
                    try:
                        trigger.trigger_due()
                    except Exception as exc:
                        logger.warning(
                            "Schedule trigger failed",
                            extra={
                                "event": "schedule_trigger_failed",
                                "error_class": type(exc).__name__,
                            },
                        )
                last_schedule_trigger = now_mono
            if now_mono - last_worker_heartbeat >= worker_heartbeat_interval:
                try:
                    refreshed = self.repository.heartbeat_worker(
                        self.worker_id,
                        worker_version,
                        now=self.clock(),
                    )
                    worker_version = refreshed.version
                    last_worker_heartbeat = now_mono
                except Exception as exc:
                    logger.warning(
                        "Worker heartbeat failed",
                        extra={
                            "event": "worker_heartbeat_failed",
                            "worker_id": self.worker_id,
                            "error_class": type(exc).__name__,
                        },
                    )
            if self.run_once() is None:
                stop_event.wait(idle_wait_seconds)
        self._drain(worker_version)

    def _drain(self, worker_version: int) -> None:
        """Kontrollü kapanma: DRAINING → STOPPED."""

        try:
            drained = self.repository.begin_drain(
                self.worker_id,
                worker_version,
                now=self.clock(),
            )
            self.repository.stop_worker(
                self.worker_id,
                drained.version,
                now=self.clock(),
            )
        except Exception:
            pass

    def run_once(self) -> BackgroundJob | None:
        now = self.clock()
        resolved = self.policy_resolver.resolve_policy(at=now)
        concurrency = resolved.concurrency_policy
        claim_audit = self.transactional_audit.prepare(
            AuditEventInput(
                actor_id=self.worker_id,
                actor_type="SERVICE",
                correlation_id="job-claim",
                action="JOB_CLAIMED",
                object_type="BackgroundJob",
                object_id="",
                result=AuditResult.SUCCESS,
                reason_code="QUEUE_CLAIM",
                old_values={"status": JobStatus.QUEUED.value},
                new_values={"status": JobStatus.RUNNING.value, "worker_id": self.worker_id},
                occurred_at=now,
            )
        )
        claimed = self.repository.claim_next(
            self.worker_id,
            self.lease_policy,
            now=now,
            max_running=concurrency.max_total,
            source_limits=concurrency.per_source_limits,
            default_source_limit=concurrency.default_source_limit,
            audit_event=claim_audit,
            audit_outbox=self.transactional_audit,
        )
        if claimed is None:
            return None
        logger.info(
            "Job claimed",
            extra={
                "event": "job_claimed",
                "job_id": claimed.job_id,
                "job_type": claimed.job_type,
                "worker_id": self.worker_id,
                "attempt_count": claimed.attempt_count,
            },
        )
        try:
            source_ids = _source_ids(claimed)
        except PermanentJobError as exc:
            runtime = resolved.default_runtime_policy
            return self._fail(
                claimed,
                exc.error_class,
                JobFailureKind.PERMANENT_TECHNICAL,
                JobRetryPolicy(runtime.retry_count, runtime.retry_delay_seconds),
            )
        runtime = resolved.runtime_policy_for(source_ids)
        policy_allows = (
            all(concurrency.source_allowed(source_id) for source_id in source_ids)
            if source_ids
            else concurrency.default_source_allowed
        )
        if not policy_allows:
            # If the job has been blocked too many times, fail permanently
            # instead of creating an infinite retry storm.
            if claimed.block_count >= claimed.max_blocks:
                return self._fail(
                    claimed,
                    "SOURCE_POLICY_DENIED",
                    JobFailureKind.PERMANENT_TECHNICAL,
                    JobRetryPolicy(runtime.retry_count, runtime.retry_delay_seconds),
                )
            blocked_until = now + timedelta(seconds=_BLOCKED_DELAY_SECONDS)
            block_audit = self.transactional_audit.prepare(
                AuditEventInput(
                    actor_id=self.worker_id,
                    actor_type="SERVICE",
                    correlation_id=claimed.job_id,
                    action="JOB_BLOCKED",
                    object_type="BackgroundJob",
                    object_id=claimed.job_id,
                    result=AuditResult.SUCCESS,
                    reason_code="SOURCE_POLICY_DENIED",
                    old_values={"status": claimed.status.value},
                    new_values={
                        "status": JobStatus.BLOCKED.value,
                        "blocked_until": blocked_until.isoformat(),
                    },
                    occurred_at=now,
                )
            )
            return self.repository.block_job(
                claimed.job_id,
                self.worker_id,
                claimed.version,
                reason_code="SOURCE_POLICY_DENIED",
                blocked_until=blocked_until,
                now=now,
                audit_event=block_audit,
                audit_outbox=self.transactional_audit,
            )
        handler = self.handlers.get(claimed.job_type)
        if handler is None:
            return self._fail(
                claimed,
                "JOB_HANDLER_UNAVAILABLE",
                JobFailureKind.PERMANENT_TECHNICAL,
                JobRetryPolicy(runtime.retry_count, runtime.retry_delay_seconds),
            )
        outcome_or_error = self._execute_handler(claimed, handler, runtime)
        if isinstance(outcome_or_error, RetryableJobError):
            return self._fail(
                claimed,
                outcome_or_error.error_class,
                JobFailureKind.RETRYABLE_TECHNICAL,
                JobRetryPolicy(runtime.retry_count, runtime.retry_delay_seconds),
            )
        if isinstance(outcome_or_error, JobTimeoutError):
            return self._fail(
                claimed,
                outcome_or_error.error_class,
                JobFailureKind.TIMEOUT,
                JobRetryPolicy(runtime.retry_count, runtime.retry_delay_seconds),
            )
        if isinstance(outcome_or_error, PermanentJobError):
            return self._fail(
                claimed,
                outcome_or_error.error_class,
                JobFailureKind.PERMANENT_TECHNICAL,
                JobRetryPolicy(runtime.retry_count, runtime.retry_delay_seconds),
            )
        if isinstance(outcome_or_error, Exception):
            return self._fail(
                claimed,
                "UNEXPECTED",
                JobFailureKind.PERMANENT_TECHNICAL,
                JobRetryPolicy(runtime.retry_count, runtime.retry_delay_seconds),
            )
        outcome = outcome_or_error

        current = self.repository.require_by_id(claimed.job_id)
        if current.status is JobStatus.CANCEL_REQUESTED:
            audit = self._audit(
                current,
                action="JOB_CANCELLED",
                result=AuditResult.SUCCESS,
                reason_code="CANCEL_REQUEST_ACKNOWLEDGED",
                new_status=JobStatus.CANCELLED,
            )
            return self.repository.complete_cancelled(
                current.job_id,
                self.worker_id,
                current.version,
                now=self.clock(),
                audit_event=audit,
                audit_outbox=self.transactional_audit,
            )
        audit = self._audit(
            current,
            action="JOB_COMPLETED",
            result=AuditResult.SUCCESS,
            reason_code=outcome.value,
            new_status=JobStatus.SUCCESS,
        )
        completed = self.repository.complete(
            current.job_id,
            self.worker_id,
            current.version,
            outcome,
            now=self.clock(),
            audit_event=audit,
            audit_outbox=self.transactional_audit,
        )
        logger.info(
            "Job completed",
            extra={
                "event": "job_completed",
                "job_id": completed.job_id,
                "job_type": completed.job_type,
                "worker_id": self.worker_id,
                "outcome": outcome.value,
            },
        )
        return completed

    def _execute_handler(
        self,
        claimed: BackgroundJob,
        handler: JobHandler,
        runtime,
    ) -> JobCompletionOutcome | Exception:
        process_context = get_context("fork")
        cancellation_event = process_context.Event()
        result_reader, result_writer = process_context.Pipe(duplex=False)
        process = process_context.Process(
            target=_invoke_handler,
            args=(
                handler,
                claimed,
                runtime.connection_timeout_seconds,
                runtime.query_timeout_seconds,
                runtime.total_job_timeout_seconds,
                cancellation_event,
                result_writer,
            ),
            name=f"persistent-job-{claimed.job_id}",
            daemon=True,
        )
        process.start()
        result_writer.close()
        started = self.monotonic_clock()
        total_deadline = started + runtime.total_job_timeout_seconds
        heartbeat_seconds = max(
            0.01,
            min(self.lease_policy.duration.total_seconds() / 3, 5.0),
        )
        next_heartbeat = started + heartbeat_seconds
        current_version = claimed.version
        last_progress = -1
        try:
            while True:
                current_tick = self.monotonic_clock()
                if current_tick >= total_deadline:
                    _cancel_process(
                        process,
                        cancellation_event,
                        grace_seconds=_CANCELLATION_GRACE_SECONDS,
                    )
                    return JobTimeoutError("TOTAL_JOB_TIMEOUT")
                wait_seconds = min(
                    0.1,
                    max(0.0, next_heartbeat - current_tick),
                    max(0.0, total_deadline - current_tick),
                )
                if result_reader.poll(wait_seconds):
                    payload = _read_raw_pipe(result_reader)
                    if _is_progress_payload(payload):
                        current_version, last_progress = self._record_progress(
                            claimed,
                            current_version,
                            last_progress,
                            payload[1],
                        )
                        continue
                    return _finish_handler_process(process, payload)

                current = self.repository.require_by_id(claimed.job_id)
                stop_error = _stop_error_for_inactive_job(
                    current,
                    process,
                    cancellation_event,
                )
                if stop_error is not None:
                    return stop_error

                current_tick = self.monotonic_clock()
                current_version, next_heartbeat = self._renew_handler_lease(
                    current,
                    current_version,
                    current_tick,
                    next_heartbeat,
                    heartbeat_seconds,
                )
        finally:
            result_reader.close()
            if process.is_alive():
                _terminate_process(process)

    def _record_progress(
        self,
        claimed: BackgroundJob,
        current_version: int,
        last_progress: int,
        percent: object,
    ) -> tuple[int, int]:
        if not isinstance(percent, int) or not 0 <= percent <= 100 or percent <= last_progress:
            return current_version, last_progress
        try:
            updated = self.repository.update_progress(
                claimed.job_id,
                self.worker_id,
                current_version,
                percent,
                now=self.clock(),
            )
            current_version = updated.version
        except (JobConcurrencyError, Exception):
            pass
        return current_version, percent

    def _renew_handler_lease(
        self,
        current: BackgroundJob,
        current_version: int,
        current_tick: float,
        next_heartbeat: float,
        heartbeat_seconds: float,
    ) -> tuple[int, float]:
        if current_tick < next_heartbeat:
            return current_version, next_heartbeat
        try:
            refreshed = self.repository.heartbeat(
                current.job_id,
                self.worker_id,
                current.version,
                self.lease_policy,
                now=self.clock(),
            )
            current_version = refreshed.version
        except JobConcurrencyError:
            # İptal isteği heartbeat ile yarışmış olabilir; sonraki turda
            # güncel sürüm ve durum yeniden okunur.
            pass
        return current_version, current_tick + heartbeat_seconds

    def _fail(
        self,
        job: BackgroundJob,
        error_class: str,
        kind: JobFailureKind,
        retry_policy: JobRetryPolicy,
    ) -> BackgroundJob:
        current = self.repository.require_by_id(job.job_id)
        if current.status is JobStatus.CANCEL_REQUESTED:
            audit = self._audit(
                current,
                action="JOB_CANCELLED",
                result=AuditResult.SUCCESS,
                reason_code="CANCEL_REQUEST_ACKNOWLEDGED",
                new_status=JobStatus.CANCELLED,
            )
            return self.repository.complete_cancelled(
                current.job_id,
                self.worker_id,
                current.version,
                now=self.clock(),
                audit_event=audit,
                audit_outbox=self.transactional_audit,
            )
        terminal = (
            kind is not JobFailureKind.RETRYABLE_TECHNICAL
            or current.attempt_count > retry_policy.retry_count
        )
        target = (
            JobStatus.TIMEOUT
            if kind is JobFailureKind.TIMEOUT
            else JobStatus.TECHNICAL_ERROR
            if terminal
            else JobStatus.QUEUED
        )
        audit = self._audit(
            current,
            action="JOB_FAILED" if terminal else "JOB_RETRY_SCHEDULED",
            result=AuditResult.FAILURE,
            reason_code=error_class,
            new_status=target,
        )
        failed = self.repository.record_failure(
            current.job_id,
            self.worker_id,
            current.version,
            error_class=error_class,
            kind=kind,
            retry_policy=retry_policy,
            now=self.clock(),
            audit_event=audit,
            audit_outbox=self.transactional_audit,
        )
        logger.warning(
            "Job execution failed",
            extra={
                "event": "job_failed",
                "job_id": failed.job_id,
                "job_type": failed.job_type,
                "worker_id": self.worker_id,
                "error_class": error_class,
                "failure_kind": kind.value,
                "status": failed.status.value,
                "attempt_count": failed.attempt_count,
            },
        )
        if (
            kind is JobFailureKind.RETRYABLE_TECHNICAL
            and failed.status is JobStatus.TECHNICAL_ERROR
        ):
            logger.error(
                "Job moved to dead letter queue",
                extra={
                    "event": "job_dead_lettered",
                    "job_id": failed.job_id,
                    "job_type": failed.job_type,
                    "error_class": error_class,
                    "attempt_count": failed.attempt_count,
                },
            )
        return failed

    def _audit(
        self,
        job: BackgroundJob,
        *,
        action: str,
        result: AuditResult,
        reason_code: str,
        new_status: JobStatus,
    ):
        return self.transactional_audit.prepare(
            AuditEventInput(
                actor_id=self.worker_id,
                actor_type="SERVICE",
                correlation_id=job.job_id,
                action=action,
                object_type="BackgroundJob",
                object_id=job.job_id,
                result=result,
                reason_code=reason_code,
                old_values={"status": job.status.value, "attempt_count": job.attempt_count},
                new_values={"status": new_status.value, "attempt_count": job.attempt_count},
                occurred_at=self.clock(),
            )
        )


def _invoke_handler(
    handler: JobHandler,
    claimed: BackgroundJob,
    connection_timeout_seconds: int,
    query_timeout_seconds: int,
    total_timeout_seconds: int,
    cancellation_event,
    result_writer: Connection,
) -> None:
    def progress_callback(percent: int) -> None:
        try:
            result_writer.send(("progress", percent))
        except Exception:
            pass

    try:
        outcome = handler(
            claimed,
            connection_timeout_seconds=connection_timeout_seconds,
            query_timeout_seconds=query_timeout_seconds,
            total_timeout_seconds=total_timeout_seconds,
            cancellation_event=cancellation_event,
            progress_callback=progress_callback,
        )
        if not isinstance(outcome, JobCompletionOutcome):
            raise PermanentJobError("INVALID_JOB_OUTCOME")
        result_writer.send(("outcome", outcome.value))
    except RetryableJobError as exc:
        result_writer.send(("retryable", exc.error_class))
    except JobTimeoutError as exc:
        result_writer.send(("timeout", exc.error_class))
    except PermanentJobError as exc:
        result_writer.send(("permanent", exc.error_class))
    except Exception:
        result_writer.send(("permanent", "UNEXPECTED"))
    finally:
        result_writer.close()


def _decode_handler_result(payload: tuple[str, str]) -> JobCompletionOutcome | Exception:
    kind, value = payload
    if kind == "outcome":
        return JobCompletionOutcome(value)
    if kind == "retryable":
        return RetryableJobError(value)
    if kind == "timeout":
        return JobTimeoutError(value)
    return PermanentJobError(value)


def _is_progress_payload(payload: object) -> bool:
    return isinstance(payload, tuple) and len(payload) == 2 and payload[0] == "progress"


def _finish_handler_process(
    process: BaseProcess,
    payload: tuple[str, str],
) -> JobCompletionOutcome | Exception:
    result = _decode_handler_result(payload)
    process.join(timeout=0.1)
    if process.is_alive():
        _terminate_process(process)
    return result


def _stop_error_for_inactive_job(
    current: BackgroundJob,
    process: BaseProcess,
    cancellation_event,
) -> PermanentJobError | None:
    if current.status is JobStatus.RUNNING:
        return None
    _cancel_process(
        process,
        cancellation_event,
        grace_seconds=_CANCELLATION_GRACE_SECONDS,
    )
    if current.status is JobStatus.CANCEL_REQUESTED:
        return PermanentJobError("JOB_CANCELLED")
    return PermanentJobError("JOB_OWNERSHIP_LOST")


def _read_raw_pipe(reader: Connection) -> tuple[str, str] | tuple:
    try:
        return cast(tuple, reader.recv())
    except EOFError:
        return ("permanent", "JOB_HANDLER_PROCESS_EXITED")


def _read_handler_result(result_reader: Connection) -> JobCompletionOutcome | Exception:
    return _decode_handler_result(_read_raw_pipe(result_reader))


def _terminate_process(process: BaseProcess) -> None:
    if process.is_alive():
        process.terminate()
    process.join(timeout=1)
    if process.is_alive():
        process.kill()
        process.join()


def _cancel_process(
    process: BaseProcess,
    cancellation_event,
    *,
    grace_seconds: float,
) -> None:
    """Child'a aktif iptal için süre ver, kesin sınırda zorla sonlandır."""

    cancellation_event.set()
    process.join(timeout=grace_seconds)
    if process.is_alive():
        _terminate_process(process)


def _source_ids(job: BackgroundJob) -> tuple[str, ...]:
    value = job.payload.get("source_ids")
    if value is None:
        return ()
    if not isinstance(value, tuple) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise PermanentJobError("INVALID_SOURCE_SCOPE")
    return value
