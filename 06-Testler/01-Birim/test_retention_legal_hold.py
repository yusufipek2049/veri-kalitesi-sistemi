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
    PreparedAuditEvent,
    SQLiteAuditRepository,
    SQLiteTransactionalAudit,
)
from veri_kalitesi.identity import ActorContext, ActorContextIssuer, ActorType
from veri_kalitesi.retention import (
    LegalHoldAccessPolicy,
    LegalHoldEventType,
    LegalHoldService,
    LegalHoldTarget,
    RetentionAuthorizationError,
    RetentionDisposition,
    RetentionEvaluator,
    RetentionRecordClass,
    RetentionRecordReference,
    RetentionScopeType,
    RetentionTechnicalError,
    RetentionValidationError,
    SQLiteLegalHoldRepository,
    provisional_retention_catalog,
)


UTC = timezone.utc
NOW = datetime(2026, 7, 21, 12, 0, tzinfo=UTC)
ACTOR_POLICY_VERSION = "ACTOR_POLICY_V1"
DATASET_ID = "dataset-retention-1"


@dataclass
class MutableClock:
    value: datetime = NOW

    def __call__(self) -> datetime:
        return self.value


class FailingAuditRepository:
    def append(self, prepared: PreparedAuditEvent) -> AuditEvent:
        del prepared
        raise OSError("synthetic central audit outage")


def test_bfr_lcm_002_places_hold_with_atomic_data_minimum_audit() -> None:
    service, repository, audit_repository, _ = _service()

    hold = service.place_hold(
        _target(),
        reason_code="LITIGATION",
        actor_context=_actor("placer-1", frozenset({"LEGAL_HOLD_PLACER"})),
    )

    assert hold.policy_version == provisional_retention_catalog().version
    assert hold.scope_type is RetentionScopeType.DATASET
    assert repository.count_events() == 1
    active = repository.list_active_holds(_record(), as_of=NOW)
    assert active == (hold,)
    audit = audit_repository.list_events()
    assert len(audit) == 1
    assert audit[0].action == "LEGAL_HOLD_PLACED"
    assert audit[0].new_value_summary == {
        "policy_version": provisional_retention_catalog().version,
        "record_class": RetentionRecordClass.BANKING_RECORD.value,
        "scope_type": RetentionScopeType.DATASET.value,
        "status": "ACTIVE",
    }
    assert "record_reference_id" not in audit[0].new_value_summary


def test_bfr_lcm_002_active_hold_blocks_retention_disposal_evaluation() -> None:
    service, repository, _, _ = _service()
    service.place_hold(
        _target(),
        reason_code="LITIGATION",
        actor_context=_actor("placer-1", frozenset({"LEGAL_HOLD_PLACER"})),
    )
    evaluator = RetentionEvaluator(provisional_retention_catalog(), repository)

    result = evaluator.evaluate(_record(), as_of=datetime(2040, 1, 1, tzinfo=UTC))

    assert result.disposition is RetentionDisposition.LEGAL_HOLD


def test_bfr_lcm_002_active_hold_survives_repository_reopen(tmp_path: Path) -> None:
    database = str(tmp_path / "retention.sqlite")
    repository = SQLiteLegalHoldRepository(database)
    transactional_audit = SQLiteTransactionalAudit(
        repository.connection,
        _redactor(),
        SQLiteAuditRepository(),
        policy_version="LEGAL_HOLD_OUTBOX_V1",
    )
    service = _build_service(repository, transactional_audit, MutableClock())
    hold = service.place_hold(
        _target(),
        reason_code="LITIGATION",
        actor_context=_actor("placer-1", frozenset({"LEGAL_HOLD_PLACER"})),
    )
    repository.connection.close()

    reopened = SQLiteLegalHoldRepository(database)

    assert reopened.get(hold.hold_reference_id) == hold
    assert reopened.list_active_holds(_record(), as_of=NOW) == (hold,)


def test_bfr_lcm_002_release_requires_different_actor_and_appends_history() -> None:
    service, repository, audit_repository, clock = _service()
    placed = service.place_hold(
        _target(),
        reason_code="LITIGATION",
        actor_context=_actor("placer-1", frozenset({"LEGAL_HOLD_PLACER"})),
    )
    clock.value = NOW + timedelta(hours=1)

    released = service.release_hold(
        placed.hold_reference_id,
        reason_code="CASE_CLOSED",
        actor_context=_actor("releaser-1", frozenset({"LEGAL_HOLD_RELEASER"})),
    )

    assert released.released_at == clock.value
    assert released.released_by_actor_id == "releaser-1"
    history = repository.list_history(placed.hold_reference_id)
    assert tuple(event.event_type for event in history) == (
        LegalHoldEventType.PLACED,
        LegalHoldEventType.RELEASED,
    )
    assert repository.list_active_holds(_record(), as_of=clock.value) == ()
    assert [event.action for event in audit_repository.list_events()] == [
        "LEGAL_HOLD_PLACED",
        "LEGAL_HOLD_RELEASED",
    ]


