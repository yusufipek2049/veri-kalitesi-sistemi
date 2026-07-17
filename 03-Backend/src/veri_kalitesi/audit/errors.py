"""Merkezi audit siniri hata turleri."""


class AuditError(Exception):
    """Audit hatalarinin taban sinifi."""


class AuditValidationError(AuditError):
    """Audit olay girdisi veya politika gecersiz."""


class AuditWriteError(AuditError):
    """Audit olayi politika geregi guvenli bicimde yazilamadi."""


class AuditMigrationTechnicalError(AuditError):
    """Legacy audit aktarimi teknik altyapi hatasi nedeniyle tamamlanamadi."""
