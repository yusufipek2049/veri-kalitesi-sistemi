"""Salt-okunur veri kaynağı bağlayıcıları."""

from __future__ import annotations

import csv
from collections.abc import Mapping
from pathlib import Path
from time import perf_counter
from typing import Any, Protocol

from veri_kalitesi.data_sources.models import (
    ConnectionTestResult,
    DataField,
    DataSource,
    Dataset,
    DatasetType,
    ErrorClass,
    MetadataDatasetCandidate,
    MetadataDiscoveryOptions,
    MetadataFieldCandidate,
    ProfileComputationResult,
    ProfileOptions,
    ProfileStatus,
    SourceType,
)


class DataSourceConnector(Protocol):
    source_type: SourceType

    def test_connection(
        self,
        data_source: DataSource,
        secret: Mapping[str, Any],
    ) -> ConnectionTestResult:
        """Salt-okunur bağlantı testi çalıştır."""

    def discover_metadata(
        self,
        data_source: DataSource,
        secret: Mapping[str, Any],
        options: MetadataDiscoveryOptions,
    ) -> tuple[MetadataDatasetCandidate, ...]:
        """Kaynak metadata bilgisini salt-okunur olarak keşfet."""

    def profile_dataset(
        self,
        data_source: DataSource,
        secret: Mapping[str, Any],
        dataset: Dataset,
        fields: tuple[DataField, ...],
        options: ProfileOptions,
    ) -> ProfileComputationResult:
        """Dataset için temel profil metriklerini salt-okunur olarak hesapla."""


class CSVConnector:
    source_type = SourceType.CSV

    def test_connection(
        self,
        data_source: DataSource,
        secret: Mapping[str, Any],
    ) -> ConnectionTestResult:
        started = perf_counter()
        config = data_source.connection_config
        path = Path(str(config["file_path"]))
        delimiter = str(config.get("delimiter", ","))
        encoding = str(config.get("encoding", "utf-8"))

        try:
            if not path.exists():
                return _failure(
                    data_source,
                    started,
                    ErrorClass.FILE_NOT_FOUND,
                    "CSV file could not be found.",
                )
            if not path.is_file():
                return _failure(
                    data_source,
                    started,
                    ErrorClass.VALIDATION,
                    "CSV location must point to a file.",
                )

            with path.open("r", newline="", encoding=encoding) as handle:
                reader = csv.reader(handle, delimiter=delimiter)
                header = next(reader, [])
                sample_row = next(reader, None)

            return ConnectionTestResult(
                data_source_id=data_source.data_source_id,
                succeeded=True,
                duration_ms=_elapsed_ms(started),
                message="CSV source is readable.",
                source_info={
                    "source_type": SourceType.CSV.value,
                    "column_count": len(header),
                    "has_sample_row": sample_row is not None,
                    "size_bytes": path.stat().st_size,
                },
            )
        except PermissionError:
            return _failure(
                data_source,
                started,
                ErrorClass.PERMISSION,
                "CSV file cannot be read with current permissions.",
            )
        except UnicodeDecodeError:
            return _failure(
                data_source,
                started,
                ErrorClass.DRIVER,
                "CSV file cannot be decoded with the configured encoding.",
            )
        except csv.Error:
            return _failure(
                data_source,
                started,
                ErrorClass.DRIVER,
                "CSV file cannot be parsed with the configured dialect.",
            )

    def discover_metadata(
        self,
        data_source: DataSource,
        secret: Mapping[str, Any],
        options: MetadataDiscoveryOptions,
    ) -> tuple[MetadataDatasetCandidate, ...]:
        config = data_source.connection_config
        path = Path(str(config["file_path"]))
        delimiter = str(config.get("delimiter", ","))
        encoding = str(config.get("encoding", "utf-8"))

        with path.open("r", newline="", encoding=encoding) as handle:
            reader = csv.reader(handle, delimiter=delimiter)
            header = next(reader, [])

        if len(header) > options.max_objects:
            header = header[: options.max_objects]

        fields = tuple(
            MetadataFieldCandidate(
                name=column.strip() or f"column_{index + 1}",
                native_data_type="TEXT",
                is_nullable=True,
            )
            for index, column in enumerate(header)
        )
        return (
            MetadataDatasetCandidate(
                namespace=str(path.parent),
                name=path.name,
                dataset_type=DatasetType.FILE_SHEET,
                fields=fields,
            ),
        )

    def profile_dataset(
        self,
        data_source: DataSource,
        secret: Mapping[str, Any],
        dataset: Dataset,
        fields: tuple[DataField, ...],
        options: ProfileOptions,
    ) -> ProfileComputationResult:
        config = data_source.connection_config
        path = Path(str(config["file_path"]))
        delimiter = str(config.get("delimiter", ","))
        encoding = str(config.get("encoding", "utf-8"))
        selected_names = (
            set(options.field_names) if options.field_names else {field.name for field in fields}
        )
        selected_fields = [field for field in fields if field.name in selected_names]
        stats = {field.name: _new_field_stats() for field in selected_fields}
        unique_values: dict[str, set[str]] = {field.name: set() for field in selected_fields}
        numeric_values: dict[str, list[float]] = {field.name: [] for field in selected_fields}
        duplicate_groups: dict[tuple[str, ...], int] = {}
        row_count = 0
        sampled_count = 0

        with path.open("r", newline="", encoding=encoding) as handle:
            reader = csv.DictReader(handle, delimiter=delimiter)
            for row_index, row in enumerate(reader, start=1):
                row_count += 1
                if not _include_row(row_index, options.sample_ratio):
                    continue
                sampled_count += 1
                if options.key_field_names:
                    duplicate_key = tuple(
                        row.get(field_name, "") for field_name in options.key_field_names
                    )
                    duplicate_groups[duplicate_key] = duplicate_groups.get(duplicate_key, 0) + 1
                for field in selected_fields:
                    value = row.get(field.name)
                    if value is None or value == "":
                        stats[field.name]["null_count"] += 1
                        continue
                    unique_values[field.name].add(value)
                    numeric = _to_float(value)
                    if numeric is not None:
                        numeric_values[field.name].append(numeric)

        if sampled_count == 0:
            return ProfileComputationResult(
                status=ProfileStatus.NO_DATA,
                metrics=_build_metrics(
                    options,
                    row_count,
                    sampled_count,
                    selected_fields,
                    stats,
                    {},
                    {},
                    {},
                ),
                row_count=row_count,
                message="Dataset has no rows in selected profile scope.",
            )

        metrics = _build_metrics(
            options,
            row_count,
            sampled_count,
            selected_fields,
            stats,
            unique_values,
            numeric_values,
            duplicate_groups,
        )
        return ProfileComputationResult(
            status=ProfileStatus.COMPLETED,
            metrics=metrics,
            row_count=row_count,
            message="CSV profile completed.",
        )


