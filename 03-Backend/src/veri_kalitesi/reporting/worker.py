"""Asenkron rapor is protocol ve worker.

Rapor talebi alindiginda QUEUED kaydi olusur. Worker bu kaydi alir,
raporu uretir ve READY/FAILED durumuna gecirir.

Dayaniklilik: retry, timeout, hata siniflandirmasi.
"""

from __future__ import annotations

import time as time_module
import concurrent.futures
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Event
from typing import Protocol

from veri_kalitesi.reporting.errors import ReportNotReadyError, ReportRetryableError
from veri_kalitesi.reporting.export import GeneratedFile, ReportDataProvider, generate_report
from veri_kalitesi.reporting.models import (
    Report,
    ReportExportPolicy,
    ReportFormat,
    ReportStatus,
    ReportType,
)
from veri_kalitesi.reporting.policies import ReportExportPolicyRepository


class ReportRepository(Protocol):
    """Rapor repository protocol — worker'in ihtiyac duydugu metodlar."""

    def get_report(self, report_id: str) -> Report: ...
    def update_report_status(
        self,
        report_id: str,
        status: ReportStatus,
        *,
        online_file_reference: str | None = None,
        file_size: int | None = None,
        failure_reason: str | None = None,
        expires_at: datetime | None = None,
    ) -> Report: ...


@dataclass(frozen=True)
class ReportWorkerSettings:
    """Worker yapilandirmasi."""

    storage_path: str = "/tmp/reports"
    default_online_duration_days: int = 30
    max_retry_attempts: int = 3
    retry_delay_seconds: float = 5.0
    generation_timeout_seconds: int = 300


class ReportWorker:
    """Rapor worker — QUEUED kayitlari alir, rapor uretir ve kaydeder.

    Retry mantigi: gecici (retryable) hatalarda max_retry_attempts'e kadar
    ussel backoff ile yeniden dener. Retry sonrasi da basarisizsa FAILED
    durumuna gecer. Non-retryable hatalarda direkt FAILED.
    """

    def __init__(
        self,
        report_repository: ReportRepository,
        policy_repository: ReportExportPolicyRepository,
        data_provider: ReportDataProvider,
        settings: ReportWorkerSettings | None = None,
    ) -> None:
        self._repo = report_repository
        self._policy_repo = policy_repository
        self._data_provider = data_provider
        self._settings = settings or ReportWorkerSettings()

    def process_report(
        self,
        report_id: str,
        *,
        timeout_seconds: int | None = None,
        cancellation_event: Event | None = None,
    ) -> Report:
        """Bir raporu isler: QUEUED -> RUNNING -> READY/FAILED.

        Retryable hatalarda max_retry_attempts'e kadar ussel backoff ile
        yeniden dener. Non-retryable hatalarda direkt FAILED.
        """
        from pathlib import Path

        report = self._repo.get_report(report_id)
        if cancellation_event is not None and cancellation_event.is_set():
            raise ReportRetryableError("Report generation was cancelled.")

        if report.status != ReportStatus.QUEUED:
            raise ReportNotReadyError(report_id, report.status.value)

        # RUNNING -> uretim basliyor
        report = self._repo.update_report_status(
            report_id, ReportStatus.RUNNING
        )

        last_exception: Exception | None = None
        max_attempts = max(1, self._settings.max_retry_attempts)
        retried = False

        for attempt in range(1, max_attempts + 1):
            try:
                if cancellation_event is not None and cancellation_event.is_set():
                    raise ReportRetryableError("Report generation was cancelled.")
                policy = self._policy_repo.get_active_policy(report.sensitivity_level)

                watermark_text = None
                if policy and policy.watermark_enabled:
                    watermark_text = (
                        f"Data Quality Report — {report.report_id} — "
                        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
                    )

                generated = self._generate_with_timeout(
                    report_type=report.report_type,
                    fmt=report.format,
                    parameters=report.parameters,
                    policy=policy,
                    watermark_text=watermark_text,
                    timeout_seconds=timeout_seconds,
                )
                if cancellation_event is not None and cancellation_event.is_set():
                    raise ReportRetryableError("Report generation was cancelled.")

                # Dosyayi kaydet
                storage = Path(self._settings.storage_path)
                storage.mkdir(parents=True, exist_ok=True)
                file_path = storage / f"{report_id}_{generated.filename}"
                file_path.write_bytes(generated.content)

                # Expiry hesapla
                expires_at: datetime | None = None
                if policy:
                    expires_at = datetime.now(timezone.utc) + timedelta(
                        seconds=policy.online_duration_seconds
                    )
                else:
                    expires_at = datetime.now(timezone.utc) + timedelta(
                        days=self._settings.default_online_duration_days
                    )

                # READY
                report = self._repo.update_report_status(
                    report_id,
                    ReportStatus.READY,
                    online_file_reference=str(file_path),
                    file_size=generated.size_bytes,
                    expires_at=expires_at,
                )
                return report

            except Exception as exc:
                if cancellation_event is not None and cancellation_event.is_set():
                    raise ReportRetryableError(
                        "Report generation was cancelled."
                    ) from exc
                last_exception = exc
                if not self._is_retryable(exc):
                    # Non-retryable hata — direkt FAILED, retry bilgisi eklenmez
                    report = self._repo.update_report_status(
                        report_id,
                        ReportStatus.FAILED,
                        failure_reason=f"{type(exc).__name__}: {exc}",
                    )
                    return report
                retried = True
                if attempt < max_attempts:
                    # Ussel backoff: delay * 2^(attempt-1)
                    backoff = self._settings.retry_delay_seconds * (2 ** (attempt - 1))
                    time_module.sleep(backoff)
                    continue

        # Retry sonrasi da basarisiz -> FAILED
        assert last_exception is not None
        retry_info = f" (attempts={max_attempts})" if retried else ""
        report = self._repo.update_report_status(
            report_id,
            ReportStatus.FAILED,
            failure_reason=f"{type(last_exception).__name__}: {last_exception}{retry_info}",
        )
        return report

    def _generate_with_timeout(
        self,
        report_type: ReportType,
        fmt: ReportFormat,
        parameters: dict,
        policy: ReportExportPolicy | None,
        watermark_text: str | None,
        timeout_seconds: int | None = None,
    ) -> GeneratedFile:
        """Raporu timeout ile uretir.

        generation_timeout_seconds asiminda concurrent.futures.TimeoutError
        firlatilir.
        """
        timeout = max(
            1,
            min(
                self._settings.generation_timeout_seconds,
                timeout_seconds or self._settings.generation_timeout_seconds,
            ),
        )

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                generate_report,
                report_type=report_type,
                fmt=fmt,
                parameters=parameters,
                data_provider=self._data_provider,
                policy=policy,
                watermark_text=watermark_text,
            )
            try:
                return future.result(timeout=timeout)
            except concurrent.futures.TimeoutError:
                raise ReportRetryableError(
                    f"Report generation timed out after {timeout}s",
                )

    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        """Hatanin yeniden denenebilir olup olmadigini belirler.

        Retryable: gecici dosya/ag/konteyner hatalari.
        Non-retryable: gecersiz parametre, tip hatasi gibi kalici hatalar.
        """
        if isinstance(exc, ReportRetryableError):
            return True
        if isinstance(exc, (ConnectionError, TimeoutError, MemoryError)):
            return True
        # RuntimeError: alt sinifi olmayan genel hatalar icin retryable
        if type(exc) is RuntimeError:
            return True
        # Non-retryable: ValueError, TypeError, KeyError, AttributeError, OSError
        return False
