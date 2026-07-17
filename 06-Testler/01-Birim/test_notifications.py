from __future__ import annotations

from datetime import datetime, timedelta, timezone
import sqlite3

import pytest

from veri_kalitesi.audit import (
    AuditRedactionPolicy,
    AuditRedactor,
    SQLiteAuditRepository,
    SQLiteTransactionalAudit,
)
from veri_kalitesi.identity import ActorContext, ActorContextIssuer, ActorType
from veri_kalitesi.notifications import (
    Notification,
    NotificationAccessPolicy,
    NotificationAuthorizationError,
    NotificationConflictError,
    NotificationEvent,
    NotificationEventType,
    NotificationNotFoundError,
    NotificationRecipientError,
    NotificationScopeType,
    NotificationService,
    NotificationStatus,
    NotificationTechnicalError,
    NotificationValidationError,
    SQLiteNotificationRepository,
)


NOW = datetime(2026, 7, 17, 12, 0, tzinfo=timezone.utc)
ACTOR_POLICY_VERSION = "BANK_NOTIFICATION_ACTOR_V1"
RECIPIENT_ID = "11111111-1111-4111-8111-111111111111"
OTHER_RECIPIENT_ID = "22222222-2222-4222-8222-222222222222"
SCOPE_ID = "33333333-3333-4333-8333-333333333333"
OTHER_SCOPE_ID = "44444444-4444-4444-8444-444444444444"


def test_fr_059_ac_015_creates_data_minimum_unread_notification_within_five_minutes() -> None:
    service, repository, audit_repository, resolver = _service((RECIPIENT_ID, RECIPIENT_ID))
    event = _event(NotificationEventType.QUALITY_THRESHOLD)

    notifications = _create(service, event)

    assert len(notifications) == 1
    notification = notifications[0]
    assert notification.recipient_user_id == RECIPIENT_ID
    assert notification.status is NotificationStatus.UNREAD
    assert notification.created_at - event.occurred_at <= timedelta(minutes=5)
    assert notification.title == "Data quality threshold alert"
    assert SCOPE_ID not in notification.title + notification.body
    assert notification.deduplication_key_digest != event.deduplication_key
    assert repository.count() == 1
    assert resolver.calls == 1
    audit_event = audit_repository.list_events()[-1]
    assert audit_event.action == "NOTIFICATION_CREATED"
    assert audit_event.actor_id == "55555555-5555-4555-8555-555555555555"
    assert audit_event.actor_type == ActorType.SERVICE.value
    assert audit_event.session_id_digest is not None
    assert "scope_id" not in audit_event.new_value_summary
    assert "deduplication_key" not in audit_event.new_value_summary


def test_fr_060_technical_error_is_distinct_from_quality_notification() -> None:
    service, _, _, _ = _service((RECIPIENT_ID,))

    quality = _create(service, _event(NotificationEventType.CRITICAL_RULE_FAILURE))[0]
    technical = _create(
        service,
        _event(
            NotificationEventType.TECHNICAL_ERROR,
            scope_type=NotificationScopeType.EXECUTION,
            deduplication_key="TECHNICAL.EVENT.1",
        ),
    )[0]

    assert quality.event_type is NotificationEventType.CRITICAL_RULE_FAILURE
    assert technical.event_type is NotificationEventType.TECHNICAL_ERROR
    assert quality.title != technical.title
    assert "Technical" in technical.title


def test_fr_063_rule_011_ac_016_repeated_event_updates_single_notification() -> None:
    service, repository, _, _ = _service((RECIPIENT_ID,))
    first = _event(NotificationEventType.QUALITY_THRESHOLD)
    second = _event(NotificationEventType.QUALITY_THRESHOLD)

    first_notification = _create(service, first)[0]
    repeated_notification = _create(service, second)[0]

    assert repeated_notification.notification_id == first_notification.notification_id
    assert repeated_notification.occurrence_count == 2
    assert repeated_notification.last_seen_at == NOW
    assert repository.count() == 1


def test_rule_011_same_key_with_different_payload_is_conflict() -> None:
    service, repository, _, _ = _service((RECIPIENT_ID,))
    _create(service, _event(NotificationEventType.QUALITY_THRESHOLD))

    with pytest.raises(NotificationConflictError):
        _create(service, _event(NotificationEventType.QUALITY_THRESHOLD, scope_id=OTHER_SCOPE_ID))

    assert repository.count() == 1


