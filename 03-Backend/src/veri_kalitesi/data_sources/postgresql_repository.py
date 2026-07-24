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

from veri_kalitesi.audit import PostgreSQLTransactionalAudit, PreparedAuditEvent
from veri_kalitesi.data_protection import (
    ClassificationCode,
    DataProcessingInventory,
    INVENTORY_REQUIRED_CLASSIFICATIONS,
    InventoryCoverageItem,
    InventoryCoverageTechnicalError,
)
from veri_kalitesi.data_sources.errors import NotFoundError, ValidationError
from veri_kalitesi.data_sources.models import (
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
    ErrorClass,
    MetadataChange,
    MetadataDiscoveryResult,
    ProfileMethod,
    ProfileStatus,
    SourceType,
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
    processing_inventory: Table
    connection_revisions: Table
    activation_requests: Table


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
            "source_type IN ('CSV', 'POSTGRESQL', 'MSSQL', 'ORACLE', 'MYSQL', 'REST_API', 'OTHER')",
            name="ck_ds_source_type",
        ),
        CheckConstraint(
            "status IN ('PASSIVE', 'TEST_SUCCEEDED', 'TEST_FAILED', 'ACTIVE', 'INACTIVE', 'ARCHIVED')",
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
        UniqueConstraint(
            "data_source_id", "namespace", "name", name="uq_ds_datasets_source_ns_name"
        ),
        CheckConstraint(
            "dataset_type IN ('TABLE', 'VIEW', 'FILE', 'API', 'OTHER')",
            name="ck_ds_dataset_type",
        ),
        CheckConstraint(
            "criticality IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="ck_ds_criticality",
        ),
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
        UniqueConstraint("dataset_id", "name", name="uq_ds_fields_dataset_name"),
        CheckConstraint(
            "classification IN ('UNCLASSIFIED', 'PUBLIC', 'INTERNAL', 'CONFIDENTIAL', "
            "'RESTRICTED', 'PERSONAL_DATA', 'SPECIAL_CATEGORY_PERSONAL_DATA', "
            "'CUSTOMER_SECRET', 'BANK_SECRET')",
            name="ck_ds_fields_classification",
        ),
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
        CheckConstraint("method IN ('FULL', 'SAMPLE')", name="ck_ds_profile_method"),
        CheckConstraint(
            "status IN ('COMPLETED', 'FAILED', 'TIMEOUT', 'CANCELLED')",
            name="ck_ds_profile_status",
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
        CheckConstraint(
            "status IN ('PENDING', 'APPROVED', 'REJECTED', 'WITHDRAWN', 'EXPIRED', 'INVALIDATED')",
            name="ck_ds_activation_status",
        ),
    )
    return DataSourceTables(
        sources=sources,
        connection_tests=connection_tests,
        datasets=datasets,
        fields=fields,
        metadata_discovery=metadata_discovery,
        profiles=profiles,
        processing_inventory=processing_inventory,
        connection_revisions=connection_revisions,
        activation_requests=activation_requests,
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
            raise NotFoundError("DataSourceActivationRequest not found.")
        return _row_to_activation_request(row)

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
                raise ValidationError("Data source is no longer eligible for deactivation.")
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
                    )
                )
                audit_outbox.stage(audit_event, session=session)
            except IntegrityError as exc:
                raise ValidationError(
                    "A pending activation request already exists for this data source revision."
                ) from exc
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
                raise ValidationError("Data source activation request is not pending.")
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
                    raise ValidationError(
                        "Data source revision is no longer eligible for activation."
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
                changes=json.dumps([_metadata_change_to_dict(c) for c in result.changes]),
                discovered_at=result.discovered_at,
            )
        )


# ------------------------------------------------------------------
# Row mapping helpers
# ------------------------------------------------------------------


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


def _metadata_change_to_dict(change: MetadataChange) -> dict[str, Any]:
    return {
        "change_type": change.change_type.value,
        "object_type": change.object_type,
        "namespace": change.namespace,
        "dataset_name": change.dataset_name,
        "field_name": change.field_name,
        "old_values": change.old_values,
        "new_values": change.new_values,
        "requires_rule_review": change.requires_rule_review,
        "affected_rule_ids": list(change.affected_rule_ids),
    }


def _json_load(value: Any) -> Any:
    if isinstance(value, dict | list):
        return value
    if isinstance(value, str):
        return json.loads(value)
    return value
