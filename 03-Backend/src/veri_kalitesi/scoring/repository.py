"""SQLite tabanlı değişmez QualityScore geçmişi."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from decimal import Decimal
from threading import RLock
from typing import Mapping

from veri_kalitesi.audit import PreparedAuditEvent, SQLiteTransactionalAudit
from veri_kalitesi.data_sources.models import Criticality
from veri_kalitesi.executions.models import MeasurementStatus
from veri_kalitesi.rules.models import QualityDimension
from veri_kalitesi.scoring.errors import (
    ScoreNotFoundError,
    ScoringValidationError,
)
from veri_kalitesi.scoring.models import (
    DEFAULT_THRESHOLD_SET,
    QualityScore,
    ScoreLevel,
    ScoreScopeType,
    ScoreStatus,
    ScoringApprovalStatus,
    ScoringConfiguration,
    ScoringConfigurationApproval,
    ThresholdSet,
    default_criticality_weights,
    default_dimension_weights,
    is_official_observation,
    thaw,
    utc_now,
)


class SQLiteScoreRepository:
    def __init__(self, database: str = ":memory:") -> None:
        self.connection = sqlite3.connect(database, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self._lock = RLock()
        self._create_schema()

    def _create_schema(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS quality_scores (
                quality_score_id TEXT PRIMARY KEY,
                execution_id TEXT NOT NULL,
                rule_result_id TEXT,
                rule_version_id TEXT,
                scope_type TEXT NOT NULL,
                scope_id TEXT,
                score_value TEXT,
                score_status TEXT NOT NULL,
                measurement_status TEXT,
                level TEXT,
                calculation_details TEXT NOT NULL,
                calculated_at TEXT NOT NULL,
                UNIQUE (execution_id, rule_version_id)
            )
            """
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS scoring_configurations (
                configuration_id TEXT PRIMARY KEY,
                version TEXT NOT NULL UNIQUE,
                threshold_version TEXT NOT NULL,
                critical_upper_exclusive TEXT NOT NULL,
                risky_upper_exclusive TEXT NOT NULL,
                acceptable_upper_exclusive TEXT NOT NULL,
                dimension_weights TEXT NOT NULL,
                criticality_weights TEXT NOT NULL,
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL,
                is_active INTEGER NOT NULL,
                activated_at TEXT
            )
            """
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS scoring_configuration_approvals (
                approval_id TEXT PRIMARY KEY,
                configuration_id TEXT NOT NULL UNIQUE,
                maker_actor_id TEXT NOT NULL,
                checker_actor_id TEXT,
                policy_version TEXT NOT NULL,
                status TEXT NOT NULL,
                decision_reason_code TEXT,
                requested_at TEXT NOT NULL,
                decided_at TEXT,
                FOREIGN KEY (configuration_id)
                    REFERENCES scoring_configurations(configuration_id)
            )
            """
        )
        self._ensure_schema()
        self._ensure_configuration_schema()
        self.connection.execute("DROP INDEX IF EXISTS idx_quality_scores_execution_scope")
        self.connection.executescript(
            """
            CREATE UNIQUE INDEX idx_quality_scores_execution_scope
            ON quality_scores(execution_id, scope_type, COALESCE(scope_id, ''));

            CREATE INDEX IF NOT EXISTS idx_quality_scores_scope_time
            ON quality_scores(scope_type, scope_id, calculated_at);

            CREATE UNIQUE INDEX IF NOT EXISTS idx_scoring_configurations_one_active
            ON scoring_configurations(is_active) WHERE is_active = 1;
            """
        )
        self._ensure_default_configuration()
        self.connection.commit()

    def _ensure_default_configuration(self) -> None:
        existing = self.connection.execute(
            "SELECT 1 FROM scoring_configurations LIMIT 1"
        ).fetchone()
        if existing is not None:
            return
        now = utc_now()
        self.connection.execute(
            """
            INSERT INTO scoring_configurations (
                configuration_id, version, threshold_version, critical_upper_exclusive,
                risky_upper_exclusive, acceptable_upper_exclusive,
                dimension_weights, criticality_weights, created_by, created_at,
                is_active, activated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
            """,
            (
                "default-scoring-configuration",
                "DEFAULT_SCORING_V1",
                DEFAULT_THRESHOLD_SET.version,
                str(DEFAULT_THRESHOLD_SET.critical_upper_exclusive),
                str(DEFAULT_THRESHOLD_SET.risky_upper_exclusive),
                str(DEFAULT_THRESHOLD_SET.acceptable_upper_exclusive),
                _serialize_dimension_weights(default_dimension_weights()),
                _serialize_criticality_weights(default_criticality_weights()),
                "system",
                now.isoformat(),
                now.isoformat(),
            ),
        )

    def _ensure_configuration_schema(self) -> None:
        columns = {
            row["name"]
            for row in self.connection.execute(
                "PRAGMA table_info(scoring_configurations)"
            ).fetchall()
        }
        if "criticality_weights" not in columns:
            self.connection.execute(
                """
                ALTER TABLE scoring_configurations
                ADD COLUMN criticality_weights TEXT NOT NULL
                DEFAULT '{"LOW":"1.0","MEDIUM":"1.0","HIGH":"1.0","CRITICAL":"1.0"}'
                """
            )

    def _ensure_schema(self) -> None:
        columns = {
            row["name"]: row
            for row in self.connection.execute("PRAGMA table_info(quality_scores)").fetchall()
        }
        if columns["rule_version_id"]["notnull"] or columns["scope_id"]["notnull"]:
            self.connection.execute("DROP INDEX IF EXISTS idx_quality_scores_scope_time")
            self.connection.execute("DROP INDEX IF EXISTS idx_quality_scores_execution_scope")
            self.connection.execute("ALTER TABLE quality_scores RENAME TO quality_scores_old")
            self.connection.execute(
                """
                CREATE TABLE quality_scores (
                    quality_score_id TEXT PRIMARY KEY,
                    execution_id TEXT NOT NULL,
                    rule_result_id TEXT,
                    rule_version_id TEXT,
                    scope_type TEXT NOT NULL,
                    scope_id TEXT,
                    score_value TEXT,
                    score_status TEXT NOT NULL,
                    measurement_status TEXT,
                    level TEXT,
                    calculation_details TEXT NOT NULL,
                    calculated_at TEXT NOT NULL,
                    UNIQUE (execution_id, rule_version_id)
                )
                """
            )
            self.connection.execute(
                """
                INSERT INTO quality_scores (
                    quality_score_id, execution_id, rule_result_id, rule_version_id,
                    scope_type, scope_id, score_value, score_status, level,
                    measurement_status, calculation_details, calculated_at
                )
                SELECT quality_score_id, execution_id, rule_result_id, rule_version_id,
                    scope_type, scope_id, score_value, score_status, NULL,
                    NULL, calculation_details, calculated_at
                FROM quality_scores_old
                """
            )
            self.connection.execute("DROP TABLE quality_scores_old")
        elif "level" not in columns:
            self.connection.execute("ALTER TABLE quality_scores ADD COLUMN level TEXT")
        columns = {
            row["name"]: row
            for row in self.connection.execute("PRAGMA table_info(quality_scores)").fetchall()
        }
        if "measurement_status" not in columns:
            self.connection.execute("ALTER TABLE quality_scores ADD COLUMN measurement_status TEXT")

    def add_or_get(self, score: QualityScore) -> tuple[QualityScore, bool]:
        with self._lock, self.connection:
            existing = self.connection.execute(
                """
                SELECT * FROM quality_scores
                WHERE execution_id = ? AND scope_type = ? AND scope_id IS ?
                """,
                (score.execution_id, score.scope_type.value, score.scope_id),
            ).fetchone()
            if existing is not None:
                return _row_to_score(existing), False
            self.connection.execute(
                """
                INSERT INTO quality_scores (
                    quality_score_id, execution_id, rule_result_id, rule_version_id,
                    scope_type, scope_id, score_value, score_status,
                    measurement_status, level, calculation_details, calculated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    score.quality_score_id,
                    score.execution_id,
                    score.rule_result_id,
                    score.rule_version_id,
                    score.scope_type.value,
                    score.scope_id,
                    str(score.score_value) if score.score_value is not None else None,
                    score.score_status.value,
                    (
                        score.measurement_status.value
                        if score.measurement_status is not None
                        else None
                    ),
                    score.level.value if score.level else None,
                    json.dumps(thaw(score.calculation_details), sort_keys=True),
                    score.calculated_at.isoformat(),
                ),
            )
        return score, True

    def get(self, quality_score_id: str) -> QualityScore:
        with self._lock:
            row = self.connection.execute(
                "SELECT * FROM quality_scores WHERE quality_score_id = ?",
                (quality_score_id,),
            ).fetchone()
        if row is None:
            raise ScoreNotFoundError("QualityScore not found.")
        return _row_to_score(row)

    def list_for_execution(self, execution_id: str) -> list[QualityScore]:
        with self._lock:
            rows = self.connection.execute(
                """
                SELECT * FROM quality_scores
                WHERE execution_id = ?
                ORDER BY scope_type, scope_id
                """,
                (execution_id,),
            ).fetchall()
        return [_row_to_score(row) for row in rows]

    def list_for_dashboard_trend(
        self,
        start_at: datetime,
        end_at: datetime,
        allowed_source_ids: frozenset[str],
        include_enterprise: bool,
    ) -> list[QualityScore]:
        if (
            start_at.tzinfo is None
            or start_at.utcoffset() is None
            or end_at.tzinfo is None
            or end_at.utcoffset() is None
            or start_at >= end_at
        ):
            raise ScoringValidationError("Dashboard trend time range is invalid.")
        if any(not source_id.strip() for source_id in allowed_source_ids):
            raise ScoringValidationError("Dashboard trend source IDs must not be blank.")
        scope_clauses: list[str] = []
        parameters: list[object] = [start_at.isoformat(), end_at.isoformat()]
        if allowed_source_ids:
            placeholders = ", ".join("?" for _ in allowed_source_ids)
            scope_clauses.append(f"(scope_type = ? AND scope_id IN ({placeholders}))")
            parameters.append(ScoreScopeType.SOURCE.value)
            parameters.extend(sorted(allowed_source_ids))
        if include_enterprise:
            scope_clauses.append("(scope_type = ? AND scope_id IS NULL)")
            parameters.append(ScoreScopeType.ENTERPRISE.value)
        if not scope_clauses:
            return []
        query = f"""
            SELECT * FROM quality_scores
            WHERE julianday(calculated_at) >= julianday(?)
              AND julianday(calculated_at) <= julianday(?)
              AND ({" OR ".join(scope_clauses)})
            ORDER BY calculated_at, scope_type, scope_id, quality_score_id
        """
        with self._lock:
            rows = self.connection.execute(query, parameters).fetchall()
        return [score for row in rows if is_official_observation(score := _row_to_score(row))]

    def add_configuration_with_approval(
        self,
        configuration: ScoringConfiguration,
        approval: ScoringConfigurationApproval,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> tuple[ScoringConfiguration, ScoringConfigurationApproval]:
        if audit_outbox.connection is not self.connection:
            raise ScoringValidationError("Audit outbox must share the scoring transaction.")
        try:
            with self._lock, self.connection:
                self.connection.execute(
                    """
                    INSERT INTO scoring_configurations (
                        configuration_id, version, threshold_version,
                        critical_upper_exclusive,
                        risky_upper_exclusive, acceptable_upper_exclusive,
                        dimension_weights, criticality_weights, created_by,
                        created_at, is_active, activated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL)
                    """,
                    (
                        configuration.configuration_id,
                        configuration.version,
                        configuration.threshold_set.version,
                        str(configuration.threshold_set.critical_upper_exclusive),
                        str(configuration.threshold_set.risky_upper_exclusive),
                        str(configuration.threshold_set.acceptable_upper_exclusive),
                        _serialize_dimension_weights(configuration.dimension_weights),
                        _serialize_criticality_weights(configuration.criticality_weights),
                        configuration.created_by,
                        configuration.created_at.isoformat(),
                    ),
                )
                self.connection.execute(
                    """
                    INSERT INTO scoring_configuration_approvals (
                        approval_id, configuration_id, maker_actor_id,
                        checker_actor_id, policy_version, status,
                        decision_reason_code, requested_at, decided_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        approval.approval_id,
                        approval.configuration_id,
                        approval.maker_actor_id,
                        approval.checker_actor_id,
                        approval.policy_version,
                        approval.status.value,
                        approval.decision_reason_code,
                        approval.requested_at.isoformat(),
                        approval.decided_at.isoformat() if approval.decided_at else None,
                    ),
                )
                audit_outbox.stage(audit_event)
        except sqlite3.IntegrityError as exc:
            raise ScoringValidationError("Scoring configuration version must be unique.") from exc
        return (
            self.get_configuration(configuration.version),
            self.get_configuration_approval(approval.approval_id),
        )

    def get_configuration_approval(self, approval_id: str) -> ScoringConfigurationApproval:
        with self._lock:
            row = self.connection.execute(
                "SELECT * FROM scoring_configuration_approvals WHERE approval_id = ?",
                (approval_id,),
            ).fetchone()
        if row is None:
            raise ScoreNotFoundError("ScoringConfigurationApproval not found.")
        return _row_to_configuration_approval(row)

    def decide_configuration_approval(
        self,
        approval: ScoringConfigurationApproval,
        *,
        activate_configuration: bool,
        activated_at: datetime,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> tuple[ScoringConfiguration, ScoringConfigurationApproval]:
        if audit_outbox.connection is not self.connection:
            raise ScoringValidationError("Audit outbox must share the scoring transaction.")
        with self._lock, self.connection:
            latest = self.connection.execute(
                "SELECT configuration_id FROM scoring_configurations ORDER BY rowid DESC LIMIT 1"
            ).fetchone()
            if latest is None or latest["configuration_id"] != approval.configuration_id:
                raise ScoringValidationError(
                    "Approval does not target the latest scoring configuration."
                )
            cursor = self.connection.execute(
                """
                UPDATE scoring_configuration_approvals
                SET status = ?, checker_actor_id = ?, decision_reason_code = ?, decided_at = ?
                WHERE approval_id = ? AND status = ?
                """,
                (
                    approval.status.value,
                    approval.checker_actor_id,
                    approval.decision_reason_code,
                    approval.decided_at.isoformat() if approval.decided_at else None,
                    approval.approval_id,
                    ScoringApprovalStatus.PENDING.value,
                ),
            )
            if cursor.rowcount != 1:
                raise ScoringValidationError("Scoring configuration approval is not pending.")
            if activate_configuration:
                self.connection.execute(
                    "UPDATE scoring_configurations SET is_active = 0 WHERE is_active = 1"
                )
                cursor = self.connection.execute(
                    """
                    UPDATE scoring_configurations
                    SET is_active = 1, activated_at = ?
                    WHERE configuration_id = ? AND is_active = 0
                    """,
                    (activated_at.isoformat(), approval.configuration_id),
                )
                if cursor.rowcount != 1:
                    raise ScoringValidationError("Scoring configuration cannot be activated.")
            audit_outbox.stage(audit_event)
        configuration = self.connection.execute(
            "SELECT version FROM scoring_configurations WHERE configuration_id = ?",
            (approval.configuration_id,),
        ).fetchone()
        if configuration is None:
            raise ScoreNotFoundError("ScoringConfiguration not found.")
        return (
            self.get_configuration(configuration["version"]),
            self.get_configuration_approval(approval.approval_id),
        )

    def get_configuration(self, version: str) -> ScoringConfiguration:
        with self._lock:
            row = self.connection.execute(
                "SELECT * FROM scoring_configurations WHERE version = ?", (version,)
            ).fetchone()
        if row is None:
            raise ScoreNotFoundError("ScoringConfiguration not found.")
        return _row_to_configuration(row)

    def get_configuration_by_id(self, configuration_id: str) -> ScoringConfiguration:
        with self._lock:
            row = self.connection.execute(
                "SELECT * FROM scoring_configurations WHERE configuration_id = ?",
                (configuration_id,),
            ).fetchone()
        if row is None:
            raise ScoreNotFoundError("ScoringConfiguration not found.")
        return _row_to_configuration(row)

    def get_latest_configuration(self) -> ScoringConfiguration:
        with self._lock:
            row = self.connection.execute(
                "SELECT * FROM scoring_configurations ORDER BY rowid DESC LIMIT 1"
            ).fetchone()
        if row is None:
            raise ScoreNotFoundError("ScoringConfiguration not found.")
        return _row_to_configuration(row)

    def get_active_configuration(self) -> ScoringConfiguration:
        with self._lock:
            row = self.connection.execute(
                "SELECT * FROM scoring_configurations WHERE is_active = 1"
            ).fetchone()
        if row is None:
            raise ScoreNotFoundError("Active ScoringConfiguration not found.")
        return _row_to_configuration(row)

    def list_configurations(self) -> list[ScoringConfiguration]:
        with self._lock:
            rows = self.connection.execute(
                "SELECT * FROM scoring_configurations ORDER BY created_at, version"
            ).fetchall()
        return [_row_to_configuration(row) for row in rows]


def _row_to_score(row: sqlite3.Row) -> QualityScore:
    return QualityScore(
        quality_score_id=row["quality_score_id"],
        execution_id=row["execution_id"],
        rule_result_id=row["rule_result_id"],
        rule_version_id=row["rule_version_id"],
        scope_type=ScoreScopeType(row["scope_type"]),
        scope_id=row["scope_id"],
        score_value=Decimal(row["score_value"]) if row["score_value"] else None,
        score_status=ScoreStatus(row["score_status"]),
        measurement_status=(
            MeasurementStatus(row["measurement_status"])
            if row["measurement_status"] is not None
            else None
        ),
        level=ScoreLevel(row["level"]) if row["level"] else None,
        calculation_details=json.loads(row["calculation_details"]),
        calculated_at=datetime.fromisoformat(row["calculated_at"]),
    )


def _serialize_dimension_weights(
    weights: dict[QualityDimension, Decimal] | Mapping[QualityDimension, Decimal],
) -> str:
    return json.dumps(
        {dimension.value: str(weight) for dimension, weight in weights.items()},
        sort_keys=True,
    )


def _serialize_criticality_weights(
    weights: Mapping[Criticality, Decimal],
) -> str:
    return json.dumps(
        {criticality.value: str(weight) for criticality, weight in weights.items()},
        sort_keys=True,
    )


def _row_to_configuration(row: sqlite3.Row) -> ScoringConfiguration:
    weights = json.loads(row["dimension_weights"])
    criticality_weights = json.loads(row["criticality_weights"])
    return ScoringConfiguration(
        configuration_id=row["configuration_id"],
        version=row["version"],
        threshold_set=ThresholdSet(
            version=row["threshold_version"],
            critical_upper_exclusive=Decimal(row["critical_upper_exclusive"]),
            risky_upper_exclusive=Decimal(row["risky_upper_exclusive"]),
            acceptable_upper_exclusive=Decimal(row["acceptable_upper_exclusive"]),
        ),
        dimension_weights={
            QualityDimension(dimension): Decimal(weight) for dimension, weight in weights.items()
        },
        criticality_weights={
            Criticality(criticality): Decimal(weight)
            for criticality, weight in criticality_weights.items()
        },
        created_by=row["created_by"],
        created_at=datetime.fromisoformat(row["created_at"]),
        is_active=bool(row["is_active"]),
        activated_at=(datetime.fromisoformat(row["activated_at"]) if row["activated_at"] else None),
    )


def _row_to_configuration_approval(row: sqlite3.Row) -> ScoringConfigurationApproval:
    return ScoringConfigurationApproval(
        approval_id=row["approval_id"],
        configuration_id=row["configuration_id"],
        maker_actor_id=row["maker_actor_id"],
        checker_actor_id=row["checker_actor_id"],
        policy_version=row["policy_version"],
        status=ScoringApprovalStatus(row["status"]),
        decision_reason_code=row["decision_reason_code"],
        requested_at=datetime.fromisoformat(row["requested_at"]),
        decided_at=(
            datetime.fromisoformat(row["decided_at"]) if row["decided_at"] is not None else None
        ),
    )
