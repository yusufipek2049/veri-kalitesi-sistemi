"""PostgreSQLExecutionRepository icin PostgreSQL entegrasyon testleri.

Iteration 36E — Execution PostgreSQL migration.
PostgreSQL gerektiren testler DATA_QUALITY_POSTGRES_TEST_URL ortam degiskeni
olmadan atlanir. Issues/postgresql_repository.py sablonunu izler.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text

from alembic import command
from alembic.config import Config

from veri_kalitesi.audit import (
    AuditRedactor,
    PostgreSQLTransactionalAudit,
    PreparedAuditEvent,
    build_default_redaction_policy,
)
from veri_kalitesi.audit.models import AuditEventInput, AuditResult
from veri_kalitesi.audit.outbox import PreparedAuditRepository
from veri_kalitesi.executions.models import (
    ConcurrencyPolicy,
    ExecutionAttempt,
    ExecutionStatus,
    ExecutionType,
    RuleExecution,
    RuleExecutionResult,
    WorkloadClass,
)
from veri_kalitesi.executions.postgresql_repository import (
    PostgreSQLExecutionRepository,
)
from veri_kalitesi.persistence import (
    DatabaseSettings,
    DEFAULT_SCHEMA_NAME,
    create_session_factory,
)

ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_CFG = ROOT / "05-Veritabani" / "alembic.ini"

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATA_QUALITY_POSTGRES_TEST_URL"),
    reason="Requires DATA_QUALITY_POSTGRES_TEST_URL pointing to a test PostgreSQL database",
)


@pytest.fixture(scope="module")
def db_settings() -> DatabaseSettings:
    raw_url = os.environ["DATA_QUALITY_POSTGRES_TEST_URL"]
    schema = os.environ.get("DATA_QUALITY_DATABASE_SCHEMA", DEFAULT_SCHEMA_NAME)
    return DatabaseSettings.from_url(raw_url, schema=schema)


@pytest.fixture(scope="module")
def alembic_up_to_date(db_settings: DatabaseSettings) -> None:
    """Tum migration'lari calistir."""
    config = Config(str(ALEMBIC_CFG))
    config.set_main_option("sqlalchemy.url", db_settings.url.render_as_string(hide_password=False))
    config.set_main_option("data_quality_schema", db_settings.schema)
    command.upgrade(config, "head")


@pytest.fixture
def session_factory(db_settings: DatabaseSettings, alembic_up_to_date: None) -> type:
    """Her test icin yeni bir session factory. Tablo yapisi korunur."""
    engine = create_engine(
        db_settings.url.render_as_string(hide_password=False),
        pool_pre_ping=True,
    )
    # Clean all tables before each test
    with engine.begin() as conn:
        for table_name in [
            "rule_execution_results",
            "execution_attempts",
            "rule_executions",
        ]:
            conn.execute(text(f"DELETE FROM {db_settings.schema}.{table_name}"))
    factory = create_session_factory(db_settings, engine=engine)
    return factory


@pytest.fixture
def repository(session_factory: type) -> PostgreSQLExecutionRepository:
    return PostgreSQLExecutionRepository(session_factory)


@pytest.fixture
def audit_outbox(session_factory: type) -> PostgreSQLTransactionalAudit:
    redactor = AuditRedactor(build_default_redaction_policy())
    repo = PreparedAuditRepository(session_factory)
    return PostgreSQLTransactionalAudit(
        session_factory=session_factory,
        redactor=redactor,
        repository=repo,
        policy_version="TEST_V1",
    )


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _sample_execution(
    *,
    rule_version_ids: tuple[str, ...] | None = None,
    source_ids: tuple[str, ...] | None = None,
    **kwargs: object,
) -> RuleExecution:
    return RuleExecution(
        idempotency_key_hash=str(uuid4()),
        payload_hash=str(uuid4()),
        rule_version_ids=rule_version_ids or ("rv-001", "rv-002"),
        scope={"dataset": "ds-001"},
        triggered_by="test-actor",
        correlation_id=str(uuid4()),
        source_ids=source_ids or ("src-001",),
        created_at=_now(),
        **kwargs,  # type: ignore[arg-type]
    )


