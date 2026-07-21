from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from veri_kalitesi.audit import (
    AuditEvent,
    AuditRedactionPolicy,
    AuditRedactor,
    AuditResult,
    PreparedAuditEvent,
    SQLiteAuditRepository,
    SQLiteTransactionalAudit,
)
from veri_kalitesi.identity import ActorContext, ActorContextIssuer, ActorType
from veri_kalitesi.retention import (
    ArchiveRecallAccessPolicy,
    ArchiveRecallDecisionType,
    ArchiveRecallService,
    ArchiveRecallStatus,
    ArchiveRecordType,
    RetentionAuthorizationError,
    RetentionConflictError,
    RetentionScopeType,
    RetentionTechnicalError,
    RetentionValidationError,
    SQLiteArchiveRecallRepository,
)


UTC = timezone.utc
NOW = datetime(2026, 7, 21, 15, 0, tzinfo=UTC)
ACTOR_POLICY_VERSION = "ACTOR_POLICY_V1"
DATASET_ID = "dataset-archive-1"
ARCHIVE_REFERENCE = "opaque-archive-reference-1"


@dataclass
class MutableClock:
    value: datetime = NOW

    def __call__(self) -> datetime:
        return self.value


class FailingAuditRepository:
    def append(self, prepared: PreparedAuditEvent) -> AuditEvent:
        del prepared
        raise OSError("synthetic central audit outage")


def test_bfr_lcm_004_creates_data_minimum_recall_request_with_atomic_audit() -> None:
    service, repository, audit_repository, _ = _service()

    request = _request(service)

    assert request.status is ArchiveRecallStatus.PENDING
    assert request.record_type is ArchiveRecordType.AUDIT_LOG
    assert request.archive_reference_digest != ARCHIVE_REFERENCE
    assert request.scope_digest != DATASET_ID
    assert repository.count_requests() == 1
    audit = audit_repository.list_events()[0]
    assert audit.action == "ARCHIVE_RECALL_REQUESTED"
    assert audit.new_value_summary == {
        "record_type": "AUDIT_LOG",
        "scope_type": "DATASET",
        "status": "PENDING",
    }
    assert ARCHIVE_REFERENCE not in str(audit.new_value_summary)
    assert DATASET_ID not in str(audit.new_value_summary)
    assert not hasattr(service, "read_archive")
    assert not hasattr(service, "fetch_content")


def test_bfr_lcm_004_quality_score_archive_request_is_supported() -> None:
    service, _, _, _ = _service()

    request = _request(service, record_type=ArchiveRecordType.QUALITY_SCORE)

    assert request.record_type is ArchiveRecordType.QUALITY_SCORE


def test_bfr_lcm_004_same_idempotency_key_returns_single_request_and_audit() -> None:
    service, repository, audit_repository, _ = _service()

    first = _request(service)
    second = _request(service)

    assert second == first
    assert repository.count_requests() == 1
    assert len(audit_repository.list_events()) == 1


def test_bfr_lcm_004_reused_idempotency_key_with_different_payload_is_rejected() -> None:
    service, repository, _, _ = _service()
    _request(service)

    with pytest.raises(RetentionConflictError, match="different payload"):
        _request(service, purpose_code="REGULATORY_EXAMINATION")

    assert repository.count_requests() == 1


@pytest.mark.parametrize(
    "actor_kind",
    ["untrusted", "wrong-role", "wrong-scope", "service-account", "break-glass"],
)
def test_nfr_sec_001_unauthorized_actor_cannot_request_archive_recall(
    actor_kind: str,
) -> None:
    service, repository, _, _ = _service()
    actor_context: ActorContext | None = None
    if actor_kind == "wrong-role":
        actor_context = _actor("user-1", frozenset({"DATA_VIEWER"}))
    elif actor_kind == "wrong-scope":
        actor_context = _actor(
            "user-1",
            frozenset({"ARCHIVE_RECALL_REQUESTER"}),
            dataset_ids=frozenset({"another-dataset"}),
        )
    elif actor_kind == "service-account":
        actor_context = _actor(
            "service-1",
            frozenset({"ARCHIVE_RECALL_REQUESTER"}),
            actor_type=ActorType.SERVICE,
        )
    elif actor_kind == "break-glass":
        actor_context = _actor(
            "break-glass-1",
            frozenset({"ARCHIVE_RECALL_REQUESTER"}),
            actor_type=ActorType.BREAK_GLASS,
        )

    with pytest.raises(RetentionAuthorizationError):
        _request(
            service,
            actor_context=actor_context,
            use_default_actor=actor_kind != "untrusted",
        )

    assert repository.count_requests() == 0


