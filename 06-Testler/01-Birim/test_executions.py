from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
import sqlite3
from time import perf_counter
from typing import Any

import pytest

from veri_kalitesi.audit import (
    AuditEvent,
    AuditRedactor,
    PreparedAuditEvent,
    SQLiteAuditRepository,
    SQLiteTransactionalAudit,
    build_default_redaction_policy,
)
from veri_kalitesi.data_sources import DataSource, DataSourceStatus, Dataset, SourceType
from veri_kalitesi.executions import (
    ConcurrencyPolicy,
    ExecutionService,
    ExecutionStatus,
    MeasurementStatus,
    ExecutionTechnicalError,
    ExecutionTimeoutError,
    ExecutionTimeouts,
    ExecutionType,
    ExecutionValidationError,
    IdempotencyConflictError,
    RetryPolicy,
    Schedule,
    ScheduleType,
    SchedulingService,
    RuleResultComputation,
    SQLiteExecutionRepository,
    SQLiteScheduleRepository,
    SQLiteSourceUsagePolicyRepository,
    SourceUsagePolicy,
    SourceUsagePolicyStatus,
    SourceUsagePolicyUnavailableError,
    SourceUsageWindow,
    WorkloadClass,
    preview_runs,
)
from veri_kalitesi.rules import (
    QualityDimension,
    QualityRule,
    RuleCriticality,
    RuleStatus,
    RuleType,
    RuleVersion,
)


DATASET_ID = "dataset-main"
SOURCE_ID = "source-main"


@dataclass
class FakeRuleCatalog:
    rule: QualityRule
    version: RuleVersion

    def get_rule(self, quality_rule_id: str) -> QualityRule:
        assert quality_rule_id == self.rule.quality_rule_id
        return self.rule

    def get_version(self, rule_version_id: str) -> RuleVersion:
        assert rule_version_id == self.version.rule_version_id
        return self.version

    def list_versions(self, quality_rule_id: str) -> list[RuleVersion]:
        assert quality_rule_id == self.rule.quality_rule_id
        return [self.version]


@dataclass
class FakeSourceCatalog:
    source_status: DataSourceStatus = DataSourceStatus.ACTIVE

    def get_dataset(self, dataset_id: str) -> Dataset:
        assert dataset_id == DATASET_ID
        return Dataset(
            dataset_id=DATASET_ID,
            data_source_id=SOURCE_ID,
            namespace="public",
            name="customers",
        )

    def get_data_source(self, data_source_id: str) -> DataSource:
        assert data_source_id == SOURCE_ID
        return DataSource(
            data_source_id=SOURCE_ID,
            name="Test CSV",
            source_type=SourceType.CSV,
            connection_config={"file_path": "/not-read-by-execution-unit-test.csv"},
            secret_reference="secret://test/executions",
            status=self.source_status,
        )


class FakeExecutionExecutor:
    def __init__(self, outcomes: list[tuple[RuleResultComputation, ...] | Exception]) -> None:
        self.outcomes = outcomes
        self.calls: list[dict[str, Any]] = []

    def execute(self, **kwargs: Any) -> tuple[RuleResultComputation, ...]:
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FakeTechnicalEventSink:
    def __init__(self) -> None:
        self.executions: list[Any] = []

    def notify_technical_failure(self, execution: Any) -> None:
        self.executions.append(execution)


class FakeCancellationSink:
    def __init__(self) -> None:
        self.executions: list[Any] = []

    def request_cancel(self, execution: Any) -> None:
        self.executions.append(execution)


class FakeScheduleTechnicalEventSink:
    def __init__(self) -> None:
        self.events: list[tuple[Any, str]] = []

    def notify_schedule_failure(self, schedule: Any, error_class: str) -> None:
        self.events.append((schedule, error_class))


def _schedule_audit(
    repository: SQLiteScheduleRepository,
    audit_repository: Any | None = None,
) -> SQLiteTransactionalAudit:
    return SQLiteTransactionalAudit(
        repository.connection,
        AuditRedactor(build_default_redaction_policy()),
        audit_repository or SQLiteAuditRepository(),
        policy_version="AUDIT_OUTBOX_TEST_V1",
    )


def _schedule_events(service: SchedulingService) -> list[AuditEvent]:
    repository = service.transactional_audit.repository
    assert isinstance(repository, SQLiteAuditRepository)
    return repository.list_events()


class FailingScheduleAuditRepository:
    def append(self, prepared: PreparedAuditEvent) -> AuditEvent:
        raise sqlite3.OperationalError("synthetic audit outage")


class FailingScheduleStageAudit(SQLiteTransactionalAudit):
    def stage(self, prepared: PreparedAuditEvent) -> None:
        raise sqlite3.OperationalError("synthetic outbox write failure")


@dataclass
class StaticWorkloadClassifier:
    workload_class: WorkloadClass

    def classify(self, versions: Any, scope: Any) -> WorkloadClass:
        return self.workload_class


def test_fr_036_fr_043_fr_044_uc_008_manual_execution_persists_queue_history_and_results() -> None:
    executor = FakeExecutionExecutor([(_computation(125, 100, 25),)])
    service, repository, version = _service(executor)

    started = perf_counter()
    queued = service.start_manual(
        actor_id="user-1",
        idempotency_key="manual-customers-2026-07-16",
        rule_version_ids=(version.rule_version_id,),
        scope={"partition": "2026-07"},
        correlation_id="correlation-1",
    )
    elapsed = perf_counter() - started
    completed = service.run_next()

    assert elapsed < 3
    assert queued.status is ExecutionStatus.QUEUED
    assert queued.correlation_id == "correlation-1"
    assert completed is not None
    assert completed.status is ExecutionStatus.SUCCESS
    assert completed.started_at is not None
    assert completed.finished_at is not None
    assert completed.attempt_count == 1
    assert repository.list_executions() == [completed]
    result = repository.list_results(completed.execution_id)[0]
    assert (result.checked_count, result.passed_count, result.failed_count) == (125, 100, 25)


