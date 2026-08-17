"""Salt-okunur dataset satır önizleme servisi.

Katalogdaki alan listesini kullanarak PostgreSQL tablosundan sınırlı sayıda
satırı metin olarak döndürür. Hassas (sensitive) alan değerleri asla ham
şekilde yüzeye çıkmaz; maske sabiti ile değiştirilir.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from veri_kalitesi.data_sources.errors import ValidationError
from veri_kalitesi.data_sources.models import (
    DataField,
    DataSource,
    DataSourceStatus,
    Dataset,
    SourceType,
)

MASKED_VALUE = "•••"
DEFAULT_PREVIEW_LIMIT = 50
MAX_PREVIEW_LIMIT = 200


class PreviewNotSupportedError(Exception):
    """Veri kaynağı tipi satır önizlemeyi desteklemiyor."""

    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


class _PreviewReader(Protocol):
    def get_dataset(self, dataset_id: str) -> Dataset: ...

    def get_data_source(self, data_source_id: str) -> DataSource: ...

    def list_data_fields(self, dataset_id: str) -> list[DataField]: ...


class _PreviewConnector(Protocol):
    def preview_table(
        self,
        data_source: DataSource,
        secret: Mapping[str, Any],
        *,
        schema: str,
        table: str,
        columns: tuple[str, ...],
        limit: int,
        connect_timeout_seconds: int = 5,
        statement_timeout_ms: int = 10_000,
    ) -> tuple[tuple[str | None, ...], ...]: ...


class _SecretResolver(Protocol):
    def resolve(self, secret_reference: str) -> Mapping[str, Any]: ...


@dataclass(frozen=True)
class PreviewColumn:
    name: str
    native_data_type: str
    is_sensitive: bool


@dataclass(frozen=True)
class DatasetPreview:
    dataset_id: str
    data_source_id: str
    source_type: str
    namespace: str
    table_name: str
    columns: tuple[PreviewColumn, ...]
    rows: tuple[tuple[str | None, ...], ...]
    limit: int


class DatasetPreviewService:
    """Katalog dataset'i için kaynak tablodan sınırlı satır önizlemesi üretir."""

    def __init__(
        self,
        reader: _PreviewReader,
        connector: _PreviewConnector,
        secret_resolver: _SecretResolver,
    ) -> None:
        self.reader = reader
        self.connector = connector
        self.secret_resolver = secret_resolver

    def preview(self, dataset_id: str, *, limit: int = DEFAULT_PREVIEW_LIMIT) -> DatasetPreview:
        if not 1 <= limit <= MAX_PREVIEW_LIMIT:
            raise ValidationError(f"Preview limit must be between 1 and {MAX_PREVIEW_LIMIT}.")
        dataset = self.reader.get_dataset(dataset_id)
        data_source = self.reader.get_data_source(dataset.data_source_id)
        if data_source.source_type is not SourceType.POSTGRESQL:
            raise PreviewNotSupportedError("PREVIEW_UNSUPPORTED_SOURCE_TYPE")
        if data_source.status is not DataSourceStatus.ACTIVE:
            raise PreviewNotSupportedError("DATA_SOURCE_NOT_ACTIVE")
        fields = tuple(field for field in self.reader.list_data_fields(dataset_id) if field.name)
        if not fields:
            raise PreviewNotSupportedError("DATASET_FIELDS_MISSING")

        secret = self.secret_resolver.resolve(data_source.secret_reference)
        rows = self.connector.preview_table(
            data_source,
            secret,
            schema=dataset.namespace,
            table=dataset.name,
            columns=tuple(field.name for field in fields),
            limit=limit,
        )
        sensitive_indexes = {index for index, field in enumerate(fields) if field.is_sensitive}
        masked_rows = tuple(
            tuple(
                MASKED_VALUE if index in sensitive_indexes and value is not None else value
                for index, value in enumerate(row)
            )
            for row in rows
        )
        return DatasetPreview(
            dataset_id=dataset.dataset_id,
            data_source_id=data_source.data_source_id,
            source_type=data_source.source_type.value,
            namespace=dataset.namespace,
            table_name=dataset.name,
            columns=tuple(
                PreviewColumn(
                    name=field.name,
                    native_data_type=field.native_data_type,
                    is_sensitive=field.is_sensitive,
                )
                for field in fields
            ),
            rows=masked_rows,
            limit=limit,
        )
