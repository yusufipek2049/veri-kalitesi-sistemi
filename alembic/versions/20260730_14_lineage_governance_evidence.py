"""Değişmez lineage, yönetişim profili ve kaynaklı etki kanıtı snapshot'ları.

Revision ID: 20260730_14
Revises: 20260730_13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260730_14"
down_revision = "20260730_13"
branch_labels = None
depends_on = None


def _schema() -> str:
    return op.get_context().config.get_main_option("data_quality_schema", "dq")


def upgrade() -> None:
    schema = _schema()
    op.create_table(
        "lineage_evidence_snapshots",
        sa.Column("snapshot_id", sa.String(64), primary_key=True),
        sa.Column("snapshot_kind", sa.String(32), nullable=False),
        sa.Column("subject_ref", sa.String(256), nullable=False),
        sa.Column("version_label", sa.String(128), nullable=False),
        sa.Column("digest", sa.String(71), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "snapshot_kind IN ('GOVERNANCE_PROFILE','LINEAGE_EVENTS',"
            "'IMPACT_ASSESSMENT','ROOT_CAUSE_HYPOTHESIS')",
            name="ck_lineage_evidence_snapshot_kind",
        ),
        sa.CheckConstraint(
            "digest LIKE 'sha256:%'",
            name="ck_lineage_evidence_digest_algorithm",
        ),
        sa.UniqueConstraint(
            "snapshot_kind",
            "subject_ref",
            "version_label",
            name="uq_lineage_evidence_subject_version",
        ),
        schema=schema,
    )
    op.create_index(
        "ix_lineage_evidence_kind_subject",
        "lineage_evidence_snapshots",
        ["snapshot_kind", "subject_ref", "created_at"],
        schema=schema,
    )


def downgrade() -> None:
    raise RuntimeError(
        "Production downgrade is disabled for immutable lineage evidence; "
        "create a forward corrective migration instead."
    )