def test_fr_045_nfr_rel_005_ac_024_concurrent_repeats_return_one_execution_id() -> None:
    executor = FakeExecutionExecutor([(_computation(1, 1, 0),)])
    service, repository, version = _service(executor)

    def start(_: int) -> str:
        execution = service.start_manual(
            actor_id="user-1",
            idempotency_key="same-request",
            rule_version_ids=(version.rule_version_id,),
            scope={"dataset_id": DATASET_ID},
        )
        return execution.execution_id

    with ThreadPoolExecutor(max_workers=10) as pool:
        execution_ids = list(pool.map(start, range(10)))

    assert len(set(execution_ids)) == 1
    assert len(repository.list_executions()) == 1


def test_fr_045_rule_011_rejects_same_idempotency_key_with_different_payload() -> None:
    executor = FakeExecutionExecutor([(_computation(1, 1, 0),)])
    service, repository, version = _service(executor)
    service.start_manual(
        actor_id="user-1",
        idempotency_key="same-key",
        rule_version_ids=(version.rule_version_id,),
        scope={"partition": "A"},
    )

    with pytest.raises(IdempotencyConflictError):
        service.start_manual(
            actor_id="user-1",
            idempotency_key="same-key",
            rule_version_ids=(version.rule_version_id,),
            scope={"partition": "B"},
        )

    assert len(repository.list_executions()) == 1


def test_fr_036_uc_008_rejects_draft_rule_before_queue_creation() -> None:
    executor = FakeExecutionExecutor([(_computation(1, 1, 0),)])
    service, repository, version = _service(executor, rule_status=RuleStatus.DRAFT)

    with pytest.raises(ExecutionValidationError, match="active rules"):
        service.start_manual(
            actor_id="user-1",
            idempotency_key="draft-rule",
            rule_version_ids=(version.rule_version_id,),
        )

    assert repository.list_executions() == []


def test_nfr_sec_005_uc_008_rejects_secret_fields_in_execution_scope() -> None:
    executor = FakeExecutionExecutor([(_computation(1, 1, 0),)])
    service, repository, version = _service(executor)

    with pytest.raises(ExecutionValidationError, match="secret fields"):
        service.start_manual(
            actor_id="user-1",
            idempotency_key="unsafe-scope",
            rule_version_ids=(version.rule_version_id,),
            scope={"partition": {"token": "must-not-be-stored"}},
        )

    assert repository.list_executions() == []


def test_fr_041_nfr_rel_001_uc_008_retries_transient_error_with_exponential_delays() -> None:
    executor = FakeExecutionExecutor(
        [
            ExecutionTechnicalError("NETWORK", retryable=True),
            ExecutionTechnicalError("NETWORK", retryable=True),
            (_computation(10, 10, 0),),
        ]
    )
    delays: list[float] = []
    service, repository, version = _service(executor, sleeper=delays.append)
    queued = _start(service, version)

    completed = service.run_next()

    assert completed is not None
    assert completed.status is ExecutionStatus.SUCCESS
    assert completed.attempt_count == 3
    assert delays == [1.0, 2.0]
    attempts = repository.list_attempts(queued.execution_id)
    assert [attempt.status for attempt in attempts] == [
        ExecutionStatus.TECHNICAL_ERROR,
        ExecutionStatus.TECHNICAL_ERROR,
        ExecutionStatus.SUCCESS,
    ]


def test_fr_041_rule_003_quality_failure_does_not_retry() -> None:
    executor = FakeExecutionExecutor([(_computation(20, 15, 5),)])
    service, repository, version = _service(executor)
    queued = _start(service, version)

    completed = service.run_next()

    assert completed is not None
    assert completed.status is ExecutionStatus.SUCCESS
    assert len(executor.calls) == 1
    assert len(repository.list_attempts(queued.execution_id)) == 1
    assert repository.list_results(queued.execution_id)[0].failed_count == 5


def test_fr_040_fr_041_ac_010_technical_error_retries_without_numeric_result_and_notifies() -> None:
    executor = FakeExecutionExecutor(
        [ExecutionTechnicalError("NETWORK", retryable=True) for _ in range(3)]
    )
    notifications = FakeTechnicalEventSink()
    service, repository, version = _service(
        executor,
        sleeper=lambda _: None,
        technical_event_sink=notifications,
    )
    queued = _start(service, version)

    failed = service.run_next()

    assert failed is not None
    assert failed.status is ExecutionStatus.TECHNICAL_ERROR
    assert failed.error_class == "NETWORK"
    assert failed.attempt_count == 3
    assert repository.list_results(queued.execution_id) == []
    assert notifications.executions == [failed]


def test_fr_040_nfr_rel_002_passes_separate_timeouts_to_worker() -> None:
    executor = FakeExecutionExecutor([(_computation(1, 1, 0),)])
    timeouts = ExecutionTimeouts(connection_seconds=10, query_seconds=20, total_seconds=30)
    service, _, version = _service(executor, timeouts=timeouts)
    _start(service, version)

    service.run_next()

    assert executor.calls[0]["timeouts"] == timeouts


