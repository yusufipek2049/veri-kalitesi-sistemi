"""Adapter: CancellableMetadataDiscoveryCommand → DataSourceService.execute_discovery_for_worker."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from threading import Event
from typing import Any, Protocol

from veri_kalitesi.data_sources.service import DataSourceService
from veri_kalitesi.identity import ActorContext
from veri_kalitesi.jobs.models import JobCompletionOutcome


class MetadataServiceActorContextProvider(Protocol):
    """Worker için güvenilir SERVICE ActorContext üretir."""

    def __call__(self, data_source_id: str, correlation_id: str) -> ActorContext: ...


@dataclass(frozen=True)
class PersistentMetadataDiscoveryCommandAdapter:
    """Queue'nun CancellableMetadataDiscoveryCommand portunu DataSourceService'e bağlar.

    Worker context'i provider üzerinden güvenilir ActorContext olarak alınır.
    Provider yoksa composition root fail-fast çıkar.
    """

    service: DataSourceService
    actor_context_provider: MetadataServiceActorContextProvider
    clock: Callable[[], Any] | None = None

    def execute(
        self,
        discovery_id: int,
        *,
        timeout_seconds: int,
        cancellation_event: Event,
        progress_callback: Callable[[int], None] = lambda _percent: None,
    ) -> JobCompletionOutcome:
        existing = self.service.repository.get_discovery_result(discovery_id)
        context = self.actor_context_provider(
            existing.data_source_id,
            existing.correlation_id or f"metadata-discovery-{discovery_id}",
        )
        result = self.service.execute_discovery_for_worker(
            discovery_id,
            actor_id=context.actor_id,
            correlation_id=context.correlation_id,
            cancellation_event=cancellation_event,
        )
        progress_callback(100)
        if result.status.value in {"SUCCESS", "PARTIAL"}:
            return JobCompletionOutcome.SUCCESS
        return JobCompletionOutcome.QUALITY_FAILURE
