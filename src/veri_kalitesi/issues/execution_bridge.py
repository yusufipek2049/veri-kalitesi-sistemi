"""Persisted execution sonuçlarını IssueTrigger'a dönüştüren adapter.

DS-05: Execution→issue trigger bridge.
- Kalite trigger'ları: eligible_for_auto_issue=True, failed_count>0, OFFICIAL mod,
  terminal SUCCESS, desteklenen measurement status (FAILED/WARNING).
- Teknik trigger'lar: terminal TECHNICAL_ERROR/TIMEOUT, source scope.
- Passed/shadow/partial/cancel/ineligible sonuçlar atlanır.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from veri_kalitesi.executions.models import (
    ExecutionMode,
    ExecutionStatus,
    MeasurementStatus,
    RuleExecution,
    RuleExecutionResult,
)
from veri_kalitesi.issues.models import (
    IssueScopeType,
    IssueTrigger,
    IssueTriggerType,
)


class ExecutionReader(Protocol):
    def get(self, execution_id: str) -> RuleExecution: ...

    def list_results(self, execution_id: str) -> list[RuleExecutionResult]: ...


_QUALITY_TRIGGER_STATUSES: frozenset[MeasurementStatus] = frozenset(
    {MeasurementStatus.FAILED, MeasurementStatus.WARNING}
)

_TECHNICAL_TRIGGER_STATUSES: frozenset[ExecutionStatus] = frozenset(
    {ExecutionStatus.TECHNICAL_ERROR, ExecutionStatus.TIMEOUT}
)

_TERMINAL_SUCCESS_STATUSES: frozenset[ExecutionStatus] = frozenset({ExecutionStatus.SUCCESS})


@dataclass(frozen=True)
class IssueGenerationSummary:
    """Bridge çağrısının ürettiği trigger ve atlama özetleri."""

    execution_id: str
    triggers: tuple[IssueTrigger, ...]
    skipped_rule_result_ids: tuple[str, ...]
    technical_trigger: IssueTrigger | None = None


@dataclass(frozen=True)
class ExecutionIssueTriggerAdapter:
    """Persisted execution/result kayıtlarından IssueTrigger üretir."""

    execution_reader: ExecutionReader

    def process_execution(self, execution_id: str) -> IssueGenerationSummary:
        execution = self.execution_reader.get(execution_id)
        results = self.execution_reader.list_results(execution_id)

        if _is_technical_terminal(execution):
            technical_trigger = _build_technical_trigger(execution)
            return IssueGenerationSummary(
                execution_id=execution_id,
                triggers=(technical_trigger,),
                skipped_rule_result_ids=tuple(result.rule_result_id for result in results),
                technical_trigger=technical_trigger,
            )

        if not _is_eligible_execution(execution):
            return IssueGenerationSummary(
                execution_id=execution_id,
                triggers=(),
                skipped_rule_result_ids=tuple(result.rule_result_id for result in results),
            )

        triggers: list[IssueTrigger] = []
        skipped: list[str] = []

        for result in results:
            trigger = _try_build_quality_trigger(execution, result)
            if trigger is not None:
                triggers.append(trigger)
            else:
                skipped.append(result.rule_result_id)

        return IssueGenerationSummary(
            execution_id=execution_id,
            triggers=tuple(triggers),
            skipped_rule_result_ids=tuple(skipped),
        )


def _is_technical_terminal(execution: RuleExecution) -> bool:
    return execution.status in _TECHNICAL_TRIGGER_STATUSES


def _is_eligible_execution(execution: RuleExecution) -> bool:
    if execution.execution_mode is not ExecutionMode.OFFICIAL:
        return False
    if execution.status not in _TERMINAL_SUCCESS_STATUSES:
        return False
    return True


def _try_build_quality_trigger(
    execution: RuleExecution,
    result: RuleExecutionResult,
) -> IssueTrigger | None:
    if not result.eligible_for_auto_issue:
        return None
    if result.failed_count is None or result.failed_count <= 0:
        return None
    if result.measurement_status not in _QUALITY_TRIGGER_STATUSES:
        return None

    scope_type, scope_id = _resolve_scope(execution)
    occurred_at = execution.finished_at or execution.started_at or execution.created_at
    title = _build_quality_title(result)
    deduplication_key = f"dq-issue:{result.rule_version_id}:{scope_type}:{scope_id}"

    return IssueTrigger(
        trigger_type=IssueTriggerType.QUALITY_THRESHOLD,
        scope_type=scope_type,
        scope_id=scope_id,
        deduplication_key=deduplication_key,
        occurred_at=occurred_at,
        correlation_id=execution.correlation_id,
        event_id=result.rule_result_id,
        title=title,
        execution_id=execution.execution_id,
        rule_version_id=result.rule_version_id,
        eligible_for_auto_issue=True,
        failed_count=result.failed_count,
        measurement_status=result.measurement_status.value if result.measurement_status else None,
    )


def _build_technical_trigger(execution: RuleExecution) -> IssueTrigger:
    scope_type, scope_id = _resolve_scope(execution)
    occurred_at = execution.finished_at or execution.started_at or execution.created_at
    title = f"Technical execution failure: {execution.status.value}"
    deduplication_key = f"dq-issue:technical:{execution.execution_id}:{scope_type}:{scope_id}"

    return IssueTrigger(
        trigger_type=IssueTriggerType.TECHNICAL_ERROR,
        scope_type=scope_type,
        scope_id=scope_id,
        deduplication_key=deduplication_key,
        occurred_at=occurred_at,
        correlation_id=execution.correlation_id,
        event_id=execution.execution_id,
        title=title,
        execution_id=execution.execution_id,
        rule_version_id=None,
        eligible_for_auto_issue=False,
        failed_count=None,
        measurement_status=MeasurementStatus.TECHNICAL_ERROR.value,
    )


def _resolve_scope(execution: RuleExecution) -> tuple[IssueScopeType, str]:
    if execution.scope:
        dataset_id = execution.scope.get("dataset_id")
        if dataset_id:
            return IssueScopeType.DATASET, str(dataset_id)
    if execution.source_ids:
        return IssueScopeType.SOURCE, execution.source_ids[0]
    if execution.scope:
        source_id = execution.scope.get("source_id")
        if source_id:
            return IssueScopeType.SOURCE, str(source_id)
    raise ValueError(
        f"Execution '{execution.execution_id}' has no resolvable scope for issue generation."
    )


def _build_quality_title(result: RuleExecutionResult) -> str:
    status = result.measurement_status.value if result.measurement_status else "UNKNOWN"
    failed = result.failed_count or 0
    population = result.population_count or 0
    return f"Quality threshold breach: {failed}/{population} failed ({status})"