def test_fr_039_fr_040_fr_041_source_policy_controls_query_timeout_and_retry() -> None:
    fixed_now = datetime(2026, 7, 21, 8, 0, tzinfo=timezone.utc)
    resolver = SQLiteSourceUsagePolicyRepository()
    resolver.save(
        _active_source_policy(
            query_timeout_seconds=120,
            retry_count=1,
            retry_delay_seconds=4,
        )
    )
    executor = FakeExecutionExecutor(
        [
            ExecutionTechnicalError("NETWORK", retryable=True),
            (_computation(1, 1, 0),),
        ]
    )
    delays: list[float] = []
    service, _, version = _service(
        executor,
        timeouts=ExecutionTimeouts(
            connection_seconds=10,
            query_seconds=900,
            total_seconds=1200,
        ),
        source_usage_policy_resolver=resolver,
        sleeper=delays.append,
        clock=lambda: fixed_now,
    )
    _start(service, version)

    completed = service.run_next()

    assert completed is not None and completed.status is ExecutionStatus.SUCCESS
    assert len(executor.calls) == 2
    assert [call["timeouts"] for call in executor.calls] == [
        ExecutionTimeouts(connection_seconds=10, query_seconds=120, total_seconds=1200),
        ExecutionTimeouts(connection_seconds=10, query_seconds=120, total_seconds=1200),
    ]
    assert delays == [4]


def test_fr_041_source_policy_zero_retry_stops_after_first_technical_error() -> None:
    fixed_now = datetime(2026, 7, 21, 8, 0, tzinfo=timezone.utc)
    resolver = SQLiteSourceUsagePolicyRepository()
    resolver.save(_active_source_policy(retry_count=0))
    executor = FakeExecutionExecutor(
        [
            ExecutionTechnicalError("NETWORK", retryable=True),
            (_computation(1, 1, 0),),
        ]
    )
    delays: list[float] = []
    service, _, version = _service(
        executor,
        source_usage_policy_resolver=resolver,
        sleeper=delays.append,
        clock=lambda: fixed_now,
    )
    _start(service, version)

    completed = service.run_next()

    assert completed is not None
    assert completed.status is ExecutionStatus.TECHNICAL_ERROR
    assert len(executor.calls) == 1
    assert delays == []


def test_fr_042_queued_execution_is_cancelled_immediately_and_idempotently() -> None:
    executor = FakeExecutionExecutor([(_computation(1, 1, 0),)])
    service, repository, version = _service(executor)
    queued = _start(service, version)

    started = perf_counter()
    cancelled = service.cancel_execution(
        actor_id="operator-1",
        execution_id=queued.execution_id,
        reason="Yanlış kapsam seçildi.",
    )
    repeated = service.cancel_execution(
        actor_id="operator-1",
        execution_id=queued.execution_id,
        reason="Yanlış kapsam seçildi.",
    )

    assert perf_counter() - started < 5
    assert cancelled.status is ExecutionStatus.CANCELLED
    assert cancelled.cancel_requested_by == "operator-1"
    assert cancelled.cancel_requested_at is not None
    assert cancelled.cancelled_at == cancelled.finished_at
    assert repeated == cancelled
    assert service.run_next() is None
    assert executor.calls == []
    assert repository.list_results(queued.execution_id) == []


def test_fr_042_running_execution_records_request_and_signals_executor_once() -> None:
    cancellation_sink = FakeCancellationSink()
    service, repository, version = _service(
        FakeExecutionExecutor([(_computation(1, 1, 0),)]),
        cancellation_sink=cancellation_sink,
    )
    queued = _start(service, version)
    running = repository.claim_next(datetime.now(timezone.utc))
    assert running is not None

    requested = service.cancel_execution(
        actor_id="operator-1",
        execution_id=queued.execution_id,
        reason="Kaynak bakım penceresine girdi.",
    )
    repeated = service.cancel_execution(
        actor_id="operator-1",
        execution_id=queued.execution_id,
        reason="Kaynak bakım penceresine girdi.",
    )

    assert requested.status is ExecutionStatus.CANCEL_REQUESTED
    assert requested.finished_at is None
    assert repeated == requested
    assert cancellation_sink.executions == [requested]


def test_fr_042_cancel_requested_execution_closes_at_total_timeout() -> None:
    now = datetime(2026, 7, 16, 8, 0, tzinfo=timezone.utc)
    current = [now]
    service, repository, version = _service(
        FakeExecutionExecutor([(_computation(1, 1, 0),)]),
        timeouts=ExecutionTimeouts(
            connection_seconds=5,
            query_seconds=10,
            total_seconds=20,
        ),
        clock=lambda: current[0],
    )
    queued = _start(service, version)
    assert repository.claim_next(now) is not None
    service.cancel_execution(
        actor_id="operator-1",
        execution_id=queued.execution_id,
        reason="Uzun süren sorguyu durdur.",
    )

    current[0] = now + timedelta(seconds=19)
    assert service.close_expired_cancellations() == ()
    current[0] = now + timedelta(seconds=20)
    closed = service.close_expired_cancellations()

    assert len(closed) == 1
    assert closed[0].status is ExecutionStatus.CANCELLED
    assert closed[0].cancelled_at == current[0]
    assert repository.get(queued.execution_id) == closed[0]


def test_fr_042_rejects_invalid_reason_and_terminal_execution_transition() -> None:
    service, _, version = _service(FakeExecutionExecutor([(_computation(1, 1, 0),)]))
    queued = _start(service, version)

    with pytest.raises(ExecutionValidationError, match="Cancellation reason"):
        service.cancel_execution(
            actor_id="operator-1", execution_id=queued.execution_id, reason=" "
        )

    completed = service.run_next()
    assert completed is not None
    with pytest.raises(ExecutionValidationError, match="queued or running"):
        service.cancel_execution(
            actor_id="operator-1",
            execution_id=completed.execution_id,
            reason="Artık çok geç.",
        )


