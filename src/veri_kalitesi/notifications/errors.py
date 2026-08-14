"""Notification domain error types."""


class NotificationError(Exception):
    """Base notification domain error."""


class NotificationValidationError(NotificationError):
    """Notification input or state transition is invalid."""


class NotificationRecipientError(NotificationError):
    """A trusted recipient could not be resolved."""


class NotificationConflictError(NotificationError):
    """An idempotency key was reused with a different payload."""


class NotificationAuthorizationError(NotificationError):
    """The actor cannot access the requested notification."""


class NotificationNotFoundError(NotificationError):
    """The requested notification does not exist."""


class NotificationTechnicalError(NotificationError):
    """Notification processing failed for a technical reason."""

    def __init__(self, message: str, correlation_id: str) -> None:
        super().__init__(message)
        self.correlation_id = correlation_id


class NotificationDeliveryError(NotificationError):
    """Delivery state transition or attempt failed."""


class NotificationConfigurationError(NotificationError):
    """Channel or subscription configuration is invalid or unavailable."""


class NotificationTransportError(NotificationDeliveryError):
    """Bildirim taşıyıcısının güvenli, kalıcı hata sınıfı."""

    def __init__(self, error_class: str) -> None:
        super().__init__(error_class)
        self.error_class = error_class


class TemporaryNotificationTransportError(NotificationTransportError):
    """Yeniden denenebilen bağlantı, zaman aşımı veya uzak servis hatası."""


class PermanentNotificationTransportError(NotificationTransportError):
    """Yeniden denemeyle düzelmeyecek hedef veya yapılandırma hatası."""


class UnsupportedNotificationChannelError(PermanentNotificationTransportError):
    """Kayıtlı bir adaptörü olmayan kanal tipi."""
