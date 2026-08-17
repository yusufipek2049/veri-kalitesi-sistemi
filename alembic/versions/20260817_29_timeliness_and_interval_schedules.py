"""Dataset zamanlılık niteliği ve schedule INTERVAL aralığı.

Jobs ekranı tablo niteliğine (NEAR_TIME / REAL_TIME / BATCH_TIME) göre
önerilen tekrarlama aralıkları sunar; dakika bazlı INTERVAL zamanlayıcılar
için schedules tablosuna interval_minutes kolonu eklenir.

Revision ID: 20260817_29
Revises: 20260817_28
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260817_29"
down_revision = "20260817_28"
branch_labels = None
depends_on = None


def _schema() -> str:
    return op.get_context().config.get_main_option("data_quality_schema", "dq")


def upgrade() -> None:
    schema = _schema()

    op.add_column(
        "datasets",
        sa.Column("timeliness_nature", sa.String(20), nullable=True),
        schema=schema,
    )
    op.create_check_constraint(
        "ck_ds_timeliness_nature",
        "datasets",
        "timeliness_nature IS NULL OR timeliness_nature IN "
        "('NEAR_TIME', 'REAL_TIME', 'BATCH_TIME')",
        schema=schema,
    )
    op.add_column(
        "schedules",
        sa.Column("interval_minutes", sa.Integer(), nullable=True),
        schema=schema,
    )
    op.create_check_constraint(
        "ck_schedules_interval_minutes",
        "schedules",
        "interval_minutes IS NULL OR interval_minutes BETWEEN 1 AND 43200",
        schema=schema,
    )


def downgrade() -> None:
    """Üretim politikası ileri düzeltmedir; downgrade yalnız Alembic sözleşmesi içindir."""

    schema = _schema()
    op.drop_constraint("ck_schedules_interval_minutes", "schedules", schema=schema)
    op.drop_column("schedules", "interval_minutes", schema=schema)
    op.drop_constraint("ck_ds_timeliness_nature", "datasets", schema=schema)
    op.drop_column("datasets", "timeliness_nature", schema=schema)