def test_fr_040_ac_012_timeout_persists_partial_results_outside_official_scoring() -> None:
    timeout = ExecutionTimeoutError(
        "QUERY_TIMEOUT",
        partial_results=(
            RuleResultComputation(
                rule_version_id="version-main",
                population_count=50,
                eligible_count=50,
                evaluated_count=50,
                passed_count=45,
                failed_count=5,
                excluded_count=0,
                technical_error_count=0,
                unknown_count=0,
                measurement_status=MeasurementStatus.FAILED,
                completed_partitions=("2026-01", "2026-02"),
            ),
        ),
    )
    notifications = FakeTechnicalEventSink()
    service, repository, version = _service(
        FakeExecutionExecutor([timeout]),
        technical_event_sink=notifications,
    )
    queued = _start(service, version)

    partial = service.run_next()

    assert partial is not None
    assert partial.status is ExecutionStatus.PARTIAL
    assert partial.error_class == "QUERY_TIMEOUT"
    assert partial.attempt_count == 1
    result = repository.list_results(queued.execution_id)[0]
    assert result.completed_partitions == ("2026-01", "2026-02")
    assert result.eligible_for_official_scoring is False
    assert repository.list_attempts(queued.execution_id)[0].status is ExecutionStatus.PARTIAL
    assert notifications.executions == [partial]


def test_fr_040_rule_003_timeout_without_partial_data_has_no_numeric_result() -> None:
    notifications = FakeTechnicalEventSink()
    service, repository, version = _service(
        FakeExecutionExecutor([ExecutionTimeoutError("TOTAL_TIMEOUT")]),
        technical_event_sink=notifications,
    )
    queued = _start(service, version)

    timed_out = service.run_next()

    assert timed_out is not None
    assert timed_out.status is ExecutionStatus.TIMEOUT
    assert timed_out.error_class == "TOTAL_TIMEOUT"
    assert timed_out.attempt_count == 1
    assert repository.list_results(queued.execution_id) == []
    assert notifications.executions == [timed_out]


def test_fr_043_uc_008_unexpected_worker_error_does_not_leave_execution_running() -> None:
    executor = FakeExecutionExecutor([RuntimeError("internal detail must not be persisted")])
    notifications = FakeTechnicalEventSink()
    service, repository, version = _service(
        executor,
        technical_event_sink=notifications,
    )
    queued = _start(service, version)

    failed = service.run_next()

    assert failed is not None
    assert failed.status is ExecutionStatus.TECHNICAL_ERROR
    assert failed.error_class == "UNEXPECTED"
    assert repository.list_attempts(queued.execution_id)[0].error_class == "UNEXPECTED"
    assert "internal detail" not in str(failed)


def test_nfr_rel_002_rejects_total_timeout_shorter_than_query_timeout() -> None:
    executor = FakeExecutionExecutor([(_computation(1, 1, 0),)])

    with pytest.raises(ExecutionValidationError, match="must cover"):
        _service(
            executor,
            timeouts=ExecutionTimeouts(
                connection_seconds=10,
                query_seconds=30,
                total_seconds=20,
            ),
        )


def test_fr_037_uc_007_daily_schedule_persists_and_previews_next_five_runs() -> None:
    now = datetime(2026, 7, 16, 6, 0, tzinfo=timezone.utc)
    execution_service, _, version = _service(FakeExecutionExecutor([(_computation(1, 1, 0),)]))
    repository = SQLiteScheduleRepository()
    scheduler = SchedulingService(
        repository,
        execution_service,
        transactional_audit=_schedule_audit(repository),
        clock=lambda: now,
    )

    schedule, preview = scheduler.create_schedule(
        actor_id="user-1",
        name="Günlük müşteri kontrolü",
        schedule_type="DAILY",
        timezone_name="Europe/Istanbul",
        rule_version_ids=(version.rule_version_id,),
        local_time="10:00",
        correlation_id="correlation-schedule-create",
    )

    assert len(preview) == 5
    assert preview[0] == datetime(2026, 7, 16, 7, 0, tzinfo=timezone.utc)
    assert preview[-1] == datetime(2026, 7, 20, 7, 0, tzinfo=timezone.utc)
    assert repository.get(schedule.schedule_id) == schedule
    audit = _schedule_events(scheduler)[0]
    assert audit.action == "SCHEDULE_CREATED"
    assert audit.correlation_id == "correlation-schedule-create"
    assert audit.new_value_summary["timezone"] == "Europe/Istanbul"
    assert audit.new_value_summary["next_run_count"] == 5
    assert audit.new_value_summary["next_run_at"] == preview[0].isoformat()
    assert "Günlük müşteri kontrolü" not in str(audit.new_value_summary)
    assert scheduler.transactional_audit.list_pending() == []


