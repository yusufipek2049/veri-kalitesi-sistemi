"""Skorlama konfigürasyonunun dataset kapsamına alınması.

ScoringConfiguration satırlarına dataset_id kolonu eklenir; NULL ise
global varsayılan konfigürasyonu, dolu ise belirli bir dataset'e özel
konfigürasyonu temsil eder. Aktif konfigürasyon sorguları için
dataset_id bazlı kısmi indeks oluşturulur.

Revision ID: 20260817_30
Revises: 20260817_29
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260817_30"
down_revision = "20260817_29"
branch_labels = None
depends_on = None


def _schema() -> str:
    return op.get_context().config.get_main_option("data_quality_schema", "dq")


def upgrade() -> None:
    schema = _schema()

    op.add_column(
        "scoring_configurations",
        sa.Column("dataset_id", sa.String(36), nullable=True),
        schema=schema,
    )
    op.create_index(
        "ix_scoring_configurations_dataset_active",
        "scoring_configurations",
        ["dataset_id", "is_active"],
        postgresql_where=sa.text("is_active = true"),
        schema=schema,
    )


def downgrade() -> None:
    """Üretim politikası ileri düzeltmedir; downgrade yalnız Alembic sözleşmesi içindir."""

    schema = _schema()
    op.drop_index(
        "ix_scoring_configurations_dataset_active",
        table_name="scoring_configurations",
        schema=schema,
    )
    op.drop_column("scoring_configurations", "dataset_id", schema=schema)
