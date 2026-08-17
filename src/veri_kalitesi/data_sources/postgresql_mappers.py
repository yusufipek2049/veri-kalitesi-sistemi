"""PostgreSQL veri kaynağı satırlarını alan modellerine eşler."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import IntegrityError

from veri_kalitesi.data_protection import ClassificationCode, DataProcessingInventory
from veri_kalitesi.data_sources.models import (
    CatalogItemStatus,
    ConnectionRevisionStatus,
    ConnectionTestResult,
    Criticality,
    DataField,
    DataProfile,
    DataSource,
    DataSourceActivationRequest,
    DataSourceActivationStatus,
    DataSourceConnectionRevision,
    DataSourceStatus,
    Dataset,
    DatasetType,
    DiscoveryScope,
    DiscoveryStatus,
    ErrorClass,
    MetadataDiff,
    MetadataDiffStatus,
    MetadataDiscoveryResult,
    ProfileComparison,
    ProfileComparisonStatus,
    ProfileMethod,
    ProfileStatus,
    SourceType,
    TimelinessNature,
)


def constraint_name(error: IntegrityError) -> str | None:
    diagnostic = getattr(error.orig, "diag", None)
    value = getattr(diagnostic, "constraint_name", None)
    return str(value) if value is not None else None


def row_to_data_source(row: RowMapping) -> DataSource:
    return DataSource(
        data_source_id=row["data_source_id"],
        name=row["name"],
        source_type=SourceType(row["source_type"]),
        connection_config=json_load(row["connection_config"]),
        secret_reference=row["secret_reference"],
        owner_user_id=row["owner_user_id"],
        status=DataSourceStatus(row["status"]),
        revision=row["revision"],
        last_test_at=row["last_test_at"],
        created_at=row["created_at"],
    )


def row_to_connection_test(row: RowMapping) -> ConnectionTestResult:
    return ConnectionTestResult(
        data_source_id=row["data_source_id"],
        succeeded=bool(row["succeeded"]),
        duration_ms=row["duration_ms"],
        error_class=ErrorClass(row["error_class"]) if row["error_class"] else None,
        message=row["message"],
        source_info=json_load(row["source_info"]),
        data_source_revision=row["data_source_revision"],
        tested_at=row["tested_at"],
    )


def row_to_connection_revision(row: RowMapping) -> DataSourceConnectionRevision:
    return DataSourceConnectionRevision(
        connection_revision_id=row["connection_revision_id"],
        data_source_id=row["data_source_id"],
        revision=row["revision"],
        base_revision=row["base_revision"],
        connection_config=json_load(row["connection_config"]),
        secret_reference=row["secret_reference"],
        prepared_by_actor_id=row["prepared_by_actor_id"],
        policy_version=row["policy_version"],
        reason_code=row["reason_code"],
        status=ConnectionRevisionStatus(row["status"]),
        created_at=row["created_at"],
        tested_at=row["tested_at"],
    )


def row_to_activation_request(row: RowMapping) -> DataSourceActivationRequest:
    return DataSourceActivationRequest(
        activation_request_id=row["activation_request_id"],
        data_source_id=row["data_source_id"],
        data_source_revision=row["data_source_revision"],
        maker_actor_id=row["maker_actor_id"],
        checker_actor_id=row["checker_actor_id"],
        policy_version=row["policy_version"],
        status=DataSourceActivationStatus(row["status"]),
        decision_reason_code=row["decision_reason_code"],
        requested_at=row["requested_at"],
        target_at=row["target_at"],
        expires_at=row["expires_at"],
        business_calendar_version=row["business_calendar_version"],
        decided_at=row["decided_at"],
        request_type=row.get("request_type") or "ACTIVATION",
    )


def row_to_dataset(row: RowMapping) -> Dataset:
    return Dataset(
        dataset_id=row["dataset_id"],
        data_source_id=row["data_source_id"],
        namespace=row["namespace"],
        name=row["name"],
        dataset_type=DatasetType(row["dataset_type"]),
        criticality=Criticality(row["criticality"]),
        owner_user_id=row["owner_user_id"],
        estimated_row_count=row["estimated_row_count"],
        timeliness_nature=(
            TimelinessNature(row["timeliness_nature"]) if row.get("timeliness_nature") else None
        ),
        status=CatalogItemStatus(row.get("status", "ACTIVE") or "ACTIVE"),
        first_seen_discovery_id=row.get("first_seen_discovery_id"),
        last_seen_discovery_id=row.get("last_seen_discovery_id"),
        updated_at=row.get("updated_at") or row.get("discovered_at") or datetime.now(timezone.utc),
        version=row.get("version") or 1,
    )


def row_to_data_field(row: RowMapping) -> DataField:
    return DataField(
        data_field_id=row["data_field_id"],
        dataset_id=row["dataset_id"],
        name=row["name"],
        native_data_type=row["native_data_type"],
        is_nullable=bool(row["is_nullable"]),
        is_sensitive=bool(row["is_sensitive"]),
        classification=ClassificationCode(row["classification"]),
        classification_policy_version=row["classification_policy_version"],
        status=CatalogItemStatus(row.get("status", "ACTIVE") or "ACTIVE"),
        first_seen_discovery_id=row.get("first_seen_discovery_id"),
        last_seen_discovery_id=row.get("last_seen_discovery_id"),
        updated_at=row.get("updated_at") or datetime.now(timezone.utc),
        version=row.get("version") or 1,
    )


def row_to_data_profile(row: RowMapping) -> DataProfile:
    return DataProfile(
        profile_id=row["profile_id"],
        dataset_id=row["dataset_id"],
        execution_id=row["execution_id"],
        method=ProfileMethod(row["method"]),
        sample_ratio=row["sample_ratio"],
        metrics=json_load(row["metrics"]),
        status=ProfileStatus(row["status"]),
        duration_ms=row["duration_ms"],
        error_class=ErrorClass(row["error_class"]) if row["error_class"] else None,
        message=row["message"],
        started_at=row["started_at"],
        finished_at=row["finished_at"],
    )


def row_to_profile_comparison(row: RowMapping) -> ProfileComparison:
    return ProfileComparison(
        comparison_id=row["comparison_id"],
        dataset_id=row["dataset_id"],
        baseline_profile_id=row["baseline_profile_id"],
        current_profile_id=row["current_profile_id"],
        policy_version=row["policy_version"],
        status=ProfileComparisonStatus(row["status"]),
        anomaly_candidate=row["anomaly_candidate"],
        result=json_load(row["result"]),
        message=row["message"],
        created_at=row["created_at"],
    )


def row_to_processing_inventory(row: RowMapping) -> DataProcessingInventory:
    return DataProcessingInventory(
        inventory_id=row["inventory_id"],
        data_field_id=row["data_field_id"],
        version_number=row["version_number"],
        processing_purpose=row["processing_purpose"],
        legal_basis_reference=row["legal_basis_reference"],
        data_owner_id=row["data_owner_id"],
        retention_policy_id=row["retention_policy_id"],
        access_role_codes=tuple(json_load(row["access_role_codes"])),
        cross_border_transfer=bool(row["cross_border_transfer"]),
        recipient_groups=tuple(json_load(row["recipient_groups"])),
        recorded_at=row["recorded_at"],
    )


def json_load(value: Any) -> Any:
    if isinstance(value, dict | list):
        return value
    if isinstance(value, str):
        return json.loads(value)
    return value


def row_to_discovery_result(row: RowMapping) -> MetadataDiscoveryResult:
    return MetadataDiscoveryResult(
        data_source_id=row["data_source_id"],
        succeeded=bool(row["succeeded"]),
        duration_ms=row["duration_ms"],
        scanned_object_count=row["scanned_object_count"],
        error_class=ErrorClass(row["error_class"]) if row["error_class"] else None,
        message=row["message"],
        discovered_at=row["discovered_at"],
        discovery_id=row["discovery_id"],
        status=DiscoveryStatus(row["status"]),
        job_id=row.get("job_id"),
        requested_by_actor_id=row.get("requested_by_actor_id"),
        correlation_id=row.get("correlation_id"),
        scope_version=row.get("scope_version"),
        completed_scope=json_load(row.get("completed_scope") or {}),
        partial_reason_code=row.get("partial_reason_code"),
        started_at=row.get("started_at"),
        finished_at=row.get("finished_at"),
        version=row.get("version") or 1,
    )


def row_to_discovery_scope(row: RowMapping) -> DiscoveryScope:
    return DiscoveryScope(
        data_source_id=row["data_source_id"],
        include_patterns=tuple(json_load(row["include_patterns"])),
        exclude_patterns=tuple(json_load(row["exclude_patterns"])),
        page_size=row["page_size"],
        max_objects=row["max_objects"],
        timeout_seconds=row["timeout_seconds"],
        policy_version=row["policy_version"],
        updated_by_actor_id=row["updated_by_actor_id"],
        updated_at=row["updated_at"],
        version=row["version"],
    )


def row_to_metadata_diff(row: RowMapping) -> MetadataDiff:
    return MetadataDiff(
        metadata_diff_id=row["metadata_diff_id"],
        discovery_id=row["discovery_id"],
        data_source_id=row["data_source_id"],
        added_objects=tuple(json_load(row["added_objects"])),
        changed_objects=tuple(json_load(row["changed_objects"])),
        removed_objects=tuple(json_load(row["removed_objects"])),
        status=MetadataDiffStatus(row["status"]),
        requires_rule_review=bool(row["requires_rule_review"]),
        created_at=row["created_at"],
        applied_at=row.get("applied_at"),
        applied_by_actor_id=row.get("applied_by_actor_id"),
        version=row["version"],
    )
