"""Raporlama hata turleri."""


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
    """Rapor istegi veya politikasi gecersiz."""


class ReportNotFoundError(ReportingError):
    """Rapor kaydi bulunamadi."""

    def __init__(self, report_id: str) -> None:
        super().__init__(f"Report {report_id} not found.")
        self.report_id = report_id


class ReportExpiredError(ReportingError):
    """Rapor indirme suresi dolmus."""

    def __init__(self, report_id: str) -> None:
        super().__init__(f"Report {report_id} has expired.")
        self.report_id = report_id


class ReportExportDeniedError(ReportingError):
    """Rapor disa aktarma politikasi tarafindan reddedildi."""

    def __init__(self, reason_code: str, correlation_id: str) -> None:
        super().__init__("Report export denied by policy.")
        self.reason_code = reason_code
        self.correlation_id = correlation_id


class ReportNotReadyError(ReportingError):
    """Rapor henuz hazir degil."""

    def __init__(self, report_id: str, status: str) -> None:
        super().__init__(f"Report {report_id} is not ready (status={status}).")
        self.report_id = report_id
        self.status = status


class ReportExportPolicyNotFoundError(ReportingError):
    """Rapor politikasi bulunamadi — fail-closed."""

    def __init__(self, sensitivity_level: str | None) -> None:
        super().__init__(f"No export policy for sensitivity={sensitivity_level}.")
        self.sensitivity_level = sensitivity_level


class ReportRetryableError(ReportingError):
    """Worker'in yeniden deneyebilecegi gecici hata.

    Ornekler: gecici dosya sistemi hatasi, baglanti zaman asimi,
    gecici kaynak yetersizligi.
    """

    def __init__(self, message: str, correlation_id: str = "") -> None:
        super().__init__(message)
        self.correlation_id = correlation_id
