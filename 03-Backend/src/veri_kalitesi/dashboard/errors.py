"""Dashboard okuma katmani hata turleri."""


class DashboardError(Exception):
    """Dashboard domain hatalarinin taban sinifi."""


class DashboardValidationError(DashboardError):
    """Dashboard sorgu girdisi gecersiz."""


class DashboardAuthorizationError(DashboardError):
    """Istenen dashboard kapsami kullanici yetkisinin disinda."""

    def __init__(self, message: str, correlation_id: str) -> None:
        super().__init__(message)
        self.correlation_id = correlation_id


class DashboardNotFoundError(DashboardError):
    """Yetkili kapsamdaki dashboard nesnesi bulunamadi."""


class DashboardQueryError(DashboardError):
    """Dashboard deposu sorguyu teknik nedenle tamamlayamadi."""

    def __init__(self, message: str, correlation_id: str) -> None:
        super().__init__(message)
        self.correlation_id = correlation_id
