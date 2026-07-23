"""PostgreSQL transaction sınırında redakte audit outbox."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    func,
    insert,
    select,
)
from sqlalchemy.orm import Session

from veri_kalitesi.audit.models import AuditEventInput, PreparedAuditEvent
from veri_kalitesi.audit.outbox import (
    AuditOutboxStatus,
    PreparedAuditRepository,
    prepared_audit_from_document,
    prepared_audit_to_document,
)
from veri_kalitesi.audit.redaction import AuditRedactor
from veri_kalitesi.persistence import DEFAULT_SCHEMA_NAME, SessionFactory, transactional_session


def audit_outbox_table(schema: str = DEFAULT_SCHEMA_NAME) -> Table:
    return Table(
        "audit_outbox",
        MetaData(schema=schema),
        Column("event_id", String(36), primary_key=True),
        Column("prepared_event", JSON, nullable=False),
        Column("policy_version", String(80), nullable=False),
        Column("status", String(20), nullable=False),
        Column("attempt_count", Integer, nullable=False),
        Column("last_error_code", String(100)),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("published_at", DateTime(timezone=True)),
    )


class PostgreSQLTransactionalAudit:
    def __init__(
        self,
        session_factory: SessionFactory,
        redactor: AuditRedactor,
        repository: PreparedAuditRepository,
        *,
        policy_version: str,
        schema: str = DEFAULT_SCHEMA_NAME,
    ) -> None:
        if not policy_version.strip():
            raise ValueError("Audit outbox policy version is required.")
        self.session_factory = session_factory
        self.redactor = redactor
        self.repository = repository
        self.policy_version = policy_version
        self.table = audit_outbox_table(schema)

    def prepare(self, event: AuditEventInput) -> PreparedAuditEvent:
        return self.redactor.prepare(event)

    def stage(self, prepared: PreparedAuditEvent, *, session: Session) -> None:
        if session.get_bind() is not self.session_factory.kw["bind"]:
            raise ValueError("Audit outbox must share the issue transaction.")
        session.execute(
            insert(self.table).values(
                event_id=prepared.event_id,
                prepared_event=prepared_audit_to_document(prepared),
                policy_version=self.policy_version,
                status="PENDING",
                attempt_count=0,
                created_at=datetime.now(timezone.utc),
            )
        )

    def publish_pending(self, *, limit: int = 100) -> AuditOutboxStatus:
        published = 0
        failed = 0
        with transactional_session(self.session_factory) as session:
            rows = (
                session.execute(
                    select(self.table)
                    .where(self.table.c.status == "PENDING")
                    .order_by(self.table.c.created_at, self.table.c.event_id)
                    .limit(limit)
                    .with_for_update(skip_locked=True)
                )
                .mappings()
                .all()
            )
            for row in rows:
                try:
                    self.repository.append(
                        prepared_audit_from_document(dict(row["prepared_event"]))
                    )
                except Exception:
                    failed += 1
                    session.execute(
                        self.table.update()
                        .where(
                            self.table.c.event_id == row["event_id"],
                            self.table.c.status == "PENDING",
                        )
                        .values(
                            attempt_count=self.table.c.attempt_count + 1,
                            last_error_code="AUDIT_REPOSITORY_UNAVAILABLE",
                        )
                    )
                    continue
                published += 1
                session.execute(
                    self.table.update()
                    .where(
                        self.table.c.event_id == row["event_id"],
                        self.table.c.status == "PENDING",
                    )
                    .values(
                        status="PUBLISHED",
                        attempt_count=self.table.c.attempt_count + 1,
                        last_error_code=None,
                        published_at=datetime.now(timezone.utc),
                    )
                )
            pending = session.scalar(
                select(func.count()).select_from(self.table).where(self.table.c.status == "PENDING")
            )
        return AuditOutboxStatus(pending or 0, published, failed)

    def list_pending(self) -> list[PreparedAuditEvent]:
        with self.session_factory() as session:
            rows = (
                session.execute(
                    select(self.table.c.prepared_event)
                    .where(self.table.c.status == "PENDING")
                    .order_by(self.table.c.created_at, self.table.c.event_id)
                )
                .scalars()
                .all()
            )
        return [prepared_audit_from_document(dict(row)) for row in rows]
