"""Reports tablosu baseline — 36G guvenli rapor uretimi/indirme.

Revision ID: 20260724_06
Revises: 20260724_05
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260724_06"
down_revision = "20260724_05"
branch_labels = None
depends_on = None


def _schema() -> str:
    return op.get_context().config.get_main_option("data_quality_schema", "dq")


def upgrade() -> None:
    schema = _schema()

    op.create_table(
        "reports",
        sa.Column("report_id", sa.String(36), primary_key=True),
        sa.Column("report_type", sa.String(30), nullable=False),
        sa.Column("format", sa.String(10), nullable=False),
        sa.Column("requested_by", sa.String(128), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("sensitivity_level", sa.String(100)),
        sa.Column("retention_policy_id", sa.String(36)),
        sa.Column("online_file_reference", sa.String(500)),
        sa.Column("file_size", sa.Integer()),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("failure_reason", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "report_type IN ('SUMMARY', 'DETAIL', 'TREND', 'UNIT', 'OWNER', "
            "'CRITICAL_DATA', 'ISSUE_PERFORMANCE')",
            name="ck_reports_type",
        ),
        sa.CheckConstraint(
            "format IN ('PDF', 'XLSX', 'CSV')",
            name="ck_reports_format",
        ),
        sa.CheckConstraint(
            "status IN ('QUEUED', 'RUNNING', 'READY', 'FAILED', 'EXPIRED')",
            name="ck_reports_status",
        ),
        schema=schema,
    )
    op.create_index(
        "ix_dq_reports_requested_by",
        "reports",
        ["requested_by", sa.text("created_at DESC")],
        schema=schema,
    )


def downgrade() -> None:
    schema = _schema()
    op.drop_index("ix_dq_reports_requested_by", table_name="reports", schema=schema)
    op.drop_table("reports", schema=schema)