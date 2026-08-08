"""In-app notification domain package."""

from veri_kalitesi.notifications.channel_adapters import (
    ChannelDeliveryResult,
    ChannelDeliveryStatus,
    ChannelKind,
    ChannelRoute,
    DispatchOutcome,
    FakeChannelAdapter,
    NotificationChannelAdapter,
    NotificationChannelDispatcher,
    NotificationChannelPolicy,
)
from veri_kalitesi.notifications.errors import (
    NotificationAuthorizationError,
    NotificationConflictError,
    NotificationConfigurationError,
    NotificationDeliveryError,
    NotificationError,
    NotificationNotFoundError,
    NotificationRecipientError,
    NotificationTechnicalError,
    NotificationValidationError,
)
from veri_kalitesi.notifications.models import (
    MANDATORY_EVENT_TYPES,
    Notification,
    NotificationAccessPolicy,
    NotificationChannel,
    NotificationChannelStatus,
    NotificationDelivery,
    NotificationDeliveryStatus,
    NotificationEvent,
    NotificationEventType,
    NotificationScopeType,
    NotificationStatus,
    NotificationSubscription,
    NotificationSubscriptionStatus,
    validate_access_policy,
    validate_delivery_transition,
    validate_notification_event,
    validate_payload_safety,
    validate_recipient_id,
)
from veri_kalitesi.notifications.batch_stager import DefaultNotificationBatchStager
from veri_kalitesi.notifications.contracts import (
    NotificationBatchStager,
    NotificationRepository,
    PreparedNotificationBatch,
)
from veri_kalitesi.notifications.delivery_service import (
    DefaultInAppAdapter,
    DeliveryAttemptResult,
    NotificationDeliveryService,
)
from veri_kalitesi.notifications.jobs import (
    NotificationDeliveryJobEnqueuer,
    NotificationDeliveryJobHandler,
    NotificationDeliveryJobPayload,
)
from veri_kalitesi.notifications.postgresql_repository import (
    PostgreSQLNotificationRepository,
    notification_tables,
)
from veri_kalitesi.notifications.query_service import (
    InboxPage,
    NotificationQueryService,
)
from veri_kalitesi.notifications.repository import SQLiteNotificationRepository
from veri_kalitesi.notifications.service import (
    NotificationRecipientResolver,
    NotificationService,
)

__all__ = [
    "ChannelDeliveryResult",
    "ChannelDeliveryStatus",
    "ChannelKind",
    "ChannelRoute",
    "DefaultInAppAdapter",
    "DefaultNotificationBatchStager",
    "DeliveryAttemptResult",
    "DispatchOutcome",
    "FakeChannelAdapter",
    "InboxPage",
    "MANDATORY_EVENT_TYPES",
    "Notification",
    "NotificationAccessPolicy",
    "NotificationAuthorizationError",
    "NotificationBatchStager",
    "NotificationChannel",
    "NotificationChannelAdapter",
    "NotificationChannelDispatcher",
    "NotificationChannelPolicy",
    "NotificationChannelStatus",
    "NotificationConflictError",
    "NotificationConfigurationError",
    "NotificationDelivery",
    "NotificationDeliveryError",
    "NotificationDeliveryJobEnqueuer",
    "NotificationDeliveryJobHandler",
    "NotificationDeliveryJobPayload",
    "NotificationDeliveryService",
    "NotificationDeliveryStatus",
    "NotificationError",
    "NotificationEvent",
    "NotificationEventType",
    "NotificationNotFoundError",
    "NotificationQueryService",
    "NotificationRecipientError",
    "NotificationRecipientResolver",
    "NotificationRepository",
    "NotificationScopeType",
    "NotificationService",
    "NotificationStatus",
    "NotificationSubscription",
    "NotificationSubscriptionStatus",
    "NotificationTechnicalError",
    "NotificationValidationError",
    "PostgreSQLNotificationRepository",
    "PreparedNotificationBatch",
    "SQLiteNotificationRepository",
    "notification_tables",
    "validate_access_policy",
    "validate_delivery_transition",
    "validate_notification_event",
    "validate_payload_safety",
    "validate_recipient_id",
]
