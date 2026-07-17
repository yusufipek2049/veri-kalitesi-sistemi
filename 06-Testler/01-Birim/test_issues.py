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
from veri_kalitesi.issues import (
    DataQualityIssue,
    IssueAccessPolicy,
    IssueAssignment,
    IssueAssignmentError,
    IssueAssigneeProfile,
    IssueAuthorizationError,
    IssueConflictError,
    IssueNotificationConfigurationError,
    IssueNotificationTechnicalError,
    IssueNotFoundError,
    IssuePriority,
    IssueResolutionDraft,
    IssueScopeType,
    IssueService,
    IssueSourceEventType,
    IssueStatus,
    IssueTechnicalError,
    IssueTrigger,
    IssueTriggerType,
    IssueValidationError,
    IssueVerificationOutcome,
    ProtectedIssueResolution,
    SQLiteIssueRepository,
    TrustedIssueVerificationResult,
)
from veri_kalitesi.notifications import (
    NotificationAccessPolicy,
    NotificationEvent,
    NotificationEventType,
    NotificationRecipientError,
    NotificationService,
    NotificationStatus,
    NotificationTechnicalError,
    SQLiteNotificationRepository,
)


NOW = datetime(2026, 7, 17, 15, 0, tzinfo=timezone.utc)
ACTOR_POLICY_VERSION = "BANK_ISSUE_ACTOR_V1"
ASSIGNEE_ID = "11111111-1111-4111-8111-111111111111"
OTHER_USER_ID = "22222222-2222-4222-8222-222222222222"
DATASET_ID = "33333333-3333-4333-8333-333333333333"
OTHER_DATASET_ID = "44444444-4444-4444-8444-444444444444"
SERVICE_ID = "55555555-5555-4555-8555-555555555555"
EVIDENCE_ID = "66666666-6666-4666-8666-666666666666"
VERIFICATION_REFERENCE_ID = "77777777-7777-4777-8777-777777777777"
EXECUTION_ID = "88888888-8888-4888-8888-888888888888"
SCORE_ID = "99999999-9999-4999-8999-999999999999"


def _verification_result(
    *,
    outcome: IssueVerificationOutcome = IssueVerificationOutcome.QUALITY_FAILED,
    score_id: str | None = SCORE_ID,
    scope_id: str = DATASET_ID,
) -> TrustedIssueVerificationResult:
    return TrustedIssueVerificationResult(
        verification_reference_id=VERIFICATION_REFERENCE_ID,
        execution_id=EXECUTION_ID,
        score_id=score_id,
        scope_type=IssueScopeType.DATASET,
        scope_id=scope_id,
        outcome=outcome,
        completed_at=NOW,
    )


def test_fr_064_fr_065_ac_015_creates_assigned_issue_and_notification_within_five_minutes() -> None:
    fixture = _fixture()
    trigger = _trigger(IssueTriggerType.QUALITY_THRESHOLD)

    issue = _create(fixture.service, trigger)

    assert issue.status is IssueStatus.ASSIGNED
    assert issue.priority is IssuePriority.CRITICAL
    assert issue.assignee_user_id == ASSIGNEE_ID
    assert issue.source_event_type is IssueSourceEventType.QUALITY
    assert issue.created_at - trigger.occurred_at <= timedelta(minutes=5)
    assert issue.deduplication_key_digest != trigger.deduplication_key
    assert fixture.repository.count() == 1
    assert fixture.assignment_resolver.calls == 1
    notifications = fixture.notification_repository.list_for_recipient(ASSIGNEE_ID)
    assert len(notifications) == 1
    assert notifications[0].status is NotificationStatus.UNREAD
    history = fixture.repository.list_history(issue.issue_id)
    assert [item.action for item in history] == ["ISSUE_CREATED_AND_ASSIGNED"]
    audit_event = fixture.issue_audit_repository.list_events()[-1]
    assert audit_event.actor_id == SERVICE_ID
    assert audit_event.actor_type == ActorType.SERVICE.value
    assert "assignee_user_id" not in audit_event.new_value_summary
    assert "scope_id" not in audit_event.new_value_summary
    assert "deduplication_key" not in audit_event.new_value_summary


def test_uc_011_technical_issue_and_notification_are_distinct_from_quality() -> None:
    fixture = _fixture()

    quality = _create(fixture.service, _trigger(IssueTriggerType.CRITICAL_RULE_FAILURE))
    technical = _create(
        fixture.service,
        _trigger(
            IssueTriggerType.TECHNICAL_ERROR,
            deduplication_key="TECHNICAL.ISSUE.1",
        ),
    )

    assert quality.source_event_type is IssueSourceEventType.QUALITY
    assert technical.source_event_type is IssueSourceEventType.TECHNICAL
    notifications = fixture.notification_repository.list_for_recipient(ASSIGNEE_ID)
    assert {item.event_type.value for item in notifications} == {
        "CRITICAL_RULE_FAILURE",
        "TECHNICAL_ERROR",
    }


def test_fr_064_rule_011_ac_016_repeated_trigger_updates_one_issue_and_notification() -> None:
    fixture = _fixture()
    first = _create(fixture.service, _trigger(IssueTriggerType.QUALITY_THRESHOLD))
    repeated = _create(fixture.service, _trigger(IssueTriggerType.QUALITY_THRESHOLD))

    assert repeated.issue_id == first.issue_id
    assert repeated.occurrence_count == 2
    assert fixture.repository.count() == 1
    assert [item.action for item in fixture.repository.list_history(first.issue_id)] == [
        "ISSUE_CREATED_AND_ASSIGNED",
        "ISSUE_REPEATED",
    ]
    notification = fixture.notification_repository.list_for_recipient(ASSIGNEE_ID)[0]
    assert notification.occurrence_count == 2


def test_rule_011_repeated_trigger_preserves_current_investigating_status() -> None:
    fixture = _fixture()
    issue = _create(fixture.service, _trigger(IssueTriggerType.QUALITY_THRESHOLD))
    fixture.service.start_investigation(
        issue.issue_id,
        _user_context(ASSIGNEE_ID, dataset_ids={DATASET_ID}),
    )

    repeated = _create(fixture.service, _trigger(IssueTriggerType.QUALITY_THRESHOLD))

    assert repeated.status is IssueStatus.INVESTIGATING
    repeated_history = fixture.repository.list_history(issue.issue_id)[-1]
    assert repeated_history.action == "ISSUE_REPEATED"
    assert repeated_history.old_status is IssueStatus.INVESTIGATING
    assert repeated_history.new_status is IssueStatus.INVESTIGATING


def test_nfr_rel_005_one_hundred_replays_keep_single_issue() -> None:
    fixture = _fixture()

    issues = [
        _create(fixture.service, _trigger(IssueTriggerType.QUALITY_THRESHOLD)) for _ in range(100)
    ]

    assert len({issue.issue_id for issue in issues}) == 1
    assert issues[-1].occurrence_count == 100
    assert fixture.repository.count() == 1
    assert len(fixture.repository.list_history(issues[-1].issue_id)) == 100
    notification = fixture.notification_repository.list_for_recipient(ASSIGNEE_ID)[0]
    assert notification.occurrence_count == 100


def test_rule_011_same_key_with_different_scope_is_conflict() -> None:
    fixture = _fixture()
    _create(fixture.service, _trigger(IssueTriggerType.QUALITY_THRESHOLD))

    with pytest.raises(IssueConflictError):
        _create(
            fixture.service,
            _trigger(IssueTriggerType.QUALITY_THRESHOLD, scope_id=OTHER_DATASET_ID),
        )

    assert fixture.repository.count() == 1


@pytest.mark.parametrize("context_kind", ["missing", "user", "privileged-service"])
def test_bfr_iam_001_issue_creation_requires_standard_trusted_service_context(
    context_kind: str,
) -> None:
    fixture = _fixture()
    contexts = {
        "missing": None,
        "user": _user_context(ASSIGNEE_ID),
        "privileged-service": _producer_context(privileged=True),
    }

    with pytest.raises(IssueAuthorizationError):
        fixture.service.create_for_trigger(
            _trigger(IssueTriggerType.QUALITY_THRESHOLD),
            contexts[context_kind],
        )

    assert fixture.assignment_resolver.calls == 0
    assert fixture.repository.count() == 0


