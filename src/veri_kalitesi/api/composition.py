"""PostgreSQL-only S1 application composition root."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from sqlalchemy import inspect, text

from veri_kalitesi.api.app import IssueAssigneeOptionProvider, create_dashboard_api
from veri_kalitesi.api.bff import BffSessionBoundary
from veri_kalitesi.api.data_source_commands import DataSourceCommandAdapter
from veri_kalitesi.api.identity import (
    ActorContextResolver,
    DevelopmentActorContextResolver,
    DevelopmentUserRegistry,
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

CURRENT_MIGRATION_HEAD = "20260806_20"
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

    bff = identity_provider if isinstance(identity_provider, BffSessionBoundary) else None
    resolver = None if bff is not None else identity_provider
    app = create_dashboard_api(
        actor_context_resolver=resolver,
        bff_session_boundary=bff,
        allowed_origins=settings.allowed_origins,
        data_origin="postgresql-runtime",
        data_source_query_service=query_service,
        data_source_mutation_service=command_adapter,
        rule_query_service=rule_query_service,
        issue_query_service=issue_query_service,
        issue_investigation_service=issue_service,
        issue_closure_service=issue_service,
        issue_creation_service=issue_service,
        issue_assignment_service=issue_service if phase_b_providers is not None else None,
        issue_assignee_option_provider=(
            phase_b_providers.issue_assignee_option_provider
            if phase_b_providers is not None
            else None
        ),
        issue_resolution_service=issue_service if phase_b_providers is not None else None,
        issue_verification_service=issue_service if phase_b_providers is not None else None,
        rule_creator_service=rule_command_adapter,
        rule_mutation_service=rule_command_adapter,
        execution_query_service=execution_query_service,
        execution_start_service=execution_start_service,
        execution_cancel_service=execution_cancel_service,
        audit_query_service=audit_query_service,
        development_user_registry=development_user_registry,
        metadata_command_service=metadata_command_service,
        catalog_query_service=catalog_query_service,
        score_query_service=score_query_service,
        notification_query_service=notification_query_service,
        notification_delivery_service=notification_delivery_service,
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
    return app