def _prepare_event(
    audit_outbox: PostgreSQLTransactionalAudit, action: str = "EXECUTION_TEST"
) -> PreparedAuditEvent:
    event = AuditEventInput(
        actor_id="test-actor",
        correlation_id=str(uuid4()),
        action=action,
        object_type="RuleExecution",
        object_id=str(uuid4()),
        result=AuditResult.SUCCESS,
        reason_code="TEST",
        old_values={},
        new_values={"test": True},
        occurred_at=datetime.now(timezone.utc),
    )
    return audit_outbox.prepare(event)


def test_create_and_get_execution(
    repository: PostgreSQLExecutionRepository,
    audit_outbox: PostgreSQLTransactionalAudit,
) -> None:
    """FR-036: Execution olusturma ve okuma."""
    execution = _sample_execution()
    prepared = _prepare_event(audit_outbox, "EXECUTION_CREATED")

    stored, created = repository.create_or_get(
        execution, audit_event=prepared, audit_outbox=audit_outbox
    )
    assert created is True
    assert stored.execution_id == execution.execution_id
    assert stored.status is ExecutionStatus.QUEUED

    retrieved = repository.get(execution.execution_id)
    assert retrieved.execution_id == execution.execution_id
    assert retrieved.execution_type is ExecutionType.MANUAL
    assert retrieved.rule_version_ids == execution.rule_version_ids
    assert retrieved.source_ids == execution.source_ids
    assert retrieved.workload_class is WorkloadClass.LIGHT


def test_idempotency_same_payload(
    repository: PostgreSQLExecutionRepository,
    audit_outbox: PostgreSQLTransactionalAudit,
) -> None:
    """FR-045: Ayni idempotency key ayni payload ile mevcut execution'u dondurur."""
    execution = _sample_execution()
    prepared = _prepare_event(audit_outbox, "EXECUTION_CREATED")

    stored1, created1 = repository.create_or_get(
        execution, audit_event=prepared, audit_outbox=audit_outbox
    )
    assert created1 is True

    stored2, created2 = repository.create_or_get(
        execution, audit_event=prepared, audit_outbox=audit_outbox
    )
    assert created2 is False
    assert stored2.execution_id == stored1.execution_id


def test_idempotency_different_payload_raises_conflict(
    repository: PostgreSQLExecutionRepository,
    audit_outbox: PostgreSQLTransactionalAudit,
) -> None:
    """FR-045: Ayni key farkli payload conflict hatasi verir."""
    execution = _sample_execution()
    prepared = _prepare_event(audit_outbox, "EXECUTION_CREATED")
    repository.create_or_get(execution, audit_event=prepared, audit_outbox=audit_outbox)

    # Same idempotency key, different payload
    conflict = RuleExecution(
        idempotency_key_hash=execution.idempotency_key_hash,
        payload_hash="different-payload-hash",
        rule_version_ids=("rv-003",),
        scope={"dataset": "ds-002"},
        triggered_by="test-actor",
        correlation_id=str(uuid4()),
        source_ids=("src-002",),
        created_at=_now(),
    )
    from veri_kalitesi.executions.errors import IdempotencyConflictError

    with pytest.raises(IdempotencyConflictError, match="different payload"):
        repository.create_or_get(conflict)


def test_claim_next_returns_queued_execution(
    repository: PostgreSQLExecutionRepository,
    audit_outbox: PostgreSQLTransactionalAudit,
) -> None:
    """FR-043: claim_next QUEUED execution'u RUNNING yapar."""
    execution = _sample_execution()
    prepared = _prepare_event(audit_outbox, "EXECUTION_CREATED")
    repository.create_or_get(execution, audit_event=prepared, audit_outbox=audit_outbox)

    claimed = repository.claim_next(_now())
    assert claimed is not None
    assert claimed.execution_id == execution.execution_id
    assert claimed.status is ExecutionStatus.RUNNING

    # Second claim should return None
    assert repository.claim_next(_now()) is None


