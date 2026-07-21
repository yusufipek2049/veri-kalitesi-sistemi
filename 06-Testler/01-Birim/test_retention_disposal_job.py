from __future__ import annotations

import sqlite3
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from veri_kalitesi.audit import (
    AuditRedactionPolicy,
    AuditRedactor,
    AuditResult,
    SQLiteAuditRepository,
    SQLiteTransactionalAudit,
)
from veri_kalitesi.identity import ActorContext, ActorContextIssuer, ActorType
from veri_kalitesi.retention import (
    DisposalJobAccessPolicy,
    DisposalJobService,
    DisposalJobStatus,
    LegalHold,
    RetentionAuthorizationError,
    RetentionConflictError,
    RetentionEvaluator,
    RetentionPolicyCatalog,
    RetentionRecordClass,
    RetentionRecordReference,
    RetentionReviewStatus,
    RetentionScopeType,
    RetentionTechnicalError,
    RetentionValidationError,
    SQLiteDisposalJobRepository,
    provisional_retention_catalog,
)


UTC = timezone.utc
NOW = datetime(2030, 3, 1, 12, 0, tzinfo=UTC)
ACTOR_POLICY_VERSION = "ACTOR_POLICY_V1"
DATASET_ID = "dataset-retention-1"
RECORD_REFERENCE_ID = "opaque-record-reference-1"


@dataclass
class MutableClock:
    value: datetime = NOW

    def __call__(self) -> datetime:
        return self.value


class MutableLegalHoldResolver:
    def __init__(self) -> None:
        self.holds: tuple[LegalHold, ...] = ()

    def list_active_holds(
        self,
        record_reference: RetentionRecordReference,
        *,
        as_of: datetime,
    ) -> tuple[LegalHold, ...]:
        del record_reference, as_of
        return self.holds


def test_bfr_lcm_003_prepares_data_minimum_job_with_atomic_audit() -> None:
    service, repository, audit_repository, _ = _service()

    job = _prepare(service)

    assert job.status is DisposalJobStatus.PREPARED
    assert job.record_reference_digest != RECORD_REFERENCE_ID
    assert job.scope_digest != DATASET_ID
    assert job.approval_reference == "APPROVAL:RETENTION:001"
    assert repository.count_jobs() == 1
    audit = audit_repository.list_events()[0]
    assert audit.action == "DISPOSAL_JOB_PREPARED"
    assert audit.new_value_summary == {
        "disposal_method": "CONTROLLED_DESTRUCTION",
        "policy_version": "RETENTION_POLICY_2026_07_PROVISIONAL_V1",
        "record_class": "BANKING_RECORD",
        "scope_type": "DATASET",
        "status": "PREPARED",
    }
    assert RECORD_REFERENCE_ID not in str(audit.new_value_summary)
    assert DATASET_ID not in str(audit.new_value_summary)


def test_bfr_lcm_003_same_idempotency_key_returns_single_job_and_audit() -> None:
    service, repository, audit_repository, _ = _service()

    first = _prepare(service)
    second = _prepare(service)

    assert second == first
    assert repository.count_jobs() == 1
    assert len(audit_repository.list_events()) == 1


def test_bfr_lcm_003_reused_idempotency_key_with_different_payload_is_rejected() -> None:
    service, repository, _, _ = _service()
    _prepare(service)

    with pytest.raises(RetentionConflictError, match="different payload"):
        _prepare(service, approval_reference="APPROVAL:RETENTION:002")

    assert repository.count_jobs() == 1


def test_nfr_cmp_001_provisional_policy_cannot_prepare_disposal_job() -> None:
    service, repository, _, _ = _service(catalog=provisional_retention_catalog())

    with pytest.raises(RetentionValidationError, match="COMPLIANCE_REVIEW_REQUIRED"):
        _prepare(service)

    assert repository.count_jobs() == 0


