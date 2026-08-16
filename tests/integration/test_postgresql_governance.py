"""Yönetişim görev merkezi PostgreSQL entegrasyon testi.

Gerçek PostgreSQLRuleRepository ve PostgreSQLDataSourceRepository üzerinden
ortak görev merkezinin her iki domain talebini tek biçimde listelediğini ve
kapsam dışı kayıtları fail-closed elediğini kanıtlar.

DATA_QUALITY_POSTGRES_TEST_URL gerektirir; set edilmemisse atlanir.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, insert, text

from veri_kalitesi.audit.models import (
    AuditEventInput,
    AuditFailureMode,
    AuditFailurePolicy,
    AuditRedactionPolicy,
    AuditResult,
    PreparedAuditEvent,
)
from veri_kalitesi.audit.policies import build_default_redaction_policy
from veri_kalitesi.audit.postgresql_outbox import PostgreSQLTransactionalAudit
from veri_kalitesi.audit.redaction import AuditRedactor
from veri_kalitesi.audit.repository import SQLiteAuditRepository
from veri_kalitesi.audit.service import AuditService
from veri_kalitesi.data_protection.policy import ClassificationCode
from veri_kalitesi.data_sources.models import (
    Criticality,
    DataField,
    DataSource,
    DataSourceActivationRequest,
    Dataset,
    SourceType,
)
from veri_kalitesi.data_sources.postgresql_repository import (
    PostgreSQLDataSourceRepository,
)
from veri_kalitesi.governance import GovernanceApprovalQueryService, GovernanceView
from veri_kalitesi.governance.errors import (
    GovernanceConflictError,
    GovernanceValidationError,
)
from veri_kalitesi.governance.models import (
    GovernanceApprovalPolicy,
    GovernanceApprovalRequest,
    GovernanceApprovalStatus,
    GovernanceRequestType,
)
from veri_kalitesi.governance.repository import PostgreSQLGovernanceApprovalRepository
from veri_kalitesi.governance.service import (
    GovernanceApprovalCommandService,
    PostgreSQLDatasetOwnershipWriter,
    PostgreSQLMetadataGovernanceWriter,
)
from veri_kalitesi.identity import (
    ActorContextIssuer,
    ActorType,
    DashboardAuthorizationPolicy,
    PolicyAuthorizationService,
)
from veri_kalitesi.persistence import DatabaseSettings, SessionFactory, create_session_factory
from veri_kalitesi.rules import QualityDimension, QualityRule, RuleCriticality, RuleType
from veri_kalitesi.rules.models import RuleApprovalRequest, RuleStatus, RuleVersion
from veri_kalitesi.rules.postgresql_repository import PostgreSQLRuleRepository

POSTGRES_TEST_URL = os.environ.get("DATA_QUALITY_POSTGRES_TEST_URL")
pytestmark = pytest.mark.skipif(
    not POSTGRES_TEST_URL,
    reason="DATA_QUALITY_POSTGRES_TEST_URL is required for governance integration.",
)
ROOT = Path(__file__).resolve().parents[2]
ACTOR_POLICY_VERSION = "GOVERNANCE_INTEGRATION_POLICY_V1"
NOW = datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc)


@dataclass
class PgFixture:
    session_factory: SessionFactory
    schema: str
    engine: Any


@pytest.fixture
def pg() -> Iterator[PgFixture]:
    settings = DatabaseSettings.from_url(
        POSTGRES_TEST_URL,
        schema=f"test_governance_{uuid4().hex[:8]}",
    )
    session_factory = create_session_factory(settings)
    engine = create_engine(settings.url)
    alembic_cfg = Config(str(ROOT / "alembic.ini"))
    alembic_cfg.set_main_option(
        "sqlalchemy.url", settings.url.render_as_string(hide_password=False)
    )
    alembic_cfg.set_main_option("data_quality_schema", settings.schema)
    command.upgrade(alembic_cfg, "head")
    yield PgFixture(
        session_factory=session_factory,
        schema=settings.schema,
        engine=engine,
    )
    with engine.begin() as conn:
        conn.execute(text(f'DROP SCHEMA IF EXISTS "{settings.schema}" CASCADE'))
    engine.dispose()


def _audit(pg: PgFixture) -> PostgreSQLTransactionalAudit:
    from conftest import FakePreparedAuditRepository  # type: ignore[import-untyped]

    return PostgreSQLTransactionalAudit(
        pg.session_factory,
        AuditRedactor(build_default_redaction_policy()),
        FakePreparedAuditRepository(),
        policy_version="TEST_V1",
        schema=pg.schema,
    )


def _prepared(audit: PostgreSQLTransactionalAudit, **overrides: Any) -> PreparedAuditEvent:
    return audit.prepare(
        AuditEventInput(
            actor_id="test-actor",
            actor_type="USER",
            correlation_id="test-correlation",
            action=overrides.get("action", "GOVERNANCE_TEST"),
            object_type=overrides.get("object_type", "QualityRule"),
            object_id=overrides.get("object_id", str(uuid4())),
            result=AuditResult.SUCCESS,
            reason_code="TEST",
            old_values={},
            new_values={"test": True},
            occurred_at=NOW,
            session_id=None,
        )
    )


def _actor_context(
    permitted_dataset_ids: frozenset[str],
    permitted_source_ids: frozenset[str],
    *,
    actor_id: str = "checker-1",
    roles: frozenset[str] = frozenset({"DATA_OWNER"}),
):
    return ActorContextIssuer().issue(
        actor_id=actor_id,
        actor_type=ActorType.USER,
        authentication_source="synthetic-identity-adapter",
        session_id=f"session-{actor_id}",
        roles=roles,
        permitted_source_ids=permitted_source_ids,
        permitted_dataset_ids=permitted_dataset_ids,
        can_view_enterprise=False,
        privileged=False,
        issued_at=NOW - timedelta(minutes=5),
        expires_at=NOW + timedelta(hours=1),
        policy_version=ACTOR_POLICY_VERSION,
        correlation_id="correlation-checker",
    )


def _authorization() -> PolicyAuthorizationService:
    audit_service = AuditService(
        SQLiteAuditRepository(),
        AuditRedactor(
            AuditRedactionPolicy(
                version="GOVERNANCE_INTEGRATION_REDACTION_V1",
                allowed_fields_by_action={},
            )
        ),
        AuditFailurePolicy("GOVERNANCE_INTEGRATION_AUDIT_V1", AuditFailureMode.FAIL_CLOSED),
    )
    return PolicyAuthorizationService(
        DashboardAuthorizationPolicy(version=ACTOR_POLICY_VERSION),
        audit_service,
        clock=lambda: NOW,
    )


def test_governance_center_lists_rule_and_source_requests(pg: PgFixture) -> None:
    rule_repo = PostgreSQLRuleRepository(pg.session_factory, schema=pg.schema)
    source_repo = PostgreSQLDataSourceRepository(pg.session_factory, schema=pg.schema)
    audit = _audit(pg)

    # Kural + bekleyen onay talebi
    rule = QualityRule(
        quality_rule_id=str(uuid4()),
        code="GOV-RULE",
        name="Governance Rule",
        dataset_id="dataset-gov",
        field_ids=(),
        primary_dimension=QualityDimension.COMPLETENESS,
        owner_user_id="owner-1",
        status=RuleStatus.DRAFT,
    )
    version = RuleVersion(
        quality_rule_id=rule.quality_rule_id,
        version_no=1,
        rule_type=RuleType.REQUIRED,
        definition={"field_id": "f"},
        threshold=90.0,
        weight=1.0,
        criticality=RuleCriticality.CRITICAL,
        prepared_by_actor_id="maker-1",
        created_at=NOW,
    )
    rule_repo.add_rule_with_version(
        rule,
        version,
        audit_event=_prepared(audit, object_id=rule.quality_rule_id),
        audit_outbox=audit,
    )
    rule_request = RuleApprovalRequest(
        rule_version_id=version.rule_version_id,
        maker_actor_id="maker-1",
        policy_version="RULE_POLICY_V1",
        requested_at=NOW - timedelta(hours=1),
    )
    rule_repo.add_approval_request(
        rule_request,
        audit_event=_prepared(audit, object_id=rule.quality_rule_id),
        audit_outbox=audit,
    )

    # Veri kaynağı + bekleyen aktivasyon talebi
    source = DataSource(
        data_source_id=str(uuid4()),
        name="Governance Source",
        source_type=SourceType.POSTGRESQL,
        connection_config={},
        secret_reference="secret-gov",
    )
    source_repo.add_data_source(
        source,
        audit_event=_prepared(audit, object_type="DataSource", object_id=source.data_source_id),
        audit_outbox=audit,
    )
    source_request = DataSourceActivationRequest(
        data_source_id=source.data_source_id,
        data_source_revision=1,
        maker_actor_id="maker-2",
        policy_version="SOURCE_POLICY_V1",
        requested_at=NOW,
        request_type="ACTIVATION",
    )
    source_repo.add_activation_request(
        source_request,
        audit_event=_prepared(audit, object_type="DataSource", object_id=source.data_source_id),
        audit_outbox=audit,
    )

    service = GovernanceApprovalQueryService(rule_repo, source_repo, _authorization())
    context = _actor_context(
        permitted_dataset_ids=frozenset({"dataset-gov"}),
        permitted_source_ids=frozenset({source.data_source_id}),
    )

    items = service.list_for_actor(context, view=GovernanceView.ALL)
    assert len(items) == 2
    domains = {item.domain.value for item in items}
    assert domains == {"QUALITY_RULE", "DATA_SOURCE"}
    assert all(item.status.value == "PENDING" for item in items)

    rule_item = next(item for item in items if item.domain.value == "QUALITY_RULE")
    assert rule_item.object_id == rule.quality_rule_id
    assert rule_item.scope_id == "dataset-gov"
    source_item = next(item for item in items if item.domain.value == "DATA_SOURCE")
    assert source_item.object_id == source.data_source_id
    assert source_item.request_type.value == "SOURCE_ACTIVATION"


def test_governance_center_hides_out_of_scope_requests(pg: PgFixture) -> None:
    rule_repo = PostgreSQLRuleRepository(pg.session_factory, schema=pg.schema)
    source_repo = PostgreSQLDataSourceRepository(pg.session_factory, schema=pg.schema)
    audit = _audit(pg)

    rule = QualityRule(
        quality_rule_id=str(uuid4()),
        code="GOV-RULE-2",
        name="Out Of Scope Rule",
        dataset_id="dataset-hidden",
        field_ids=(),
        primary_dimension=QualityDimension.COMPLETENESS,
        owner_user_id="owner-1",
        status=RuleStatus.DRAFT,
    )
    version = RuleVersion(
        quality_rule_id=rule.quality_rule_id,
        version_no=1,
        rule_type=RuleType.REQUIRED,
        definition={"field_id": "f"},
        threshold=90.0,
        weight=1.0,
        criticality=RuleCriticality.CRITICAL,
        prepared_by_actor_id="maker-1",
        created_at=NOW,
    )
    rule_repo.add_rule_with_version(
        rule,
        version,
        audit_event=_prepared(audit, object_id=rule.quality_rule_id),
        audit_outbox=audit,
    )
    rule_repo.add_approval_request(
        RuleApprovalRequest(
            rule_version_id=version.rule_version_id,
            maker_actor_id="maker-1",
            policy_version="RULE_POLICY_V1",
            requested_at=NOW,
        ),
        audit_event=_prepared(audit, object_id=rule.quality_rule_id),
        audit_outbox=audit,
    )

    service = GovernanceApprovalQueryService(rule_repo, source_repo, _authorization())
    context = _actor_context(
        permitted_dataset_ids=frozenset({"dataset-visible"}),
        permitted_source_ids=frozenset(),
    )

    assert service.list_for_actor(context, view=GovernanceView.ALL) == ()


def _ownership_service(pg: PgFixture, governance_repo=None):
    source_repo = PostgreSQLDataSourceRepository(pg.session_factory, schema=pg.schema)
    governance_repo = governance_repo or PostgreSQLGovernanceApprovalRepository(
        pg.session_factory, schema=pg.schema
    )
    audit = _audit(pg)

    class _NoopAuditSink:
        def append(self, event: AuditEventInput) -> None:
            del event

    policy = GovernanceApprovalPolicy(
        version="GOVERNANCE_APPROVAL_POLICY_V1",
        actor_policy_version=ACTOR_POLICY_VERSION,
        maker_roles=frozenset({"DATA_STEWARD"}),
        checker_roles=frozenset({"DATA_OWNER"}),
        applier_roles=frozenset({"DATA_GOVERNANCE_SPECIALIST"}),
    )
    command_service = GovernanceApprovalCommandService(
        governance_repo,
        source_repo,
        PostgreSQLDatasetOwnershipWriter(source_repo),
        audit_sink=_NoopAuditSink(),
        transactional_audit=audit,
        policy=policy,
        metadata_writer=PostgreSQLMetadataGovernanceWriter(source_repo),
        clock=lambda: NOW,
    )
    return command_service, source_repo, governance_repo


def _seed_dataset(pg: PgFixture, source_repo, *, owner: str | None) -> Dataset:
    source = DataSource(
        data_source_id=str(uuid4()),
        name="Ownership Source",
        source_type=SourceType.POSTGRESQL,
        connection_config={},
        secret_reference="secret-ownership",
    )
    audit = _audit(pg)
    source_repo.add_data_source(
        source,
        audit_event=_prepared(audit, object_type="DataSource", object_id=source.data_source_id),
        audit_outbox=audit,
    )
    dataset = Dataset(
        data_source_id=source.data_source_id,
        namespace="core",
        name="ownership-table",
        owner_user_id=owner,
        dataset_id=str(uuid4()),
    )
    from veri_kalitesi.persistence import transactional_session

    with transactional_session(pg.session_factory) as session:
        session.execute(
            insert(source_repo.tables.datasets).values(
                dataset_id=dataset.dataset_id,
                data_source_id=dataset.data_source_id,
                namespace=dataset.namespace,
                name=dataset.name,
                dataset_type=dataset.dataset_type.value,
                criticality=dataset.criticality.value,
                owner_user_id=dataset.owner_user_id,
                estimated_row_count=None,
            )
        )
    return source_repo.get_dataset(dataset.dataset_id)


def _seed_field(pg: PgFixture, source_repo, dataset: Dataset) -> DataField:
    from veri_kalitesi.persistence import transactional_session

    field_id = str(uuid4())
    with transactional_session(pg.session_factory) as session:
        session.execute(
            insert(source_repo.tables.fields).values(
                data_field_id=field_id,
                dataset_id=dataset.dataset_id,
                name="tc_kimlik_no",
                native_data_type="varchar(11)",
                is_nullable=False,
                is_sensitive=False,
            )
        )
    return source_repo.get_data_field(field_id)


def test_ownership_change_flow_end_to_end(pg: PgFixture) -> None:
    command_service, source_repo, governance_repo = _ownership_service(pg)
    dataset = _seed_dataset(pg, source_repo, owner="current-owner")
    scope = frozenset({dataset.dataset_id})

    maker = _actor_context(
        scope, frozenset(), actor_id="maker-1", roles=frozenset({"DATA_STEWARD"})
    )
    request = command_service.submit_request(
        actor_context=maker,
        request_type="DATASET_OWNER_CHANGE",
        object_id=dataset.dataset_id,
        new_owner_user_id="new-owner",
        reason_code="OWNERSHIP.TRANSFER",
    )
    assert request.status is GovernanceApprovalStatus.SUBMITTED
    assert request.scope_version == dataset.version

    # Merkezi listede DATA_OWNERSHIP talebi gorunur
    checker = _actor_context(scope, frozenset(), actor_id="owner-1")
    query_service = GovernanceApprovalQueryService(
        None,
        None,
        _authorization(),
        center_reader=governance_repo,
        center_policy=command_service.policy,
    )
    listed = query_service.list_for_actor(checker, view=GovernanceView.PENDING)
    assert len(listed) == 1
    assert listed[0].domain.value == "DATA_OWNERSHIP"
    assert listed[0].available_actions == ("DECIDE_APPROVAL",)

    decided = command_service.decide_request(
        actor_context=checker,
        approval_request_id=request.approval_request_id,
        decision="APPROVE",
        reason_code="OWNERSHIP.VERIFIED",
    )
    assert decided.status is GovernanceApprovalStatus.APPROVED

    applier = _actor_context(
        scope,
        frozenset(),
        actor_id="applier-1",
        roles=frozenset({"DATA_GOVERNANCE_SPECIALIST"}),
    )
    applied = command_service.apply_request(
        actor_context=applier,
        approval_request_id=request.approval_request_id,
    )
    assert applied.status is GovernanceApprovalStatus.APPLIED

    updated = source_repo.get_dataset(dataset.dataset_id)
    assert updated.owner_user_id == "new-owner"
    assert updated.version == dataset.version + 1


def test_ownership_request_invalidated_when_dataset_changes(pg: PgFixture) -> None:
    command_service, source_repo, governance_repo = _ownership_service(pg)
    dataset = _seed_dataset(pg, source_repo, owner="current-owner")
    scope = frozenset({dataset.dataset_id})

    maker = _actor_context(
        scope, frozenset(), actor_id="maker-1", roles=frozenset({"DATA_STEWARD"})
    )
    request = command_service.submit_request(
        actor_context=maker,
        request_type="DATASET_OWNER_CHANGE",
        object_id=dataset.dataset_id,
        new_owner_user_id="new-owner",
        reason_code="OWNERSHIP.TRANSFER",
    )

    # Hedef nesne onaya esas surumden sonra degisir (ornegin metadata guncellemesi)
    source_repo.update_dataset(
        dataset_id=dataset.dataset_id,
        updates={"name": "ownership-table-renamed"},
        expected_version=dataset.version,
    )

    checker = _actor_context(scope, frozenset(), actor_id="owner-1")
    with pytest.raises(GovernanceConflictError):
        command_service.decide_request(
            actor_context=checker,
            approval_request_id=request.approval_request_id,
            decision="APPROVE",
            reason_code="OWNERSHIP.VERIFIED",
        )

    stored = governance_repo.get(request.approval_request_id)
    assert stored.status is GovernanceApprovalStatus.INVALIDATED


# ----------------------------------------------------------------------
# Execution domain integration
# ----------------------------------------------------------------------


def _execution_governance_service(pg: PgFixture, governance_repo=None):
    """Governance command service with execution domain support."""
    source_repo = PostgreSQLDataSourceRepository(pg.session_factory, schema=pg.schema)
    rule_repo = PostgreSQLRuleRepository(pg.session_factory, schema=pg.schema)
    governance_repo = governance_repo or PostgreSQLGovernanceApprovalRepository(
        pg.session_factory, schema=pg.schema
    )
    audit = _audit(pg)

    class _NoopAuditSink:
        def append(self, event: AuditEventInput) -> None:
            del event

    class _CompositeCatalog:
        def __init__(self, source_repo, rule_repo):
            self._source = source_repo
            self._rule = rule_repo

        def get_dataset(self, dataset_id):
            return self._source.get_dataset(dataset_id)

        def get_data_field(self, field_id):
            return self._source.get_data_field(field_id)

        def get_rule(self, quality_rule_id):
            return self._rule.get_rule(quality_rule_id)

        def get_rule_version(self, rule_version_id):
            return self._rule.get_version(rule_version_id)

        def get_execution(self, execution_id):
            raise KeyError(execution_id)

        def get_dead_letter(self, dead_letter_id):
            raise KeyError(dead_letter_id)

    class _FakeExecutionWriter:
        def __init__(self):
            self.applied: list = []

        def apply_manual_start(self, *, request, actor_context):
            self.applied.append(("start", request.object_id))
            return None

        def apply_cancel(self, *, request, actor_context):
            self.applied.append(("cancel", request.object_id))
            return None

        def apply_dead_letter_reprocess(self, *, request, actor_context):
            self.applied.append(("dead_letter", request.object_id))
            return None

    policy = GovernanceApprovalPolicy(
        version="GOVERNANCE_APPROVAL_POLICY_V1",
        actor_policy_version=ACTOR_POLICY_VERSION,
        maker_roles=frozenset({"DATA_STEWARD"}),
        checker_roles=frozenset({"DATA_OWNER"}),
        applier_roles=frozenset({"DATA_GOVERNANCE_SPECIALIST"}),
    )
    catalog = _CompositeCatalog(source_repo, rule_repo)
    writer = _FakeExecutionWriter()
    command_service = GovernanceApprovalCommandService(
        governance_repo,
        catalog,
        PostgreSQLDatasetOwnershipWriter(source_repo),
        audit_sink=_NoopAuditSink(),
        transactional_audit=audit,
        policy=policy,
        metadata_writer=PostgreSQLMetadataGovernanceWriter(source_repo),
        execution_writer=writer,
        clock=lambda: NOW,
    )
    return command_service, source_repo, rule_repo, governance_repo, writer


def _seed_rule(pg, rule_repo, source_repo, dataset_id: str):
    """Seed a quality rule + version linked to the given dataset."""
    rule = QualityRule(
        quality_rule_id=str(uuid4()),
        code="EXEC-RULE",
        name="Execution Rule",
        dataset_id=dataset_id,
        field_ids=(),
        primary_dimension=QualityDimension.COMPLETENESS,
        owner_user_id="rule-owner",
        status=RuleStatus.ACTIVE,
    )
    version = RuleVersion(
        quality_rule_id=rule.quality_rule_id,
        version_no=1,
        rule_type=RuleType.REQUIRED,
        definition={"field_id": "f"},
        threshold=90.0,
        weight=1.0,
        criticality=RuleCriticality.CRITICAL,
        prepared_by_actor_id="maker-1",
        created_at=NOW,
    )
    audit = _audit(pg)
    rule_repo.add_rule_with_version(
        rule,
        version,
        audit_event=_prepared(audit, object_id=rule.quality_rule_id),
        audit_outbox=audit,
    )
    return rule, version


def test_execution_manual_start_governance_flow(pg: PgFixture) -> None:
    command_service, source_repo, rule_repo, governance_repo, writer = (
        _execution_governance_service(pg)
    )
    dataset = _seed_dataset(pg, source_repo, owner="current-owner")
    rule, version = _seed_rule(pg, rule_repo, source_repo, dataset.dataset_id)
    scope = frozenset({dataset.dataset_id})

    maker = _actor_context(
        scope, frozenset(), actor_id="maker-1", roles=frozenset({"DATA_STEWARD"})
    )
    request = command_service.submit_request(
        actor_context=maker,
        request_type="EXECUTION_MANUAL_START",
        object_id="new-exec-gov",
        reason_code="EXECUTION.MANUAL.START",
        proposed_changes={
            "rule_version_ids": [version.rule_version_id],
            "execution_mode": "OFFICIAL",
        },
    )
    assert request.status is GovernanceApprovalStatus.SUBMITTED
    assert request.object_type == "RuleExecution"
    assert request.scope_version == 0
    assert "dataset_versions" in request.change_summary["before"]

    # Merkezi listede EXECUTION domain talebi gorunur
    checker = _actor_context(scope, frozenset(), actor_id="owner-1")
    query_service = GovernanceApprovalQueryService(
        None,
        None,
        _authorization(),
        center_reader=governance_repo,
        center_policy=command_service.policy,
    )
    listed = query_service.list_for_actor(checker, view=GovernanceView.PENDING)
    exec_items = [i for i in listed if i.domain.value == "EXECUTION"]
    assert len(exec_items) == 1
    assert exec_items[0].request_type.value == "EXECUTION_MANUAL_START"
    assert exec_items[0].available_actions == ("DECIDE_APPROVAL",)

    # Karar ve uygulama
    decided = command_service.decide_request(
        actor_context=checker,
        approval_request_id=request.approval_request_id,
        decision="APPROVE",
        reason_code="EXECUTION.VERIFIED",
    )
    assert decided.status is GovernanceApprovalStatus.APPROVED

    applier = _actor_context(
        scope,
        frozenset(),
        actor_id="applier-1",
        roles=frozenset({"DATA_GOVERNANCE_SPECIALIST"}),
    )
    applied = command_service.apply_request(
        actor_context=applier,
        approval_request_id=request.approval_request_id,
    )
    assert applied.status is GovernanceApprovalStatus.APPLIED
    assert len(writer.applied) == 1
    assert writer.applied[0] == ("start", "new-exec-gov")


def test_execution_governance_invalidated_on_dataset_change(pg: PgFixture) -> None:
    command_service, source_repo, rule_repo, governance_repo, _writer = (
        _execution_governance_service(pg)
    )
    dataset = _seed_dataset(pg, source_repo, owner="current-owner")
    _rule, version = _seed_rule(pg, rule_repo, source_repo, dataset.dataset_id)
    scope = frozenset({dataset.dataset_id})

    maker = _actor_context(
        scope, frozenset(), actor_id="maker-1", roles=frozenset({"DATA_STEWARD"})
    )
    request = command_service.submit_request(
        actor_context=maker,
        request_type="EXECUTION_MANUAL_START",
        object_id="new-exec-inv",
        reason_code="EXECUTION.MANUAL.START",
        proposed_changes={"rule_version_ids": [version.rule_version_id]},
    )

    # Dataset version changes between submit and decide
    source_repo.update_dataset(
        dataset_id=dataset.dataset_id,
        updates={"name": "renamed-table"},
        expected_version=dataset.version,
    )

    checker = _actor_context(scope, frozenset(), actor_id="owner-1")
    with pytest.raises(GovernanceConflictError):
        command_service.decide_request(
            actor_context=checker,
            approval_request_id=request.approval_request_id,
            decision="APPROVE",
            reason_code="EXECUTION.VERIFIED",
        )

    stored = governance_repo.get(request.approval_request_id)
    assert stored.status is GovernanceApprovalStatus.INVALIDATED


def test_duplicate_pending_ownership_request_rejected(pg: PgFixture) -> None:
    command_service, source_repo, _governance_repo = _ownership_service(pg)
    dataset = _seed_dataset(pg, source_repo, owner="current-owner")
    scope = frozenset({dataset.dataset_id})
    maker = _actor_context(
        scope, frozenset(), actor_id="maker-1", roles=frozenset({"DATA_STEWARD"})
    )

    command_service.submit_request(
        actor_context=maker,
        request_type="DATASET_OWNER_CHANGE",
        object_id=dataset.dataset_id,
        new_owner_user_id="new-owner",
        reason_code="OWNERSHIP.TRANSFER",
    )
    with pytest.raises(GovernanceConflictError):
        command_service.submit_request(
            actor_context=maker,
            request_type="DATASET_OWNER_CHANGE",
            object_id=dataset.dataset_id,
            new_owner_user_id="another-owner",
            reason_code="OWNERSHIP.TRANSFER",
        )


def test_metadata_critical_change_flow_end_to_end(pg: PgFixture) -> None:
    command_service, source_repo, governance_repo = _ownership_service(pg)
    dataset = _seed_dataset(pg, source_repo, owner="current-owner")
    scope = frozenset({dataset.dataset_id})

    maker = _actor_context(
        scope, frozenset(), actor_id="maker-1", roles=frozenset({"DATA_STEWARD"})
    )
    request = command_service.submit_request(
        actor_context=maker,
        request_type="METADATA_CRITICAL_CHANGE",
        object_id=dataset.dataset_id,
        reason_code="METADATA.CRITICALITY.CHANGE",
        proposed_changes={"criticality": "CRITICAL"},
    )
    assert request.status is GovernanceApprovalStatus.SUBMITTED
    assert request.scope_version == dataset.version

    # Merkezi listede METADATA_AND_CLASSIFICATION domain talebi gorunur
    checker = _actor_context(scope, frozenset(), actor_id="owner-1")
    query_service = GovernanceApprovalQueryService(
        None,
        None,
        _authorization(),
        center_reader=governance_repo,
        center_policy=command_service.policy,
    )
    listed = query_service.list_for_actor(checker, view=GovernanceView.PENDING)
    assert len(listed) == 1
    assert listed[0].domain.value == "METADATA_AND_CLASSIFICATION"
    assert listed[0].request_type.value == "METADATA_CRITICAL_CHANGE"

    decided = command_service.decide_request(
        actor_context=checker,
        approval_request_id=request.approval_request_id,
        decision="APPROVE",
        reason_code="METADATA.VERIFIED",
    )
    assert decided.status is GovernanceApprovalStatus.APPROVED

    applier = _actor_context(
        scope,
        frozenset(),
        actor_id="applier-1",
        roles=frozenset({"DATA_GOVERNANCE_SPECIALIST"}),
    )
    applied = command_service.apply_request(
        actor_context=applier,
        approval_request_id=request.approval_request_id,
    )
    assert applied.status is GovernanceApprovalStatus.APPLIED

    updated = source_repo.get_dataset(dataset.dataset_id)
    assert updated.criticality is Criticality.CRITICAL
    assert updated.version == dataset.version + 1

    # Idempotent yeniden uygulama durumu korur
    reapplied = command_service.apply_request(
        actor_context=applier,
        approval_request_id=request.approval_request_id,
    )
    assert reapplied.status is GovernanceApprovalStatus.APPLIED


def test_field_sensitivity_mark_flow_end_to_end(pg: PgFixture) -> None:
    command_service, source_repo, _governance_repo = _ownership_service(pg)
    dataset = _seed_dataset(pg, source_repo, owner="current-owner")
    data_field = _seed_field(pg, source_repo, dataset)
    scope = frozenset({dataset.dataset_id})

    maker = _actor_context(
        scope, frozenset(), actor_id="maker-1", roles=frozenset({"DATA_STEWARD"})
    )
    request = command_service.submit_request(
        actor_context=maker,
        request_type="FIELD_SENSITIVITY_MARK",
        object_id=data_field.data_field_id,
        reason_code="METADATA.SENSITIVITY.MARK",
        proposed_changes={"is_sensitive": True, "classification": "PERSONAL_DATA"},
    )
    assert request.object_type == "DataField"
    assert request.scope_type == "DATASET"
    assert request.scope_id == dataset.dataset_id
    assert request.scope_version == data_field.version

    checker = _actor_context(scope, frozenset(), actor_id="owner-1")
    decided = command_service.decide_request(
        actor_context=checker,
        approval_request_id=request.approval_request_id,
        decision="APPROVE",
        reason_code="METADATA.VERIFIED",
    )
    assert decided.status is GovernanceApprovalStatus.APPROVED

    applier = _actor_context(
        scope,
        frozenset(),
        actor_id="applier-1",
        roles=frozenset({"DATA_GOVERNANCE_SPECIALIST"}),
    )
    applied = command_service.apply_request(
        actor_context=applier,
        approval_request_id=request.approval_request_id,
    )
    assert applied.status is GovernanceApprovalStatus.APPLIED

    updated = source_repo.get_data_field(data_field.data_field_id)
    assert updated.is_sensitive is True
    assert updated.classification is ClassificationCode.PERSONAL_DATA
    assert updated.version == data_field.version + 1


def test_metadata_request_invalidated_when_dataset_changes(pg: PgFixture) -> None:
    command_service, source_repo, governance_repo = _ownership_service(pg)
    dataset = _seed_dataset(pg, source_repo, owner="current-owner")
    scope = frozenset({dataset.dataset_id})

    maker = _actor_context(
        scope, frozenset(), actor_id="maker-1", roles=frozenset({"DATA_STEWARD"})
    )
    request = command_service.submit_request(
        actor_context=maker,
        request_type="METADATA_CRITICAL_CHANGE",
        object_id=dataset.dataset_id,
        reason_code="METADATA.STATUS.CHANGE",
        proposed_changes={"status": "INACTIVE"},
    )

    # Hedef nesne onaya esas surumden sonra degisir
    source_repo.update_dataset(
        dataset_id=dataset.dataset_id,
        updates={"name": "ownership-table-renamed"},
        expected_version=dataset.version,
    )

    checker = _actor_context(scope, frozenset(), actor_id="owner-1")
    with pytest.raises(GovernanceConflictError):
        command_service.decide_request(
            actor_context=checker,
            approval_request_id=request.approval_request_id,
            decision="APPROVE",
            reason_code="METADATA.VERIFIED",
        )

    stored = governance_repo.get(request.approval_request_id)
    assert stored.status is GovernanceApprovalStatus.INVALIDATED


# ----------------------------------------------------------------------
# F-02: execution talepleri scope_version=0 ile gercek PostgreSQL'e yazilabilmeli
# ----------------------------------------------------------------------

_EXECUTION_REQUEST_TYPES_WITH_OBJECTS = (
    (GovernanceRequestType.EXECUTION_MANUAL_START, "RuleExecution"),
    (GovernanceRequestType.EXECUTION_CANCEL, "RuleExecution"),
    (GovernanceRequestType.DEAD_LETTER_REPROCESS, "DeadLetterRecord"),
)


@pytest.mark.parametrize(("request_type", "object_type"), _EXECUTION_REQUEST_TYPES_WITH_OBJECTS)
def test_execution_requests_persist_with_zero_scope_version(
    pg: PgFixture, request_type: GovernanceRequestType, object_type: str
) -> None:
    """ck_governance_approval_scope_version execution tiplerinde 0'i kabul etmeli."""

    repository = PostgreSQLGovernanceApprovalRepository(pg.session_factory, schema=pg.schema)
    audit = _audit(pg)
    request = GovernanceApprovalRequest(
        request_type=request_type,
        object_type=object_type,
        object_id=str(uuid4()),
        scope_type="DATASET",
        scope_id="dataset-exec-scope",
        scope_version=0,
        maker_actor_id="maker-1",
        maker_roles=("DATA_STEWARD",),
        policy_version="GOVERNANCE_APPROVAL_POLICY_V1",
        correlation_id="correlation-exec",
        change_summary={"before": {"status": None}, "after": {"status": "QUEUED"}},
        status=GovernanceApprovalStatus.SUBMITTED,
        reason_code="EXECUTION.MANUAL.START",
        requested_at=NOW,
    )

    stored = repository.add(
        request,
        audit_event=_prepared(audit, object_id=request.object_id),
        audit_outbox=audit,
    )

    assert repository.get(stored.approval_request_id).scope_version == 0