def test_bfr_lcm_002_all_concurrent_holds_must_be_released() -> None:
    service, repository, _, clock = _service()
    first = service.place_hold(
        _target(),
        reason_code="LITIGATION",
        actor_context=_actor("placer-1", frozenset({"LEGAL_HOLD_PLACER"})),
    )
    second = service.place_hold(
        _target(),
        reason_code="REGULATORY_REVIEW",
        actor_context=_actor("placer-2", frozenset({"LEGAL_HOLD_PLACER"})),
    )
    assert len(repository.list_active_holds(_record(), as_of=NOW)) == 2

    clock.value = NOW + timedelta(hours=1)
    service.release_hold(
        first.hold_reference_id,
        reason_code="CASE_CLOSED",
        actor_context=_actor("releaser-1", frozenset({"LEGAL_HOLD_RELEASER"})),
    )

    active = repository.list_active_holds(_record(), as_of=clock.value)
    assert tuple(hold.hold_reference_id for hold in active) == (second.hold_reference_id,)


def test_bfr_sod_002_placer_cannot_release_same_hold() -> None:
    service, repository, _, _ = _service()
    actor = _actor(
        "dual-role-actor",
        frozenset({"LEGAL_HOLD_PLACER", "LEGAL_HOLD_RELEASER"}),
    )
    hold = service.place_hold(_target(), reason_code="LITIGATION", actor_context=actor)

    with pytest.raises(RetentionAuthorizationError, match="different authorized actor"):
        service.release_hold(
            hold.hold_reference_id,
            reason_code="CASE_CLOSED",
            actor_context=actor,
        )

    assert repository.count_events() == 1


@pytest.mark.parametrize(
    "actor_kind",
    [
        "untrusted",
        "wrong-role",
        "wrong-scope",
        "service-account",
        "break-glass",
    ],
)
def test_bfr_iam_001_unauthorized_actor_cannot_place_hold(
    actor_kind: str,
) -> None:
    service, repository, _, _ = _service()
    actor_context: ActorContext | None
    if actor_kind == "untrusted":
        actor_context = None
    elif actor_kind == "wrong-role":
        actor_context = _actor("wrong-role", frozenset({"DATA_VIEWER"}))
    elif actor_kind == "wrong-scope":
        actor_context = _actor(
            "wrong-scope",
            frozenset({"LEGAL_HOLD_PLACER"}),
            dataset_ids=frozenset({"another-dataset"}),
        )
    elif actor_kind == "service-account":
        actor_context = _actor(
            "service-account",
            frozenset({"LEGAL_HOLD_PLACER"}),
            actor_type=ActorType.SERVICE,
        )
    else:
        actor_context = _actor(
            "break-glass",
            frozenset({"LEGAL_HOLD_PLACER"}),
            actor_type=ActorType.BREAK_GLASS,
        )

    with pytest.raises(RetentionAuthorizationError):
        service.place_hold(
            _target(),
            reason_code="LITIGATION",
            actor_context=actor_context,
        )

    assert repository.count_events() == 0


def test_nfr_cmp_001_rejects_unapproved_reason_code() -> None:
    service, repository, _, _ = _service()

    with pytest.raises(RetentionValidationError, match="reason is not allowed"):
        service.place_hold(
            _target(),
            reason_code="FREE_TEXT_REASON",
            actor_context=_actor("placer-1", frozenset({"LEGAL_HOLD_PLACER"})),
        )

    assert repository.count_events() == 0


def test_bfr_aud_004_audit_stage_failure_rolls_back_hold() -> None:
    service, repository, audit_repository, _ = _service()

    def fail_stage(*args: object, **kwargs: object) -> None:
        raise RuntimeError("synthetic audit stage outage")

    service.transactional_audit.stage = fail_stage  # type: ignore[method-assign]

    with pytest.raises(RetentionTechnicalError, match="could not be persisted"):
        service.place_hold(
            _target(),
            reason_code="LITIGATION",
            actor_context=_actor("placer-1", frozenset({"LEGAL_HOLD_PLACER"})),
        )

    assert repository.count_events() == 0
    assert audit_repository.list_events() == []


def test_bfr_aud_004_audit_stage_failure_keeps_hold_active_on_release() -> None:
    service, repository, _, clock = _service()
    hold = service.place_hold(
        _target(),
        reason_code="LITIGATION",
        actor_context=_actor("placer-1", frozenset({"LEGAL_HOLD_PLACER"})),
    )
    clock.value = NOW + timedelta(hours=1)

    def fail_stage(*args: object, **kwargs: object) -> None:
        raise RuntimeError("synthetic audit stage outage")

    service.transactional_audit.stage = fail_stage  # type: ignore[method-assign]

    with pytest.raises(RetentionTechnicalError, match="could not be persisted"):
        service.release_hold(
            hold.hold_reference_id,
            reason_code="CASE_CLOSED",
            actor_context=_actor("releaser-1", frozenset({"LEGAL_HOLD_RELEASER"})),
        )

    assert repository.count_events() == 1
    assert repository.list_active_holds(_record(), as_of=clock.value)


