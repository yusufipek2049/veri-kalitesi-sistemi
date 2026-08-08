"""DS-05: Otomatik issue üretimi ve manuel issue oluşturma birim testleri.

Kapsam:
- OwnershipIssueAssignmentResolver (quality/technical/manual chain)
- ExecutionIssueTriggerAdapter (quality/technical trigger, skip conditions)
- ManualIssueDraft validation + digest_idempotency_key
- issue_source_event_type MANUAL mapping
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from veri_kalitesi.data_sources.models import (
    Dataset,
    DatasetType,
    DataSource,
    SourceType,
)
from veri_kalitesi.executions.models import (
    ExecutionMode,
    ExecutionStatus,
    ExecutionType,
    MeasurementStatus,
    RuleExecution,
    RuleExecutionResult,
    WorkloadClass,
)
from veri_kalitesi.issues import (
    IssueAssignmentError,
    IssueAssigneeProfile,
    IssuePriority,
    IssueScopeType,
    IssueSourceEventType,
    IssueTrigger,
    IssueTriggerType,
)
from veri_kalitesi.issues.assignment import OwnershipIssueAssignmentResolver
from veri_kalitesi.issues.execution_bridge import (
    ExecutionIssueTriggerAdapter,
)
from veri_kalitesi.issues.models import (
    ManualIssueDraft,
    digest_idempotency_key,
    issue_source_event_type,
    validate_manual_issue_draft,
)
from veri_kalitesi.issues.service import IssueAssigneeDirectory
from veri_kalitesi.rules.models import (
    QualityDimension,
    QualityRule,
    RuleCriticality,
    RuleStatus,
    RuleType,
    RuleVersion,
)


# ---------------------------------------------------------------------------
# Sabitler
# ---------------------------------------------------------------------------

NOW = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)
OWNER_USER_ID = "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa"
SCOPE_DATASET_ID = "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb"
SCOPE_SOURCE_ID = "cccccccc-cccc-4ccc-cccc-cccccccccccc"
RULE_VERSION_ID = "dddddddd-dddd-4ddd-dddd-dddddddddddd"
QUALITY_RULE_ID = "eeeeeeee-eeee-4eee-eeee-eeeeeeeeeeee"
EXECUTION_ID = "ffffffff-ffff-4fff-ffff-ffffffffffff"
CORRELATION_ID = "corr-00000000-0000-4000-8000-000000000000"


# ---------------------------------------------------------------------------
# Stub lookup sınıfları (Protocol implementasyonları)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _StubRuleVersionLookup:
    version: RuleVersion

    def get_version(self, rule_version_id: str) -> RuleVersion:
        if rule_version_id == self.version.rule_version_id:
            return self.version
        raise KeyError(f"version {rule_version_id} not found")


@dataclass(frozen=True)
class _StubRuleLookup:
    rule: QualityRule

    def get_rule(self, quality_rule_id: str) -> QualityRule:
        if quality_rule_id == self.rule.quality_rule_id:
            return self.rule
        raise KeyError(f"rule {quality_rule_id} not found")


@dataclass(frozen=True)
class _StubDatasetLookup:
    dataset: Dataset

    def get_dataset(self, dataset_id: str) -> Dataset:
        if dataset_id == self.dataset.dataset_id:
            return self.dataset
        raise KeyError(f"dataset {dataset_id} not found")


@dataclass(frozen=True)
class _StubDataSourceLookup:
    source: DataSource

    def get_data_source(self, data_source_id: str) -> DataSource:
        if data_source_id == self.source.data_source_id:
            return self.source
        raise KeyError(f"source {data_source_id} not found")


# ---------------------------------------------------------------------------
# Stub IssueAssigneeDirectory (Protocol implementasyonu)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _InMemoryAssigneeDirectory:
    profile: IssueAssigneeProfile

    def get_assignee_profile(self, user_id: str) -> IssueAssigneeProfile | None:
        if user_id == self.profile.user_id:
            return self.profile
        return None


# ---------------------------------------------------------------------------
# Yardımcı factory fonksiyonları
# ---------------------------------------------------------------------------


def _make_rule_version(
    *,
    criticality: RuleCriticality = RuleCriticality.HIGH,
    rule_version_id: str = RULE_VERSION_ID,
    quality_rule_id: str = QUALITY_RULE_ID,
) -> RuleVersion:
    return RuleVersion(
        quality_rule_id=quality_rule_id,
        version_no=1,
        rule_type=RuleType.REQUIRED,
        definition={"column": "test_col"},
        threshold=0.95,
        weight=1.0,
        criticality=criticality,
        rule_version_id=rule_version_id,
    )


def _make_quality_rule(
    *,
    owner_user_id: str = OWNER_USER_ID,
    quality_rule_id: str = QUALITY_RULE_ID,
) -> QualityRule:
    return QualityRule(
        code="DQ_NULL_CHECK",
        name="Null check",
        dataset_id=SCOPE_DATASET_ID,
        field_ids=("field-1",),
        primary_dimension=QualityDimension.COMPLETENESS,
        owner_user_id=owner_user_id,
        status=RuleStatus.ACTIVE,
        quality_rule_id=quality_rule_id,
    )


def _make_dataset(
    *,
    dataset_id: str = SCOPE_DATASET_ID,
    owner_user_id: str | None = OWNER_USER_ID,
    data_source_id: str = "source-parent-0000-0000-000000000000",
) -> Dataset:
    return Dataset(
        data_source_id=data_source_id,
        namespace="public",
        name="test_table",
        dataset_type=DatasetType.TABLE,
        owner_user_id=owner_user_id,
        dataset_id=dataset_id,
    )


def _make_source(
    *,
    source_id: str = SCOPE_SOURCE_ID,
    owner_user_id: str | None = OWNER_USER_ID,
) -> DataSource:
    return DataSource(
        name="test_source",
        source_type=SourceType.POSTGRESQL,
        connection_config={"host": "localhost"},
        secret_reference="secret/ref",
        owner_user_id=owner_user_id,
        data_source_id=source_id,
    )


def _make_assignee_directory(
    *,
    user_id: str = OWNER_USER_ID,
    active: bool = True,
    permitted_dataset_ids: frozenset[str] | None = None,
    permitted_source_ids: frozenset[str] | None = None,
) -> _InMemoryAssigneeDirectory:
    profile = IssueAssigneeProfile(
        user_id=user_id,
        active=active,
        permitted_source_ids=permitted_source_ids
        if permitted_source_ids is not None
        else frozenset({SCOPE_SOURCE_ID}),
        permitted_dataset_ids=permitted_dataset_ids
        if permitted_dataset_ids is not None
        else frozenset({SCOPE_DATASET_ID}),
    )
    return _InMemoryAssigneeDirectory(profile)


def _make_resolver(
    *,
    rule_version: RuleVersion | None = None,
    quality_rule: QualityRule | None = None,
    dataset: Dataset | None = None,
    source: DataSource | None = None,
    directory: IssueAssigneeDirectory | None = None,
) -> OwnershipIssueAssignmentResolver:
    rv = rule_version or _make_rule_version()
    qr = quality_rule or _make_quality_rule()
    ds = dataset or _make_dataset()
    src = source or _make_source()
    dir_ = directory or _make_assignee_directory()
    return OwnershipIssueAssignmentResolver(
        rule_version_lookup=_StubRuleVersionLookup(rv),
        rule_lookup=_StubRuleLookup(qr),
        dataset_lookup=_StubDatasetLookup(ds),
        data_source_lookup=_StubDataSourceLookup(src),
        assignee_directory=dir_,
    )


def _make_execution(
    *,
    status: ExecutionStatus = ExecutionStatus.SUCCESS,
    mode: ExecutionMode = ExecutionMode.OFFICIAL,
    scope: dict | None = None,
    source_ids: tuple[str, ...] = (),
) -> RuleExecution:
    return RuleExecution(
        idempotency_key_hash="hash",
        payload_hash="phash",
        rule_version_ids=(RULE_VERSION_ID,),
        scope=scope or {"dataset_id": SCOPE_DATASET_ID},
        triggered_by="test",
        correlation_id=CORRELATION_ID,
        source_ids=source_ids,
        workload_class=WorkloadClass.LIGHT,
        execution_type=ExecutionType.MANUAL,
        execution_mode=mode,
        status=status,
        execution_id=EXECUTION_ID,
        started_at=NOW,
        finished_at=NOW,
    )


def _make_result(
    *,
    eligible: bool = True,
    failed_count: int = 5,
    status: MeasurementStatus = MeasurementStatus.FAILED,
    rule_version_id: str = RULE_VERSION_ID,
) -> RuleExecutionResult:
    return RuleExecutionResult(
        execution_id=EXECUTION_ID,
        rule_version_id=rule_version_id,
        population_count=100,
        eligible_count=100,
        evaluated_count=100,
        passed_count=95,
        failed_count=failed_count,
        excluded_count=0,
        technical_error_count=0,
        unknown_count=0,
        measurement_status=status,
        eligible_for_auto_issue=eligible,
    )


# ---------------------------------------------------------------------------
# OwnershipIssueAssignmentResolver testleri
# ---------------------------------------------------------------------------


class TestOwnershipAssignmentResolver:
    def test_quality_trigger_resolves_rule_owner(self) -> None:
        resolver = _make_resolver()
        trigger = IssueTrigger(
            trigger_type=IssueTriggerType.QUALITY_THRESHOLD,
            scope_type=IssueScopeType.DATASET,
            scope_id=SCOPE_DATASET_ID,
            deduplication_key="dq-issue:rv:ds",
            occurred_at=NOW,
            correlation_id=CORRELATION_ID,
            rule_version_id=RULE_VERSION_ID,
        )
        assignment = resolver.resolve_assignment(trigger)
        assert assignment.assignee_user_id == OWNER_USER_ID
        assert assignment.priority is IssuePriority.HIGH

    def test_quality_trigger_critical_maps_to_critical_priority(self) -> None:
        rv = _make_rule_version(criticality=RuleCriticality.CRITICAL)
        resolver = _make_resolver(rule_version=rv)
        trigger = IssueTrigger(
            trigger_type=IssueTriggerType.CRITICAL_RULE_FAILURE,
            scope_type=IssueScopeType.DATASET,
            scope_id=SCOPE_DATASET_ID,
            deduplication_key="dq-issue:crit",
            occurred_at=NOW,
            correlation_id=CORRELATION_ID,
            rule_version_id=RULE_VERSION_ID,
        )
        assignment = resolver.resolve_assignment(trigger)
        assert assignment.priority is IssuePriority.CRITICAL

    def test_technical_trigger_resolves_source_owner(self) -> None:
        resolver = _make_resolver()
        trigger = IssueTrigger(
            trigger_type=IssueTriggerType.TECHNICAL_ERROR,
            scope_type=IssueScopeType.SOURCE,
            scope_id=SCOPE_SOURCE_ID,
            deduplication_key="dq-issue:tech",
            occurred_at=NOW,
            correlation_id=CORRELATION_ID,
        )
        assignment = resolver.resolve_assignment(trigger)
        assert assignment.assignee_user_id == OWNER_USER_ID
        assert assignment.priority is IssuePriority.HIGH

    def test_manual_dataset_trigger_resolves_dataset_owner(self) -> None:
        resolver = _make_resolver()
        trigger = IssueTrigger(
            trigger_type=IssueTriggerType.MANUAL,
            scope_type=IssueScopeType.DATASET,
            scope_id=SCOPE_DATASET_ID,
            deduplication_key="dq-issue:manual",
            occurred_at=NOW,
            correlation_id=CORRELATION_ID,
        )
        assignment = resolver.resolve_assignment(trigger)
        assert assignment.assignee_user_id == OWNER_USER_ID
        assert assignment.priority is IssuePriority.MEDIUM

    def test_manual_source_trigger_resolves_source_owner(self) -> None:
        resolver = _make_resolver()
        trigger = IssueTrigger(
            trigger_type=IssueTriggerType.MANUAL,
            scope_type=IssueScopeType.SOURCE,
            scope_id=SCOPE_SOURCE_ID,
            deduplication_key="dq-issue:manual-src",
            occurred_at=NOW,
            correlation_id=CORRELATION_ID,
        )
        assignment = resolver.resolve_assignment(trigger)
        assert assignment.assignee_user_id == OWNER_USER_ID

    def test_dataset_owner_fallback_to_source_owner(self) -> None:
        source = _make_source(owner_user_id=OWNER_USER_ID)
        dataset = _make_dataset(
            owner_user_id=None,
            data_source_id=source.data_source_id,
        )
        directory = _make_assignee_directory()
        resolver = _make_resolver(dataset=dataset, source=source, directory=directory)
        trigger = IssueTrigger(
            trigger_type=IssueTriggerType.MANUAL,
            scope_type=IssueScopeType.DATASET,
            scope_id=SCOPE_DATASET_ID,
            deduplication_key="dq-issue:fallback",
            occurred_at=NOW,
            correlation_id=CORRELATION_ID,
        )
        assignment = resolver.resolve_assignment(trigger)
        assert assignment.assignee_user_id == OWNER_USER_ID

    def test_no_owner_raises_assignment_error(self) -> None:
        source = _make_source(owner_user_id=None)
        resolver = _make_resolver(source=source)
        trigger = IssueTrigger(
            trigger_type=IssueTriggerType.TECHNICAL_ERROR,
            scope_type=IssueScopeType.SOURCE,
            scope_id=SCOPE_SOURCE_ID,
            deduplication_key="dq-issue:no-owner",
            occurred_at=NOW,
            correlation_id=CORRELATION_ID,
        )
        with pytest.raises(IssueAssignmentError, match="No owner"):
            resolver.resolve_assignment(trigger)

    def test_inactive_owner_raises_assignment_error(self) -> None:
        directory = _make_assignee_directory(active=False)
        resolver = _make_resolver(directory=directory)
        trigger = IssueTrigger(
            trigger_type=IssueTriggerType.MANUAL,
            scope_type=IssueScopeType.SOURCE,
            scope_id=SCOPE_SOURCE_ID,
            deduplication_key="dq-issue:inactive",
            occurred_at=NOW,
            correlation_id=CORRELATION_ID,
        )
        with pytest.raises(IssueAssignmentError, match="not active"):
            resolver.resolve_assignment(trigger)

    def test_out_of_scope_owner_raises_assignment_error(self) -> None:
        directory = _make_assignee_directory(
            permitted_source_ids=frozenset(),
            permitted_dataset_ids=frozenset(),
        )
        resolver = _make_resolver(directory=directory)
        trigger = IssueTrigger(
            trigger_type=IssueTriggerType.MANUAL,
            scope_type=IssueScopeType.SOURCE,
            scope_id=SCOPE_SOURCE_ID,
            deduplication_key="dq-issue:scope",
            occurred_at=NOW,
            correlation_id=CORRELATION_ID,
        )
        with pytest.raises(IssueAssignmentError, match="not permitted"):
            resolver.resolve_assignment(trigger)

    def test_quality_trigger_without_rule_version_raises(self) -> None:
        resolver = _make_resolver()
        trigger = IssueTrigger(
            trigger_type=IssueTriggerType.QUALITY_THRESHOLD,
            scope_type=IssueScopeType.DATASET,
            scope_id=SCOPE_DATASET_ID,
            deduplication_key="dq-issue:no-rv",
            occurred_at=NOW,
            correlation_id=CORRELATION_ID,
            rule_version_id=None,
        )
        with pytest.raises(IssueAssignmentError, match="rule_version_id"):
            resolver.resolve_assignment(trigger)


# ---------------------------------------------------------------------------
# ExecutionIssueTriggerAdapter testleri
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _StubExecutionReader:
    execution: RuleExecution
    results: list[RuleExecutionResult]

    def get(self, execution_id: str) -> RuleExecution:
        return self.execution

    def list_results(self, execution_id: str) -> list[RuleExecutionResult]:
        return self.results


class TestExecutionIssueTriggerAdapter:
    def test_quality_trigger_from_eligible_failed_result(self) -> None:
        execution = _make_execution()
        result = _make_result()
        reader = _StubExecutionReader(execution, [result])
        adapter = ExecutionIssueTriggerAdapter(execution_reader=reader)

        summary = adapter.process_execution(EXECUTION_ID)

        assert len(summary.triggers) == 1
        trigger = summary.triggers[0]
        assert trigger.trigger_type is IssueTriggerType.QUALITY_THRESHOLD
        assert trigger.scope_type is IssueScopeType.DATASET
        assert trigger.scope_id == SCOPE_DATASET_ID
        assert trigger.execution_id == EXECUTION_ID
        assert trigger.rule_version_id == RULE_VERSION_ID
        assert trigger.title != ""
        assert len(summary.skipped_rule_result_ids) == 0

    def test_skips_ineligible_result(self) -> None:
        execution = _make_execution()
        result = _make_result(eligible=False)
        reader = _StubExecutionReader(execution, [result])
        adapter = ExecutionIssueTriggerAdapter(execution_reader=reader)

        summary = adapter.process_execution(EXECUTION_ID)

        assert len(summary.triggers) == 0
        assert result.rule_result_id in summary.skipped_rule_result_ids

    def test_skips_passed_result(self) -> None:
        execution = _make_execution()
        result = _make_result(failed_count=0, status=MeasurementStatus.PASSED)
        reader = _StubExecutionReader(execution, [result])
        adapter = ExecutionIssueTriggerAdapter(execution_reader=reader)

        summary = adapter.process_execution(EXECUTION_ID)

        assert len(summary.triggers) == 0

    def test_skips_shadow_execution(self) -> None:
        execution = _make_execution(mode=ExecutionMode.SHADOW)
        result = _make_result()
        reader = _StubExecutionReader(execution, [result])
        adapter = ExecutionIssueTriggerAdapter(execution_reader=reader)

        summary = adapter.process_execution(EXECUTION_ID)

        assert len(summary.triggers) == 0

    def test_technical_error_produces_technical_trigger(self) -> None:
        execution = _make_execution(status=ExecutionStatus.TECHNICAL_ERROR)
        result = _make_result()
        reader = _StubExecutionReader(execution, [result])
        adapter = ExecutionIssueTriggerAdapter(execution_reader=reader)

        summary = adapter.process_execution(EXECUTION_ID)

        assert summary.technical_trigger is not None
        assert summary.technical_trigger.trigger_type is IssueTriggerType.TECHNICAL_ERROR
        assert len(summary.triggers) == 1
        assert result.rule_result_id in summary.skipped_rule_result_ids

    def test_timeout_produces_technical_trigger(self) -> None:
        execution = _make_execution(status=ExecutionStatus.TIMEOUT)
        reader = _StubExecutionReader(execution, [])
        adapter = ExecutionIssueTriggerAdapter(
            execution_reader=reader,
        )

        summary = adapter.process_execution(EXECUTION_ID)

        assert summary.technical_trigger is not None
        assert summary.technical_trigger.trigger_type is IssueTriggerType.TECHNICAL_ERROR

    def test_source_scope_resolution_from_source_ids(self) -> None:
        execution = _make_execution(
            scope={"source_id": SCOPE_SOURCE_ID},
            source_ids=(SCOPE_SOURCE_ID,),
        )
        result = _make_result()
        reader = _StubExecutionReader(execution, [result])
        adapter = ExecutionIssueTriggerAdapter(execution_reader=reader)

        summary = adapter.process_execution(EXECUTION_ID)

        assert len(summary.triggers) == 1
        # scope has no dataset_id, so falls through to source_ids
        assert summary.triggers[0].scope_id == SCOPE_SOURCE_ID

    def test_multiple_results_produce_multiple_triggers(self) -> None:
        execution = _make_execution()
        results = [
            _make_result(failed_count=10, status=MeasurementStatus.FAILED),
            _make_result(failed_count=3, status=MeasurementStatus.WARNING),
            _make_result(eligible=False),
        ]
        reader = _StubExecutionReader(execution, results)
        adapter = ExecutionIssueTriggerAdapter(execution_reader=reader)

        summary = adapter.process_execution(EXECUTION_ID)

        assert len(summary.triggers) == 2
        assert len(summary.skipped_rule_result_ids) == 1


# ---------------------------------------------------------------------------
# ManualIssueDraft validation + yardımcı fonksiyon testleri
# ---------------------------------------------------------------------------


class TestManualIssueDraftValidation:
    def test_valid_draft_passes(self) -> None:
        draft = ManualIssueDraft(
            title="Manuel kalite sorunu",
            scope_type=IssueScopeType.DATASET,
            scope_id=SCOPE_DATASET_ID,
            priority=IssuePriority.HIGH,
            idempotency_key="MANUAL_V1:test-key",
            creator_user_id=OWNER_USER_ID,
        )
        validate_manual_issue_draft(draft)  # no exception

    def test_empty_title_raises(self) -> None:
        draft = ManualIssueDraft(
            title="",
            scope_type=IssueScopeType.DATASET,
            scope_id=SCOPE_DATASET_ID,
            priority=IssuePriority.HIGH,
            idempotency_key="MANUAL_V1:key",
            creator_user_id=OWNER_USER_ID,
        )
        with pytest.raises(Exception):
            validate_manual_issue_draft(draft)

    def test_title_over_200_chars_raises(self) -> None:
        draft = ManualIssueDraft(
            title="x" * 201,
            scope_type=IssueScopeType.DATASET,
            scope_id=SCOPE_DATASET_ID,
            priority=IssuePriority.HIGH,
            idempotency_key="MANUAL_V1:key",
            creator_user_id=OWNER_USER_ID,
        )
        with pytest.raises(Exception):
            validate_manual_issue_draft(draft)

    def test_invalid_scope_id_raises(self) -> None:
        draft = ManualIssueDraft(
            title="Test",
            scope_type=IssueScopeType.DATASET,
            scope_id="not-a-uuid",
            priority=IssuePriority.HIGH,
            idempotency_key="MANUAL_V1:key",
            creator_user_id=OWNER_USER_ID,
        )
        with pytest.raises(Exception):
            validate_manual_issue_draft(draft)

    def test_title_with_markup_raises(self) -> None:
        draft = ManualIssueDraft(
            title="<script>alert('xss')</script>",
            scope_type=IssueScopeType.DATASET,
            scope_id=SCOPE_DATASET_ID,
            priority=IssuePriority.HIGH,
            idempotency_key="MANUAL_V1:key",
            creator_user_id=OWNER_USER_ID,
        )
        with pytest.raises(Exception):
            validate_manual_issue_draft(draft)


class TestDigestIdempotencyKey:
    def test_produces_sha256_hex(self) -> None:
        digest = digest_idempotency_key("test-key-123")
        assert len(digest) == 64
        assert all(c in "0123456789abcdef" for c in digest)

    def test_same_input_same_digest(self) -> None:
        assert digest_idempotency_key("abc") == digest_idempotency_key("abc")

    def test_different_input_different_digest(self) -> None:
        assert digest_idempotency_key("abc") != digest_idempotency_key("def")

    def test_strips_whitespace(self) -> None:
        assert digest_idempotency_key("  key  ") == digest_idempotency_key("key")


class TestIssueSourceEventTypeMapping:
    def test_manual_maps_to_manual(self) -> None:
        assert issue_source_event_type(IssueTriggerType.MANUAL) is IssueSourceEventType.MANUAL

    def test_technical_maps_to_technical(self) -> None:
        assert (
            issue_source_event_type(IssueTriggerType.TECHNICAL_ERROR)
            is IssueSourceEventType.TECHNICAL
        )

    def test_quality_threshold_maps_to_quality(self) -> None:
        assert (
            issue_source_event_type(IssueTriggerType.QUALITY_THRESHOLD)
            is IssueSourceEventType.QUALITY
        )

    def test_critical_rule_failure_maps_to_quality(self) -> None:
        assert (
            issue_source_event_type(IssueTriggerType.CRITICAL_RULE_FAILURE)
            is IssueSourceEventType.QUALITY
        )
