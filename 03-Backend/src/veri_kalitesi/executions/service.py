"""İdempotent manuel iş oluşturma ve sınırlı retry worker servisi."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from datetime import timedelta
from time import sleep
from typing import Any, Protocol
from uuid import uuid4

from veri_kalitesi.data_sources.models import DataSourceStatus
from veri_kalitesi.executions.errors import (
    ExecutionTechnicalError,
    ExecutionTimeoutError,
    ExecutionValidationError,
)
from veri_kalitesi.executions.models import (
    ConcurrencyPolicy,
    ExecutionAttempt,
    ExecutionStatus,
    ExecutionTimeouts,
    ExecutionType,
    RetryPolicy,
    RuleExecution,
    RuleExecutionResult,
    RuleResultComputation,
    WorkloadClass,
    utc_now,
)
from veri_kalitesi.executions.repository import SQLiteExecutionRepository
from veri_kalitesi.executions.source_usage_policies import SourceUsagePolicyResolver
from veri_kalitesi.rules.models import RuleStatus, RuleVersion


_FORBIDDEN_SCOPE_KEYS = {
    "api_key",
    "authorization",
    "credential",
    "credentials",
    "password",
    "secret",
    "token",
}


class RuleCatalog(Protocol):
    def get_rule(self, quality_rule_id: str) -> Any: ...

    def get_version(self, rule_version_id: str) -> RuleVersion: ...

    def list_versions(self, quality_rule_id: str) -> list[RuleVersion]: ...


class SourceCatalog(Protocol):
    def get_dataset(self, dataset_id: str) -> Any: ...

    def get_data_source(self, data_source_id: str) -> Any: ...


class ExecutionExecutor(Protocol):
    def execute(
        self,
        *,
        execution: RuleExecution,
        versions: tuple[RuleVersion, ...],
        timeouts: ExecutionTimeouts,
    ) -> tuple[RuleResultComputation, ...]: ...


class TechnicalEventSink(Protocol):
    def notify_technical_failure(self, execution: RuleExecution) -> None: ...


class ExecutionCancellationSink(Protocol):
    def request_cancel(self, execution: RuleExecution) -> None: ...


class WorkloadClassifier(Protocol):
    def classify(
        self,
        versions: tuple[RuleVersion, ...],
        scope: Mapping[str, Any],
    ) -> WorkloadClass: ...


class DefaultWorkloadClassifier:
    def classify(
        self,
        versions: tuple[RuleVersion, ...],
        scope: Mapping[str, Any],
    ) -> WorkloadClass:
        return WorkloadClass.LIGHT


class ExecutionService:
    def __init__(
        self,
        repository: SQLiteExecutionRepository,
        rule_catalog: RuleCatalog,
        source_catalog: SourceCatalog,
        executor: ExecutionExecutor,
        *,
        timeouts: ExecutionTimeouts | None = None,
        retry_policy: RetryPolicy | None = None,
        concurrency_policy: ConcurrencyPolicy | None = None,
        source_usage_policy_resolver: SourceUsagePolicyResolver | None = None,
        workload_classifier: WorkloadClassifier | None = None,
        technical_event_sink: TechnicalEventSink | None = None,
        cancellation_sink: ExecutionCancellationSink | None = None,
        sleeper: Callable[[float], None] = sleep,
        clock: Callable[[], Any] = utc_now,
    ) -> None:
        self.repository = repository
        self.rule_catalog = rule_catalog
        self.source_catalog = source_catalog
        self.executor = executor
        self.timeouts = timeouts or ExecutionTimeouts()
        self.retry_policy = retry_policy or RetryPolicy()
        if concurrency_policy is not None and source_usage_policy_resolver is not None:
            raise ExecutionValidationError(
                "Concurrency policy and source usage policy resolver cannot be combined."
            )
        self.concurrency_policy = concurrency_policy or ConcurrencyPolicy()
        self.source_usage_policy_resolver = source_usage_policy_resolver
        self.workload_classifier = workload_classifier or DefaultWorkloadClassifier()
        self.technical_event_sink = technical_event_sink
        self.cancellation_sink = cancellation_sink
        self.sleeper = sleeper
        self.clock = clock
        _validate_policy(self.timeouts, self.retry_policy)
        _validate_concurrency_policy(self.concurrency_policy)

    def start_manual(
        self,
        *,
        actor_id: str,
        idempotency_key: str,
        rule_version_ids: tuple[str, ...],
        scope: Mapping[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> RuleExecution:
        return self._start(
            execution_type=ExecutionType.MANUAL,
            actor_id=actor_id,
            idempotency_key=idempotency_key,
            rule_version_ids=rule_version_ids,
            scope=scope,
            correlation_id=correlation_id,
        )

    def start_scheduled(
        self,
        *,
        idempotency_key: str,
        rule_version_ids: tuple[str, ...],
        scope: Mapping[str, Any],
        correlation_id: str,
    ) -> RuleExecution:
        return self._start(
            execution_type=ExecutionType.SCHEDULED,
            actor_id="scheduler",
            idempotency_key=idempotency_key,
            rule_version_ids=rule_version_ids,
            scope=scope,
            correlation_id=correlation_id,
        )

    def validate_rule_versions(self, rule_version_ids: tuple[str, ...]) -> tuple[str, ...]:
        if not rule_version_ids or len(set(rule_version_ids)) != len(rule_version_ids):
            raise ExecutionValidationError("Rule versions must be non-empty and unique.")
        versions = tuple(self.rule_catalog.get_version(item) for item in rule_version_ids)
        return self._validate_versions(versions)

    def _start(
        self,
        *,
        execution_type: ExecutionType,
        actor_id: str,
        idempotency_key: str,
        rule_version_ids: tuple[str, ...],
        scope: Mapping[str, Any] | None,
        correlation_id: str | None,
    ) -> RuleExecution:
        _validate_start(actor_id, idempotency_key, rule_version_ids)
        versions = tuple(self.rule_catalog.get_version(item) for item in rule_version_ids)
        source_ids = self._validate_versions(versions)
        normalized_scope = dict(scope or {})
        _reject_sensitive_scope(normalized_scope)
        workload_class = self.workload_classifier.classify(versions, normalized_scope)
        if not isinstance(workload_class, WorkloadClass):
            raise ExecutionValidationError("Workload classifier returned an invalid class.")
        payload_hash = _hash_payload(rule_version_ids, normalized_scope)
        execution = RuleExecution(
            idempotency_key_hash=_hash_text(idempotency_key),
            payload_hash=payload_hash,
            rule_version_ids=rule_version_ids,
            scope=normalized_scope,
            triggered_by=actor_id,
            correlation_id=correlation_id or str(uuid4()),
            source_ids=source_ids,
            workload_class=workload_class,
            execution_type=execution_type,
            created_at=self.clock(),
        )
        stored, _ = self.repository.create_or_get(execution)
        return stored

    def cancel_execution(self, *, actor_id: str, execution_id: str, reason: str) -> RuleExecution:
        if not actor_id.strip():
            raise ExecutionValidationError("actor_id is required.")
        if not reason.strip() or len(reason) > 500:
            raise ExecutionValidationError("Cancellation reason must contain 1 to 500 characters.")
        previous = self.repository.get(execution_id)
        cancelled = self.repository.request_cancel(
            execution_id,
            actor_id=actor_id,
            reason=reason,
            requested_at=self.clock(),
        )
        if (
            cancelled.status is ExecutionStatus.CANCEL_REQUESTED
            and previous.status is ExecutionStatus.RUNNING
            and self.cancellation_sink is not None
        ):
            self.cancellation_sink.request_cancel(cancelled)
        return cancelled

    def run_next(self) -> RuleExecution | None:
        self.close_expired_cancellations()
        concurrency_policy = (
            self.source_usage_policy_resolver.resolve_concurrency_policy()
            if self.source_usage_policy_resolver is not None
            else self.concurrency_policy
        )
        execution = self.repository.claim_next(self.clock(), concurrency_policy)
        if execution is None:
            return None
        versions = tuple(self.rule_catalog.get_version(item) for item in execution.rule_version_ids)
        last_error: ExecutionTechnicalError | None = None
        for attempt_no in range(1, self.retry_policy.max_attempts + 1):
            try:
                computations = self.executor.execute(
                    execution=execution,
                    versions=versions,
                    timeouts=self.timeouts,
                )
                _validate_computations(execution, computations)
                self.repository.add_attempt(
                    ExecutionAttempt(
                        execution_id=execution.execution_id,
                        attempt_no=attempt_no,
                        status=ExecutionStatus.SUCCESS,
                        created_at=self.clock(),
                    )
                )
                results = tuple(
                    RuleExecutionResult(
                        execution_id=execution.execution_id,
                        rule_version_id=item.rule_version_id,
                        checked_count=item.checked_count,
                        passed_count=item.passed_count,
                        failed_count=item.failed_count,
                        not_evaluated_count=item.not_evaluated_count,
                        completed_partitions=item.completed_partitions,
                    )
                    for item in computations
                )
                return self.repository.complete_success(
                    execution.execution_id, results, self.clock()
                )
            except ExecutionTimeoutError as exc:
                _validate_partial_computations(execution, exc.partial_results)
                _validate_partitions(exc.completed_partitions)
                attempt_status = (
                    ExecutionStatus.PARTIAL if exc.partial_results else ExecutionStatus.TIMEOUT
                )
                self.repository.add_attempt(
                    ExecutionAttempt(
                        execution_id=execution.execution_id,
                        attempt_no=attempt_no,
                        status=attempt_status,
                        error_class=exc.error_class,
                        retryable=False,
                        created_at=self.clock(),
                    )
                )
                results = tuple(
                    RuleExecutionResult(
                        execution_id=execution.execution_id,
                        rule_version_id=item.rule_version_id,
                        checked_count=item.checked_count,
                        passed_count=item.passed_count,
                        failed_count=item.failed_count,
                        not_evaluated_count=item.not_evaluated_count,
                        completed_partitions=(
                            item.completed_partitions or exc.completed_partitions
                        ),
                        eligible_for_official_scoring=False,
                    )
                    for item in exc.partial_results
                )
                failed = self.repository.complete_timeout(
                    execution.execution_id,
                    exc.error_class,
                    results,
                    self.clock(),
                )
                if (
                    failed.status is not ExecutionStatus.CANCELLED
                    and self.technical_event_sink is not None
                ):
                    self.technical_event_sink.notify_technical_failure(failed)
                return failed
            except ExecutionTechnicalError as exc:
                last_error = exc
                self.repository.add_attempt(
                    ExecutionAttempt(
                        execution_id=execution.execution_id,
                        attempt_no=attempt_no,
                        status=ExecutionStatus.TECHNICAL_ERROR,
                        error_class=exc.error_class,
                        retryable=exc.retryable,
                        created_at=self.clock(),
                    )
                )
                if not exc.retryable or attempt_no == self.retry_policy.max_attempts:
                    break
                self.sleeper(self.retry_policy.base_delay_seconds * (2 ** (attempt_no - 1)))
            except Exception:
                last_error = ExecutionTechnicalError("UNEXPECTED", retryable=False)
                self.repository.add_attempt(
                    ExecutionAttempt(
                        execution_id=execution.execution_id,
                        attempt_no=attempt_no,
                        status=ExecutionStatus.TECHNICAL_ERROR,
                        error_class=last_error.error_class,
                        retryable=False,
                        created_at=self.clock(),
                    )
                )
                break

        if last_error is None:
            raise ExecutionValidationError("Execution ended without a result.")
        failed = self.repository.complete_technical_error(
            execution.execution_id, last_error.error_class, self.clock()
        )
        if self.technical_event_sink is not None:
            self.technical_event_sink.notify_technical_failure(failed)
        return failed

    def close_expired_cancellations(self) -> tuple[RuleExecution, ...]:
        now = self.clock()
        closed: list[RuleExecution] = []
        for execution in self.repository.list_cancel_requested():
            if execution.started_at is None:
                continue
            deadline = execution.started_at + timedelta(seconds=self.timeouts.total_seconds)
            if deadline <= now:
                closed.append(self.repository.complete_cancelled(execution.execution_id, now))
        return tuple(closed)

    def _validate_versions(self, versions: tuple[RuleVersion, ...]) -> tuple[str, ...]:
        source_ids: list[str] = []
        for version in versions:
            rule = self.rule_catalog.get_rule(version.quality_rule_id)
            if rule.status is not RuleStatus.ACTIVE:
                raise ExecutionValidationError("Manual execution requires active rules.")
            available = self.rule_catalog.list_versions(rule.quality_rule_id)
            if not available or available[-1].rule_version_id != version.rule_version_id:
                raise ExecutionValidationError("Manual execution requires the latest rule version.")
            dataset = self.source_catalog.get_dataset(rule.dataset_id)
            source = self.source_catalog.get_data_source(dataset.data_source_id)
            if source.status is not DataSourceStatus.ACTIVE:
                raise ExecutionValidationError("Execution requires an active data source.")
            source_ids.append(source.data_source_id)
        return tuple(dict.fromkeys(source_ids))


def _validate_start(actor_id: str, key: str, version_ids: tuple[str, ...]) -> None:
    if not actor_id.strip():
        raise ExecutionValidationError("actor_id is required.")
    if not key.strip() or len(key) > 200:
        raise ExecutionValidationError("Idempotency key must contain 1 to 200 characters.")
    if not version_ids or len(set(version_ids)) != len(version_ids):
        raise ExecutionValidationError("Rule versions must be non-empty and unique.")


def _validate_policy(timeouts: ExecutionTimeouts, policy: RetryPolicy) -> None:
    values = (timeouts.connection_seconds, timeouts.query_seconds, timeouts.total_seconds)
    if any(isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in values):
        raise ExecutionValidationError("Execution timeouts must be positive integers.")
    if timeouts.total_seconds < max(timeouts.connection_seconds, timeouts.query_seconds):
        raise ExecutionValidationError("Total timeout must cover connection and query timeouts.")
    if (
        not 1 <= policy.max_attempts <= 3
        or isinstance(policy.base_delay_seconds, bool)
        or policy.base_delay_seconds < 0
    ):
        raise ExecutionValidationError("Retry policy must allow between 1 and 3 attempts.")


def _validate_concurrency_policy(policy: ConcurrencyPolicy) -> None:
    limits = (
        policy.max_total,
        policy.max_heavy,
        policy.max_light,
        policy.default_source_limit,
        policy.default_heavy_source_limit,
    )
    if any(isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in limits):
        raise ExecutionValidationError("Concurrency limits must be positive integers.")
    if any(
        not source_id or isinstance(value, bool) or not isinstance(value, int) or value <= 0
        for source_id, value in {
            **policy.per_source_limits,
            **policy.per_source_heavy_limits,
        }.items()
    ):
        raise ExecutionValidationError("Per-source concurrency limits are invalid.")


def _validate_computations(
    execution: RuleExecution,
    computations: tuple[RuleResultComputation, ...],
) -> None:
    if {item.rule_version_id for item in computations} != set(execution.rule_version_ids):
        raise ExecutionValidationError("Executor results do not match requested rule versions.")
    for item in computations:
        counts = (
            item.checked_count,
            item.passed_count,
            item.failed_count,
            item.not_evaluated_count,
        )
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in counts
        ):
            raise ExecutionValidationError("Execution counts must be non-negative integers.")
        if item.checked_count != sum(counts[1:]):
            raise ExecutionValidationError("Execution counts are inconsistent.")


def _validate_partial_computations(
    execution: RuleExecution,
    computations: tuple[RuleResultComputation, ...],
) -> None:
    version_ids = [item.rule_version_id for item in computations]
    if len(version_ids) != len(set(version_ids)) or not set(version_ids).issubset(
        execution.rule_version_ids
    ):
        raise ExecutionValidationError(
            "Partial executor results do not match requested rule versions."
        )
    for item in computations:
        counts = (
            item.checked_count,
            item.passed_count,
            item.failed_count,
            item.not_evaluated_count,
        )
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in counts
        ):
            raise ExecutionValidationError("Execution counts must be non-negative integers.")
        if item.checked_count != sum(counts[1:]):
            raise ExecutionValidationError("Execution counts are inconsistent.")
        _validate_partitions(item.completed_partitions)


def _validate_partitions(partitions: tuple[str, ...]) -> None:
    if any(not isinstance(partition, str) or not partition.strip() for partition in partitions):
        raise ExecutionValidationError("Completed partition identifiers are invalid.")


def _hash_payload(version_ids: tuple[str, ...], scope: dict[str, Any]) -> str:
    try:
        serialized = json.dumps(
            {"rule_version_ids": list(version_ids), "scope": scope},
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise ExecutionValidationError("Execution scope must be JSON serializable.") from exc
    return _hash_text(serialized)


def _reject_sensitive_scope(scope: Mapping[str, Any]) -> None:
    for key, value in scope.items():
        if str(key).lower() in _FORBIDDEN_SCOPE_KEYS:
            raise ExecutionValidationError("Execution scope must not contain secret fields.")
        if isinstance(value, Mapping):
            _reject_sensitive_scope(value)


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
