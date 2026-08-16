"""Dashboard API bileşiminde kullanılan alan bazlı bağımlılık grupları."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from fastapi import Request

from veri_kalitesi.api.bff import BffSessionBoundary
from veri_kalitesi.api.catalog_router import (
    CatalogQueryService,
    MetadataCommandService,
)
from veri_kalitesi.api.data_sources_router import DataSourceMutationService
from veri_kalitesi.api.executions_router import (
    ExecutionCancelService,
    ExecutionGovernanceGuard,
    ExecutionStartService,
)
from veri_kalitesi.api.health import ReadinessCheck
from veri_kalitesi.api.identity import ActorContextResolver, DevelopmentUserRegistry
from veri_kalitesi.api.issues_router import (
    IssueAssignmentService,
    IssueAssigneeOptionProvider,
    IssueClosureService,
    IssueCreationService,
    IssueEvidenceUploadService,
    IssueInvestigationService,
    IssueResolutionService,
    IssueVerificationService,
)
from veri_kalitesi.api.notifications_router import (
    NotificationDeliveryCommand,
    NotificationQuery,
)
from veri_kalitesi.api.rules_router import RuleCreatorService, RuleMutationService
from veri_kalitesi.audit.service import AuditQueryService
from veri_kalitesi.dashboard.service import DashboardQueryService
from veri_kalitesi.data_sources.models import DataSource, Dataset
from veri_kalitesi.data_sources.query import DataSourceQueryService
from veri_kalitesi.executions.query import ExecutionQueryService
from veri_kalitesi.governance import (
    GovernanceApprovalCommandService,
    GovernanceApprovalQueryService,
)
from veri_kalitesi.identity import ActorContext
from veri_kalitesi.issues import (
    IssueEvidenceService,
    IssueInvestigationEvidenceService,
    IssueQueryService,
)
from veri_kalitesi.jobs.models import BackgroundJob
from veri_kalitesi.rules import RuleQueryService
from veri_kalitesi.scoring.query import ScoreQueryService
from veri_kalitesi.dashboard.rule_health import RuleHealthQueryService
from veri_kalitesi.dashboard.metadata_health import MetadataHealthQueryService
from veri_kalitesi.dashboard.issue_performance import IssuePerformanceQueryService
from veri_kalitesi.dashboard.scoring_policy_impact import ScoringPolicyImpactQueryService
from veri_kalitesi.reporting.service import ReportQueryService


class StateChangeBoundary(Protocol):
    """Durum değiştiren HTTP isteklerini koruyan kimlik sınırı."""

    def protect_state_changing(self, request: Request) -> ActorContext | None: ...


class CatalogDatasetReader(Protocol):
    """Execution dataset çözümleyicisinin tükettiği katalog yüzeyi."""

    def get_data_source(self, data_source_id: str) -> DataSource: ...

    def get_dataset(self, dataset_id: str) -> Dataset: ...

    def list_datasets(self, data_source_id: str) -> list[Dataset]: ...


class JobQueueReader(Protocol):
    """Execution iş bilgisi çözümleyicisinin tükettiği kuyruk yüzeyi."""

    def get_by_id(self, job_id: str) -> BackgroundJob | None: ...


@dataclass(frozen=True)
class ActorResolverIdentity:
    """Doğrudan actor-context çözümleyicisi kullanan kimlik bileşimi."""

    resolver: ActorContextResolver


@dataclass(frozen=True)
class BffSessionIdentity:
    """Cookie ve CSRF korumalı BFF oturumu kullanan kimlik bileşimi."""

    boundary: BffSessionBoundary


ApiIdentity = ActorResolverIdentity | BffSessionIdentity


@dataclass(frozen=True)
class ApiOptions:
    """Alan servislerinden bağımsız dashboard API ayarları."""

    allowed_origins: Sequence[str] = ()
    data_origin: str = "runtime"
    development_user_registry: DevelopmentUserRegistry | None = None
    readiness_check: ReadinessCheck | None = None
    clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)


@dataclass(frozen=True)
class DataSourceServices:
    """Veri kaynağı rotalarının eksiksiz bağımlılık sözleşmesi."""

    query: DataSourceQueryService | None
    mutation: DataSourceMutationService | None


@dataclass(frozen=True)
class ExecutionServices:
    """Çalıştırma rotalarının ve iş ayrıntılarının bağımlılık sözleşmesi."""

    query: ExecutionQueryService | None
    start: ExecutionStartService | None
    cancel: ExecutionCancelService | None
    job_queue: JobQueueReader | None
    governance_guard: ExecutionGovernanceGuard | None = None


@dataclass(frozen=True)
class RuleServices:
    """Kural sorgu ve komut rotalarının bağımlılık sözleşmesi."""

    query: RuleQueryService | None
    creator: RuleCreatorService | None
    mutation: RuleMutationService | None


@dataclass(frozen=True)
class IssueServices:
    """Sorun yönetimi rotalarının eksiksiz bağımlılık sözleşmesi."""

    query: IssueQueryService | None
    investigation: IssueInvestigationService | None
    investigation_evidence: IssueInvestigationEvidenceService | None
    assignment: IssueAssignmentService | None
    assignee_options: IssueAssigneeOptionProvider | None
    resolution: IssueResolutionService | None
    verification: IssueVerificationService | None
    closure: IssueClosureService | None
    creation: IssueCreationService | None
    evidence_catalog: IssueEvidenceService | None = None
    evidence_upload: IssueEvidenceUploadService | None = None


@dataclass(frozen=True)
class CatalogServices:
    """Katalog ile katalog verisini kullanan okuma yüzeyleri."""

    metadata_command: MetadataCommandService | None
    query: CatalogQueryService | None
    score_query: ScoreQueryService | None
    dashboard_query: DashboardQueryService | None


@dataclass(frozen=True)
class AuditServices:
    """Denetim rotalarının bağımlılık sözleşmesi."""

    query: AuditQueryService | None


@dataclass(frozen=True)
class NotificationServices:
    """Bildirim sorgu ve teslim rotalarının bağımlılık sözleşmesi."""

    query: NotificationQuery | None
    delivery: NotificationDeliveryCommand | None


@dataclass(frozen=True)
class ReportingServices:
    """Rapor rotalarının salt-okunur bağımlılık sözleşmesi."""

    query: ReportQueryService | None


@dataclass(frozen=True)
class GovernanceServices:
    """Yönetişim görev merkezi rotalarının bağımlılık sözleşmesi."""

    query: GovernanceApprovalQueryService | None
    command: GovernanceApprovalCommandService | None = None


@dataclass(frozen=True)
class AnalyticsServices:
    """Analytics dashboard rotalarının bağımlılık sözleşmesi."""

    rule_health: RuleHealthQueryService | None = None
    metadata_health: MetadataHealthQueryService | None = None
    issue_performance: IssuePerformanceQueryService | None = None
    scoring_policy_impact: ScoringPolicyImpactQueryService | None = None
