"""Katalog ve metadata keşfi — async lifecycle, diff ve scope yönetimi.

Revision ID: 20260805_17
Revises: 20260805_16

DS-04 dikey dilimi:
  1. discovery_scopes tablosu
  2. metadata_discovery_results async lifecycle kolonları + backfill
  3. metadata_diffs tablosu
  4. datasets lifecycle kolonları + dataset_type domain düzeltme
  5. data_fields lifecycle kolonları
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260805_17"
down_revision = "20260805_16"
branch_labels = None
depends_on = None


def _schema() -> str:
    return op.get_context().config.get_main_option("data_quality_schema", "dq")


def upgrade() -> None:
    schema = _schema()

    # ── 1. discovery_scopes ──
    op.create_table(
        "discovery_scopes",
        sa.Column("data_source_id", sa.String(36), primary_key=True),
        sa.Column("include_patterns", sa.JSON(), nullable=False),
        sa.Column("exclude_patterns", sa.JSON(), nullable=False),
        sa.Column("page_size", sa.Integer(), nullable=False),
        sa.Column("max_objects", sa.Integer(), nullable=False),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("policy_version", sa.String(100), nullable=False),
        sa.Column("updated_by_actor_id", sa.String(128), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.ForeignKeyConstraint(
            ["data_source_id"],
            [f"{schema}.data_sources.data_source_id"],
        ),
        sa.CheckConstraint(
            "page_size >= 1 AND page_size <= 10000", name="ck_discovery_scopes_page_size"
        ),
        sa.CheckConstraint(
            "max_objects >= 1 AND max_objects <= 100000", name="ck_discovery_scopes_max_objects"
        ),
        sa.CheckConstraint(
            "timeout_seconds >= 1 AND timeout_seconds <= 3600",
            name="ck_discovery_scopes_timeout",
        ),
        sa.CheckConstraint("version >= 1", name="ck_discovery_scopes_version"),
        schema=schema,
    )

    # ── 2. metadata_discovery_results: async lifecycle kolonları ──
    op.add_column(
        "metadata_discovery_results",
        sa.Column("status", sa.String(30)),
        schema=schema,
    )
    op.add_column(
        "metadata_discovery_results",
        sa.Column("job_id", sa.String(36)),
        schema=schema,
    )
    op.add_column(
        "metadata_discovery_results",
        sa.Column("requested_by_actor_id", sa.String(128)),
        schema=schema,
    )
    op.add_column(
        "metadata_discovery_results",
        sa.Column("correlation_id", sa.String(128)),
        schema=schema,
    )
    op.add_column(
        "metadata_discovery_results",
        sa.Column("scope_version", sa.Integer()),
        schema=schema,
    )
    op.add_column(
        "metadata_discovery_results",
        sa.Column(
            "completed_scope",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        schema=schema,
    )
    op.add_column(
        "metadata_discovery_results",
        sa.Column("partial_reason_code", sa.String(100)),
        schema=schema,
    )
    op.add_column(
        "metadata_discovery_results",
        sa.Column("started_at", sa.DateTime(timezone=True)),
        schema=schema,
    )
    op.add_column(
        "metadata_discovery_results",
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        schema=schema,
    )
    op.add_column(
        "metadata_discovery_results",
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        schema=schema,
    )

    # ── 2a. Legacy backfill: succeeded → status ──
    op.execute(
        f'UPDATE "{schema}"."metadata_discovery_results" '
        f"SET status = CASE WHEN succeeded THEN 'SUCCESS' ELSE 'TECHNICAL_ERROR' END "
        f"WHERE status IS NULL"
    )
    op.execute(
        f'UPDATE "{schema}"."metadata_discovery_results" '
        f"SET finished_at = discovered_at, started_at = discovered_at "
        f"WHERE started_at IS NULL"
    )
    op.execute(
        f'UPDATE "{schema}"."metadata_discovery_results" '
        f"SET completed_scope = '{{}}'::jsonb "
        f"WHERE completed_scope IS NULL"
    )

    # status NOT NULL yap
    op.alter_column(
        "metadata_discovery_results",
        "status",
        existing_type=sa.String(30),
        nullable=False,
        schema=schema,
    )

    # status check constraint
    op.create_check_constraint(
        "ck_metadata_discovery_results_status",
        "metadata_discovery_results",
        "status IN ('QUEUED', 'RUNNING', 'SUCCESS', 'PARTIAL', 'TECHNICAL_ERROR', 'CANCELLED')",
        schema=schema,
    )
    op.create_check_constraint(
        "ck_metadata_discovery_results_version",
        "metadata_discovery_results",
        "version >= 1",
        schema=schema,
    )

    # job_id unique (nullable legacy uyumu)
    op.create_unique_constraint(
        "uq_metadata_discovery_results_job",
        "metadata_discovery_results",
        ["job_id"],
        schema=schema,
    )

    # ── 3. metadata_diffs ──
    op.create_table(
        "metadata_diffs",
        sa.Column("metadata_diff_id", sa.String(36), primary_key=True),
        sa.Column(
            "discovery_id",
            sa.BigInteger(),
            sa.ForeignKey(f"{schema}.metadata_discovery_results.discovery_id"),
            nullable=False,
        ),
        sa.Column(
            "data_source_id",
            sa.String(36),
            sa.ForeignKey(f"{schema}.data_sources.data_source_id"),
            nullable=False,
        ),
        sa.Column("added_objects", sa.JSON(), nullable=False),
        sa.Column("changed_objects", sa.JSON(), nullable=False),
        sa.Column("removed_objects", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column(
            "requires_rule_review", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True)),
        sa.Column("applied_by_actor_id", sa.String(128)),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.CheckConstraint(
            "status IN ('PENDING', 'APPLIED')",
            name="ck_metadata_diffs_status",
        ),
        sa.CheckConstraint("version >= 1", name="ck_metadata_diffs_version"),
        schema=schema,
    )
    op.create_unique_constraint(
        "uq_metadata_diffs_discovery",
        "metadata_diffs",
        ["discovery_id"],
        schema=schema,
    )
    op.create_index(
        "ix_dq_metadata_diffs_source_status",
        "metadata_diffs",
        ["data_source_id", "status", "created_at"],
        schema=schema,
    )

    # ── 4. datasets: lifecycle + dataset_type düzeltme ──

    # 4a. dataset_type değer dönüşümü
    op.execute(
        f'UPDATE "{schema}"."datasets" SET dataset_type = \'FILE_SHEET\' '
        f"WHERE dataset_type = 'FILE'"
    )
    op.execute(
        f'UPDATE "{schema}"."datasets" SET dataset_type = \'API_COLLECTION\' '
        f"WHERE dataset_type = 'API'"
    )

    # OTHER fail-fast
    other_count_result = op.get_bind().execute(
        sa.text(f'SELECT COUNT(*) FROM "{schema}"."datasets" WHERE dataset_type = \'OTHER\'')
    )
    other_count = other_count_result.scalar()
    if other_count and other_count > 0:
        raise RuntimeError(
            f"Migration 17 cannot proceed: {other_count} dataset row(s) have "
            f"dataset_type='OTHER'. RemEDIATE these rows to TABLE, VIEW, FILE_SHEET, "
            f"or API_COLLECTION before re-running this migration."
        )

    # check constraint güncelle
    op.drop_constraint(
        "ck_datasets_dataset_type",
        "datasets",
        schema=schema,
        type_="check",
    )
    op.create_check_constraint(
        "ck_datasets_dataset_type",
        "datasets",
        "dataset_type IN ('TABLE', 'VIEW', 'FILE_SHEET', 'API_COLLECTION')",
        schema=schema,
    )

    # 4b. lifecycle kolonları
    op.add_column(
        "datasets",
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'ACTIVE'"),
        ),
        schema=schema,
    )
    op.add_column(
        "datasets",
        sa.Column("first_seen_discovery_id", sa.BigInteger()),
        schema=schema,
    )
    op.add_column(
        "datasets",
        sa.Column("last_seen_discovery_id", sa.BigInteger()),
        schema=schema,
    )
    op.add_column(
        "datasets",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        schema=schema,
    )
    op.add_column(
        "datasets",
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        schema=schema,
    )

    op.create_check_constraint(
        "ck_datasets_status",
        "datasets",
        "status IN ('ACTIVE', 'INACTIVE')",
        schema=schema,
    )
    op.create_check_constraint(
        "ck_datasets_version",
        "datasets",
        "version >= 1",
        schema=schema,
    )
    op.create_foreign_key(
        "fk_datasets_first_discovery",
        "datasets",
        "metadata_discovery_results",
        ["first_seen_discovery_id"],
        ["discovery_id"],
        source_schema=schema,
        referent_schema=schema,
    )
    op.create_foreign_key(
        "fk_datasets_last_discovery",
        "datasets",
        "metadata_discovery_results",
        ["last_seen_discovery_id"],
        ["discovery_id"],
        source_schema=schema,
        referent_schema=schema,
    )

    # ── 5. data_fields: lifecycle kolonları ──
    op.add_column(
        "data_fields",
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'ACTIVE'"),
        ),
        schema=schema,
    )
    op.add_column(
        "data_fields",
        sa.Column("first_seen_discovery_id", sa.BigInteger()),
        schema=schema,
    )
    op.add_column(
        "data_fields",
        sa.Column("last_seen_discovery_id", sa.BigInteger()),
        schema=schema,
    )
    op.add_column(
        "data_fields",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        schema=schema,
    )
    op.add_column(
        "data_fields",
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        schema=schema,
    )

    op.create_check_constraint(
        "ck_data_fields_status",
        "data_fields",
        "status IN ('ACTIVE', 'INACTIVE')",
        schema=schema,
    )
    op.create_check_constraint(
        "ck_data_fields_version",
        "data_fields",
        "version >= 1",
        schema=schema,
    )
    op.create_foreign_key(
        "fk_data_fields_first_discovery",
        "data_fields",
        "metadata_discovery_results",
        ["first_seen_discovery_id"],
        ["discovery_id"],
        source_schema=schema,
        referent_schema=schema,
    )
    op.create_foreign_key(
        "fk_data_fields_last_discovery",
        "data_fields",
        "metadata_discovery_results",
        ["last_seen_discovery_id"],
        ["discovery_id"],
        source_schema=schema,
        referent_schema=schema,
    )


def downgrade() -> None:
    """Üretim politikası ileri düzeltmedir; downgrade yalnız Alembic sözleşmesi içindir."""

    schema = _schema()

    # data_fields lifecycle kaldır
    for fk_name in ("fk_data_fields_last_discovery", "fk_data_fields_first_discovery"):
        op.drop_constraint(fk_name, "data_fields", schema=schema, type_="foreignkey")
    op.drop_constraint("ck_data_fields_version", "data_fields", schema=schema, type_="check")
    op.drop_constraint("ck_data_fields_status", "data_fields", schema=schema, type_="check")
    for col in (
        "version",
        "updated_at",
        "last_seen_discovery_id",
        "first_seen_discovery_id",
        "status",
    ):
        op.drop_column("data_fields", col, schema=schema)

    # datasets lifecycle + type kaldır
    for fk_name in ("fk_datasets_last_discovery", "fk_datasets_first_discovery"):
        op.drop_constraint(fk_name, "datasets", schema=schema, type_="foreignkey")
    op.drop_constraint("ck_datasets_version", "datasets", schema=schema, type_="check")
    op.drop_constraint("ck_datasets_status", "datasets", schema=schema, type_="check")
    for col in (
        "version",
        "updated_at",
        "last_seen_discovery_id",
        "first_seen_discovery_id",
        "status",
    ):
        op.drop_column("datasets", col, schema=schema)

    op.drop_constraint("ck_datasets_dataset_type", "datasets", schema=schema, type_="check")
    op.create_check_constraint(
        "ck_datasets_dataset_type",
        "datasets",
        "dataset_type IN ('TABLE', 'VIEW', 'FILE', 'API', 'OTHER')",
        schema=schema,
    )
    op.execute(
        f'UPDATE "{schema}"."datasets" SET dataset_type = \'FILE\' '
        f"WHERE dataset_type = 'FILE_SHEET'"
    )
    op.execute(
        f'UPDATE "{schema}"."datasets" SET dataset_type = \'API\' '
        f"WHERE dataset_type = 'API_COLLECTION'"
    )

    # metadata_diffs kaldır
    op.drop_index(
        "ix_dq_metadata_diffs_source_status",
        table_name="metadata_diffs",
        schema=schema,
    )
    op.drop_table("metadata_diffs", schema=schema)

    # metadata_discovery_results kolonlarını kaldır
    op.drop_constraint(
        "uq_metadata_discovery_results_job",
        "metadata_discovery_results",
        schema=schema,
        type_="unique",
    )
    op.drop_constraint(
        "ck_metadata_discovery_results_version",
        "metadata_discovery_results",
        schema=schema,
        type_="check",
    )
    op.drop_constraint(
        "ck_metadata_discovery_results_status",
        "metadata_discovery_results",
        schema=schema,
        type_="check",
    )
    for col in (
        "version",
        "finished_at",
        "started_at",
        "partial_reason_code",
        "completed_scope",
        "scope_version",
        "correlation_id",
        "requested_by_actor_id",
        "job_id",
        "status",
    ):
        op.drop_column("metadata_discovery_results", col, schema=schema)

    # discovery_scopes kaldır
    op.drop_table("discovery_scopes", schema=schema)
