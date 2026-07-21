"""SQLite tabanlı kalıcı manuel iş kuyruğu ve çalıştırma geçmişi."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from threading import RLock

from veri_kalitesi.executions.errors import (
    ExecutionNotFoundError,
    ExecutionValidationError,
    IdempotencyConflictError,
)
from veri_kalitesi.executions.models import (
    ConcurrencyPolicy,
    ExecutionAttempt,
    ExecutionStatus,
    ExecutionType,
    MeasurementStatus,
    RuleExecution,
    RuleExecutionResult,
    WorkloadClass,
)


class SQLiteExecutionRepository:
    def __init__(self, database: str = ":memory:") -> None:
        self.connection = sqlite3.connect(database, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self._lock = RLock()
        self._create_schema()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS rule_executions (
                execution_id TEXT PRIMARY KEY,
                execution_type TEXT NOT NULL,
                status TEXT NOT NULL,
                idempotency_key_hash TEXT NOT NULL UNIQUE,
                payload_hash TEXT NOT NULL,
                rule_version_ids TEXT NOT NULL,
                scope TEXT NOT NULL,
                triggered_by TEXT NOT NULL,
                correlation_id TEXT NOT NULL,
                source_ids TEXT NOT NULL,
                workload_class TEXT NOT NULL,
                error_class TEXT,
                attempt_count INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT,
                cancel_requested_at TEXT,
                cancel_requested_by TEXT,
                cancel_reason TEXT,
                cancelled_at TEXT
            );

            CREATE TABLE IF NOT EXISTS execution_attempts (
                attempt_id TEXT PRIMARY KEY,
                execution_id TEXT NOT NULL,
                attempt_no INTEGER NOT NULL,
                status TEXT NOT NULL,
                error_class TEXT,
                retryable INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE (execution_id, attempt_no),
                FOREIGN KEY (execution_id) REFERENCES rule_executions(execution_id)
            );

            CREATE TABLE IF NOT EXISTS rule_execution_results (
                rule_result_id TEXT PRIMARY KEY,
                execution_id TEXT NOT NULL,
                rule_version_id TEXT NOT NULL,
                population_count INTEGER,
                eligible_count INTEGER,
                evaluated_count INTEGER,
                passed_count INTEGER,
                failed_count INTEGER,
                excluded_count INTEGER,
                technical_error_count INTEGER,
                unknown_count INTEGER,
                measurement_status TEXT,
                completed_partitions TEXT NOT NULL,
                eligible_for_official_scoring INTEGER NOT NULL,
                UNIQUE (execution_id, rule_version_id),
                FOREIGN KEY (execution_id) REFERENCES rule_executions(execution_id)
            );
            """
        )
        self._ensure_execution_columns()
        self._ensure_result_columns()

    def _ensure_execution_columns(self) -> None:
        columns = {
            row["name"]
            for row in self.connection.execute("PRAGMA table_info(rule_executions)").fetchall()
        }
        if "source_ids" not in columns:
            self.connection.execute(
                "ALTER TABLE rule_executions ADD COLUMN source_ids TEXT NOT NULL DEFAULT '[]'"
            )
        if "workload_class" not in columns:
            self.connection.execute(
                """
                ALTER TABLE rule_executions
                ADD COLUMN workload_class TEXT NOT NULL DEFAULT 'LIGHT'
                """
            )
        optional_columns = {
            "cancel_requested_at": "TEXT",
            "cancel_requested_by": "TEXT",
            "cancel_reason": "TEXT",
            "cancelled_at": "TEXT",
        }
        for name, definition in optional_columns.items():
            if name not in columns:
                self.connection.execute(
                    f"ALTER TABLE rule_executions ADD COLUMN {name} {definition}"
                )
        self.connection.commit()

    def _ensure_result_columns(self) -> None:
        columns = {
            row["name"]
            for row in self.connection.execute(
                "PRAGMA table_info(rule_execution_results)"
            ).fetchall()
        }
        if "checked_count" in columns or "not_evaluated_count" in columns:
            completed_partitions = (
                "completed_partitions" if "completed_partitions" in columns else "'[]'"
            )
            eligible_for_official_scoring = (
                "eligible_for_official_scoring"
                if "eligible_for_official_scoring" in columns
                else "1"
            )
            self.connection.execute(
                "ALTER TABLE rule_execution_results RENAME TO rule_execution_results_legacy"
            )
            self.connection.execute(
                """
                CREATE TABLE rule_execution_results (
                    rule_result_id TEXT PRIMARY KEY,
                    execution_id TEXT NOT NULL,
                    rule_version_id TEXT NOT NULL,
                    population_count INTEGER,
                    eligible_count INTEGER,
                    evaluated_count INTEGER,
                    passed_count INTEGER,
                    failed_count INTEGER,
                    excluded_count INTEGER,
                    technical_error_count INTEGER,
                    unknown_count INTEGER,
                    measurement_status TEXT,
                    completed_partitions TEXT NOT NULL,
                    eligible_for_official_scoring INTEGER NOT NULL,
                    UNIQUE (execution_id, rule_version_id),
                    FOREIGN KEY (execution_id) REFERENCES rule_executions(execution_id)
                )
                """
            )
            self.connection.execute(
                f"""
                INSERT INTO rule_execution_results (
                    rule_result_id, execution_id, rule_version_id,
                    population_count, eligible_count, evaluated_count,
                    passed_count, failed_count, excluded_count,
                    technical_error_count, unknown_count, measurement_status,
                    completed_partitions, eligible_for_official_scoring
                )
                SELECT rule_result_id, execution_id, rule_version_id,
                    NULL, NULL, NULL, passed_count, failed_count, NULL, NULL, NULL, NULL,
                    {completed_partitions}, {eligible_for_official_scoring}
                FROM rule_execution_results_legacy
                """
            )
            self.connection.execute("DROP TABLE rule_execution_results_legacy")
            columns = {
                row["name"]
                for row in self.connection.execute(
                    "PRAGMA table_info(rule_execution_results)"
                ).fetchall()
            }
        canonical_columns = {
            "population_count": "INTEGER",
            "eligible_count": "INTEGER",
            "evaluated_count": "INTEGER",
            "passed_count": "INTEGER",
            "failed_count": "INTEGER",
            "excluded_count": "INTEGER",
            "technical_error_count": "INTEGER",
            "unknown_count": "INTEGER",
            "measurement_status": "TEXT",
            "completed_partitions": "TEXT NOT NULL DEFAULT '[]'",
            "eligible_for_official_scoring": "INTEGER NOT NULL DEFAULT 1",
        }
        for name, definition in canonical_columns.items():
            if name not in columns:
                self.connection.execute(
                    f"ALTER TABLE rule_execution_results ADD COLUMN {name} {definition}"
                )
        self.connection.commit()

    def create_or_get(self, execution: RuleExecution) -> tuple[RuleExecution, bool]:
        with self._lock, self.connection:
            existing = self.connection.execute(
                "SELECT * FROM rule_executions WHERE idempotency_key_hash = ?",
                (execution.idempotency_key_hash,),
            ).fetchone()
            if existing is not None:
                if existing["payload_hash"] != execution.payload_hash:
                    raise IdempotencyConflictError(
                        "Idempotency key was already used with a different payload."
                    )
                return _row_to_execution(existing), False
            self.connection.execute(
                """
                INSERT INTO rule_executions (
                    execution_id, execution_type, status, idempotency_key_hash,
                    payload_hash, rule_version_ids, scope, triggered_by, correlation_id,
                    source_ids, workload_class, error_class, attempt_count, created_at,
                    started_at, finished_at, cancel_requested_at, cancel_requested_by,
                    cancel_reason, cancelled_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                _execution_values(execution),
            )
            return execution, True

    def claim_next(
        self,
        started_at: datetime,
        policy: ConcurrencyPolicy | None = None,
    ) -> RuleExecution | None:
        policy = policy or ConcurrencyPolicy()
        with self._lock, self.connection:
            queued_rows = self.connection.execute(
                """
                SELECT * FROM rule_executions
                WHERE status = ?
                ORDER BY created_at, execution_id
                """,
                (ExecutionStatus.QUEUED.value,),
            ).fetchall()
            running = [
                _row_to_execution(item)
                for item in self.connection.execute(
                    "SELECT * FROM rule_executions WHERE status = ?",
                    (ExecutionStatus.RUNNING.value,),
                ).fetchall()
            ]
            heavy_count = sum(item.workload_class is WorkloadClass.HEAVY for item in running)
            light_count = sum(item.workload_class is WorkloadClass.LIGHT for item in running)
            source_counts: dict[str, int] = {}
            heavy_source_counts: dict[str, int] = {}
            for item in running:
                for source_id in item.source_ids:
                    source_counts[source_id] = source_counts.get(source_id, 0) + 1
                    if item.workload_class is WorkloadClass.HEAVY:
                        heavy_source_counts[source_id] = heavy_source_counts.get(source_id, 0) + 1
            row = next(
                (
                    item
                    for item in queued_rows
                    if _fits_policy(
                        _row_to_execution(item),
                        policy,
                        heavy_count,
                        light_count,
                        source_counts,
                        heavy_source_counts,
                    )
                ),
                None,
            )
            if row is None:
                return None
            self.connection.execute(
                """
                UPDATE rule_executions
                SET status = ?, started_at = ?
                WHERE execution_id = ? AND status = ?
                """,
                (
                    ExecutionStatus.RUNNING.value,
                    started_at.isoformat(),
                    row["execution_id"],
                    ExecutionStatus.QUEUED.value,
                ),
            )
            return self.get(row["execution_id"])

    def add_attempt(self, attempt: ExecutionAttempt) -> None:
        with self._lock, self.connection:
            self.connection.execute(
                """
                INSERT INTO execution_attempts (
                    attempt_id, execution_id, attempt_no, status, error_class,
                    retryable, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    attempt.attempt_id,
                    attempt.execution_id,
                    attempt.attempt_no,
                    attempt.status.value,
                    attempt.error_class,
                    1 if attempt.retryable else 0,
                    attempt.created_at.isoformat(),
                ),
            )
            self.connection.execute(
                "UPDATE rule_executions SET attempt_count = ? WHERE execution_id = ?",
                (attempt.attempt_no, attempt.execution_id),
            )

    def complete_success(
        self,
        execution_id: str,
        results: tuple[RuleExecutionResult, ...],
        finished_at: datetime,
    ) -> RuleExecution:
        with self._lock, self.connection:
            current = self.get(execution_id)
            if current.status is ExecutionStatus.CANCEL_REQUESTED:
                return self._write_cancelled(execution_id, finished_at)
            for result in results:
                self.connection.execute(
                    """
                    INSERT INTO rule_execution_results (
                        rule_result_id, execution_id, rule_version_id,
                        population_count, eligible_count, evaluated_count,
                        passed_count, failed_count,
                        excluded_count, technical_error_count, unknown_count,
                        measurement_status, completed_partitions,
                        eligible_for_official_scoring
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.rule_result_id,
                        result.execution_id,
                        result.rule_version_id,
                        result.population_count,
                        result.eligible_count,
                        result.evaluated_count,
                        result.passed_count,
                        result.failed_count,
                        result.excluded_count,
                        result.technical_error_count,
                        result.unknown_count,
                        (
                            result.measurement_status.value
                            if result.measurement_status is not None
                            else None
                        ),
                        json.dumps(result.completed_partitions),
                        1 if result.eligible_for_official_scoring else 0,
                    ),
                )
            self.connection.execute(
                """
                UPDATE rule_executions
                SET status = ?, error_class = NULL, finished_at = ?
                WHERE execution_id = ?
                """,
                (ExecutionStatus.SUCCESS.value, finished_at.isoformat(), execution_id),
            )
        return self.get(execution_id)

    def complete_timeout(
        self,
        execution_id: str,
        error_class: str,
        results: tuple[RuleExecutionResult, ...],
        finished_at: datetime,
    ) -> RuleExecution:
        status = ExecutionStatus.PARTIAL if results else ExecutionStatus.TIMEOUT
        with self._lock, self.connection:
            current = self.get(execution_id)
            if current.status is ExecutionStatus.CANCEL_REQUESTED:
                return self._write_cancelled(execution_id, finished_at)
            for result in results:
                self.connection.execute(
                    """
                    INSERT INTO rule_execution_results (
                        rule_result_id, execution_id, rule_version_id,
                        population_count, eligible_count, evaluated_count,
                        passed_count, failed_count,
                        excluded_count, technical_error_count, unknown_count,
                        measurement_status, completed_partitions,
                        eligible_for_official_scoring
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.rule_result_id,
                        result.execution_id,
                        result.rule_version_id,
                        result.population_count,
                        result.eligible_count,
                        result.evaluated_count,
                        result.passed_count,
                        result.failed_count,
                        result.excluded_count,
                        result.technical_error_count,
                        result.unknown_count,
                        (
                            result.measurement_status.value
                            if result.measurement_status is not None
                            else None
                        ),
                        json.dumps(result.completed_partitions),
                        0,
                    ),
                )
            self.connection.execute(
                """
                UPDATE rule_executions
                SET status = ?, error_class = ?, finished_at = ?
                WHERE execution_id = ?
                """,
                (status.value, error_class, finished_at.isoformat(), execution_id),
            )
        return self.get(execution_id)

    def request_cancel(
        self,
        execution_id: str,
        *,
        actor_id: str,
        reason: str,
        requested_at: datetime,
    ) -> RuleExecution:
        with self._lock, self.connection:
            execution = self.get(execution_id)
            if execution.status is ExecutionStatus.CANCEL_REQUESTED:
                return execution
            if (
                execution.status is ExecutionStatus.CANCELLED
                and execution.cancel_requested_at is not None
            ):
                return execution
            if execution.status is ExecutionStatus.QUEUED:
                status = ExecutionStatus.CANCELLED
                finished_at = requested_at.isoformat()
                cancelled_at = finished_at
            elif execution.status is ExecutionStatus.RUNNING:
                status = ExecutionStatus.CANCEL_REQUESTED
                finished_at = None
                cancelled_at = None
            else:
                raise ExecutionValidationError(
                    "Only queued or running executions can be cancelled."
                )
            self.connection.execute(
                """
                UPDATE rule_executions
                SET status = ?, cancel_requested_at = ?, cancel_requested_by = ?,
                    cancel_reason = ?, cancelled_at = ?, finished_at = ?
                WHERE execution_id = ?
                """,
                (
                    status.value,
                    requested_at.isoformat(),
                    actor_id,
                    reason,
                    cancelled_at,
                    finished_at,
                    execution_id,
                ),
            )
        return self.get(execution_id)

    def complete_cancelled(self, execution_id: str, cancelled_at: datetime) -> RuleExecution:
        with self._lock, self.connection:
            execution = self.get(execution_id)
            if execution.status is not ExecutionStatus.CANCEL_REQUESTED:
                raise ExecutionValidationError(
                    "Only cancellation-requested executions can be closed."
                )
            return self._write_cancelled(execution_id, cancelled_at)

    def _write_cancelled(self, execution_id: str, cancelled_at: datetime) -> RuleExecution:
        self.connection.execute(
            """
            UPDATE rule_executions
            SET status = ?, error_class = NULL, cancelled_at = ?, finished_at = ?
            WHERE execution_id = ?
            """,
            (
                ExecutionStatus.CANCELLED.value,
                cancelled_at.isoformat(),
                cancelled_at.isoformat(),
                execution_id,
            ),
        )
        return self.get(execution_id)

    def complete_technical_error(
        self,
        execution_id: str,
        error_class: str,
        finished_at: datetime,
    ) -> RuleExecution:
        with self._lock, self.connection:
            current = self.get(execution_id)
            if current.status is ExecutionStatus.CANCEL_REQUESTED:
                return self._write_cancelled(execution_id, finished_at)
            self.connection.execute(
                """
                UPDATE rule_executions
                SET status = ?, error_class = ?, finished_at = ?
                WHERE execution_id = ?
                """,
                (
                    ExecutionStatus.TECHNICAL_ERROR.value,
                    error_class,
                    finished_at.isoformat(),
                    execution_id,
                ),
            )
        return self.get(execution_id)

    def get(self, execution_id: str) -> RuleExecution:
        with self._lock:
            row = self.connection.execute(
                "SELECT * FROM rule_executions WHERE execution_id = ?", (execution_id,)
            ).fetchone()
        if row is None:
            raise ExecutionNotFoundError("RuleExecution not found.")
        return _row_to_execution(row)

    def list_executions(self) -> list[RuleExecution]:
        with self._lock:
            rows = self.connection.execute(
                "SELECT * FROM rule_executions ORDER BY created_at, execution_id"
            ).fetchall()
        return [_row_to_execution(row) for row in rows]

    def list_cancel_requested(self) -> list[RuleExecution]:
        with self._lock:
            rows = self.connection.execute(
                """
                SELECT * FROM rule_executions
                WHERE status = ?
                ORDER BY started_at, execution_id
                """,
                (ExecutionStatus.CANCEL_REQUESTED.value,),
            ).fetchall()
        return [_row_to_execution(row) for row in rows]

    def list_attempts(self, execution_id: str) -> list[ExecutionAttempt]:
        with self._lock:
            rows = self.connection.execute(
                """
                SELECT * FROM execution_attempts
                WHERE execution_id = ?
                ORDER BY attempt_no
                """,
                (execution_id,),
            ).fetchall()
        return [_row_to_attempt(row) for row in rows]

    def list_results(self, execution_id: str) -> list[RuleExecutionResult]:
        with self._lock:
            rows = self.connection.execute(
                """
                SELECT * FROM rule_execution_results
                WHERE execution_id = ?
                ORDER BY rule_version_id
                """,
                (execution_id,),
            ).fetchall()
        return [_row_to_result(row) for row in rows]


