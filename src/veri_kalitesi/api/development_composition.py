"""Geliştirme ortamı API bileşim kökü — DEPRECATED.

.. deprecated::
    Bu modül sentetik skor ve seed verilerle yerel gösterim uygulaması üretir.
    Gerçek runtime ``development_runtime.py`` modülüdür (68 rota, PostgreSQL).
    Bu modül yalnızca 58 rota kaydeder ve /api/v1/notifications/* ile
    catalog/score servislerini HİÇ geçirmiyor. Yeni kod bu modülü
    kullanmamalıdır; testlerin ``development_runtime`` kullanması gerekir.

Üretimde kullanılmaz.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from veri_kalitesi.api.app import create_dashboard_api
from veri_kalitesi.api.development_data_source_store import (
    DevelopmentDataSourceReader,
    DevelopmentDataSourceStore,
)
from veri_kalitesi.api.development_execution_store import (
    DevelopmentExecutionReader,
    DevelopmentExecutionStore,
)
from veri_kalitesi.api.development_fixtures import (
    DEVELOPMENT_RULES,
    DEVELOPMENT_SOURCES,
    DEVELOPMENT_TREND_POLICY,
    POLICY_VERSION,
)
from veri_kalitesi.api.development_issue_store import DevelopmentIssueStore
from veri_kalitesi.issues.evidence import IssueEvidenceService
from veri_kalitesi.issues.evidence_files import (
    AllowAllDevelopmentScanner,
    EvidenceFilePolicy,
    IssueEvidenceFileService,
    LocalEvidenceStorage,
)
from veri_kalitesi.issues.evidence_candidates import ExecutionIssueEvidenceCandidateProvider
from veri_kalitesi.api.development_rule_store import DevelopmentRuleReader, DevelopmentRuleStore
from veri_kalitesi.governance import GovernanceApprovalQueryService
from veri_kalitesi.api.identity import (
    DevelopmentActorContextResolver,
    DevelopmentUserRegistry,
    build_default_development_users,
)
from veri_kalitesi.api.postgresql_execution import (
    PostgreSQLExecutionCancelService,
    PostgreSQLExecutionStartService,
)
from veri_kalitesi.api.executions_router import ExecutionCancelService, ExecutionStartService
from veri_kalitesi.api.service_groups import (
    ActorResolverIdentity,
    ApiOptions,
    AuditServices,
    CatalogServices,
    DataSourceServices,
    ExecutionServices,
    GovernanceServices,
    IssueServices,
    RuleServices,
)
from veri_kalitesi.audit.models import (
    AuditAccessPolicy,
    AuditEventInput,
    AuditFailureMode,
    AuditFailurePolicy,
    AuditResult,
)
from veri_kalitesi.audit.policies import build_default_redaction_policy
from veri_kalitesi.audit.postgresql_outbox import PostgreSQLTransactionalAudit
from veri_kalitesi.audit.redaction import AuditRedactor
from veri_kalitesi.audit.repository import SQLiteAuditRepository
from veri_kalitesi.audit.service import (
    AuditQueryService,
    AuditService,
)
from veri_kalitesi.data_sources.query import DataSourceQueryService
from veri_kalitesi.executions.postgresql_repository import (
    PostgreSQLExecutionRepository,
)
from veri_kalitesi.executions.query import ExecutionQueryService
from veri_kalitesi.executions.strategy_engine import ExecutionStrategyEngine
from veri_kalitesi.identity import (
    DashboardAuthorizationPolicy,
    PolicyAuthorizationService,
)
from veri_kalitesi.issues import IssueQueryService
from veri_kalitesi.jobs import PostgreSQLJobQueueRepository
from veri_kalitesi.persistence import SessionFactory
from veri_kalitesi.reporting import (
    ReportExportPolicy,
    ReportFormat,
)
from veri_kalitesi.reporting.models import ReportType
from veri_kalitesi.reporting.repository import (
    PostgreSQLReportRepository,
    report_tables,
)
from veri_kalitesi.rules import RuleQueryService
from veri_kalitesi.scoring.models import (
    QualityScore,
    ScoreLevel,
    ScoreScopeType,
    ScoreStatus,
)
from veri_kalitesi.scoring.repository import SQLiteScoreRepository
from veri_kalitesi.dashboard.service import DashboardQueryService

DEVELOPMENT_USER_REGISTRY = DevelopmentUserRegistry(build_default_development_users())


class _DevPolicyRepository:
    """Geliştirme ortamı için sabit export-policy döndüren uyum sağlayıcı."""

    def get_active_policy(self, sensitivity_level: str | None) -> ReportExportPolicy | None:
        if sensitivity_level and sensitivity_level.upper() in {
            "HIGH",
            "CRITICAL",
            "CONFIDENTIAL",
        }:
            return None
        return ReportExportPolicy(
            version="DEVELOPMENT_EXPORT_POLICY_V1",
            policy_name="development-export",
            sensitivity_level=sensitivity_level,
            max_file_size=50 * 1024 * 1024,
            online_duration_seconds=3600,
            require_justification=False,
            require_maker_checker=False,
            watermark_enabled=True,
            dlp_enabled=False,
            allowed_formats=frozenset(ReportFormat),
        )


class _DevReportDataProvider:
    """Geliştirme ortamı için sabit rapor verisi döndüren uyum sağlayıcı."""

    def fetch_report_data(
        self,
        report_type: ReportType,
        parameters: dict,
    ) -> tuple[tuple[str, ...], tuple[tuple[str, ...], ...]]:
        headers = ("Source ID", "Score", "Status", "Level", "Calculated At")
        rows = (
            ("source-core-banking", "91.80", "CALCULATED", "GOOD", "2026-07-24 12:00 UTC"),
            ("source-customer-file", "82.40", "PARTIAL", "ACCEPTABLE", "2026-07-24 11:00 UTC"),
            ("source-risk-mart", "", "NO_DATA", "", "2026-07-24 10:00 UTC"),
            (
                "source-regulatory-api",
                "",
                "NOT_CALCULATED_TECHNICAL_ERROR",
                "",
                "2026-07-24 09:00 UTC",
            ),
        )
        return headers, rows


def _create_development_report_repository(
    session_factory: SessionFactory | None,
) -> PostgreSQLReportRepository:
    if session_factory is not None:
        return PostgreSQLReportRepository(session_factory)
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.orm import Session as SaSession

    engine = create_engine("sqlite://", echo=False)
    tables = report_tables(schema="")
    tables.reports.create(engine, checkfirst=True)
    sf: SessionFactory = sessionmaker(bind=engine, class_=SaSession)  # type: ignore[assignment]
    return PostgreSQLReportRepository(sf, schema="")


def _seed_development_scores(repository: SQLiteScoreRepository, now: datetime) -> None:
    """Dashboard ve rapor görünümleri için sentetik skor verilerini yükler."""
    for index, (days_ago, score_value) in enumerate(
        (
            (28, "72.10"),
            (24, "76.80"),
            (20, "78.20"),
            (12, "82.40"),
            (8, "84.60"),
            (4, "86.20"),
            (0, "87.40"),
        )
    ):
        repository.add_or_get(
            QualityScore(
                execution_id=f"development-dashboard-{index}",
                rule_version_id=None,
                scope_type=ScoreScopeType.ENTERPRISE,
                scope_id=None,
                score_value=Decimal(score_value),
                score_status=ScoreStatus.CALCULATED,
                level=ScoreLevel.ACCEPTABLE,
                calculation_details={"included_in_official_aggregation": True},
                calculated_at=now - timedelta(days=days_ago),
            )
        )
    source_observations = (
        ("source-core-banking", "91.80", ScoreStatus.CALCULATED, ScoreLevel.GOOD, True),
        ("source-customer-file", "82.40", ScoreStatus.PARTIAL, ScoreLevel.ACCEPTABLE, True),
        ("source-risk-mart", None, ScoreStatus.NO_DATA, None, None),
        (
            "source-regulatory-api",
            None,
            ScoreStatus.NOT_CALCULATED_TECHNICAL_ERROR,
            None,
            None,
        ),
    )
    for index, (source_id, observed_score_value, status, level, official) in enumerate(
        source_observations
    ):
        calculation_details: dict[str, object] = {"aggregate": True}
        if official is not None:
            calculation_details["included_in_official_aggregation"] = official
        repository.add_or_get(
            QualityScore(
                execution_id=f"development-report-{index}",
                rule_version_id=None,
                scope_type=ScoreScopeType.SOURCE,
                scope_id=source_id,
                score_value=Decimal(observed_score_value)
                if observed_score_value is not None
                else None,
                score_status=status,
                level=level,
                calculation_details=calculation_details,
                calculated_at=now - timedelta(hours=index + 1),
            )
        )


def _seed_development_audit_events(audit_service: AuditService, now: datetime) -> None:
    """Audit görünümü için sentetik olay kayıtlarını yükler."""
    for index, (actor_id, action, object_type, object_id, result, reason_code) in enumerate(
        (
            (
                "synthetic-iam-user",
                "LDAP_AUTHENTICATION",
                "UserSession",
                "synthetic-session",
                AuditResult.SUCCESS,
                "AUTHENTICATED",
            ),
            (
                "synthetic-data-steward",
                "DATA_SOURCE_CONNECTION_TEST",
                "DataSource",
                "source-core-banking",
                AuditResult.SUCCESS,
                "TEST_SUCCEEDED",
            ),
            (
                "synthetic-rule-checker",
                "RULE_ACTIVATION",
                "QualityRule",
                "rule-customer-id-required",
                AuditResult.SUCCESS,
                "APPROVED",
            ),
            (
                "synthetic-score-checker",
                "SCORING_CONFIGURATION_ACTIVATION",
                "ScoringConfiguration",
                "scoring-policy-v2",
                AuditResult.DENIED,
                "MAKER_CHECKER_REQUIRED",
            ),
            (
                "synthetic-report-viewer",
                "REPORT_PREVIEW_VIEWED",
                "ReportPreview",
                None,
                AuditResult.SUCCESS,
                "QUERY_COMPLETED",
            ),
            (
                "synthetic-session-user",
                "IDENTITY_SESSION",
                "UserSession",
                "synthetic-expired-session",
                AuditResult.FAILURE,
                "ABSOLUTE_TIMEOUT",
            ),
        )
    ):
        audit_service.append(
            AuditEventInput(
                actor_id=actor_id,
                actor_type="USER",
                correlation_id=f"synthetic-audit-{index + 1}",
                action=action,
                object_type=object_type,
                object_id=object_id,
                result=result,
                reason_code=reason_code,
                old_values={},
                new_values={},
                occurred_at=now - timedelta(days=index, hours=1),
                session_id=None,
            )
        )


def create_synthetic_development_app(  # type: ignore[no-untyped-def]
    user_registry: DevelopmentUserRegistry | None = None,
    session_factory: SessionFactory | None = None,
    transactional_audit: PostgreSQLTransactionalAudit | None = None,
):
    """Sentetik skorlarla yerel gösterim uygulaması üretir; üretimde kullanılmaz.

    session_factory verilirse PostgreSQLExecutionRepository kullanarak
    gerçek kalıcılıkla çalışır; verilmezse DevelopmentExecutionStore
    (bellek içi) kullanır.
    """

    now = datetime.now(timezone.utc)
    repository = SQLiteScoreRepository()
    _seed_development_scores(repository, now)

    audit_repository = SQLiteAuditRepository()
    audit_service = AuditService(
        audit_repository,
        AuditRedactor(build_default_redaction_policy()),
        AuditFailurePolicy(
            version="DEVELOPMENT_API_AUDIT_FAILURE_V1",
            default_mode=AuditFailureMode.FAIL_CLOSED,
        ),
    )
    _seed_development_audit_events(audit_service, now)

    authorization = PolicyAuthorizationService(
        DashboardAuthorizationPolicy(version=POLICY_VERSION),
        audit_service,
        clock=lambda: datetime.now(timezone.utc),
    )
    development_origins = frozenset({"http://127.0.0.1:5173", "http://localhost:5173"})
    effective_registry = user_registry or DEVELOPMENT_USER_REGISTRY
    resolver = DevelopmentActorContextResolver(
        runtime_environment="development",
        policy_version=POLICY_VERSION,
        permitted_source_ids=frozenset(source.data_source_id for source in DEVELOPMENT_SOURCES),
        permitted_dataset_ids=frozenset(rule.dataset_id for rule, _ in DEVELOPMENT_RULES),
        roles=frozenset({"DATA_VIEWER", "DATA_STEWARD", "AUDIT_VIEWER"}),
        allowed_origins=development_origins,
        can_view_enterprise=True,
        user_registry=effective_registry,
    )
    issue_store = DevelopmentIssueStore()
    issue_evidence_service = IssueEvidenceService(
        issue_reader=issue_store,
        evidence_store=issue_store,
        candidate_provider=ExecutionIssueEvidenceCandidateProvider(
            DevelopmentExecutionReader(),
            DevelopmentRuleReader(),
        ),
        authorization_service=authorization,
        clock=lambda: datetime.now(timezone.utc),
    )
    issue_evidence_upload_service = IssueEvidenceFileService(
        issue_reader=issue_store,
        repository=issue_store,
        authorization_service=authorization,
        storage=LocalEvidenceStorage(".local/development-issue-evidence"),
        scanner=AllowAllDevelopmentScanner(),
        policy=EvidenceFilePolicy(version="EVIDENCE_FILE_POLICY_V1"),
        audit_sink=audit_service,
        clock=lambda: datetime.now(timezone.utc),
    )
    rule_store = DevelopmentRuleStore()
    data_source_store = DevelopmentDataSourceStore()
    if session_factory is not None:
        if transactional_audit is None:
            raise ValueError("PostgreSQL execution composition requires transactional audit.")
        pg_repository = PostgreSQLExecutionRepository(session_factory)
        job_queue = PostgreSQLJobQueueRepository(session_factory)
        execution_start_service: ExecutionStartService = PostgreSQLExecutionStartService(
            pg_repository,
            job_queue=job_queue,
            transactional_audit=transactional_audit,
            strategy_engine=ExecutionStrategyEngine(),
        )
        execution_cancel_service: ExecutionCancelService = PostgreSQLExecutionCancelService(
            pg_repository,
            transactional_audit=transactional_audit,
            job_queue=job_queue,
        )
    else:
        execution_store = DevelopmentExecutionStore()
        execution_start_service = execution_store  # type: ignore[assignment]
        execution_cancel_service = execution_store  # type: ignore[assignment]
    return create_dashboard_api(
        identity=ActorResolverIdentity(resolver),
        options=ApiOptions(
            allowed_origins=tuple(development_origins),
            data_origin="synthetic-development",
            development_user_registry=effective_registry,
            clock=lambda: datetime.now(timezone.utc),
        ),
        data_sources=DataSourceServices(
            query=DataSourceQueryService(DevelopmentDataSourceReader(), authorization),
            mutation=data_source_store,  # type: ignore[arg-type]
        ),
        rules=RuleServices(
            query=RuleQueryService(DevelopmentRuleReader(), authorization),
            creator=rule_store,
            mutation=None,
        ),
        executions=ExecutionServices(
            query=ExecutionQueryService(DevelopmentExecutionReader(), authorization),
            start=execution_start_service,
            cancel=execution_cancel_service,
            job_queue=None,
        ),
        issues=IssueServices(
            query=IssueQueryService(issue_store, authorization),
            investigation=issue_store,
            investigation_evidence=None,
            assignment=issue_store,
            assignee_options=issue_store,
            resolution=issue_store,
            verification=issue_store,
            closure=issue_store,
            creation=issue_store,
            evidence_catalog=issue_evidence_service,
            evidence_upload=issue_evidence_upload_service,
        ),
        audit=AuditServices(
            query=AuditQueryService(
                audit_repository,
                audit_service,
                AuditAccessPolicy(
                    version="DEVELOPMENT_AUDIT_ACCESS_V1",
                    context_policy_version=POLICY_VERSION,
                ),
                clock=lambda: datetime.now(timezone.utc),
            ),
        ),
        catalog=CatalogServices(
            metadata_command=None,
            query=None,
            score_query=None,
            dashboard_query=DashboardQueryService(
                score_reader=repository,
                authorization_service=authorization,
                clock=lambda: datetime.now(timezone.utc),
                trend_policy=DEVELOPMENT_TREND_POLICY,
            ),
        ),
        governance=GovernanceServices(
            query=GovernanceApprovalQueryService(
                DevelopmentRuleReader(),
                DevelopmentDataSourceReader(),
                authorization,
            ),
        ),
    )
