"""PostgreSQL-only production worker composition."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from veri_kalitesi.audit.postgresql_outbox import PostgreSQLTransactionalAudit
from veri_kalitesi.executions.postgresql_source_usage import PostgreSQLSourceUsagePolicyRepository
from veri_kalitesi.jobs.lifecycle import (
    DeadLetterReprocessPolicy,
    DeadLetterReprocessService,
)
from veri_kalitesi.jobs.models import JobLeasePolicy
from veri_kalitesi.jobs.handlers import (
    CancellableExecutionCommand,
    CancellableMetadataDiscoveryCommand,
    ExecutionJobHandler,
    MetadataDiscoveryJobHandler,
)
from veri_kalitesi.jobs.postgresql_repository import PostgreSQLJobQueueRepository
from veri_kalitesi.jobs.worker import JobHandler, PersistentJobWorker, ScheduleTrigger
from veri_kalitesi.persistence import DEFAULT_SCHEMA_NAME, SessionFactory


@dataclass(frozen=True)
class PersistentJobRuntime:
    repository: PostgreSQLJobQueueRepository
    worker: PersistentJobWorker
    dead_letter_service: DeadLetterReprocessService


def create_persistent_job_runtime(
    session_factory: SessionFactory,
    *,
    transactional_audit: PostgreSQLTransactionalAudit,
    execution_command: CancellableExecutionCommand,
    worker_id: str,
    worker_hostname: str = "localhost",
    worker_capacity: int = 1,
    lease_policy: JobLeasePolicy,
    reprocess_policy: DeadLetterReprocessPolicy,
    metadata_discovery_command: CancellableMetadataDiscoveryCommand,
    notification_delivery_handler: JobHandler,
    schedule_triggers: tuple[ScheduleTrigger, ...] = (),
    schedule_trigger_interval_seconds: float = 5.0,
    source_types_by_id: Mapping[str, str] | None = None,
    schema: str = DEFAULT_SCHEMA_NAME,
) -> PersistentJobRuntime:
    """Üretim bileşimini kalıcı queue/policy/audit bağımlılıklarıyla kurar."""

    repository = PostgreSQLJobQueueRepository(session_factory, schema=schema)
    policy_repository = PostgreSQLSourceUsagePolicyRepository(
        session_factory,
        schema=schema,
        source_types_by_id=source_types_by_id,
    )
    handlers: dict[str, JobHandler] = {
        "EXECUTION": ExecutionJobHandler(execution_command),
        "METADATA_DISCOVERY": MetadataDiscoveryJobHandler(metadata_discovery_command),
        "NOTIFICATION_DELIVERY": notification_delivery_handler,
    }
    return PersistentJobRuntime(
        repository=repository,
        worker=PersistentJobWorker(
            repository=repository,
            policy_resolver=policy_repository,
            handlers=handlers,
            transactional_audit=transactional_audit,
            worker_id=worker_id,
            lease_policy=lease_policy,
            hostname=worker_hostname,
            capacity=worker_capacity,
            schedule_triggers=schedule_triggers,
            schedule_trigger_interval_seconds=schedule_trigger_interval_seconds,
        ),
        dead_letter_service=DeadLetterReprocessService(
            repository,
            transactional_audit,
            reprocess_policy,
        ),
    )
