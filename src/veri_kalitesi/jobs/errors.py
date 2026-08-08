"""Kalıcı iş kuyruğu domain hata tipleri."""


class JobError(Exception):
    """İş kuyruğu için temel hata."""


class JobValidationError(JobError):
    """İş veya lease girdisi geçersiz."""


class JobNotFoundError(JobError):
    """İstenen iş bulunamadı."""


class JobConflictError(JobError):
    """İş kaydı bir veritabanı çakışması nedeniyle yazılamadı."""


class JobIdempotencyConflictError(JobConflictError):
    """Aynı idempotency anahtarı farklı bir payload ile kullanıldı."""


class JobLeaseError(JobConflictError):
    """İş claim sahibi veya lease koşulu geçersiz."""


class JobConcurrencyError(JobConflictError):
    """İş sürümü optimistic concurrency kontrolünde çakıştı."""


class JobAuthorizationError(JobError):
    """Dead-letter yeniden işleme yetkisi doğrulanamadı."""
