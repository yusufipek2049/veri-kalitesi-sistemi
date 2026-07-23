"""36A2a gerçek PostgreSQL issue mutasyon ve atomik audit testleri."""

from __future__ import annotations

import os
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from veri_kalitesi.audit import (
    AuditEventInput,
    AuditRedactionPolicy,
    AuditRedactor,
    AuditResult,
    PostgreSQLTransactionalAudit,
    PreparedAuditEvent,
)
from veri_kalitesi.issues import (
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
    IssueValidationError,
    IssueVerificationOutcome,
    IssueVerificationRecord,
    PostgreSQLIssueRepository,
)
from veri_kalitesi.persistence import DatabaseSettings, create_session_factory

POSTGRES_TEST_URL = os.environ.get("DATA_QUALITY_POSTGRES_TEST_URL")
pytestmark = pytest.mark.skipif(
    not POSTGRES_TEST_URL,
    reason="DATA_QUALITY_POSTGRES_TEST_URL is required for PostgreSQL integration.",
)
ROOT = Path(__file__).resolve().parents[2]


def test_fr_064_070_issue_lifecycle_and_audit_share_postgresql_transactions() -> None:
    """FR-064–FR-070, UC-011/013/014, NFR-REL-005/006, NFR-SEC-011."""

    with _postgres_fixture() as fixture:
        now = datetime.now(timezone.utc)
        issue = _issue(now)
        stored = fixture.repository.add_or_increment(
            issue,
            _history(issue, None, IssueStatus.ASSIGNED, "ISSUE_CREATED", now),
            payload_digest="payload-v1",
            source_event_occurred_at=now,
            relationship=None,
            relationship_history=None,
            audit_event=fixture.audit_event(issue.issue_id, now),
            reopen_audit_event=fixture.audit_event(issue.issue_id, now),
            relationship_audit_event=None,
            audit_outbox=fixture.audit,
        )
        repeated = fixture.repository.add_or_increment(
            issue,
            _history(issue, None, IssueStatus.ASSIGNED, "IGNORED", now),
            payload_digest="payload-v1",
            source_event_occurred_at=now,
            relationship=None,
            relationship_history=None,
            audit_event=fixture.audit_event(issue.issue_id, now),
            reopen_audit_event=fixture.audit_event(issue.issue_id, now),
            relationship_audit_event=None,
            audit_outbox=fixture.audit,
        )
        investigated = fixture.repository.transition_status(
            issue.issue_id,
            IssueStatus.ASSIGNED,
            IssueStatus.INVESTIGATING,
            now + timedelta(seconds=1),
            _history(
                issue,
                IssueStatus.ASSIGNED,
                IssueStatus.INVESTIGATING,
                "ISSUE_INVESTIGATION_STARTED",
                now + timedelta(seconds=1),
            ),
            expected_version=repeated.version,
            audit_event=fixture.audit_event(issue.issue_id, now),
            audit_outbox=fixture.audit,
        )
        with pytest.raises(IssueValidationError, match="no longer valid"):
            fixture.repository.transition_status(
                issue.issue_id,
                IssueStatus.INVESTIGATING,
                IssueStatus.WAITING_FOR_RESOLUTION,
                now + timedelta(seconds=2),
                _history(
                    issue,
                    IssueStatus.INVESTIGATING,
                    IssueStatus.WAITING_FOR_RESOLUTION,
                    "STALE_TRANSITION",
                    now + timedelta(seconds=2),
                ),
                expected_version=repeated.version,
                audit_event=fixture.audit_event(issue.issue_id, now),
                audit_outbox=fixture.audit,
            )
        assert fixture.repository.get(issue.issue_id).version == investigated.version
        assert len(fixture.repository.list_history(issue.issue_id)) == 3
        new_assignee = str(uuid4())
        with pytest.raises(IssueValidationError, match="no longer valid"):
            fixture.repository.update_assignment(
                issue.issue_id,
                expected_version=repeated.version,
                expected_status=IssueStatus.INVESTIGATING,
                expected_assignee_user_id=issue.assignee_user_id,
                expected_priority=issue.priority,
                assignee_user_id=new_assignee,
                priority=IssuePriority.CRITICAL,
                updated_at=now + timedelta(seconds=2),
                history=IssueHistoryEntry(
                    issue_id=issue.issue_id,
                    action="STALE_REASSIGNMENT",
                    actor_id=str(uuid4()),
                    old_status=IssueStatus.INVESTIGATING,
                    new_status=IssueStatus.ASSIGNED,
                    occurred_at=now + timedelta(seconds=2),
                ),
                audit_event=fixture.audit_event(issue.issue_id, now),
                audit_outbox=fixture.audit,
            )
        assert fixture.repository.get(issue.issue_id).version == investigated.version
        assert len(fixture.repository.list_history(issue.issue_id)) == 3
        assigned = fixture.repository.update_assignment(
            issue.issue_id,
            expected_version=investigated.version,
            expected_status=IssueStatus.INVESTIGATING,
            expected_assignee_user_id=issue.assignee_user_id,
            expected_priority=issue.priority,
            assignee_user_id=new_assignee,
            priority=IssuePriority.CRITICAL,
            updated_at=now + timedelta(seconds=2),
            history=IssueHistoryEntry(
                issue_id=issue.issue_id,
                action="ISSUE_REASSIGNED",
                actor_id=str(uuid4()),
                old_status=IssueStatus.INVESTIGATING,
                new_status=IssueStatus.ASSIGNED,
                occurred_at=now + timedelta(seconds=2),
                old_assignee_user_id=issue.assignee_user_id,
                new_assignee_user_id=new_assignee,
                old_priority=issue.priority,
                new_priority=IssuePriority.CRITICAL,
            ),
            audit_event=fixture.audit_event(issue.issue_id, now),
            audit_outbox=fixture.audit,
        )
        resolution = IssueResolutionRecord(
            issue_id=issue.issue_id,
            root_cause="Sentetik kök neden",
            corrective_action="Sentetik düzeltici faaliyet",
            evidence_reference_id=str(uuid4()),
            completed_at=now + timedelta(seconds=3),
            protection_policy_version="TEST_POLICY_V1",
            created_by=new_assignee,
            created_at=now + timedelta(seconds=3),
        )
        resolved = fixture.repository.resolve(
            issue.issue_id,
            expected_status=IssueStatus.ASSIGNED,
            expected_assignee_user_id=new_assignee,
            resolution=resolution,
            updated_at=now + timedelta(seconds=3),
            history=IssueHistoryEntry(
                issue_id=issue.issue_id,
                action="ISSUE_RESOLVED",
                actor_id=new_assignee,
                old_status=IssueStatus.ASSIGNED,
                new_status=IssueStatus.RESOLVED,
                occurred_at=now + timedelta(seconds=3),
                resolution_id=resolution.resolution_id,
            ),
            audit_event=fixture.audit_event(issue.issue_id, now),
            audit_outbox=fixture.audit,
        )
        verification = IssueVerificationRecord(
            issue_id=issue.issue_id,
            verification_reference_id=str(uuid4()),
            execution_id=str(uuid4()),
            score_id=str(uuid4()),
            scope_type=issue.scope_type,
            scope_id=issue.scope_id,
            outcome=IssueVerificationOutcome.QUALITY_PASSED,
            completed_at=now + timedelta(seconds=4),
            recorded_by=str(uuid4()),
            recorded_at=now + timedelta(seconds=4),
        )
        verified = fixture.repository.record_verification(
            issue.issue_id,
            expected_status=IssueStatus.RESOLVED,
            target_status=IssueStatus.VERIFIED,
            verification=verification,
            updated_at=now + timedelta(seconds=4),
            history=IssueHistoryEntry(
                issue_id=issue.issue_id,
                action="ISSUE_VERIFIED",
                actor_id=verification.recorded_by,
                old_status=IssueStatus.RESOLVED,
                new_status=IssueStatus.VERIFIED,
                occurred_at=now + timedelta(seconds=4),
                verification_id=verification.verification_id,
            ),
            audit_event=fixture.audit_event(issue.issue_id, now),
            audit_outbox=fixture.audit,
        )
        closed = fixture.repository.transition_status(
            issue.issue_id,
            IssueStatus.VERIFIED,
            IssueStatus.CLOSED,
            now + timedelta(seconds=5),
            _history(
                issue,
                IssueStatus.VERIFIED,
                IssueStatus.CLOSED,
                "ISSUE_CLOSED",
                now + timedelta(seconds=5),
            ),
            expected_version=verified.version,
            audit_event=fixture.audit_event(issue.issue_id, now),
            audit_outbox=fixture.audit,
        )
        successor = _issue(
            now + timedelta(seconds=6),
            deduplication_digest=uuid4().hex,
        )
        successor = replace(
            successor,
            scope_id=issue.scope_id,
            trigger_type=issue.trigger_type,
        )
        relationship = IssueRelationship(
            predecessor_issue_id=issue.issue_id,
            successor_issue_id=successor.issue_id,
            relationship_type=IssueRelationshipType.RECURRENCE,
            created_at=now + timedelta(seconds=6),
        )
        fixture.repository.add_or_increment(
            successor,
            _history(
                successor,
                None,
                IssueStatus.ASSIGNED,
                "ISSUE_CREATED",
                now + timedelta(seconds=6),
            ),
            payload_digest="payload-successor",
            source_event_occurred_at=now + timedelta(seconds=6),
            relationship=relationship,
            relationship_history=_history(
                issue,
                IssueStatus.CLOSED,
                IssueStatus.CLOSED,
                "ISSUE_RECURRENCE_LINKED",
                now + timedelta(seconds=6),
            ),
            audit_event=fixture.audit_event(successor.issue_id, now),
            reopen_audit_event=fixture.audit_event(successor.issue_id, now),
            relationship_audit_event=fixture.audit_event(issue.issue_id, now),
            audit_outbox=fixture.audit,
        )

        assert stored.status is IssueStatus.ASSIGNED
        assert repeated.occurrence_count == 2
        assert investigated.status is IssueStatus.INVESTIGATING
        assert assigned.assignee_user_id == new_assignee
        assert assigned.priority is IssuePriority.CRITICAL
        assert resolved.status is IssueStatus.RESOLVED
        assert verified.status is IssueStatus.VERIFIED
        assert closed.status is IssueStatus.CLOSED
        assert fixture.repository.get_latest_resolution(issue.issue_id) == resolution
        assert fixture.repository.get_latest_verification(issue.issue_id) == verification
        assert fixture.repository.list_relationships(issue.issue_id) == (relationship,)
        assert len(fixture.repository.list_history(issue.issue_id)) == 8
        assert len(fixture.audit.list_pending()) == 9

        status = fixture.audit.publish_pending()

        assert status.pending_count == 0
        assert status.published_count == 9
        assert status.failed_count == 0
        assert len(fixture.sink.events) == 9


