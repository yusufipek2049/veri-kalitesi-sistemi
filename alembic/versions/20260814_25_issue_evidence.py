"""Çözüm kanıtı defteri (issue_evidence) ve çözüm kaydının FK bağı.

Çözüm formundaki ``evidence_reference_id`` alanı serbest metin bir UUID
bekliyordu; girilen değerin gerçek bir kanıta karşılık geldiği hiçbir yerde
doğrulanmıyordu. Bu göç kanıdı kalıcı bir kayıt hâline getirir:

- ``issue_evidence``: kural çalıştırmasının sonucundan veya log kaydından
  türetilmiş, issue'ya bağlı kanıt kaydı. Veri-minimum: ham satır tutmaz.
- ``issue_resolutions.evidence_reference_id`` artık bu tabloya FK ile bağlıdır.

Mevcut çözüm kayıtları kaybolmasın diye, FK eklenmeden önce her ayrık eski
referans için ``LEGACY_REFERENCE`` türünde bir kanıt satırı üretilir.

Revision ID: 20260814_25
Revises: 20260814_24
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260814_25"
down_revision = "20260814_24"
branch_labels = None
depends_on = None


def _schema() -> str:
    return op.get_context().config.get_main_option("data_quality_schema", "dq")


def upgrade() -> None:
    schema = _schema()

    op.create_table(
        "issue_evidence",
        sa.Column("sequence_no", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("evidence_id", sa.String(36), nullable=False, unique=True),
        sa.Column("issue_id", sa.String(36), nullable=False),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("execution_id", sa.String(64), nullable=False),
        sa.Column("rule_version_id", sa.String(36), nullable=True),
        sa.Column("evaluated_count", sa.Integer(), nullable=True),
        sa.Column("failed_count", sa.Integer(), nullable=True),
        sa.Column("measurement_status", sa.String(40), nullable=True),
        sa.Column("fingerprint", sa.String(128), nullable=True),
        sa.Column("query_reference", sa.String(200), nullable=True),
        sa.Column("plan_reference", sa.String(200), nullable=True),
        sa.Column("content_digest", sa.String(64), nullable=False),
        sa.Column("source_digest", sa.String(64), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("captured_by", sa.String(128), nullable=False),
        sa.ForeignKeyConstraint(
            ["issue_id"],
            [f"{schema}.data_quality_issues.issue_id"],
            name="fk_issue_evidence_issue",
        ),
        sa.CheckConstraint(
            "kind IN ('EXECUTION_RESULT', 'EXECUTION_LOG', 'LEGACY_REFERENCE')",
            name="ck_issue_evidence_kind",
        ),
        sa.UniqueConstraint("issue_id", "source_digest", name="uq_issue_evidence_source"),
        schema=schema,
    )
    op.create_index(
        "ix_issue_evidence_issue",
        "issue_evidence",
        ["issue_id", sa.text("captured_at DESC")],
        schema=schema,
    )

    # Eski çözüm kayıtlarının referansları için taşıma kanıtı üret; aksi hâlde
    # FK eklenemez ve mevcut veri kaybolur.
    op.execute(
        sa.text(
            f"""
            INSERT INTO {schema}.issue_evidence (
                evidence_id, issue_id, kind, label, execution_id,
                content_digest, source_digest, observed_at, captured_at, captured_by
            )
            SELECT DISTINCT ON (r.evidence_reference_id)
                r.evidence_reference_id,
                r.issue_id,
                'LEGACY_REFERENCE',
                'Göç öncesi kanıt referansı',
                COALESCE(i.source_execution_id, 'unknown'),
                encode(sha256(r.evidence_reference_id::bytea), 'hex'),
                encode(sha256(('legacy:' || r.evidence_reference_id)::bytea), 'hex'),
                r.completed_at,
                r.created_at,
                r.created_by
            FROM {schema}.issue_resolutions AS r
            JOIN {schema}.data_quality_issues AS i ON i.issue_id = r.issue_id
            ORDER BY r.evidence_reference_id, r.sequence_no
            """
        )
    )

    op.create_foreign_key(
        "fk_issue_resolution_evidence",
        "issue_resolutions",
        "issue_evidence",
        ["evidence_reference_id"],
        ["evidence_id"],
        source_schema=schema,
        referent_schema=schema,
    )


def downgrade() -> None:
    schema = _schema()
    op.drop_constraint(
        "fk_issue_resolution_evidence",
        "issue_resolutions",
        schema=schema,
        type_="foreignkey",
    )
    op.drop_index("ix_issue_evidence_issue", table_name="issue_evidence", schema=schema)
    op.drop_table("issue_evidence", schema=schema)
