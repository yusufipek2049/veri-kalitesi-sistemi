"""SQLite skor gecmisi icin salt okunur rapor onizleme reader'i
ve PostgreSQL rapor repository'si."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from threading import RLock
from uuid import uuid4

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    JSON,
    MetaData,
    String,
    Table,
    and_,
    delete,
    func,
    insert,
    select,
    update,
)
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from veri_kalitesi.persistence import DEFAULT_SCHEMA_NAME, SessionFactory, transactional_session
from veri_kalitesi.reporting.errors import (
    ReportNotFoundError,
    ReportValidationError,
)
from veri_kalitesi.reporting.models import (
    Report,
    ReportExportPolicy,
    ReportFormat,
    ReportRequest,
    ReportScoreObservation,
    ReportStatus,
    ReportType,
)
from veri_kalitesi.reporting.policies import ReportExportPolicyRepository
from veri_kalitesi.reporting.scheduling import ReportSchedule, ReportScheduleRepository
from veri_kalitesi.executions.scheduling import ScheduleType
from veri_kalitesi.scoring.models import (
    QualityScore,
    ScoreLevel,
    ScoreScopeType,
    ScoreStatus,
    is_official_observation,
)


@dataclass(frozen=True)
class ReportTables:
    reports: Table


def report_tables(schema: str = DEFAULT_SCHEMA_NAME) -> ReportTables:
    metadata = MetaData(schema=schema)
    reports = Table(
        "reports",
        metadata,
        Column("report_id", String(36), primary_key=True),
        Column("report_type", String(30), nullable=False),
        Column("format", String(10), nullable=False),
        Column("requested_by", String(128), nullable=False),
        Column("parameters", JSON, nullable=False),
        Column("status", String(20), nullable=False),
        Column("sensitivity_level", String(100)),
        Column("retention_policy_id", String(36)),
        Column("online_file_reference", String(500)),
        Column("file_size", Integer()),
        Column("expires_at", DateTime(timezone=True)),
        Column("failure_reason", String(500)),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("completed_at", DateTime(timezone=True)),
        Column("version", Integer, nullable=False),
        schema=schema,
    )
    return ReportTables(reports=reports)


class PostgreSQLReportRepository:
    """PostgreSQL destekli rapor repository'si.

    Mevcut execution/rules PostgreSQL repository pattern'ini izler:
    SQLAlchemy core, transactional_session, RowMapping donusumu.
    """

    def __init__(
        self,
        session_factory: SessionFactory,
        schema: str = DEFAULT_SCHEMA_NAME,
    ) -> None:
        self._session_factory = session_factory
        self._tables = report_tables(schema)

    def create_report(
        self,
        request: ReportRequest,
        requested_by: str,
        *,
        session: Session | None = None,
    ) -> Report:
        now = datetime.now(timezone.utc)
        report_id = str(uuid4())
        row = {
            "report_id": report_id,
            "report_type": request.report_type.value,
            "format": request.format.value,
            "requested_by": requested_by,
            "parameters": request.parameters,
            "status": ReportStatus.QUEUED.value,
            "sensitivity_level": request.sensitivity_level,
            "created_at": now,
            "version": 1,
        }

        def _do_insert(s: Session) -> Report:
            try:
                s.execute(insert(self._tables.reports).values(row))
            except IntegrityError as exc:
                raise ReportValidationError(f"Duplicate report id: {report_id}") from exc
            return Report(
                report_id=report_id,
                report_type=request.report_type,
                format=request.format,
                requested_by=requested_by,
                parameters=request.parameters,
                status=ReportStatus.QUEUED,
                sensitivity_level=request.sensitivity_level,
                created_at=now,
                version=1,
            )

        if session is not None:
            return _do_insert(session)
        with transactional_session(self._session_factory) as s:
            return _do_insert(s)

    def get_report(
        self,
        report_id: str,
        *,
        session: Session | None = None,
    ) -> Report:
        def _do_get(s: Session) -> Report:
            row = s.execute(
                select(self._tables.reports).where(
                    self._tables.reports.c.report_id == report_id
                )
            ).one_or_none()
            if row is None:
                raise ReportNotFoundError(report_id)
            return _row_to_report(row._mapping)

        if session is not None:
            return _do_get(session)
        with transactional_session(self._session_factory) as s:
            return _do_get(s)

    def list_reports_by_user(
        self,
        requested_by: str,
        *,
        limit: int = 50,
        offset: int = 0,
        session: Session | None = None,
    ) -> tuple[Report, ...]:
        def _do_list(s: Session) -> tuple[Report, ...]:
            rows = s.execute(
                select(self._tables.reports)
                .where(self._tables.reports.c.requested_by == requested_by)
                .order_by(self._tables.reports.c.created_at.desc())
                .limit(limit)
                .offset(offset)
            ).all()
            return tuple(_row_to_report(row._mapping) for row in rows)

        if session is not None:
            return _do_list(session)
        with transactional_session(self._session_factory) as s:
            return _do_list(s)

    def update_report_status(
        self,
        report_id: str,
        status: ReportStatus,
        *,
        online_file_reference: str | None = None,
        file_size: int | None = None,
        failure_reason: str | None = None,
        expires_at: datetime | None = None,
        session: Session | None = None,
    ) -> Report:
        now = datetime.now(timezone.utc)

        def _do_update(s: Session) -> Report:
            current = s.execute(
                select(self._tables.reports).where(
                    self._tables.reports.c.report_id == report_id
                )
            ).one_or_none()
            if current is None:
                raise ReportNotFoundError(report_id)

            current_version = current._mapping["version"]
            values: dict[str, object] = {
                "status": status.value,
                "version": current_version + 1,
            }
            if status in (ReportStatus.READY, ReportStatus.FAILED):
                values["completed_at"] = now
            if online_file_reference is not None:
                values["online_file_reference"] = online_file_reference
            if file_size is not None:
                values["file_size"] = file_size
            if failure_reason is not None:
                values["failure_reason"] = failure_reason
            if expires_at is not None:
                values["expires_at"] = expires_at

            result = s.execute(
                update(self._tables.reports)
                .where(
                    and_(
                        self._tables.reports.c.report_id == report_id,
                        self._tables.reports.c.version == current_version,
                    )
                )
                .values(values)
            )
            if result.rowcount == 0:
                raise ReportValidationError(
                    f"Optimistic lock conflict on report {report_id}"
                )

            # Re-read to get full state
            updated = s.execute(
                select(self._tables.reports).where(
                    self._tables.reports.c.report_id == report_id
                )
            ).one()
            return _row_to_report(updated._mapping)

        if session is not None:
            return _do_update(session)
        with transactional_session(self._session_factory) as s:
            return _do_update(s)

    def delete_report(
        self,
        report_id: str,
        *,
        session: Session | None = None,
    ) -> None:
        def _do_delete(s: Session) -> None:
            result = s.execute(
                delete(self._tables.reports).where(
                    self._tables.reports.c.report_id == report_id
                )
            )
            if result.rowcount == 0:
                raise ReportNotFoundError(report_id)

        if session is not None:
            return _do_delete(session)
        with transactional_session(self._session_factory) as s:
            return _do_delete(s)


def _row_to_report(row: RowMapping) -> Report:
    return Report(
        report_id=row["report_id"],
        report_type=ReportType(row["report_type"]),
        format=ReportFormat(row["format"]),
        requested_by=row["requested_by"],
        parameters=row["parameters"] or {},
        status=ReportStatus(row["status"]),
        sensitivity_level=row.get("sensitivity_level"),
        retention_policy_id=row.get("retention_policy_id"),
        online_file_reference=row.get("online_file_reference"),
        file_size=row.get("file_size"),
        expires_at=row.get("expires_at"),
        created_at=row.get("created_at"),
        completed_at=row.get("completed_at"),
        failure_reason=row.get("failure_reason"),
        version=row["version"],
    )


class SQLiteReportPreviewReader:
    """SQLite skor gecmisi icin salt okunur rapor onizleme reader'i."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.row_factory = sqlite3.Row
        self._lock = RLock()

    def latest_source_scores(
        self,
        start_at: datetime,
        end_at: datetime,
        allowed_source_ids: frozenset[str],
    ) -> tuple[ReportScoreObservation, ...]:
        if not allowed_source_ids:
            return ()
        placeholders = ", ".join("?" for _ in allowed_source_ids)
        parameters: list[object] = [
            ScoreScopeType.SOURCE.value,
            start_at.isoformat(),
            end_at.isoformat(),
            *sorted(allowed_source_ids),
        ]
        statement = f"""
            SELECT quality_score_id, execution_id, rule_version_id, rule_result_id,
                scope_id, score_value, score_status, level, calculation_details,
                calculated_at
            FROM quality_scores
            WHERE scope_type = ?
              AND julianday(calculated_at) >= julianday(?)
              AND julianday(calculated_at) <= julianday(?)
              AND scope_id IN ({placeholders})
            ORDER BY scope_id, julianday(calculated_at) DESC, quality_score_id DESC
        """
        with self._lock:
            rows = self.connection.execute(statement, parameters).fetchall()
        latest: dict[str, ReportScoreObservation] = {}
        for row in rows:
            source_id = row["scope_id"]
            if source_id not in latest and is_official_observation(_row_to_score(row)):
                latest[source_id] = _row_to_observation(row)
        return tuple(latest[source_id] for source_id in sorted(latest))


