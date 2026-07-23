"""PostgreSQL-only rule persistence and immutable version history.

Iteration 36C0 — Rules PostgreSQL migration.
Issues/postgresql_repository.py sablonunu izler.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    insert,
    select,
    update,
)
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from veri_kalitesi.audit import PostgreSQLTransactionalAudit, PreparedAuditEvent
from veri_kalitesi.persistence import DEFAULT_SCHEMA_NAME, SessionFactory, transactional_session
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
)


@dataclass(frozen=True)
class RuleTables:
    rules: Table
    versions: Table
    test_results: Table
    approval_requests: Table


def rule_tables(schema: str = DEFAULT_SCHEMA_NAME) -> RuleTables:
    metadata = MetaData(schema=schema)
    rules = Table(
        "quality_rules",
        metadata,
        Column("quality_rule_id", String(36), primary_key=True),
        Column("code", String(200), nullable=False, unique=True),
        Column("name", String(400), nullable=False),
        Column("dataset_id", String(36), nullable=False),
        Column("field_ids", JSON, nullable=False),
        Column("primary_dimension", String(40), nullable=False),
        Column("owner_user_id", String(128), nullable=False),
        Column("status", String(30), nullable=False),
    )
    versions = Table(
        "rule_versions",
        metadata,
        Column("rule_version_id", String(36), primary_key=True),
        Column(
            "quality_rule_id",
            String(36),
            ForeignKey(f"{schema}.quality_rules.quality_rule_id"),
            nullable=False,
        ),
        Column("version_no", Integer, nullable=False),
        Column("rule_type", String(40), nullable=False),
        Column("definition", JSON, nullable=False),
        Column("threshold", Float, nullable=False),
        Column("weight", Float, nullable=False),
        Column("criticality", String(20), nullable=False),
        Column("prepared_by_actor_id", String(128), nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
        UniqueConstraint("quality_rule_id", "version_no", name="uq_rule_versions_rule_version_seq"),
    )
    test_results = Table(
        "rule_test_results",
        metadata,
        Column("rule_test_result_id", String(36), primary_key=True),
        Column(
            "rule_version_id",
            String(36),
            ForeignKey(f"{schema}.rule_versions.rule_version_id"),
            nullable=False,
        ),
        Column("status", String(30), nullable=False),
        Column("record_limit", Integer, nullable=False),
        Column("checked_count", Integer, nullable=False),
        Column("passed_count", Integer, nullable=False),
        Column("failed_count", Integer, nullable=False),
        Column("not_evaluated_count", Integer, nullable=False),
        Column("success_rate", Float),
        Column("preview_score", Float),
        Column("official_score_included", Integer, nullable=False),
        Column("error_class", String(200)),
        Column("message", Text, nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
    )
    approval_requests = Table(
        "rule_approval_requests",
        metadata,
        Column("approval_request_id", String(36), primary_key=True),
        Column(
            "rule_version_id",
            String(36),
            ForeignKey(f"{schema}.rule_versions.rule_version_id"),
            nullable=False,
        ),
        Column("maker_actor_id", String(128), nullable=False),
        Column("checker_actor_id", String(128)),
        Column("policy_version", String(80), nullable=False),
        Column("status", String(20), nullable=False),
        Column("decision_reason_code", String(100)),
        Column("requested_at", DateTime(timezone=True), nullable=False),
        Column("target_at", DateTime(timezone=True)),
        Column("expires_at", DateTime(timezone=True)),
        Column("business_calendar_version", String(80)),
        Column("decided_at", DateTime(timezone=True)),
    )
    return RuleTables(
        rules=rules,
        versions=versions,
        test_results=test_results,
        approval_requests=approval_requests,
    )


class PostgreSQLRuleRepository:
    """Rule yasam dongusunu PostgreSQL ve atomik audit outbox ile saklar."""

    def __init__(
        self,
        session_factory: SessionFactory,
        *,
        schema: str = DEFAULT_SCHEMA_NAME,
    ) -> None:
        self._session_factory = session_factory
        self._tables = rule_tables(schema)
        self._table = self._tables.rules

    # ------------------------------------------------------------------
    # Public read methods
    # ------------------------------------------------------------------

    def get_rule(self, quality_rule_id: str) -> QualityRule:
        with self._session_factory() as session:
            row = (
                session.execute(
                    select(self._tables.rules).where(
                        self._tables.rules.c.quality_rule_id == quality_rule_id
                    )
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            raise RuleNotFoundError("QualityRule not found.")
        return _row_to_rule(row)

    def get_version(self, rule_version_id: str) -> RuleVersion:
        with self._session_factory() as session:
            row = (
                session.execute(
                    select(self._tables.versions).where(
                        self._tables.versions.c.rule_version_id == rule_version_id
                    )
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            raise RuleNotFoundError("RuleVersion not found.")
        return _row_to_version(row)

    def list_versions(self, quality_rule_id: str) -> list[RuleVersion]:
        with self._session_factory() as session:
            rows = (
                session.execute(
                    select(self._tables.versions)
                    .where(self._tables.versions.c.quality_rule_id == quality_rule_id)
                    .order_by(self._tables.versions.c.version_no)
                )
                .mappings()
                .all()
            )
        return [_row_to_version(row) for row in rows]

    def list_rules_with_latest_version(
        self,
        allowed_dataset_ids: frozenset[str],
    ) -> list[tuple[QualityRule, RuleVersion]]:
        if not allowed_dataset_ids:
            return []
        dataset_ids = sorted(allowed_dataset_ids)
        r = self._tables.rules
        v = self._tables.versions
        latest_version = (
            select(v.c.rule_version_id)
            .where(v.c.quality_rule_id == r.c.quality_rule_id)
            .order_by(v.c.version_no.desc())
            .limit(1)
            .correlate(r)
            .scalar_subquery()
        )
        with self._session_factory() as session:
            rows = (
                session.execute(
                    select(r, v)
                    .select_from(r.join(v, v.c.rule_version_id == latest_version))
                    .where(r.c.dataset_id.in_(dataset_ids))
                    .order_by(r.c.code, r.c.quality_rule_id)
                )
                .mappings()
                .all()
            )
        return [(_row_to_rule(row), _row_to_version(row)) for row in rows]

    def list_test_results(self, rule_version_id: str) -> list[RuleTestResult]:
        with self._session_factory() as session:
            rows = (
                session.execute(
                    select(self._tables.test_results)
                    .where(self._tables.test_results.c.rule_version_id == rule_version_id)
                    .order_by(self._tables.test_results.c.created_at)
                )
                .mappings()
                .all()
            )
        return [_row_to_test_result(row) for row in rows]

    def latest_test_result(self, rule_version_id: str) -> RuleTestResult | None:
        with self._session_factory() as session:
            row = (
                session.execute(
                    select(self._tables.test_results)
                    .where(self._tables.test_results.c.rule_version_id == rule_version_id)
                    .order_by(
                        self._tables.test_results.c.created_at.desc(),
                        self._tables.test_results.c.rule_test_result_id.desc(),
                    )
                    .limit(1)
                )
                .mappings()
                .one_or_none()
            )
        return _row_to_test_result(row) if row is not None else None

    def get_approval_request(self, approval_request_id: str) -> RuleApprovalRequest:
        with self._session_factory() as session:
            row = (
                session.execute(
                    select(self._tables.approval_requests).where(
                        self._tables.approval_requests.c.approval_request_id == approval_request_id
                    )
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            raise RuleNotFoundError("RuleApprovalRequest not found.")
        return _row_to_approval_request(row)

    def list_due_approval_requests(self, as_of: datetime) -> list[RuleApprovalRequest]:
        a = self._tables.approval_requests
        with self._session_factory() as session:
            rows = (
                session.execute(
                    select(a)
                    .where(
                        a.c.status == RuleApprovalStatus.PENDING.value,
                        a.c.expires_at.isnot(None),
                        a.c.expires_at <= as_of,
                    )
                    .order_by(a.c.expires_at, a.c.approval_request_id)
                )
                .mappings()
                .all()
            )
        return [_row_to_approval_request(row) for row in rows]

    # ------------------------------------------------------------------
    # Public write methods
    # ------------------------------------------------------------------

    def add_rule_with_version(
        self,
        rule: QualityRule,
        version: RuleVersion,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: PostgreSQLTransactionalAudit,
    ) -> None:
        self._require_postgresql_audit(audit_outbox)
        with transactional_session(self._session_factory) as session:
            try:
                session.execute(
                    insert(self._tables.rules).values(
                        quality_rule_id=rule.quality_rule_id,
                        code=rule.code,
                        name=rule.name,
                        dataset_id=rule.dataset_id,
                        field_ids=list(rule.field_ids),
                        primary_dimension=rule.primary_dimension.value,
                        owner_user_id=rule.owner_user_id,
                        status=rule.status.value,
                    )
                )
                self._insert_version(session, version)
            except IntegrityError as exc:
                raise RuleValidationError("Rule code and version number must be unique.") from exc
            audit_outbox.stage(audit_event, session=session)

    def add_version(
        self,
        version: RuleVersion,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: PostgreSQLTransactionalAudit,
    ) -> None:
        self._require_postgresql_audit(audit_outbox)
        with transactional_session(self._session_factory) as session:
            try:
                self._insert_version(session, version)
            except IntegrityError as exc:
                raise RuleValidationError("Rule version number must be unique.") from exc
            audit_outbox.stage(audit_event, session=session)

    def update_rule_status(
        self,
        quality_rule_id: str,
        status: RuleStatus,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: PostgreSQLTransactionalAudit,
    ) -> QualityRule:
        self._require_postgresql_audit(audit_outbox)
        with transactional_session(self._session_factory) as session:
            result = session.execute(
                update(self._tables.rules)
                .where(self._tables.rules.c.quality_rule_id == quality_rule_id)
                .values(status=status.value)
            )
            self._require_updated(result, operation="status update")
            audit_outbox.stage(audit_event, session=session)
        return self.get_rule(quality_rule_id)

    def add_test_result(
        self,
        result: RuleTestResult,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: PostgreSQLTransactionalAudit,
    ) -> None:
        self._require_postgresql_audit(audit_outbox)
        with transactional_session(self._session_factory) as session:
            session.execute(
                insert(self._tables.test_results).values(
                    rule_test_result_id=result.rule_test_result_id,
                    rule_version_id=result.rule_version_id,
                    status=result.status.value,
                    record_limit=result.record_limit,
                    checked_count=result.checked_count,
                    passed_count=result.passed_count,
                    failed_count=result.failed_count,
                    not_evaluated_count=result.not_evaluated_count,
                    success_rate=result.success_rate,
                    preview_score=result.preview_score,
                    official_score_included=1 if result.official_score_included else 0,
                    error_class=result.error_class,
                    message=result.message,
                    created_at=result.created_at,
                )
            )
            audit_outbox.stage(audit_event, session=session)

    def add_approval_request(
        self,
        request: RuleApprovalRequest,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: PostgreSQLTransactionalAudit,
    ) -> RuleApprovalRequest:
        self._require_postgresql_audit(audit_outbox)
        with transactional_session(self._session_factory) as session:
            try:
                session.execute(
                    insert(self._tables.approval_requests).values(
                        approval_request_id=request.approval_request_id,
                        rule_version_id=request.rule_version_id,
                        maker_actor_id=request.maker_actor_id,
                        checker_actor_id=request.checker_actor_id,
                        policy_version=request.policy_version,
                        status=request.status.value,
                        decision_reason_code=request.decision_reason_code,
                        requested_at=request.requested_at,
                        target_at=request.target_at,
                        expires_at=request.expires_at,
                        business_calendar_version=request.business_calendar_version,
                        decided_at=request.decided_at,
                    )
                )
            except IntegrityError as exc:
                raise RuleValidationError(
                    "RuleVersion already has an approval request."
                ) from exc
            audit_outbox.stage(audit_event, session=session)
        return request

    def decide_approval_request(
        self,
        request: RuleApprovalRequest,
        *,
        quality_rule_id: str,
        activate_rule: bool,
        audit_event: PreparedAuditEvent,
        audit_outbox: PostgreSQLTransactionalAudit,
    ) -> RuleApprovalRequest:
        self._require_postgresql_audit(audit_outbox)
        with transactional_session(self._session_factory) as session:
            result = session.execute(
                update(self._tables.approval_requests)
                .where(
                    self._tables.approval_requests.c.approval_request_id
                    == request.approval_request_id,
                    self._tables.approval_requests.c.status == RuleApprovalStatus.PENDING.value,
                )
                .values(
                    status=request.status.value,
                    checker_actor_id=request.checker_actor_id,
                    decision_reason_code=request.decision_reason_code,
                    decided_at=request.decided_at,
                )
            )
            self._require_updated(result, operation="approval decision")
            if activate_rule:
                result = session.execute(
                    update(self._tables.rules)
                    .where(
                        self._tables.rules.c.quality_rule_id == quality_rule_id,
                        self._tables.rules.c.status == RuleStatus.DRAFT.value,
                    )
                    .values(status=RuleStatus.ACTIVE.value)
                )
                self._require_updated(result, operation="rule activation")
            audit_outbox.stage(audit_event, session=session)
        return self.get_approval_request(request.approval_request_id)

    def withdraw_approval_request(
        self,
        request: RuleApprovalRequest,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: PostgreSQLTransactionalAudit,
    ) -> RuleApprovalRequest:
        self._require_postgresql_audit(audit_outbox)
        if request.status is not RuleApprovalStatus.WITHDRAWN:
            raise RuleValidationError("Rule approval withdrawal status is invalid.")
        with transactional_session(self._session_factory) as session:
            result = session.execute(
                update(self._tables.approval_requests)
                .where(
                    self._tables.approval_requests.c.approval_request_id
                    == request.approval_request_id,
                    self._tables.approval_requests.c.status == RuleApprovalStatus.PENDING.value,
                )
                .values(
                    status=request.status.value,
                    checker_actor_id=None,
                    decision_reason_code=request.decision_reason_code,
                    decided_at=request.decided_at,
                )
            )
            self._require_updated(result, operation="approval withdraw")
            audit_outbox.stage(audit_event, session=session)
        return self.get_approval_request(request.approval_request_id)

    def expire_approval_request(
        self,
        request: RuleApprovalRequest,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: PostgreSQLTransactionalAudit,
    ) -> RuleApprovalRequest:
        self._require_postgresql_audit(audit_outbox)
        if request.status is not RuleApprovalStatus.EXPIRED:
            raise RuleValidationError("Rule approval expiry status is invalid.")
        with transactional_session(self._session_factory) as session:
            result = session.execute(
                update(self._tables.approval_requests)
                .where(
                    self._tables.approval_requests.c.approval_request_id
                    == request.approval_request_id,
                    self._tables.approval_requests.c.status == RuleApprovalStatus.PENDING.value,
                )
                .values(
                    status=request.status.value,
                    checker_actor_id=None,
                    decision_reason_code=request.decision_reason_code,
                    decided_at=request.decided_at,
                )
            )
            self._require_updated(result, operation="approval expiry")
            audit_outbox.stage(audit_event, session=session)
        return self.get_approval_request(request.approval_request_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _insert_version(self, session: Session, version: RuleVersion) -> None:
        session.execute(
            insert(self._tables.versions).values(
                rule_version_id=version.rule_version_id,
                quality_rule_id=version.quality_rule_id,
                version_no=version.version_no,
                rule_type=version.rule_type.value,
                definition=json.loads(json.dumps(version.definition, sort_keys=True)),
                threshold=version.threshold,
                weight=version.weight,
                criticality=version.criticality.value,
                prepared_by_actor_id=version.prepared_by_actor_id,
                created_at=version.created_at,
            )
        )

    def _require_postgresql_audit(
        self,
        audit_outbox: PostgreSQLTransactionalAudit,
    ) -> None:
        if not isinstance(audit_outbox, PostgreSQLTransactionalAudit):
            raise RuleValidationError("PostgreSQL audit outbox is required.")

    def _require_updated(
        self,
        result: Any,
        operation: str = "",
    ) -> None:
        if result.rowcount != 1:
            raise RuleValidationError(f"Rule operation {operation} did not affect exactly one row.")


# ------------------------------------------------------------------
# Row-to-model conversion functions
# ------------------------------------------------------------------


def _row_to_rule(row: RowMapping) -> QualityRule:
    return QualityRule(
        quality_rule_id=row["quality_rule_id"],
        code=row["code"],
        name=row["name"],
        dataset_id=row["dataset_id"],
        field_ids=tuple(_json_loads(row["field_ids"])),
        primary_dimension=QualityDimension(row["primary_dimension"]),
        owner_user_id=row["owner_user_id"],
        status=RuleStatus(row["status"]),
    )


def _row_to_version(row: RowMapping) -> RuleVersion:
    return RuleVersion(
        rule_version_id=row["rule_version_id"],
        quality_rule_id=row["quality_rule_id"],
        version_no=row["version_no"],
        rule_type=RuleType(row["rule_type"]),
        definition=_json_loads(row["definition"]),
        threshold=row["threshold"],
        weight=row["weight"],
        criticality=RuleCriticality(row["criticality"]),
        prepared_by_actor_id=row["prepared_by_actor_id"],
        created_at=row["created_at"],
    )


def _row_to_test_result(row: RowMapping) -> RuleTestResult:
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
        created_at=row["created_at"],
    )


def _row_to_approval_request(row: RowMapping) -> RuleApprovalRequest:
    return RuleApprovalRequest(
        approval_request_id=row["approval_request_id"],
        rule_version_id=row["rule_version_id"],
        maker_actor_id=row["maker_actor_id"],
        checker_actor_id=row["checker_actor_id"],
        policy_version=row["policy_version"],
        status=RuleApprovalStatus(row["status"]),
        decision_reason_code=row["decision_reason_code"],
        requested_at=row["requested_at"],
        target_at=row.get("target_at"),
        expires_at=row.get("expires_at"),
        business_calendar_version=row["business_calendar_version"],
        decided_at=row.get("decided_at"),
    )


def _json_loads(value: Any) -> Any:
    if isinstance(value, (list, dict)):
        return value
    if isinstance(value, str):
        return json.loads(value)
    return {}