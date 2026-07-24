"""PostgreSQLDataSourceRepository icin PostgreSQL gerektirmeyen birim testleri.

Iteration 36D0 — Data sources PostgreSQL migration.
"""

from __future__ import annotations

from sqlalchemy import CheckConstraint, UniqueConstraint

from veri_kalitesi.persistence import DEFAULT_SCHEMA_NAME
from veri_kalitesi.data_sources.postgresql_repository import data_source_tables


def test_data_source_tables_uses_dq_schema() -> None:
    """data_source_tables varsayilan schema'yi kullanir."""
    tables = data_source_tables()
    assert tables.sources.schema == DEFAULT_SCHEMA_NAME
    assert tables.connection_tests.schema == DEFAULT_SCHEMA_NAME
    assert tables.datasets.schema == DEFAULT_SCHEMA_NAME
    assert tables.fields.schema == DEFAULT_SCHEMA_NAME
    assert tables.metadata_discovery.schema == DEFAULT_SCHEMA_NAME
    assert tables.profiles.schema == DEFAULT_SCHEMA_NAME
    assert tables.processing_inventory.schema == DEFAULT_SCHEMA_NAME
    assert tables.connection_revisions.schema == DEFAULT_SCHEMA_NAME
    assert tables.activation_requests.schema == DEFAULT_SCHEMA_NAME


def test_data_source_tables_has_nine_tables() -> None:
    """Dokuz tablo tanimlanir."""
    tables = data_source_tables()
    names = {
        t.name
        for t in (
            tables.sources,
            tables.connection_tests,
            tables.datasets,
            tables.fields,
            tables.metadata_discovery,
            tables.profiles,
            tables.processing_inventory,
            tables.connection_revisions,
            tables.activation_requests,
        )
    }
    assert names == {
        "data_sources",
        "connection_test_results",
        "datasets",
        "data_fields",
        "metadata_discovery_results",
        "data_profiles",
        "data_processing_inventory_versions",
        "data_source_connection_revisions",
        "data_source_activation_requests",
    }


def test_data_source_tables_primary_keys() -> None:
    """Her tablonun birincil anahtari vardir."""
    tables = data_source_tables()
    assert [c.name for c in tables.sources.primary_key.columns] == ["data_source_id"]
    assert [c.name for c in tables.datasets.primary_key.columns] == ["dataset_id"]
    assert [c.name for c in tables.fields.primary_key.columns] == ["data_field_id"]
    assert [c.name for c in tables.profiles.primary_key.columns] == ["profile_id"]
    assert [c.name for c in tables.processing_inventory.primary_key.columns] == ["inventory_id"]
    assert [c.name for c in tables.connection_revisions.primary_key.columns] == ["connection_revision_id"]
    assert [c.name for c in tables.activation_requests.primary_key.columns] == ["activation_request_id"]


def test_data_source_tables_auto_increment_primary_keys() -> None:
    """connection_test_results ve metadata_discovery autoincrement primary key kullanir."""
    tables = data_source_tables()
    assert tables.connection_tests.c.test_result_id.primary_key
    assert tables.connection_tests.c.test_result_id.autoincrement is True
    assert tables.metadata_discovery.c.discovery_id.primary_key
    assert tables.metadata_discovery.c.discovery_id.autoincrement is True


def test_data_source_tables_unique_constraints() -> None:
    """data_sources.name, datasets (source_id, namespace, name), data_fields (dataset_id, name) unique."""
    tables = data_source_tables()
    source_constraints = list(tables.sources.constraints)
    source_uq = [c for c in source_constraints if isinstance(c, UniqueConstraint)]
    assert any(set(c.columns.keys()) == {"name"} for c in source_uq)

    dataset_constraints = list(tables.datasets.constraints)
    dataset_uq = [c for c in dataset_constraints if isinstance(c, UniqueConstraint)]
    assert any(
        set(c.columns.keys()) == {"data_source_id", "namespace", "name"}
        for c in dataset_uq
    )

    field_constraints = list(tables.fields.constraints)
    field_uq = [c for c in field_constraints if isinstance(c, UniqueConstraint)]
    assert any(set(c.columns.keys()) == {"dataset_id", "name"} for c in field_uq)


