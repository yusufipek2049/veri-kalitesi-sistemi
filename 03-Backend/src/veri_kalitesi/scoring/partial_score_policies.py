"""Dataset bazlı kısmi skor uygunluk politikası."""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from threading import RLock
from uuid import uuid4

from veri_kalitesi.scoring.errors import ScoringTechnicalError, ScoringValidationError
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
    def __init__(self, database: str = ":memory:") -> None:
        self.connection = sqlite3.connect(database, check_same_thread=False)
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
