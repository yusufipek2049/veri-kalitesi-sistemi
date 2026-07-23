"""Issue ve audit outbox PostgreSQL baseline.

Revision ID: 20260723_01
Revises:
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260723_01"
down_revision = None
branch_labels = None
depends_on = None


def _schema() -> str:
    return op.get_context().config.get_main_option("data_quality_schema", "dq")


def upgrade() -> None:
    schema = _schema()
    op.create_table(
        "data_quality_issues",
        sa.Column("issue_id", sa.String(36), primary_key=True),
        sa.Column("issue_no", sa.String(40), nullable=False, unique=True),
        sa.Column("source_event_id", sa.String(36), nullable=False),
        sa.Column("source_event_type", sa.String(40), nullable=False),
        sa.Column("trigger_type", sa.String(40), nullable=False),
        sa.Column("scope_type", sa.String(20), nullable=False),
        sa.Column("scope_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False),
        sa.Column("assignee_user_id", sa.String(36), nullable=False),
        sa.Column("deduplication_key_digest", sa.String(128), nullable=False, unique=True),
        sa.Column("payload_digest", sa.String(128), nullable=False),
        sa.Column("occurrence_count", sa.Integer(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "source_event_type IN ('QUALITY', 'TECHNICAL')",
            name="ck_issue_source_event_type",
        ),
        sa.CheckConstraint(
            "trigger_type IN ('QUALITY_THRESHOLD', 'CRITICAL_RULE_FAILURE', 'TECHNICAL_ERROR')",
            name="ck_issue_trigger_type",
        ),
        sa.CheckConstraint("scope_type IN ('DATASET', 'SOURCE')", name="ck_issue_scope_type"),
        sa.CheckConstraint(
            "status IN ('NEW', 'ASSIGNED', 'INVESTIGATING', "
            "'WAITING_FOR_RESOLUTION', 'RESOLVED', 'VERIFIED', 'CLOSED', 'CANCELLED')",
            name="ck_issue_status",
        ),
        sa.CheckConstraint(
            "priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="ck_issue_priority",
        ),
        sa.CheckConstraint("occurrence_count >= 1", name="ck_issue_occurrence_count"),
        schema=schema,
    )
    op.create_index(
        "ix_dq_issues_scope_updated",
        "data_quality_issues",
        ["scope_type", "scope_id", sa.text("updated_at DESC"), sa.text("issue_id DESC")],
        schema=schema,
    )
    op.create_index(
        "ix_dq_issues_assignee_status_updated",
        "data_quality_issues",
        ["assignee_user_id", "status", sa.text("updated_at DESC")],
        schema=schema,
    )
    _create_history_tables(schema)
    op.create_table(
        "audit_outbox",
        sa.Column("event_id", sa.String(36), primary_key=True),
        sa.Column("prepared_event", sa.JSON(), nullable=False),
        sa.Column("policy_version", sa.String(80), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error_code", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("status IN ('PENDING', 'PUBLISHED')", name="ck_audit_outbox_status"),
        schema=schema,
    )
    op.create_index(
        "ix_dq_audit_outbox_pending",
        "audit_outbox",
        ["status", "created_at", "event_id"],
        schema=schema,
    )


def _create_history_tables(schema: str) -> None:
    issue_fk = f"{schema}.data_quality_issues.issue_id"
    op.create_table(
        "issue_history",
        sa.Column("sequence_no", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("history_id", sa.String(36), nullable=False, unique=True),
        sa.Column("issue_id", sa.String(36), sa.ForeignKey(issue_fk), nullable=False),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("actor_id", sa.String(128), nullable=False),
        sa.Column("old_status", sa.String(30)),
        sa.Column("new_status", sa.String(30), nullable=False),
        sa.Column("old_assignee_user_id", sa.String(36)),
        sa.Column("new_assignee_user_id", sa.String(36)),
        sa.Column("old_priority", sa.String(20)),
        sa.Column("new_priority", sa.String(20)),
        sa.Column("resolution_id", sa.String(36)),
        sa.Column("verification_id", sa.String(36)),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "old_status IS NULL OR old_status IN "
            "('NEW', 'ASSIGNED', 'INVESTIGATING', 'WAITING_FOR_RESOLUTION', "
            "'RESOLVED', 'VERIFIED', 'CLOSED', 'CANCELLED')",
            name="ck_issue_history_old_status",
        ),
        sa.CheckConstraint(
            "new_status IN ('NEW', 'ASSIGNED', 'INVESTIGATING', "
            "'WAITING_FOR_RESOLUTION', 'RESOLVED', 'VERIFIED', 'CLOSED', 'CANCELLED')",
            name="ck_issue_history_new_status",
        ),
        sa.CheckConstraint(
            "old_priority IS NULL OR old_priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="ck_issue_history_old_priority",
        ),
        sa.CheckConstraint(
            "new_priority IS NULL OR new_priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="ck_issue_history_new_priority",
        ),
        schema=schema,
    )
    op.create_index(
        "ix_dq_issue_history_issue_sequence",
        "issue_history",
        ["issue_id", "sequence_no"],
        schema=schema,
    )
    op.create_table(
        "issue_resolutions",
        sa.Column("sequence_no", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("resolution_id", sa.String(36), nullable=False, unique=True),
        sa.Column("issue_id", sa.String(36), sa.ForeignKey(issue_fk), nullable=False),
        sa.Column("root_cause", sa.Text(), nullable=False),
        sa.Column("corrective_action", sa.Text(), nullable=False),
        sa.Column("evidence_reference_id", sa.String(36), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("protection_policy_version", sa.String(80), nullable=False),
        sa.Column("created_by", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "length(btrim(root_cause)) BETWEEN 1 AND 2000 "
            "AND strpos(root_cause, '<') = 0 AND strpos(root_cause, '>') = 0",
            name="ck_issue_resolution_root_cause",
        ),
        sa.CheckConstraint(
            "length(btrim(corrective_action)) BETWEEN 1 AND 2000 "
            "AND strpos(corrective_action, '<') = 0 "
            "AND strpos(corrective_action, '>') = 0",
            name="ck_issue_resolution_corrective_action",
        ),
        schema=schema,
    )
    op.create_index(
        "ix_dq_issue_resolutions_issue_sequence",
        "issue_resolutions",
        ["issue_id", "sequence_no"],
        schema=schema,
    )
    op.create_table(
        "issue_verifications",
        sa.Column("sequence_no", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("verification_id", sa.String(36), nullable=False, unique=True),
        sa.Column("issue_id", sa.String(36), sa.ForeignKey(issue_fk), nullable=False),
        sa.Column("verification_reference_id", sa.String(36), nullable=False, unique=True),
        sa.Column("execution_id", sa.String(36), nullable=False),
        sa.Column("score_id", sa.String(36)),
        sa.Column("scope_type", sa.String(20), nullable=False),
        sa.Column("scope_id", sa.String(36), nullable=False),
        sa.Column("outcome", sa.String(30), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_by", sa.String(128), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "scope_type IN ('DATASET', 'SOURCE')",
            name="ck_issue_verification_scope_type",
        ),
        sa.CheckConstraint(
            "outcome IN ('QUALITY_FAILED', 'PARTIAL', 'TECHNICAL_ERROR', 'QUALITY_PASSED')",
            name="ck_issue_verification_outcome",
        ),
        schema=schema,
    )
    op.create_index(
        "ix_dq_issue_verifications_issue_sequence",
        "issue_verifications",
        ["issue_id", "sequence_no"],
        schema=schema,
    )
    op.create_table(
        "issue_relationships",
        sa.Column("sequence_no", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("relationship_id", sa.String(36), nullable=False, unique=True),
        sa.Column(
            "predecessor_issue_id",
            sa.String(36),
            sa.ForeignKey(issue_fk),
            nullable=False,
        ),
        sa.Column(
            "successor_issue_id",
            sa.String(36),
            sa.ForeignKey(issue_fk),
            nullable=False,
        ),
        sa.Column("relationship_type", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "relationship_type IN ('RECURRENCE')",
            name="ck_issue_relationship_type",
        ),
        sa.UniqueConstraint(
            "predecessor_issue_id",
            "successor_issue_id",
            "relationship_type",
            name="uq_issue_relationship",
        ),
        schema=schema,
    )
    op.create_index(
        "ix_dq_issue_relationships_predecessor_sequence",
        "issue_relationships",
        ["predecessor_issue_id", "sequence_no"],
        schema=schema,
    )


def downgrade() -> None:
    raise RuntimeError("Production downgrade is disabled; create a forward corrective migration.")
