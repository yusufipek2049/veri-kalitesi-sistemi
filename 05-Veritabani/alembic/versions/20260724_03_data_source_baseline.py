"""DataSource, dataset, field, profil, connection revision ve activation request baseline.

Revision ID: 20260724_03
Revises: 20260723_02
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260724_03"
down_revision = "20260723_02"
branch_labels = None
depends_on = None


def _schema() -> str:
    return op.get_context().config.get_main_option("data_quality_schema", "dq")


def upgrade() -> None:
    schema = _schema()

    op.create_table(
        "data_sources",
        sa.Column("data_source_id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(400), nullable=False),
        sa.Column("source_type", sa.String(40), nullable=False),
        sa.Column("connection_config", sa.JSON(), nullable=False),
        sa.Column("secret_reference", sa.String(500), nullable=False),
        sa.Column("owner_user_id", sa.String(128), nullable=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("last_test_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "source_type IN ('CSV', 'POSTGRESQL', 'MSSQL', 'ORACLE', 'MYSQL', 'REST_API', 'OTHER')",
            name="ck_data_sources_source_type",
        ),
        sa.CheckConstraint(
            "status IN ('PASSIVE', 'TEST_SUCCEEDED', 'TEST_FAILED', 'ACTIVE', 'INACTIVE', 'ARCHIVED')",
            name="ck_data_sources_status",
        ),
        sa.UniqueConstraint("name", name="uq_data_sources_name"),
        schema=schema,
    )
    op.create_index(
        "ix_dq_data_sources_status",
        "data_sources",
        ["status"],
        schema=schema,
    )

    op.create_table(
        "connection_test_results",
        sa.Column("test_result_id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("data_source_id", sa.String(36), nullable=False),
        sa.Column("succeeded", sa.Boolean(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("error_class", sa.String(40), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("source_info", sa.JSON(), nullable=False),
        sa.Column("data_source_revision", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("tested_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["data_source_id"],
            [f"{schema}.data_sources.data_source_id"],
        ),
        schema=schema,
    )
    op.create_index(
        "ix_dq_connection_test_results_source",
        "connection_test_results",
        ["data_source_id", "data_source_revision"],
        schema=schema,
    )

    op.create_table(
        "datasets",
        sa.Column("dataset_id", sa.String(36), primary_key=True),
        sa.Column("data_source_id", sa.String(36), nullable=False),
        sa.Column("namespace", sa.String(200), nullable=False),
        sa.Column("name", sa.String(400), nullable=False),
        sa.Column("dataset_type", sa.String(40), nullable=False),
        sa.Column("criticality", sa.String(20), nullable=False),
        sa.Column("owner_user_id", sa.String(128), nullable=True),
        sa.Column("estimated_row_count", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["data_source_id"],
            [f"{schema}.data_sources.data_source_id"],
        ),
        sa.UniqueConstraint(
            "data_source_id", "namespace", "name",
            name="uq_datasets_source_namespace_name",
        ),
        sa.CheckConstraint(
            "dataset_type IN ('TABLE', 'VIEW', 'FILE', 'API', 'OTHER')",
            name="ck_datasets_dataset_type",
        ),
        sa.CheckConstraint(
            "criticality IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="ck_datasets_criticality",
        ),
        schema=schema,
    )
    op.create_index(
        "ix_dq_datasets_source",
        "datasets",
        ["data_source_id"],
        schema=schema,
    )

    op.create_table(
        "data_fields",
        sa.Column("data_field_id", sa.String(36), primary_key=True),
        sa.Column("dataset_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(400), nullable=False),
        sa.Column("native_data_type", sa.String(100), nullable=False),
        sa.Column("is_nullable", sa.Boolean(), nullable=False),
        sa.Column("is_sensitive", sa.Boolean(), nullable=False),
        sa.Column("classification", sa.String(40), nullable=False, server_default=sa.text("'UNCLASSIFIED'")),
        sa.Column("classification_policy_version", sa.String(40), nullable=False,
                  server_default=sa.text("'CLASSIFICATION_POLICY_V1'")),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            [f"{schema}.datasets.dataset_id"],
        ),
        sa.UniqueConstraint("dataset_id", "name", name="uq_data_fields_dataset_name"),
        sa.CheckConstraint(
            "classification IN ('UNCLASSIFIED', 'PUBLIC', 'INTERNAL', 'CONFIDENTIAL', "
            "'RESTRICTED', 'PERSONAL_DATA', 'SPECIAL_CATEGORY_PERSONAL_DATA', "
            "'CUSTOMER_SECRET', 'BANK_SECRET')",
            name="ck_data_fields_classification",
        ),
        schema=schema,
    )
    op.create_index(
        "ix_dq_data_fields_dataset",
        "data_fields",
        ["dataset_id"],
        schema=schema,
    )

    op.create_table(
        "metadata_discovery_results",
        sa.Column("discovery_id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("data_source_id", sa.String(36), nullable=False),
        sa.Column("succeeded", sa.Boolean(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("scanned_object_count", sa.Integer(), nullable=False),
        sa.Column("error_class", sa.String(40), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("changes", sa.JSON(), nullable=False),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["data_source_id"],
            [f"{schema}.data_sources.data_source_id"],
        ),
        schema=schema,
    )
    op.create_index(
        "ix_dq_metadata_discovery_results_source",
        "metadata_discovery_results",
        ["data_source_id", "discovery_id"],
        schema=schema,
    )

    op.create_table(
        "data_profiles",
        sa.Column("profile_id", sa.String(36), primary_key=True),
        sa.Column("dataset_id", sa.String(36), nullable=False),
        sa.Column("execution_id", sa.String(36), nullable=False),
        sa.Column("method", sa.String(20), nullable=False),
        sa.Column("sample_ratio", sa.Float(), nullable=True),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("error_class", sa.String(40), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            [f"{schema}.datasets.dataset_id"],
        ),
        sa.CheckConstraint(
            "method IN ('FULL', 'SAMPLE')",
            name="ck_data_profiles_method",
        ),
        sa.CheckConstraint(
            "status IN ('COMPLETED', 'FAILED', 'TIMEOUT', 'CANCELLED')",
            name="ck_data_profiles_status",
        ),
        schema=schema,
    )
    op.create_index(
        "ix_dq_data_profiles_dataset",
        "data_profiles",
        ["dataset_id"],
        schema=schema,
    )

    op.create_table(
        "data_processing_inventory_versions",
        sa.Column("inventory_id", sa.String(36), primary_key=True),
        sa.Column("data_field_id", sa.String(36), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("processing_purpose", sa.Text(), nullable=False),
        sa.Column("legal_basis_reference", sa.Text(), nullable=False),
        sa.Column("data_owner_id", sa.String(128), nullable=False),
        sa.Column("retention_policy_id", sa.String(40), nullable=False),
        sa.Column("access_role_codes", sa.JSON(), nullable=False),
        sa.Column("cross_border_transfer", sa.Boolean(), nullable=False),
        sa.Column("recipient_groups", sa.JSON(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["data_field_id"],
            [f"{schema}.data_fields.data_field_id"],
        ),
        sa.UniqueConstraint(
            "data_field_id", "version_number",
            name="uq_processing_inventory_field_version",
        ),
        sa.CheckConstraint(
            "version_number > 0",
            name="ck_processing_inventory_version_number",
        ),
        schema=schema,
    )
    op.create_index(
        "ix_dq_processing_inventory_field",
        "data_processing_inventory_versions",
        ["data_field_id", "version_number"],
        schema=schema,
    )

    op.create_table(
        "data_source_connection_revisions",
        sa.Column("connection_revision_id", sa.String(36), primary_key=True),
        sa.Column("data_source_id", sa.String(36), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("base_revision", sa.Integer(), nullable=False),
        sa.Column("connection_config", sa.JSON(), nullable=False),
        sa.Column("secret_reference", sa.String(500), nullable=False),
        sa.Column("prepared_by_actor_id", sa.String(128), nullable=False),
        sa.Column("policy_version", sa.String(40), nullable=False),
        sa.Column("reason_code", sa.String(100), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["data_source_id"],
            [f"{schema}.data_sources.data_source_id"],
        ),
        sa.UniqueConstraint(
            "data_source_id", "revision",
            name="uq_connection_revisions_source_revision",
        ),
        sa.CheckConstraint(
            "revision > 0",
            name="ck_connection_revisions_revision",
        ),
        sa.CheckConstraint(
            "base_revision > 0",
            name="ck_connection_revisions_base_revision",
        ),
        sa.CheckConstraint(
            "status IN ('PENDING_TEST', 'PROMOTED', 'TEST_FAILED', 'REJECTED')",
            name="ck_connection_revisions_status",
        ),
        schema=schema,
    )
    op.create_index(
        "ix_dq_connection_revisions_source",
        "data_source_connection_revisions",
        ["data_source_id", "revision"],
        schema=schema,
    )

    op.create_table(
        "data_source_activation_requests",
        sa.Column("activation_request_id", sa.String(36), primary_key=True),
        sa.Column("data_source_id", sa.String(36), nullable=False),
        sa.Column("data_source_revision", sa.Integer(), nullable=False),
        sa.Column("maker_actor_id", sa.String(128), nullable=False),
        sa.Column("checker_actor_id", sa.String(128), nullable=True),
        sa.Column("policy_version", sa.String(40), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("decision_reason_code", sa.String(100), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("target_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("business_calendar_version", sa.String(40), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["data_source_id"],
            [f"{schema}.data_sources.data_source_id"],
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'APPROVED', 'REJECTED', 'WITHDRAWN', 'EXPIRED', 'INVALIDATED')",
            name="ck_activation_requests_status",
        ),
        schema=schema,
    )
    op.create_index(
        "ix_dq_activation_requests_source",
        "data_source_activation_requests",
        ["data_source_id", "data_source_revision"],
        schema=schema,
    )
    op.create_index(
        "ix_dq_activation_requests_status",
        "data_source_activation_requests",
        ["status"],
        schema=schema,
        postgresql_where=sa.text("status = 'PENDING'"),
    )


def downgrade() -> None:
    schema = _schema()
    op.drop_table("data_source_activation_requests", schema=schema)
    op.drop_table("data_source_connection_revisions", schema=schema)
    op.drop_table("data_processing_inventory_versions", schema=schema)
    op.drop_table("data_profiles", schema=schema)
    op.drop_table("metadata_discovery_results", schema=schema)
    op.drop_table("data_fields", schema=schema)
    op.drop_table("datasets", schema=schema)
    op.drop_table("connection_test_results", schema=schema)
    op.drop_table("data_sources", schema=schema)