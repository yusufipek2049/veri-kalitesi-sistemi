from __future__ import annotations

from dataclasses import dataclass, field
from threading import Event
from typing import Any

import pytest

from veri_kalitesi.jobs.execution_command import PersistentExecutionCommandAdapter


@dataclass
class FailingExecutionService:
    reconciliations: list[tuple[str, str]] = field(default_factory=list)

    def run_for_execution_id(self, execution_id: str, **_: Any) -> None:
        raise RuntimeError(f"synthetic failure for {execution_id}")

    def fail_active_execution(self, execution_id: str, error_class: str) -> None:
        self.reconciliations.append((execution_id, error_class))


def test_unhandled_execution_job_failure_reconciles_active_execution() -> None:
    service = FailingExecutionService()
    command = PersistentExecutionCommandAdapter(service)  # type: ignore[arg-type]

    with pytest.raises(RuntimeError, match="synthetic failure"):
        command.execute(
            "execution-1",
            connection_timeout_seconds=10,
            query_timeout_seconds=20,
            cancellation_event=Event(),
        )

    assert service.reconciliations == [("execution-1", "UNEXPECTED")]
