"""Production worker composition with concrete execution executor."""

from __future__ import annotations

from typing import TYPE_CHECKING
from datetime import datetime, timezone

if TYPE_CHECKING:
    from veri_kalitesi.identity import ActorContext
    from veri_kalitesi.notifications.models import NotificationEvent
    from veri_kalitesi.reporting.models import Report, ReportRequest

from veri_kalitesi.audit.models import (
    AuditFailureMode,
    AuditFailurePolicy,
)
from veri_kalitesi.audit.policies import build_default_redaction_policy
from veri_kalitesi.audit.postgresql_outbox import PostgreSQLTransactionalAudit
from veri_kalitesi.audit.postgresql_repository import PostgreSQLAuditRepository
from veri_kalitesi.audit.redaction import AuditRedactor
from veri_kalitesi.audit.service import AuditService
from veri_kalitesi.data_sources.connectors import ConnectorRegistry
from veri_kalitesi.data_sources.postgresql import PostgreSQLConnector
from veri_kalitesi.data_sources.postgresql_driver import SQLAlchemyPostgreSQLDriver
from veri_kalitesi.data_sources.postgresql_repository import PostgreSQLDataSourceRepository
from veri_kalitesi.data_sources.secrets import MountedFileSecretResolver, SecretResolver
from veri_kalitesi.data_sources.service import DataSourceService
from veri_kalitesi.executions.postgresql_repository import PostgreSQLExecutionRepository
from veri_kalitesi.executions.postgresql_scheduling import PostgreSQLScheduleRepository
from veri_kalitesi.executions.scheduling import Schedule, SchedulingService
from veri_kalitesi.executions.postgresql_executor import PostgreSQLRuleExecutionExecutor
from veri_kalitesi.executions.postgresql_source_usage import (
    PostgreSQLSourceUsagePolicyRepository,
)
from veri_kalitesi.jobs.composition import (
    PersistentJobRuntime,
    create_persistent_job_runtime,
)
from veri_kalitesi.jobs.lifecycle import DeadLetterReprocessPolicy
from veri_kalitesi.jobs.metadata_command import PersistentMetadataDiscoveryCommandAdapter
from veri_kalitesi.jobs.models import JobLeasePolicy
from veri_kalitesi.jobs.settings import PersistentJobSettings
from veri_kalitesi.persistence import create_session_factory
from veri_kalitesi.rules import PostgreSQLRuleRepository


