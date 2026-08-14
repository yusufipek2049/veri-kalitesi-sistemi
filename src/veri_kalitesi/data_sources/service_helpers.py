"""Veri kaynağı servisi için saf hesaplama ve sonuç üretme yardımcıları."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from time import perf_counter
from typing import Any
from uuid import uuid4

from veri_kalitesi.data_sources.models import (
    DataField,
    DataProfile,
    Dataset,
    ErrorClass,
    MetadataChange,
    MetadataChangeType,
    ProfileOptions,
    ProfileStatus,
    utc_now,
)
from veri_kalitesi.data_sources.postgresql import (
    AuthenticationConnectionError,
    DNSConnectionError,
    NetworkConnectionError,
    PermissionConnectionError,
    TLSConnectionError,
    TimeoutConnectionError,
)


def elapsed_ms(started: float) -> int:
    return max(0, round((perf_counter() - started) * 1000))


def error_class_for_exception(exc: Exception) -> ErrorClass:
    if isinstance(exc, DNSConnectionError):
        return ErrorClass.DNS
    if isinstance(exc, NetworkConnectionError):
        return ErrorClass.NETWORK
    if isinstance(exc, TimeoutConnectionError):
        return ErrorClass.TIMEOUT
    if isinstance(exc, AuthenticationConnectionError):
        return ErrorClass.AUTHENTICATION
    if isinstance(exc, TLSConnectionError):
        return ErrorClass.TLS
    if isinstance(exc, PermissionConnectionError):
        return ErrorClass.PERMISSION
    return ErrorClass.DRIVER


def diff_metadata(
    previous: dict[tuple[str, str], list[DataField]],
    datasets: list[Dataset],
    fields_by_dataset_id: dict[str, list[DataField]],
) -> list[MetadataChange]:
    changes: list[MetadataChange] = []
    current_keys = {(dataset.namespace, dataset.name): dataset for dataset in datasets}

    for dataset_key, dataset in current_keys.items():
        if dataset_key not in previous:
            changes.append(
                MetadataChange(
                    change_type=MetadataChangeType.ADDED,
                    object_type="DATASET",
                    namespace=dataset.namespace,
                    dataset_name=dataset.name,
                    new_values={"dataset_type": dataset.dataset_type.value},
                )
            )

        previous_fields = {field.name: field for field in previous.get(dataset_key, [])}
        current_fields = {
            field.name: field for field in fields_by_dataset_id.get(dataset.dataset_id, [])
        }
        for field_name, field in current_fields.items():
            previous_field = previous_fields.get(field_name)
            if previous_field is None:
                changes.append(
                    MetadataChange(
                        change_type=MetadataChangeType.ADDED,
                        object_type="DATA_FIELD",
                        namespace=dataset.namespace,
                        dataset_name=dataset.name,
                        field_name=field.name,
                        new_values=field_signature(field),
                    )
                )
            elif field_signature(previous_field) != field_signature(field):
                changes.append(
                    MetadataChange(
                        change_type=MetadataChangeType.CHANGED,
                        object_type="DATA_FIELD",
                        namespace=dataset.namespace,
                        dataset_name=dataset.name,
                        field_name=field.name,
                        old_values=field_signature(previous_field),
                        new_values=field_signature(field),
                        requires_rule_review=True,
                    )
                )
        for field_name, previous_field in previous_fields.items():
            if field_name not in current_fields:
                changes.append(
                    MetadataChange(
                        change_type=MetadataChangeType.REMOVED,
                        object_type="DATA_FIELD",
                        namespace=dataset.namespace,
                        dataset_name=dataset.name,
                        field_name=previous_field.name,
                        old_values=field_signature(previous_field),
                        requires_rule_review=True,
                    )
                )

    for namespace, dataset_name in previous:
        if (namespace, dataset_name) not in current_keys:
            changes.append(
                MetadataChange(
                    change_type=MetadataChangeType.REMOVED,
                    object_type="DATASET",
                    namespace=namespace,
                    dataset_name=dataset_name,
                    requires_rule_review=True,
                )
            )
    return changes


def field_signature(field: DataField) -> dict[str, Any]:
    return {
        "native_data_type": field.native_data_type,
        "is_nullable": field.is_nullable,
        "is_sensitive": field.is_sensitive,
        "classification": field.classification.value,
        "classification_policy_version": field.classification_policy_version,
    }


def profile_from_failure(
    dataset_id: str,
    options: ProfileOptions,
    error_class: ErrorClass,
    message: str,
    started_at: Any | None = None,
    duration_ms: int = 0,
) -> DataProfile:
    started_at = started_at or utc_now()
    return DataProfile(
        dataset_id=dataset_id,
        execution_id=str(uuid4()),
        method=options.method,
        sample_ratio=options.sample_ratio,
        metrics={},
        status=ProfileStatus.TECHNICAL_ERROR,
        duration_ms=duration_ms,
        error_class=error_class,
        message=message,
        started_at=started_at,
        finished_at=utc_now(),
    )


def latest_profile_observation(metrics: Mapping[str, Any]) -> datetime | None:
    latest: datetime | None = None
    fields = metrics.get("fields")
    if not isinstance(fields, Mapping):
        return None
    for field_metrics in fields.values():
        if not isinstance(field_metrics, Mapping):
            continue
        value = field_metrics.get("freshness_max")
        if not isinstance(value, str):
            continue
        try:
            observed_at = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            continue
        if observed_at.tzinfo is None or observed_at.utcoffset() is None:
            continue
        observed_at = observed_at.astimezone(timezone.utc)
        if latest is None or observed_at > latest:
            latest = observed_at
    return latest
