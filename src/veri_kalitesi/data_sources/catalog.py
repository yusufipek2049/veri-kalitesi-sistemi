"""Salt-okunur katalog sorgu servisi — scope-safe projeksiyonlar."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from veri_kalitesi.data_sources.errors import NotFoundError
from veri_kalitesi.data_sources.models import (
    DataField,
    DataSource,
    Dataset,
    DiscoveryScope,
    MetadataDiff,
    MetadataDiscoveryResult,
)


class CatalogReader(Protocol):
    """Katalog okuma için gerekli repository metotları."""

    def get_data_source(self, data_source_id: str) -> DataSource: ...

    def list_data_sources(self, allowed_source_ids: frozenset[str]) -> list[DataSource]: ...

    def list_all_data_sources(self) -> list[DataSource]: ...

    def list_datasets(self, data_source_id: str) -> list[Dataset]: ...

    def get_dataset(self, dataset_id: str) -> Dataset: ...

    def list_data_fields(self, dataset_id: str) -> list[DataField]: ...

    def get_data_field(self, data_field_id: str) -> DataField: ...

    def get_discovery_result(self, discovery_id: int) -> MetadataDiscoveryResult: ...

    def get_diff_by_discovery(self, discovery_id: int) -> MetadataDiff | None: ...

    def get_metadata_diff(self, metadata_diff_id: str) -> MetadataDiff: ...

    def list_pending_diffs(self, data_source_id: str) -> list[MetadataDiff]: ...

    def get_discovery_scope(self, data_source_id: str) -> DiscoveryScope | None: ...


@dataclass(frozen=True)
class CatalogDatasetView:
    dataset: Dataset
    data_source: DataSource
    field_count: int = 0
    last_discovery: MetadataDiscoveryResult | None = None


@dataclass(frozen=True)
class CatalogFieldView:
    field: DataField
    dataset: Dataset
    data_source: DataSource


class CatalogQueryService:
    """Scope-safe katalog okuma servisi.

    GET sorguları actor'ün ``permitted_source_ids`` ve
    ``can_view_enterprise`` kararını PostgreSQL sorgusuna taşır.
    Boş iki küme sıfır sonuçtur; 'tüm katalog' anlamına gelmez.
    """

    def __init__(self, reader: CatalogReader) -> None:
        self.reader = reader

    def list_datasets_for_actor(
        self,
        *,
        permitted_source_ids: frozenset[str],
        status_filter: str | None = None,
        name_contains: str | None = None,
        limit: int = 200,
    ) -> list[CatalogDatasetView]:
        if not permitted_source_ids:
            return []
        bounded_limit = min(max(1, limit), 500)
        views: list[CatalogDatasetView] = []
        for source_id in sorted(permitted_source_ids):
            try:
                source = self.reader.get_data_source(source_id)
            except NotFoundError:
                continue
            datasets = self.reader.list_datasets(source_id)
            for dataset in datasets:
                if status_filter and dataset.status.value != status_filter:
                    continue
                if name_contains and name_contains.lower() not in dataset.name.lower():
                    continue
                fields = self.reader.list_data_fields(dataset.dataset_id)
                views.append(
                    CatalogDatasetView(
                        dataset=dataset,
                        data_source=source,
                        field_count=len(fields),
                    )
                )
                if len(views) >= bounded_limit:
                    return views
        return views

    def get_dataset_view(
        self,
        dataset_id: str,
        *,
        permitted_source_ids: frozenset[str],
    ) -> CatalogDatasetView:
        dataset = self.reader.get_dataset(dataset_id)
        if dataset.data_source_id not in permitted_source_ids:
            raise NotFoundError("Dataset is outside the permitted source scope.")
        source = self.reader.get_data_source(dataset.data_source_id)
        fields = self.reader.list_data_fields(dataset_id)
        return CatalogDatasetView(
            dataset=dataset,
            data_source=source,
            field_count=len(fields),
        )

    def list_fields_for_dataset(
        self,
        dataset_id: str,
        *,
        permitted_source_ids: frozenset[str],
    ) -> list[DataField]:
        dataset = self.reader.get_dataset(dataset_id)
        if dataset.data_source_id not in permitted_source_ids:
            raise NotFoundError("Dataset is outside the permitted source scope.")
        return self.reader.list_data_fields(dataset_id)

    def get_field_view(
        self,
        data_field_id: str,
        *,
        permitted_source_ids: frozenset[str],
    ) -> CatalogFieldView:
        field = self.reader.get_data_field(data_field_id)
        dataset = self.reader.get_dataset(field.dataset_id)
        if dataset.data_source_id not in permitted_source_ids:
            raise NotFoundError("Field is outside the permitted source scope.")
        source = self.reader.get_data_source(dataset.data_source_id)
        return CatalogFieldView(
            field=field,
            dataset=dataset,
            data_source=source,
        )

    def get_discovery(
        self,
        discovery_id: int,
        *,
        permitted_source_ids: frozenset[str],
    ) -> MetadataDiscoveryResult:
        result = self.reader.get_discovery_result(discovery_id)
        if result.data_source_id not in permitted_source_ids:
            raise NotFoundError("Discovery is outside the permitted source scope.")
        return result

    def get_discovery_diff(
        self,
        discovery_id: int,
        *,
        permitted_source_ids: frozenset[str],
    ) -> MetadataDiff | None:
        result = self.reader.get_discovery_result(discovery_id)
        if result.data_source_id not in permitted_source_ids:
            raise NotFoundError("Discovery is outside the permitted source scope.")
        return self.reader.get_diff_by_discovery(discovery_id)

    def get_diff(
        self,
        metadata_diff_id: str,
        *,
        permitted_source_ids: frozenset[str],
    ) -> MetadataDiff:
        diff = self.reader.get_metadata_diff(metadata_diff_id)
        if diff.data_source_id not in permitted_source_ids:
            raise NotFoundError("Diff is outside the permitted source scope.")
        return diff

    def list_pending_diffs_for_source(
        self,
        data_source_id: str,
        *,
        permitted_source_ids: frozenset[str],
    ) -> list[MetadataDiff]:
        if data_source_id not in permitted_source_ids:
            return []
        return self.reader.list_pending_diffs(data_source_id)

    def get_discovery_scope(
        self,
        data_source_id: str,
        *,
        permitted_source_ids: frozenset[str],
    ) -> DiscoveryScope | None:
        if data_source_id not in permitted_source_ids:
            raise NotFoundError("Data source is outside the permitted scope.")
        return self.reader.get_discovery_scope(data_source_id)
