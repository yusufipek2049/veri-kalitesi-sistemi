"""SQLite tabanlı veri kaynağı metadata deposu."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any

from veri_kalitesi.audit import PreparedAuditEvent, SQLiteTransactionalAudit
from veri_kalitesi.data_protection import (
    CLASSIFICATION_POLICY_VERSION,
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
    DataSource,
    DataSourceActivationRequest,
    DataSourceActivationStatus,
    DataSourceConnectionRevision,
    DataSourceStatus,
    DataField,
    Dataset,
    DatasetType,
    ErrorClass,
    MetadataChange,
    MetadataDiscoveryResult,
    DataProfile,
    SourceType,
    ProfileMethod,
    ProfileStatus,
)


class SQLiteDataSourceRepository:
    """DataSource, bağlantı testi sonucu ve audit kayıtlarını saklar."""

    def __init__(self, database: str = ":memory:") -> None:
        self.connection = sqlite3.connect(database)
        self.connection.row_factory = sqlite3.Row
        self._create_schema()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS data_sources (
                data_source_id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                source_type TEXT NOT NULL,
                connection_config TEXT NOT NULL,
                secret_reference TEXT NOT NULL,
                owner_user_id TEXT,
                status TEXT NOT NULL,
                revision INTEGER NOT NULL DEFAULT 1,
                last_test_at TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS connection_test_results (
                test_result_id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_source_id TEXT NOT NULL,
                succeeded INTEGER NOT NULL,
                duration_ms INTEGER NOT NULL,
                error_class TEXT,
                message TEXT NOT NULL,
                source_info TEXT NOT NULL,
                data_source_revision INTEGER NOT NULL DEFAULT 1,
                tested_at TEXT NOT NULL,
                FOREIGN KEY (data_source_id) REFERENCES data_sources(data_source_id)
            );

            CREATE TABLE IF NOT EXISTS audit_records (
                audit_id TEXT PRIMARY KEY,
                actor_id TEXT NOT NULL,
                action TEXT NOT NULL,
                object_type TEXT NOT NULL,
                object_id TEXT NOT NULL,
                result TEXT NOT NULL,
                old_values TEXT NOT NULL,
                new_values TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS datasets (
                dataset_id TEXT PRIMARY KEY,
                data_source_id TEXT NOT NULL,
                namespace TEXT NOT NULL,
                name TEXT NOT NULL,
                dataset_type TEXT NOT NULL,
                criticality TEXT NOT NULL,
                owner_user_id TEXT,
                estimated_row_count INTEGER,
                UNIQUE (data_source_id, namespace, name),
                FOREIGN KEY (data_source_id) REFERENCES data_sources(data_source_id)
            );

            CREATE TABLE IF NOT EXISTS data_fields (
                data_field_id TEXT PRIMARY KEY,
                dataset_id TEXT NOT NULL,
                name TEXT NOT NULL,
                native_data_type TEXT NOT NULL,
                is_nullable INTEGER NOT NULL,
                is_sensitive INTEGER NOT NULL,
                classification TEXT NOT NULL DEFAULT 'UNCLASSIFIED',
                classification_policy_version TEXT NOT NULL
                    DEFAULT 'CLASSIFICATION_POLICY_V1',
                UNIQUE (dataset_id, name),
                FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id)
            );

            CREATE TABLE IF NOT EXISTS metadata_discovery_results (
                discovery_id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_source_id TEXT NOT NULL,
                succeeded INTEGER NOT NULL,
                duration_ms INTEGER NOT NULL,
                scanned_object_count INTEGER NOT NULL,
                error_class TEXT,
                message TEXT NOT NULL,
                changes TEXT NOT NULL,
                discovered_at TEXT NOT NULL,
                FOREIGN KEY (data_source_id) REFERENCES data_sources(data_source_id)
            );

            CREATE TABLE IF NOT EXISTS data_profiles (
                profile_id TEXT PRIMARY KEY,
                dataset_id TEXT NOT NULL,
                execution_id TEXT NOT NULL,
                method TEXT NOT NULL,
                sample_ratio REAL,
                metrics TEXT NOT NULL,
                status TEXT NOT NULL,
                duration_ms INTEGER NOT NULL,
                error_class TEXT,
                message TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT NOT NULL,
                FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id)
            );

            CREATE TABLE IF NOT EXISTS data_processing_inventory_versions (
                inventory_id TEXT PRIMARY KEY,
                data_field_id TEXT NOT NULL,
                version_number INTEGER NOT NULL CHECK (version_number > 0),
                processing_purpose TEXT NOT NULL,
                legal_basis_reference TEXT NOT NULL,
                data_owner_id TEXT NOT NULL,
                retention_policy_id TEXT NOT NULL,
                access_role_codes TEXT NOT NULL,
                cross_border_transfer INTEGER NOT NULL
                    CHECK (cross_border_transfer IN (0, 1)),
                recipient_groups TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                UNIQUE (data_field_id, version_number),
                FOREIGN KEY (data_field_id) REFERENCES data_fields(data_field_id)
            );

            CREATE INDEX IF NOT EXISTS idx_processing_inventory_field_version
            ON data_processing_inventory_versions(data_field_id, version_number DESC);

            CREATE TABLE IF NOT EXISTS data_source_connection_revisions (
                connection_revision_id TEXT PRIMARY KEY,
                data_source_id TEXT NOT NULL,
                revision INTEGER NOT NULL CHECK (revision > 0),
                base_revision INTEGER NOT NULL CHECK (base_revision > 0),
                connection_config TEXT NOT NULL,
                secret_reference TEXT NOT NULL,
                prepared_by_actor_id TEXT NOT NULL,
                policy_version TEXT NOT NULL,
                reason_code TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                tested_at TEXT,
                UNIQUE (data_source_id, revision),
                FOREIGN KEY (data_source_id) REFERENCES data_sources(data_source_id)
            );

            CREATE TABLE IF NOT EXISTS data_source_activation_requests (
                activation_request_id TEXT PRIMARY KEY,
                data_source_id TEXT NOT NULL,
                data_source_revision INTEGER NOT NULL,
                maker_actor_id TEXT NOT NULL,
                checker_actor_id TEXT,
                policy_version TEXT NOT NULL,
                status TEXT NOT NULL,
                decision_reason_code TEXT,
                requested_at TEXT NOT NULL,
                target_at TEXT,
                expires_at TEXT,
                business_calendar_version TEXT,
                decided_at TEXT,
                FOREIGN KEY (data_source_id) REFERENCES data_sources(data_source_id)
            );

            CREATE UNIQUE INDEX IF NOT EXISTS ux_data_source_activation_pending
            ON data_source_activation_requests (data_source_id, data_source_revision)
            WHERE status = 'PENDING';
            """
        )
        self._migrate_data_source_revision()
        self._migrate_connection_test_revision()
        self._migrate_connection_revision_history()
        self._migrate_activation_timing()
        self._migrate_data_field_classification()
        self._create_data_field_classification_guards()

    def _migrate_data_source_revision(self) -> None:
        columns = {
            row["name"]
            for row in self.connection.execute("PRAGMA table_info(data_sources)").fetchall()
        }
        if "revision" not in columns:
            with self.connection:
                self.connection.execute(
                    "ALTER TABLE data_sources ADD COLUMN revision INTEGER NOT NULL DEFAULT 1"
                )

    def _migrate_activation_timing(self) -> None:
        columns = {
            row["name"]
            for row in self.connection.execute(
                "PRAGMA table_info(data_source_activation_requests)"
            ).fetchall()
        }
        with self.connection:
            for name in ("target_at", "expires_at", "business_calendar_version"):
                if name not in columns:
                    self.connection.execute(
                        f"ALTER TABLE data_source_activation_requests ADD COLUMN {name} TEXT"
                    )

    def _migrate_connection_test_revision(self) -> None:
        columns = {
            row["name"]
            for row in self.connection.execute(
                "PRAGMA table_info(connection_test_results)"
            ).fetchall()
        }
        if "data_source_revision" not in columns:
            with self.connection:
                self.connection.execute(
                    """
                    ALTER TABLE connection_test_results
                    ADD COLUMN data_source_revision INTEGER NOT NULL DEFAULT 1
                    """
                )

    def _migrate_connection_revision_history(self) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO data_source_connection_revisions (
                    connection_revision_id, data_source_id, revision, base_revision,
                    connection_config, secret_reference, prepared_by_actor_id,
                    policy_version, reason_code, status, created_at, tested_at
                )
                SELECT
                    'legacy-' || data_source_id || '-' || revision,
                    data_source_id, revision, revision, connection_config,
                    secret_reference, 'SYSTEM_MIGRATION', 'LEGACY_V1',
                    'DATA_SOURCE.LEGACY_MIGRATION', 'PROMOTED', created_at, last_test_at
                FROM data_sources
                WHERE NOT EXISTS (
                    SELECT 1 FROM data_source_connection_revisions revisions
                    WHERE revisions.data_source_id = data_sources.data_source_id
                      AND revisions.revision = data_sources.revision
                )
                """
            )

    def _migrate_data_field_classification(self) -> None:
        columns = {
            row["name"]
            for row in self.connection.execute("PRAGMA table_info(data_fields)").fetchall()
        }
        with self.connection:
            if "classification_policy_version" not in columns:
                self.connection.execute(
                    """
                    ALTER TABLE data_fields
                    ADD COLUMN classification_policy_version TEXT NOT NULL
                    DEFAULT 'CLASSIFICATION_POLICY_V1'
                    """
                )
            approved = tuple(code.value for code in ClassificationCode)
            placeholders = ",".join("?" for _ in approved)
            self.connection.execute(
                f"""
                UPDATE data_fields
                SET classification = ?, classification_policy_version = ?
                WHERE classification IS NULL
                   OR TRIM(classification) = ''
                   OR UPPER(classification) NOT IN ({placeholders})
                """,
                (
                    ClassificationCode.UNCLASSIFIED.value,
                    CLASSIFICATION_POLICY_VERSION,
                    *approved,
                ),
            )
            self.connection.execute(
                """
                UPDATE data_fields
                SET classification = UPPER(classification),
                    classification_policy_version = ?
                """,
                (CLASSIFICATION_POLICY_VERSION,),
            )

    def _create_data_field_classification_guards(self) -> None:
        approved = ", ".join(f"'{code.value}'" for code in ClassificationCode)
        self.connection.executescript(
            f"""
            CREATE TRIGGER IF NOT EXISTS trg_data_fields_classification_insert
            BEFORE INSERT ON data_fields
            WHEN NEW.classification NOT IN ({approved})
            BEGIN
                SELECT RAISE(ABORT, 'unsupported data classification');
            END;

            CREATE TRIGGER IF NOT EXISTS trg_data_fields_classification_update
            BEFORE UPDATE OF classification ON data_fields
            WHEN NEW.classification NOT IN ({approved})
            BEGIN
                SELECT RAISE(ABORT, 'unsupported data classification');
            END;
            """
        )

    def add_data_source(
        self,
        data_source: DataSource,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> DataSource:
        if audit_outbox.connection is not self.connection:
            raise ValidationError("Audit outbox must share the data source transaction.")
        try:
            with self.connection:
                self.connection.execute(
                    """
                    INSERT INTO data_sources (
                        data_source_id, name, source_type, connection_config, secret_reference,
                        owner_user_id, status, revision, last_test_at, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        data_source.data_source_id,
                        data_source.name,
                        data_source.source_type.value,
                        json.dumps(data_source.connection_config, sort_keys=True),
                        data_source.secret_reference,
                        data_source.owner_user_id,
                        data_source.status.value,
                        data_source.revision,
                        _to_text(data_source.last_test_at),
                        _to_text(data_source.created_at),
                    ),
                )
                self.connection.execute(
                    """
                    INSERT INTO data_source_connection_revisions (
                        connection_revision_id, data_source_id, revision, base_revision,
                        connection_config, secret_reference, prepared_by_actor_id,
                        policy_version, reason_code, status, created_at, tested_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"initial-{data_source.data_source_id}-{data_source.revision}",
                        data_source.data_source_id,
                        data_source.revision,
                        data_source.revision,
                        json.dumps(data_source.connection_config, sort_keys=True),
                        data_source.secret_reference,
                        "SYSTEM_CREATE",
                        "INITIAL_V1",
                        "DATA_SOURCE.CREATED",
                        ConnectionRevisionStatus.PROMOTED.value,
                        _to_text(data_source.created_at),
                        _to_text(data_source.last_test_at),
                    ),
                )
                audit_outbox.stage(audit_event)
        except sqlite3.IntegrityError as exc:
            raise ValidationError("DataSource name must be unique.") from exc
        return data_source

    def get_data_source(self, data_source_id: str) -> DataSource:
        row = self.connection.execute(
            "SELECT * FROM data_sources WHERE data_source_id = ?",
            (data_source_id,),
        ).fetchone()
        if row is None:
            raise NotFoundError("DataSource not found.")
        return _row_to_data_source(row)

    def list_data_sources(self, allowed_source_ids: frozenset[str]) -> list[DataSource]:
        """Yetki katmanından gelen kaynak kümesini ada göre deterministik döndürür."""

        if not allowed_source_ids:
            return []
        source_ids = sorted(allowed_source_ids)
        placeholders = ", ".join("?" for _ in source_ids)
        rows = self.connection.execute(
            f"SELECT * FROM data_sources WHERE data_source_id IN ({placeholders}) "
            "ORDER BY name COLLATE NOCASE, data_source_id",
            source_ids,
        ).fetchall()
        return [_row_to_data_source(row) for row in rows]

    def deactivate_data_source(
        self,
        data_source_id: str,
        *,
        expected_revision: int,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> DataSource:
        self._require_shared_audit_transaction(audit_outbox)
        with self.connection:
            cursor = self.connection.execute(
                """
                UPDATE data_sources
                SET status = ?
                WHERE data_source_id = ? AND revision = ? AND status = ?
                """,
                (
                    DataSourceStatus.INACTIVE.value,
                    data_source_id,
                    expected_revision,
                    DataSourceStatus.ACTIVE.value,
                ),
            )
            if cursor.rowcount != 1:
                raise ValidationError("Data source is no longer eligible for deactivation.")
            audit_outbox.stage(audit_event)
        return self.get_data_source(data_source_id)

    def update_connection_test(
        self,
        result: ConnectionTestResult,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> None:
        self._require_shared_audit_transaction(audit_outbox)
        current = self.get_data_source(result.data_source_id)
        status = DataSourceStatus.TEST_FAILED
        if result.succeeded:
            status = (
                DataSourceStatus.ACTIVE
                if current.status is DataSourceStatus.ACTIVE
                else DataSourceStatus.TEST_SUCCEEDED
            )
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO connection_test_results (
                    data_source_id, succeeded, duration_ms, error_class, message, source_info,
                    data_source_revision, tested_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.data_source_id,
                    1 if result.succeeded else 0,
                    result.duration_ms,
                    result.error_class.value if result.error_class else None,
                    result.message,
                    json.dumps(result.source_info, sort_keys=True),
                    result.data_source_revision,
                    _to_text(result.tested_at),
                ),
            )
            self.connection.execute(
                """
                UPDATE data_sources
                SET status = ?, last_test_at = ?
                WHERE data_source_id = ?
                """,
                (status.value, _to_text(result.tested_at), result.data_source_id),
            )
            audit_outbox.stage(audit_event)

    def latest_connection_test(
        self, data_source_id: str, *, data_source_revision: int | None = None
    ) -> ConnectionTestResult | None:
        if data_source_revision is None:
            row = self.connection.execute(
                """
                SELECT * FROM connection_test_results
                WHERE data_source_id = ?
                ORDER BY test_result_id DESC
                LIMIT 1
                """,
                (data_source_id,),
            ).fetchone()
        else:
            row = self.connection.execute(
                """
                SELECT * FROM connection_test_results
                WHERE data_source_id = ? AND data_source_revision = ?
                ORDER BY test_result_id DESC
                LIMIT 1
                """,
                (data_source_id, data_source_revision),
            ).fetchone()
        if row is None:
            return None
        return ConnectionTestResult(
            data_source_id=row["data_source_id"],
            succeeded=bool(row["succeeded"]),
            duration_ms=row["duration_ms"],
            error_class=ErrorClass(row["error_class"]) if row["error_class"] else None,
            message=row["message"],
            source_info=json.loads(row["source_info"]),
            data_source_revision=row["data_source_revision"],
            tested_at=_from_text(row["tested_at"]),
        )

    def next_connection_revision(self, data_source_id: str) -> int:
        row = self.connection.execute(
            """
            SELECT COALESCE(MAX(revision), 0) + 1 AS next_revision
            FROM data_source_connection_revisions
            WHERE data_source_id = ?
            """,
            (data_source_id,),
        ).fetchone()
        return int(row["next_revision"])

    def latest_pending_connection_revision(
        self, data_source_id: str
    ) -> DataSourceConnectionRevision | None:
        row = self.connection.execute(
            """
            SELECT * FROM data_source_connection_revisions
            WHERE data_source_id = ? AND status = ?
            ORDER BY revision DESC
            LIMIT 1
            """,
            (data_source_id, ConnectionRevisionStatus.PENDING_TEST.value),
        ).fetchone()
        return _row_to_connection_revision(row) if row is not None else None

    def add_connection_revision(
        self,
        revision: DataSourceConnectionRevision,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> DataSourceConnectionRevision:
        self._require_shared_audit_transaction(audit_outbox)
        try:
            with self.connection:
                self.connection.execute(
                    """
                    INSERT INTO data_source_connection_revisions (
                        connection_revision_id, data_source_id, revision, base_revision,
                        connection_config, secret_reference, prepared_by_actor_id,
                        policy_version, reason_code, status, created_at, tested_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        revision.connection_revision_id,
                        revision.data_source_id,
                        revision.revision,
                        revision.base_revision,
                        json.dumps(revision.connection_config, sort_keys=True),
                        revision.secret_reference,
                        revision.prepared_by_actor_id,
                        revision.policy_version,
                        revision.reason_code,
                        revision.status.value,
                        _to_text(revision.created_at),
                        _to_text(revision.tested_at),
                    ),
                )
                audit_outbox.stage(audit_event)
        except sqlite3.IntegrityError as exc:
            raise ValidationError("Data source connection revision already exists.") from exc
        return self.get_connection_revision(revision.connection_revision_id)

    def get_connection_revision(self, connection_revision_id: str) -> DataSourceConnectionRevision:
        row = self.connection.execute(
            """
            SELECT * FROM data_source_connection_revisions
            WHERE connection_revision_id = ?
            """,
            (connection_revision_id,),
        ).fetchone()
        if row is None:
            raise NotFoundError("DataSourceConnectionRevision not found.")
        return _row_to_connection_revision(row)

    def count_pending_activation_requests_except(self, data_source_id: str, revision: int) -> int:
        row = self.connection.execute(
            """
            SELECT COUNT(*) AS request_count
            FROM data_source_activation_requests
            WHERE data_source_id = ? AND data_source_revision != ? AND status = ?
            """,
            (data_source_id, revision, DataSourceActivationStatus.PENDING.value),
        ).fetchone()
        return int(row["request_count"])

    def record_connection_revision_test(
        self,
        revision: DataSourceConnectionRevision,
        result: ConnectionTestResult,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> DataSourceConnectionRevision:
        self._require_shared_audit_transaction(audit_outbox)
        if revision.status not in {
            ConnectionRevisionStatus.PROMOTED,
            ConnectionRevisionStatus.TEST_FAILED,
        }:
            raise ValidationError("Connection revision test status is invalid.")
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO connection_test_results (
                    data_source_id, succeeded, duration_ms, error_class, message,
                    source_info, data_source_revision, tested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.data_source_id,
                    1 if result.succeeded else 0,
                    result.duration_ms,
                    result.error_class.value if result.error_class else None,
                    result.message,
                    json.dumps(result.source_info, sort_keys=True),
                    result.data_source_revision,
                    _to_text(result.tested_at),
                ),
            )
            cursor = self.connection.execute(
                """
                UPDATE data_source_connection_revisions
                SET status = ?, tested_at = ?
                WHERE connection_revision_id = ? AND status IN (?, ?)
                """,
                (
                    revision.status.value,
                    _to_text(revision.tested_at),
                    revision.connection_revision_id,
                    ConnectionRevisionStatus.PENDING_TEST.value,
                    ConnectionRevisionStatus.TEST_FAILED.value,
                ),
            )
            if cursor.rowcount != 1:
                raise ValidationError("Connection revision is not testable.")
            if revision.status is ConnectionRevisionStatus.PROMOTED:
                source_cursor = self.connection.execute(
                    """
                    UPDATE data_sources
                    SET connection_config = ?, secret_reference = ?, revision = ?,
                        status = ?, last_test_at = ?
                    WHERE data_source_id = ? AND revision = ? AND status != ?
                    """,
                    (
                        json.dumps(revision.connection_config, sort_keys=True),
                        revision.secret_reference,
                        revision.revision,
                        DataSourceStatus.TEST_SUCCEEDED.value,
                        _to_text(result.tested_at),
                        revision.data_source_id,
                        revision.base_revision,
                        DataSourceStatus.ARCHIVED.value,
                    ),
                )
                if source_cursor.rowcount != 1:
                    raise ValidationError("Connection revision base is stale.")
                self.connection.execute(
                    """
                    UPDATE data_source_activation_requests
                    SET status = ?, decision_reason_code = ?, decided_at = ?
                    WHERE data_source_id = ? AND data_source_revision != ? AND status = ?
                    """,
                    (
                        DataSourceActivationStatus.INVALIDATED.value,
                        "DATA_SOURCE.REVISION_CHANGED",
                        _to_text(result.tested_at),
                        revision.data_source_id,
                        revision.revision,
                        DataSourceActivationStatus.PENDING.value,
                    ),
                )
            audit_outbox.stage(audit_event)
        return self.get_connection_revision(revision.connection_revision_id)

    def add_activation_request(
        self,
        request: DataSourceActivationRequest,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> DataSourceActivationRequest:
        self._require_shared_audit_transaction(audit_outbox)
        try:
            with self.connection:
                self.connection.execute(
                    """
                    INSERT INTO data_source_activation_requests (
                        activation_request_id, data_source_id, data_source_revision,
                        maker_actor_id, checker_actor_id, policy_version, status,
                        decision_reason_code, requested_at, target_at, expires_at,
                        business_calendar_version, decided_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        request.activation_request_id,
                        request.data_source_id,
                        request.data_source_revision,
                        request.maker_actor_id,
                        request.checker_actor_id,
                        request.policy_version,
                        request.status.value,
                        request.decision_reason_code,
                        _to_text(request.requested_at),
                        _to_text(request.target_at),
                        _to_text(request.expires_at),
                        request.business_calendar_version,
                        _to_text(request.decided_at),
                    ),
                )
                audit_outbox.stage(audit_event)
        except sqlite3.IntegrityError as exc:
            raise ValidationError(
                "A pending activation request already exists for this data source revision."
            ) from exc
        return self.get_activation_request(request.activation_request_id)

    def get_activation_request(self, activation_request_id: str) -> DataSourceActivationRequest:
        row = self.connection.execute(
            "SELECT * FROM data_source_activation_requests WHERE activation_request_id = ?",
            (activation_request_id,),
        ).fetchone()
        if row is None:
            raise NotFoundError("DataSourceActivationRequest not found.")
        return _row_to_activation_request(row)

    def list_due_activation_requests(self, as_of: datetime) -> list[DataSourceActivationRequest]:
        rows = self.connection.execute(
            """
            SELECT * FROM data_source_activation_requests
            WHERE status = ? AND expires_at IS NOT NULL AND expires_at <= ?
            ORDER BY expires_at, activation_request_id
            """,
            (DataSourceActivationStatus.PENDING.value, _to_text(as_of)),
        ).fetchall()
        return [_row_to_activation_request(row) for row in rows]

    def decide_activation_request(
        self,
        request: DataSourceActivationRequest,
        *,
        activate_source: bool,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> DataSourceActivationRequest:
        self._require_shared_audit_transaction(audit_outbox)
        if request.status not in {
            DataSourceActivationStatus.APPROVED,
            DataSourceActivationStatus.REJECTED,
        }:
            raise ValidationError("Data source activation decision status is invalid.")
        with self.connection:
            cursor = self.connection.execute(
                """
                UPDATE data_source_activation_requests
                SET checker_actor_id = ?, status = ?, decision_reason_code = ?, decided_at = ?
                WHERE activation_request_id = ? AND status = 'PENDING'
                """,
                (
                    request.checker_actor_id,
                    request.status.value,
                    request.decision_reason_code,
                    _to_text(request.decided_at),
                    request.activation_request_id,
                ),
            )
            if cursor.rowcount != 1:
                raise ValidationError("Data source activation request is not pending.")
            if activate_source:
                source_cursor = self.connection.execute(
                    """
                    UPDATE data_sources
                    SET status = ?
                    WHERE data_source_id = ? AND revision = ? AND status IN (?, ?)
                    """,
                    (
                        DataSourceStatus.ACTIVE.value,
                        request.data_source_id,
                        request.data_source_revision,
                        DataSourceStatus.TEST_SUCCEEDED.value,
                        DataSourceStatus.INACTIVE.value,
                    ),
                )
                if source_cursor.rowcount != 1:
                    raise ValidationError(
                        "Data source revision is no longer eligible for activation."
                    )
            audit_outbox.stage(audit_event)
        return self.get_activation_request(request.activation_request_id)

    def withdraw_activation_request(
        self,
        request: DataSourceActivationRequest,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
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
        audit_outbox: SQLiteTransactionalAudit,
    ) -> DataSourceActivationRequest:
        if request.status is not DataSourceActivationStatus.EXPIRED:
            raise ValidationError("Data source activation expiry status is invalid.")
        return self._finish_activation_request(
            request, audit_event=audit_event, audit_outbox=audit_outbox
        )

    def _finish_activation_request(
        self,
        request: DataSourceActivationRequest,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> DataSourceActivationRequest:
        self._require_shared_audit_transaction(audit_outbox)
        with self.connection:
            cursor = self.connection.execute(
                """
                UPDATE data_source_activation_requests
                SET checker_actor_id = NULL, status = ?, decision_reason_code = ?, decided_at = ?
                WHERE activation_request_id = ? AND status = 'PENDING'
                """,
                (
                    request.status.value,
                    request.decision_reason_code,
                    _to_text(request.decided_at),
                    request.activation_request_id,
                ),
            )
            if cursor.rowcount != 1:
                raise ValidationError("Data source activation request is not pending.")
            audit_outbox.stage(audit_event)
        return self.get_activation_request(request.activation_request_id)

    def dump_data_source_storage(self, data_source_id: str) -> dict[str, Any]:
        row = self.connection.execute(
            "SELECT * FROM data_sources WHERE data_source_id = ?",
            (data_source_id,),
        ).fetchone()
        if row is None:
            raise NotFoundError("DataSource not found.")
        return dict(row)

    def list_datasets(self, data_source_id: str) -> list[Dataset]:
        rows = self.connection.execute(
            """
            SELECT * FROM datasets
            WHERE data_source_id = ?
            ORDER BY namespace, name
            """,
            (data_source_id,),
        ).fetchall()
        return [_row_to_dataset(row) for row in rows]

    def list_data_fields(self, dataset_id: str) -> list[DataField]:
        rows = self.connection.execute(
            """
            SELECT * FROM data_fields
            WHERE dataset_id = ?
            ORDER BY name
            """,
            (dataset_id,),
        ).fetchall()
        return [_row_to_data_field(row) for row in rows]

    def get_dataset(self, dataset_id: str) -> Dataset:
        row = self.connection.execute(
            "SELECT * FROM datasets WHERE dataset_id = ?",
            (dataset_id,),
        ).fetchone()
        if row is None:
            raise NotFoundError("Dataset not found.")
        return _row_to_dataset(row)

    def get_data_field(self, data_field_id: str) -> DataField:
        row = self.connection.execute(
            "SELECT * FROM data_fields WHERE data_field_id = ?", (data_field_id,)
        ).fetchone()
        if row is None:
            raise NotFoundError("DataField not found.")
        return _row_to_data_field(row)

    def list_metadata_snapshot(self, data_source_id: str) -> dict[tuple[str, str], list[DataField]]:
        snapshot: dict[tuple[str, str], list[DataField]] = {}
        for dataset in self.list_datasets(data_source_id):
            snapshot[(dataset.namespace, dataset.name)] = self.list_data_fields(dataset.dataset_id)
        return snapshot

    def replace_metadata(
        self,
        data_source_id: str,
        datasets: list[Dataset],
        fields_by_dataset_id: dict[str, list[DataField]],
        result: MetadataDiscoveryResult,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> None:
        self._require_shared_audit_transaction(audit_outbox)
        with self.connection:
            dataset_ids = [
                row["dataset_id"]
                for row in self.connection.execute(
                    "SELECT dataset_id FROM datasets WHERE data_source_id = ?",
                    (data_source_id,),
                ).fetchall()
            ]
            if dataset_ids:
                placeholders = ",".join("?" for _ in dataset_ids)
                self.connection.execute(
                    f"DELETE FROM data_fields WHERE dataset_id IN ({placeholders})",
                    dataset_ids,
                )
            self.connection.execute(
                "DELETE FROM datasets WHERE data_source_id = ?",
                (data_source_id,),
            )

            for dataset in datasets:
                self.connection.execute(
                    """
                    INSERT INTO datasets (
                        dataset_id, data_source_id, namespace, name, dataset_type,
                        criticality, owner_user_id, estimated_row_count
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        dataset.dataset_id,
                        dataset.data_source_id,
                        dataset.namespace,
                        dataset.name,
                        dataset.dataset_type.value,
                        dataset.criticality.value,
                        dataset.owner_user_id,
                        dataset.estimated_row_count,
                    ),
                )
                for field in fields_by_dataset_id.get(dataset.dataset_id, []):
                    self.connection.execute(
                        """
                        INSERT INTO data_fields (
                            data_field_id, dataset_id, name, native_data_type,
                            is_nullable, is_sensitive, classification,
                            classification_policy_version
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            field.data_field_id,
                            field.dataset_id,
                            field.name,
                            field.native_data_type,
                            1 if field.is_nullable else 0,
                            1 if field.is_sensitive else 0,
                            field.classification.value,
                            field.classification_policy_version,
                        ),
                    )
            self._insert_metadata_discovery_result(result)
            audit_outbox.stage(audit_event)

    def record_metadata_discovery_failure(
        self,
        result: MetadataDiscoveryResult,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> None:
        self._require_shared_audit_transaction(audit_outbox)
        with self.connection:
            self._insert_metadata_discovery_result(result)
            audit_outbox.stage(audit_event)

    def add_data_profile(
        self,
        profile: DataProfile,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> DataProfile:
        self._require_shared_audit_transaction(audit_outbox)
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO data_profiles (
                    profile_id, dataset_id, execution_id, method, sample_ratio, metrics,
                    status, duration_ms, error_class, message, started_at, finished_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile.profile_id,
                    profile.dataset_id,
                    profile.execution_id,
                    profile.method.value,
                    profile.sample_ratio,
                    json.dumps(profile.metrics, sort_keys=True),
                    profile.status.value,
                    profile.duration_ms,
                    profile.error_class.value if profile.error_class else None,
                    profile.message,
                    _to_text(profile.started_at),
                    _to_text(profile.finished_at),
                ),
            )
            audit_outbox.stage(audit_event)
        return profile

    def list_data_profiles(self, dataset_id: str) -> list[DataProfile]:
        rows = self.connection.execute(
            """
            SELECT * FROM data_profiles
            WHERE dataset_id = ?
            ORDER BY finished_at, profile_id
            """,
            (dataset_id,),
        ).fetchall()
        return [_row_to_data_profile(row) for row in rows]

    def next_processing_inventory_version(self, data_field_id: str) -> int:
        row = self.connection.execute(
            """
            SELECT MAX(version_number) AS latest_version
            FROM data_processing_inventory_versions
            WHERE data_field_id = ?
            """,
            (data_field_id,),
        ).fetchone()
        return int(row["latest_version"] or 0) + 1

    def add_processing_inventory(
        self,
        inventory: DataProcessingInventory,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> DataProcessingInventory:
        self._require_shared_audit_transaction(audit_outbox)
        try:
            with self.connection:
                self.connection.execute(
                    """
                    INSERT INTO data_processing_inventory_versions (
                        inventory_id, data_field_id, version_number,
                        processing_purpose, legal_basis_reference, data_owner_id,
                        retention_policy_id, access_role_codes, cross_border_transfer,
                        recipient_groups, recorded_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        inventory.inventory_id,
                        inventory.data_field_id,
                        inventory.version_number,
                        inventory.processing_purpose,
                        inventory.legal_basis_reference,
                        inventory.data_owner_id,
                        inventory.retention_policy_id,
                        json.dumps(inventory.access_role_codes),
                        1 if inventory.cross_border_transfer else 0,
                        json.dumps(inventory.recipient_groups),
                        _to_text(inventory.recorded_at),
                    ),
                )
                audit_outbox.stage(audit_event)
        except sqlite3.IntegrityError as exc:
            raise ValidationError("Processing inventory version must be unique.") from exc
        return inventory

    def list_processing_inventory_history(
        self, data_field_id: str
    ) -> list[DataProcessingInventory]:
        rows = self.connection.execute(
            """
            SELECT * FROM data_processing_inventory_versions
            WHERE data_field_id = ?
            ORDER BY version_number
            """,
            (data_field_id,),
        ).fetchall()
        return [_row_to_processing_inventory(row) for row in rows]

    def get_current_processing_inventory(
        self, data_field_id: str
    ) -> DataProcessingInventory | None:
        row = self.connection.execute(
            """
            SELECT * FROM data_processing_inventory_versions
            WHERE data_field_id = ?
            ORDER BY version_number DESC
            LIMIT 1
            """,
            (data_field_id,),
        ).fetchone()
        return _row_to_processing_inventory(row) if row is not None else None

    def list_processing_inventory_coverage(
        self, data_source_id: str | None = None
    ) -> tuple[InventoryCoverageItem, ...]:
        required_classifications = sorted(
            classification.value for classification in INVENTORY_REQUIRED_CLASSIFICATIONS
        )
        try:
            rows = self.connection.execute(
                """
                WITH current_inventory AS (
                    SELECT data_field_id, MAX(version_number) AS version_number
                    FROM data_processing_inventory_versions
                    GROUP BY data_field_id
                )
                SELECT
                    sources.data_source_id,
                    datasets.dataset_id,
                    fields.data_field_id,
                    fields.classification,
                    current_inventory.version_number
                FROM data_fields AS fields
                JOIN datasets ON datasets.dataset_id = fields.dataset_id
                JOIN data_sources AS sources
                    ON sources.data_source_id = datasets.data_source_id
                LEFT JOIN current_inventory
                    ON current_inventory.data_field_id = fields.data_field_id
                WHERE fields.classification IN (?, ?)
                  AND (? IS NULL OR sources.data_source_id = ?)
                ORDER BY
                    sources.data_source_id,
                    datasets.dataset_id,
                    fields.data_field_id
                """,
                (
                    *required_classifications,
                    data_source_id,
                    data_source_id,
                ),
            ).fetchall()
        except sqlite3.Error as exc:
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

    def _insert_metadata_discovery_result(self, result: MetadataDiscoveryResult) -> None:
        self.connection.execute(
            """
            INSERT INTO metadata_discovery_results (
                data_source_id, succeeded, duration_ms, scanned_object_count,
                error_class, message, changes, discovered_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result.data_source_id,
                1 if result.succeeded else 0,
                result.duration_ms,
                result.scanned_object_count,
                result.error_class.value if result.error_class else None,
                result.message,
                json.dumps([_metadata_change_to_dict(change) for change in result.changes]),
                _to_text(result.discovered_at),
            ),
        )

    def _require_shared_audit_transaction(self, audit_outbox: SQLiteTransactionalAudit) -> None:
        if audit_outbox.connection is not self.connection:
            raise ValidationError("Audit outbox must share the data source transaction.")


def _row_to_data_source(row: sqlite3.Row) -> DataSource:
    return DataSource(
        data_source_id=row["data_source_id"],
        name=row["name"],
        source_type=SourceType(row["source_type"]),
        connection_config=json.loads(row["connection_config"]),
        secret_reference=row["secret_reference"],
        owner_user_id=row["owner_user_id"],
        status=DataSourceStatus(row["status"]),
        revision=row["revision"],
        last_test_at=_from_text(row["last_test_at"]) if row["last_test_at"] else None,
        created_at=_from_text(row["created_at"]),
    )


def _row_to_connection_revision(row: sqlite3.Row) -> DataSourceConnectionRevision:
    return DataSourceConnectionRevision(
        connection_revision_id=row["connection_revision_id"],
        data_source_id=row["data_source_id"],
        revision=row["revision"],
        base_revision=row["base_revision"],
        connection_config=json.loads(row["connection_config"]),
        secret_reference=row["secret_reference"],
        prepared_by_actor_id=row["prepared_by_actor_id"],
        policy_version=row["policy_version"],
        reason_code=row["reason_code"],
        status=ConnectionRevisionStatus(row["status"]),
        created_at=_from_text(row["created_at"]),
        tested_at=_from_text(row["tested_at"]) if row["tested_at"] else None,
    )


def _row_to_activation_request(row: sqlite3.Row) -> DataSourceActivationRequest:
    return DataSourceActivationRequest(
        activation_request_id=row["activation_request_id"],
        data_source_id=row["data_source_id"],
        data_source_revision=row["data_source_revision"],
        maker_actor_id=row["maker_actor_id"],
        checker_actor_id=row["checker_actor_id"],
        policy_version=row["policy_version"],
        status=DataSourceActivationStatus(row["status"]),
        decision_reason_code=row["decision_reason_code"],
        requested_at=_from_text(row["requested_at"]),
        target_at=_from_text(row["target_at"]) if row["target_at"] else None,
        expires_at=_from_text(row["expires_at"]) if row["expires_at"] else None,
        business_calendar_version=row["business_calendar_version"],
        decided_at=_from_text(row["decided_at"]) if row["decided_at"] else None,
    )


def _row_to_dataset(row: sqlite3.Row) -> Dataset:
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


def _row_to_data_field(row: sqlite3.Row) -> DataField:
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


def _row_to_data_profile(row: sqlite3.Row) -> DataProfile:
    return DataProfile(
        profile_id=row["profile_id"],
        dataset_id=row["dataset_id"],
        execution_id=row["execution_id"],
        method=ProfileMethod(row["method"]),
        sample_ratio=row["sample_ratio"],
        metrics=json.loads(row["metrics"]),
        status=ProfileStatus(row["status"]),
        duration_ms=row["duration_ms"],
        error_class=ErrorClass(row["error_class"]) if row["error_class"] else None,
        message=row["message"],
        started_at=_from_text(row["started_at"]),
        finished_at=_from_text(row["finished_at"]),
    )


def _row_to_processing_inventory(row: sqlite3.Row) -> DataProcessingInventory:
    return DataProcessingInventory(
        inventory_id=row["inventory_id"],
        data_field_id=row["data_field_id"],
        version_number=row["version_number"],
        processing_purpose=row["processing_purpose"],
        legal_basis_reference=row["legal_basis_reference"],
        data_owner_id=row["data_owner_id"],
        retention_policy_id=row["retention_policy_id"],
        access_role_codes=tuple(json.loads(row["access_role_codes"])),
        cross_border_transfer=bool(row["cross_border_transfer"]),
        recipient_groups=tuple(json.loads(row["recipient_groups"])),
        recorded_at=_from_text(row["recorded_at"]),
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


def _to_text(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _from_text(value: str) -> datetime:
    return datetime.fromisoformat(value)
