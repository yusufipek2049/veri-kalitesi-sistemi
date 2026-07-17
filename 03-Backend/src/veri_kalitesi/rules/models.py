"""Kural yönetimi domain modelleri."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4

from veri_kalitesi.identity import ActorType


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RuleType(str, Enum):
    REQUIRED = "REQUIRED"
    UNIQUE = "UNIQUE"
    RANGE = "RANGE"
    REGEX = "REGEX"
    FRESHNESS = "FRESHNESS"
    REFERENTIAL_INTEGRITY = "REFERENTIAL_INTEGRITY"
    CROSS_TABLE_CONSISTENCY = "CROSS_TABLE_CONSISTENCY"
    CUSTOM_SQL = "CUSTOM_SQL"


class RuleStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PASSIVE = "PASSIVE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    ARCHIVED = "ARCHIVED"


class QualityDimension(str, Enum):
    COMPLETENESS = "COMPLETENESS"
    ACCURACY = "ACCURACY"
    VALIDITY = "VALIDITY"
    CONSISTENCY = "CONSISTENCY"
    UNIQUENESS = "UNIQUENESS"
    TIMELINESS = "TIMELINESS"
    INTEGRITY = "INTEGRITY"


class RuleCriticality(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RuleTestStatus(str, Enum):
    SUCCESS = "SUCCESS"
    TECHNICAL_ERROR = "TECHNICAL_ERROR"


class RuleApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"


@dataclass(frozen=True)
class RuleApprovalPolicy:
    version: str
    actor_policy_version: str
    maker_roles: frozenset[str]
    checker_roles: frozenset[str]
    criticalities: frozenset[RuleCriticality] = field(
        default_factory=lambda: frozenset({RuleCriticality.CRITICAL})
    )
    allowed_actor_types: frozenset[ActorType] = field(
        default_factory=lambda: frozenset({ActorType.USER})
    )


@dataclass(frozen=True)
class RuleApprovalRequest:
    rule_version_id: str
    maker_actor_id: str
    policy_version: str
    status: RuleApprovalStatus = RuleApprovalStatus.PENDING
    checker_actor_id: str | None = None
    decision_reason_code: str | None = None
    approval_request_id: str = field(default_factory=lambda: str(uuid4()))
    requested_at: datetime = field(default_factory=utc_now)
    decided_at: datetime | None = None


@dataclass(frozen=True)
class QualityRule:
    code: str
    name: str
    dataset_id: str
    field_ids: tuple[str, ...]
    primary_dimension: QualityDimension
    owner_user_id: str
    status: RuleStatus = RuleStatus.DRAFT
    quality_rule_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(frozen=True)
class RuleVersion:
    quality_rule_id: str
    version_no: int
    rule_type: RuleType
    definition: Mapping[str, Any]
    threshold: float
    weight: float
    criticality: RuleCriticality
    prepared_by_actor_id: str = "LEGACY_UNKNOWN"
    rule_version_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "definition", _freeze(dict(self.definition)))


@dataclass(frozen=True)
class RuleTestOptions:
    limit: int = 10_000


@dataclass(frozen=True)
class RuleTestComputation:
    checked_count: int
    passed_count: int
    failed_count: int
    not_evaluated_count: int = 0


@dataclass(frozen=True)
class RuleTestResult:
    rule_version_id: str
    status: RuleTestStatus
    record_limit: int
    checked_count: int = 0
    passed_count: int = 0
    failed_count: int = 0
    not_evaluated_count: int = 0
    success_rate: float | None = None
    preview_score: float | None = None
    official_score_included: bool = False
    error_class: str | None = None
    message: str = ""
    rule_test_result_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=utc_now)


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list | tuple):
        return tuple(_freeze(item) for item in value)
    return value


def thaw(value: Any) -> Any:
    """Değişmez tanımı JSON ile saklanabilir değerlere dönüştürür."""
    if isinstance(value, Mapping):
        return {key: thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [thaw(item) for item in value]
    return value