def test_fr_077_bfr_aud_004_schedule_is_durably_buffered_on_audit_outage() -> None:
    now = datetime(2026, 7, 16, 6, 0, tzinfo=timezone.utc)
    execution_service, _, version = _service(FakeExecutionExecutor([(_computation(1, 1, 0),)]))
    repository = SQLiteScheduleRepository()
    scheduler = SchedulingService(
        repository,
        execution_service,
        transactional_audit=_schedule_audit(repository, FailingScheduleAuditRepository()),
        clock=lambda: now,
    )

    schedule, _ = scheduler.create_schedule(
        actor_id="user-1",
        name="Kesintide korunan plan",
        schedule_type="DAILY",
        timezone_name="Europe/Istanbul",
        rule_version_ids=(version.rule_version_id,),
        local_time="10:00",
        correlation_id="correlation-buffered-schedule",
    )

    pending = scheduler.transactional_audit.list_pending()
    assert repository.get(schedule.schedule_id) == schedule
    assert len(pending) == 1
    assert pending[0].action == "SCHEDULE_CREATED"
    assert pending[0].correlation_id == "correlation-buffered-schedule"
    assert "Kesintide korunan plan" not in str(pending[0].new_value_summary)


def test_bfr_aud_004_outbox_failure_rolls_back_schedule_creation() -> None:
    now = datetime(2026, 7, 16, 6, 0, tzinfo=timezone.utc)
    execution_service, _, version = _service(FakeExecutionExecutor([(_computation(1, 1, 0),)]))
    repository = SQLiteScheduleRepository()
    central_repository = SQLiteAuditRepository()
    scheduler = SchedulingService(
        repository,
        execution_service,
        transactional_audit=FailingScheduleStageAudit(
            repository.connection,
            AuditRedactor(build_default_redaction_policy()),
            central_repository,
            policy_version="AUDIT_OUTBOX_TEST_V1",
        ),
        clock=lambda: now,
    )

    with pytest.raises(sqlite3.OperationalError, match="outbox write failure"):
        scheduler.create_schedule(
            actor_id="user-1",
            name="Atomik plan",
            schedule_type="DAILY",
            timezone_name="Europe/Istanbul",
            rule_version_ids=(version.rule_version_id,),
            local_time="10:00",
        )

    assert repository.list_all() == []
    assert central_repository.list_events() == []


def test_bfr_aud_002_blank_correlation_is_rejected_before_schedule_write() -> None:
    now = datetime(2026, 7, 16, 6, 0, tzinfo=timezone.utc)
    execution_service, _, version = _service(FakeExecutionExecutor([(_computation(1, 1, 0),)]))
    repository = SQLiteScheduleRepository()
    scheduler = SchedulingService(
        repository,
        execution_service,
        transactional_audit=_schedule_audit(repository),
        clock=lambda: now,
    )

    with pytest.raises(ExecutionValidationError, match="correlation_id"):
        scheduler.create_schedule(
            actor_id="user-1",
            name="Correlation olmayan plan",
            schedule_type="DAILY",
            timezone_name="Europe/Istanbul",
            rule_version_ids=(version.rule_version_id,),
            local_time="10:00",
            correlation_id=" ",
        )

    assert repository.list_all() == []


@pytest.mark.parametrize(
    ("schedule_type", "kwargs", "expected_count"),
    [
        (
            "ONCE",
            {"once_at": datetime(2026, 7, 20, 8, 0, tzinfo=timezone.utc)},
            1,
        ),
        ("WEEKLY", {"local_time": "09:00", "day_of_week": 0}, 5),
        ("MONTHLY", {"local_time": "09:00", "day_of_month": 31}, 5),
    ],
)
def test_fr_037_uc_007_supports_once_weekly_and_monthly_schedules(
    schedule_type: str,
    kwargs: dict[str, Any],
    expected_count: int,
) -> None:
    now = datetime(2026, 7, 16, 6, 0, tzinfo=timezone.utc)
    execution_service, _, version = _service(FakeExecutionExecutor([(_computation(1, 1, 0),)]))
    repository = SQLiteScheduleRepository()
    scheduler = SchedulingService(
        repository,
        execution_service,
        transactional_audit=_schedule_audit(repository),
        clock=lambda: now,
    )

    schedule, preview = scheduler.create_schedule(
        actor_id="user-1",
        name=f"Plan {schedule_type}",
        schedule_type=schedule_type,
        timezone_name="Europe/Istanbul",
        rule_version_ids=(version.rule_version_id,),
        **kwargs,
    )

    assert schedule.schedule_type.value == schedule_type
    assert len(preview) == expected_count
    assert all(item.tzinfo is timezone.utc for item in preview)


