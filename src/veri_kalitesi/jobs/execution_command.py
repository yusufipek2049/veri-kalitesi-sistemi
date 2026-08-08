"""Adapter: CancellableExecutionCommand → ExecutionService.run_for_execution_id."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from threading import Event
from typing import Any, Protocol

from veri_kalitesi.executions.service import ExecutionService
from veri_kalitesi.identity import ActorContext
from veri_kalitesi.issues.execution_bridge import ExecutionIssueTriggerAdapter
from veri_kalitesi.issues.models import IssueTrigger
from veri_kalitesi.jobs.models import JobCompletionOutcome

logger = logging.getLogger(__name__)


class IssueServicePort(Protocol):
    def create_for_trigger(
        self,
        trigger: IssueTrigger,
        actor_context: ActorContext | None,
    ) -> Any: ...


@dataclass(frozen=True)
class PersistentExecutionCommandAdapter:
    """Queue'nun CancellableExecutionCommand portunu ExecutionService'e bağlar.

    Bu adapter yeni bir execution claim yapmaz; queue tarafından zaten seçilmiş
    execution_id ile çalışır. run_for_execution_id metodu execution repository'deki
    mevcut doğrulama/sonuç yazma mantığını yeniden kullanır.

    DS-05: Issue bridge injection — execution tamamlandıktan sonra issue
    post-processing yapılır. Bridge None ise sadece execution yapılır.
    """

    execution_service: ExecutionService[Any]
    clock: Callable[[], Any] | None = None
    issue_bridge: ExecutionIssueTriggerAdapter | None = None
    issue_service: IssueServicePort | None = None
    issue_actor_context_provider: Callable[[], ActorContext] | None = None

    def execute(
        self,
        execution_id: str,
        *,
        connection_timeout_seconds: int,
        query_timeout_seconds: int,
        cancellation_event: Event,
        progress_callback: Callable[[int], None] = lambda _percent: None,
    ) -> JobCompletionOutcome:
        result = self.execution_service.run_for_execution_id(
            execution_id,
            progress_callback=progress_callback,
        )
        if result is None:
            from veri_kalitesi.jobs.worker import PermanentJobError

            raise PermanentJobError("EXECUTION_NOT_FOUND_OR_TERMINAL")

        outcome = (
            JobCompletionOutcome.SUCCESS
            if result.status.value in {"SUCCESS", "PARTIAL"}
            else JobCompletionOutcome.QUALITY_FAILURE
        )

        if self.issue_bridge is not None and self.issue_service is not None:
            self._process_issue_post_processing(execution_id)

        return outcome

    def _process_issue_post_processing(self, execution_id: str) -> None:
        assert self.issue_bridge is not None
        assert self.issue_service is not None

        actor_context: ActorContext | None = None
        if self.issue_actor_context_provider is not None:
            actor_context = self.issue_actor_context_provider()

        summary = self.issue_bridge.process_execution(execution_id)
        for trigger in summary.triggers:
            try:
                self.issue_service.create_for_trigger(trigger, actor_context)
            except Exception:
                logger.exception(
                    "Issue creation failed for trigger %s in execution %s",
                    trigger.event_id,
                    execution_id,
                )
                raise

    def cancel(self, execution_id: str) -> None:
        try:
            self.execution_service.cancel_execution(
                actor_id="worker-cancel",
                execution_id=execution_id,
                reason="WORKER_CANCELLATION",
            )
        except Exception:
            pass
