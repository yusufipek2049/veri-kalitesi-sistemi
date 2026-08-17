"""DS-04 metadata command service — request/scope/apply orchestration.

HTTP transaction, connector execution ve salt-okunur katalog sorgusunu
birbirinden ayıran uygulama servisi.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from veri_kalitesi.data_sources.contracts import DataSourceRepository, DataSourceTransactionalAudit
from veri_kalitesi.data_sources.errors import AuthorizationError
from veri_kalitesi.data_sources.models import (
    DataSourceCommandPolicy,
    DiscoveryScope,
    MetadataDiscoveryResult,
)
from veri_kalitesi.data_sources.service import DataSourceService
from veri_kalitesi.identity import ActorContext, ActorType, is_trusted_actor_context
from veri_kalitesi.jobs.models import BackgroundJob


class JobEnqueuer(Protocol):
    def enqueue(
        self,
        job: BackgroundJob,
        *,
        audit_event: Any | None = None,
        audit_outbox: Any | None = None,
        session: Any | None = None,
    ) -> tuple[BackgroundJob, bool]: ...


@dataclass(frozen=True)
class PostgreSQLMetadataCommandService:
    """Discovery request + scope update + diff apply orchestration.

    Her yöntem trusted ActorContext doğrulaması yapar; policy version,
    actor type, roller ve permitted_source_ids kontrol edilir.
    """

    service: DataSourceService
    repository: DataSourceRepository[Any]
    transactional_audit: DataSourceTransactionalAudit
    job_enqueuer: JobEnqueuer
    command_policy: DataSourceCommandPolicy

    def request_discovery(
        self,
        *,
        actor_context: ActorContext,
        data_source_id: str,
        idempotency_key: str | None = None,
        correlation_id: str,
    ) -> MetadataDiscoveryResult:
        self._assert_user_actor(
            actor_context,
            required_roles=self.command_policy.metadata_discovery_roles,
            data_source_id=data_source_id,
        )
        discovery = self.service.request_discovery(
            actor_id=actor_context.actor_id,
            data_source_id=data_source_id,
            correlation_id=correlation_id,
        )
        job = BackgroundJob(
            job_type="METADATA_DISCOVERY",
            payload={
                "discovery_id": discovery.discovery_id,
                "data_source_id": data_source_id,
            },
            idempotency_key=idempotency_key or f"discovery-{discovery.discovery_id}",
        )
        self.job_enqueuer.enqueue(job)
        return discovery

    def update_discovery_scope(
        self,
        *,
        actor_context: ActorContext,
        data_source_id: str,
        include_patterns: list[str],
        exclude_patterns: list[str],
        page_size: int,
        max_objects: int,
        timeout_seconds: int,
        expected_version: int,
        policy_version: str,
        correlation_id: str,
    ) -> DiscoveryScope:
        self._assert_user_actor(
            actor_context,
            required_roles=self.command_policy.metadata_scope_configurer_roles,
            data_source_id=data_source_id,
        )
        return self.service.update_discovery_scope(
            actor_id=actor_context.actor_id,
            data_source_id=data_source_id,
            include_patterns=tuple(include_patterns),
            exclude_patterns=tuple(exclude_patterns),
            page_size=page_size,
            max_objects=max_objects,
            timeout_seconds=timeout_seconds,
            expected_version=expected_version,
            policy_version=policy_version,
            correlation_id=correlation_id,
        )

    def update_dataset(
        self,
        *,
        dataset_id: str,
        updates: dict[str, Any],
        expected_version: int,
        actor_context: ActorContext,
        correlation_id: str,
    ) -> Any:
        """Dataset bilgilerini güncelle."""
        # Get dataset to verify source access
        dataset = self.repository.get_dataset(dataset_id)
        self._assert_user_actor(
            actor_context,
            required_roles=self.command_policy.metadata_diff_applier_roles,
            data_source_id=dataset.data_source_id,
        )
        return self.repository.update_dataset(
            dataset_id=dataset_id,
            updates=updates,
            expected_version=expected_version,
        )

    def update_field(
        self,
        *,
        field_id: str,
        updates: dict[str, Any],
        expected_version: int,
        actor_context: ActorContext,
        correlation_id: str,
    ) -> Any:
        """Field bilgilerini güncelle."""
        # Get field to verify source access
        field = self.repository.get_data_field(field_id)
        dataset = self.repository.get_dataset(field.dataset_id)
        self._assert_user_actor(
            actor_context,
            required_roles=self.command_policy.metadata_diff_applier_roles,
            data_source_id=dataset.data_source_id,
        )
        return self.repository.update_field(
            field_id=field_id,
            updates=updates,
            expected_version=expected_version,
        )

    def _assert_user_actor(
        self,
        actor_context: ActorContext,
        *,
        required_roles: frozenset[str],
        data_source_id: str,
    ) -> None:
        if not is_trusted_actor_context(actor_context):
            raise AuthorizationError("Trusted actor context is required.")
        if actor_context.actor_type is not ActorType.USER:
            raise AuthorizationError("Metadata commands require a USER actor type.")
        if actor_context.privileged:
            raise AuthorizationError("Non-privileged workflow is required.")
        now = self.service.clock()
        if actor_context.issued_at > now or actor_context.expires_at <= now:
            raise AuthorizationError("Actor context has expired.")
        if actor_context.policy_version != self.command_policy.actor_policy_version:
            raise AuthorizationError("Actor policy version mismatch.")
        if data_source_id not in actor_context.permitted_source_ids:
            raise AuthorizationError("Data source is outside the permitted scope.")
        if actor_context.roles.isdisjoint(required_roles):
            raise AuthorizationError("Actor does not hold the required metadata role.")
