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
