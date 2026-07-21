"""Dataset bazlı kısmi skor uygunluk politikası."""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from threading import RLock
from typing import Callable
from uuid import uuid4

from veri_kalitesi.audit import (
    AuditEventInput,
    AuditResult,
    PreparedAuditEvent,
    SQLiteTransactionalAudit,
)
from veri_kalitesi.identity import ActorContext, ActorType, is_trusted_actor_context
from veri_kalitesi.scoring.errors import (
    ScoringAuthorizationError,
    ScoringTechnicalError,
    ScoringValidationError,
)
from veri_kalitesi.scoring.models import utc_now


class PartialScorePolicyStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"
    EXPIRED = "EXPIRED"


class PartialScoreEligibility(str, Enum):
    OFFICIAL = "OFFICIAL"
    PROVISIONAL = "PROVISIONAL"


@dataclass(frozen=True)
class PartialScorePolicyAccessPolicy:
    version: str
    actor_policy_version: str
    maker_roles: frozenset[str]
    checker_roles: frozenset[str]
    allowed_actor_types: frozenset[ActorType] = field(
        default_factory=lambda: frozenset({ActorType.USER})
    )


@dataclass(frozen=True)
class DatasetPartialScorePolicy:
    dataset_id: str
    policy_version: str
    allow_official_partial_score: bool
    minimum_coverage_ratio: Decimal
    required_critical_rule_ids: tuple[str, ...]
    required_partitions: tuple[str, ...]
    maximum_missing_record_ratio: Decimal
    maximum_technical_error_ratio: Decimal
    minimum_successful_rule_ratio: Decimal
    effective_from: datetime
    approval_status: PartialScorePolicyStatus
    created_by: str
    approved_by: str | None = None
    audit_reference: str | None = None
    policy_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "required_critical_rule_ids",
            tuple(self.required_critical_rule_ids),
        )
        object.__setattr__(self, "required_partitions", tuple(self.required_partitions))


@dataclass(frozen=True)
class PartialExecutionFacts:
    dataset_id: str
    coverage_ratio: Decimal
    executed_rule_ids: tuple[str, ...]
    technical_error_rule_ids: tuple[str, ...]
    completed_partitions: tuple[str, ...]
    missing_record_ratio: Decimal
    total_rule_count: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "executed_rule_ids", tuple(self.executed_rule_ids))
        object.__setattr__(
            self,
            "technical_error_rule_ids",
            tuple(self.technical_error_rule_ids),
        )
        object.__setattr__(self, "completed_partitions", tuple(self.completed_partitions))


@dataclass(frozen=True)
class PartialScoreDecision:
    eligibility: PartialScoreEligibility
    reason_codes: tuple[str, ...]
    policy_version: str | None
    coverage_ratio: Decimal
    executed_rule_count: int
    not_executed_rule_count: int
    missing_partitions: tuple[str, ...]


