"""Zamanlanmis rapor uretimi (FR-076).

Mevcut executions.scheduling modulundeki ScheduleType ve preview_runs
fonksiyonlarini yeniden kullanir. Ayri bir report_schedules tablosu
ile calisir.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from datetime import datetime, time, timezone
from typing import Callable, Protocol
from uuid import uuid4
from zoneinfo import ZoneInfo

from veri_kalitesi.executions.scheduling import (
    Schedule as ExecSchedule,
    ScheduleType,
    preview_runs,
)
from veri_kalitesi.reporting.models import Report, ReportFormat, ReportRequest, ReportType
from veri_kalitesi.reporting.errors import ReportingError
from veri_kalitesi.executions.scheduling import ScheduleTechnicalEventSink
from veri_kalitesi.identity import ActorContext, create_service_actor_context


@dataclass(frozen=True)
class ReportSchedule:
    """Zamanlanmis rapor tanimi."""

    schedule_id: str
    name: str
    report_type: ReportType
    format: ReportFormat
    parameters: dict
    sensitivity_level: str | None
    recipients: tuple[str, ...]
    schedule_type: ScheduleType
    timezone_name: str
    local_time: time | None = None
    once_at: datetime | None = None
    day_of_week: int | None = None
    day_of_month: int | None = None
    is_active: bool = True
    next_run_at: datetime | None = None
    created_by: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_triggered_at: datetime | None = None


@dataclass(frozen=True)
class ReportScheduleCreateRequest:
    name: str
    report_type: ReportType
    format: ReportFormat
    parameters: dict
    sensitivity_level: str | None
    recipients: tuple[str, ...]
    schedule_type: str
    timezone_name: str
    local_time: str | None = None
    once_at: datetime | None = None
    day_of_week: int | None = None
    day_of_month: int | None = None


class ReportScheduleRepository(Protocol):
    def add(self, schedule: ReportSchedule) -> ReportSchedule: ...
    def list_all(self) -> tuple[ReportSchedule, ...]: ...
    def get(self, schedule_id: str) -> ReportSchedule: ...
    def delete(self, schedule_id: str) -> None: ...
    def due(self, now: datetime) -> tuple[ReportSchedule, ...]: ...
    def claim_due(
        self,
        schedule_id: str,
        *,
        scheduled_for: datetime,
        triggered_at: datetime,
        next_run_at: datetime | None,
        is_active: bool,
    ) -> bool: ...
    def advance(
        self,
        schedule_id: str,
        *,
        triggered_at: datetime,
        next_run_at: datetime | None,
        is_active: bool,
    ) -> ReportSchedule: ...


class ScheduledReportRequester(Protocol):
    def request_report(
        self,
        request: ReportRequest,
        actor_context: ActorContext | None,
    ) -> Report: ...


class ReportScheduleService:
    """Zamanlanmis rapor servisi.

    FR-076: Raporlari zamanlanmis olarak uretir ve bildirim gonderir.
    Mevcut ReportService ve notification altyapisini kullanir.
    """

    def __init__(
        self,
        repository: ReportScheduleRepository,
        report_service: ScheduledReportRequester,
        *,
        technical_event_sink: ScheduleTechnicalEventSink | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self._repo = repository
        self._report_service = report_service
        self._technical_event_sink = technical_event_sink
        self._clock = clock

    def create_schedule(
        self,
        request: ReportScheduleCreateRequest,
        created_by: str,
    ) -> tuple[ReportSchedule, tuple[datetime, ...]]:
        """Zamanlanmis rapor kaydi olusturur."""
        if not request.name.strip():
            raise ReportingError("Schedule name is required.")
        if not created_by.strip():
            raise ReportingError("Created by is required.")

        parsed_type = ScheduleType(request.schedule_type.upper())
        zone = _zone(request.timezone_name)
        parsed_time = _parse_time(request.local_time) if request.local_time is not None else None

        _validate_definition(
            parsed_type, parsed_time, request.once_at, request.day_of_week, request.day_of_month
        )

        now = self._clock().astimezone(timezone.utc)

        schedule = ReportSchedule(
            schedule_id=str(uuid4()),
            name=request.name.strip(),
            report_type=request.report_type,
            format=request.format,
            parameters=request.parameters,
            sensitivity_level=request.sensitivity_level,
            recipients=request.recipients,
            schedule_type=parsed_type,
            timezone_name=zone.key,
            local_time=parsed_time,
            once_at=request.once_at.astimezone(timezone.utc) if request.once_at else None,
            day_of_week=request.day_of_week,
            day_of_month=request.day_of_month,
            created_by=created_by,
            created_at=now,
        )

        preview = preview_runs(
            _to_schedule_backend(schedule),
            after=now,
            count=5,
        )
        if not preview:
            raise ReportingError("Schedule must have a future trigger.")

        schedule = _replace(schedule, next_run_at=preview[0])
        stored = self._repo.add(schedule)
        return stored, preview

    def list_schedules(
        self,
    ) -> tuple[ReportSchedule, ...]:
        """Tum zamanlanmis raporlari listeler."""
        return self._repo.list_all()

    def delete_schedule(self, schedule_id: str) -> None:
        """Zamanlanmis raporu siler."""
        self._repo.get(schedule_id)  # raises if not found
        self._repo.delete(schedule_id)

    def trigger_due(
        self,
        *,
        now: datetime | None = None,
        actor_id: str = "scheduler",
    ) -> tuple[str, ...]:
        """Vadesi gelen raporlari tetikler ve rapor uretir.

        Her vadesi gelen schedule icin:
        1. ReportService.request_report ile rapor talebi olusturulur
        2. Schedule bir sonraki calisma zamanina ilerletilir
        3. Uretilen rapor id'leri donulur

        Returns: Uretilen rapor id'leri.
        """
        current = (now or self._clock()).astimezone(timezone.utc)
        triggered: list[str] = []

        for schedule in self._repo.due(current):
            scheduled_for = schedule.next_run_at
            if scheduled_for is None:
                continue

            following = preview_runs(
                _to_schedule_backend(schedule),
                after=scheduled_for,
                count=1,
            )
            claim_due = getattr(self._repo, "claim_due", None)
            if claim_due is None:
                self._repo.advance(
                    schedule.schedule_id,
                    triggered_at=current,
                    next_run_at=following[0] if following else None,
                    is_active=bool(following),
                )
                claimed = True
            else:
                claimed = claim_due(
                    schedule.schedule_id,
                    scheduled_for=scheduled_for,
                    triggered_at=current,
                    next_run_at=following[0] if following else None,
                    is_active=bool(following),
                )
            if not claimed:
                continue

            try:
                report_request = ReportRequest(
                    report_type=schedule.report_type,
                    format=schedule.format,
                    parameters=schedule.parameters,
                    reason_code="SCHEDULED_REPORT",
                    sensitivity_level=schedule.sensitivity_level,
                )
                report = self._report_service.request_report(
                    report_request,
                    create_service_actor_context(
                        actor_id=actor_id,
                        correlation_id=(
                            f"report-schedule-{schedule.schedule_id}-"
                            f"{int(scheduled_for.timestamp())}"
                        ),
                        roles=frozenset({"REPORT_SCHEDULER"}),
                    ),
                )
                triggered.append(report.report_id)
            except Exception as exc:
                # Hata durumunda schedule pasiflestirilir
                self._repo.advance(
                    schedule.schedule_id,
                    triggered_at=current,
                    next_run_at=None,
                    is_active=False,
                )
                if self._technical_event_sink is not None:
                    try:
                        self._technical_event_sink.notify_schedule_failure(
                            _to_schedule_backend(schedule), type(exc).__name__
                        )
                    except Exception:
                        pass
                continue

        return tuple(triggered)


def _to_schedule_backend(schedule: ReportSchedule) -> ExecSchedule:
    """ReportSchedule'i executions.scheduling.Schedule benzeri bir
    nesneye donusturur (preview_runs fonksiyonunun kullanabilmesi icin).

    preview_runs su alanlara bakar: schedule_type, once_at, local_time,
    day_of_week, day_of_month, timezone_name.
    """
    return ExecSchedule(
        name=schedule.name,
        schedule_type=schedule.schedule_type,
        timezone_name=schedule.timezone_name,
        rule_version_ids=(),
        created_by=schedule.created_by,
        local_time=schedule.local_time,
        once_at=schedule.once_at,
        day_of_week=schedule.day_of_week,
        day_of_month=schedule.day_of_month,
        is_active=schedule.is_active,
        next_run_at=schedule.next_run_at,
        schedule_id=schedule.schedule_id,
        created_at=schedule.created_at,
        last_triggered_at=schedule.last_triggered_at,
    )


def _replace(schedule: ReportSchedule, **kwargs: object) -> ReportSchedule:
    """Frozen dataclass field guncelleme yardimcisi."""
    values = {f.name: kwargs.get(f.name, getattr(schedule, f.name)) for f in fields(ReportSchedule)}
    return ReportSchedule(**values)  # type: ignore[arg-type]


def _validate_definition(
    schedule_type: ScheduleType,
    local_time: time | None,
    once_at: datetime | None,
    day_of_week: int | None,
    day_of_month: int | None,
) -> None:
    if schedule_type is ScheduleType.ONCE:
        if once_at is None or once_at.tzinfo is None:
            raise ReportingError("ONCE schedule requires an aware once_at value.")
        return
    if local_time is None:
        raise ReportingError("Periodic schedule requires local_time.")
    if schedule_type is ScheduleType.WEEKLY and (
        isinstance(day_of_week, bool)
        or not isinstance(day_of_week, int)
        or not 0 <= day_of_week <= 6
    ):
        raise ReportingError("WEEKLY schedule requires day_of_week between 0 and 6.")
    if schedule_type is ScheduleType.MONTHLY and (
        isinstance(day_of_month, bool)
        or not isinstance(day_of_month, int)
        or not 1 <= day_of_month <= 31
    ):
        raise ReportingError("MONTHLY schedule requires day_of_month between 1 and 31.")


def _zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (TypeError, ZoneInfoNotFoundError) as exc:
        raise ReportingError("Schedule timezone must be a valid IANA timezone.") from exc


def _parse_time(value: str) -> time:
    try:
        parsed = time.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ReportingError("Schedule local_time must use HH:MM[:SS].") from exc
    if parsed.tzinfo is not None:
        raise ReportingError("Schedule local_time must not include an offset.")
    return parsed


try:
    from zoneinfo import ZoneInfoNotFoundError  # type: ignore[attr-defined]
except ImportError:

    class ZoneInfoNotFoundError(Exception):  # type: ignore[no-redef]
        pass
