"""FR-089–FR-095 PostgreSQL sentetik dataset gerçek ortam doğrulaması."""

from __future__ import annotations

import os

import psycopg
import pytest

from veri_kalitesi.synthetic_data.errors import SyntheticDataValidationError
from veri_kalitesi.synthetic_data.postgresql_dataset import (
    CONTROL_SCHEMA,
    MIN_ROW_COUNT,
    SOURCE_SCHEMA,
    TABLE_SPECS,
    PostgreSQLSyntheticDatasetManager,
)


pytestmark = pytest.mark.skipif(
    os.environ.get("SYNTHETIC_POSTGRES_TEST") != "1",
    reason="SYNTHETIC_POSTGRES_TEST=1 is required for PostgreSQL integration.",
)


def _connection() -> psycopg.Connection[tuple[object, ...]]:
    return psycopg.connect(
        host=os.environ.get("PGHOST", "localhost"),
        port=int(os.environ.get("PGPORT", "5433")),
        dbname=os.environ.get("PGDATABASE", "data_quality_test"),
        user=os.environ.get("PGUSER", "postgres"),
        password=os.environ["PGPASSWORD"],
        connect_timeout=10,
        application_name="synthetic-postgresql-integration-test",
        autocommit=True,
    )


def test_fr_089_fr_092_generator_creates_and_validates_seventeen_tables() -> None:
    connection = _connection()
    try:
        manager = PostgreSQLSyntheticDatasetManager(connection)
        summary = manager.generate(
            environment="test",
            allow_test_data=True,
            seed=2026,
            scenario="mixed-quality",
            row_count=MIN_ROW_COUNT,
            reset=True,
            progress=False,
        )

        assert len(summary.table_metrics) == 17
        assert summary.total_rows == 17 * MIN_ROW_COUNT
        assert summary.all_validations_passed is True
        assert all(metric.generated_row_count == MIN_ROW_COUNT for metric in summary.table_metrics)
        assert all(
            0.15 <= metric.defective_row_count / MIN_ROW_COUNT <= 0.20
            for metric in summary.table_metrics
        )
        assert all(metric.false_positive == 0 for metric in summary.validation_metrics)
        assert all(metric.false_negative == 0 for metric in summary.validation_metrics)

        with connection.cursor() as cursor:
            source_tables = {
                str(row[0])
                for row in cursor.execute(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = %s AND table_type = 'BASE TABLE'
                    """,
                    (SOURCE_SCHEMA,),
                ).fetchall()
            }
            assert source_tables == {spec.name for spec in TABLE_SPECS}
            foreign_keys = cursor.execute(
                """
                SELECT COUNT(*)
                FROM information_schema.table_constraints
                WHERE table_schema = %s AND constraint_type = 'FOREIGN KEY'
                """,
                (SOURCE_SCHEMA,),
            ).fetchone()
            assert foreign_keys is not None and foreign_keys[0] == 0

        with pytest.raises(SyntheticDataValidationError, match="already exists"):
            manager.generate(
                environment="test",
                allow_test_data=True,
                seed=2026,
                scenario="mixed-quality",
                row_count=MIN_ROW_COUNT,
                reset=False,
                progress=False,
            )
    finally:
        connection.close()

    reopened = _connection()
    try:
        with reopened.cursor() as cursor:
            persisted = cursor.execute(
                "SELECT total_row_count FROM synthetic_control.generation_runs"
            ).fetchone()
        assert persisted is not None and persisted[0] == 17 * MIN_ROW_COUNT
    finally:
        reopened.close()


def test_fr_095_reset_removes_only_synthetic_schemas() -> None:
    connection = _connection()
    try:
        manager = PostgreSQLSyntheticDatasetManager(connection)
        with connection.transaction(), connection.cursor() as cursor:
            cursor.execute("CREATE SCHEMA IF NOT EXISTS synthetic_reset_sentinel")
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS synthetic_reset_sentinel.keep_me (id INTEGER PRIMARY KEY)"
            )

        manager.reset()

        with connection.cursor() as cursor:
            schemas = {
                str(row[0])
                for row in cursor.execute(
                    """
                    SELECT schema_name FROM information_schema.schemata
                    WHERE schema_name IN (%s, %s, 'synthetic_reset_sentinel')
                    """,
                    (SOURCE_SCHEMA, CONTROL_SCHEMA),
                ).fetchall()
            }
        assert schemas == {"synthetic_reset_sentinel"}
        with connection.cursor() as cursor:
            cursor.execute("DROP SCHEMA synthetic_reset_sentinel CASCADE")
    finally:
        connection.close()