def test_uc_012_missing_trusted_recipient_is_configuration_failure() -> None:
    service, repository, _, _ = _service(())

    with pytest.raises(NotificationRecipientError):
        _create(service, _event(NotificationEventType.QUALITY_THRESHOLD))

    assert repository.count() == 0


def test_uc_012_recipient_resolver_failure_is_redacted_technical_error() -> None:
    resolver = StaticRecipientResolver(error=OSError("owner database password=unsafe"))
    service, repository, _, _ = _service((), resolver=resolver)

    with pytest.raises(NotificationTechnicalError) as error:
        _create(service, _event(NotificationEventType.QUALITY_THRESHOLD))

    assert error.value.correlation_id == "correlation-notification"
    assert "password" not in str(error.value)
    assert repository.count() == 0


def test_rule_009_sensitive_deduplication_key_is_rejected_before_resolution() -> None:
    service, repository, _, resolver = _service((RECIPIENT_ID,))
    event = _event(
        NotificationEventType.QUALITY_THRESHOLD,
        deduplication_key="secret.reference",
    )

    with pytest.raises(NotificationValidationError, match="forbidden"):
        _create(service, event)

    assert resolver.calls == 0
    assert repository.count() == 0


def test_nfr_rel_006_audit_stage_failure_rolls_back_notification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, repository, _, _ = _service((RECIPIENT_ID,))

    def fail_stage(*args: object) -> None:
        raise sqlite3.OperationalError("audit outbox unavailable")

    monkeypatch.setattr(service.transactional_audit, "stage", fail_stage)

    with pytest.raises(NotificationTechnicalError):
        _create(service, _event(NotificationEventType.QUALITY_THRESHOLD))

    assert repository.count() == 0
    assert service.transactional_audit.list_pending() == []


def test_uc_012_recipient_can_list_and_mark_notification_read() -> None:
    service, _, audit_repository, _ = _service((RECIPIENT_ID,))
    notification = _create(service, _event(NotificationEventType.QUALITY_THRESHOLD))[0]
    context = _context(RECIPIENT_ID)

    listed = service.list_my_notifications(context)
    read = service.mark_read(notification.notification_id, context)
    read_again = service.mark_read(notification.notification_id, context)

    assert listed[0].notification_id == notification.notification_id
    assert read.status is NotificationStatus.READ
    assert read.read_at == NOW
    assert read_again == read
    read_events = [
        event for event in audit_repository.list_events() if event.action == "NOTIFICATION_READ"
    ]
    assert len(read_events) == 1
    assert read_events[0].session_id_digest is not None
    assert "synthetic-session" not in str(read_events[0].new_value_summary)


def test_bfr_iam_002_other_recipient_cannot_discover_or_read_notification() -> None:
    service, _, _, _ = _service((RECIPIENT_ID,))
    notification = _create(service, _event(NotificationEventType.QUALITY_THRESHOLD))[0]

    with pytest.raises(NotificationNotFoundError):
        service.mark_read(notification.notification_id, _context(OTHER_RECIPIENT_ID))

    assert service.list_my_notifications(_context(OTHER_RECIPIENT_ID)) == ()


@pytest.mark.parametrize(
    "context_kind",
    [
        "untrusted",
        "expired",
        "service",
        "privileged",
    ],
)
def test_bfr_iam_001_untrusted_expired_service_and_privileged_access_is_denied(
    context_kind: str,
) -> None:
    service, _, _, _ = _service((RECIPIENT_ID,))
    contexts = {
        "untrusted": None,
        "expired": _context(RECIPIENT_ID, expires_at=NOW),
        "service": _context(RECIPIENT_ID, actor_type=ActorType.SERVICE),
        "privileged": _context(RECIPIENT_ID, privileged=True),
    }

    with pytest.raises(NotificationAuthorizationError):
        service.list_my_notifications(contexts[context_kind])


@pytest.mark.parametrize("context", [None, pytest.param("user", id="user-context")])
def test_bfr_iam_001_notification_producer_requires_trusted_service_context(
    context: str | None,
) -> None:
    service, repository, _, resolver = _service((RECIPIENT_ID,))
    actor_context = None if context is None else _context(RECIPIENT_ID)

    with pytest.raises(NotificationAuthorizationError):
        service.create_for_event(
            _event(NotificationEventType.QUALITY_THRESHOLD),
            actor_context,
        )

    assert resolver.calls == 0
    assert repository.count() == 0


