from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import sqlite3

import pytest

from veri_kalitesi.audit import (
    AuditRedactor,
    PreparedAuditEvent,
    SQLiteAuditRepository,
    SQLiteTransactionalAudit,
    build_default_redaction_policy,
)
from veri_kalitesi.identity import ActorContext, ActorContextIssuer, ActorType
from veri_kalitesi.scoring import (
    DatasetPartialScorePolicy,
    DatasetPartialScorePolicyLifecycleService,
    DatasetPartialScorePolicyService,
    PartialExecutionFacts,
    PartialScoreEligibility,
    PartialScorePolicyAccessPolicy,
    PartialScorePolicyStatus,
    ScoringAuthorizationError,
    ScoringTechnicalError,
    ScoringValidationError,
    SQLiteDatasetPartialScorePolicyRepository,
)


AT = datetime(2026, 7, 21, 10, 0, tzinfo=timezone.utc)
ACTOR_POLICY_VERSION = "BANK_ACTOR_V1"


def _policy(
    *,
    policy_version: str = "DATASET_PARTIAL_V1",
    effective_from: datetime = AT,
    allow_official_partial_score: bool = True,
) -> DatasetPartialScorePolicy:
    return DatasetPartialScorePolicy(
        policy_id=f"policy-{policy_version}",
        dataset_id="dataset-main",
        policy_version=policy_version,
        allow_official_partial_score=allow_official_partial_score,
        minimum_coverage_ratio=Decimal("0.90"),
        required_critical_rule_ids=("rule-critical",),
        required_partitions=("partition-required",),
        maximum_missing_record_ratio=Decimal("0.05"),
        maximum_technical_error_ratio=Decimal("0.10"),
        minimum_successful_rule_ratio=Decimal("0.75"),
        effective_from=effective_from,
        approval_status=PartialScorePolicyStatus.APPROVED,
        created_by="maker-1",
        approved_by="checker-1",
        audit_reference=f"audit-{policy_version}",
        created_at=effective_from,
    )


def _facts() -> PartialExecutionFacts:
    return PartialExecutionFacts(
        dataset_id="dataset-main",
        coverage_ratio=Decimal("0.95"),
        executed_rule_ids=("rule-critical", "rule-2", "rule-3", "rule-4"),
        technical_error_rule_ids=(),
        completed_partitions=("partition-required", "partition-optional"),
        missing_record_ratio=Decimal("0.01"),
        total_rule_count=4,
    )


def test_fr_048_open_018_approved_policy_is_versioned_and_effective_by_time() -> None:
    repository = SQLiteDatasetPartialScorePolicyRepository()
    first = _policy(effective_from=AT - timedelta(days=1))
    second = _policy(
        policy_version="DATASET_PARTIAL_V2",
        effective_from=AT + timedelta(hours=1),
    )

    repository.save(first)
    repository.save(second)

    assert repository.list_policies("dataset-main") == [first, second]
    assert repository.resolve_effective("dataset-main", at=AT) == first
    assert repository.resolve_effective("dataset-main", at=AT + timedelta(hours=2)) == second


def test_fr_048_uc_009_all_partial_policy_conditions_allow_official_score() -> None:
    repository = SQLiteDatasetPartialScorePolicyRepository()
    repository.save(_policy())
    service = DatasetPartialScorePolicyService(repository)

    decision = service.evaluate(_facts(), at=AT)

    assert decision.eligibility is PartialScoreEligibility.OFFICIAL
    assert decision.reason_codes == ("ALL_POLICY_CONDITIONS_MET",)
    assert decision.policy_version == "DATASET_PARTIAL_V1"
    assert decision.executed_rule_count == 4
    assert decision.not_executed_rule_count == 0
    assert decision.missing_partitions == ()


