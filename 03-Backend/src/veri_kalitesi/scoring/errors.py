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
