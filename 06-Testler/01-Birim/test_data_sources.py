import sqlite3
from pathlib import Path
from typing import cast

import pytest

from veri_kalitesi.audit import (
    AuditEvent,
    AuditFailureMode,
    AuditFailurePolicy,
    AuditRedactor,
    AuditService,
    PreparedAuditEvent,
    SQLiteAuditRepository,
    SQLiteTransactionalAudit,
    build_default_redaction_policy,
)
from veri_kalitesi.data_sources import (
    AuthenticationConnectionError,
    CSVConnector,
    ClassificationCode,
    ConnectorRegistry,
    DNSConnectionError,
    DataSourceService,
    DataSourceStatus,
    ErrorClass,
    InMemorySecretResolver,
    InventoryCoverageStatus,
    InventoryCoverageTechnicalError,
    MetadataChangeType,
    MetadataDatasetCandidate,
    MetadataDiscoveryOptions,
    MetadataFieldCandidate,
    PermissionConnectionError,
    ProfileComputationResult,
    ProfileMethod,
    ProfileOptions,
    ProfileStatus,
    PostgreSQLConnector,
    PostgreSQLProbeResult,
    SQLiteDataSourceRepository,
    TimeoutConnectionError,
)
from veri_kalitesi.data_sources.errors import ValidationError
from veri_kalitesi.data_protection import CLASSIFICATION_POLICY_VERSION


@pytest.fixture
def service() -> DataSourceService:
    repository = SQLiteDataSourceRepository()
    registry = ConnectorRegistry([CSVConnector()])
    return _data_source_service(repository, registry)


def _data_source_service(
    repository: SQLiteDataSourceRepository,
    registry: ConnectorRegistry,
    resolver: InMemorySecretResolver | None = None,
) -> DataSourceService:
    audit_repository = SQLiteAuditRepository()
    redactor = AuditRedactor(build_default_redaction_policy())
    audit_service = AuditService(
        audit_repository,
        redactor,
        AuditFailurePolicy("AUDIT_FAILURE_TEST_V1", AuditFailureMode.FAIL_CLOSED),
    )
    return DataSourceService(
        repository,
        registry,
        resolver,
        audit_sink=audit_service,
        transactional_audit=SQLiteTransactionalAudit(
            repository.connection,
            redactor,
            audit_repository,
            policy_version="AUDIT_OUTBOX_TEST_V1",
        ),
    )


def _audit_events(service: DataSourceService) -> list[AuditEvent]:
    return _audit_repository(service).list_events()


def _audit_repository(service: DataSourceService) -> SQLiteAuditRepository:
    audit_service = cast(AuditService, service.audit_sink)
    repository = cast(SQLiteAuditRepository, audit_service.repository)
    return repository


class FakePostgreSQLDriver:
    def __init__(
        self,
        outcome: Exception | PostgreSQLProbeResult | None = None,
        metadata_outcomes: list[Exception | tuple[MetadataDatasetCandidate, ...]] | None = None,
        profile_outcomes: list[Exception | ProfileComputationResult] | None = None,
    ) -> None:
        self.outcome = outcome or PostgreSQLProbeResult(
            database_name="dq_metadata",
            user_name="readonly_app",
            server_version="PostgreSQL 16.2",
            read_only=True,
        )
        self.metadata_outcomes = metadata_outcomes or []
        self.profile_outcomes = profile_outcomes or []
        self.calls: list[dict[str, object]] = []
        self.metadata_calls: list[dict[str, object]] = []
        self.profile_calls: list[dict[str, object]] = []

    def probe(
        self,
        *,
        config: dict[str, object],
        credentials: dict[str, object],
        test_query: str,
        connect_timeout_seconds: int,
        statement_timeout_ms: int,
    ) -> PostgreSQLProbeResult:
        self.calls.append(
            {
                "config": config,
                "credentials": credentials,
                "test_query": test_query,
                "connect_timeout_seconds": connect_timeout_seconds,
                "statement_timeout_ms": statement_timeout_ms,
            }
        )
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome

    def discover_metadata(
        self,
        *,
        config: dict[str, object],
        credentials: dict[str, object],
        scope: dict[str, object],
        page_size: int,
        max_objects: int,
        timeout_seconds: int,
    ) -> tuple[MetadataDatasetCandidate, ...]:
        self.metadata_calls.append(
            {
                "config": config,
                "credentials": credentials,
                "scope": scope,
                "page_size": page_size,
                "max_objects": max_objects,
                "timeout_seconds": timeout_seconds,
            }
        )
        outcome = self.metadata_outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def profile_dataset(
        self,
        *,
        config: dict[str, object],
        credentials: dict[str, object],
        dataset: object,
        fields: tuple[object, ...],
        options: ProfileOptions,
    ) -> ProfileComputationResult:
        self.profile_calls.append(
            {
                "config": config,
                "credentials": credentials,
                "dataset": dataset,
                "fields": fields,
                "options": options,
            }
        )
        outcome = self.profile_outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def postgresql_service(driver: FakePostgreSQLDriver) -> DataSourceService:
    repository = SQLiteDataSourceRepository()
    registry = ConnectorRegistry([CSVConnector(), PostgreSQLConnector(driver)])
    resolver = InMemorySecretResolver(
        {
            "secret://datasources/postgresql-main": {
                "username": "readonly_app",
                "password": "plain-text-test-password",
            }
        }
    )
    return _data_source_service(repository, registry, resolver)


def postgresql_config(**overrides: object) -> dict[str, object]:
    config: dict[str, object] = {
        "host": "postgres.internal",
        "port": 5432,
        "database": "dq_metadata",
        "ssl_mode": "verify-full",
        "connect_timeout_seconds": 3,
        "statement_timeout_ms": 2000,
    }
    config.update(overrides)
    return config


def test_fr_007_uc_002_creates_csv_data_source_with_secret_reference_and_audit(
    service: DataSourceService,
) -> None:
    data_source = service.create_data_source(
        actor_id="user-1",
        name="Musteri CSV",
        source_type="CSV",
        connection_config={"file_path": "/safe/import/customer.csv", "delimiter": ","},
        secret_reference="secret://datasources/customer-csv",
        owner_user_id="owner-1",
        correlation_id="correlation-source-create",
    )

    stored = service.repository.dump_data_source_storage(data_source.data_source_id)
    audits = _audit_events(service)

    assert data_source.status is DataSourceStatus.TEST_PENDING
    assert stored["secret_reference"] == "secret://datasources/customer-csv"
    assert "password" not in str(stored).lower()
    assert audits[-1].action == "DATA_SOURCE_CREATED"
    assert audits[-1].correlation_id == "correlation-source-create"
    assert audits[-1].new_value_summary["status"] == "TEST_PENDING"
    assert audits[-1].redaction_policy_version == "AUDIT_REDACTION_V3"
    assert _audit_repository(service).verify_integrity().valid is True
    legacy_count = service.repository.connection.execute(
        "SELECT COUNT(*) FROM audit_records"
    ).fetchone()[0]
    assert legacy_count == 0