def test_uc_011_missing_assignment_is_configuration_failure() -> None:
    fixture = _fixture(assignment=None)

    with pytest.raises(IssueAssignmentError):
        _create(fixture.service, _trigger(IssueTriggerType.QUALITY_THRESHOLD))

    assert fixture.repository.count() == 0


def test_uc_011_assignment_resolver_failure_is_redacted_technical_error() -> None:
    resolver = StaticAssignmentResolver(error=OSError("owner database password=unsafe"))
    fixture = _fixture(assignment_resolver=resolver)

    with pytest.raises(IssueTechnicalError) as error:
        _create(fixture.service, _trigger(IssueTriggerType.QUALITY_THRESHOLD))

    assert error.value.correlation_id == "correlation-issue"
    assert "password" not in str(error.value)
    assert fixture.repository.count() == 0


def test_nfr_rel_006_audit_stage_failure_rolls_back_issue_and_skips_notification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    publisher = CountingNotificationPublisher()
    fixture = _fixture(notification_publisher=publisher)

    def fail_stage(*args: object) -> None:
        raise sqlite3.OperationalError("audit outbox unavailable")

    monkeypatch.setattr(fixture.service.transactional_audit, "stage", fail_stage)

    with pytest.raises(IssueTechnicalError):
        _create(fixture.service, _trigger(IssueTriggerType.QUALITY_THRESHOLD))

    assert fixture.repository.count() == 0
    assert fixture.service.transactional_audit.list_pending() == []
    assert publisher.calls == 0


def test_uc_011_notification_technical_failure_preserves_committed_issue() -> None:
    publisher = CountingNotificationPublisher(
        error=NotificationTechnicalError("notification unavailable", "correlation-issue")
    )
    fixture = _fixture(notification_publisher=publisher)

    with pytest.raises(IssueNotificationTechnicalError) as error:
        _create(fixture.service, _trigger(IssueTriggerType.QUALITY_THRESHOLD))

    assert fixture.repository.get(error.value.issue_id).status is IssueStatus.ASSIGNED
    assert fixture.repository.count() == 1


def test_uc_011_unexpected_notification_failure_is_redacted_and_preserves_issue() -> None:
    publisher = CountingNotificationPublisher(error=RuntimeError("secret notification detail"))
    fixture = _fixture(notification_publisher=publisher)

    with pytest.raises(IssueNotificationTechnicalError) as error:
        _create(fixture.service, _trigger(IssueTriggerType.QUALITY_THRESHOLD))

    assert "secret" not in str(error.value)
    assert fixture.repository.get(error.value.issue_id).status is IssueStatus.ASSIGNED


def test_uc_011_notification_configuration_failure_preserves_committed_issue() -> None:
    publisher = CountingNotificationPublisher(
        error=NotificationRecipientError("recipient unavailable")
    )
    fixture = _fixture(notification_publisher=publisher)

    with pytest.raises(IssueNotificationConfigurationError) as error:
        _create(fixture.service, _trigger(IssueTriggerType.QUALITY_THRESHOLD))

    assert fixture.repository.get(error.value.issue_id).status is IssueStatus.ASSIGNED
    assert fixture.repository.count() == 1


def test_fr_066_uc_013_assignee_with_scope_starts_investigation_and_history() -> None:
    fixture = _fixture()
    issue = _create(fixture.service, _trigger(IssueTriggerType.QUALITY_THRESHOLD))

    investigating = fixture.service.start_investigation(
        issue.issue_id,
        _user_context(ASSIGNEE_ID, dataset_ids={DATASET_ID}),
    )

    assert investigating.status is IssueStatus.INVESTIGATING
    history = fixture.repository.list_history(issue.issue_id)
    assert [item.new_status for item in history] == [
        IssueStatus.ASSIGNED,
        IssueStatus.INVESTIGATING,
    ]
    audit_event = fixture.issue_audit_repository.list_events()[-1]
    assert audit_event.action == "DATA_QUALITY_ISSUE_STATUS_CHANGED"
    assert audit_event.old_value_summary == {"status": "ASSIGNED"}
    assert audit_event.new_value_summary == {"status": "INVESTIGATING"}


@pytest.mark.parametrize("context_kind", ["other-user", "missing-scope", "service", "privileged"])
def test_fr_066_unauthorized_actor_cannot_start_investigation(context_kind: str) -> None:
    fixture = _fixture()
    issue = _create(fixture.service, _trigger(IssueTriggerType.QUALITY_THRESHOLD))
    contexts = {
        "other-user": _user_context(OTHER_USER_ID, dataset_ids={DATASET_ID}),
        "missing-scope": _user_context(ASSIGNEE_ID),
        "service": _producer_context(),
        "privileged": _user_context(
            ASSIGNEE_ID,
            dataset_ids={DATASET_ID},
            privileged=True,
        ),
    }

    with pytest.raises(IssueAuthorizationError):
        fixture.service.start_investigation(issue.issue_id, contexts[context_kind])

    assert fixture.repository.get(issue.issue_id).status is IssueStatus.ASSIGNED
    assert len(fixture.repository.list_history(issue.issue_id)) == 1


def test_fr_066_repeated_investigation_transition_is_rejected() -> None:
    fixture = _fixture()
    issue = _create(fixture.service, _trigger(IssueTriggerType.QUALITY_THRESHOLD))
    context = _user_context(ASSIGNEE_ID, dataset_ids={DATASET_ID})
    fixture.service.start_investigation(issue.issue_id, context)

    with pytest.raises(IssueValidationError, match="assigned"):
        fixture.service.start_investigation(issue.issue_id, context)

    assert len(fixture.repository.list_history(issue.issue_id)) == 2


def test_bfr_data_003_sensitive_deduplication_key_is_rejected_before_assignment() -> None:
    fixture = _fixture()

    with pytest.raises(IssueValidationError, match="forbidden"):
        _create(
            fixture.service,
            _trigger(
                IssueTriggerType.QUALITY_THRESHOLD,
                deduplication_key="secret.issue.reference",
            ),
        )

    assert fixture.assignment_resolver.calls == 0
    assert fixture.repository.count() == 0


def test_uc_011_closed_repository_is_redacted_technical_failure() -> None:
    fixture = _fixture()
    fixture.repository.connection.close()

    with pytest.raises(IssueTechnicalError) as error:
        _create(fixture.service, _trigger(IssueTriggerType.QUALITY_THRESHOLD))

    assert error.value.correlation_id == "correlation-issue"
    assert "closed database" not in str(error.value)


def test_fr_066_sqlite_schema_rejects_unknown_issue_status() -> None:
    fixture = _fixture()
    issue = _create(fixture.service, _trigger(IssueTriggerType.QUALITY_THRESHOLD))

    with pytest.raises(sqlite3.IntegrityError):
        with fixture.repository.connection:
            fixture.repository.connection.execute(
                "UPDATE data_quality_issues SET status = 'UNKNOWN' WHERE issue_id = ?",
                (issue.issue_id,),
            )

    assert fixture.repository.get(issue.issue_id).status is IssueStatus.ASSIGNED


def test_fr_065_fr_070_uc_013_ac_017_authorized_steward_reassigns_with_history_audit_and_notification() -> (
    None
):
    fixture = _fixture()
    issue = _create(fixture.service, _trigger(IssueTriggerType.QUALITY_THRESHOLD))

    assigned = fixture.service.reassign(
        issue.issue_id,
        IssueAssignment(OTHER_USER_ID, IssuePriority.HIGH),
        _user_context(ASSIGNEE_ID, dataset_ids={DATASET_ID}),
    )

    assert assigned.status is IssueStatus.ASSIGNED
    assert assigned.assignee_user_id == OTHER_USER_ID
    assert assigned.priority is IssuePriority.HIGH
    history = fixture.repository.list_history(issue.issue_id)
    assert [item.action for item in history] == [
        "ISSUE_CREATED_AND_ASSIGNED",
        "ISSUE_REASSIGNED",
    ]
    assert history[-1].old_assignee_user_id == ASSIGNEE_ID
    assert history[-1].new_assignee_user_id == OTHER_USER_ID
    assert history[-1].old_priority is IssuePriority.CRITICAL
    assert history[-1].new_priority is IssuePriority.HIGH
    notifications = fixture.notification_repository.list_for_recipient(OTHER_USER_ID)
    assert len(notifications) == 1
    assert notifications[0].event_type is NotificationEventType.ISSUE_ASSIGNED
    audit_event = fixture.issue_audit_repository.list_events()[-1]
    assert audit_event.action == "DATA_QUALITY_ISSUE_ASSIGNED"
    assert audit_event.actor_id == ASSIGNEE_ID
    assert audit_event.old_value_summary == {"priority": "CRITICAL", "status": "ASSIGNED"}
    assert audit_event.new_value_summary == {"priority": "HIGH", "status": "ASSIGNED"}
    assert "assignee_user_id" not in audit_event.new_value_summary
    assert "scope_id" not in audit_event.new_value_summary


