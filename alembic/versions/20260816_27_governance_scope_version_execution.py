"""Execution yönetişim talepleri için scope_version=0'ı meşru kıl.

Migration 24, ``scope_version > 0`` check constraint'i koymuştu. Ancak
execution alanındaki üç talep tipi (manual start, cancel, dead-letter
reprocess) versiyonlanmış tek bir nesneye bağlanmadığı için domain
``scope_version=0`` üretir; bu değer ``_assert_object_unchanged`` içinde
"nesne henüz yok" anlamına gelir. Sonuç: bu üç iş akışının INSERT'i
production PostgreSQL'de check-constraint ihlaliyle düşüyordu.

Constraint kaldırılmaz, request-type'a duyarlı hale getirilir: yalnız
execution tipleri 0 taşıyabilir, diğer tüm tipler pozitif versiyon
zorunluluğunu korur.

Revision ID: 20260816_27
Revises: 20260816_26
"""

from __future__ import annotations

from alembic import op

revision = "20260816_27"
down_revision = "20260816_26"
branch_labels = None
depends_on = None

#: scope_version=0 taşımasına izin verilen talep tipleri.
#: tests/unit/test_governance_scope_version_constraint.py bu demeti
#: ``veri_kalitesi.governance.service._EXECUTION_REQUEST_TYPES`` ile eşleştirir.
EXECUTION_REQUEST_TYPES = (
    "EXECUTION_MANUAL_START",
    "EXECUTION_CANCEL",
    "DEAD_LETTER_REPROCESS",
)

SCOPE_VERSION_CHECK = "scope_version > 0 OR request_type IN ({types})".format(
    types=", ".join(f"'{name}'" for name in EXECUTION_REQUEST_TYPES)
)

CONSTRAINT_NAME = "ck_governance_approval_scope_version"


def _schema() -> str:
    return op.get_context().config.get_main_option("data_quality_schema", "dq")


def upgrade() -> None:
    schema = _schema()
    op.drop_constraint(
        CONSTRAINT_NAME, "governance_approval_requests", schema=schema, type_="check"
    )
    op.create_check_constraint(
        CONSTRAINT_NAME,
        "governance_approval_requests",
        SCOPE_VERSION_CHECK,
        schema=schema,
    )


def downgrade() -> None:
    """İleri düzeltme politikası; downgrade yalnız Alembic sözleşmesi içindir."""

    schema = _schema()
    op.drop_constraint(
        CONSTRAINT_NAME, "governance_approval_requests", schema=schema, type_="check"
    )
    op.create_check_constraint(
        CONSTRAINT_NAME,
        "governance_approval_requests",
        "scope_version > 0",
        schema=schema,
    )