def test_data_source_tables_foreign_keys() -> None:
    """Tablolar arasi FK iliskileri dogru."""
    tables = data_source_tables()

    datasets_fk = list(tables.datasets.foreign_keys)
    assert any(
        fk.column.table.name == "data_sources" and fk.column.name == "data_source_id"
        for fk in datasets_fk
    )

    fields_fk = list(tables.fields.foreign_keys)
    assert any(
        fk.column.table.name == "datasets" and fk.column.name == "dataset_id"
        for fk in fields_fk
    )

    connection_tests_fk = list(tables.connection_tests.foreign_keys)
    assert any(
        fk.column.table.name == "data_sources" and fk.column.name == "data_source_id"
        for fk in connection_tests_fk
    )

    connection_revisions_fk = list(tables.connection_revisions.foreign_keys)
    assert any(
        fk.column.table.name == "data_sources" and fk.column.name == "data_source_id"
        for fk in connection_revisions_fk
    )

    activation_requests_fk = list(tables.activation_requests.foreign_keys)
    assert any(
        fk.column.table.name == "data_sources" and fk.column.name == "data_source_id"
        for fk in activation_requests_fk
    )


def test_data_source_tables_check_constraints() -> None:
    """data_sources, data_fields, datasets, data_profiles ve connection_revisions CheckConstraint icerir."""
    tables = data_source_tables()

    source_cc = [c for c in tables.sources.constraints if isinstance(c, CheckConstraint)]
    assert any("source_type" in str(c.sqltext) for c in source_cc)
    assert any("status" in str(c.sqltext) for c in source_cc)

    field_cc = [c for c in tables.fields.constraints if isinstance(c, CheckConstraint)]
    assert any("classification" in str(c.sqltext) for c in field_cc)

    dataset_cc = [c for c in tables.datasets.constraints if isinstance(c, CheckConstraint)]
    assert any("dataset_type" in str(c.sqltext) for c in dataset_cc)
    assert any("criticality" in str(c.sqltext) for c in dataset_cc)

    profile_cc = [c for c in tables.profiles.constraints if isinstance(c, CheckConstraint)]
    assert any("method" in str(c.sqltext) for c in profile_cc)
    assert any("status" in str(c.sqltext) for c in profile_cc)

    revision_cc = [c for c in tables.connection_revisions.constraints if isinstance(c, CheckConstraint)]
    assert any("revision > 0" in str(c.sqltext) for c in revision_cc)
    assert any("base_revision > 0" in str(c.sqltext) for c in revision_cc)

    activation_cc = [c for c in tables.activation_requests.constraints if isinstance(c, CheckConstraint)]
    assert any("status" in str(c.sqltext) for c in activation_cc)


def test_data_source_tables_json_columns() -> None:
    """data_sources.connection_config, connection_test_results.source_info, data_profiles.metrics, connection_revisions.connection_config JSON türündedir."""
    tables = data_source_tables()
    assert "connection_config" in tables.sources.c
    assert "source_info" in tables.connection_tests.c
    assert "metrics" in tables.profiles.c
    assert "connection_config" in tables.connection_revisions.c
    assert "changes" in tables.metadata_discovery.c
    assert "access_role_codes" in tables.processing_inventory.c
    assert "recipient_groups" in tables.processing_inventory.c


def test_data_source_tables_boolean_columns() -> None:
    """data_fields.is_nullable, data_fields.is_sensitive, processing_inventory.cross_border_transfer Boolean türündedir."""
    tables = data_source_tables()
    assert str(tables.fields.c.is_nullable.type) == "BOOLEAN"
    assert str(tables.fields.c.is_sensitive.type) == "BOOLEAN"
    assert str(tables.processing_inventory.c.cross_border_transfer.type) == "BOOLEAN"
    assert str(tables.connection_tests.c.succeeded.type) == "BOOLEAN"
    assert str(tables.metadata_discovery.c.succeeded.type) == "BOOLEAN"