@pytest.mark.parametrize(
    "context_kind",
    ["missing", "service", "privileged", "role-escalation", "scope-manipulation"],
)
def test_fr_065_nfr_sec_001_unauthorized_actor_cannot_reassign(
    context_kind: str,
) -> None:
    fixture = _fixture()
    issue = _create(fixture.service, _trigger(IssueTriggerType.QUALITY_THRESHOLD))
    contexts = {
        "missing": None,
        "service": _producer_context(),
        "privileged": _user_context(ASSIGNEE_ID, dataset_ids={DATASET_ID}, privileged=True),
        "role-escalation": _user_context(ASSIGNEE_ID, dataset_ids={DATASET_ID}, roles={"VIEWER"}),
        "scope-manipulation": _user_context(ASSIGNEE_ID),
    }

    with pytest.raises(IssueAuthorizationError):
        fixture.service.reassign(
            issue.issue_id,
            IssueAssignment(OTHER_USER_ID, IssuePriority.HIGH),
            contexts[context_kind],
        )

    assert fixture.repository.get(issue.issue_id).assignee_user_id == ASSIGNEE_ID
    assert fixture.assignee_directory.calls == 0
    assert len(fixture.repository.list_history(issue.issue_id)) == 1


@pytest.mark.parametrize(
    "profile",
    [
        IssueAssigneeProfile(OTHER_USER_ID, False, frozenset(), frozenset({DATASET_ID})),
        IssueAssigneeProfile(OTHER_USER_ID, True, frozenset(), frozenset({OTHER_DATASET_ID})),
    ],
    ids=["inactive", "outside-scope"],
)
def test_fr_065_uc_013_inactive_or_outside_scope_assignee_is_rejected(
    profile: IssueAssigneeProfile,
) -> None:
    fixture = _fixture(assignee_profile=profile)
    issue = _create(fixture.service, _trigger(IssueTriggerType.QUALITY_THRESHOLD))

    with pytest.raises(IssueAssignmentError, match="inactive or outside"):
        fixture.service.reassign(
            issue.issue_id,
            IssueAssignment(OTHER_USER_ID, IssuePriority.HIGH),
            _user_context(ASSIGNEE_ID, dataset_ids={DATASET_ID}),
        )

    assert fixture.repository.get(issue.issue_id).assignee_user_id == ASSIGNEE_ID
    assert len(fixture.repository.list_history(issue.issue_id)) == 1


def test_fr_065_same_assignee_and_priority_is_rejected_without_history_or_notification() -> None:
    fixture = _fixture()
    issue = _create(fixture.service, _trigger(IssueTriggerType.QUALITY_THRESHOLD))

    with pytest.raises(IssueValidationError, match="must change"):
        fixture.service.reassign(
            issue.issue_id,
            IssueAssignment(ASSIGNEE_ID, IssuePriority.CRITICAL),
            _user_context(ASSIGNEE_ID, dataset_ids={DATASET_ID}),
        )

    assert len(fixture.repository.list_history(issue.issue_id)) == 1
    assert fixture.assignee_directory.calls == 0


def test_fr_065_assignee_directory_failure_is_redacted_technical_error() -> None:
    directory = StaticAssigneeDirectory(error=OSError("directory password=unsafe"))
    fixture = _fixture(assignee_directory=directory)
    issue = _create(fixture.service, _trigger(IssueTriggerType.QUALITY_THRESHOLD))

    with pytest.raises(IssueTechnicalError) as error:
        fixture.service.reassign(
            issue.issue_id,
            IssueAssignment(OTHER_USER_ID, IssuePriority.HIGH),
            _user_context(ASSIGNEE_ID, dataset_ids={DATASET_ID}),
        )

    assert "password" not in str(error.value)
    assert fixture.repository.get(issue.issue_id).assignee_user_id == ASSIGNEE_ID


def test_fr_065_nfr_rel_006_assignment_audit_failure_rolls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture()
    issue = _create(fixture.service, _trigger(IssueTriggerType.QUALITY_THRESHOLD))

    def fail_stage(*args: object) -> None:
        raise sqlite3.OperationalError("audit outbox unavailable")

    monkeypatch.setattr(fixture.service.transactional_audit, "stage", fail_stage)

    with pytest.raises(IssueTechnicalError):
        fixture.service.reassign(
            issue.issue_id,
            IssueAssignment(OTHER_USER_ID, IssuePriority.HIGH),
            _user_context(ASSIGNEE_ID, dataset_ids={DATASET_ID}),
        )

    stored = fixture.repository.get(issue.issue_id)
    assert stored.assignee_user_id == ASSIGNEE_ID
    assert stored.priority is IssuePriority.CRITICAL
    assert len(fixture.repository.list_history(issue.issue_id)) == 1


def test_uc_013_notification_failure_preserves_committed_assignment() -> None:
    fixture = _fixture()
    issue = _create(fixture.service, _trigger(IssueTriggerType.QUALITY_THRESHOLD))
    fixture.service.notification_publisher = CountingNotificationPublisher(
        error=NotificationTechnicalError("notification unavailable", "correlation-issue-user")
    )

    with pytest.raises(IssueNotificationTechnicalError) as error:
        fixture.service.reassign(
            issue.issue_id,
            IssueAssignment(OTHER_USER_ID, IssuePriority.HIGH),
            _user_context(ASSIGNEE_ID, dataset_ids={DATASET_ID}),
        )

    stored = fixture.repository.get(error.value.issue_id)
    assert stored.assignee_user_id == OTHER_USER_ID
    assert stored.priority is IssuePriority.HIGH
    assert fixture.repository.list_history(issue.issue_id)[-1].action == "ISSUE_REASSIGNED"


def test_fr_066_fr_068_fr_070_uc_014_assignee_records_protected_resolution() -> None:
    protected = ProtectedIssueResolution(
        root_cause="Invalid source mapping",
        corrective_action="Corrected mapping configuration",
        evidence_reference_id=EVIDENCE_ID,
        completed_at=NOW,
        protection_policy_version="ISSUE_TEXT_POLICY_V1",
    )
    fixture = _fixture(resolution_protector=StaticResolutionProtector(protected=protected))
    issue = _investigating_issue(fixture)

    resolved = fixture.service.resolve(
        issue.issue_id,
        IssueResolutionDraft(
            root_cause="<b>Invalid source mapping</b>",
            corrective_action="<p>Corrected mapping configuration</p>",
            evidence_reference_id=EVIDENCE_ID,
            completed_at=NOW,
        ),
        _user_context(ASSIGNEE_ID, dataset_ids={DATASET_ID}),
    )

    assert resolved.status is IssueStatus.RESOLVED
    resolution = fixture.repository.get_latest_resolution(issue.issue_id)
    assert resolution.root_cause == "Invalid source mapping"
    assert resolution.corrective_action == "Corrected mapping configuration"
    assert resolution.evidence_reference_id == EVIDENCE_ID
    assert resolution.protection_policy_version == "ISSUE_TEXT_POLICY_V1"
    history = fixture.repository.list_history(issue.issue_id)
    assert history[-1].action == "ISSUE_RESOLVED"
    assert history[-1].old_status is IssueStatus.INVESTIGATING
    assert history[-1].new_status is IssueStatus.RESOLVED
    assert history[-1].resolution_id == resolution.resolution_id
    audit_event = fixture.issue_audit_repository.list_events()[-1]
    assert audit_event.action == "DATA_QUALITY_ISSUE_RESOLVED"
    assert audit_event.old_value_summary == {"status": "INVESTIGATING"}
    assert audit_event.new_value_summary == {
        "protection_policy_version": "ISSUE_TEXT_POLICY_V1",
        "resolution_fields_complete": True,
        "status": "RESOLVED",
    }
    assert "root_cause" not in audit_event.new_value_summary
    assert "corrective_action" not in audit_event.new_value_summary
    assert "evidence_reference_id" not in audit_event.new_value_summary