class FailingAuditRepository:
    def append(self, prepared: PreparedAuditEvent) -> AuditEvent:
        raise sqlite3.OperationalError("synthetic audit outage")


def test_fr_077_bfr_aud_004_data_source_creation_is_durably_buffered_on_outage() -> None:
    repository = SQLiteDataSourceRepository()
    failing_repository = FailingAuditRepository()
    redactor = AuditRedactor(build_default_redaction_policy())
    audit_service = AuditService(
        failing_repository,
        redactor,
        AuditFailurePolicy("AUDIT_FAILURE_TEST_V1", AuditFailureMode.FAIL_CLOSED),
    )
    transactional_audit = SQLiteTransactionalAudit(
        repository.connection,
        redactor,
        failing_repository,
        policy_version="AUDIT_OUTBOX_TEST_V1",
    )
    service = DataSourceService(
        repository,
        ConnectorRegistry([CSVConnector()]),
        audit_sink=audit_service,
        transactional_audit=transactional_audit,
    )

    service.create_data_source(
        actor_id="user-1",
        name="Audit Failure CSV",
        source_type="CSV",
        connection_config={"file_path": "/safe/import/audit-failure.csv"},
        secret_reference="secret://datasources/audit-failure",
        correlation_id="correlation-audit-failure",
    )

    stored_count = repository.connection.execute("SELECT COUNT(*) FROM data_sources").fetchone()[0]
    assert stored_count == 1
    pending = transactional_audit.list_pending()
    assert len(pending) == 1
    assert pending[0].correlation_id == "correlation-audit-failure"
    assert "secret://" not in str(pending[0].new_value_summary)

    central_repository = SQLiteAuditRepository()
    transactional_audit.repository = central_repository
    status = transactional_audit.publish_pending()
    duplicate = central_repository.append(pending[0])

    assert status.pending_count == 0
    assert status.published_count == 1
    assert len(central_repository.list_events()) == 1
    assert duplicate.event_id == pending[0].event_id


class FailingStageAudit(SQLiteTransactionalAudit):
    def stage(self, prepared: PreparedAuditEvent) -> None:
        raise sqlite3.OperationalError("synthetic outbox write failure")


def _use_failing_stage(service: DataSourceService) -> None:
    current_audit = service.transactional_audit
    service.transactional_audit = FailingStageAudit(
        service.repository.connection,
        current_audit.redactor,
        current_audit.repository,
        policy_version="AUDIT_OUTBOX_TEST_V1",
    )


def test_bfr_aud_004_outbox_failure_rolls_back_data_source_creation() -> None:
    repository = SQLiteDataSourceRepository()
    central_repository = SQLiteAuditRepository()
    redactor = AuditRedactor(build_default_redaction_policy())
    transactional_audit = FailingStageAudit(
        repository.connection,
        redactor,
        central_repository,
        policy_version="AUDIT_OUTBOX_TEST_V1",
    )
    service = DataSourceService(
        repository,
        ConnectorRegistry([CSVConnector()]),
        audit_sink=AuditService(
            central_repository,
            redactor,
            AuditFailurePolicy("AUDIT_FAILURE_TEST_V1", AuditFailureMode.FAIL_CLOSED),
        ),
        transactional_audit=transactional_audit,
    )

    with pytest.raises(sqlite3.OperationalError, match="outbox write failure"):
        service.create_data_source(
            actor_id="user-1",
            name="Atomic Failure CSV",
            source_type="CSV",
            connection_config={"file_path": "/safe/import/atomic-failure.csv"},
            secret_reference="secret://datasources/atomic-failure",
        )

    stored_count = repository.connection.execute("SELECT COUNT(*) FROM data_sources").fetchone()[0]
    assert stored_count == 0


def test_bfr_aud_004_outbox_failure_rolls_back_connection_test(tmp_path: Path) -> None:
    csv_file = tmp_path / "atomic-connection.csv"
    csv_file.write_text("id\n1\n", encoding="utf-8")
    repository = SQLiteDataSourceRepository()
    service = _data_source_service(repository, ConnectorRegistry([CSVConnector()]))
    data_source = service.create_data_source(
        actor_id="user-1",
        name="Atomic Connection CSV",
        source_type="CSV",
        connection_config={"file_path": str(csv_file)},
        secret_reference="secret://datasources/atomic-connection",
    )
    _use_failing_stage(service)

    with pytest.raises(sqlite3.OperationalError, match="outbox write failure"):
        service.test_connection(actor_id="user-1", data_source_id=data_source.data_source_id)

    assert (
        repository.get_data_source(data_source.data_source_id).status
        is DataSourceStatus.TEST_PENDING
    )
    assert repository.latest_connection_test(data_source.data_source_id) is None


def test_bfr_aud_004_outbox_failure_rolls_back_successful_metadata(tmp_path: Path) -> None:
    csv_file = tmp_path / "atomic-metadata.csv"
    csv_file.write_text("id,name\n1,Ada\n", encoding="utf-8")
    repository = SQLiteDataSourceRepository()
    service = _data_source_service(repository, ConnectorRegistry([CSVConnector()]))
    data_source = service.create_data_source(
        actor_id="user-1",
        name="Atomic Metadata CSV",
        source_type="CSV",
        connection_config={"file_path": str(csv_file)},
        secret_reference="secret://datasources/atomic-metadata",
    )
    service.test_connection(actor_id="user-1", data_source_id=data_source.data_source_id)
    _use_failing_stage(service)

    with pytest.raises(sqlite3.OperationalError, match="outbox write failure"):
        service.discover_metadata(actor_id="user-1", data_source_id=data_source.data_source_id)

    discovery_count = repository.connection.execute(
        "SELECT COUNT(*) FROM metadata_discovery_results"
    ).fetchone()[0]
    assert repository.list_datasets(data_source.data_source_id) == []
    assert discovery_count == 0


def test_bfr_aud_004_outbox_failure_rolls_back_failed_metadata(tmp_path: Path) -> None:
    csv_file = tmp_path / "atomic-metadata-failure.csv"
    csv_file.write_text("id\n1\n", encoding="utf-8")
    repository = SQLiteDataSourceRepository()
    service = _data_source_service(repository, ConnectorRegistry([CSVConnector()]))
    data_source = service.create_data_source(
        actor_id="user-1",
        name="Atomic Metadata Failure CSV",
        source_type="CSV",
        connection_config={"file_path": str(csv_file)},
        secret_reference="secret://datasources/atomic-metadata-failure",
    )
    service.test_connection(actor_id="user-1", data_source_id=data_source.data_source_id)
    service.registry = ConnectorRegistry([])
    _use_failing_stage(service)

    with pytest.raises(sqlite3.OperationalError, match="outbox write failure"):
        service.discover_metadata(actor_id="user-1", data_source_id=data_source.data_source_id)

    discovery_count = repository.connection.execute(
        "SELECT COUNT(*) FROM metadata_discovery_results"
    ).fetchone()[0]
    assert discovery_count == 0


