"""Yönetişim onay merkezi ortak modelleri.

Bu modeller domain onay tablolarını yeniden yazmaz; kural onayları ve veri
kaynağı aktivasyon talepleri için tek biçimli, veri-minimum bir projeksiyon
tanımlar. Yeni domain'ler (sahiplik vb.) ortak GovernanceApprovalRequest
varlığına yazar.
"""

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


class GovernanceDomain(str, Enum):
    QUALITY_RULE = "QUALITY_RULE"
    DATA_SOURCE = "DATA_SOURCE"
    DATA_OWNERSHIP = "DATA_OWNERSHIP"
    METADATA_AND_CLASSIFICATION = "METADATA_AND_CLASSIFICATION"
    EXECUTION = "EXECUTION"


class GovernanceRequestType(str, Enum):
    RULE_APPROVAL = "RULE_APPROVAL"
    SOURCE_ACTIVATION = "SOURCE_ACTIVATION"
    SOURCE_DEACTIVATION = "SOURCE_DEACTIVATION"
    DATASET_OWNER_ASSIGN = "DATASET_OWNER_ASSIGN"
    DATASET_OWNER_CHANGE = "DATASET_OWNER_CHANGE"
    METADATA_CRITICAL_CHANGE = "METADATA_CRITICAL_CHANGE"
    FIELD_SENSITIVITY_MARK = "FIELD_SENSITIVITY_MARK"
    EXECUTION_MANUAL_START = "EXECUTION_MANUAL_START"
    EXECUTION_CANCEL = "EXECUTION_CANCEL"
    DEAD_LETTER_REPROCESS = "DEAD_LETTER_REPROCESS"


class GovernanceRequestStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"
    EXPIRED = "EXPIRED"
    INVALIDATED = "INVALIDATED"
    APPLIED = "APPLIED"
    APPLICATION_FAILED = "APPLICATION_FAILED"


class GovernanceApprovalStatus(str, Enum):
    """Ortak governance tablosundaki talep yaşam döngüsü durumları."""

    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"
    EXPIRED = "EXPIRED"
    INVALIDATED = "INVALIDATED"
    APPLIED = "APPLIED"
    APPLICATION_FAILED = "APPLICATION_FAILED"


#: Kontrollü gerekçe kodu sözlüğü (fail-closed).
GOVERNANCE_REASON_CODES = frozenset(
    {
        "OWNERSHIP.ASSIGN",
        "OWNERSHIP.TRANSFER",
        "OWNERSHIP.CORRECTION",
        "OWNERSHIP.VERIFIED",
        "OWNERSHIP.INSUFFICIENT.EVIDENCE",
        "OWNERSHIP.SCOPE.MISMATCH",
        "OWNERSHIP.POLICY.VIOLATION",
        "METADATA.CRITICALITY.CHANGE",
        "METADATA.STATUS.CHANGE",
        "METADATA.SENSITIVITY.MARK",
        "METADATA.CLASSIFICATION.CHANGE",
        "METADATA.VERIFIED",
        "METADATA.INSUFFICIENT.EVIDENCE",
        "MAKER.WITHDRAWAL",
        "GOVERNANCE.APPROVAL.EXPIRED",
        "GOVERNANCE.OBJECT.CHANGED",
        "EXECUTION.MANUAL.START",
        "EXECUTION.CANCEL",
        "EXECUTION.DEAD.LETTER.REPROCESS",
        "EXECUTION.VERIFIED",
        "EXECUTION.INSUFFICIENT.EVIDENCE",
    }
)


#: Merkezi tabloda saklanan talep türlerinin domain projeksiyonu.
GOVERNANCE_REQUEST_DOMAINS: Mapping[GovernanceRequestType, GovernanceDomain] = MappingProxyType(
    {
        GovernanceRequestType.DATASET_OWNER_ASSIGN: GovernanceDomain.DATA_OWNERSHIP,
        GovernanceRequestType.DATASET_OWNER_CHANGE: GovernanceDomain.DATA_OWNERSHIP,
        GovernanceRequestType.METADATA_CRITICAL_CHANGE: (
            GovernanceDomain.METADATA_AND_CLASSIFICATION
        ),
        GovernanceRequestType.FIELD_SENSITIVITY_MARK: (
            GovernanceDomain.METADATA_AND_CLASSIFICATION
        ),
        GovernanceRequestType.EXECUTION_MANUAL_START: GovernanceDomain.EXECUTION,
        GovernanceRequestType.EXECUTION_CANCEL: GovernanceDomain.EXECUTION,
        GovernanceRequestType.DEAD_LETTER_REPROCESS: GovernanceDomain.EXECUTION,
    }
)


@dataclass(frozen=True)
class GovernanceApprovalPolicy:
    """Ortak yönetişim talepleri için rol, kapsam ve aktör politikası."""

    version: str
    actor_policy_version: str
    maker_roles: frozenset[str]
    checker_roles: frozenset[str]
    applier_roles: frozenset[str] = field(default_factory=frozenset)
    allowed_actor_types: frozenset[ActorType] = field(
        default_factory=lambda: frozenset({ActorType.USER})
    )


@dataclass(frozen=True)
class GovernanceApprovalRequest:
    """Ortak governance tablosundaki tek bir maker-checker talebi."""

    request_type: GovernanceRequestType
    object_type: str
    object_id: str
    scope_type: str
    scope_id: str
    scope_version: int
    maker_actor_id: str
    maker_roles: tuple[str, ...]
    policy_version: str
    correlation_id: str
    change_summary: Mapping[str, Any]
    status: GovernanceApprovalStatus = GovernanceApprovalStatus.SUBMITTED
    approval_request_id: str = field(default_factory=lambda: str(uuid4()))
    checker_actor_id: str | None = None
    checker_role: str | None = None
    reason_code: str | None = None
    before_snapshot_reference: str | None = None
    after_snapshot_reference: str | None = None
    evidence_references: tuple[str, ...] = ()
    requested_at: datetime = field(default_factory=utc_now)
    expires_at: datetime | None = None
    decided_at: datetime | None = None
    applied_at: datetime | None = None
    version: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "change_summary", MappingProxyType(dict(self.change_summary)))


@dataclass(frozen=True)
class GovernanceApprovalItem:
    """Tek bir yönetişim talebinin ortak, salt okunur izdüşümü."""

    approval_request_id: str
    domain: GovernanceDomain
    request_type: GovernanceRequestType
    status: GovernanceRequestStatus
    object_type: str
    object_id: str
    object_name: str
    scope_type: str
    scope_id: str
    maker_actor_id: str
    checker_actor_id: str | None
    reason_code: str | None
    requested_at: datetime
    decided_at: datetime | None
    expires_at: datetime | None
    policy_version: str
    available_actions: tuple[str, ...] = ()
    change_summary: Mapping[str, Any] = field(default_factory=dict)