@pytest.mark.parametrize(
    "draft",
    [
        IssueResolutionDraft("", "Corrected mapping", EVIDENCE_ID, NOW),
        IssueResolutionDraft("Invalid mapping", "", EVIDENCE_ID, NOW),
        IssueResolutionDraft("Invalid mapping", "Corrected mapping", "not-a-uuid", NOW),
        IssueResolutionDraft(
            "Invalid mapping",
            "Corrected mapping",
            EVIDENCE_ID,
            datetime(2026, 7, 17, 15, 0),
        ),
    ],
    ids=["missing-root-cause", "missing-action", "invalid-evidence", "naive-completion"],
)
def test_fr_068_uc_014_missing_or_invalid_resolution_fields_are_rejected(
    draft: IssueResolutionDraft,
) -> None:
    fixture = _fixture()
    issue = _investigating_issue(fixture)

    with pytest.raises(IssueValidationError):
        fixture.service.resolve(
            issue.issue_id,
            draft,
            _user_context(ASSIGNEE_ID, dataset_ids={DATASET_ID}),
        )

    assert fixture.repository.get(issue.issue_id).status is IssueStatus.INVESTIGATING
    assert fixture.resolution_protector.calls == 0


@pytest.mark.parametrize(
    "context_kind",
    ["missing", "other-user", "missing-scope", "service", "privileged", "role-escalation"],
)
def test_fr_066_nfr_sec_001_unauthorized_actor_cannot_resolve(context_kind: str) -> None:
    fixture = _fixture()
    issue = _investigating_issue(fixture)
    contexts = {
        "missing": None,
        "other-user": _user_context(OTHER_USER_ID, dataset_ids={DATASET_ID}),
        "missing-scope": _user_context(ASSIGNEE_ID),
        "service": _producer_context(),
        "privileged": _user_context(ASSIGNEE_ID, dataset_ids={DATASET_ID}, privileged=True),
        "role-escalation": _user_context(ASSIGNEE_ID, dataset_ids={DATASET_ID}, roles={"VIEWER"}),
    }

    with pytest.raises(IssueAuthorizationError):
        fixture.service.resolve(issue.issue_id, _resolution_draft(), contexts[context_kind])

    assert fixture.repository.get(issue.issue_id).status is IssueStatus.INVESTIGATING
    assert fixture.resolution_protector.calls == 0


def test_fr_066_uc_014_assigned_issue_cannot_skip_investigation_to_resolved() -> None:
    fixture = _fixture()
    issue = _create(fixture.service, _trigger(IssueTriggerType.QUALITY_THRESHOLD))

    with pytest.raises(IssueValidationError, match="investigating"):
        fixture.service.resolve(
            issue.issue_id,
            _resolution_draft(),
            _user_context(ASSIGNEE_ID, dataset_ids={DATASET_ID}),
        )

    assert fixture.repository.get(issue.issue_id).status is IssueStatus.ASSIGNED
    assert fixture.resolution_protector.calls == 0


@pytest.mark.parametrize(
    "completed_at",
    [NOW - timedelta(seconds=1), NOW + timedelta(seconds=1)],
    ids=["before-issue", "future"],
)
def test_fr_068_resolution_completion_must_be_within_issue_lifetime(
    completed_at: datetime,
) -> None:
    fixture = _fixture()
    issue = _investigating_issue(fixture)

    with pytest.raises(IssueValidationError, match="lifetime"):
        fixture.service.resolve(
            issue.issue_id,
            _resolution_draft(completed_at=completed_at),
            _user_context(ASSIGNEE_ID, dataset_ids={DATASET_ID}),
        )

    assert fixture.resolution_protector.calls == 0


@pytest.mark.parametrize(
    "protected",
    [
        ProtectedIssueResolution(
            "<b>unsafe</b>",
            "Corrected mapping",
            EVIDENCE_ID,
            NOW,
            "ISSUE_TEXT_POLICY_V1",
        ),
        ProtectedIssueResolution(
            "database password=unsafe",
            "Corrected mapping",
            EVIDENCE_ID,
            NOW,
            "ISSUE_TEXT_POLICY_V1",
        ),
    ],
    ids=["unsafe-markup", "sensitive-text"],
)
def test_bfr_data_003_unprotected_resolution_output_is_rejected(
    protected: ProtectedIssueResolution,
) -> None:
    fixture = _fixture(resolution_protector=StaticResolutionProtector(protected=protected))
    issue = _investigating_issue(fixture)

    with pytest.raises(IssueValidationError):
        fixture.service.resolve(
            issue.issue_id,
            _resolution_draft(),
            _user_context(ASSIGNEE_ID, dataset_ids={DATASET_ID}),
        )

    assert fixture.repository.get(issue.issue_id).status is IssueStatus.INVESTIGATING
    with pytest.raises(IssueNotFoundError):
        fixture.repository.get_latest_resolution(issue.issue_id)


def test_fr_068_resolution_protector_cannot_change_evidence_reference() -> None:
    protected = ProtectedIssueResolution(
        "Invalid mapping",
        "Corrected mapping",
        OTHER_DATASET_ID,
        NOW,
        "ISSUE_TEXT_POLICY_V1",
    )
    fixture = _fixture(resolution_protector=StaticResolutionProtector(protected=protected))
    issue = _investigating_issue(fixture)

    with pytest.raises(IssueValidationError, match="immutable"):
        fixture.service.resolve(
            issue.issue_id,
            _resolution_draft(),
            _user_context(ASSIGNEE_ID, dataset_ids={DATASET_ID}),
        )

    assert fixture.repository.get(issue.issue_id).status is IssueStatus.INVESTIGATING


def test_fr_068_resolution_protector_failure_is_redacted_technical_error() -> None:
    protector = StaticResolutionProtector(error=OSError("classifier token=unsafe"))
    fixture = _fixture(resolution_protector=protector)
    issue = _investigating_issue(fixture)

    with pytest.raises(IssueTechnicalError) as error:
        fixture.service.resolve(
            issue.issue_id,
            _resolution_draft(),
            _user_context(ASSIGNEE_ID, dataset_ids={DATASET_ID}),
        )

    assert "token" not in str(error.value)
    assert fixture.repository.get(issue.issue_id).status is IssueStatus.INVESTIGATING


def test_fr_068_nfr_rel_006_resolution_audit_failure_rolls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture()
    issue = _investigating_issue(fixture)

    def fail_stage(*args: object) -> None:
        raise sqlite3.OperationalError("audit outbox unavailable")

    monkeypatch.setattr(fixture.service.transactional_audit, "stage", fail_stage)

    with pytest.raises(IssueTechnicalError):
        fixture.service.resolve(
            issue.issue_id,
            _resolution_draft(),
            _user_context(ASSIGNEE_ID, dataset_ids={DATASET_ID}),
        )

    assert fixture.repository.get(issue.issue_id).status is IssueStatus.INVESTIGATING
    assert fixture.repository.list_history(issue.issue_id)[-1].action == (
        "ISSUE_INVESTIGATION_STARTED"
    )
    with pytest.raises(IssueNotFoundError):
        fixture.repository.get_latest_resolution(issue.issue_id)


@pytest.mark.parametrize(
    "outcome",
    [IssueVerificationOutcome.QUALITY_FAILED, IssueVerificationOutcome.PARTIAL],
)
def test_fr_066_fr_069_uc_014_ac_018_failed_verification_returns_issue_to_waiting(
    outcome: IssueVerificationOutcome,
) -> None:
    fixture = _fixture(verification_result=_verification_result(outcome=outcome))
    issue = _resolved_issue(fixture)

    waiting = fixture.service.record_verification_result(
        issue.issue_id,
        VERIFICATION_REFERENCE_ID,
        _user_context(OTHER_USER_ID, dataset_ids={DATASET_ID}),
    )

    assert waiting.status is IssueStatus.WAITING_FOR_RESOLUTION
    verification = fixture.repository.get_latest_verification(issue.issue_id)
    assert verification.execution_id == EXECUTION_ID
    assert verification.score_id == SCORE_ID
    assert verification.outcome is outcome
    history = fixture.repository.list_history(issue.issue_id)[-1]
    assert history.action == "ISSUE_VERIFICATION_FAILED"
    assert history.old_status is IssueStatus.RESOLVED
    assert history.new_status is IssueStatus.WAITING_FOR_RESOLUTION
    assert history.verification_id == verification.verification_id
    audit = fixture.issue_audit_repository.list_events()[-1]
    assert audit.action == "DATA_QUALITY_ISSUE_VERIFICATION_RECORDED"
    assert audit.old_value_summary == {"status": "RESOLVED"}
    assert audit.new_value_summary == {
        "has_score_reference": True,
        "status": "WAITING_FOR_RESOLUTION",
        "verification_outcome": outcome.value,
    }
    serialized_audit = repr(audit)
    assert EXECUTION_ID not in serialized_audit
    assert SCORE_ID not in serialized_audit
    assert DATASET_ID not in serialized_audit