def test_bfr_lcm_002_active_legal_hold_blocks_disposal_job() -> None:
    resolver = MutableLegalHoldResolver()
    resolver.holds = (_active_hold(),)
    service, repository, _, _ = _service(resolver=resolver)

    with pytest.raises(RetentionValidationError, match="LEGAL_HOLD"):
        _prepare(service)

    assert repository.count_jobs() == 0


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
def test_nfr_sec_001_unauthorized_actor_cannot_prepare_job(
    actor_kind: str,
) -> None:
    service, repository, _, _ = _service()
    actor_context: ActorContext | None = None
    if actor_kind == "wrong-role":
        actor_context = _actor("user-1", frozenset({"DATA_VIEWER"}))
    elif actor_kind == "wrong-scope":
        actor_context = _actor(
            "user-1",
            frozenset({"DISPOSAL_PREPARER"}),
            dataset_ids=frozenset({"another-dataset"}),
        )
    elif actor_kind == "service-account":
        actor_context = _actor(
            "service-1",
            frozenset({"DISPOSAL_PREPARER"}),
            actor_type=ActorType.SERVICE,
        )
    elif actor_kind == "break-glass":
        actor_context = _actor(
            "break-glass-1",
            frozenset({"DISPOSAL_PREPARER"}),
            actor_type=ActorType.BREAK_GLASS,
        )

    with pytest.raises(RetentionAuthorizationError):
        _prepare(
            service,
            actor_context=actor_context,
            use_default_actor=actor_kind != "untrusted",
        )

    assert repository.count_jobs() == 0


def test_bfr_lcm_003_trusted_worker_records_success_evidence_once() -> None:
    resolver = MutableLegalHoldResolver()
    service, repository, audit_repository, _ = _service(resolver=resolver)
    job = _prepare(service)

    completed = _record_success(service, job.job_id)
    resolver.holds = (_active_hold(),)
    replayed = _record_success(service, job.job_id)

    assert completed.status is DisposalJobStatus.SUCCEEDED
    assert completed.result is not None
    assert completed.result.affected_record_count == 125
    assert completed.result.failed_record_count == 0
    assert replayed == completed
    assert repository.count_results() == 1
    audits = audit_repository.list_events()
    assert len(audits) == 2
    assert audits[1].action == "DISPOSAL_JOB_RESULT_RECORDED"
    assert audits[1].result is AuditResult.SUCCESS
    assert audits[1].new_value_summary == {
        "affected_record_count": 125,
        "disposal_method": "CONTROLLED_DESTRUCTION",
        "failed_record_count": 0,
        "status": "SUCCEEDED",
        "technical_error_code": None,
    }


def test_bfr_lcm_003_technical_failure_is_distinct_and_data_minimum() -> None:
    service, _, audit_repository, _ = _service()
    job = _prepare(service)

    failed = service.record_result(
        job.job_id,
        _record(),
        status=DisposalJobStatus.FAILED_TECHNICAL,
        affected_record_count=0,
        failed_record_count=1,
        evidence_reference="EVIDENCE:DISPOSAL:TECHNICAL:001",
        technical_error_code="ADAPTER_UNAVAILABLE",
        actor_context=_worker(),
    )

    assert failed.status is DisposalJobStatus.FAILED_TECHNICAL
    audit = audit_repository.list_events()[-1]
    assert audit.result is AuditResult.FAILURE
    assert audit.new_value_summary["technical_error_code"] == "ADAPTER_UNAVAILABLE"
    assert "raw" not in str(audit.new_value_summary).lower()


def test_nfr_sec_001_normal_user_cannot_record_worker_result() -> None:
    service, repository, _, _ = _service()
    job = _prepare(service)

    with pytest.raises(RetentionAuthorizationError):
        _record_success(
            service,
            job.job_id,
            actor_context=_actor("user-2", frozenset({"DISPOSAL_RESULT_WRITER"})),
        )

    assert repository.count_results() == 0


