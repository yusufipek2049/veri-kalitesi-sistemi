"""PostgreSQL kalıcı iş kuyruğu çekirdeği.

Revision ID: 20260728_08
Revises: 20260724_07
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260728_08"
down_revision = "20260724_07"
branch_labels = None
depends_on = None


def _schema() -> str:
    return op.get_context().config.get_main_option("data_quality_schema", "dq")


def upgrade() -> None:
    schema = _schema()
    op.create_table(
        "background_jobs",
        sa.Column("job_id", sa.String(36), primary_key=True),
        sa.Column("job_type", sa.String(100), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(200)),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("claimed_by", sa.String(128)),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True)),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("last_error_class", sa.String(200)),
        sa.UniqueConstraint(
            "job_type",
            "idempotency_key",
            name="uq_background_jobs_type_idempotency",
        ),
        sa.CheckConstraint(
            "status IN ('QUEUED', 'RUNNING', 'SUCCESS', 'TECHNICAL_ERROR', 'TIMEOUT', 'CANCELLED')",
            name="ck_background_jobs_status",
        ),
        sa.CheckConstraint("priority >= 0", name="ck_background_jobs_priority"),
        sa.CheckConstraint(
            "attempt_count >= 0",
            name="ck_background_jobs_attempt_count",
        ),
        sa.CheckConstraint("version >= 0", name="ck_background_jobs_version"),
        schema=schema,
    )
    op.create_index(
        "ix_dq_background_jobs_claim",
        "background_jobs",
        [
            "status",
            sa.text("priority DESC"),
            "available_at",
            "created_at",
            "job_id",
        ],
        schema=schema,
    )
    op.create_index(
        "ix_dq_background_jobs_lease",
        "background_jobs",
        ["status", "lease_expires_at"],
        schema=schema,
    )
    op.create_index(
        "ix_dq_background_jobs_job_type",
        "background_jobs",
        ["job_type"],
        schema=schema,
    )


def downgrade() -> None:
    schema = _schema()
    op.drop_index(
        "ix_dq_background_jobs_job_type",
        table_name="background_jobs",
        schema=schema,
    )
    op.drop_index(
        "ix_dq_background_jobs_lease",
        table_name="background_jobs",
        schema=schema,
    )
    op.drop_index(
        "ix_dq_background_jobs_claim",
        table_name="background_jobs",
        schema=schema,
    )
    op.drop_table("background_jobs", schema=schema)
