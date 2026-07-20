from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta, timezone
import sqlite3
from typing import cast
from uuid import uuid4

import pytest

from veri_kalitesi.audit import (
    AuditRedactor,
    SQLiteAuditRepository,
    SQLiteTransactionalAudit,
    build_default_redaction_policy,
)
from veri_kalitesi.identity import ActorContext, ActorContextIssuer, ActorType
from veri_kalitesi.incident_response import (
    BreachDecisionDraft,
    BreachDeadlineStatus,
    BreachNotificationDecision,
    BreachOrigin,
    BreachSuspicionDraft,
    BreachTimelineQuery,
    IncidentAuthorizationError,
    IncidentConflictError,
    IncidentResponseAccessPolicy,
    IncidentResponseService,
    IncidentScopeType,
    IncidentSeverity,
    IncidentSource,
    IncidentTechnicalError,
    IncidentTimelineEventType,
    IncidentValidationError,
    PersonalDataCategory,
    SQLiteIncidentResponseRepository,
    SecurityIncidentDraft,
)


NOW = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
ACTOR_POLICY_VERSION = "BANK_ACTOR_V1"
INCIDENT_POLICY_VERSION = "INCIDENT_RESPONSE_V1"
SOURCE_A = "source-a"
SOURCE_B = "source-b"


def test_bfr_ir_001_security_incident_is_not_implicitly_a_breach() -> None:
    fixture = _fixture()

    incident = fixture.service.record_security_incident(_incident_draft(), fixture.incident_actor)

    assert fixture.repository.get_incident(incident.incident_id) == incident
    assert (
        fixture.repository.connection.execute(
            "SELECT COUNT(*) FROM personal_data_breach_suspicions"
        ).fetchone()[0]
        == 0
    )
    assert [
        entry.event_type for entry in fixture.repository.list_timeline(incident.incident_id)
    ] == [IncidentTimelineEventType.SECURITY_INCIDENT_RECORDED]


def test_bfr_ir_001_002_breach_suspicion_has_separate_append_only_timeline() -> None:
    fixture = _fixture()
    incident = fixture.service.record_security_incident(_incident_draft(), fixture.incident_actor)

    breach = fixture.service.record_breach_suspicion(
        _breach_draft(incident.incident_id), fixture.privacy_maker
    )

    assert breach.incident_id == incident.incident_id
    assert breach.evaluation_deadline_at == breach.learned_at + timedelta(hours=72)
    assert breach.status.value == "ASSESSMENT_PENDING"
    assert [
        entry.event_type for entry in fixture.repository.list_timeline(incident.incident_id)
    ] == [
        IncidentTimelineEventType.SECURITY_INCIDENT_RECORDED,
        IncidentTimelineEventType.BREACH_SUSPICION_RECORDED,
        IncidentTimelineEventType.CONTAINMENT_RECORDED,
    ]
    assert not hasattr(fixture.repository, "update")
    assert not hasattr(fixture.repository, "delete")


def test_bfr_ir_003_human_checker_decision_never_dispatches_authority_notification() -> None:
    fixture = _fixture()
    incident = fixture.service.record_security_incident(_incident_draft(), fixture.incident_actor)
    breach = fixture.service.record_breach_suspicion(
        _breach_draft(incident.incident_id), fixture.privacy_maker
    )

    decision = fixture.service.record_notification_decision(
        _decision_draft(breach.breach_id), fixture.privacy_checker
    )

    assert decision.external_notification_dispatched is False
    assert fixture.repository.get_breach_decision(breach.breach_id) == decision
    assert fixture.repository.get_breach_suspicion(breach.breach_id).status.value == (
        "NOTIFICATION_DECIDED"
    )
    row = fixture.repository.connection.execute(
        "SELECT external_notification_dispatched FROM breach_notification_decisions"
    ).fetchone()
    assert row[0] == 0
    assert fixture.repository.list_timeline(incident.incident_id)[-1].event_type is (
        IncidentTimelineEventType.NOTIFICATION_DECISION_RECORDED
    )


