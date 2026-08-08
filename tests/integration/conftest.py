"""Entegrasyon testleri için ortak fixture ve yardımcılar.

Proje kökündeki .env dosyası PostgreSQL bağlantı bilgilerini içerir.
Bu dosya .gitignore ile git dışındadır, local geliştirme içindir.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

from veri_kalitesi.audit.models import AuditEvent, PreparedAuditEvent

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


class FakePreparedAuditRepository:
    """PreparedAuditRepository protocol'ünü gerçekleyen test double.

    Audit event'lerini kabul eder, kalıcılık yapmaz.
    publish_pending akışında repository.append() çağrıldığında
    başarılı yanıt döndürmek için kullanılır.
    """

    def __init__(self) -> None:
        self.events: list[PreparedAuditEvent] = []
        self.sequence = 0

    def append(self, prepared: PreparedAuditEvent) -> AuditEvent:
        self.sequence += 1
        self.events.append(prepared)
        return AuditEvent(
            sequence_no=self.sequence,
            event_id=prepared.event_id,
            event_version=prepared.event_version,
            occurred_at=prepared.occurred_at,
            actor_id=prepared.actor_id,
            actor_type=prepared.actor_type,
            session_id_digest=prepared.session_id_digest,
            correlation_id=prepared.correlation_id,
            action=prepared.action,
            object_type=prepared.object_type,
            object_id=prepared.object_id,
            result=prepared.result,
            reason_code=prepared.reason_code,
            old_value_summary=prepared.old_value_summary,
            new_value_summary=prepared.new_value_summary,
            old_value_digest=prepared.old_value_digest,
            new_value_digest=prepared.new_value_digest,
            redacted_fields=prepared.redacted_fields,
            redaction_policy_version=prepared.redaction_policy_version,
            previous_event_hash=str(uuid4()),
            event_hash=str(uuid4()),
        )
