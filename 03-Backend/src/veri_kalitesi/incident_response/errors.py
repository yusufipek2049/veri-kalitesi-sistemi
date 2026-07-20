"""Incident response domain error types."""


class IncidentResponseError(Exception):
    """Base incident response error."""


class IncidentValidationError(IncidentResponseError):
    """Incident response input or state is invalid."""


class IncidentAuthorizationError(IncidentResponseError):
    """The actor cannot perform the requested incident operation."""

    def __init__(self, reason_code: str, correlation_id: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code
        self.correlation_id = correlation_id


class IncidentNotFoundError(IncidentResponseError):
    """The requested incident record does not exist."""


class IncidentConflictError(IncidentResponseError):
    """An immutable incident record already exists."""


class IncidentTechnicalError(IncidentResponseError):
    """Incident processing failed for a technical reason."""

    def __init__(self, correlation_id: str) -> None:
        super().__init__("Incident response processing failed.")
        self.correlation_id = correlation_id
