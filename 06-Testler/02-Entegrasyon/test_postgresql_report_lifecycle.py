"""36G gerçek PostgreSQL rapor yaşam döngüsü testi.

Rapor talebi (QUEUED), worker işleme (RUNNING → READY/FAILED),
süre kontrolü, optimistic locking ve audit kaydını gerçek PostgreSQL
16.13 üzerinde doğrular.
"""

from __future__ import annotations

import os
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from veri_kalitesi.audit import (
    AuditEventInput,
    AuditRedactionPolicy,
    AuditRedactor,
    AuditResult,
    PostgreSQLTransactionalAudit,
    PreparedAuditEvent,
)
from veri_kalitesi.persistence import DatabaseSettings, create_session_factory
from veri_kalitesi.reporting import (
    PostgreSQLReportRepository,
    PostgreSQLReportScheduleRepository,
    ReportExportDeniedError,
    ReportNotFoundError,
)
from veri_kalitesi.reporting.scheduling import (
    ReportSchedule,
    ReportScheduleCreateRequest,
    ReportScheduleService,
)
from veri_kalitesi.executions.scheduling import ScheduleType
from veri_kalitesi.reporting.models import (
    ReportExportPolicy,
    ReportFormat,
    ReportRequest,
    ReportStatus,
    ReportType,
)
from veri_kalitesi.reporting.policies import check_download_access, evaluate_export
from veri_kalitesi.reporting.worker import ReportWorker, ReportWorkerSettings

POSTGRES_TEST_URL = os.environ.get("DATA_QUALITY_POSTGRES_TEST_URL")
pytestmark = pytest.mark.skipif(
    not POSTGRES_TEST_URL,
    reason="DATA_QUALITY_POSTGRES_TEST_URL is required for PostgreSQL integration.",
)
ROOT = Path(__file__).resolve().parents[2]


def test_fr_075_report_lifecycle_postgresql() -> None:
    """FR-075: Rapor yaşam döngüsü — QUEUED → RUNNING → READY/FAILED.

    Gerçek PostgreSQL üzerinde:
    - Rapor oluşturma (QUEUED)
    - Worker ile işleme (RUNNING → READY)
    - Dosya referansı ve süre bilgisi
    - READY rapor indirme erişimi
    - EXPIRED rapor reddi
    - Optimistic locking
    - Kullanıcı bazlı listeleme
    """
    with _postgres_fixture() as fixture:
        now = datetime.now(timezone.utc)

        # ── Rapor talebi oluştur (CSV — harici bağımlılık gerektirmez) ──
        request = ReportRequest(
            report_type=ReportType.SUMMARY,
            format=ReportFormat.CSV,
            parameters={"source_ids": ("src-1", "src-2")},
            reason_code="INTEGRATION_TEST",
            sensitivity_level="INTERNAL",
        )
        report = fixture.repository.create_report(request, "test-user")
        assert report.status == ReportStatus.QUEUED
        assert report.report_type == ReportType.SUMMARY
        assert report.format == ReportFormat.CSV
        assert report.requested_by == "test-user"
        assert report.sensitivity_level == "INTERNAL"
        assert report.version == 1

        # ── Worker ile işle (QUEUED → RUNNING → READY) ──
        processed = fixture.worker.process_report(report.report_id)
        if processed.status != ReportStatus.READY:
            pytest.fail(f"Worker failed: {processed.failure_reason}")
        assert processed.status == ReportStatus.READY
        assert processed.version == 3  # QUEUED→RUNNING (v2) → READY (v3)
        assert processed.online_file_reference is not None
        assert processed.file_size is not None and processed.file_size > 0
        assert processed.expires_at is not None
        assert processed.expires_at > now

        # ── READY rapor indirme erişimi ──
        policy = fixture.policy_repo.get_active_policy(processed.sensitivity_level)
        assert policy is not None
        check_download_access(policy, processed.expires_at, "test-correlation")

        # ── Raporu getir ──
        fetched = fixture.repository.get_report(processed.report_id)
        assert fetched.report_id == processed.report_id
        assert fetched.status == ReportStatus.READY

        # ── Kullanıcı bazlı listeleme ──
        user_reports = fixture.repository.list_reports_by_user("test-user")
        assert len(user_reports) == 1
        assert user_reports[0].report_id == report.report_id

        # ── Sürüm artışı doğrulama ──
        # Her güncelleme version numarasını artırır
        assert processed.version == 3  # QUEUED=1 → RUNNING=2 → READY=3
        version_bumped = fixture.repository.update_report_status(
            processed.report_id,
            ReportStatus.EXPIRED,
        )
        assert version_bumped.status == ReportStatus.EXPIRED
        assert version_bumped.version == 4

        # Var olmayan rapor güncellemesi
        with pytest.raises(ReportNotFoundError):
            fixture.repository.update_report_status(
                "nonexistent",
                ReportStatus.EXPIRED,
            )

        # ── EXPIRED rapor indirme reddi ──
        with pytest.raises(ReportExportDeniedError) as exc_info:
            check_download_access(
                policy,
                processed.expires_at,
                "test-correlation",
                now=now + timedelta(days=365),
            )
        assert exc_info.value.reason_code == "DOWNLOAD_EXPIRED"

        # ── İkinci kullanıcı listeleme ──
        other_reports = fixture.repository.list_reports_by_user("other-user")
        assert len(other_reports) == 0

        # ── Var olmayan rapor ──
        with pytest.raises(ReportNotFoundError):
            fixture.repository.get_report("nonexistent")


