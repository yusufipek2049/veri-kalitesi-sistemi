"""PostgreSQL-only data source persistence with immutable revision history.

Iteration 36D0 — Data sources PostgreSQL migration.
Issues/postgresql_repository.py ve rules/postgresql_repository.py sablonunu izler.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    and_,
    func,
    insert,
    select,
    update,
)
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from veri_kalitesi.audit.models import PreparedAuditEvent
from veri_kalitesi.audit.postgresql_outbox import PostgreSQLTransactionalAudit
from veri_kalitesi.data_protection import (
    ClassificationCode,
    DataProcessingInventory,
    INVENTORY_REQUIRED_CLASSIFICATIONS,
    InventoryCoverageItem,
    InventoryCoverageTechnicalError,
)
from veri_kalitesi.data_sources.errors import ConflictError, NotFoundError, ValidationError
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
    ProfileMethod,
    ProfileComparison,
    ProfileComparisonStatus,
    ProfileStatus,
    SourceType,
    metadata_change_to_dict,
)
from veri_kalitesi.persistence import DEFAULT_SCHEMA_NAME, SessionFactory, transactional_session


@dataclass(frozen=True)
class DataSourceTables:
    sources: Table
    connection_tests: Table
    datasets: Table
    fields: Table
    metadata_discovery: Table
    profiles: Table
    profile_comparisons: Table
    processing_inventory: Table
    connection_revisions: Table
    activation_requests: Table
    discovery_scopes: Table
    metadata_diffs: Table


def data_source_tables(schema: str = DEFAULT_SCHEMA_NAME) -> DataSourceTables:
    metadata = MetaData(schema=schema)
    sources = Table(
        "data_sources",
        metadata,
        Column("data_source_id", String(36), primary_key=True),
        Column("name", String(400), nullable=False, unique=True),
        Column("source_type", String(40), nullable=False),
        Column("connection_config", JSON, nullable=False),
        Column("secret_reference", String(500), nullable=False),
        Column("owner_user_id", String(128)),
        Column("status", String(30), nullable=False),
        Column("revision", Integer, nullable=False, server_default="1"),
        Column("last_test_at", DateTime(timezone=True)),
        Column("created_at", DateTime(timezone=True), nullable=False),
        CheckConstraint(
            "source_type IN ('POSTGRESQL', 'MSSQL', 'ORACLE', 'MYSQL', 'CSV', 'EXCEL', 'REST')",
            name="ck_ds_source_type",
        ),
        CheckConstraint(
            "status IN ("
            "'TEST_PENDING', 'TEST_SUCCEEDED', 'TEST_FAILED',"
            " 'ACTIVE', 'INACTIVE', 'ARCHIVED')",
            name="ck_ds_status",
        ),
    )
    connection_tests = Table(
        "connection_test_results",
        metadata,
        Column("test_result_id", Integer, primary_key=True, autoincrement=True),
        Column(
            "data_source_id",
            String(36),
            ForeignKey(f"{schema}.data_sources.data_source_id"),
            nullable=False,
        ),
        Column("succeeded", Boolean, nullable=False),
        Column("duration_ms", Integer, nullable=False),
        Column("error_class", String(40)),
        Column("message", Text, nullable=False),
        Column("source_info", JSON, nullable=False),
        Column("data_source_revision", Integer, nullable=False, server_default="1"),
        Column("tested_at", DateTime(timezone=True), nullable=False),
    )
    datasets = Table(
        "datasets",
        metadata,
        Column("dataset_id", String(36), primary_key=True),
        Column(
            "data_source_id",
            String(36),
            ForeignKey(f"{schema}.data_sources.data_source_id"),
            nullable=False,
        ),
        Column("namespace", String(200), nullable=False),
        Column("name", String(400), nullable=False),
        Column("dataset_type", String(40), nullable=False),
        Column("criticality", String(20), nullable=False),
        Column("owner_user_id", String(128)),
        Column("estimated_row_count", Integer),
        Column("status", String(20), nullable=False, server_default="ACTIVE"),
        Column("first_seen_discovery_id", Integer),
        Column("last_seen_discovery_id", Integer),
        Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
        Column("version", Integer, nullable=False, server_default="1"),
        UniqueConstraint(
            "data_source_id", "namespace", "name", name="uq_ds_datasets_source_ns_name"
        ),
        CheckConstraint(
            "dataset_type IN ('TABLE', 'VIEW', 'FILE_SHEET', 'API_COLLECTION')",
            name="ck_ds_dataset_type",
        ),
        CheckConstraint(
            "criticality IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="ck_ds_criticality",
        ),
        CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="ck_ds_datasets_status"),
        CheckConstraint("version >= 1", name="ck_ds_datasets_version"),
    )
    fields = Table(
        "data_fields",
        metadata,
        Column("data_field_id", String(36), primary_key=True),
        Column(
            "dataset_id", String(36), ForeignKey(f"{schema}.datasets.dataset_id"), nullable=False
        ),
        Column("name", String(400), nullable=False),
        Column("native_data_type", String(100), nullable=False),
        Column("is_nullable", Boolean, nullable=False),
        Column("is_sensitive", Boolean, nullable=False),
        Column("classification", String(40), nullable=False, server_default="UNCLASSIFIED"),
        Column(
            "classification_policy_version",
            String(40),
            nullable=False,
            server_default="CLASSIFICATION_POLICY_V1",
        ),
        Column("status", String(20), nullable=False, server_default="ACTIVE"),
        Column("first_seen_discovery_id", Integer),
        Column("last_seen_discovery_id", Integer),
        Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
        Column("version", Integer, nullable=False, server_default="1"),
        UniqueConstraint("dataset_id", "name", name="uq_ds_fields_dataset_name"),
        CheckConstraint(
            "classification IN ('UNCLASSIFIED', 'PUBLIC', 'INTERNAL', 'CONFIDENTIAL', "
            "'RESTRICTED', 'PERSONAL_DATA', 'SPECIAL_CATEGORY_PERSONAL_DATA', "
            "'CUSTOMER_SECRET', 'BANK_SECRET')",
            name="ck_ds_fields_classification",
        ),
        CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="ck_ds_fields_status"),
        CheckConstraint("version >= 1", name="ck_ds_fields_version"),
    )
    metadata_discovery = Table(
        "metadata_discovery_results",
        metadata,
        Column("discovery_id", Integer, primary_key=True, autoincrement=True),
        Column(
            "data_source_id",
            String(36),
            ForeignKey(f"{schema}.data_sources.data_source_id"),
            nullable=False,
        ),
        Column("succeeded", Boolean, nullable=False),
        Column("duration_ms", Integer, nullable=False),
        Column("scanned_object_count", Integer, nullable=False),
        Column("error_class", String(40)),
        Column("message", Text, nullable=False),
        Column("changes", JSON, nullable=False),
        Column("discovered_at", DateTime(timezone=True), nullable=False),
        Column("status", String(30), nullable=False),
        Column("job_id", String(36)),
        Column("requested_by_actor_id", String(128)),
        Column("correlation_id", String(128)),
        Column("scope_version", Integer),
        Column("completed_scope", JSON, nullable=False, server_default="'{}'::jsonb"),
        Column("partial_reason_code", String(100)),
        Column("started_at", DateTime(timezone=True)),
        Column("finished_at", DateTime(timezone=True)),
        Column("version", Integer, nullable=False, server_default="1"),
        UniqueConstraint("job_id", name="uq_ds_discovery_job"),
        CheckConstraint(
            "status IN ('QUEUED', 'RUNNING', 'SUCCESS', 'PARTIAL', 'TECHNICAL_ERROR', 'CANCELLED')",
            name="ck_ds_discovery_status",
        ),
        CheckConstraint("version >= 1", name="ck_ds_discovery_version"),
    )
    profiles = Table(
        "data_profiles",
        metadata,
        Column("profile_id", String(36), primary_key=True),
        Column(
            "dataset_id", String(36), ForeignKey(f"{schema}.datasets.dataset_id"), nullable=False
        ),
        Column("execution_id", String(36), nullable=False),
        Column("method", String(20), nullable=False),
        Column("sample_ratio", Float),
        Column("metrics", JSON, nullable=False),
        Column("status", String(30), nullable=False),
        Column("duration_ms", Integer, nullable=False),
        Column("error_class", String(40)),
        Column("message", Text, nullable=False),
        Column("started_at", DateTime(timezone=True), nullable=False),
        Column("finished_at", DateTime(timezone=True), nullable=False),
        CheckConstraint(
            "method IN ('FULL', 'SAMPLE', 'PARTITION', 'AGGREGATE')",
            name="ck_ds_profile_method",
        ),
        CheckConstraint(
            "status IN ('COMPLETED', 'NO_DATA', 'TECHNICAL_ERROR')",
            name="ck_ds_profile_status",
        ),
    )
    profile_comparisons = Table(
        "profile_comparisons",
        metadata,
        Column("comparison_id", String(36), primary_key=True),
        Column(
            "dataset_id", String(36), ForeignKey(f"{schema}.datasets.dataset_id"), nullable=False
        ),
        Column(
            "baseline_profile_id",
            String(36),
            ForeignKey(f"{schema}.data_profiles.profile_id"),
            nullable=False,
        ),
        Column(
            "current_profile_id",
            String(36),
            ForeignKey(f"{schema}.data_profiles.profile_id"),
            nullable=False,
        ),
        Column("policy_version", String(100)),
        Column("status", String(40), nullable=False),
        Column("anomaly_candidate", Boolean),
        Column("result", JSON, nullable=False),
        Column("message", Text, nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
        CheckConstraint(
            "status IN ('COMPLETED', 'CONFIGURATION_ERROR', "
            "'INSUFFICIENT_HISTORY', 'INCOMPATIBLE')",
            name="ck_ds_profile_comparison_status",
        ),
    )
    processing_inventory = Table(
        "data_processing_inventory_versions",
        metadata,
        Column("inventory_id", String(36), primary_key=True),
        Column(
            "data_field_id",
            String(36),
            ForeignKey(f"{schema}.data_fields.data_field_id"),
            nullable=False,
        ),
        Column("version_number", Integer, nullable=False),
        Column("processing_purpose", Text, nullable=False),
        Column("legal_basis_reference", Text, nullable=False),
        Column("data_owner_id", String(128), nullable=False),
        Column("retention_policy_id", String(40), nullable=False),
        Column("access_role_codes", JSON, nullable=False),
        Column("cross_border_transfer", Boolean, nullable=False),
        Column("recipient_groups", JSON, nullable=False),
        Column("recorded_at", DateTime(timezone=True), nullable=False),
        UniqueConstraint("data_field_id", "version_number", name="uq_ds_inventory_field_version"),
        CheckConstraint("version_number > 0", name="ck_ds_inventory_version"),
    )
    connection_revisions = Table(
        "data_source_connection_revisions",
        metadata,
        Column("connection_revision_id", String(36), primary_key=True),
        Column(
            "data_source_id",
            String(36),
            ForeignKey(f"{schema}.data_sources.data_source_id"),
            nullable=False,
        ),
        Column("revision", Integer, nullable=False),
        Column("base_revision", Integer, nullable=False),
        Column("connection_config", JSON, nullable=False),
        Column("secret_reference", String(500), nullable=False),
        Column("prepared_by_actor_id", String(128), nullable=False),
        Column("policy_version", String(40), nullable=False),
        Column("reason_code", String(100), nullable=False),
        Column("status", String(30), nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("tested_at", DateTime(timezone=True)),
        UniqueConstraint("data_source_id", "revision", name="uq_ds_conn_revision_source_rev"),
        CheckConstraint("revision > 0", name="ck_ds_conn_revision_revision"),
        CheckConstraint("base_revision > 0", name="ck_ds_conn_revision_base_revision"),
        CheckConstraint(
            "status IN ('PENDING_TEST', 'PROMOTED', 'TEST_FAILED', 'REJECTED')",
            name="ck_ds_conn_revision_status",
        ),
    )
    activation_requests = Table(
        "data_source_activation_requests",
        metadata,
        Column("activation_request_id", String(36), primary_key=True),
        Column(
            "data_source_id",
            String(36),
            ForeignKey(f"{schema}.data_sources.data_source_id"),
            nullable=False,
        ),
        Column("data_source_revision", Integer, nullable=False),
        Column("maker_actor_id", String(128), nullable=False),
        Column("checker_actor_id", String(128)),
        Column("policy_version", String(40), nullable=False),
        Column("status", String(30), nullable=False),
        Column("decision_reason_code", String(100)),
        Column("requested_at", DateTime(timezone=True), nullable=False),
        Column("target_at", DateTime(timezone=True)),
        Column("expires_at", DateTime(timezone=True)),
        Column("business_calendar_version", String(40)),
        Column("decided_at", DateTime(timezone=True)),
        Column("request_type", String(20), nullable=False, server_default="ACTIVATION"),
        CheckConstraint(
            "status IN ('PENDING', 'APPROVED', 'REJECTED', 'WITHDRAWN', 'EXPIRED', 'INVALIDATED')",
            name="ck_ds_activation_status",
        ),
    )
    discovery_scopes = Table(
        "discovery_scopes",
        metadata,
        Column(
            "data_source_id",
            String(36),
            ForeignKey(f"{schema}.data_sources.data_source_id"),
            primary_key=True,
        ),
        Column("include_patterns", JSON, nullable=False),
        Column("exclude_patterns", JSON, nullable=False),
        Column("page_size", Integer, nullable=False),
        Column("max_objects", Integer, nullable=False),
        Column("timeout_seconds", Integer, nullable=False),
        Column("policy_version", String(100), nullable=False),
        Column("updated_by_actor_id", String(128), nullable=False),
        Column("updated_at", DateTime(timezone=True), nullable=False),
        Column("version", Integer, nullable=False, server_default="1"),
        CheckConstraint("page_size >= 1 AND page_size <= 10000", name="ck_ds_scope_page_size"),
        CheckConstraint(
            "max_objects >= 1 AND max_objects <= 100000", name="ck_ds_scope_max_objects"
        ),
        CheckConstraint(
            "timeout_seconds >= 1 AND timeout_seconds <= 3600",
            name="ck_ds_scope_timeout",
        ),
        CheckConstraint("version >= 1", name="ck_ds_scope_version"),
    )
    metadata_diffs = Table(
        "metadata_diffs",
        metadata,
        Column("metadata_diff_id", String(36), primary_key=True),
        Column(
            "discovery_id",
            Integer,
            ForeignKey(f"{schema}.metadata_discovery_results.discovery_id"),
            nullable=False,
        ),
        Column(
            "data_source_id",
            String(36),
            ForeignKey(f"{schema}.data_sources.data_source_id"),
            nullable=False,
        ),
        Column("added_objects", JSON, nullable=False),
        Column("changed_objects", JSON, nullable=False),
        Column("removed_objects", JSON, nullable=False),
        Column("status", String(20), nullable=False),
        Column("requires_rule_review", Boolean, nullable=False, server_default="false"),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("applied_at", DateTime(timezone=True)),
        Column("applied_by_actor_id", String(128)),
        Column("version", Integer, nullable=False, server_default="1"),
        UniqueConstraint("discovery_id", name="uq_ds_diff_discovery"),
        CheckConstraint("status IN ('PENDING', 'APPLIED')", name="ck_ds_diff_status"),
        CheckConstraint("version >= 1", name="ck_ds_diff_version"),
    )
    return DataSourceTables(
        sources=sources,
        connection_tests=connection_tests,
        datasets=datasets,
        fields=fields,
        metadata_discovery=metadata_discovery,
        profiles=profiles,
        profile_comparisons=profile_comparisons,
        processing_inventory=processing_inventory,
        connection_revisions=connection_revisions,
        activation_requests=activation_requests,
        discovery_scopes=discovery_scopes,
        metadata_diffs=metadata_diffs,
    )


class PostgreSQLDataSourceRepository:
    """PostgreSQL-only DataSource repository.

    DataSourceService ile kullanilmak uzere DataSourceRepository
    protokolunu uygular. Her yazma islemi audit outbox ile ayni
    transaction icinde calisir.
    """

    def __init__(
        self,
        session_factory: SessionFactory,
        tables: DataSourceTables | None = None,
        *,
        schema: str = DEFAULT_SCHEMA_NAME,
    ) -> None:
        self.session_factory = session_factory
        self.tables = tables or data_source_tables(schema)

    def _s(self, session: Session) -> DataSourceTables:
        return self.tables

    # ------------------------------------------------------------------
    # Read methods
    # ------------------------------------------------------------------

    def get_data_source(self, data_source_id: str) -> DataSource:
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            row = (
                session.execute(
                    select(t.sources).where(t.sources.c.data_source_id == data_source_id)
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            raise NotFoundError("DataSource not found.")
        return _row_to_data_source(row)

    def list_data_sources(self, allowed_source_ids: frozenset[str]) -> list[DataSource]:
        if not allowed_source_ids:
            return []
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            source_ids = sorted(allowed_source_ids)
            rows = (
                session.execute(
                    select(t.sources)
                    .where(t.sources.c.data_source_id.in_(source_ids))
                    .order_by(func.lower(t.sources.c.name), t.sources.c.data_source_id)
                )
                .mappings()
                .all()
            )
        return [_row_to_data_source(row) for row in rows]

    def list_all_data_sources(self) -> list[DataSource]:
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            rows = (
                session.execute(
                    select(t.sources).order_by(
                        func.lower(t.sources.c.name), t.sources.c.data_source_id
                    )
                )
                .mappings()
                .all()
            )
        return [_row_to_data_source(row) for row in rows]

    def latest_connection_test(
        self,
        data_source_id: str,
        *,
        data_source_revision: int | None = None,
    ) -> ConnectionTestResult | None:
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            query = select(t.connection_tests).where(
                t.connection_tests.c.data_source_id == data_source_id
            )
            if data_source_revision is not None:
                query = query.where(
                    t.connection_tests.c.data_source_revision == data_source_revision
                )
            query = query.order_by(t.connection_tests.c.test_result_id.desc()).limit(1)
            row = session.execute(query).mappings().one_or_none()
        if row is None:
            return None
        return _row_to_connection_test(row)

    def next_connection_revision(self, data_source_id: str) -> int:
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            row = session.execute(
                select(func.coalesce(func.max(t.connection_revisions.c.revision), 0) + 1).where(
                    t.connection_revisions.c.data_source_id == data_source_id
                )
            ).scalar()
        return int(row)  # type: ignore[arg-type]

    def latest_pending_connection_revision(
        self,
        data_source_id: str,
    ) -> DataSourceConnectionRevision | None:
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            row = (
                session.execute(
                    select(t.connection_revisions)
                    .where(
                        and_(
                            t.connection_revisions.c.data_source_id == data_source_id,
                            t.connection_revisions.c.status
                            == ConnectionRevisionStatus.PENDING_TEST.value,
                        )
                    )
                    .order_by(t.connection_revisions.c.revision.desc())
                    .limit(1)
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            return None
        return _row_to_connection_revision(row)

    def get_connection_revision(
        self,
        connection_revision_id: str,
    ) -> DataSourceConnectionRevision:
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            row = (
                session.execute(
                    select(t.connection_revisions).where(
                        t.connection_revisions.c.connection_revision_id == connection_revision_id
                    )
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            raise NotFoundError("DataSourceConnectionRevision not found.")
        return _row_to_connection_revision(row)

    def count_pending_activation_requests_except(
        self,
        data_source_id: str,
        revision: int,
    ) -> int:
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            count = session.execute(
                select(func.count()).where(
                    and_(
                        t.activation_requests.c.data_source_id == data_source_id,
                        t.activation_requests.c.data_source_revision != revision,
                        t.activation_requests.c.status == DataSourceActivationStatus.PENDING.value,
                    )
                )
            ).scalar()
        return int(count)  # type: ignore[arg-type]

    def get_activation_request(
        self,
        activation_request_id: str,
    ) -> DataSourceActivationRequest:
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            row = (
                session.execute(
                    select(t.activation_requests).where(
                        t.activation_requests.c.activation_request_id == activation_request_id
                    )
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            raise NotFoundError(
                "DataSourceActivationRequest not found.",
                code="ACTIVATION_REQUEST_NOT_FOUND",
            )
        return _row_to_activation_request(row)

    def latest_pending_activation_request(
        self,
        data_source_id: str,
    ) -> DataSourceActivationRequest | None:
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            row = (
                session.execute(
                    select(t.activation_requests)
                    .where(
                        and_(
                            t.activation_requests.c.data_source_id == data_source_id,
                            t.activation_requests.c.status
                            == DataSourceActivationStatus.PENDING.value,
                        )
                    )
                    .order_by(t.activation_requests.c.requested_at.desc())
                    .limit(1)
                )
                .mappings()
                .one_or_none()
            )
        return _row_to_activation_request(row) if row is not None else None

    def list_due_activation_requests(
        self,
        as_of: datetime,
    ) -> list[DataSourceActivationRequest]:
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            rows = (
                session.execute(
                    select(t.activation_requests)
                    .where(
                        and_(
                            t.activation_requests.c.status
                            == DataSourceActivationStatus.PENDING.value,
                            t.activation_requests.c.expires_at.isnot(None),
                            t.activation_requests.c.expires_at <= as_of,
                        )
                    )
                    .order_by(
                        t.activation_requests.c.expires_at,
                        t.activation_requests.c.activation_request_id,
                    )
                )
                .mappings()
                .all()
            )
        return [_row_to_activation_request(row) for row in rows]

    def list_datasets(self, data_source_id: str) -> list[Dataset]:
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            rows = (
                session.execute(
                    select(t.datasets)
                    .where(t.datasets.c.data_source_id == data_source_id)
                    .order_by(t.datasets.c.namespace, t.datasets.c.name)
                )
                .mappings()
                .all()
            )
        return [_row_to_dataset(row) for row in rows]

    def list_data_fields(self, dataset_id: str) -> list[DataField]:
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            rows = (
                session.execute(
                    select(t.fields)
                    .where(t.fields.c.dataset_id == dataset_id)
                    .order_by(t.fields.c.name)
                )
                .mappings()
                .all()
            )
        return [_row_to_data_field(row) for row in rows]

    def get_dataset(self, dataset_id: str) -> Dataset:
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            row = (
                session.execute(select(t.datasets).where(t.datasets.c.dataset_id == dataset_id))
                .mappings()
                .one_or_none()
            )
        if row is None:
            raise NotFoundError("Dataset not found.")
        return _row_to_dataset(row)

    def get_data_field(self, data_field_id: str) -> DataField:
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            row = (
                session.execute(select(t.fields).where(t.fields.c.data_field_id == data_field_id))
                .mappings()
                .one_or_none()
            )
        if row is None:
            raise NotFoundError("DataField not found.")
        return _row_to_data_field(row)

    def update_dataset(
        self,
        *,
        dataset_id: str,
        updates: dict[str, Any],
        expected_version: int,
    ) -> Dataset:
        if not updates:
            return self.get_dataset(dataset_id)
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            stmt = (
                update(t.datasets)
                .where(
                    and_(
                        t.datasets.c.dataset_id == dataset_id,
                        t.datasets.c.version == expected_version,
                    )
                )
                .values(**updates, version=expected_version + 1, updated_at=func.now())
                .returning(t.datasets)
            )
            row = session.execute(stmt).mappings().one_or_none()
            if row is None:
                raise ConflictError(
                    f"Dataset not found or version mismatch (expected {expected_version})."
                )
        return _row_to_dataset(row)

    def update_field(
        self,
        *,
        field_id: str,
        updates: dict[str, Any],
        expected_version: int,
    ) -> DataField:
        if not updates:
            return self.get_data_field(field_id)
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            stmt = (
                update(t.fields)
                .where(
                    and_(
                        t.fields.c.data_field_id == field_id,
                        t.fields.c.version == expected_version,
                    )
                )
                .values(**updates, version=expected_version + 1, updated_at=func.now())
                .returning(t.fields)
            )
            row = session.execute(stmt).mappings().one_or_none()
            if row is None:
                raise ConflictError(
                    f"DataField not found or version mismatch (expected {expected_version})."
                )
        return _row_to_data_field(row)

    def list_metadata_snapshot(
        self,
        data_source_id: str,
    ) -> dict[tuple[str, str], list[DataField]]:
        snapshot: dict[tuple[str, str], list[DataField]] = {}
        for dataset in self.list_datasets(data_source_id):
            snapshot[(dataset.namespace, dataset.name)] = self.list_data_fields(dataset.dataset_id)
        return snapshot

    def list_data_profiles(self, dataset_id: str) -> list[DataProfile]:
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            rows = (
                session.execute(
                    select(t.profiles)
                    .where(t.profiles.c.dataset_id == dataset_id)
                    .order_by(t.profiles.c.finished_at, t.profiles.c.profile_id)
                )
                .mappings()
                .all()
            )
        return [_row_to_data_profile(row) for row in rows]

    def list_profile_comparisons(self, dataset_id: str) -> list[ProfileComparison]:
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            rows = (
                session.execute(
                    select(t.profile_comparisons)
                    .where(t.profile_comparisons.c.dataset_id == dataset_id)
                    .order_by(
                        t.profile_comparisons.c.created_at,
                        t.profile_comparisons.c.comparison_id,
                    )
                )
                .mappings()
                .all()
            )
        return [_row_to_profile_comparison(row) for row in rows]

    def next_processing_inventory_version(self, data_field_id: str) -> int:
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            row = session.execute(
                select(
                    func.coalesce(func.max(t.processing_inventory.c.version_number), 0) + 1
                ).where(t.processing_inventory.c.data_field_id == data_field_id)
            ).scalar()
        return int(row)  # type: ignore[arg-type]

    def list_processing_inventory_history(
        self,
        data_field_id: str,
    ) -> list[DataProcessingInventory]:
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            rows = (
                session.execute(
                    select(t.processing_inventory)
                    .where(t.processing_inventory.c.data_field_id == data_field_id)
                    .order_by(t.processing_inventory.c.version_number)
                )
                .mappings()
                .all()
            )
        return [_row_to_processing_inventory(row) for row in rows]

    def get_current_processing_inventory(
        self,
        data_field_id: str,
    ) -> DataProcessingInventory | None:
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            row = (
                session.execute(
                    select(t.processing_inventory)
                    .where(t.processing_inventory.c.data_field_id == data_field_id)
                    .order_by(t.processing_inventory.c.version_number.desc())
                    .limit(1)
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            return None
        return _row_to_processing_inventory(row)

    def list_processing_inventory_coverage(
        self,
        data_source_id: str | None = None,
    ) -> tuple[InventoryCoverageItem, ...]:
        required_classifications = sorted(
            classification.value for classification in INVENTORY_REQUIRED_CLASSIFICATIONS
        )
        try:
            with transactional_session(self.session_factory) as session:
                t = self._s(session)
                current_inv = (
                    select(
                        t.processing_inventory.c.data_field_id,
                        func.max(t.processing_inventory.c.version_number).label("version_number"),
                    )
                    .group_by(t.processing_inventory.c.data_field_id)
                    .subquery()
                )
                query = (
                    select(
                        t.sources.c.data_source_id,
                        t.datasets.c.dataset_id,
                        t.fields.c.data_field_id,
                        t.fields.c.classification,
                        current_inv.c.version_number,
                    )
                    .select_from(t.fields)
                    .join(t.datasets, t.datasets.c.dataset_id == t.fields.c.dataset_id)
                    .join(t.sources, t.sources.c.data_source_id == t.datasets.c.data_source_id)
                    .outerjoin(
                        current_inv,
                        current_inv.c.data_field_id == t.fields.c.data_field_id,
                    )
                    .where(t.fields.c.classification.in_(required_classifications))
                )
                if data_source_id is not None:
                    query = query.where(t.sources.c.data_source_id == data_source_id)
                query = query.order_by(
                    t.sources.c.data_source_id,
                    t.datasets.c.dataset_id,
                    t.fields.c.data_field_id,
                )
                rows = session.execute(query).mappings().all()
        except Exception as exc:
            raise InventoryCoverageTechnicalError(
                "Processing inventory coverage could not be read."
            ) from exc
        return tuple(
            InventoryCoverageItem(
                data_source_id=row["data_source_id"],
                dataset_id=row["dataset_id"],
                data_field_id=row["data_field_id"],
                classification=ClassificationCode(row["classification"]),
                inventory_version=row["version_number"],
                issue_code=(
                    None if row["version_number"] is not None else "MISSING_CURRENT_INVENTORY"
                ),
            )
            for row in rows
        )

    def dump_data_source_storage(self, data_source_id: str) -> dict[str, Any]:
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            row = (
                session.execute(
                    select(t.sources).where(t.sources.c.data_source_id == data_source_id)
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            raise NotFoundError("DataSource not found.")
        return dict(row)

    # ------------------------------------------------------------------
    # Write methods
    # ------------------------------------------------------------------

    def add_data_source(
        self,
        data_source: DataSource,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: PostgreSQLTransactionalAudit,
    ) -> DataSource:
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            try:
                session.execute(
                    insert(t.sources).values(
                        data_source_id=data_source.data_source_id,
                        name=data_source.name,
                        source_type=data_source.source_type.value,
                        connection_config=json.dumps(data_source.connection_config, sort_keys=True),
                        secret_reference=data_source.secret_reference,
                        owner_user_id=data_source.owner_user_id,
                        status=data_source.status.value,
                        revision=data_source.revision,
                        last_test_at=data_source.last_test_at,
                        created_at=data_source.created_at,
                    )
                )
                session.execute(
                    insert(t.connection_revisions).values(
                        connection_revision_id=f"initial-{data_source.data_source_id}-{data_source.revision}",
                        data_source_id=data_source.data_source_id,
                        revision=data_source.revision,
                        base_revision=data_source.revision,
                        connection_config=json.dumps(data_source.connection_config, sort_keys=True),
                        secret_reference=data_source.secret_reference,
                        prepared_by_actor_id="SYSTEM_CREATE",
                        policy_version="INITIAL_V1",
                        reason_code="DATA_SOURCE.CREATED",
                        status=ConnectionRevisionStatus.PROMOTED.value,
                        created_at=data_source.created_at,
                        tested_at=data_source.last_test_at,
                    )
                )
                audit_outbox.stage(audit_event, session=session)
            except IntegrityError as exc:
                raise ValidationError("DataSource name must be unique.") from exc
        return data_source

    def deactivate_data_source(
        self,
        data_source_id: str,
        *,
        expected_revision: int,
        audit_event: PreparedAuditEvent,
        audit_outbox: PostgreSQLTransactionalAudit,
    ) -> DataSource:
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            result = session.execute(
                update(t.sources)
                .where(
                    and_(
                        t.sources.c.data_source_id == data_source_id,
                        t.sources.c.revision == expected_revision,
                        t.sources.c.status == DataSourceStatus.ACTIVE.value,
                    )
                )
                .values(status=DataSourceStatus.INACTIVE.value)
            )
            if result.rowcount != 1:  # type: ignore[attr-defined]
                raise ConflictError(
                    "Data source is no longer eligible for deactivation.",
                    code="DATA_SOURCE_REVISION_CONFLICT",
                )
            audit_outbox.stage(audit_event, session=session)
            # Re-read within transaction
            row = (
                session.execute(
                    select(t.sources).where(t.sources.c.data_source_id == data_source_id)
                )
                .mappings()
                .one()
            )
        return _row_to_data_source(row)

    def update_connection_test(
        self,
        result: ConnectionTestResult,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: PostgreSQLTransactionalAudit,
    ) -> None:
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            current = (
                session.execute(
                    select(t.sources).where(t.sources.c.data_source_id == result.data_source_id)
                )
                .mappings()
                .one()
            )
            current_status = DataSourceStatus(current["status"])
            new_status = DataSourceStatus.TEST_FAILED
            if result.succeeded:
                new_status = (
                    DataSourceStatus.ACTIVE
                    if current_status is DataSourceStatus.ACTIVE
                    else DataSourceStatus.TEST_SUCCEEDED
                )
            session.execute(
                insert(t.connection_tests).values(
                    data_source_id=result.data_source_id,
                    succeeded=result.succeeded,
                    duration_ms=result.duration_ms,
                    error_class=result.error_class.value if result.error_class else None,
                    message=result.message,
                    source_info=json.dumps(result.source_info, sort_keys=True),
                    data_source_revision=result.data_source_revision,
                    tested_at=result.tested_at,
                )
            )
            session.execute(
                update(t.sources)
                .where(t.sources.c.data_source_id == result.data_source_id)
                .values(status=new_status.value, last_test_at=result.tested_at)
            )
            audit_outbox.stage(audit_event, session=session)

    def add_connection_revision(
        self,
        revision: DataSourceConnectionRevision,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: PostgreSQLTransactionalAudit,
    ) -> DataSourceConnectionRevision:
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            try:
                session.execute(
                    insert(t.connection_revisions).values(
                        connection_revision_id=revision.connection_revision_id,
                        data_source_id=revision.data_source_id,
                        revision=revision.revision,
                        base_revision=revision.base_revision,
                        connection_config=json.dumps(revision.connection_config, sort_keys=True),
                        secret_reference=revision.secret_reference,
                        prepared_by_actor_id=revision.prepared_by_actor_id,
                        policy_version=revision.policy_version,
                        reason_code=revision.reason_code,
                        status=revision.status.value,
                        created_at=revision.created_at,
                        tested_at=revision.tested_at,
                    )
                )
                audit_outbox.stage(audit_event, session=session)
            except IntegrityError as exc:
                raise ValidationError("Data source connection revision already exists.") from exc
        return self.get_connection_revision(revision.connection_revision_id)

    def record_connection_revision_test(
        self,
        revision: DataSourceConnectionRevision,
        result: ConnectionTestResult,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: PostgreSQLTransactionalAudit,
    ) -> DataSourceConnectionRevision:
        if revision.status not in {
            ConnectionRevisionStatus.PROMOTED,
            ConnectionRevisionStatus.TEST_FAILED,
        }:
            raise ValidationError("Connection revision test status is invalid.")
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            session.execute(
                insert(t.connection_tests).values(
                    data_source_id=result.data_source_id,
                    succeeded=result.succeeded,
                    duration_ms=result.duration_ms,
                    error_class=result.error_class.value if result.error_class else None,
                    message=result.message,
                    source_info=json.dumps(result.source_info, sort_keys=True),
                    data_source_revision=result.data_source_revision,
                    tested_at=result.tested_at,
                )
            )
            update_result = session.execute(
                update(t.connection_revisions)
                .where(
                    and_(
                        t.connection_revisions.c.connection_revision_id
                        == revision.connection_revision_id,
                        t.connection_revisions.c.status.in_(
                            [
                                ConnectionRevisionStatus.PENDING_TEST.value,
                                ConnectionRevisionStatus.TEST_FAILED.value,
                            ]
                        ),
                    )
                )
                .values(status=revision.status.value, tested_at=revision.tested_at)
            )
            if update_result.rowcount != 1:  # type: ignore[attr-defined]
                raise ValidationError("Connection revision is not testable.")
            if revision.status is ConnectionRevisionStatus.PROMOTED:
                source_update = session.execute(
                    update(t.sources)
                    .where(
                        and_(
                            t.sources.c.data_source_id == revision.data_source_id,
                            t.sources.c.revision == revision.base_revision,
                            t.sources.c.status != DataSourceStatus.ARCHIVED.value,
                        )
                    )
                    .values(
                        connection_config=json.dumps(revision.connection_config, sort_keys=True),
                        secret_reference=revision.secret_reference,
                        revision=revision.revision,
                        status=DataSourceStatus.TEST_SUCCEEDED.value,
                        last_test_at=result.tested_at,
                    )
                )
                if source_update.rowcount != 1:  # type: ignore[attr-defined]
                    raise ValidationError("Connection revision base is stale.")
                session.execute(
                    update(t.activation_requests)
                    .where(
                        and_(
                            t.activation_requests.c.data_source_id == revision.data_source_id,
                            t.activation_requests.c.data_source_revision != revision.revision,
                            t.activation_requests.c.status
                            == DataSourceActivationStatus.PENDING.value,
                        )
                    )
                    .values(
                        status=DataSourceActivationStatus.INVALIDATED.value,
                        decision_reason_code="DATA_SOURCE.REVISION_CHANGED",
                        decided_at=result.tested_at,
                    )
                )
            audit_outbox.stage(audit_event, session=session)
        return self.get_connection_revision(revision.connection_revision_id)

    def add_activation_request(
        self,
        request: DataSourceActivationRequest,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: PostgreSQLTransactionalAudit,
    ) -> DataSourceActivationRequest:
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            try:
                session.execute(
                    insert(t.activation_requests).values(
                        activation_request_id=request.activation_request_id,
                        data_source_id=request.data_source_id,
                        data_source_revision=request.data_source_revision,
                        maker_actor_id=request.maker_actor_id,
                        checker_actor_id=request.checker_actor_id,
                        policy_version=request.policy_version,
                        status=request.status.value,
                        decision_reason_code=request.decision_reason_code,
                        requested_at=request.requested_at,
                        target_at=request.target_at,
                        expires_at=request.expires_at,
                        business_calendar_version=request.business_calendar_version,
                        decided_at=request.decided_at,
                        request_type=request.request_type,
                    )
                )
                audit_outbox.stage(audit_event, session=session)
            except IntegrityError as exc:
                if _constraint_name(exc) == "uq_activation_requests_pending_source_revision":
                    raise ConflictError(
                        "A pending activation request already exists "
                        "for this data source revision.",
                        code="DATA_SOURCE_PENDING_ACTIVATION_EXISTS",
                    ) from exc
                raise
        return self.get_activation_request(request.activation_request_id)

    def decide_activation_request(
        self,
        request: DataSourceActivationRequest,
        *,
        activate_source: bool,
        audit_event: PreparedAuditEvent,
        audit_outbox: PostgreSQLTransactionalAudit,
    ) -> DataSourceActivationRequest:
        if request.status not in {
            DataSourceActivationStatus.APPROVED,
            DataSourceActivationStatus.REJECTED,
        }:
            raise ValidationError("Data source activation decision status is invalid.")
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            update_result = session.execute(
                update(t.activation_requests)
                .where(
                    and_(
                        t.activation_requests.c.activation_request_id
                        == request.activation_request_id,
                        t.activation_requests.c.status == DataSourceActivationStatus.PENDING.value,
                    )
                )
                .values(
                    checker_actor_id=request.checker_actor_id,
                    status=request.status.value,
                    decision_reason_code=request.decision_reason_code,
                    decided_at=request.decided_at,
                )
            )
            if update_result.rowcount != 1:  # type: ignore[attr-defined]
                raise ConflictError(
                    "Data source activation request is not pending.",
                    code="DATA_SOURCE_DECISION_CONFLICT",
                )
            if activate_source:
                source_update = session.execute(
                    update(t.sources)
                    .where(
                        and_(
                            t.sources.c.data_source_id == request.data_source_id,
                            t.sources.c.revision == request.data_source_revision,
                            t.sources.c.status.in_(
                                [
                                    DataSourceStatus.TEST_SUCCEEDED.value,
                                    DataSourceStatus.INACTIVE.value,
                                ]
                            ),
                        )
                    )
                    .values(status=DataSourceStatus.ACTIVE.value)
                )
                if source_update.rowcount != 1:  # type: ignore[attr-defined]
                    raise ConflictError(
                        "Data source revision is no longer eligible for activation.",
                        code="DATA_SOURCE_REVISION_CONFLICT",
                    )
            audit_outbox.stage(audit_event, session=session)
        return self.get_activation_request(request.activation_request_id)

    def _finish_activation_request(
        self,
        request: DataSourceActivationRequest,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: PostgreSQLTransactionalAudit,
    ) -> DataSourceActivationRequest:
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            update_result = session.execute(
                update(t.activation_requests)
                .where(
                    and_(
                        t.activation_requests.c.activation_request_id
                        == request.activation_request_id,
                        t.activation_requests.c.status == DataSourceActivationStatus.PENDING.value,
                    )
                )
                .values(
                    checker_actor_id=None,
                    status=request.status.value,
                    decision_reason_code=request.decision_reason_code,
                    decided_at=request.decided_at,
                )
            )
            if update_result.rowcount != 1:  # type: ignore[attr-defined]
                raise ValidationError("Data source activation request is not pending.")
            audit_outbox.stage(audit_event, session=session)
        return self.get_activation_request(request.activation_request_id)

    def withdraw_activation_request(
        self,
        request: DataSourceActivationRequest,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: PostgreSQLTransactionalAudit,
    ) -> DataSourceActivationRequest:
        if request.status is not DataSourceActivationStatus.WITHDRAWN:
            raise ValidationError("Data source activation withdrawal status is invalid.")
        return self._finish_activation_request(
            request, audit_event=audit_event, audit_outbox=audit_outbox
        )

    def expire_activation_request(
        self,
        request: DataSourceActivationRequest,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: PostgreSQLTransactionalAudit,
    ) -> DataSourceActivationRequest:
        if request.status is not DataSourceActivationStatus.EXPIRED:
            raise ValidationError("Data source activation expiry status is invalid.")
        return self._finish_activation_request(
            request, audit_event=audit_event, audit_outbox=audit_outbox
        )

    def latest_pending_deactivation_request(
        self,
        data_source_id: str,
    ) -> DataSourceActivationRequest | None:
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            row = (
                session.execute(
                    select(t.activation_requests)
                    .where(
                        and_(
                            t.activation_requests.c.data_source_id == data_source_id,
                            t.activation_requests.c.status
                            == DataSourceActivationStatus.PENDING.value,
                            t.activation_requests.c.request_type == "DEACTIVATION",
                        )
                    )
                    .order_by(t.activation_requests.c.requested_at.desc())
                    .limit(1)
                )
                .mappings()
                .one_or_none()
            )
        return _row_to_activation_request(row) if row is not None else None

    def add_deactivation_request(
        self,
        request: DataSourceActivationRequest,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: PostgreSQLTransactionalAudit,
    ) -> DataSourceActivationRequest:
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            try:
                session.execute(
                    insert(t.activation_requests).values(
                        activation_request_id=request.activation_request_id,
                        data_source_id=request.data_source_id,
                        data_source_revision=request.data_source_revision,
                        maker_actor_id=request.maker_actor_id,
                        checker_actor_id=request.checker_actor_id,
                        policy_version=request.policy_version,
                        status=request.status.value,
                        decision_reason_code=request.decision_reason_code,
                        requested_at=request.requested_at,
                        target_at=request.target_at,
                        expires_at=request.expires_at,
                        business_calendar_version=request.business_calendar_version,
                        decided_at=request.decided_at,
                        request_type="DEACTIVATION",
                    )
                )
                audit_outbox.stage(audit_event, session=session)
            except IntegrityError as exc:
                if _constraint_name(exc) == "uq_activation_requests_pending_source_revision":
                    raise ConflictError(
                        "A pending deactivation request already exists "
                        "for this data source revision.",
                        code="DATA_SOURCE_PENDING_DEACTIVATION_EXISTS",
                    ) from exc
                raise
        return self.get_activation_request(request.activation_request_id)

    def decide_deactivation_request(
        self,
        request: DataSourceActivationRequest,
        *,
        deactivate_source: bool,
        audit_event: PreparedAuditEvent,
        audit_outbox: PostgreSQLTransactionalAudit,
    ) -> DataSourceActivationRequest:
        if request.status not in {
            DataSourceActivationStatus.APPROVED,
            DataSourceActivationStatus.REJECTED,
        }:
            raise ValidationError("Data source deactivation decision status is invalid.")
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            update_result = session.execute(
                update(t.activation_requests)
                .where(
                    and_(
                        t.activation_requests.c.activation_request_id
                        == request.activation_request_id,
                        t.activation_requests.c.status == DataSourceActivationStatus.PENDING.value,
                    )
                )
                .values(
                    checker_actor_id=request.checker_actor_id,
                    status=request.status.value,
                    decision_reason_code=request.decision_reason_code,
                    decided_at=request.decided_at,
                )
            )
            if update_result.rowcount != 1:  # type: ignore[attr-defined]
                raise ConflictError(
                    "Data source deactivation request is not pending.",
                    code="DATA_SOURCE_DECISION_CONFLICT",
                )
            if deactivate_source:
                source_update = session.execute(
                    update(t.sources)
                    .where(
                        and_(
                            t.sources.c.data_source_id == request.data_source_id,
                            t.sources.c.revision == request.data_source_revision,
                            t.sources.c.status == DataSourceStatus.ACTIVE.value,
                        )
                    )
                    .values(status=DataSourceStatus.INACTIVE.value)
                )
                if source_update.rowcount != 1:  # type: ignore[attr-defined]
                    raise ConflictError(
                        "Data source revision is no longer eligible for deactivation.",
                        code="DATA_SOURCE_REVISION_CONFLICT",
                    )
            audit_outbox.stage(audit_event, session=session)
        return self.get_activation_request(request.activation_request_id)

    def replace_metadata(
        self,
        data_source_id: str,
        datasets: list[Dataset],
        fields_by_dataset_id: dict[str, list[DataField]],
        result: MetadataDiscoveryResult,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: PostgreSQLTransactionalAudit,
    ) -> None:
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            # Fetch existing dataset IDs
            existing = (
                session.execute(
                    select(t.datasets.c.dataset_id).where(
                        t.datasets.c.data_source_id == data_source_id
                    )
                )
                .scalars()
                .all()
            )
            if existing:
                session.execute(t.fields.delete().where(t.fields.c.dataset_id.in_(existing)))
            session.execute(
                t.datasets.delete().where(t.datasets.c.data_source_id == data_source_id)
            )
            for dataset in datasets:
                session.execute(
                    insert(t.datasets).values(
                        dataset_id=dataset.dataset_id,
                        data_source_id=dataset.data_source_id,
                        namespace=dataset.namespace,
                        name=dataset.name,
                        dataset_type=dataset.dataset_type.value,
                        criticality=dataset.criticality.value,
                        owner_user_id=dataset.owner_user_id,
                        estimated_row_count=dataset.estimated_row_count,
                    )
                )
                for field in fields_by_dataset_id.get(dataset.dataset_id, []):
                    session.execute(
                        insert(t.fields).values(
                            data_field_id=field.data_field_id,
                            dataset_id=field.dataset_id,
                            name=field.name,
                            native_data_type=field.native_data_type,
                            is_nullable=field.is_nullable,
                            is_sensitive=field.is_sensitive,
                            classification=field.classification.value,
                            classification_policy_version=field.classification_policy_version,
                        )
                    )
            self._insert_metadata_discovery_result(session, t, result)
            audit_outbox.stage(audit_event, session=session)

    def record_metadata_discovery_failure(
        self,
        result: MetadataDiscoveryResult,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: PostgreSQLTransactionalAudit,
    ) -> None:
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            self._insert_metadata_discovery_result(session, t, result)
            audit_outbox.stage(audit_event, session=session)

    def add_data_profile(
        self,
        profile: DataProfile,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: PostgreSQLTransactionalAudit,
    ) -> DataProfile:
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            session.execute(
                insert(t.profiles).values(
                    profile_id=profile.profile_id,
                    dataset_id=profile.dataset_id,
                    execution_id=profile.execution_id,
                    method=profile.method.value,
                    sample_ratio=profile.sample_ratio,
                    metrics=json.dumps(profile.metrics, sort_keys=True),
                    status=profile.status.value,
                    duration_ms=profile.duration_ms,
                    error_class=profile.error_class.value if profile.error_class else None,
                    message=profile.message,
                    started_at=profile.started_at,
                    finished_at=profile.finished_at,
                )
            )
            audit_outbox.stage(audit_event, session=session)
        return profile

    def add_profile_comparison(
        self,
        comparison: ProfileComparison,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: PostgreSQLTransactionalAudit,
    ) -> ProfileComparison:
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            session.execute(
                insert(t.profile_comparisons).values(
                    comparison_id=comparison.comparison_id,
                    dataset_id=comparison.dataset_id,
                    baseline_profile_id=comparison.baseline_profile_id,
                    current_profile_id=comparison.current_profile_id,
                    policy_version=comparison.policy_version,
                    status=comparison.status.value,
                    anomaly_candidate=comparison.anomaly_candidate,
                    result=json.dumps(comparison.result, sort_keys=True),
                    message=comparison.message,
                    created_at=comparison.created_at,
                )
            )
            audit_outbox.stage(audit_event, session=session)
        return comparison

    def add_processing_inventory(
        self,
        inventory: DataProcessingInventory,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: PostgreSQLTransactionalAudit,
    ) -> DataProcessingInventory:
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            try:
                session.execute(
                    insert(t.processing_inventory).values(
                        inventory_id=inventory.inventory_id,
                        data_field_id=inventory.data_field_id,
                        version_number=inventory.version_number,
                        processing_purpose=inventory.processing_purpose,
                        legal_basis_reference=inventory.legal_basis_reference,
                        data_owner_id=inventory.data_owner_id,
                        retention_policy_id=inventory.retention_policy_id,
                        access_role_codes=json.dumps(inventory.access_role_codes),
                        cross_border_transfer=inventory.cross_border_transfer,
                        recipient_groups=json.dumps(inventory.recipient_groups),
                        recorded_at=inventory.recorded_at,
                    )
                )
                audit_outbox.stage(audit_event, session=session)
            except IntegrityError as exc:
                raise ValidationError("Processing inventory version must be unique.") from exc
        return inventory

    def _insert_metadata_discovery_result(
        self,
        session: Session,
        t: DataSourceTables,
        result: MetadataDiscoveryResult,
    ) -> None:
        session.execute(
            insert(t.metadata_discovery).values(
                data_source_id=result.data_source_id,
                succeeded=result.succeeded,
                duration_ms=result.duration_ms,
                scanned_object_count=result.scanned_object_count,
                error_class=result.error_class.value if result.error_class else None,
                message=result.message,
                changes=json.dumps([metadata_change_to_dict(c) for c in result.changes]),
                discovered_at=result.discovered_at,
                status=result.status.value,
                job_id=result.job_id,
                requested_by_actor_id=result.requested_by_actor_id,
                correlation_id=result.correlation_id,
                scope_version=result.scope_version,
                completed_scope=json.dumps(result.completed_scope),
                partial_reason_code=result.partial_reason_code,
                started_at=result.started_at,
                finished_at=result.finished_at,
            )
        )

    # ------------------------------------------------------------------
    # DS-04: async discovery lifecycle
    # ------------------------------------------------------------------

    def record_discovery_request(
        self,
        result: MetadataDiscoveryResult,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: PostgreSQLTransactionalAudit,
    ) -> MetadataDiscoveryResult:
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            db_result = session.execute(
                insert(t.metadata_discovery).values(
                    data_source_id=result.data_source_id,
                    succeeded=result.succeeded,
                    duration_ms=result.duration_ms,
                    scanned_object_count=result.scanned_object_count,
                    error_class=result.error_class.value if result.error_class else None,
                    message=result.message,
                    changes=json.dumps([]),
                    discovered_at=result.discovered_at,
                    status=DiscoveryStatus.QUEUED.value,
                    job_id=result.job_id,
                    requested_by_actor_id=result.requested_by_actor_id,
                    correlation_id=result.correlation_id,
                    scope_version=result.scope_version,
                    completed_scope=json.dumps(result.completed_scope),
                    partial_reason_code=None,
                    started_at=None,
                    finished_at=None,
                )
            )
            discovery_id = db_result.inserted_primary_key[0]  # type: ignore[attr-defined]
            audit_outbox.stage(audit_event, session=session)
        return MetadataDiscoveryResult(
            **{**vars(result), "discovery_id": discovery_id, "status": DiscoveryStatus.QUEUED}
        )

    def update_discovery_status(
        self,
        discovery_id: int,
        *,
        status: str,
        expected_version: int,
        finished_at: datetime | None = None,
        partial_reason_code: str | None = None,
        completed_scope: dict[str, Any] | None = None,
        scanned_object_count: int | None = None,
        error_class: str | None = None,
        message: str | None = None,
        audit_event: PreparedAuditEvent,
        audit_outbox: PostgreSQLTransactionalAudit,
    ) -> MetadataDiscoveryResult:
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            values: dict[str, Any] = {
                "status": status,
                "version": expected_version + 1,
            }
            if finished_at is not None:
                values["finished_at"] = finished_at
            if partial_reason_code is not None:
                values["partial_reason_code"] = partial_reason_code
            if completed_scope is not None:
                values["completed_scope"] = json.dumps(completed_scope)
            if scanned_object_count is not None:
                values["scanned_object_count"] = scanned_object_count
            if error_class is not None:
                values["error_class"] = error_class
            if message is not None:
                values["message"] = message
            if status == DiscoveryStatus.RUNNING.value:
                values["started_at"] = finished_at or func.now()
            succeeded = status in (DiscoveryStatus.SUCCESS.value, DiscoveryStatus.PARTIAL.value)
            values["succeeded"] = succeeded
            result = session.execute(
                update(t.metadata_discovery)
                .where(
                    and_(
                        t.metadata_discovery.c.discovery_id == discovery_id,
                        t.metadata_discovery.c.version == expected_version,
                    )
                )
                .values(**values)
            )
            if result.rowcount == 0:  # type: ignore[attr-defined]
                raise ConflictError("Discovery version conflict.")
            audit_outbox.stage(audit_event, session=session)
            row = (
                session.execute(
                    select(t.metadata_discovery).where(
                        t.metadata_discovery.c.discovery_id == discovery_id
                    )
                )
                .mappings()
                .one()
            )
        return _row_to_discovery_result(row)

    def get_discovery_result(self, discovery_id: int) -> MetadataDiscoveryResult:
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            row = (
                session.execute(
                    select(t.metadata_discovery).where(
                        t.metadata_discovery.c.discovery_id == discovery_id
                    )
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            raise NotFoundError(f"Discovery {discovery_id} not found.")
        return _row_to_discovery_result(row)

    def get_discovery_result_by_job(self, job_id: str) -> MetadataDiscoveryResult:
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            row = (
                session.execute(
                    select(t.metadata_discovery).where(t.metadata_discovery.c.job_id == job_id)
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            raise NotFoundError(f"Discovery for job {job_id} not found.")
        return _row_to_discovery_result(row)

    # ------------------------------------------------------------------
    # DS-04: discovery scope
    # ------------------------------------------------------------------

    def get_discovery_scope(self, data_source_id: str) -> DiscoveryScope | None:
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            row = (
                session.execute(
                    select(t.discovery_scopes).where(
                        t.discovery_scopes.c.data_source_id == data_source_id
                    )
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            return None
        return _row_to_discovery_scope(row)

    def update_discovery_scope(
        self,
        scope: DiscoveryScope,
        *,
        expected_version: int,
        audit_event: PreparedAuditEvent,
        audit_outbox: PostgreSQLTransactionalAudit,
    ) -> DiscoveryScope:
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            values = {
                "include_patterns": json.dumps(list(scope.include_patterns)),
                "exclude_patterns": json.dumps(list(scope.exclude_patterns)),
                "page_size": scope.page_size,
                "max_objects": scope.max_objects,
                "timeout_seconds": scope.timeout_seconds,
                "policy_version": scope.policy_version,
                "updated_by_actor_id": scope.updated_by_actor_id,
                "updated_at": scope.updated_at,
                "version": expected_version + 1,
            }
            existing = self.get_discovery_scope(scope.data_source_id)
            if existing is None:
                try:
                    session.execute(
                        insert(t.discovery_scopes).values(
                            data_source_id=scope.data_source_id,
                            **values,
                        )
                    )
                except IntegrityError as exc:
                    raise ConflictError("Discovery scope conflict.") from exc
            else:
                result = session.execute(
                    update(t.discovery_scopes)
                    .where(
                        and_(
                            t.discovery_scopes.c.data_source_id == scope.data_source_id,
                            t.discovery_scopes.c.version == expected_version,
                        )
                    )
                    .values(**values)
                )
                if result.rowcount == 0:  # type: ignore[attr-defined]
                    raise ConflictError("Discovery scope version conflict.")
            audit_outbox.stage(audit_event, session=session)
        return DiscoveryScope(
            data_source_id=scope.data_source_id,
            include_patterns=scope.include_patterns,
            exclude_patterns=scope.exclude_patterns,
            page_size=scope.page_size,
            max_objects=scope.max_objects,
            timeout_seconds=scope.timeout_seconds,
            policy_version=scope.policy_version,
            updated_by_actor_id=scope.updated_by_actor_id,
            updated_at=scope.updated_at,
            version=expected_version + 1,
        )

    # ------------------------------------------------------------------
    # DS-04: metadata diff
    # ------------------------------------------------------------------

    def persist_metadata_diff(
        self,
        diff: MetadataDiff,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: PostgreSQLTransactionalAudit,
    ) -> MetadataDiff:
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            session.execute(
                insert(t.metadata_diffs).values(
                    metadata_diff_id=diff.metadata_diff_id,
                    discovery_id=diff.discovery_id,
                    data_source_id=diff.data_source_id,
                    added_objects=json.dumps([dict(o) for o in diff.added_objects]),
                    changed_objects=json.dumps([dict(o) for o in diff.changed_objects]),
                    removed_objects=json.dumps([dict(o) for o in diff.removed_objects]),
                    status=diff.status.value,
                    requires_rule_review=diff.requires_rule_review,
                    created_at=diff.created_at,
                    applied_at=diff.applied_at,
                    applied_by_actor_id=diff.applied_by_actor_id,
                )
            )
            audit_outbox.stage(audit_event, session=session)
        return diff

    def get_metadata_diff(self, metadata_diff_id: str) -> MetadataDiff:
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            row = (
                session.execute(
                    select(t.metadata_diffs).where(
                        t.metadata_diffs.c.metadata_diff_id == metadata_diff_id
                    )
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            raise NotFoundError(f"MetadataDiff {metadata_diff_id} not found.")
        return _row_to_metadata_diff(row)

    def get_diff_by_discovery(self, discovery_id: int) -> MetadataDiff | None:
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            row = (
                session.execute(
                    select(t.metadata_diffs).where(t.metadata_diffs.c.discovery_id == discovery_id)
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            return None
        return _row_to_metadata_diff(row)

    def list_pending_diffs(self, data_source_id: str) -> list[MetadataDiff]:
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            rows = (
                session.execute(
                    select(t.metadata_diffs)
                    .where(
                        and_(
                            t.metadata_diffs.c.data_source_id == data_source_id,
                            t.metadata_diffs.c.status == MetadataDiffStatus.PENDING.value,
                        )
                    )
                    .order_by(t.metadata_diffs.c.created_at)
                )
                .mappings()
                .all()
            )
        return [_row_to_metadata_diff(row) for row in rows]

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
        audit_event: PreparedAuditEvent,
        audit_outbox: PostgreSQLTransactionalAudit,
    ) -> MetadataDiff:
        now = datetime.now(__import__("datetime").timezone.utc)
        with transactional_session(self.session_factory) as session:
            t = self._s(session)
            diff_result = session.execute(
                update(t.metadata_diffs)
                .where(
                    and_(
                        t.metadata_diffs.c.metadata_diff_id == metadata_diff_id,
                        t.metadata_diffs.c.version == expected_version,
                        t.metadata_diffs.c.status == MetadataDiffStatus.PENDING.value,
                    )
                )
                .values(
                    status=MetadataDiffStatus.APPLIED.value,
                    applied_at=now,
                    applied_by_actor_id=applied_by_actor_id,
                    version=expected_version + 1,
                )
            )
            if diff_result.rowcount == 0:  # type: ignore[attr-defined]
                raise ConflictError("Metadata diff version conflict or already applied.")
            for dataset in datasets:
                existing = session.execute(
                    select(t.datasets.c.dataset_id).where(
                        t.datasets.c.dataset_id == dataset.dataset_id
                    )
                ).scalar_one_or_none()
                if existing is not None:
                    session.execute(
                        update(t.datasets)
                        .where(t.datasets.c.dataset_id == dataset.dataset_id)
                        .values(
                            namespace=dataset.namespace,
                            name=dataset.name,
                            dataset_type=dataset.dataset_type.value,
                            estimated_row_count=dataset.estimated_row_count,
                            status=CatalogItemStatus.ACTIVE.value,
                            updated_at=now,
                            version=t.datasets.c.version + 1,
                        )
                    )
                else:
                    session.execute(
                        insert(t.datasets).values(
                            dataset_id=dataset.dataset_id,
                            data_source_id=dataset.data_source_id,
                            namespace=dataset.namespace,
                            name=dataset.name,
                            dataset_type=dataset.dataset_type.value,
                            criticality=dataset.criticality.value,
                            owner_user_id=dataset.owner_user_id,
                            estimated_row_count=dataset.estimated_row_count,
                            status=CatalogItemStatus.ACTIVE.value,
                            updated_at=now,
                            version=1,
                        )
                    )
                for field in fields_by_dataset_id.get(dataset.dataset_id, []):
                    existing_field = session.execute(
                        select(t.fields.c.data_field_id).where(
                            t.fields.c.data_field_id == field.data_field_id
                        )
                    ).scalar_one_or_none()
                    if existing_field is not None:
                        session.execute(
                            update(t.fields)
                            .where(t.fields.c.data_field_id == field.data_field_id)
                            .values(
                                name=field.name,
                                native_data_type=field.native_data_type,
                                is_nullable=field.is_nullable,
                                is_sensitive=field.is_sensitive,
                                classification=field.classification.value,
                                classification_policy_version=field.classification_policy_version,
                                status=CatalogItemStatus.ACTIVE.value,
                                updated_at=now,
                                version=t.fields.c.version + 1,
                            )
                        )
                    else:
                        session.execute(
                            insert(t.fields).values(
                                data_field_id=field.data_field_id,
                                dataset_id=field.dataset_id,
                                name=field.name,
                                native_data_type=field.native_data_type,
                                is_nullable=field.is_nullable,
                                is_sensitive=field.is_sensitive,
                                classification=field.classification.value,
                                classification_policy_version=field.classification_policy_version,
                                status=CatalogItemStatus.ACTIVE.value,
                                updated_at=now,
                                version=1,
                            )
                        )
            if passivated_dataset_ids:
                session.execute(
                    update(t.datasets)
                    .where(t.datasets.c.dataset_id.in_(passivated_dataset_ids))
                    .values(
                        status=CatalogItemStatus.INACTIVE.value,
                        updated_at=now,
                        version=t.datasets.c.version + 1,
                    )
                )
            if passivated_field_ids:
                session.execute(
                    update(t.fields)
                    .where(t.fields.c.data_field_id.in_(passivated_field_ids))
                    .values(
                        status=CatalogItemStatus.INACTIVE.value,
                        updated_at=now,
                        version=t.fields.c.version + 1,
                    )
                )
            audit_outbox.stage(audit_event, session=session)
            row = (
                session.execute(
                    select(t.metadata_diffs).where(
                        t.metadata_diffs.c.metadata_diff_id == metadata_diff_id
                    )
                )
                .mappings()
                .one()
            )
        return _row_to_metadata_diff(row)


# ------------------------------------------------------------------
# Row mapping helpers
# ------------------------------------------------------------------


def _constraint_name(error: IntegrityError) -> str | None:
    diagnostic = getattr(error.orig, "diag", None)
    value = getattr(diagnostic, "constraint_name", None)
    return str(value) if value is not None else None


def _row_to_data_source(row: RowMapping) -> DataSource:
    return DataSource(
        data_source_id=row["data_source_id"],
        name=row["name"],
        source_type=SourceType(row["source_type"]),
        connection_config=_json_load(row["connection_config"]),
        secret_reference=row["secret_reference"],
        owner_user_id=row["owner_user_id"],
        status=DataSourceStatus(row["status"]),
        revision=row["revision"],
        last_test_at=row["last_test_at"],
        created_at=row["created_at"],
    )


def _row_to_connection_test(row: RowMapping) -> ConnectionTestResult:
    return ConnectionTestResult(
        data_source_id=row["data_source_id"],
        succeeded=bool(row["succeeded"]),
        duration_ms=row["duration_ms"],
        error_class=ErrorClass(row["error_class"]) if row["error_class"] else None,
        message=row["message"],
        source_info=_json_load(row["source_info"]),
        data_source_revision=row["data_source_revision"],
        tested_at=row["tested_at"],
    )


def _row_to_connection_revision(row: RowMapping) -> DataSourceConnectionRevision:
    return DataSourceConnectionRevision(
        connection_revision_id=row["connection_revision_id"],
        data_source_id=row["data_source_id"],
        revision=row["revision"],
        base_revision=row["base_revision"],
        connection_config=_json_load(row["connection_config"]),
        secret_reference=row["secret_reference"],
        prepared_by_actor_id=row["prepared_by_actor_id"],
        policy_version=row["policy_version"],
        reason_code=row["reason_code"],
        status=ConnectionRevisionStatus(row["status"]),
        created_at=row["created_at"],
        tested_at=row["tested_at"],
    )


def _row_to_activation_request(row: RowMapping) -> DataSourceActivationRequest:
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


def _row_to_dataset(row: RowMapping) -> Dataset:
    return Dataset(
        dataset_id=row["dataset_id"],
        data_source_id=row["data_source_id"],
        namespace=row["namespace"],
        name=row["name"],
        dataset_type=DatasetType(row["dataset_type"]),
        criticality=Criticality(row["criticality"]),
        owner_user_id=row["owner_user_id"],
        estimated_row_count=row["estimated_row_count"],
        status=CatalogItemStatus(row.get("status", "ACTIVE") or "ACTIVE"),
        first_seen_discovery_id=row.get("first_seen_discovery_id"),
        last_seen_discovery_id=row.get("last_seen_discovery_id"),
        updated_at=row.get("updated_at")
        or row.get("discovered_at")
        or datetime.now(__import__("datetime").timezone.utc),
        version=row.get("version") or 1,
    )


def _row_to_data_field(row: RowMapping) -> DataField:
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
        updated_at=row.get("updated_at") or datetime.now(__import__("datetime").timezone.utc),
        version=row.get("version") or 1,
    )


def _row_to_data_profile(row: RowMapping) -> DataProfile:
    return DataProfile(
        profile_id=row["profile_id"],
        dataset_id=row["dataset_id"],
        execution_id=row["execution_id"],
        method=ProfileMethod(row["method"]),
        sample_ratio=row["sample_ratio"],
        metrics=_json_load(row["metrics"]),
        status=ProfileStatus(row["status"]),
        duration_ms=row["duration_ms"],
        error_class=ErrorClass(row["error_class"]) if row["error_class"] else None,
        message=row["message"],
        started_at=row["started_at"],
        finished_at=row["finished_at"],
    )


def _row_to_profile_comparison(row: RowMapping) -> ProfileComparison:
    return ProfileComparison(
        comparison_id=row["comparison_id"],
        dataset_id=row["dataset_id"],
        baseline_profile_id=row["baseline_profile_id"],
        current_profile_id=row["current_profile_id"],
        policy_version=row["policy_version"],
        status=ProfileComparisonStatus(row["status"]),
        anomaly_candidate=row["anomaly_candidate"],
        result=_json_load(row["result"]),
        message=row["message"],
        created_at=row["created_at"],
    )


def _row_to_processing_inventory(row: RowMapping) -> DataProcessingInventory:
    return DataProcessingInventory(
        inventory_id=row["inventory_id"],
        data_field_id=row["data_field_id"],
        version_number=row["version_number"],
        processing_purpose=row["processing_purpose"],
        legal_basis_reference=row["legal_basis_reference"],
        data_owner_id=row["data_owner_id"],
        retention_policy_id=row["retention_policy_id"],
        access_role_codes=tuple(_json_load(row["access_role_codes"])),
        cross_border_transfer=bool(row["cross_border_transfer"]),
        recipient_groups=tuple(_json_load(row["recipient_groups"])),
        recorded_at=row["recorded_at"],
    )


def _json_load(value: Any) -> Any:
    if isinstance(value, dict | list):
        return value
    if isinstance(value, str):
        return json.loads(value)
    return value


def _row_to_discovery_result(row: RowMapping) -> MetadataDiscoveryResult:
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
        completed_scope=_json_load(row.get("completed_scope") or {}),
        partial_reason_code=row.get("partial_reason_code"),
        started_at=row.get("started_at"),
        finished_at=row.get("finished_at"),
        version=row.get("version") or 1,
    )


def _row_to_discovery_scope(row: RowMapping) -> DiscoveryScope:
    return DiscoveryScope(
        data_source_id=row["data_source_id"],
        include_patterns=tuple(_json_load(row["include_patterns"])),
        exclude_patterns=tuple(_json_load(row["exclude_patterns"])),
        page_size=row["page_size"],
        max_objects=row["max_objects"],
        timeout_seconds=row["timeout_seconds"],
        policy_version=row["policy_version"],
        updated_by_actor_id=row["updated_by_actor_id"],
        updated_at=row["updated_at"],
        version=row["version"],
    )


def _row_to_metadata_diff(row: RowMapping) -> MetadataDiff:
    return MetadataDiff(
        metadata_diff_id=row["metadata_diff_id"],
        discovery_id=row["discovery_id"],
        data_source_id=row["data_source_id"],
        added_objects=tuple(_json_load(row["added_objects"])),
        changed_objects=tuple(_json_load(row["changed_objects"])),
        removed_objects=tuple(_json_load(row["removed_objects"])),
        status=MetadataDiffStatus(row["status"]),
        requires_rule_review=bool(row["requires_rule_review"]),
        created_at=row["created_at"],
        applied_at=row.get("applied_at"),
        applied_by_actor_id=row.get("applied_by_actor_id"),
        version=row["version"],
    )