def test_bfr_lcm_004_unapproved_purpose_code_is_rejected() -> None:
    service, repository, _, _ = _service()

    with pytest.raises(RetentionValidationError, match="purpose is not allowed"):
        _request(service, purpose_code="FREE_TEXT_PURPOSE")

    assert repository.count_requests() == 0


def test_bfr_sod_002_different_authorized_actor_approves_recall() -> None:
    service, repository, audit_repository, clock = _service()
    request = _request(service)
    clock.value = NOW + timedelta(hours=1)

    approved = _decide(service, request.request_id)

    assert approved.status is ArchiveRecallStatus.APPROVED
    assert approved.decision is not None
    assert approved.decision.decided_by_actor_id == "approver-1"
    assert repository.count_decisions() == 1
    audits = audit_repository.list_events()
    assert [event.action for event in audits] == [
        "ARCHIVE_RECALL_REQUESTED",
        "ARCHIVE_RECALL_DECIDED",
    ]
    assert audits[-1].result is AuditResult.SUCCESS
    assert audits[-1].new_value_summary == {
        "record_type": "AUDIT_LOG",
        "scope_type": "DATASET",
        "status": "APPROVED",
    }


def test_bfr_sod_004_authorized_actor_can_reject_recall() -> None:
    service, _, audit_repository, _ = _service()
    request = _request(service)

    rejected = _decide(
        service,
        request.request_id,
        decision=ArchiveRecallDecisionType.REJECTED,
        reason_code="INSUFFICIENT_JUSTIFICATION",
    )

    assert rejected.status is ArchiveRecallStatus.REJECTED
    assert audit_repository.list_events()[-1].result is AuditResult.DENIED


def test_bfr_sod_002_requester_cannot_decide_same_recall() -> None:
    service, repository, _, _ = _service()
    requester = _actor(
        "requester-1",
        frozenset({"ARCHIVE_RECALL_REQUESTER", "ARCHIVE_RECALL_APPROVER"}),
    )
    request = _request(service, actor_context=requester)

    with pytest.raises(RetentionAuthorizationError, match="cannot decide"):
        _decide(service, request.request_id, actor_context=requester)

    assert repository.count_decisions() == 0


@pytest.mark.parametrize(
    "actor_kind",
    ["untrusted", "wrong-role", "wrong-scope", "service-account", "break-glass"],
)
def test_nfr_sec_001_unauthorized_actor_cannot_decide_archive_recall(
    actor_kind: str,
) -> None:
    service, repository, _, _ = _service()
    request = _request(service)
    actor_context: ActorContext | None = None
    if actor_kind == "wrong-role":
        actor_context = _actor("user-2", frozenset({"DATA_VIEWER"}))
    elif actor_kind == "wrong-scope":
        actor_context = _actor(
            "user-2",
            frozenset({"ARCHIVE_RECALL_APPROVER"}),
            dataset_ids=frozenset({"another-dataset"}),
        )
    elif actor_kind == "service-account":
        actor_context = _actor(
            "service-2",
            frozenset({"ARCHIVE_RECALL_APPROVER"}),
            actor_type=ActorType.SERVICE,
        )
    elif actor_kind == "break-glass":
        actor_context = _actor(
            "break-glass-2",
            frozenset({"ARCHIVE_RECALL_APPROVER"}),
            actor_type=ActorType.BREAK_GLASS,
        )

    with pytest.raises(RetentionAuthorizationError):
        _decide(
            service,
            request.request_id,
            actor_context=actor_context,
            use_default_actor=actor_kind != "untrusted",
        )

    assert repository.count_decisions() == 0


