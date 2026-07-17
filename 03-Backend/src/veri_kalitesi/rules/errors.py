"""Kural yönetimi domain hata tipleri."""


class RuleError(Exception):
    """Kural yönetimi modülü için temel hata."""


class RuleValidationError(RuleError):
    """Kural tanımı veya iş kuralı doğrulaması başarısız oldu."""


class RuleAuthorizationError(RuleError):
    """Kural yonetimi yetkilendirme karari islemi reddetti."""


class RuleNotFoundError(RuleError):
    """İstenen kural nesnesi bulunamadı."""


class RuleTestTechnicalError(RuleError):
    """Kural testi yürütücüsünün sınıflandırılmış teknik hatası."""

    def __init__(self, error_class: str) -> None:
        super().__init__(error_class)
        self.error_class = error_class