def _execution_values(execution: RuleExecution) -> tuple[object, ...]:
    return (
        execution.execution_id,
        execution.execution_type.value,
        execution.status.value,
        execution.idempotency_key_hash,
        execution.payload_hash,
        json.dumps(execution.rule_version_ids),
        json.dumps(dict(execution.scope), sort_keys=True),
        execution.triggered_by,
        execution.correlation_id,
        json.dumps(execution.source_ids),
        execution.workload_class.value,
        execution.error_class,
        execution.attempt_count,
        execution.created_at.isoformat(),
        execution.started_at.isoformat() if execution.started_at else None,
        execution.finished_at.isoformat() if execution.finished_at else None,
        execution.cancel_requested_at.isoformat() if execution.cancel_requested_at else None,
        execution.cancel_requested_by,
        execution.cancel_reason,
        execution.cancelled_at.isoformat() if execution.cancelled_at else None,
    )


def _row_to_execution(row: sqlite3.Row) -> RuleExecution:
    return RuleExecution(
        execution_id=row["execution_id"],
        execution_type=ExecutionType(row["execution_type"]),
        status=ExecutionStatus(row["status"]),
        idempotency_key_hash=row["idempotency_key_hash"],
        payload_hash=row["payload_hash"],
        rule_version_ids=tuple(json.loads(row["rule_version_ids"])),
        scope=json.loads(row["scope"]),
        triggered_by=row["triggered_by"],
        correlation_id=row["correlation_id"],
        source_ids=tuple(json.loads(row["source_ids"])),
        workload_class=WorkloadClass(row["workload_class"]),
        error_class=row["error_class"],
        attempt_count=row["attempt_count"],
        created_at=datetime.fromisoformat(row["created_at"]),
        started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
        finished_at=datetime.fromisoformat(row["finished_at"]) if row["finished_at"] else None,
        cancel_requested_at=datetime.fromisoformat(row["cancel_requested_at"])
        if row["cancel_requested_at"]
        else None,
        cancel_requested_by=row["cancel_requested_by"],
        cancel_reason=row["cancel_reason"],
        cancelled_at=datetime.fromisoformat(row["cancelled_at"]) if row["cancelled_at"] else None,
    )


