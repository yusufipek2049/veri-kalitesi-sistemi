"""Adlandırılmış SQL şablonları tablosu (SqlTemplate).

Çalıştırma ekranındaki özel SQL akışı, otomatik üretilen "Ad-hoc SQL <tarih>"
adı yerine kullanıcı tarafından adlandırılmış ve tekrar kullanılabilir
şablonlara dayanır.

Revision ID: 20260817_28
Revises: 20260816_27
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260817_28"
down_revision = "20260816_27"
branch_labels = None
depends_on = None


def _schema() -> str:
    return op.get_context().config.get_main_option("data_quality_schema", "dq")


def upgrade() -> None:
    schema = _schema()

    op.create_table(
        "sql_query_templates",
        sa.Column("template_id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("sql_text", sa.Text(), nullable=False),
        sa.Column("default_timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("default_row_limit", sa.Integer(), nullable=False),
        sa.Column("owner_user_id", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.CheckConstraint("length(btrim(name)) > 0", name="ck_sql_query_templates_name"),
        sa.CheckConstraint(
            "default_timeout_seconds BETWEEN 1 AND 300",
            name="ck_sql_query_templates_timeout",
        ),
        sa.CheckConstraint(
            "default_row_limit BETWEEN 1 AND 100000",
            name="ck_sql_query_templates_row_limit",
        ),
        sa.CheckConstraint("version > 0", name="ck_sql_query_templates_version"),
        schema=schema,
    )
    # Ad benzersizliği büyük/küçük harften bağımsız uygulanır.
    op.execute(
        f"""
        CREATE UNIQUE INDEX ux_sql_query_templates_name
        ON "{schema}".sql_query_templates (lower(name))
        """
    )
    op.create_index(
        "ix_sql_query_templates_owner",
        "sql_query_templates",
        ["owner_user_id"],
        schema=schema,
    )


def downgrade() -> None:
    """Üretim politikası ileri düzeltmedir; downgrade yalnız Alembic sözleşmesi içindir."""

    schema = _schema()
    op.drop_index(
        "ix_sql_query_templates_owner",
        table_name="sql_query_templates",
        schema=schema,
    )
    op.execute(f'DROP INDEX IF EXISTS "{schema}".ux_sql_query_templates_name')
    op.drop_table("sql_query_templates", schema=schema)