def test_bfr_ir_004_processor_origin_requires_and_preserves_opaque_notice_evidence() -> None:
    fixture = _fixture()
    incident = fixture.service.record_security_incident(_incident_draft(), fixture.incident_actor)
    processor_evidence = str(uuid4())

    breach = fixture.service.record_breach_suspicion(
        replace(
            _breach_draft(incident.incident_id),
            origin=BreachOrigin.DATA_PROCESSOR,
            processor_notification_evidence_id=processor_evidence,
        ),
        fixture.privacy_maker,
    )

    assert breach.processor_notification_evidence_id == processor_evidence
    assert fixture.repository.list_timeline(incident.incident_id)[-1].event_type is (
        IncidentTimelineEventType.PROCESSOR_NOTICE_EVIDENCE_RECORDED
    )


def test_bfr_ir_004_processor_origin_without_notice_evidence_is_rejected() -> None:
    fixture = _fixture()
    incident = fixture.service.record_security_incident(_incident_draft(), fixture.incident_actor)

    with pytest.raises(IncidentValidationError, match="requires notification evidence"):
        fixture.service.record_breach_suspicion(
            replace(
                _breach_draft(incident.incident_id),
                origin=BreachOrigin.DATA_PROCESSOR,
            ),
            fixture.privacy_maker,
        )


def test_bfr_ir_003_maker_cannot_record_own_notification_decision_and_denial_is_audited() -> None:
    fixture = _fixture()
    incident = fixture.service.record_security_incident(_incident_draft(), fixture.incident_actor)
    breach = fixture.service.record_breach_suspicion(
        _breach_draft(incident.incident_id), fixture.privacy_maker
    )

    with pytest.raises(IncidentAuthorizationError) as exc_info:
        fixture.service.record_notification_decision(
            _decision_draft(breach.breach_id), fixture.privacy_maker
        )

    assert exc_info.value.reason_code == "MAKER_CHECKER_REQUIRED"
    assert fixture.repository.get_breach_decision(breach.breach_id) is None
    denied = fixture.audit_repository.list_events()[-1]
    assert denied.action == "INCIDENT_RESPONSE_AUTHORIZATION"
    assert denied.reason_code == "MAKER_CHECKER_REQUIRED"


@pytest.mark.parametrize(
    ("context_kind", "reason_code"),
    [
        ("missing", "UNTRUSTED_CONTEXT"),
        ("forged", "UNTRUSTED_CONTEXT"),
        ("roleless", "INCIDENT_ROLE_REQUIRED"),
        ("privileged", "PRIVILEGED_CONTEXT_NOT_ALLOWED"),
        ("service", "ACTOR_TYPE_NOT_ALLOWED"),
    ],
)
def test_nfr_sec_001_brule_001_untrusted_privileged_and_service_access_is_denied(
    context_kind: str,
    reason_code: str,
) -> None:
    fixture = _fixture()
    contexts = {
        "missing": None,
        "forged": replace(fixture.incident_actor, _trust_marker=object()),
        "roleless": _context("roleless", roles=frozenset()),
        "privileged": _context(
            "privileged",
            roles=frozenset({"SECURITY_INCIDENT_RESPONDER"}),
            privileged=True,
        ),
        "service": _context(
            "service",
            roles=frozenset({"SECURITY_INCIDENT_RESPONDER"}),
            actor_type=ActorType.SERVICE,
        ),
    }

    with pytest.raises(IncidentAuthorizationError) as exc_info:
        fixture.service.record_security_incident(_incident_draft(), contexts[context_kind])

    assert exc_info.value.reason_code == reason_code
    denied = fixture.audit_repository.list_events()[-1]
    assert denied.result.value == "DENIED"
    assert denied.new_value_summary == {
        "policy_version": INCIDENT_POLICY_VERSION,
        "reason_code": reason_code,
    }


def test_nfr_sec_001_scope_manipulation_is_rejected_before_incident_write() -> None:
    fixture = _fixture()

    with pytest.raises(IncidentAuthorizationError) as exc_info:
        fixture.service.record_security_incident(
            replace(_incident_draft(), scope_id=SOURCE_B), fixture.incident_actor
        )

    assert exc_info.value.reason_code == "SOURCE_SCOPE_DENIED"
    assert (
        fixture.repository.connection.execute("SELECT COUNT(*) FROM security_incidents").fetchone()[
            0
        ]
        == 0
    )
    assert fixture.audit_repository.list_events()[-1].reason_code == "SOURCE_SCOPE_DENIED"


