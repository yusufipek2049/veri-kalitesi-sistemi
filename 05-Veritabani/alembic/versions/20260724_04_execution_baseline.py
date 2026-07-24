"""Execution, attempt ve sonuc tablolari baseline.

Revision ID: 20260724_04
Revises: 20260724_03
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260724_04"
down_revision = "20260724_03"
branch_labels = None
depends_on = None


def _schema() -> str:
    return op.get_context().config.get_main_option("data_quality_schema", "dq")


def upgrade() -> None:
    schema = _schema()

    op.create_table(
        "rule_executions",
        sa.Column("execution_id", sa.String(36), primary_key=True),
        sa.Column("execution_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("idempotency_key_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("rule_version_ids", sa.JSON(), nullable=False),
        sa.Column("scope", sa.JSON(), nullable=False),
        sa.Column("triggered_by", sa.String(128), nullable=False),
        sa.Column("correlation_id", sa.String(36), nullable=False),
        sa.Column("source_ids", sa.JSON(), nullable=False),
        sa.Column("workload_class", sa.String(20), nullable=False),
        sa.Column("error_class", sa.String(200)),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("cancel_requested_at", sa.DateTime(timezone=True)),
        sa.Column("cancel_requested_by", sa.String(128)),
        sa.Column("cancel_reason", sa.String(500)),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "execution_type IN ('MANUAL', 'SCHEDULED')",
            name="ck_execution_type",
        ),
        sa.CheckConstraint(
            "status IN ('QUEUED', 'RUNNING', 'CANCEL_REQUESTED', 'SUCCESS', "
            "'PARTIAL', 'TECHNICAL_ERROR', 'TIMEOUT', 'CANCELLED')",
            name="ck_execution_status",
        ),
        sa.CheckConstraint(
            "workload_class IN ('HEAVY', 'LIGHT')",
            name="ck_execution_workload_class",
        ),
        schema=schema,
    )

    op.create_table(
        "execution_attempts",
        sa.Column("attempt_id", sa.String(36), primary_key=True),
        sa.Column(
            "execution_id",
            sa.String(36),
            sa.ForeignKey(f"{schema}.rule_executions.execution_id"),
            nullable=False,
        ),
        sa.Column("attempt_no", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("error_class", sa.String(200)),
        sa.Column("retryable", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("execution_id", "attempt_no", name="uq_exec_attempts_exec_attempt"),
        sa.CheckConstraint(
            "status IN ('QUEUED', 'RUNNING', 'CANCEL_REQUESTED', 'SUCCESS', "
            "'PARTIAL', 'TECHNICAL_ERROR', 'TIMEOUT', 'CANCELLED')",
            name="ck_attempt_status",
        ),
        schema=schema,
    )

    op.create_table(
        "rule_execution_results",
        sa.Column("rule_result_id", sa.String(36), primary_key=True),
        sa.Column(
            "execution_id",
            sa.String(36),
            sa.ForeignKey(f"{schema}.rule_executions.execution_id"),
            nullable=False,
        ),
        sa.Column("rule_version_id", sa.String(36), nullable=False),
        sa.Column("population_count", sa.Integer()),
        sa.Column("eligible_count", sa.Integer()),
        sa.Column("evaluated_count", sa.Integer()),
        sa.Column("passed_count", sa.Integer()),
        sa.Column("failed_count", sa.Integer()),
        sa.Column("excluded_count", sa.Integer()),
        sa.Column("technical_error_count", sa.Integer()),
        sa.Column("unknown_count", sa.Integer()),
        sa.Column("measurement_status", sa.String(30)),
        sa.Column("completed_partitions", sa.JSON(), nullable=False),
        sa.Column("eligible_for_official_scoring", sa.Integer(), nullable=False),
        sa.UniqueConstraint("execution_id", "rule_version_id", name="uq_exec_results_exec_rule"),
        schema=schema,
    )

    op.create_index(
        "ix_executions_status",
        "rule_executions",
        ["status"],
        schema=schema,
    )
    op.create_index(
        "ix_executions_created_at",
        "rule_executions",
        ["created_at"],
        schema=schema,
    )
    op.create_index(
        "ix_execution_attempts_execution_id",
        "execution_attempts",
        ["execution_id"],
        schema=schema,
    )
    op.create_index(
        "ix_execution_results_execution_id",
        "rule_execution_results",
        ["execution_id"],
        schema=schema,
    )


def downgrade() -> None:
    schema = _schema()
    op.drop_table("rule_execution_results", schema=schema)
    op.drop_table("execution_attempts", schema=schema)
    op.drop_table("rule_executions", schema=schema)