@pytest.mark.parametrize(
    ("policy", "facts", "reason_code"),
    [
        (
            _policy(allow_official_partial_score=False),
            _facts(),
            "OFFICIAL_PARTIAL_DISABLED",
        ),
        (
            _policy(),
            replace(_facts(), coverage_ratio=Decimal("0.89")),
            "COVERAGE_BELOW_MINIMUM",
        ),
        (
            _policy(),
            replace(
                _facts(),
                executed_rule_ids=("rule-2", "rule-3", "rule-4"),
            ),
            "REQUIRED_CRITICAL_RULE_MISSING",
        ),
        (
            _policy(),
            replace(_facts(), completed_partitions=("partition-optional",)),
            "REQUIRED_PARTITION_MISSING",
        ),
        (
            _policy(),
            replace(_facts(), missing_record_ratio=Decimal("0.06")),
            "MISSING_RECORD_RATIO_EXCEEDED",
        ),
        (
            _policy(),
            replace(
                _facts(),
                executed_rule_ids=("rule-critical", "rule-2", "rule-3"),
                technical_error_rule_ids=("rule-4",),
            ),
            "TECHNICAL_ERROR_RATIO_EXCEEDED",
        ),
        (
            _policy(),
            replace(
                _facts(),
                executed_rule_ids=("rule-critical", "rule-2"),
            ),
            "SUCCESSFUL_RULE_RATIO_BELOW_MINIMUM",
        ),
    ],
)
def test_fr_048_open_018_any_failed_condition_is_provisional(
    policy: DatasetPartialScorePolicy,
    facts: PartialExecutionFacts,
    reason_code: str,
) -> None:
    repository = SQLiteDatasetPartialScorePolicyRepository()
    repository.save(policy)
    service = DatasetPartialScorePolicyService(repository)

    decision = service.evaluate(facts, at=AT)

    assert decision.eligibility is PartialScoreEligibility.PROVISIONAL
    assert reason_code in decision.reason_codes


def test_fr_048_open_018_missing_policy_fails_closed_as_provisional() -> None:
    service = DatasetPartialScorePolicyService(SQLiteDatasetPartialScorePolicyRepository())

    decision = service.evaluate(_facts(), at=AT)

    assert decision.eligibility is PartialScoreEligibility.PROVISIONAL
    assert decision.reason_codes == ("POLICY_NOT_FOUND",)
    assert decision.policy_version is None


def test_fr_048_open_012_unapproved_policy_is_not_effective() -> None:
    repository = SQLiteDatasetPartialScorePolicyRepository()
    repository.save(
        replace(
            _policy(),
            approval_status=PartialScorePolicyStatus.PENDING,
            approved_by=None,
            audit_reference=None,
        )
    )
    service = DatasetPartialScorePolicyService(repository)

    decision = service.evaluate(_facts(), at=AT)

    assert decision.eligibility is PartialScoreEligibility.PROVISIONAL
    assert decision.reason_codes == ("POLICY_NOT_FOUND",)


def test_fr_048_open_012_creator_cannot_approve_same_partial_policy() -> None:
    repository = SQLiteDatasetPartialScorePolicyRepository()
    policy = replace(_policy(), approved_by="maker-1")

    with pytest.raises(ScoringValidationError, match="creator cannot approve"):
        repository.save(policy)

    assert repository.list_policies("dataset-main") == []


def test_fr_048_partial_execution_facts_reject_conflicting_rule_outcomes() -> None:
    repository = SQLiteDatasetPartialScorePolicyRepository()
    repository.save(_policy())
    service = DatasetPartialScorePolicyService(repository)
    facts = replace(
        _facts(),
        technical_error_rule_ids=("rule-critical",),
    )

    with pytest.raises(ScoringValidationError, match="must be disjoint"):
        service.evaluate(facts, at=AT)


def test_fr_048_partial_policy_repository_failure_is_technical_error() -> None:
    repository = SQLiteDatasetPartialScorePolicyRepository()
    repository.connection.close()

    with pytest.raises(ScoringTechnicalError):
        repository.resolve_effective("dataset-main", at=AT)


