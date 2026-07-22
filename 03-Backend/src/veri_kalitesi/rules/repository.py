"""SQLite tabanlı kural ve test geçmişi deposu."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from veri_kalitesi.audit import PreparedAuditEvent, SQLiteTransactionalAudit
from veri_kalitesi.rules.errors import RuleNotFoundError, RuleValidationError
from veri_kalitesi.rules.models import (
    QualityDimension,
    QualityRule,
    RuleApprovalRequest,
    RuleApprovalStatus,
    RuleCriticality,
    RuleStatus,
    RuleTestResult,
    RuleTestStatus,
    RuleType,
    RuleVersion,
    thaw,
)


class SQLiteRuleRepository:
    def __init__(self, database: str = ":memory:") -> None:
        self.connection = sqlite3.connect(database)
        self.connection.row_factory = sqlite3.Row
        self._create_schema()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS quality_rules (
                quality_rule_id TEXT PRIMARY KEY,
                code TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                dataset_id TEXT NOT NULL,
                field_ids TEXT NOT NULL,
                primary_dimension TEXT NOT NULL,
                owner_user_id TEXT NOT NULL,
                status TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS rule_versions (
                rule_version_id TEXT PRIMARY KEY,
                quality_rule_id TEXT NOT NULL,
                version_no INTEGER NOT NULL,
                rule_type TEXT NOT NULL,
                definition TEXT NOT NULL,
                threshold REAL NOT NULL,
                weight REAL NOT NULL,
                criticality TEXT NOT NULL,
                prepared_by_actor_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE (quality_rule_id, version_no),
                FOREIGN KEY (quality_rule_id) REFERENCES quality_rules(quality_rule_id)
            );

            CREATE TABLE IF NOT EXISTS rule_test_results (
                rule_test_result_id TEXT PRIMARY KEY,
                rule_version_id TEXT NOT NULL,
                status TEXT NOT NULL,
                record_limit INTEGER NOT NULL,
                checked_count INTEGER NOT NULL,
                passed_count INTEGER NOT NULL,
                failed_count INTEGER NOT NULL,
                not_evaluated_count INTEGER NOT NULL,
                success_rate REAL,
                preview_score REAL,
                official_score_included INTEGER NOT NULL,
                error_class TEXT,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (rule_version_id) REFERENCES rule_versions(rule_version_id)
            );

            CREATE TABLE IF NOT EXISTS rule_approval_requests (
                approval_request_id TEXT PRIMARY KEY,
                rule_version_id TEXT NOT NULL,
                maker_actor_id TEXT NOT NULL,
                checker_actor_id TEXT,
                policy_version TEXT NOT NULL,
                status TEXT NOT NULL,
                decision_reason_code TEXT,
                requested_at TEXT NOT NULL,
                target_at TEXT,
                expires_at TEXT,
                business_calendar_version TEXT,
                decided_at TEXT,
                FOREIGN KEY (rule_version_id) REFERENCES rule_versions(rule_version_id)
            );
            """
        )
        self._migrate_rule_versions()
        self._migrate_rule_approval_requests()

    def _migrate_rule_versions(self) -> None:
        columns = {
            row["name"]
            for row in self.connection.execute("PRAGMA table_info(rule_versions)").fetchall()
        }
        if "prepared_by_actor_id" not in columns:
            with self.connection:
                self.connection.execute(
                    """
                    ALTER TABLE rule_versions
                    ADD COLUMN prepared_by_actor_id TEXT NOT NULL DEFAULT 'LEGACY_UNKNOWN'
                    """
                )

    def _migrate_rule_approval_requests(self) -> None:
        table_sql = self.connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
            ("rule_approval_requests",),
        ).fetchone()["sql"]
        if "rule_version_id TEXT NOT NULL UNIQUE" in table_sql:
            with self.connection:
                self.connection.executescript(
                    """
                    ALTER TABLE rule_approval_requests RENAME TO rule_approval_requests_legacy;
                    CREATE TABLE rule_approval_requests (
                        approval_request_id TEXT PRIMARY KEY,
                        rule_version_id TEXT NOT NULL,
                        maker_actor_id TEXT NOT NULL,
                        checker_actor_id TEXT,
                        policy_version TEXT NOT NULL,
                        status TEXT NOT NULL,
                        decision_reason_code TEXT,
                        requested_at TEXT NOT NULL,
                        target_at TEXT,
                        expires_at TEXT,
                        business_calendar_version TEXT,
                        decided_at TEXT,
                        FOREIGN KEY (rule_version_id) REFERENCES rule_versions(rule_version_id)
                    );
                    INSERT INTO rule_approval_requests (
                        approval_request_id, rule_version_id, maker_actor_id,
                        checker_actor_id, policy_version, status,
                        decision_reason_code, requested_at, decided_at
                    )
                    SELECT approval_request_id, rule_version_id, maker_actor_id,
                           checker_actor_id, policy_version, status,
                           decision_reason_code, requested_at, decided_at
                    FROM rule_approval_requests_legacy;
                    DROP TABLE rule_approval_requests_legacy;
                    """
                )
        columns = {
            row["name"]
            for row in self.connection.execute(
                "PRAGMA table_info(rule_approval_requests)"
            ).fetchall()
        }
        additions = {
            "target_at": "TEXT",
            "expires_at": "TEXT",
            "business_calendar_version": "TEXT",
        }
        with self.connection:
            for column, column_type in additions.items():
                if column not in columns:
                    self.connection.execute(
                        f"ALTER TABLE rule_approval_requests ADD COLUMN {column} {column_type}"
                    )
            self.connection.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS ux_rule_approval_pending_version
                ON rule_approval_requests (rule_version_id)
                WHERE status = 'PENDING'
                """
            )

    def add_rule_with_version(
        self,
        rule: QualityRule,
        version: RuleVersion,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> None:
        if audit_outbox.connection is not self.connection:
            raise RuleValidationError("Audit outbox must share the rule transaction.")
        try:
            with self.connection:
                self.connection.execute(
                    """
                    INSERT INTO quality_rules (
                        quality_rule_id, code, name, dataset_id, field_ids,
                        primary_dimension, owner_user_id, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        rule.quality_rule_id,
                        rule.code,
                        rule.name,
                        rule.dataset_id,
                        json.dumps(rule.field_ids),
                        rule.primary_dimension.value,
                        rule.owner_user_id,
                        rule.status.value,
                    ),
                )
                self._insert_version(version)
                audit_outbox.stage(audit_event)
        except sqlite3.IntegrityError as exc:
            raise RuleValidationError("Rule code and version number must be unique.") from exc

    def add_version(
        self,
        version: RuleVersion,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> None:
        self._require_shared_audit_transaction(audit_outbox)
        try:
            with self.connection:
                self._insert_version(version)
                audit_outbox.stage(audit_event)
        except sqlite3.IntegrityError as exc:
            raise RuleValidationError("Rule version number must be unique.") from exc

    def get_rule(self, quality_rule_id: str) -> QualityRule:
        row = self.connection.execute(
            "SELECT * FROM quality_rules WHERE quality_rule_id = ?", (quality_rule_id,)
        ).fetchone()
        if row is None:
            raise RuleNotFoundError("QualityRule not found.")
        return _row_to_rule(row)

    def get_version(self, rule_version_id: str) -> RuleVersion:
        row = self.connection.execute(
            "SELECT * FROM rule_versions WHERE rule_version_id = ?", (rule_version_id,)
        ).fetchone()
        if row is None:
            raise RuleNotFoundError("RuleVersion not found.")
        return _row_to_version(row)

    def list_versions(self, quality_rule_id: str) -> list[RuleVersion]:
        rows = self.connection.execute(
            """
            SELECT * FROM rule_versions
            WHERE quality_rule_id = ?
            ORDER BY version_no
            """,
            (quality_rule_id,),
        ).fetchall()
        return [_row_to_version(row) for row in rows]

    def list_rules_with_latest_version(
        self, allowed_dataset_ids: frozenset[str]
    ) -> list[tuple[QualityRule, RuleVersion]]:
        """Yetkili datasetlerdeki kuralları son değişmez sürümüyle listeler."""

        if not allowed_dataset_ids:
            return []
        dataset_ids = sorted(allowed_dataset_ids)
        placeholders = ", ".join("?" for _ in dataset_ids)
        rows = self.connection.execute(
            f"""
            SELECT
                rules.*,
                versions.rule_version_id AS latest_rule_version_id,
                versions.version_no AS latest_version_no,
                versions.rule_type AS latest_rule_type,
                versions.definition AS latest_definition,
                versions.threshold AS latest_threshold,
                versions.weight AS latest_weight,
                versions.criticality AS latest_criticality,
                versions.prepared_by_actor_id AS latest_prepared_by_actor_id,
                versions.created_at AS latest_created_at
            FROM quality_rules rules
            JOIN rule_versions versions
              ON versions.quality_rule_id = rules.quality_rule_id
             AND versions.version_no = (
                SELECT MAX(candidate.version_no)
                FROM rule_versions candidate
                WHERE candidate.quality_rule_id = rules.quality_rule_id
             )
            WHERE rules.dataset_id IN ({placeholders})
            ORDER BY rules.code COLLATE NOCASE, rules.quality_rule_id
            """,
            dataset_ids,
        ).fetchall()
        return [(_row_to_rule(row), _row_to_latest_version(row)) for row in rows]

    def update_rule_status(
        self,
        quality_rule_id: str,
        status: RuleStatus,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> QualityRule:
        self._require_shared_audit_transaction(audit_outbox)
        with self.connection:
            cursor = self.connection.execute(
                "UPDATE quality_rules SET status = ? WHERE quality_rule_id = ?",
                (status.value, quality_rule_id),
            )
            if cursor.rowcount != 1:
                raise RuleNotFoundError("QualityRule not found.")
            audit_outbox.stage(audit_event)
        return self.get_rule(quality_rule_id)

    def add_test_result(
        self,
        result: RuleTestResult,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> None:
        self._require_shared_audit_transaction(audit_outbox)
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO rule_test_results (
                    rule_test_result_id, rule_version_id, status, record_limit,
                    checked_count, passed_count, failed_count, not_evaluated_count,
                    success_rate, preview_score, official_score_included, error_class,
                    message, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.rule_test_result_id,
                    result.rule_version_id,
                    result.status.value,
                    result.record_limit,
                    result.checked_count,
                    result.passed_count,
                    result.failed_count,
                    result.not_evaluated_count,
                    result.success_rate,
                    result.preview_score,
                    1 if result.official_score_included else 0,
                    result.error_class,
                    result.message,
                    result.created_at.isoformat(),
                ),
            )
            audit_outbox.stage(audit_event)

    def list_test_results(self, rule_version_id: str) -> list[RuleTestResult]:
        rows = self.connection.execute(
            """
            SELECT * FROM rule_test_results
            WHERE rule_version_id = ?
            ORDER BY created_at, rule_test_result_id
            """,
            (rule_version_id,),
        ).fetchall()
        return [_row_to_test_result(row) for row in rows]

    def latest_test_result(self, rule_version_id: str) -> RuleTestResult | None:
        row = self.connection.execute(
            """
            SELECT * FROM rule_test_results
            WHERE rule_version_id = ?
            ORDER BY created_at DESC, rule_test_result_id DESC
            LIMIT 1
            """,
            (rule_version_id,),
        ).fetchone()
        return _row_to_test_result(row) if row is not None else None

    def add_approval_request(
        self,
        request: RuleApprovalRequest,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> RuleApprovalRequest:
        self._require_shared_audit_transaction(audit_outbox)
        try:
            with self.connection:
                self.connection.execute(
                    """
                    INSERT INTO rule_approval_requests (
                        approval_request_id, rule_version_id, maker_actor_id,
                        checker_actor_id, policy_version, status,
                        decision_reason_code, requested_at, target_at, expires_at,
                        business_calendar_version, decided_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        request.approval_request_id,
                        request.rule_version_id,
                        request.maker_actor_id,
                        request.checker_actor_id,
                        request.policy_version,
                        request.status.value,
                        request.decision_reason_code,
                        request.requested_at.isoformat(),
                        request.target_at.isoformat() if request.target_at else None,
                        request.expires_at.isoformat() if request.expires_at else None,
                        request.business_calendar_version,
                        request.decided_at.isoformat() if request.decided_at else None,
                    ),
                )
                audit_outbox.stage(audit_event)
        except sqlite3.IntegrityError as exc:
            raise RuleValidationError("RuleVersion already has an approval request.") from exc
        return request

    def get_approval_request(self, approval_request_id: str) -> RuleApprovalRequest:
        row = self.connection.execute(
            "SELECT * FROM rule_approval_requests WHERE approval_request_id = ?",
            (approval_request_id,),
        ).fetchone()
        if row is None:
            raise RuleNotFoundError("RuleApprovalRequest not found.")
        return _row_to_approval_request(row)

    def list_due_approval_requests(self, as_of: datetime) -> list[RuleApprovalRequest]:
        rows = self.connection.execute(
            """
            SELECT * FROM rule_approval_requests
            WHERE status = ? AND expires_at IS NOT NULL AND expires_at <= ?
            ORDER BY expires_at, approval_request_id
            """,
            (RuleApprovalStatus.PENDING.value, as_of.isoformat()),
        ).fetchall()
        return [_row_to_approval_request(row) for row in rows]

    def decide_approval_request(
        self,
        request: RuleApprovalRequest,
        *,
        quality_rule_id: str,
        activate_rule: bool,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> RuleApprovalRequest:
        self._require_shared_audit_transaction(audit_outbox)
        with self.connection:
            cursor = self.connection.execute(
                """
                UPDATE rule_approval_requests
                SET status = ?, checker_actor_id = ?, decision_reason_code = ?, decided_at = ?
                WHERE approval_request_id = ? AND status = ?
                """,
                (
                    request.status.value,
                    request.checker_actor_id,
                    request.decision_reason_code,
                    request.decided_at.isoformat() if request.decided_at else None,
                    request.approval_request_id,
                    RuleApprovalStatus.PENDING.value,
                ),
            )
            if cursor.rowcount != 1:
                raise RuleValidationError("Rule approval request is not pending.")
            if activate_rule:
                cursor = self.connection.execute(
                    """
                    UPDATE quality_rules SET status = ?
                    WHERE quality_rule_id = ? AND status = ?
                    """,
                    (RuleStatus.ACTIVE.value, quality_rule_id, RuleStatus.DRAFT.value),
                )
                if cursor.rowcount != 1:
                    raise RuleValidationError("Only a draft rule can be activated.")
            audit_outbox.stage(audit_event)
        return self.get_approval_request(request.approval_request_id)

    def withdraw_approval_request(
        self,
        request: RuleApprovalRequest,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> RuleApprovalRequest:
        self._require_shared_audit_transaction(audit_outbox)
        if request.status is not RuleApprovalStatus.WITHDRAWN:
            raise RuleValidationError("Rule approval withdrawal status is invalid.")
        with self.connection:
            cursor = self.connection.execute(
                """
                UPDATE rule_approval_requests
                SET status = ?, checker_actor_id = NULL,
                    decision_reason_code = ?, decided_at = ?
                WHERE approval_request_id = ? AND status = ?
                """,
                (
                    request.status.value,
                    request.decision_reason_code,
                    request.decided_at.isoformat() if request.decided_at else None,
                    request.approval_request_id,
                    RuleApprovalStatus.PENDING.value,
                ),
            )
            if cursor.rowcount != 1:
                raise RuleValidationError("Rule approval request is not pending.")
            audit_outbox.stage(audit_event)
        return self.get_approval_request(request.approval_request_id)

    def expire_approval_request(
        self,
        request: RuleApprovalRequest,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> RuleApprovalRequest:
        self._require_shared_audit_transaction(audit_outbox)
        if request.status is not RuleApprovalStatus.EXPIRED:
            raise RuleValidationError("Rule approval expiry status is invalid.")
        with self.connection:
            cursor = self.connection.execute(
                """
                UPDATE rule_approval_requests
                SET status = ?, checker_actor_id = NULL,
                    decision_reason_code = ?, decided_at = ?
                WHERE approval_request_id = ? AND status = ?
                """,
                (
                    request.status.value,
                    request.decision_reason_code,
                    request.decided_at.isoformat() if request.decided_at else None,
                    request.approval_request_id,
                    RuleApprovalStatus.PENDING.value,
                ),
            )
            if cursor.rowcount != 1:
                raise RuleValidationError("Rule approval request is not pending.")
            audit_outbox.stage(audit_event)
        return self.get_approval_request(request.approval_request_id)

    def _insert_version(self, version: RuleVersion) -> None:
        self.connection.execute(
            """
            INSERT INTO rule_versions (
                rule_version_id, quality_rule_id, version_no, rule_type, definition,
                threshold, weight, criticality, prepared_by_actor_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                version.rule_version_id,
                version.quality_rule_id,
                version.version_no,
                version.rule_type.value,
                json.dumps(thaw(version.definition), sort_keys=True),
                version.threshold,
                version.weight,
                version.criticality.value,
                version.prepared_by_actor_id,
                version.created_at.isoformat(),
            ),
        )

    def _require_shared_audit_transaction(self, audit_outbox: SQLiteTransactionalAudit) -> None:
        if audit_outbox.connection is not self.connection:
            raise RuleValidationError("Audit outbox must share the rule transaction.")


def _row_to_rule(row: sqlite3.Row) -> QualityRule:
    return QualityRule(
        quality_rule_id=row["quality_rule_id"],
        code=row["code"],
        name=row["name"],
        dataset_id=row["dataset_id"],
        field_ids=tuple(json.loads(row["field_ids"])),
        primary_dimension=QualityDimension(row["primary_dimension"]),
        owner_user_id=row["owner_user_id"],
        status=RuleStatus(row["status"]),
    )


def _row_to_version(row: sqlite3.Row) -> RuleVersion:
    return RuleVersion(
        rule_version_id=row["rule_version_id"],
        quality_rule_id=row["quality_rule_id"],
        version_no=row["version_no"],
        rule_type=RuleType(row["rule_type"]),
        definition=json.loads(row["definition"]),
        threshold=row["threshold"],
        weight=row["weight"],
        criticality=RuleCriticality(row["criticality"]),
        prepared_by_actor_id=row["prepared_by_actor_id"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def _row_to_latest_version(row: sqlite3.Row) -> RuleVersion:
    return RuleVersion(
        rule_version_id=row["latest_rule_version_id"],
        quality_rule_id=row["quality_rule_id"],
        version_no=row["latest_version_no"],
        rule_type=RuleType(row["latest_rule_type"]),
        definition=json.loads(row["latest_definition"]),
        threshold=row["latest_threshold"],
        weight=row["latest_weight"],
        criticality=RuleCriticality(row["latest_criticality"]),
        prepared_by_actor_id=row["latest_prepared_by_actor_id"],
        created_at=datetime.fromisoformat(row["latest_created_at"]),
    )


def _row_to_test_result(row: sqlite3.Row) -> RuleTestResult:
    return RuleTestResult(
        rule_test_result_id=row["rule_test_result_id"],
        rule_version_id=row["rule_version_id"],
        status=RuleTestStatus(row["status"]),
        record_limit=row["record_limit"],
        checked_count=row["checked_count"],
        passed_count=row["passed_count"],
        failed_count=row["failed_count"],
        not_evaluated_count=row["not_evaluated_count"],
        success_rate=row["success_rate"],
        preview_score=row["preview_score"],
        official_score_included=bool(row["official_score_included"]),
        error_class=row["error_class"],
        message=row["message"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def _row_to_approval_request(row: sqlite3.Row) -> RuleApprovalRequest:
    return RuleApprovalRequest(
        approval_request_id=row["approval_request_id"],
        rule_version_id=row["rule_version_id"],
        maker_actor_id=row["maker_actor_id"],
        checker_actor_id=row["checker_actor_id"],
        policy_version=row["policy_version"],
        status=RuleApprovalStatus(row["status"]),
        decision_reason_code=row["decision_reason_code"],
        requested_at=datetime.fromisoformat(row["requested_at"]),
        target_at=(datetime.fromisoformat(row["target_at"]) if row["target_at"] else None),
        expires_at=(datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None),
        business_calendar_version=row["business_calendar_version"],
        decided_at=(
            datetime.fromisoformat(row["decided_at"]) if row["decided_at"] is not None else None
        ),
    )
