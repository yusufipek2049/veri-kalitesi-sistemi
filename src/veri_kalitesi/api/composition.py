"""PostgreSQL-only S1 application composition root."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from sqlalchemy import inspect, text

from veri_kalitesi.api.app import create_dashboard_api
from veri_kalitesi.api.bff import BffSessionBoundary
from veri_kalitesi.api.data_source_commands import DataSourceCommandAdapter
from veri_kalitesi.api.identity import (
    ActorContextResolver,
    DevelopmentActorContextResolver,
    DevelopmentUserRegistry,
)
from veri_kalitesi.api.issues_router import IssueAssigneeOptionProvider
from veri_kalitesi.api.service_groups import (
    ActorResolverIdentity,
    ApiOptions,
    AuditServices,
    BffSessionIdentity,
    CatalogServices,
    DataSourceServices,
    ExecutionServices,
    IssueServices,
    NotificationServices,
    ReportingServices,
    RuleServices,
)
from veri_kalitesi.api.postgresql_metadata import PostgreSQLMetadataCommandService
from veri_kalitesi.api.rule_commands import RuleCommandAdapter
from veri_kalitesi.api.postgresql_execution import (
    PostgreSQLExecutionCancelService,
    PostgreSQLExecutionStartService,
)
from veri_kalitesi.api.settings import ApplicationSettings
from veri_kalitesi.audit.models import (
    AuditAccessPolicy,
    AuditFailureMode,
    AuditFailurePolicy,
)
from veri_kalitesi.audit.policies import build_default_redaction_policy
from veri_kalitesi.audit.postgresql_outbox import PostgreSQLTransactionalAudit
from veri_kalitesi.audit.postgresql_repository import PostgreSQLAuditRepository
from veri_kalitesi.audit.redaction import AuditRedactor
from veri_kalitesi.audit.service import (
    AuditQueryService,
    AuditService,
)
from veri_kalitesi.data_sources.connectors import ConnectorRegistry
from veri_kalitesi.data_sources.models import DataSourceCommandPolicy
from veri_kalitesi.data_sources.postgresql import PostgreSQLConnector
from veri_kalitesi.data_sources.postgresql_driver import SQLAlchemyPostgreSQLDriver
from veri_kalitesi.data_sources.postgresql_repository import PostgreSQLDataSourceRepository
from veri_kalitesi.data_sources.query import DataSourceQueryService
from veri_kalitesi.data_sources.secrets import SecretResolver
from veri_kalitesi.data_sources.service import DataSourceService
from veri_kalitesi.data_sources.catalog import CatalogQueryService
from veri_kalitesi.executions.postgresql_repository import PostgreSQLExecutionRepository
from veri_kalitesi.executions.query import ExecutionQueryService
from veri_kalitesi.executions.strategy_engine import ExecutionStrategyEngine
from veri_kalitesi.identity import (
    ActorContext,
    DashboardAuthorizationPolicy,
    PolicyAuthorizationService,
)
from veri_kalitesi.issues import (
    IssueAccessPolicy,
    IssueAssigneeDirectory,
    IssueAssignment,
    IssueAssignmentError,
    IssueAssignmentResolver,
    IssueNotificationPublisher,
    IssueQueryService,
    IssueResolutionProtector,
    IssueService,
    IssueTrigger,
    IssueVerificationResolver,
    PostgreSQLIssueRepository,
)
from veri_kalitesi.jobs import PostgreSQLJobQueueRepository
from veri_kalitesi.notifications import NotificationEvent, NotificationTechnicalError
from veri_kalitesi.notifications.models import (
    NotificationEventType,
    NotificationScopeType,
)
from veri_kalitesi.persistence import SessionFactory, create_session_factory
from veri_kalitesi.rules import (
    PostgreSQLRuleRepository,
    RuleApprovalPolicy,
    RuleQueryService,
    RuleService,
    RuleTestExecutor,
)
from veri_kalitesi.scoring.postgresql_contributions import (
    PostgreSQLContributionGraphRepository,
)
from veri_kalitesi.scoring.postgresql_repository import PostgreSQLScoreRepository
from veri_kalitesi.scoring.query import ScoreQueryService
from veri_kalitesi.dashboard.service import DashboardQueryService

CURRENT_MIGRATION_HEAD = "20260813_23"
REQUIRED_TABLES = frozenset(
    {
        "data_sources",
        "data_source_activation_requests",
        "datasets",
        "data_fields",
        "quality_rules",
        "rule_versions",
        "rule_test_results",
        "rule_approval_requests",
        "data_quality_issues",
        "issue_history",
        "issue_resolutions",
        "issue_verifications",
        "issue_relationships",
        "rule_executions",
        "score_contribution_graphs",
        "scoring_configurations",
        "scoring_configuration_approvals",
        "dataset_partial_score_policies",
        "score_publications",
        "quality_scores",
        "audit_outbox",
        "audit_events",
        "background_jobs",
        "job_dead_letters",
        "workers",
        "source_usage_policies",
        "metadata_discovery_results",
        "discovery_scopes",
        "metadata_diffs",
        "notification_channels",
        "notification_events",
        "notification_subscriptions",
        "notification_deliveries",
        "reports",
    }
)


@dataclass(frozen=True)
class PhaseBProviders:
    """Production-owned trusted ports required by the complete DS-02 command chain."""

    rule_test_executor: RuleTestExecutor
    issue_assignee_directory: IssueAssigneeDirectory
    issue_assignment_resolver: IssueAssignmentResolver
    issue_assignee_option_provider: IssueAssigneeOptionProvider
    issue_resolution_protector: IssueResolutionProtector
    issue_verification_resolver: IssueVerificationResolver
    issue_notification_publisher: IssueNotificationPublisher
    issue_notification_actor_context_provider: Callable[[], ActorContext]

    def __post_init__(self) -> None:
        if any(
            provider is None
            for provider in (
                self.rule_test_executor,
                self.issue_assignee_directory,
                self.issue_assignment_resolver,
                self.issue_assignee_option_provider,
                self.issue_resolution_protector,
                self.issue_verification_resolver,
                self.issue_notification_publisher,
                self.issue_notification_actor_context_provider,
            )
        ):
            raise ValueError("All trusted DS-02 Phase B providers are required.")


class UnavailableIssueAssignmentResolver:
    """Faz A'da kullanılmayan issue-create bağımlılığını fail-closed tutar."""

    def resolve_assignment(self, trigger: IssueTrigger) -> IssueAssignment:
        raise IssueAssignmentError("Trusted issue assignment resolver is unavailable.")


