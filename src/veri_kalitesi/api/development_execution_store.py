"""Geliştirme ortamı çalıştırma (execution) bellek içi deposu ve okuyucusu."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from threading import RLock
from uuid import uuid4

from veri_kalitesi.api.development_fixtures import DEVELOPMENT_EXECUTIONS
from veri_kalitesi.executions.errors import (
    ExecutionConflictError,
    ExecutionNotFoundError,
)
from veri_kalitesi.executions.models import (
    ExecutionMode,
    ExecutionStatus,
    ExecutionType,
    RuleExecution,
    WorkloadClass,
)
from veri_kalitesi.identity import ActorContext


class DevelopmentExecutionReader:
    def list_executions_for_sources(
        self,
        allowed_source_ids: frozenset[str],
        *,
        limit: int = 100,
    ) -> list[RuleExecution]:
        return sorted(
            (
                execution
                for execution in DEVELOPMENT_EXECUTIONS
                if execution.source_ids and set(execution.source_ids).issubset(allowed_source_ids)
            ),
            key=lambda execution: (execution.created_at, execution.execution_id),
            reverse=True,
        )[:limit]

    def get(self, execution_id: str) -> RuleExecution:
        for execution in DEVELOPMENT_EXECUTIONS:
            if execution.execution_id == execution_id:
                return execution
        raise ExecutionNotFoundError(f"Execution {execution_id} not found.")

    def list_results(self, execution_id: str) -> list:
        return []


class DevelopmentExecutionStore:
    """Geliştirme ortamında çalıştırma işlemleri için bellek içi depo."""

    def __init__(self) -> None:
        self._executions = {
            execution.execution_id: execution for execution in DEVELOPMENT_EXECUTIONS
        }
        self._lock = RLock()

    def start_manual(
        self,
        *,
        rule_version_ids: tuple[str, ...],
        source_ids: tuple[str, ...],
        idempotency_key: str,
        actor_context: ActorContext,
        execution_mode: ExecutionMode = ExecutionMode.OFFICIAL,
    ) -> RuleExecution:
        with self._lock:
            execution_id = f"execution-{uuid4().hex[:12]}"
            now = datetime.now(timezone.utc)
            execution = RuleExecution(
                execution_id=execution_id,
                idempotency_key_hash=f"dev-manual-{idempotency_key}-{execution_id}",
                payload_hash=f"dev-manual-payload-{execution_id}",
                rule_version_ids=rule_version_ids,
                scope={},
                triggered_by=actor_context.actor_id,
                correlation_id=execution_id,
                source_ids=source_ids,
                workload_class=WorkloadClass.LIGHT,
                execution_type=ExecutionType.MANUAL,
                execution_mode=execution_mode,
                status=ExecutionStatus.QUEUED,
                created_at=now,
            )
            self._executions[execution_id] = execution
            return execution

    def cancel(
        self, execution_id: str, *, reason: str, actor_context: ActorContext
    ) -> RuleExecution:
        with self._lock:
            execution = self._executions.get(execution_id)
            if execution is None:
                raise ExecutionNotFoundError(f"Execution {execution_id} not found.")
            if execution.status in {
                ExecutionStatus.SUCCESS,
                ExecutionStatus.TECHNICAL_ERROR,
                ExecutionStatus.CANCELLED,
                ExecutionStatus.TIMEOUT,
            }:
                raise ExecutionConflictError(
                    f"Cannot cancel execution in {execution.status.value} status."
                )
            now = datetime.now(timezone.utc)
            if execution.status is ExecutionStatus.QUEUED:
                updated = replace(
                    execution,
                    status=ExecutionStatus.CANCELLED,
                    cancelled_at=now,
                    cancel_reason=reason,
                    finished_at=now,
                    cancel_requested_by=actor_context.actor_id,
                )
            else:
                updated = replace(
                    execution,
                    status=ExecutionStatus.CANCEL_REQUESTED,
                    cancel_requested_at=now,
                    cancel_reason=reason,
                    cancel_requested_by=actor_context.actor_id,
                )
            self._executions[execution_id] = updated
            return updated