def test_complete_success(
    repository: PostgreSQLExecutionRepository,
    audit_outbox: PostgreSQLTransactionalAudit,
) -> None:
    """FR-043: Basarili execution SUCCESS durumuna gecer."""
    execution = _sample_execution()
    created_prepared = _prepare_event(audit_outbox, "EXECUTION_CREATED")
    repository.create_or_get(execution, audit_event=created_prepared, audit_outbox=audit_outbox)
    repository.claim_next(_now())

    now = _now()
    results = (
        RuleExecutionResult(
            execution_id=execution.execution_id,
            rule_version_id="rv-001",
            population_count=100,
            eligible_count=90,
            evaluated_count=90,
            passed_count=80,
            failed_count=10,
            excluded_count=10,
            technical_error_count=0,
            unknown_count=0,
            measurement_status=None,
            completed_partitions=(),
            eligible_for_official_scoring=True,
        ),
    )
    success_prepared = _prepare_event(audit_outbox, "EXECUTION_SUCCEEDED")
    completed = repository.complete_success(
        execution.execution_id, results, now,
        audit_event=success_prepared, audit_outbox=audit_outbox,
    )
    assert completed.status is ExecutionStatus.SUCCESS
    assert completed.finished_at is not None

    # Check results
    stored_results = repository.list_results(execution.execution_id)
    assert len(stored_results) == 1
    assert stored_results[0].passed_count == 80


def test_complete_technical_error(
    repository: PostgreSQLExecutionRepository,
    audit_outbox: PostgreSQLTransactionalAudit,
) -> None:
    """FR-041: Teknik hata TECHNICAL_ERROR durumuna gecer."""
    execution = _sample_execution()
    created_prepared = _prepare_event(audit_outbox, "EXECUTION_CREATED")
    repository.create_or_get(execution, audit_event=created_prepared, audit_outbox=audit_outbox)
    repository.claim_next(_now())

    now = _now()
    error_prepared = _prepare_event(audit_outbox, "EXECUTION_TECHNICAL_ERROR")
    failed = repository.complete_technical_error(
        execution.execution_id, "CONNECTION_TIMEOUT", now,
        audit_event=error_prepared, audit_outbox=audit_outbox,
    )
    assert failed.status is ExecutionStatus.TECHNICAL_ERROR
    assert failed.error_class == "CONNECTION_TIMEOUT"


def test_cancel_queued_execution(
    repository: PostgreSQLExecutionRepository,
    audit_outbox: PostgreSQLTransactionalAudit,
) -> None:
    """FR-042: QUEUED execution iptal edilebilir."""
    execution = _sample_execution()
    prepared = _prepare_event(audit_outbox, "EXECUTION_CREATED")
    repository.create_or_get(execution, audit_event=prepared, audit_outbox=audit_outbox)

    cancel_prepared = _prepare_event(audit_outbox, "EXECUTION_CANCELLED")
    cancelled = repository.request_cancel(
        execution.execution_id,
        actor_id="test-actor",
        reason="Test cancellation",
        requested_at=_now(),
        audit_event=cancel_prepared,
        audit_outbox=audit_outbox,
    )
    assert cancelled.status is ExecutionStatus.CANCELLED
    assert cancelled.cancel_reason == "Test cancellation"


def test_cancel_running_execution(
    repository: PostgreSQLExecutionRepository,
    audit_outbox: PostgreSQLTransactionalAudit,
) -> None:
    """FR-042: RUNNING execution CANCEL_REQUESTED durumuna gecer."""
    execution = _sample_execution()
    prepared = _prepare_event(audit_outbox, "EXECUTION_CREATED")
    repository.create_or_get(execution, audit_event=prepared, audit_outbox=audit_outbox)
    repository.claim_next(_now())

    cancel_prepared = _prepare_event(audit_outbox, "EXECUTION_CANCEL_REQUESTED")
    requested = repository.request_cancel(
        execution.execution_id,
        actor_id="test-actor",
        reason="Running cancellation",
        requested_at=_now(),
        audit_event=cancel_prepared,
        audit_outbox=audit_outbox,
    )
    assert requested.status is ExecutionStatus.CANCEL_REQUESTED

    # Complete the cancellation
    complete_prepared = _prepare_event(audit_outbox, "EXECUTION_CANCELLED")
    cancelled = repository.complete_cancelled(
        execution.execution_id, _now(),
        audit_event=complete_prepared, audit_outbox=audit_outbox,
    )
    assert cancelled.status is ExecutionStatus.CANCELLED


