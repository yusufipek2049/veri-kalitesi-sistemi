"""Çalıştırma ve kuyruk domain hata tipleri."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from veri_kalitesi.executions.models import RuleResultComputation


class ExecutionError(Exception):
    """Çalıştırma modülü için temel hata."""


class ExecutionValidationError(ExecutionError):
    """Çalıştırma isteği veya durum geçişi geçersiz."""


class ExecutionNotFoundError(ExecutionError):
    """İstenen çalıştırma bulunamadı."""


class IdempotencyConflictError(ExecutionError):
    """Aynı idempotency anahtarı farklı bir payload ile kullanıldı."""


class ExecutionTechnicalError(ExecutionError):
    """Worker tarafından sınıflandırılmış teknik hata."""

    def __init__(self, error_class: str, *, retryable: bool) -> None:
        super().__init__(error_class)
        self.error_class = error_class
        self.retryable = retryable


class ExecutionTimeoutError(ExecutionTechnicalError):
    """Timeout anına kadar tamamlanmış sonuçları taşıyan teknik hata."""

    def __init__(
        self,
        error_class: str = "TOTAL_TIMEOUT",
        *,
        partial_results: tuple[RuleResultComputation, ...] = (),
        completed_partitions: tuple[str, ...] = (),
    ) -> None:
        super().__init__(error_class, retryable=False)
        self.partial_results = partial_results
        self.completed_partitions = completed_partitions
