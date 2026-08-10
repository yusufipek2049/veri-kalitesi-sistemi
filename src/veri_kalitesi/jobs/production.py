"""Production worker composition with concrete execution executor."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from veri_kalitesi.identity import ActorContext

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
        clock=lambda: __import__("datetime").datetime.now(__import__("datetime").timezone.utc),
    )

    from veri_kalitesi.jobs.execution_command import PersistentExecutionCommandAdapter

    command_adapter = PersistentExecutionCommandAdapter(
        execution_service=execution_service,
    )

    connector_registry = ConnectorRegistry([connector])
    data_source_service: DataSourceService = DataSourceService(
        source_repository,
        connector_registry,
        secret_resolver,
        audit_sink=audit_service,
        transactional_audit=transactional_audit,
    )

    from veri_kalitesi.identity import create_service_actor_context

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

    from veri_kalitesi.notifications.delivery_service import NotificationDeliveryService
    from veri_kalitesi.notifications.jobs import NotificationDeliveryJobHandler
    from veri_kalitesi.notifications.postgresql_repository import (
        PostgreSQLNotificationRepository,
    )

    notification_repository = PostgreSQLNotificationRepository(session_factory, schema=schema)
    notification_handler = NotificationDeliveryJobHandler(
        delivery_service=NotificationDeliveryService(repository=notification_repository),
    )

    return create_persistent_job_runtime(
        session_factory,
        transactional_audit=transactional_audit,
        execution_command=command_adapter,
        metadata_discovery_command=metadata_command_adapter,
        notification_delivery_handler=notification_handler,
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
