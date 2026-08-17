"""Katalog ve metadata keşfi HTTP yanıt modelleri."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DiscoveryRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    idempotency_key: str | None = None


class DiscoveryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    discovery_id: int
    data_source_id: str
    status: str
    job_id: str | None = None


class DiscoveryScopeRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    include_patterns: list[str] = Field(default_factory=list)
    exclude_patterns: list[str] = Field(default_factory=list)
    page_size: int = Field(default=1000, ge=1, le=10_000)
    max_objects: int = Field(default=100_000, ge=1, le=100_000)
    timeout_seconds: int = Field(default=60, ge=1, le=3600)
    expected_version: int = Field(ge=1)
    policy_version: str


class DiscoveryScopeResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    data_source_id: str
    include_patterns: tuple[str, ...]
    exclude_patterns: tuple[str, ...]
    page_size: int
    max_objects: int
    timeout_seconds: int
    version: int


class DiscoveryStatusResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    discovery_id: int
    data_source_id: str
    status: str
    scanned_object_count: int
    completed_scope: dict[str, Any] = Field(default_factory=dict)
    partial_reason_code: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    discovery_correlation_id: str | None = None


class DiscoveryDiffResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    metadata_diff_id: str | None = None
    discovery_id: int
    data_source_id: str
    status: str
    added_objects: tuple[dict[str, Any], ...] = ()
    changed_objects: tuple[dict[str, Any], ...] = ()
    removed_objects: tuple[dict[str, Any], ...] = ()
    requires_rule_review: bool = False


class CatalogDatasetResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    dataset_id: str
    data_source_id: str
    namespace: str
    name: str
    dataset_type: str
    status: str
    criticality: str
    estimated_row_count: int | None = None
    field_count: int = 0
    version: int = 1
    owner_user_id: str | None = None
    timeliness_nature: str | None = None


class CatalogDatasetListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    items: tuple[CatalogDatasetResponse, ...]


class CatalogDatasetDetailResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    dataset: CatalogDatasetResponse
    data_source_name: str


class CatalogFieldResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    data_field_id: str
    dataset_id: str
    name: str
    native_data_type: str
    is_nullable: bool
    is_sensitive: bool
    classification: str
    status: str
    version: int = 1


class CatalogFieldListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    items: tuple[CatalogFieldResponse, ...]


class CatalogFieldDetailResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    field: CatalogFieldResponse
    dataset_name: str
    data_source_name: str


class DatasetPreviewColumnResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    native_data_type: str
    is_sensitive: bool


class DatasetPreviewResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    dataset_id: str
    source_type: str
    namespace: str
    table_name: str
    limit: int
    columns: tuple[DatasetPreviewColumnResponse, ...]
    rows: tuple[tuple[str | None, ...], ...]


# ── Update request models ─────────────────────────────────────────────


class DatasetUpdateRequest(BaseModel):
    """Dataset güncelleme isteği — yalnız yetkili kullanıcılar."""

    model_config = ConfigDict(frozen=True)

    name: str | None = Field(default=None, min_length=1, max_length=400)
    namespace: str | None = Field(default=None, min_length=1, max_length=200)
    status: str | None = Field(default=None, pattern="^(ACTIVE|INACTIVE)$")
    timeliness_nature: str | None = Field(
        default=None, pattern="^(NEAR_TIME|REAL_TIME|BATCH_TIME)$"
    )
    expected_version: int | None = Field(default=None, ge=1)


class FieldUpdateRequest(BaseModel):
    """Field güncelleme isteği — yalnız yetkili kullanıcılar."""

    model_config = ConfigDict(frozen=True)

    native_data_type: str | None = Field(default=None, min_length=1, max_length=200)
    is_nullable: bool | None = None
    is_sensitive: bool | None = None
    classification: str | None = Field(
        default=None,
        pattern="^(UNCLASSIFIED|PUBLIC|INTERNAL|CONFIDENTIAL|RESTRICTED|PERSONAL_DATA|SPECIAL_CATEGORY_PERSONAL_DATA|CUSTOMER_SECRET|BANK_SECRET)$",
    )
    status: str | None = Field(default=None, pattern="^(ACTIVE|INACTIVE)$")
    expected_version: int | None = Field(default=None, ge=1)