def test_versioned_request_still_rejects_zero_scope_version(pg: PgFixture) -> None:
    """Execution disi tipler pozitif versiyon zorunlulugunu korumali.

    Ihlal, yaniltici "pending request" cakismasi degil, domain dogrulama
    hatasi olarak raporlanmalidir (F-02 siniflandirma duzeltmesi).
    """

    repository = PostgreSQLGovernanceApprovalRepository(pg.session_factory, schema=pg.schema)
    audit = _audit(pg)
    request = GovernanceApprovalRequest(
        request_type=GovernanceRequestType.DATASET_OWNER_CHANGE,
        object_type="Dataset",
        object_id=str(uuid4()),
        scope_type="DATASET",
        scope_id="dataset-owner-scope",
        scope_version=0,
        maker_actor_id="maker-1",
        maker_roles=("DATA_STEWARD",),
        policy_version="GOVERNANCE_APPROVAL_POLICY_V1",
        correlation_id="correlation-owner",
        change_summary={"before": {"owner_user_id": "a"}, "after": {"owner_user_id": "b"}},
        status=GovernanceApprovalStatus.SUBMITTED,
        reason_code="OWNERSHIP.TRANSFER",
        requested_at=NOW,
    )

    with pytest.raises(GovernanceValidationError, match="ck_governance_approval_scope_version"):
        repository.add(
            request,
            audit_event=_prepared(audit, object_id=request.object_id),
            audit_outbox=audit,
        )
