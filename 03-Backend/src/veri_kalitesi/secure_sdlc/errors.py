"""Safe error types for local secure SDLC checks."""


class SecretScanError(Exception):
    """Base local secret scan error."""


class SecretScanValidationError(SecretScanError):
    """The scan request or policy is invalid."""

    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


class SecretScanTechnicalError(SecretScanError):
    """A candidate file could not be inspected completely."""

    def __init__(self, operation_code: str, relative_path: str) -> None:
        super().__init__(operation_code)
        self.operation_code = operation_code
        self.relative_path = relative_path


class DependencyInventoryError(Exception):
    """Base dependency inventory error."""


class DependencyInventoryValidationError(DependencyInventoryError):
    """The declared project or dependency metadata is invalid."""

    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


class DependencyInventoryTechnicalError(DependencyInventoryError):
    """The dependency manifest could not be inspected completely."""

    def __init__(self, operation_code: str) -> None:
        super().__init__(operation_code)
        self.operation_code = operation_code


class SastGateError(Exception):
    """Base error for local SAST evidence and release gating."""


class SastGateValidationError(SastGateError):
    """The scanner envelope or release input is invalid."""

    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


class SastGateBlockedError(SastGateError):
    """A completed scan contains release-blocking findings."""

    def __init__(self, reason_code: str, blocking_finding_count: int) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code
        self.blocking_finding_count = blocking_finding_count


class SastGateTechnicalError(SastGateError):
    """The SAST scan did not complete and cannot produce release evidence."""

    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code
