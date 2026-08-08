"""Veri kaynağı domain hata tipleri."""


class DataSourceError(Exception):
    """Veri kaynağı modülü için güvenli, makine-okunur temel hata."""

    default_code = "DATA_SOURCE_ERROR"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code or self.default_code


class ValidationError(DataSourceError):
    """Kullanıcı girdisi veya iş kuralı doğrulaması başarısız oldu."""

    default_code = "DATA_SOURCE_DOMAIN_VALIDATION_FAILED"


class AuthorizationError(DataSourceError):
    """Güvenilir aktör bağlamı veri kaynağı işlemi için yetkili değil."""

    default_code = "DATA_SOURCE_PERMISSION_DENIED"


class NotFoundError(DataSourceError):
    """İstenen domain nesnesi bulunamadı."""

    default_code = "DATA_SOURCE_NOT_FOUND"


class ConflictError(ValidationError):
    """Komut mevcut state/revision ile güvenli biçimde tamamlanamaz."""

    default_code = "DATA_SOURCE_STATE_CONFLICT"


class TechnicalError(DataSourceError):
    """Beklenmeyen teknik hata oluştu."""

    default_code = "DATA_SOURCE_SERVICE_UNAVAILABLE"


class SecretResolutionError(DataSourceError):
    """Secret referansı güvenli depodan çözülemedi."""

    default_code = "DATA_SOURCE_SECRET_UNAVAILABLE"