def test_fr_066_fr_069_uc_014_successful_verification_moves_issue_to_verified() -> None:
    fixture = _fixture(
        verification_result=_verification_result(outcome=IssueVerificationOutcome.QUALITY_PASSED)
    )
    issue = _resolved_issue(fixture)

    verified = fixture.service.record_verification_result(
        issue.issue_id,
        VERIFICATION_REFERENCE_ID,
        _user_context(OTHER_USER_ID, dataset_ids={DATASET_ID}, roles={"DATA_OWNER"}),
    )

    assert verified.status is IssueStatus.VERIFIED
    verification = fixture.repository.get_latest_verification(issue.issue_id)
    assert verification.outcome is IssueVerificationOutcome.QUALITY_PASSED
    assert verification.score_id == SCORE_ID
    assert verification.recorded_by == OTHER_USER_ID
    history = fixture.repository.list_history(issue.issue_id)[-1]
    assert history.action == "ISSUE_VERIFIED"
    assert history.old_status is IssueStatus.RESOLVED
    assert history.new_status is IssueStatus.VERIFIED
    assert history.verification_id == verification.verification_id
    audit = fixture.issue_audit_repository.list_events()[-1]
    assert audit.action == "DATA_QUALITY_ISSUE_VERIFICATION_RECORDED"
    assert audit.reason_code == "QUALITY_PASSED"
    assert audit.old_value_summary == {"status": "RESOLVED"}
    assert audit.new_value_summary == {
        "has_score_reference": True,
        "status": "VERIFIED",
        "verification_outcome": "QUALITY_PASSED",
    }
    serialized_audit = repr(audit)
    assert EXECUTION_ID not in serialized_audit
    assert SCORE_ID not in serialized_audit
    assert DATASET_ID not in serialized_audit


def test_fr_069_rule_013_resolution_creator_cannot_verify_own_resolution() -> None:
    fixture = _fixture(
        verification_result=_verification_result(outcome=IssueVerificationOutcome.QUALITY_PASSED)
    )
    issue = _resolved_issue(fixture)

    with pytest.raises(IssueAuthorizationError, match="creator"):
        fixture.service.record_verification_result(
            issue.issue_id,
            VERIFICATION_REFERENCE_ID,
            _user_context(ASSIGNEE_ID, dataset_ids={DATASET_ID}),
        )

    assert fixture.repository.get(issue.issue_id).status is IssueStatus.RESOLVED
    assert fixture.verification_resolver.calls == 1
    with pytest.raises(IssueNotFoundError):
        fixture.repository.get_latest_verification(issue.issue_id)


def test_rule_003_uc_014_technical_verification_error_does_not_fail_quality() -> None:
    fixture = _fixture(
        verification_result=_verification_result(
            outcome=IssueVerificationOutcome.TECHNICAL_ERROR,
            score_id=None,
        )
    )
    issue = _resolved_issue(fixture)

    stored = fixture.service.record_verification_result(
        issue.issue_id,
        VERIFICATION_REFERENCE_ID,
        _user_context(OTHER_USER_ID, dataset_ids={DATASET_ID}, roles={"DATA_OWNER"}),
    )

    assert stored.status is IssueStatus.RESOLVED
    verification = fixture.repository.get_latest_verification(issue.issue_id)
    assert verification.outcome is IssueVerificationOutcome.TECHNICAL_ERROR
    assert verification.score_id is None
    history = fixture.repository.list_history(issue.issue_id)[-1]
    assert history.action == "ISSUE_VERIFICATION_TECHNICAL_ERROR"
    assert history.old_status is IssueStatus.RESOLVED
    assert history.new_status is IssueStatus.RESOLVED
    audit = fixture.issue_audit_repository.list_events()[-1]
    assert audit.reason_code == "TECHNICAL_ERROR"
    assert audit.new_value_summary["has_score_reference"] is False


@pytest.mark.parametrize(
    "context_kind",
    ["missing", "service", "privileged", "role-escalation", "scope-manipulation"],
)
def test_fr_069_nfr_sec_001_unauthorized_actor_cannot_record_verification(
    context_kind: str,
) -> None:
    fixture = _fixture()
    issue = _resolved_issue(fixture)
    contexts = {
        "missing": None,
        "service": _producer_context(),
        "privileged": _user_context(OTHER_USER_ID, dataset_ids={DATASET_ID}, privileged=True),
        "role-escalation": _user_context(OTHER_USER_ID, dataset_ids={DATASET_ID}, roles={"VIEWER"}),
        "scope-manipulation": _user_context(OTHER_USER_ID),
    }

    with pytest.raises(IssueAuthorizationError):
        fixture.service.record_verification_result(
            issue.issue_id,
            VERIFICATION_REFERENCE_ID,
            contexts[context_kind],
        )

    assert fixture.repository.get(issue.issue_id).status is IssueStatus.RESOLVED
    assert fixture.verification_resolver.calls == 0
    with pytest.raises(IssueNotFoundError):
        fixture.repository.get_latest_verification(issue.issue_id)


def test_fr_069_verification_must_match_trusted_reference_and_issue_scope() -> None:
    result = _verification_result(scope_id=OTHER_DATASET_ID)
    fixture = _fixture(verification_result=result)
    issue = _resolved_issue(fixture)

    with pytest.raises(IssueAuthorizationError, match="outside"):
        fixture.service.record_verification_result(
            issue.issue_id,
            VERIFICATION_REFERENCE_ID,
            _user_context(OTHER_USER_ID, dataset_ids={DATASET_ID}),
        )

    assert fixture.repository.get(issue.issue_id).status is IssueStatus.RESOLVED
    with pytest.raises(IssueNotFoundError):
        fixture.repository.get_latest_verification(issue.issue_id)


@pytest.mark.parametrize(
    "result",
    [
        _verification_result(score_id=None),
        _verification_result(
            outcome=IssueVerificationOutcome.TECHNICAL_ERROR,
            score_id=SCORE_ID,
        ),
    ],
    ids=["failed-without-score", "technical-with-score"],
)
def test_fr_069_rule_003_invalid_or_out_of_scope_verification_result_is_rejected(
    result: TrustedIssueVerificationResult,
) -> None:
    fixture = _fixture(verification_result=result)
    issue = _resolved_issue(fixture)

    with pytest.raises(IssueValidationError):
        fixture.service.record_verification_result(
            issue.issue_id,
            VERIFICATION_REFERENCE_ID,
            _user_context(OTHER_USER_ID, dataset_ids={DATASET_ID}),
        )

    assert fixture.repository.get(issue.issue_id).status is IssueStatus.RESOLVED
    with pytest.raises(IssueNotFoundError):
        fixture.repository.get_latest_verification(issue.issue_id)


def test_fr_069_verification_resolver_failure_is_redacted_technical_error() -> None:
    resolver = StaticVerificationResolver(error=OSError("execution token=unsafe"))
    fixture = _fixture(verification_resolver=resolver)
    issue = _resolved_issue(fixture)

    with pytest.raises(IssueTechnicalError) as error:
        fixture.service.record_verification_result(
            issue.issue_id,
            VERIFICATION_REFERENCE_ID,
            _user_context(OTHER_USER_ID, dataset_ids={DATASET_ID}),
        )

    assert "token" not in str(error.value)
    assert fixture.repository.get(issue.issue_id).status is IssueStatus.RESOLVED


