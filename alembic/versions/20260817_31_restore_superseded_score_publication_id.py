"""Supersede işlemi sırasında publication_id'si NULL yapılan skorları geri yükle.

Önceki sürümlerde _atomic_publish, eski yayını SUPERSEDED ederken
eskisinin scores'larının publication_id değerini NULL yapıyordu.
list_scores sorgusu publication_id IS NOT NULL filtresi uyguladığı
için bu skorlar hem skor ekranından hem de trend grafiğinden
kayboluyordu.

Bu migration:
  1. publication_id'si NULL olan quality_scores satırlarını
     execution_id üzerinden score_publications tablosuna eşleyerek
     orijinal publication_id değerini geri yükler.
  2. Eski skorların tekrar görünür olmasını sağlar.

Revision ID: 20260817_31
Revises: 20260817_30
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260817_31"
down_revision = "20260817_30"
branch_labels = None
depends_on = None


def _schema() -> str:
    return op.get_context().config.get_main_option("data_quality_schema", "dq")


def upgrade() -> None:
    schema = _schema()
    bind = op.get_bind()

    # execution_id ile score_publications'ı eşleyerek publication_id'yi geri yükle.
    # score_publications.execution_id UNIQUE olduğundan her execution tek bir
    # publication'a karşılık gelir; JOIN güvenlidir.
    bind.execute(
        sa.text(
            f'UPDATE "{schema}".quality_scores '
            f'SET publication_id = sp.publication_id '
            f'FROM "{schema}".score_publications sp '
            f'WHERE quality_scores.execution_id = sp.execution_id '
            f'AND quality_scores.publication_id IS NULL'
        )
    )


def downgrade() -> None:
    # Geri alma: superseded publication'lara ait skorların publication_id'sini
    # tekrar NULL yap. Bu, eski davranışı geri yükler.
    schema = _schema()
    bind = op.get_bind()

    bind.execute(
        sa.text(
            f'UPDATE "{schema}".quality_scores '
            f'SET publication_id = NULL '
            f'WHERE publication_id IN ('
            f'SELECT publication_id FROM "{schema}".score_publications '
            f"WHERE status = 'SUPERSEDED'"
            f')'
        )
    )
