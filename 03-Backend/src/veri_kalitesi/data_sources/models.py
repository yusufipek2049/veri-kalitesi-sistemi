"""Veri kaynağı domain modelleri."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from veri_kalitesi.data_protection import (
    CLASSIFICATION_POLICY_VERSION,
    ClassificationCode,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SourceType(str, Enum):
    POSTGRESQL = "POSTGRESQL"
    MSSQL = "MSSQL"
    ORACLE = "ORACLE"
    MYSQL = "MYSQL"
    CSV = "CSV"
    EXCEL = "EXCEL"
    REST = "REST"


class DataSourceStatus(str, Enum):
    TEST_PENDING = "TEST_PENDING"
    TEST_SUCCEEDED = "TEST_SUCCEEDED"
    TEST_FAILED = "TEST_FAILED"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class DataSourceActivationStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"
    EXPIRED = "EXPIRED"


@dataclass(frozen=True)
class DataSourceActivationPolicy:
    version: str
    actor_policy_version: str
    maker_roles: frozenset[str]
    checker_roles: frozenset[str]
    allowed_actor_types: frozenset[str] = field(default_factory=lambda: frozenset({"USER"}))
    target_business_days: int | None = None
    expiration_business_days: int | None = None
    business_calendar_version: str | None = None
    expiry_service_roles: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class DataSourceActivationRequest:
    data_source_id: str
    data_source_revision: int
    maker_actor_id: str
    policy_version: str
    status: DataSourceActivationStatus = DataSourceActivationStatus.PENDING
    checker_actor_id: str | None = None
    decision_reason_code: str | None = None
    activation_request_id: str = field(default_factory=lambda: str(uuid4()))
    requested_at: datetime = field(default_factory=utc_now)
    target_at: datetime | None = None
    expires_at: datetime | None = None
    business_calendar_version: str | None = None
    decided_at: datetime | None = None


class DatasetType(str, Enum):
    TABLE = "TABLE"
    VIEW = "VIEW"
    FILE_SHEET = "FILE_SHEET"
    API_COLLECTION = "API_COLLECTION"


class Criticality(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class MetadataChangeType(str, Enum):
    ADDED = "ADDED"
    CHANGED = "CHANGED"
    REMOVED = "REMOVED"


class ProfileMethod(str, Enum):
    FULL = "FULL"
    SAMPLE = "SAMPLE"
    PARTITION = "PARTITION"
    AGGREGATE = "AGGREGATE"


class ProfileStatus(str, Enum):
    COMPLETED = "COMPLETED"
    NO_DATA = "NO_DATA"
    TECHNICAL_ERROR = "TECHNICAL_ERROR"


class ErrorClass(str, Enum):
    VALIDATION = "VALIDATION"
    DNS = "DNS"
    NETWORK = "NETWORK"
    TIMEOUT = "TIMEOUT"
    AUTHENTICATION = "AUTHENTICATION"
    TLS = "TLS"
    PERMISSION = "PERMISSION"
    DRIVER = "DRIVER"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    UNSUPPORTED_SOURCE = "UNSUPPORTED_SOURCE"


@dataclass(frozen=True)
class DataSource:
    name: str
    source_type: SourceType
    connection_config: dict[str, Any]
    secret_reference: str
    owner_user_id: str | None = None
    data_source_id: str = field(default_factory=lambda: str(uuid4()))
    status: DataSourceStatus = DataSourceStatus.TEST_PENDING
    revision: int = 1
    last_test_at: datetime | None = None
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class Dataset:
    data_source_id: str
    namespace: str
    name: str
    dataset_type: DatasetType = DatasetType.TABLE
    criticality: Criticality = Criticality.MEDIUM
    owner_user_id: str | None = None
    estimated_row_count: int | None = None
    dataset_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(frozen=True)
class DataField:
    dataset_id: str
    name: str
    native_data_type: str
    is_nullable: bool = True
    is_sensitive: bool = False
    classification: ClassificationCode = ClassificationCode.UNCLASSIFIED
    classification_policy_version: str = CLASSIFICATION_POLICY_VERSION
    data_field_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(frozen=True)
class MetadataFieldCandidate:
    name: str
    native_data_type: str
    is_nullable: bool = True
    is_sensitive: bool = False
    classification: ClassificationCode | str | None = None


@dataclass(frozen=True)
class MetadataDatasetCandidate:
    namespace: str
    name: str
    dataset_type: DatasetType = DatasetType.TABLE
    estimated_row_count: int | None = None
    fields: tuple[MetadataFieldCandidate, ...] = ()


@dataclass(frozen=True)
class MetadataDiscoveryOptions:
    scope: dict[str, Any] = field(default_factory=dict)
    page_size: int = 1000
    max_objects: int = 100_000
    timeout_seconds: int = 60


@dataclass(frozen=True)
class MetadataChange:
    change_type: MetadataChangeType
    object_type: str
    namespace: str
    dataset_name: str
    field_name: str | None = None
    old_values: dict[str, Any] = field(default_factory=dict)
    new_values: dict[str, Any] = field(default_factory=dict)
    requires_rule_review: bool = False
    affected_rule_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class MetadataDiscoveryResult:
    data_source_id: str
    succeeded: bool
    duration_ms: int
    scanned_object_count: int = 0
    datasets: tuple[Dataset, ...] = ()
    fields: tuple[DataField, ...] = ()
    changes: tuple[MetadataChange, ...] = ()
    error_class: ErrorClass | None = None
    message: str = ""
    discovered_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class ProfileOptions:
    method: ProfileMethod = ProfileMethod.FULL
    sample_ratio: float | None = None
    field_names: tuple[str, ...] = ()
    key_field_names: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProfileComputationResult:
    status: ProfileStatus
    metrics: dict[str, Any]
    row_count: int
    error_class: ErrorClass | None = None
    message: str = ""


@dataclass(frozen=True)
class DataProfile:
    dataset_id: str
    execution_id: str
    method: ProfileMethod
    metrics: dict[str, Any]
    status: ProfileStatus
    sample_ratio: float | None = None
    duration_ms: int = 0
    error_class: ErrorClass | None = None
    message: str = ""
    profile_id: str = field(default_factory=lambda: str(uuid4()))
    started_at: datetime = field(default_factory=utc_now)
    finished_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class ConnectionTestResult:
    data_source_id: str
    succeeded: bool
    duration_ms: int
    error_class: ErrorClass | None = None
    message: str = ""
    source_info: dict[str, Any] = field(default_factory=dict)
    tested_at: datetime = field(default_factory=utc_now)
