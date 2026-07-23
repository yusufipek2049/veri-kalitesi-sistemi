"""PostgreSQL-only, yetki kapsamlı issue envanteri okuyucusu."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    and_,
    func,
    or_,
    select,
)
from sqlalchemy.engine import RowMapping

from veri_kalitesi.issues.errors import IssueNotFoundError, IssueValidationError
from veri_kalitesi.issues.models import (
    DataQualityIssue,
    IssuePriority,
    IssueScopeType,
    IssueSourceEventType,
    IssueStatus,
    IssueTriggerType,
)
from veri_kalitesi.persistence import DEFAULT_SCHEMA_NAME, SessionFactory


def issue_table(schema: str = DEFAULT_SCHEMA_NAME) -> Table:
    metadata = MetaData(schema=schema)
    table = Table(
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
        CheckConstraint(
            "source_event_type IN ('QUALITY', 'TECHNICAL')",
            name="ck_issue_source_event_type",
        ),
        CheckConstraint(
            "trigger_type IN ('QUALITY_THRESHOLD', 'CRITICAL_RULE_FAILURE', 'TECHNICAL_ERROR')",
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
    Index(
        "ix_dq_issues_scope_updated",
        table.c.scope_type,
        table.c.scope_id,
        table.c.updated_at.desc(),
        table.c.issue_id.desc(),
    )
    Index(
        "ix_dq_issues_assignee_status_updated",
        table.c.assignee_user_id,
        table.c.status,
        table.c.updated_at.desc(),
    )
    return table


class PostgreSQLIssueRepository:
    """Issue okuma yolunda SQLite fallback bulundurmayan repository."""

    def __init__(
        self,
        session_factory: SessionFactory,
        *,
        schema: str = DEFAULT_SCHEMA_NAME,
    ) -> None:
        self._session_factory = session_factory
        self._table = issue_table(schema)

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

    def count(self) -> int:
        with self._session_factory() as session:
            return session.scalar(select(func.count()).select_from(self._table)) or 0


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
    )


def _require_datetime(value: object) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError("PostgreSQL timestamp value is invalid.")
    return value