@pytest.mark.parametrize(
    "invalid_kind",
    ["event-code", "source-reference", "evidence-reference", "future-time"],
)
def test_nfr_prv_005_invalid_or_sensitive_incident_input_is_rejected(
    invalid_kind: str,
) -> None:
    fixture = _fixture()
    drafts = {
        "event-code": replace(_incident_draft(), event_code="free text"),
        "source-reference": replace(_incident_draft(), source_event_reference_id="not-a-uuid"),
        "evidence-reference": replace(
            _incident_draft(), evidence_reference_id="secret://synthetic/not-real"
        ),
        "future-time": replace(_incident_draft(), detected_at=NOW + timedelta(seconds=1)),
    }

    with pytest.raises(IncidentValidationError):
        fixture.service.record_security_incident(drafts[invalid_kind], fixture.incident_actor)

    assert (
        fixture.repository.connection.execute("SELECT COUNT(*) FROM security_incidents").fetchone()[
            0
        ]
        == 0
    )


def test_invalid_runtime_enum_is_rejected_as_validation_failure() -> None:
    fixture = _fixture()

    with pytest.raises(IncidentValidationError, match="source is invalid"):
        fixture.service.record_security_incident(
            replace(_incident_draft(), source=cast(IncidentSource, "UNSUPPORTED")),
            fixture.incident_actor,
        )


def test_nfr_sec_008_incident_audit_is_allowlisted_and_data_minimum() -> None:
    fixture = _fixture()
    incident_draft = _incident_draft()
    incident = fixture.service.record_security_incident(incident_draft, fixture.incident_actor)
    breach_draft = _breach_draft(incident.incident_id)

    fixture.service.record_breach_suspicion(breach_draft, fixture.privacy_maker)

    event = fixture.audit_repository.list_events()[-1]
    assert event.action == "PERSONAL_DATA_BREACH_SUSPICION_RECORDED"
    assert event.new_value_summary == {
        "assessment_status": "ASSESSMENT_PENDING",
        "containment_action_code": "ACCOUNT_DISABLED",
        "data_category_count": 1,
        "evaluation_deadline_at": (NOW - timedelta(hours=1) + timedelta(hours=72)).isoformat(),
        "origin": "DATA_CONTROLLER",
        "policy_version": INCIDENT_POLICY_VERSION,
        "processor_notification_evidence_present": False,
    }
    serialized = repr(event)
    assert SOURCE_A not in serialized
    assert incident_draft.evidence_reference_id not in serialized
    assert breach_draft.evidence_reference_id not in serialized


def test_bfr_ir_001_duplicate_breach_for_same_incident_is_rejected() -> None:
    fixture = _fixture()
    incident = fixture.service.record_security_incident(_incident_draft(), fixture.incident_actor)
    draft = _breach_draft(incident.incident_id)
    fixture.service.record_breach_suspicion(draft, fixture.privacy_maker)

    with pytest.raises(IncidentConflictError):
        fixture.service.record_breach_suspicion(draft, fixture.privacy_maker)


def test_bfr_ir_002_timeline_cannot_move_backwards() -> None:
    fixture = _fixture()
    incident = fixture.service.record_security_incident(_incident_draft(), fixture.incident_actor)

    with pytest.raises(IncidentValidationError, match="precede incident detection"):
        fixture.service.record_breach_suspicion(
            replace(
                _breach_draft(incident.incident_id),
                learned_at=incident.detected_at - timedelta(seconds=1),
            ),
            fixture.privacy_maker,
        )

    breach = fixture.service.record_breach_suspicion(
        _breach_draft(incident.incident_id), fixture.privacy_maker
    )
    with pytest.raises(IncidentValidationError, match="precede learned time"):
        fixture.service.record_notification_decision(
            replace(
                _decision_draft(breach.breach_id),
                decided_at=breach.learned_at - timedelta(seconds=1),
            ),
            fixture.privacy_checker,
        )


def test_bfr_ir_002_decision_after_72_hours_remains_visible_as_overdue() -> None:
    fixture = _fixture(now=NOW + timedelta(hours=80))
    incident = fixture.service.record_security_incident(
        replace(_incident_draft(), detected_at=NOW - timedelta(hours=2)),
        fixture.incident_actor,
    )
    breach = fixture.service.record_breach_suspicion(
        replace(_breach_draft(incident.incident_id), learned_at=NOW),
        fixture.privacy_maker,
    )

    fixture.service.record_notification_decision(
        replace(_decision_draft(breach.breach_id), decided_at=NOW + timedelta(hours=73)),
        fixture.privacy_checker,
    )

    event = fixture.audit_repository.list_events()[-1]
    assert event.new_value_summary["deadline_status"] == "OVERDUE"
    assert event.new_value_summary["external_notification_dispatched"] is False


