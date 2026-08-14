"""GAP-027/S1: PostgreSQL-only executable composition verification."""

from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from veri_kalitesi.api.composition import create_application
from veri_kalitesi.api.identity import DevelopmentActorContextResolver
from veri_kalitesi.api.settings import ApplicationSettings
from veri_kalitesi.audit.postgresql_repository import PostgreSQLAuditRepository
from veri_kalitesi.data_sources.postgresql_repository import PostgreSQLDataSourceRepository
from veri_kalitesi.data_sources.secrets import InMemorySecretResolver
from veri_kalitesi.executions.postgresql_repository import PostgreSQLExecutionRepository
from veri_kalitesi.issues import PostgreSQLIssueRepository
from veri_kalitesi.persistence import DatabaseSettings
from veri_kalitesi.rules import PostgreSQLRuleRepository
from veri_kalitesi.scoring.postgresql_repository import PostgreSQLScoreRepository
from veri_kalitesi.reporting.repository import PostgreSQLReportRepository

ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_CFG = ROOT / "alembic.ini"
pytestmark = pytest.mark.skipif(
    not os.environ.get("DATA_QUALITY_POSTGRES_TEST_URL"),
    reason="Requires DATA_QUALITY_POSTGRES_TEST_URL pointing to PostgreSQL 16",
)


def _database() -> DatabaseSettings:
    return DatabaseSettings.from_url(
        os.environ["DATA_QUALITY_POSTGRES_TEST_URL"],
        schema=os.environ.get("DATA_QUALITY_DATABASE_SCHEMA", "dq"),
    )


def _upgrade(database: DatabaseSettings) -> None:
    config = Config(str(ALEMBIC_CFG))
    config.set_main_option("sqlalchemy.url", database.url.render_as_string(hide_password=False))
    config.set_main_option("data_quality_schema", database.schema)
    command.upgrade(config, "head")


def test_ds02_ac_create_application_uses_postgresql_query_repositories() -> None:
    database = _database()
    _upgrade(database)
    settings = ApplicationSettings(
        runtime_environment="test",
        database=database,
        allowed_origins=("https://dq.test",),
        actor_policy_version="S1_COMPOSITION_ACTOR_V1",
    )
    resolver = DevelopmentActorContextResolver(
        runtime_environment="development",
        policy_version=settings.actor_policy_version,
        permitted_source_ids=frozenset(),
        can_view_enterprise=True,
        roles=frozenset({"DATA_VIEWER", "DATA_STEWARD", "DATA_OWNER", "AUDIT_VIEWER"}),
        allowed_origins=frozenset(settings.allowed_origins),
    )
    app = create_application(
        settings,
        resolver,
        secret_resolver=InMemorySecretResolver({}),
    )
    assert isinstance(app.state.data_source_repository, PostgreSQLDataSourceRepository)
    assert isinstance(app.state.rule_repository, PostgreSQLRuleRepository)
    assert isinstance(app.state.issue_repository, PostgreSQLIssueRepository)
    assert isinstance(app.state.execution_repository, PostgreSQLExecutionRepository)
    assert isinstance(app.state.audit_repository, PostgreSQLAuditRepository)
    assert isinstance(app.state.score_repository, PostgreSQLScoreRepository)
    assert isinstance(app.state.report_repository, PostgreSQLReportRepository)
    assert app.state.data_source_repository.session_factory is app.state.session_factory
    assert app.state.rule_repository._session_factory is app.state.session_factory
    assert app.state.issue_repository._session_factory is app.state.session_factory
    assert app.state.execution_repository.session_factory is app.state.session_factory
    assert app.state.audit_repository.session_factory is app.state.session_factory
    assert app.state.score_repository._session_factory is app.state.session_factory

    client = TestClient(app)
    for path in (
        "/api/v1/rules",
        "/api/v1/issues",
        "/api/v1/executions",
        "/api/v1/reports",
    ):
        response = client.get(path)
        assert response.status_code == 200
        assert response.json()["data_origin"] == "postgresql-runtime"
        assert response.json()["items"] == []

    scores_response = client.get("/api/v1/scores")
    assert scores_response.status_code == 200
    assert scores_response.json()["data_origin"] == "postgresql-runtime"


def test_s1_migration_enforces_source_enum_pending_uniqueness_and_audit_ledger() -> None:
    database = _database()
    _upgrade(database)
    engine = create_engine(database.url, pool_pre_ping=True)
    schema = database.schema
    inspector = inspect(engine)

    source_constraint = next(
        item
        for item in inspector.get_check_constraints("data_sources", schema=schema)
        if item["name"] == "ck_data_sources_source_type"
    )
    constraint_sql = str(source_constraint["sqltext"])
    for source_type in ("POSTGRESQL", "MSSQL", "ORACLE", "MYSQL", "CSV", "EXCEL", "REST"):
        assert source_type in constraint_sql
    assert "REST_API" not in constraint_sql
    assert "OTHER" not in constraint_sql

    with engine.connect() as connection:
        pending_index = connection.scalar(
            text(
                """SELECT indexdef FROM pg_indexes
                   WHERE schemaname = :schema
                     AND indexname = 'uq_activation_requests_pending_source_revision'"""
            ),
            {"schema": schema},
        )
    assert pending_index is not None
    assert "UNIQUE INDEX" in pending_index
    assert "WHERE" in pending_index and "PENDING" in pending_index

    audit_columns = {
        column["name"] for column in inspector.get_columns("audit_events", schema=schema)
    }
    assert {
        "sequence_no",
        "event_id",
        "previous_event_hash",
        "event_hash",
        "old_value_summary",
        "new_value_summary",
    } <= audit_columns

    source_id = str(uuid4())
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(
                text(
                    f'''INSERT INTO "{schema}".data_sources
                        (data_source_id, name, source_type, connection_config,
                         secret_reference, owner_user_id, status, revision, created_at)
                        VALUES (:source_id, :name, 'POSTGRESQL', CAST(:config AS json),
                                'secret://local/integration', 'maker-a',
                                'TEST_SUCCEEDED', 1, now())'''
                ),
                {"source_id": source_id, "name": f"S1-{source_id}", "config": "{}"},
            )
            for request_id in (str(uuid4()), str(uuid4())):
                connection.execute(
                    text(
                        f'''INSERT INTO "{schema}".data_source_activation_requests
                            (activation_request_id, data_source_id, data_source_revision,
                             maker_actor_id, policy_version, status, requested_at)
                            VALUES (:request_id, :source_id, 1, 'maker-a',
                                    'S1_TEST_POLICY', 'PENDING', now())'''
                    ),
                    {"request_id": request_id, "source_id": source_id},
                )
