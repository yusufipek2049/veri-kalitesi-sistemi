"""Schedules ve source_usage_policies tablolari baseline.

Revision ID: 20260724_05
Revises: 20260724_04
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260724_05"
down_revision = "20260724_04"
branch_labels = None
depends_on = None


def _schema() -> str:
    return op.get_context().config.get_main_option("data_quality_schema", "dq")


def upgrade() -> None:
    schema = _schema()

    op.create_table(
        "schedules",
        sa.Column("schedule_id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False, unique=True),
        sa.Column("schedule_type", sa.String(20), nullable=False),
        sa.Column("timezone_name", sa.String(80), nullable=False),
        sa.Column("rule_version_ids", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(128), nullable=False),
        sa.Column("local_time", sa.String(10)),
        sa.Column("once_at", sa.DateTime(timezone=True)),
        sa.Column("day_of_week", sa.Integer()),
        sa.Column("day_of_month", sa.Integer()),
        sa.Column("is_active", sa.Integer(), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "schedule_type IN ('ONCE', 'DAILY', 'WEEKLY', 'MONTHLY')",
            name="ck_schedules_type",
        ),
        schema=schema,
    )
    op.create_index(
        "ix_dq_schedules_next_run",
        "schedules",
        ["next_run_at"],
        schema=schema,
        postgresql_where=sa.text("is_active = 1"),
    )

    op.create_table(
        "source_usage_policies",
        sa.Column("policy_id", sa.String(36), primary_key=True),
        sa.Column("policy_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("source_id", sa.String(36)),
        sa.Column("source_type", sa.String(40)),
        sa.Column("max_concurrent_queries", sa.Integer(), nullable=False),
        sa.Column("max_workers", sa.Integer(), nullable=False),
        sa.Column("query_timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("retry_delay_seconds", sa.Float(), nullable=False),
        sa.Column("rate_limit", sa.JSON(), nullable=False),
        sa.Column("allowed_windows", sa.JSON(), nullable=False),
        sa.Column("blocked_windows", sa.JSON(), nullable=False),
        sa.Column("cpu_limit_percent", sa.Float()),
        sa.Column("io_limit_percent", sa.Float()),
        sa.Column("peak_hours_behavior", sa.String(20), nullable=False),
        sa.Column("timeout_cancel_behavior", sa.String(20), nullable=False),
        sa.Column("approved_by", sa.String(128)),
        sa.Column("audit_reference", sa.String(200)),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'PENDING_APPROVAL', 'ACTIVE', 'RETIRED')",
            name="ck_source_usage_policies_status",
        ),
        sa.CheckConstraint(
            "NOT (source_id IS NOT NULL AND source_type IS NOT NULL)",
            name="ck_source_usage_policies_scope",
        ),
        sa.UniqueConstraint(
            "policy_version",
            "source_id",
            "source_type",
            name="uq_source_usage_policies_version_scope",
        ),
        schema=schema,
    )
    op.create_index(
        "ix_dq_source_usage_policies_active",
        "source_usage_policies",
        ["source_id", "source_type"],
        schema=schema,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )


def downgrade() -> None:
    schema = _schema()
    op.drop_table("source_usage_policies", schema=schema)
    op.drop_table("schedules", schema=schema)
