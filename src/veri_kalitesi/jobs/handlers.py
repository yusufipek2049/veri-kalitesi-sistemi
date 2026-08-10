"""Kalıcı worker için production execution ve report handler adaptörleri."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from threading import Event, Thread
from typing import Protocol

from veri_kalitesi.jobs.models import BackgroundJob, JobCompletionOutcome
from veri_kalitesi.jobs.worker import PermanentJobError

ProgressCallback = Callable[[int], None]


class CancellableExecutionCommand(Protocol):
    """Kaynak bağlayıcısına timeout ve aktif iptal aktarabilen execution komutu."""

    def execute(
        self,
        execution_id: str,
        *,
        connection_timeout_seconds: int,
        query_timeout_seconds: int,
        cancellation_event: Event,
        progress_callback: ProgressCallback,
    ) -> JobCompletionOutcome: ...

    def cancel(self, execution_id: str) -> None: ...


class CancellableMetadataDiscoveryCommand(Protocol):
    """Metadata keşif bağlayıcısına timeout ve iptal aktarabilen komut."""

    def execute(
        self,
        discovery_id: int,
        *,
        timeout_seconds: int,
        cancellation_event: Event,
        progress_callback: ProgressCallback,
    ) -> JobCompletionOutcome: ...


@dataclass(frozen=True)
class ExecutionJobHandler:
    command: CancellableExecutionCommand

    def __call__(
        self,
        job: BackgroundJob,
        *,
        connection_timeout_seconds: int,
        query_timeout_seconds: int,
        total_timeout_seconds: int,
        cancellation_event: Event,
        progress_callback: ProgressCallback = lambda _percent: None,
    ) -> JobCompletionOutcome:
        execution_id = job.payload.get("execution_id")
        if not isinstance(execution_id, str) or not execution_id.strip():
            raise PermanentJobError("INVALID_EXECUTION_JOB_PAYLOAD")

        finished = Event()

        def propagate_cancel() -> None:
            while not finished.is_set():
                if cancellation_event.wait(timeout=0.05):
                    self.command.cancel(execution_id)
                    return

        watcher = Thread(
            target=propagate_cancel,
            name=f"execution-cancel-{execution_id}",
            daemon=True,
        )
        watcher.start()
        try:
            return self.command.execute(
                execution_id,
                connection_timeout_seconds=connection_timeout_seconds,
                query_timeout_seconds=query_timeout_seconds,
                cancellation_event=cancellation_event,
                progress_callback=progress_callback,
            )
        finally:
            finished.set()
            watcher.join(timeout=0.2)


@dataclass(frozen=True)
class MetadataDiscoveryJobHandler:
    command: CancellableMetadataDiscoveryCommand

    def __call__(
        self,
        job: BackgroundJob,
        *,
        connection_timeout_seconds: int,
        query_timeout_seconds: int,
        total_timeout_seconds: int,
        cancellation_event: Event,
        progress_callback: ProgressCallback = lambda _percent: None,
    ) -> JobCompletionOutcome:
        discovery_id = job.payload.get("discovery_id")
        if not isinstance(discovery_id, int):
            raise PermanentJobError("INVALID_METADATA_DISCOVERY_JOB_PAYLOAD")
        return self.command.execute(
            discovery_id,
            timeout_seconds=min(query_timeout_seconds, total_timeout_seconds),
            cancellation_event=cancellation_event,
            progress_callback=progress_callback,
        )
