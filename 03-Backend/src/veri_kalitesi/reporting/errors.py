"""Rapor onizleme siniri hata turleri."""


class ReportingError(Exception):
    """Raporlama hatalarinin taban sinifi."""


class ReportAuthorizationError(ReportingError):
    """Rapor onizleme yetkisi varsayilan olarak reddedildi."""

    def __init__(self, reason_code: str, correlation_id: str) -> None:
        super().__init__("Report preview authorization denied.")
        self.reason_code = reason_code
        self.correlation_id = correlation_id


class ReportTechnicalError(ReportingError):
    """Rapor onizleme altyapisi guvenli sonuc uretemedi."""

    def __init__(self, correlation_id: str) -> None:
        super().__init__("Report preview could not be completed.")
        self.correlation_id = correlation_id


class ReportValidationError(ReportingError):
    """Rapor onizleme istegi veya politikasi gecersiz."""