def test_bfr_aud_004_publisher_outage_keeps_committed_hold_in_pending_outbox() -> None:
    repository = SQLiteLegalHoldRepository()
    transactional_audit = SQLiteTransactionalAudit(
        repository.connection,
        _redactor(),
        FailingAuditRepository(),
        policy_version="LEGAL_HOLD_OUTBOX_V1",
    )
    service = _build_service(repository, transactional_audit, MutableClock())

    hold = service.place_hold(
        _target(),
        reason_code="LITIGATION",
        actor_context=_actor("placer-1", frozenset({"LEGAL_HOLD_PLACER"})),
    )

    assert repository.get(hold.hold_reference_id) == hold
    assert len(transactional_audit.list_pending()) == 1


def test_fr_079_legal_hold_history_rejects_update_and_delete() -> None:
    service, repository, _, _ = _service()
    hold = service.place_hold(
        _target(),
        reason_code="LITIGATION",
        actor_context=_actor("placer-1", frozenset({"LEGAL_HOLD_PLACER"})),
    )

    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        repository.connection.execute(
            "UPDATE legal_hold_events SET reason_code = 'CHANGED' WHERE hold_reference_id = ?",
            (hold.hold_reference_id,),
        )
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        repository.connection.execute(
            "DELETE FROM legal_hold_events WHERE hold_reference_id = ?",
            (hold.hold_reference_id,),
        )

    assert repository.count_events() == 1


def test_bfr_lcm_002_resolver_reconstructs_historical_hold_state() -> None:
    service, repository, _, clock = _service()
    hold = service.place_hold(
        _target(),
        reason_code="LITIGATION",
        actor_context=_actor("placer-1", frozenset({"LEGAL_HOLD_PLACER"})),
    )
    clock.value = NOW + timedelta(hours=2)
    service.release_hold(
        hold.hold_reference_id,
        reason_code="CASE_CLOSED",
        actor_context=_actor("releaser-1", frozenset({"LEGAL_HOLD_RELEASER"})),
    )

    assert repository.list_active_holds(_record(), as_of=NOW - timedelta(seconds=1)) == ()
    assert len(repository.list_active_holds(_record(), as_of=NOW + timedelta(hours=1))) == 1
    assert repository.list_active_holds(_record(), as_of=clock.value) == ()


def _service() -> tuple[
    LegalHoldService,
    SQLiteLegalHoldRepository,
    SQLiteAuditRepository,
    MutableClock,
]:
    repository = SQLiteLegalHoldRepository()
    audit_repository = SQLiteAuditRepository()
    transactional_audit = SQLiteTransactionalAudit(
        repository.connection,
        _redactor(),
        audit_repository,
        policy_version="LEGAL_HOLD_OUTBOX_V1",
    )
    clock = MutableClock()
    service = _build_service(repository, transactional_audit, clock)
    return service, repository, audit_repository, clock


def _redactor() -> AuditRedactor:
    return AuditRedactor(
        AuditRedactionPolicy(
            version="LEGAL_HOLD_REDACTION_V1",
            allowed_fields_by_action={
                "LEGAL_HOLD_PLACED": frozenset(
                    {"status", "record_class", "policy_version", "scope_type"}
                ),
                "LEGAL_HOLD_RELEASED": frozenset({"status", "policy_version"}),
            },
        )
    )


def _build_service(
    repository: SQLiteLegalHoldRepository,
    transactional_audit: SQLiteTransactionalAudit,
    clock: MutableClock,
) -> LegalHoldService:
    return LegalHoldService(
        repository,
        transactional_audit,
        provisional_retention_catalog(),
        LegalHoldAccessPolicy(
            version="LEGAL_HOLD_ACCESS_V1",
            actor_policy_version=ACTOR_POLICY_VERSION,
            placement_roles=frozenset({"LEGAL_HOLD_PLACER"}),
            release_roles=frozenset({"LEGAL_HOLD_RELEASER"}),
            placement_reason_codes=frozenset({"LITIGATION", "REGULATORY_REVIEW"}),
            release_reason_codes=frozenset({"CASE_CLOSED", "REVIEW_COMPLETED"}),
        ),
        clock=clock,
    )


def _target() -> LegalHoldTarget:
    return LegalHoldTarget(
        record_reference_id="opaque-record-ref-1",
        record_class=RetentionRecordClass.BANKING_RECORD,
        scope_type=RetentionScopeType.DATASET,
        scope_id=DATASET_ID,
    )


def _record() -> RetentionRecordReference:
    return RetentionRecordReference(
        record_reference_id="opaque-record-ref-1",
        record_class=RetentionRecordClass.BANKING_RECORD,
        retention_trigger_at=datetime(2020, 1, 1, tzinfo=UTC),
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
        authentication_source="synthetic-ldap",
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