def test_bfr_aud_004_audit_stage_failure_rolls_back_incident_and_timeline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture()

    def fail_stage(event: object) -> None:
        raise sqlite3.OperationalError("synthetic audit outage")

    monkeypatch.setattr(fixture.transactional_audit, "stage", fail_stage)

    with pytest.raises(IncidentTechnicalError):
        fixture.service.record_security_incident(_incident_draft(), fixture.incident_actor)

    assert (
        fixture.repository.connection.execute("SELECT COUNT(*) FROM security_incidents").fetchone()[
            0
        ]
        == 0
    )
    assert (
        fixture.repository.connection.execute("SELECT COUNT(*) FROM incident_timeline").fetchone()[
            0
        ]
        == 0
    )


def test_technical_repository_failure_is_not_reported_as_breach_or_quality_failure() -> None:
    fixture = _fixture()
    fixture.repository.connection.close()

    with pytest.raises(IncidentTechnicalError) as exc_info:
        fixture.service.record_security_incident(_incident_draft(), fixture.incident_actor)

    assert exc_info.value.correlation_id == "correlation-incident-responder"


def test_bfr_ir_002_003_pending_timeline_view_is_authorized_and_data_minimum() -> None:
    fixture = _fixture()
    incident_draft = _incident_draft()
    incident = fixture.service.record_security_incident(incident_draft, fixture.incident_actor)
    breach_draft = _breach_draft(incident.incident_id)
    breach = fixture.service.record_breach_suspicion(breach_draft, fixture.privacy_maker)

    view = fixture.service.view_breach_timeline(
        _timeline_query(breach.breach_id), fixture.privacy_checker
    )

    assert view.breach_id == breach.breach_id
    assert view.deadline_status is BreachDeadlineStatus.ASSESSMENT_PENDING
    assert view.data_category_count == 1
    assert view.external_notification_dispatched is False
    assert [item.event_type for item in view.timeline] == [
        IncidentTimelineEventType.SECURITY_INCIDENT_RECORDED,
        IncidentTimelineEventType.BREACH_SUSPICION_RECORDED,
        IncidentTimelineEventType.CONTAINMENT_RECORDED,
    ]
    assert set(asdict(view)) == {
        "breach_id",
        "learned_at",
        "evaluation_deadline_at",
        "assessment_status",
        "deadline_status",
        "origin",
        "data_category_count",
        "affected_scope_code",
        "containment_action_code",
        "processor_notification_evidence_present",
        "decision",
        "decided_at",
        "decision_reason_code",
        "external_notification_dispatched",
        "timeline",
        "generated_at",
        "policy_version",
    }
    serialized = repr(view)
    assert incident.incident_id not in serialized
    assert incident.scope_id is not None
    assert incident.scope_id not in serialized
    assert incident.recorded_by not in serialized
    assert breach.recorded_by not in serialized
    assert incident_draft.evidence_reference_id not in serialized
    assert breach_draft.evidence_reference_id not in serialized


def test_bfr_ir_002_003_decided_timeline_exposes_human_decision_without_evidence() -> None:
    fixture = _fixture()
    incident = fixture.service.record_security_incident(_incident_draft(), fixture.incident_actor)
    breach = fixture.service.record_breach_suspicion(
        _breach_draft(incident.incident_id), fixture.privacy_maker
    )
    decision_draft = _decision_draft(breach.breach_id)
    fixture.service.record_notification_decision(decision_draft, fixture.privacy_checker)

    view = fixture.service.view_breach_timeline(
        _timeline_query(breach.breach_id), fixture.privacy_checker
    )

    assert view.deadline_status is BreachDeadlineStatus.DECIDED_ON_TIME
    assert view.decision is BreachNotificationDecision.AUTHORITY_NOTIFICATION_REQUIRED
    assert view.decision_reason_code == "LEGAL_REVIEW_COMPLETED"
    assert view.decided_at == NOW
    assert decision_draft.evidence_reference_id not in repr(view)
    assert view.timeline[-1].event_type is (
        IncidentTimelineEventType.NOTIFICATION_DECISION_RECORDED
    )


