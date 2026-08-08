"""S1 data-source command invariants and PostgreSQL audit ledger.

Revision ID: 20260805_15
Revises: 20260730_14
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260805_15"
down_revision = "20260730_14"
branch_labels = None
depends_on = None


def _schema() -> str:
    return op.get_context().config.get_main_option("data_quality_schema", "dq")


def upgrade() -> None:
    schema = _schema()
    bind = op.get_bind()
    duplicate = (
        bind.execute(
            sa.text(
                f'''SELECT data_source_id, data_source_revision, count(*) AS row_count
                FROM "{schema}".data_source_activation_requests
                WHERE status = 'PENDING'
                GROUP BY data_source_id, data_source_revision
                HAVING count(*) > 1
                LIMIT 1'''
            )
        )
        .mappings()
        .first()
    )
    if duplicate is not None:
        raise RuntimeError(
            "Duplicate pending data-source activation requests must be resolved before migration."
        )
    unknown_type = bind.execute(
        sa.text(
            f'''SELECT source_type FROM "{schema}".data_sources
                WHERE source_type NOT IN
                    ('POSTGRESQL','MSSQL','ORACLE','MYSQL','CSV','EXCEL','REST')
                LIMIT 1'''
        )
    ).scalar_one_or_none()
    if unknown_type is not None:
        raise RuntimeError(
            f"Unsupported existing data source type must be remediated: {unknown_type}"
        )

    op.create_index(
        "uq_activation_requests_pending_source_revision",
        "data_source_activation_requests",
        ["data_source_id", "data_source_revision"],
        unique=True,
        schema=schema,
        postgresql_where=sa.text("status = 'PENDING'"),
    )
    op.drop_constraint("ck_data_sources_source_type", "data_sources", schema=schema, type_="check")
    op.create_check_constraint(
        "ck_data_sources_source_type",
        "data_sources",
        "source_type IN ('POSTGRESQL','MSSQL','ORACLE','MYSQL','CSV','EXCEL','REST')",
        schema=schema,
    )

    op.create_table(
        "audit_events",
        sa.Column("sequence_no", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("event_id", sa.String(36), nullable=False),
        sa.Column("event_version", sa.String(80), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_id", sa.String(128), nullable=False),
        sa.Column("actor_type", sa.String(40), nullable=True),
        sa.Column("session_id_digest", sa.String(64), nullable=True),
        sa.Column("correlation_id", sa.String(128), nullable=False),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("object_type", sa.String(120), nullable=False),
        sa.Column("object_id", sa.String(256), nullable=True),
        sa.Column("result", sa.String(20), nullable=False),
        sa.Column("reason_code", sa.String(120), nullable=False),
        sa.Column("old_value_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("new_value_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("old_value_digest", sa.String(64), nullable=False),
        sa.Column("new_value_digest", sa.String(64), nullable=False),
        sa.Column("redacted_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("redaction_policy_version", sa.String(80), nullable=False),
        sa.Column("previous_event_hash", sa.String(64), nullable=False),
        sa.Column("event_hash", sa.String(64), nullable=False),
        sa.CheckConstraint(
            "result IN ('SUCCESS','FAILURE','DENIED')", name="ck_audit_events_result"
        ),
        sa.UniqueConstraint("event_id", name="uq_audit_events_event_id"),
        sa.UniqueConstraint("event_hash", name="uq_audit_events_event_hash"),
        schema=schema,
    )
    op.create_index(
        "ix_audit_events_time", "audit_events", ["occurred_at", "sequence_no"], schema=schema
    )
    op.create_index(
        "ix_audit_events_correlation",
        "audit_events",
        ["correlation_id", "sequence_no"],
        schema=schema,
    )


def downgrade() -> None:
    raise RuntimeError(
        "Production downgrade is disabled for the append-only audit ledger; "
        "create a forward corrective migration instead."
    )
