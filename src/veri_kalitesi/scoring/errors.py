"""Skorlama domain hata tipleri."""


class ScoringError(Exception):
    """Skorlama modülü için temel hata."""


class ScoringValidationError(ScoringError):
    """Skor girdisi veya durum geçişi geçersiz."""


class ScoringAuthorizationError(ScoringError):
    """Skorlama yonetimi yetkilendirme karari islemi reddetti."""


class ScoringTechnicalError(ScoringError):
    """Skorlama altyapısı teknik nedenle işlemi tamamlayamadı."""


class ScoreNotFoundError(ScoringError):
    """İstenen skor kaydı bulunamadı."""


class ScoringConflictError(ScoringError):
    """Yayın veya idempotency çakışması."""


class ScorePublicationError(ScoringError):
    """Skor yayımı state-machine hatası."""


class ScoreReproductionError(ScoringError):
    """Yeniden üretim doğrulaması başarısız."""