def _row_to_score(row: sqlite3.Row) -> QualityScore:
    return QualityScore(
        quality_score_id=row["quality_score_id"],
        execution_id=row["execution_id"],
        rule_version_id=row["rule_version_id"],
        rule_result_id=row["rule_result_id"],
        scope_type=ScoreScopeType.SOURCE,
        scope_id=row["scope_id"],
        score_value=Decimal(row["score_value"]) if row["score_value"] is not None else None,
        score_status=ScoreStatus(row["score_status"]),
        level=ScoreLevel(row["level"]) if row["level"] is not None else None,
        calculation_details=json.loads(row["calculation_details"]),
        calculated_at=datetime.fromisoformat(row["calculated_at"]),
    )


def _row_to_observation(row: sqlite3.Row) -> ReportScoreObservation:
    return ReportScoreObservation(
        source_id=row["scope_id"],
        score_value=Decimal(row["score_value"]) if row["score_value"] is not None else None,
        score_status=ScoreStatus(row["score_status"]),
        level=ScoreLevel(row["level"]) if row["level"] is not None else None,
        calculated_at=datetime.fromisoformat(row["calculated_at"]),
    )


@dataclass(frozen=True)
class ReportScheduleTables:
    report_schedules: Table


def report_schedule_tables(schema: str = DEFAULT_SCHEMA_NAME) -> ReportScheduleTables:
    metadata = MetaData(schema=schema)
    rs = Table(
        "report_schedules",
        metadata,
        Column("schedule_id", String(36), primary_key=True),
        Column("name", String(200), nullable=False, unique=True),
        Column("report_type", String(30), nullable=False),
        Column("format", String(10), nullable=False),
        Column("parameters", JSON, nullable=False),
        Column("sensitivity_level", String(100)),
        Column("recipients", JSON, nullable=False),
        Column("schedule_type", String(20), nullable=False),
        Column("timezone_name", String(80), nullable=False),
        Column("local_time", String(10)),
        Column("once_at", DateTime(timezone=True)),
        Column("day_of_week", Integer),
        Column("day_of_month", Integer),
        Column("is_active", Integer, nullable=False),
        Column("next_run_at", DateTime(timezone=True)),
        Column("created_by", String(128), nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("last_triggered_at", DateTime(timezone=True)),
        schema=schema,
    )
    return ReportScheduleTables(report_schedules=rs)


class PostgreSQLReportScheduleRepository:
    """PostgreSQL tabanli rapor schedule repository'si."""

    def __init__(
        self,
        session_factory: SessionFactory,
        schema: str = DEFAULT_SCHEMA_NAME,
    ) -> None:
        self._session_factory = session_factory
        self._tables = report_schedule_tables(schema)

    def add(self, schedule: ReportSchedule) -> ReportSchedule:
        with transactional_session(self._session_factory) as session:
            t = self._tables.report_schedules
            session.execute(
                t.insert().values(
                    schedule_id=schedule.schedule_id,
                    name=schedule.name,
                    report_type=schedule.report_type.value,
                    format=schedule.format.value,
                    parameters=schedule.parameters,
                    sensitivity_level=schedule.sensitivity_level,
                    recipients=list(schedule.recipients),
                    schedule_type=schedule.schedule_type.value,
                    timezone_name=schedule.timezone_name,
                    local_time=schedule.local_time.isoformat() if schedule.local_time else None,
                    once_at=schedule.once_at,
                    day_of_week=schedule.day_of_week,
                    day_of_month=schedule.day_of_month,
                    is_active=1 if schedule.is_active else 0,
                    next_run_at=schedule.next_run_at,
                    created_by=schedule.created_by,
                    created_at=schedule.created_at,
                    last_triggered_at=schedule.last_triggered_at,
                )
            )
        return schedule

    def list_all(self) -> tuple[ReportSchedule, ...]:
        t = self._tables.report_schedules
        with self._session_factory() as session:
            rows = (
                session.execute(
                    select(t).order_by(t.c.created_at, t.c.schedule_id)
                )
                .mappings()
                .all()
            )
        return tuple(_row_to_report_schedule(row) for row in rows)

    def get(self, schedule_id: str) -> ReportSchedule:
        t = self._tables.report_schedules
        with self._session_factory() as session:
            row = (
                session.execute(
                    select(t).where(t.c.schedule_id == schedule_id)
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            from veri_kalitesi.reporting.errors import ReportNotFoundError
            raise ReportNotFoundError(schedule_id)
        return _row_to_report_schedule(row)

    def delete(self, schedule_id: str) -> None:
        from sqlalchemy import delete as sa_delete

        t = self._tables.report_schedules
        with transactional_session(self._session_factory) as session:
            result = session.execute(
                sa_delete(t).where(t.c.schedule_id == schedule_id)
            )
            if result.rowcount == 0:
                from veri_kalitesi.reporting.errors import ReportNotFoundError
                raise ReportNotFoundError(schedule_id)

    def due(self, now: datetime) -> tuple[ReportSchedule, ...]:
        t = self._tables.report_schedules
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
        return tuple(_row_to_report_schedule(row) for row in rows)

    def advance(
        self,
        schedule_id: str,
        *,
        triggered_at: datetime,
        next_run_at: datetime | None,
        is_active: bool,
    ) -> ReportSchedule:
        from sqlalchemy import update as sa_update

        t = self._tables.report_schedules
        with transactional_session(self._session_factory) as session:
            session.execute(
                sa_update(t)
                .where(t.c.schedule_id == schedule_id)
                .values(
                    last_triggered_at=triggered_at.astimezone(timezone.utc),
                    next_run_at=next_run_at,
                    is_active=1 if is_active else 0,
                )
            )
        return self.get(schedule_id)


def _row_to_report_schedule(row: RowMapping) -> ReportSchedule:
    from datetime import time as dt_time

    recipients = row["recipients"]
    if isinstance(recipients, str):
        import json
        recipients = json.loads(recipients)

    return ReportSchedule(
        schedule_id=row["schedule_id"],
        name=row["name"],
        report_type=ReportType(row["report_type"]),
        format=ReportFormat(row["format"]),
        parameters=row["parameters"] or {},
        sensitivity_level=row.get("sensitivity_level"),
        recipients=tuple(recipients),
        schedule_type=ScheduleType(row["schedule_type"]),
        timezone_name=row["timezone_name"],
        local_time=dt_time.fromisoformat(row["local_time"]) if row.get("local_time") else None,
        once_at=row.get("once_at"),
        day_of_week=row.get("day_of_week"),
        day_of_month=row.get("day_of_month"),
        is_active=bool(row["is_active"]),
        next_run_at=row.get("next_run_at"),
        created_by=row["created_by"],
        created_at=row["created_at"],
        last_triggered_at=row.get("last_triggered_at"),
    )
