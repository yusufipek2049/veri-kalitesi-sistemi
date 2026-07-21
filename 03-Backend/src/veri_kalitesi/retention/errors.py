"""Retention lifecycle domain errors."""


class RetentionError(Exception):
    """Base retention lifecycle error."""


class RetentionValidationError(RetentionError):
    """Retention input or policy data is invalid."""


class RetentionAuthorizationError(RetentionError):
    """The trusted actor is not authorized for the retention operation."""


class RetentionConflictError(RetentionError):
    """The requested retention transition conflicts with stored history."""


class RetentionNotFoundError(RetentionError):
    """The requested retention record does not exist."""


class RetentionTechnicalError(RetentionError):
    """Retention evaluation could not complete for a technical reason."""