def test_bfr_lcm_004_same_decision_is_idempotent() -> None:
    service, repository, audit_repository, _ = _service()
    request = _request(service)

    first = _decide(service, request.request_id)
    second = _decide(service, request.request_id)

    assert second == first
    assert repository.count_decisions() == 1
    assert len(audit_repository.list_events()) == 2


def test_bfr_sod_004_different_terminal_decision_is_rejected() -> None:
    service, repository, _, _ = _service()
    request = _request(service)
    _decide(service, request.request_id)

    with pytest.raises(RetentionConflictError, match="different decision"):
        _decide(
            service,
            request.request_id,
            decision=ArchiveRecallDecisionType.REJECTED,
            reason_code="INSUFFICIENT_JUSTIFICATION",
        )

    assert repository.count_decisions() == 1


def test_bfr_aud_004_audit_stage_failure_rolls_back_recall_request() -> None:
    service, repository, _, _ = _service()

    def fail_stage(*args: object, **kwargs: object) -> None:
        raise RuntimeError("synthetic audit stage outage")

    service.transactional_audit.stage = fail_stage  # type: ignore[method-assign]

    with pytest.raises(RetentionTechnicalError, match="could not be persisted"):
        _request(service)

    assert repository.count_requests() == 0


def test_bfr_aud_004_audit_stage_failure_rolls_back_recall_decision() -> None:
    service, repository, _, _ = _service()
    request = _request(service)

    def fail_stage(*args: object, **kwargs: object) -> None:
        raise RuntimeError("synthetic audit stage outage")

    service.transactional_audit.stage = fail_stage  # type: ignore[method-assign]

    with pytest.raises(RetentionTechnicalError, match="could not be persisted"):
        _decide(service, request.request_id)

    assert repository.count_decisions() == 0
    assert repository.get(request.request_id).status is ArchiveRecallStatus.PENDING


def test_bfr_aud_004_publisher_outage_keeps_recall_audit_pending() -> None:
    repository = SQLiteArchiveRecallRepository()
    transactional_audit = SQLiteTransactionalAudit(
        repository.connection,
        _redactor(),
        FailingAuditRepository(),
        policy_version="ARCHIVE_RECALL_OUTBOX_V1",
    )
    service = _build_service(repository, transactional_audit, MutableClock())

    request = _request(service)

    assert repository.get(request.request_id) == request
    assert len(transactional_audit.list_pending()) == 1


def test_fr_079_archive_recall_history_rejects_update_and_delete() -> None:
    service, repository, _, _ = _service()
    request = _request(service)
    _decide(service, request.request_id)

    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        repository.connection.execute(
            "UPDATE archive_recall_requests SET purpose_code = 'CHANGED' WHERE request_id = ?",
            (request.request_id,),
        )
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        repository.connection.execute(
            "DELETE FROM archive_recall_decisions WHERE request_id = ?",
            (request.request_id,),
        )


def test_bfr_lcm_004_request_and_decision_survive_repository_reopen(tmp_path: Path) -> None:
    database = str(tmp_path / "archive-recall.sqlite")
    service, repository, _, _ = _service(database=database)
    request = _request(service)
    decided = _decide(service, request.request_id)
    repository.connection.close()

    reopened = SQLiteArchiveRecallRepository(database)

    assert reopened.get(request.request_id) == decided


def _service(
    *,
    database: str = ":memory:",
) -> tuple[
    ArchiveRecallService,
    SQLiteArchiveRecallRepository,
    SQLiteAuditRepository,
    MutableClock,
]:
    repository = SQLiteArchiveRecallRepository(database)
    audit_repository = SQLiteAuditRepository()
    transactional_audit = SQLiteTransactionalAudit(
        repository.connection,
        _redactor(),
        audit_repository,
        policy_version="ARCHIVE_RECALL_OUTBOX_V1",
    )
    clock = MutableClock()
    return (
        _build_service(repository, transactional_audit, clock),
        repository,
        audit_repository,
        clock,
    )


