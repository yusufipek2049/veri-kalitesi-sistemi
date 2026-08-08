"""Production job handler timeout ve iptal aktarım testleri."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Event

import pytest

from veri_kalitesi.jobs import (
    BackgroundJob,
    ExecutionJobHandler,
    JobCompletionOutcome,
    ReportJobHandler,
)
from veri_kalitesi.jobs.worker import PermanentJobError
from veri_kalitesi.reporting.models import ReportStatus
from veri_kalitesi.scoring.jobs import (
    ScorePublicationJobHandler,
    ScorePublicationJobPayload,
)


@dataclass
class _Report:
    status: ReportStatus


class _Command:
    def __init__(self) -> None:
        self.received = None
        self.cancelled = Event()

    def execute(self, execution_id, **kwargs):
        self.received = (execution_id, kwargs)
        assert kwargs["cancellation_event"].wait(timeout=1)
        return JobCompletionOutcome.SUCCESS

    def cancel(self, execution_id):
        assert execution_id == "execution-1"
        self.cancelled.set()


def _job(job_type: str, payload: dict[str, object]) -> BackgroundJob:
    now = datetime(2026, 7, 29, tzinfo=timezone.utc)
    return BackgroundJob(
        job_id=f"{job_type.lower()}-job",
        job_type=job_type,
        payload=payload,
        created_at=now,
        updated_at=now,
        available_at=now,
    )


def test_execution_handler_applies_connector_timeouts_and_driver_cancel() -> None:
    command = _Command()
    cancellation = Event()
    cancellation.set()

    result = ExecutionJobHandler(command)(
        _job("EXECUTION", {"execution_id": "execution-1"}),
        connection_timeout_seconds=7,
        query_timeout_seconds=19,
        total_timeout_seconds=31,
        cancellation_event=cancellation,
    )

    assert result is JobCompletionOutcome.SUCCESS
    assert command.cancelled.wait(timeout=1)
    assert command.received is not None
    assert command.received[1]["connection_timeout_seconds"] == 7
    assert command.received[1]["query_timeout_seconds"] == 19


def test_report_handler_passes_bounded_timeout_to_report_worker() -> None:
    class _Worker:
        def __init__(self) -> None:
            self.call = None

        def process_report(self, report_id, **kwargs):
            self.call = (report_id, kwargs)
            return _Report(ReportStatus.READY)

    worker = _Worker()
    cancellation = Event()
    result = ReportJobHandler(worker)(  # type: ignore[arg-type]
        _job("REPORT", {"report_id": "report-1"}),
        connection_timeout_seconds=5,
        query_timeout_seconds=23,
        total_timeout_seconds=17,
        cancellation_event=cancellation,
    )

    assert result is JobCompletionOutcome.SUCCESS
    assert worker.call == (
        "report-1",
        {"timeout_seconds": 17, "cancellation_event": cancellation},
    )


def test_score_publication_handler_delegates_to_publication_service() -> None:
    """DS-06: SCORE_PUBLICATION handler payload'ı command'a çevirir."""
    from dataclasses import dataclass
    from datetime import datetime, timezone
    from veri_kalitesi.scoring.publication import (
        ScorePublicationResult,
    )
    from veri_kalitesi.scoring.models import ScorePublication, ScorePublicationStatus

    @dataclass(frozen=True)
    class _StubPubService:
        def publish_execution(self, command, *, actor_context=None):
            pub = ScorePublication(
                publication_id="pub-1",
                execution_id=command.execution_id,
                period=command.period,
                input_digest="sha256:test",
                status=ScorePublicationStatus.PUBLISHED,
                policy_version=command.configuration_version,
                published_at=datetime(2026, 8, 6, tzinfo=timezone.utc),
            )
            return ScorePublicationResult(publication=pub, scores=())

    handler = ScorePublicationJobHandler(publication_service=_StubPubService())
    payload = ScorePublicationJobPayload(
        execution_id="exec-1",
        period="2026-08-06",
        configuration_version="DEFAULT_SCORING_V1",
    )
    cancellation = Event()
    result = handler(
        _job("SCORE_PUBLICATION", payload.to_dict()),
        connection_timeout_seconds=10,
        query_timeout_seconds=30,
        total_timeout_seconds=60,
        cancellation_event=cancellation,
    )
    assert result is JobCompletionOutcome.SUCCESS


def test_score_publication_handler_wraps_failure() -> None:
    """DS-06: Score handler beklenmeyen hatayı PermanentJobError'a sarar."""
    from dataclasses import dataclass

    @dataclass(frozen=True)
    class _FailingPubService:
        def publish_execution(self, command, *, actor_context=None):
            raise RuntimeError("db lost")

    handler = ScorePublicationJobHandler(publication_service=_FailingPubService())
    payload = ScorePublicationJobPayload(
        execution_id="exec-1",
        period="2026-08-06",
        configuration_version="V1",
    )
    cancellation = Event()
    with pytest.raises(PermanentJobError, match="SCORE_PUBLICATION_FAILED"):
        handler(
            _job("SCORE_PUBLICATION", payload.to_dict()),
            connection_timeout_seconds=10,
            query_timeout_seconds=30,
            total_timeout_seconds=60,
            cancellation_event=cancellation,
        )
