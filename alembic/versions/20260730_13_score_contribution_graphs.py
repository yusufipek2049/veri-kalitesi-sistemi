"""Değişmez açıklanabilir skor katkı grafikleri.

Revision ID: 20260730_13
Revises: 20260730_12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260730_13"
down_revision = "20260730_12"
branch_labels = None
depends_on = None


def _schema() -> str:
    return op.get_context().config.get_main_option("data_quality_schema", "dq")


def upgrade() -> None:
    schema = _schema()
    op.create_table(
        "score_contribution_graphs",
        sa.Column("quality_score_id", sa.String(36), primary_key=True),
        sa.Column("execution_id", sa.String(36), nullable=False),
        sa.Column("scope_type", sa.String(20), nullable=False),
        sa.Column("scope_id", sa.String(128)),
        sa.Column("graph", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "scope_type IN ('RULE','DATASET','DIMENSION','SOURCE','ENTERPRISE')",
            name="ck_contribution_graph_scope_type",
        ),
        schema=schema,
    )
    op.create_index(
        "ix_contribution_graph_execution_scope",
        "score_contribution_graphs",
        ["execution_id", "scope_type", "scope_id"],
        schema=schema,
    )


def downgrade() -> None:
    raise RuntimeError(
        "Production downgrade is disabled for immutable contribution graphs; "
        "create a forward corrective migration instead."
    )
