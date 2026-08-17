"""Dataset satır önizleme servisi birim testleri.

Kapsam: mutlu yol + hassas alan maskeleme, desteklenmeyen kaynak tipi,
pasif kaynak, eksik alan listesi ve limit doğrulaması.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import pytest

from veri_kalitesi.data_sources.errors import ValidationError
from veri_kalitesi.data_sources.models import (
    DataField,
    DataSource,
    DataSourceStatus,
    Dataset,
    SourceType,
)
from veri_kalitesi.data_sources.preview import (
    MASKED_VALUE,
    DatasetPreviewService,
    PreviewNotSupportedError,
)


@dataclass
class _StubReader:
    dataset: Dataset
    data_source: DataSource
    fields: list[DataField]

    def get_dataset(self, dataset_id: str) -> Dataset:
        assert dataset_id == self.dataset.dataset_id
        return self.dataset

    def get_data_source(self, data_source_id: str) -> DataSource:
        assert data_source_id == self.dataset.data_source_id
        return self.data_source

    def list_data_fields(self, dataset_id: str) -> list[DataField]:
        assert dataset_id == self.dataset.dataset_id
        return list(self.fields)


@dataclass
class _StubConnector:
    rows: tuple[tuple[str | None, ...], ...] = ()
    captured: dict[str, Any] | None = None

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
    ) -> tuple[tuple[str | None, ...], ...]:
        self.captured = {
            "data_source_id": data_source.data_source_id,
            "secret": dict(secret),
            "schema": schema,
            "table": table,
            "columns": columns,
            "limit": limit,
        }
        return self.rows


class _StubSecretResolver:
    def resolve(self, secret_reference: str) -> Mapping[str, Any]:
        return {"password": f"secret-for-{secret_reference}"}


def _source(
    *,
    source_type: SourceType = SourceType.POSTGRESQL,
    status: DataSourceStatus = DataSourceStatus.ACTIVE,
) -> DataSource:
    return DataSource(
        name="PostgreSQL Ana Kaynak",
        source_type=source_type,
        connection_config={"host": "db.example", "port": 5432, "database": "core"},
        secret_reference="vault://core-pg",
        data_source_id="source-1",
        status=status,
    )


def _dataset() -> Dataset:
    return Dataset(
        data_source_id="source-1",
        namespace="public",
        name="musteriler",
        dataset_id="dataset-1",
    )


def _fields() -> list[DataField]:
    return [
        DataField(dataset_id="dataset-1", name="id", native_data_type="integer"),
        DataField(
            dataset_id="dataset-1", name="ad_soyad", native_data_type="text", is_sensitive=True
        ),
        DataField(dataset_id="dataset-1", name="bakiye", native_data_type="numeric"),
    ]


def _service(
    *,
    source: DataSource | None = None,
    fields: list[DataField] | None = None,
    rows: tuple[tuple[str | None, ...], ...] = (),
) -> tuple[DatasetPreviewService, _StubConnector]:
    connector = _StubConnector(rows=rows)
    service = DatasetPreviewService(
        reader=_StubReader(
            dataset=_dataset(),
            data_source=source or _source(),
            fields=fields if fields is not None else _fields(),
        ),
        connector=connector,
        secret_resolver=_StubSecretResolver(),
    )
    return service, connector


def test_preview_returns_rows_with_masked_sensitive_columns() -> None:
    service, connector = _service(
        rows=(
            ("1", "Ayşe Yılmaz", "1250.50"),
            ("2", None, "0.00"),
        )
    )

    preview = service.preview("dataset-1", limit=10)

    assert preview.dataset_id == "dataset-1"
    assert preview.data_source_id == "source-1"
    assert preview.source_type == "POSTGRESQL"
    assert preview.namespace == "public"
    assert preview.table_name == "musteriler"
    assert preview.limit == 10
    assert [(column.name, column.is_sensitive) for column in preview.columns] == [
        ("id", False),
        ("ad_soyad", True),
        ("bakiye", False),
    ]
    # Hassas kolon maskele, NULL değerleri koruyarak.
    assert preview.rows == (
        ("1", MASKED_VALUE, "1250.50"),
        ("2", None, "0.00"),
    )
    assert connector.captured == {
        "data_source_id": "source-1",
        "secret": {"password": "secret-for-vault://core-pg"},
        "schema": "public",
        "table": "musteriler",
        "columns": ("id", "ad_soyad", "bakiye"),
        "limit": 10,
    }


def test_preview_rejects_non_postgresql_source() -> None:
    service, connector = _service(source=_source(source_type=SourceType.CSV))

    with pytest.raises(PreviewNotSupportedError) as exc_info:
        service.preview("dataset-1")

    assert exc_info.value.reason_code == "PREVIEW_UNSUPPORTED_SOURCE_TYPE"
    assert connector.captured is None


def test_preview_rejects_inactive_source() -> None:
    service, connector = _service(source=_source(status=DataSourceStatus.TEST_PENDING))

    with pytest.raises(PreviewNotSupportedError) as exc_info:
        service.preview("dataset-1")

    assert exc_info.value.reason_code == "DATA_SOURCE_NOT_ACTIVE"
    assert connector.captured is None


def test_preview_rejects_missing_fields() -> None:
    service, connector = _service(fields=[])

    with pytest.raises(PreviewNotSupportedError) as exc_info:
        service.preview("dataset-1")

    assert exc_info.value.reason_code == "DATASET_FIELDS_MISSING"
    assert connector.captured is None


@pytest.mark.parametrize("limit", [0, -3, 201])
def test_preview_validates_limit(limit: int) -> None:
    service, connector = _service()

    with pytest.raises(ValidationError):
        service.preview("dataset-1", limit=limit)

    assert connector.captured is None
