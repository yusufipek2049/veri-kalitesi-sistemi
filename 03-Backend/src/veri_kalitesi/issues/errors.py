"""Data quality issue domain error types."""


class IssueError(Exception):
    """Base issue domain error."""


class IssueValidationError(IssueError):
    """Issue input or state transition is invalid."""


class IssueAssignmentError(IssueError):
    """A trusted initial assignment could not be resolved."""


class IssueConflictError(IssueError):
    """An idempotency key was reused with a different payload."""


class IssueRelationshipError(IssueError):
    """A trusted predecessor cannot be linked to the new issue."""


class IssueAuthorizationError(IssueError):
    """The actor cannot perform the requested issue operation."""


class IssueNotFoundError(IssueError):
    """The requested issue does not exist in the actor scope."""


class IssueTechnicalError(IssueError):
    """Issue processing failed for a technical reason."""

    def __init__(self, message: str, correlation_id: str) -> None:
        super().__init__(message)
        self.correlation_id = correlation_id


class IssueNotificationError(IssueError):
    """The issue persisted but its notification could not be completed."""

    def __init__(self, message: str, issue_id: str, correlation_id: str) -> None:
        super().__init__(message)
        self.issue_id = issue_id
        self.correlation_id = correlation_id


class IssueNotificationTechnicalError(IssueNotificationError):
    """The persisted issue notification failed technically."""


class IssueNotificationConfigurationError(IssueNotificationError):
    """The persisted issue notification failed policy/configuration validation."""