def test_fr_037_uc_007_due_schedule_creates_one_idempotent_scheduled_execution() -> None:
    created_at = datetime(2026, 7, 16, 6, 0, tzinfo=timezone.utc)
    due_at = datetime(2026, 7, 16, 7, 0, tzinfo=timezone.utc)
    execution_service, execution_repository, version = _service(
        FakeExecutionExecutor([(_computation(1, 1, 0),)])
    )
    schedule_repository = SQLiteScheduleRepository()
    scheduler = SchedulingService(
        schedule_repository,
        execution_service,
        transactional_audit=_schedule_audit(schedule_repository),
        clock=lambda: created_at,
    )
    schedule, _ = scheduler.create_schedule(
        actor_id="user-1",
        name="Zamanı gelen günlük plan",
        schedule_type="DAILY",
        timezone_name="Europe/Istanbul",
        rule_version_ids=(version.rule_version_id,),
        local_time="10:00",
    )

    first = scheduler.trigger_due(now=due_at)
    repeated = scheduler.trigger_due(now=due_at)

    assert len(first) == 1
    assert repeated == ()
    assert first[0].execution_type is ExecutionType.SCHEDULED
    assert first[0].scope["schedule_id"] == schedule.schedule_id
    assert len(execution_repository.list_executions()) == 1
    advanced = schedule_repository.get(schedule.schedule_id)
    assert advanced.next_run_at == datetime(2026, 7, 17, 7, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("schedule_type", "timezone_name", "kwargs"),
    [
        ("DAILY", "Invalid/Zone", {"local_time": "09:00"}),
        ("WEEKLY", "Europe/Istanbul", {"local_time": "09:00", "day_of_week": 7}),
        ("MONTHLY", "Europe/Istanbul", {"local_time": "09:00", "day_of_month": 0}),
        (
            "ONCE",
            "Europe/Istanbul",
            {"once_at": datetime(2026, 7, 15, 8, 0, tzinfo=timezone.utc)},
        ),
        ("CRON", "Europe/Istanbul", {"local_time": "09:00"}),
    ],
)
def test_fr_037_uc_007_rejects_invalid_or_unsupported_schedule_definition(
    schedule_type: str,
    timezone_name: str,
    kwargs: dict[str, Any],
) -> None:
    now = datetime(2026, 7, 16, 6, 0, tzinfo=timezone.utc)
    execution_service, _, version = _service(FakeExecutionExecutor([(_computation(1, 1, 0),)]))
    repository = SQLiteScheduleRepository()
    scheduler = SchedulingService(
        repository,
        execution_service,
        transactional_audit=_schedule_audit(repository),
        clock=lambda: now,
    )

    with pytest.raises(ExecutionValidationError):
        scheduler.create_schedule(
            actor_id="user-1",
            name=f"Geçersiz {schedule_type}",
            schedule_type=schedule_type,
            timezone_name=timezone_name,
            rule_version_ids=(version.rule_version_id,),
            **kwargs,
        )

    assert repository.list_all() == []


def test_fr_037_rule_003_uc_007_rejects_schedule_for_inactive_rule() -> None:
    now = datetime(2026, 7, 16, 6, 0, tzinfo=timezone.utc)
    execution_service, _, version = _service(
        FakeExecutionExecutor([(_computation(1, 1, 0),)]),
        rule_status=RuleStatus.PASSIVE,
    )
    repository = SQLiteScheduleRepository()
    scheduler = SchedulingService(
        repository,
        execution_service,
        transactional_audit=_schedule_audit(repository),
        clock=lambda: now,
    )

    with pytest.raises(ExecutionValidationError, match="active rules"):
        scheduler.create_schedule(
            actor_id="user-1",
            name="Pasif kural planı",
            schedule_type="DAILY",
            timezone_name="Europe/Istanbul",
            rule_version_ids=(version.rule_version_id,),
            local_time="09:00",
        )

    assert repository.list_all() == []


def test_fr_037_rule_003_uc_007_due_plan_is_disabled_if_source_becomes_inactive() -> None:
    created_at = datetime(2026, 7, 16, 6, 0, tzinfo=timezone.utc)
    due_at = datetime(2026, 7, 16, 7, 0, tzinfo=timezone.utc)
    source_catalog = FakeSourceCatalog()
    execution_service, execution_repository, version = _service(
        FakeExecutionExecutor([(_computation(1, 1, 0),)]),
        source_catalog=source_catalog,
    )
    schedule_repository = SQLiteScheduleRepository()
    events = FakeScheduleTechnicalEventSink()
    scheduler = SchedulingService(
        schedule_repository,
        execution_service,
        transactional_audit=_schedule_audit(schedule_repository),
        technical_event_sink=events,
        clock=lambda: created_at,
    )
    schedule, _ = scheduler.create_schedule(
        actor_id="user-1",
        name="Kaynağı pasifleşen plan",
        schedule_type="DAILY",
        timezone_name="Europe/Istanbul",
        rule_version_ids=(version.rule_version_id,),
        local_time="10:00",
    )
    source_catalog.source_status = DataSourceStatus.INACTIVE

    with pytest.raises(ExecutionValidationError, match="active data source"):
        scheduler.create_schedule(
            actor_id="user-2",
            name="Yeni pasif kaynak planı",
            schedule_type="DAILY",
            timezone_name="Europe/Istanbul",
            rule_version_ids=(version.rule_version_id,),
            local_time="11:00",
        )

    executions = scheduler.trigger_due(now=due_at)

    assert executions == ()
    assert execution_repository.list_executions() == []
    assert len(schedule_repository.list_all()) == 1
    disabled = schedule_repository.get(schedule.schedule_id)
    assert disabled.is_active is False
    assert disabled.next_run_at is None
    assert events.events == [(schedule, "INVALID_EXECUTION_SCOPE")]


def test_fr_010_fr_036_uc_008_inactive_source_preserves_running_and_rejects_new_execution() -> None:
    source_catalog = FakeSourceCatalog()
    execution_service, repository, version = _service(
        FakeExecutionExecutor([(_computation(1, 1, 0),)]),
        source_catalog=source_catalog,
    )
    existing = _start(execution_service, version)
    running = repository.claim_next(datetime.now(timezone.utc))
    source_catalog.source_status = DataSourceStatus.INACTIVE

    with pytest.raises(ExecutionValidationError, match="active data source"):
        execution_service.start_manual(
            actor_id="user-2",
            idempotency_key="manual-after-deactivation",
            rule_version_ids=(version.rule_version_id,),
        )

    assert running is not None
    assert running.execution_id == existing.execution_id
    assert repository.get(existing.execution_id).status is ExecutionStatus.RUNNING
    assert len(repository.list_executions()) == 1


