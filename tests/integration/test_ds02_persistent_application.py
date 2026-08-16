"""DS-02 Faz A production composition persistence acceptance tests."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator
from uuid import uuid4

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, text

from veri_kalitesi.api.composition import PhaseBProviders, create_application
from veri_kalitesi.api.identity import (
    DevelopmentActorContextResolver,
    DevelopmentUser,
    DevelopmentUserRegistry,
)
from veri_kalitesi.api.models import IssueAssigneeOptionResponse
from veri_kalitesi.api.settings import ApplicationSettings
from veri_kalitesi.data_sources.secrets import InMemorySecretResolver
from veri_kalitesi.identity import ActorContext, ActorContextIssuer, ActorType
from veri_kalitesi.issues import (
    IssueAssigneeProfile,
    IssueAssignment,
    IssuePriority,
    IssueResolutionDraft,
    IssueScopeType,
    IssueTrigger,
    IssueVerificationOutcome,
    ProtectedIssueResolution,
    TrustedIssueVerificationResult,
)
from veri_kalitesi.notifications import NotificationEvent
from veri_kalitesi.persistence import DatabaseSettings
from veri_kalitesi.rules import RuleTestComputation

ROOT = Path(__file__).resolve().parents[2]
POSTGRES_TEST_URL = os.environ.get("DATA_QUALITY_POSTGRES_TEST_URL")
pytestmark = pytest.mark.skipif(
    not POSTGRES_TEST_URL,
    reason="DATA_QUALITY_POSTGRES_TEST_URL is required for DS-02 integration.",
)


@dataclass(frozen=True)
class _Fixture:
    settings: ApplicationSettings
    actor_id: str
    source_id: str
    dataset_id: str
    field_id: str
    rule_id: str
    execution_id: str
    investigation_issue_id: str
    closure_issue_id: str


class _RuleExecutor:
    def execute(self, **values: object) -> RuleTestComputation:
        return RuleTestComputation(checked_count=10, passed_count=10, failed_count=0)


class _AssigneeDirectory:
    def __init__(self, profile: IssueAssigneeProfile) -> None:
        self.profile = profile

    def get_assignee_profile(self, user_id: str) -> IssueAssigneeProfile | None:
        return self.profile if user_id == self.profile.user_id else None


class _AssignmentResolver:
    def __init__(self, user_id: str) -> None:
        self.user_id = user_id

    def resolve_assignment(self, trigger: IssueTrigger) -> IssueAssignment:
        return IssueAssignment(assignee_user_id=self.user_id, priority=IssuePriority.MEDIUM)


class _AssigneeOptions:
    def __init__(self, user_id: str) -> None:
        self.user_id = user_id

    def list_assignment_options(
        self,
        issue_id: str,
        actor_context: ActorContext | None,
    ) -> tuple[IssueAssigneeOptionResponse, ...]:
        assert actor_context is not None
        return (
            IssueAssigneeOptionResponse(
                user_id=self.user_id,
                display_name="DS-02 trusted assignee",
            ),
        )


class _ResolutionProtector:
    def protect_resolution(
        self,
        draft: IssueResolutionDraft,
    ) -> ProtectedIssueResolution:
        return ProtectedIssueResolution(
            root_cause=draft.root_cause,
            corrective_action=draft.corrective_action,
            evidence_reference_id=draft.evidence_reference_id,
            completed_at=draft.completed_at,
            protection_policy_version="DS02_EXTERNAL_PROTECTION_V1",
        )


class _VerificationResolver:
    def __init__(self, fixture: _Fixture, reference_id: str, score_id: str) -> None:
        self.fixture = fixture
        self.reference_id = reference_id
        self.score_id = score_id
        self.completed_at: datetime | None = None

    def mark_completed(self) -> None:
        self.completed_at = datetime.now(timezone.utc)

    def resolve_verification(
        self,
        verification_reference_id: str,
    ) -> TrustedIssueVerificationResult | None:
        if verification_reference_id != self.reference_id:
            return None
        assert self.completed_at is not None
        return TrustedIssueVerificationResult(
            verification_reference_id=verification_reference_id,
            execution_id=self.fixture.execution_id,
            score_id=self.score_id,
            scope_type=IssueScopeType.DATASET,
            scope_id=self.fixture.dataset_id,
            outcome=IssueVerificationOutcome.QUALITY_PASSED,
            completed_at=self.completed_at,
        )


class _NotificationPublisher:
    def __init__(self) -> None:
        self.events: list[NotificationEvent] = []

    def create_for_event(
        self,
        event: NotificationEvent,
        actor_context: ActorContext | None,
    ) -> tuple[object, ...]:
        assert actor_context is not None
        self.events.append(event)
        return (event,)


@dataclass(frozen=True)
class _PhaseBFixture:
    providers: PhaseBProviders
    assignee_id: str
    verifier_id: str
    verification_reference_id: str
    verification_resolver: _VerificationResolver
    publisher: _NotificationPublisher


@pytest.fixture
def ds02() -> Iterator[_Fixture]:
    assert POSTGRES_TEST_URL is not None
    schema = f"test_ds02_{uuid4().hex[:10]}"
    database = DatabaseSettings.from_url(POSTGRES_TEST_URL, schema=schema)
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database.url.render_as_string(hide_password=False))
    config.set_main_option("data_quality_schema", schema)
    command.upgrade(config, "head")

    fixture = _Fixture(
        settings=ApplicationSettings(
            runtime_environment="test",
            database=database,
            allowed_origins=("https://dq.test",),
            audit_policy_version="DS02_AUDIT_V1",
            issue_policy_version="DS02_ISSUE_V1",
            actor_policy_version="DS02_ACTOR_V1",
        ),
        actor_id="development-dashboard-user",
        source_id=str(uuid4()),
        dataset_id=str(uuid4()),
        field_id=str(uuid4()),
        rule_id=str(uuid4()),
        execution_id=str(uuid4()),
        investigation_issue_id=str(uuid4()),
        closure_issue_id=str(uuid4()),
    )
    _seed(fixture)
    yield fixture

    engine = create_engine(database.url)
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
    engine.dispose()


def test_ds02_ac_queries_survive_application_reconstruction(ds02: _Fixture) -> None:
    first_app = _app(ds02)
    with TestClient(first_app, base_url="https://dq.test") as client:
        assert _ids(client.get("/api/v1/rules"), "quality_rule_id") == {ds02.rule_id}
        assert _ids(client.get("/api/v1/issues"), "issue_id") == {
            ds02.investigation_issue_id,
            ds02.closure_issue_id,
        }
        assert _ids(client.get("/api/v1/executions"), "execution_id") == {ds02.execution_id}
    _dispose(first_app)

    reconstructed_app = _app(ds02)
    with TestClient(reconstructed_app, base_url="https://dq.test") as client:
        assert _ids(client.get("/api/v1/rules"), "quality_rule_id") == {ds02.rule_id}
        assert _ids(client.get("/api/v1/issues"), "issue_id") == {
            ds02.investigation_issue_id,
            ds02.closure_issue_id,
        }
        assert _ids(client.get("/api/v1/executions"), "execution_id") == {ds02.execution_id}
        for response in (
            client.get("/api/v1/rules"),
            client.get("/api/v1/issues"),
            client.get("/api/v1/executions"),
        ):
            assert response.json()["data_origin"] == "postgresql-runtime"
    _dispose(reconstructed_app)


def test_ds02_ac_investigation_and_closure_persist_with_real_audit(ds02: _Fixture) -> None:
    app = _app(ds02)
    headers = {
        "Origin": "https://dq.test",
        "Referer": "https://dq.test/issues",
        "Sec-Fetch-Site": "same-origin",
        "X-CSRF-Token": "development-request-proof-v1",
    }
    with TestClient(app, base_url="https://dq.test") as client:
        investigated = client.post(
            f"/api/v1/issues/{ds02.investigation_issue_id}/investigation",
            json={"version": 1},
            headers=headers,
        )
        closed = client.post(
            f"/api/v1/issues/{ds02.closure_issue_id}/closure",
            json={"version": 1},
            headers=headers,
        )

        assert investigated.status_code == 200, investigated.text
        assert investigated.json()["item"]["status"] == "INVESTIGATING"
        assert closed.status_code == 200, closed.text
        assert closed.json()["item"]["status"] == "CLOSED"

        investigation_audit = client.get(
            "/api/v1/audit/events",
            params={"action": "DATA_QUALITY_ISSUE_STATUS_CHANGED"},
        )
        closure_audit = client.get(
            "/api/v1/audit/events",
            params={"action": "DATA_QUALITY_ISSUE_CLOSED"},
        )
        assert investigation_audit.status_code == 200
        assert closure_audit.status_code == 200
        assert {item["object_id"] for item in investigation_audit.json()["items"]} == {
            ds02.investigation_issue_id
        }
        assert {item["object_id"] for item in closure_audit.json()["items"]} == {
            ds02.closure_issue_id
        }
    _dispose(app)

    reconstructed_app = _app(ds02)
    with TestClient(reconstructed_app, base_url="https://dq.test") as client:
        statuses = {
            item["issue_id"]: item["status"]
            for item in client.get("/api/v1/issues").json()["items"]
        }
        assert statuses[ds02.investigation_issue_id] == "INVESTIGATING"
        assert statuses[ds02.closure_issue_id] == "CLOSED"
    _dispose(reconstructed_app)


def test_ds02_phase_b_rule_commands_use_trusted_scope_and_persist(
    ds02: _Fixture,
) -> None:
    phase_b = _phase_b(ds02)
    app = _app(ds02, phase_b_providers=phase_b.providers)
    headers = _mutation_headers()
    with TestClient(app, base_url="https://dq.test") as client:
        created = client.post(
            "/api/v1/rules",
            json={
                "code": f"DS02B_{uuid4().hex[:10]}",
                "name": "DS-02 Phase B rule",
                "dataset_id": ds02.dataset_id,
                "rule_type": "REQUIRED",
                "primary_dimension": "COMPLETENESS",
                "threshold": 90,
                "weight": 1,
                "criticality": "MEDIUM",
                "owner_user_id": ds02.actor_id,
                "parameters": {"field_id": ds02.field_id},
            },
            headers=headers,
        )
        assert created.status_code == 201, created.text
        rule_id = created.json()["item"]["quality_rule_id"]
        versioned = client.post(
            f"/api/v1/rules/{rule_id}/versions",
            json={
                "threshold": 95,
                "weight": 1,
                "criticality": "MEDIUM",
                "parameters": {"field_id": ds02.field_id},
            },
            headers=headers,
        )
        assert versioned.status_code == 201, versioned.text
        version_id = versioned.json()["item"]["rule_version_id"]

        tested = client.post(
            f"/api/v1/rules/{rule_id}/test",
            json={"rule_version_id": version_id, "limit": 100},
            headers=headers,
        )
        activated = client.post(
            f"/api/v1/rules/{rule_id}/activation",
            json={"quality_rule_id": rule_id},
            headers=headers,
        )
        assert tested.status_code == 201, tested.text
        assert tested.json()["status"] == "SUCCESS"
        assert activated.status_code == 200, activated.text
        assert activated.json()["item"]["status"] == "ACTIVE"
        passivated = client.post(
            f"/api/v1/rules/{rule_id}/passivation",
            json={"quality_rule_id": rule_id},
            headers=headers,
        )
        assert passivated.status_code == 200, passivated.text
        assert passivated.json()["item"]["status"] == "PASSIVE"
    _dispose(app)

    reconstructed = _app(ds02, phase_b_providers=_phase_b(ds02).providers)
    with TestClient(reconstructed, base_url="https://dq.test") as client:
        rules = client.get("/api/v1/rules").json()["items"]
        assert (
            next(item for item in rules if item["quality_rule_id"] == rule_id)["status"]
            == "PASSIVE"
        )
    _dispose(reconstructed)


def test_ds02_phase_b_assignment_uses_trusted_directory_and_notification(
    ds02: _Fixture,
) -> None:
    phase_b = _phase_b(ds02)
    registry = _phase_b_users(ds02, phase_b.verifier_id)
    app = _app(
        ds02,
        phase_b_providers=phase_b.providers,
        user_registry=registry,
    )
    with TestClient(app, base_url="https://dq.test") as client:
        options = client.get(f"/api/v1/issues/{ds02.investigation_issue_id}/assignment-options")
        assert options.status_code == 200
        assert options.json()["items"][0]["user_id"] == phase_b.assignee_id

        reassigned = client.post(
            f"/api/v1/issues/{ds02.investigation_issue_id}/assignment",
            json={
                "version": 1,
                "assignee_user_id": phase_b.assignee_id,
                "priority": "CRITICAL",
            },
            headers=_mutation_headers(),
        )
        assert reassigned.status_code == 200, reassigned.text
        assert reassigned.json()["item"]["priority"] == "CRITICAL"
        assert len(phase_b.publisher.events) == 1
    _dispose(app)


def test_ds02_phase_b_critical_rule_maker_checker_chain(ds02: _Fixture) -> None:
    phase_b = _phase_b(ds02)
    app = _app(
        ds02,
        phase_b_providers=phase_b.providers,
        user_registry=_phase_b_users(ds02, phase_b.verifier_id),
    )
    with TestClient(app, base_url="https://dq.test") as client:
        created = client.post(
            "/api/v1/rules",
            json={
                "code": f"DS02C_{uuid4().hex[:10]}",
                "name": "DS-02 critical rule",
                "dataset_id": ds02.dataset_id,
                "rule_type": "REQUIRED",
                "primary_dimension": "COMPLETENESS",
                "threshold": 99,
                "weight": 1,
                "criticality": "CRITICAL",
                "owner_user_id": phase_b.verifier_id,
                "parameters": {"field_id": ds02.field_id},
            },
            headers=_mutation_headers(),
        )
        assert created.status_code == 201, created.text
        rule_id = created.json()["item"]["quality_rule_id"]
        version_id = created.json()["item"]["rule_version_id"]
        tested = client.post(
            f"/api/v1/rules/{rule_id}/test",
            json={"rule_version_id": version_id, "limit": 100},
            headers=_mutation_headers(),
        )
        requested = client.post(
            f"/api/v1/rules/{rule_id}/approval",
            json={"quality_rule_id": rule_id},
            headers=_mutation_headers(),
        )
        assert tested.status_code == 201, tested.text
        assert requested.status_code == 201, requested.text
        approval_id = requested.json()["item"]["pending_approval_request_id"]
        assert approval_id
        decided = client.post(
            f"/api/v1/rules/approval/{approval_id}/decide",
            json={
                "approval_request_id": approval_id,
                "decision": "APPROVE",
                "reason_code": "DS02_VERIFIED",
            },
            headers=_mutation_headers(phase_b.verifier_id),
        )
        assert decided.status_code == 200, decided.text
        assert decided.json()["item"]["status"] == "ACTIVE"
    _dispose(app)


def test_ds02_phase_b_resolution_verification_and_closure_are_persistent(
    ds02: _Fixture,
) -> None:
    phase_b = _phase_b(ds02)
    registry = _phase_b_users(ds02, phase_b.verifier_id)
    app = _app(
        ds02,
        phase_b_providers=phase_b.providers,
        user_registry=registry,
    )
    with TestClient(app, base_url="https://dq.test") as client:
        investigated = client.post(
            f"/api/v1/issues/{ds02.investigation_issue_id}/investigation",
            json={"version": 1},
            headers=_mutation_headers(),
        )
        resolved = client.post(
            f"/api/v1/issues/{ds02.investigation_issue_id}/resolution",
            json={
                "version": 2,
                "root_cause": "Upstream completeness regression",
                "corrective_action": "Source validation restored",
                "evidence_reference_id": str(uuid4()),
                "completed_at": datetime.now(timezone.utc).isoformat(),
            },
            headers=_mutation_headers(),
        )
        phase_b.verification_resolver.mark_completed()
        verified = client.post(
            f"/api/v1/issues/{ds02.investigation_issue_id}/verification",
            json={
                "version": 3,
                "verification_reference_id": phase_b.verification_reference_id,
            },
            headers=_mutation_headers(phase_b.verifier_id),
        )
        closed = client.post(
            f"/api/v1/issues/{ds02.investigation_issue_id}/closure",
            json={"version": 4},
            headers=_mutation_headers(phase_b.verifier_id),
        )
        assert investigated.status_code == 200, investigated.text
        assert resolved.status_code == 200, resolved.text
        assert verified.status_code == 200, verified.text
        assert closed.status_code == 200, closed.text
        assert closed.json()["item"]["status"] == "CLOSED"
    _dispose(app)


def test_ds02_ac_issue_mutation_fails_closed_outside_dataset_scope(
    ds02: _Fixture,
) -> None:
    denied_app = _app(ds02, permitted_dataset_ids=frozenset())
    headers = {
        "Origin": "https://dq.test",
        "Referer": "https://dq.test/issues",
        "Sec-Fetch-Site": "same-origin",
        "X-CSRF-Token": "development-request-proof-v1",
    }
    with TestClient(denied_app, base_url="https://dq.test") as client:
        denied = client.post(
            f"/api/v1/issues/{ds02.investigation_issue_id}/investigation",
            json={"version": 1},
            headers=headers,
        )
        assert denied.status_code == 403
    _dispose(denied_app)

    authorized_app = _app(ds02)
    with TestClient(authorized_app, base_url="https://dq.test") as client:
        issue = next(
            item
            for item in client.get("/api/v1/issues").json()["items"]
            if item["issue_id"] == ds02.investigation_issue_id
        )
        audit = client.get(
            "/api/v1/audit/events",
            params={"action": "DATA_QUALITY_ISSUE_STATUS_CHANGED"},
        )
        assert issue["status"] == "ASSIGNED"
        assert audit.status_code == 200
        assert audit.json()["items"] == []
    _dispose(authorized_app)


def _phase_b(fixture: _Fixture) -> _PhaseBFixture:
    assignee_id = str(uuid4())
    verifier_id = "ds02-independent-verifier"
    verification_reference_id = str(uuid4())
    publisher = _NotificationPublisher()
    verification_resolver = _VerificationResolver(
        fixture,
        verification_reference_id,
        str(uuid4()),
    )
    directory = _AssigneeDirectory(
        IssueAssigneeProfile(
            user_id=assignee_id,
            active=True,
            permitted_source_ids=frozenset({fixture.source_id}),
            permitted_dataset_ids=frozenset({fixture.dataset_id}),
        )
    )
    return _PhaseBFixture(
        providers=PhaseBProviders(
            rule_test_executor=_RuleExecutor(),
            issue_assignee_directory=directory,
            issue_assignment_resolver=_AssignmentResolver(assignee_id),
            issue_assignee_option_provider=_AssigneeOptions(assignee_id),
            issue_resolution_protector=_ResolutionProtector(),
            issue_verification_resolver=verification_resolver,
            issue_notification_publisher=publisher,
            issue_notification_actor_context_provider=lambda: _service_actor(fixture),
        ),
        assignee_id=assignee_id,
        verifier_id=verifier_id,
        verification_reference_id=verification_reference_id,
        verification_resolver=verification_resolver,
        publisher=publisher,
    )


def _phase_b_users(
    fixture: _Fixture,
    verifier_id: str,
) -> DevelopmentUserRegistry:
    return DevelopmentUserRegistry(
        [
            DevelopmentUser(
                user_id=verifier_id,
                display_name="DS-02 independent verifier",
                roles=frozenset({"DATA_VIEWER", "DATA_OWNER"}),
                permitted_source_ids=frozenset({fixture.source_id}),
                permitted_dataset_ids=frozenset({fixture.dataset_id}),
            )
        ]
    )


def _service_actor(fixture: _Fixture) -> ActorContext:
    issued_at = datetime.now(timezone.utc)
    return ActorContextIssuer().issue(
        actor_id="ds02-notification-service",
        actor_type=ActorType.SERVICE,
        authentication_source="ds02-production-boundary-test",
        session_id="ds02-notification-session",
        roles=frozenset({"NOTIFICATION_PRODUCER"}),
        permitted_source_ids=frozenset({fixture.source_id}),
        permitted_dataset_ids=frozenset({fixture.dataset_id}),
        can_view_enterprise=False,
        privileged=False,
        issued_at=issued_at,
        expires_at=issued_at + timedelta(minutes=5),
        policy_version=fixture.settings.actor_policy_version,
        correlation_id="ds02-notification",
    )


def _mutation_headers(user_id: str | None = None) -> dict[str, str]:
    headers = {
        "Origin": "https://dq.test",
        "Referer": "https://dq.test/issues",
        "Sec-Fetch-Site": "same-origin",
        "X-CSRF-Token": "development-request-proof-v1",
    }
    if user_id is not None:
        headers["X-Development-User-Id"] = user_id
    return headers


def _app(
    fixture: _Fixture,
    *,
    permitted_dataset_ids: frozenset[str] | None = None,
    phase_b_providers: PhaseBProviders | None = None,
    user_registry: DevelopmentUserRegistry | None = None,
):
    resolver = DevelopmentActorContextResolver(
        runtime_environment="development",
        policy_version=fixture.settings.actor_policy_version,
        permitted_source_ids=frozenset({fixture.source_id}),
        permitted_dataset_ids=(
            frozenset({fixture.dataset_id})
            if permitted_dataset_ids is None
            else permitted_dataset_ids
        ),
        roles=frozenset({"DATA_VIEWER", "DATA_STEWARD", "AUDIT_VIEWER"}),
        allowed_origins=frozenset(fixture.settings.allowed_origins),
        can_view_enterprise=False,
        user_registry=user_registry,
    )
    return create_application(
        fixture.settings,
        resolver,
        secret_resolver=InMemorySecretResolver({}),
        development_user_registry=user_registry,
        phase_b_providers=phase_b_providers,
    )


def _dispose(app: object) -> None:
    session_factory = getattr(getattr(app, "state"), "session_factory")
    engine = session_factory.kw.get("bind")
    if engine is not None:
        engine.dispose()


def _ids(response: object, field: str) -> set[str]:
    assert getattr(response, "status_code") == 200
    payload = getattr(response, "json")()
    return {item[field] for item in payload["items"]}


def _seed(fixture: _Fixture) -> None:
    engine = create_engine(fixture.settings.database.url)
    schema = fixture.settings.database.schema
    now = datetime.now(timezone.utc)
    verification_id = str(uuid4())
    with engine.begin() as connection:
        connection.execute(
            text(
                f'''INSERT INTO "{schema}".data_sources
                    (data_source_id, name, source_type, connection_config,
                     secret_reference, owner_user_id, status, revision,
                     last_test_at, created_at)
                    VALUES (:source_id, :name, 'POSTGRESQL', CAST(:config AS json),
                            'secret://ds02/source', :actor_id, 'ACTIVE', 1,
                            :now, :now)'''
            ),
            {
                "source_id": fixture.source_id,
                "name": f"DS-02 source {fixture.source_id}",
                "config": json.dumps(
                    {
                        "host": "ds02.example",
                        "port": 5432,
                        "database": "ds02",
                        "ssl_mode": "verify-full",
                    }
                ),
                "actor_id": fixture.actor_id,
                "now": now,
            },
        )
        connection.execute(
            text(
                f'''INSERT INTO "{schema}".datasets
                    (dataset_id, data_source_id, namespace, name, dataset_type,
                     criticality, owner_user_id, estimated_row_count)
                    VALUES (:dataset_id, :source_id, 'public', :name, 'TABLE',
                            'HIGH', :actor_id, 100)'''
            ),
            {
                "dataset_id": fixture.dataset_id,
                "source_id": fixture.source_id,
                "name": f"ds02_{fixture.dataset_id.replace('-', '')[:12]}",
                "actor_id": fixture.actor_id,
            },
        )
        connection.execute(
            text(
                f'''INSERT INTO "{schema}".data_fields
                    (data_field_id, dataset_id, name, native_data_type,
                     is_nullable, is_sensitive, classification,
                     classification_policy_version)
                    VALUES (:field_id, :dataset_id, 'customer_id', 'TEXT',
                            false, false, 'INTERNAL', 'DS02_CLASSIFICATION_V1')'''
            ),
            {"field_id": fixture.field_id, "dataset_id": fixture.dataset_id},
        )
        connection.execute(
            text(
                f'''INSERT INTO "{schema}".quality_rules
                    (quality_rule_id, code, name, dataset_id, field_ids,
                     primary_dimension, owner_user_id, status)
                    VALUES (:rule_id, :code, 'DS-02 rule', :dataset_id,
                            CAST(:field_ids AS json), 'COMPLETENESS', :actor_id, 'DRAFT')'''
            ),
            {
                "rule_id": fixture.rule_id,
                "code": f"DS02_{fixture.rule_id.replace('-', '')[:12]}",
                "dataset_id": fixture.dataset_id,
                "field_ids": json.dumps([]),
                "actor_id": fixture.actor_id,
            },
        )
        connection.execute(
            text(
                f'''INSERT INTO "{schema}".rule_versions
                    (rule_version_id, quality_rule_id, version_no, rule_type,
                     definition, threshold, weight, criticality,
                     prepared_by_actor_id, created_at)
                    VALUES (:version_id, :rule_id, 1, 'REQUIRED',
                            CAST(:definition AS json), 0.9, 1.0, 'HIGH',
                            :actor_id, :now)'''
            ),
            {
                "version_id": str(uuid4()),
                "rule_id": fixture.rule_id,
                "definition": json.dumps(
                    {
                        "ir_version": "DQ_RULE_IR_V1",
                        "definition_source": "TEMPLATE",
                        "scope_type": "DATASET",
                    }
                ),
                "actor_id": fixture.actor_id,
                "now": now,
            },
        )
        for issue_id, status in (
            (fixture.investigation_issue_id, "ASSIGNED"),
            (fixture.closure_issue_id, "VERIFIED"),
        ):
            connection.execute(
                text(
                    f'''INSERT INTO "{schema}".data_quality_issues
                        (issue_id, issue_no, title, source_event_id, source_event_type,
                         trigger_type, scope_type, scope_id, status, priority,
                         assignee_user_id, deduplication_key_digest, payload_digest,
                         occurrence_count, version, created_at, updated_at, last_seen_at)
                        VALUES (:issue_id, :issue_no, :title, :event_id, 'QUALITY',
                                'QUALITY_THRESHOLD', 'DATASET', :dataset_id, :status,
                                'HIGH', :actor_id, :dedup, :payload, 1, 1,
                                :now, :now, :now)'''
                ),
                {
                    "issue_id": issue_id,
                    "issue_no": f"DQI-{issue_id.replace('-', '')[:12].upper()}",
                    # title migration 18'de NOT NULL oldu; fixture guncellenmemisti.
                    "title": f"DQI-{issue_id.replace('-', '')[:12].upper()}",
                    "event_id": str(uuid4()),
                    "dataset_id": fixture.dataset_id,
                    "status": status,
                    "actor_id": fixture.actor_id,
                    "dedup": uuid4().hex,
                    "payload": uuid4().hex,
                    "now": now,
                },
            )
        connection.execute(
            text(
                f'''INSERT INTO "{schema}".issue_verifications
                    (verification_id, issue_id, verification_reference_id,
                     execution_id, score_id, scope_type, scope_id, outcome,
                     completed_at, recorded_by, recorded_at)
                    VALUES (:verification_id, :issue_id, :reference_id,
                            :execution_id, :score_id, 'DATASET', :dataset_id,
                            'QUALITY_PASSED', :now, :recorded_by, :now)'''
            ),
            {
                "verification_id": verification_id,
                "issue_id": fixture.closure_issue_id,
                "reference_id": str(uuid4()),
                "execution_id": str(uuid4()),
                "score_id": str(uuid4()),
                "dataset_id": fixture.dataset_id,
                "recorded_by": str(uuid4()),
                "now": now,
            },
        )
        connection.execute(
            text(
                f'''INSERT INTO "{schema}".rule_executions
                    (execution_id, execution_type, status, idempotency_key_hash,
                     payload_hash, rule_version_ids, scope, triggered_by,
                     correlation_id, source_ids, workload_class, execution_mode,
                     attempt_count, created_at)
                    VALUES (:execution_id, 'MANUAL', 'QUEUED', :idempotency_hash,
                            :payload_hash, CAST(:rule_versions AS json),
                            CAST(:scope AS json), :actor_id, :correlation_id,
                            CAST(:source_ids AS json), 'LIGHT', 'OFFICIAL', 0, :now)'''
            ),
            {
                "execution_id": fixture.execution_id,
                "idempotency_hash": uuid4().hex + uuid4().hex,
                "payload_hash": uuid4().hex + uuid4().hex,
                "rule_versions": json.dumps([]),
                "scope": json.dumps({}),
                "actor_id": fixture.actor_id,
                "correlation_id": str(uuid4()),
                "source_ids": json.dumps([fixture.source_id]),
                "now": now,
            },
        )
    engine.dispose()