def test_bfr_sod_002_preparer_identity_cannot_record_result_as_service() -> None:
    service, repository, _, _ = _service()
    job = _prepare(service)

    with pytest.raises(RetentionAuthorizationError, match="different trusted actor"):
        _record_success(
            service,
            job.job_id,
            actor_context=_actor(
                "preparer-1",
                frozenset({"DISPOSAL_RESULT_WRITER"}),
                actor_type=ActorType.SERVICE,
            ),
        )

    assert repository.count_results() == 0


def test_bfr_lcm_002_hold_added_after_preparation_blocks_result() -> None:
    resolver = MutableLegalHoldResolver()
    service, repository, _, _ = _service(resolver=resolver)
    job = _prepare(service)
    resolver.holds = (_active_hold(),)

    with pytest.raises(RetentionValidationError, match="LEGAL_HOLD"):
        _record_success(service, job.job_id)

    assert repository.count_results() == 0


def test_bfr_lcm_003_different_terminal_result_is_rejected() -> None:
    service, repository, _, _ = _service()
    job = _prepare(service)
    _record_success(service, job.job_id)

    with pytest.raises(RetentionConflictError, match="different terminal result"):
        service.record_result(
            job.job_id,
            _record(),
            status=DisposalJobStatus.FAILED_TECHNICAL,
            affected_record_count=0,
            failed_record_count=1,
            evidence_reference="EVIDENCE:DISPOSAL:TECHNICAL:001",
            technical_error_code="ADAPTER_UNAVAILABLE",
            actor_context=_worker(),
        )

    assert repository.count_results() == 1


def test_bfr_aud_004_audit_stage_failure_rolls_back_job() -> None:
    service, repository, _, _ = _service()

    def fail_stage(*args: object, **kwargs: object) -> None:
        raise RuntimeError("synthetic audit stage outage")

    service.transactional_audit.stage = fail_stage  # type: ignore[method-assign]

    with pytest.raises(RetentionTechnicalError, match="could not be persisted"):
        _prepare(service)

    assert repository.count_jobs() == 0


def test_bfr_aud_004_audit_stage_failure_rolls_back_result() -> None:
    service, repository, _, _ = _service()
    job = _prepare(service)

    def fail_stage(*args: object, **kwargs: object) -> None:
        raise RuntimeError("synthetic audit stage outage")

    service.transactional_audit.stage = fail_stage  # type: ignore[method-assign]

    with pytest.raises(RetentionTechnicalError, match="could not be persisted"):
        _record_success(service, job.job_id)

    assert repository.count_results() == 0


def test_fr_079_disposal_history_rejects_update_and_delete() -> None:
    service, repository, _, _ = _service()
    job = _prepare(service)
    _record_success(service, job.job_id)

    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        repository.connection.execute(
            "UPDATE disposal_jobs SET reason_code = 'CHANGED' WHERE job_id = ?",
            (job.job_id,),
        )
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        repository.connection.execute(
            "DELETE FROM disposal_job_results WHERE job_id = ?",
            (job.job_id,),
        )


def test_bfr_lcm_003_job_and_result_survive_repository_reopen(tmp_path: Path) -> None:
    database = str(tmp_path / "disposal.sqlite")
    service, repository, _, _ = _service(database=database)
    job = _prepare(service)
    completed = _record_success(service, job.job_id)
    repository.connection.close()

    reopened = SQLiteDisposalJobRepository(database)

    assert reopened.get(job.job_id) == completed


