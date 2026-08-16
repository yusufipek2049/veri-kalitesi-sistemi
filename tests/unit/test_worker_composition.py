"""Varsayılan worker composition sözleşmesi testleri."""

from __future__ import annotations

from datetime import timedelta
from importlib.util import find_spec
from inspect import signature
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from veri_kalitesi.jobs import entrypoint, production
from veri_kalitesi.jobs.composition import create_persistent_job_runtime
from veri_kalitesi.jobs.lifecycle import DeadLetterReprocessPolicy
from veri_kalitesi.jobs.models import JobCompletionOutcome, JobLeasePolicy
from veri_kalitesi.jobs.settings import PersistentJobSettings
from veri_kalitesi.notifications.jobs import NotificationDeliveryJobHandler
from veri_kalitesi.executions.scheduling import SchedulingService
from veri_kalitesi.reporting.scheduling import ReportScheduleService
from veri_kalitesi.persistence import DatabaseSettings


class _ExecutionCommand:
    def execute(self, execution_id: str, **kwargs: object) -> JobCompletionOutcome:
        return JobCompletionOutcome.SUCCESS

    def cancel(self, execution_id: str) -> None:
        return None


class _MetadataCommand:
    def execute(self, discovery_id: int, **kwargs: object) -> JobCompletionOutcome:
        return JobCompletionOutcome.SUCCESS


def _notification_handler(job: object, **kwargs: object) -> JobCompletionOutcome:
    return JobCompletionOutcome.SUCCESS


def _settings(secret_dir: Path) -> PersistentJobSettings:
    return PersistentJobSettings(
        worker_id="worker-composition-test",
        hostname="worker-host",
        capacity=1,
        lease_duration_seconds=30,
        idle_wait_seconds=0.1,
        shutdown_grace_seconds=1.0,
        database=DatabaseSettings.from_url(
            "postgresql+psycopg://worker:secret@localhost/data_quality"
        ),
        local_secret_dir=str(secret_dir),
        actor_policy_version="WORKER_ACTOR_POLICY_V1",
    )


def test_default_runtime_registers_every_supported_job_type_without_conditionals() -> None:
    runtime = create_persistent_job_runtime(
        lambda: None,  # type: ignore[arg-type,return-value]
        transactional_audit=object(),  # type: ignore[arg-type]
        execution_command=_ExecutionCommand(),  # type: ignore[arg-type]
        metadata_discovery_command=_MetadataCommand(),  # type: ignore[arg-type]
        notification_delivery_handler=_notification_handler,  # type: ignore[arg-type]
        worker_id="worker-composition-test",
        lease_policy=JobLeasePolicy(duration=timedelta(seconds=30)),
        reprocess_policy=DeadLetterReprocessPolicy(
            version="WORKER_COMPOSITION_TEST_V1",
            allowed_roles=frozenset({"TEST_OPERATOR"}),
        ),
    )

    assert runtime.worker.supported_job_types == (
        "EXECUTION",
        "METADATA_DISCOVERY",
        "NOTIFICATION_DELIVERY",
    )
    assert set(runtime.worker.handlers) == set(runtime.worker.supported_job_types)


def test_removed_job_types_have_no_handler_or_enqueue_module() -> None:
    from veri_kalitesi.jobs import handlers
    from veri_kalitesi.reporting import service

    assert not hasattr(handlers, "ReportJobHandler")
    assert find_spec("veri_kalitesi.scoring.jobs") is None
    assert "job_queue" not in signature(service.ReportService).parameters
    assert "transactional_audit" not in signature(service.ReportService).parameters


def test_production_factory_directly_composes_notification_delivery(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}
    expected_runtime = object()
    settings = _settings(tmp_path)

    def capture_runtime(*args: object, **kwargs: object) -> object:
        captured.update(kwargs)
        return expected_runtime

    monkeypatch.setattr(production, "create_session_factory", lambda settings: object())
    monkeypatch.setattr(production, "create_persistent_job_runtime", capture_runtime)

    runtime = production.create_production_worker(settings)

    assert runtime is expected_runtime
    assert tuple(signature(production.create_production_worker).parameters) == ("settings",)
    assert isinstance(
        captured["notification_delivery_handler"],
        NotificationDeliveryJobHandler,
    )
    assert captured["metadata_discovery_command"] is not None
    execution_command = captured["execution_command"]
    assert execution_command.issue_actor_context_provider().policy_version == (
        settings.actor_policy_version
    )
    assert execution_command.score_actor_context_provider().policy_version == (
        settings.actor_policy_version
    )
    metadata_command = captured["metadata_discovery_command"]
    assert metadata_command.actor_context_provider(
        "source-1", "correlation-1"
    ).policy_version == settings.actor_policy_version
    schedule_triggers = captured["schedule_triggers"]
    assert isinstance(schedule_triggers, tuple)
    assert any(isinstance(item, SchedulingService) for item in schedule_triggers)
    assert any(isinstance(item, ReportScheduleService) for item in schedule_triggers)
    assert (
        captured["schedule_trigger_interval_seconds"] == settings.schedule_trigger_interval_seconds
    )


def test_entrypoint_reaches_the_default_production_factory(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    calls: list[PersistentJobSettings] = []

    class _Worker:
        def run_forever(self, stop_event: object, *, idle_wait_seconds: float) -> None:
            assert idle_wait_seconds == settings.idle_wait_seconds

    def factory(received: PersistentJobSettings) -> object:
        calls.append(received)
        return SimpleNamespace(worker=_Worker())

    monkeypatch.setattr(entrypoint.PersistentJobSettings, "from_environment", lambda: settings)
    monkeypatch.setattr(production, "create_production_worker", factory)
    monkeypatch.setattr(entrypoint.signal, "signal", lambda *args: None)

    assert entrypoint.main() == 0
    assert calls == [settings]
