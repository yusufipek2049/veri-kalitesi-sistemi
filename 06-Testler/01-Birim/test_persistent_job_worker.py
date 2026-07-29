"""Kalıcı worker politika, retry ve kalite ayrımı testleri."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from multiprocessing import get_context
from threading import Event, Thread
from time import monotonic, sleep

import pytest

from veri_kalitesi.executions import ConcurrencyPolicy
from veri_kalitesi.executions.source_usage_policies import (
    ResolvedSourceUsagePolicy,
    SourceRuntimePolicy,
)
from veri_kalitesi.jobs import (
    BackgroundJob,
    ExecutionJobHandler,
    JobCompletionOutcome,
    JobFailureKind,
    JobLeasePolicy,
    JobStatus,
    PermanentJobError,
    PersistentJobWorker,
    RetryableJobError,
)

NOW = datetime(2026, 7, 29, 9, 0, tzinfo=timezone.utc)


class _Audit:
    def prepare(self, event):
        return event


class _Resolver:
    def __init__(self, *, allowed: bool = True, retry_count: int = 2) -> None:
        self.policy = ResolvedSourceUsagePolicy(
            concurrency_policy=ConcurrencyPolicy(
                max_total=2,
                max_heavy=2,
                max_light=2,
                default_source_limit=2,
                default_heavy_source_limit=2,
                default_source_allowed=allowed,
            ),
            default_runtime_policy=SourceRuntimePolicy(
                connection_timeout_seconds=11,
                query_timeout_seconds=37,
                total_job_timeout_seconds=60,
                retry_count=retry_count,
                retry_delay_seconds=4,
            ),
            per_source_runtime_policies={},
        )

    def resolve_policy(self, *, at: datetime) -> ResolvedSourceUsagePolicy:
        assert at == NOW
        return self.policy


class _Repository:
    def __init__(self) -> None:
        self.job = BackgroundJob(
            job_id="job-001",
            job_type="EXECUTION",
            payload={"source_ids": ["source-a"]},
            status=JobStatus.RUNNING,
            claimed_by="worker-a",
            lease_expires_at=NOW + timedelta(minutes=5),
            last_heartbeat_at=NOW,
            attempt_count=1,
            version=1,
            available_at=NOW,
            created_at=NOW,
            updated_at=NOW,
        )
        self.claimed = False
        self.failure_call: tuple[JobFailureKind, int, float] | None = None
        self.completed_outcome: JobCompletionOutcome | None = None
        self.heartbeat_count = 0
        self.reaper_count = 0

    def claim_next(
        self,
        worker_id,
        lease_policy,
        *,
        now,
        max_running,
        source_limits,
        default_source_limit,
    ):
        assert worker_id == "worker-a"
        assert max_running == 2
        assert source_limits == {}
        assert default_source_limit == 2
        if self.claimed:
            return None
        self.claimed = True
        return self.job

    def require_by_id(self, job_id):
        assert job_id == self.job.job_id
        return self.job

    def release_expired_claims(self, *, now, audit_outbox, actor_id):
        assert audit_outbox is not None
        assert actor_id == "worker-a-lease-reaper"
        self.reaper_count += 1
        if (
            self.job.status is JobStatus.CANCEL_REQUESTED
            and self.job.lease_expires_at is not None
            and self.job.lease_expires_at <= now
        ):
            self.job = replace(
                self.job,
                status=JobStatus.CANCELLED,
                claimed_by=None,
                lease_expires_at=None,
            )
            return 1
        return 0

    def heartbeat(self, job_id, worker_id, expected_version, lease_policy, *, now):
        assert expected_version == self.job.version
        self.heartbeat_count += 1
        self.job = replace(
            self.job,
            last_heartbeat_at=now,
            lease_expires_at=now + lease_policy.duration,
            version=self.job.version + 1,
        )
        return self.job

    def record_failure(
        self,
        job_id,
        worker_id,
        expected_version,
        *,
        error_class,
        kind,
        retry_policy,
        now,
        audit_event,
        audit_outbox,
    ):
        self.failure_call = (
            kind,
            retry_policy.retry_count,
            retry_policy.retry_delay_seconds,
        )
        status = (
            JobStatus.QUEUED
            if kind is JobFailureKind.RETRYABLE_TECHNICAL
            else JobStatus.TIMEOUT
            if kind is JobFailureKind.TIMEOUT
            else JobStatus.TECHNICAL_ERROR
        )
        self.job = replace(self.job, status=status, last_error_class=error_class)
        return self.job

    def complete(
        self,
        job_id,
        worker_id,
        expected_version,
        outcome,
        *,
        now,
        audit_event,
        audit_outbox,
    ):
        self.completed_outcome = outcome
        self.job = replace(
            self.job,
            status=JobStatus.SUCCESS,
            completion_outcome=outcome,
        )
        return self.job

    def complete_cancelled(
        self,
        job_id,
        worker_id,
        expected_version,
        *,
        now,
        audit_event,
        audit_outbox,
    ):
        self.job = replace(self.job, status=JobStatus.CANCELLED)
        return self.job


def _worker(
    repository: _Repository,
    handler,
    *,
    resolver: _Resolver | None = None,
    lease_policy: JobLeasePolicy | None = None,
):
    return PersistentJobWorker(
        repository=repository,  # type: ignore[arg-type]
        policy_resolver=resolver or _Resolver(),
        handlers={"EXECUTION": handler},
        transactional_audit=_Audit(),  # type: ignore[arg-type]
        worker_id="worker-a",
        lease_policy=lease_policy or JobLeasePolicy(),
        clock=lambda: NOW,
    )


def test_retryable_technical_error_uses_active_policy_retry_limits() -> None:
    repository = _Repository()

    result = _worker(
        repository,
        lambda job, **kwargs: (_ for _ in ()).throw(
            RetryableJobError("TRANSIENT_NETWORK")
        ),
    ).run_once()

    assert result is not None
    assert result.status is JobStatus.QUEUED
    assert repository.failure_call == (JobFailureKind.RETRYABLE_TECHNICAL, 2, 4)


def test_production_poll_lifecycle_stops_on_signal() -> None:
    repository = _Repository()
    stop_event = Event()

    def handler(job, **kwargs):
        return JobCompletionOutcome.SUCCESS

    runner = Thread(
        target=_worker(repository, handler).run_forever,
        args=(stop_event,),
        kwargs={"idle_wait_seconds": 0.01},
    )
    runner.start()
    deadline = monotonic() + 1
    while repository.job.status is not JobStatus.SUCCESS and monotonic() < deadline:
        sleep(0.005)
    stop_event.set()
    runner.join(timeout=1)

    assert not runner.is_alive()
    assert repository.job.status is JobStatus.SUCCESS
    assert repository.reaper_count >= 1


def test_production_poll_reaps_expired_cancel_request_before_claim() -> None:
    repository = _Repository()
    repository.claimed = True
    repository.job = replace(
        repository.job,
        status=JobStatus.CANCEL_REQUESTED,
        lease_expires_at=NOW,
    )
    stop_event = Event()
    runner = Thread(
        target=_worker(
            repository,
            lambda job, **kwargs: JobCompletionOutcome.SUCCESS,
        ).run_forever,
        args=(stop_event,),
        kwargs={"idle_wait_seconds": 0.01},
    )

    runner.start()
    deadline = monotonic() + 1
    while repository.job.status is not JobStatus.CANCELLED and monotonic() < deadline:
        sleep(0.005)
    stop_event.set()
    runner.join(timeout=1)

    assert not runner.is_alive()
    assert repository.job.status is JobStatus.CANCELLED
    assert repository.reaper_count >= 1


@pytest.mark.parametrize(
    ("handler", "expected_outcome"),
    [
        (
            lambda job, **kwargs: JobCompletionOutcome.QUALITY_FAILURE,
            JobCompletionOutcome.QUALITY_FAILURE,
        ),
        (
            lambda job, **kwargs: (_ for _ in ()).throw(
                PermanentJobError("INVALID_SQL")
            ),
            None,
        ),
    ],
)
def test_quality_failure_is_successful_queue_work_and_permanent_error_is_not_retried(
    handler,
    expected_outcome: JobCompletionOutcome | None,
) -> None:
    repository = _Repository()

    result = _worker(repository, handler).run_once()

    assert result is not None
    if expected_outcome is not None:
        assert result.status is JobStatus.SUCCESS
        assert repository.completed_outcome is expected_outcome
        assert repository.failure_call is None
    else:
        assert result.status is JobStatus.TECHNICAL_ERROR
        assert repository.failure_call == (JobFailureKind.PERMANENT_TECHNICAL, 2, 4)


def test_closed_policy_rejects_claimed_job_without_running_handler() -> None:
    repository = _Repository()
    worker = _worker(
        repository,
        lambda job, **kwargs: JobCompletionOutcome.SUCCESS,
        resolver=_Resolver(allowed=False),
    )

    result = worker.run_once()

    assert result is not None
    assert result.status is JobStatus.TECHNICAL_ERROR
    assert repository.claimed is True
    assert repository.failure_call == (JobFailureKind.PERMANENT_TECHNICAL, 2, 4)


def test_handler_receives_separate_deadlines_and_long_execution_renews_lease() -> None:
    repository = _Repository()

    def handler(
        job,
        *,
        connection_timeout_seconds,
        query_timeout_seconds,
        total_timeout_seconds,
        cancellation_event,
    ):
        assert connection_timeout_seconds == 11
        assert query_timeout_seconds == 37
        assert total_timeout_seconds == 60
        assert cancellation_event is not None
        sleep(0.08)
        return JobCompletionOutcome.SUCCESS

    worker = PersistentJobWorker(
        repository=repository,  # type: ignore[arg-type]
        policy_resolver=_Resolver(),
        handlers={"EXECUTION": handler},
        transactional_audit=_Audit(),  # type: ignore[arg-type]
        worker_id="worker-a",
        lease_policy=JobLeasePolicy(duration=timedelta(milliseconds=30)),
        clock=lambda: NOW,
    )

    result = worker.run_once()

    assert result is not None
    assert result.status is JobStatus.SUCCESS
    assert repository.heartbeat_count >= 2


def test_running_cancel_stops_unaware_handler_and_prevents_late_side_effect() -> None:
    repository = _Repository()
    late_side_effect = get_context("fork").Event()

    def handler(job, **kwargs):
        sleep(0.5)
        late_side_effect.set()
        return JobCompletionOutcome.SUCCESS

    worker = _worker(repository, handler)
    runner = Thread(target=worker.run_once)
    runner.start()
    while not repository.claimed:
        sleep(0.005)
    repository.job = replace(
        repository.job,
        status=JobStatus.CANCEL_REQUESTED,
        version=repository.job.version + 1,
    )
    started = monotonic()
    runner.join(timeout=1)
    elapsed = monotonic() - started

    assert not runner.is_alive()
    assert repository.job.status is JobStatus.CANCELLED
    assert elapsed < 0.4
    sleep(0.35)
    assert not late_side_effect.is_set()


def test_total_deadline_forces_timeout_and_signals_blocked_handler() -> None:
    repository = _Repository()
    resolver = _Resolver()
    resolver.policy = replace(
        resolver.policy,
        default_runtime_policy=replace(
            resolver.policy.default_runtime_policy,
            total_job_timeout_seconds=0.05,
        ),
    )
    signalled = get_context("fork").Event()
    late_side_effect = get_context("fork").Event()

    def handler(job, *, cancellation_event, **kwargs):
        cancellation_event.wait(timeout=1)
        signalled.set()
        sleep(0.5)
        late_side_effect.set()
        return JobCompletionOutcome.SUCCESS

    started = monotonic()
    result = _worker(
        repository,
        handler,
        resolver=resolver,
        lease_policy=JobLeasePolicy(duration=timedelta(milliseconds=30)),
    ).run_once()
    elapsed = monotonic() - started

    assert result is not None
    assert result.status is JobStatus.TIMEOUT
    assert repository.failure_call == (JobFailureKind.TIMEOUT, 2, 4)
    assert signalled.is_set()
    assert repository.heartbeat_count >= 1
    assert elapsed < 0.4
    heartbeat_count_at_timeout = repository.heartbeat_count
    sleep(0.35)
    assert repository.heartbeat_count == heartbeat_count_at_timeout
    assert not late_side_effect.is_set()


@pytest.mark.parametrize("stop_reason", ["timeout", "cancel"])
def test_isolated_execution_invokes_connector_cancel_before_forced_termination(
    stop_reason: str,
) -> None:
    repository = _Repository()
    resolver = _Resolver()
    resolver.policy = replace(
        resolver.policy,
        default_runtime_policy=replace(
            resolver.policy.default_runtime_policy,
            total_job_timeout_seconds=0.05,
        ),
    )
    process_context = get_context("fork")
    execute_started = process_context.Event()
    connector_cancelled = process_context.Event()
    late_side_effect = process_context.Event()

    class _BlockedCommand:
        def execute(self, execution_id, **kwargs):
            assert execution_id == "execution-1"
            execute_started.set()
            sleep(1)
            late_side_effect.set()
            return JobCompletionOutcome.SUCCESS

        def cancel(self, execution_id):
            assert execution_id == "execution-1"
            connector_cancelled.set()

    repository.job = replace(
        repository.job,
        payload={
            "execution_id": "execution-1",
            "source_ids": ("source-a",),
        },
    )
    worker = _worker(
        repository,
        ExecutionJobHandler(_BlockedCommand()),
        resolver=resolver,
    )
    started = monotonic()
    runner = Thread(target=worker.run_once)
    runner.start()
    assert execute_started.wait(timeout=1)
    if stop_reason == "cancel":
        repository.job = replace(
            repository.job,
            status=JobStatus.CANCEL_REQUESTED,
            version=repository.job.version + 1,
        )
    runner.join(timeout=1)
    elapsed = monotonic() - started

    assert not runner.is_alive()
    assert connector_cancelled.is_set()
    assert repository.job.status is (
        JobStatus.TIMEOUT if stop_reason == "timeout" else JobStatus.CANCELLED
    )
    assert elapsed < 0.5
    sleep(0.6)
    assert not late_side_effect.is_set()


def test_blocked_cancel_unaware_handler_is_closed_by_total_deadline() -> None:
    repository = _Repository()
    resolver = _Resolver()
    resolver.policy = replace(
        resolver.policy,
        default_runtime_policy=replace(
            resolver.policy.default_runtime_policy,
            total_job_timeout_seconds=0.05,
        ),
    )

    def handler(job, **kwargs):
        sleep(0.2)
        return JobCompletionOutcome.SUCCESS

    worker = _worker(repository, handler, resolver=resolver)
    runner = Thread(target=worker.run_once)
    runner.start()
    while not repository.claimed:
        sleep(0.005)
    repository.job = replace(
        repository.job,
        status=JobStatus.CANCEL_REQUESTED,
        version=repository.job.version + 1,
    )
    runner.join(timeout=1)

    assert not runner.is_alive()
    assert repository.job.status is JobStatus.CANCELLED
