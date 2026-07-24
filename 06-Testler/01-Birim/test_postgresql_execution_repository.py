"""PostgreSQLExecutionRepository icin PostgreSQL gerektirmeyen birim testleri.

Iteration 36E — Execution PostgreSQL migration.
"""

from __future__ import annotations

from sqlalchemy import CheckConstraint, UniqueConstraint

from veri_kalitesi.persistence import DEFAULT_SCHEMA_NAME
from veri_kalitesi.executions.postgresql_repository import execution_tables


def test_execution_tables_uses_dq_schema() -> None:
    """execution_tables varsayilan schema'yi kullanir."""
    tables = execution_tables()
    assert tables.executions.schema == DEFAULT_SCHEMA_NAME
    assert tables.attempts.schema == DEFAULT_SCHEMA_NAME
    assert tables.results.schema == DEFAULT_SCHEMA_NAME


def test_execution_tables_has_three_tables() -> None:
    """Uc tablo tanimlanir."""
    tables = execution_tables()
    names = {
        t.name
        for t in (
            tables.executions,
            tables.attempts,
            tables.results,
        )
    }
    assert names == {
        "rule_executions",
        "execution_attempts",
        "rule_execution_results",
    }


def test_execution_tables_primary_keys() -> None:
    """Her tablonun birincil anahtari vardir."""
    tables = execution_tables()
    assert [c.name for c in tables.executions.primary_key.columns] == ["execution_id"]
    assert [c.name for c in tables.attempts.primary_key.columns] == ["attempt_id"]
    assert [c.name for c in tables.results.primary_key.columns] == ["rule_result_id"]


def test_execution_tables_unique_constraints() -> None:
    """rule_executions.idempotency_key_hash unique; execution_attempts (execution_id, attempt_no) unique;
    rule_execution_results (execution_id, rule_version_id) unique."""
    tables = execution_tables()

    # idempotency_key_hash is defined as unique=True on Column, not UniqueConstraint
    # So check the column directly
    assert tables.executions.c.idempotency_key_hash.unique

    attempt_constraints = list(tables.attempts.constraints)
    attempt_uq = [c for c in attempt_constraints if isinstance(c, UniqueConstraint)]
    assert any(
        set(c.columns.keys()) == {"execution_id", "attempt_no"}
        for c in attempt_uq
    )

    result_constraints = list(tables.results.constraints)
    result_uq = [c for c in result_constraints if isinstance(c, UniqueConstraint)]
    assert any(
        set(c.columns.keys()) == {"execution_id", "rule_version_id"}
        for c in result_uq
    )


def test_execution_tables_foreign_keys() -> None:
    """execution_attempts ve rule_execution_results rule_executions.execution_id FK'si icerir."""
    tables = execution_tables()

    attempts_fk = list(tables.attempts.foreign_keys)
    assert any(
        fk.column.table.name == "rule_executions" and fk.column.name == "execution_id"
        for fk in attempts_fk
    )

    results_fk = list(tables.results.foreign_keys)
    assert any(
        fk.column.table.name == "rule_executions" and fk.column.name == "execution_id"
        for fk in results_fk
    )


def test_execution_tables_check_constraints() -> None:
    """rule_executions execution_type, status ve workload_class CheckConstraint icerir."""
    tables = execution_tables()

    exec_cc = [c for c in tables.executions.constraints if isinstance(c, CheckConstraint)]
    assert any("execution_type" in str(c.sqltext) for c in exec_cc)
    assert any("status" in str(c.sqltext) for c in exec_cc)
    assert any("workload_class" in str(c.sqltext) for c in exec_cc)

    attempt_cc = [c for c in tables.attempts.constraints if isinstance(c, CheckConstraint)]
    assert any("status" in str(c.sqltext) for c in attempt_cc)


def test_execution_tables_json_columns() -> None:
    """rule_executions JSON sutunlari icerir."""
    tables = execution_tables()
    assert "rule_version_ids" in tables.executions.c
    assert "scope" in tables.executions.c
    assert "source_ids" in tables.executions.c
    assert "completed_partitions" in tables.results.c


def test_execution_tables_timestamptz_columns() -> None:
    """rule_executions timestamptz sutunlari icerir."""
    tables = execution_tables()
    assert "created_at" in tables.executions.c
    assert "started_at" in tables.executions.c
    assert "finished_at" in tables.executions.c
    assert "cancel_requested_at" in tables.executions.c
    assert "cancelled_at" in tables.executions.c


def test_execution_tables_custom_schema() -> None:
    """Ozel schema parametresi tum tablolara uygulanir."""
    tables = execution_tables(schema="custom")
    assert tables.executions.schema == "custom"
    assert tables.attempts.schema == "custom"
    assert tables.results.schema == "custom"