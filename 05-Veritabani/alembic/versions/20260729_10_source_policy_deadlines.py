"""Kaynak politikası bağlantı ve toplam iş deadline alanları.

Revision ID: 20260729_10
Revises: 20260729_09
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260729_10"
down_revision = "20260729_09"
branch_labels = None
depends_on = None


def _schema() -> str:
    return op.get_context().config.get_main_option("data_quality_schema", "dq")


def upgrade() -> None:
    schema = _schema()
    op.add_column(
        "source_usage_policies",
        sa.Column(
            "connection_timeout_seconds",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("15"),
        ),
        schema=schema,
    )
    op.add_column(
        "source_usage_policies",
        sa.Column(
            "total_job_timeout_seconds",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("3600"),
        ),
        schema=schema,
    )


def downgrade() -> None:
    """Üretim politikası ileri düzeltmedir; downgrade yalnız Alembic sözleşmesi içindir."""

    schema = _schema()
    op.drop_column(
        "source_usage_policies",
        "total_job_timeout_seconds",
        schema=schema,
    )
    op.drop_column(
        "source_usage_policies",
        "connection_timeout_seconds",
        schema=schema,
    )