@pytest.mark.parametrize(
    ("decision_offset", "expected_status"),
    [
        (None, BreachDeadlineStatus.ASSESSMENT_OVERDUE),
        (73, BreachDeadlineStatus.DECIDED_OVERDUE),
    ],
)
def test_bfr_ir_003_overdue_assessment_state_is_visible_without_automatic_action(
    decision_offset: int | None,
    expected_status: BreachDeadlineStatus,
) -> None:
    fixture = _fixture(now=NOW + timedelta(hours=80))
    incident = fixture.service.record_security_incident(_incident_draft(), fixture.incident_actor)
    breach = fixture.service.record_breach_suspicion(
        replace(_breach_draft(incident.incident_id), learned_at=NOW),
        fixture.privacy_maker,
    )
    if decision_offset is not None:
        fixture.service.record_notification_decision(
            replace(
                _decision_draft(breach.breach_id),
                decided_at=NOW + timedelta(hours=decision_offset),
            ),
            fixture.privacy_checker,
        )

    view = fixture.service.view_breach_timeline(
        _timeline_query(breach.breach_id), fixture.privacy_checker
    )

    assert view.deadline_status is expected_status
    assert view.external_notification_dispatched is False


def test_bfr_ir_004_processor_notice_is_reduced_to_presence_flag_in_view() -> None:
    fixture = _fixture()
    incident = fixture.service.record_security_incident(_incident_draft(), fixture.incident_actor)
    evidence_id = str(uuid4())
    breach = fixture.service.record_breach_suspicion(
        replace(
            _breach_draft(incident.incident_id),
            origin=BreachOrigin.DATA_PROCESSOR,
            processor_notification_evidence_id=evidence_id,
        ),
        fixture.privacy_maker,
    )

    view = fixture.service.view_breach_timeline(
        _timeline_query(breach.breach_id), fixture.privacy_checker
    )

    assert view.processor_notification_evidence_present is True
    assert evidence_id not in repr(view)