def test_bfr_aud_004_outbox_failure_rolls_back_profile(tmp_path: Path) -> None:
    csv_file = tmp_path / "atomic-profile.csv"
    csv_file.write_text("id\n1\n", encoding="utf-8")
    repository = SQLiteDataSourceRepository()
    service = _data_source_service(repository, ConnectorRegistry([CSVConnector()]))
    data_source = service.create_data_source(
        actor_id="user-1",
        name="Atomic Profile CSV",
        source_type="CSV",
        connection_config={"file_path": str(csv_file)},
        secret_reference="secret://datasources/atomic-profile",
    )
    service.test_connection(actor_id="user-1", data_source_id=data_source.data_source_id)
    discovery = service.discover_metadata(
        actor_id="user-1", data_source_id=data_source.data_source_id
    )
    dataset = discovery.datasets[0]
    _use_failing_stage(service)

    with pytest.raises(sqlite3.OperationalError, match="outbox write failure"):
        service.run_profile(actor_id="user-1", dataset_id=dataset.dataset_id)

    assert repository.list_data_profiles(dataset.dataset_id) == []


def test_fr_077_bfr_aud_004_connection_test_is_durably_buffered_on_outage(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "buffered-connection.csv"
    csv_file.write_text("id\n1\n", encoding="utf-8")
    repository = SQLiteDataSourceRepository()
    service = _data_source_service(repository, ConnectorRegistry([CSVConnector()]))
    data_source = service.create_data_source(
        actor_id="user-1",
        name="Buffered Connection CSV",
        source_type="CSV",
        connection_config={"file_path": str(csv_file)},
        secret_reference="secret://datasources/buffered-connection",
    )
    service.transactional_audit.repository = FailingAuditRepository()

    result = service.test_connection(
        actor_id="user-1",
        data_source_id=data_source.data_source_id,
        correlation_id="correlation-buffered-connection",
    )

    pending = service.transactional_audit.list_pending()
    assert result.succeeded is True
    assert repository.latest_connection_test(data_source.data_source_id) == result
    assert [event.action for event in pending] == ["DATA_SOURCE_CONNECTION_TESTED"]
    assert pending[0].correlation_id == "correlation-buffered-connection"


def test_bfr_aud_002_blank_correlation_is_rejected_before_data_source_write() -> None:
    repository = SQLiteDataSourceRepository()
    service = _data_source_service(repository, ConnectorRegistry([CSVConnector()]))

    with pytest.raises(ValidationError, match="correlation_id"):
        service.create_data_source(
            actor_id="user-1",
            name="Invalid Correlation CSV",
            source_type="CSV",
            connection_config={"file_path": "/safe/import/invalid-correlation.csv"},
            secret_reference="secret://datasources/invalid-correlation",
            correlation_id=" ",
        )

    stored_count = repository.connection.execute("SELECT COUNT(*) FROM data_sources").fetchone()[0]
    assert stored_count == 0


def test_fr_009_uc_002_rejects_raw_secret_fields(service: DataSourceService) -> None:
    with pytest.raises(ValidationError, match="raw secret"):
        service.create_data_source(
            actor_id="user-1",
            name="Gizli CSV",
            source_type="CSV",
            connection_config={
                "file_path": "/safe/import/customer.csv",
                "password": "plain-text-secret",
            },
            secret_reference="secret://datasources/customer-csv",
            owner_user_id="owner-1",
        )


def test_fr_008_uc_003_ac_004_successful_csv_connection_test_is_read_only_and_audited(
    tmp_path: Path,
    service: DataSourceService,
) -> None:
    csv_file = tmp_path / "customers.csv"
    csv_file.write_text("id,name\n1,Ada\n", encoding="utf-8")
    before = csv_file.read_text(encoding="utf-8")
    data_source = service.create_data_source(
        actor_id="user-1",
        name="Calisan CSV",
        source_type="CSV",
        connection_config={"file_path": str(csv_file), "delimiter": ","},
        secret_reference="secret://datasources/working-csv",
        owner_user_id="owner-1",
    )

    result = service.test_connection(actor_id="user-1", data_source_id=data_source.data_source_id)
    stored = service.repository.get_data_source(data_source.data_source_id)
    after = csv_file.read_text(encoding="utf-8")
    audits = _audit_events(service)

    assert result.succeeded is True
    assert result.error_class is None
    assert result.duration_ms >= 0
    assert result.source_info == {
        "source_type": "CSV",
        "column_count": 2,
        "has_sample_row": True,
        "size_bytes": len(before.encode("utf-8")),
    }
    assert before == after
    assert stored.status is DataSourceStatus.TEST_SUCCEEDED
    assert stored.last_test_at is not None
    assert audits[-1].action == "DATA_SOURCE_CONNECTION_TESTED"
    assert str(csv_file) not in str(audits[-1].new_value_summary)


def test_fr_008_uc_003_ac_005_failed_csv_connection_has_classified_error_without_secret(
    service: DataSourceService,
) -> None:
    data_source = service.create_data_source(
        actor_id="user-1",
        name="Eksik CSV",
        source_type="CSV",
        connection_config={"file_path": "/tmp/does-not-exist-for-veri-kalitesi.csv"},
        secret_reference="secret://datasources/missing-csv",
        owner_user_id="owner-1",
    )

    result = service.test_connection(actor_id="user-1", data_source_id=data_source.data_source_id)
    stored = service.repository.get_data_source(data_source.data_source_id)
    latest = service.repository.latest_connection_test(data_source.data_source_id)
    audits = _audit_events(service)

    assert result.succeeded is False
    assert result.error_class is ErrorClass.FILE_NOT_FOUND
    assert stored.status is DataSourceStatus.TEST_FAILED
    assert latest == result
    assert "secret://datasources/missing-csv" not in result.message
    assert "secret://datasources/missing-csv" not in str(audits[-1].new_value_summary)


def test_fr_007_uc_002_creates_postgresql_source_without_storing_raw_secret() -> None:
    driver = FakePostgreSQLDriver()
    service = postgresql_service(driver)

    data_source = service.create_data_source(
        actor_id="user-1",
        name="Ana PostgreSQL",
        source_type="POSTGRESQL",
        connection_config=postgresql_config(),
        secret_reference="secret://datasources/postgresql-main",
        owner_user_id="owner-1",
    )
    stored = service.repository.dump_data_source_storage(data_source.data_source_id)

    assert data_source.status is DataSourceStatus.TEST_PENDING
    assert stored["secret_reference"] == "secret://datasources/postgresql-main"
    assert "plain-text-test-password" not in str(stored)


def test_fr_008_uc_003_ac_004_successful_postgresql_connection_uses_secret_adapter() -> None:
    driver = FakePostgreSQLDriver()
    service = postgresql_service(driver)
    data_source = service.create_data_source(
        actor_id="user-1",
        name="Test PostgreSQL",
        source_type="POSTGRESQL",
        connection_config=postgresql_config(),
        secret_reference="secret://datasources/postgresql-main",
        owner_user_id="owner-1",
    )

    result = service.test_connection(actor_id="user-1", data_source_id=data_source.data_source_id)
    stored = service.repository.get_data_source(data_source.data_source_id)
    audits = _audit_events(service)

    assert result.succeeded is True
    assert result.error_class is None
    assert result.source_info == {
        "source_type": "POSTGRESQL",
        "database_name": "dq_metadata",
        "user_name": "readonly_app",
        "server_version": "PostgreSQL 16.2",
        "ssl_mode": "verify-full",
    }
    assert stored.status is DataSourceStatus.TEST_SUCCEEDED
    assert driver.calls[0]["credentials"] == {
        "username": "readonly_app",
        "password": "plain-text-test-password",
    }
    assert driver.calls[0]["test_query"].lower().startswith("select")
    assert "plain-text-test-password" not in str(result)
    assert "plain-text-test-password" not in str(audits[-1].new_value_summary)
    assert "secret://datasources/postgresql-main" not in str(audits[-1].new_value_summary)


@pytest.mark.parametrize(
    ("driver_error", "expected_error_class"),
    [
        (DNSConnectionError(), ErrorClass.DNS),
        (TimeoutConnectionError(), ErrorClass.TIMEOUT),
        (AuthenticationConnectionError(), ErrorClass.AUTHENTICATION),
    ],
)
def test_fr_008_uc_003_ac_005_postgresql_failures_are_classified_without_secret(
    driver_error: Exception,
    expected_error_class: ErrorClass,
) -> None:
    driver = FakePostgreSQLDriver(driver_error)
    service = postgresql_service(driver)
    data_source = service.create_data_source(
        actor_id="user-1",
        name=f"Arizali PostgreSQL {expected_error_class.value}",
        source_type="POSTGRESQL",
        connection_config=postgresql_config(),
        secret_reference="secret://datasources/postgresql-main",
        owner_user_id="owner-1",
    )

    result = service.test_connection(actor_id="user-1", data_source_id=data_source.data_source_id)
    stored = service.repository.get_data_source(data_source.data_source_id)
    audits = _audit_events(service)

    assert result.succeeded is False
    assert result.error_class is expected_error_class
    assert stored.status is DataSourceStatus.TEST_FAILED
    assert "plain-text-test-password" not in result.message
    assert "plain-text-test-password" not in str(audits[-1].new_value_summary)


def test_nfr_sec_006_ac_006_postgresql_write_test_query_is_rejected_before_driver_call() -> None:
    driver = FakePostgreSQLDriver(PermissionConnectionError())
    service = postgresql_service(driver)

    with pytest.raises(ValidationError, match="read-only"):
        service.create_data_source(
            actor_id="user-1",
            name="Yazan PostgreSQL",
            source_type="POSTGRESQL",
            connection_config=postgresql_config(test_query="DROP TABLE customer"),
            secret_reference="secret://datasources/postgresql-main",
            owner_user_id="owner-1",
        )

    assert driver.calls == []


def test_nfr_sec_003_postgresql_requires_tls_mode() -> None:
    driver = FakePostgreSQLDriver()
    service = postgresql_service(driver)

    with pytest.raises(ValidationError, match="ssl_mode"):
        service.create_data_source(
            actor_id="user-1",
            name="TLS Kapali PostgreSQL",
            source_type="POSTGRESQL",
            connection_config=postgresql_config(ssl_mode="disable"),
            secret_reference="secret://datasources/postgresql-main",
            owner_user_id="owner-1",
        )


def test_fr_011_fr_015_uc_004_csv_metadata_discovery_persists_dataset_fields_and_audit(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "customers.csv"
    csv_file.write_text("id,name,email\n1,Ada,ada@example.invalid\n", encoding="utf-8")
    repository = SQLiteDataSourceRepository()
    service = _data_source_service(repository, ConnectorRegistry([CSVConnector()]))
    data_source = service.create_data_source(
        actor_id="user-1",
        name="Metadata CSV",
        source_type="CSV",
        connection_config={"file_path": str(csv_file), "delimiter": ","},
        secret_reference="secret://datasources/metadata-csv",
        owner_user_id="owner-1",
    )
    service.test_connection(actor_id="user-1", data_source_id=data_source.data_source_id)

    result = service.discover_metadata(actor_id="user-1", data_source_id=data_source.data_source_id)
    datasets = repository.list_datasets(data_source.data_source_id)
    fields = repository.list_data_fields(datasets[0].dataset_id)
    audits = _audit_events(service)

    assert result.succeeded is True
    assert result.scanned_object_count == 4
    assert len(result.datasets) == 1
    assert [field.name for field in fields] == ["email", "id", "name"]
    assert all(field.native_data_type == "TEXT" for field in fields)
    assert {change.change_type for change in result.changes} == {MetadataChangeType.ADDED}
    assert audits[-1].action == "DATA_SOURCE_METADATA_DISCOVERED"
    assert "ada@example.invalid" not in str(result)
    assert "ada@example.invalid" not in str(audits[-1].new_value_summary)


def test_fr_011_uc_004_metadata_discovery_requires_successful_connection() -> None:
    repository = SQLiteDataSourceRepository()
    service = _data_source_service(repository, ConnectorRegistry([CSVConnector()]))
    data_source = service.create_data_source(
        actor_id="user-1",
        name="Test Edilmemis CSV",
        source_type="CSV",
        connection_config={"file_path": "/tmp/not-used.csv", "delimiter": ","},
        secret_reference="secret://datasources/not-tested",
        owner_user_id="owner-1",
    )

    with pytest.raises(ValidationError, match="successful connection"):
        service.discover_metadata(actor_id="user-1", data_source_id=data_source.data_source_id)


def test_fr_022_ac_025_postgresql_metadata_change_requires_rule_review() -> None:
    first_scan = (
        MetadataDatasetCandidate(
            namespace="public",
            name="orders",
            fields=(
                MetadataFieldCandidate("order_id", "BIGINT", is_nullable=False),
                MetadataFieldCandidate("amount", "NUMERIC", is_nullable=False),
            ),
        ),
    )
    second_scan = (
        MetadataDatasetCandidate(
            namespace="public",
            name="orders",
            fields=(
                MetadataFieldCandidate("order_id", "BIGINT", is_nullable=False),
                MetadataFieldCandidate("amount", "TEXT", is_nullable=True),
            ),
        ),
    )
    driver = FakePostgreSQLDriver(metadata_outcomes=[first_scan, second_scan])
    service = postgresql_service(driver)
    data_source = service.create_data_source(
        actor_id="user-1",
        name="Siparis PostgreSQL",
        source_type="POSTGRESQL",
        connection_config=postgresql_config(),
        secret_reference="secret://datasources/postgresql-main",
        owner_user_id="owner-1",
    )
    service.test_connection(actor_id="user-1", data_source_id=data_source.data_source_id)

    service.discover_metadata(actor_id="user-1", data_source_id=data_source.data_source_id)
    result = service.discover_metadata(actor_id="user-1", data_source_id=data_source.data_source_id)

    changed = [
        change
        for change in result.changes
        if change.change_type is MetadataChangeType.CHANGED and change.field_name == "amount"
    ]
    assert len(changed) == 1
    assert changed[0].requires_rule_review is True
    assert changed[0].old_values["native_data_type"] == "NUMERIC"
    assert changed[0].new_values["native_data_type"] == "TEXT"
    assert driver.metadata_calls[-1]["page_size"] == 1000
    assert driver.metadata_calls[-1]["max_objects"] == 100_000
    assert "plain-text-test-password" not in str(result)


def test_fr_011_uc_004_metadata_timeout_is_classified_without_secret() -> None:
    driver = FakePostgreSQLDriver(metadata_outcomes=[TimeoutConnectionError()])
    service = postgresql_service(driver)
    data_source = service.create_data_source(
        actor_id="user-1",
        name="Timeout Metadata PostgreSQL",
        source_type="POSTGRESQL",
        connection_config=postgresql_config(),
        secret_reference="secret://datasources/postgresql-main",
        owner_user_id="owner-1",
    )
    service.test_connection(actor_id="user-1", data_source_id=data_source.data_source_id)

    result = service.discover_metadata(
        actor_id="user-1",
        data_source_id=data_source.data_source_id,
        options=MetadataDiscoveryOptions(timeout_seconds=2),
    )
    audits = _audit_events(service)

    assert result.succeeded is False
    assert result.error_class is ErrorClass.TIMEOUT
    assert "plain-text-test-password" not in result.message
    assert "plain-text-test-password" not in str(audits[-1].new_value_summary)


def test_fr_016_fr_020_uc_004_ac_007_full_csv_profile_computes_basic_metrics(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "scores.csv"
    csv_file.write_text("id,age,score\n1,10,5\n2,,7\n3,30,9\n", encoding="utf-8")
    repository = SQLiteDataSourceRepository()
    service = _data_source_service(repository, ConnectorRegistry([CSVConnector()]))
    data_source = service.create_data_source(
        actor_id="user-1",
        name="Profil CSV",
        source_type="CSV",
        connection_config={"file_path": str(csv_file), "delimiter": ","},
        secret_reference="secret://datasources/profile-csv",
        owner_user_id="owner-1",
    )
    service.test_connection(actor_id="user-1", data_source_id=data_source.data_source_id)
    discovery = service.discover_metadata(
        actor_id="user-1", data_source_id=data_source.data_source_id
    )
    dataset = discovery.datasets[0]

    profile = service.run_profile(actor_id="user-1", dataset_id=dataset.dataset_id)
    stored = repository.list_data_profiles(dataset.dataset_id)
    audits = _audit_events(service)

    assert profile.status is ProfileStatus.COMPLETED
    assert profile.method is ProfileMethod.FULL
    assert profile.sample_ratio is None
    assert profile.metrics["record_count"] == 3
    assert profile.metrics["sampled_count"] == 3
    assert profile.metrics["fields"]["age"]["null_count"] == 1
    assert profile.metrics["fields"]["age"]["distinct_count"] == 2
    assert profile.metrics["fields"]["age"]["min"] == 10.0
    assert profile.metrics["fields"]["age"]["max"] == 30.0
    assert profile.metrics["fields"]["age"]["average"] == 20.0
    assert stored[-1].profile_id == profile.profile_id
    assert audits[-1].action == "DATASET_PROFILE_CREATED"


def test_fr_018_uc_004_csv_profile_computes_duplicate_metrics_for_key_fields(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "orders.csv"
    csv_file.write_text("order_id,line_no,amount\n1,1,10\n1,1,10\n1,2,20\n", encoding="utf-8")
    repository = SQLiteDataSourceRepository()
    service = _data_source_service(repository, ConnectorRegistry([CSVConnector()]))
    data_source = service.create_data_source(
        actor_id="user-1",
        name="Duplicate CSV",
        source_type="CSV",
        connection_config={"file_path": str(csv_file), "delimiter": ","},
        secret_reference="secret://datasources/duplicate-csv",
        owner_user_id="owner-1",
    )
    service.test_connection(actor_id="user-1", data_source_id=data_source.data_source_id)
    discovery = service.discover_metadata(
        actor_id="user-1", data_source_id=data_source.data_source_id
    )

    profile = service.run_profile(
        actor_id="user-1",
        dataset_id=discovery.datasets[0].dataset_id,
        options=ProfileOptions(key_field_names=("order_id", "line_no")),
    )

    assert profile.metrics["duplicates"] == {
        "key_fields": ["order_id", "line_no"],
        "duplicate_group_count": 1,
        "duplicate_record_count": 1,
        "duplicate_ratio": 1 / 3,
    }


def test_fr_016_uc_004_profile_requires_discovered_metadata() -> None:
    repository = SQLiteDataSourceRepository()
    service = _data_source_service(repository, ConnectorRegistry([CSVConnector()]))
    data_source = service.create_data_source(
        actor_id="user-1",
        name="Metadata Yok CSV",
        source_type="CSV",
        connection_config={"file_path": "/tmp/not-used.csv", "delimiter": ","},
        secret_reference="secret://datasources/no-metadata",
        owner_user_id="owner-1",
    )

    with pytest.raises(Exception, match="Dataset not found"):
        service.run_profile(actor_id="user-1", dataset_id=data_source.data_source_id)


def test_fr_018_uc_004_ac_008_postgresql_sample_profile_stores_method_and_ratio() -> None:
    first_scan = (
        MetadataDatasetCandidate(
            namespace="public",
            name="large_orders",
            estimated_row_count=20_000_000,
            fields=(
                MetadataFieldCandidate("order_id", "BIGINT", is_nullable=False),
                MetadataFieldCandidate("amount", "NUMERIC", is_nullable=False),
            ),
        ),
    )
    profile_result = ProfileComputationResult(
        status=ProfileStatus.COMPLETED,
        row_count=20_000_000,
        metrics={
            "record_count": 20_000_000,
            "sampled_count": 20_000,
            "method": "SAMPLE",
            "sample_ratio": 0.001,
            "fields": {
                "amount": {
                    "null_count": 0,
                    "null_ratio": 0.0,
                    "distinct_count": 5000,
                    "distinct_ratio": 0.25,
                    "min": 1.0,
                    "max": 999.0,
                    "average": 120.5,
                }
            },
        },
        message="PostgreSQL aggregate sample profile completed.",
    )
    driver = FakePostgreSQLDriver(
        metadata_outcomes=[first_scan],
        profile_outcomes=[profile_result],
    )
    service = postgresql_service(driver)
    data_source = service.create_data_source(
        actor_id="user-1",
        name="Buyuk PostgreSQL",
        source_type="POSTGRESQL",
        connection_config=postgresql_config(),
        secret_reference="secret://datasources/postgresql-main",
        owner_user_id="owner-1",
    )
    service.test_connection(actor_id="user-1", data_source_id=data_source.data_source_id)
    discovery = service.discover_metadata(
        actor_id="user-1", data_source_id=data_source.data_source_id
    )

    profile = service.run_profile(
        actor_id="user-1",
        dataset_id=discovery.datasets[0].dataset_id,
        options=ProfileOptions(method=ProfileMethod.SAMPLE, sample_ratio=0.001),
    )

    assert profile.status is ProfileStatus.COMPLETED
    assert profile.method is ProfileMethod.SAMPLE
    assert profile.sample_ratio == 0.001
    assert profile.metrics["record_count"] == 20_000_000
    assert profile.metrics["sampled_count"] == 20_000
    assert driver.profile_calls[-1]["options"].method is ProfileMethod.SAMPLE
    assert "plain-text-test-password" not in str(profile)


def test_fr_016_uc_004_profile_timeout_is_stored_as_technical_error_without_secret() -> None:
    first_scan = (
        MetadataDatasetCandidate(
            namespace="public",
            name="orders",
            fields=(MetadataFieldCandidate("order_id", "BIGINT", is_nullable=False),),
        ),
    )
    driver = FakePostgreSQLDriver(
        metadata_outcomes=[first_scan],
        profile_outcomes=[TimeoutConnectionError()],
    )
    service = postgresql_service(driver)
    data_source = service.create_data_source(
        actor_id="user-1",
        name="Profil Timeout PostgreSQL",
        source_type="POSTGRESQL",
        connection_config=postgresql_config(),
        secret_reference="secret://datasources/postgresql-main",
        owner_user_id="owner-1",
    )
    service.test_connection(actor_id="user-1", data_source_id=data_source.data_source_id)
    discovery = service.discover_metadata(
        actor_id="user-1", data_source_id=data_source.data_source_id
    )

    profile = service.run_profile(actor_id="user-1", dataset_id=discovery.datasets[0].dataset_id)
    audits = _audit_events(service)

    assert profile.status is ProfileStatus.TECHNICAL_ERROR
    assert profile.error_class is ErrorClass.TIMEOUT
    assert "plain-text-test-password" not in profile.message
    assert "plain-text-test-password" not in str(audits[-1].new_value_summary)


def test_bfr_data_001_unknown_classification_is_rejected_without_metadata_write() -> None:
    candidates = (
        MetadataDatasetCandidate(
            namespace="public",
            name="customers",
            fields=(
                MetadataFieldCandidate(
                    "customer_id",
                    "BIGINT",
                    is_nullable=False,
                    classification="UNAPPROVED_EXTERNAL_LABEL",
                ),
            ),
        ),
    )
    driver = FakePostgreSQLDriver(metadata_outcomes=[candidates])
    service = postgresql_service(driver)
    data_source = service.create_data_source(
        actor_id="user-1",
        name="Siniflandirma PostgreSQL",
        source_type="POSTGRESQL",
        connection_config=postgresql_config(),
        secret_reference="secret://datasources/postgresql-main",
        owner_user_id="owner-1",
    )
    service.test_connection(actor_id="user-1", data_source_id=data_source.data_source_id)

    with pytest.raises(ValidationError, match="approved policy code"):
        service.discover_metadata(actor_id="user-1", data_source_id=data_source.data_source_id)

    assert service.repository.list_datasets(data_source.data_source_id) == []
    assert all(
        event.action != "DATA_SOURCE_METADATA_DISCOVERED" for event in _audit_events(service)
    )


def test_rule_010_bfr_data_002_003_profile_strips_raw_values_and_keeps_aggregates() -> None:
    candidates = (
        MetadataDatasetCandidate(
            namespace="public",
            name="customers",
            fields=(
                MetadataFieldCandidate(
                    "email",
                    "TEXT",
                    is_sensitive=True,
                    classification="CUSTOMER_SECRET",
                ),
                MetadataFieldCandidate("segment", "TEXT"),
            ),
        ),
    )
    profile_result = ProfileComputationResult(
        status=ProfileStatus.COMPLETED,
        row_count=2,
        metrics={
            "record_count": 2,
            "sampled_count": 2,
            "method": "FULL",
            "sample_ratio": None,
            "fields": {
                "email": {
                    "null_count": 0,
                    "null_ratio": 0.0,
                    "distinct_count": 2,
                    "distinct_ratio": 1.0,
                    "min": "person-zero@example.invalid",
                    "top_values": ["person-one@example.invalid"],
                    "samples": ["person-two@example.invalid"],
                },
                "segment": {
                    "null_count": 0,
                    "null_ratio": 0.0,
                    "distinct_count": 1,
                    "distinct_ratio": 0.5,
                    "pattern_examples": ["retail"],
                },
            },
        },
        message="Synthetic profile completed.",
    )
    driver = FakePostgreSQLDriver(
        metadata_outcomes=[candidates],
        profile_outcomes=[profile_result],
    )
    service = postgresql_service(driver)
    data_source = service.create_data_source(
        actor_id="user-1",
        name="Maskeli PostgreSQL",
        source_type="POSTGRESQL",
        connection_config=postgresql_config(),
        secret_reference="secret://datasources/postgresql-main",
        owner_user_id="owner-1",
    )
    service.test_connection(actor_id="user-1", data_source_id=data_source.data_source_id)
    discovery = service.discover_metadata(
        actor_id="user-1", data_source_id=data_source.data_source_id
    )

    profile = service.run_profile(actor_id="user-1", dataset_id=discovery.datasets[0].dataset_id)
    stored = service.repository.list_data_profiles(discovery.datasets[0].dataset_id)[0]
    fields = {field.name: field for field in discovery.fields}

    assert fields["email"].classification is ClassificationCode.CUSTOMER_SECRET
    assert fields["segment"].classification is ClassificationCode.UNCLASSIFIED
    assert profile.metrics["fields"]["email"]["distinct_count"] == 2
    assert profile.metrics["fields"]["email"]["masked"] is True
    assert profile.metrics["fields"]["segment"]["masked"] is True
    assert profile.metrics["fields"]["email"]["raw_values_included"] is False
    assert "person-one@example.invalid" not in str(profile.metrics)
    assert "person-zero@example.invalid" not in str(profile.metrics)
    assert "min" not in profile.metrics["fields"]["email"]
    assert "person-two@example.invalid" not in str(stored.metrics)
    assert "retail" not in str(stored.metrics)
    assert "top_values" not in str(stored.metrics)
    assert "samples" not in str(stored.metrics)
    assert "pattern_examples" not in str(stored.metrics)
    assert "person-one@example.invalid" not in str(_audit_events(service))


def test_bfr_data_001_legacy_free_text_classification_migrates_fail_closed(
    tmp_path: Path,
) -> None:
    database = tmp_path / "legacy-classification.sqlite"
    connection = sqlite3.connect(database)
    connection.executescript(
        """
        CREATE TABLE data_fields (
            data_field_id TEXT PRIMARY KEY,
            dataset_id TEXT NOT NULL,
            name TEXT NOT NULL,
            native_data_type TEXT NOT NULL,
            is_nullable INTEGER NOT NULL,
            is_sensitive INTEGER NOT NULL,
            classification TEXT,
            UNIQUE (dataset_id, name)
        );
        INSERT INTO data_fields VALUES (
            'field-null', 'dataset-legacy', 'email', 'TEXT', 1, 1, NULL
        );
        INSERT INTO data_fields VALUES (
            'field-free', 'dataset-legacy', 'account', 'TEXT', 1, 1, 'legacy-free-text'
        );
        """
    )
    connection.close()

    repository = SQLiteDataSourceRepository(str(database))
    fields = repository.list_data_fields("dataset-legacy")

    assert len(fields) == 2
    assert all(field.classification is ClassificationCode.UNCLASSIFIED for field in fields)
    assert all(
        field.classification_policy_version == CLASSIFICATION_POLICY_VERSION for field in fields
    )
    stored = repository.connection.execute(
        """
        SELECT classification, classification_policy_version
        FROM data_fields
        ORDER BY data_field_id
        """
    ).fetchall()
    assert {row["classification"] for row in stored} == {"UNCLASSIFIED"}
    with pytest.raises(sqlite3.IntegrityError, match="unsupported data classification"):
        repository.connection.execute(
            "UPDATE data_fields SET classification = 'FREE_TEXT' WHERE data_field_id = ?",
            ("field-null",),
        )
    inventory_columns = {
        row["name"]
        for row in repository.connection.execute(
            "PRAGMA table_info(data_processing_inventory_versions)"
        ).fetchall()
    }
    assert {
        "processing_purpose",
        "legal_basis_reference",
        "data_owner_id",
        "retention_policy_id",
        "access_role_codes",
        "cross_border_transfer",
    }.issubset(inventory_columns)


def test_bfr_data_004_nfr_prv_005_inventory_is_versioned_and_survives_metadata_rescan() -> None:
    candidates = (
        MetadataDatasetCandidate(
            namespace="public",
            name="customers",
            fields=(
                MetadataFieldCandidate(
                    "customer_id",
                    "BIGINT",
                    is_nullable=False,
                    classification="PERSONAL_DATA",
                ),
            ),
        ),
    )
    driver = FakePostgreSQLDriver(metadata_outcomes=[candidates, candidates])
    service = postgresql_service(driver)
    data_source = service.create_data_source(
        actor_id="user-1",
        name="Isleme Envanteri PostgreSQL",
        source_type="POSTGRESQL",
        connection_config=postgresql_config(),
        secret_reference="secret://datasources/postgresql-main",
        owner_user_id="owner-1",
    )
    service.test_connection(actor_id="user-1", data_source_id=data_source.data_source_id)
    first_discovery = service.discover_metadata(
        actor_id="user-1", data_source_id=data_source.data_source_id
    )
    original_field = first_discovery.fields[0]

    first = service.record_processing_inventory(
        actor_id="governance-user-1",
        data_field_id=original_field.data_field_id,
        processing_purpose="PURPOSE.CUSTOMER_QUALITY",
        legal_basis_reference="LEGAL.REF.001",
        data_owner_id="OWNER.REF.001",
        retention_policy_id="RETENTION.REF.001",
        access_role_codes=("ROLE.DATA_STEWARD",),
        cross_border_transfer=False,
        recipient_groups=("GROUP.DATA_GOVERNANCE",),
        correlation_id="correlation-inventory-v1",
    )
    second_discovery = service.discover_metadata(
        actor_id="user-1", data_source_id=data_source.data_source_id
    )
    second = service.record_processing_inventory(
        actor_id="governance-user-2",
        data_field_id=second_discovery.fields[0].data_field_id,
        processing_purpose="PURPOSE.CUSTOMER_QUALITY",
        legal_basis_reference="LEGAL.REF.001",
        data_owner_id="OWNER.REF.001",
        retention_policy_id="RETENTION.REF.002",
        access_role_codes=("ROLE.DATA_STEWARD", "ROLE.DATA_OWNER"),
        cross_border_transfer=True,
        recipient_groups=("GROUP.DATA_GOVERNANCE", "GROUP.RISK"),
        correlation_id="correlation-inventory-v2",
    )

    history = service.repository.list_processing_inventory_history(original_field.data_field_id)
    current = service.repository.get_current_processing_inventory(original_field.data_field_id)
    inventory_audits = [
        event
        for event in _audit_events(service)
        if event.action == "DATA_PROCESSING_INVENTORY_RECORDED"
    ]

    assert second_discovery.fields[0].data_field_id == original_field.data_field_id
    assert [item.version_number for item in history] == [1, 2]
    assert first.version_number == 1
    assert second.version_number == 2
    assert current == second
    assert history[0].retention_policy_id == "RETENTION.REF.001"
    assert history[1].retention_policy_id == "RETENTION.REF.002"
    assert inventory_audits[-1].correlation_id == "correlation-inventory-v2"
    assert inventory_audits[-1].new_value_summary == {
        "inventory_version": 2,
        "classification": "PERSONAL_DATA",
        "cross_border_transfer": True,
        "access_role_count": 2,
        "recipient_group_count": 2,
    }
    assert "PURPOSE.CUSTOMER_QUALITY" not in str(inventory_audits)
    assert "LEGAL.REF.001" not in str(inventory_audits)
    assert "OWNER.REF.001" not in str(inventory_audits)

    with pytest.raises(ValidationError, match="references are invalid"):
        service.record_processing_inventory(
            actor_id="governance-user-2",
            data_field_id=original_field.data_field_id,
            processing_purpose="PURPOSE.CUSTOMER_QUALITY",
            legal_basis_reference="secret://synthetic/not-a-legal-reference",
            data_owner_id="OWNER.REF.001",
            retention_policy_id="RETENTION.REF.002",
            access_role_codes=("ROLE.DATA_STEWARD",),
            cross_border_transfer=False,
        )
    assert (
        len(service.repository.list_processing_inventory_history(original_field.data_field_id)) == 2
    )


def test_bfr_data_004_inventory_validation_is_data_quality_not_technical_error() -> None:
    candidates = (
        MetadataDatasetCandidate(
            namespace="public",
            name="customers",
            fields=(MetadataFieldCandidate("customer_id", "BIGINT"),),
        ),
    )
    driver = FakePostgreSQLDriver(metadata_outcomes=[candidates])
    service = postgresql_service(driver)
    data_source = service.create_data_source(
        actor_id="user-1",
        name="Eksik Sinif Envanteri PostgreSQL",
        source_type="POSTGRESQL",
        connection_config=postgresql_config(),
        secret_reference="secret://datasources/postgresql-main",
        owner_user_id="owner-1",
    )
    service.test_connection(actor_id="user-1", data_source_id=data_source.data_source_id)
    discovery = service.discover_metadata(
        actor_id="user-1", data_source_id=data_source.data_source_id
    )

    with pytest.raises(ValidationError, match="explicitly classified"):
        service.record_processing_inventory(
            actor_id="governance-user-1",
            data_field_id=discovery.fields[0].data_field_id,
            processing_purpose="PURPOSE.CUSTOMER_QUALITY",
            legal_basis_reference="LEGAL.REF.001",
            data_owner_id="OWNER.REF.001",
            retention_policy_id="RETENTION.REF.001",
            access_role_codes=("ROLE.DATA_STEWARD",),
            cross_border_transfer=False,
        )

    assert (
        service.repository.list_processing_inventory_history(discovery.fields[0].data_field_id)
        == []
    )


def test_bfr_data_004_inventory_outbox_failure_rolls_back_new_version() -> None:
    candidates = (
        MetadataDatasetCandidate(
            namespace="public",
            name="customers",
            fields=(
                MetadataFieldCandidate("customer_id", "BIGINT", classification="PERSONAL_DATA"),
            ),
        ),
    )
    driver = FakePostgreSQLDriver(metadata_outcomes=[candidates])
    service = postgresql_service(driver)
    data_source = service.create_data_source(
        actor_id="user-1",
        name="Atomik Envanter PostgreSQL",
        source_type="POSTGRESQL",
        connection_config=postgresql_config(),
        secret_reference="secret://datasources/postgresql-main",
        owner_user_id="owner-1",
    )
    service.test_connection(actor_id="user-1", data_source_id=data_source.data_source_id)
    discovery = service.discover_metadata(
        actor_id="user-1", data_source_id=data_source.data_source_id
    )
    data_field_id = discovery.fields[0].data_field_id
    _use_failing_stage(service)

    with pytest.raises(sqlite3.OperationalError, match="outbox write failure"):
        service.record_processing_inventory(
            actor_id="governance-user-1",
            data_field_id=data_field_id,
            processing_purpose="PURPOSE.CUSTOMER_QUALITY",
            legal_basis_reference="LEGAL.REF.001",
            data_owner_id="OWNER.REF.001",
            retention_policy_id="RETENTION.REF.001",
            access_role_codes=("ROLE.DATA_STEWARD",),
            cross_border_transfer=False,
            recipient_groups=("GROUP.DATA_GOVERNANCE",),
        )

    assert service.repository.list_processing_inventory_history(data_field_id) == []


def test_bfr_data_004_nfr_prv_005_inventory_coverage_reports_missing_and_complete() -> None:
    candidates = (
        MetadataDatasetCandidate(
            namespace="public",
            name="customers",
            fields=(
                MetadataFieldCandidate("customer_id", "BIGINT", classification="PERSONAL_DATA"),
                MetadataFieldCandidate(
                    "health_code",
                    "TEXT",
                    classification="SPECIAL_CATEGORY_PERSONAL_DATA",
                ),
                MetadataFieldCandidate("segment", "TEXT", classification="PUBLIC"),
            ),
        ),
    )
    service = postgresql_service(FakePostgreSQLDriver(metadata_outcomes=[candidates]))
    data_source = service.create_data_source(
        actor_id="user-1",
        name="Envanter Kapsam PostgreSQL",
        source_type="POSTGRESQL",
        connection_config=postgresql_config(),
        secret_reference="secret://datasources/postgresql-main",
    )
    service.test_connection(actor_id="user-1", data_source_id=data_source.data_source_id)
    discovery = service.discover_metadata(
        actor_id="user-1", data_source_id=data_source.data_source_id
    )
    fields = {field.name: field for field in discovery.fields}
    service.record_processing_inventory(
        actor_id="governance-user-1",
        data_field_id=fields["customer_id"].data_field_id,
        processing_purpose="PURPOSE.CUSTOMER_QUALITY",
        legal_basis_reference="LEGAL.REF.001",
        data_owner_id="OWNER.REF.001",
        retention_policy_id="RETENTION.REF.001",
        access_role_codes=("ROLE.DATA_STEWARD",),
        cross_border_transfer=False,
    )

    traced_statements: list[str] = []
    service.repository.connection.set_trace_callback(traced_statements.append)
    incomplete = service.get_processing_inventory_coverage(
        data_source_id=data_source.data_source_id
    )
    service.repository.connection.set_trace_callback(None)

    assert incomplete.status is InventoryCoverageStatus.INCOMPLETE
    assert incomplete.total_required_count == 2
    assert incomplete.complete_count == 1
    assert incomplete.missing_count == 1
    assert {item.data_field_id for item in incomplete.items} == {
        fields["customer_id"].data_field_id,
        fields["health_code"].data_field_id,
    }
    assert [item.issue_code for item in incomplete.items].count("MISSING_CURRENT_INVENTORY") == 1
    assert all(statement.lstrip().upper().startswith("WITH") for statement in traced_statements)
    assert "PURPOSE.CUSTOMER_QUALITY" not in str(incomplete)
    assert "LEGAL.REF.001" not in str(incomplete)

    service.record_processing_inventory(
        actor_id="governance-user-1",
        data_field_id=fields["health_code"].data_field_id,
        processing_purpose="PURPOSE.CUSTOMER_QUALITY",
        legal_basis_reference="LEGAL.REF.002",
        data_owner_id="OWNER.REF.001",
        retention_policy_id="RETENTION.REF.001",
        access_role_codes=("ROLE.DATA_STEWARD",),
        cross_border_transfer=False,
    )
    complete = service.get_processing_inventory_coverage(data_source_id=data_source.data_source_id)

    assert complete.status is InventoryCoverageStatus.COMPLETE
    assert complete.complete_count == 2
    assert complete.missing_count == 0
    assert all(item.inventory_version == 1 for item in complete.items)
    assert all(item.issue_code is None for item in complete.items)


def test_nfr_prv_005_inventory_coverage_distinguishes_empty_required_scope() -> None:
    candidates = (
        MetadataDatasetCandidate(
            namespace="public",
            name="reference_data",
            fields=(MetadataFieldCandidate("code", "TEXT", classification="PUBLIC"),),
        ),
    )
    service = postgresql_service(FakePostgreSQLDriver(metadata_outcomes=[candidates]))
    data_source = service.create_data_source(
        actor_id="user-1",
        name="Envantersiz Kapsam PostgreSQL",
        source_type="POSTGRESQL",
        connection_config=postgresql_config(),
        secret_reference="secret://datasources/postgresql-main",
    )
    service.test_connection(actor_id="user-1", data_source_id=data_source.data_source_id)
    service.discover_metadata(actor_id="user-1", data_source_id=data_source.data_source_id)

    report = service.get_processing_inventory_coverage(data_source_id=data_source.data_source_id)

    assert report.status is InventoryCoverageStatus.NO_REQUIRED_FIELDS
    assert report.total_required_count == 0
    assert report.complete_count == 0
    assert report.missing_count == 0
    assert report.items == ()


def test_bfr_data_004_inventory_coverage_read_failure_is_technical_error() -> None:
    service = postgresql_service(FakePostgreSQLDriver())
    service.repository.connection.close()

    with pytest.raises(
        InventoryCoverageTechnicalError,
        match="coverage could not be read",
    ):
        service.get_processing_inventory_coverage()
