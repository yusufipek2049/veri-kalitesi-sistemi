from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from legacy_sqlite_issue_repository import SQLiteIssueRepository

from veri_kalitesi.api import DevelopmentActorContextResolver, create_dashboard_api
from veri_kalitesi.api.development import create_development_app
from veri_kalitesi.audit import (
    AuditFailureMode,
    AuditFailurePolicy,
    AuditRedactionPolicy,
    AuditRedactor,
    AuditService,
    SQLiteAuditRepository,
)
from veri_kalitesi.dashboard import DashboardQueryService
from veri_kalitesi.identity import DashboardAuthorizationPolicy, PolicyAuthorizationService
from veri_kalitesi.issues import (
    DataQualityIssue,
    IssuePriority,
    IssueQueryService,
    IssueScopeType,
    IssueSourceEventType,
    IssueStatus,
    IssueTriggerType,
    IssueValidationError,
)
from veri_kalitesi.scoring import SQLiteScoreRepository

NOW = datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc)
POLICY_VERSION = "ISSUE_API_TEST_V1"


def test_fr_064_fr_066_issue_list_is_scope_filtered_and_data_minimum() -> None:
    reader = FakeIssueReader(
        (
            _issue("issue-dataset", IssueScopeType.DATASET, "dataset-a"),
            _issue("issue-source", IssueScopeType.SOURCE, "source-a"),
            _issue("issue-hidden", IssueScopeType.DATASET, "dataset-b"),
        )
    )
    client = TestClient(
        _app(reader, source_ids=frozenset({"source-a"}), dataset_ids=frozenset({"dataset-a"}))
    )

    response = client.get(
        "/api/v1/issues",
        headers={"X-Dataset-IDs": "dataset-b", "X-Roles": "ADMIN"},
    )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["limit"] == 100
    assert {item["issue_id"] for item in response.json()["items"]} == {
        "issue-dataset",
        "issue-source",
    }
    for protected_field in (
        "source_event_id",
        "assignee_user_id",
        "deduplication_key_digest",
        "root_cause",
        "corrective_action",
        "development-assignee",
        "must-not-leak",
    ):
        assert protected_field not in response.text


def test_nfr_sec_001_empty_issue_scope_does_not_escalate() -> None:
    reader = FakeIssueReader((_issue("issue-dataset", IssueScopeType.DATASET, "dataset-a"),))
    response = TestClient(_app(reader)).get("/api/v1/issues")

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert reader.last_source_ids == frozenset()
    assert reader.last_dataset_ids == frozenset()


def test_nfr_usa_003_issue_repository_failure_returns_safe_technical_error() -> None:
    response = TestClient(_app(FailingIssueReader(), dataset_ids=frozenset({"dataset-a"}))).get(
        "/api/v1/issues"
    )

    assert response.status_code == 503
    assert response.json()["title"] == "Issues temporarily unavailable"
    assert "database contains sensitive detail" not in response.text


def test_development_api_exposes_all_issue_lifecycle_states() -> None:
    response = TestClient(create_development_app()).get("/api/v1/issues")

    assert response.status_code == 200
    assert len(response.json()["items"]) == 8
    assert {item["status"] for item in response.json()["items"]} == {
        "NEW",
        "ASSIGNED",
        "INVESTIGATING",
        "WAITING_FOR_RESOLUTION",
        "RESOLVED",
        "VERIFIED",
        "CLOSED",
        "CANCELLED",
    }
    assert {item["source_event_type"] for item in response.json()["items"]} == {
        "QUALITY",
        "TECHNICAL",
    }
    assert "development-assignee" not in response.text


def test_fr_064_repository_lists_only_allowed_scopes_newest_first_and_bounded() -> None:
    repository = SQLiteIssueRepository()
    _insert_issue(repository, _issue("issue-old", IssueScopeType.DATASET, "dataset-a", -2))
    _insert_issue(repository, _issue("issue-new", IssueScopeType.SOURCE, "source-a"))
    _insert_issue(repository, _issue("issue-hidden", IssueScopeType.DATASET, "dataset-b", -1))

    visible = repository.list_issues_for_scopes(
        frozenset({"source-a"}),
        frozenset({"dataset-a"}),
        limit=1,
    )

    assert [issue.issue_id for issue in visible] == ["issue-new"]
    assert repository.list_issues_for_scopes(frozenset(), frozenset()) == []
    with pytest.raises(IssueValidationError):
        repository.list_issues_for_scopes(frozenset(), frozenset({"dataset-a"}), limit=101)