@pytest.mark.parametrize(
    "outcome",
    [IssueVerificationOutcome.QUALITY_FAILED, IssueVerificationOutcome.QUALITY_PASSED],
)
def test_fr_069_nfr_rel_006_verification_audit_failure_rolls_back(
    monkeypatch: pytest.MonkeyPatch,
    outcome: IssueVerificationOutcome,
) -> None:
    fixture = _fixture(verification_result=_verification_result(outcome=outcome))
    issue = _resolved_issue(fixture)
    initial_history_count = len(fixture.repository.list_history(issue.issue_id))

    def fail_stage(*args: object) -> None:
        raise sqlite3.OperationalError("audit outbox unavailable")

    monkeypatch.setattr(fixture.service.transactional_audit, "stage", fail_stage)

    with pytest.raises(IssueTechnicalError):
        fixture.service.record_verification_result(
            issue.issue_id,
            VERIFICATION_REFERENCE_ID,
            _user_context(OTHER_USER_ID, dataset_ids={DATASET_ID}),
        )

    assert fixture.repository.get(issue.issue_id).status is IssueStatus.RESOLVED
    assert len(fixture.repository.list_history(issue.issue_id)) == initial_history_count
    with pytest.raises(IssueNotFoundError):
        fixture.repository.get_latest_verification(issue.issue_id)


def test_fr_066_unresolved_issue_cannot_receive_verification_result() -> None:
    fixture = _fixture()
    issue = _investigating_issue(fixture)

    with pytest.raises(IssueValidationError, match="resolved"):
        fixture.service.record_verification_result(
            issue.issue_id,
            VERIFICATION_REFERENCE_ID,
            _user_context(OTHER_USER_ID, dataset_ids={DATASET_ID}),
        )

    assert fixture.verification_resolver.calls == 0


def test_fr_066_fr_069_fr_070_uc_014_verified_issue_is_closed_with_history_and_audit() -> None:
    fixture = _fixture(
        verification_result=_verification_result(outcome=IssueVerificationOutcome.QUALITY_PASSED)
    )
    issue = _verified_issue(fixture)
    verification = fixture.repository.get_latest_verification(issue.issue_id)

    closed = fixture.service.close(
        issue.issue_id,
        _user_context(OTHER_USER_ID, dataset_ids={DATASET_ID}, roles={"DATA_OWNER"}),
    )

    assert closed.status is IssueStatus.CLOSED
    history = fixture.repository.list_history(issue.issue_id)[-1]
    assert history.action == "ISSUE_CLOSED"
    assert history.old_status is IssueStatus.VERIFIED
    assert history.new_status is IssueStatus.CLOSED
    assert history.verification_id == verification.verification_id
    audit = fixture.issue_audit_repository.list_events()[-1]
    assert audit.action == "DATA_QUALITY_ISSUE_CLOSED"
    assert audit.reason_code == "SUCCESSFUL_VERIFICATION_CONFIRMED"
    assert audit.old_value_summary == {"status": "VERIFIED"}
    assert audit.new_value_summary == {
        "status": "CLOSED",
        "verification_outcome": "QUALITY_PASSED",
    }
    serialized_audit = repr(audit)
    assert EXECUTION_ID not in serialized_audit
    assert SCORE_ID not in serialized_audit
    assert DATASET_ID not in serialized_audit


@pytest.mark.parametrize(
    "context_kind",
    ["missing", "service", "privileged", "role-escalation", "scope-manipulation"],
)
def test_fr_069_nfr_sec_001_unauthorized_actor_cannot_close_verified_issue(
    context_kind: str,
) -> None:
    fixture = _fixture(
        verification_result=_verification_result(outcome=IssueVerificationOutcome.QUALITY_PASSED)
    )
    issue = _verified_issue(fixture)
    contexts = {
        "missing": None,
        "service": _producer_context(),
        "privileged": _user_context(OTHER_USER_ID, dataset_ids={DATASET_ID}, privileged=True),
        "role-escalation": _user_context(OTHER_USER_ID, dataset_ids={DATASET_ID}, roles={"VIEWER"}),
        "scope-manipulation": _user_context(OTHER_USER_ID),
    }
    initial_history_count = len(fixture.repository.list_history(issue.issue_id))

    with pytest.raises(IssueAuthorizationError):
        fixture.service.close(issue.issue_id, contexts[context_kind])

    assert fixture.repository.get(issue.issue_id).status is IssueStatus.VERIFIED
    assert len(fixture.repository.list_history(issue.issue_id)) == initial_history_count


def test_fr_069_ac_018_resolved_issue_cannot_bypass_verification_to_closed() -> None:
    fixture = _fixture()
    issue = _resolved_issue(fixture)

    with pytest.raises(IssueValidationError, match="verified"):
        fixture.service.close(
            issue.issue_id,
            _user_context(OTHER_USER_ID, dataset_ids={DATASET_ID}),
        )

    assert fixture.repository.get(issue.issue_id).status is IssueStatus.RESOLVED


def test_rule_013_verified_status_without_persisted_result_cannot_be_closed() -> None:
    fixture = _fixture()
    issue = _resolved_issue(fixture)
    with fixture.repository.connection:
        fixture.repository.connection.execute(
            "UPDATE data_quality_issues SET status = ? WHERE issue_id = ?",
            (IssueStatus.VERIFIED.value, issue.issue_id),
        )

    with pytest.raises(IssueValidationError, match="persisted verification"):
        fixture.service.close(
            issue.issue_id,
            _user_context(OTHER_USER_ID, dataset_ids={DATASET_ID}),
        )

    assert fixture.repository.get(issue.issue_id).status is IssueStatus.VERIFIED


def test_fr_069_closure_verification_lookup_failure_is_redacted_technical_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture(
        verification_result=_verification_result(outcome=IssueVerificationOutcome.QUALITY_PASSED)
    )
    issue = _verified_issue(fixture)

    def fail_lookup(issue_id: str) -> None:
        raise sqlite3.OperationalError("verification score token=unsafe")

    monkeypatch.setattr(fixture.repository, "get_latest_verification", fail_lookup)

    with pytest.raises(IssueTechnicalError) as error:
        fixture.service.close(
            issue.issue_id,
            _user_context(OTHER_USER_ID, dataset_ids={DATASET_ID}),
        )

    assert "token" not in str(error.value)
    assert fixture.repository.get(issue.issue_id).status is IssueStatus.VERIFIED


def test_fr_069_nfr_rel_006_closure_audit_failure_rolls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture(
        verification_result=_verification_result(outcome=IssueVerificationOutcome.QUALITY_PASSED)
    )
    issue = _verified_issue(fixture)
    initial_history_count = len(fixture.repository.list_history(issue.issue_id))

    def fail_stage(*args: object) -> None:
        raise sqlite3.OperationalError("audit outbox unavailable")

    monkeypatch.setattr(fixture.service.transactional_audit, "stage", fail_stage)

    with pytest.raises(IssueTechnicalError):
        fixture.service.close(
            issue.issue_id,
            _user_context(OTHER_USER_ID, dataset_ids={DATASET_ID}),
        )

    assert fixture.repository.get(issue.issue_id).status is IssueStatus.VERIFIED
    assert len(fixture.repository.list_history(issue.issue_id)) == initial_history_count


def test_fr_066_repeated_close_transition_is_rejected() -> None:
    fixture = _fixture(
        verification_result=_verification_result(outcome=IssueVerificationOutcome.QUALITY_PASSED)
    )
    issue = _verified_issue(fixture)
    context = _user_context(OTHER_USER_ID, dataset_ids={DATASET_ID})
    fixture.service.close(issue.issue_id, context)

    with pytest.raises(IssueValidationError, match="verified"):
        fixture.service.close(issue.issue_id, context)

    assert fixture.repository.get(issue.issue_id).status is IssueStatus.CLOSED
    assert fixture.repository.list_history(issue.issue_id)[-1].action == "ISSUE_CLOSED"


