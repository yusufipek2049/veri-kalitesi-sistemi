"""Metadata diff seçili uygulama birim testleri.

Kapsam:
- apply_discovery_diff: seçim filtresi, changed_objects kataloğa yazımı,
  boş/uyumsuz seçim hataları, seçilmeyen objelerin uygulanmaması.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import Any, cast

import pytest

from veri_kalitesi.audit.models import AuditFailureMode, AuditFailurePolicy
from veri_kalitesi.audit.outbox import SQLiteTransactionalAudit
from veri_kalitesi.audit.policies import build_default_redaction_policy
from veri_kalitesi.audit.redaction import AuditRedactor
from veri_kalitesi.audit.repository import SQLiteAuditRepository
from veri_kalitesi.audit.service import AuditService
from veri_kalitesi.data_protection.policy import ClassificationCode
from veri_kalitesi.data_sources.connectors import CSVConnector, ConnectorRegistry
from veri_kalitesi.data_sources.errors import NotFoundError, ValidationError
from veri_kalitesi.data_sources.models import (
    DataField,
    DataSource,
    DataSourceStatus,
    Dataset,
    MetadataDiff,
    MetadataDiffStatus,
    MetadataDiscoveryResult,
    SourceType,
)
from veri_kalitesi.data_sources.repository import SQLiteDataSourceRepository
from veri_kalitesi.data_sources.service import DataSourceService

NOW = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)


class _DiffRepository(SQLiteDataSourceRepository):
    """Diff/catalog katmanını bellekte tutan test repository'si."""

    def __init__(self) -> None:
        super().__init__()
        self.sources: dict[str, DataSource] = {}
        self.datasets_by_source: dict[str, list[Dataset]] = {}
        self.fields_by_dataset: dict[str, list[DataField]] = {}
        self.diffs: dict[str, MetadataDiff] = {}
        self.discoveries: dict[int, MetadataDiscoveryResult] = {}
        self.apply_calls: list[dict[str, Any]] = []

    def get_data_source(self, data_source_id: str) -> DataSource:
        if data_source_id not in self.sources:
            raise NotFoundError(f"Source {data_source_id}")
        return self.sources[data_source_id]

    def list_datasets(self, data_source_id: str) -> list[Dataset]:
        return list(self.datasets_by_source.get(data_source_id, []))

    def list_data_fields(self, dataset_id: str) -> list[DataField]:
        return list(self.fields_by_dataset.get(dataset_id, []))

    def get_discovery_result(self, discovery_id: int) -> MetadataDiscoveryResult:
        if discovery_id not in self.discoveries:
            raise NotFoundError(f"Discovery {discovery_id}")
        return self.discoveries[discovery_id]

    def get_metadata_diff(self, metadata_diff_id: str) -> MetadataDiff:
        if metadata_diff_id not in self.diffs:
            raise NotFoundError(f"Diff {metadata_diff_id}")
        return self.diffs[metadata_diff_id]

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
        audit_event: Any,
        audit_outbox: Any,
    ) -> MetadataDiff:
        diff = self.get_metadata_diff(metadata_diff_id)
        if diff.version != expected_version:
            raise NotFoundError("Version mismatch")
        audit_outbox.stage(audit_event)
        self.apply_calls.append(
            {
                "datasets": list(datasets),
                "fields_by_dataset_id": {k: list(v) for k, v in fields_by_dataset_id.items()},
                "passivated_dataset_ids": list(passivated_dataset_ids),
                "passivated_field_ids": list(passivated_field_ids),
            }
        )
        applied = replace(
            diff,
            status=MetadataDiffStatus.APPLIED,
            applied_at=NOW,
            applied_by_actor_id=applied_by_actor_id,
            version=diff.version + 1,
        )
        self.diffs[metadata_diff_id] = applied
        return applied


def _diff_service() -> tuple[DataSourceService, _DiffRepository]:
    repository = _DiffRepository()
    audit_repository = SQLiteAuditRepository()
    redactor = AuditRedactor(build_default_redaction_policy())
    audit_service = AuditService(
        audit_repository,
        redactor,
        AuditFailurePolicy("AUDIT_FAILURE_TEST_V1", AuditFailureMode.FAIL_CLOSED),
    )
    service = DataSourceService(
        repository,
        ConnectorRegistry([CSVConnector()]),
        None,
        audit_sink=audit_service,
        transactional_audit=SQLiteTransactionalAudit(
            repository.connection,
            redactor,
            audit_repository,
            policy_version="AUDIT_OUTBOX_TEST_V1",
        ),
        clock=lambda: NOW,
    )
    return service, repository


def _seed_catalog(repository: _DiffRepository) -> tuple[DataField, DataField]:
    repository.sources["src-1"] = DataSource(
        name="Test DB",
        source_type=SourceType.POSTGRESQL,
        connection_config={},
        secret_reference="secret://test",
        data_source_id="src-1",
        status=DataSourceStatus.ACTIVE,
    )
    repository.datasets_by_source["src-1"] = [
        Dataset(
            data_source_id="src-1",
            namespace="public",
            name="customers",
            dataset_id="ds-customers",
        )
    ]
    amount_field = DataField(
        dataset_id="ds-customers",
        name="amount",
        native_data_type="integer",
        is_nullable=True,
        data_field_id="f-amount",
    )
    legacy_field = DataField(
        dataset_id="ds-customers",
        name="legacy",
        native_data_type="text",
        data_field_id="f-legacy",
    )
    repository.fields_by_dataset["ds-customers"] = [amount_field, legacy_field]
    repository.discoveries[1] = MetadataDiscoveryResult(
        data_source_id="src-1",
        succeeded=True,
        duration_ms=10,
        discovery_id=1,
    )
    return amount_field, legacy_field


