"""Yeni kural tipleri: ALLOWED_VALUES, LENGTH_CHECK, FORMAT_CHECK.

Revision ID: 20260810_22
Revises: 20260810_21

rule_versions tablosundaki rule_type CHECK constraint'i genişletilerek
üç yeni kural tipi eklenir:
  - ALLOWED_VALUES: Alan değeri önceden tanımlı küme içinde olmalı
  - LENGTH_CHECK: Karakter uzunluğu sınırları kontrolü
  - FORMAT_CHECK: Yapılandırılmış format doğrulama (EMAIL, IBAN, PHONE vb.)
"""

from __future__ import annotations

from alembic import op

revision = "20260810_22"
down_revision = "20260810_21"
branch_labels = None
depends_on = None


def _schema() -> str:
    return op.get_context().config.get_main_option("data_quality_schema", "dq")


def upgrade() -> None:
    schema = _schema()

    # Mevcut CHECK constraint'i kaldır
    op.drop_constraint(
        "ck_rule_versions_rule_type",
        "rule_versions",
        type_="check",
        schema=schema,
    )

    # Genişletilmiş CHECK constraint ile yeniden oluştur
    op.create_check_constraint(
        "ck_rule_versions_rule_type",
        "rule_versions",
        "rule_type IN "
        "('REQUIRED', 'UNIQUE', 'RANGE', 'REGEX', 'FRESHNESS', "
        "'REFERENTIAL_INTEGRITY', 'CROSS_TABLE_CONSISTENCY', 'CUSTOM_SQL', "
        "'ALLOWED_VALUES', 'LENGTH_CHECK', 'FORMAT_CHECK')",
        schema=schema,
    )


def downgrade() -> None:
    schema = _schema()

    # Eski constraint'e geri dön
    op.drop_constraint(
        "ck_rule_versions_rule_type",
        "rule_versions",
        type_="check",
        schema=schema,
    )
    op.create_check_constraint(
        "ck_rule_versions_rule_type",
        "rule_versions",
        "rule_type IN "
        "('REQUIRED', 'UNIQUE', 'RANGE', 'REGEX', 'FRESHNESS', "
        "'REFERENTIAL_INTEGRITY', 'CROSS_TABLE_CONSISTENCY', 'CUSTOM_SQL')",
        schema=schema,
    )
