"""PostgreSQL-only S1 application composition root."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

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
    AnalyticsServices,
    ApiOptions,
    AuditServices,
    BffSessionIdentity,
    CatalogServices,
    DataSourceServices,
    ExecutionServices,
    GovernanceServices,
    ScoringConfigurationServices,
    SqlTemplateServices,
    IssueServices,
    NotificationServices,
    ReportingServices,
    RuleServices,
    ScheduleServices,
)
from veri_kalitesi.api.postgresql_metadata import PostgreSQLMetadataCommandService
from veri_kalitesi.api.rule_commands import RuleCommandAdapter
from veri_kalitesi.api.postgresql_execution import (
    PostgreSQLExecutionCancelService,
    PostgreSQLExecutionGovernanceWriter,
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
from veri_kalitesi.data_sources.preview import DatasetPreviewService
from veri_kalitesi.data_sources.query import DataSourceQueryService
from veri_kalitesi.data_sources.secrets import SecretResolver
from veri_kalitesi.data_sources.service import DataSourceService
from veri_kalitesi.data_sources.catalog import CatalogQueryService
from veri_kalitesi.executions.postgresql_repository import PostgreSQLExecutionRepository
from veri_kalitesi.executions.postgresql_scheduling import PostgreSQLScheduleRepository
from veri_kalitesi.executions.query import ExecutionQueryService
from veri_kalitesi.executions.scheduling import SchedulingService
from veri_kalitesi.executions.service import validate_rule_versions_for_catalogs
from veri_kalitesi.executions.errors import ExecutionValidationError
from veri_kalitesi.executions.strategy_engine import ExecutionStrategyEngine
from veri_kalitesi.executions.governance import ExecutionCriticalityGuard
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
    PostgreSQLIssueEvidenceProvider,
    PostgreSQLIssueRepository,
)
from veri_kalitesi.jobs import PostgreSQLJobQueueRepository
from veri_kalitesi.notifications import NotificationEvent, NotificationTechnicalError
from veri_kalitesi.notifications.models import (
    NotificationEventType,
    NotificationScopeType,
)
from veri_kalitesi.issues.clamav import build_production_scanner
from veri_kalitesi.persistence import SessionFactory, create_session_factory
from veri_kalitesi.governance import (
    GovernanceApprovalCommandService,
    GovernanceApprovalPolicy,
    GovernanceApprovalQueryService,
    GovernanceApprovalRequest,
    PostgreSQLDatasetOwnershipWriter,
    PostgreSQLDiffGovernanceWriter,
    PostgreSQLGovernanceApprovalRepository,
    PostgreSQLMetadataGovernanceWriter,
    PostgreSQLScheduleGovernanceWriter,
)
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
from veri_kalitesi.scoring.models import ScoringApprovalPolicy
from veri_kalitesi.scoring.query import ScoreQueryService
from veri_kalitesi.scoring.service import ScoringConfigurationService
from veri_kalitesi.dashboard.service import DashboardQueryService
from veri_kalitesi.dashboard.postgresql_insights import PostgreSQLInsightsReader
from veri_kalitesi.dashboard.rule_health import RuleHealthQueryService
from veri_kalitesi.dashboard.metadata_health import MetadataHealthQueryService
from veri_kalitesi.dashboard.issue_performance import IssuePerformanceQueryService
from veri_kalitesi.dashboard.scoring_policy_impact import ScoringPolicyImpactQueryService
from veri_kalitesi.sql_templates import (
    PostgreSQLSqlTemplateRepository,
    SqlTemplateService,
)

CURRENT_MIGRATION_HEAD = "20260817_34"


class ApiScheduleExecutionBridge:
    """API katmanı zamanlayıcı köprüsü: yalnız kural sürüm doğrulaması yapar.

    Tetikleme (start_scheduled) worker sürecinde kalır; API üzerinden
    çağrılırsa fail-closed reddedilir.
    """

    def __init__(self, rule_catalog: Any, source_catalog: Any) -> None:
        self._rule_catalog = rule_catalog
        self._source_catalog = source_catalog

    def validate_rule_versions(self, rule_version_ids: tuple[str, ...]) -> tuple[str, ...]:
        return validate_rule_versions_for_catalogs(
            self._rule_catalog, self._source_catalog, rule_version_ids
        )

    def start_scheduled(self, **kwargs: Any) -> Any:
        raise ExecutionValidationError("Scheduled triggering runs in the worker process.")


# Migration zincirinin head'i tarafindan olusturulan tam tablo envanteri.
# tests/unit/test_migration_preflight.py bu iki sabiti alembic/versions ile
# karsilastirir; yeni migration eklendiginde ikisi birlikte guncellenmelidir.
REQUIRED_TABLES = frozenset(
    {
        "audit_events",
        "audit_outbox",
        "background_jobs",
        "connection_test_results",
        "data_fields",
        "data_processing_inventory_versions",
        "data_profiles",
        "data_quality_issues",
        "data_source_activation_requests",
        "data_source_connection_revisions",
        "data_sources",
        "dataset_partial_score_policies",
        "datasets",
        "discovery_scopes",
        "execution_attempts",
        "governance_approval_requests",
        "issue_evidence",
        "issue_evidence_files",
        "issue_history",
        "issue_relationships",
        "issue_resolutions",
        "issue_verifications",
        "job_dead_letters",
        "lineage_evidence_snapshots",
        "metadata_diffs",
        "metadata_discovery_results",
        "notification_channels",
        "notification_deliveries",
        "notification_events",
        "notification_subscriptions",
        "profile_comparisons",
        "quality_rules",
        "quality_scores",
        "report_schedules",
        "reports",
        "rule_approval_requests",
        "rule_execution_results",
        "rule_executions",
        "rule_test_results",
        "rule_versions",
        "schedules",
        "score_contribution_graphs",
        "score_publications",
        "scoring_configuration_approvals",
        "scoring_configurations",
        "source_usage_policies",
        "sql_query_templates",
        "workers",
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


def _build_governance_recipient_provider(
    registry: DevelopmentUserRegistry,
) -> Callable[[GovernanceApprovalRequest, str], list[str]]:
    """Return a provider that yields governance specialist user IDs."""

    def _provider(
        request: GovernanceApprovalRequest, event_type: str
    ) -> list[str]:
        return [
            user.user_id
            for user in registry.list_users()
            if "DATA_GOVERNANCE_SPECIALIST" in user.roles
        ]

    return _provider


def _build_governance_actor_id_resolver(
    registry: DevelopmentUserRegistry,
) -> Callable[[str], str | None]:
    """Return a resolver that maps actor UUIDs to notification-compatible user IDs."""

    def _resolver(actor_or_user_id: str) -> str | None:
        user = registry.get_user(actor_or_user_id)
        return user.user_id if user is not None else None

    return _resolver


class DefaultGovernanceApprovalNotificationSink:
    """Governance approval notification sink — builds NotificationEvent and publishes."""

    def __init__(
        self,
        notification_publisher: object,
        actor_context_provider: Callable[[], ActorContext] | None,
    ) -> None:
        self._publisher = notification_publisher
        self._actor_context_provider = actor_context_provider

    def publish_governance_approval_event(
        self,
        *,
        event_type: str,
        approval_request_id: str,
        request_type: str,
        object_type: str,
        object_id: str,
        object_name: str,
        scope_type: str,
        scope_id: str,
        maker_actor_id: str,
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
        try:
            notif_event_type = NotificationEventType(event_type)
        except ValueError:
            return
        try:
            notif_scope_type = NotificationScopeType(scope_type)
        except ValueError:
            notif_scope_type = NotificationScopeType.GOVERNANCE
        event = NotificationEvent(
            event_type=notif_event_type,
            scope_type=notif_scope_type,
            scope_id=scope_id or object_id,
            deduplication_key=(
                f"governance-approval-{event_type}-{approval_request_id}"
            ),
            occurred_at=datetime.now(timezone.utc),
            correlation_id=correlation_id,
            source_ref=f"{object_type}:{object_id}",
            payload={
                "approval_request_id": approval_request_id,
                "request_type": request_type,
                "object_type": object_type,
                "object_id": object_id,
                "object_name": object_name,
                "maker_actor_id": maker_actor_id,
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

    # Kanit dosyasi malware tarayicisi: yapilandirilmamissa None kalir ve
    # yukleme akisi fail-closed davranir (yuklenen dosya SCAN_FAILED olur).
    evidence_scanner = build_production_scanner()

    def readiness_check() -> None:
        with session_factory() as session:
            session.execute(text("SELECT 1"))
        if evidence_scanner is not None:
            evidence_scanner.ping()

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
    postgresql_connector = PostgreSQLConnector(SQLAlchemyPostgreSQLDriver())
    service = DataSourceService(
        repository,
        ConnectorRegistry([postgresql_connector]),
        secret_resolver,
        audit_sink=audit_service,
        transactional_audit=transactional_audit,
        activation_policy=command_policy,
        enforce_command_authorization=True,
    )
    dataset_preview_service = DatasetPreviewService(
        reader=repository,
        connector=postgresql_connector,
        secret_resolver=secret_resolver,
    )
    command_adapter = DataSourceCommandAdapter(service, query_service, audit_service)
    rule_query_service = RuleQueryService(rule_repository, authorization)
    job_queue_repository = PostgreSQLJobQueueRepository(session_factory)
    governance_approval_repository = PostgreSQLGovernanceApprovalRepository(
        session_factory, schema=settings.database.schema
    )
    governance_policy = GovernanceApprovalPolicy(
        version="GOVERNANCE_APPROVAL_POLICY_V1",
        actor_policy_version=settings.actor_policy_version,
        maker_roles=frozenset({"DATA_STEWARD", "DATA_GOVERNANCE_SPECIALIST"}),
        checker_roles=frozenset({"DATA_OWNER"}),
        applier_roles=frozenset({"DATA_GOVERNANCE_SPECIALIST"}),
    )

    # Composite catalog for governance command service (dataset + rule + execution + dead-letter)
    class _GovernanceCompositeCatalog:
        def __init__(self, source_repo, rule_repo, exec_repo, job_repo):
            self._source_repo = source_repo
            self._rule_repo = rule_repo
            self._exec_repo = exec_repo
            self._job_repo = job_repo

        def get_dataset(self, dataset_id):
            return self._source_repo.get_dataset(dataset_id)

        def get_data_field(self, field_id):
            return self._source_repo.get_data_field(field_id)

        def get_rule_version(self, rule_version_id):
            return self._rule_repo.get_version(rule_version_id)

        def get_rule(self, quality_rule_id):
            return self._rule_repo.get_rule(quality_rule_id)

        def get_execution(self, execution_id):
            return self._exec_repo.get(execution_id)

        def get_dead_letter(self, dead_letter_id):
            for letter in self._job_repo.list_dead_letters():
                if letter.dead_letter_id == dead_letter_id:
                    return letter
            raise KeyError(f"Dead letter {dead_letter_id} not found")

    governance_catalog = _GovernanceCompositeCatalog(
        repository, rule_repository, execution_repository, job_queue_repository
    )
    schedule_repository = PostgreSQLScheduleRepository(
        session_factory, schema=settings.database.schema
    )
    scheduling_service = SchedulingService(
        schedule_repository,
        ApiScheduleExecutionBridge(rule_repository, repository),
        transactional_audit=transactional_audit,
    )
    governance_command_service = GovernanceApprovalCommandService(
        governance_approval_repository,
        governance_catalog,
        PostgreSQLDatasetOwnershipWriter(repository),
        audit_sink=audit_service,
        transactional_audit=transactional_audit,
        policy=governance_policy,
        metadata_writer=PostgreSQLMetadataGovernanceWriter(repository),
        diff_writer=None,  # wired after metadata command service
        execution_writer=None,  # wired after execution services
        schedule_writer=PostgreSQLScheduleGovernanceWriter(scheduling_service),
        notification_recipient_provider=(
            _build_governance_recipient_provider(development_user_registry)
            if development_user_registry is not None
            else None
        ),
        notification_actor_id_resolver=(
            _build_governance_actor_id_resolver(development_user_registry)
            if development_user_registry is not None
            else None
        ),
    )
    governance_query_service = GovernanceApprovalQueryService(
        rule_repository,
        repository,
        authorization,
        center_reader=governance_approval_repository,
        center_policy=governance_policy,
    )
    sql_template_service = SqlTemplateService(
        PostgreSQLSqlTemplateRepository(session_factory),
        clock=lambda: datetime.now(timezone.utc),
    )
    issue_query_service = IssueQueryService(issue_repository, authorization)
    execution_query_service = ExecutionQueryService(execution_repository, authorization)
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
    # Execution governance guard and writer
    execution_governance_guard = ExecutionCriticalityGuard(
        rule_lookup=rule_repository,
        dataset_lookup=repository,
        execution_lookup=execution_repository,
    )
    execution_governance_writer = PostgreSQLExecutionGovernanceWriter(
        start_service=execution_start_service,
        cancel_service=execution_cancel_service,
        job_queue=job_queue_repository,
        transactional_audit=transactional_audit,
    )
    # Wire execution writer into governance command service
    governance_command_service.execution_writer = execution_governance_writer
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
        # Wire governance notification sink
        governance_approval_notification_sink = DefaultGovernanceApprovalNotificationSink(
            notification_publisher=notification_publisher,
            actor_context_provider=(
                phase_b_providers.issue_notification_actor_context_provider
                if phase_b_providers is not None
                else None
            ),
        )
        governance_command_service.notification_sink = governance_approval_notification_sink
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
    # Wire metadata diff writer into governance command service
    governance_command_service.diff_writer = PostgreSQLDiffGovernanceWriter(service, repository)
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
    scoring_configuration_service = ScoringConfigurationService(
        score_repository,
        transactional_audit=transactional_audit,
        approval_policy=ScoringApprovalPolicy(
            version="SCORING_APPROVAL_POLICY_V1",
            actor_policy_version=settings.actor_policy_version,
            maker_roles=frozenset({"DATA_STEWARD", "DATA_GOVERNANCE_SPECIALIST"}),
            checker_roles=frozenset({"DATA_OWNER"}),
        ),
    )

    # Analytics insights reader and services
    insights_reader = PostgreSQLInsightsReader(session_factory, schema=settings.database.schema)
    rule_health_service = RuleHealthQueryService(
        reader=insights_reader,
        authorization_service=authorization,
    )
    metadata_health_service = MetadataHealthQueryService(
        reader=insights_reader,
        authorization_service=authorization,
        stale_after_days=30,
        classification_policy_version="CLASSIFICATION_POLICY_V1",
    )
    issue_performance_service = IssuePerformanceQueryService(
        reader=insights_reader,
        authorization_service=authorization,
    )
    scoring_policy_impact_service = ScoringPolicyImpactQueryService(
        reader=insights_reader,
        score_reader=insights_reader,
        authorization_service=authorization,
    )

    # Issue investigation kanıtı kaynak execution sonucundan okunur.
    from veri_kalitesi.issues.investigation import IssueInvestigationEvidenceService

    issue_investigation_evidence_service = IssueInvestigationEvidenceService(
        reader=issue_repository,
        authorization_service=authorization,
        evidence_provider=PostgreSQLIssueEvidenceProvider(
            issue_repository,
            execution_repository,
            rule_repository,
        ),
    )

    # Cozum kaniti defteri: adaylar kaynak calistirmanin sonuc ve loglarindan turetilir,
    # secilen aday issue_evidence tablosuna yazilir ve cozum kaydi ona FK ile baglanir.
    from veri_kalitesi.issues.evidence import IssueEvidenceService
    from veri_kalitesi.issues.evidence_candidates import (
        ExecutionIssueEvidenceCandidateProvider,
    )

    issue_evidence_service = IssueEvidenceService(
        issue_reader=issue_repository,
        evidence_store=issue_repository,
        candidate_provider=ExecutionIssueEvidenceCandidateProvider(
            execution_repository,
            rule_repository,
        ),
        authorization_service=authorization,
        clock=lambda: datetime.now(timezone.utc),
    )
    from veri_kalitesi.issues.evidence_files import (
        EvidenceFilePolicy,
        IssueEvidenceFileService,
        LocalEvidenceStorage,
    )
    import os

    issue_evidence_upload_service = IssueEvidenceFileService(
        issue_reader=issue_repository,
        repository=issue_repository,
        authorization_service=authorization,
        storage=LocalEvidenceStorage(
            os.environ.get("DQ_EVIDENCE_STORAGE_ROOT", ".local/issue-evidence")
        ),
        # clamd yapilandirilmamissa None kalir; tarayicisiz kurulum fail-closed
        # davranir ve hicbir dosya AVAILABLE olmaz (DQ_CLAMAV_HOST/SOCKET).
        scanner=evidence_scanner,
        policy=EvidenceFilePolicy(version="EVIDENCE_FILE_POLICY_V1"),
        audit_sink=audit_service,
        clock=lambda: datetime.now(timezone.utc),
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
            evidence_catalog=issue_evidence_service,
            evidence_upload=issue_evidence_upload_service,
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
            governance_guard=execution_governance_guard,
        ),
        audit=AuditServices(query=audit_query_service, command=audit_service),
        catalog=CatalogServices(
            metadata_command=metadata_command_service,
            query=catalog_query_service,
            score_query=score_query_service,
            dashboard_query=dashboard_query_service,
            preview=dataset_preview_service,
        ),
        notifications=NotificationServices(
            query=notification_query_service,
            delivery=notification_delivery_service,
        ),
        reporting=ReportingServices(query=report_query_service),
        governance=GovernanceServices(
            query=governance_query_service,
            command=governance_command_service,
        ),
        scoring_configurations=ScoringConfigurationServices(
            command=scoring_configuration_service,
            reader=score_repository,
        ),
        sql_templates=SqlTemplateServices(service=sql_template_service),
        analytics=AnalyticsServices(
            rule_health=rule_health_service,
            metadata_health=metadata_health_service,
            issue_performance=issue_performance_service,
            scoring_policy_impact=scoring_policy_impact_service,
        ),
        schedules=ScheduleServices(scheduling=scheduling_service),
    )
    app.state.application_settings = settings
    app.state.session_factory = session_factory
    app.state.data_source_repository = repository
    app.state.rule_repository = rule_repository
    app.state.issue_repository = issue_repository
    app.state.execution_repository = execution_repository
    app.state.scheduling_service = scheduling_service
    app.state.scheduling_service = scheduling_service
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
