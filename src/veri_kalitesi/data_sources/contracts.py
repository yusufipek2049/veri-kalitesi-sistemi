"""DataSource kalıcılığı ve atomik audit için repository sözleşmesi.

İterasyon 36D0 — Data sources PostgreSQL migration.
Issues/contracts.py ve rules/contracts.py şablonunu izler.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol, TypeVar

from veri_kalitesi.audit.models import (
    AuditEventInput,
    PreparedAuditEvent,
)
from veri_kalitesi.audit.outbox import AuditOutboxStatus
from veri_kalitesi.data_protection import (
    DataProcessingInventory,
    InventoryCoverageItem,
)
from veri_kalitesi.data_sources.models import (
    ConnectionTestResult,
    DataField,
    DataProfile,
    DiscoveryScope,
    ProfileComparison,
    DataSource,
    DataSourceActivationRequest,
    DataSourceConnectionRevision,
    Dataset,
    MetadataDiff,
    MetadataDiscoveryResult,
)


class DataSourceTransactionalAudit(Protocol):
    """DataSource domaini için transactional audit outbox sözleşmesi."""

    def prepare(self, event: AuditEventInput) -> PreparedAuditEvent: ...

    def publish_pending(self, *, limit: int = 100) -> AuditOutboxStatus: ...


AuditT = TypeVar("AuditT", bound=DataSourceTransactionalAudit)
AuditRepoT = TypeVar("AuditRepoT", bound=DataSourceTransactionalAudit, contravariant=True)


class DataSourceRepository(Protocol[AuditRepoT]):
    """DataSource domaini için repository sözleşmesi (generic audit outbox ile).

    SQLiteDataSourceRepository ve PostgreSQLDataSourceRepository bu sözleşmeyi uygular.
    """

    # --- Read methods ---

    def get_data_source(self, data_source_id: str) -> DataSource: ...

    def list_data_sources(self, allowed_source_ids: frozenset[str]) -> list[DataSource]: ...

    def list_all_data_sources(self) -> list[DataSource]: ...

    def latest_connection_test(
        self,
        data_source_id: str,
        *,
        data_source_revision: int | None = None,
    ) -> ConnectionTestResult | None: ...

    def next_connection_revision(self, data_source_id: str) -> int: ...

    def latest_pending_connection_revision(
        self,
        data_source_id: str,
    ) -> DataSourceConnectionRevision | None: ...

    def get_connection_revision(
        self,
        connection_revision_id: str,
    ) -> DataSourceConnectionRevision: ...

    def count_pending_activation_requests_except(
        self,
        data_source_id: str,
        revision: int,
    ) -> int: ...

    def get_activation_request(
        self,
        activation_request_id: str,
    ) -> DataSourceActivationRequest: ...

    def latest_pending_activation_request(
        self,
        data_source_id: str,
    ) -> DataSourceActivationRequest | None: ...

    def list_due_activation_requests(
        self,
        as_of: datetime,
    ) -> list[DataSourceActivationRequest]: ...

    def list_datasets(self, data_source_id: str) -> list[Dataset]: ...

    def list_data_fields(self, dataset_id: str) -> list[DataField]: ...

    def get_dataset(self, dataset_id: str) -> Dataset: ...

    def get_data_field(self, data_field_id: str) -> DataField: ...

    def list_metadata_snapshot(
        self,
        data_source_id: str,
    ) -> dict[tuple[str, str], list[DataField]]: ...

    def list_data_profiles(self, dataset_id: str) -> list[DataProfile]: ...

    def list_profile_comparisons(self, dataset_id: str) -> list[ProfileComparison]: ...

    def next_processing_inventory_version(self, data_field_id: str) -> int: ...

    def list_processing_inventory_history(
        self,
        data_field_id: str,
    ) -> list[DataProcessingInventory]: ...

    def get_current_processing_inventory(
        self,
        data_field_id: str,
    ) -> DataProcessingInventory | None: ...

    def list_processing_inventory_coverage(
        self,
        data_source_id: str | None = None,
    ) -> tuple[InventoryCoverageItem, ...]: ...

    def dump_data_source_storage(self, data_source_id: str) -> dict[str, Any]: ...

    # --- Write methods (with audit) ---

    def add_data_source(
        self,
        data_source: DataSource,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: AuditRepoT,
    ) -> DataSource: ...

    def deactivate_data_source(
        self,
        data_source_id: str,
        *,
        expected_revision: int,
        audit_event: PreparedAuditEvent,
        audit_outbox: AuditRepoT,
    ) -> DataSource: ...

    def update_connection_test(
        self,
        result: ConnectionTestResult,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: AuditRepoT,
    ) -> None: ...

    def add_connection_revision(
        self,
        revision: DataSourceConnectionRevision,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: AuditRepoT,
    ) -> DataSourceConnectionRevision: ...

    def record_connection_revision_test(
        self,
        revision: DataSourceConnectionRevision,
        result: ConnectionTestResult,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: AuditRepoT,
    ) -> DataSourceConnectionRevision: ...

    def add_activation_request(
        self,
        request: DataSourceActivationRequest,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: AuditRepoT,
    ) -> DataSourceActivationRequest: ...

    def decide_activation_request(
        self,
        request: DataSourceActivationRequest,
        *,
        activate_source: bool,
        audit_event: PreparedAuditEvent,
        audit_outbox: AuditRepoT,
    ) -> DataSourceActivationRequest: ...

    def withdraw_activation_request(
        self,
        request: DataSourceActivationRequest,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: AuditRepoT,
    ) -> DataSourceActivationRequest: ...

    def expire_activation_request(
        self,
        request: DataSourceActivationRequest,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: AuditRepoT,
    ) -> DataSourceActivationRequest: ...

    def latest_pending_deactivation_request(
        self,
        data_source_id: str,
    ) -> DataSourceActivationRequest | None: ...

    def add_deactivation_request(
        self,
        request: DataSourceActivationRequest,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: AuditRepoT,
    ) -> DataSourceActivationRequest: ...

    def decide_deactivation_request(
        self,
        request: DataSourceActivationRequest,
        *,
        deactivate_source: bool,
        audit_event: PreparedAuditEvent,
        audit_outbox: AuditRepoT,
    ) -> DataSourceActivationRequest: ...

    def replace_metadata(
        self,
        data_source_id: str,
        datasets: list[Dataset],
        fields_by_dataset_id: dict[str, list[DataField]],
        result: MetadataDiscoveryResult,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: AuditRepoT,
    ) -> None: ...

    def record_metadata_discovery_failure(
        self,
        result: MetadataDiscoveryResult,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: AuditRepoT,
    ) -> None: ...

    # --- DS-04: async discovery lifecycle ---

    def record_discovery_request(
        self,
        result: MetadataDiscoveryResult,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: AuditRepoT,
    ) -> MetadataDiscoveryResult: ...

    def update_discovery_status(
        self,
        discovery_id: int,
        *,
        status: str,
        expected_version: int,
        finished_at: datetime | None = None,
        partial_reason_code: str | None = None,
        completed_scope: dict[str, Any] | None = None,
        scanned_object_count: int | None = None,
        error_class: str | None = None,
        message: str | None = None,
        audit_event: PreparedAuditEvent,
        audit_outbox: AuditRepoT,
    ) -> MetadataDiscoveryResult: ...

    def get_discovery_result(
        self,
        discovery_id: int,
    ) -> MetadataDiscoveryResult: ...

    def get_discovery_result_by_job(
        self,
        job_id: str,
    ) -> MetadataDiscoveryResult: ...

    # --- DS-04: discovery scope ---

    def get_discovery_scope(
        self,
        data_source_id: str,
    ) -> DiscoveryScope | None: ...

    def update_discovery_scope(
        self,
        scope: DiscoveryScope,
        *,
        expected_version: int,
        audit_event: PreparedAuditEvent,
        audit_outbox: AuditRepoT,
    ) -> DiscoveryScope: ...

    # --- DS-04: metadata diff ---

    def persist_metadata_diff(
        self,
        diff: MetadataDiff,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: AuditRepoT,
    ) -> MetadataDiff: ...

    def get_metadata_diff(
        self,
        metadata_diff_id: str,
    ) -> MetadataDiff: ...

    def get_diff_by_discovery(
        self,
        discovery_id: int,
    ) -> MetadataDiff | None: ...

    def list_pending_diffs(
        self,
        data_source_id: str,
    ) -> list[MetadataDiff]: ...

    def apply_metadata_diff(
        self,
        metadata_diff_id: str,
        *,
        applied_by_actor_id: str,
        reason_code: str,
        expected_version: int,
        datasets: list[Dataset],
        fields_by_dataset_id: dict[str, list[DataField]],
        passivated_dataset_ids: list[str],
        passivated_field_ids: list[str],
        audit_event: PreparedAuditEvent,
        audit_outbox: AuditRepoT,
    ) -> MetadataDiff: ...

    def add_data_profile(
        self,
        profile: DataProfile,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: AuditRepoT,
    ) -> DataProfile: ...

    def add_profile_comparison(
        self,
        comparison: ProfileComparison,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: AuditRepoT,
    ) -> ProfileComparison: ...

    def add_processing_inventory(
        self,
        inventory: DataProcessingInventory,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: AuditRepoT,
    ) -> DataProcessingInventory: ...

    # --- Catalog entity updates ---

    def update_dataset(
        self,
        *,
        dataset_id: str,
        updates: dict[str, Any],
        expected_version: int,
    ) -> Dataset: ...

    def update_field(
        self,
        *,
        field_id: str,
        updates: dict[str, Any],
        expected_version: int,
    ) -> DataField: ...
