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


class ScorePublicationPort(Protocol):
    def publish_execution(
        self,
        command: Any,
        *,
        actor_context: ActorContext | None = None,
    ) -> Any: ...


@dataclass(frozen=True)
class PersistentExecutionCommandAdapter:
    """Queue'nun CancellableExecutionCommand portunu ExecutionService'e bağlar.

    Bu adapter yeni bir execution claim yapmaz; queue tarafından zaten seçilmiş
    execution_id ile çalışır. run_for_execution_id metodu execution repository'deki
    mevcut doğrulama/sonuç yazma mantığını yeniden kullanır.

    DS-05: Issue bridge injection — execution tamamlandıktan sonra issue
    post-processing yapılır. Bridge None ise sadece execution yapılır.
    Skor yayımı — execution başarılıysa skor hesaplanır ve yayımlanır.
    """

    execution_service: ExecutionService[Any]
    clock: Callable[[], Any] | None = None
    issue_bridge: ExecutionIssueTriggerAdapter | None = None
    issue_service: IssueServicePort | None = None
    issue_actor_context_provider: Callable[[], ActorContext] | None = None
    score_publication_service: ScorePublicationPort | None = None
    score_actor_context_provider: Callable[[], ActorContext] | None = None

    def execute(
        self,
        execution_id: str,
        *,
        connection_timeout_seconds: int,
        query_timeout_seconds: int,
        cancellation_event: Event,
        progress_callback: Callable[[int], None] = lambda _percent: None,
    ) -> JobCompletionOutcome:
        try:
            result = self.execution_service.run_for_execution_id(
                execution_id,
                progress_callback=progress_callback,
            )
        except Exception:
            try:
                self.execution_service.fail_active_execution(execution_id, "UNEXPECTED")
            except Exception:
                logger.exception(
                    "Active execution could not be reconciled after job failure: %s",
                    execution_id,
                )
            raise
        if result is None:
            from veri_kalitesi.jobs.worker import PermanentJobError

            raise PermanentJobError("EXECUTION_NOT_FOUND_OR_TERMINAL")

        outcome = (
            JobCompletionOutcome.SUCCESS
            if result.status.value in {"SUCCESS", "PARTIAL"}
            else JobCompletionOutcome.QUALITY_FAILURE
        )

        # Skor yayımı — execution başarılıysa skor hesapla ve yayımla
        if self.score_publication_service is not None and result.status.value in {
            "SUCCESS",
            "PARTIAL",
        }:
            self._process_score_publication(execution_id)

        # Issue post-processing — başarısız/uyarı sonuçlarından issue üret
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

    def _process_score_publication(self, execution_id: str) -> None:
        assert self.score_publication_service is not None
        from datetime import datetime, timezone

        actor_context: ActorContext | None = None
        if self.score_actor_context_provider is not None:
            actor_context = self.score_actor_context_provider()

        try:
            from veri_kalitesi.scoring.publication import ScorePublicationCommand

            now = datetime.now(timezone.utc)
            period = now.strftime("%Y-%m-%d")
            command = ScorePublicationCommand(
                execution_id=execution_id,
                period=period,
                configuration_version="DEFAULT_SCORING_V1",
                idempotency_key=execution_id,
            )
            self.score_publication_service.publish_execution(command, actor_context=actor_context)
        except Exception:
            logger.exception(
                "Score publication failed for execution %s",
                execution_id,
            )

    def cancel(self, execution_id: str) -> None:
        try:
            self.execution_service.cancel_execution(
                actor_id="worker-cancel",
                execution_id=execution_id,
                reason="WORKER_CANCELLATION",
            )
        except Exception:
            pass