class UnavailableIssueNotificationPublisher:
    """Faz B bildirim hattı bağlanana kadar hiçbir olayı başarılı saymaz."""

    def create_for_event(
        self, event: NotificationEvent, actor_context: ActorContext | None
    ) -> tuple[object, ...]:
        raise NotificationTechnicalError(
            "Persistent issue notification is unavailable.",
            "issue-notification-unavailable",
        )


class DefaultRuleApprovalNotificationSink:
    """Rule approval notification sink — builds NotificationEvent and publishes."""

    def __init__(
        self,
        notification_publisher: object,
        actor_context_provider: Callable[[], ActorContext] | None,
    ) -> None:
        self._publisher = notification_publisher
        self._actor_context_provider = actor_context_provider

    def publish_rule_approval_event(
        self,
        *,
        event_type: NotificationEventType,
        quality_rule_id: str,
        rule_code: str,
        rule_name: str,
        recipient_user_id: str,
        actor_context: ActorContext | None,
        correlation_id: str,
        payload: dict,
    ) -> None:
        from uuid import uuid4
        from datetime import datetime, timezone

        actor_ctx = actor_context or (
            self._actor_context_provider() if self._actor_context_provider else None
        )
        event = NotificationEvent(
            event_type=event_type,
            scope_type=NotificationScopeType.RULE,
            scope_id=quality_rule_id,
            deduplication_key=(
                f"rule-approval-{event_type.value}-{quality_rule_id}-"
                f"{payload.get('approval_request_id', '')}"
            ),
            occurred_at=datetime.now(timezone.utc),
            correlation_id=correlation_id,
            source_ref=f"QualityRule:{quality_rule_id}",
            payload={
                "rule_code": rule_code,
                "rule_name": rule_name,
                "recipient_user_id": recipient_user_id,
                **payload,
            },
            event_id=str(uuid4()),
        )
        if hasattr(self._publisher, "create_for_event"):
            self._publisher.create_for_event(event, actor_ctx)


