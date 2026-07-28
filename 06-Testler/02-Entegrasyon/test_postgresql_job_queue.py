"""Kalıcı iş kuyruğu için opt-in PostgreSQL entegrasyon testleri."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, func, select, text, update

from veri_kalitesi.jobs import (
    BackgroundJob,
    JobConcurrencyError,
    JobIdempotencyConflictError,
    JobLeaseError,
    JobLeasePolicy,
    JobStatus,
    PostgreSQLJobQueueRepository,
    job_tables,
)
from veri_kalitesi.persistence import (
    DEFAULT_SCHEMA_NAME,
    DatabaseSettings,
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
def session_factory(db_settings: DatabaseSettings, alembic_up_to_date: None) -> type:
    engine = create_engine(
        db_settings.url.render_as_string(hide_password=False),
        pool_pre_ping=True,
    )
    with engine.begin() as connection:
        connection.execute(text(f"DELETE FROM {db_settings.schema}.background_jobs"))
    return create_session_factory(db_settings, engine=engine)


@pytest.fixture
def repository(
    session_factory: type, db_settings: DatabaseSettings
) -> PostgreSQLJobQueueRepository:
    return PostgreSQLJobQueueRepository(session_factory, schema=db_settings.schema)


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
) -> BackgroundJob:
    created = created_at or _at()
    return BackgroundJob(
        job_id=job_id or str(uuid4()),
        job_type=job_type,
        payload={"object_ref": payload_ref or str(uuid4())},
        idempotency_key=idempotency_key,
        priority=priority,
        available_at=available_at or created,
        created_at=created,
        updated_at=created,
    )


def test_enqueue_is_persistent_across_repository_and_session_instances(
    repository: PostgreSQLJobQueueRepository,
    session_factory: type,
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


def test_idempotent_enqueue_creates_one_row(
    repository: PostgreSQLJobQueueRepository,
    session_factory: type,
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
    session_factory: type,
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
    session_factory: type,
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

    assert heartbeat.last_heartbeat_at > claimed.last_heartbeat_at
    assert heartbeat.lease_expires_at > claimed.lease_expires_at
    assert heartbeat.version == claimed.version + 1


def test_active_lease_cannot_be_claimed_by_second_worker(
    repository: PostgreSQLJobQueueRepository,
) -> None:
    repository.enqueue(_job())
    assert repository.claim_next("worker-a", JobLeasePolicy(), now=_at()) is not None

    assert repository.claim_next("worker-b", JobLeasePolicy(), now=_at(1)) is None


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

        assert revision == "20260728_08"
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

        assert current_revision == "20260728_08"
        assert job_table_count == 1
    finally:
        engine.dispose()
        _drop_isolated_schema(db_settings, schema)


def test_conditional_heartbeat_update_affects_zero_rows_for_stale_version(
    repository: PostgreSQLJobQueueRepository,
    session_factory: type,
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

    assert result.rowcount == 0