def test_fr_064_fr_069_uc_014_closed_issue_reopens_for_recurring_quality_failure() -> None:
    fixture = _fixture(
        verification_result=_verification_result(outcome=IssueVerificationOutcome.QUALITY_PASSED)
    )
    issue = _closed_issue(fixture)

    reopened = _create(
        fixture.service,
        _trigger(IssueTriggerType.QUALITY_THRESHOLD, occurred_at=NOW),
    )

    assert reopened.issue_id == issue.issue_id
    assert reopened.status is IssueStatus.WAITING_FOR_RESOLUTION
    assert reopened.occurrence_count == 2
    history = fixture.repository.list_history(issue.issue_id)[-1]
    assert history.action == "ISSUE_REOPENED_BY_RECURRING_QUALITY_FAILURE"
    assert history.old_status is IssueStatus.CLOSED
    assert history.new_status is IssueStatus.WAITING_FOR_RESOLUTION
    audit = fixture.issue_audit_repository.list_events()[-1]
    assert audit.action == "DATA_QUALITY_ISSUE_REOPENED"
    assert audit.reason_code == "RECURRING_QUALITY_FAILURE"
    assert audit.old_value_summary == {"status": "CLOSED"}
    assert audit.new_value_summary == {
        "source_event_type": "QUALITY",
        "status": "WAITING_FOR_RESOLUTION",
        "trigger_type": "QUALITY_THRESHOLD",
    }
    serialized_audit = repr(audit)
    assert DATASET_ID not in serialized_audit
    assert "QUALITY.ISSUE.1" not in serialized_audit


def test_fr_069_stale_quality_event_does_not_reopen_closed_issue() -> None:
    fixture = _fixture(
        verification_result=_verification_result(outcome=IssueVerificationOutcome.QUALITY_PASSED)
    )
    issue = _closed_issue(fixture)

    repeated = _create(fixture.service, _trigger(IssueTriggerType.QUALITY_THRESHOLD))

    assert repeated.status is IssueStatus.CLOSED
    assert repeated.occurrence_count == 2
    history = fixture.repository.list_history(issue.issue_id)[-1]
    assert history.action == "ISSUE_REPEATED"
    assert history.old_status is IssueStatus.CLOSED
    assert history.new_status is IssueStatus.CLOSED

    reopened = _create(
        fixture.service,
        _trigger(IssueTriggerType.QUALITY_THRESHOLD, occurred_at=NOW),
    )

    assert reopened.status is IssueStatus.WAITING_FOR_RESOLUTION
    assert reopened.occurrence_count == 3


def test_rule_003_technical_event_does_not_reopen_closed_issue_as_quality_failure() -> None:
    fixture = _fixture(
        verification_result=_verification_result(outcome=IssueVerificationOutcome.QUALITY_PASSED)
    )
    trigger = _trigger(
        IssueTriggerType.TECHNICAL_ERROR,
        deduplication_key="TECHNICAL.ISSUE.REOPEN",
    )
    issue = _closed_issue(fixture, trigger)

    repeated = _create(
        fixture.service,
        _trigger(
            IssueTriggerType.TECHNICAL_ERROR,
            deduplication_key="TECHNICAL.ISSUE.REOPEN",
            occurred_at=NOW,
        ),
    )

    assert repeated.status is IssueStatus.CLOSED
    assert fixture.repository.list_history(issue.issue_id)[-1].action == "ISSUE_REPEATED"


def test_rule_011_closed_issue_reopen_rejects_same_key_with_different_payload() -> None:
    fixture = _fixture(
        verification_result=_verification_result(outcome=IssueVerificationOutcome.QUALITY_PASSED)
    )
    issue = _closed_issue(fixture)

    with pytest.raises(IssueConflictError):
        _create(
            fixture.service,
            _trigger(
                IssueTriggerType.QUALITY_THRESHOLD,
                scope_id=OTHER_DATASET_ID,
                occurred_at=NOW,
            ),
        )

    assert fixture.repository.get(issue.issue_id).status is IssueStatus.CLOSED
    assert fixture.repository.get(issue.issue_id).occurrence_count == 1


def test_rule_011_nfr_rel_005_one_hundred_closed_replays_reopen_single_issue_once() -> None:
    fixture = _fixture(
        verification_result=_verification_result(outcome=IssueVerificationOutcome.QUALITY_PASSED)
    )
    issue = _closed_issue(fixture)

    results = [
        _create(
            fixture.service,
            _trigger(IssueTriggerType.QUALITY_THRESHOLD, occurred_at=NOW),
        )
        for _ in range(100)
    ]

    assert {result.issue_id for result in results} == {issue.issue_id}
    assert results[-1].status is IssueStatus.WAITING_FOR_RESOLUTION
    assert results[-1].occurrence_count == 101
    assert fixture.repository.count() == 1
    history = fixture.repository.list_history(issue.issue_id)
    assert (
        sum(item.action == "ISSUE_REOPENED_BY_RECURRING_QUALITY_FAILURE" for item in history) == 1
    )


def test_fr_069_nfr_rel_006_reopen_audit_failure_rolls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture(
        verification_result=_verification_result(outcome=IssueVerificationOutcome.QUALITY_PASSED)
    )
    issue = _closed_issue(fixture)
    initial_history_count = len(fixture.repository.list_history(issue.issue_id))

    def fail_stage(*args: object) -> None:
        raise sqlite3.OperationalError("audit outbox unavailable")

    monkeypatch.setattr(fixture.service.transactional_audit, "stage", fail_stage)

    with pytest.raises(IssueTechnicalError):
        _create(
            fixture.service,
            _trigger(IssueTriggerType.QUALITY_THRESHOLD, occurred_at=NOW),
        )

    stored = fixture.repository.get(issue.issue_id)
    assert stored.status is IssueStatus.CLOSED
    assert stored.occurrence_count == 1
    assert len(fixture.repository.list_history(issue.issue_id)) == initial_history_count


class StaticAssignmentResolver:
    def __init__(
        self,
        assignment: IssueAssignment | None = IssueAssignment(
            ASSIGNEE_ID,
            IssuePriority.CRITICAL,
        ),
        *,
        error: Exception | None = None,
    ) -> None:
        self.assignment = assignment
        self.error = error
        self.calls = 0

    def resolve_assignment(self, trigger: IssueTrigger) -> IssueAssignment:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.assignment  # type: ignore[return-value]


class StaticAssigneeDirectory:
    def __init__(
        self,
        profile: IssueAssigneeProfile | None = IssueAssigneeProfile(
            OTHER_USER_ID,
            True,
            frozenset(),
            frozenset({DATASET_ID}),
        ),
        *,
        error: Exception | None = None,
    ) -> None:
        self.profile = profile
        self.error = error
        self.calls = 0

    def get_assignee_profile(self, user_id: str) -> IssueAssigneeProfile | None:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.profile


class StaticResolutionProtector:
    def __init__(
        self,
        *,
        protected: ProtectedIssueResolution | None = None,
        error: Exception | None = None,
    ) -> None:
        self.protected = protected
        self.error = error
        self.calls = 0

    def protect_resolution(self, draft: IssueResolutionDraft) -> ProtectedIssueResolution:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.protected or ProtectedIssueResolution(
            root_cause=draft.root_cause,
            corrective_action=draft.corrective_action,
            evidence_reference_id=draft.evidence_reference_id,
            completed_at=draft.completed_at,
            protection_policy_version="ISSUE_TEXT_POLICY_V1",
        )