def test_complete_timeout_partial(
    repository: PostgreSQLExecutionRepository,
    audit_outbox: PostgreSQLTransactionalAudit,
) -> None:
    """FR-040: Kismi timeout PARTIAL durumuna gecer."""
    execution = _sample_execution(rule_version_ids=("rv-001",))
    prepared = _prepare_event(audit_outbox, "EXECUTION_CREATED")
    repository.create_or_get(execution, audit_event=prepared, audit_outbox=audit_outbox)
    repository.claim_next(_now())

    now = _now()
    partial_results = (
        RuleExecutionResult(
            execution_id=execution.execution_id,
            rule_version_id="rv-001",
            population_count=50,
            eligible_count=45,
            evaluated_count=45,
            passed_count=40,
            failed_count=5,
            excluded_count=5,
            technical_error_count=0,
            unknown_count=0,
            measurement_status=None,
            completed_partitions=("p1",),
            eligible_for_official_scoring=False,
        ),
    )
    timeout_prepared = _prepare_event(audit_outbox, "EXECUTION_TIMEOUT")
    partial = repository.complete_timeout(
        execution.execution_id, "QUERY_TIMEOUT", partial_results, now,
        audit_event=timeout_prepared, audit_outbox=audit_outbox,
    )
    assert partial.status is ExecutionStatus.PARTIAL


def test_complete_timeout_no_results(
    repository: PostgreSQLExecutionRepository,
    audit_outbox: PostgreSQLTransactionalAudit,
) -> None:
    """FR-040: Sonucsuz timeout TIMEOUT durumuna gecer."""
    execution = _sample_execution()
    prepared = _prepare_event(audit_outbox, "EXECUTION_CREATED")
    repository.create_or_get(execution, audit_event=prepared, audit_outbox=audit_outbox)
    repository.claim_next(_now())

    timeout_prepared = _prepare_event(audit_outbox, "EXECUTION_TIMEOUT")
    timeout = repository.complete_timeout(
        execution.execution_id, "TOTAL_TIMEOUT", (), _now(),
        audit_event=timeout_prepared, audit_outbox=audit_outbox,
    )
    assert timeout.status is ExecutionStatus.TIMEOUT


def test_add_and_list_attempts(
    repository: PostgreSQLExecutionRepository,
    audit_outbox: PostgreSQLTransactionalAudit,
) -> None:
    """FR-041: Deneme kaydi ekleme ve listeleme."""
    execution = _sample_execution()
    prepared = _prepare_event(audit_outbox, "EXECUTION_CREATED")
    repository.create_or_get(execution, audit_event=prepared, audit_outbox=audit_outbox)

    attempt = ExecutionAttempt(
        execution_id=execution.execution_id,
        attempt_no=1,
        status=ExecutionStatus.SUCCESS,
        created_at=_now(),
    )
    attempt_prepared = _prepare_event(audit_outbox, "ATTEMPT_RECORDED")
    repository.add_attempt(attempt, audit_event=attempt_prepared, audit_outbox=audit_outbox)

    attempts = repository.list_attempts(execution.execution_id)
    assert len(attempts) == 1
    assert attempts[0].attempt_no == 1
    assert attempts[0].status is ExecutionStatus.SUCCESS


def test_list_executions_for_sources(
    repository: PostgreSQLExecutionRepository,
    audit_outbox: PostgreSQLTransactionalAudit,
) -> None:
    """FR-044: Kaynak bazli execution listeleme."""
    execution1 = _sample_execution(source_ids=("src-001",))
    execution2 = _sample_execution(source_ids=("src-002",))

    prepared = _prepare_event(audit_outbox, "EXECUTION_CREATED")
    repository.create_or_get(execution1, audit_event=prepared, audit_outbox=audit_outbox)
    repository.create_or_get(execution2, audit_event=prepared, audit_outbox=audit_outbox)

    # Only src-001
    result = repository.list_executions_for_sources(frozenset({"src-001"}))
    assert len(result) == 1
    assert result[0].execution_id == execution1.execution_id

    # Both sources
    result = repository.list_executions_for_sources(frozenset({"src-001", "src-002"}))
    assert len(result) == 2


def test_list_cancel_requested(
    repository: PostgreSQLExecutionRepository,
    audit_outbox: PostgreSQLTransactionalAudit,
) -> None:
    """FR-043: Iptal istenen execution'lari listeleme."""
    execution = _sample_execution()
    prepared = _prepare_event(audit_outbox, "EXECUTION_CREATED")
    repository.create_or_get(execution, audit_event=prepared, audit_outbox=audit_outbox)
    repository.claim_next(_now())

    cancel_prepared = _prepare_event(audit_outbox, "EXECUTION_CANCEL_REQUESTED")
    repository.request_cancel(
        execution.execution_id,
        actor_id="test-actor",
        reason="Cancel",
        requested_at=_now(),
        audit_event=cancel_prepared,
        audit_outbox=audit_outbox,
    )

    cancel_requested = repository.list_cancel_requested()
    assert len(cancel_requested) == 1
    assert cancel_requested[0].execution_id == execution.execution_id