def _row_to_attempt(row: sqlite3.Row) -> ExecutionAttempt:
    return ExecutionAttempt(
        attempt_id=row["attempt_id"],
        execution_id=row["execution_id"],
        attempt_no=row["attempt_no"],
        status=ExecutionStatus(row["status"]),
        error_class=row["error_class"],
        retryable=bool(row["retryable"]),
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def _row_to_result(row: sqlite3.Row) -> RuleExecutionResult:
    return RuleExecutionResult(
        rule_result_id=row["rule_result_id"],
        execution_id=row["execution_id"],
        rule_version_id=row["rule_version_id"],
        population_count=row["population_count"],
        eligible_count=row["eligible_count"],
        evaluated_count=row["evaluated_count"],
        passed_count=row["passed_count"],
        failed_count=row["failed_count"],
        excluded_count=row["excluded_count"],
        technical_error_count=row["technical_error_count"],
        unknown_count=row["unknown_count"],
        measurement_status=(
            MeasurementStatus(row["measurement_status"])
            if row["measurement_status"] is not None
            else None
        ),
        completed_partitions=tuple(json.loads(row["completed_partitions"])),
        eligible_for_official_scoring=bool(row["eligible_for_official_scoring"]),
    )


def _fits_policy(
    execution: RuleExecution,
    policy: ConcurrencyPolicy,
    heavy_count: int,
    light_count: int,
    source_counts: dict[str, int],
    heavy_source_counts: dict[str, int],
) -> bool:
    if any(not policy.source_allowed(source_id) for source_id in execution.source_ids):
        return False
    if heavy_count + light_count >= policy.max_total:
        return False
    if execution.workload_class is WorkloadClass.HEAVY and heavy_count >= policy.max_heavy:
        return False
    if execution.workload_class is WorkloadClass.LIGHT and light_count >= policy.max_light:
        return False
    if execution.workload_class is WorkloadClass.HEAVY and any(
        heavy_source_counts.get(source_id, 0) >= policy.heavy_source_limit(source_id)
        for source_id in execution.source_ids
    ):
        return False
    return all(
        source_counts.get(source_id, 0) < policy.source_limit(source_id)
        for source_id in execution.source_ids
    )
