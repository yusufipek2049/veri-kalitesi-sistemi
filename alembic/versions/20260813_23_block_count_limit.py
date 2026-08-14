"""Block count tracking to prevent infinite SOURCE_POLICY_DENIED retry storms.

Revision ID: 20260813_23
Revises: 20260810_22
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260813_23"
down_revision = "20260810_22"
branch_labels = None
depends_on = None


def _schema() -> str:
    return op.get_context().config.get_main_option("data_quality_schema", "dq")


def upgrade() -> None:
    schema = _schema()
    op.add_column(
        "background_jobs",
        sa.Column(
            "block_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        schema=schema,
    )
    op.add_column(
        "background_jobs",
        sa.Column(
            "max_blocks",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("10"),
        ),
        schema=schema,
    )
    op.create_check_constraint(
        "ck_background_jobs_block_count",
        "background_jobs",
        "block_count >= 0",
        schema=schema,
    )
    op.create_check_constraint(
        "ck_background_jobs_max_blocks",
        "background_jobs",
        "max_blocks > 0",
        schema=schema,
    )


def downgrade() -> None:
    """Üretim politikası ileri düzeltmedir; downgrade yalnız Alembic sözleşmesi içindir."""

    schema = _schema()
    op.drop_constraint(
        "ck_background_jobs_max_blocks",
        "background_jobs",
        schema=schema,
        type_="check",
    )
    op.drop_constraint(
        "ck_background_jobs_block_count",
        "background_jobs",
        schema=schema,
        type_="check",
    )
    op.drop_column("background_jobs", "max_blocks", schema=schema)
    op.drop_column("background_jobs", "block_count", schema=schema)
