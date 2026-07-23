"""36A2b salt okunur ve idempotent SQLite issue aktarım testleri."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from veri_kalitesi.issues import IssueMigrationError, SQLiteIssueMigrator
from veri_kalitesi.persistence import DatabaseSettings, create_session_factory

POSTGRES_TEST_URL = os.environ.get("DATA_QUALITY_POSTGRES_TEST_URL")
pytestmark = pytest.mark.skipif(
    not POSTGRES_TEST_URL,
    reason="DATA_QUALITY_POSTGRES_TEST_URL is required for PostgreSQL integration.",
)
ROOT = Path(__file__).resolve().parents[2]


def test_legacy_issue_rows_are_read_only_selective_and_idempotent(tmp_path: Path) -> None:
    """FR-064–FR-070, NFR-REL-005/006, NFR-SEC-005/008/011."""

    legacy_database = tmp_path / "legacy-issues.sqlite3"
    _create_legacy_database(legacy_database)

    with _postgres_fixture() as fixture:
        migrator = SQLiteIssueMigrator(fixture.session_factory, schema=fixture.schema)

        first = migrator.migrate(legacy_database)
        second = migrator.migrate(legacy_database)

        assert first.source_count == 8
        assert first.inserted_count == 8
        assert second.source_count == 8
        assert second.inserted_count == 0
        assert first.foreign_key_violations == 0
        assert first.source_sha256_before == first.source_sha256_after
        assert second.source_sha256_before == second.source_sha256_after
        assert all(item.source_hash == item.target_hash for item in first.tables)
        assert all(item.source_hash == item.target_hash for item in second.tables)

        with fixture.engine.connect() as connection:
            assert (
                connection.scalar(
                    text(f'SELECT COUNT(*) FROM "{fixture.schema}".data_quality_issues')
                )
                == 2
            )
            assert (
                connection.scalar(text(f'SELECT COUNT(*) FROM "{fixture.schema}".audit_outbox'))
                == 1
            )


def test_existing_target_payload_mismatch_rolls_back_migration(tmp_path: Path) -> None:
    legacy_database = tmp_path / "legacy-issues.sqlite3"
    issue_id = _create_legacy_database(legacy_database)

    with _postgres_fixture() as fixture:
        migrator = SQLiteIssueMigrator(fixture.session_factory, schema=fixture.schema)
        migrator.migrate(legacy_database)
        with fixture.engine.begin() as connection:
            connection.execute(
                text(
                    f'UPDATE "{fixture.schema}".data_quality_issues '
                    "SET occurrence_count = 99 WHERE issue_id = :issue_id"
                ),
                {"issue_id": issue_id},
            )

        with pytest.raises(IssueMigrationError, match="hash"):
            migrator.migrate(legacy_database)

        with fixture.engine.connect() as connection:
            assert (
                connection.scalar(
                    text(f'SELECT COUNT(*) FROM "{fixture.schema}".data_quality_issues')
                )
                == 2
            )


def _create_legacy_database(path: Path) -> str:
    now = datetime.now(timezone.utc).isoformat()
    issue_id = str(uuid4())
    predecessor_id = str(uuid4())
    history_id = str(uuid4())
    predecessor_history_id = str(uuid4())
    resolution_id = str(uuid4())
    verification_id = str(uuid4())
    relationship_id = str(uuid4())
    event_id = str(uuid4())
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE data_quality_issues (
                issue_id TEXT PRIMARY KEY,
                issue_no TEXT NOT NULL UNIQUE,
                source_event_id TEXT NOT NULL,
                source_event_type TEXT NOT NULL,
                trigger_type TEXT NOT NULL,
                scope_type TEXT NOT NULL,
                scope_id TEXT NOT NULL,
                status TEXT NOT NULL,
                priority TEXT NOT NULL,
                assignee_user_id TEXT NOT NULL,
                deduplication_key_digest TEXT NOT NULL UNIQUE,
                payload_digest TEXT NOT NULL,
                occurrence_count INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL
            );
            CREATE TABLE issue_history (
                sequence_no INTEGER PRIMARY KEY AUTOINCREMENT,
                history_id TEXT NOT NULL UNIQUE,
                issue_id TEXT NOT NULL REFERENCES data_quality_issues(issue_id),
                action TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                old_status TEXT,
                new_status TEXT NOT NULL,
                old_assignee_user_id TEXT,
                new_assignee_user_id TEXT,
                old_priority TEXT,
                new_priority TEXT,
                resolution_id TEXT,
                verification_id TEXT,
                occurred_at TEXT NOT NULL
            );
            CREATE TABLE issue_resolutions (
                sequence_no INTEGER PRIMARY KEY AUTOINCREMENT,
                resolution_id TEXT NOT NULL UNIQUE,
                issue_id TEXT NOT NULL REFERENCES data_quality_issues(issue_id),
                root_cause TEXT NOT NULL,
                corrective_action TEXT NOT NULL,
                evidence_reference_id TEXT NOT NULL,
                completed_at TEXT NOT NULL,
                protection_policy_version TEXT NOT NULL,
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE issue_verifications (
                sequence_no INTEGER PRIMARY KEY AUTOINCREMENT,
                verification_id TEXT NOT NULL UNIQUE,
                issue_id TEXT NOT NULL REFERENCES data_quality_issues(issue_id),
                verification_reference_id TEXT NOT NULL UNIQUE,
                execution_id TEXT NOT NULL,
                score_id TEXT,
                scope_type TEXT NOT NULL,
                scope_id TEXT NOT NULL,
                outcome TEXT NOT NULL,
                completed_at TEXT NOT NULL,
                recorded_by TEXT NOT NULL,
                recorded_at TEXT NOT NULL
            );
            CREATE TABLE issue_relationships (
                sequence_no INTEGER PRIMARY KEY AUTOINCREMENT,
                relationship_id TEXT NOT NULL UNIQUE,
                predecessor_issue_id TEXT NOT NULL
                    REFERENCES data_quality_issues(issue_id),
                successor_issue_id TEXT NOT NULL
                    REFERENCES data_quality_issues(issue_id),
                relationship_type TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE audit_outbox (
                event_id TEXT PRIMARY KEY,
                prepared_event TEXT NOT NULL,
                policy_version TEXT NOT NULL,
                status TEXT NOT NULL,
                attempt_count INTEGER NOT NULL,
                last_error_code TEXT,
                created_at TEXT NOT NULL,
                published_at TEXT
            );
            """
        )
        issue_rows = (
            (
                predecessor_id,
                "DQI-LEGACY-001",
                str(uuid4()),
                "QUALITY",
                "QUALITY_THRESHOLD",
                "DATASET",
                str(uuid4()),
                "CLOSED",
                "HIGH",
                str(uuid4()),
                uuid4().hex,
                uuid4().hex,
                1,
                now,
                now,
                now,
            ),
            (
                issue_id,
                "DQI-LEGACY-002",
                str(uuid4()),
                "QUALITY",
                "QUALITY_THRESHOLD",
                "DATASET",
                str(uuid4()),
                "VERIFIED",
                "CRITICAL",
                str(uuid4()),
                uuid4().hex,
                uuid4().hex,
                2,
                now,
                now,
                now,
            ),
        )
        connection.executemany(
            """
            INSERT INTO data_quality_issues VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            issue_rows,
        )
        connection.executemany(
            """
            INSERT INTO issue_history (
                history_id, issue_id, action, actor_id, old_status, new_status,
                occurred_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                (
                    predecessor_history_id,
                    predecessor_id,
                    "ISSUE_CLOSED",
                    str(uuid4()),
                    "VERIFIED",
                    "CLOSED",
                    now,
                ),
                (
                    history_id,
                    issue_id,
                    "ISSUE_VERIFIED",
                    str(uuid4()),
                    "RESOLVED",
                    "VERIFIED",
                    now,
                ),
            ),
        )
        connection.execute(
            """
            INSERT INTO issue_resolutions (
                resolution_id, issue_id, root_cause, corrective_action,
                evidence_reference_id, completed_at, protection_policy_version,
                created_by, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                resolution_id,
                issue_id,
                "Korunan kök neden",
                "Korunan düzeltici faaliyet",
                str(uuid4()),
                now,
                "LEGACY_PROTECTION_V1",
                str(uuid4()),
                now,
            ),
        )
        connection.execute(
            """
            INSERT INTO issue_verifications (
                verification_id, issue_id, verification_reference_id, execution_id,
                score_id, scope_type, scope_id, outcome, completed_at, recorded_by,
                recorded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                verification_id,
                issue_id,
                str(uuid4()),
                str(uuid4()),
                str(uuid4()),
                "DATASET",
                issue_rows[1][6],
                "QUALITY_PASSED",
                now,
                str(uuid4()),
                now,
            ),
        )
        connection.execute(
            """
            INSERT INTO issue_relationships (
                relationship_id, predecessor_issue_id, successor_issue_id,
                relationship_type, created_at
            ) VALUES (?, ?, ?, 'RECURRENCE', ?)
            """,
            (relationship_id, predecessor_id, issue_id, now),
        )
        connection.executemany(
            """
            INSERT INTO audit_outbox VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                (
                    event_id,
                    json.dumps(
                        {
                            "event_id": event_id,
                            "object_type": "DATA_QUALITY_ISSUE",
                            "action": "ISSUE_VERIFIED",
                        }
                    ),
                    "LEGACY_OUTBOX_V1",
                    "PENDING",
                    0,
                    None,
                    now,
                    None,
                ),
                (
                    str(uuid4()),
                    json.dumps({"object_type": "NOTIFICATION"}),
                    "LEGACY_OUTBOX_V1",
                    "PENDING",
                    0,
                    None,
                    now,
                    None,
                ),
                (
                    str(uuid4()),
                    json.dumps({"object_type": "DATA_QUALITY_ISSUE"}),
                    "LEGACY_OUTBOX_V1",
                    "PUBLISHED",
                    1,
                    None,
                    now,
                    now,
                ),
            ),
        )
    return issue_id


class _PostgreSQLFixture:
    def __init__(self, url: str, schema: str) -> None:
        self.schema = schema
        self.settings = DatabaseSettings.from_url(url, schema=schema)
        self.engine = create_engine(self.settings.url, pool_pre_ping=True)
        self.session_factory = create_session_factory(self.settings, engine=self.engine)


class _postgres_fixture:
    def __enter__(self) -> _PostgreSQLFixture:
        assert POSTGRES_TEST_URL is not None
        schema = f"dq_test_{uuid4().hex}"
        self.fixture = _PostgreSQLFixture(POSTGRES_TEST_URL, schema)
        config = Config(str(ROOT / "05-Veritabani/alembic.ini"))
        config.set_main_option(
            "sqlalchemy.url",
            self.fixture.settings.url.render_as_string(hide_password=False),
        )
        config.set_main_option("data_quality_schema", schema)
        command.upgrade(config, "head")
        return self.fixture

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        with self.fixture.engine.connect().execution_options(
            isolation_level="AUTOCOMMIT"
        ) as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{self.fixture.schema}" CASCADE'))
        self.fixture.engine.dispose()