def test_fr_037_uc_007_preview_skips_nonexistent_dst_local_time() -> None:
    schedule = Schedule(
        name="DST planı",
        schedule_type=ScheduleType.DAILY,
        timezone_name="Europe/Berlin",
        rule_version_ids=("version-main",),
        created_by="user-1",
        local_time=time(2, 30),
    )

    preview = preview_runs(
        schedule,
        after=datetime(2026, 3, 28, 3, 0, tzinfo=timezone.utc),
        count=2,
    )

    assert preview == (
        datetime(2026, 3, 30, 0, 30, tzinfo=timezone.utc),
        datetime(2026, 3, 31, 0, 30, tzinfo=timezone.utc),
    )


def test_fr_039_uc_008_execution_persists_system_classification_and_source_scope() -> None:
    service, repository, version = _service(
        FakeExecutionExecutor([(_computation(1, 1, 0),)]),
        workload_classifier=StaticWorkloadClassifier(WorkloadClass.HEAVY),
    )

    execution = _start(service, version)
    stored = repository.get(execution.execution_id)

    assert stored.workload_class is WorkloadClass.HEAVY
    assert stored.source_ids == (SOURCE_ID,)


@pytest.mark.parametrize(
    ("workload_class", "allowed"),
    [(WorkloadClass.HEAVY, 2), (WorkloadClass.LIGHT, 4)],
)
def test_fr_039_mvp_default_global_quota_blocks_excess_running_jobs(
    workload_class: WorkloadClass,
    allowed: int,
) -> None:
    repository = SQLiteExecutionRepository()
    policy = ConcurrencyPolicy(default_source_limit=10)
    started_at = datetime(2026, 7, 16, 8, 0, tzinfo=timezone.utc)
    for index in range(allowed + 1):
        repository.create_or_get(
            _queued_execution(
                execution_id=f"execution-{index}",
                workload_class=workload_class,
                source_id=f"source-{index}",
                created_at=started_at + timedelta(seconds=index),
            )
        )

    claimed = [repository.claim_next(started_at, policy) for _ in range(allowed)]
    blocked = repository.claim_next(started_at, policy)

    assert all(item is not None for item in claimed)
    assert blocked is None
    assert (
        sum(item.status is ExecutionStatus.RUNNING for item in repository.list_executions())
        == allowed
    )


def test_fr_039_rule_012_source_quota_skips_blocked_head_and_claims_other_source() -> None:
    repository = SQLiteExecutionRepository()
    policy = ConcurrencyPolicy(
        max_heavy=4,
        max_light=4,
        default_source_limit=1,
    )
    created_at = datetime(2026, 7, 16, 8, 0, tzinfo=timezone.utc)
    for execution in (
        _queued_execution("source-a-first", WorkloadClass.LIGHT, "source-a", created_at),
        _queued_execution(
            "source-a-second",
            WorkloadClass.LIGHT,
            "source-a",
            created_at + timedelta(seconds=1),
        ),
        _queued_execution(
            "source-b-first",
            WorkloadClass.LIGHT,
            "source-b",
            created_at + timedelta(seconds=2),
        ),
    ):
        repository.create_or_get(execution)

    first = repository.claim_next(created_at, policy)
    second = repository.claim_next(created_at, policy)

    assert first is not None and first.execution_id == "source-a-first"
    assert second is not None and second.execution_id == "source-b-first"
    assert repository.get("source-a-second").status is ExecutionStatus.QUEUED


def test_nfr_perf_008_fr_039_same_source_allows_only_one_heavy_job_by_default() -> None:
    repository = SQLiteExecutionRepository()
    policy = ConcurrencyPolicy()
    created_at = datetime(2026, 7, 16, 8, 0, tzinfo=timezone.utc)
    for index in range(2):
        repository.create_or_get(
            _queued_execution(
                f"heavy-source-{index}",
                WorkloadClass.HEAVY,
                "source-a",
                created_at + timedelta(seconds=index),
            )
        )

    first = repository.claim_next(created_at, policy)
    blocked = repository.claim_next(created_at, policy)

    assert first is not None
    assert blocked is None


def test_fr_039_rejects_invalid_concurrency_policy_before_queue_use() -> None:
    with pytest.raises(ExecutionValidationError, match="Concurrency limits"):
        _service(
            FakeExecutionExecutor([(_computation(1, 1, 0),)]),
            concurrency_policy=ConcurrencyPolicy(max_heavy=0),
        )


def test_fr_039_open_003_policy_resolver_blocks_claim_when_global_policy_is_missing() -> None:
    resolver = SQLiteSourceUsagePolicyRepository()
    service, repository, version = _service(
        FakeExecutionExecutor([(_computation(1, 1, 0),)]),
        source_usage_policy_resolver=resolver,
    )
    execution = _start(service, version)

    with pytest.raises(SourceUsagePolicyUnavailableError):
        service.run_next()

    assert repository.get(execution.execution_id).status is ExecutionStatus.QUEUED


