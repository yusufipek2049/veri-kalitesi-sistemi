"""Skorlama domain hata tipleri."""


class ScoringError(Exception):
    """Skorlama modülü için temel hata."""


class ScoringValidationError(ScoringError):
    """Skor girdisi veya durum geçişi geçersiz."""


class ScoringAuthorizationError(ScoringError):
    """Skorlama yonetimi yetkilendirme karari islemi reddetti."""


class ScoreNotFoundError(ScoringError):
    """İstenen skor kaydı bulunamadı."""
