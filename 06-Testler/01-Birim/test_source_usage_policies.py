from __future__ import annotations

from dataclasses import replace
from datetime import datetime, time, timedelta, timezone

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
    SourceUsageWindow,
    WorkloadClass,
)
from veri_kalitesi.executions.models import RuleExecution


AT = datetime(2026, 7, 21, 8, 0, tzinfo=timezone.utc)
ALL_DAYS = (1, 2, 3, 4, 5, 6, 7)


def _window(
    starts_at: time = time(8),
    ends_at: time = time(18),
    *,
    weekdays: tuple[int, ...] = ALL_DAYS,
) -> SourceUsageWindow:
    return SourceUsageWindow(
        timezone="Europe/Istanbul",
        weekdays=weekdays,
        starts_at=starts_at,
        ends_at=ends_at,
    )


def _policy(
    policy_id: str,
    *,
    policy_version: int = 1,
    source_id: str | None = None,
    source_type: str | None = None,
    max_concurrent_queries: int = 4,
    max_workers: int = 6,
    query_timeout_seconds: int = 900,
    retry_count: int = 2,
    retry_delay_seconds: float = 1.5,
    allowed_windows: tuple[SourceUsageWindow, ...] | None = None,
    blocked_windows: tuple[SourceUsageWindow, ...] = (),
) -> SourceUsagePolicy:
    return SourceUsagePolicy(
        policy_id=policy_id,
        policy_version=policy_version,
        status=SourceUsagePolicyStatus.ACTIVE,
        source_id=source_id,
        source_type=source_type,
        max_concurrent_queries=max_concurrent_queries,
        max_workers=max_workers,
        query_timeout_seconds=query_timeout_seconds,
        retry_count=retry_count,
        retry_delay_seconds=retry_delay_seconds,
        rate_limit={"limit": 30, "period": "MINUTE"},
        allowed_windows=allowed_windows if allowed_windows is not None else (_window(),),
        blocked_windows=blocked_windows,
        cpu_limit_percent=40,
        io_limit_percent=50,
        peak_hours_behavior="DEFER",
        timeout_cancel_behavior="CANCEL",
        approved_by="checker-1",
        audit_reference=f"audit-{policy_id}",
    )


def test_fr_039_open_002_persists_complete_active_global_policy() -> None:
    repository = SQLiteSourceUsagePolicyRepository()
    policy = _policy("global-v1")

    repository.save(policy)

    assert repository.list_policies() == [policy]
    resolved = repository.resolve_concurrency_policy(at=AT)
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

    resolved = repository.resolve_concurrency_policy(at=AT)

    assert resolved.source_limit("source-a") == 1
    assert resolved.source_limit("source-b") == 2
    assert resolved.source_limit("unmapped-source") == 4


def test_fr_039_fr_040_fr_041_multi_source_runtime_policy_uses_strictest_values() -> None:
    repository = SQLiteSourceUsagePolicyRepository()
    repository.save(_policy("global-v1"))
    repository.save(
        _policy(
            "source-a-v1",
            source_id="source-a",
            query_timeout_seconds=300,
            retry_count=2,
            retry_delay_seconds=2,
        )
    )
    repository.save(
        _policy(
            "source-b-v1",
            source_id="source-b",
            query_timeout_seconds=600,
            retry_count=0,
            retry_delay_seconds=5,
        )
    )

    resolved = repository.resolve_policy(at=AT)
    runtime = resolved.runtime_policy_for(("source-a", "source-b"))

    assert runtime.query_timeout_seconds == 300
    assert runtime.retry_count == 0
    assert runtime.retry_delay_seconds == 5


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

    policy = policy_repository.resolve_concurrency_policy(at=AT)
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
    assert repository.resolve_concurrency_policy(at=AT).max_total == 3


def test_fr_039_open_003_missing_active_global_policy_fails_closed() -> None:
    repository = SQLiteSourceUsagePolicyRepository()

    with pytest.raises(SourceUsagePolicyUnavailableError):
        repository.resolve_concurrency_policy(at=AT)


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
        repository.resolve_concurrency_policy(at=AT)


