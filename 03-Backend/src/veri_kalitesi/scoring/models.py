"""Kural skoru ve hesaplama durumu domain modelleri."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4

from veri_kalitesi.data_sources.models import Criticality
from veri_kalitesi.executions.models import MeasurementStatus
from veri_kalitesi.identity import ActorType
from veri_kalitesi.rules.models import QualityDimension


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ScoreScopeType(str, Enum):
    RULE = "RULE"
    DATASET = "DATASET"
    DIMENSION = "DIMENSION"
    SOURCE = "SOURCE"
    ENTERPRISE = "ENTERPRISE"


class ScoreStatus(str, Enum):
    CALCULATED = "CALCULATED"
    NOT_CALCULATED = "NOT_CALCULATED"
    NO_DATA = "NO_DATA"
    PARTIAL = "PARTIAL"
    NOT_CALCULATED_TECHNICAL_ERROR = "NOT_CALCULATED_TECHNICAL_ERROR"
    CONFIG_ERROR = "CONFIG_ERROR"


class ScoreLevel(str, Enum):
    GOOD = "GOOD"
    ACCEPTABLE = "ACCEPTABLE"
    RISKY = "RISKY"
    CRITICAL = "CRITICAL"


class ScoringApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class ScoringApprovalPolicy:
    version: str
    actor_policy_version: str
    maker_roles: frozenset[str]
    checker_roles: frozenset[str]
    allowed_actor_types: frozenset[ActorType] = field(
        default_factory=lambda: frozenset({ActorType.USER})
    )
    require_enterprise_scope: bool = True


@dataclass(frozen=True)
class ThresholdSet:
    version: str
    critical_upper_exclusive: Decimal = Decimal("50.00")
    risky_upper_exclusive: Decimal = Decimal("75.00")
    acceptable_upper_exclusive: Decimal = Decimal("90.00")


DEFAULT_THRESHOLD_SET = ThresholdSet(version="DEFAULT_THRESHOLDS_V1")


@dataclass(frozen=True)
class ScoringConfiguration:
    version: str
    threshold_set: ThresholdSet
    dimension_weights: Mapping[QualityDimension, Decimal]
    criticality_weights: Mapping[Criticality, Decimal]
    created_by: str
    configuration_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=utc_now)
    is_active: bool = False
    activated_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "dimension_weights",
            MappingProxyType(dict(self.dimension_weights)),
        )
        object.__setattr__(
            self,
            "criticality_weights",
            MappingProxyType(dict(self.criticality_weights)),
        )


@dataclass(frozen=True)
class ScoringConfigurationApproval:
    configuration_id: str
    maker_actor_id: str
    policy_version: str
    status: ScoringApprovalStatus = ScoringApprovalStatus.PENDING
    checker_actor_id: str | None = None
    decision_reason_code: str | None = None
    approval_id: str = field(default_factory=lambda: str(uuid4()))
    requested_at: datetime = field(default_factory=utc_now)
    decided_at: datetime | None = None


def default_dimension_weights() -> dict[QualityDimension, Decimal]:
    return {dimension: Decimal("1.0") for dimension in QualityDimension}


def default_criticality_weights() -> dict[Criticality, Decimal]:
    return {criticality: Decimal("1.0") for criticality in Criticality}


@dataclass(frozen=True)
class QualityScore:
    execution_id: str
    rule_version_id: str | None
    scope_id: str | None
    score_status: ScoreStatus
    calculation_details: Mapping[str, Any]
    measurement_status: MeasurementStatus | None = None
    rule_result_id: str | None = None
    score_value: Decimal | None = None
    level: ScoreLevel | None = None
    scope_type: ScoreScopeType = ScoreScopeType.RULE
    quality_score_id: str = field(default_factory=lambda: str(uuid4()))
    calculated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "calculation_details",
            _freeze(dict(self.calculation_details)),
        )


def is_official_score(score: QualityScore) -> bool:
    """Skorun resmî agregasyon, trend ve raporlama için uygunluğunu döndürür."""

    explicit = score.calculation_details.get("included_in_official_aggregation")
    if isinstance(explicit, bool):
        return explicit and score.score_value is not None
    return score.score_status is ScoreStatus.CALCULATED and score.score_value is not None


def is_official_observation(score: QualityScore) -> bool:
    """Provizyonel kısmi sonucu resmî trend ve rapor gözleminden ayırır."""

    if score.score_status is ScoreStatus.PARTIAL:
        return is_official_score(score)
    return True


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list | tuple):
        return tuple(_freeze(item) for item in value)
    return value


def thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [thaw(item) for item in value]
    return value
