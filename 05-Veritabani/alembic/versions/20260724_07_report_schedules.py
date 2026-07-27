"""Report schedules tablosu — FR-076 zamanlanmis rapor uretimi.

Revision ID: 20260724_07
Revises: 20260724_06
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260724_07"
down_revision = "20260724_06"
branch_labels = None
depends_on = None


def _schema() -> str:
    return op.get_context().config.get_main_option("data_quality_schema", "dq")


def upgrade() -> None:
    schema = _schema()

    op.create_table(
        "report_schedules",
        sa.Column("schedule_id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False, unique=True),
        sa.Column("report_type", sa.String(30), nullable=False),
        sa.Column("format", sa.String(10), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("sensitivity_level", sa.String(100)),
        sa.Column("recipients", sa.JSON(), nullable=False),
        sa.Column("schedule_type", sa.String(20), nullable=False),
        sa.Column("timezone_name", sa.String(80), nullable=False),
        sa.Column("local_time", sa.String(10)),
        sa.Column("once_at", sa.DateTime(timezone=True)),
        sa.Column("day_of_week", sa.Integer()),
        sa.Column("day_of_month", sa.Integer()),
        sa.Column("is_active", sa.Integer(), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "report_type IN ('SUMMARY', 'DETAIL', 'TREND', 'UNIT', 'OWNER', "
            "'CRITICAL_DATA', 'ISSUE_PERFORMANCE')",
            name="ck_report_schedules_type",
        ),
        sa.CheckConstraint(
            "format IN ('PDF', 'XLSX', 'CSV')",
            name="ck_report_schedules_format",
        ),
        sa.CheckConstraint(
            "schedule_type IN ('ONCE', 'DAILY', 'WEEKLY', 'MONTHLY')",
            name="ck_report_schedules_schedule_type",
        ),
        schema=schema,
    )
    op.create_index(
        "ix_dq_report_schedules_next_run",
        "report_schedules",
        ["next_run_at"],
        schema=schema,
        postgresql_where=sa.text("is_active = 1"),
    )


def downgrade() -> None:
    schema = _schema()
    op.drop_index("ix_dq_report_schedules_next_run", table_name="report_schedules", schema=schema)
    op.drop_table("report_schedules", schema=schema)