def test_nfr_rel_006_audit_conflict_rolls_back_issue_and_history() -> None:
    """NFR-REL-006/NFR-SEC-011: Audit stage başarısızsa issue commit edilmez."""

    with _postgres_fixture() as fixture:
        now = datetime.now(timezone.utc)
        first = _issue(now)
        duplicate_audit = fixture.audit_event(first.issue_id, now)
        fixture.repository.add_or_increment(
            first,
            _history(first, None, IssueStatus.ASSIGNED, "ISSUE_CREATED", now),
            payload_digest="payload-first",
            source_event_occurred_at=now,
            relationship=None,
            relationship_history=None,
            audit_event=duplicate_audit,
            reopen_audit_event=fixture.audit_event(first.issue_id, now),
            relationship_audit_event=None,
            audit_outbox=fixture.audit,
        )
        second = _issue(now, deduplication_digest=uuid4().hex)

        with pytest.raises(IntegrityError):
            fixture.repository.add_or_increment(
                second,
                _history(second, None, IssueStatus.ASSIGNED, "ISSUE_CREATED", now),
                payload_digest="payload-second",
                source_event_occurred_at=now,
                relationship=None,
                relationship_history=None,
                audit_event=duplicate_audit,
                reopen_audit_event=fixture.audit_event(second.issue_id, now),
                relationship_audit_event=None,
                audit_outbox=fixture.audit,
            )

        assert fixture.repository.count() == 1
        assert fixture.repository.list_history(second.issue_id) == ()


