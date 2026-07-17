"""IANA saat dilimli periyodik planlama ve idempotent tetikleme."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field, replace
from datetime import date, datetime, time, timedelta, timezone
from enum import Enum
from threading import RLock
from typing import Any, Protocol
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from veri_kalitesi.audit import (
    AuditEventInput,
    AuditResult,
    PreparedAuditEvent,
    SQLiteTransactionalAudit,
)
from veri_kalitesi.executions.errors import ExecutionValidationError
from veri_kalitesi.executions.models import RuleExecution
from veri_kalitesi.executions.service import ExecutionService


class ScheduleType(str, Enum):
    ONCE = "ONCE"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"


@dataclass(frozen=True)
class Schedule:
    name: str
    schedule_type: ScheduleType
    timezone_name: str
    rule_version_ids: tuple[str, ...]
    created_by: str
    local_time: time | None = None
    once_at: datetime | None = None
    day_of_week: int | None = None
    day_of_month: int | None = None
    is_active: bool = True
    next_run_at: datetime | None = None
    schedule_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_triggered_at: datetime | None = None


class ScheduleTechnicalEventSink(Protocol):
    def notify_schedule_failure(self, schedule: Schedule, error_class: str) -> None: ...


class SQLiteScheduleRepository:
    def __init__(self, database: str = ":memory:") -> None:
        self.connection = sqlite3.connect(database, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self._lock = RLock()
        self._create_schema()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS schedules (
                schedule_id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                schedule_type TEXT NOT NULL,
                timezone_name TEXT NOT NULL,
                rule_version_ids TEXT NOT NULL,
                created_by TEXT NOT NULL,
                local_time TEXT,
                once_at TEXT,
                day_of_week INTEGER,
                day_of_month INTEGER,
                is_active INTEGER NOT NULL,
                next_run_at TEXT,
                created_at TEXT NOT NULL,
                last_triggered_at TEXT
            );
            """
        )

    def add(
        self,
        schedule: Schedule,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> Schedule:
        import json

        if audit_outbox.connection is not self.connection:
            raise ExecutionValidationError("Audit outbox must share the schedule transaction.")
        try:
            with self._lock, self.connection:
                self.connection.execute(
                    """
                    INSERT INTO schedules (
                        schedule_id, name, schedule_type, timezone_name,
                        rule_version_ids, created_by, local_time, once_at,
                        day_of_week, day_of_month, is_active, next_run_at,
                        created_at, last_triggered_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        schedule.schedule_id,
                        schedule.name,
                        schedule.schedule_type.value,
                        schedule.timezone_name,
                        json.dumps(schedule.rule_version_ids),
                        schedule.created_by,
                        schedule.local_time.isoformat() if schedule.local_time else None,
                        _datetime_text(schedule.once_at),
                        schedule.day_of_week,
                        schedule.day_of_month,
                        1 if schedule.is_active else 0,
                        _datetime_text(schedule.next_run_at),
                        schedule.created_at.isoformat(),
                        _datetime_text(schedule.last_triggered_at),
                    ),
                )
                audit_outbox.stage(audit_event)
        except sqlite3.IntegrityError as exc:
            raise ExecutionValidationError("Schedule name must be unique.") from exc
        return schedule

    def due(self, now: datetime) -> list[Schedule]:
        with self._lock:
            rows = self.connection.execute(
                """
                SELECT * FROM schedules
                WHERE is_active = 1 AND next_run_at IS NOT NULL AND next_run_at <= ?
                ORDER BY next_run_at, schedule_id
                """,
                (now.astimezone(timezone.utc).isoformat(),),
            ).fetchall()
        return [_row_to_schedule(row) for row in rows]

    def advance(
        self,
        schedule_id: str,
        *,
        triggered_at: datetime,
        next_run_at: datetime | None,
        is_active: bool,
    ) -> Schedule:
        with self._lock, self.connection:
            self.connection.execute(
                """
                UPDATE schedules
                SET last_triggered_at = ?, next_run_at = ?, is_active = ?
                WHERE schedule_id = ?
                """,
                (
                    triggered_at.astimezone(timezone.utc).isoformat(),
                    _datetime_text(next_run_at),
                    1 if is_active else 0,
                    schedule_id,
                ),
            )
        return self.get(schedule_id)

    def get(self, schedule_id: str) -> Schedule:
        with self._lock:
            row = self.connection.execute(
                "SELECT * FROM schedules WHERE schedule_id = ?", (schedule_id,)
            ).fetchone()
        if row is None:
            raise ExecutionValidationError("Schedule not found.")
        return _row_to_schedule(row)

    def list_all(self) -> list[Schedule]:
        with self._lock:
            rows = self.connection.execute(
                "SELECT * FROM schedules ORDER BY created_at, schedule_id"
            ).fetchall()
        return [_row_to_schedule(row) for row in rows]


class SchedulingService:
    def __init__(
        self,
        repository: SQLiteScheduleRepository,
        execution_service: ExecutionService,
        *,
        transactional_audit: SQLiteTransactionalAudit,
        technical_event_sink: ScheduleTechnicalEventSink | None = None,
        clock: Any = lambda: datetime.now(timezone.utc),
    ) -> None:
        self.repository = repository
        self.execution_service = execution_service
        self.transactional_audit = transactional_audit
        self.technical_event_sink = technical_event_sink
        self.clock = clock

    def create_schedule(
        self,
        *,
        actor_id: str,
        name: str,
        schedule_type: str,
        timezone_name: str,
        rule_version_ids: tuple[str, ...],
        local_time: str | None = None,
        once_at: datetime | None = None,
        day_of_week: int | None = None,
        day_of_month: int | None = None,
        correlation_id: str | None = None,
    ) -> tuple[Schedule, tuple[datetime, ...]]:
        correlation_id = _resolve_correlation_id(correlation_id)
        if not actor_id.strip() or not name.strip() or len(name.strip()) > 200:
            raise ExecutionValidationError("Schedule actor and name are required.")
        try:
            parsed_type = ScheduleType(schedule_type.upper())
        except (AttributeError, ValueError) as exc:
            raise ExecutionValidationError("Schedule type is invalid.") from exc
        zone = _zone(timezone_name)
        parsed_time = _parse_time(local_time) if local_time is not None else None
        _validate_definition(parsed_type, parsed_time, once_at, day_of_week, day_of_month)
        self.execution_service.validate_rule_versions(rule_version_ids)
        now = self.clock().astimezone(timezone.utc)
        schedule = Schedule(
            name=name.strip(),
            schedule_type=parsed_type,
            timezone_name=zone.key,
            rule_version_ids=rule_version_ids,
            created_by=actor_id,
            local_time=parsed_time,
            once_at=once_at.astimezone(timezone.utc) if once_at else None,
            day_of_week=day_of_week,
            day_of_month=day_of_month,
            created_at=now,
        )
        preview = preview_runs(schedule, after=now, count=5)
        if not preview:
            raise ExecutionValidationError("Schedule must have a future trigger.")
        schedule = replace(schedule, next_run_at=preview[0])
        event = AuditEventInput(
            actor_id=actor_id,
            actor_type="USER",
            correlation_id=correlation_id,
            action="SCHEDULE_CREATED",
            object_type="Schedule",
            object_id=schedule.schedule_id,
            result=AuditResult.SUCCESS,
            reason_code="SCHEDULE_CREATED",
            old_values={},
            new_values={
                "schedule_type": schedule.schedule_type.value,
                "timezone": schedule.timezone_name,
                "rule_version_count": len(schedule.rule_version_ids),
                "next_run_count": len(preview),
                "next_run_at": preview[0].isoformat(),
            },
            occurred_at=now,
        )
        self.repository.add(
            schedule,
            audit_event=self.transactional_audit.prepare(event),
            audit_outbox=self.transactional_audit,
        )
        self.transactional_audit.publish_pending()
        return schedule, preview

    def trigger_due(self, *, now: datetime | None = None) -> tuple[RuleExecution, ...]:
        current = (now or self.clock()).astimezone(timezone.utc)
        executions: list[RuleExecution] = []
        for schedule in self.repository.due(current):
            scheduled_for = schedule.next_run_at
            if scheduled_for is None:
                continue
            try:
                execution = self.execution_service.start_scheduled(
                    idempotency_key=f"schedule:{schedule.schedule_id}:{scheduled_for.isoformat()}",
                    rule_version_ids=schedule.rule_version_ids,
                    scope={
                        "schedule_id": schedule.schedule_id,
                        "scheduled_for": scheduled_for.isoformat(),
                    },
                    correlation_id=f"schedule-{schedule.schedule_id}-{int(scheduled_for.timestamp())}",
                )
            except ExecutionValidationError:
                self.repository.advance(
                    schedule.schedule_id,
                    triggered_at=current,
                    next_run_at=None,
                    is_active=False,
                )
                if self.technical_event_sink is not None:
                    self.technical_event_sink.notify_schedule_failure(
                        schedule, "INVALID_EXECUTION_SCOPE"
                    )
                continue
            executions.append(execution)
            following = preview_runs(schedule, after=scheduled_for, count=1)
            self.repository.advance(
                schedule.schedule_id,
                triggered_at=current,
                next_run_at=following[0] if following else None,
                is_active=bool(following),
            )
        return tuple(executions)


def preview_runs(schedule: Schedule, *, after: datetime, count: int) -> tuple[datetime, ...]:
    if count < 1:
        raise ExecutionValidationError("Preview count must be positive.")
    after_utc = after.astimezone(timezone.utc)
    if schedule.schedule_type is ScheduleType.ONCE:
        if schedule.once_at is not None and schedule.once_at > after_utc:
            return (schedule.once_at.astimezone(timezone.utc),)
        return ()

    zone = _zone(schedule.timezone_name)
    local_after = after_utc.astimezone(zone)
    candidate_date = local_after.date()
    results: list[datetime] = []
    max_days = 366 * 10
    for offset in range(max_days):
        day = candidate_date + timedelta(days=offset)
        if not _date_matches(schedule, day):
            continue
        candidate = _valid_local_datetime(day, schedule.local_time, zone)
        if candidate is None:
            continue
        candidate_utc = candidate.astimezone(timezone.utc)
        if candidate_utc <= after_utc:
            continue
        results.append(candidate_utc)
        if len(results) == count:
            return tuple(results)
    raise ExecutionValidationError("Schedule preview exceeded supported search horizon.")


def _date_matches(schedule: Schedule, value: date) -> bool:
    if schedule.schedule_type is ScheduleType.DAILY:
        return True
    if schedule.schedule_type is ScheduleType.WEEKLY:
        return value.weekday() == schedule.day_of_week
    if schedule.schedule_type is ScheduleType.MONTHLY:
        return value.day == schedule.day_of_month
    return False


def _valid_local_datetime(value: date, local_time: time | None, zone: ZoneInfo) -> datetime | None:
    if local_time is None:
        return None
    naive = datetime.combine(value, local_time)
    candidate = naive.replace(tzinfo=zone, fold=0)
    round_trip = candidate.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None)
    return candidate if round_trip == naive else None


def _validate_definition(
    schedule_type: ScheduleType,
    local_time: time | None,
    once_at: datetime | None,
    day_of_week: int | None,
    day_of_month: int | None,
) -> None:
    if schedule_type is ScheduleType.ONCE:
        if once_at is None or once_at.tzinfo is None:
            raise ExecutionValidationError("ONCE schedule requires an aware once_at value.")
        return
    if local_time is None:
        raise ExecutionValidationError("Periodic schedule requires local_time.")
    if schedule_type is ScheduleType.WEEKLY and (
        isinstance(day_of_week, bool)
        or not isinstance(day_of_week, int)
        or not 0 <= day_of_week <= 6
    ):
        raise ExecutionValidationError("WEEKLY schedule requires day_of_week between 0 and 6.")
    if schedule_type is ScheduleType.MONTHLY and (
        isinstance(day_of_month, bool)
        or not isinstance(day_of_month, int)
        or not 1 <= day_of_month <= 31
    ):
        raise ExecutionValidationError("MONTHLY schedule requires day_of_month between 1 and 31.")


def _zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (TypeError, ZoneInfoNotFoundError) as exc:
        raise ExecutionValidationError("Schedule timezone must be a valid IANA timezone.") from exc


def _resolve_correlation_id(correlation_id: str | None) -> str:
    if correlation_id is None:
        return str(uuid4())
    if not correlation_id.strip():
        raise ExecutionValidationError("correlation_id cannot be blank.")
    return correlation_id


def _parse_time(value: str) -> time:
    try:
        parsed = time.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ExecutionValidationError("Schedule local_time must use HH:MM[:SS].") from exc
    if parsed.tzinfo is not None:
        raise ExecutionValidationError("Schedule local_time must not include an offset.")
    return parsed


def _row_to_schedule(row: sqlite3.Row) -> Schedule:
    import json

    return Schedule(
        schedule_id=row["schedule_id"],
        name=row["name"],
        schedule_type=ScheduleType(row["schedule_type"]),
        timezone_name=row["timezone_name"],
        rule_version_ids=tuple(json.loads(row["rule_version_ids"])),
        created_by=row["created_by"],
        local_time=time.fromisoformat(row["local_time"]) if row["local_time"] else None,
        once_at=_datetime_value(row["once_at"]),
        day_of_week=row["day_of_week"],
        day_of_month=row["day_of_month"],
        is_active=bool(row["is_active"]),
        next_run_at=_datetime_value(row["next_run_at"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        last_triggered_at=_datetime_value(row["last_triggered_at"]),
    )


def _datetime_text(value: datetime | None) -> str | None:
    return value.astimezone(timezone.utc).isoformat() if value else None


def _datetime_value(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None