class SQLiteDatasetPartialScorePolicyRepository:
    def __init__(
        self,
        database: str = ":memory:",
        *,
        connection: sqlite3.Connection | None = None,
    ) -> None:
        self.connection = connection or sqlite3.connect(database, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self._lock = RLock()
        self._create_schema()

    def _create_schema(self) -> None:
        try:
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS dataset_partial_score_policies (
                    policy_id TEXT PRIMARY KEY,
                    dataset_id TEXT NOT NULL,
                    policy_version TEXT NOT NULL,
                    allow_official_partial_score INTEGER NOT NULL,
                    minimum_coverage_ratio TEXT NOT NULL,
                    required_critical_rule_ids TEXT NOT NULL,
                    required_partitions TEXT NOT NULL,
                    maximum_missing_record_ratio TEXT NOT NULL,
                    maximum_technical_error_ratio TEXT NOT NULL,
                    minimum_successful_rule_ratio TEXT NOT NULL,
                    effective_from TEXT NOT NULL,
                    approval_status TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    approved_by TEXT,
                    audit_reference TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE (dataset_id, policy_version)
                )
                """
            )
            self.connection.commit()
        except sqlite3.DatabaseError as exc:
            raise ScoringTechnicalError(
                "Dataset partial score policy schema could not be initialized."
            ) from exc

    def save(self, policy: DatasetPartialScorePolicy) -> DatasetPartialScorePolicy:
        _validate_policy(policy)
        try:
            with self._lock, self.connection:
                self.connection.execute(
                    """
                    INSERT INTO dataset_partial_score_policies (
                        policy_id, dataset_id, policy_version,
                        allow_official_partial_score, minimum_coverage_ratio,
                        required_critical_rule_ids, required_partitions,
                        maximum_missing_record_ratio, maximum_technical_error_ratio,
                        minimum_successful_rule_ratio, effective_from, approval_status,
                        created_by, approved_by, audit_reference, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    _policy_values(policy),
                )
        except sqlite3.IntegrityError as exc:
            raise ScoringValidationError(
                "Dataset partial score policy identity or version conflicts."
            ) from exc
        except sqlite3.DatabaseError as exc:
            raise ScoringTechnicalError(
                "Dataset partial score policy could not be persisted."
            ) from exc
        return policy

    def save_with_audit(
        self,
        policy: DatasetPartialScorePolicy,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> DatasetPartialScorePolicy:
        if audit_outbox.connection is not self.connection:
            raise ScoringValidationError("Audit outbox must share the policy transaction.")
        _validate_policy(policy)
        try:
            with self._lock, self.connection:
                self.connection.execute(
                    """
                    INSERT INTO dataset_partial_score_policies (
                        policy_id, dataset_id, policy_version,
                        allow_official_partial_score, minimum_coverage_ratio,
                        required_critical_rule_ids, required_partitions,
                        maximum_missing_record_ratio, maximum_technical_error_ratio,
                        minimum_successful_rule_ratio, effective_from, approval_status,
                        created_by, approved_by, audit_reference, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    _policy_values(policy),
                )
                audit_outbox.stage(audit_event)
        except sqlite3.IntegrityError as exc:
            raise ScoringValidationError(
                "Dataset partial score policy identity or version conflicts."
            ) from exc
        except sqlite3.DatabaseError as exc:
            raise ScoringTechnicalError(
                "Dataset partial score policy and audit could not be persisted."
            ) from exc
        return self.get(policy.policy_id)

    def get(self, policy_id: str) -> DatasetPartialScorePolicy:
        if not policy_id.strip():
            raise ScoringValidationError("policy_id is required.")
        try:
            row = self.connection.execute(
                "SELECT * FROM dataset_partial_score_policies WHERE policy_id = ?",
                (policy_id,),
            ).fetchone()
        except sqlite3.DatabaseError as exc:
            raise ScoringTechnicalError("Dataset partial score policy could not be read.") from exc
        if row is None:
            raise ScoringValidationError("Dataset partial score policy was not found.")
        return _row_to_policy(row)

    def decide_with_audit(
        self,
        policy: DatasetPartialScorePolicy,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> DatasetPartialScorePolicy:
        if audit_outbox.connection is not self.connection:
            raise ScoringValidationError("Audit outbox must share the policy transaction.")
        _validate_policy(policy)
        try:
            with self._lock, self.connection:
                cursor = self.connection.execute(
                    """
                    UPDATE dataset_partial_score_policies
                    SET approval_status = ?, approved_by = ?, audit_reference = ?
                    WHERE policy_id = ? AND approval_status = ?
                    """,
                    (
                        policy.approval_status.value,
                        policy.approved_by,
                        policy.audit_reference,
                        policy.policy_id,
                        PartialScorePolicyStatus.PENDING.value,
                    ),
                )
                if cursor.rowcount != 1:
                    raise ScoringValidationError("Dataset partial score policy is not pending.")
                audit_outbox.stage(audit_event)
        except sqlite3.DatabaseError as exc:
            raise ScoringTechnicalError(
                "Dataset partial score policy decision and audit could not be persisted."
            ) from exc
        return self.get(policy.policy_id)

    def list_policies(self, dataset_id: str) -> list[DatasetPartialScorePolicy]:
        if not dataset_id.strip():
            raise ScoringValidationError("dataset_id is required.")
        try:
            rows = self.connection.execute(
                """
                SELECT * FROM dataset_partial_score_policies
                WHERE dataset_id = ?
                ORDER BY effective_from, created_at, policy_version
                """,
                (dataset_id,),
            ).fetchall()
        except sqlite3.DatabaseError as exc:
            raise ScoringTechnicalError(
                "Dataset partial score policies could not be read."
            ) from exc
        return [_row_to_policy(row) for row in rows]

    def resolve_effective(
        self,
        dataset_id: str,
        *,
        at: datetime,
    ) -> DatasetPartialScorePolicy | None:
        if not dataset_id.strip():
            raise ScoringValidationError("dataset_id is required.")
        _validate_utc_time(at, "Evaluation time")
        try:
            row = self.connection.execute(
                """
                SELECT * FROM dataset_partial_score_policies
                WHERE dataset_id = ?
                  AND approval_status = ?
                  AND effective_from <= ?
                ORDER BY effective_from DESC, created_at DESC, policy_version DESC
                LIMIT 1
                """,
                (dataset_id, PartialScorePolicyStatus.APPROVED.value, at.isoformat()),
            ).fetchone()
        except sqlite3.DatabaseError as exc:
            raise ScoringTechnicalError(
                "Effective dataset partial score policy could not be read."
            ) from exc
        return _row_to_policy(row) if row is not None else None


class DatasetPartialScorePolicyService:
    def __init__(self, repository: SQLiteDatasetPartialScorePolicyRepository) -> None:
        self.repository = repository

    def evaluate(
        self,
        facts: PartialExecutionFacts,
        *,
        at: datetime,
    ) -> PartialScoreDecision:
        _validate_facts(facts)
        policy = self.repository.resolve_effective(facts.dataset_id, at=at)
        if policy is None:
            return _decision(
                facts,
                eligibility=PartialScoreEligibility.PROVISIONAL,
                reason_codes=("POLICY_NOT_FOUND",),
                policy=None,
            )

        executed = frozenset(facts.executed_rule_ids)
        technical_errors = frozenset(facts.technical_error_rule_ids)
        completed_partitions = frozenset(facts.completed_partitions)
        missing_partitions = tuple(
            partition
            for partition in policy.required_partitions
            if partition not in completed_partitions
        )
        successful_rule_ratio = Decimal(len(executed)) / Decimal(facts.total_rule_count)
        technical_error_ratio = Decimal(len(technical_errors)) / Decimal(facts.total_rule_count)
        reasons: list[str] = []
        if not policy.allow_official_partial_score:
            reasons.append("OFFICIAL_PARTIAL_DISABLED")
        if facts.coverage_ratio < policy.minimum_coverage_ratio:
            reasons.append("COVERAGE_BELOW_MINIMUM")
        if not frozenset(policy.required_critical_rule_ids).issubset(executed):
            reasons.append("REQUIRED_CRITICAL_RULE_MISSING")
        if missing_partitions:
            reasons.append("REQUIRED_PARTITION_MISSING")
        if facts.missing_record_ratio > policy.maximum_missing_record_ratio:
            reasons.append("MISSING_RECORD_RATIO_EXCEEDED")
        if technical_error_ratio > policy.maximum_technical_error_ratio:
            reasons.append("TECHNICAL_ERROR_RATIO_EXCEEDED")
        if successful_rule_ratio < policy.minimum_successful_rule_ratio:
            reasons.append("SUCCESSFUL_RULE_RATIO_BELOW_MINIMUM")
        return _decision(
            facts,
            eligibility=(
                PartialScoreEligibility.OFFICIAL
                if not reasons
                else PartialScoreEligibility.PROVISIONAL
            ),
            reason_codes=tuple(reasons) if reasons else ("ALL_POLICY_CONDITIONS_MET",),
            policy=policy,
            missing_partitions=missing_partitions,
        )


class DatasetPartialScorePolicyLifecycleService:
    def __init__(
        self,
        repository: SQLiteDatasetPartialScorePolicyRepository,
        *,
        transactional_audit: SQLiteTransactionalAudit,
        access_policy: PartialScorePolicyAccessPolicy,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self.repository = repository
        self.transactional_audit = transactional_audit
        self.access_policy = access_policy
        self.clock = clock
        _validate_access_policy(access_policy)

    def create_and_submit(
        self,
        *,
        actor_context: ActorContext | None,
        dataset_id: str,
        policy_version: str,
        allow_official_partial_score: bool,
        minimum_coverage_ratio: Decimal,
        required_critical_rule_ids: tuple[str, ...],
        required_partitions: tuple[str, ...],
        maximum_missing_record_ratio: Decimal,
        maximum_technical_error_ratio: Decimal,
        minimum_successful_rule_ratio: Decimal,
        effective_from: datetime,
    ) -> DatasetPartialScorePolicy:
        now = _clock_value(self.clock)
        context = self._authorize(
            actor_context,
            required_roles=self.access_policy.maker_roles,
            dataset_id=dataset_id,
            now=now,
        )
        policy = DatasetPartialScorePolicy(
            dataset_id=dataset_id,
            policy_version=policy_version,
            allow_official_partial_score=allow_official_partial_score,
            minimum_coverage_ratio=minimum_coverage_ratio,
            required_critical_rule_ids=required_critical_rule_ids,
            required_partitions=required_partitions,
            maximum_missing_record_ratio=maximum_missing_record_ratio,
            maximum_technical_error_ratio=maximum_technical_error_ratio,
            minimum_successful_rule_ratio=minimum_successful_rule_ratio,
            effective_from=effective_from,
            approval_status=PartialScorePolicyStatus.PENDING,
            created_by=context.actor_id,
            created_at=now,
        )
        _validate_policy(policy)
        event = AuditEventInput(
            actor_id=context.actor_id,
            actor_type=context.actor_type.value,
            correlation_id=context.correlation_id,
            action="PARTIAL_SCORE_POLICY_APPROVAL_REQUESTED",
            object_type="DatasetPartialScorePolicy",
            object_id=policy.policy_id,
            result=AuditResult.SUCCESS,
            reason_code="PARTIAL_SCORE_POLICY_APPROVAL_REQUESTED",
            old_values={},
            new_values=_policy_audit_values(policy, self.access_policy.version),
            occurred_at=now,
            session_id=context.session_id,
        )
        prepared = self.transactional_audit.prepare(event)
        stored = self.repository.save_with_audit(
            replace(policy, audit_reference=prepared.event_id),
            audit_event=prepared,
            audit_outbox=self.transactional_audit,
        )
        self.transactional_audit.publish_pending()
        return stored

    def decide(
        self,
        *,
        actor_context: ActorContext | None,
        policy_id: str,
        decision: str,
        reason_code: str,
    ) -> DatasetPartialScorePolicy:
        now = _clock_value(self.clock)
        current = self.repository.get(policy_id)
        context = self._authorize(
            actor_context,
            required_roles=self.access_policy.checker_roles,
            dataset_id=current.dataset_id,
            now=now,
        )
        if current.approval_status is not PartialScorePolicyStatus.PENDING:
            raise ScoringValidationError("Dataset partial score policy is not pending.")
        if current.created_by == context.actor_id:
            raise ScoringAuthorizationError(
                "Policy maker cannot decide the same partial score policy."
            )
        status = _parse_decision(decision)
        normalized_reason = _validate_reason_code(reason_code)
        event = AuditEventInput(
            actor_id=context.actor_id,
            actor_type=context.actor_type.value,
            correlation_id=context.correlation_id,
            action="PARTIAL_SCORE_POLICY_APPROVAL_DECIDED",
            object_type="DatasetPartialScorePolicy",
            object_id=current.policy_id,
            result=AuditResult.SUCCESS,
            reason_code=normalized_reason,
            old_values=_policy_audit_values(current, self.access_policy.version),
            new_values={
                **_policy_audit_values(current, self.access_policy.version),
                "status": status.value,
            },
            occurred_at=now,
            session_id=context.session_id,
        )
        prepared = self.transactional_audit.prepare(event)
        decided = replace(
            current,
            approval_status=status,
            approved_by=(context.actor_id if status is PartialScorePolicyStatus.APPROVED else None),
            audit_reference=prepared.event_id,
        )
        stored = self.repository.decide_with_audit(
            decided,
            audit_event=prepared,
            audit_outbox=self.transactional_audit,
        )
        self.transactional_audit.publish_pending()
        return stored

    def _authorize(
        self,
        context: ActorContext | None,
        *,
        required_roles: frozenset[str],
        dataset_id: str,
        now: datetime,
    ) -> ActorContext:
        if not is_trusted_actor_context(context):
            raise ScoringAuthorizationError("Trusted actor context is required.")
        assert context is not None
        if context.issued_at > now or context.expires_at <= now:
            raise ScoringAuthorizationError("Actor context is not currently valid.")
        if context.policy_version != self.access_policy.actor_policy_version:
            raise ScoringAuthorizationError("Actor context policy version is not accepted.")
        if context.actor_type not in self.access_policy.allowed_actor_types:
            raise ScoringAuthorizationError("Actor type is not allowed for policy approval.")
        if context.privileged:
            raise ScoringAuthorizationError(
                "Privileged context is not allowed for policy approval."
            )
        if context.roles.isdisjoint(required_roles):
            raise ScoringAuthorizationError("Actor does not have the required policy role.")
        if not context.can_view_enterprise and dataset_id not in context.permitted_dataset_ids:
            raise ScoringAuthorizationError("Actor does not have the required dataset scope.")
        return context


def _decision(
    facts: PartialExecutionFacts,
    *,
    eligibility: PartialScoreEligibility,
    reason_codes: tuple[str, ...],
    policy: DatasetPartialScorePolicy | None,
    missing_partitions: tuple[str, ...] = (),
) -> PartialScoreDecision:
    return PartialScoreDecision(
        eligibility=eligibility,
        reason_codes=reason_codes,
        policy_version=policy.policy_version if policy else None,
        coverage_ratio=facts.coverage_ratio,
        executed_rule_count=len(facts.executed_rule_ids),
        not_executed_rule_count=facts.total_rule_count - len(facts.executed_rule_ids),
        missing_partitions=missing_partitions,
    )


def _validate_policy(policy: DatasetPartialScorePolicy) -> None:
    if not policy.policy_id.strip() or not policy.dataset_id.strip():
        raise ScoringValidationError("Policy and dataset identities are required.")
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", policy.policy_version):
        raise ScoringValidationError("Partial score policy version is invalid.")
    if not isinstance(policy.allow_official_partial_score, bool):
        raise ScoringValidationError("Official partial score flag must be boolean.")
    if not isinstance(policy.approval_status, PartialScorePolicyStatus):
        raise ScoringValidationError("Partial score policy approval status is invalid.")
    for name, value in (
        ("minimum coverage ratio", policy.minimum_coverage_ratio),
        ("maximum missing record ratio", policy.maximum_missing_record_ratio),
        ("maximum technical error ratio", policy.maximum_technical_error_ratio),
        ("minimum successful rule ratio", policy.minimum_successful_rule_ratio),
    ):
        _validate_ratio(value, name)
    _validate_identifiers(policy.required_critical_rule_ids, "critical rule")
    _validate_identifiers(policy.required_partitions, "required partition")
    _validate_utc_time(policy.effective_from, "Effective time")
    _validate_utc_time(policy.created_at, "Creation time")
    if not policy.created_by.strip():
        raise ScoringValidationError("Policy creator is required.")
    if policy.approval_status is PartialScorePolicyStatus.APPROVED:
        if (
            not policy.approved_by
            or not policy.approved_by.strip()
            or not policy.audit_reference
            or not policy.audit_reference.strip()
        ):
            raise ScoringValidationError(
                "Approved partial score policy requires approver and audit reference."
            )
        if policy.approved_by == policy.created_by:
            raise ScoringValidationError(
                "Partial score policy creator cannot approve the same policy."
            )


def _validate_facts(facts: PartialExecutionFacts) -> None:
    if not facts.dataset_id.strip():
        raise ScoringValidationError("dataset_id is required.")
    _validate_ratio(facts.coverage_ratio, "coverage ratio")
    _validate_ratio(facts.missing_record_ratio, "missing record ratio")
    _validate_identifiers(facts.executed_rule_ids, "executed rule")
    _validate_identifiers(facts.technical_error_rule_ids, "technical error rule")
    _validate_identifiers(facts.completed_partitions, "completed partition")
    if (
        isinstance(facts.total_rule_count, bool)
        or not isinstance(facts.total_rule_count, int)
        or facts.total_rule_count <= 0
    ):
        raise ScoringValidationError("Total rule count must be a positive integer.")
    executed = set(facts.executed_rule_ids)
    technical = set(facts.technical_error_rule_ids)
    if executed & technical:
        raise ScoringValidationError(
            "Executed and technical error rule identifiers must be disjoint."
        )
    if len(executed | technical) > facts.total_rule_count:
        raise ScoringValidationError("Rule facts exceed total rule count.")


def _validate_ratio(value: Decimal, name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or not Decimal(0) <= value <= 1:
        raise ScoringValidationError(f"{name.capitalize()} must be between zero and one.")


def _validate_identifiers(values: tuple[str, ...], name: str) -> None:
    if len(values) != len(set(values)) or any(
        not isinstance(value, str) or not value.strip() for value in values
    ):
        raise ScoringValidationError(f"{name.capitalize()} identifiers must be unique and valid.")


def _validate_access_policy(policy: PartialScorePolicyAccessPolicy) -> None:
    if not policy.version.strip() or not policy.actor_policy_version.strip():
        raise ScoringValidationError("Partial score access policy versions are required.")
    if not policy.maker_roles or not policy.checker_roles:
        raise ScoringValidationError("Partial score maker and checker roles are required.")
    if any(not role.strip() for role in (*policy.maker_roles, *policy.checker_roles)):
        raise ScoringValidationError("Partial score policy roles must not be blank.")
    if not policy.allowed_actor_types:
        raise ScoringValidationError("At least one policy actor type is required.")


def _parse_decision(value: str) -> PartialScorePolicyStatus:
    normalized = value.strip().upper()
    decisions = {
        "APPROVE": PartialScorePolicyStatus.APPROVED,
        "REJECT": PartialScorePolicyStatus.REJECTED,
    }
    if normalized not in decisions:
        raise ScoringValidationError("Partial score policy decision is invalid.")
    return decisions[normalized]


def _validate_reason_code(value: str) -> str:
    normalized = value.strip().upper()
    if not re.fullmatch(r"[A-Z0-9_.-]{1,120}", normalized):
        raise ScoringValidationError("Partial score policy reason code is invalid.")
    return normalized


def _clock_value(clock: Callable[[], datetime]) -> datetime:
    value = clock()
    _validate_utc_time(value, "Policy lifecycle time")
    return value


def _policy_audit_values(
    policy: DatasetPartialScorePolicy,
    approval_policy_version: str,
) -> dict[str, str | int | bool]:
    return {
        "dataset_id": policy.dataset_id,
        "policy_version": policy.policy_version,
        "approval_policy_version": approval_policy_version,
        "status": policy.approval_status.value,
        "allow_official_partial_score": policy.allow_official_partial_score,
        "minimum_coverage_ratio": str(policy.minimum_coverage_ratio),
        "required_critical_rule_count": len(policy.required_critical_rule_ids),
        "required_partition_count": len(policy.required_partitions),
        "maximum_missing_record_ratio": str(policy.maximum_missing_record_ratio),
        "maximum_technical_error_ratio": str(policy.maximum_technical_error_ratio),
        "minimum_successful_rule_ratio": str(policy.minimum_successful_rule_ratio),
        "effective_from": policy.effective_from.isoformat(),
    }


def _validate_utc_time(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ScoringValidationError(f"{name} must be UTC.")


def _policy_values(policy: DatasetPartialScorePolicy) -> tuple[object, ...]:
    return (
        policy.policy_id,
        policy.dataset_id,
        policy.policy_version,
        1 if policy.allow_official_partial_score else 0,
        str(policy.minimum_coverage_ratio),
        json.dumps(policy.required_critical_rule_ids),
        json.dumps(policy.required_partitions),
        str(policy.maximum_missing_record_ratio),
        str(policy.maximum_technical_error_ratio),
        str(policy.minimum_successful_rule_ratio),
        policy.effective_from.isoformat(),
        policy.approval_status.value,
        policy.created_by,
        policy.approved_by,
        policy.audit_reference,
        policy.created_at.isoformat(),
    )


def _row_to_policy(row: sqlite3.Row) -> DatasetPartialScorePolicy:
    try:
        policy = DatasetPartialScorePolicy(
            policy_id=row["policy_id"],
            dataset_id=row["dataset_id"],
            policy_version=row["policy_version"],
            allow_official_partial_score=bool(row["allow_official_partial_score"]),
            minimum_coverage_ratio=Decimal(row["minimum_coverage_ratio"]),
            required_critical_rule_ids=tuple(json.loads(row["required_critical_rule_ids"])),
            required_partitions=tuple(json.loads(row["required_partitions"])),
            maximum_missing_record_ratio=Decimal(row["maximum_missing_record_ratio"]),
            maximum_technical_error_ratio=Decimal(row["maximum_technical_error_ratio"]),
            minimum_successful_rule_ratio=Decimal(row["minimum_successful_rule_ratio"]),
            effective_from=datetime.fromisoformat(row["effective_from"]),
            approval_status=PartialScorePolicyStatus(row["approval_status"]),
            created_by=row["created_by"],
            approved_by=row["approved_by"],
            audit_reference=row["audit_reference"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )
        _validate_policy(policy)
        return policy
    except (
        TypeError,
        ValueError,
        KeyError,
        json.JSONDecodeError,
        ScoringValidationError,
    ) as exc:
        raise ScoringTechnicalError("Stored partial score policy payload is invalid.") from exc