class _RecordingAuditSink:
    def __init__(self) -> None:
        self.events: list[PreparedAuditEvent] = []

    def append(self, prepared: PreparedAuditEvent) -> Any:
        self.events.append(prepared)
        return object()


class _PostgreSQLFixture:
    def __init__(self, url: str, schema: str) -> None:
        self.schema = schema
        self.settings = DatabaseSettings.from_url(url, schema=schema)
        self.engine = create_engine(self.settings.url, pool_pre_ping=True)
        self.session_factory = create_session_factory(self.settings, engine=self.engine)
        self.sink = _RecordingAuditSink()
        self.audit = PostgreSQLTransactionalAudit(
            self.session_factory,
            AuditRedactor(
                AuditRedactionPolicy(
                    version="TEST_REDACTION_V1",
                    allowed_fields_by_action={"ISSUE_TEST": frozenset()},
                )
            ),
            self.sink,
            policy_version="TEST_OUTBOX_V1",
            schema=schema,
        )
        self.repository = PostgreSQLIssueRepository(self.session_factory, schema=schema)

    def audit_event(self, issue_id: str, now: datetime) -> PreparedAuditEvent:
        return self.audit.prepare(
            AuditEventInput(
                actor_id=str(uuid4()),
                actor_type="SERVICE",
                correlation_id=uuid4().hex,
                action="ISSUE_TEST",
                object_type="DATA_QUALITY_ISSUE",
                object_id=issue_id,
                result=AuditResult.SUCCESS,
                reason_code="TEST",
                old_values={},
                new_values={},
                occurred_at=now,
            )
        )


