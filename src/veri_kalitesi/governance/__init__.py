"""Sistem geneli maker-checker yönetişim onay merkezi.

Domain onay kayıtları (kural onayları, veri kaynağı aktivasyon talepleri)
kendi tablolarında kalır; bu modül salt okunur adaptörlerle ortak bir
görev merkezi projeksiyonu üretir. Yeni domain'ler (sahiplik vb.) ortak
``governance_approval_requests`` tablosuna yazar.
"""

from veri_kalitesi.governance.errors import (
    GovernanceAuthorizationError,
    GovernanceConflictError,
    GovernanceError,
    GovernanceNotFoundError,
    GovernanceValidationError,
)
from veri_kalitesi.governance.models import (
    GOVERNANCE_REASON_CODES,
    GOVERNANCE_REQUEST_DOMAINS,
    GovernanceApprovalItem,
    GovernanceApprovalPolicy,
    GovernanceApprovalRequest,
    GovernanceApprovalStatus,
    GovernanceDomain,
    GovernanceRequestStatus,
    GovernanceRequestType,
)
from veri_kalitesi.governance.query import (
    GovernanceApprovalQueryService,
    GovernanceCenterReader,
    GovernanceQueryAuthorizationError,
    GovernanceQueryError,
    GovernanceQueryTechnicalError,
    GovernanceRuleApprovalReader,
    GovernanceSourceApprovalReader,
    GovernanceView,
    center_request_to_item,
)
from veri_kalitesi.governance.repository import (
    PostgreSQLGovernanceApprovalRepository,
)
from veri_kalitesi.governance.service import (
    GovernanceApprovalCommandService,
    GovernanceCatalog,
    GovernanceExecutionWriter,
    GovernanceMetadataWriter,
    GovernanceOwnershipWriter,
    PostgreSQLDatasetOwnershipWriter,
    PostgreSQLMetadataGovernanceWriter,
)

__all__ = [
    "GOVERNANCE_REASON_CODES",
    "GOVERNANCE_REQUEST_DOMAINS",
    "GovernanceApprovalCommandService",
    "GovernanceApprovalItem",
    "GovernanceApprovalPolicy",
    "GovernanceApprovalQueryService",
    "GovernanceApprovalRequest",
    "GovernanceApprovalStatus",
    "GovernanceAuthorizationError",
    "GovernanceCatalog",
    "GovernanceCenterReader",
    "GovernanceConflictError",
    "GovernanceDomain",
    "GovernanceError",
    "GovernanceExecutionWriter",
    "GovernanceMetadataWriter",
    "GovernanceNotFoundError",
    "GovernanceOwnershipWriter",
    "GovernanceQueryAuthorizationError",
    "GovernanceQueryError",
    "GovernanceQueryTechnicalError",
    "GovernanceRequestStatus",
    "GovernanceRequestType",
    "GovernanceRuleApprovalReader",
    "GovernanceSourceApprovalReader",
    "GovernanceValidationError",
    "GovernanceView",
    "PostgreSQLDatasetOwnershipWriter",
    "PostgreSQLGovernanceApprovalRepository",
    "PostgreSQLMetadataGovernanceWriter",
    "center_request_to_item",
]
