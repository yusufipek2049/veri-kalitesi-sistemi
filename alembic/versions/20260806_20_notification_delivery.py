"""DS-09 kalıcı uygulama içi bildirim hattı.

Revision ID: 20260806_20
Revises: 20260806_19

DS-09 dikey dilimi:
  1. notification_channels — kanal yapılandırması (IN_APP + harici)
  2. notification_events — canonical iş olayı (immutable)
  3. notification_subscriptions — kullanıcı tercih/abonelik kayıtları
  4. notification_deliveries — teslimat durum makinesi (ST-NotificationDelivery)
  5. Check constraint'ler, unique constraint'ler, indeksler
  6. Varsayılan IN_APP kanal seed
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260806_20"
down_revision = "20260806_19"
branch_labels = None
depends_on = None


def _schema() -> str:
    return op.get_context().config.get_main_option("data_quality_schema", "dq")


def upgrade() -> None:
    schema = _schema()

    # ── 1. notification_channels ────────────────────────────────────────
    op.create_table(
        "notification_channels",
        sa.Column("channel_id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("channel_type", sa.String(24), nullable=False),
        sa.Column(
            "target_config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("secret_ref", sa.String(255), nullable=True),
        sa.Column(
            "allowed_event_types",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("status", sa.String(24), nullable=False, server_default="ACTIVE"),
        sa.Column("policy_version", sa.String(80), nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        schema=schema,
    )
    op.create_unique_constraint(
        "uq_notification_channel_name",
        "notification_channels",
        ["name"],
        schema=schema,
    )
    op.create_check_constraint(
        "ck_notification_channel_type",
        "notification_channels",
        "channel_type IN ('IN_APP','EMAIL','MESSAGING','SERVICENOW','JIRA')",
        schema=schema,
    )
    op.create_check_constraint(
        "ck_notification_channel_status",
        "notification_channels",
        "status IN ('ACTIVE','INACTIVE')",
        schema=schema,
    )
    op.create_check_constraint(
        "ck_notification_channel_version",
        "notification_channels",
        "version >= 1",
        schema=schema,
    )
    op.create_index(
        "ix_notification_channel_status_type",
        "notification_channels",
        ["status", "channel_type"],
        schema=schema,
    )

    # ── 2. notification_events ──────────────────────────────────────────
    op.create_table(
        "notification_events",
        sa.Column("event_id", sa.String(36), primary_key=True),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("scope_type", sa.String(30), nullable=False),
        sa.Column("scope_id", sa.String(128), nullable=False),
        sa.Column("source_ref", sa.String(200), nullable=False),
        sa.Column("deduplication_key_digest", sa.String(64), nullable=False),
        sa.Column("payload_digest", sa.String(64), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("correlation_id", sa.String(128), nullable=False),
        sa.Column("policy_version", sa.String(80), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        schema=schema,
    )
    op.create_unique_constraint(
        "uq_notification_event_source_type",
        "notification_events",
        ["source_ref", "event_type"],
        schema=schema,
    )
    op.create_check_constraint(
        "ck_notification_event_type",
        "notification_events",
        "event_type IN ("
        "'QUALITY_THRESHOLD','CRITICAL_RULE_FAILURE',"
        "'TECHNICAL_ERROR','ISSUE_ASSIGNED'"
        ")",
        schema=schema,
    )
    op.create_check_constraint(
        "ck_notification_event_scope_type",
        "notification_events",
        "scope_type IN ('RULE','DATASET','SOURCE','EXECUTION','ISSUE_ASSIGNMENT')",
        schema=schema,
    )
    op.create_index(
        "ix_notification_event_type_time",
        "notification_events",
        ["event_type", sa.text("published_at DESC")],
        schema=schema,
    )
    op.create_index(
        "ix_notification_event_scope_time",
        "notification_events",
        ["scope_type", "scope_id", sa.text("published_at DESC")],
        schema=schema,
    )

    # ── 3. notification_subscriptions ───────────────────────────────────
    op.create_table(
        "notification_subscriptions",
        sa.Column("subscription_id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(128), nullable=False),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("scope_type", sa.String(30), nullable=True),
        sa.Column("scope_id", sa.String(128), nullable=True),
        sa.Column("channel_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="ACTIVE"),
        sa.Column("policy_version", sa.String(80), nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(
            ["channel_id"],
            [f"{schema}.notification_channels.channel_id"],
            name="fk_notification_subscription_channel",
        ),
        schema=schema,
    )
    # Functional unique constraint requires a unique INDEX because PostgreSQL
    # UNIQUE constraints only accept plain column names, not expressions.
    op.create_index(
        "uq_notification_subscription",
        "notification_subscriptions",
        [
            "user_id",
            "event_type",
            sa.text("COALESCE(scope_type, '')"),
            sa.text("COALESCE(scope_id, '')"),
            "channel_id",
        ],
        unique=True,
        schema=schema,
    )
    op.create_check_constraint(
        "ck_notification_subscription_scope_consistency",
        "notification_subscriptions",
        "(scope_type IS NULL AND scope_id IS NULL) "
        "OR (scope_type IS NOT NULL AND scope_id IS NOT NULL)",
        schema=schema,
    )
    op.create_check_constraint(
        "ck_notification_subscription_status",
        "notification_subscriptions",
        "status IN ('ACTIVE','INACTIVE')",
        schema=schema,
    )
    op.create_check_constraint(
        "ck_notification_subscription_event_type",
        "notification_subscriptions",
        "event_type IN ("
        "'QUALITY_THRESHOLD','CRITICAL_RULE_FAILURE',"
        "'TECHNICAL_ERROR','ISSUE_ASSIGNED'"
        ")",
        schema=schema,
    )
    op.create_check_constraint(
        "ck_notification_subscription_version",
        "notification_subscriptions",
        "version >= 1",
        schema=schema,
    )
    op.create_index(
        "ix_notification_subscription_event_status",
        "notification_subscriptions",
        ["event_type", "status"],
        schema=schema,
    )
    op.create_index(
        "ix_notification_subscription_user_status",
        "notification_subscriptions",
        ["user_id", "status"],
        schema=schema,
    )

    # ── 4. notification_deliveries ──────────────────────────────────────
    op.create_table(
        "notification_deliveries",
        sa.Column("delivery_id", sa.String(36), primary_key=True),
        sa.Column("event_id", sa.String(36), nullable=False),
        sa.Column("recipient_user_id", sa.String(128), nullable=False),
        sa.Column("channel_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("attempt_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_error_class", sa.String(80), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rerouted_to_channel_id", sa.String(36), nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            [f"{schema}.notification_events.event_id"],
            name="fk_notification_delivery_event",
        ),
        sa.ForeignKeyConstraint(
            ["channel_id"],
            [f"{schema}.notification_channels.channel_id"],
            name="fk_notification_delivery_channel",
        ),
        sa.ForeignKeyConstraint(
            ["rerouted_to_channel_id"],
            [f"{schema}.notification_channels.channel_id"],
            name="fk_notification_delivery_reroute_channel",
        ),
        schema=schema,
    )
    op.create_unique_constraint(
        "uq_notification_delivery_recipient_channel",
        "notification_deliveries",
        ["event_id", "recipient_user_id", "channel_id"],
        schema=schema,
    )
    op.create_check_constraint(
        "ck_notification_delivery_status",
        "notification_deliveries",
        "status IN ('PENDING','SENDING','DELIVERED','FAILED','UNDELIVERABLE','REROUTED','READ')",
        schema=schema,
    )
    op.create_check_constraint(
        "ck_notification_delivery_attempt_count",
        "notification_deliveries",
        "attempt_count >= 0",
        schema=schema,
    )
    op.create_check_constraint(
        "ck_notification_delivery_version",
        "notification_deliveries",
        "version >= 1",
        schema=schema,
    )
    op.create_check_constraint(
        "ck_notification_delivery_read_requires_delivered",
        "notification_deliveries",
        "status != 'READ' OR (delivered_at IS NOT NULL AND read_at IS NOT NULL)",
        schema=schema,
    )
    op.create_check_constraint(
        "ck_notification_delivery_delivered_requires_timestamp",
        "notification_deliveries",
        "status NOT IN ('DELIVERED','READ') OR delivered_at IS NOT NULL",
        schema=schema,
    )
    op.create_check_constraint(
        "ck_notification_delivery_rerouted_requires_target",
        "notification_deliveries",
        "status != 'REROUTED' OR rerouted_to_channel_id IS NOT NULL",
        schema=schema,
    )
    op.create_index(
        "ix_notification_delivery_recipient_status_time",
        "notification_deliveries",
        ["recipient_user_id", "status", sa.text("created_at DESC")],
        schema=schema,
    )
    op.create_index(
        "ix_notification_delivery_retry_pending",
        "notification_deliveries",
        ["status", "next_attempt_at"],
        schema=schema,
        postgresql_where=sa.text("status IN ('PENDING','FAILED')"),
    )
    op.create_index(
        "ix_notification_delivery_event",
        "notification_deliveries",
        ["event_id"],
        schema=schema,
    )

    # ── 5. Default IN_APP channel seed ──────────────────────────────────
    op.execute(
        f"""
        INSERT INTO {schema}.notification_channels (
            channel_id, name, channel_type, target_config, secret_ref,
            allowed_event_types, status, policy_version, version,
            created_by, created_at, updated_at
        ) SELECT
            'default-inapp-channel',
            'Uygulama İçi Bildirim',
            'IN_APP',
            '{{}}'::jsonb,
            NULL,
            '["QUALITY_THRESHOLD","CRITICAL_RULE_FAILURE",'
            '"TECHNICAL_ERROR","ISSUE_ASSIGNED"]'::jsonb,
            'ACTIVE',
            'DS09_CHANNEL_POLICY_V1',
            1,
            'system',
            NOW(),
            NOW()
        WHERE NOT EXISTS (
            SELECT 1 FROM {schema}.notification_channels
            WHERE channel_type = 'IN_APP' LIMIT 1
        )
        """
    )


def downgrade() -> None:
    raise RuntimeError(
        "Production downgrade is disabled for DS-09 notification delivery; "
        "create a forward corrective migration instead."
    )
