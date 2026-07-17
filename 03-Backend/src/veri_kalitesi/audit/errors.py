"""Merkezi audit siniri hata turleri."""


class AuditError(Exception):
    """Audit hatalarinin taban sinifi."""


class AuditValidationError(AuditError):
    """Audit olay girdisi veya politika gecersiz."""


class AuditWriteError(AuditError):
    """Audit olayi politika geregi guvenli bicimde yazilamadi."""


class AuditMigrationTechnicalError(AuditError):
    """Legacy audit aktarimi teknik altyapi hatasi nedeniyle tamamlanamadi."""


class AuditQueryAuthorizationError(AuditError):
    """Audit inceleme yetkisi varsayilan olarak reddedildi."""

    def __init__(self, reason_code: str, correlation_id: str) -> None:
        super().__init__("Audit query authorization denied.")
        self.reason_code = reason_code
        self.correlation_id = correlation_id


class AuditQueryTechnicalError(AuditError):
    """Audit inceleme altyapisi guvenli sonuc uretemedi."""

    def __init__(self, correlation_id: str) -> None:
        super().__init__("Audit query could not be completed.")
        self.correlation_id = correlation_id


class AuditQueryValidationError(AuditError):
    """Audit inceleme filtresi veya politikasi gecersiz."""
