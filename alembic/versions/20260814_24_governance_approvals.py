"""Ortak yönetişim onay talepleri tablosu (GovernanceApprovalRequest).

Sistem geneli maker-checker talepleri için tek yazma noktası. Mevcut kural
ve veri kaynağı onay tablolarına dokunulmaz; yeni domain'ler (sahiplik,
metadata, çalıştırma, zamanlayıcı, skorlama) bu tabloya yazar.

Revision ID: 20260814_24
Revises: 20260813_23
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260814_24"
down_revision = "20260813_23"
branch_labels = None
depends_on = None


def _schema() -> str:
    return op.get_context().config.get_main_option("data_quality_schema", "dq")


def upgrade() -> None:
    schema = _schema()

    op.create_table(
        "governance_approval_requests",
        sa.Column("approval_request_id", sa.String(36), primary_key=True),
        sa.Column("request_type", sa.String(40), nullable=False),
        sa.Column("object_type", sa.String(40), nullable=False),
        sa.Column("object_id", sa.String(36), nullable=False),
        sa.Column("scope_type", sa.String(40), nullable=False),
        sa.Column("scope_id", sa.String(36), nullable=False),
        sa.Column("scope_version", sa.Integer(), nullable=False),
        sa.Column("maker_actor_id", sa.String(128), nullable=False),
        sa.Column("maker_roles", sa.JSON(), nullable=False),
        sa.Column("checker_actor_id", sa.String(128), nullable=True),
        sa.Column("checker_role", sa.String(40), nullable=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("reason_code", sa.String(120), nullable=True),
        sa.Column("change_summary", sa.JSON(), nullable=False),
        sa.Column("before_snapshot_reference", sa.String(500), nullable=True),
        sa.Column("after_snapshot_reference", sa.String(500), nullable=True),
        sa.Column("evidence_references", sa.JSON(), nullable=False),
        sa.Column("policy_version", sa.String(40), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("correlation_id", sa.String(64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'SUBMITTED', 'APPROVED', 'REJECTED', 'WITHDRAWN',"
            " 'EXPIRED', 'INVALIDATED', 'APPLIED', 'APPLICATION_FAILED')",
            name="ck_governance_approval_status",
        ),
        sa.CheckConstraint("scope_version > 0", name="ck_governance_approval_scope_version"),
        sa.CheckConstraint("version > 0", name="ck_governance_approval_version"),
        schema=schema,
    )
    op.create_index(
        "ix_governance_approval_scope",
        "governance_approval_requests",
        ["scope_type", "scope_id"],
        schema=schema,
    )
    op.create_index(
        "ix_governance_approval_object",
        "governance_approval_requests",
        ["object_type", "object_id"],
        schema=schema,
    )
    op.create_index(
        "ix_governance_approval_status",
        "governance_approval_requests",
        ["status"],
        schema=schema,
    )
    op.create_index(
        "ix_governance_approval_requested_at",
        "governance_approval_requests",
        ["requested_at"],
        schema=schema,
    )
    # Nesne başına tek bekleyen talep (fail-closed idempotency guard).
    op.execute(
        f"""
        CREATE UNIQUE INDEX ux_governance_approval_pending_object
        ON "{schema}".governance_approval_requests (object_type, object_id, request_type)
        WHERE status = 'SUBMITTED'
        """
    )


def downgrade() -> None:
    """Üretim politikası ileri düzeltmedir; downgrade yalnız Alembic sözleşmesi içindir."""

    schema = _schema()
    op.execute(f'DROP INDEX IF EXISTS "{schema}".ux_governance_approval_pending_object')
    op.drop_index(
        "ix_governance_approval_requested_at",
        table_name="governance_approval_requests",
        schema=schema,
    )
    op.drop_index(
        "ix_governance_approval_status",
        table_name="governance_approval_requests",
        schema=schema,
    )
    op.drop_index(
        "ix_governance_approval_object",
        table_name="governance_approval_requests",
        schema=schema,
    )
    op.drop_index(
        "ix_governance_approval_scope",
        table_name="governance_approval_requests",
        schema=schema,
    )
    op.drop_table("governance_approval_requests", schema=schema)
