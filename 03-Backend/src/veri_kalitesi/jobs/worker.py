"""Politika kontrollü kalıcı iş worker yaşam döngüsü."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from multiprocessing import get_context
from multiprocessing.connection import Connection
from multiprocessing.process import BaseProcess
from threading import Event
from time import monotonic
from types import MappingProxyType
from typing import Protocol

from veri_kalitesi.audit import AuditEventInput, AuditResult, PostgreSQLTransactionalAudit
from veri_kalitesi.executions.source_usage_policies import SourceUsagePolicyResolver
from veri_kalitesi.jobs.models import (
    BackgroundJob,
    JobCompletionOutcome,
    JobFailureKind,
    JobLeasePolicy,
    JobRetryPolicy,
    JobStatus,
)
from veri_kalitesi.jobs.errors import JobConcurrencyError
from veri_kalitesi.jobs.postgresql_repository import PostgreSQLJobQueueRepository

_CANCELLATION_GRACE_SECONDS = 0.2


class JobHandler(Protocol):
    def __call__(
        self,
        job: BackgroundJob,
        *,
        connection_timeout_seconds: int,
        query_timeout_seconds: int,
        total_timeout_seconds: int,
        cancellation_event: Event,
    ) -> JobCompletionOutcome: ...


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
    clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)
    monotonic_clock: Callable[[], float] = monotonic

    def __post_init__(self) -> None:
        object.__setattr__(self, "handlers", MappingProxyType(dict(self.handlers)))

    def run_forever(
        self,
        stop_event: Event,
        *,
        idle_wait_seconds: float = 0.5,
    ) -> None:
        """Kontrollü kapatılabilen production poll yaşam döngüsünü çalıştır."""

        if idle_wait_seconds <= 0:
            raise ValueError("Worker idle wait must be positive.")
        while not stop_event.is_set():
            self.repository.release_expired_claims(
                now=self.clock(),
                audit_outbox=self.transactional_audit,
                actor_id=f"{self.worker_id}-lease-reaper",
            )
            if self.run_once() is None:
                stop_event.wait(idle_wait_seconds)

    def run_once(self) -> BackgroundJob | None:
        now = self.clock()
        resolved = self.policy_resolver.resolve_policy(at=now)
        concurrency = resolved.concurrency_policy
        claimed = self.repository.claim_next(
            self.worker_id,
            self.lease_policy,
            now=now,
            max_running=concurrency.max_total,
            source_limits=concurrency.per_source_limits,
            default_source_limit=concurrency.default_source_limit,
        )
        if claimed is None:
            return None
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
            return self._fail(
                claimed,
                "SOURCE_POLICY_DENIED",
                JobFailureKind.PERMANENT_TECHNICAL,
                JobRetryPolicy(runtime.retry_count, runtime.retry_delay_seconds),
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
        return self.repository.complete(
            current.job_id,
            self.worker_id,
            current.version,
            outcome,
            now=self.clock(),
            audit_event=audit,
            audit_outbox=self.transactional_audit,
        )

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
                    result = _read_handler_result(result_reader)
                    process.join(timeout=0.1)
                    if process.is_alive():
                        _terminate_process(process)
                    return result

                current = self.repository.require_by_id(claimed.job_id)
                if current.status is JobStatus.CANCEL_REQUESTED:
                    _cancel_process(
                        process,
                        cancellation_event,
                        grace_seconds=_CANCELLATION_GRACE_SECONDS,
                    )
                    return PermanentJobError("JOB_CANCELLED")
                if current.status is not JobStatus.RUNNING:
                    _cancel_process(
                        process,
                        cancellation_event,
                        grace_seconds=_CANCELLATION_GRACE_SECONDS,
                    )
                    return PermanentJobError("JOB_OWNERSHIP_LOST")

                current_tick = self.monotonic_clock()
                if current_tick >= next_heartbeat:
                    try:
                        self.repository.heartbeat(
                            current.job_id,
                            self.worker_id,
                            current.version,
                            self.lease_policy,
                            now=self.clock(),
                        )
                    except JobConcurrencyError:
                        # İptal isteği heartbeat ile yarışmış olabilir; sonraki
                        # turda güncel sürüm ve durum yeniden okunur.
                        pass
                    next_heartbeat = current_tick + heartbeat_seconds
                if not process.is_alive():
                    if result_reader.poll():
                        return _read_handler_result(result_reader)
                    return PermanentJobError("JOB_HANDLER_PROCESS_EXITED")
        finally:
            result_reader.close()
            if process.is_alive():
                _terminate_process(process)

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
        return self.repository.record_failure(
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
    try:
        outcome = handler(
            claimed,
            connection_timeout_seconds=connection_timeout_seconds,
            query_timeout_seconds=query_timeout_seconds,
            total_timeout_seconds=total_timeout_seconds,
            cancellation_event=cancellation_event,
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


def _read_handler_result(result_reader: Connection) -> JobCompletionOutcome | Exception:
    try:
        return _decode_handler_result(result_reader.recv())
    except EOFError:
        return PermanentJobError("JOB_HANDLER_PROCESS_EXITED")


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
