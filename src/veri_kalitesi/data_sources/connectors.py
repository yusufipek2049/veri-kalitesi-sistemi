"""Salt-okunur veri kaynağı bağlayıcıları."""

from __future__ import annotations

import csv
from collections.abc import Mapping
from datetime import date, datetime, time, timezone
from hashlib import sha256
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
    MetadataDiscoveryOutcome,
    MetadataFieldCandidate,
    ProfileComputationResult,
    ProfileOptions,
    ProfileStatus,
    SourceType,
)
from veri_kalitesi.data_sources.profiling import (
    BoundedDeterministicSample,
    build_advanced_field_metrics,
    validate_freshness_field_scope,
)
from veri_kalitesi.data_sources.errors import ValidationError


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
    ) -> MetadataDiscoveryOutcome:
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
    ) -> MetadataDiscoveryOutcome:
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
        candidates = (
            MetadataDatasetCandidate(
                namespace=str(path.parent),
                name=path.name,
                dataset_type=DatasetType.FILE_SHEET,
                fields=fields,
            ),
        )
        return MetadataDiscoveryOutcome(
            candidates=candidates,
            completed_scope={"namespace": str(path.parent), "name": path.name},
            scanned_object_count=1 + len(fields),
            is_complete=True,
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
        validate_freshness_field_scope(
            options.analysis_policy,
            fields,
            selected_field_names=tuple(field.name for field in selected_fields),
        )
        stats = {field.name: _new_field_stats() for field in selected_fields}
        distinct_fingerprints: dict[str, set[bytes]] = {
            field.name: set() for field in selected_fields
        }
        samples = {
            field.name: BoundedDeterministicSample(
                field_name=field.name,
                policy=options.analysis_policy,
            )
            for field in selected_fields
            if options.analysis_policy is not None
        }
        numeric_stats = {field.name: _new_numeric_stats() for field in selected_fields}
        duplicate_groups: dict[bytes, int] = {}
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
                    duplicate_key = _fingerprint_values(
                        tuple(row.get(field_name, "") for field_name in options.key_field_names)
                    )
                    duplicate_groups[duplicate_key] = duplicate_groups.get(duplicate_key, 0) + 1
                for field in selected_fields:
                    value = row.get(field.name)
                    if value is None or value == "":
                        stats[field.name]["null_count"] += 1
                        continue
                    distinct_fingerprints[field.name].add(sha256(value.encode()).digest())
                    if field.name in samples:
                        samples[field.name].add(value, row_index=row_index)
                    numeric = _to_float(value)
                    if numeric is not None:
                        _update_numeric_stats(numeric_stats[field.name], numeric)

        if sampled_count == 0:
            return ProfileComputationResult(
                status=ProfileStatus.NO_DATA,
                metrics=_build_metrics(
                    options,
                    row_count,
                    sampled_count,
                    selected_fields,
                    stats,
                    distinct_fingerprints,
                    samples,
                    numeric_stats,
                    duplicate_groups,
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
            distinct_fingerprints,
            samples,
            numeric_stats,
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


def _new_numeric_stats() -> dict[str, float | int | None]:
    return {"count": 0, "min": None, "max": None, "sum": 0.0}


def _update_numeric_stats(stats: dict[str, float | int | None], value: float) -> None:
    stats["count"] = int(stats["count"] or 0) + 1
    stats["sum"] = float(stats["sum"] or 0.0) + value
    stats["min"] = value if stats["min"] is None else min(float(stats["min"]), value)
    stats["max"] = value if stats["max"] is None else max(float(stats["max"]), value)


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


def _fingerprint_values(values: tuple[str, ...]) -> bytes:
    digest = sha256()
    for value in values:
        encoded = value.encode()
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
    return digest.digest()


def _to_aware_datetime(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def _to_freshness_datetime(value: str) -> datetime | None:
    parsed = _to_aware_datetime(value)
    if parsed is not None:
        return parsed
    try:
        parsed_date = date.fromisoformat(value.strip())
    except ValueError:
        return None
    return datetime.combine(parsed_date, time.min, tzinfo=timezone.utc)


def _build_metrics(
    options: ProfileOptions,
    row_count: int,
    sampled_count: int,
    fields: list[DataField],
    stats: dict[str, dict[str, int]],
    distinct_fingerprints: dict[str, set[bytes]],
    samples: dict[str, BoundedDeterministicSample],
    numeric_stats: dict[str, dict[str, float | int | None]],
    duplicate_groups: dict[bytes, int],
) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "record_count": row_count,
        "sampled_count": sampled_count,
        "method": options.method.value,
        "sample_ratio": options.sample_ratio,
        "fields": {},
        "advanced_analysis": {
            "status": "RESOLVED" if options.analysis_policy is not None else "CONFIGURATION_ERROR",
            "reason": (
                None if options.analysis_policy is not None else "ACTIVE_PROFILE_POLICY_MISSING"
            ),
        },
    }
    if options.key_field_names:
        duplicate_group_count = sum(1 for count in duplicate_groups.values() if count > 1)
        duplicate_record_count = sum(count - 1 for count in duplicate_groups.values() if count > 1)
        metrics["duplicates"] = {
            "key_fields": list(options.key_field_names),
            "duplicate_group_count": duplicate_group_count,
            "duplicate_record_count": duplicate_record_count,
            "duplicate_ratio": duplicate_record_count / sampled_count if sampled_count else None,
            "measurement": "EXACT",
        }
    for field in fields:
        null_count = stats[field.name]["null_count"]
        sample = samples.get(field.name)
        sampled_values = sample.values() if sample is not None else []
        distinct_count = len(distinct_fingerprints[field.name])
        field_metrics: dict[str, Any] = {
            "null_count": null_count,
            "null_ratio": null_count / sampled_count if sampled_count else None,
            "distinct_count": distinct_count,
            "distinct_ratio": distinct_count / sampled_count if sampled_count else None,
            "distinct_measurement": "EXACT",
        }
        if field.is_sensitive:
            field_metrics["masked"] = True
        numeric = numeric_stats[field.name]
        if numeric["count"]:
            field_metrics["min"] = numeric["min"]
            field_metrics["max"] = numeric["max"]
            field_metrics["average"] = float(numeric["sum"] or 0.0) / int(numeric["count"])
        if options.analysis_policy is not None:
            numeric_sample = [
                parsed for value in sampled_values if (parsed := _to_float(value)) is not None
            ]
            field_metrics.update(
                build_advanced_field_metrics(
                    sampled_values,
                    numeric_sample,
                    options.analysis_policy,
                )
            )
            field_metrics["sampling"] = sample.evidence() if sample is not None else {}
            if field.name in options.analysis_policy.freshness_field_names:
                observed_times = [
                    parsed_time
                    for value in sampled_values
                    if (parsed_time := _to_freshness_datetime(value)) is not None
                ]
                if sampled_values and len(observed_times) != len(sampled_values):
                    raise ValidationError(
                        "Profile policy freshness field contains incompatible date/time values."
                    )
                if observed_times:
                    field_metrics["freshness_max"] = max(observed_times).isoformat()
        metrics["fields"][field.name] = field_metrics
    if options.analysis_policy is not None:
        metrics["analysis_execution"] = {
            "method": "APPLICATION_BOUNDED_SAMPLE",
            "strategy": options.analysis_policy.sampling_strategy.value,
            "sample_size_limit": options.analysis_policy.advanced_sample_size,
            "sampling_seed": options.analysis_policy.sampling_seed,
        }
    return metrics
