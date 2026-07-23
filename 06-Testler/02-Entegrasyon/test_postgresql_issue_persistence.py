"""36A1 gerçek PostgreSQL migration, scope ve rollback entegrasyonu."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, insert, text
from sqlalchemy.orm import Session, sessionmaker

from veri_kalitesi.issues import PostgreSQLIssueRepository, issue_table
from veri_kalitesi.persistence import DatabaseSettings

POSTGRES_TEST_URL = os.environ.get("DATA_QUALITY_POSTGRES_TEST_URL")
pytestmark = pytest.mark.skipif(
    not POSTGRES_TEST_URL,
    reason="DATA_QUALITY_POSTGRES_TEST_URL is required for PostgreSQL integration.",
)
ROOT = Path(__file__).resolve().parents[2]


def test_issue_baseline_scope_query_and_outer_transaction_rollback() -> None:
    """FR-064, FR-070, NFR-MNT-004, NFR-REL-006."""

    assert POSTGRES_TEST_URL is not None
    schema = f"dq_test_{uuid4().hex}"
    settings = DatabaseSettings.from_url(POSTGRES_TEST_URL, schema=schema)
    engine = create_engine(settings.url, pool_pre_ping=True)
    config = Config(str(ROOT / "05-Veritabani/alembic.ini"))
    config.set_main_option("sqlalchemy.url", settings.url.render_as_string(hide_password=False))
    config.set_main_option("data_quality_schema", schema)

    try:
        command.upgrade(config, "head")
        with engine.connect() as connection:
            transaction = connection.begin()
            factory = sessionmaker(
                bind=connection,
                class_=Session,
                expire_on_commit=False,
                join_transaction_mode="create_savepoint",
            )
            table = issue_table(schema)
            dataset_id = str(uuid4())
            other_dataset_id = str(uuid4())
            now = datetime.now(timezone.utc)
            with factory.begin() as session:
                session.execute(
                    insert(table),
                    [
                        _issue_row(str(uuid4()), "DQI-TEST-001", dataset_id, now),
                        _issue_row(str(uuid4()), "DQI-TEST-002", other_dataset_id, now),
                    ],
                )

            repository = PostgreSQLIssueRepository(factory, schema=schema)
            visible = repository.list_issues_for_scopes(
                frozenset(),
                frozenset({dataset_id}),
            )

            assert [issue.issue_no for issue in visible] == ["DQI-TEST-001"]
            assert repository.count() == 2
            transaction.rollback()

        with engine.connect() as connection:
            remaining = connection.scalar(
                text(f'SELECT COUNT(*) FROM "{schema}".data_quality_issues')
            )
            assert remaining == 0
    finally:
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()


def _issue_row(issue_id: str, issue_no: str, dataset_id: str, now: datetime) -> dict[str, object]:
    return {
        "issue_id": issue_id,
        "issue_no": issue_no,
        "source_event_id": str(uuid4()),
        "source_event_type": "QUALITY",
        "trigger_type": "QUALITY_THRESHOLD",
        "scope_type": "DATASET",
        "scope_id": dataset_id,
        "status": "NEW",
        "priority": "HIGH",
        "assignee_user_id": str(uuid4()),
        "deduplication_key_digest": uuid4().hex,
        "payload_digest": uuid4().hex,
        "occurrence_count": 1,
        "version": 1,
        "created_at": now,
        "updated_at": now,
        "last_seen_at": now,
    }
