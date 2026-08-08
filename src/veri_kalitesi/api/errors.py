"""HTTP API sınırındaki güvenli hata türleri."""


class ApiError(Exception):
    """API taşıma katmanı hatalarının taban sınıfı."""

    def __init__(self, message: str, correlation_id: str) -> None:
        super().__init__(message)
        self.correlation_id = correlation_id


class ApiAuthenticationError(ApiError):
    """Güvenilir oturum bağlamı üretilemedi."""


class ApiCsrfError(ApiError):
    """Durum değiştiren istek güvenilir CSRF kanıtı üretemedi."""


class ApiConfigurationError(ApiError):
    """API güvenli biçimde başlatılamadı."""


class ApiSessionUnavailableError(ApiError):
    """Oturum sınırı teknik olarak kullanılamıyor."""
