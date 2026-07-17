"""SQLite persistence for data quality issues and immutable history."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from threading import RLock

from veri_kalitesi.audit import PreparedAuditEvent, SQLiteTransactionalAudit
from veri_kalitesi.issues.errors import (
    IssueConflictError,
    IssueNotFoundError,
    IssueValidationError,
)
from veri_kalitesi.issues.models import (
    DataQualityIssue,
    IssueHistoryEntry,
    IssuePriority,
    IssueResolutionRecord,
    IssueScopeType,
    IssueSourceEventType,
    IssueStatus,
    IssueTriggerType,
)


class SQLiteIssueRepository:
    def __init__(self, database: str = ":memory:") -> None:
        self.connection = sqlite3.connect(database, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self._lock = RLock()
        self._create_schema()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS data_quality_issues (
                issue_id TEXT PRIMARY KEY,
                issue_no TEXT NOT NULL UNIQUE,
                source_event_id TEXT NOT NULL,
                source_event_type TEXT NOT NULL
                    CHECK (source_event_type IN ('QUALITY', 'TECHNICAL')),
                trigger_type TEXT NOT NULL
                    CHECK (trigger_type IN (
                        'QUALITY_THRESHOLD', 'CRITICAL_RULE_FAILURE', 'TECHNICAL_ERROR'
                    )),
                scope_type TEXT NOT NULL CHECK (scope_type IN ('DATASET', 'SOURCE')),
                scope_id TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN (
                    'NEW', 'ASSIGNED', 'INVESTIGATING', 'WAITING_FOR_RESOLUTION',
                    'RESOLVED', 'VERIFIED', 'CLOSED', 'CANCELLED'
                )),
                priority TEXT NOT NULL CHECK (priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
                assignee_user_id TEXT NOT NULL,
                deduplication_key_digest TEXT NOT NULL UNIQUE,
                payload_digest TEXT NOT NULL,
                occurrence_count INTEGER NOT NULL CHECK (occurrence_count >= 1),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS issue_history (
                sequence_no INTEGER PRIMARY KEY AUTOINCREMENT,
                history_id TEXT NOT NULL UNIQUE,
                issue_id TEXT NOT NULL,
                action TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                old_status TEXT CHECK (old_status IS NULL OR old_status IN (
                    'NEW', 'ASSIGNED', 'INVESTIGATING', 'WAITING_FOR_RESOLUTION',
                    'RESOLVED', 'VERIFIED', 'CLOSED', 'CANCELLED'
                )),
                new_status TEXT NOT NULL CHECK (new_status IN (
                    'NEW', 'ASSIGNED', 'INVESTIGATING', 'WAITING_FOR_RESOLUTION',
                    'RESOLVED', 'VERIFIED', 'CLOSED', 'CANCELLED'
                )),
                old_assignee_user_id TEXT,
                new_assignee_user_id TEXT,
                old_priority TEXT CHECK (old_priority IS NULL OR old_priority IN (
                    'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
                )),
                new_priority TEXT CHECK (new_priority IS NULL OR new_priority IN (
                    'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
                )),
                resolution_id TEXT,
                occurred_at TEXT NOT NULL,
                FOREIGN KEY (issue_id) REFERENCES data_quality_issues(issue_id)
            );

            CREATE TABLE IF NOT EXISTS issue_resolutions (
                sequence_no INTEGER PRIMARY KEY AUTOINCREMENT,
                resolution_id TEXT NOT NULL UNIQUE,
                issue_id TEXT NOT NULL,
                root_cause TEXT NOT NULL CHECK (
                    length(trim(root_cause)) BETWEEN 1 AND 2000
                    AND instr(root_cause, '<') = 0 AND instr(root_cause, '>') = 0
                ),
                corrective_action TEXT NOT NULL CHECK (
                    length(trim(corrective_action)) BETWEEN 1 AND 2000
                    AND instr(corrective_action, '<') = 0
                    AND instr(corrective_action, '>') = 0
                ),
                evidence_reference_id TEXT NOT NULL,
                completed_at TEXT NOT NULL,
                protection_policy_version TEXT NOT NULL,
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (issue_id) REFERENCES data_quality_issues(issue_id)
            );

            CREATE INDEX IF NOT EXISTS idx_issues_assignee_status_time
            ON data_quality_issues(assignee_user_id, status, updated_at DESC);

            CREATE INDEX IF NOT EXISTS idx_issue_history_issue_time
            ON issue_history(issue_id, sequence_no);

            CREATE INDEX IF NOT EXISTS idx_issue_resolutions_issue_time
            ON issue_resolutions(issue_id, sequence_no);
            """
        )
        self._ensure_history_assignment_columns()
        self.connection.commit()

    def _ensure_history_assignment_columns(self) -> None:
        existing = {
            row["name"]
            for row in self.connection.execute("PRAGMA table_info(issue_history)").fetchall()
        }
        additions = {
            "old_assignee_user_id": "TEXT",
            "new_assignee_user_id": "TEXT",
            "old_priority": "TEXT",
            "new_priority": "TEXT",
            "resolution_id": "TEXT",
        }
        for column, column_type in additions.items():
            if column not in existing:
                self.connection.execute(
                    f"ALTER TABLE issue_history ADD COLUMN {column} {column_type}"
                )

    def add_or_increment(
        self,
        issue: DataQualityIssue,
        history: IssueHistoryEntry,
        *,
        payload_digest: str,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> DataQualityIssue:
        self._require_shared_audit_transaction(audit_outbox)
        with self._lock, self.connection:
            existing = self.connection.execute(
                """
                SELECT issue_id, payload_digest, status
                FROM data_quality_issues
                WHERE deduplication_key_digest = ?
                """,
                (issue.deduplication_key_digest,),
            ).fetchone()
            if existing is not None:
                if existing["payload_digest"] != payload_digest:
                    raise IssueConflictError(
                        "Deduplication key was reused with a different issue payload."
                    )
                self.connection.execute(
                    """
                    UPDATE data_quality_issues
                    SET occurrence_count = occurrence_count + 1,
                        last_seen_at = ?, updated_at = ?, source_event_id = ?
                    WHERE issue_id = ?
                    """,
                    (
                        issue.last_seen_at.isoformat(),
                        issue.updated_at.isoformat(),
                        issue.source_event_id,
                        existing["issue_id"],
                    ),
                )
                repeated_history = IssueHistoryEntry(
                    issue_id=existing["issue_id"],
                    action="ISSUE_REPEATED",
                    actor_id=history.actor_id,
                    old_status=IssueStatus(existing["status"]),
                    new_status=IssueStatus(existing["status"]),
                    occurred_at=history.occurred_at,
                )
                self._insert_history(repeated_history)
                issue_id = existing["issue_id"]
            else:
                self.connection.execute(
                    """
                    INSERT INTO data_quality_issues (
                        issue_id, issue_no, source_event_id, source_event_type,
                        trigger_type, scope_type, scope_id, status, priority,
                        assignee_user_id, deduplication_key_digest, payload_digest,
                        occurrence_count, created_at, updated_at, last_seen_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        issue.issue_id,
                        issue.issue_no,
                        issue.source_event_id,
                        issue.source_event_type.value,
                        issue.trigger_type.value,
                        issue.scope_type.value,
                        issue.scope_id,
                        issue.status.value,
                        issue.priority.value,
                        issue.assignee_user_id,
                        issue.deduplication_key_digest,
                        payload_digest,
                        issue.occurrence_count,
                        issue.created_at.isoformat(),
                        issue.updated_at.isoformat(),
                        issue.last_seen_at.isoformat(),
                    ),
                )
                self._insert_history(history)
                issue_id = issue.issue_id
            audit_outbox.stage(audit_event)
        return self.get(issue_id)

    def transition_status(
        self,
        issue_id: str,
        expected_status: IssueStatus,
        target_status: IssueStatus,
        updated_at: datetime,
        history: IssueHistoryEntry,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> DataQualityIssue:
        self._require_shared_audit_transaction(audit_outbox)
        with self._lock, self.connection:
            row = self.connection.execute(
                "SELECT status FROM data_quality_issues WHERE issue_id = ?",
                (issue_id,),
            ).fetchone()
            if row is None:
                raise IssueNotFoundError("Issue not found.")
            if IssueStatus(row["status"]) is not expected_status:
                raise IssueValidationError("Issue status transition is no longer valid.")
            self.connection.execute(
                """
                UPDATE data_quality_issues
                SET status = ?, updated_at = ?
                WHERE issue_id = ?
                """,
                (target_status.value, updated_at.isoformat(), issue_id),
            )
            self._insert_history(history)
            audit_outbox.stage(audit_event)
        return self.get(issue_id)

    def update_assignment(
        self,
        issue_id: str,
        *,
        expected_status: IssueStatus,
        expected_assignee_user_id: str,
        expected_priority: IssuePriority,
        assignee_user_id: str,
        priority: IssuePriority,
        updated_at: datetime,
        history: IssueHistoryEntry,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> DataQualityIssue:
        self._require_shared_audit_transaction(audit_outbox)
        with self._lock, self.connection:
            cursor = self.connection.execute(
                """
                UPDATE data_quality_issues
                SET status = ?, assignee_user_id = ?, priority = ?, updated_at = ?
                WHERE issue_id = ? AND status = ?
                    AND assignee_user_id = ? AND priority = ?
                """,
                (
                    IssueStatus.ASSIGNED.value,
                    assignee_user_id,
                    priority.value,
                    updated_at.isoformat(),
                    issue_id,
                    expected_status.value,
                    expected_assignee_user_id,
                    expected_priority.value,
                ),
            )
            if cursor.rowcount != 1:
                exists = self.connection.execute(
                    "SELECT 1 FROM data_quality_issues WHERE issue_id = ?",
                    (issue_id,),
                ).fetchone()
                if exists is None:
                    raise IssueNotFoundError("Issue not found.")
                raise IssueValidationError("Issue assignment is no longer valid.")
            self._insert_history(history)
            audit_outbox.stage(audit_event)
        return self.get(issue_id)

    def resolve(
        self,
        issue_id: str,
        *,
        expected_status: IssueStatus,
        expected_assignee_user_id: str,
        resolution: IssueResolutionRecord,
        updated_at: datetime,
        history: IssueHistoryEntry,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> DataQualityIssue:
        self._require_shared_audit_transaction(audit_outbox)
        with self._lock, self.connection:
            cursor = self.connection.execute(
                """
                UPDATE data_quality_issues
                SET status = ?, updated_at = ?
                WHERE issue_id = ? AND status = ? AND assignee_user_id = ?
                """,
                (
                    IssueStatus.RESOLVED.value,
                    updated_at.isoformat(),
                    issue_id,
                    expected_status.value,
                    expected_assignee_user_id,
                ),
            )
            if cursor.rowcount != 1:
                exists = self.connection.execute(
                    "SELECT 1 FROM data_quality_issues WHERE issue_id = ?",
                    (issue_id,),
                ).fetchone()
                if exists is None:
                    raise IssueNotFoundError("Issue not found.")
                raise IssueValidationError("Issue resolution is no longer valid.")
            self.connection.execute(
                """
                INSERT INTO issue_resolutions (
                    resolution_id, issue_id, root_cause, corrective_action,
                    evidence_reference_id, completed_at, protection_policy_version,
                    created_by, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    resolution.resolution_id,
                    resolution.issue_id,
                    resolution.root_cause,
                    resolution.corrective_action,
                    resolution.evidence_reference_id,
                    resolution.completed_at.isoformat(),
                    resolution.protection_policy_version,
                    resolution.created_by,
                    resolution.created_at.isoformat(),
                ),
            )
            self._insert_history(history)
            audit_outbox.stage(audit_event)
        return self.get(issue_id)

    def get(self, issue_id: str) -> DataQualityIssue:
        with self._lock:
            row = self.connection.execute(
                "SELECT * FROM data_quality_issues WHERE issue_id = ?",
                (issue_id,),
            ).fetchone()
        if row is None:
            raise IssueNotFoundError("Issue not found.")
        return _row_to_issue(row)

    def list_history(self, issue_id: str) -> tuple[IssueHistoryEntry, ...]:
        with self._lock:
            rows = self.connection.execute(
                """
                SELECT * FROM issue_history
                WHERE issue_id = ?
                ORDER BY sequence_no
                """,
                (issue_id,),
            ).fetchall()
        return tuple(_row_to_history(row) for row in rows)

    def get_history(self, history_id: str) -> IssueHistoryEntry:
        with self._lock:
            row = self.connection.execute(
                "SELECT * FROM issue_history WHERE history_id = ?",
                (history_id,),
            ).fetchone()
        if row is None:
            raise IssueNotFoundError("Issue history not found.")
        return _row_to_history(row)

    def get_latest_resolution(self, issue_id: str) -> IssueResolutionRecord:
        with self._lock:
            row = self.connection.execute(
                """
                SELECT * FROM issue_resolutions
                WHERE issue_id = ?
                ORDER BY sequence_no DESC
                LIMIT 1
                """,
                (issue_id,),
            ).fetchone()
        if row is None:
            raise IssueNotFoundError("Issue resolution not found.")
        return _row_to_resolution(row)

    def count(self) -> int:
        with self._lock:
            return self.connection.execute("SELECT COUNT(*) FROM data_quality_issues").fetchone()[0]

    def _insert_history(self, history: IssueHistoryEntry) -> None:
        self.connection.execute(
            """
            INSERT INTO issue_history (
                history_id, issue_id, action, actor_id,
                old_status, new_status, old_assignee_user_id,
                new_assignee_user_id, old_priority, new_priority,
                occurred_at, resolution_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                history.history_id,
                history.issue_id,
                history.action,
                history.actor_id,
                history.old_status.value if history.old_status else None,
                history.new_status.value,
                history.old_assignee_user_id,
                history.new_assignee_user_id,
                history.old_priority.value if history.old_priority else None,
                history.new_priority.value if history.new_priority else None,
                history.occurred_at.isoformat(),
                history.resolution_id,
            ),
        )

    def _require_shared_audit_transaction(self, audit_outbox: SQLiteTransactionalAudit) -> None:
        if audit_outbox.connection is not self.connection:
            raise IssueValidationError("Audit outbox must share the issue transaction.")


def _row_to_issue(row: sqlite3.Row) -> DataQualityIssue:
    return DataQualityIssue(
        issue_id=row["issue_id"],
        issue_no=row["issue_no"],
        source_event_id=row["source_event_id"],
        source_event_type=IssueSourceEventType(row["source_event_type"]),
        trigger_type=IssueTriggerType(row["trigger_type"]),
        scope_type=IssueScopeType(row["scope_type"]),
        scope_id=row["scope_id"],
        status=IssueStatus(row["status"]),
        priority=IssuePriority(row["priority"]),
        assignee_user_id=row["assignee_user_id"],
        deduplication_key_digest=row["deduplication_key_digest"],
        occurrence_count=row["occurrence_count"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        last_seen_at=datetime.fromisoformat(row["last_seen_at"]),
    )


def _row_to_history(row: sqlite3.Row) -> IssueHistoryEntry:
    return IssueHistoryEntry(
        history_id=row["history_id"],
        issue_id=row["issue_id"],
        action=row["action"],
        actor_id=row["actor_id"],
        old_status=IssueStatus(row["old_status"]) if row["old_status"] else None,
        new_status=IssueStatus(row["new_status"]),
        occurred_at=datetime.fromisoformat(row["occurred_at"]),
        old_assignee_user_id=row["old_assignee_user_id"],
        new_assignee_user_id=row["new_assignee_user_id"],
        old_priority=IssuePriority(row["old_priority"]) if row["old_priority"] else None,
        new_priority=IssuePriority(row["new_priority"]) if row["new_priority"] else None,
        resolution_id=row["resolution_id"],
    )


def _row_to_resolution(row: sqlite3.Row) -> IssueResolutionRecord:
    return IssueResolutionRecord(
        resolution_id=row["resolution_id"],
        issue_id=row["issue_id"],
        root_cause=row["root_cause"],
        corrective_action=row["corrective_action"],
        evidence_reference_id=row["evidence_reference_id"],
        completed_at=datetime.fromisoformat(row["completed_at"]),
        protection_policy_version=row["protection_policy_version"],
        created_by=row["created_by"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )
