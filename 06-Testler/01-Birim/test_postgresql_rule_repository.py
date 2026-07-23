"""PostgreSQLRuleRepository icin PostgreSQL gerektirmeyen birim testleri.

Iteration 36C0 — Rules PostgreSQL migration.
"""

from __future__ import annotations

from sqlalchemy import UniqueConstraint

from veri_kalitesi.persistence import DEFAULT_SCHEMA_NAME
from veri_kalitesi.rules.postgresql_repository import rule_tables


def test_rule_tables_uses_dq_schema() -> None:
    """rule_tables varsayilan schema'yi kullanir."""
    tables = rule_tables()
    assert tables.rules.schema == DEFAULT_SCHEMA_NAME
    assert tables.versions.schema == DEFAULT_SCHEMA_NAME
    assert tables.test_results.schema == DEFAULT_SCHEMA_NAME
    assert tables.approval_requests.schema == DEFAULT_SCHEMA_NAME


def test_rule_tables_has_four_tables() -> None:
    """Dort tablo tanimlanir."""
    tables = rule_tables()
    names = {t.name for t in (tables.rules, tables.versions, tables.test_results, tables.approval_requests)}
    assert names == {"quality_rules", "rule_versions", "rule_test_results", "rule_approval_requests"}


def test_rule_tables_primary_keys() -> None:
    """Her tablonun birincil anahtari vardir."""
    tables = rule_tables()
    pk_rules = [c.name for c in tables.rules.primary_key.columns]
    pk_versions = [c.name for c in tables.versions.primary_key.columns]
    pk_results = [c.name for c in tables.test_results.primary_key.columns]
    pk_approvals = [c.name for c in tables.approval_requests.primary_key.columns]
    assert pk_rules == ["quality_rule_id"]
    assert pk_versions == ["rule_version_id"]
    assert pk_results == ["rule_test_result_id"]
    assert pk_approvals == ["approval_request_id"]


def test_rule_tables_has_unique_constraint_on_versions() -> None:
    """rule_versions tablosunda (quality_rule_id, version_no) unique constraint vardir."""
    tables = rule_tables()
    constraints = list(tables.versions.constraints)
    uq = [c for c in constraints if isinstance(c, UniqueConstraint)]
    assert any(
        set(c.columns.keys()) == {"quality_rule_id", "version_no"} for c in uq
    )


def test_rule_tables_has_foreign_keys() -> None:
    """rule_versions FK -> quality_rules, test_results FK -> rule_versions, approval_requests FK -> rule_versions."""
    tables = rule_tables()

    versions_fk = list(tables.versions.foreign_keys)
    results_fk = list(tables.test_results.foreign_keys)
    approvals_fk = list(tables.approval_requests.foreign_keys)

    assert any(
        fk.column.table.name == "quality_rules" and fk.column.name == "quality_rule_id"
        for fk in versions_fk
    )
    assert any(
        fk.column.table.name == "rule_versions" and fk.column.name == "rule_version_id"
        for fk in results_fk
    )
    assert any(
        fk.column.table.name == "rule_versions" and fk.column.name == "rule_version_id"
        for fk in approvals_fk
    )


def test_rule_tables_has_json_columns() -> None:
    """quality_rules.field_ids ve rule_versions.definition JSON türündedir."""
    tables = rule_tables()
    assert "field_ids" in tables.rules.c
    assert "definition" in tables.versions.c


def test_rule_tables_has_timestamptz_columns() -> None:
    """rule_versions.created_at, approval_requests.*_at timestamptz alanlaridir."""
    tables = rule_tables()
    assert "created_at" in tables.versions.c
    assert "requested_at" in tables.approval_requests.c
    assert "target_at" in tables.approval_requests.c
    assert "expires_at" in tables.approval_requests.c
    assert "decided_at" in tables.approval_requests.c


def test_custom_schema_is_applied() -> None:
    """Ozel schema parametresi tablo metadata'sina uygulanir."""
    custom_schema = "custom_schema"
    tables = rule_tables(schema=custom_schema)
    assert tables.rules.schema == custom_schema
    assert tables.versions.schema == custom_schema
    assert tables.test_results.schema == custom_schema
    assert tables.approval_requests.schema == custom_schema