def preflight_database(settings: ApplicationSettings, session_factory: SessionFactory) -> None:
    schema = settings.database.schema
    engine = session_factory.kw.get("bind")
    if engine is None:
        raise RuntimeError("PostgreSQL session factory has no bound engine.")
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
        schema_exists = connection.scalar(
            text("SELECT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = :schema)"),
            {"schema": schema},
        )
        if not schema_exists:
            raise RuntimeError(f"Application schema is missing: {schema}")
        tables = set(inspect(connection).get_table_names(schema=schema))
        missing = sorted(REQUIRED_TABLES - tables)
        if missing:
            raise RuntimeError(f"Required application tables are missing: {', '.join(missing)}")
        migration_head = connection.scalar(
            text(f'SELECT version_num FROM "{schema}".alembic_version')
        )
        if migration_head != CURRENT_MIGRATION_HEAD:
            raise RuntimeError(
                f"Database migration head is {migration_head!r}; "
                f"expected {CURRENT_MIGRATION_HEAD!r}."
            )


def create_application(
    settings: ApplicationSettings,
    identity_provider: ActorContextResolver | BffSessionBoundary,
    *,
    secret_resolver: SecretResolver,
    development_user_registry: DevelopmentUserRegistry | None = None,
    phase_b_providers: PhaseBProviders | None = None,
):
    if identity_provider is None:
        raise ValueError("A trusted identity provider is required.")
    if secret_resolver is None:
        raise ValueError("A secret resolver is required.")
    session_factory = create_session_factory(settings.database)
    if settings.migration_check_enabled:
        preflight_database(settings, session_factory)

    def readiness_check() -> None:
        with session_factory() as session:
            session.execute(text("SELECT 1"))

    audit_repository = PostgreSQLAuditRepository(session_factory, schema=settings.database.schema)
    redactor = AuditRedactor(build_default_redaction_policy())
    audit_service = AuditService(
        audit_repository,
        redactor,
        AuditFailurePolicy(
            version=f"{settings.audit_policy_version}_FAILURE",
            default_mode=AuditFailureMode.FAIL_CLOSED,
        ),
    )
    transactional_audit = PostgreSQLTransactionalAudit(
        session_factory,
        redactor,
        audit_repository,
        policy_version=settings.audit_policy_version,
        schema=settings.database.schema,
    )
    command_policy = DataSourceCommandPolicy(
        version=settings.data_source_policy_version,
        actor_policy_version=settings.actor_policy_version,
        creator_roles=frozenset({"DATA_STEWARD", "DATA_OWNER"}),
        connection_tester_roles=frozenset({"DATA_STEWARD"}),
        maker_roles=frozenset({"DATA_STEWARD"}),
        checker_roles=frozenset({"DATA_OWNER"}),
        deactivator_roles=frozenset({"DATA_OWNER"}),
    )
    authorization = PolicyAuthorizationService(
        DashboardAuthorizationPolicy(version=settings.actor_policy_version),
        audit_service,
    )
    repository = PostgreSQLDataSourceRepository(session_factory, schema=settings.database.schema)
    rule_repository = PostgreSQLRuleRepository(session_factory, schema=settings.database.schema)
    issue_repository = PostgreSQLIssueRepository(session_factory, schema=settings.database.schema)
    execution_repository = PostgreSQLExecutionRepository(
        session_factory, schema=settings.database.schema
    )
    if isinstance(identity_provider, DevelopmentActorContextResolver):
        identity_provider.bind_enterprise_source_scope_provider(
            lambda: frozenset(
                source.data_source_id for source in repository.list_all_data_sources()
            )
        )
        identity_provider.bind_enterprise_dataset_scope_provider(
            lambda: frozenset(
                dataset.dataset_id
                for source in repository.list_all_data_sources()
                for dataset in repository.list_datasets(source.data_source_id)
            )
        )
    query_service = DataSourceQueryService(
        repository,
        authorization,
        command_policy,
    )
    service = DataSourceService(
        repository,
        ConnectorRegistry([PostgreSQLConnector(SQLAlchemyPostgreSQLDriver())]),
        secret_resolver,
        audit_sink=audit_service,
        transactional_audit=transactional_audit,
        activation_policy=command_policy,
        enforce_command_authorization=True,
    )
    command_adapter = DataSourceCommandAdapter(service, query_service, audit_service)
    rule_query_service = RuleQueryService(rule_repository, authorization)
    issue_query_service = IssueQueryService(issue_repository, authorization)
    execution_query_service = ExecutionQueryService(execution_repository, authorization)
    job_queue_repository = PostgreSQLJobQueueRepository(session_factory)
    execution_start_service = PostgreSQLExecutionStartService(
        execution_repository,
        job_queue=job_queue_repository,
        transactional_audit=transactional_audit,
        strategy_engine=ExecutionStrategyEngine(),
        rule_catalog=rule_repository,
        source_catalog=repository,
    )
    execution_cancel_service = PostgreSQLExecutionCancelService(
        execution_repository,
        transactional_audit=transactional_audit,
        job_queue=job_queue_repository,
    )
    notification_publisher = (
        phase_b_providers.issue_notification_publisher
        if phase_b_providers is not None
        else UnavailableIssueNotificationPublisher()
    )

    # DS-09: Notification services (must be created before IssueService)
    from veri_kalitesi.notifications.postgresql_repository import (
        PostgreSQLNotificationRepository,
    )
    from veri_kalitesi.notifications.query_service import NotificationQueryService
    from veri_kalitesi.notifications.delivery_service import NotificationDeliveryService
    from veri_kalitesi.notifications.batch_stager import DefaultNotificationBatchStager

    notification_repository = PostgreSQLNotificationRepository(
        session_factory, schema=settings.database.schema
    )

    # Development otomatik PhaseBProviders oluşturma
    if (
        phase_b_providers is None
        and isinstance(identity_provider, DevelopmentActorContextResolver)
        and development_user_registry is not None
    ):
        from veri_kalitesi.api.development_providers import (
            build_development_phase_b_providers,
        )

        phase_b_providers = build_development_phase_b_providers(
            user_registry=development_user_registry,
            notification_repository=notification_repository,
            resolver=identity_provider,
        )
        # notification_publisher'ı güncelle (yukarıda henüz repository yoktu)
        notification_publisher = phase_b_providers.issue_notification_publisher

    notification_query_service = NotificationQueryService(notification_repository)
    notification_delivery_service = NotificationDeliveryService(
        repository=notification_repository,
    )
    notification_batch_stager = DefaultNotificationBatchStager(
        repository=notification_repository,
    )

    issue_service = IssueService(
        issue_repository,
        (
            phase_b_providers.issue_assignment_resolver
            if phase_b_providers is not None
            else UnavailableIssueAssignmentResolver()
        ),
        notification_publisher,
        transactional_audit,
        IssueAccessPolicy(
            version=settings.issue_policy_version,
            actor_policy_version=settings.actor_policy_version,
        ),
        assignee_directory=(
            phase_b_providers.issue_assignee_directory if phase_b_providers is not None else None
        ),
        resolution_protector=(
            phase_b_providers.issue_resolution_protector if phase_b_providers is not None else None
        ),
        verification_resolver=(
            phase_b_providers.issue_verification_resolver if phase_b_providers is not None else None
        ),
        notification_actor_context_provider=(
            phase_b_providers.issue_notification_actor_context_provider
            if phase_b_providers is not None
            else None
        ),
        notification_batch_stager=notification_batch_stager,
    )
    rule_command_adapter = None
    if phase_b_providers is not None:
        rule_approval_notification_sink = DefaultRuleApprovalNotificationSink(
            notification_publisher=notification_publisher,
            actor_context_provider=(
                phase_b_providers.issue_notification_actor_context_provider
                if phase_b_providers is not None
                else None
            ),
        )
        rule_service = RuleService(
            rule_repository,
            repository,
            phase_b_providers.rule_test_executor,
            audit_sink=audit_service,
            transactional_audit=transactional_audit,
            approval_policy=RuleApprovalPolicy(
                version=settings.rule_policy_version,
                actor_policy_version=settings.actor_policy_version,
                maker_roles=frozenset({"DATA_STEWARD"}),
                checker_roles=frozenset({"DATA_OWNER"}),
            ),
            enforce_command_authorization=True,
            notification_sink=rule_approval_notification_sink,
        )
        rule_command_adapter = RuleCommandAdapter(rule_service)
    audit_query_service = AuditQueryService(
        audit_repository,
        audit_service,
        AuditAccessPolicy(
            version=f"{settings.audit_policy_version}_ACCESS",
            context_policy_version=settings.actor_policy_version,
            required_role="AUDIT_VIEWER",
        ),
    )
    from veri_kalitesi.reporting.repository import PostgreSQLReportRepository
    from veri_kalitesi.reporting.service import ReportQueryService

    report_repository = PostgreSQLReportRepository(
        session_factory,
        schema=settings.database.schema,
    )
    report_query_service = ReportQueryService(report_repository, audit_service)
    metadata_command_service = PostgreSQLMetadataCommandService(
        service=service,
        repository=repository,
        transactional_audit=transactional_audit,
        job_enqueuer=job_queue_repository,
        command_policy=command_policy,
    )
    catalog_query_service = CatalogQueryService(reader=repository)

    # DS-06: Skor sorgulama bileşenleri
    score_repository = PostgreSQLScoreRepository(session_factory, schema=settings.database.schema)
    contribution_graph_repository = PostgreSQLContributionGraphRepository(
        session_factory, schema=settings.database.schema
    )
    score_query_service = ScoreQueryService(
        score_repository=score_repository,
        contribution_graph_repository=contribution_graph_repository,
    )
    dashboard_query_service = DashboardQueryService(
        score_reader=score_repository,
        authorization_service=authorization,
        clock=lambda: datetime.now(timezone.utc),
    )

    # IssueInvestigationEvidenceService oluştur
    issue_investigation_evidence_service = None
    from veri_kalitesi.issues.investigation import IssueInvestigationEvidenceService

    class _PassthroughEvidenceProvider:
        """Development/production için boş kanıt sağlayıcı — Unknown döner."""

        def get_evidence_for_issue(self, issue_id, scope_type, scope_id):
            return None

    issue_investigation_evidence_service = IssueInvestigationEvidenceService(
        reader=issue_repository,
        authorization_service=authorization,
        evidence_provider=_PassthroughEvidenceProvider(),
    )

    app = create_dashboard_api(
        identity=(
            BffSessionIdentity(identity_provider)
            if isinstance(identity_provider, BffSessionBoundary)
            else ActorResolverIdentity(identity_provider)
        ),
        options=ApiOptions(
            allowed_origins=settings.allowed_origins,
            data_origin="postgresql-runtime",
            development_user_registry=development_user_registry,
            readiness_check=readiness_check,
        ),
        data_sources=DataSourceServices(query=query_service, mutation=command_adapter),
        rules=RuleServices(
            query=rule_query_service,
            creator=rule_command_adapter,
            mutation=rule_command_adapter,
        ),
        issues=IssueServices(
            query=issue_query_service,
            investigation=issue_service,
            investigation_evidence=issue_investigation_evidence_service,
            assignment=issue_service if phase_b_providers is not None else None,
            assignee_options=(
                phase_b_providers.issue_assignee_option_provider
                if phase_b_providers is not None
                else None
            ),
            resolution=issue_service if phase_b_providers is not None else None,
            verification=issue_service if phase_b_providers is not None else None,
            closure=issue_service,
            creation=issue_service,
        ),
        executions=ExecutionServices(
            query=execution_query_service,
            start=execution_start_service,
            cancel=execution_cancel_service,
            job_queue=job_queue_repository,
        ),
        audit=AuditServices(query=audit_query_service),
        catalog=CatalogServices(
            metadata_command=metadata_command_service,
            query=catalog_query_service,
            score_query=score_query_service,
            dashboard_query=dashboard_query_service,
        ),
        notifications=NotificationServices(
            query=notification_query_service,
            delivery=notification_delivery_service,
        ),
        reporting=ReportingServices(query=report_query_service),
    )
    app.state.application_settings = settings
    app.state.session_factory = session_factory
    app.state.data_source_repository = repository
    app.state.rule_repository = rule_repository
    app.state.issue_repository = issue_repository
    app.state.execution_repository = execution_repository
    app.state.issue_service = issue_service
    app.state.rule_command_adapter = rule_command_adapter
    app.state.audit_repository = audit_repository
    app.state.score_repository = score_repository
    app.state.notification_repository = notification_repository
    app.state.notification_query_service = notification_query_service
    app.state.notification_delivery_service = notification_delivery_service
    app.state.report_repository = report_repository
    app.state.report_query_service = report_query_service
    return app