def test_fr_048_rule_005_fr_077_partial_policy_requires_different_checker_and_audit() -> None:
    lifecycle, repository, audit_repository = _lifecycle()

    pending = _submit(lifecycle, _context("maker-1", {"PARTIAL_POLICY_MAKER"}))
    before_approval = DatasetPartialScorePolicyService(repository).evaluate(_facts(), at=AT)
    approved = lifecycle.decide(
        actor_context=_context("checker-1", {"PARTIAL_POLICY_CHECKER"}),
        policy_id=pending.policy_id,
        decision="APPROVE",
        reason_code="PARTIAL_POLICY.REVIEWED",
    )
    after_approval = DatasetPartialScorePolicyService(repository).evaluate(_facts(), at=AT)

    assert pending.approval_status is PartialScorePolicyStatus.PENDING
    assert before_approval.eligibility is PartialScoreEligibility.PROVISIONAL
    assert approved.approval_status is PartialScorePolicyStatus.APPROVED
    assert approved.approved_by == "checker-1"
    assert approved.audit_reference is not None
    assert after_approval.eligibility is PartialScoreEligibility.OFFICIAL
    events = audit_repository.list_events()
    assert [event.action for event in events] == [
        "PARTIAL_SCORE_POLICY_APPROVAL_REQUESTED",
        "PARTIAL_SCORE_POLICY_APPROVAL_DECIDED",
    ]
    assert events[-1].new_value_summary["status"] == "APPROVED"
    assert events[-1].new_value_summary["required_critical_rule_count"] == 1
    assert events[-1].new_value_summary["required_partition_count"] == 1
    assert "rule-critical" not in repr(events)
    assert "partition-required" not in repr(events)


def test_rule_005_policy_maker_cannot_decide_same_change() -> None:
    lifecycle, repository, audit_repository = _lifecycle()
    maker = _context(
        "maker-1",
        {"PARTIAL_POLICY_MAKER", "PARTIAL_POLICY_CHECKER"},
    )
    pending = _submit(lifecycle, maker)

    with pytest.raises(ScoringAuthorizationError, match="maker cannot decide"):
        lifecycle.decide(
            actor_context=maker,
            policy_id=pending.policy_id,
            decision="APPROVE",
            reason_code="PARTIAL_POLICY.REVIEWED",
        )

    assert repository.get(pending.policy_id).approval_status is PartialScorePolicyStatus.PENDING
    assert len(audit_repository.list_events()) == 1


def test_rule_005_rejected_partial_policy_never_becomes_effective() -> None:
    lifecycle, repository, audit_repository = _lifecycle()
    pending = _submit(lifecycle, _context("maker-1", {"PARTIAL_POLICY_MAKER"}))

    rejected = lifecycle.decide(
        actor_context=_context("checker-1", {"PARTIAL_POLICY_CHECKER"}),
        policy_id=pending.policy_id,
        decision="REJECT",
        reason_code="PARTIAL_POLICY.REJECTED",
    )
    decision = DatasetPartialScorePolicyService(repository).evaluate(_facts(), at=AT)

    assert rejected.approval_status is PartialScorePolicyStatus.REJECTED
    assert rejected.approved_by is None
    assert decision.eligibility is PartialScoreEligibility.PROVISIONAL
    assert decision.reason_codes == ("POLICY_NOT_FOUND",)
    assert audit_repository.list_events()[-1].new_value_summary["status"] == "REJECTED"


@pytest.mark.parametrize(
    "context_kind",
    ["missing", "missing-role", "missing-scope", "privileged", "service"],
)
def test_rule_005_untrusted_partial_policy_submission_is_rejected_before_write(
    context_kind: str,
) -> None:
    lifecycle, repository, audit_repository = _lifecycle()
    contexts = {
        "missing": None,
        "missing-role": _context("actor-1", set()),
        "missing-scope": _context(
            "actor-1",
            {"PARTIAL_POLICY_MAKER"},
            dataset_ids=set(),
        ),
        "privileged": _context(
            "actor-1",
            {"PARTIAL_POLICY_MAKER"},
            privileged=True,
        ),
        "service": _context(
            "service-1",
            {"PARTIAL_POLICY_MAKER"},
            actor_type=ActorType.SERVICE,
        ),
    }

    with pytest.raises(ScoringAuthorizationError):
        _submit(lifecycle, contexts[context_kind])

    assert repository.list_policies("dataset-main") == []
    assert audit_repository.list_events() == []