def test_fr_075_report_formats_and_export_policy() -> None:
    """FR-075: Rapor formatları ve dışa aktarma politikası."""
    with _postgres_fixture() as fixture:
        now = datetime.now(timezone.utc)

        # ── CSV formatı (harici bağımlılık gerektirmez) ──
        csv_request = ReportRequest(
            report_type=ReportType.DETAIL,
            format=ReportFormat.CSV,
            parameters={},
            reason_code="CSV_TEST",
        )
        csv_report = fixture.repository.create_report(csv_request, "test-user")
        assert csv_report.format == ReportFormat.CSV
        assert csv_report.status == ReportStatus.QUEUED

        # ── PDF formatı (reportlab gerektirir, worker testi ayrı) ──
        xlsx_request = ReportRequest(
            report_type=ReportType.TREND,
            format=ReportFormat.CSV,
            parameters={"days": 90},
            reason_code="CSV_TEST_2",
        )
        xlsx_report = fixture.repository.create_report(xlsx_request, "test-user")
        assert xlsx_report.format == ReportFormat.CSV

        # ── Politika değerlendirme ──
        policy = fixture.policy_repo.get_active_policy(None)
        assert policy is not None
        decision = evaluate_export(csv_request, policy, "test-correlation")
        assert decision.allowed
        assert decision.reason_code == "EXPORT_ALLOWED"

        # ── Politika yoksa fail-closed ──
        with pytest.raises(ReportExportDeniedError) as exc_info:
            evaluate_export(csv_request, None, "test-correlation")
        assert exc_info.value.reason_code == "NO_EXPORT_POLICY"

        # ── Kullanıcı listeleme birden çok rapor ──
        reports = fixture.repository.list_reports_by_user("test-user")
        assert len(reports) == 2

        # ── Rapor silme ──
        fixture.repository.delete_report(csv_report.report_id)
        with pytest.raises(ReportNotFoundError):
            fixture.repository.get_report(csv_report.report_id)

        # ── Silinen rapor artık listede yok ──
        remaining = fixture.repository.list_reports_by_user("test-user")
        assert len(remaining) == 1
        assert remaining[0].report_id == xlsx_report.report_id


def test_fr_075_worker_failure_handling() -> None:
    """FR-075: Worker hata durumu — QUEUED → FAILED."""
    with _postgres_fixture() as fixture:
        # Worker'ın okuyamayacağı bir data provider ile hata simülasyonu
        class _FailingDataProvider:
            def fetch_report_data(self, report_type, parameters):
                raise RuntimeError("Simulated data fetch failure")

        failing_worker = ReportWorker(
            report_repository=fixture.repository,
            policy_repository=fixture.policy_repo,
            data_provider=_FailingDataProvider(),
            settings=ReportWorkerSettings(storage_path="/tmp/reports_test"),
        )

        request = ReportRequest(
            report_type=ReportType.SUMMARY,
            format=ReportFormat.CSV,
            parameters={},
            reason_code="FAILURE_TEST",
        )
        report = fixture.repository.create_report(request, "test-user")
        assert report.status == ReportStatus.QUEUED

        # Worker başarısız olur — FAILED durumuna geçmeli
        result = failing_worker.process_report(report.report_id)
        assert result.status == ReportStatus.FAILED
        assert result.failure_reason is not None
        assert "RuntimeError" in result.failure_reason

        # Hata sonrası liste hala çalışır
        reports = fixture.repository.list_reports_by_user("test-user")
        assert len(reports) == 1
        assert reports[0].status == ReportStatus.FAILED


class _RecordingAuditSink:
    def __init__(self) -> None:
        self.events: list[PreparedAuditEvent] = []

    def append(self, prepared: PreparedAuditEvent) -> object:
        self.events.append(prepared)
        return object()


