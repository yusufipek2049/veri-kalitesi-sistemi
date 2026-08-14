"""request_type kolonu + execution source_ids JSON düzeltmesi + skor publication bağlantısı.

Revision ID: 20260810_21
Revises: 20260806_20

Sorunlar:
  1. data_source_activation_requests tablosunda request_type kolonu eksik.
     Kod ACTIVATION/DEACTIVATION ayrımı yapıyor ama tabloya yansımamış.
  2. rule_executions.source_ids ve rule_version_ids JSON kolonları
     seed sırasında json.dumps() ile çift-kodlanmış (scalar string olmuş).
     json_array_length() scalar üzerinde hata veriyor.
  3. quality_scores tablosundaki seed skorlarının publication_id'si NULL.
     list_scores sorgusu publication_id IS NOT NULL filtresi uyguladığı
     için skorlar görüntülenemiyor.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260810_21"
down_revision = "20260806_20"
branch_labels = None
depends_on = None


def _schema() -> str:
    return op.get_context().config.get_main_option("data_quality_schema", "dq")


def upgrade() -> None:
    schema = _schema()
    bind = op.get_bind()

    # 1. request_type kolonu ekle (varsayılan ACTIVATION)
    existing = bind.execute(
        sa.text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = :schema AND table_name = 'data_source_activation_requests' "
            "AND column_name = 'request_type'"
        ),
        {"schema": schema},
    ).fetchone()

    if existing is None:
        op.add_column(
            "data_source_activation_requests",
            sa.Column(
                "request_type",
                sa.String(20),
                nullable=False,
                server_default="ACTIVATION",
            ),
            schema=schema,
        )

    # 2. rule_executions JSON kolonlarını düzelt: çift-kodlanmış string'leri aç
    _fix_json_column(bind, schema, "rule_executions", "source_ids")
    _fix_json_column(bind, schema, "rule_executions", "rule_version_ids")

    # 3. publication_id'si NULL olan skorları bir publication'a bağla
    _fix_orphan_scores(bind, schema)


def _fix_json_column(bind, schema: str, table: str, column: str) -> None:
    """JSON kolonundaki çift-kodlanmış scalar string'leri gerçek JSON array'e dönüştür."""
    rows = bind.execute(
        sa.text(
            f'SELECT ctid, {column} FROM "{schema}".{table} '
            f"WHERE {column} IS NOT NULL "
            f"AND left({column}::text, 1) = '\"'"
        )
    ).fetchall()

    import json

    for row in rows:
        ctid = row[0]
        raw = row[1]
        try:
            # Çift-kodlanmış: json.loads bir kere açınca Python listesi verir
            parsed = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(parsed, str):
                # Hala string ise tekrar dene
                parsed = json.loads(parsed)
            # Şimdi düzgün JSON olarak yaz
            bind.execute(
                sa.text(f'UPDATE "{schema}".{table} SET {column} = :val WHERE ctid = :ctid'),
                {"val": json.dumps(parsed), "ctid": ctid},
            )
        except (json.JSONDecodeError, TypeError):
            # Bozuk veri — boş array'e sıfırla
            bind.execute(
                sa.text(f'UPDATE "{schema}".{table} SET {column} = :val WHERE ctid = :ctid'),
                {"val": "[]", "ctid": ctid},
            )


def _fix_orphan_scores(bind, schema: str) -> None:
    """publication_id'si NULL olan skorları bir publication kaydına bağlar.

    Seed skoru publication olmadan eklenmişti; list_scores sorgusu
    publication_id IS NOT NULL filtresi uyguladığı için görüntülenemiyordu.
    """
    import uuid
    from datetime import datetime, timezone

    orphan_count = bind.execute(
        sa.text(f'SELECT COUNT(*) FROM "{schema}".quality_scores WHERE publication_id IS NULL')
    ).scalar()

    if orphan_count == 0:
        return

    # Mevcut publication'lardan birini kullan veya yeni oluştur
    existing_pub = bind.execute(
        sa.text(f'SELECT publication_id FROM "{schema}".score_publications LIMIT 1')
    ).scalar()

    if existing_pub is None:
        pub_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        bind.execute(
            sa.text(
                f'INSERT INTO "{schema}".score_publications '
                f"(publication_id, execution_id, period, input_digest, status, policy_version, published_at) "
                f"VALUES (:pub_id, :exec_id, :period, :digest, :status, :policy, :published)"
            ),
            {
                "pub_id": pub_id,
                "exec_id": str(uuid.uuid4()),
                "period": "MIGRATION_BACKFILL",
                "digest": "sha256:migration-backfill",
                "status": "PUBLISHED",
                "policy": "MIGRATION",
                "published": now,
            },
        )
        existing_pub = pub_id

    bind.execute(
        sa.text(
            f'UPDATE "{schema}".quality_scores '
            f"SET publication_id = :pub_id WHERE publication_id IS NULL"
        ),
        {"pub_id": existing_pub},
    )


def downgrade() -> None:
    schema = _schema()
    op.drop_column("data_source_activation_requests", "request_type", schema=schema)