class StaticVerificationResolver:
    def __init__(
        self,
        result: TrustedIssueVerificationResult | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self.result = result or _verification_result()
        self.error = error
        self.calls = 0

    def resolve_verification(
        self,
        verification_reference_id: str,
    ) -> TrustedIssueVerificationResult | None:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.result


class IssueAwareNotificationRecipientResolver:
    def __init__(self, issue_repository: SQLiteIssueRepository) -> None:
        self.issue_repository = issue_repository

    def resolve_recipients(self, event: NotificationEvent) -> tuple[str, ...]:
        if event.event_type is NotificationEventType.ISSUE_ASSIGNED:
            assignee_id = self.issue_repository.get_history(event.scope_id).new_assignee_user_id
            return (assignee_id,) if assignee_id else ()
        return (ASSIGNEE_ID,)


class CountingNotificationPublisher:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.calls = 0

    def create_for_event(
        self,
        event: NotificationEvent,
        actor_context: ActorContext | None,
    ) -> tuple[object, ...]:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return ()


class IssueFixture:
    def __init__(
        self,
        service: IssueService,
        repository: SQLiteIssueRepository,
        assignment_resolver: StaticAssignmentResolver,
        assignee_directory: StaticAssigneeDirectory,
        resolution_protector: StaticResolutionProtector,
        verification_resolver: StaticVerificationResolver,
        issue_audit_repository: SQLiteAuditRepository,
        notification_repository: SQLiteNotificationRepository,
    ) -> None:
        self.service = service
        self.repository = repository
        self.assignment_resolver = assignment_resolver
        self.assignee_directory = assignee_directory
        self.resolution_protector = resolution_protector
        self.verification_resolver = verification_resolver
        self.issue_audit_repository = issue_audit_repository
        self.notification_repository = notification_repository


def _fixture(
    *,
    assignment: IssueAssignment | None = IssueAssignment(
        ASSIGNEE_ID,
        IssuePriority.CRITICAL,
    ),
    assignment_resolver: StaticAssignmentResolver | None = None,
    assignee_profile: IssueAssigneeProfile | None = IssueAssigneeProfile(
        OTHER_USER_ID,
        True,
        frozenset(),
        frozenset({DATASET_ID}),
    ),
    assignee_directory: StaticAssigneeDirectory | None = None,
    resolution_protector: StaticResolutionProtector | None = None,
    verification_result: TrustedIssueVerificationResult | None = None,
    verification_resolver: StaticVerificationResolver | None = None,
    notification_publisher: CountingNotificationPublisher | None = None,
) -> IssueFixture:
    issue_repository = SQLiteIssueRepository()
    issue_audit_repository = SQLiteAuditRepository()
    issue_outbox = SQLiteTransactionalAudit(
        issue_repository.connection,
        AuditRedactor(
            AuditRedactionPolicy(
                version="ISSUE_REDACTION_V1",
                allowed_fields_by_action={
                    "DATA_QUALITY_ISSUE_TRIGGER_PROCESSED": frozenset(
                        {"source_event_type", "trigger_type", "status", "priority"}
                    ),
                    "DATA_QUALITY_ISSUE_STATUS_CHANGED": frozenset({"status"}),
                    "DATA_QUALITY_ISSUE_ASSIGNED": frozenset({"status", "priority"}),
                    "DATA_QUALITY_ISSUE_RESOLVED": frozenset(
                        {
                            "status",
                            "resolution_fields_complete",
                            "protection_policy_version",
                        }
                    ),
                    "DATA_QUALITY_ISSUE_VERIFICATION_RECORDED": frozenset(
                        {"status", "verification_outcome", "has_score_reference"}
                    ),
                    "DATA_QUALITY_ISSUE_CLOSED": frozenset({"status", "verification_outcome"}),
                    "DATA_QUALITY_ISSUE_REOPENED": frozenset(
                        {"status", "source_event_type", "trigger_type"}
                    ),
                },
            )
        ),
        issue_audit_repository,
        policy_version="ISSUE_OUTBOX_V1",
    )
    notification_repository = SQLiteNotificationRepository()
    notification_audit_repository = SQLiteAuditRepository()
    notification_service = NotificationService(
        notification_repository,
        IssueAwareNotificationRecipientResolver(issue_repository),
        SQLiteTransactionalAudit(
            notification_repository.connection,
            AuditRedactor(
                AuditRedactionPolicy(
                    version="NOTIFICATION_REDACTION_V1",
                    allowed_fields_by_action={
                        "NOTIFICATION_CREATED": frozenset(
                            {"event_type", "recipient_count", "status"}
                        ),
                        "NOTIFICATION_READ": frozenset({"status"}),
                    },
                )
            ),
            notification_audit_repository,
            policy_version="NOTIFICATION_OUTBOX_V1",
        ),
        NotificationAccessPolicy(
            version="NOTIFICATION_ACCESS_V1",
            actor_policy_version=ACTOR_POLICY_VERSION,
        ),
        clock=lambda: NOW,
    )
    resolver = assignment_resolver or StaticAssignmentResolver(assignment)
    directory = assignee_directory or StaticAssigneeDirectory(assignee_profile)
    protector = resolution_protector or StaticResolutionProtector()
    actual_verification_resolver = verification_resolver or StaticVerificationResolver(
        verification_result
    )
    service = IssueService(
        issue_repository,
        resolver,
        notification_publisher or notification_service,
        issue_outbox,
        IssueAccessPolicy(
            version="ISSUE_ACCESS_V1",
            actor_policy_version=ACTOR_POLICY_VERSION,
        ),
        assignee_directory=directory,
        resolution_protector=protector,
        verification_resolver=actual_verification_resolver,
        notification_actor_context_provider=_producer_context,
        clock=lambda: NOW,
    )
    return IssueFixture(
        service,
        issue_repository,
        resolver,
        directory,
        protector,
        actual_verification_resolver,
        issue_audit_repository,
        notification_repository,
    )


def _trigger(
    trigger_type: IssueTriggerType,
    *,
    scope_id: str = DATASET_ID,
    deduplication_key: str = "QUALITY.ISSUE.1",
    occurred_at: datetime = NOW - timedelta(minutes=1),
) -> IssueTrigger:
    return IssueTrigger(
        trigger_type=trigger_type,
        scope_type=IssueScopeType.DATASET,
        scope_id=scope_id,
        deduplication_key=deduplication_key,
        occurred_at=occurred_at,
        correlation_id="correlation-issue",
    )


def _create(service: IssueService, trigger: IssueTrigger) -> DataQualityIssue:
    return service.create_for_trigger(trigger, _producer_context())


def _investigating_issue(
    fixture: IssueFixture,
    trigger: IssueTrigger | None = None,
) -> DataQualityIssue:
    issue = _create(
        fixture.service,
        trigger or _trigger(IssueTriggerType.QUALITY_THRESHOLD),
    )
    return fixture.service.start_investigation(
        issue.issue_id,
        _user_context(ASSIGNEE_ID, dataset_ids={DATASET_ID}),
    )


def _resolved_issue(
    fixture: IssueFixture,
    trigger: IssueTrigger | None = None,
) -> DataQualityIssue:
    issue = _investigating_issue(fixture, trigger)
    return fixture.service.resolve(
        issue.issue_id,
        _resolution_draft(),
        _user_context(ASSIGNEE_ID, dataset_ids={DATASET_ID}),
    )


def _verified_issue(
    fixture: IssueFixture,
    trigger: IssueTrigger | None = None,
) -> DataQualityIssue:
    issue = _resolved_issue(fixture, trigger)
    return fixture.service.record_verification_result(
        issue.issue_id,
        VERIFICATION_REFERENCE_ID,
        _user_context(OTHER_USER_ID, dataset_ids={DATASET_ID}, roles={"DATA_OWNER"}),
    )


def _closed_issue(
    fixture: IssueFixture,
    trigger: IssueTrigger | None = None,
) -> DataQualityIssue:
    issue = _verified_issue(fixture, trigger)
    return fixture.service.close(
        issue.issue_id,
        _user_context(OTHER_USER_ID, dataset_ids={DATASET_ID}, roles={"DATA_OWNER"}),
    )


def _resolution_draft(*, completed_at: datetime = NOW) -> IssueResolutionDraft:
    return IssueResolutionDraft(
        root_cause="Invalid source mapping",
        corrective_action="Corrected mapping configuration",
        evidence_reference_id=EVIDENCE_ID,
        completed_at=completed_at,
    )


def _producer_context(*, privileged: bool = False) -> ActorContext:
    return ActorContextIssuer().issue(
        actor_id=SERVICE_ID,
        actor_type=ActorType.SERVICE,
        authentication_source="synthetic-service-adapter",
        session_id="synthetic-service-session",
        roles=frozenset({"ISSUE_PRODUCER"}),
        permitted_source_ids=frozenset(),
        permitted_dataset_ids=frozenset(),
        can_view_enterprise=False,
        privileged=privileged,
        issued_at=NOW - timedelta(minutes=5),
        expires_at=NOW + timedelta(hours=1),
        policy_version=ACTOR_POLICY_VERSION,
        correlation_id="correlation-issue-producer",
    )


def _user_context(
    actor_id: str,
    *,
    dataset_ids: set[str] | None = None,
    privileged: bool = False,
    roles: set[str] | None = None,
) -> ActorContext:
    return ActorContextIssuer().issue(
        actor_id=actor_id,
        actor_type=ActorType.USER,
        authentication_source="synthetic-adapter",
        session_id="synthetic-session",
        roles=frozenset(roles or {"DATA_STEWARD"}),
        permitted_source_ids=frozenset(),
        permitted_dataset_ids=frozenset(dataset_ids or set()),
        can_view_enterprise=False,
        privileged=privileged,
        issued_at=NOW - timedelta(minutes=5),
        expires_at=NOW + timedelta(hours=1),
        policy_version=ACTOR_POLICY_VERSION,
        correlation_id="correlation-issue-user",
    )
