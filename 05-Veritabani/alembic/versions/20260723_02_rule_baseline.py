"""Rule ve approval request PostgreSQL baseline.

Revision ID: 20260723_02
Revises: 20260723_01
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260723_02"
down_revision = "20260723_01"
branch_labels = None
depends_on = None


def _schema() -> str:
    return op.get_context().config.get_main_option("data_quality_schema", "dq")


def upgrade() -> None:
    schema = _schema()
    op.create_table(
        "quality_rules",
        sa.Column("quality_rule_id", sa.String(36), primary_key=True),
        sa.Column("code", sa.String(200), nullable=False, unique=True),
        sa.Column("name", sa.String(400), nullable=False),
        sa.Column("dataset_id", sa.String(36), nullable=False),
        sa.Column("field_ids", sa.JSON(), nullable=False),
        sa.Column("primary_dimension", sa.String(40), nullable=False),
        sa.Column("owner_user_id", sa.String(128), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.CheckConstraint(
            "primary_dimension IN "
            "('COMPLETENESS', 'ACCURACY', 'VALIDITY', 'CONSISTENCY', "
            "'UNIQUENESS', 'TIMELINESS', 'INTEGRITY')",
            name="ck_quality_rules_primary_dimension",
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'ACTIVE', 'PASSIVE', 'REVIEW_REQUIRED', 'ARCHIVED')",
            name="ck_quality_rules_status",
        ),
        schema=schema,
    )
    op.create_index(
        "ix_dq_quality_rules_dataset",
        "quality_rules",
        ["dataset_id"],
        schema=schema,
    )
    op.create_table(
        "rule_versions",
        sa.Column("rule_version_id", sa.String(36), primary_key=True),
        sa.Column(
            "quality_rule_id",
            sa.String(36),
            sa.ForeignKey(f"{schema}.quality_rules.quality_rule_id"),
            nullable=False,
        ),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("rule_type", sa.String(40), nullable=False),
        sa.Column("definition", sa.JSON(), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("criticality", sa.String(20), nullable=False),
        sa.Column("prepared_by_actor_id", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "quality_rule_id",
            "version_no",
            name="uq_rule_versions_quality_rule_id_version_no",
        ),
        sa.CheckConstraint(
            "rule_type IN "
            "('REQUIRED', 'UNIQUE', 'RANGE', 'REGEX', 'FRESHNESS', "
            "'REFERENTIAL_INTEGRITY', 'CROSS_TABLE_CONSISTENCY', 'CUSTOM_SQL')",
            name="ck_rule_versions_rule_type",
        ),
        sa.CheckConstraint(
            "criticality IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="ck_rule_versions_criticality",
        ),
        schema=schema,
    )
    op.create_index(
        "ix_dq_rule_versions_rule_version_seq",
        "rule_versions",
        ["quality_rule_id", "version_no"],
        schema=schema,
    )
    op.create_table(
        "rule_test_results",
        sa.Column("rule_test_result_id", sa.String(36), primary_key=True),
        sa.Column(
            "rule_version_id",
            sa.String(36),
            sa.ForeignKey(f"{schema}.rule_versions.rule_version_id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("record_limit", sa.Integer(), nullable=False),
        sa.Column("checked_count", sa.Integer(), nullable=False),
        sa.Column("passed_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("not_evaluated_count", sa.Integer(), nullable=False),
        sa.Column("success_rate", sa.Float()),
        sa.Column("preview_score", sa.Float()),
        sa.Column("official_score_included", sa.Integer(), nullable=False),
        sa.Column("error_class", sa.String(200)),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('SUCCESS', 'TECHNICAL_ERROR')",
            name="ck_rule_test_results_status",
        ),
        schema=schema,
    )
    op.create_index(
        "ix_dq_rule_test_results_version_created",
        "rule_test_results",
        ["rule_version_id", sa.text("created_at DESC")],
        schema=schema,
    )
    op.create_table(
        "rule_approval_requests",
        sa.Column("approval_request_id", sa.String(36), primary_key=True),
        sa.Column(
            "rule_version_id",
            sa.String(36),
            sa.ForeignKey(f"{schema}.rule_versions.rule_version_id"),
            nullable=False,
        ),
        sa.Column("maker_actor_id", sa.String(128), nullable=False),
        sa.Column("checker_actor_id", sa.String(128)),
        sa.Column("policy_version", sa.String(80), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("decision_reason_code", sa.String(100)),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("target_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("business_calendar_version", sa.String(80)),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN ('PENDING', 'APPROVED', 'REJECTED', 'WITHDRAWN', 'EXPIRED')",
            name="ck_rule_approval_requests_status",
        ),
        schema=schema,
    )
    op.create_index(
        "ix_dq_rule_approval_requests_pending_expires",
        "rule_approval_requests",
        ["status", "expires_at"],
        schema=schema,
        postgresql_where=sa.text("status = 'PENDING'"),
    )
    op.execute(
        f"""
        CREATE UNIQUE INDEX IF NOT EXISTS ux_dq_rule_approval_pending_version
        ON "{schema}".rule_approval_requests (rule_version_id)
        WHERE status = 'PENDING'
        """
    )


def downgrade() -> None:
    raise RuntimeError(
        "Production downgrade is disabled for rule tables; "
        "create a forward corrective migration instead."
    )