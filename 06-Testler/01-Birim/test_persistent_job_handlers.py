"""Production job handler timeout ve iptal aktarım testleri."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Event

from veri_kalitesi.jobs import (
    BackgroundJob,
    ExecutionJobHandler,
    JobCompletionOutcome,
    ReportJobHandler,
)
from veri_kalitesi.reporting.models import ReportStatus


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
