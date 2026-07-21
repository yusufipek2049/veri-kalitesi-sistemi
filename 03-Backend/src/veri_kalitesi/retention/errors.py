"""Retention lifecycle domain errors."""


class RetentionError(Exception):
    """Base retention lifecycle error."""


class RetentionValidationError(RetentionError):
    """Retention input or policy data is invalid."""


class RetentionTechnicalError(RetentionError):
    """Retention evaluation could not complete for a technical reason."""
