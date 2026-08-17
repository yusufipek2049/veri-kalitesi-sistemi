"""schedules tablosu CHECK constraint'ine INTERVAL tipi ekle.

20260817_29 migration'ı interval_minutes kolonunu ekledi ancak
ck_schedules_type CHECK constraint'ini güncellemeyi unuttu.
Bu migration constraint'i ONCE/DAILY/WEEKLY/MONTHLY/INTERVAL olarak genişletir.

Revision ID: 20260817_31
Revises: 20260817_30
"""

from __future__ import annotations

from alembic import op

revision = "20260817_31"
down_revision = "20260817_30"
branch_labels = None
depends_on = None


def _schema() -> str:
    return op.get_context().config.get_main_option("data_quality_schema", "dq")


def upgrade() -> None:
    schema = _schema()
    op.drop_constraint("ck_schedules_type", "schedules", schema=schema)
    op.create_check_constraint(
        "ck_schedules_type",
        "schedules",
        "schedule_type IN ('ONCE', 'DAILY', 'WEEKLY', 'MONTHLY', 'INTERVAL')",
        schema=schema,
    )


def downgrade() -> None:
    schema = _schema()
    op.drop_constraint("ck_schedules_type", "schedules", schema=schema)
    op.create_check_constraint(
        "ck_schedules_type",
        "schedules",
        "schedule_type IN ('ONCE', 'DAILY', 'WEEKLY', 'MONTHLY')",
        schema=schema,
    )
