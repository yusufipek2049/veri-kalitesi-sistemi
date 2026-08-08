"""FR-077/BFR-AUD-004: PostgreSQL audit ledger persistence and integrity."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import create_engine, text

from veri_kalitesi.audit.models import (
    AuditEventInput,
    AuditQuery,
    AuditResult,
)
from veri_kalitesi.audit.policies import build_default_redaction_policy
from veri_kalitesi.audit.postgresql_repository import PostgreSQLAuditRepository
from veri_kalitesi.audit.redaction import AuditRedactor
from veri_kalitesi.persistence import DatabaseSettings, create_session_factory

ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_CFG = ROOT / "alembic.ini"
pytestmark = pytest.mark.skipif(
    not os.environ.get("DATA_QUALITY_POSTGRES_TEST_URL"),
    reason="Requires DATA_QUALITY_POSTGRES_TEST_URL pointing to PostgreSQL 16",
)
NOW = datetime(2026, 8, 5, 9, 0, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def settings() -> DatabaseSettings:
    return DatabaseSettings.from_url(
        os.environ["DATA_QUALITY_POSTGRES_TEST_URL"],
        schema=os.environ.get("DATA_QUALITY_DATABASE_SCHEMA", "dq"),
    )


@pytest.fixture(scope="module", autouse=True)
def migrated(settings: DatabaseSettings) -> None:
    config = Config(str(ALEMBIC_CFG))
    config.set_main_option("sqlalchemy.url", settings.url.render_as_string(hide_password=False))
    config.set_main_option("data_quality_schema", settings.schema)
    command.upgrade(config, "head")


@pytest.fixture
def repository(settings: DatabaseSettings, migrated: None) -> PostgreSQLAuditRepository:
    engine = create_engine(settings.url, pool_pre_ping=True)
    with engine.begin() as connection:
        connection.execute(text(f'DELETE FROM "{settings.schema}".audit_outbox'))
        connection.execute(text(f'DELETE FROM "{settings.schema}".audit_events'))
    return PostgreSQLAuditRepository(
        create_session_factory(settings, engine=engine), schema=settings.schema
    )


def _prepared(index: int):  # type: ignore[no-untyped-def]
    return AuditRedactor(build_default_redaction_policy()).prepare(
        AuditEventInput(
            actor_id=f"actor-{index}",
            actor_type="USER",
            correlation_id=f"correlation-{index}",
            action="DATA_SOURCE_CREATED",
            object_type="DataSource",
            object_id=f"source-{index}",
            result=AuditResult.SUCCESS,
            reason_code="DATA_SOURCE_CREATED",
            old_values={},
            new_values={"status": "TEST_PENDING"},
            occurred_at=NOW + timedelta(seconds=index),
        )
    )


def test_audit_ledger_survives_repository_reconstruction_and_is_idempotent(
    repository: PostgreSQLAuditRepository,
) -> None:
    prepared = _prepared(1)
    first = repository.append(prepared)
    replay = repository.append(prepared)
    reconstructed = PostgreSQLAuditRepository(
        repository.session_factory,
        schema=repository.table.schema or "dq",
    )
    page, has_more = reconstructed.query_events(
        AuditQuery(
            start_at=NOW - timedelta(minutes=1),
            end_at=NOW + timedelta(minutes=1),
            reason_code="TEST_QUERY",
        )
    )
    assert replay == first
    assert [event.event_id for event in page] == [first.event_id]
    assert has_more is False
    assert reconstructed.verify_integrity().valid is True


def test_concurrent_append_keeps_single_valid_hash_chain(
    repository: PostgreSQLAuditRepository,
) -> None:
    prepared = [_prepared(index) for index in range(2, 10)]
    with ThreadPoolExecutor(max_workers=4) as executor:
        events = list(executor.map(repository.append, prepared))
    assert len({event.sequence_no for event in events}) == len(prepared)
    assert repository.verify_integrity().valid is True