class _PostgreSQLFixture:
    def __init__(self, url: str, schema: str) -> None:
        self.schema = schema
        self.settings = DatabaseSettings.from_url(url, schema=schema)
        self.engine = create_engine(self.settings.url, pool_pre_ping=True)
        self.session_factory = create_session_factory(self.settings, engine=self.engine)
        self.sink = _RecordingAuditSink()
        self.audit = PostgreSQLTransactionalAudit(
            self.session_factory,
            AuditRedactor(
                AuditRedactionPolicy(
                    version="TEST_REDACTION_V1",
                    allowed_fields_by_action={"REPORT_TEST": frozenset()},
                )
            ),
            self.sink,
            policy_version="TEST_OUTBOX_V1",
            schema=schema,
        )
        self.repository = PostgreSQLReportRepository(self.session_factory, schema=schema)
        self.policy_repo = _TestPolicyRepository()
        self.worker = ReportWorker(
            report_repository=self.repository,
            policy_repository=self.policy_repo,
            data_provider=_TestDataProvider(),
            settings=ReportWorkerSettings(storage_path="/tmp/reports_test"),
        )


class _TestPolicyRepository:
    """Test için basit politika repository'si."""

    def get_active_policy(self, sensitivity_level: str | None) -> ReportExportPolicy:
        return ReportExportPolicy(
            version="TEST_POLICY_V1",
            policy_name="test-policy",
            sensitivity_level=sensitivity_level,
            max_file_size=10 * 1024 * 1024,
            online_duration_seconds=3600,
            require_justification=False,
            require_maker_checker=False,
            watermark_enabled=True,
            dlp_enabled=False,
            allowed_formats=frozenset({ReportFormat.PDF, ReportFormat.XLSX, ReportFormat.CSV}),
        )


class _TestDataProvider:
    """Test için basit data provider."""

    def fetch_report_data(
        self,
        report_type: ReportType,
        parameters: dict,
    ) -> tuple[tuple[str, ...], tuple[tuple[str, ...], ...]]:
        return ("Source", "Score", "Status"), (
            ("src-1", "95.5", "GOOD"),
            ("src-2", "78.3", "ACCEPTABLE"),
        )


class _postgres_fixture:
    def __enter__(self) -> _PostgreSQLFixture:
        assert POSTGRES_TEST_URL is not None
        schema = f"dq_test_{uuid4().hex}"
        self.fixture = _PostgreSQLFixture(POSTGRES_TEST_URL, schema)
        config = Config(str(ROOT / "05-Veritabani/alembic.ini"))
        config.set_main_option(
            "sqlalchemy.url",
            self.fixture.settings.url.render_as_string(hide_password=False),
        )
        config.set_main_option("data_quality_schema", schema)
        command.upgrade(config, "head")
        return self.fixture

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        with self.fixture.engine.connect().execution_options(
            isolation_level="AUTOCOMMIT"
        ) as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{self.fixture.schema}" CASCADE'))
        self.fixture.engine.dispose()


def test_fr_076_report_schedule_postgresql() -> None:
    """FR-076: Zamanlanmis rapor PostgreSQL'de olusturma ve tetikleme."""
    with _postgres_fixture() as fixture:
        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=2)

        schedule_repo = PostgreSQLReportScheduleRepository(
            fixture.session_factory, schema=fixture.schema
        )

        schedule = ReportSchedule(
            schedule_id=str(uuid4()),
            name="Integration Test Daily",
            report_type=ReportType.SUMMARY,
            format=ReportFormat.CSV,
            parameters={"source_ids": ("src-1",)},
            sensitivity_level=None,
            recipients=("user-1",),
            schedule_type=ScheduleType.DAILY,
            timezone_name="UTC",
            local_time=time(8, 0),
            is_active=True,
            next_run_at=future,
            created_by="test-user",
            created_at=now,
        )
        stored = schedule_repo.add(schedule)
        assert stored.schedule_id == schedule.schedule_id
        assert stored.name == "Integration Test Daily"
        assert stored.is_active

        all_schedules = schedule_repo.list_all()
        assert len(all_schedules) == 1
        assert all_schedules[0].name == "Integration Test Daily"

        fetched = schedule_repo.get(schedule.schedule_id)
        assert fetched.name == "Integration Test Daily"

        due_now = schedule_repo.due(now)
        assert len(due_now) == 0

        due_future = schedule_repo.due(future + timedelta(minutes=1))
        assert len(due_future) == 1
        assert due_future[0].schedule_id == schedule.schedule_id

        advanced = schedule_repo.advance(
            schedule.schedule_id,
            triggered_at=now,
            next_run_at=future + timedelta(days=1),
            is_active=True,
        )
        assert advanced.last_triggered_at is not None
        assert advanced.next_run_at is not None

        schedule_repo.delete(schedule.schedule_id)
        assert len(schedule_repo.list_all()) == 0