class _postgres_fixture:
    def __enter__(self) -> _PostgreSQLFixture:
        assert POSTGRES_TEST_URL is not None
        schema = f"dq_test_{uuid4().hex}"
        self.fixture = _PostgreSQLFixture(POSTGRES_TEST_URL, schema)
        config = Config(str(ROOT / "05-Veritabani/alembic.ini"))
        config.set_main_option(
            "sqlalchemy.url",
            self.fixture.settings.url.render_as_string(hide_password=False),
        )
        config.set_main_option("data_quality_schema", schema)
        command.upgrade(config, "head")
        return self.fixture

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        with self.fixture.engine.connect().execution_options(
            isolation_level="AUTOCOMMIT"
        ) as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{self.fixture.schema}" CASCADE'))
        self.fixture.engine.dispose()


def _issue(
    now: datetime,
    *,
    deduplication_digest: str | None = None,
) -> DataQualityIssue:
    return DataQualityIssue(
        issue_id=str(uuid4()),
        issue_no=f"DQI-{uuid4().hex[:12].upper()}",
        source_event_id=str(uuid4()),
        source_event_type=IssueSourceEventType.QUALITY,
        trigger_type=IssueTriggerType.QUALITY_THRESHOLD,
        scope_type=IssueScopeType.DATASET,
        scope_id=str(uuid4()),
        status=IssueStatus.ASSIGNED,
        priority=IssuePriority.HIGH,
        assignee_user_id=str(uuid4()),
        deduplication_key_digest=deduplication_digest or uuid4().hex,
        occurrence_count=1,
        created_at=now,
        updated_at=now,
        last_seen_at=now,
    )


def _history(
    issue: DataQualityIssue,
    old_status: IssueStatus | None,
    new_status: IssueStatus,
    action: str,
    now: datetime,
) -> IssueHistoryEntry:
    return IssueHistoryEntry(
        issue_id=issue.issue_id,
        action=action,
        actor_id=str(uuid4()),
        old_status=old_status,
        new_status=new_status,
        occurred_at=now,
    )