class FakeIssueReader:
    def __init__(self, issues: tuple[DataQualityIssue, ...]) -> None:
        self.issues = issues
        self.last_source_ids: frozenset[str] | None = None
        self.last_dataset_ids: frozenset[str] | None = None

    def list_issues_for_scopes(
        self,
        allowed_source_ids: frozenset[str],
        allowed_dataset_ids: frozenset[str],
        *,
        limit: int = 100,
    ) -> list[DataQualityIssue]:
        self.last_source_ids = allowed_source_ids
        self.last_dataset_ids = allowed_dataset_ids
        return [
            issue
            for issue in self.issues
            if (issue.scope_type is IssueScopeType.SOURCE and issue.scope_id in allowed_source_ids)
            or (
                issue.scope_type is IssueScopeType.DATASET and issue.scope_id in allowed_dataset_ids
            )
        ][:limit]


class FailingIssueReader:
    def list_issues_for_scopes(
        self,
        allowed_source_ids: frozenset[str],
        allowed_dataset_ids: frozenset[str],
        *,
        limit: int = 100,
    ) -> list[DataQualityIssue]:
        raise sqlite3.OperationalError("database contains sensitive detail")


def _issue(
    issue_id: str,
    scope_type: IssueScopeType,
    scope_id: str,
    day_offset: int = 0,
) -> DataQualityIssue:
    timestamp = NOW + timedelta(days=day_offset)
    return DataQualityIssue(
        issue_id=issue_id,
        issue_no=f"DQI-{issue_id}",
        source_event_id="must-not-leak",
        source_event_type=(
            IssueSourceEventType.TECHNICAL
            if scope_type is IssueScopeType.SOURCE
            else IssueSourceEventType.QUALITY
        ),
        trigger_type=(
            IssueTriggerType.TECHNICAL_ERROR
            if scope_type is IssueScopeType.SOURCE
            else IssueTriggerType.QUALITY_THRESHOLD
        ),
        scope_type=scope_type,
        scope_id=scope_id,
        status=IssueStatus.INVESTIGATING,
        priority=IssuePriority.HIGH,
        assignee_user_id="development-assignee",
        deduplication_key_digest="must-not-leak",
        occurrence_count=2,
        created_at=timestamp,
        updated_at=timestamp,
        last_seen_at=timestamp,
    )


def _insert_issue(repository: SQLiteIssueRepository, issue: DataQualityIssue) -> None:
    repository.connection.execute(
        """
        INSERT INTO data_quality_issues (
            issue_id, issue_no, source_event_id, source_event_type, trigger_type,
            scope_type, scope_id, status, priority, assignee_user_id,
            deduplication_key_digest, payload_digest, occurrence_count,
            created_at, updated_at, last_seen_at
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
            f"{issue.issue_id}-dedup",
            f"{issue.issue_id}-payload",
            issue.occurrence_count,
            issue.created_at.isoformat(),
            issue.updated_at.isoformat(),
            issue.last_seen_at.isoformat(),
        ),
    )
    repository.connection.commit()


def _app(
    reader: FakeIssueReader | FailingIssueReader,
    *,
    source_ids: frozenset[str] = frozenset(),
    dataset_ids: frozenset[str] = frozenset(),
):
    audit_service = AuditService(
        SQLiteAuditRepository(),
        AuditRedactor(
            AuditRedactionPolicy(
                version="ISSUE_API_REDACTION_V1",
                allowed_fields_by_action={
                    "DASHBOARD_SCOPE_AUTHORIZATION": frozenset(
                        {
                            "policy_version",
                            "permitted_source_count",
                            "can_view_enterprise",
                            "reason_code",
                        }
                    )
                },
            )
        ),
        AuditFailurePolicy("ISSUE_API_AUDIT_V1", AuditFailureMode.FAIL_CLOSED),
    )
    authorization = PolicyAuthorizationService(
        DashboardAuthorizationPolicy(version=POLICY_VERSION),
        audit_service,
        clock=lambda: NOW,
    )
    resolver = DevelopmentActorContextResolver(
        runtime_environment="development",
        policy_version=POLICY_VERSION,
        permitted_source_ids=source_ids,
        permitted_dataset_ids=dataset_ids,
        can_view_enterprise=False,
        clock=lambda: NOW,
    )
    dashboard = DashboardQueryService(SQLiteScoreRepository(), authorization, clock=lambda: NOW)
    return create_dashboard_api(
        dashboard,
        actor_context_resolver=resolver,
        issue_query_service=IssueQueryService(reader, authorization),
        data_origin="synthetic-test",
    )
