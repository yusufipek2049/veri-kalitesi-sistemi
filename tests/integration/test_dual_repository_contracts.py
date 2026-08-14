"""Ayni davranis sözlesmesini SQLite ve canli PostgreSQL depolarinda kosturur."""

from __future__ import annotations

import os
from typing import Any

import pytest

from repository_contracts import REPOSITORY_CONTRACTS, RepositoryContract
from veri_kalitesi.audit.postgresql_repository import PostgreSQLAuditRepository
from veri_kalitesi.audit.repository import SQLiteAuditRepository
from veri_kalitesi.data_sources.postgresql_repository import PostgreSQLDataSourceRepository
from veri_kalitesi.data_sources.repository import SQLiteDataSourceRepository
from veri_kalitesi.executions.postgresql_repository import PostgreSQLExecutionRepository
from veri_kalitesi.executions.repository import SQLiteExecutionRepository
from veri_kalitesi.notifications.postgresql_repository import PostgreSQLNotificationRepository
from veri_kalitesi.notifications.repository import SQLiteNotificationRepository
from veri_kalitesi.persistence import DatabaseSettings, create_session_factory
from veri_kalitesi.rules.postgresql_repository import PostgreSQLRuleRepository
from veri_kalitesi.rules.repository import SQLiteRuleRepository
from veri_kalitesi.scoring.postgresql_repository import PostgreSQLScoreRepository
from veri_kalitesi.scoring.repository import SQLiteScoreRepository


pytestmark = pytest.mark.skipif(
    not os.environ.get("DATA_QUALITY_POSTGRES_TEST_URL"),
    reason="DATA_QUALITY_POSTGRES_TEST_URL is required for PostgreSQL integration.",
)


def _repositories(settings: DatabaseSettings) -> dict[str, tuple[Any, Any]]:
    session_factory = create_session_factory(settings)
    schema = settings.schema
    return {
        "audit": (
            SQLiteAuditRepository(),
            PostgreSQLAuditRepository(session_factory, schema=schema),
        ),
        "data_sources": (
            SQLiteDataSourceRepository(),
            PostgreSQLDataSourceRepository(session_factory, schema=schema),
        ),
        "executions": (
            SQLiteExecutionRepository(),
            PostgreSQLExecutionRepository(session_factory, schema=schema),
        ),
        "notifications": (
            SQLiteNotificationRepository(),
            PostgreSQLNotificationRepository(session_factory, schema=schema),
        ),
        "rules": (
            SQLiteRuleRepository(),
            PostgreSQLRuleRepository(session_factory, schema=schema),
        ),
        "scoring": (
            SQLiteScoreRepository(),
            PostgreSQLScoreRepository(session_factory, schema=schema),
        ),
    }


@pytest.mark.parametrize("contract", REPOSITORY_CONTRACTS, ids=lambda item: item.name)
def test_empty_state_behavior_is_equal_for_both_implementations(
    contract: RepositoryContract,
    postgresql_test_database: DatabaseSettings | None,
) -> None:
    assert postgresql_test_database is not None
    sqlite_repository, postgresql_repository = _repositories(postgresql_test_database)[
        contract.name
    ]
    try:
        contract.assert_equivalent(sqlite_repository, postgresql_repository)
    finally:
        connection = getattr(sqlite_repository, "connection", None)
        if connection is not None:
            connection.close()
