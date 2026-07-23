"""PostgreSQL rule repository entegrasyon testleri.

DATA_QUALITY_POSTGRES_TEST_URL gerektirir; set edilmemisse atlanir.

Iterasyon 36C0 — Rules PostgreSQL migration.
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
from sqlalchemy import create_engine, text

from veri_kalitesi.audit import (
    PostgreSQLTransactionalAudit,
    PreparedAuditEvent,
    build_default_redaction_policy,
    AuditRedactor,
    AuditEventInput,
    AuditResult,
)
from veri_kalitesi.persistence import DatabaseSettings, SessionFactory, create_session_factory
from veri_kalitesi.rules import (
    QualityRule,
    RuleTestResult,
    RuleTestStatus,
    RuleApprovalRequest,
    RuleApprovalStatus,
    RuleStatus,
    RuleCriticality,
    RuleType,
    QualityDimension,
    RuleVersion,
    RuleValidationError,
    RuleNotFoundError,
)
from veri_kalitesi.rules.postgresql_repository import PostgreSQLRuleRepository

POSTGRES_TEST_URL = os.environ.get("DATA_QUALITY_POSTGRES_TEST_URL")
pytestmark = pytest.mark.skipif(
    not POSTGRES_TEST_URL,
    reason="DATA_QUALITY_POSTGRES_TEST_URL is required for PostgreSQL integration.",
)
ROOT = Path(__file__).resolve().parents[2]


@dataclass
class PgFixture:
    session_factory: SessionFactory
    schema: str
    engine: Any


@pytest.fixture
def pg() -> Iterator[PgFixture]:
    settings = DatabaseSettings.from_url(
        POSTGRES_TEST_URL,
        schema=f"test_rules_{uuid4().hex[:8]}",
    )
    session_factory = create_session_factory(settings)
    engine = create_engine(settings.url)
    alembic_cfg = Config(str(ROOT / "05-Veritabani" / "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.url.render_as_string(hide_password=False))
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


def _repo(pg: PgFixture) -> PostgreSQLRuleRepository:
    return PostgreSQLRuleRepository(pg.session_factory, schema=pg.schema)


def _audit(pg: PgFixture) -> PostgreSQLTransactionalAudit:
    return PostgreSQLTransactionalAudit(
        pg.session_factory,
        AuditRedactor(build_default_redaction_policy()),
        policy_version="TEST_V1",
        schema=pg.schema,
    )


def _prepared(audit: PostgreSQLTransactionalAudit, **overrides: Any) -> PreparedAuditEvent:
    return audit.prepare(
        AuditEventInput(
            actor_id=overrides.get("actor_id", "test-actor"),
            actor_type="USER",
            correlation_id=overrides.get("correlation_id", "test-correlation"),
            action=overrides.get("action", "QUALITY_RULE_CREATED"),
            object_type="QualityRule",
            object_id=overrides.get("object_id", str(uuid4())),
            result=AuditResult.SUCCESS,
            reason_code="TEST",
            old_values={},
            new_values={"test": True},
            occurred_at=datetime.now(timezone.utc),
            session_id=None,
        )
    )


def _now() -> datetime:
    return datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc)


def _make_rule(**overrides: Any) -> QualityRule:
    return QualityRule(
        quality_rule_id=overrides.get("quality_rule_id", str(uuid4())),
        code=overrides.get("code", "TEST-RULE"),
        name=overrides.get("name", "Test Rule"),
        dataset_id=overrides.get("dataset_id", "dataset-main"),
        field_ids=overrides.get("field_ids", ()),
        primary_dimension=QualityDimension.COMPLETENESS,
        owner_user_id=overrides.get("owner_user_id", "test-owner"),
        status=overrides.get("status", RuleStatus.DRAFT),
    )


def _make_version(rule_id: str, **overrides: Any) -> RuleVersion:
    return RuleVersion(
        quality_rule_id=rule_id,
        version_no=overrides.get("version_no", 1),
        rule_type=RuleType.REQUIRED,
        definition={"field_id": "test-field"},
        threshold=80.0,
        weight=1.0,
        criticality=RuleCriticality.LOW,
        prepared_by_actor_id=overrides.get("prepared_by", "test-maker"),
        rule_version_id=overrides.get("rule_version_id", str(uuid4())),
        created_at=_now(),
    )


def test_create_rule_persists_to_postgresql(pg: PgFixture) -> None:
    repo = _repo(pg)
    audit = _audit(pg)
    rule = _make_rule()
    version = _make_version(rule.quality_rule_id)

    repo.add_rule_with_version(
        rule, version,
        audit_event=_prepared(audit, object_id=rule.quality_rule_id),
        audit_outbox=audit,
    )

    fetched_rule = repo.get_rule(rule.quality_rule_id)
    assert fetched_rule.code == rule.code
    assert fetched_rule.name == rule.name
    assert fetched_rule.status is RuleStatus.DRAFT

    fetched_version = repo.get_version(version.rule_version_id)
    assert fetched_version.version_no == 1
    assert fetched_version.criticality is RuleCriticality.LOW


def test_add_version_and_list_versions(pg: PgFixture) -> None:
    repo = _repo(pg)
    audit = _audit(pg)
    rule = _make_rule()
    v1 = _make_version(rule.quality_rule_id, version_no=1)
    repo.add_rule_with_version(
        rule, v1,
        audit_event=_prepared(audit, object_id=rule.quality_rule_id),
        audit_outbox=audit,
    )
    v2 = _make_version(rule.quality_rule_id, version_no=2,
                        rule_version_id=str(uuid4()), threshold=90.0)
    repo.add_version(
        v2,
        audit_event=_prepared(audit, object_id=rule.quality_rule_id),
        audit_outbox=audit,
    )

    versions = repo.list_versions(rule.quality_rule_id)
    assert len(versions) == 2
    assert versions[0].version_no == 1
    assert versions[1].version_no == 2
    assert versions[1].threshold == 90.0


def test_list_rules_with_latest_version(pg: PgFixture) -> None:
    repo = _repo(pg)
    audit = _audit(pg)
    r1 = _make_rule(code="RULE-A", dataset_id="ds-1")
    r1_v1 = _make_version(r1.quality_rule_id, version_no=1)
    repo.add_rule_with_version(r1, r1_v1, audit_event=_prepared(audit, object_id=r1.quality_rule_id), audit_outbox=audit)
    r1_v2 = _make_version(r1.quality_rule_id, version_no=2, rule_version_id=str(uuid4()))
    repo.add_version(r1_v2, audit_event=_prepared(audit, object_id=r1.quality_rule_id), audit_outbox=audit)

    r2 = _make_rule(code="RULE-B", dataset_id="ds-1")
    r2_v1 = _make_version(r2.quality_rule_id, version_no=1)
    repo.add_rule_with_version(r2, r2_v1, audit_event=_prepared(audit, object_id=r2.quality_rule_id), audit_outbox=audit)

    r3 = _make_rule(code="RULE-C", dataset_id="ds-2")
    r3_v1 = _make_version(r3.quality_rule_id, version_no=1)
    repo.add_rule_with_version(r3, r3_v1, audit_event=_prepared(audit, object_id=r3.quality_rule_id), audit_outbox=audit)

    ds1_results = repo.list_rules_with_latest_version(frozenset({"ds-1"}))
    assert len(ds1_results) == 2
    for rule, version in ds1_results:
        assert rule.dataset_id == "ds-1"
    latest_a = [v for r, v in ds1_results if r.code == "RULE-A"][0]
    assert latest_a.version_no == 2

    ds2_results = repo.list_rules_with_latest_version(frozenset({"ds-2"}))
    assert len(ds2_results) == 1
    assert ds2_results[0][0].code == "RULE-C"

    empty = repo.list_rules_with_latest_version(frozenset())
    assert empty == []


def test_rule_test_result_persistence(pg: PgFixture) -> None:
    repo = _repo(pg)
    audit = _audit(pg)
    rule = _make_rule()
    version = _make_version(rule.quality_rule_id)
    repo.add_rule_with_version(rule, version, audit_event=_prepared(audit), audit_outbox=audit)

    result = RuleTestResult(
        rule_version_id=version.rule_version_id,
        status=RuleTestStatus.SUCCESS,
        record_limit=5000,
        checked_count=100,
        passed_count=95,
        failed_count=5,
        success_rate=95.0,
        preview_score=95.0,
        message="Test completed.",
    )

    repo.add_test_result(
        result,
        audit_event=_prepared(audit, object_id=rule.quality_rule_id),
        audit_outbox=audit,
    )

    results = repo.list_test_results(version.rule_version_id)
    assert len(results) == 1
    assert results[0].passed_count == 95

    latest = repo.latest_test_result(version.rule_version_id)
    assert latest is not None
    assert latest.rule_test_result_id == result.rule_test_result_id

    no_results = repo.latest_test_result(str(uuid4()))
    assert no_results is None


def test_approval_request_lifecycle(pg: PgFixture) -> None:
    repo = _repo(pg)
    audit = _audit(pg)
    rule = _make_rule()
    version = _make_version(rule.quality_rule_id)
    repo.add_rule_with_version(rule, version, audit_event=_prepared(audit), audit_outbox=audit)

    request = RuleApprovalRequest(
        rule_version_id=version.rule_version_id,
        maker_actor_id="test-maker",
        policy_version="TEST_V1",
        requested_at=_now(),
    )

    stored = repo.add_approval_request(
        request,
        audit_event=_prepared(audit, object_id=rule.quality_rule_id),
        audit_outbox=audit,
    )
    assert stored.status is RuleApprovalStatus.PENDING

    fetched = repo.get_approval_request(request.approval_request_id)
    assert fetched.maker_actor_id == "test-maker"

    decided = RuleApprovalRequest(
        approval_request_id=request.approval_request_id,
        rule_version_id=version.rule_version_id,
        maker_actor_id="test-maker",
        checker_actor_id="test-checker",
        policy_version="TEST_V1",
        status=RuleApprovalStatus.APPROVED,
        decision_reason_code="APPROVED",
        requested_at=_now(),
        decided_at=_now() + timedelta(hours=1),
    )

    result = repo.decide_approval_request(
        decided,
        quality_rule_id=rule.quality_rule_id,
        activate_rule=True,
        audit_event=_prepared(audit, object_id=rule.quality_rule_id),
        audit_outbox=audit,
    )
    assert result.status is RuleApprovalStatus.APPROVED

    updated_rule = repo.get_rule(rule.quality_rule_id)
    assert updated_rule.status is RuleStatus.ACTIVE


def test_duplicate_rule_code_rejects(pg: PgFixture) -> None:
    repo = _repo(pg)
    audit = _audit(pg)
    rule_a = _make_rule(code="DUPE")
    version_a = _make_version(rule_a.quality_rule_id)
    repo.add_rule_with_version(rule_a, version_a, audit_event=_prepared(audit), audit_outbox=audit)

    rule_b = _make_rule(code="DUPE")
    version_b = _make_version(rule_b.quality_rule_id)
    with pytest.raises(RuleValidationError, match="unique"):
        repo.add_rule_with_version(
            rule_b, version_b,
            audit_event=_prepared(audit, object_id=rule_b.quality_rule_id),
            audit_outbox=audit,
        )


def test_expire_approval_requests(pg: PgFixture) -> None:
    repo = _repo(pg)
    audit = _audit(pg)
    rule = _make_rule()
    version = _make_version(rule.quality_rule_id)
    repo.add_rule_with_version(rule, version, audit_event=_prepared(audit), audit_outbox=audit)

    request = RuleApprovalRequest(
        rule_version_id=version.rule_version_id,
        maker_actor_id="test-maker",
        policy_version="TEST_V1",
        requested_at=_now() - timedelta(days=10),
        expires_at=_now() - timedelta(days=1),
    )
    repo.add_approval_request(request, audit_event=_prepared(audit), audit_outbox=audit)

    due = repo.list_due_approval_requests(_now())
    assert len(due) == 1
    assert due[0].approval_request_id == request.approval_request_id

    expired = RuleApprovalRequest(
        approval_request_id=request.approval_request_id,
        rule_version_id=version.rule_version_id,
        maker_actor_id="test-maker",
        policy_version="TEST_V1",
        status=RuleApprovalStatus.EXPIRED,
        decision_reason_code="RULE.APPROVAL.EXPIRED",
        requested_at=_now() - timedelta(days=10),
        expires_at=_now() - timedelta(days=1),
        decided_at=_now(),
    )
    result = repo.expire_approval_request(
        expired,
        audit_event=_prepared(audit, object_id=rule.quality_rule_id),
        audit_outbox=audit,
    )
    assert result.status is RuleApprovalStatus.EXPIRED

    no_due = repo.list_due_approval_requests(_now())
    assert len(no_due) == 0


def test_get_missing_rule_raises_not_found(pg: PgFixture) -> None:
    repo = _repo(pg)
    with pytest.raises(RuleNotFoundError):
        repo.get_rule(str(uuid4()))


def test_update_rule_status(pg: PgFixture) -> None:
    repo = _repo(pg)
    audit = _audit(pg)
    rule = _make_rule(status=RuleStatus.DRAFT)
    version = _make_version(rule.quality_rule_id)
    repo.add_rule_with_version(rule, version, audit_event=_prepared(audit), audit_outbox=audit)

    updated = repo.update_rule_status(
        rule.quality_rule_id,
        RuleStatus.ACTIVE,
        audit_event=_prepared(audit, object_id=rule.quality_rule_id),
        audit_outbox=audit,
    )
    assert updated.status is RuleStatus.ACTIVE


def test_get_missing_version_raises_not_found(pg: PgFixture) -> None:
    repo = _repo(pg)
    with pytest.raises(RuleNotFoundError):
        repo.get_version(str(uuid4()))


def test_get_missing_approval_request_raises_not_found(pg: PgFixture) -> None:
    repo = _repo(pg)
    with pytest.raises(RuleNotFoundError):
        repo.get_approval_request(str(uuid4()))