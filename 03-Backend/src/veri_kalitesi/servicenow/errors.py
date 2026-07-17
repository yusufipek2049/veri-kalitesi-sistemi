"""ServiceNow integration error types."""

from enum import Enum


class ServiceNowError(Exception):
    """Base ServiceNow integration error."""


class ServiceNowValidationError(ServiceNowError):
    """ServiceNow command or trusted projection is invalid."""


class ServiceNowAuthorizationError(ServiceNowError):
    """The actor cannot create a ServiceNow ticket."""


class ServiceNowPolicyError(ServiceNowError):
    """The issue is not eligible under the configured export policy."""


class ServiceNowConflictError(ServiceNowError):
    """An idempotency key or issue was reused with a different payload."""


class ServiceNowAdapterErrorKind(str, Enum):
    AUTHENTICATION = "AUTHENTICATION"
    RATE_LIMIT = "RATE_LIMIT"
    TEMPORARY = "TEMPORARY"
    PERMANENT = "PERMANENT"
    UNKNOWN = "UNKNOWN"


class ServiceNowAdapterError(ServiceNowError):
    """A classified failure returned by the external adapter."""

    def __init__(
        self,
        error_kind: ServiceNowAdapterErrorKind,
        *,
        retry_after_seconds: int | None = None,
    ) -> None:
        super().__init__(error_kind.value)
        self.error_kind = error_kind
        self.retry_after_seconds = retry_after_seconds


class ServiceNowTechnicalError(ServiceNowError):
    """ServiceNow processing failed for a technical reason."""

    def __init__(
        self,
        message: str,
        correlation_id: str,
        error_kind: ServiceNowAdapterErrorKind = ServiceNowAdapterErrorKind.UNKNOWN,
        *,
        attempt_count: int = 1,
        retry_job_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.correlation_id = correlation_id
        self.error_kind = error_kind
        self.attempt_count = attempt_count
        self.retry_job_id = retry_job_id
