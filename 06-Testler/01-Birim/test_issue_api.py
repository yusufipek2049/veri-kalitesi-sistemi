from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from legacy_sqlite_issue_repository import SQLiteIssueRepository

from veri_kalitesi.api import (
    CSRF_HEADER_NAME,
    ApiCsrfError,
    DevelopmentActorContextResolver,
    create_dashboard_api,
)
from veri_kalitesi.api.development import create_development_app
from veri_kalitesi.api.models import IssueAssigneeOptionResponse
from veri_kalitesi.audit import (
    AuditFailureMode,
    AuditFailurePolicy,
    AuditRedactionPolicy,
    AuditRedactor,
    AuditService,
    SQLiteAuditRepository,
)
from veri_kalitesi.dashboard import DashboardQueryService
from veri_kalitesi.identity import (
    ActorContext,
    ActorContextIssuer,
    ActorType,
    DashboardAuthorizationPolicy,
    PolicyAuthorizationService,
)
from veri_kalitesi.issues import (
    DataQualityIssue,
    IssueAssignment,
    IssueAssignmentError,
    IssueAuthorizationError,
    IssueConflictError,
    IssuePriority,
    IssueQueryService,
    IssueResolutionDraft,
    IssueScopeType,
    IssueSourceEventType,
    IssueStatus,
    IssueTriggerType,
    IssueTechnicalError,
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


def test_development_api_supports_same_origin_issue_investigation_demo() -> None:
    client = TestClient(
        create_development_app(),
        base_url="http://localhost:5173",
    )
    listed = client.get("/api/v1/issues")
    proof = listed.headers[CSRF_HEADER_NAME]
    assigned = next(
        item
        for item in listed.json()["items"]
        if "START_INVESTIGATION" in item["available_actions"]
    )

    changed = client.post(
        f"/api/v1/issues/{assigned['issue_id']}/investigation",
        json={"version": assigned["version"]},
        headers={
            CSRF_HEADER_NAME: proof,
            "Origin": "http://localhost:5173",
            "Referer": "http://localhost:5173/issues",
            "Sec-Fetch-Site": "same-origin",
        },
    )

    assert changed.status_code == 200
    assert changed.json()["item"]["status"] == "INVESTIGATING"
    assert changed.json()["item"]["version"] == assigned["version"] + 1


def test_fr_065_uc_013_development_api_supports_reassignment_demo() -> None:
    client = TestClient(
        create_development_app(),
        base_url="http://localhost:5173",
    )
    listed = client.get("/api/v1/issues")
    proof = listed.headers[CSRF_HEADER_NAME]
    assignable = next(
        item for item in listed.json()["items"] if "REASSIGN" in item["available_actions"]
    )
    options = client.get(f"/api/v1/issues/{assignable['issue_id']}/assignment-options")

    changed = client.post(
        f"/api/v1/issues/{assignable['issue_id']}/assignment",
        json={
            "version": assignable["version"],
            "assignee_user_id": options.json()["items"][0]["user_id"],
            "priority": "MEDIUM",
        },
        headers={
            CSRF_HEADER_NAME: proof,
            "Origin": "http://localhost:5173",
            "Referer": "http://localhost:5173/issues",
            "Sec-Fetch-Site": "same-origin",
        },
    )

    assert options.status_code == 200
    assert options.headers["cache-control"] == "no-store"
    assert len(options.json()["items"]) == 3
    assert changed.status_code == 200
    assert changed.json()["item"]["status"] == "ASSIGNED"
    assert changed.json()["item"]["priority"] == "MEDIUM"
    assert changed.json()["item"]["version"] == assignable["version"] + 1
    assert changed.json()["item"]["available_actions"] == ["REASSIGN"]


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


def test_fr_066_uc_013_assignee_starts_investigation_through_bff() -> None:
    boundary = FakeBffBoundary()
    command = FakeInvestigationService()
    client = TestClient(_mutation_app(boundary, command), base_url="https://app.example")

    response = client.post(
        "/api/v1/issues/issue-assigned/investigation",
        json={"version": 1},
        headers=_mutation_headers(),
    )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["item"]["status"] == "INVESTIGATING"
    assert response.json()["item"]["version"] == 2
    assert response.json()["item"]["available_actions"] == ["REASSIGN", "RESOLVE"]
    assert command.calls == [("issue-assigned", 1, boundary.context.actor_id)]


def test_nfr_sec_007_missing_csrf_rejects_issue_mutation_before_service() -> None:
    boundary = FakeBffBoundary()
    command = FakeInvestigationService()
    client = TestClient(_mutation_app(boundary, command), base_url="https://app.example")
    headers = _mutation_headers()
    headers.pop(CSRF_HEADER_NAME)

    response = client.post(
        "/api/v1/issues/issue-assigned/investigation",
        json={"version": 1},
        headers=headers,
    )

    assert response.status_code == 403
    assert command.calls == []


def test_fr_065_uc_013_authorized_steward_reassigns_through_bff() -> None:
    boundary = FakeBffBoundary()
    command = FakeAssignmentService()
    options = FakeAssignmentOptions()
    client = TestClient(
        _mutation_app(
            boundary,
            FakeInvestigationService(),
            assignment_command=command,
            assignment_options=options,
        ),
        base_url="https://app.example",
    )

    candidates = client.get("/api/v1/issues/issue-assigned/assignment-options")
    response = client.post(
        "/api/v1/issues/issue-assigned/assignment",
        json={
            "version": 4,
            "assignee_user_id": "4ec96cb4-d150-45d2-9565-c1879d135f08",
            "priority": "CRITICAL",
        },
        headers=_mutation_headers(),
    )

    assert candidates.status_code == 200
    assert candidates.headers["cache-control"] == "no-store"
    assert candidates.json()["items"][0]["display_name"] == "Veri Sorumlusu A"
    assert response.status_code == 200
    assert response.json()["item"]["version"] == 5
    assert response.json()["item"]["priority"] == "CRITICAL"
    assert command.calls == [
        (
            "issue-assigned",
            "4ec96cb4-d150-45d2-9565-c1879d135f08",
            IssuePriority.CRITICAL,
            4,
            boundary.context.actor_id,
        )
    ]
    assert options.calls == [("issue-assigned", boundary.context.actor_id)]


def test_ui_write_002_reassignment_conflict_is_redacted() -> None:
    boundary = FakeBffBoundary()
    command = FakeAssignmentService(error=IssueConflictError("sensitive version"))
    response = TestClient(
        _mutation_app(
            boundary,
            FakeInvestigationService(),
            assignment_command=command,
        ),
        base_url="https://app.example",
    ).post(
        "/api/v1/issues/issue-assigned/assignment",
        json={
            "version": 3,
            "assignee_user_id": "4ec96cb4-d150-45d2-9565-c1879d135f08",
            "priority": "HIGH",
        },
        headers=_mutation_headers(),
    )

    assert response.status_code == 409
    assert response.json()["title"] == "Issue changed"
    assert "sensitive" not in response.text


def test_fr_065_invalid_assignee_is_safe_conflict() -> None:
    boundary = FakeBffBoundary()
    command = FakeAssignmentService(error=IssueAssignmentError("inactive user detail"))
    response = TestClient(
        _mutation_app(
            boundary,
            FakeInvestigationService(),
            assignment_command=command,
        ),
        base_url="https://app.example",
    ).post(
        "/api/v1/issues/issue-assigned/assignment",
        json={
            "version": 3,
            "assignee_user_id": "4ec96cb4-d150-45d2-9565-c1879d135f08",
            "priority": "HIGH",
        },
        headers=_mutation_headers(),
    )

    assert response.status_code == 409
    assert response.json()["title"] == "Issue assignment unavailable"
    assert "inactive" not in response.text


@pytest.mark.parametrize(
    ("error", "status", "title"),
    [
        (IssueAuthorizationError("sensitive scope"), 403, "Issue action denied"),
        (IssueConflictError("sensitive version"), 409, "Issue changed"),
        (
            IssueValidationError("sensitive state"),
            409,
            "Issue action unavailable",
        ),
        (
            IssueTechnicalError("database password=unsafe", "issue-technical"),
            503,
            "Issue action temporarily unavailable",
        ),
    ],
)
def test_issue_mutation_errors_are_classified_and_redacted(
    error: Exception,
    status: int,
    title: str,
) -> None:
    boundary = FakeBffBoundary()
    command = FakeInvestigationService(error=error)
    response = TestClient(
        _mutation_app(boundary, command),
        base_url="https://app.example",
    ).post(
        "/api/v1/issues/issue-assigned/investigation",
        json={"version": 1},
        headers=_mutation_headers(),
    )

    assert response.status_code == status
    assert response.json()["title"] == title
    assert "sensitive" not in response.text
    assert "password" not in response.text


def test_fr_068_authorized_assignee_resolves_issue_through_bff() -> None:
    boundary = FakeBffBoundary()
    resolution = FakeResolutionService()
    client = TestClient(
        _mutation_app(
            boundary,
            FakeInvestigationService(),
            resolution_command=resolution,
        ),
        base_url="https://app.example",
    )

    response = client.post(
        "/api/v1/issues/issue-resolved/resolution",
        json={
            "version": 1,
            "root_cause": "Eksik kaynak doğrulaması",
            "corrective_action": "Kaynak doğrulama kuralı eklendi",
            "evidence_reference_id": "550e8400-e29b-41d4-a716-446655440000",
            "completed_at": "2026-07-23T10:00:00Z",
        },
        headers=_mutation_headers(),
    )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["item"]["status"] == "RESOLVED"
    assert response.json()["item"]["version"] == 2
    assert resolution.calls == [
        (
            "issue-resolved",
            "Eksik kaynak doğrulaması",
            "Kaynak doğrulama kuralı eklendi",
            "550e8400-e29b-41d4-a716-446655440000",
            1,
            boundary.context.actor_id,
        )
    ]


def test_fr_068_resolution_missing_csrf_is_rejected() -> None:
    boundary = FakeBffBoundary()
    resolution = FakeResolutionService()
    client = TestClient(
        _mutation_app(
            boundary,
            FakeInvestigationService(),
            resolution_command=resolution,
        ),
        base_url="https://app.example",
    )
    headers = _mutation_headers()
    headers.pop(CSRF_HEADER_NAME)

    response = client.post(
        "/api/v1/issues/issue-resolved/resolution",
        json={
            "version": 1,
            "root_cause": "Test nedeni",
            "corrective_action": "Test aksiyonu",
            "evidence_reference_id": "550e8400-e29b-41d4-a716-446655440000",
            "completed_at": "2026-07-23T10:00:00Z",
        },
        headers=headers,
    )

    assert response.status_code == 403
    assert resolution.calls == []


def test_fr_068_resolution_errors_are_classified_and_redacted() -> None:
    boundary = FakeBffBoundary()
    resolution = FakeResolutionService(error=IssueTechnicalError("db password=unsafe", "issue-err"))
    response = TestClient(
        _mutation_app(
            boundary,
            FakeInvestigationService(),
            resolution_command=resolution,
        ),
        base_url="https://app.example",
    ).post(
        "/api/v1/issues/issue-resolved/resolution",
        json={
            "version": 1,
            "root_cause": "Test nedeni",
            "corrective_action": "Test aksiyonu",
            "evidence_reference_id": "550e8400-e29b-41d4-a716-446655440000",
            "completed_at": "2026-07-23T10:00:00Z",
        },
        headers=_mutation_headers(),
    )

    assert response.status_code == 503
    assert response.json()["title"] == "Issue action temporarily unavailable"
    assert "password" not in response.text
    assert "unsafe" not in response.text


def test_fr_068_ui_write_002_stale_resolution_returns_conflict() -> None:
    boundary = FakeBffBoundary()
    resolution = FakeResolutionService(
        error=IssueConflictError("stale resolution contains sensitive details")
    )
    response = TestClient(
        _mutation_app(
            boundary,
            FakeInvestigationService(),
            resolution_command=resolution,
        ),
        base_url="https://app.example",
    ).post(
        "/api/v1/issues/issue-resolved/resolution",
        json={
            "version": 7,
            "root_cause": "Test nedeni",
            "corrective_action": "Test aksiyonu",
            "evidence_reference_id": "550e8400-e29b-41d4-a716-446655440000",
            "completed_at": "2026-07-23T10:00:00Z",
        },
        headers=_mutation_headers(),
    )

    assert response.status_code == 409
    assert response.json()["title"] == "Issue changed"
    assert "sensitive" not in response.text
    assert resolution.calls[0][4] == 7


def test_development_api_supports_resolution_demo() -> None:
    client = TestClient(
        create_development_app(),
        base_url="http://localhost:5173",
    )
    listed = client.get("/api/v1/issues")
    proof = listed.headers[CSRF_HEADER_NAME]
    investigating = next(
        item for item in listed.json()["items"] if "RESOLVE" in item["available_actions"]
    )

    changed = client.post(
        f"/api/v1/issues/{investigating['issue_id']}/resolution",
        json={
            "version": investigating["version"],
            "root_cause": "Sentetik kaynak eşlemesi",
            "corrective_action": "Sentetik eşleme düzeltildi",
            "evidence_reference_id": "550e8400-e29b-41d4-a716-446655440000",
            "completed_at": datetime.now(timezone.utc).isoformat(),
        },
        headers={
            CSRF_HEADER_NAME: proof,
            "Origin": "http://localhost:5173",
            "Referer": "http://localhost:5173/issues",
            "Sec-Fetch-Site": "same-origin",
        },
    )

    assert changed.status_code == 200
    assert changed.json()["item"]["status"] == "RESOLVED"
    assert changed.json()["item"]["version"] == investigating["version"] + 1
    assert changed.json()["item"]["available_actions"] == []


def test_issue_list_exposes_action_only_to_assignee_in_scope() -> None:
    boundary = FakeBffBoundary()
    assigned = _issue("issue-assigned", IssueScopeType.DATASET, "dataset-a")
    assigned = DataQualityIssue(
        **{
            **assigned.__dict__,
            "status": IssueStatus.ASSIGNED,
            "assignee_user_id": boundary.context.actor_id,
        }
    )
    other = _issue("issue-other", IssueScopeType.DATASET, "dataset-a")
    response = TestClient(
        _mutation_app(
            boundary,
            FakeInvestigationService(),
            reader=FakeIssueReader((assigned, other)),
        ),
        base_url="https://app.example",
    ).get("/api/v1/issues")

    actions = {item["issue_id"]: item["available_actions"] for item in response.json()["items"]}
    assert actions == {
        "issue-assigned": ["START_INVESTIGATION", "REASSIGN"],
        "issue-other": ["REASSIGN"],
    }


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


class FakeBffBoundary:
    def __init__(self) -> None:
        self.context = ActorContextIssuer().issue(
            actor_id="actor-assignee",
            actor_type=ActorType.USER,
            authentication_source="test-idp",
            session_id="test-session",
            roles=frozenset({"DATA_STEWARD"}),
            permitted_source_ids=frozenset({"source-a"}),
            permitted_dataset_ids=frozenset({"dataset-a"}),
            can_view_enterprise=False,
            privileged=False,
            issued_at=NOW,
            expires_at=NOW + timedelta(minutes=15),
            policy_version=POLICY_VERSION,
            correlation_id="issue-api",
        )

    def resolve(self, request) -> ActorContext:  # type: ignore[no-untyped-def]
        return self.context

    def protect_state_changing(self, request) -> ActorContext:  # type: ignore[no-untyped-def]
        if request.headers.get(CSRF_HEADER_NAME) != "test-csrf-proof":
            raise ApiCsrfError("rejected", request.state.correlation_id)
        return self.context


class FakeInvestigationService:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[tuple[str, int, str]] = []

    def start_investigation(
        self,
        issue_id: str,
        expected_version: int,
        actor_context: ActorContext | None,
    ) -> DataQualityIssue:
        assert actor_context is not None
        self.calls.append((issue_id, expected_version, actor_context.actor_id))
        if self.error is not None:
            raise self.error
        issue = _issue(issue_id, IssueScopeType.DATASET, "dataset-a")
        return DataQualityIssue(
            **{
                **issue.__dict__,
                "status": IssueStatus.INVESTIGATING,
                "assignee_user_id": actor_context.actor_id,
                "version": expected_version + 1,
            }
        )


class FakeAssignmentService:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[tuple[str, str, IssuePriority, int, str]] = []

    def reassign(
        self,
        issue_id: str,
        assignment: IssueAssignment,
        expected_version: int,
        actor_context: ActorContext | None,
    ) -> DataQualityIssue:
        assert actor_context is not None
        self.calls.append(
            (
                issue_id,
                assignment.assignee_user_id,
                assignment.priority,
                expected_version,
                actor_context.actor_id,
            )
        )
        if self.error is not None:
            raise self.error
        issue = _issue(issue_id, IssueScopeType.DATASET, "dataset-a")
        return DataQualityIssue(
            **{
                **issue.__dict__,
                "status": IssueStatus.ASSIGNED,
                "assignee_user_id": assignment.assignee_user_id,
                "priority": assignment.priority,
                "version": expected_version + 1,
            }
        )


class FakeAssignmentOptions:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def list_assignment_options(
        self,
        issue_id: str,
        actor_context: ActorContext | None,
    ) -> tuple[IssueAssigneeOptionResponse, ...]:
        assert actor_context is not None
        self.calls.append((issue_id, actor_context.actor_id))
        return (
            IssueAssigneeOptionResponse(
                user_id="4ec96cb4-d150-45d2-9565-c1879d135f08",
                display_name="Veri Sorumlusu A",
            ),
        )


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


def _mutation_app(
    boundary: FakeBffBoundary,
    command: FakeInvestigationService,
    *,
    reader: FakeIssueReader | None = None,
    assignment_command: FakeAssignmentService | None = None,
    assignment_options: FakeAssignmentOptions | None = None,
    resolution_command: FakeResolutionService | None = None,
    verification_command: FakeVerificationService | None = None,
):
    audit_service = AuditService(
        SQLiteAuditRepository(),
        AuditRedactor(
            AuditRedactionPolicy(
                version="MUTATION_TEST_V1",
                allowed_fields_by_action={},
            )
        ),
        AuditFailurePolicy("MUTATION_TEST_V1", AuditFailureMode.FAIL_CLOSED),
    )
    authorization = PolicyAuthorizationService(
        DashboardAuthorizationPolicy(version=POLICY_VERSION),
        audit_service,
        clock=lambda: NOW,
    )
    dashboard = DashboardQueryService(
        SQLiteScoreRepository(),
        authorization,
        clock=lambda: NOW,
    )
    return create_dashboard_api(
        dashboard,
        bff_session_boundary=boundary,  # type: ignore[arg-type]
        allowed_origins=("https://app.example",),
        issue_query_service=(
            IssueQueryService(reader, authorization) if reader is not None else None
        ),
        issue_investigation_service=command,
        issue_assignment_service=assignment_command,
        issue_assignee_option_provider=assignment_options,
        issue_resolution_service=resolution_command,
        issue_verification_service=verification_command,
        data_origin="test",
    )


class FakeResolutionService:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[tuple[str, str, str, str, int, str]] = []

    def resolve(
        self,
        issue_id: str,
        draft: IssueResolutionDraft,
        expected_version: int,
        actor_context: ActorContext | None,
    ) -> DataQualityIssue:
        assert actor_context is not None
        self.calls.append(
            (
                issue_id,
                draft.root_cause,
                draft.corrective_action,
                draft.evidence_reference_id,
                expected_version,
                actor_context.actor_id,
            )
        )
        if self.error is not None:
            raise self.error
        issue = _issue(issue_id, IssueScopeType.DATASET, "dataset-a")
        return DataQualityIssue(
            **{
                **issue.__dict__,
                "status": IssueStatus.RESOLVED,
                "version": issue.version + 1,
            }
        )


class FakeVerificationService:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[tuple[str, str, str]] = []

    def record_verification_result(
        self,
        issue_id: str,
        verification_reference_id: str,
        actor_context: ActorContext | None,
    ) -> DataQualityIssue:
        assert actor_context is not None
        self.calls.append((issue_id, verification_reference_id, actor_context.actor_id))
        if self.error is not None:
            raise self.error
        issue = _issue(issue_id, IssueScopeType.DATASET, "dataset-a")
        return DataQualityIssue(
            **{
                **issue.__dict__,
                "status": IssueStatus.VERIFIED,
                "version": issue.version + 1,
            }
        )


def test_fr_070_uc_015_authorized_verifier_verifies_issue_through_bff() -> None:
    boundary = FakeBffBoundary()
    verification = FakeVerificationService()
    client = TestClient(
        _mutation_app(
            boundary,
            FakeInvestigationService(),
            verification_command=verification,
        ),
        base_url="https://app.example",
    )

    response = client.post(
        "/api/v1/issues/issue-resolved/verification",
        json={
            "version": 1,
            "verification_reference_id": "550e8400-e29b-41d4-a716-446655440000",
        },
        headers=_mutation_headers(),
    )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["item"]["status"] == "VERIFIED"
    assert response.json()["item"]["version"] == 2
    assert verification.calls == [
        (
            "issue-resolved",
            "550e8400-e29b-41d4-a716-446655440000",
            boundary.context.actor_id,
        )
    ]


def test_fr_070_verification_missing_csrf_is_rejected() -> None:
    boundary = FakeBffBoundary()
    verification = FakeVerificationService()
    client = TestClient(
        _mutation_app(
            boundary,
            FakeInvestigationService(),
            verification_command=verification,
        ),
        base_url="https://app.example",
    )
    headers = _mutation_headers()
    headers.pop(CSRF_HEADER_NAME)

    response = client.post(
        "/api/v1/issues/issue-resolved/verification",
        json={
            "version": 1,
            "verification_reference_id": "550e8400-e29b-41d4-a716-446655440000",
        },
        headers=headers,
    )

    assert response.status_code == 403
    assert verification.calls == []


def test_fr_070_verification_errors_are_classified_and_redacted() -> None:
    boundary = FakeBffBoundary()
    verification = FakeVerificationService(
        error=IssueTechnicalError("db password=unsafe", "issue-err")
    )
    response = TestClient(
        _mutation_app(
            boundary,
            FakeInvestigationService(),
            verification_command=verification,
        ),
        base_url="https://app.example",
    ).post(
        "/api/v1/issues/issue-resolved/verification",
        json={
            "version": 1,
            "verification_reference_id": "550e8400-e29b-41d4-a716-446655440000",
        },
        headers=_mutation_headers(),
    )

    assert response.status_code == 503
    assert response.json()["title"] == "Issue action temporarily unavailable"
    assert "password" not in response.text
    assert "unsafe" not in response.text


def test_development_api_supports_verification_demo() -> None:
    client = TestClient(
        create_development_app(),
        base_url="http://localhost:5173",
    )
    listed = client.get("/api/v1/issues")
    proof = listed.headers[CSRF_HEADER_NAME]
    resolved = next(
        item for item in listed.json()["items"] if "VERIFY" in item["available_actions"]
    )

    changed = client.post(
        f"/api/v1/issues/{resolved['issue_id']}/verification",
        json={
            "version": resolved["version"],
            "verification_reference_id": "550e8400-e29b-41d4-a716-446655440000",
        },
        headers={
            CSRF_HEADER_NAME: proof,
            "Origin": "http://localhost:5173",
            "Referer": "http://localhost:5173/issues",
            "Sec-Fetch-Site": "same-origin",
        },
    )

    assert changed.status_code == 200
    assert changed.json()["item"]["status"] == "VERIFIED"
    assert changed.json()["item"]["version"] == resolved["version"] + 1


def _mutation_headers() -> dict[str, str]:
    return {
        CSRF_HEADER_NAME: "test-csrf-proof",
        "Origin": "https://app.example",
        "Referer": "https://app.example/issues",
        "Sec-Fetch-Site": "same-origin",
    }
