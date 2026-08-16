"""Cozum kaniti defteri birim testleri.

Kapatilan bosluk: cozum formu serbest metin bir UUID istiyordu ve girilen
degerin gercek bir kanita ait oldugu dogrulanmiyordu.

AC-01: Kanit adaylari kural calistirmasinin sonuc ve loglarindan turetilir.
AC-02: Kaydedilen kanit kendi UUID'sini alir; calistirma kimliginin bicimi onemsizdir.
AC-03: Ayni aday tekrar kaydedilirse yeni kayit uretilmez (idempotent).
AC-04: Kapsam disi aktor veri sizdirmayan hata alir.
AC-05: Cozum, kayitli olmayan veya baska issue'ya ait kaniti reddeder (fail-closed).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from veri_kalitesi.executions.models import (
    ExecutionAttempt,
    ExecutionStatus,
    MeasurementStatus,
    RuleExecution,
    RuleExecutionResult,
)
from veri_kalitesi.identity import (
    ActorContext,
    ActorContextIssuer,
    ActorType,
    DashboardAuthorizationDecision,
)
from veri_kalitesi.issues import (
    DataQualityIssue,
    IssueEvidenceKind,
    IssueEvidenceRecord,
    IssueEvidenceService,
    IssueNotFoundError,
    IssuePriority,
    IssueScopeType,
    IssueSourceEventType,
    IssueStatus,
    IssueTriggerType,
    IssueValidationError,
)
from veri_kalitesi.issues.evidence_candidates import (
    ExecutionIssueEvidenceCandidateProvider,
)

NOW = datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc)
POLICY_VERSION = "ISSUE_EVIDENCE_TEST_V1"


def _issue(
    *,
    issue_id: str = "issue-001",
    execution_id: str | None = "execution-not-a-uuid",
) -> DataQualityIssue:
    return DataQualityIssue(
        issue_id=issue_id,
        issue_no=f"DQI-{issue_id}",
        source_event_id="source-event-001",
        source_event_type=IssueSourceEventType.QUALITY,
        trigger_type=IssueTriggerType.QUALITY_THRESHOLD,
        scope_type=IssueScopeType.DATASET,
        scope_id="dataset-a",
        status=IssueStatus.INVESTIGATING,
        priority=IssuePriority.HIGH,
        assignee_user_id="assignee-001",
        deduplication_key_digest="sha256:dedup",
        occurrence_count=1,
        created_at=NOW - timedelta(days=1),
        updated_at=NOW,
        last_seen_at=NOW,
        source_execution_id=execution_id,
        source_rule_version_id="rule-version-001",
    )


class FakeIssueReader:
    def __init__(self, issues: dict[str, DataQualityIssue]) -> None:
        self._issues = issues

    def get(self, issue_id: str) -> DataQualityIssue:
        if issue_id not in self._issues:
            raise IssueNotFoundError("Issue not found.")
        return self._issues[issue_id]


class FakeEvidenceStore:
    def __init__(self) -> None:
        self.records: list[IssueEvidenceRecord] = []

    def list_evidence(self, issue_id: str) -> list[IssueEvidenceRecord]:
        return [record for record in self.records if record.issue_id == issue_id]

    def get_evidence(self, evidence_id: str) -> IssueEvidenceRecord | None:
        return next(
            (record for record in self.records if record.evidence_id == evidence_id),
            None,
        )

    def add_evidence(self, record: IssueEvidenceRecord) -> IssueEvidenceRecord:
        existing = next(
            (
                item
                for item in self.records
                if item.issue_id == record.issue_id and item.source_digest == record.source_digest
            ),
            None,
        )
        if existing is not None:
            return existing
        self.records.append(record)
        return record


class FakeExecutionReader:
    def __init__(self) -> None:
        self.execution = RuleExecution(
            execution_id="execution-not-a-uuid",
            idempotency_key_hash="hash",
            payload_hash="payload",
            rule_version_ids=("rule-version-001",),
            scope={},
            triggered_by="scheduler",
            correlation_id="corr-1",
            status=ExecutionStatus.SUCCESS,
            created_at=NOW - timedelta(hours=2),
            started_at=NOW - timedelta(hours=2),
            finished_at=NOW - timedelta(hours=1),
        )

    def get(self, execution_id: str) -> RuleExecution:
        if execution_id != self.execution.execution_id:
            raise LookupError("not found")
        return self.execution

    def list_results(self, execution_id: str) -> list[RuleExecutionResult]:
        return [
            RuleExecutionResult(
                execution_id=execution_id,
                rule_version_id="rule-version-001",
                population_count=1000,
                eligible_count=1000,
                evaluated_count=1000,
                passed_count=940,
                failed_count=60,
                excluded_count=0,
                technical_error_count=0,
                unknown_count=0,
                measurement_status=MeasurementStatus.FAILED,
                evidence={
                    "fingerprint": "sha256:" + "a" * 64,
                    "query_reference": "query://v1",
                    "plan_reference": "plan://v1",
                },
            )
        ]

    def list_attempts(self, execution_id: str) -> list[ExecutionAttempt]:
        return [
            ExecutionAttempt(
                execution_id=execution_id,
                attempt_no=1,
                status=ExecutionStatus.SUCCESS,
                created_at=NOW - timedelta(hours=2),
            )
        ]


class FakeAuthorizationService:
    def __init__(self, dataset_ids: frozenset[str] = frozenset({"dataset-a"})) -> None:
        self._dataset_ids = dataset_ids

    def authorize_dashboard(self, context: ActorContext | None) -> DashboardAuthorizationDecision:
        if context is None:
            return DashboardAuthorizationDecision(
                permitted_source_ids=frozenset(),
                permitted_dataset_ids=frozenset(),
                can_view_enterprise=False,
                policy_version=POLICY_VERSION,
            )
        return DashboardAuthorizationDecision(
            permitted_source_ids=frozenset(),
            permitted_dataset_ids=self._dataset_ids & context.permitted_dataset_ids,
            can_view_enterprise=False,
            policy_version=POLICY_VERSION,
        )


def _actor(dataset_ids: frozenset[str] = frozenset({"dataset-a"})) -> ActorContext:
    return ActorContextIssuer().issue(
        actor_id="assignee-001",
        actor_type=ActorType.USER,
        authentication_source="test-idp",
        session_id="test-session",
        roles=frozenset({"DATA_STEWARD"}),
        permitted_source_ids=frozenset(),
        permitted_dataset_ids=dataset_ids,
        can_view_enterprise=False,
        privileged=False,
        issued_at=NOW,
        expires_at=NOW + timedelta(minutes=15),
        policy_version=POLICY_VERSION,
        correlation_id="issue-evidence-test",
    )


def _service(
    store: FakeEvidenceStore,
    issues: dict[str, DataQualityIssue] | None = None,
) -> IssueEvidenceService:
    return IssueEvidenceService(
        issue_reader=FakeIssueReader(issues or {"issue-001": _issue()}),
        evidence_store=store,
        candidate_provider=ExecutionIssueEvidenceCandidateProvider(FakeExecutionReader()),
        authorization_service=FakeAuthorizationService(),
        clock=lambda: NOW,
    )


def test_ac01_candidates_are_derived_from_execution_results_and_logs() -> None:
    service = _service(FakeEvidenceStore())

    records, candidates = service.list_evidence(issue_id="issue-001", actor_context=_actor())

    assert records == ()
    kinds = {candidate.kind for candidate in candidates}
    assert kinds == {IssueEvidenceKind.EXECUTION_RESULT, IssueEvidenceKind.EXECUTION_LOG}
    result_candidate = next(
        item for item in candidates if item.kind is IssueEvidenceKind.EXECUTION_RESULT
    )
    assert result_candidate.failed_count == 60
    assert result_candidate.evaluated_count == 1000
    assert "60/1000" in result_candidate.label


def test_ac02_captured_evidence_gets_its_own_uuid_even_for_non_uuid_execution() -> None:
    from uuid import UUID

    store = FakeEvidenceStore()
    service = _service(store)
    _, candidates = service.list_evidence(issue_id="issue-001", actor_context=_actor())

    record = service.capture(
        issue_id="issue-001",
        candidate_key=candidates[0].candidate_key,
        actor_context=_actor(),
    )

    assert UUID(record.evidence_id)  # cozum formunun bekledigi UUID bicimi
    assert record.execution_id == "execution-not-a-uuid"
    assert record.issue_id == "issue-001"
    assert record.captured_by == "assignee-001"


def test_ac03_capturing_the_same_candidate_twice_is_idempotent() -> None:
    store = FakeEvidenceStore()
    service = _service(store)
    _, candidates = service.list_evidence(issue_id="issue-001", actor_context=_actor())
    key = candidates[0].candidate_key

    first = service.capture(issue_id="issue-001", candidate_key=key, actor_context=_actor())
    second = service.capture(issue_id="issue-001", candidate_key=key, actor_context=_actor())

    assert first.evidence_id == second.evidence_id
    assert len(store.records) == 1


def test_captured_candidate_disappears_from_pending_list() -> None:
    store = FakeEvidenceStore()
    service = _service(store)
    _, candidates = service.list_evidence(issue_id="issue-001", actor_context=_actor())
    service.capture(
        issue_id="issue-001",
        candidate_key=candidates[0].candidate_key,
        actor_context=_actor(),
    )

    records, pending = service.list_evidence(issue_id="issue-001", actor_context=_actor())

    assert len(records) == 1
    assert candidates[0].candidate_key not in {item.candidate_key for item in pending}


def test_ac04_out_of_scope_actor_gets_not_found() -> None:
    service = _service(FakeEvidenceStore())

    with pytest.raises(IssueNotFoundError):
        service.list_evidence(
            issue_id="issue-001",
            actor_context=_actor(dataset_ids=frozenset({"dataset-b"})),
        )


def test_unknown_candidate_key_is_rejected() -> None:
    service = _service(FakeEvidenceStore())

    with pytest.raises(IssueValidationError):
        service.capture(
            issue_id="issue-001",
            candidate_key="RESULT:execution-not-a-uuid:rule-version-999",
            actor_context=_actor(),
        )


def test_issue_without_source_execution_has_no_candidates() -> None:
    store = FakeEvidenceStore()
    service = _service(
        store,
        issues={"issue-002": _issue(issue_id="issue-002", execution_id=None)},
    )

    records, candidates = service.list_evidence(issue_id="issue-002", actor_context=_actor())

    assert records == ()
    assert candidates == ()