def test_uc_012_closed_repository_is_redacted_technical_failure() -> None:
    service, repository, _, _ = _service((RECIPIENT_ID,))
    repository.connection.close()

    with pytest.raises(NotificationTechnicalError) as error:
        _create(service, _event(NotificationEventType.QUALITY_THRESHOLD))

    assert error.value.correlation_id == "correlation-notification"
    assert "closed database" not in str(error.value)


class StaticRecipientResolver:
    def __init__(
        self,
        recipient_ids: tuple[str, ...] = (),
        *,
        error: Exception | None = None,
    ) -> None:
        self.recipient_ids = recipient_ids
        self.error = error
        self.calls = 0

    def resolve_recipients(self, event: NotificationEvent) -> tuple[str, ...]:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.recipient_ids


def _service(
    recipient_ids: tuple[str, ...],
    *,
    resolver: StaticRecipientResolver | None = None,
) -> tuple[
    NotificationService,
    SQLiteNotificationRepository,
    SQLiteAuditRepository,
    StaticRecipientResolver,
]:
    repository = SQLiteNotificationRepository()
    audit_repository = SQLiteAuditRepository()
    redactor = AuditRedactor(
        AuditRedactionPolicy(
            version="NOTIFICATION_REDACTION_V1",
            allowed_fields_by_action={
                "NOTIFICATION_CREATED": frozenset({"event_type", "recipient_count", "status"}),
                "NOTIFICATION_READ": frozenset({"status"}),
            },
        )
    )
    transactional_audit = SQLiteTransactionalAudit(
        repository.connection,
        redactor,
        audit_repository,
        policy_version="NOTIFICATION_OUTBOX_V1",
    )
    actual_resolver = resolver or StaticRecipientResolver(recipient_ids)
    service = NotificationService(
        repository,
        actual_resolver,
        transactional_audit,
        NotificationAccessPolicy(
            version="NOTIFICATION_ACCESS_V1",
            actor_policy_version=ACTOR_POLICY_VERSION,
        ),
        clock=lambda: NOW,
    )
    return service, repository, audit_repository, actual_resolver


def _event(
    event_type: NotificationEventType,
    *,
    scope_type: NotificationScopeType = NotificationScopeType.DATASET,
    scope_id: str = SCOPE_ID,
    deduplication_key: str = "QUALITY.EVENT.1",
) -> NotificationEvent:
    return NotificationEvent(
        event_type=event_type,
        scope_type=scope_type,
        scope_id=scope_id,
        deduplication_key=deduplication_key,
        occurred_at=NOW - timedelta(minutes=1),
        correlation_id="correlation-notification",
    )


def _create(
    service: NotificationService,
    event: NotificationEvent,
) -> tuple[Notification, ...]:
    return service.create_for_event(event, _producer_context())


def _context(
    actor_id: str,
    *,
    actor_type: ActorType = ActorType.USER,
    expires_at: datetime = NOW + timedelta(hours=1),
    privileged: bool = False,
) -> ActorContext:
    return ActorContextIssuer().issue(
        actor_id=actor_id,
        actor_type=actor_type,
        authentication_source="synthetic-adapter",
        session_id="synthetic-session",
        roles=frozenset({"DATA_VIEWER"}),
        permitted_source_ids=frozenset(),
        permitted_dataset_ids=frozenset(),
        can_view_enterprise=False,
        privileged=privileged,
        issued_at=NOW - timedelta(minutes=5),
        expires_at=expires_at,
        policy_version=ACTOR_POLICY_VERSION,
        correlation_id="correlation-notification-reader",
    )


def _producer_context() -> ActorContext:
    return ActorContextIssuer().issue(
        actor_id="55555555-5555-4555-8555-555555555555",
        actor_type=ActorType.SERVICE,
        authentication_source="synthetic-service-adapter",
        session_id="synthetic-service-session",
        roles=frozenset({"NOTIFICATION_PRODUCER"}),
        permitted_source_ids=frozenset(),
        permitted_dataset_ids=frozenset(),
        can_view_enterprise=False,
        privileged=False,
        issued_at=NOW - timedelta(minutes=5),
        expires_at=NOW + timedelta(hours=1),
        policy_version=ACTOR_POLICY_VERSION,
        correlation_id="correlation-notification-producer",
    )