def create_production_worker(
    settings: PersistentJobSettings,
) -> PersistentJobRuntime:
    """Production worker'ı gerçek PG repository/audit/policy ile kurar.

    Fake/no-op executor composition root'a taşınmaz; eksik provider'da
    worker process fail-fast çıkar.

    Varsayılan entrypoint'in desteklediği bütün iş tipleri koşulsuz bağlanır.
    """

    session_factory = create_session_factory(settings.database)
    schema = settings.database.schema

    def production_clock() -> datetime:
        return datetime.now(timezone.utc)

    audit_repository = PostgreSQLAuditRepository(session_factory, schema=schema)
    redactor = AuditRedactor(build_default_redaction_policy())
    audit_service = AuditService(
        audit_repository,
        redactor,
        AuditFailurePolicy(
            version="AUDIT_OUTBOX_V1_FAILURE",
            default_mode=AuditFailureMode.FAIL_CLOSED,
        ),
    )
    transactional_audit = PostgreSQLTransactionalAudit(
        session_factory,
        redactor,
        audit_repository,
        policy_version="AUDIT_OUTBOX_V1",
        schema=schema,
    )

    rule_repository = PostgreSQLRuleRepository(session_factory, schema=schema)
    source_repository = PostgreSQLDataSourceRepository(session_factory, schema=schema)
    execution_repository = PostgreSQLExecutionRepository(session_factory, schema=schema)
    policy_repository = PostgreSQLSourceUsagePolicyRepository(session_factory, schema=schema)

    connector = PostgreSQLConnector(SQLAlchemyPostgreSQLDriver())
    secret_resolver = (
        MountedFileSecretResolver(settings.local_secret_dir)
        if settings.local_secret_dir
        else _require_secret_resolver()
    )

    executor = PostgreSQLRuleExecutionExecutor(
        rule_repository=rule_repository,
        source_repository=source_repository,
        secret_resolver=secret_resolver,
        connector=connector,
    )

    from veri_kalitesi.executions.service import ExecutionService

    execution_service: ExecutionService = ExecutionService(
        repository=execution_repository,
        rule_catalog=rule_repository,
        source_catalog=source_repository,
        executor=executor,
        source_usage_policy_resolver=policy_repository,
        clock=production_clock,
    )

    # ── Issue bridge & service wiring ──────────────────────────────────
    from veri_kalitesi.identity import create_service_actor_context
    from veri_kalitesi.issues.assignment import OwnershipIssueAssignmentResolver
    from veri_kalitesi.issues.execution_bridge import ExecutionIssueTriggerAdapter
    from veri_kalitesi.issues.models import (
        IssueAccessPolicy,
        IssueAssigneeProfile,
    )
    from veri_kalitesi.issues.postgresql_repository import PostgreSQLIssueRepository
    from veri_kalitesi.issues.service import IssueService
    from veri_kalitesi.notifications.postgresql_repository import (
        PostgreSQLNotificationRepository,
    )

    issue_repository = PostgreSQLIssueRepository(session_factory, schema=schema)
    notification_repository = PostgreSQLNotificationRepository(session_factory, schema=schema)

    class _ProductionIssueAssigneeDirectory:
        """Production assignee directory — owner is always active if they exist."""

        def __init__(self, source_repo: PostgreSQLDataSourceRepository) -> None:
            self._source_repo = source_repo

        def get_assignee_profile(self, user_id: str) -> "IssueAssigneeProfile | None":
            if not user_id:
                return None
            return IssueAssigneeProfile(
                user_id=user_id,
                active=True,
                permitted_source_ids=frozenset(),
                permitted_dataset_ids=frozenset(),
            )

    assignee_directory = _ProductionIssueAssigneeDirectory(source_repository)

    assignment_resolver = OwnershipIssueAssignmentResolver(
        rule_version_lookup=rule_repository,
        rule_lookup=rule_repository,
        dataset_lookup=source_repository,
        data_source_lookup=source_repository,
        assignee_directory=assignee_directory,
    )

    class _WorkerNotificationPublisher:
        """Worker-scoped notification publisher — creates staged events/deliveries."""

        def __init__(self, repo: PostgreSQLNotificationRepository) -> None:
            self._repo = repo

        def create_for_event(
            self,
            event: "NotificationEvent",
            actor_context: "ActorContext | None",
        ) -> tuple[object, ...]:
            import hashlib
            from uuid import uuid4 as _uuid4

            from veri_kalitesi.notifications.contracts import _StagedDelivery, _StagedEvent
            from veri_kalitesi.notifications.models import (
                NotificationDeliveryStatus,
            )
            now = __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            )
            staged_event = _StagedEvent(
                event_id=event.event_id,
                event_type=event.event_type.value,
                scope_type=event.scope_type.value,
                scope_id=event.scope_id,
                source_ref=event.source_ref or "",
                deduplication_key_digest=hashlib.sha256(
                    event.deduplication_key.encode()
                ).hexdigest()[:32],
                payload_digest=hashlib.sha256(
                    str(event.payload).encode()
                ).hexdigest()[:16],
                payload=event.payload,
                correlation_id=event.correlation_id,
                policy_version=event.policy_version,
                occurred_at=event.occurred_at,
                published_at=now,
            )
            delivery_id = str(_uuid4())
            recipient = (
                actor_context.actor_id
                if actor_context is not None
                else "worker-notification-sink"
            )
            staged_delivery = _StagedDelivery(
                delivery_id=delivery_id,
                event_id=event.event_id,
                recipient_user_id=recipient,
                channel_id="default-inapp-channel",
                status=NotificationDeliveryStatus.DELIVERED,
                created_at=now,
            )
            with self._repo._session_factory() as session:
                self._repo._insert_event(session, staged_event)
                self._repo._insert_delivery(session, staged_delivery)
                session.commit()
            return (delivery_id,)

    worker_notification_publisher = _WorkerNotificationPublisher(notification_repository)

    def _issue_actor_context_provider() -> "ActorContext":
        return create_service_actor_context(
            actor_id="issue-creation-worker",
            correlation_id="issue-worker-correlation",
            roles=frozenset({"ISSUE_CREATION_WORKER"}),
        )

    issue_service = IssueService(
        issue_repository,
        assignment_resolver,
        worker_notification_publisher,
        transactional_audit,
        IssueAccessPolicy(
            version="ISSUE_ACCESS_V1",
            actor_policy_version=settings.actor_policy_version,
        ),
        assignee_directory=assignee_directory,
        notification_actor_context_provider=_issue_actor_context_provider,
    )

    issue_bridge = ExecutionIssueTriggerAdapter(
        execution_reader=execution_repository,
    )

    # ── Score publication wiring ───────────────────────────────────────
    from veri_kalitesi.scoring.postgresql_repository import PostgreSQLScoreRepository
    from veri_kalitesi.scoring.service import ScoringService
    from veri_kalitesi.scoring.publication import ScorePublicationService

    score_repository = PostgreSQLScoreRepository(session_factory, schema=schema)
    scoring_service = ScoringService(
        repository=score_repository,
        execution_history=execution_repository,
        rule_catalog=rule_repository,
        source_catalog=source_repository,
        clock=production_clock,
    )
    score_publication_service = ScorePublicationService(
        scoring_service=scoring_service,
        score_repository=score_repository,
        execution_history=execution_repository,
        rule_catalog=rule_repository,
        source_catalog=source_repository,
        transactional_audit=transactional_audit,
    )

    def _score_actor_context_provider() -> "ActorContext":
        return create_service_actor_context(
            actor_id="score-publication-worker",
            correlation_id="score-worker-correlation",
            roles=frozenset({"SCORE_PUBLICATION_WORKER"}),
        )

    from veri_kalitesi.jobs.execution_command import PersistentExecutionCommandAdapter

    command_adapter = PersistentExecutionCommandAdapter(
        execution_service=execution_service,
        issue_bridge=issue_bridge,
        issue_service=issue_service,
        issue_actor_context_provider=_issue_actor_context_provider,
        score_publication_service=score_publication_service,
        score_actor_context_provider=_score_actor_context_provider,
    )

    connector_registry = ConnectorRegistry([connector])
    data_source_service: DataSourceService = DataSourceService(
        source_repository,
        connector_registry,
        secret_resolver,
        audit_sink=audit_service,
        transactional_audit=transactional_audit,
    )

    from veri_kalitesi.notifications.delivery_service import NotificationDeliveryService
    from veri_kalitesi.notifications.jobs import NotificationDeliveryJobHandler
    from veri_kalitesi.notifications.transports import (
        MountedNotificationSecretResolver,
        SMTPNotificationAdapter,
        WebhookNotificationAdapter,
    )

    def _service_actor_context_provider(data_source_id: str, correlation_id: str) -> "ActorContext":
        return create_service_actor_context(
            actor_id="metadata-discovery-worker",
            correlation_id=correlation_id,
            roles=frozenset({"METADATA_DISCOVERY_WORKER"}),
            permitted_source_ids=frozenset({data_source_id}),
        )

    metadata_command_adapter = PersistentMetadataDiscoveryCommandAdapter(
        service=data_source_service,
        actor_context_provider=_service_actor_context_provider,
    )

    lease_policy = JobLeasePolicy(duration=settings.lease_policy_duration)

    notification_secret_resolver = (
        MountedNotificationSecretResolver(settings.local_secret_dir)
        if settings.local_secret_dir
        else secret_resolver
    )
    notification_handler = NotificationDeliveryJobHandler(
        delivery_service=NotificationDeliveryService(
            repository=notification_repository,
            adapters={
                "EMAIL": SMTPNotificationAdapter(notification_secret_resolver),
                "WEBHOOK": WebhookNotificationAdapter(notification_secret_resolver),
            },
        ),
    )

    class _ProductionScheduleTechnicalEventSink:
        """Zamanlayici arizalarini merkezi audit akisina yazar."""

        def notify_schedule_failure(self, schedule: Schedule, error_class: str) -> None:
            from veri_kalitesi.audit.models import AuditEventInput, AuditResult

            audit_service.append(
                AuditEventInput(
                    actor_id="schedule-worker",
                    actor_type="SERVICE",
                    correlation_id=f"schedule-failure-{schedule.schedule_id}",
                    action="SCHEDULE_TRIGGER_FAILED",
                    object_type="Schedule",
                    object_id=schedule.schedule_id,
                    result=AuditResult.FAILURE,
                    reason_code=error_class,
                    old_values={},
                    new_values={"error_class": error_class},
                    occurred_at=production_clock(),
                )
            )

    schedule_event_sink = _ProductionScheduleTechnicalEventSink()
    execution_scheduler = SchedulingService(
        PostgreSQLScheduleRepository(session_factory, schema=schema),
        execution_service,
        transactional_audit=transactional_audit,
        technical_event_sink=schedule_event_sink,
        clock=production_clock,
    )

    from veri_kalitesi.reporting.repository import (
        PostgreSQLReportRepository,
        PostgreSQLReportScheduleRepository,
    )
    from veri_kalitesi.reporting.scheduling import ReportScheduleService

    class _QueuedScheduledReportService:
        """Zamanlanmis rapor istegini kalici QUEUED kaydina donusturur."""

        def __init__(self) -> None:
            self._repository = PostgreSQLReportRepository(session_factory, schema=schema)

        def request_report(
            self,
            request: "ReportRequest",
            actor_context: "ActorContext | None",
        ) -> "Report":
            assert actor_context is not None
            return self._repository.create_report(request, actor_context.actor_id)

    report_scheduler = ReportScheduleService(
        PostgreSQLReportScheduleRepository(session_factory, schema=schema),
        _QueuedScheduledReportService(),
        technical_event_sink=schedule_event_sink,
        clock=production_clock,
    )

    return create_persistent_job_runtime(
        session_factory,
        transactional_audit=transactional_audit,
        execution_command=command_adapter,
        metadata_discovery_command=metadata_command_adapter,
        notification_delivery_handler=notification_handler,
        schedule_triggers=(execution_scheduler, report_scheduler),
        schedule_trigger_interval_seconds=settings.schedule_trigger_interval_seconds,
        worker_id=settings.worker_id,
        worker_hostname=settings.hostname,
        worker_capacity=settings.capacity,
        lease_policy=lease_policy,
        reprocess_policy=DeadLetterReprocessPolicy(
            version=settings.actor_policy_version,
            allowed_roles=frozenset({"PLATFORM_ADMIN"}),
        ),
        schema=schema,
    )


def _require_secret_resolver() -> SecretResolver:
    raise RuntimeError(
        "Production worker requires a secret resolver; "
        "set DATA_QUALITY_LOCAL_SECRET_DIR or provide a mounted secret provider."
    )
