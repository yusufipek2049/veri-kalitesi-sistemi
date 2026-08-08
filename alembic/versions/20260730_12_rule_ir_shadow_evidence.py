"""Sürümlü kural IR, shadow yürütme ve veri-minimum kanıt alanları.

Revision ID: 20260730_12
Revises: 20260729_11
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260730_12"
down_revision = "20260729_11"
branch_labels = None
depends_on = None


def _schema() -> str:
    return op.get_context().config.get_main_option("data_quality_schema", "dq")


def upgrade() -> None:
    schema = _schema()
    op.add_column(
        "rule_executions",
        sa.Column(
            "execution_mode",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'OFFICIAL'"),
        ),
        schema=schema,
    )
    op.create_check_constraint(
        "ck_execution_mode",
        "rule_executions",
        "execution_mode IN ('OFFICIAL', 'SHADOW')",
        schema=schema,
    )
    for name in (
        "eligible_for_notification",
        "eligible_for_sla",
        "eligible_for_auto_issue",
    ):
        op.add_column(
            "rule_execution_results",
            sa.Column(
                name,
                sa.Integer(),
                nullable=False,
                server_default=sa.text("1"),
            ),
            schema=schema,
        )
    op.add_column(
        "rule_execution_results",
        sa.Column(
            "evidence",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
        schema=schema,
    )


def downgrade() -> None:
    raise RuntimeError(
        "Production downgrade is disabled for rule IR/shadow evidence fields; "
        "create a forward corrective migration instead."
    )