def test_fr_039_repository_migrates_existing_execution_queue_columns(tmp_path: Any) -> None:
    database = tmp_path / "old-executions.sqlite"
    connection = sqlite3.connect(database)
    connection.execute(
        """
        CREATE TABLE rule_executions (
            execution_id TEXT PRIMARY KEY,
            execution_type TEXT NOT NULL,
            status TEXT NOT NULL,
            idempotency_key_hash TEXT NOT NULL UNIQUE,
            payload_hash TEXT NOT NULL,
            rule_version_ids TEXT NOT NULL,
            scope TEXT NOT NULL,
            triggered_by TEXT NOT NULL,
            correlation_id TEXT NOT NULL,
            error_class TEXT,
            attempt_count INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            started_at TEXT,
            finished_at TEXT
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE rule_execution_results (
            rule_result_id TEXT PRIMARY KEY,
            execution_id TEXT NOT NULL,
            rule_version_id TEXT NOT NULL,
            checked_count INTEGER NOT NULL,
            passed_count INTEGER NOT NULL,
            failed_count INTEGER NOT NULL,
            not_evaluated_count INTEGER NOT NULL,
            UNIQUE (execution_id, rule_version_id)
        )
        """
    )
    connection.commit()
    connection.close()

    repository = SQLiteExecutionRepository(str(database))
    columns = {
        row["name"]
        for row in repository.connection.execute("PRAGMA table_info(rule_executions)").fetchall()
    }
    result_columns = {
        row["name"]
        for row in repository.connection.execute(
            "PRAGMA table_info(rule_execution_results)"
        ).fetchall()
    }

    assert {
        "source_ids",
        "workload_class",
        "cancel_requested_at",
        "cancel_requested_by",
        "cancel_reason",
        "cancelled_at",
    } <= columns
    assert {
        "population_count",
        "eligible_count",
        "evaluated_count",
        "excluded_count",
        "technical_error_count",
        "unknown_count",
        "measurement_status",
    } <= result_columns
    assert {"checked_count", "not_evaluated_count"}.isdisjoint(result_columns)
    assert {"completed_partitions", "eligible_for_official_scoring"} <= result_columns


def _service(
    executor: FakeExecutionExecutor,
    *,
    rule_status: RuleStatus = RuleStatus.ACTIVE,
    sleeper: Any = lambda _: None,
    technical_event_sink: Any = None,
    timeouts: ExecutionTimeouts | None = None,
    source_catalog: FakeSourceCatalog | None = None,
    concurrency_policy: ConcurrencyPolicy | None = None,
    source_usage_policy_resolver: Any = None,
    workload_classifier: Any = None,
    cancellation_sink: Any = None,
    clock: Any = None,
) -> tuple[ExecutionService, SQLiteExecutionRepository, RuleVersion]:
    rule = QualityRule(
        quality_rule_id="rule-main",
        code="DQ_CUSTOMER_REQUIRED",
        name="Müşteri alanı zorunlu",
        dataset_id=DATASET_ID,
        field_ids=("field-main",),
        primary_dimension=QualityDimension.COMPLETENESS,
        owner_user_id="owner-1",
        status=rule_status,
    )
    version = RuleVersion(
        rule_version_id="version-main",
        quality_rule_id=rule.quality_rule_id,
        version_no=1,
        rule_type=RuleType.REQUIRED,
        definition={"operator": "IS_NOT_NULL", "field_id": "field-main"},
        threshold=90,
        weight=1,
        criticality=RuleCriticality.HIGH,
    )
    repository = SQLiteExecutionRepository()
    service_kwargs: dict[str, Any] = {}
    if clock is not None:
        service_kwargs["clock"] = clock
    service = ExecutionService(
        repository,
        FakeRuleCatalog(rule, version),
        source_catalog or FakeSourceCatalog(),
        executor,
        timeouts=timeouts,
        retry_policy=RetryPolicy(max_attempts=3, base_delay_seconds=1),
        concurrency_policy=concurrency_policy,
        source_usage_policy_resolver=source_usage_policy_resolver,
        workload_classifier=workload_classifier,
        technical_event_sink=technical_event_sink,
        cancellation_sink=cancellation_sink,
        sleeper=sleeper,
        **service_kwargs,
    )
    return service, repository, version


def _active_source_policy(
    *,
    query_timeout_seconds: int = 900,
    retry_count: int = 2,
    retry_delay_seconds: float = 1.5,
) -> SourceUsagePolicy:
    return SourceUsagePolicy(
        policy_id="global-v1",
        policy_version=1,
        status=SourceUsagePolicyStatus.ACTIVE,
        max_concurrent_queries=4,
        max_workers=6,
        query_timeout_seconds=query_timeout_seconds,
        retry_count=retry_count,
        retry_delay_seconds=retry_delay_seconds,
        rate_limit={"limit": 30, "period": "MINUTE"},
        allowed_windows=(
            SourceUsageWindow(
                timezone="Europe/Istanbul",
                weekdays=(1, 2, 3, 4, 5, 6, 7),
                starts_at=time(0),
                ends_at=time(23, 59),
            ),
        ),
        approved_by="checker-1",
        audit_reference="audit-global-v1",
    )


def _start(service: ExecutionService, version: RuleVersion) -> Any:
    return service.start_manual(
        actor_id="user-1",
        idempotency_key="manual-run",
        rule_version_ids=(version.rule_version_id,),
    )


def _computation(checked: int, passed: int, failed: int) -> RuleResultComputation:
    return RuleResultComputation(
        rule_version_id="version-main",
        population_count=checked,
        eligible_count=checked,
        evaluated_count=checked,
        passed_count=passed,
        failed_count=failed,
        excluded_count=0,
        technical_error_count=0,
        unknown_count=0,
        measurement_status=(MeasurementStatus.PASSED if failed == 0 else MeasurementStatus.FAILED),
    )


def _queued_execution(
    execution_id: str,
    workload_class: WorkloadClass,
    source_id: str,
    created_at: datetime,
) -> Any:
    from veri_kalitesi.executions import RuleExecution

    return RuleExecution(
        execution_id=execution_id,
        idempotency_key_hash=f"key-{execution_id}",
        payload_hash=f"payload-{execution_id}",
        rule_version_ids=("version-main",),
        scope={},
        triggered_by="user-1",
        correlation_id=f"correlation-{execution_id}",
        source_ids=(source_id,),
        workload_class=workload_class,
        created_at=created_at,
    )