def test_fr_077_audit_stage_failure_rolls_back_partial_policy_submission() -> None:
    repository = SQLiteDatasetPartialScorePolicyRepository()
    audit_repository = SQLiteAuditRepository()
    audit = FailingPartialPolicyAudit(
        repository.connection,
        AuditRedactor(build_default_redaction_policy()),
        audit_repository,
        policy_version="PARTIAL_POLICY_AUDIT_V1",
    )
    lifecycle = _lifecycle_service(repository, audit)

    with pytest.raises(ScoringTechnicalError):
        _submit(lifecycle, _context("maker-1", {"PARTIAL_POLICY_MAKER"}))

    assert repository.list_policies("dataset-main") == []
    assert audit_repository.list_events() == []


class FailingPartialPolicyAudit(SQLiteTransactionalAudit):
    def stage(self, prepared: PreparedAuditEvent) -> None:
        raise sqlite3.OperationalError("synthetic audit outbox failure")


def _lifecycle() -> tuple[
    DatasetPartialScorePolicyLifecycleService,
    SQLiteDatasetPartialScorePolicyRepository,
    SQLiteAuditRepository,
]:
    repository = SQLiteDatasetPartialScorePolicyRepository()
    audit_repository = SQLiteAuditRepository()
    audit = SQLiteTransactionalAudit(
        repository.connection,
        AuditRedactor(build_default_redaction_policy()),
        audit_repository,
        policy_version="PARTIAL_POLICY_AUDIT_V1",
    )
    return _lifecycle_service(repository, audit), repository, audit_repository


def _lifecycle_service(
    repository: SQLiteDatasetPartialScorePolicyRepository,
    audit: SQLiteTransactionalAudit,
) -> DatasetPartialScorePolicyLifecycleService:
    return DatasetPartialScorePolicyLifecycleService(
        repository,
        transactional_audit=audit,
        access_policy=PartialScorePolicyAccessPolicy(
            version="PARTIAL_POLICY_ACCESS_V1",
            actor_policy_version=ACTOR_POLICY_VERSION,
            maker_roles=frozenset({"PARTIAL_POLICY_MAKER"}),
            checker_roles=frozenset({"PARTIAL_POLICY_CHECKER"}),
        ),
        clock=lambda: AT,
    )


def _submit(
    lifecycle: DatasetPartialScorePolicyLifecycleService,
    context: ActorContext | None,
) -> DatasetPartialScorePolicy:
    return lifecycle.create_and_submit(
        actor_context=context,
        dataset_id="dataset-main",
        policy_version="DATASET_PARTIAL_LIFECYCLE_V1",
        allow_official_partial_score=True,
        minimum_coverage_ratio=Decimal("0.90"),
        required_critical_rule_ids=("rule-critical",),
        required_partitions=("partition-required",),
        maximum_missing_record_ratio=Decimal("0.05"),
        maximum_technical_error_ratio=Decimal("0.10"),
        minimum_successful_rule_ratio=Decimal("0.75"),
        effective_from=AT,
    )


def _context(
    actor_id: str,
    roles: set[str],
    *,
    dataset_ids: set[str] | None = None,
    actor_type: ActorType = ActorType.USER,
    privileged: bool = False,
) -> ActorContext:
    return ActorContextIssuer().issue(
        actor_id=actor_id,
        actor_type=actor_type,
        authentication_source="synthetic-identity-adapter",
        session_id=f"session-{actor_id}",
        roles=frozenset(roles),
        permitted_source_ids=frozenset(),
        permitted_dataset_ids=frozenset({"dataset-main"} if dataset_ids is None else dataset_ids),
        can_view_enterprise=False,
        privileged=privileged,
        issued_at=AT - timedelta(minutes=5),
        expires_at=AT + timedelta(hours=1),
        policy_version=ACTOR_POLICY_VERSION,
        correlation_id=f"correlation-{actor_id}",
    )
