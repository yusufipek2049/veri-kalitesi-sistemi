"""Kalıcı iş kuyruğu için opt-in PostgreSQL entegrasyon testleri."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, time, timedelta, timezone
from multiprocessing import get_context
from pathlib import Path
from threading import Barrier
from time import sleep
from typing import Any, cast
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, func, select, text, update
from sqlalchemy.engine import CursorResult

from veri_kalitesi.audit import (
    AuditEventInput,
    AuditRedactor,
    AuditResult,
    PostgreSQLTransactionalAudit,
    build_default_redaction_policy,
)
from veri_kalitesi.identity import ActorContextIssuer, ActorType
from veri_kalitesi.executions import (
    ConcurrencyPolicy,
    ExecutionMode,
    ExecutionNotFoundError,
    PostgreSQLSourceUsagePolicyRepository,
    SourceUsagePolicy,
    SourceUsagePolicyStatus,
    SourceUsageWindow,
)
from veri_kalitesi.executions.source_usage_policies import (
    ResolvedSourceUsagePolicy,
    SourceRuntimePolicy,
)
from veri_kalitesi.executions.postgresql_repository import PostgreSQLExecutionRepository
from veri_kalitesi.api.postgresql_execution import (
    PostgreSQLExecutionCancelService,
    PostgreSQLExecutionStartService,
)
from veri_kalitesi.reporting.models import (
    ReportExportPolicy,
    ReportFormat,
    ReportRequest,
    ReportType,
)
from veri_kalitesi.reporting.repository import PostgreSQLReportRepository
from veri_kalitesi.reporting.service import ReportService
from veri_kalitesi.jobs import (
    BackgroundJob,
    DeadLetterReprocessPolicy,
    DeadLetterReprocessService,
    DeadLetterStatus,
    JobCompletionOutcome,
    JobConcurrencyError,
    JobIdempotencyConflictError,
    JobLeaseError,
    JobLeasePolicy,
    JobFailureKind,
    JobRetryPolicy,
    JobStatus,
    JobValidationError,
    PostgreSQLJobQueueRepository,
    PersistentJobWorker,
    job_tables,
)
from veri_kalitesi.persistence import (
    DEFAULT_SCHEMA_NAME,
    DatabaseSettings,
    SessionFactory,
    create_session_factory,
)

ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_CFG = ROOT / "05-Veritabani" / "alembic.ini"
TEST_URL = os.environ.get("DATA_QUALITY_POSTGRES_TEST_URL")

pytestmark = pytest.mark.skipif(
    not TEST_URL,
    reason="Requires DATA_QUALITY_POSTGRES_TEST_URL pointing to a test PostgreSQL database",
)


@pytest.fixture(scope="module")
def db_settings() -> DatabaseSettings:
    schema = os.environ.get("DATA_QUALITY_DATABASE_SCHEMA", DEFAULT_SCHEMA_NAME)
    return DatabaseSettings.from_url(os.environ["DATA_QUALITY_POSTGRES_TEST_URL"], schema=schema)


@pytest.fixture(scope="module")
def alembic_up_to_date(db_settings: DatabaseSettings) -> None:
    config = _alembic_config(db_settings, db_settings.schema)
    command.upgrade(config, "head")


@pytest.fixture
def session_factory(db_settings: DatabaseSettings, alembic_up_to_date: None) -> SessionFactory:
    engine = create_engine(
        db_settings.url.render_as_string(hide_password=False),
        pool_pre_ping=True,
    )
    with engine.begin() as connection:
        connection.execute(text(f"DELETE FROM {db_settings.schema}.job_dead_letters"))
        connection.execute(text(f"DELETE FROM {db_settings.schema}.background_jobs"))
        connection.execute(text(f"DELETE FROM {db_settings.schema}.source_usage_policies"))
    return create_session_factory(db_settings, engine=engine)


@pytest.fixture
def repository(
    session_factory: SessionFactory, db_settings: DatabaseSettings
) -> PostgreSQLJobQueueRepository:
    return PostgreSQLJobQueueRepository(session_factory, schema=db_settings.schema)


@pytest.fixture
def audit_outbox(
    session_factory: SessionFactory,
    db_settings: DatabaseSettings,
) -> PostgreSQLTransactionalAudit:
    from conftest import FakePreparedAuditRepository  # type: ignore[import-untyped]

    return PostgreSQLTransactionalAudit(
        session_factory,
        AuditRedactor(build_default_redaction_policy()),
        FakePreparedAuditRepository(),
        policy_version="TEST_JOB_POLICY",
        schema=db_settings.schema,
    )


def _at(second: int = 0) -> datetime:
    return datetime(2026, 7, 28, 12, 0, second, tzinfo=timezone.utc)


def _alembic_config(db_settings: DatabaseSettings, schema: str) -> Config:
    config = Config(str(ALEMBIC_CFG))
    config.set_main_option(
        "sqlalchemy.url",
        db_settings.url.render_as_string(hide_password=False),
    )
    config.set_main_option("data_quality_schema", schema)
    return config


def _current_alembic_head(config: Config) -> str:
    head = ScriptDirectory.from_config(config).get_current_head()
    assert head is not None
    return head


def _drop_isolated_schema(db_settings: DatabaseSettings, schema: str) -> None:
    engine = create_engine(
        db_settings.url.render_as_string(hide_password=False),
        pool_pre_ping=True,
    )
    try:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
    finally:
        engine.dispose()


def _job(
    *,
    job_type: str = "EXECUTION",
    payload_ref: str | None = None,
    idempotency_key: str | None = None,
    priority: int = 0,
    available_at: datetime | None = None,
    created_at: datetime | None = None,
    job_id: str | None = None,
    source_ids: tuple[str, ...] = (),
) -> BackgroundJob:
    created = created_at or _at()
    return BackgroundJob(
        job_id=job_id or str(uuid4()),
        job_type=job_type,
        payload={
            "object_ref": payload_ref or str(uuid4()),
            **({"source_ids": source_ids} if source_ids else {}),
        },
        idempotency_key=idempotency_key,
        priority=priority,
        available_at=available_at or created,
        created_at=created,
        updated_at=created,
    )


def _audit_event(
    outbox: PostgreSQLTransactionalAudit,
    job_id: str,
    action: str,
):
    return outbox.prepare(
        AuditEventInput(
            actor_id="test-worker",
            actor_type="SERVICE",
            correlation_id=job_id,
            action=action,
            object_type="BackgroundJob",
            object_id=job_id,
            result=AuditResult.SUCCESS,
            reason_code="TEST_TRANSITION",
            old_values={},
            new_values={},
            occurred_at=_at(),
        )
    )


def test_enqueue_is_persistent_across_repository_and_session_instances(
    repository: PostgreSQLJobQueueRepository,
    session_factory: SessionFactory,
    db_settings: DatabaseSettings,
) -> None:
    job = _job(idempotency_key="persistent-key")
    stored, created = repository.enqueue(job)

    independent_repository = PostgreSQLJobQueueRepository(
        session_factory,
        schema=db_settings.schema,
    )
    retrieved = independent_repository.get_by_id(stored.job_id)
    with session_factory() as session:
        direct_id = session.execute(
            text(f"SELECT job_id FROM {db_settings.schema}.background_jobs WHERE job_id = :job_id"),
            {"job_id": stored.job_id},
        ).scalar_one()

    assert created is True
    assert retrieved is not None
    assert retrieved.job_id == stored.job_id
    assert direct_id == stored.job_id


def test_execution_start_atomically_creates_execution_and_persistent_job(
    repository: PostgreSQLJobQueueRepository,
    audit_outbox: PostgreSQLTransactionalAudit,
    session_factory: SessionFactory,
    db_settings: DatabaseSettings,
) -> None:
    service = PostgreSQLExecutionStartService(
        PostgreSQLExecutionRepository(session_factory, schema=db_settings.schema),
        job_queue=repository,
        transactional_audit=audit_outbox,
        clock=lambda: _at(),
    )

    execution = service.start_manual(
        rule_version_ids=("rule-version-1",),
        source_ids=("source-a",),
        triggered_by="operator-a",
        execution_mode=ExecutionMode.SHADOW,
    )

    job = repository.get_by_idempotency_key("EXECUTION", execution.execution_id)
    assert job is not None
    assert job.job_id == execution.execution_id
    assert job.payload["execution_id"] == execution.execution_id
    assert job.payload["source_ids"] == ("source-a",)
    assert execution.execution_mode is ExecutionMode.SHADOW


def test_execution_start_rolls_back_domain_record_when_enqueue_fails(
    repository: PostgreSQLJobQueueRepository,
    audit_outbox: PostgreSQLTransactionalAudit,
    session_factory: SessionFactory,
    db_settings: DatabaseSettings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    execution_repository = PostgreSQLExecutionRepository(
        session_factory,
        schema=db_settings.schema,
    )
    service = PostgreSQLExecutionStartService(
        execution_repository,
        job_queue=repository,
        transactional_audit=audit_outbox,
        clock=lambda: _at(),
    )
    captured: dict[str, str] = {}

    def fail_enqueue(job, **kwargs):
        captured["execution_id"] = job.job_id
        raise RuntimeError("injected enqueue failure")

    monkeypatch.setattr(repository, "enqueue", fail_enqueue)
    with pytest.raises(RuntimeError, match="injected enqueue failure"):
        service.start_manual(
            rule_version_ids=("rule-version-rollback",),
            source_ids=("source-a",),
            triggered_by="operator-a",
        )

    with pytest.raises(ExecutionNotFoundError):
        execution_repository.get(captured["execution_id"])


def test_execution_cancel_rolls_back_execution_and_audit_when_job_cancel_fails(
    repository: PostgreSQLJobQueueRepository,
    audit_outbox: PostgreSQLTransactionalAudit,
    session_factory: SessionFactory,
    db_settings: DatabaseSettings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    execution_repository = PostgreSQLExecutionRepository(
        session_factory,
        schema=db_settings.schema,
    )
    start_service = PostgreSQLExecutionStartService(
        execution_repository,
        job_queue=repository,
        transactional_audit=audit_outbox,
        clock=lambda: _at(),
    )
    execution = start_service.start_manual(
        rule_version_ids=("rule-version-cancel-rollback",),
        source_ids=("source-a",),
        triggered_by="operator-a",
    )
    job_before = repository.get_by_idempotency_key("EXECUTION", execution.execution_id)
    assert job_before is not None
    pending_before = audit_outbox.list_pending()

    def fail_job_cancel(*args, **kwargs):
        raise RuntimeError("injected job cancellation failure")

    monkeypatch.setattr(repository, "request_cancel", fail_job_cancel)
    service = PostgreSQLExecutionCancelService(
        execution_repository,
        transactional_audit=audit_outbox,
        job_queue=repository,
        clock=lambda: _at(1),
    )

    with pytest.raises(RuntimeError, match="injected job cancellation failure"):
        service.cancel(
            execution.execution_id,
            reason="operator request",
            requested_by="operator-a",
        )

    assert execution_repository.get(execution.execution_id) == execution
    assert (
        repository.get_by_idempotency_key("EXECUTION", execution.execution_id)
        == job_before
    )
    assert audit_outbox.list_pending() == pending_before


def test_report_request_uses_persistent_job_instead_of_inline_worker(
    repository: PostgreSQLJobQueueRepository,
    audit_outbox: PostgreSQLTransactionalAudit,
    session_factory: SessionFactory,
) -> None:
    class _Policy:
        def get_active_policy(self, sensitivity_level):
            return ReportExportPolicy(
                version="TEST_REPORT_POLICY",
                policy_name="test-report",
                sensitivity_level=sensitivity_level,
                max_file_size=1_000_000,
                online_duration_seconds=3600,
                require_justification=False,
                require_maker_checker=False,
                watermark_enabled=False,
                dlp_enabled=False,
                allowed_formats=frozenset({ReportFormat.CSV}),
            )

    class _UnusedAudit:
        def append(self, event):
            raise AssertionError("Production report request must use transactional outbox.")

    service = ReportService(
        PostgreSQLReportRepository(session_factory),
        _Policy(),  # type: ignore[arg-type]
        None,
        _UnusedAudit(),  # type: ignore[arg-type]
        job_queue=repository,
        transactional_audit=audit_outbox,
    )
    context = ActorContextIssuer().issue(
        actor_id="reporter-a",
        actor_type=ActorType.USER,
        authentication_source="TEST_IDP",
        session_id="session-report",
        roles=frozenset({"DATA_STEWARD"}),
        permitted_source_ids=frozenset({"source-a"}),
        permitted_dataset_ids=frozenset(),
        can_view_enterprise=False,
        privileged=False,
        issued_at=_at(),
        expires_at=_at() + timedelta(hours=1),
        policy_version="TEST_REPORT_POLICY",
        correlation_id="report-correlation",
    )

    report = service.request_report(
        ReportRequest(
            report_type=ReportType.SUMMARY,
            format=ReportFormat.CSV,
            parameters={"source_ids": ["source-a"]},
            reason_code="TEST",
        ),
        context,
    )

    job = repository.get_by_idempotency_key("REPORT", report.report_id)
    assert job is not None
    assert job.payload["report_id"] == report.report_id
    assert job.payload["source_ids"] == ("source-a",)


def test_idempotent_enqueue_creates_one_row(
    repository: PostgreSQLJobQueueRepository,
    session_factory: SessionFactory,
    db_settings: DatabaseSettings,
) -> None:
    first = _job(payload_ref="same", idempotency_key="same-key")
    second = _job(payload_ref="same", idempotency_key="same-key")

    stored_first, created_first = repository.enqueue(first)
    stored_second, created_second = repository.enqueue(second)
    table = job_tables(db_settings.schema).background_jobs
    with session_factory() as session:
        count = session.scalar(
            select(func.count())
            .select_from(table)
            .where(
                table.c.job_type == first.job_type,
                table.c.idempotency_key == first.idempotency_key,
            )
        )

    assert created_first is True
    assert created_second is False
    assert stored_second.job_id == stored_first.job_id
    assert count == 1


def test_idempotent_enqueue_rejects_different_payload(
    repository: PostgreSQLJobQueueRepository,
) -> None:
    repository.enqueue(_job(payload_ref="first", idempotency_key="conflict-key"))

    with pytest.raises(JobIdempotencyConflictError, match="different payload"):
        repository.enqueue(_job(payload_ref="second", idempotency_key="conflict-key"))


def test_same_key_is_independent_between_job_types(
    repository: PostgreSQLJobQueueRepository,
    session_factory: SessionFactory,
    db_settings: DatabaseSettings,
) -> None:
    repository.enqueue(_job(job_type="EXECUTION", idempotency_key="shared-key"))
    repository.enqueue(_job(job_type="REPORT", idempotency_key="shared-key"))
    table = job_tables(db_settings.schema).background_jobs

    with session_factory() as session:
        count = session.scalar(
            select(func.count()).select_from(table).where(table.c.idempotency_key == "shared-key")
        )

    assert count == 2


def test_future_job_is_not_claimed(
    repository: PostgreSQLJobQueueRepository,
) -> None:
    job = _job(available_at=_at() + timedelta(hours=1))
    repository.enqueue(job)

    assert repository.claim_next("worker-a", JobLeasePolicy(), now=_at()) is None
    queued = repository.require_by_id(job.job_id)
    assert queued.status is JobStatus.QUEUED


def test_concurrent_workers_claim_exactly_once(
    repository: PostgreSQLJobQueueRepository,
    session_factory: SessionFactory,
    db_settings: DatabaseSettings,
) -> None:
    repository.enqueue(_job())
    barrier = Barrier(2)

    def claim(worker_id: str) -> BackgroundJob | None:
        worker_repository = PostgreSQLJobQueueRepository(
            session_factory,
            schema=db_settings.schema,
        )
        barrier.wait()
        return worker_repository.claim_next(worker_id, JobLeasePolicy(), now=_at())

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(claim, ("worker-a", "worker-b")))

    claimed = [result for result in results if result is not None]
    assert len(claimed) == 1


def test_claim_updates_all_lease_fields_atomically(
    repository: PostgreSQLJobQueueRepository,
) -> None:
    job = _job()
    repository.enqueue(job)

    claimed = repository.claim_next(
        "worker-a",
        JobLeasePolicy(duration=timedelta(seconds=45)),
        now=_at(),
    )

    assert claimed is not None
    assert claimed.status is JobStatus.RUNNING
    assert claimed.claimed_by == "worker-a"
    assert claimed.lease_expires_at == _at() + timedelta(seconds=45)
    assert claimed.last_heartbeat_at == _at()
    assert claimed.attempt_count == 1
    assert claimed.version == 1


def test_non_owner_heartbeat_is_rejected_without_change(
    repository: PostgreSQLJobQueueRepository,
) -> None:
    job = _job()
    repository.enqueue(job)
    claimed = repository.claim_next("worker-a", JobLeasePolicy(), now=_at())
    assert claimed is not None

    with pytest.raises(JobLeaseError):
        repository.heartbeat(
            claimed.job_id,
            "worker-b",
            claimed.version,
            JobLeasePolicy(),
            now=_at(1),
        )

    unchanged = repository.require_by_id(claimed.job_id)
    assert unchanged.last_heartbeat_at == claimed.last_heartbeat_at
    assert unchanged.lease_expires_at == claimed.lease_expires_at
    assert unchanged.version == claimed.version


def test_owner_heartbeat_advances_lease_and_version(
    repository: PostgreSQLJobQueueRepository,
) -> None:
    repository.enqueue(_job())
    claimed = repository.claim_next("worker-a", JobLeasePolicy(), now=_at())
    assert claimed is not None

    heartbeat = repository.heartbeat(
        claimed.job_id,
        "worker-a",
        claimed.version,
        JobLeasePolicy(duration=timedelta(minutes=8)),
        now=_at(2),
    )

    assert claimed.last_heartbeat_at is not None
    assert claimed.lease_expires_at is not None
    assert heartbeat.last_heartbeat_at is not None
    assert heartbeat.lease_expires_at is not None
    assert heartbeat.last_heartbeat_at > claimed.last_heartbeat_at
    assert heartbeat.lease_expires_at > claimed.lease_expires_at
    assert heartbeat.version == claimed.version + 1


def test_active_lease_cannot_be_claimed_by_second_worker(
    repository: PostgreSQLJobQueueRepository,
) -> None:
    repository.enqueue(_job())
    assert repository.claim_next("worker-a", JobLeasePolicy(), now=_at()) is not None

    assert repository.claim_next("worker-b", JobLeasePolicy(), now=_at(1)) is None


def test_policy_worker_quota_blocks_additional_claim(
    repository: PostgreSQLJobQueueRepository,
) -> None:
    repository.enqueue(_job())
    repository.enqueue(_job())
    assert (
        repository.claim_next(
            "worker-a",
            JobLeasePolicy(),
            now=_at(),
            max_running=1,
        )
        is not None
    )
    assert (
        repository.claim_next(
            "worker-b",
            JobLeasePolicy(),
            now=_at(1),
            max_running=1,
        )
        is None
    )


def test_concurrent_same_source_claim_respects_atomic_source_quota(
    repository: PostgreSQLJobQueueRepository,
    session_factory: SessionFactory,
    db_settings: DatabaseSettings,
) -> None:
    repository.enqueue(_job(source_ids=("source-a",)))
    repository.enqueue(_job(source_ids=("source-a",)))
    barrier = Barrier(2)

    def claim(worker_id: str) -> BackgroundJob | None:
        worker_repository = PostgreSQLJobQueueRepository(
            session_factory,
            schema=db_settings.schema,
        )
        barrier.wait()
        return worker_repository.claim_next(
            worker_id,
            JobLeasePolicy(),
            now=_at(),
            max_running=2,
            source_limits={"source-a": 1},
            default_source_limit=2,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(claim, ("worker-a", "worker-b")))

    assert len([result for result in results if result is not None]) == 1


def test_worker_heartbeats_beyond_lease_and_prevents_duplicate_reclaim(
    repository: PostgreSQLJobQueueRepository,
    audit_outbox: PostgreSQLTransactionalAudit,
) -> None:
    now = datetime.now(timezone.utc)
    repository.enqueue(
        BackgroundJob(
            job_type="EXECUTION",
            payload={"source_ids": ["source-a"]},
            available_at=now,
            created_at=now,
            updated_at=now,
        )
    )
    process_context = get_context("fork")
    started = process_context.Event()
    finish = process_context.Event()

    class Resolver:
        def resolve_policy(self, *, at: datetime) -> ResolvedSourceUsagePolicy:
            return ResolvedSourceUsagePolicy(
                concurrency_policy=ConcurrencyPolicy(
                    max_total=2,
                    default_source_limit=2,
                ),
                default_runtime_policy=SourceRuntimePolicy(
                    connection_timeout_seconds=1,
                    query_timeout_seconds=2,
                    total_job_timeout_seconds=3,
                    retry_count=0,
                    retry_delay_seconds=0,
                ),
                per_source_runtime_policies={},
            )

    def handler(job, *, cancellation_event, **timeouts):
        started.set()
        assert finish.wait(timeout=2)
        assert not cancellation_event.is_set()
        return JobCompletionOutcome.SUCCESS

    worker = PersistentJobWorker(
        repository=repository,
        policy_resolver=Resolver(),
        handlers={"EXECUTION": handler},
        transactional_audit=audit_outbox,
        worker_id="worker-a",
        lease_policy=JobLeasePolicy(duration=timedelta(milliseconds=120)),
    )
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(worker.run_once)
        assert started.wait(timeout=1)
        sleep(0.2)
        duplicate = repository.claim_next(
            "worker-b",
            JobLeasePolicy(duration=timedelta(milliseconds=120)),
            now=datetime.now(timezone.utc),
            max_running=2,
            source_limits={"source-a": 2},
            default_source_limit=2,
        )
        finish.set()
        completed = future.result(timeout=2)

    assert duplicate is None
    assert completed is not None
    assert completed.status is JobStatus.SUCCESS
    assert completed.last_heartbeat_at is None


def test_source_policy_persists_separate_connection_query_and_total_deadlines(
    session_factory: SessionFactory,
    db_settings: DatabaseSettings,
) -> None:
    policy_repository = PostgreSQLSourceUsagePolicyRepository(
        session_factory,
        schema=db_settings.schema,
    )
    policy_repository.save(
        SourceUsagePolicy(
            policy_id=str(uuid4()),
            policy_version=1,
            status=SourceUsagePolicyStatus.ACTIVE,
            max_concurrent_queries=2,
            max_workers=2,
            connection_timeout_seconds=7,
            query_timeout_seconds=11,
            total_job_timeout_seconds=19,
            retry_count=1,
            retry_delay_seconds=1,
            rate_limit={"limit": 10, "period": "MINUTE"},
            allowed_windows=(
                SourceUsageWindow(
                    timezone="UTC",
                    weekdays=(1, 2, 3, 4, 5, 6, 7),
                    starts_at=time(0),
                    ends_at=time(23, 59),
                ),
            ),
            approved_by="checker-a",
            audit_reference="audit-source-policy-a",
        )
    )

    runtime = policy_repository.resolve_policy(
        at=datetime.now(timezone.utc)
    ).default_runtime_policy

    assert runtime.connection_timeout_seconds == 7
    assert runtime.query_timeout_seconds == 11
    assert runtime.total_job_timeout_seconds == 19


def test_expired_lease_can_be_reclaimed(
    repository: PostgreSQLJobQueueRepository,
) -> None:
    repository.enqueue(_job())
    first = repository.claim_next(
        "worker-a",
        JobLeasePolicy(duration=timedelta(seconds=1)),
        now=_at(),
    )
    assert first is not None

    second = repository.claim_next("worker-b", JobLeasePolicy(), now=_at(2))

    assert second is not None
    assert first.lease_expires_at is not None
    assert second.lease_expires_at is not None
    assert second.job_id == first.job_id
    assert second.claimed_by == "worker-b"
    assert second.lease_expires_at > first.lease_expires_at
    assert second.attempt_count == 2
    assert second.version == 2


def test_stale_version_raises_concurrency_error(
    repository: PostgreSQLJobQueueRepository,
) -> None:
    repository.enqueue(_job())
    claimed = repository.claim_next("worker-a", JobLeasePolicy(), now=_at())
    assert claimed is not None

    with pytest.raises(JobConcurrencyError, match="version conflict"):
        repository.renew_lease(
            claimed.job_id,
            "worker-a",
            claimed.version - 1,
            JobLeasePolicy(),
            now=_at(1),
        )


def test_release_expired_claim_returns_job_to_queue(
    repository: PostgreSQLJobQueueRepository,
) -> None:
    repository.enqueue(_job())
    claimed = repository.claim_next(
        "worker-a",
        JobLeasePolicy(duration=timedelta(seconds=1)),
        now=_at(),
    )
    assert claimed is not None

    released = repository.release_expired_claims(now=_at(2), job_id=claimed.job_id)
    queued = repository.require_by_id(claimed.job_id)

    assert released == 1
    assert queued.status is JobStatus.QUEUED
    assert queued.claimed_by is None
    assert queued.lease_expires_at is None
    assert queued.version == claimed.version + 1


def test_completion_releases_lease_and_preserves_quality_outcome_separately(
    repository: PostgreSQLJobQueueRepository,
    audit_outbox: PostgreSQLTransactionalAudit,
) -> None:
    job = _job()
    repository.enqueue(job)
    claimed = repository.claim_next("worker-a", JobLeasePolicy(), now=_at())
    assert claimed is not None

    completed = repository.complete(
        claimed.job_id,
        "worker-a",
        claimed.version,
        JobCompletionOutcome.QUALITY_FAILURE,
        now=_at(1),
        audit_event=_audit_event(audit_outbox, claimed.job_id, "JOB_COMPLETED"),
        audit_outbox=audit_outbox,
    )

    assert completed.status is JobStatus.SUCCESS
    assert completed.completion_outcome is JobCompletionOutcome.QUALITY_FAILURE
    assert completed.claimed_by is None
    assert completed.lease_expires_at is None
    assert completed.completed_at == _at(1)


def test_terminal_transition_without_transactional_audit_is_rejected_atomically(
    repository: PostgreSQLJobQueueRepository,
) -> None:
    repository.enqueue(_job())
    claimed = repository.claim_next("worker-a", JobLeasePolicy(), now=_at())
    assert claimed is not None

    with pytest.raises(JobValidationError, match="transactional audit"):
        repository.complete(
            claimed.job_id,
            "worker-a",
            claimed.version,
            JobCompletionOutcome.SUCCESS,
            now=_at(1),
        )

    current = repository.require_by_id(claimed.job_id)
    assert current.status is JobStatus.RUNNING
    assert current.version == claimed.version


def test_retry_exhaustion_creates_dead_letter(
    repository: PostgreSQLJobQueueRepository,
    audit_outbox: PostgreSQLTransactionalAudit,
) -> None:
    repository.enqueue(_job())
    claimed = repository.claim_next("worker-a", JobLeasePolicy(), now=_at())
    assert claimed is not None

    queued = repository.record_failure(
        claimed.job_id,
        "worker-a",
        claimed.version,
        error_class="TRANSIENT_NETWORK",
        kind=JobFailureKind.RETRYABLE_TECHNICAL,
        retry_policy=JobRetryPolicy(retry_count=1, retry_delay_seconds=2),
        now=_at(1),
    )
    assert queued.status is JobStatus.QUEUED
    assert queued.available_at == _at(3)
    assert repository.list_dead_letters() == ()

    reclaimed = repository.claim_next("worker-b", JobLeasePolicy(), now=_at(3))
    assert reclaimed is not None
    failed = repository.record_failure(
        reclaimed.job_id,
        "worker-b",
        reclaimed.version,
        error_class="TRANSIENT_NETWORK",
        kind=JobFailureKind.RETRYABLE_TECHNICAL,
        retry_policy=JobRetryPolicy(retry_count=1, retry_delay_seconds=2),
        now=_at(4),
        audit_event=_audit_event(audit_outbox, reclaimed.job_id, "JOB_FAILED"),
        audit_outbox=audit_outbox,
    )
    letters = repository.list_dead_letters()

    assert failed.status is JobStatus.TECHNICAL_ERROR
    assert len(letters) == 1
    assert letters[0].job_id == failed.job_id
    assert letters[0].status is DeadLetterStatus.OPEN
    assert letters[0].attempt_count == 2


def test_queued_and_running_cancellation_close_persistently(
    repository: PostgreSQLJobQueueRepository,
    audit_outbox: PostgreSQLTransactionalAudit,
) -> None:
    queued_job = _job()
    repository.enqueue(queued_job)
    cancelled = repository.request_cancel(
        queued_job.job_id,
        queued_job.version,
        requested_by="operator-a",
        reason_code="USER_REQUEST",
        now=_at(1),
        audit_event=_audit_event(audit_outbox, queued_job.job_id, "JOB_CANCELLED"),
        audit_outbox=audit_outbox,
    )
    assert cancelled.status is JobStatus.CANCELLED
    assert cancelled.completed_at == _at(1)

    running_job = _job()
    repository.enqueue(running_job)
    claimed = repository.claim_next("worker-a", JobLeasePolicy(), now=_at(2))
    assert claimed is not None
    requested = repository.request_cancel(
        claimed.job_id,
        claimed.version,
        requested_by="operator-a",
        reason_code="USER_REQUEST",
        now=_at(3),
        audit_event=_audit_event(audit_outbox, claimed.job_id, "JOB_CANCEL_REQUESTED"),
        audit_outbox=audit_outbox,
    )
    assert requested.status is JobStatus.CANCEL_REQUESTED
    closed = repository.complete_cancelled(
        requested.job_id,
        "worker-a",
        requested.version,
        now=_at(4),
        audit_event=_audit_event(audit_outbox, requested.job_id, "JOB_CANCELLED"),
        audit_outbox=audit_outbox,
    )
    assert closed.status is JobStatus.CANCELLED
    assert closed.claimed_by is None


def test_expired_cancel_request_closes_instead_of_requeueing(
    repository: PostgreSQLJobQueueRepository,
    audit_outbox: PostgreSQLTransactionalAudit,
) -> None:
    repository.enqueue(_job())
    claimed = repository.claim_next(
        "worker-a",
        JobLeasePolicy(duration=timedelta(seconds=1)),
        now=_at(),
    )
    assert claimed is not None
    requested = repository.request_cancel(
        claimed.job_id,
        claimed.version,
        requested_by="operator-a",
        reason_code="USER_REQUEST",
        now=_at(1),
        audit_event=_audit_event(audit_outbox, claimed.job_id, "JOB_CANCEL_REQUESTED"),
        audit_outbox=audit_outbox,
    )

    assert repository.release_expired_claims(
        now=_at(2),
        job_id=requested.job_id,
        audit_outbox=audit_outbox,
    ) == 1
    closed = repository.require_by_id(requested.job_id)
    assert closed.status is JobStatus.CANCELLED
    assert closed.completed_at == _at(2)


def test_lease_expiry_cancel_without_audit_rolls_back(
    repository: PostgreSQLJobQueueRepository,
    audit_outbox: PostgreSQLTransactionalAudit,
) -> None:
    repository.enqueue(_job())
    claimed = repository.claim_next(
        "worker-a",
        JobLeasePolicy(duration=timedelta(seconds=1)),
        now=_at(),
    )
    assert claimed is not None
    requested = repository.request_cancel(
        claimed.job_id,
        claimed.version,
        requested_by="operator-a",
        reason_code="USER_REQUEST",
        now=_at(1),
        audit_event=_audit_event(audit_outbox, claimed.job_id, "JOB_CANCEL_REQUESTED"),
        audit_outbox=audit_outbox,
    )

    with pytest.raises(JobValidationError, match="transactional audit"):
        repository.release_expired_claims(now=_at(2), job_id=requested.job_id)

    current = repository.require_by_id(requested.job_id)
    assert current.status is JobStatus.CANCEL_REQUESTED


def test_authorized_dead_letter_reprocess_is_atomic_and_audited(
    repository: PostgreSQLJobQueueRepository,
    audit_outbox: PostgreSQLTransactionalAudit,
) -> None:
    repository.enqueue(_job())
    claimed = repository.claim_next("worker-a", JobLeasePolicy(), now=_at())
    assert claimed is not None
    repository.record_failure(
        claimed.job_id,
        "worker-a",
        claimed.version,
        error_class="TRANSIENT_NETWORK",
        kind=JobFailureKind.RETRYABLE_TECHNICAL,
        retry_policy=JobRetryPolicy(retry_count=0, retry_delay_seconds=1),
        now=_at(1),
        audit_event=_audit_event(audit_outbox, claimed.job_id, "JOB_FAILED"),
        audit_outbox=audit_outbox,
    )
    letter = repository.list_dead_letters()[0]
    context = ActorContextIssuer().issue(
        actor_id="operator-a",
        actor_type=ActorType.USER,
        authentication_source="TEST_IDP",
        session_id="session-a",
        roles=frozenset({"TEST_REPROCESS_ROLE"}),
        permitted_source_ids=frozenset(),
        permitted_dataset_ids=frozenset(),
        can_view_enterprise=False,
        privileged=False,
        issued_at=_at(),
        expires_at=_at() + timedelta(hours=1),
        policy_version="TEST_JOB_POLICY",
        correlation_id="correlation-a",
    )
    service = DeadLetterReprocessService(
        repository,
        audit_outbox,
        DeadLetterReprocessPolicy(
            version="TEST_JOB_POLICY",
            allowed_roles=frozenset({"TEST_REPROCESS_ROLE"}),
        ),
    )

    requeued = service.reprocess(letter.dead_letter_id, context, now=_at(2))

    assert requeued.status is JobStatus.QUEUED
    assert repository.list_dead_letters() == ()
    reprocessed = repository.list_dead_letters(status=DeadLetterStatus.REPROCESSED)
    assert len(reprocessed) == 1
    assert reprocessed[0].reprocessed_by == "operator-a"
    assert reprocessed[0].audit_event_id is not None
    assert audit_outbox.list_pending()[-1].action == "JOB_DEAD_LETTER_REPROCESSED"


def test_claim_order_is_priority_then_times_then_id(
    repository: PostgreSQLJobQueueRepository,
) -> None:
    jobs = [
        _job(job_id="00000000-0000-0000-0000-000000000004", priority=1, created_at=_at(2)),
        _job(job_id="00000000-0000-0000-0000-000000000003", priority=2, created_at=_at(2)),
        _job(job_id="00000000-0000-0000-0000-000000000002", priority=2, created_at=_at(1)),
        _job(job_id="00000000-0000-0000-0000-000000000001", priority=2, created_at=_at(1)),
    ]
    for job in jobs:
        repository.enqueue(job)

    claimed_ids = []
    for worker_number in range(len(jobs)):
        claimed = repository.claim_next(
            f"worker-{worker_number}",
            JobLeasePolicy(),
            now=_at(3),
        )
        assert claimed is not None
        claimed_ids.append(claimed.job_id)

    assert claimed_ids == [
        "00000000-0000-0000-0000-000000000001",
        "00000000-0000-0000-0000-000000000002",
        "00000000-0000-0000-0000-000000000003",
        "00000000-0000-0000-0000-000000000004",
    ]


def test_migration_from_empty_schema_reaches_head(db_settings: DatabaseSettings) -> None:
    schema = f"dq_job_fresh_{uuid4().hex}"
    config = _alembic_config(db_settings, schema)
    expected_head = _current_alembic_head(config)
    engine = create_engine(
        db_settings.url.render_as_string(hide_password=False),
        pool_pre_ping=True,
    )
    try:
        with engine.connect() as connection:
            assert (
                connection.execute(
                    text("SELECT to_regnamespace(:schema)"),
                    {"schema": schema},
                ).scalar_one_or_none()
                is None
            )

        command.upgrade(config, "head")

        with engine.connect() as connection:
            revision = connection.execute(
                text(f'SELECT version_num FROM "{schema}".alembic_version')
            ).scalar_one()
            columns = {
                row[0]
                for row in connection.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_schema = :schema AND table_name = 'background_jobs'"
                    ),
                    {"schema": schema},
                )
            }

        assert revision == expected_head
        assert {
            "job_id",
            "job_type",
            "payload",
            "status",
            "priority",
            "available_at",
            "claimed_by",
            "lease_expires_at",
            "version",
        }.issubset(columns)
    finally:
        engine.dispose()
        _drop_isolated_schema(db_settings, schema)


def test_migration_upgrades_explicit_previous_head(db_settings: DatabaseSettings) -> None:
    schema = f"dq_job_upgrade_{uuid4().hex}"
    config = _alembic_config(db_settings, schema)
    expected_head = _current_alembic_head(config)
    engine = create_engine(
        db_settings.url.render_as_string(hide_password=False),
        pool_pre_ping=True,
    )
    try:
        command.upgrade(config, "20260724_07")
        with engine.connect() as connection:
            previous_revision = connection.execute(
                text(f'SELECT version_num FROM "{schema}".alembic_version')
            ).scalar_one()
            job_table_count = connection.execute(
                text(
                    "SELECT count(*) FROM information_schema.tables "
                    "WHERE table_schema = :schema AND table_name = 'background_jobs'"
                ),
                {"schema": schema},
            ).scalar_one()

        assert previous_revision == "20260724_07"
        assert job_table_count == 0

        command.upgrade(config, "head")

        with engine.connect() as connection:
            current_revision = connection.execute(
                text(f'SELECT version_num FROM "{schema}".alembic_version')
            ).scalar_one()
            job_table_count = connection.execute(
                text(
                    "SELECT count(*) FROM information_schema.tables "
                    "WHERE table_schema = :schema AND table_name = 'background_jobs'"
                ),
                {"schema": schema},
            ).scalar_one()

        assert current_revision == expected_head
        assert job_table_count == 1
    finally:
        engine.dispose()
        _drop_isolated_schema(db_settings, schema)


def test_conditional_heartbeat_update_affects_zero_rows_for_stale_version(
    repository: PostgreSQLJobQueueRepository,
    session_factory: SessionFactory,
) -> None:
    repository.enqueue(_job())
    claimed = repository.claim_next("worker-a", JobLeasePolicy(), now=_at())
    assert claimed is not None
    table = job_tables().background_jobs

    with session_factory.begin() as session:
        result = session.execute(
            update(table)
            .where(
                table.c.job_id == claimed.job_id,
                table.c.version == claimed.version - 1,
            )
            .values(last_heartbeat_at=_at(1))
        )

    assert cast(CursorResult[Any], result).rowcount == 0
