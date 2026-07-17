"""Veri kaynağı domain hata tipleri."""


class DataSourceError(Exception):
    """Veri kaynağı modülü için temel hata."""


class ValidationError(DataSourceError):
    """Kullanıcı girdisi veya iş kuralı doğrulaması başarısız oldu."""


class NotFoundError(DataSourceError):
    """İstenen domain nesnesi bulunamadı."""


class TechnicalError(DataSourceError):
    """Beklenmeyen teknik hata oluştu."""


class SecretResolutionError(DataSourceError):
    """Secret referansı güvenli depodan çözülemedi."""