def _service(
    *,
    catalog: RetentionPolicyCatalog | None = None,
    resolver: MutableLegalHoldResolver | None = None,
    database: str = ":memory:",
) -> tuple[
    DisposalJobService,
    SQLiteDisposalJobRepository,
    SQLiteAuditRepository,
    MutableClock,
]:
    repository = SQLiteDisposalJobRepository(database)
    audit_repository = SQLiteAuditRepository()
    transactional_audit = SQLiteTransactionalAudit(
        repository.connection,
        _redactor(),
        audit_repository,
        policy_version="DISPOSAL_OUTBOX_V1",
    )
    clock = MutableClock()
    evaluator = RetentionEvaluator(
        catalog or _approved_catalog(),
        resolver or MutableLegalHoldResolver(),
    )
    service = DisposalJobService(
        repository,
        transactional_audit,
        evaluator,
        DisposalJobAccessPolicy(
            version="DISPOSAL_ACCESS_V1",
            actor_policy_version=ACTOR_POLICY_VERSION,
            preparation_roles=frozenset({"DISPOSAL_PREPARER"}),
            result_roles=frozenset({"DISPOSAL_RESULT_WRITER"}),
            preparation_reason_codes=frozenset({"RETENTION_PERIOD_EXPIRED"}),
            technical_error_codes=frozenset({"ADAPTER_UNAVAILABLE", "EVIDENCE_WRITE_FAILED"}),
        ),
        clock=clock,
    )
    return service, repository, audit_repository, clock


def _redactor() -> AuditRedactor:
    return AuditRedactor(
        AuditRedactionPolicy(
            version="DISPOSAL_REDACTION_V1",
            allowed_fields_by_action={
                "DISPOSAL_JOB_PREPARED": frozenset(
                    {
                        "status",
                        "record_class",
                        "policy_version",
                        "disposal_method",
                        "scope_type",
                    }
                ),
                "DISPOSAL_JOB_RESULT_RECORDED": frozenset(
                    {
                        "status",
                        "disposal_method",
                        "affected_record_count",
                        "failed_record_count",
                        "technical_error_code",
                    }
                ),
            },
        )
    )


def _prepare(
    service: DisposalJobService,
    *,
    approval_reference: str = "APPROVAL:RETENTION:001",
    actor_context: ActorContext | None = None,
    use_default_actor: bool = True,
):
    selected_actor = actor_context
    if selected_actor is None and use_default_actor:
        selected_actor = _actor("preparer-1", frozenset({"DISPOSAL_PREPARER"}))
    return service.prepare_job(
        _record(),
        scope_type=RetentionScopeType.DATASET,
        scope_id=DATASET_ID,
        approval_reference=approval_reference,
        reason_code="RETENTION_PERIOD_EXPIRED",
        idempotency_key="disposal-request-001",
        actor_context=selected_actor,
    )


def _record_success(
    service: DisposalJobService,
    job_id: str,
    *,
    actor_context: ActorContext | None = None,
):
    return service.record_result(
        job_id,
        _record(),
        status=DisposalJobStatus.SUCCEEDED,
        affected_record_count=125,
        failed_record_count=0,
        evidence_reference="EVIDENCE:DISPOSAL:SUCCESS:001",
        technical_error_code=None,
        actor_context=actor_context or _worker(),
    )


def _record() -> RetentionRecordReference:
    return RetentionRecordReference(
        record_reference_id=RECORD_REFERENCE_ID,
        record_class=RetentionRecordClass.BANKING_RECORD,
        retention_trigger_at=datetime(2020, 2, 29, 12, 0, tzinfo=UTC),
    )


def _approved_catalog() -> RetentionPolicyCatalog:
    catalog = provisional_retention_catalog()
    policies = tuple(
        replace(
            policy,
            review_status=RetentionReviewStatus.APPROVED_BY_BANK,
            approval_reference="SYNTHETIC:BANK:APPROVAL",
        )
        if policy.record_class is RetentionRecordClass.BANKING_RECORD
        else policy
        for policy in catalog.policies
    )
    return replace(catalog, policies=policies)


def _active_hold() -> LegalHold:
    return LegalHold(
        hold_reference_id="hold-reference-1",
        record_reference_id=RECORD_REFERENCE_ID,
        record_class=RetentionRecordClass.BANKING_RECORD,
        policy_version=provisional_retention_catalog().version,
        decision_owner_role="LEGAL_HOLD_AUTHORITY",
        effective_at=NOW - timedelta(days=1),
    )


def _worker() -> ActorContext:
    return _actor(
        "worker-1",
        frozenset({"DISPOSAL_RESULT_WRITER"}),
        actor_type=ActorType.SERVICE,
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
