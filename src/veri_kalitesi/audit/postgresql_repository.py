"""PostgreSQL append-only audit ledger ve bütünlük sorguları."""

from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Index,
    JSON,
    MetaData,
    String,
    Table,
    and_,
    func,
    insert,
    select,
)
from sqlalchemy.engine import RowMapping

from veri_kalitesi.audit.errors import AuditValidationError
from veri_kalitesi.audit.models import (
    AuditEvent,
    AuditIntegrityResult,
    AuditQuery,
    AuditResult,
    PreparedAuditEvent,
)
from veri_kalitesi.audit.repository import GENESIS_HASH, compute_event_hash
from veri_kalitesi.persistence import DEFAULT_SCHEMA_NAME, SessionFactory, transactional_session

_AUDIT_CHAIN_LOCK_KEY = 864_205_081


def audit_events_table(schema: str = DEFAULT_SCHEMA_NAME) -> Table:
    table = Table(
        "audit_events",
        MetaData(schema=schema),
        Column("sequence_no", BigInteger, primary_key=True, autoincrement=True),
        Column("event_id", String(36), nullable=False, unique=True),
        Column("event_version", String(80), nullable=False),
        Column("occurred_at", DateTime(timezone=True), nullable=False),
        Column("actor_id", String(128), nullable=False),
        Column("actor_type", String(40)),
        Column("session_id_digest", String(64)),
        Column("correlation_id", String(128), nullable=False),
        Column("action", String(120), nullable=False),
        Column("object_type", String(120), nullable=False),
        Column("object_id", String(256)),
        Column("result", String(20), nullable=False),
        Column("reason_code", String(120), nullable=False),
        Column("old_value_summary", JSON, nullable=False),
        Column("new_value_summary", JSON, nullable=False),
        Column("old_value_digest", String(64), nullable=False),
        Column("new_value_digest", String(64), nullable=False),
        Column("redacted_fields", JSON, nullable=False),
        Column("redaction_policy_version", String(80), nullable=False),
        Column("previous_event_hash", String(64), nullable=False),
        Column("event_hash", String(64), nullable=False, unique=True),
    )
    Index("ix_audit_events_time", table.c.occurred_at, table.c.sequence_no)
    Index("ix_audit_events_correlation", table.c.correlation_id, table.c.sequence_no)
    return table


class PostgreSQLAuditRepository:
    """Advisory transaction lock ile serialize edilen kalıcı audit zinciri."""

    def __init__(
        self,
        session_factory: SessionFactory,
        *,
        schema: str = DEFAULT_SCHEMA_NAME,
    ) -> None:
        self.session_factory = session_factory
        self.table = audit_events_table(schema)

    def append(self, prepared: PreparedAuditEvent) -> AuditEvent:
        with transactional_session(self.session_factory) as session:
            session.execute(select(func.pg_advisory_xact_lock(_AUDIT_CHAIN_LOCK_KEY)))
            existing = (
                session.execute(
                    select(self.table).where(self.table.c.event_id == prepared.event_id)
                )
                .mappings()
                .one_or_none()
            )
            if existing is not None:
                event = _row_to_event(existing)
                if _event_to_prepared(event) != prepared:
                    raise AuditValidationError(
                        "Audit event_id cannot be reused with different content."
                    )
                return event
            previous_hash = (
                session.scalar(
                    select(self.table.c.event_hash)
                    .order_by(self.table.c.sequence_no.desc())
                    .limit(1)
                )
                or GENESIS_HASH
            )
            event_hash = compute_event_hash(prepared, previous_hash)
            sequence_no = session.scalar(
                insert(self.table)
                .values(**_insert_values(prepared, previous_hash, event_hash))
                .returning(self.table.c.sequence_no)
            )
            if sequence_no is None:
                raise AuditValidationError("Audit event sequence could not be assigned.")
        return _to_event(prepared, int(sequence_no), previous_hash, event_hash)

    def query_events(self, query: AuditQuery) -> tuple[tuple[AuditEvent, ...], bool]:
        clauses = [
            self.table.c.sequence_no > query.after_sequence_no,
            self.table.c.occurred_at >= query.start_at,
            self.table.c.occurred_at <= query.end_at,
        ]
        if query.through_sequence_no is not None:
            clauses.append(self.table.c.sequence_no <= query.through_sequence_no)
        optional_filters = (
            (self.table.c.actor_id, query.actor_id),
            (self.table.c.action, query.action),
            (self.table.c.object_type, query.object_type),
            (self.table.c.object_id, query.object_id),
            (self.table.c.correlation_id, query.correlation_id),
            (self.table.c.result, query.result.value if query.result is not None else None),
        )
        clauses.extend(column == value for column, value in optional_filters if value is not None)
        with self.session_factory() as session:
            rows = (
                session.execute(
                    select(self.table)
                    .where(and_(*clauses))
                    .order_by(self.table.c.sequence_no)
                    .limit(query.page_size + 1)
                )
                .mappings()
                .all()
            )
        has_more = len(rows) > query.page_size
        return tuple(_row_to_event(row) for row in rows[: query.page_size]), has_more

    def latest_sequence_no(self) -> int:
        with self.session_factory() as session:
            return int(
                session.scalar(select(func.coalesce(func.max(self.table.c.sequence_no), 0))) or 0
            )

    def verify_integrity(self) -> AuditIntegrityResult:
        with self.session_factory() as session:
            rows = (
                session.execute(select(self.table).order_by(self.table.c.sequence_no))
                .mappings()
                .all()
            )
        previous_hash = GENESIS_HASH
        for index, row in enumerate(rows, start=1):
            try:
                event = _row_to_event(row)
                expected_hash = compute_event_hash(_event_to_prepared(event), previous_hash)
            except (TypeError, ValueError):
                return AuditIntegrityResult(False, index, str(row["event_id"]))
            if event.previous_event_hash != previous_hash or event.event_hash != expected_hash:
                return AuditIntegrityResult(False, index, event.event_id)
            previous_hash = event.event_hash
        return AuditIntegrityResult(True, len(rows))


def _insert_values(
    prepared: PreparedAuditEvent, previous_hash: str, event_hash: str
) -> dict[str, object]:
    return {
        "event_id": prepared.event_id,
        "event_version": prepared.event_version,
        "occurred_at": prepared.occurred_at,
        "actor_id": prepared.actor_id,
        "actor_type": prepared.actor_type,
        "session_id_digest": prepared.session_id_digest,
        "correlation_id": prepared.correlation_id,
        "action": prepared.action,
        "object_type": prepared.object_type,
        "object_id": prepared.object_id,
        "result": prepared.result.value,
        "reason_code": prepared.reason_code,
        "old_value_summary": dict(prepared.old_value_summary),
        "new_value_summary": dict(prepared.new_value_summary),
        "old_value_digest": prepared.old_value_digest,
        "new_value_digest": prepared.new_value_digest,
        "redacted_fields": list(prepared.redacted_fields),
        "redaction_policy_version": prepared.redaction_policy_version,
        "previous_event_hash": previous_hash,
        "event_hash": event_hash,
    }


def _row_to_event(row: RowMapping) -> AuditEvent:
    return AuditEvent(
        sequence_no=int(row["sequence_no"]),
        event_id=str(row["event_id"]),
        event_version=str(row["event_version"]),
        occurred_at=row["occurred_at"],
        actor_id=str(row["actor_id"]),
        actor_type=row["actor_type"],
        session_id_digest=row["session_id_digest"],
        correlation_id=str(row["correlation_id"]),
        action=str(row["action"]),
        object_type=str(row["object_type"]),
        object_id=row["object_id"],
        result=AuditResult(str(row["result"])),
        reason_code=str(row["reason_code"]),
        old_value_summary=dict(row["old_value_summary"]),
        new_value_summary=dict(row["new_value_summary"]),
        old_value_digest=str(row["old_value_digest"]),
        new_value_digest=str(row["new_value_digest"]),
        redacted_fields=tuple(row["redacted_fields"]),
        redaction_policy_version=str(row["redaction_policy_version"]),
        previous_event_hash=str(row["previous_event_hash"]),
        event_hash=str(row["event_hash"]),
    )


def _event_to_prepared(event: AuditEvent) -> PreparedAuditEvent:
    return PreparedAuditEvent(
        event_id=event.event_id,
        event_version=event.event_version,
        occurred_at=event.occurred_at,
        actor_id=event.actor_id,
        actor_type=event.actor_type,
        session_id_digest=event.session_id_digest,
        correlation_id=event.correlation_id,
        action=event.action,
        object_type=event.object_type,
        object_id=event.object_id,
        result=event.result,
        reason_code=event.reason_code,
        old_value_summary=event.old_value_summary,
        new_value_summary=event.new_value_summary,
        old_value_digest=event.old_value_digest,
        new_value_digest=event.new_value_digest,
        redacted_fields=event.redacted_fields,
        redaction_policy_version=event.redaction_policy_version,
    )


def _to_event(
    prepared: PreparedAuditEvent,
    sequence_no: int,
    previous_hash: str,
    event_hash: str,
) -> AuditEvent:
    return AuditEvent(
        sequence_no=sequence_no,
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
        previous_event_hash=previous_hash,
        event_hash=event_hash,
    )
