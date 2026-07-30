"""Deterministik profil karşılaştırma sonuçları.

Revision ID: 20260729_11
Revises: 20260729_10
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260729_11"
down_revision = "20260729_10"
branch_labels = None
depends_on = None


def _schema() -> str:
    return op.get_context().config.get_main_option("data_quality_schema", "dq")


def upgrade() -> None:
    schema = _schema()
    op.drop_constraint(
        "ck_data_profiles_method",
        "data_profiles",
        schema=schema,
        type_="check",
    )
    op.drop_constraint(
        "ck_data_profiles_status",
        "data_profiles",
        schema=schema,
        type_="check",
    )
    op.create_check_constraint(
        "ck_data_profiles_method",
        "data_profiles",
        "method IN ('FULL', 'SAMPLE', 'PARTITION', 'AGGREGATE')",
        schema=schema,
    )
    op.create_check_constraint(
        "ck_data_profiles_status",
        "data_profiles",
        "status IN ('COMPLETED', 'NO_DATA', 'TECHNICAL_ERROR')",
        schema=schema,
    )
    op.create_table(
        "profile_comparisons",
        sa.Column("comparison_id", sa.String(36), primary_key=True),
        sa.Column("dataset_id", sa.String(36), nullable=False),
        sa.Column("baseline_profile_id", sa.String(36), nullable=False),
        sa.Column("current_profile_id", sa.String(36), nullable=False),
        sa.Column("policy_version", sa.String(100), nullable=True),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("anomaly_candidate", sa.Boolean(), nullable=True),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], [f"{schema}.datasets.dataset_id"]),
        sa.ForeignKeyConstraint(["baseline_profile_id"], [f"{schema}.data_profiles.profile_id"]),
        sa.ForeignKeyConstraint(["current_profile_id"], [f"{schema}.data_profiles.profile_id"]),
        sa.CheckConstraint(
            "status IN ('COMPLETED', 'CONFIGURATION_ERROR', "
            "'INSUFFICIENT_HISTORY', 'INCOMPATIBLE')",
            name="ck_profile_comparisons_status",
        ),
        schema=schema,
    )
    op.create_index(
        "ix_dq_profile_comparisons_dataset_created",
        "profile_comparisons",
        ["dataset_id", "created_at"],
        schema=schema,
    )


def downgrade() -> None:
    schema = _schema()
    op.drop_index(
        "ix_dq_profile_comparisons_dataset_created",
        table_name="profile_comparisons",
        schema=schema,
    )
    op.drop_table("profile_comparisons", schema=schema)
    op.drop_constraint(
        "ck_data_profiles_method",
        "data_profiles",
        schema=schema,
        type_="check",
    )
    op.drop_constraint(
        "ck_data_profiles_status",
        "data_profiles",
        schema=schema,
        type_="check",
    )
    op.create_check_constraint(
        "ck_data_profiles_method",
        "data_profiles",
        "method IN ('FULL', 'SAMPLE')",
        schema=schema,
    )
    op.create_check_constraint(
        "ck_data_profiles_status",
        "data_profiles",
        "status IN ('COMPLETED', 'FAILED', 'TIMEOUT', 'CANCELLED')",
        schema=schema,
    )