def _pending_diff() -> MetadataDiff:
    return MetadataDiff(
        metadata_diff_id="diff-1",
        discovery_id=1,
        data_source_id="src-1",
        added_objects=(
            {
                "object_type": "DATASET",
                "namespace": "public",
                "dataset_name": "orders",
                "new_values": {"dataset_type": "TABLE"},
            },
            {
                "object_type": "DATA_FIELD",
                "namespace": "public",
                "dataset_name": "customers",
                "field_name": "email",
                "new_values": {
                    "native_data_type": "text",
                    "is_nullable": True,
                    "is_sensitive": True,
                },
            },
        ),
        changed_objects=(
            {
                "object_type": "DATA_FIELD",
                "namespace": "public",
                "dataset_name": "customers",
                "field_name": "amount",
                "new_values": {"native_data_type": "numeric", "is_nullable": False},
            },
        ),
        removed_objects=(
            {
                "object_type": "DATA_FIELD",
                "namespace": "public",
                "dataset_name": "customers",
                "field_name": "legacy",
            },
        ),
    )


def _apply_call(repository: _DiffRepository) -> dict[str, Any]:
    assert len(repository.apply_calls) == 1
    return repository.apply_calls[0]


class TestApplyDiscoveryDiffSelection:
    def test_full_apply_writes_added_changed_and_removed(self) -> None:
        service, repository = _diff_service()
        _seed_catalog(repository)
        repository.diffs["diff-1"] = _pending_diff()

        applied = service.apply_discovery_diff(
            actor_id="dev-data-governance",
            metadata_diff_id="diff-1",
            reason_code="METADATA.DIFF.APPLICATION",
            expected_version=1,
        )

        assert applied.status is MetadataDiffStatus.APPLIED
        call = _apply_call(repository)
        dataset_names = {(d.namespace, d.name) for d in call["datasets"]}
        assert ("public", "orders") in dataset_names
        # changed_objects güncellemesi mevcut dataset'i upsert kapsamına alır.
        assert ("public", "customers") in dataset_names
        fields = call["fields_by_dataset_id"]["ds-customers"]
        field_names = {f.name for f in fields}
        assert field_names == {"email", "amount"}
        assert call["passivated_field_ids"] == ["f-legacy"]
        assert call["passivated_dataset_ids"] == []

    def test_changed_field_reuses_identity_and_preserves_classification(self) -> None:
        service, repository = _diff_service()
        _seed_catalog(repository)
        repository.fields_by_dataset["ds-customers"] = [
            replace(
                repository.fields_by_dataset["ds-customers"][0],
                classification=ClassificationCode.PERSONAL_DATA,
            ),
            repository.fields_by_dataset["ds-customers"][1],
        ]
        repository.diffs["diff-1"] = _pending_diff()

        service.apply_discovery_diff(
            actor_id="dev-data-governance",
            metadata_diff_id="diff-1",
            reason_code="METADATA.DIFF.APPLICATION",
            expected_version=1,
        )

        call = _apply_call(repository)
        changed = next(
            f for f in call["fields_by_dataset_id"]["ds-customers"] if f.name == "amount"
        )
        assert changed.data_field_id == "f-amount"
        assert changed.native_data_type == "numeric"
        assert changed.is_nullable is False
        assert changed.classification is ClassificationCode.PERSONAL_DATA

    def test_selection_limits_application_to_chosen_objects(self) -> None:
        service, repository = _diff_service()
        _seed_catalog(repository)
        repository.diffs["diff-1"] = _pending_diff()

        service.apply_discovery_diff(
            actor_id="dev-data-governance",
            metadata_diff_id="diff-1",
            reason_code="METADATA.DIFF.APPLICATION",
            expected_version=1,
            selected_objects=frozenset({("ADDED", "DATA_FIELD", "public", "customers", "email")}),
        )

        call = _apply_call(repository)
        fields = call["fields_by_dataset_id"]["ds-customers"]
        assert [f.name for f in fields] == ["email"]
        # Seçilmeyen changed/removed objeler uygulanmaz.
        assert call["passivated_field_ids"] == []
        assert call["passivated_dataset_ids"] == []
        dataset_names = {(d.namespace, d.name) for d in call["datasets"]}
        assert ("public", "orders") not in dataset_names

        audit_service = cast(AuditService, service.audit_sink)
        audit_repository = cast(SQLiteAuditRepository, audit_service.repository)
        events = [
            e
            for e in audit_repository.list_events()
            if e.action == "DATA_SOURCE_METADATA_DIFF_APPLIED"
        ]
        assert len(events) == 1
        assert events[0].reason_code == "METADATA.DIFF.APPLICATION"
        assert events[0].object_id == "src-1"

    def test_empty_selection_raises_validation_error(self) -> None:
        service, repository = _diff_service()
        _seed_catalog(repository)
        repository.diffs["diff-1"] = _pending_diff()

        with pytest.raises(ValidationError):
            service.apply_discovery_diff(
                actor_id="dev-data-governance",
                metadata_diff_id="diff-1",
                reason_code="METADATA.DIFF.APPLICATION",
                expected_version=1,
                selected_objects=frozenset(),
            )
        assert repository.apply_calls == []

    def test_non_matching_selection_raises_validation_error(self) -> None:
        service, repository = _diff_service()
        _seed_catalog(repository)
        repository.diffs["diff-1"] = _pending_diff()

        with pytest.raises(ValidationError):
            service.apply_discovery_diff(
                actor_id="dev-data-governance",
                metadata_diff_id="diff-1",
                reason_code="METADATA.DIFF.APPLICATION",
                expected_version=1,
                selected_objects=frozenset(
                    {("ADDED", "DATA_FIELD", "public", "customers", "missing")}
                ),
            )
        assert repository.apply_calls == []
