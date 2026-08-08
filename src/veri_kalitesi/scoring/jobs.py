"""Dayanıklı SCORE_PUBLICATION job enqueue ve handler adaptörü."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol


from veri_kalitesi.identity import ActorContext
from veri_kalitesi.jobs.models import BackgroundJob, JobCompletionOutcome
from veri_kalitesi.jobs.worker import PermanentJobError
from veri_kalitesi.persistence import (
    DEFAULT_SCHEMA_NAME,
    SessionFactory,
    transactional_session,
)
from veri_kalitesi.scoring.publication import (
    ScorePublicationCommand,
    ScorePublicationService,
)


class ScorePublicationProtocol(Protocol):
    """ScorePublicationService için minimal protokol."""

    def publish_execution(
        self,
        command: ScorePublicationCommand,
        *,
        actor_context: ActorContext | None = None,
    ) -> object: ...


@dataclass(frozen=True)
class ScorePublicationJobPayload:
    """SCORE_PUBLICATION job payload."""

    execution_id: str
    period: str
    configuration_version: str

    def to_dict(self) -> dict[str, str]:
        return {
            "execution_id": self.execution_id,
            "period": self.period,
            "configuration_version": self.configuration_version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScorePublicationJobPayload:
        execution_id = data.get("execution_id")
        period = data.get("period")
        configuration_version = data.get("configuration_version")
        if not isinstance(execution_id, str) or not execution_id.strip():
            raise PermanentJobError("INVALID_SCORE_PUBLICATION_JOB_PAYLOAD")
        if not isinstance(period, str) or not period.strip():
            raise PermanentJobError("INVALID_SCORE_PUBLICATION_JOB_PAYLOAD")
        if not isinstance(configuration_version, str) or not configuration_version.strip():
            raise PermanentJobError("INVALID_SCORE_PUBLICATION_JOB_PAYLOAD")
        return cls(
            execution_id=execution_id,
            period=period,
            configuration_version=configuration_version,
        )


def score_publication_idempotency_key(execution_id: str) -> str:
    """Deterministik idempotency key — execution başına tek job."""
    return f"score-pub:{execution_id}"


def canonical_period(at: datetime | None = None) -> str:
    """UTC ISO-8601 dönem dizgesi — gün çözünürlüğü."""
    now = at or datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%d")


class PostgreSQLScoreJobEnqueuer:
    """Execution completion → SCORE_PUBLICATION job enqueue.

    Mevcut execution result transaction'ına katılır; session-aware enqueue.
    """

    def __init__(
        self,
        session_factory: SessionFactory,
        *,
        schema: str = DEFAULT_SCHEMA_NAME,
    ) -> None:
        self._session_factory = session_factory
        self._schema = schema

    def enqueue_score_publication(
        self,
        execution_id: str,
        *,
        configuration_version: str,
        period: str | None = None,
        session: Any = None,
    ) -> BackgroundJob:
        """SCORE_PUBLICATION job'ı enqueuer.

        session verilirse mevcut transaction'a katılır; aksi hâlde yeni
        transaction açar.
        """
        payload = ScorePublicationJobPayload(
            execution_id=execution_id,
            period=period or canonical_period(),
            configuration_version=configuration_version,
        )
        job = BackgroundJob(
            job_type="SCORE_PUBLICATION",
            payload=payload.to_dict(),
            idempotency_key=score_publication_idempotency_key(execution_id),
        )
        if session is not None:
            from veri_kalitesi.jobs.postgresql_repository import (
                PostgreSQLJobQueueRepository,
            )

            repo = PostgreSQLJobQueueRepository(self._session_factory, schema=self._schema)
            repo.enqueue(job, session=session)
        else:
            with transactional_session(self._session_factory) as active_session:
                from veri_kalitesi.jobs.postgresql_repository import (
                    PostgreSQLJobQueueRepository,
                )

                repo = PostgreSQLJobQueueRepository(self._session_factory, schema=self._schema)
                repo.enqueue(job, session=active_session)
        return job


@dataclass(frozen=True)
class ScorePublicationJobHandler:
    """SCORE_PUBLICATION job → ScorePublicationService adapter."""

    publication_service: ScorePublicationService
    actor_context: ActorContext | None = None

    def __call__(
        self,
        job: BackgroundJob,
        *,
        connection_timeout_seconds: int,
        query_timeout_seconds: int,
        total_timeout_seconds: int,
        cancellation_event: Any,
        progress_callback: Any = lambda _percent: None,
    ) -> JobCompletionOutcome:
        payload = ScorePublicationJobPayload.from_dict(job.payload)
        command = ScorePublicationCommand(
            execution_id=payload.execution_id,
            period=payload.period,
            configuration_version=payload.configuration_version,
        )
        try:
            self.publication_service.publish_execution(command, actor_context=self.actor_context)
        except PermanentJobError:
            raise
        except Exception as exc:
            raise PermanentJobError(f"SCORE_PUBLICATION_FAILED: {exc}") from exc
        return JobCompletionOutcome.SUCCESS