def test_get_execution_not_found(repository: PostgreSQLExecutionRepository) -> None:
    """Bulunamayan execution ExecutionNotFoundError firlatir."""
    from veri_kalitesi.executions.errors import ExecutionNotFoundError

    with pytest.raises(ExecutionNotFoundError, match="not found"):
        repository.get("nonexistent")


def test_claim_next_with_concurrency_policy(
    repository: PostgreSQLExecutionRepository,
    audit_outbox: PostgreSQLTransactionalAudit,
) -> None:
    """FR-039: Concurrency policy ile claim_next."""
    execution = _sample_execution()
    prepared = _prepare_event(audit_outbox, "EXECUTION_CREATED")
    repository.create_or_get(execution, audit_event=prepared, audit_outbox=audit_outbox)

    policy = ConcurrencyPolicy(max_total=1, max_heavy=1, max_light=1)
    claimed = repository.claim_next(_now(), policy=policy)
    assert claimed is not None

    # Second should be none due to max_total=1
    assert repository.claim_next(_now(), policy=policy) is None


def test_audit_outbox_atomic_write(
    repository: PostgreSQLExecutionRepository,
    audit_outbox: PostgreSQLTransactionalAudit,
) -> None:
    """Audit outbox execution ile ayni transaction'da yazilir."""
    execution = _sample_execution()
    prepared = _prepare_event(audit_outbox, "EXECUTION_CREATED")
    repository.create_or_get(execution, audit_event=prepared, audit_outbox=audit_outbox)

    # Verify audit outbox has PENDING event
    pending = audit_outbox.list_pending()
    assert len(pending) >= 1
    matching = [p for p in pending if p.event_id == prepared.event_id]
    assert len(matching) == 1


def test_create_or_get_without_audit(
    repository: PostgreSQLExecutionRepository,
) -> None:
    """Audit olmadan execution olusturma (opsiyonel audit)."""
    execution = _sample_execution()
    stored, created = repository.create_or_get(execution)
    assert created is True
    assert stored.execution_id == execution.execution_id

    retrieved = repository.get(execution.execution_id)
    assert retrieved.status is ExecutionStatus.QUEUED


def test_list_results_empty(
    repository: PostgreSQLExecutionRepository,
) -> None:
    """Sonucu olmayan execution icin bos liste doner."""
    execution = _sample_execution()
    repository.create_or_get(execution)
    assert repository.list_results(execution.execution_id) == []


def test_complete_success_cancel_requested_during_run(
    repository: PostgreSQLExecutionRepository,
    audit_outbox: PostgreSQLTransactionalAudit,
) -> None:
    """CANCEL_REQUESTED execution basariyla tamamlanmaya calisirsa CANCELLED olur."""
    execution = _sample_execution()
    prepared = _prepare_event(audit_outbox, "EXECUTION_CREATED")
    repository.create_or_get(execution, audit_event=prepared, audit_outbox=audit_outbox)
    repository.claim_next(_now())

    cancel_prepared = _prepare_event(audit_outbox, "EXECUTION_CANCEL_REQUESTED")
    repository.request_cancel(
        execution.execution_id,
        actor_id="test-actor",
        reason="Cancel during run",
        requested_at=_now(),
        audit_event=cancel_prepared,
        audit_outbox=audit_outbox,
    )

    now = _now()
    results = (
        RuleExecutionResult(
            execution_id=execution.execution_id,
            rule_version_id="rv-001",
            population_count=100,
            eligible_count=90,
            evaluated_count=90,
            passed_count=80,
            failed_count=10,
            excluded_count=10,
            technical_error_count=0,
            unknown_count=0,
            measurement_status=None,
            completed_partitions=(),
            eligible_for_official_scoring=True,
        ),
    )
    success_prepared = _prepare_event(audit_outbox, "EXECUTION_CANCELLED")
    completed = repository.complete_success(
        execution.execution_id, results, now,
        audit_event=success_prepared, audit_outbox=audit_outbox,
    )
    assert completed.status is ExecutionStatus.CANCELLED