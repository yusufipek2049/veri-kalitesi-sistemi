"""Çalıştırma worker yaşam döngüsü ve BLOCKED iş durumları.

Revision ID: 20260805_16
Revises: 20260805_15
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260805_16"
down_revision = "20260805_15"
branch_labels = None
depends_on = None


def _schema() -> str:
    return op.get_context().config.get_main_option("data_quality_schema", "dq")


def upgrade() -> None:
    schema = _schema()

    # ── workers tablosu ──
    op.create_table(
        "workers",
        sa.Column("worker_id", sa.String(128), primary_key=True),
        sa.Column("hostname", sa.String(255), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("supported_job_types", sa.JSON(), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stopped_at", sa.DateTime(timezone=True)),
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
        sa.CheckConstraint(
            "capacity > 0",
            name="ck_workers_capacity",
        ),
        sa.CheckConstraint(
            "state IN ('STARTING', 'RUNNING', 'DRAINING', 'STOPPED', 'UNHEALTHY')",
            name="ck_workers_state",
        ),
        sa.CheckConstraint(
            "version >= 0",
            name="ck_workers_version",
        ),
        schema=schema,
    )
    op.create_index(
        "ix_dq_workers_state_last_seen",
        "workers",
        ["state", "last_seen_at"],
        schema=schema,
    )

    # ── background_jobs: yeni kolonlar (nullable/default-safe) ──
    op.add_column(
        "background_jobs",
        sa.Column(
            "progress_percent",
            sa.SmallInteger(),
            nullable=False,
            server_default="0",
        ),
        schema=schema,
    )
    op.add_column(
        "background_jobs",
        sa.Column("blocked_reason_code", sa.String(100)),
        schema=schema,
    )
    op.add_column(
        "background_jobs",
        sa.Column("blocked_until", sa.DateTime(timezone=True)),
        schema=schema,
    )

    # ── mevcut satırları backfill ──
    op.execute(
        f'UPDATE "{schema}"."background_jobs" SET progress_percent = 0 '
        f"WHERE progress_percent IS NULL"
    )

    # ── status check: BLOCKED ekle ──
    op.drop_constraint(
        "ck_background_jobs_status",
        "background_jobs",
        schema=schema,
        type_="check",
    )
    op.create_check_constraint(
        "ck_background_jobs_status",
        "background_jobs",
        "status IN ('QUEUED', 'RUNNING', 'CANCEL_REQUESTED', 'SUCCESS', "
        "'TECHNICAL_ERROR', 'TIMEOUT', 'CANCELLED', 'BLOCKED')",
        schema=schema,
    )

    # ── progress ve blocked tutarlılık check'leri ──
    op.create_check_constraint(
        "ck_background_jobs_progress_percent",
        "background_jobs",
        "progress_percent >= 0 AND progress_percent <= 100",
        schema=schema,
    )
    op.create_check_constraint(
        "ck_background_jobs_blocked_consistency",
        "background_jobs",
        "(status != 'BLOCKED') OR (blocked_reason_code IS NOT NULL)",
        schema=schema,
    )

    # ── claim indeksi: BLOCKED/blocked_until tekrar uygunluğu ──
    op.drop_index(
        "ix_dq_background_jobs_claim",
        table_name="background_jobs",
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


def downgrade() -> None:
    """Üretim politikası ileri düzeltmedir; downgrade yalnız Alembic sözleşmesi içindir."""

    schema = _schema()

    op.drop_index(
        "ix_dq_background_jobs_claim",
        table_name="background_jobs",
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
    op.drop_constraint(
        "ck_background_jobs_blocked_consistency",
        "background_jobs",
        schema=schema,
        type_="check",
    )
    op.drop_constraint(
        "ck_background_jobs_progress_percent",
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
    op.create_check_constraint(
        "ck_background_jobs_status",
        "background_jobs",
        "status IN ('QUEUED', 'RUNNING', 'CANCEL_REQUESTED', 'SUCCESS', "
        "'TECHNICAL_ERROR', 'TIMEOUT', 'CANCELLED')",
        schema=schema,
    )
    for column in ("blocked_until", "blocked_reason_code", "progress_percent"):
        op.drop_column("background_jobs", column, schema=schema)
    op.drop_index(
        "ix_dq_workers_state_last_seen",
        table_name="workers",
        schema=schema,
    )
    op.drop_table("workers", schema=schema)
