"""In-app notification domain package."""

from veri_kalitesi.notifications.errors import (
    NotificationAuthorizationError,
    NotificationConflictError,
    NotificationError,
    NotificationNotFoundError,
    NotificationRecipientError,
    NotificationTechnicalError,
    NotificationValidationError,
)
from veri_kalitesi.notifications.models import (
    Notification,
    NotificationAccessPolicy,
    NotificationEvent,
    NotificationEventType,
    NotificationScopeType,
    NotificationStatus,
)
from veri_kalitesi.notifications.repository import SQLiteNotificationRepository
from veri_kalitesi.notifications.service import NotificationRecipientResolver, NotificationService

__all__ = [
    "Notification",
    "NotificationAccessPolicy",
    "NotificationAuthorizationError",
    "NotificationConflictError",
    "NotificationError",
    "NotificationEvent",
    "NotificationEventType",
    "NotificationNotFoundError",
    "NotificationRecipientError",
    "NotificationRecipientResolver",
    "NotificationScopeType",
    "NotificationService",
    "NotificationStatus",
    "NotificationTechnicalError",
    "NotificationValidationError",
    "SQLiteNotificationRepository",
]
