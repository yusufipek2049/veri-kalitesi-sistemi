"""Manuel çalıştırma, deneme ve sonuç domain modelleri."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ExecutionType(str, Enum):
    MANUAL = "MANUAL"
    SCHEDULED = "SCHEDULED"


class ExecutionStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    TECHNICAL_ERROR = "TECHNICAL_ERROR"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"


class WorkloadClass(str, Enum):
    HEAVY = "HEAVY"
    LIGHT = "LIGHT"


@dataclass(frozen=True)
class ExecutionTimeouts:
    connection_seconds: int = 15
    query_seconds: int = 30 * 60
    total_seconds: int = 60 * 60


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: float = 1.0


@dataclass(frozen=True)
class ConcurrencyPolicy:
    max_heavy: int = 2
    max_light: int = 4
    default_source_limit: int = 4
    default_heavy_source_limit: int = 1
    per_source_limits: Mapping[str, int] = field(default_factory=dict)
    per_source_heavy_limits: Mapping[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "per_source_limits", MappingProxyType(dict(self.per_source_limits)))
        object.__setattr__(
            self,
            "per_source_heavy_limits",
            MappingProxyType(dict(self.per_source_heavy_limits)),
        )

    def source_limit(self, source_id: str) -> int:
        return self.per_source_limits.get(source_id, self.default_source_limit)

    def heavy_source_limit(self, source_id: str) -> int:
        return self.per_source_heavy_limits.get(
            source_id, self.default_heavy_source_limit
        )


@dataclass(frozen=True)
class RuleExecution:
    idempotency_key_hash: str
    payload_hash: str
    rule_version_ids: tuple[str, ...]
    scope: Mapping[str, Any]
    triggered_by: str
    correlation_id: str
    source_ids: tuple[str, ...] = ()
    workload_class: WorkloadClass = WorkloadClass.LIGHT
    execution_type: ExecutionType = ExecutionType.MANUAL
    status: ExecutionStatus = ExecutionStatus.QUEUED
    execution_id: str = field(default_factory=lambda: str(uuid4()))
    error_class: str | None = None
    attempt_count: int = 0
    created_at: datetime = field(default_factory=utc_now)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    cancel_requested_at: datetime | None = None
    cancel_requested_by: str | None = None
    cancel_reason: str | None = None
    cancelled_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "scope", MappingProxyType(dict(self.scope)))


@dataclass(frozen=True)
class RuleResultComputation:
    rule_version_id: str
    checked_count: int
    passed_count: int
    failed_count: int
    not_evaluated_count: int = 0
    completed_partitions: tuple[str, ...] = ()


@dataclass(frozen=True)
class RuleExecutionResult:
    execution_id: str
    rule_version_id: str
    checked_count: int
    passed_count: int
    failed_count: int
    not_evaluated_count: int = 0
    completed_partitions: tuple[str, ...] = ()
    eligible_for_official_scoring: bool = True
    rule_result_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(frozen=True)
class ExecutionAttempt:
    execution_id: str
    attempt_no: int
    status: ExecutionStatus
    error_class: str | None = None
    retryable: bool = False
    attempt_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=utc_now)