@pytest.mark.parametrize(
    ("context_kind", "reason_code"),
    [
        ("missing", "UNTRUSTED_CONTEXT"),
        ("roleless", "INCIDENT_ROLE_REQUIRED"),
        ("privileged", "PRIVILEGED_CONTEXT_NOT_ALLOWED"),
        ("service", "ACTOR_TYPE_NOT_ALLOWED"),
    ],
)
def test_nfr_sec_001_timeline_authorization_fails_before_repository_read(
    context_kind: str,
    reason_code: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture()
    contexts = {
        "missing": None,
        "roleless": _context("roleless-viewer", roles=frozenset()),
        "privileged": _context(
            "privileged-viewer",
            roles=frozenset({"PRIVACY_INCIDENT_REVIEWER"}),
            privileged=True,
        ),
        "service": _context(
            "service-viewer",
            roles=frozenset({"PRIVACY_INCIDENT_REVIEWER"}),
            actor_type=ActorType.SERVICE,
        ),
    }
    calls = 0

    def fail_if_read(breach_id: str) -> object:
        nonlocal calls
        calls += 1
        raise AssertionError("repository must not be read")

    monkeypatch.setattr(fixture.repository, "get_breach_suspicion", fail_if_read)

    with pytest.raises(IncidentAuthorizationError) as exc_info:
        fixture.service.view_breach_timeline(_timeline_query(str(uuid4())), contexts[context_kind])

    assert exc_info.value.reason_code == reason_code
    assert calls == 0


def test_nfr_sec_001_scope_denial_does_not_read_timeline_and_is_audited(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture()
    incident = fixture.service.record_security_incident(_incident_draft(), fixture.incident_actor)
    breach = fixture.service.record_breach_suspicion(
        _breach_draft(incident.incident_id), fixture.privacy_maker
    )
    out_of_scope = _context(
        "out-of-scope-viewer",
        roles=frozenset({"PRIVACY_INCIDENT_REVIEWER"}),
        source_ids=frozenset({SOURCE_B}),
    )
    timeline_reads = 0
    breach_reads = 0

    def fail_if_timeline_read(incident_id: str) -> tuple[object, ...]:
        nonlocal timeline_reads
        timeline_reads += 1
        raise AssertionError("timeline must not be read before scope authorization")

    monkeypatch.setattr(fixture.repository, "list_timeline", fail_if_timeline_read)

    def fail_if_breach_read(breach_id: str) -> object:
        nonlocal breach_reads
        breach_reads += 1
        raise AssertionError("breach must not be read before scope authorization")

    monkeypatch.setattr(fixture.repository, "get_breach_suspicion", fail_if_breach_read)

    with pytest.raises(IncidentAuthorizationError) as exc_info:
        fixture.service.view_breach_timeline(_timeline_query(breach.breach_id), out_of_scope)

    assert exc_info.value.reason_code == "INCIDENT_SCOPE_DENIED"
    assert timeline_reads == 0
    assert breach_reads == 0
    event = fixture.audit_repository.list_events()[-1]
    assert event.action == "INCIDENT_RESPONSE_AUTHORIZATION"
    assert event.reason_code == "INCIDENT_SCOPE_DENIED"
    assert SOURCE_A not in repr(event)


@pytest.mark.parametrize("invalid_kind", ["breach-id", "reason-code"])
def test_bfr_ir_002_invalid_timeline_query_is_rejected(invalid_kind: str) -> None:
    fixture = _fixture()
    queries = {
        "breach-id": BreachTimelineQuery(breach_id="not-a-uuid", reason_code="PRIVACY_REVIEW"),
        "reason-code": BreachTimelineQuery(breach_id=str(uuid4()), reason_code="free text"),
    }

    with pytest.raises(IncidentValidationError):
        fixture.service.view_breach_timeline(queries[invalid_kind], fixture.privacy_checker)


def test_nfr_sec_008_timeline_view_audit_is_data_minimum() -> None:
    fixture = _fixture()
    incident = fixture.service.record_security_incident(_incident_draft(), fixture.incident_actor)
    breach = fixture.service.record_breach_suspicion(
        _breach_draft(incident.incident_id), fixture.privacy_maker
    )

    fixture.service.view_breach_timeline(_timeline_query(breach.breach_id), fixture.privacy_checker)

    event = fixture.audit_repository.list_events()[-1]
    assert event.action == "PERSONAL_DATA_BREACH_TIMELINE_VIEWED"
    assert event.new_value_summary == {
        "assessment_status": "ASSESSMENT_PENDING",
        "data_category_count": 1,
        "deadline_status": "ASSESSMENT_PENDING",
        "external_notification_dispatched": False,
        "policy_version": INCIDENT_POLICY_VERSION,
        "processor_notification_evidence_present": False,
        "query_reason_code": "PRIVACY_REVIEW",
        "timeline_event_count": 3,
    }
    serialized = repr(event)
    assert incident.scope_id is not None
    assert incident.scope_id not in serialized
    assert breach.evidence_reference_id not in serialized
    assert breach.recorded_by not in serialized


def test_bfr_aud_004_timeline_view_is_fail_closed_when_audit_stage_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture()
    incident = fixture.service.record_security_incident(_incident_draft(), fixture.incident_actor)
    breach = fixture.service.record_breach_suspicion(
        _breach_draft(incident.incident_id), fixture.privacy_maker
    )

    def fail_stage(event: object) -> None:
        raise sqlite3.OperationalError("synthetic audit outage")

    monkeypatch.setattr(fixture.transactional_audit, "stage", fail_stage)

    with pytest.raises(IncidentTechnicalError):
        fixture.service.view_breach_timeline(
            _timeline_query(breach.breach_id), fixture.privacy_checker
        )


def test_corrupted_or_duplicate_timeline_is_rejected_as_technical_failure() -> None:
    fixture = _fixture()
    incident = fixture.service.record_security_incident(_incident_draft(), fixture.incident_actor)
    breach = fixture.service.record_breach_suspicion(
        _breach_draft(incident.incident_id), fixture.privacy_maker
    )
    fixture.repository.connection.execute(
        """
        INSERT INTO incident_timeline (
            timeline_id, incident_id, breach_id, event_type, event_at,
            actor_id, reason_code, evidence_reference_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid4()),
            incident.incident_id,
            breach.breach_id,
            IncidentTimelineEventType.CONTAINMENT_RECORDED.value,
            NOW.isoformat(),
            "synthetic-actor",
            "DUPLICATE_EVENT",
            str(uuid4()),
        ),
    )
    fixture.repository.connection.commit()

    with pytest.raises(IncidentTechnicalError):
        fixture.service.view_breach_timeline(
            _timeline_query(breach.breach_id), fixture.privacy_checker
        )


def test_timeline_repository_failure_is_classified_as_technical_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture()

    def fail_read(breach_id: str) -> object:
        raise sqlite3.OperationalError("synthetic repository outage")

    monkeypatch.setattr(fixture.repository, "get_breach_incident_scope", fail_read)

    with pytest.raises(IncidentTechnicalError) as exc_info:
        fixture.service.view_breach_timeline(_timeline_query(str(uuid4())), fixture.privacy_checker)

    assert exc_info.value.correlation_id == "correlation-privacy-checker"


@dataclass(frozen=True)
class IncidentFixture:
    service: IncidentResponseService
    repository: SQLiteIncidentResponseRepository
    audit_repository: SQLiteAuditRepository
    transactional_audit: SQLiteTransactionalAudit
    incident_actor: ActorContext
    privacy_maker: ActorContext
    privacy_checker: ActorContext


def _fixture(*, now: datetime = NOW) -> IncidentFixture:
    repository = SQLiteIncidentResponseRepository()
    audit_repository = SQLiteAuditRepository()
    transactional_audit = SQLiteTransactionalAudit(
        repository.connection,
        AuditRedactor(build_default_redaction_policy()),
        audit_repository,
        policy_version="AUDIT_OUTBOX_V1",
    )
    service = IncidentResponseService(
        repository,
        transactional_audit,
        IncidentResponseAccessPolicy(
            version=INCIDENT_POLICY_VERSION,
            actor_policy_version=ACTOR_POLICY_VERSION,
        ),
        clock=lambda: now,
    )
    return IncidentFixture(
        service=service,
        repository=repository,
        audit_repository=audit_repository,
        transactional_audit=transactional_audit,
        incident_actor=_context(
            "incident-responder", roles=frozenset({"SECURITY_INCIDENT_RESPONDER"})
        ),
        privacy_maker=_context("privacy-maker", roles=frozenset({"PRIVACY_INCIDENT_REVIEWER"})),
        privacy_checker=_context("privacy-checker", roles=frozenset({"PRIVACY_INCIDENT_REVIEWER"})),
    )


def _context(
    actor_id: str,
    *,
    roles: frozenset[str],
    privileged: bool = False,
    actor_type: ActorType = ActorType.USER,
    source_ids: frozenset[str] = frozenset({SOURCE_A}),
) -> ActorContext:
    return ActorContextIssuer().issue(
        actor_id=actor_id,
        actor_type=actor_type,
        authentication_source="synthetic-identity-adapter",
        session_id=f"synthetic-session-{actor_id}",
        roles=roles,
        permitted_source_ids=source_ids,
        permitted_dataset_ids=frozenset({"dataset-a"}),
        can_view_enterprise=False,
        privileged=privileged,
        issued_at=NOW - timedelta(minutes=5),
        expires_at=NOW + timedelta(days=7),
        policy_version=ACTOR_POLICY_VERSION,
        correlation_id=f"correlation-{actor_id}",
    )


def _incident_draft() -> SecurityIncidentDraft:
    return SecurityIncidentDraft(
        source_event_reference_id=str(uuid4()),
        detected_at=NOW - timedelta(hours=2),
        source=IncidentSource.IDENTITY,
        severity=IncidentSeverity.HIGH,
        event_code="SUSPICIOUS_ACCESS_PATTERN",
        scope_type=IncidentScopeType.SOURCE,
        scope_id=SOURCE_A,
        evidence_reference_id=str(uuid4()),
    )


def _breach_draft(incident_id: str) -> BreachSuspicionDraft:
    return BreachSuspicionDraft(
        incident_id=incident_id,
        learned_at=NOW - timedelta(hours=1),
        origin=BreachOrigin.DATA_CONTROLLER,
        data_categories=frozenset({PersonalDataCategory.PERSONAL_DATA}),
        affected_scope_code="CUSTOMER_CONTACT_DATA",
        containment_action_code="ACCOUNT_DISABLED",
        evidence_reference_id=str(uuid4()),
    )


def _decision_draft(breach_id: str) -> BreachDecisionDraft:
    return BreachDecisionDraft(
        breach_id=breach_id,
        decision=BreachNotificationDecision.AUTHORITY_NOTIFICATION_REQUIRED,
        decided_at=NOW,
        reason_code="LEGAL_REVIEW_COMPLETED",
        evidence_reference_id=str(uuid4()),
    )


def _timeline_query(breach_id: str) -> BreachTimelineQuery:
    return BreachTimelineQuery(breach_id=breach_id, reason_code="PRIVACY_REVIEW")
