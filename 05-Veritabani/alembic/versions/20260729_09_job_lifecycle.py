"""Kalıcı iş yaşam döngüsü ve dead-letter kayıtları.

Revision ID: 20260729_09
Revises: 20260728_08
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260729_09"
down_revision = "20260728_08"
branch_labels = None
depends_on = None


def _schema() -> str:
    return op.get_context().config.get_main_option("data_quality_schema", "dq")


def upgrade() -> None:
    schema = _schema()
    op.drop_constraint(
        "ck_background_jobs_status",
        "background_jobs",
        schema=schema,
        type_="check",
    )
    op.add_column(
        "background_jobs",
        sa.Column("completion_outcome", sa.String(30)),
        schema=schema,
    )
    op.add_column(
        "background_jobs",
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        schema=schema,
    )
    op.add_column(
        "background_jobs",
        sa.Column("cancel_requested_at", sa.DateTime(timezone=True)),
        schema=schema,
    )
    op.add_column(
        "background_jobs",
        sa.Column("cancel_requested_by", sa.String(128)),
        schema=schema,
    )
    op.add_column(
        "background_jobs",
        sa.Column("cancel_reason_code", sa.String(100)),
        schema=schema,
    )
    op.create_check_constraint(
        "ck_background_jobs_status",
        "background_jobs",
        "status IN ('QUEUED', 'RUNNING', 'CANCEL_REQUESTED', 'SUCCESS', "
        "'TECHNICAL_ERROR', 'TIMEOUT', 'CANCELLED')",
        schema=schema,
    )
    op.create_check_constraint(
        "ck_background_jobs_completion_outcome",
        "background_jobs",
        "completion_outcome IS NULL OR completion_outcome IN ('SUCCESS', 'QUALITY_FAILURE')",
        schema=schema,
    )
    op.create_table(
        "job_dead_letters",
        sa.Column("dead_letter_id", sa.String(36), primary_key=True),
        sa.Column(
            "job_id",
            sa.String(36),
            sa.ForeignKey(f"{schema}.background_jobs.job_id"),
            nullable=False,
        ),
        sa.Column("error_class", sa.String(200), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reprocessed_at", sa.DateTime(timezone=True)),
        sa.Column("reprocessed_by", sa.String(128)),
        sa.Column("audit_event_id", sa.String(36)),
        sa.CheckConstraint(
            "status IN ('OPEN', 'REPROCESSED')",
            name="ck_job_dead_letters_status",
        ),
        sa.CheckConstraint(
            "attempt_count > 0",
            name="ck_job_dead_letters_attempt_count",
        ),
        schema=schema,
    )
    op.create_index(
        "ix_dq_job_dead_letters_open",
        "job_dead_letters",
        ["status", "created_at", "dead_letter_id"],
        schema=schema,
    )
    op.create_index(
        "ix_dq_job_dead_letters_job",
        "job_dead_letters",
        ["job_id"],
        schema=schema,
    )


def downgrade() -> None:
    """Üretim politikası ileri düzeltmedir; downgrade yalnız Alembic sözleşmesi içindir."""

    schema = _schema()
    op.drop_index(
        "ix_dq_job_dead_letters_job",
        table_name="job_dead_letters",
        schema=schema,
    )
    op.drop_index(
        "ix_dq_job_dead_letters_open",
        table_name="job_dead_letters",
        schema=schema,
    )
    op.drop_table("job_dead_letters", schema=schema)
    op.drop_constraint(
        "ck_background_jobs_completion_outcome",
        "background_jobs",
        schema=schema,
        type_="check",
    )
    op.drop_constraint(
        "ck_background_jobs_status",
        "background_jobs",
        schema=schema,
        type_="check",
    )
    for column in (
        "cancel_reason_code",
        "cancel_requested_by",
        "cancel_requested_at",
        "completed_at",
        "completion_outcome",
    ):
        op.drop_column("background_jobs", column, schema=schema)
    op.create_check_constraint(
        "ck_background_jobs_status",
        "background_jobs",
        "status IN ('QUEUED', 'RUNNING', 'SUCCESS', 'TECHNICAL_ERROR', 'TIMEOUT', 'CANCELLED')",
        schema=schema,
    )