class ConnectorRegistry:
    def __init__(self, connectors: list[DataSourceConnector]) -> None:
        self._connectors = {connector.source_type: connector for connector in connectors}

    def get(self, source_type: SourceType) -> DataSourceConnector | None:
        return self._connectors.get(source_type)


def _failure(
    data_source: DataSource,
    started: float,
    error_class: ErrorClass,
    message: str,
) -> ConnectionTestResult:
    return ConnectionTestResult(
        data_source_id=data_source.data_source_id,
        succeeded=False,
        duration_ms=_elapsed_ms(started),
        error_class=error_class,
        message=message,
        source_info={"source_type": data_source.source_type.value},
    )


def _elapsed_ms(started: float) -> int:
    return max(0, round((perf_counter() - started) * 1000))


def _new_field_stats() -> dict[str, int]:
    return {"null_count": 0}


def _include_row(row_index: int, sample_ratio: float | None) -> bool:
    if sample_ratio is None:
        return True
    if sample_ratio >= 1:
        return True
    interval = max(1, round(1 / sample_ratio))
    return (row_index - 1) % interval == 0


def _to_float(value: str) -> float | None:
    try:
        return float(value)
    except ValueError:
        return None


def _build_metrics(
    options: ProfileOptions,
    row_count: int,
    sampled_count: int,
    fields: list[DataField],
    stats: dict[str, dict[str, int]],
    unique_values: dict[str, set[str]],
    numeric_values: dict[str, list[float]],
    duplicate_groups: dict[tuple[str, ...], int],
) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "record_count": row_count,
        "sampled_count": sampled_count,
        "method": options.method.value,
        "sample_ratio": options.sample_ratio,
        "fields": {},
    }
    if options.key_field_names:
        duplicate_group_count = sum(1 for count in duplicate_groups.values() if count > 1)
        duplicate_record_count = sum(count - 1 for count in duplicate_groups.values() if count > 1)
        metrics["duplicates"] = {
            "key_fields": list(options.key_field_names),
            "duplicate_group_count": duplicate_group_count,
            "duplicate_record_count": duplicate_record_count,
            "duplicate_ratio": duplicate_record_count / sampled_count if sampled_count else None,
        }
    for field in fields:
        null_count = stats[field.name]["null_count"]
        distinct_count = len(unique_values.get(field.name, set()))
        field_metrics: dict[str, Any] = {
            "null_count": null_count,
            "null_ratio": null_count / sampled_count if sampled_count else None,
            "distinct_count": distinct_count,
            "distinct_ratio": distinct_count / sampled_count if sampled_count else None,
        }
        if field.is_sensitive:
            field_metrics["masked"] = True
        else:
            numeric = numeric_values.get(field.name, [])
            if numeric:
                field_metrics["min"] = min(numeric)
                field_metrics["max"] = max(numeric)
                field_metrics["average"] = sum(numeric) / len(numeric)
        metrics["fields"][field.name] = field_metrics
    return metrics