def _build_service(
    repository: SQLiteArchiveRecallRepository,
    transactional_audit: SQLiteTransactionalAudit,
    clock: MutableClock,
) -> ArchiveRecallService:
    return ArchiveRecallService(
        repository,
        transactional_audit,
        ArchiveRecallAccessPolicy(
            version="ARCHIVE_RECALL_ACCESS_V1",
            actor_policy_version=ACTOR_POLICY_VERSION,
            request_roles=frozenset({"ARCHIVE_RECALL_REQUESTER"}),
            decision_roles=frozenset({"ARCHIVE_RECALL_APPROVER"}),
            purpose_codes=frozenset({"AUDIT_REVIEW", "REGULATORY_EXAMINATION"}),
            approval_reason_codes=frozenset({"AUTHORIZED_REVIEW"}),
            rejection_reason_codes=frozenset({"INSUFFICIENT_JUSTIFICATION"}),
        ),
        clock=clock,
    )


def _redactor() -> AuditRedactor:
    fields = frozenset({"status", "record_type", "scope_type"})
    return AuditRedactor(
        AuditRedactionPolicy(
            version="ARCHIVE_RECALL_REDACTION_V1",
            allowed_fields_by_action={
                "ARCHIVE_RECALL_REQUESTED": fields,
                "ARCHIVE_RECALL_DECIDED": fields,
            },
        )
    )


def _request(
    service: ArchiveRecallService,
    *,
    record_type: ArchiveRecordType = ArchiveRecordType.AUDIT_LOG,
    purpose_code: str = "AUDIT_REVIEW",
    actor_context: ActorContext | None = None,
    use_default_actor: bool = True,
):
    selected_actor = actor_context
    if selected_actor is None and use_default_actor:
        selected_actor = _actor("requester-1", frozenset({"ARCHIVE_RECALL_REQUESTER"}))
    return service.request_recall(
        archive_reference=ARCHIVE_REFERENCE,
        record_type=record_type,
        scope_type=RetentionScopeType.DATASET,
        scope_id=DATASET_ID,
        purpose_code=purpose_code,
        idempotency_key="archive-recall-request-001",
        actor_context=selected_actor,
    )


def _decide(
    service: ArchiveRecallService,
    request_id: str,
    *,
    decision: ArchiveRecallDecisionType = ArchiveRecallDecisionType.APPROVED,
    reason_code: str = "AUTHORIZED_REVIEW",
    actor_context: ActorContext | None = None,
    use_default_actor: bool = True,
):
    selected_actor = actor_context
    if selected_actor is None and use_default_actor:
        selected_actor = _actor("approver-1", frozenset({"ARCHIVE_RECALL_APPROVER"}))
    return service.decide_recall(
        request_id,
        decision=decision,
        reason_code=reason_code,
        actor_context=selected_actor,
    )


def _actor(
    actor_id: str,
    roles: frozenset[str],
    *,
    dataset_ids: frozenset[str] = frozenset({DATASET_ID}),
    actor_type: ActorType = ActorType.USER,
) -> ActorContext:
    return ActorContextIssuer().issue(
        actor_id=actor_id,
        actor_type=actor_type,
        authentication_source="synthetic-identity-adapter",
        session_id=f"session-{actor_id}",
        roles=roles,
        permitted_source_ids=frozenset(),
        permitted_dataset_ids=dataset_ids,
        can_view_enterprise=False,
        privileged=actor_type is ActorType.BREAK_GLASS,
        issued_at=NOW - timedelta(hours=1),
        expires_at=NOW + timedelta(hours=8),
        policy_version=ACTOR_POLICY_VERSION,
        correlation_id=f"correlation-{actor_id}",
    )
