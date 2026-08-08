"""DS-05 otomatik sorun üretimi — title, source refs, MANUAL constraints, history receipt.

Revision ID: 20260806_18
Revises: 20260805_17

DS-05 dikey dilimi:
  1. data_quality_issues: title, source_execution_id, source_rule_version_id
  2. Legacy title backfill (issue_no tabanlı deterministik)
  3. source_execution_id / source_rule_version_id FK ve indeksleri
  4. ck_issue_source_event_type ve ck_issue_trigger_type: MANUAL ekleme
  5. issue_history: source-event receipt kolonları
  6. Receipt consistency check ve partial unique index
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260806_18"
down_revision = "20260805_17"
branch_labels = None
depends_on = None


def _schema() -> str:
    return op.get_context().config.get_main_option("data_quality_schema", "dq")


def upgrade() -> None:
    schema = _schema()

    # ── 1. data_quality_issues: nullable kolonlar ──
    op.add_column(
        "data_quality_issues",
        sa.Column("title", sa.String(200), nullable=True),
        schema=schema,
    )
    op.add_column(
        "data_quality_issues",
        sa.Column("source_execution_id", sa.String(36), nullable=True),
        schema=schema,
    )
    op.add_column(
        "data_quality_issues",
        sa.Column("source_rule_version_id", sa.String(36), nullable=True),
        schema=schema,
    )

    # ── 2. Legacy title backfill ──
    op.execute(
        f"""
        UPDATE {schema}.data_quality_issues
        SET title = 'DQI-' || UPPER(SUBSTR(issue_no, 5, 12))
        WHERE title IS NULL
        """
    )

    # title NOT NULL
    op.alter_column(
        "data_quality_issues",
        "title",
        existing_type=sa.String(200),
        nullable=False,
        schema=schema,
    )

    # ── 3. FK ve indeksler ──
    op.create_foreign_key(
        "fk_issue_source_execution",
        "data_quality_issues",
        "rule_executions",
        ["source_execution_id"],
        ["execution_id"],
        source_schema=schema,
        referent_schema=schema,
    )
    op.create_foreign_key(
        "fk_issue_source_rule_version",
        "data_quality_issues",
        "rule_versions",
        ["source_rule_version_id"],
        ["rule_version_id"],
        source_schema=schema,
        referent_schema=schema,
    )
    op.create_index(
        "ix_dq_issues_source_execution",
        "data_quality_issues",
        ["source_execution_id"],
        schema=schema,
    )
    op.create_index(
        "ix_dq_issues_source_rule_version",
        "data_quality_issues",
        ["source_rule_version_id"],
        schema=schema,
    )

    # ── 4. CHECK constraint'leri: MANUAL ekleme ──
    op.drop_constraint("ck_issue_source_event_type", "data_quality_issues", schema=schema)
    op.create_check_constraint(
        "ck_issue_source_event_type",
        "data_quality_issues",
        "source_event_type IN ('QUALITY', 'TECHNICAL', 'MANUAL')",
        schema=schema,
    )
    op.drop_constraint("ck_issue_trigger_type", "data_quality_issues", schema=schema)
    op.create_check_constraint(
        "ck_issue_trigger_type",
        "data_quality_issues",
        "trigger_type IN ('QUALITY_THRESHOLD', 'CRITICAL_RULE_FAILURE', 'TECHNICAL_ERROR', 'MANUAL')",
        schema=schema,
    )

    # ── 5. issue_history: receipt kolonları ──
    op.add_column(
        "issue_history",
        sa.Column("source_event_id", sa.String(36), nullable=True),
        schema=schema,
    )
    op.add_column(
        "issue_history",
        sa.Column("source_event_occurred_at", sa.DateTime(timezone=True), nullable=True),
        schema=schema,
    )
    op.add_column(
        "issue_history",
        sa.Column("source_event_payload_digest", sa.String(64), nullable=True),
        schema=schema,
    )

    # ── 6. Receipt consistency check ve partial unique index ──
    op.create_check_constraint(
        "ck_issue_history_receipt_consistency",
        "issue_history",
        (
            "(source_event_id IS NULL AND source_event_occurred_at IS NULL"
            " AND source_event_payload_digest IS NULL)"
            " OR"
            " (source_event_id IS NOT NULL AND source_event_occurred_at IS NOT NULL"
            " AND source_event_payload_digest IS NOT NULL)"
        ),
        schema=schema,
    )
    op.create_index(
        "uq_issue_history_source_event_id",
        "issue_history",
        ["source_event_id"],
        unique=True,
        schema=schema,
        postgresql_where=sa.text("source_event_id IS NOT NULL"),
    )


def downgrade() -> None:
    schema = _schema()

    # 6. Receipt index ve constraint
    op.drop_index("uq_issue_history_source_event_id", table_name="issue_history", schema=schema)
    op.drop_constraint("ck_issue_history_receipt_consistency", "issue_history", schema=schema)

    # 5. Receipt kolonları
    op.drop_column("issue_history", "source_event_payload_digest", schema=schema)
    op.drop_column("issue_history", "source_event_occurred_at", schema=schema)
    op.drop_column("issue_history", "source_event_id", schema=schema)

    # 4. CHECK constraint'leri: MANUAL kaldır
    op.drop_constraint("ck_issue_trigger_type", "data_quality_issues", schema=schema)
    op.create_check_constraint(
        "ck_issue_trigger_type",
        "data_quality_issues",
        "trigger_type IN ('QUALITY_THRESHOLD', 'CRITICAL_RULE_FAILURE', 'TECHNICAL_ERROR')",
        schema=schema,
    )
    op.drop_constraint("ck_issue_source_event_type", "data_quality_issues", schema=schema)
    op.create_check_constraint(
        "ck_issue_source_event_type",
        "data_quality_issues",
        "source_event_type IN ('QUALITY', 'TECHNICAL')",
        schema=schema,
    )

    # 3. FK ve indeksler
    op.drop_index(
        "ix_dq_issues_source_rule_version", table_name="data_quality_issues", schema=schema
    )
    op.drop_index("ix_dq_issues_source_execution", table_name="data_quality_issues", schema=schema)
    op.drop_constraint("fk_issue_source_rule_version", "data_quality_issues", schema=schema)
    op.drop_constraint("fk_issue_source_execution", "data_quality_issues", schema=schema)

    # 1–2. Kolonlar
    op.drop_column("data_quality_issues", "source_rule_version_id", schema=schema)
    op.drop_column("data_quality_issues", "source_execution_id", schema=schema)
    op.drop_column("data_quality_issues", "title", schema=schema)
