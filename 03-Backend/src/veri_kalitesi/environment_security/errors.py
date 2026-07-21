"""Ortam kimligi ve baslangic guvenlik kapisi hatalari."""


class EnvironmentSecurityError(Exception):
    """Ortam guvenligi temel hatasi."""


class EnvironmentConfigurationValidationError(EnvironmentSecurityError):
    """Ortam konfigurasyonu veya saglayici sozlesmesi gecersiz."""

    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


class EnvironmentPolicyBlockedError(EnvironmentSecurityError):
    """Ortam, veri veya secret sinifi politika tarafindan engellendi."""

    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


class EnvironmentConfigurationTechnicalError(EnvironmentSecurityError):
    """Guvenilir konfigurasyon kaynagi teknik nedenle okunamadi."""

    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code
