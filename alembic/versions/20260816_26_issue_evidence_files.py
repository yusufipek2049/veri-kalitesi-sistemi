"""Uploaded issue evidence file metadata.

Revision ID: 20260816_26
Revises: 20260814_25
"""

from alembic import op
import sqlalchemy as sa

revision = "20260816_26"
down_revision = "20260814_25"
branch_labels = None
depends_on = None


def _schema() -> str:
    return op.get_context().config.get_main_option("data_quality_schema", "dq")


def upgrade() -> None:
    schema = _schema()
    op.drop_constraint("ck_issue_evidence_kind", "issue_evidence", schema=schema, type_="check")
    op.create_check_constraint(
        "ck_issue_evidence_kind",
        "issue_evidence",
        "kind IN ('EXECUTION_RESULT','EXECUTION_LOG','LEGACY_REFERENCE','UPLOADED_FILE')",
        schema=schema,
    )
    op.create_table(
        "issue_evidence_files",
        sa.Column("file_id", sa.String(36), primary_key=True),
        sa.Column("evidence_id", sa.String(36), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("safe_filename", sa.String(255), nullable=False),
        sa.Column("declared_media_type", sa.String(120)),
        sa.Column("detected_media_type", sa.String(120), nullable=False),
        sa.Column("byte_size", sa.BigInteger, nullable=False),
        sa.Column("object_key", sa.String(500), nullable=False, unique=True),
        sa.Column("sha256_digest", sa.String(64), nullable=False),
        sa.Column("scan_status", sa.String(30), nullable=False),
        sa.Column("scan_reason_code", sa.String(100)),
        sa.Column("scan_completed_at", sa.DateTime(timezone=True)),
        sa.Column("classification", sa.String(40), nullable=False),
        sa.Column("uploaded_by", sa.String(128), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retention_until", sa.DateTime(timezone=True)),
        sa.Column("legal_hold", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("deleted_by", sa.String(128)),
        sa.Column("idempotency_digest", sa.String(64), nullable=False),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            [f"{schema}.issue_evidence.evidence_id"],
            name="fk_issue_evidence_file_evidence",
        ),
        sa.CheckConstraint("byte_size > 0", name="ck_issue_evidence_file_size"),
        sa.CheckConstraint(
            "sha256_digest ~ '^[0-9a-f]{64}$'", name="ck_issue_evidence_file_sha256"
        ),
        sa.CheckConstraint(
            "scan_status IN ('UPLOADING','PENDING_SCAN','AVAILABLE','REJECTED','SCAN_FAILED')",
            name="ck_issue_evidence_file_scan_status",
        ),
        sa.CheckConstraint(
            "scan_status <> 'AVAILABLE' OR scan_completed_at IS NOT NULL",
            name="ck_issue_evidence_file_available_at",
        ),
        sa.UniqueConstraint("evidence_id", name="uq_issue_evidence_file_evidence"),
        schema=schema,
    )
    op.create_index(
        "ix_issue_evidence_files_idempotency",
        "issue_evidence_files",
        ["idempotency_digest"],
        schema=schema,
    )


def downgrade() -> None:
    schema = _schema()
    op.drop_index(
        "ix_issue_evidence_files_idempotency", table_name="issue_evidence_files", schema=schema
    )
    op.drop_table("issue_evidence_files", schema=schema)
    op.drop_constraint("ck_issue_evidence_kind", "issue_evidence", schema=schema, type_="check")
    op.create_check_constraint(
        "ck_issue_evidence_kind",
        "issue_evidence",
        "kind IN ('EXECUTION_RESULT','EXECUTION_LOG','LEGACY_REFERENCE')",
        schema=schema,
    )
