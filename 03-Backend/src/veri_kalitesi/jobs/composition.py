"""PostgreSQL-only production worker composition."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from veri_kalitesi.audit import PostgreSQLTransactionalAudit
from veri_kalitesi.executions import PostgreSQLSourceUsagePolicyRepository
from veri_kalitesi.jobs.lifecycle import (
    DeadLetterReprocessPolicy,
    DeadLetterReprocessService,
)
from veri_kalitesi.jobs.models import JobLeasePolicy
from veri_kalitesi.jobs.handlers import (
    CancellableExecutionCommand,
    ExecutionJobHandler,
    ReportJobHandler,
)
from veri_kalitesi.jobs.postgresql_repository import PostgreSQLJobQueueRepository
from veri_kalitesi.jobs.worker import PersistentJobWorker
from veri_kalitesi.persistence import DEFAULT_SCHEMA_NAME, SessionFactory
from veri_kalitesi.reporting.worker import ReportWorker


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
    report_worker: ReportWorker,
    worker_id: str,
    lease_policy: JobLeasePolicy,
    reprocess_policy: DeadLetterReprocessPolicy,
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
    return PersistentJobRuntime(
        repository=repository,
        worker=PersistentJobWorker(
            repository=repository,
            policy_resolver=policy_repository,
            handlers={
                "EXECUTION": ExecutionJobHandler(execution_command),
                "REPORT": ReportJobHandler(report_worker),
            },
            transactional_audit=transactional_audit,
            worker_id=worker_id,
            lease_policy=lease_policy,
        ),
        dead_letter_service=DeadLetterReprocessService(
            repository,
            transactional_audit,
            reprocess_policy,
        ),
    )
