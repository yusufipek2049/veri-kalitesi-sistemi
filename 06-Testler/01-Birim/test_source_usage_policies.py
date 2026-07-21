from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from veri_kalitesi.executions import (
    ExecutionValidationError,
    ExecutionStatus,
    SQLiteExecutionRepository,
    SQLiteSourceUsagePolicyRepository,
    SourceUsagePolicy,
    SourceUsagePolicyStatus,
    SourceUsagePolicyTechnicalError,
    SourceUsagePolicyUnavailableError,
    WorkloadClass,
)
from veri_kalitesi.executions.models import RuleExecution


def _policy(
    policy_id: str,
    *,
    policy_version: int = 1,
    source_id: str | None = None,
    source_type: str | None = None,
    max_concurrent_queries: int = 4,
    max_workers: int = 6,
) -> SourceUsagePolicy:
    return SourceUsagePolicy(
        policy_id=policy_id,
        policy_version=policy_version,
        status=SourceUsagePolicyStatus.ACTIVE,
        source_id=source_id,
        source_type=source_type,
        max_concurrent_queries=max_concurrent_queries,
        max_workers=max_workers,
        query_timeout_seconds=900,
        retry_count=2,
        retry_delay_seconds=1.5,
        rate_limit={"limit": 30, "period": "MINUTE"},
        allowed_windows=("WORKING_HOURS",),
        blocked_windows=("PEAK_HOURS",),
        cpu_limit_percent=40,
        io_limit_percent=50,
        peak_hours_behavior="REJECT",
        timeout_cancel_behavior="CANCEL",
        approved_by="checker-1",
        audit_reference=f"audit-{policy_id}",
    )


def test_fr_039_open_002_persists_complete_active_global_policy() -> None:
    repository = SQLiteSourceUsagePolicyRepository()
    policy = _policy("global-v1")

    repository.save(policy)

    assert repository.list_policies() == [policy]
    resolved = repository.resolve_concurrency_policy()
    assert resolved.max_total == 6
    assert resolved.default_source_limit == 4


def test_fr_039_open_002_source_id_override_precedes_source_type_override() -> None:
    repository = SQLiteSourceUsagePolicyRepository(
        source_types_by_id={"source-a": "RELATIONAL", "source-b": "RELATIONAL"}
    )
    repository.save(_policy("global-v1"))
    repository.save(
        _policy(
            "relational-v1",
            source_type="RELATIONAL",
            max_concurrent_queries=2,
            max_workers=3,
        )
    )
    repository.save(
        _policy(
            "source-a-v1",
            source_id="source-a",
            max_concurrent_queries=1,
            max_workers=1,
        )
    )

    resolved = repository.resolve_concurrency_policy()

    assert resolved.source_limit("source-a") == 1
    assert resolved.source_limit("source-b") == 2
    assert resolved.source_limit("unmapped-source") == 4


def test_fr_039_uc_008_resolved_worker_quota_limits_queue_claims() -> None:
    policy_repository = SQLiteSourceUsagePolicyRepository()
    policy_repository.save(_policy("global-v1", max_workers=1))
    execution_repository = SQLiteExecutionRepository()
    created_at = datetime(2026, 7, 21, 8, 0, tzinfo=timezone.utc)
    for index in range(2):
        execution_repository.create_or_get(
            RuleExecution(
                execution_id=f"execution-{index}",
                idempotency_key_hash=f"key-{index}",
                payload_hash=f"payload-{index}",
                rule_version_ids=("version-main",),
                scope={},
                triggered_by="scheduler",
                correlation_id=f"correlation-{index}",
                source_ids=(f"source-{index}",),
                workload_class=WorkloadClass.LIGHT,
                created_at=created_at + timedelta(seconds=index),
            )
        )

    policy = policy_repository.resolve_concurrency_policy()
    first = execution_repository.claim_next(created_at, policy)
    blocked = execution_repository.claim_next(created_at, policy)

    assert first is not None and first.status is ExecutionStatus.RUNNING
    assert blocked is None


def test_fr_039_open_002_new_active_version_retires_previous_scope() -> None:
    repository = SQLiteSourceUsagePolicyRepository()
    repository.save(_policy("global-v1"))

    repository.save(_policy("global-v2", policy_version=2, max_workers=3))

    stored = repository.list_policies()
    assert [item.status for item in stored] == [
        SourceUsagePolicyStatus.RETIRED,
        SourceUsagePolicyStatus.ACTIVE,
    ]
    assert repository.resolve_concurrency_policy().max_total == 3


def test_fr_039_open_003_missing_active_global_policy_fails_closed() -> None:
    repository = SQLiteSourceUsagePolicyRepository()

    with pytest.raises(SourceUsagePolicyUnavailableError):
        repository.resolve_concurrency_policy()


def test_fr_039_open_002_rejects_unapproved_active_policy() -> None:
    repository = SQLiteSourceUsagePolicyRepository()
    policy = replace(_policy("global-v1"), approved_by=None)

    with pytest.raises(ExecutionValidationError, match="approval and audit"):
        repository.save(policy)

    assert repository.list_policies() == []


def test_fr_039_open_002_policy_repository_failure_is_technical_error() -> None:
    repository = SQLiteSourceUsagePolicyRepository()
    repository.connection.close()

    with pytest.raises(SourceUsagePolicyTechnicalError):
        repository.resolve_concurrency_policy()
