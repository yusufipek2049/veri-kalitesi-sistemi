"""Raporlama domain birim testleri — 36G guvenli rapor uretimi/indirme."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from veri_kalitesi.reporting.errors import (
    ReportExportDeniedError,
    ReportNotFoundError,
)
from veri_kalitesi.reporting.export import GeneratedFile, generate_report
from veri_kalitesi.reporting.models import (
    Report,
    ReportExportPolicy,
    ReportFormat,
    ReportRequest,
    ReportStatus,
    ReportType,
)
from veri_kalitesi.reporting.policies import (
    check_download_access,
    evaluate_export,
)
from veri_kalitesi.reporting.scheduling import (
    ReportSchedule,
    ReportScheduleCreateRequest,
    ReportScheduleService,
    ReportingError,
)
from veri_kalitesi.executions.scheduling import ScheduleType


def _make_policy(**overrides: object) -> ReportExportPolicy:
    defaults = {
        "version": "POLICY_V1",
        "policy_name": "test",
        "sensitivity_level": None,
        "max_file_size": 1024 * 1024,
        "online_duration_seconds": 3600,
        "require_justification": False,
        "require_maker_checker": False,
        "watermark_enabled": True,
        "dlp_enabled": False,
        "allowed_formats": frozenset({ReportFormat.CSV}),
    }
    merged = {**defaults, **overrides}
    return ReportExportPolicy(**merged)  # type: ignore[arg-type]


class TestReportModels:
    def test_report_status_values(self) -> None:
        assert ReportStatus.QUEUED.value == "QUEUED"
        assert ReportStatus.RUNNING.value == "RUNNING"
        assert ReportStatus.READY.value == "READY"
        assert ReportStatus.FAILED.value == "FAILED"
        assert ReportStatus.EXPIRED.value == "EXPIRED"

    def test_report_format_values(self) -> None:
        assert ReportFormat.PDF.value == "PDF"
        assert ReportFormat.XLSX.value == "XLSX"
        assert ReportFormat.CSV.value == "CSV"

    def test_report_type_values(self) -> None:
        assert ReportType.SUMMARY.value == "SUMMARY"
        assert ReportType.DETAIL.value == "DETAIL"

    def test_report_creation(self) -> None:
        report = Report(
            report_id="test-id",
            report_type=ReportType.SUMMARY,
            format=ReportFormat.PDF,
            requested_by="test-user",
            parameters={"source_ids": ["src-1"]},
            status=ReportStatus.QUEUED,
            version=1,
        )
        assert report.report_id == "test-id"
        assert report.status == ReportStatus.QUEUED
        assert report.format == ReportFormat.PDF

    def test_report_request_creation(self) -> None:
        request = ReportRequest(
            report_type=ReportType.SUMMARY,
            format=ReportFormat.CSV,
            parameters={"days": 30},
            reason_code="TEST_REPORT",
        )
        assert request.report_type == ReportType.SUMMARY
        assert request.format == ReportFormat.CSV


class TestExportPolicy:
    def test_evaluate_export_allows_valid(self) -> None:
        policy = ReportExportPolicy(
            version="POLICY_V1",
            policy_name="test",
            sensitivity_level=None,
            max_file_size=1024 * 1024,
            online_duration_seconds=3600,
            require_justification=False,
            require_maker_checker=False,
            watermark_enabled=True,
            dlp_enabled=False,
            allowed_formats=frozenset({ReportFormat.CSV}),
        )
        request = ReportRequest(
            report_type=ReportType.SUMMARY,
            format=ReportFormat.CSV,
            parameters={},
            reason_code="",
        )
        decision = evaluate_export(request, policy, "corr-1")
        assert decision.allowed
        assert decision.reason_code == "EXPORT_ALLOWED"

    def test_evaluate_export_fail_closed_no_policy(self) -> None:
        request = ReportRequest(
            report_type=ReportType.SUMMARY,
            format=ReportFormat.CSV,
            parameters={},
            reason_code="",
        )
        with pytest.raises(ReportExportDeniedError) as exc_info:
            evaluate_export(request, None, "corr-1")
        assert exc_info.value.reason_code == "NO_EXPORT_POLICY"

    def test_evaluate_export_blocked_format(self) -> None:
        policy = ReportExportPolicy(
            version="POLICY_V1",
            policy_name="test",
            sensitivity_level=None,
            max_file_size=1024 * 1024,
            online_duration_seconds=3600,
            require_justification=False,
            require_maker_checker=False,
            watermark_enabled=True,
            dlp_enabled=False,
            allowed_formats=frozenset({ReportFormat.CSV}),
        )
        request = ReportRequest(
            report_type=ReportType.SUMMARY,
            format=ReportFormat.PDF,
            parameters={},
            reason_code="",
        )
        with pytest.raises(ReportExportDeniedError) as exc_info:
            evaluate_export(request, policy, "corr-1")
        assert exc_info.value.reason_code == "FORMAT_NOT_ALLOWED"

    def test_evaluate_export_requires_justification(self) -> None:
        policy = ReportExportPolicy(
            version="POLICY_V1",
            policy_name="test",
            sensitivity_level="HIGH",
            max_file_size=1024 * 1024,
            online_duration_seconds=3600,
            require_justification=True,
            require_maker_checker=False,
            watermark_enabled=True,
            dlp_enabled=False,
            allowed_formats=frozenset({ReportFormat.CSV}),
        )
        request = ReportRequest(
            report_type=ReportType.SUMMARY,
            format=ReportFormat.CSV,
            parameters={},
            reason_code="",
        )
        with pytest.raises(ReportExportDeniedError) as exc_info:
            evaluate_export(request, policy, "corr-1")
        assert exc_info.value.reason_code == "JUSTIFICATION_REQUIRED"

    def test_evaluate_export_requires_maker_checker(self) -> None:
        policy = ReportExportPolicy(
            version="POLICY_V1",
            policy_name="test",
            sensitivity_level="HIGH",
            max_file_size=1024 * 1024,
            online_duration_seconds=3600,
            require_justification=False,
            require_maker_checker=True,
            watermark_enabled=True,
            dlp_enabled=False,
            allowed_formats=frozenset({ReportFormat.CSV}),
        )
        request = ReportRequest(
            report_type=ReportType.SUMMARY,
            format=ReportFormat.CSV,
            parameters={},
            reason_code="",
        )
        with pytest.raises(ReportExportDeniedError) as exc_info:
            evaluate_export(request, policy, "corr-1")
        assert exc_info.value.reason_code == "MAKER_CHECKER_REQUIRED"

    def test_evaluate_export_maker_checker_approved(self) -> None:
        policy = ReportExportPolicy(
            version="POLICY_V1",
            policy_name="test",
            sensitivity_level="HIGH",
            max_file_size=1024 * 1024,
            online_duration_seconds=3600,
            require_justification=False,
            require_maker_checker=True,
            watermark_enabled=True,
            dlp_enabled=False,
            allowed_formats=frozenset({ReportFormat.CSV}),
        )
        request = ReportRequest(
            report_type=ReportType.SUMMARY,
            format=ReportFormat.CSV,
            parameters={},
            reason_code="",
        )
        decision = evaluate_export(request, policy, "corr-1", has_maker_checker_approval=True)
        assert decision.allowed

    def test_check_download_access_expired(self) -> None:
        policy = ReportExportPolicy(
            version="POLICY_V1",
            policy_name="test",
            sensitivity_level=None,
            max_file_size=1024 * 1024,
            online_duration_seconds=3600,
            require_justification=False,
            require_maker_checker=False,
            watermark_enabled=True,
            dlp_enabled=False,
            allowed_formats=frozenset({ReportFormat.CSV}),
        )
        expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        with pytest.raises(ReportExportDeniedError) as exc_info:
            check_download_access(policy, expires_at, "corr-1")
        assert exc_info.value.reason_code == "DOWNLOAD_EXPIRED"

    def test_check_download_access_valid(self) -> None:
        policy = ReportExportPolicy(
            version="POLICY_V1",
            policy_name="test",
            sensitivity_level=None,
            max_file_size=1024 * 1024,
            online_duration_seconds=3600,
            require_justification=False,
            require_maker_checker=False,
            watermark_enabled=True,
            dlp_enabled=False,
            allowed_formats=frozenset({ReportFormat.CSV}),
        )
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        check_download_access(policy, expires_at, "corr-1")

    def test_check_download_access_no_policy(self) -> None:
        with pytest.raises(ReportExportDeniedError) as exc_info:
            check_download_access(None, None, "corr-1")
        assert exc_info.value.reason_code == "NO_EXPORT_POLICY"


class TestExport:
    def test_generate_csv(self) -> None:
        class _Provider:
            def fetch_report_data(self, report_type, parameters):
                return ("Col1", "Col2"), (("a", "1"), ("b", "2"))

        result = generate_report(
            ReportType.SUMMARY,
            ReportFormat.CSV,
            {},
            _Provider(),
            None,
            watermark_text="Test Watermark",
        )
        assert isinstance(result, GeneratedFile)
        assert result.mime_type == "text/csv; charset=utf-8"
        assert result.size_bytes > 0
        text = result.content.decode("utf-8-sig")
        assert "Col1" in text
        assert "a" in text
        assert "1" in text
        assert "Test Watermark" in text


class TestReportRepository:
    """PostgreSQLReportRepository birim testleri (in-memory SQLite ile)."""

    @pytest.fixture
    def repo(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.orm import Session as SaSession
        from veri_kalitesi.reporting.repository import PostgreSQLReportRepository, report_tables

        engine = create_engine("sqlite://", echo=False)
        tables = report_tables(schema="")
        tables.reports.create(engine, checkfirst=True)
        sf = sessionmaker(bind=engine, class_=SaSession)
        return PostgreSQLReportRepository(sf, schema="")

    def test_create_and_get_report(self, repo) -> None:
        request = ReportRequest(
            report_type=ReportType.SUMMARY,
            format=ReportFormat.PDF,
            parameters={"src": "test"},
            reason_code="TEST",
        )
        report = repo.create_report(request, "test-user")
        assert report.status == ReportStatus.QUEUED
        assert report.requested_by == "test-user"

        fetched = repo.get_report(report.report_id)
        assert fetched.report_id == report.report_id
        assert fetched.report_type == ReportType.SUMMARY

    def test_get_report_not_found(self, repo) -> None:
        with pytest.raises(ReportNotFoundError):
            repo.get_report("nonexistent")

    def test_update_report_status(self, repo) -> None:
        request = ReportRequest(
            report_type=ReportType.SUMMARY,
            format=ReportFormat.CSV,
            parameters={},
            reason_code="TEST",
        )
        report = repo.create_report(request, "test-user")

        updated = repo.update_report_status(
            report.report_id,
            ReportStatus.READY,
            online_file_reference="/tmp/test.csv",
            file_size=100,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        assert updated.status == ReportStatus.READY
        assert updated.online_file_reference == "/tmp/test.csv"
        assert updated.file_size == 100
        assert updated.version == 2

    def test_update_report_status_version_bumps(self, repo) -> None:
        """Her guncelleme version sayisini artirir."""
        request = ReportRequest(
            report_type=ReportType.SUMMARY,
            format=ReportFormat.CSV,
            parameters={},
            reason_code="TEST",
        )
        report = repo.create_report(request, "test-user")
        assert report.version == 1

        r1 = repo.update_report_status(report.report_id, ReportStatus.RUNNING)
        assert r1.version == 2

        r2 = repo.update_report_status(
            r1.report_id,
            ReportStatus.READY,
            online_file_reference="/tmp/test.csv",
            file_size=100,
        )
        assert r2.version == 3

    def test_list_reports_by_user(self, repo) -> None:
        repo.create_report(ReportRequest(ReportType.SUMMARY, ReportFormat.PDF, {}, "T1"), "user1")
        repo.create_report(ReportRequest(ReportType.DETAIL, ReportFormat.CSV, {}, "T2"), "user1")
        repo.create_report(ReportRequest(ReportType.SUMMARY, ReportFormat.PDF, {}, "T3"), "user2")

        user1_reports = repo.list_reports_by_user("user1")
        assert len(user1_reports) == 2
        assert user1_reports[0].requested_by == "user1"

        user2_reports = repo.list_reports_by_user("user2")
        assert len(user2_reports) == 1

    def test_delete_report(self, repo) -> None:
        request = ReportRequest(
            report_type=ReportType.SUMMARY,
            format=ReportFormat.PDF,
            parameters={},
            reason_code="TEST",
        )
        report = repo.create_report(request, "test-user")
        repo.delete_report(report.report_id)

        with pytest.raises(ReportNotFoundError):
            repo.get_report(report.report_id)


class TestReportSchedule:
    """ReportScheduleService birim testleri."""

    @pytest.fixture
    def repo(self):
        class _MemoryRepo:
            def __init__(self):
                self._schedules: dict[str, ReportSchedule] = {}
                self._order: list[str] = []

            def add(self, schedule: ReportSchedule) -> ReportSchedule:
                self._schedules[schedule.schedule_id] = schedule
                self._order.append(schedule.schedule_id)
                return schedule

            def list_all(self) -> tuple[ReportSchedule, ...]:
                return tuple(self._schedules[sid] for sid in self._order)

            def get(self, schedule_id: str) -> ReportSchedule:
                if schedule_id not in self._schedules:
                    raise ReportNotFoundError(schedule_id)
                return self._schedules[schedule_id]

            def delete(self, schedule_id: str) -> None:
                if schedule_id not in self._schedules:
                    raise ReportNotFoundError(schedule_id)
                del self._schedules[schedule_id]
                self._order.remove(schedule_id)

            def due(self, now: datetime) -> tuple[ReportSchedule, ...]:
                result = []
                for sid in self._order:
                    s = self._schedules[sid]
                    if s.is_active and s.next_run_at is not None and s.next_run_at <= now:
                        result.append(s)
                return tuple(result)

            def advance(
                self,
                schedule_id: str,
                *,
                triggered_at: datetime,
                next_run_at: datetime | None,
                is_active: bool,
            ):
                old = self._schedules[schedule_id]
                new = ReportSchedule(
                    schedule_id=old.schedule_id,
                    name=old.name,
                    report_type=old.report_type,
                    format=old.format,
                    parameters=old.parameters,
                    sensitivity_level=old.sensitivity_level,
                    recipients=old.recipients,
                    schedule_type=old.schedule_type,
                    timezone_name=old.timezone_name,
                    local_time=old.local_time,
                    once_at=old.once_at,
                    day_of_week=old.day_of_week,
                    day_of_month=old.day_of_month,
                    is_active=is_active,
                    next_run_at=next_run_at,
                    created_by=old.created_by,
                    created_at=old.created_at,
                    last_triggered_at=triggered_at,
                )
                self._schedules[schedule_id] = new
                return new

        return _MemoryRepo()

    @pytest.fixture
    def service(self, repo):
        from veri_kalitesi.reporting.service import ReportService

        report_service = MagicMock(spec=ReportService)
        return ReportScheduleService(repo, report_service)

    def test_create_daily_schedule(self, service, repo):
        request = ReportScheduleCreateRequest(
            name="Daily Report",
            report_type=ReportType.SUMMARY,
            format=ReportFormat.CSV,
            parameters={},
            sensitivity_level=None,
            recipients=("user-1",),
            schedule_type="DAILY",
            timezone_name="UTC",
            local_time="08:00",
        )
        schedule, preview = service.create_schedule(request, created_by="test-user")
        assert schedule.name == "Daily Report"
        assert schedule.schedule_type == ScheduleType.DAILY
        assert schedule.is_active
        assert schedule.created_by == "test-user"
        assert len(preview) == 5
        assert schedule.next_run_at is not None

    def test_create_once_schedule(self, service, repo):
        future = datetime.now(timezone.utc) + timedelta(hours=2)
        request = ReportScheduleCreateRequest(
            name="One-time Report",
            report_type=ReportType.DETAIL,
            format=ReportFormat.PDF,
            parameters={"source_ids": ("src-1",)},
            sensitivity_level="INTERNAL",
            recipients=("user-1", "user-2"),
            schedule_type="ONCE",
            timezone_name="UTC",
            once_at=future,
        )
        schedule, preview = service.create_schedule(request, created_by="test-user")
        assert schedule.name == "One-time Report"
        assert schedule.schedule_type == ScheduleType.ONCE
        assert schedule.parameters == {"source_ids": ("src-1",)}
        assert schedule.recipients == ("user-1", "user-2")
        assert len(preview) == 1

    def test_create_schedule_past_raises(self, service, repo):
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        request = ReportScheduleCreateRequest(
            name="Past Report",
            report_type=ReportType.SUMMARY,
            format=ReportFormat.CSV,
            parameters={},
            sensitivity_level=None,
            recipients=(),
            schedule_type="ONCE",
            timezone_name="UTC",
            once_at=past,
        )
        with pytest.raises(ReportingError, match="must have a future trigger"):
            service.create_schedule(request, created_by="test-user")

    def test_list_schedules(self, service, repo):
        request = ReportScheduleCreateRequest(
            name="List Test",
            report_type=ReportType.SUMMARY,
            format=ReportFormat.CSV,
            parameters={},
            sensitivity_level=None,
            recipients=(),
            schedule_type="DAILY",
            timezone_name="UTC",
            local_time="09:00",
        )
        service.create_schedule(request, created_by="user-1")
        schedules = service.list_schedules()
        assert len(schedules) == 1
        assert schedules[0].name == "List Test"

    def test_delete_schedule(self, service, repo):
        request = ReportScheduleCreateRequest(
            name="Delete Test",
            report_type=ReportType.SUMMARY,
            format=ReportFormat.CSV,
            parameters={},
            sensitivity_level=None,
            recipients=(),
            schedule_type="DAILY",
            timezone_name="UTC",
            local_time="10:00",
        )
        schedule, _ = service.create_schedule(request, created_by="user-1")
        service.delete_schedule(schedule.schedule_id)
        assert len(service.list_schedules()) == 0

    def test_trigger_due_generates_report(self, service, repo):
        from veri_kalitesi.reporting.models import Report as ReportModel

        future = datetime.now(timezone.utc) + timedelta(minutes=5)
        request = ReportScheduleCreateRequest(
            name="Trigger Test",
            report_type=ReportType.SUMMARY,
            format=ReportFormat.CSV,
            parameters={},
            sensitivity_level=None,
            recipients=(),
            schedule_type="ONCE",
            timezone_name="UTC",
            once_at=future,
        )
        schedule, _ = service.create_schedule(request, created_by="user-1")

        # Simulate the schedule being due by advancing to past
        repo.advance(
            schedule.schedule_id,
            triggered_at=datetime.now(timezone.utc),
            next_run_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            is_active=True,
        )

        service._report_service.request_report.return_value = ReportModel(
            report_id="generated-rpt-1",
            report_type=ReportType.SUMMARY,
            format=ReportFormat.CSV,
            requested_by="scheduler",
            parameters={},
            status=ReportStatus.QUEUED,
            version=1,
        )

        triggered = service.trigger_due()
        assert len(triggered) == 1
        assert triggered[0] == "generated-rpt-1"
        service._report_service.request_report.assert_called_once()


class TestReportWorker:
    """ReportWorker dayaniklilik (retry, timeout, hata siniflandirmasi) testleri."""

    @pytest.fixture
    def repo(self):
        """In-memory SQLite repository fixture."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.orm import Session as SaSession
        from veri_kalitesi.reporting.repository import PostgreSQLReportRepository, report_tables

        engine = create_engine("sqlite://", echo=False)
        tables = report_tables(schema="")
        tables.reports.create(engine, checkfirst=True)
        sf = sessionmaker(bind=engine, class_=SaSession)

        class _TestRepo(PostgreSQLReportRepository):
            def create_report(self, request, requested_by, **kwargs):
                return super().create_report(request, requested_by)

        return PostgreSQLReportRepository(sf, schema="")

    @pytest.fixture
    def policy_repo(self):
        class _Repo:
            def get_active_policy(self, sensitivity_level):
                return None

        return _Repo()

    @pytest.fixture
    def worker(self, repo, policy_repo):
        from veri_kalitesi.reporting.worker import ReportWorker, ReportWorkerSettings

        class _GoodProvider:
            def fetch_report_data(self, report_type, parameters):
                return ("Col1",), (("val1",),)

        return ReportWorker(
            repo,
            policy_repo,
            _GoodProvider(),
            settings=ReportWorkerSettings(
                storage_path="/tmp/reports_test",
                max_retry_attempts=3,
                retry_delay_seconds=0.01,
                generation_timeout_seconds=60,
            ),
        )

    def _create_queued_report(self, repo, fmt=ReportFormat.CSV):
        request = ReportRequest(
            report_type=ReportType.SUMMARY,
            format=fmt,
            parameters={},
            reason_code="WORKER_TEST",
        )
        return repo.create_report(request, "test-user")

    def test_retry_success_after_failure(self, repo, worker):
        """Ilk denemede basarisiz, ikincide basarili -> READY."""
        attempt = [0]

        class _FailingThenOkProvider:
            def fetch_report_data(self, report_type, parameters):
                attempt[0] += 1
                if attempt[0] == 1:
                    raise RuntimeError("Simulated transient failure")
                return ("Col1",), (("val1",),)

        from veri_kalitesi.reporting.worker import ReportWorker, ReportWorkerSettings

        retry_worker = ReportWorker(
            repo,
            worker._policy_repo,
            _FailingThenOkProvider(),
            settings=ReportWorkerSettings(
                storage_path="/tmp/reports_test",
                max_retry_attempts=3,
                retry_delay_seconds=0.01,
            ),
        )

        report = self._create_queued_report(repo)
        result = retry_worker.process_report(report.report_id)
        assert result.status == ReportStatus.READY
        assert attempt[0] == 2

    def test_retry_exhausted(self, repo, worker):
        """Tum denemeler basarisiz -> FAILED."""

        class _AlwaysFailingProvider:
            def fetch_report_data(self, report_type, parameters):
                raise RuntimeError("Simulated persistent failure")

        from veri_kalitesi.reporting.worker import ReportWorker, ReportWorkerSettings

        fail_worker = ReportWorker(
            repo,
            worker._policy_repo,
            _AlwaysFailingProvider(),
            settings=ReportWorkerSettings(
                storage_path="/tmp/reports_test",
                max_retry_attempts=2,
                retry_delay_seconds=0.01,
            ),
        )

        report = self._create_queued_report(repo)
        result = fail_worker.process_report(report.report_id)
        assert result.status == ReportStatus.FAILED
        assert result.failure_reason is not None
        assert "attempts=2" in result.failure_reason

    def test_non_retryable_error(self, repo, worker):
        """Non-retryable hata -> direkt FAILED, retry yok."""

        class _BadProvider:
            def fetch_report_data(self, report_type, parameters):
                raise ValueError("Invalid parameter — non-retryable")

        from veri_kalitesi.reporting.worker import ReportWorker, ReportWorkerSettings

        fail_worker = ReportWorker(
            repo,
            worker._policy_repo,
            _BadProvider(),
            settings=ReportWorkerSettings(
                storage_path="/tmp/reports_test",
                max_retry_attempts=3,
                retry_delay_seconds=0.01,
            ),
        )

        report = self._create_queued_report(repo)
        result = fail_worker.process_report(report.report_id)
        assert result.status == ReportStatus.FAILED
        assert result.failure_reason is not None
        assert "ValueError" in result.failure_reason
        # Non-retryable hatada attempts bilgisi eklenmez
        assert "attempts" not in result.failure_reason

    def test_timeout_enforcement(self, repo, worker):
        """Timeout asimi -> FAILED."""

        class _SlowProvider:
            def fetch_report_data(self, report_type, parameters):
                import time

                time.sleep(5.0)  # timeout'tan cok daha uzun
                return ("Col1",), (("val1",),)

        from veri_kalitesi.reporting.worker import ReportWorker, ReportWorkerSettings

        timeout_worker = ReportWorker(
            repo,
            worker._policy_repo,
            _SlowProvider(),
            settings=ReportWorkerSettings(
                storage_path="/tmp/reports_test",
                max_retry_attempts=1,
                retry_delay_seconds=0.01,
                generation_timeout_seconds=0.2,  # 200ms — thread'in baslamasi icin yeterli
            ),
        )

        report = self._create_queued_report(repo)
        result = timeout_worker.process_report(report.report_id)
        assert result.status == ReportStatus.FAILED
        assert result.failure_reason is not None
        assert "timed out" in result.failure_reason.lower() or "Timeout" in result.failure_reason

    def test_retryable_error_classification(self, worker):
        """_is_retryable dogru siniflandirma yapiyor."""
        from veri_kalitesi.reporting.errors import ReportRetryableError

        assert worker._is_retryable(RuntimeError("transient"))
        assert worker._is_retryable(ConnectionError("connection lost"))
        assert worker._is_retryable(TimeoutError("timed out"))
        assert worker._is_retryable(MemoryError("oom"))
        assert worker._is_retryable(ReportRetryableError("transient"))

        assert not worker._is_retryable(ValueError("invalid"))
        assert not worker._is_retryable(TypeError("bad type"))
        assert not worker._is_retryable(KeyError("missing"))
        assert not worker._is_retryable(AttributeError("no attr"))
        assert not worker._is_retryable(OSError())
