"""PostgreSQL tabanlı kalıcı iş kuyruğu çekirdeği."""

from veri_kalitesi.jobs.errors import (
    JobAuthorizationError,
    JobConcurrencyError,
    JobConflictError,
    JobError,
    JobIdempotencyConflictError,
    JobLeaseError,
    JobNotFoundError,
    JobValidationError,
)
from veri_kalitesi.jobs.lifecycle import (
    DeadLetterReprocessPolicy,
    DeadLetterReprocessService,
)
from veri_kalitesi.jobs.models import (
    BackgroundJob,
    DeadLetterRecord,
    DeadLetterStatus,
    JobCompletionOutcome,
    JobFailureKind,
    JobLeasePolicy,
    JobRetryPolicy,
    JobStatus,
)
from veri_kalitesi.jobs.postgresql_repository import (
    JobTables,
    PostgreSQLJobQueueRepository,
    job_tables,
)
from veri_kalitesi.jobs.worker import (
    JobHandler,
    JobTimeoutError,
    PermanentJobError,
    PersistentJobWorker,
    RetryableJobError,
)
from veri_kalitesi.jobs.handlers import (
    CancellableExecutionCommand,
    ExecutionJobHandler,
    ReportJobHandler,
)
from veri_kalitesi.jobs.composition import (
    PersistentJobRuntime,
    create_persistent_job_runtime,
)

__all__ = [
    "BackgroundJob",
    "DeadLetterRecord",
    "DeadLetterReprocessPolicy",
    "DeadLetterReprocessService",
    "DeadLetterStatus",
    "JobAuthorizationError",
    "JobCompletionOutcome",
    "JobConcurrencyError",
    "JobConflictError",
    "JobError",
    "JobIdempotencyConflictError",
    "JobLeaseError",
    "JobLeasePolicy",
    "JobFailureKind",
    "JobNotFoundError",
    "JobStatus",
    "JobRetryPolicy",
    "JobTables",
    "JobValidationError",
    "PostgreSQLJobQueueRepository",
    "JobHandler",
    "CancellableExecutionCommand",
    "ExecutionJobHandler",
    "ReportJobHandler",
    "PersistentJobRuntime",
    "create_persistent_job_runtime",
    "JobTimeoutError",
    "PermanentJobError",
    "PersistentJobWorker",
    "RetryableJobError",
    "job_tables",
]
