"""Notification event type check constraint genişletmesi.

notification_events tablosundaki ck_notification_event_type ve
ck_notification_event_scope_type check constraint'leri, rule approval
ve governance approval event type'larını da kabul edecek şekilde
genişletilir.

Revision ID: 20260817_32
Revises: 20260817_31
"""

from __future__ import annotations

from alembic import op

revision = "20260817_32"
down_revision = "20260817_31"
branch_labels = None
depends_on = None


def _schema() -> str:
    return op.get_context().config.get_main_option("data_quality_schema", "dq")


_ALL_EVENT_TYPES = (
    "'QUALITY_THRESHOLD','CRITICAL_RULE_FAILURE',"
    "'TECHNICAL_ERROR','ISSUE_ASSIGNED',"
    "'RULE_APPROVAL_REQUESTED','RULE_APPROVAL_DECIDED',"
    "'RULE_APPROVAL_WITHDRAWN','RULE_APPROVAL_EXPIRED',"
    "'GOVERNANCE_APPROVAL_REQUESTED','GOVERNANCE_APPROVAL_DECIDED',"
    "'GOVERNANCE_APPROVAL_REJECTED','GOVERNANCE_APPROVAL_WITHDRAWN'"
)

_ALL_SCOPE_TYPES = (
    "'RULE','DATASET','SOURCE','EXECUTION',"
    "'ISSUE_ASSIGNMENT','GOVERNANCE'"
)


def upgrade() -> None:
    schema = _schema()

    op.drop_constraint(
        "ck_notification_event_type",
        "notification_events",
        schema=schema,
    )
    op.create_check_constraint(
        "ck_notification_event_type",
        "notification_events",
        f"event_type IN ({_ALL_EVENT_TYPES})",
        schema=schema,
    )

    op.drop_constraint(
        "ck_notification_event_scope_type",
        "notification_events",
        schema=schema,
    )
    op.create_check_constraint(
        "ck_notification_event_scope_type",
        "notification_events",
        f"scope_type IN ({_ALL_SCOPE_TYPES})",
        schema=schema,
    )


def downgrade() -> None:
    """Check constraint genişletmesi; downgrade yalnız Alembic sözleşmesi içindir."""

    schema = _schema()

    op.drop_constraint(
        "ck_notification_event_type",
        "notification_events",
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

    op.drop_constraint(
        "ck_notification_event_scope_type",
        "notification_events",
        schema=schema,
    )
    op.create_check_constraint(
        "ck_notification_event_scope_type",
        "notification_events",
        "scope_type IN ('RULE','DATASET','SOURCE','EXECUTION','ISSUE_ASSIGNMENT')",
        schema=schema,
    )
