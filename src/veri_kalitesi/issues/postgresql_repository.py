"""PostgreSQL-only issue persistence and immutable history."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    and_,
    func,
    insert,
    or_,
    select,
    update,
)
from sqlalchemy.engine import RowMapping
from sqlalchemy.orm import Session

from veri_kalitesi.audit.models import PreparedAuditEvent
from veri_kalitesi.audit.postgresql_outbox import PostgreSQLTransactionalAudit
from veri_kalitesi.issues.errors import (
    IssueConflictError,
    IssueNotFoundError,
    IssueRelationshipError,
    IssueValidationError,
)
from veri_kalitesi.issues.evidence import IssueEvidenceKind, IssueEvidenceRecord
from veri_kalitesi.issues.evidence_files import (
    EvidenceClassification,
    EvidenceScanStatus,
    IssueEvidenceFileRecord,
)
from veri_kalitesi.issues.models import (
    DataQualityIssue,
    IssueHistoryEntry,
    IssuePriority,
    IssueRelationship,
    IssueRelationshipType,
    IssueResolutionRecord,
    IssueScopeType,
    IssueSourceEventType,
    IssueStatus,
    IssueTriggerType,
    IssueVerificationOutcome,
    IssueVerificationRecord,
)
from veri_kalitesi.persistence import (
    DEFAULT_SCHEMA_NAME,
    SessionFactory,
    transactional_session,
)


@dataclass(frozen=True)
class IssueTables:
    issues: Table
    history: Table
    resolutions: Table
    verifications: Table
    relationships: Table
    evidence: Table
    evidence_files: Table


def issue_tables(schema: str = DEFAULT_SCHEMA_NAME) -> IssueTables:
    metadata = MetaData(schema=schema)
    issues = Table(
        "data_quality_issues",
        metadata,
        Column("issue_id", String(36), primary_key=True),
        Column("issue_no", String(40), nullable=False, unique=True),
        Column("source_event_id", String(36), nullable=False),
        Column("source_event_type", String(40), nullable=False),
        Column("trigger_type", String(40), nullable=False),
        Column("scope_type", String(20), nullable=False),
        Column("scope_id", String(36), nullable=False),
        Column("status", String(30), nullable=False),
        Column("priority", String(20), nullable=False),
        Column("assignee_user_id", String(36), nullable=False),
        Column("deduplication_key_digest", String(128), nullable=False, unique=True),
        Column("payload_digest", String(128), nullable=False),
        Column("occurrence_count", Integer, nullable=False),
        Column("version", BigInteger, nullable=False, server_default="1"),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("updated_at", DateTime(timezone=True), nullable=False),
        Column("last_seen_at", DateTime(timezone=True), nullable=False),
        Column("title", String(200), nullable=False, server_default=""),
        Column("source_execution_id", String(36)),
        Column("source_rule_version_id", String(36)),
        CheckConstraint(
            "source_event_type IN ('QUALITY', 'TECHNICAL', 'MANUAL')",
            name="ck_issue_source_event_type",
        ),
        CheckConstraint(
            "trigger_type IN ('QUALITY_THRESHOLD', 'CRITICAL_RULE_FAILURE',"
            " 'TECHNICAL_ERROR', 'MANUAL')",
            name="ck_issue_trigger_type",
        ),
        CheckConstraint("scope_type IN ('DATASET', 'SOURCE')", name="ck_issue_scope_type"),
        CheckConstraint(
            "status IN ('NEW', 'ASSIGNED', 'INVESTIGATING', "
            "'WAITING_FOR_RESOLUTION', 'RESOLVED', 'VERIFIED', 'CLOSED', 'CANCELLED')",
            name="ck_issue_status",
        ),
        CheckConstraint(
            "priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="ck_issue_priority",
        ),
        CheckConstraint("occurrence_count >= 1", name="ck_issue_occurrence_count"),
    )
    history = Table(
        "issue_history",
        metadata,
        Column("sequence_no", BigInteger, Identity(), primary_key=True),
        Column("history_id", String(36), nullable=False, unique=True),
        Column(
            "issue_id",
            String(36),
            ForeignKey(f"{schema}.data_quality_issues.issue_id"),
            nullable=False,
        ),
        Column("action", String(120), nullable=False),
        Column("actor_id", String(128), nullable=False),
        Column("old_status", String(30)),
        Column("new_status", String(30), nullable=False),
        Column("old_assignee_user_id", String(36)),
        Column("new_assignee_user_id", String(36)),
        Column("old_priority", String(20)),
        Column("new_priority", String(20)),
        Column("resolution_id", String(36)),
        Column("verification_id", String(36)),
        Column("occurred_at", DateTime(timezone=True), nullable=False),
        Column("source_event_id", String(36)),
        Column("source_event_occurred_at", DateTime(timezone=True)),
        Column("source_event_payload_digest", String(64)),
        CheckConstraint(
            "(source_event_id IS NULL AND source_event_occurred_at IS NULL"
            " AND source_event_payload_digest IS NULL) OR"
            " (source_event_id IS NOT NULL AND source_event_occurred_at IS NOT NULL"
            " AND source_event_payload_digest IS NOT NULL)",
            name="ck_issue_history_receipt_consistency",
        ),
    )
    evidence = Table(
        "issue_evidence",
        metadata,
        Column("sequence_no", BigInteger, Identity(), primary_key=True),
        Column("evidence_id", String(36), nullable=False, unique=True),
        Column(
            "issue_id",
            String(36),
            ForeignKey(f"{schema}.data_quality_issues.issue_id"),
            nullable=False,
        ),
        Column("kind", String(30), nullable=False),
        Column("label", String(200), nullable=False),
        Column("execution_id", String(64), nullable=False),
        Column("rule_version_id", String(36)),
        Column("evaluated_count", Integer),
        Column("failed_count", Integer),
        Column("measurement_status", String(40)),
        Column("fingerprint", String(128)),
        Column("query_reference", String(200)),
        Column("plan_reference", String(200)),
        Column("content_digest", String(64), nullable=False),
        Column("source_digest", String(64), nullable=False),
        Column("observed_at", DateTime(timezone=True), nullable=False),
        Column("captured_at", DateTime(timezone=True), nullable=False),
        Column("captured_by", String(128), nullable=False),
        CheckConstraint(
            "kind IN ('EXECUTION_RESULT', 'EXECUTION_LOG', 'LEGACY_REFERENCE', 'UPLOADED_FILE')",
            name="ck_issue_evidence_kind",
        ),
        UniqueConstraint("issue_id", "source_digest", name="uq_issue_evidence_source"),
    )
    evidence_files = Table(
        "issue_evidence_files",
        metadata,
        Column("file_id", String(36), primary_key=True),
        Column(
            "evidence_id",
            String(36),
            ForeignKey(f"{schema}.issue_evidence.evidence_id"),
            nullable=False,
        ),
        Column("original_filename", String(255), nullable=False),
        Column("safe_filename", String(255), nullable=False),
        Column("declared_media_type", String(120)),
        Column("detected_media_type", String(120), nullable=False),
        Column("byte_size", BigInteger, nullable=False),
        Column("object_key", String(500), nullable=False, unique=True),
        Column("sha256_digest", String(64), nullable=False),
        Column("scan_status", String(30), nullable=False),
        Column("scan_reason_code", String(100)),
        Column("scan_completed_at", DateTime(timezone=True)),
        Column("classification", String(40), nullable=False),
        Column("uploaded_by", String(128), nullable=False),
        Column("uploaded_at", DateTime(timezone=True), nullable=False),
        Column("retention_until", DateTime(timezone=True)),
        Column("legal_hold", Boolean, nullable=False, server_default="false"),
        Column("deleted_at", DateTime(timezone=True)),
        Column("deleted_by", String(128)),
        Column("idempotency_digest", String(64), nullable=False),
        CheckConstraint("byte_size > 0", name="ck_issue_evidence_file_size"),
        CheckConstraint("sha256_digest ~ '^[0-9a-f]{64}$'", name="ck_issue_evidence_file_sha256"),
        CheckConstraint(
            "scan_status IN ('UPLOADING','PENDING_SCAN','AVAILABLE','REJECTED','SCAN_FAILED')",
            name="ck_issue_evidence_file_scan_status",
        ),
        CheckConstraint(
            "scan_status <> 'AVAILABLE' OR scan_completed_at IS NOT NULL",
            name="ck_issue_evidence_file_available_at",
        ),
        UniqueConstraint("evidence_id", name="uq_issue_evidence_file_evidence"),
    )
    resolutions = Table(
        "issue_resolutions",
        metadata,
        Column("sequence_no", BigInteger, Identity(), primary_key=True),
        Column("resolution_id", String(36), nullable=False, unique=True),
        Column(
            "issue_id",
            String(36),
            ForeignKey(f"{schema}.data_quality_issues.issue_id"),
            nullable=False,
        ),
        Column("root_cause", Text, nullable=False),
        Column("corrective_action", Text, nullable=False),
        Column(
            "evidence_reference_id",
            String(36),
            ForeignKey(f"{schema}.issue_evidence.evidence_id"),
            nullable=False,
        ),
        Column("completed_at", DateTime(timezone=True), nullable=False),
        Column("protection_policy_version", String(80), nullable=False),
        Column("created_by", String(128), nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
    )
    verifications = Table(
        "issue_verifications",
        metadata,
        Column("sequence_no", BigInteger, Identity(), primary_key=True),
        Column("verification_id", String(36), nullable=False, unique=True),
        Column(
            "issue_id",
            String(36),
            ForeignKey(f"{schema}.data_quality_issues.issue_id"),
            nullable=False,
        ),
        Column("verification_reference_id", String(36), nullable=False, unique=True),
        Column("execution_id", String(36), nullable=False),
        Column("score_id", String(36)),
        Column("scope_type", String(20), nullable=False),
        Column("scope_id", String(36), nullable=False),
        Column("outcome", String(30), nullable=False),
        Column("completed_at", DateTime(timezone=True), nullable=False),
        Column("recorded_by", String(128), nullable=False),
        Column("recorded_at", DateTime(timezone=True), nullable=False),
    )
    relationships = Table(
        "issue_relationships",
        metadata,
        Column("sequence_no", BigInteger, Identity(), primary_key=True),
        Column("relationship_id", String(36), nullable=False, unique=True),
        Column(
            "predecessor_issue_id",
            String(36),
            ForeignKey(f"{schema}.data_quality_issues.issue_id"),
            nullable=False,
        ),
        Column(
            "successor_issue_id",
            String(36),
            ForeignKey(f"{schema}.data_quality_issues.issue_id"),
            nullable=False,
        ),
        Column("relationship_type", String(30), nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
        UniqueConstraint(
            "predecessor_issue_id",
            "successor_issue_id",
            "relationship_type",
            name="uq_issue_relationship",
        ),
    )
    Index(
        "ix_dq_issues_scope_updated",
        issues.c.scope_type,
        issues.c.scope_id,
        issues.c.updated_at.desc(),
        issues.c.issue_id.desc(),
    )
    Index(
        "ix_dq_issues_assignee_status_updated",
        issues.c.assignee_user_id,
        issues.c.status,
        issues.c.updated_at.desc(),
    )
    Index(
        "ix_dq_issues_source_execution",
        issues.c.source_execution_id,
    )
    Index(
        "ix_dq_issues_source_rule_version",
        issues.c.source_rule_version_id,
    )
    Index(
        "uq_issue_history_source_event_id",
        history.c.source_event_id,
        unique=True,
        postgresql_where=history.c.source_event_id.isnot(None),
    )
    Index(
        "ix_issue_evidence_issue",
        evidence.c.issue_id,
        evidence.c.captured_at.desc(),
    )
    return IssueTables(
        issues, history, resolutions, verifications, relationships, evidence, evidence_files
    )


def issue_table(schema: str = DEFAULT_SCHEMA_NAME) -> Table:
    return issue_tables(schema).issues


class PostgreSQLIssueRepository:
    """Issue yaşam döngüsünü PostgreSQL ve atomik audit outbox ile saklar."""

    def __init__(
        self,
        session_factory: SessionFactory,
        *,
        schema: str = DEFAULT_SCHEMA_NAME,
    ) -> None:
        self._session_factory = session_factory
        self._schema = schema
        self._tables = issue_tables(schema)
        self._table = self._tables.issues

    def add_or_increment(
        self,
        issue: DataQualityIssue,
        history: IssueHistoryEntry,
        *,
        payload_digest: str,
        source_event_occurred_at: datetime,
        relationship: IssueRelationship | None,
        relationship_history: IssueHistoryEntry | None,
        audit_event: PreparedAuditEvent,
        reopen_audit_event: PreparedAuditEvent,
        relationship_audit_event: PreparedAuditEvent | None,
        audit_outbox: PostgreSQLTransactionalAudit,
        notification_batch: object = None,
    ) -> DataQualityIssue:
        self._require_postgresql_audit(audit_outbox)
        with transactional_session(self._session_factory) as session:
            session.execute(
                select(
                    func.pg_advisory_xact_lock(
                        func.hashtext("dq_issue"),
                        func.hashtext(issue.deduplication_key_digest),
                    )
                )
            )
            existing = (
                session.execute(
                    select(
                        self._table.c.issue_id,
                        self._table.c.payload_digest,
                        self._table.c.status,
                        self._table.c.updated_at,
                    )
                    .where(self._table.c.deduplication_key_digest == issue.deduplication_key_digest)
                    .with_for_update()
                )
                .mappings()
                .one_or_none()
            )
            if existing is None:
                session.execute(
                    insert(self._table).values(
                        issue_id=issue.issue_id,
                        issue_no=issue.issue_no,
                        source_event_id=issue.source_event_id,
                        source_event_type=issue.source_event_type.value,
                        trigger_type=issue.trigger_type.value,
                        scope_type=issue.scope_type.value,
                        scope_id=issue.scope_id,
                        status=issue.status.value,
                        priority=issue.priority.value,
                        assignee_user_id=issue.assignee_user_id,
                        deduplication_key_digest=issue.deduplication_key_digest,
                        payload_digest=payload_digest,
                        occurrence_count=issue.occurrence_count,
                        version=1,
                        created_at=issue.created_at,
                        updated_at=issue.updated_at,
                        last_seen_at=issue.last_seen_at,
                        title=issue.title,
                        source_execution_id=issue.source_execution_id,
                        source_rule_version_id=issue.source_rule_version_id,
                    )
                )
                self._insert_history(session, history)
                issue_id = issue.issue_id
                if relationship is not None:
                    if relationship_history is None or relationship_audit_event is None:
                        raise IssueValidationError(
                            "Issue relationship history and audit event are required."
                        )
                    self._insert_relationship(
                        session,
                        issue,
                        relationship,
                        relationship_history,
                        source_event_occurred_at,
                    )
            else:
                if existing["payload_digest"] != payload_digest:
                    raise IssueConflictError(
                        "Deduplication key was reused with a different issue payload."
                    )
                current_status = IssueStatus(existing["status"])
                existing_updated_at = _require_datetime(existing["updated_at"])
                reopened = (
                    current_status is IssueStatus.CLOSED
                    and issue.source_event_type is IssueSourceEventType.QUALITY
                    and source_event_occurred_at >= existing_updated_at
                )
                target_status = IssueStatus.WAITING_FOR_RESOLUTION if reopened else current_status
                updated_at = (
                    issue.updated_at
                    if reopened or current_status is not IssueStatus.CLOSED
                    else existing_updated_at
                )
                issue_id = str(existing["issue_id"])
                session.execute(
                    update(self._table)
                    .where(self._table.c.issue_id == issue_id)
                    .values(
                        occurrence_count=self._table.c.occurrence_count + 1,
                        last_seen_at=issue.last_seen_at,
                        updated_at=updated_at,
                        source_event_id=issue.source_event_id,
                        status=target_status.value,
                        version=self._table.c.version + 1,
                    )
                )
                self._insert_history(
                    session,
                    IssueHistoryEntry(
                        issue_id=issue_id,
                        action=(
                            "ISSUE_REOPENED_BY_RECURRING_QUALITY_FAILURE"
                            if reopened
                            else "ISSUE_REPEATED"
                        ),
                        actor_id=history.actor_id,
                        old_status=current_status,
                        new_status=target_status,
                        occurred_at=history.occurred_at,
                    ),
                )
                audit_event = reopen_audit_event if reopened else audit_event
            audit_outbox.stage(audit_event, session=session)
            if existing is None and relationship_audit_event is not None:
                audit_outbox.stage(relationship_audit_event, session=session)
            if notification_batch is not None:
                self._stage_notification_batch(session, notification_batch)
        return self.get(issue_id)

    def transition_status(
        self,
        issue_id: str,
        expected_status: IssueStatus,
        target_status: IssueStatus,
        updated_at: datetime,
        history: IssueHistoryEntry,
        *,
        expected_version: int,
        audit_event: PreparedAuditEvent,
        audit_outbox: PostgreSQLTransactionalAudit,
    ) -> DataQualityIssue:
        self._require_postgresql_audit(audit_outbox)
        with transactional_session(self._session_factory) as session:
            result = session.execute(
                update(self._table)
                .where(
                    self._table.c.issue_id == issue_id,
                    self._table.c.status == expected_status.value,
                    self._table.c.version == expected_version,
                )
                .values(
                    status=target_status.value,
                    updated_at=updated_at,
                    version=self._table.c.version + 1,
                )
            )
            self._require_updated(session, result, issue_id, "status transition")
            self._insert_history(session, history)
            audit_outbox.stage(audit_event, session=session)
        return self.get(issue_id)

    def update_assignment(
        self,
        issue_id: str,
        *,
        expected_version: int,
        expected_status: IssueStatus,
        expected_assignee_user_id: str,
        expected_priority: IssuePriority,
        assignee_user_id: str,
        priority: IssuePriority,
        updated_at: datetime,
        history: IssueHistoryEntry,
        audit_event: PreparedAuditEvent,
        audit_outbox: PostgreSQLTransactionalAudit,
        notification_batch: object = None,
    ) -> DataQualityIssue:
        self._require_postgresql_audit(audit_outbox)
        with transactional_session(self._session_factory) as session:
            result = session.execute(
                update(self._table)
                .where(
                    self._table.c.issue_id == issue_id,
                    self._table.c.version == expected_version,
                    self._table.c.status == expected_status.value,
                    self._table.c.assignee_user_id == expected_assignee_user_id,
                    self._table.c.priority == expected_priority.value,
                )
                .values(
                    status=IssueStatus.ASSIGNED.value,
                    assignee_user_id=assignee_user_id,
                    priority=priority.value,
                    updated_at=updated_at,
                    version=self._table.c.version + 1,
                )
            )
            self._require_updated(session, result, issue_id, "assignment")
            self._insert_history(session, history)
            audit_outbox.stage(audit_event, session=session)
            if notification_batch is not None:
                self._stage_notification_batch(session, notification_batch)
        return self.get(issue_id)

    def resolve(
        self,
        issue_id: str,
        *,
        expected_version: int,
        expected_status: IssueStatus,
        expected_assignee_user_id: str,
        resolution: IssueResolutionRecord,
        updated_at: datetime,
        history: IssueHistoryEntry,
        audit_event: PreparedAuditEvent,
        audit_outbox: PostgreSQLTransactionalAudit,
    ) -> DataQualityIssue:
        self._require_postgresql_audit(audit_outbox)
        with transactional_session(self._session_factory) as session:
            result = session.execute(
                update(self._table)
                .where(
                    self._table.c.issue_id == issue_id,
                    self._table.c.version == expected_version,
                    self._table.c.status == expected_status.value,
                    self._table.c.assignee_user_id == expected_assignee_user_id,
                )
                .values(
                    status=IssueStatus.RESOLVED.value,
                    updated_at=updated_at,
                    version=self._table.c.version + 1,
                )
            )
            self._require_updated(session, result, issue_id, "resolution")
            session.execute(
                insert(self._tables.resolutions).values(
                    resolution_id=resolution.resolution_id,
                    issue_id=resolution.issue_id,
                    root_cause=resolution.root_cause,
                    corrective_action=resolution.corrective_action,
                    evidence_reference_id=resolution.evidence_reference_id,
                    completed_at=resolution.completed_at,
                    protection_policy_version=resolution.protection_policy_version,
                    created_by=resolution.created_by,
                    created_at=resolution.created_at,
                )
            )
            self._insert_history(session, history)
            audit_outbox.stage(audit_event, session=session)
        return self.get(issue_id)

    def record_verification(
        self,
        issue_id: str,
        *,
        expected_status: IssueStatus,
        target_status: IssueStatus,
        verification: IssueVerificationRecord,
        updated_at: datetime,
        history: IssueHistoryEntry,
        audit_event: PreparedAuditEvent,
        audit_outbox: PostgreSQLTransactionalAudit,
    ) -> DataQualityIssue:
        self._require_postgresql_audit(audit_outbox)
        with transactional_session(self._session_factory) as session:
            result = session.execute(
                update(self._table)
                .where(
                    self._table.c.issue_id == issue_id,
                    self._table.c.status == expected_status.value,
                )
                .values(
                    status=target_status.value,
                    updated_at=updated_at,
                    version=self._table.c.version + 1,
                )
            )
            self._require_updated(session, result, issue_id, "verification")
            session.execute(
                insert(self._tables.verifications).values(
                    verification_id=verification.verification_id,
                    issue_id=verification.issue_id,
                    verification_reference_id=verification.verification_reference_id,
                    execution_id=verification.execution_id,
                    score_id=verification.score_id,
                    scope_type=verification.scope_type.value,
                    scope_id=verification.scope_id,
                    outcome=verification.outcome.value,
                    completed_at=verification.completed_at,
                    recorded_by=verification.recorded_by,
                    recorded_at=verification.recorded_at,
                )
            )
            self._insert_history(session, history)
            audit_outbox.stage(audit_event, session=session)
        return self.get(issue_id)

    def get(self, issue_id: str) -> DataQualityIssue:
        with self._session_factory() as session:
            row = (
                session.execute(select(self._table).where(self._table.c.issue_id == issue_id))
                .mappings()
                .one_or_none()
            )
        if row is None:
            raise IssueNotFoundError("Issue not found.")
        return _row_to_issue(row)

    def list_issues_for_scopes(
        self,
        allowed_source_ids: frozenset[str],
        allowed_dataset_ids: frozenset[str],
        *,
        limit: int = 100,
    ) -> list[DataQualityIssue]:
        if not 1 <= limit <= 100:
            raise IssueValidationError("Issue query limit must be between 1 and 100.")
        scope_filters = []
        if allowed_source_ids:
            scope_filters.append(
                and_(
                    self._table.c.scope_type == IssueScopeType.SOURCE.value,
                    self._table.c.scope_id.in_(sorted(allowed_source_ids)),
                )
            )
        if allowed_dataset_ids:
            scope_filters.append(
                and_(
                    self._table.c.scope_type == IssueScopeType.DATASET.value,
                    self._table.c.scope_id.in_(sorted(allowed_dataset_ids)),
                )
            )
        if not scope_filters:
            return []
        statement = (
            select(self._table)
            .where(or_(*scope_filters))
            .order_by(self._table.c.updated_at.desc(), self._table.c.issue_id.desc())
            .limit(limit)
        )
        with self._session_factory() as session:
            rows = session.execute(statement).mappings().all()
        return [_row_to_issue(row) for row in rows]

    def list_history(self, issue_id: str) -> tuple[IssueHistoryEntry, ...]:
        with self._session_factory() as session:
            rows = (
                session.execute(
                    select(self._tables.history)
                    .where(self._tables.history.c.issue_id == issue_id)
                    .order_by(self._tables.history.c.sequence_no)
                )
                .mappings()
                .all()
            )
        return tuple(_row_to_history(row) for row in rows)

    def get_history(self, history_id: str) -> IssueHistoryEntry:
        with self._session_factory() as session:
            row = (
                session.execute(
                    select(self._tables.history).where(
                        self._tables.history.c.history_id == history_id
                    )
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            raise IssueNotFoundError("Issue history not found.")
        return _row_to_history(row)

    def get_latest_resolution(self, issue_id: str) -> IssueResolutionRecord:
        row = self._latest(self._tables.resolutions, issue_id)
        if row is None:
            raise IssueNotFoundError("Issue resolution not found.")
        return _row_to_resolution(row)

    def list_evidence(self, issue_id: str) -> list[IssueEvidenceRecord]:
        table = self._tables.evidence
        with self._session_factory() as session:
            rows = (
                session.execute(
                    select(table).where(table.c.issue_id == issue_id).order_by(table.c.sequence_no)
                )
                .mappings()
                .all()
            )
        return [_row_to_evidence(row) for row in rows]

    def get_evidence(self, evidence_id: str) -> IssueEvidenceRecord | None:
        table = self._tables.evidence
        with self._session_factory() as session:
            row = (
                session.execute(select(table).where(table.c.evidence_id == evidence_id))
                .mappings()
                .one_or_none()
            )
        return None if row is None else _row_to_evidence(row)

    def add_evidence(self, record: IssueEvidenceRecord) -> IssueEvidenceRecord:
        table = self._tables.evidence
        with transactional_session(self._session_factory) as session:
            session.execute(
                select(
                    func.pg_advisory_xact_lock(
                        func.hashtext("dq_issue_evidence"),
                        func.hashtext(f"{record.issue_id}:{record.source_digest}"),
                    )
                )
            )
            existing = (
                session.execute(
                    select(table).where(
                        table.c.issue_id == record.issue_id,
                        table.c.source_digest == record.source_digest,
                    )
                )
                .mappings()
                .one_or_none()
            )
            if existing is not None:
                return _row_to_evidence(existing)
            session.execute(
                insert(table).values(
                    evidence_id=record.evidence_id,
                    issue_id=record.issue_id,
                    kind=record.kind.value,
                    label=record.label,
                    execution_id=record.execution_id,
                    rule_version_id=record.rule_version_id,
                    evaluated_count=record.evaluated_count,
                    failed_count=record.failed_count,
                    measurement_status=record.measurement_status,
                    fingerprint=record.fingerprint,
                    query_reference=record.query_reference,
                    plan_reference=record.plan_reference,
                    content_digest=record.content_digest,
                    source_digest=record.source_digest,
                    observed_at=record.observed_at,
                    captured_at=record.captured_at,
                    captured_by=record.captured_by,
                )
            )
        return record

    def add_uploaded_evidence(
        self, evidence: IssueEvidenceRecord, file: IssueEvidenceFileRecord
    ) -> tuple[IssueEvidenceRecord, IssueEvidenceFileRecord]:
        with transactional_session(self._session_factory) as session:
            existing = (
                session.execute(
                    select(self._tables.evidence_files)
                    .where(
                        self._tables.evidence_files.c.idempotency_digest == file.idempotency_digest,
                        self._tables.evidence.c.issue_id == evidence.issue_id,
                    )
                    .select_from(
                        self._tables.evidence_files.join(
                            self._tables.evidence,
                            self._tables.evidence_files.c.evidence_id
                            == self._tables.evidence.c.evidence_id,
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
            if existing is not None:
                stored_file = _row_to_evidence_file(existing)
                stored_evidence = (
                    session.execute(
                        select(self._tables.evidence).where(
                            self._tables.evidence.c.evidence_id == stored_file.evidence_id
                        )
                    )
                    .mappings()
                    .one()
                )
                return _row_to_evidence(stored_evidence), stored_file
            session.execute(
                insert(self._tables.evidence).values(
                    evidence_id=evidence.evidence_id,
                    issue_id=evidence.issue_id,
                    kind=evidence.kind.value,
                    label=evidence.label,
                    execution_id=evidence.execution_id,
                    rule_version_id=evidence.rule_version_id,
                    evaluated_count=evidence.evaluated_count,
                    failed_count=evidence.failed_count,
                    measurement_status=evidence.measurement_status,
                    fingerprint=evidence.fingerprint,
                    query_reference=evidence.query_reference,
                    plan_reference=evidence.plan_reference,
                    content_digest=evidence.content_digest,
                    source_digest=evidence.source_digest,
                    observed_at=evidence.observed_at,
                    captured_at=evidence.captured_at,
                    captured_by=evidence.captured_by,
                )
            )
            session.execute(insert(self._tables.evidence_files).values(**_file_values(file)))
        return evidence, file

    def get_evidence_file(self, evidence_id: str) -> IssueEvidenceFileRecord | None:
        with self._session_factory() as session:
            row = (
                session.execute(
                    select(self._tables.evidence_files).where(
                        self._tables.evidence_files.c.evidence_id == evidence_id
                    )
                )
                .mappings()
                .one_or_none()
            )
        return None if row is None else _row_to_evidence_file(row)

    def list_evidence_files(self, issue_id: str) -> list[IssueEvidenceFileRecord]:
        with self._session_factory() as session:
            rows = (
                session.execute(
                    select(self._tables.evidence_files)
                    .select_from(self._tables.evidence_files.join(self._tables.evidence))
                    .where(self._tables.evidence.c.issue_id == issue_id)
                )
                .mappings()
                .all()
            )
        return [_row_to_evidence_file(row) for row in rows]

    def update_evidence_file(self, file: IssueEvidenceFileRecord) -> None:
        with transactional_session(self._session_factory) as session:
            session.execute(
                update(self._tables.evidence_files)
                .where(self._tables.evidence_files.c.file_id == file.file_id)
                .values(**_file_values(file))
            )

    def evidence_is_referenced(self, evidence_id: str) -> bool:
        with self._session_factory() as session:
            return (
                session.execute(
                    select(self._tables.resolutions.c.sequence_no)
                    .where(self._tables.resolutions.c.evidence_reference_id == evidence_id)
                    .limit(1)
                ).first()
                is not None
            )

    def get_latest_verification(self, issue_id: str) -> IssueVerificationRecord:
        row = self._latest(self._tables.verifications, issue_id)
        if row is None:
            raise IssueNotFoundError("Issue verification not found.")
        return _row_to_verification(row)

    def list_relationships(self, issue_id: str) -> tuple[IssueRelationship, ...]:
        table = self._tables.relationships
        with self._session_factory() as session:
            rows = (
                session.execute(
                    select(table)
                    .where(
                        or_(
                            table.c.predecessor_issue_id == issue_id,
                            table.c.successor_issue_id == issue_id,
                        )
                    )
                    .order_by(table.c.sequence_no)
                )
                .mappings()
                .all()
            )
        return tuple(_row_to_relationship(row) for row in rows)

    def count(self) -> int:
        with self._session_factory() as session:
            return session.scalar(select(func.count()).select_from(self._table)) or 0

    def _latest(self, table: Table, issue_id: str) -> RowMapping | None:
        with self._session_factory() as session:
            return (
                session.execute(
                    select(table)
                    .where(table.c.issue_id == issue_id)
                    .order_by(table.c.sequence_no.desc())
                    .limit(1)
                )
                .mappings()
                .one_or_none()
            )

    def _insert_history(self, session: Session, history: IssueHistoryEntry) -> None:
        session.execute(
            insert(self._tables.history).values(
                history_id=history.history_id,
                issue_id=history.issue_id,
                action=history.action,
                actor_id=history.actor_id,
                old_status=history.old_status.value if history.old_status else None,
                new_status=history.new_status.value,
                old_assignee_user_id=history.old_assignee_user_id,
                new_assignee_user_id=history.new_assignee_user_id,
                old_priority=history.old_priority.value if history.old_priority else None,
                new_priority=history.new_priority.value if history.new_priority else None,
                occurred_at=history.occurred_at,
                resolution_id=history.resolution_id,
                verification_id=history.verification_id,
                source_event_id=history.source_event_id,
                source_event_occurred_at=history.source_event_occurred_at,
                source_event_payload_digest=history.source_event_payload_digest,
            )
        )

    def _insert_relationship(
        self,
        session: Session,
        successor: DataQualityIssue,
        relationship: IssueRelationship,
        history: IssueHistoryEntry,
        source_event_occurred_at: datetime,
    ) -> None:
        if (
            relationship.successor_issue_id != successor.issue_id
            or relationship.predecessor_issue_id == successor.issue_id
            or relationship.relationship_type is not IssueRelationshipType.RECURRENCE
            or history.issue_id != relationship.predecessor_issue_id
            or history.old_status is not IssueStatus.CLOSED
            or history.new_status is not IssueStatus.CLOSED
        ):
            raise IssueRelationshipError("Issue relationship is inconsistent.")
        predecessor = (
            session.execute(
                select(self._table)
                .where(self._table.c.issue_id == relationship.predecessor_issue_id)
                .with_for_update()
            )
            .mappings()
            .one_or_none()
        )
        if predecessor is None:
            raise IssueRelationshipError("Predecessor issue was not found.")
        if IssueStatus(predecessor["status"]) is not IssueStatus.CLOSED:
            raise IssueRelationshipError("Predecessor issue must be closed.")
        if (
            IssueSourceEventType(predecessor["source_event_type"])
            is not IssueSourceEventType.QUALITY
            or successor.source_event_type is not IssueSourceEventType.QUALITY
        ):
            raise IssueRelationshipError("Only quality issues can be related as recurrence.")
        if (
            IssueTriggerType(predecessor["trigger_type"]) is not successor.trigger_type
            or IssueScopeType(predecessor["scope_type"]) is not successor.scope_type
            or predecessor["scope_id"] != successor.scope_id
        ):
            raise IssueRelationshipError("Predecessor issue scope or trigger does not match.")
        if source_event_occurred_at < _require_datetime(predecessor["updated_at"]):
            raise IssueRelationshipError("Related quality event predates issue closure.")
        session.execute(
            insert(self._tables.relationships).values(
                relationship_id=relationship.relationship_id,
                predecessor_issue_id=relationship.predecessor_issue_id,
                successor_issue_id=relationship.successor_issue_id,
                relationship_type=relationship.relationship_type.value,
                created_at=relationship.created_at,
            )
        )
        self._insert_history(session, history)

    def _require_updated(
        self,
        session: Session,
        result: Any,
        issue_id: str,
        operation: str,
    ) -> None:
        if result.rowcount == 1:
            return
        exists = session.scalar(
            select(func.count()).select_from(self._table).where(self._table.c.issue_id == issue_id)
        )
        if not exists:
            raise IssueNotFoundError("Issue not found.")
        raise IssueValidationError(f"Issue {operation} is no longer valid.")

    def _require_postgresql_audit(
        self,
        audit_outbox: PostgreSQLTransactionalAudit,
    ) -> None:
        if not isinstance(audit_outbox, PostgreSQLTransactionalAudit):
            raise IssueValidationError("PostgreSQL audit outbox is required.")

    def _stage_notification_batch(
        self,
        session: Session,
        notification_batch: object,
    ) -> None:
        """Stage notification batch in the same session as the issue mutation.

        The batch must be a PreparedNotificationBatch from the notifications
        contracts module. Staging is a no-op if the batch is empty.
        """
        from veri_kalitesi.notifications.contracts import PreparedNotificationBatch

        if not isinstance(notification_batch, PreparedNotificationBatch):
            return
        if notification_batch.is_empty:
            return
        from veri_kalitesi.notifications.postgresql_repository import (
            PostgreSQLNotificationRepository,
        )

        notification_repo = PostgreSQLNotificationRepository(
            self._session_factory, schema=self._schema
        )
        notification_repo.stage_batch(session, notification_batch)


def _row_to_issue(values: RowMapping) -> DataQualityIssue:
    return DataQualityIssue(
        issue_id=values["issue_id"],
        issue_no=values["issue_no"],
        source_event_id=values["source_event_id"],
        source_event_type=IssueSourceEventType(values["source_event_type"]),
        trigger_type=IssueTriggerType(values["trigger_type"]),
        scope_type=IssueScopeType(values["scope_type"]),
        scope_id=values["scope_id"],
        status=IssueStatus(values["status"]),
        priority=IssuePriority(values["priority"]),
        assignee_user_id=values["assignee_user_id"],
        deduplication_key_digest=values["deduplication_key_digest"],
        occurrence_count=values["occurrence_count"],
        created_at=_require_datetime(values["created_at"]),
        updated_at=_require_datetime(values["updated_at"]),
        last_seen_at=_require_datetime(values["last_seen_at"]),
        version=int(values["version"]),
        title=str(values.get("title", "")),
        source_execution_id=values.get("source_execution_id"),
        source_rule_version_id=values.get("source_rule_version_id"),
    )


def _row_to_history(values: RowMapping) -> IssueHistoryEntry:
    return IssueHistoryEntry(
        history_id=values["history_id"],
        issue_id=values["issue_id"],
        action=values["action"],
        actor_id=values["actor_id"],
        old_status=IssueStatus(values["old_status"]) if values["old_status"] else None,
        new_status=IssueStatus(values["new_status"]),
        occurred_at=_require_datetime(values["occurred_at"]),
        old_assignee_user_id=values["old_assignee_user_id"],
        new_assignee_user_id=values["new_assignee_user_id"],
        old_priority=(IssuePriority(values["old_priority"]) if values["old_priority"] else None),
        new_priority=(IssuePriority(values["new_priority"]) if values["new_priority"] else None),
        resolution_id=values["resolution_id"],
        verification_id=values["verification_id"],
        source_event_id=values.get("source_event_id"),
        source_event_occurred_at=(
            _require_datetime(values["source_event_occurred_at"])
            if values.get("source_event_occurred_at")
            else None
        ),
        source_event_payload_digest=values.get("source_event_payload_digest"),
    )


def _row_to_resolution(values: RowMapping) -> IssueResolutionRecord:
    return IssueResolutionRecord(
        resolution_id=values["resolution_id"],
        issue_id=values["issue_id"],
        root_cause=values["root_cause"],
        corrective_action=values["corrective_action"],
        evidence_reference_id=values["evidence_reference_id"],
        completed_at=_require_datetime(values["completed_at"]),
        protection_policy_version=values["protection_policy_version"],
        created_by=values["created_by"],
        created_at=_require_datetime(values["created_at"]),
    )


def _row_to_evidence(values: RowMapping) -> IssueEvidenceRecord:
    return IssueEvidenceRecord(
        evidence_id=values["evidence_id"],
        issue_id=values["issue_id"],
        kind=IssueEvidenceKind(values["kind"]),
        label=values["label"],
        execution_id=values["execution_id"],
        rule_version_id=values["rule_version_id"],
        evaluated_count=values["evaluated_count"],
        failed_count=values["failed_count"],
        measurement_status=values["measurement_status"],
        fingerprint=values["fingerprint"],
        query_reference=values["query_reference"],
        plan_reference=values["plan_reference"],
        content_digest=values["content_digest"],
        source_digest=values["source_digest"],
        observed_at=_require_datetime(values["observed_at"]),
        captured_at=_require_datetime(values["captured_at"]),
        captured_by=values["captured_by"],
    )


def _file_values(file: IssueEvidenceFileRecord) -> dict[str, object]:
    return dict(file.__dict__)


def _row_to_evidence_file(values: RowMapping) -> IssueEvidenceFileRecord:
    return IssueEvidenceFileRecord(
        file_id=values["file_id"],
        evidence_id=values["evidence_id"],
        original_filename=values["original_filename"],
        safe_filename=values["safe_filename"],
        declared_media_type=values["declared_media_type"],
        detected_media_type=values["detected_media_type"],
        byte_size=values["byte_size"],
        object_key=values["object_key"],
        sha256_digest=values["sha256_digest"],
        scan_status=EvidenceScanStatus(values["scan_status"]),
        scan_reason_code=values["scan_reason_code"],
        scan_completed_at=values["scan_completed_at"],
        classification=EvidenceClassification(values["classification"]),
        uploaded_by=values["uploaded_by"],
        uploaded_at=values["uploaded_at"],
        retention_until=values["retention_until"],
        legal_hold=values["legal_hold"],
        deleted_at=values["deleted_at"],
        deleted_by=values["deleted_by"],
        idempotency_digest=values["idempotency_digest"],
    )


def _row_to_verification(values: RowMapping) -> IssueVerificationRecord:
    return IssueVerificationRecord(
        verification_id=values["verification_id"],
        issue_id=values["issue_id"],
        verification_reference_id=values["verification_reference_id"],
        execution_id=values["execution_id"],
        score_id=values["score_id"],
        scope_type=IssueScopeType(values["scope_type"]),
        scope_id=values["scope_id"],
        outcome=IssueVerificationOutcome(values["outcome"]),
        completed_at=_require_datetime(values["completed_at"]),
        recorded_by=values["recorded_by"],
        recorded_at=_require_datetime(values["recorded_at"]),
    )


def _row_to_relationship(values: RowMapping) -> IssueRelationship:
    return IssueRelationship(
        relationship_id=values["relationship_id"],
        predecessor_issue_id=values["predecessor_issue_id"],
        successor_issue_id=values["successor_issue_id"],
        relationship_type=IssueRelationshipType(values["relationship_type"]),
        created_at=_require_datetime(values["created_at"]),
    )


def _require_datetime(value: object) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError("PostgreSQL timestamp value is invalid.")
    return value
