"""PostgreSQL-only schedule persistence with transactional audit outbox.

Iteration 36F — Execution politika ve worker dayanıklılığı.
PostgreSQLExecutionRepository ve postgresql_repository.py sablonunu izler.
"""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterable
from datetime import datetime, time, timezone
from typing import cast

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    JSON,
    MetaData,
    String,
    Table,
    select,
    update,
)
from sqlalchemy.engine import RowMapping

from veri_kalitesi.audit import PostgreSQLTransactionalAudit, PreparedAuditEvent
from veri_kalitesi.executions.scheduling import (
    Schedule,
    ScheduleType,
)
from veri_kalitesi.persistence import DEFAULT_SCHEMA_NAME, SessionFactory, transactional_session


@dataclass(frozen=True)
class ScheduleTables:
    schedules: Table


def schedule_tables(schema: str = DEFAULT_SCHEMA_NAME) -> ScheduleTables:
    metadata = MetaData(schema=schema)
    schedules = Table(
        "schedules",
        metadata,
        Column("schedule_id", String(36), primary_key=True),
        Column("name", String(200), nullable=False, unique=True),
        Column("schedule_type", String(20), nullable=False),
        Column("timezone_name", String(80), nullable=False),
        Column("rule_version_ids", JSON, nullable=False),
        Column("created_by", String(128), nullable=False),
        Column("local_time", String(10)),
        Column("once_at", DateTime(timezone=True)),
        Column("day_of_week", Integer),
        Column("day_of_month", Integer),
        Column("is_active", Integer, nullable=False),
        Column("next_run_at", DateTime(timezone=True)),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("last_triggered_at", DateTime(timezone=True)),
        schema=schema,
    )
    return ScheduleTables(schedules=schedules)


class PostgreSQLScheduleRepository:
    """PostgreSQL tabanli schedule repository.

    ScheduleRepository protocol'ünü gerçekler.
    """

    def __init__(
        self,
        session_factory: SessionFactory,
        *,
        schema: str = DEFAULT_SCHEMA_NAME,
    ) -> None:
        self._session_factory = session_factory
        self._tables = schedule_tables(schema)

    def add(
        self,
        schedule: Schedule,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: PostgreSQLTransactionalAudit,
    ) -> Schedule:
        with transactional_session(self._session_factory) as session:
            t = self._tables.schedules
            session.execute(
                t.insert().values(
                    schedule_id=schedule.schedule_id,
                    name=schedule.name,
                    schedule_type=schedule.schedule_type.value,
                    timezone_name=schedule.timezone_name,
                    rule_version_ids=list(schedule.rule_version_ids),
                    created_by=schedule.created_by,
                    local_time=schedule.local_time.isoformat() if schedule.local_time else None,
                    once_at=schedule.once_at,
                    day_of_week=schedule.day_of_week,
                    day_of_month=schedule.day_of_month,
                    is_active=1 if schedule.is_active else 0,
                    next_run_at=schedule.next_run_at,
                    created_at=schedule.created_at,
                    last_triggered_at=schedule.last_triggered_at,
                )
            )
            audit_outbox.stage(audit_event, session=session)
        return schedule

    def due(self, now: datetime) -> list[Schedule]:
        t = self._tables.schedules
        with self._session_factory() as session:
            rows = (
                session.execute(
                    select(t)
                    .where(
                        t.c.is_active == 1,
                        t.c.next_run_at.isnot(None),
                        t.c.next_run_at <= now.astimezone(timezone.utc),
                    )
                    .order_by(t.c.next_run_at, t.c.schedule_id)
                )
                .mappings()
                .all()
            )
        return [_row_to_schedule(row) for row in rows]

    def advance(
        self,
        schedule_id: str,
        *,
        triggered_at: datetime,
        next_run_at: datetime | None,
        is_active: bool,
    ) -> Schedule:
        with transactional_session(self._session_factory) as session:
            t = self._tables.schedules
            session.execute(
                update(t)
                .where(t.c.schedule_id == schedule_id)
                .values(
                    last_triggered_at=triggered_at.astimezone(timezone.utc),
                    next_run_at=next_run_at,
                    is_active=1 if is_active else 0,
                )
            )
        return self.get(schedule_id)

    def get(self, schedule_id: str) -> Schedule:
        t = self._tables.schedules
        with self._session_factory() as session:
            row = (
                session.execute(select(t).where(t.c.schedule_id == schedule_id))
                .mappings()
                .one_or_none()
            )
        if row is None:
            from veri_kalitesi.executions.errors import ExecutionValidationError

            raise ExecutionValidationError("Schedule not found.")
        return _row_to_schedule(row)

    def list_all(self) -> list[Schedule]:
        t = self._tables.schedules
        with self._session_factory() as session:
            rows = (
                session.execute(select(t).order_by(t.c.created_at, t.c.schedule_id))
                .mappings()
                .all()
            )
        return [_row_to_schedule(row) for row in rows]


def _row_to_schedule(row: RowMapping) -> Schedule:
    return Schedule(
        schedule_id=row["schedule_id"],
        name=row["name"],
        schedule_type=ScheduleType(row["schedule_type"]),
        timezone_name=row["timezone_name"],
        rule_version_ids=tuple(cast(Iterable[str], _from_json(row["rule_version_ids"]))),
        created_by=row["created_by"],
        local_time=time.fromisoformat(row["local_time"]) if row["local_time"] else None,
        once_at=row["once_at"],
        day_of_week=row["day_of_week"],
        day_of_month=row["day_of_month"],
        is_active=bool(row["is_active"]),
        next_run_at=row["next_run_at"],
        created_at=row["created_at"],
        last_triggered_at=row["last_triggered_at"],
    )


def _from_json(value: object) -> object:
    """JSON column değerini Python objesine dönüştürür.

    SQLAlchemy JSON sütunları otomatik deserialize eder (list/dict döner).
    Eski string formatıyla da uyumludur.
    """
    import json

    if isinstance(value, str):
        return json.loads(value)
    return value
