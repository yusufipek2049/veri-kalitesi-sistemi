"""Sürümlü kaynak kullanım politikası ve güvenli kota çözümleme."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from enum import Enum
from threading import RLock
from types import MappingProxyType
from typing import Protocol
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from veri_kalitesi.executions.errors import (
    ExecutionValidationError,
    SourceUsagePolicyConflictError,
    SourceUsagePolicyTechnicalError,
    SourceUsagePolicyUnavailableError,
)
from veri_kalitesi.executions.models import ConcurrencyPolicy


class SourceUsagePolicyStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


@dataclass(frozen=True)
class SourceUsageWindow:
    timezone: str
    weekdays: tuple[int, ...]
    starts_at: time
    ends_at: time

    def __post_init__(self) -> None:
        if not isinstance(self.timezone, str) or not self.timezone.strip():
            raise ExecutionValidationError("Source usage window timezone is required.")
        try:
            ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError as exc:
            raise ExecutionValidationError(
                "Source usage window timezone must be a valid IANA timezone."
            ) from exc
        if (
            not self.weekdays
            or len(set(self.weekdays)) != len(self.weekdays)
            or any(
                isinstance(day, bool) or not isinstance(day, int) or not 1 <= day <= 7
                for day in self.weekdays
            )
        ):
            raise ExecutionValidationError(
                "Source usage window weekdays must be unique ISO weekday values."
            )
        if not isinstance(self.starts_at, time) or not isinstance(self.ends_at, time):
            raise ExecutionValidationError("Source usage window times are required.")
        if self.starts_at.tzinfo is not None or self.ends_at.tzinfo is not None:
            raise ExecutionValidationError("Source usage window times must be local times.")
        if self.starts_at == self.ends_at:
            raise ExecutionValidationError("Source usage window start and end times must differ.")


@dataclass(frozen=True)
class SourceUsagePolicy:
    policy_id: str
    policy_version: int
    max_concurrent_queries: int
    max_workers: int
    query_timeout_seconds: int
    retry_count: int
    retry_delay_seconds: float
    rate_limit: Mapping[str, object]
    status: SourceUsagePolicyStatus = SourceUsagePolicyStatus.DRAFT
    source_id: str | None = None
    source_type: str | None = None
    allowed_windows: tuple[SourceUsageWindow, ...] = ()
    blocked_windows: tuple[SourceUsageWindow, ...] = ()
    cpu_limit_percent: float | None = None
    io_limit_percent: float | None = None
    peak_hours_behavior: str = "REJECT"
    timeout_cancel_behavior: str = "CANCEL"
    approved_by: str | None = None
    audit_reference: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "rate_limit", MappingProxyType(dict(self.rate_limit)))
        object.__setattr__(self, "allowed_windows", tuple(self.allowed_windows))
        object.__setattr__(self, "blocked_windows", tuple(self.blocked_windows))


class SourceUsagePolicyResolver(Protocol):
    def resolve_concurrency_policy(self, *, at: datetime) -> ConcurrencyPolicy: ...


class SQLiteSourceUsagePolicyRepository:
    def __init__(
        self,
        database: str = ":memory:",
        *,
        source_types_by_id: Mapping[str, str] | None = None,
    ) -> None:
        self.connection = sqlite3.connect(database, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.source_types_by_id = MappingProxyType(dict(source_types_by_id or {}))
        self._lock = RLock()
        self._create_schema()

    def _create_schema(self) -> None:
        try:
            self.connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS source_usage_policies (
                    policy_id TEXT PRIMARY KEY,
                    policy_version INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    source_id TEXT,
                    source_type TEXT,
                    max_concurrent_queries INTEGER NOT NULL,
                    max_workers INTEGER NOT NULL,
                    query_timeout_seconds INTEGER NOT NULL,
                    retry_count INTEGER NOT NULL,
                    retry_delay_seconds REAL NOT NULL,
                    rate_limit TEXT NOT NULL,
                    allowed_windows TEXT NOT NULL,
                    blocked_windows TEXT NOT NULL,
                    cpu_limit_percent REAL,
                    io_limit_percent REAL,
                    peak_hours_behavior TEXT NOT NULL,
                    timeout_cancel_behavior TEXT NOT NULL,
                    approved_by TEXT,
                    audit_reference TEXT,
                    CHECK (NOT (source_id IS NOT NULL AND source_type IS NOT NULL)),
                    UNIQUE (policy_version, source_id, source_type)
                );

                CREATE UNIQUE INDEX IF NOT EXISTS uq_source_usage_policy_scope_version
                ON source_usage_policies (
                    policy_version,
                    COALESCE(source_id, ''),
                    COALESCE(source_type, '')
                );

                CREATE UNIQUE INDEX IF NOT EXISTS uq_active_source_usage_policy_scope
                ON source_usage_policies (
                    COALESCE(source_id, ''),
                    COALESCE(source_type, '')
                )
                WHERE status = 'ACTIVE';
                """
            )
        except sqlite3.DatabaseError as exc:
            raise SourceUsagePolicyTechnicalError(
                "Source usage policy schema could not be initialized."
            ) from exc

    def save(self, policy: SourceUsagePolicy) -> SourceUsagePolicy:
        _validate_source_usage_policy(policy)
        try:
            with self._lock, self.connection:
                if policy.status is SourceUsagePolicyStatus.ACTIVE:
                    self._retire_active_scope(policy)
                self.connection.execute(
                    """
                    INSERT INTO source_usage_policies (
                        policy_id, policy_version, status, source_id, source_type,
                        max_concurrent_queries, max_workers, query_timeout_seconds,
                        retry_count, retry_delay_seconds, rate_limit, allowed_windows,
                        blocked_windows, cpu_limit_percent, io_limit_percent,
                        peak_hours_behavior, timeout_cancel_behavior, approved_by,
                        audit_reference
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    _policy_values(policy),
                )
        except sqlite3.IntegrityError as exc:
            raise SourceUsagePolicyConflictError(
                "Source usage policy identity or version conflicts."
            ) from exc
        except sqlite3.DatabaseError as exc:
            raise SourceUsagePolicyTechnicalError(
                "Source usage policy could not be persisted."
            ) from exc
        return policy

    def list_policies(self) -> list[SourceUsagePolicy]:
        try:
            rows = self.connection.execute(
                """
                SELECT * FROM source_usage_policies
                ORDER BY policy_version, policy_id
                """
            ).fetchall()
        except sqlite3.DatabaseError as exc:
            raise SourceUsagePolicyTechnicalError(
                "Source usage policies could not be read."
            ) from exc
        return _rows_to_policies(rows)

    def resolve_concurrency_policy(self, *, at: datetime) -> ConcurrencyPolicy:
        _validate_evaluation_time(at)
        try:
            rows = self.connection.execute(
                """
                SELECT * FROM source_usage_policies
                WHERE status = ?
                ORDER BY policy_version DESC, policy_id
                """,
                (SourceUsagePolicyStatus.ACTIVE.value,),
            ).fetchall()
        except sqlite3.DatabaseError as exc:
            raise SourceUsagePolicyTechnicalError(
                "Active source usage policies could not be read."
            ) from exc

        policies = _rows_to_policies(rows)
        global_policy = next(
            (
                policy
                for policy in policies
                if policy.source_id is None and policy.source_type is None
            ),
            None,
        )
        if global_policy is None:
            raise SourceUsagePolicyUnavailableError(
                "Active global source usage policy is required."
            )

        by_source = {
            policy.source_id: policy for policy in policies if policy.source_id is not None
        }
        by_type = {
            policy.source_type: policy for policy in policies if policy.source_type is not None
        }
        resolved_limits = {
            source_id: _effective_source_limit(policy) for source_id, policy in by_source.items()
        }
        resolved_allowed = {
            source_id: _policy_allows_at(policy, at) for source_id, policy in by_source.items()
        }
        for source_id, source_type in self.source_types_by_id.items():
            override = by_source.get(source_id) or by_type.get(source_type)
            if override is not None:
                resolved_limits[source_id] = _effective_source_limit(override)
                resolved_allowed[source_id] = _policy_allows_at(override, at)

        global_worker_limit = global_policy.max_workers
        global_source_limit = _effective_source_limit(global_policy)
        return ConcurrencyPolicy(
            max_total=global_worker_limit,
            max_heavy=global_worker_limit,
            max_light=global_worker_limit,
            default_source_limit=global_source_limit,
            default_heavy_source_limit=global_source_limit,
            default_source_allowed=_policy_allows_at(global_policy, at),
            per_source_limits=resolved_limits,
            per_source_heavy_limits=resolved_limits,
            per_source_allowed=resolved_allowed,
        )

    def _retire_active_scope(self, policy: SourceUsagePolicy) -> None:
        self.connection.execute(
            """
            UPDATE source_usage_policies
            SET status = ?
            WHERE status = ?
              AND source_id IS ?
              AND source_type IS ?
            """,
            (
                SourceUsagePolicyStatus.RETIRED.value,
                SourceUsagePolicyStatus.ACTIVE.value,
                policy.source_id,
                policy.source_type,
            ),
        )


def _validate_source_usage_policy(policy: SourceUsagePolicy) -> None:
    if not policy.policy_id.strip() or policy.policy_version <= 0:
        raise ExecutionValidationError("Policy identity and version are required.")
    if policy.source_id is not None and policy.source_type is not None:
        raise ExecutionValidationError("Policy can target a source id or source type, not both.")
    if policy.source_id == "" or policy.source_type == "":
        raise ExecutionValidationError("Source id and source type cannot be empty.")
    if any(
        not isinstance(window, SourceUsageWindow)
        for window in (*policy.allowed_windows, *policy.blocked_windows)
    ):
        raise ExecutionValidationError("Source usage windows are invalid.")
    integer_limits = (
        policy.max_concurrent_queries,
        policy.max_workers,
        policy.query_timeout_seconds,
    )
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value <= 0
        for value in integer_limits
    ):
        raise ExecutionValidationError("Source policy limits must be positive integers.")
    if (
        isinstance(policy.retry_count, bool)
        or not isinstance(policy.retry_count, int)
        or not 0 <= policy.retry_count <= 3
        or isinstance(policy.retry_delay_seconds, bool)
        or policy.retry_delay_seconds < 0
    ):
        raise ExecutionValidationError("Source policy retry values are invalid.")
    for value in (policy.cpu_limit_percent, policy.io_limit_percent):
        if value is not None and (
            isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 < value <= 100
        ):
            raise ExecutionValidationError("CPU and IO limits must be between 0 and 100.")
    if not policy.peak_hours_behavior.strip() or not policy.timeout_cancel_behavior.strip():
        raise ExecutionValidationError("Source policy behaviors are required.")
    if policy.peak_hours_behavior not in {"DEFER", "REJECT"}:
        raise ExecutionValidationError("Peak-hours behavior is not supported.")
    if policy.status is SourceUsagePolicyStatus.ACTIVE and (
        not policy.approved_by or not policy.audit_reference
    ):
        raise ExecutionValidationError(
            "Active source policy requires approval and audit references."
        )
    try:
        json.dumps(dict(policy.rate_limit), sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise ExecutionValidationError("Rate limit must be JSON serializable.") from exc


def _effective_source_limit(policy: SourceUsagePolicy) -> int:
    return min(policy.max_concurrent_queries, policy.max_workers)


def _validate_evaluation_time(at: datetime) -> None:
    if at.tzinfo is None or at.utcoffset() != timedelta(0):
        raise ExecutionValidationError("Source usage policy evaluation time must be UTC.")


def _policy_allows_at(policy: SourceUsagePolicy, at: datetime) -> bool:
    if any(_window_contains(window, at) for window in policy.blocked_windows):
        return False
    return any(_window_contains(window, at) for window in policy.allowed_windows)


def _window_contains(window: SourceUsageWindow, at: datetime) -> bool:
    local = at.astimezone(ZoneInfo(window.timezone))
    local_time = local.timetz().replace(tzinfo=None)
    weekday = local.isoweekday()
    if window.starts_at < window.ends_at:
        return weekday in window.weekdays and window.starts_at <= local_time < window.ends_at
    if local_time >= window.starts_at:
        return weekday in window.weekdays
    previous_weekday = 7 if weekday == 1 else weekday - 1
    return local_time < window.ends_at and previous_weekday in window.weekdays


def _window_values(window: SourceUsageWindow) -> dict[str, object]:
    return {
        "timezone": window.timezone,
        "weekdays": list(window.weekdays),
        "starts_at": window.starts_at.isoformat(),
        "ends_at": window.ends_at.isoformat(),
    }


def _window_from_value(value: object) -> SourceUsageWindow:
    if not isinstance(value, dict):
        raise ValueError("Source usage window payload must be an object.")
    weekdays = value["weekdays"]
    if not isinstance(weekdays, list):
        raise ValueError("Source usage window weekdays must be a list.")
    return SourceUsageWindow(
        timezone=str(value["timezone"]),
        weekdays=tuple(weekdays),
        starts_at=time.fromisoformat(str(value["starts_at"])),
        ends_at=time.fromisoformat(str(value["ends_at"])),
    )


def _policy_values(policy: SourceUsagePolicy) -> tuple[object, ...]:
    return (
        policy.policy_id,
        policy.policy_version,
        policy.status.value,
        policy.source_id,
        policy.source_type,
        policy.max_concurrent_queries,
        policy.max_workers,
        policy.query_timeout_seconds,
        policy.retry_count,
        policy.retry_delay_seconds,
        json.dumps(dict(policy.rate_limit), sort_keys=True),
        json.dumps([_window_values(window) for window in policy.allowed_windows]),
        json.dumps([_window_values(window) for window in policy.blocked_windows]),
        policy.cpu_limit_percent,
        policy.io_limit_percent,
        policy.peak_hours_behavior,
        policy.timeout_cancel_behavior,
        policy.approved_by,
        policy.audit_reference,
    )


def _row_to_policy(row: sqlite3.Row) -> SourceUsagePolicy:
    return SourceUsagePolicy(
        policy_id=row["policy_id"],
        policy_version=row["policy_version"],
        status=SourceUsagePolicyStatus(row["status"]),
        source_id=row["source_id"],
        source_type=row["source_type"],
        max_concurrent_queries=row["max_concurrent_queries"],
        max_workers=row["max_workers"],
        query_timeout_seconds=row["query_timeout_seconds"],
        retry_count=row["retry_count"],
        retry_delay_seconds=row["retry_delay_seconds"],
        rate_limit=json.loads(row["rate_limit"]),
        allowed_windows=tuple(
            _window_from_value(value) for value in json.loads(row["allowed_windows"])
        ),
        blocked_windows=tuple(
            _window_from_value(value) for value in json.loads(row["blocked_windows"])
        ),
        cpu_limit_percent=row["cpu_limit_percent"],
        io_limit_percent=row["io_limit_percent"],
        peak_hours_behavior=row["peak_hours_behavior"],
        timeout_cancel_behavior=row["timeout_cancel_behavior"],
        approved_by=row["approved_by"],
        audit_reference=row["audit_reference"],
    )


def _rows_to_policies(rows: list[sqlite3.Row]) -> list[SourceUsagePolicy]:
    try:
        return [_row_to_policy(row) for row in rows]
    except (KeyError, TypeError, ValueError, ExecutionValidationError, json.JSONDecodeError) as exc:
        raise SourceUsagePolicyTechnicalError(
            "Stored source usage policy payload is invalid."
        ) from exc