def test_nfr_perf_008_blocked_window_overrides_allowed_window() -> None:
    repository = SQLiteSourceUsagePolicyRepository()
    repository.save(
        _policy(
            "global-v1",
            allowed_windows=(_window(time(8), time(18)),),
            blocked_windows=(_window(time(12), time(13)),),
        )
    )
    peak_time = datetime(2026, 7, 21, 9, 30, tzinfo=timezone.utc)

    resolved = repository.resolve_concurrency_policy(at=peak_time)

    assert resolved.default_source_allowed is False


def test_nfr_perf_008_outside_allowed_window_fails_closed() -> None:
    repository = SQLiteSourceUsagePolicyRepository()
    repository.save(_policy("global-v1"))
    after_hours = datetime(2026, 7, 21, 18, 0, tzinfo=timezone.utc)

    resolved = repository.resolve_concurrency_policy(at=after_hours)

    assert resolved.default_source_allowed is False


def test_nfr_perf_008_window_start_is_inclusive_and_end_is_exclusive() -> None:
    repository = SQLiteSourceUsagePolicyRepository()
    repository.save(_policy("global-v1"))

    at_start = repository.resolve_concurrency_policy(
        at=datetime(2026, 7, 21, 5, 0, tzinfo=timezone.utc)
    )
    at_end = repository.resolve_concurrency_policy(
        at=datetime(2026, 7, 21, 15, 0, tzinfo=timezone.utc)
    )

    assert at_start.default_source_allowed is True
    assert at_end.default_source_allowed is False


def test_nfr_perf_008_empty_allowed_windows_fail_closed() -> None:
    repository = SQLiteSourceUsagePolicyRepository()
    repository.save(_policy("global-v1", allowed_windows=()))

    resolved = repository.resolve_concurrency_policy(at=AT)

    assert resolved.default_source_allowed is False


def test_rule_012_overnight_window_uses_start_day() -> None:
    repository = SQLiteSourceUsagePolicyRepository()
    repository.save(
        _policy(
            "global-v1",
            allowed_windows=(_window(time(22), time(2), weekdays=(1,)),),
        )
    )
    tuesday_after_midnight = datetime(2026, 7, 20, 22, 30, tzinfo=timezone.utc)

    resolved = repository.resolve_concurrency_policy(at=tuesday_after_midnight)

    assert resolved.default_source_allowed is True


def test_fr_039_source_window_override_skips_blocked_head() -> None:
    policy_repository = SQLiteSourceUsagePolicyRepository()
    policy_repository.save(_policy("global-v1", allowed_windows=(_window(time(0), time(23, 59)),)))
    policy_repository.save(
        _policy(
            "source-a-v1",
            source_id="source-a",
            blocked_windows=(_window(time(12), time(13)),),
        )
    )
    execution_repository = SQLiteExecutionRepository()
    peak_time = datetime(2026, 7, 21, 9, 30, tzinfo=timezone.utc)
    for index, source_id in enumerate(("source-a", "source-b")):
        execution_repository.create_or_get(
            RuleExecution(
                execution_id=f"execution-{source_id}",
                idempotency_key_hash=f"key-{source_id}",
                payload_hash=f"payload-{source_id}",
                rule_version_ids=("version-main",),
                scope={},
                triggered_by="scheduler",
                correlation_id=f"correlation-{source_id}",
                source_ids=(source_id,),
                workload_class=WorkloadClass.LIGHT,
                created_at=peak_time + timedelta(seconds=index),
            )
        )

    policy = policy_repository.resolve_concurrency_policy(at=peak_time)
    claimed = execution_repository.claim_next(peak_time, policy)

    assert claimed is not None and claimed.execution_id == "execution-source-b"
    assert execution_repository.get("execution-source-a").status is ExecutionStatus.QUEUED


def test_rule_015_policy_evaluation_rejects_non_utc_time() -> None:
    repository = SQLiteSourceUsagePolicyRepository()
    repository.save(_policy("global-v1"))

    with pytest.raises(ExecutionValidationError, match="must be UTC"):
        repository.resolve_concurrency_policy(at=datetime(2026, 7, 21, 8, 0))


def test_nfr_perf_008_window_rejects_unknown_timezone() -> None:
    with pytest.raises(ExecutionValidationError, match="valid IANA timezone"):
        SourceUsageWindow(
            timezone="Invalid/Timezone",
            weekdays=(1,),
            starts_at=time(8),
            ends_at=time(9),
        )
