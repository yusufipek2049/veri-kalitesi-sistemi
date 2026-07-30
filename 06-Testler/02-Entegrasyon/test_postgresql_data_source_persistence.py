"""PostgreSQLDataSourceRepository icin PostgreSQL entegrasyon testleri.

Iteration 36D0 — Data sources PostgreSQL migration.
PostgreSQL gerektiren testler DATA_QUALITY_POSTGRES_TEST_URL ortam degiskeni
olmadan atlanir. Issues/postgresql_repository.py sablonunu izler.
"""

from __future__ import annotations

import os
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text

from alembic import command
from alembic.config import Config

from veri_kalitesi.audit import (
    AuditRedactor,
    PostgreSQLTransactionalAudit,
    PreparedAuditEvent,
    build_default_redaction_policy,
)
from veri_kalitesi.audit.models import AuditEventInput, AuditResult
from veri_kalitesi.data_protection import (
    DefaultClassificationPolicy,
    DefaultMaskingPolicy,
)
from veri_kalitesi.data_sources.connectors import CSVConnector, ConnectorRegistry
from veri_kalitesi.data_sources.errors import ValidationError
from veri_kalitesi.data_sources.models import (
    ConnectionRevisionStatus,
    ConnectionTestResult,
    DataSource,
    DataSourceActivationRequest,
    DataSourceActivationStatus,
    DataSourceConnectionRevision,
    DataSourceStatus,
    DataField,
    DataProfile,
    Dataset,
    MetadataDiscoveryResult,
    ProfileComparison,
    ProfileComparisonStatus,
    ProfileAnalysisPolicy,
    ProfileMethod,
    ProfileOptions,
    ProfileStatus,
    ProfileSamplingStrategy,
    OutlierMethod,
    SourceType,
)
from veri_kalitesi.data_sources.profiling import (
    InMemoryProfilePolicyResolver,
    build_profile_contract,
    compare_profile_snapshots,
)
from veri_kalitesi.data_sources.postgresql_repository import (
    PostgreSQLDataSourceRepository,
)
from veri_kalitesi.data_sources.postgresql_driver import SQLAlchemyPostgreSQLDriver
from veri_kalitesi.data_sources.service import DataSourceService
from veri_kalitesi.persistence import (
    DatabaseSettings,
    DEFAULT_SCHEMA_NAME,
    create_session_factory,
)

ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_CFG = ROOT / "05-Veritabani" / "alembic.ini"

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATA_QUALITY_POSTGRES_TEST_URL"),
    reason="Requires DATA_QUALITY_POSTGRES_TEST_URL pointing to a test PostgreSQL database",
)


class _NoopAuditSink:
    def append(self, event: AuditEventInput) -> None:
        del event


@pytest.fixture(scope="module")
def db_settings() -> DatabaseSettings:
    raw_url = os.environ["DATA_QUALITY_POSTGRES_TEST_URL"]
    schema = os.environ.get("DATA_QUALITY_DATABASE_SCHEMA", DEFAULT_SCHEMA_NAME)
    return DatabaseSettings.from_url(raw_url, schema=schema)


@pytest.fixture(scope="module")
def alembic_up_to_date(db_settings: DatabaseSettings) -> None:
    """Tum migration'lari calistir."""
    config = Config(str(ALEMBIC_CFG))
    config.set_main_option("sqlalchemy.url", db_settings.url.render_as_string(hide_password=False))
    config.set_main_option("data_quality_schema", db_settings.schema)
    command.upgrade(config, "head")


@pytest.fixture
def session_factory(db_settings: DatabaseSettings, alembic_up_to_date: None) -> type:
    """Her test icin yeni bir session factory. Tablo yapisi korunur."""
    engine = create_engine(
        db_settings.url.render_as_string(hide_password=False),
        pool_pre_ping=True,
    )
    # Clean all tables before each test
    with engine.begin() as conn:
        for table_name in [
            "profile_comparisons",
            "data_source_activation_requests",
            "data_source_connection_revisions",
            "data_processing_inventory_versions",
            "data_profiles",
            "metadata_discovery_results",
            "data_fields",
            "datasets",
            "connection_test_results",
            "data_sources",
        ]:
            conn.execute(text(f"DELETE FROM {db_settings.schema}.{table_name}"))
    factory = create_session_factory(db_settings, engine=engine)
    return factory


@pytest.fixture
def repository(
    session_factory: type,
    db_settings: DatabaseSettings,
) -> PostgreSQLDataSourceRepository:
    return PostgreSQLDataSourceRepository(session_factory, schema=db_settings.schema)


@pytest.fixture
def audit_outbox(
    session_factory: type,
    db_settings: DatabaseSettings,
) -> PostgreSQLTransactionalAudit:
    from conftest import FakePreparedAuditRepository  # type: ignore[import-untyped]

    redactor = AuditRedactor(build_default_redaction_policy())
    repo = FakePreparedAuditRepository()
    return PostgreSQLTransactionalAudit(
        session_factory=session_factory,
        redactor=redactor,
        repository=repo,
        policy_version="TEST_V1",
        schema=db_settings.schema,
    )


@pytest.fixture
def sample_data_source() -> DataSource:
    return DataSource(
        name="Test PG Source",
        source_type=SourceType.POSTGRESQL,
        connection_config={"host": "localhost", "port": 5432, "database": "test"},
        secret_reference="secret://datasources/test",
        owner_user_id="user-001",
        created_at=datetime.now(timezone.utc),
    )


def _prepare_event(
    audit_outbox: PostgreSQLTransactionalAudit, action: str = "TEST_ACTION"
) -> PreparedAuditEvent:
    event = AuditEventInput(
        actor_id="test-actor",
        actor_type="USER",
        correlation_id=str(uuid4()),
        action=action,
        object_type="DataSource",
        object_id=str(uuid4()),
        result=AuditResult.SUCCESS,
        reason_code="TEST",
        old_values={},
        new_values={"test": True},
        occurred_at=datetime.now(timezone.utc),
    )
    return audit_outbox.prepare(event)


def test_profile_comparison_migration_is_available(
    db_settings: DatabaseSettings,
    alembic_up_to_date: None,
) -> None:
    engine = create_engine(
        db_settings.url.render_as_string(hide_password=False),
        pool_pre_ping=True,
    )
    with engine.connect() as connection:
        columns = {
            row[0]
            for row in connection.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = :schema
                      AND table_name = 'profile_comparisons'
                    """
                ),
                {"schema": db_settings.schema},
            )
        }
    assert {
        "comparison_id",
        "dataset_id",
        "baseline_profile_id",
        "current_profile_id",
        "policy_version",
        "status",
        "anomaly_candidate",
        "result",
        "message",
        "created_at",
    } == columns


def test_dq_cap_001_postgresql_driver_uses_source_aggregates_for_advanced_metrics(
    db_settings: DatabaseSettings,
    alembic_up_to_date: None,
) -> None:
    table_name = "synthetic_dq_cap_001_profile"
    engine = create_engine(
        db_settings.url.render_as_string(hide_password=False),
        pool_pre_ping=True,
    )
    qualified = f'"{db_settings.schema}"."{table_name}"'
    with engine.begin() as connection:
        connection.execute(text(f"DROP TABLE IF EXISTS {qualified}"))
        connection.execute(
            text(f"CREATE TABLE {qualified} (amount NUMERIC NOT NULL, segment TEXT NOT NULL)")
        )
        connection.execute(
            text(
                f"""
                INSERT INTO {qualified} (amount, segment)
                VALUES (1, 'retail'), (2, 'retail'), (3, 'commercial'), (100, 'retail')
                """
            )
        )
    policy = ProfileAnalysisPolicy(
        version="POSTGRES_SOURCE_AGGREGATE_TEST_V1",
        top_n_limit=2,
        high_cardinality_threshold=3,
        advanced_sample_size=8,
        sampling_strategy=ProfileSamplingStrategy.DETERMINISTIC_HASH,
        sampling_seed=20260729,
        enabled_outlier_methods=(OutlierMethod.IQR, OutlierMethod.ROBUST_Z_SCORE),
        iqr_multiplier=1.5,
        robust_z_score_threshold=3.5,
        minimum_numeric_sample=4,
        comparison_window=2,
        minimum_history=2,
        volume_ratio_threshold=0.1,
        null_ratio_delta_threshold=0.1,
        distinct_ratio_delta_threshold=0.1,
        category_loss_ratio_threshold=0.1,
        numeric_mean_ratio_threshold=0.1,
        numeric_median_ratio_threshold=0.1,
        freshness_delay_seconds_threshold=60,
        schema_change_detection_enabled=True,
    )
    dataset = Dataset(
        data_source_id="synthetic-source",
        namespace=db_settings.schema,
        name=table_name,
    )
    fields = (
        DataField(dataset_id=dataset.dataset_id, name="amount", native_data_type="NUMERIC"),
        DataField(dataset_id=dataset.dataset_id, name="segment", native_data_type="TEXT"),
    )
    url = db_settings.url
    try:
        result = SQLAlchemyPostgreSQLDriver().profile_dataset(
            config={
                "host": url.host,
                "port": url.port or 5432,
                "database": url.database,
                "ssl_mode": "disable",
                "connect_timeout_seconds": 5,
                "statement_timeout_ms": 5000,
            },
            credentials={
                "username": url.username,
                "password": url.password,
            },
            dataset=dataset,
            fields=fields,
            options=ProfileOptions(
                method=ProfileMethod.AGGREGATE,
                analysis_policy=policy,
                policy_version=policy.version,
            ),
        )
    finally:
        with engine.begin() as connection:
            connection.execute(text(f"DROP TABLE IF EXISTS {qualified}"))
        engine.dispose()

    assert result.status is ProfileStatus.COMPLETED
    assert result.metrics["analysis_execution"]["method"] == "SOURCE_AGGREGATE"
    assert result.metrics["analysis_execution"]["raw_rows_transferred"] is False
    assert result.metrics["fields"]["segment"]["top_values"][0] == {
        "rank": 1,
        "value": "retail",
        "count": 3,
    }
    assert result.metrics["fields"]["amount"]["numeric_summary"]["median"] == 2.5
    assert {
        item["method"]
        for item in result.metrics["fields"]["amount"]["outlier_candidates"]
    } == {"IQR", "ROBUST_Z_SCORE"}


def test_dq_cap_006_postgresql_freshness_scope_flows_from_aggregate_to_comparison(
    db_settings: DatabaseSettings,
    alembic_up_to_date: None,
) -> None:
    del alembic_up_to_date
    table_name = "synthetic_dq_cap_006_freshness"
    engine = create_engine(
        db_settings.url.render_as_string(hide_password=False),
        pool_pre_ping=True,
    )
    qualified = f'"{db_settings.schema}"."{table_name}"'
    with engine.begin() as connection:
        connection.execute(text(f"DROP TABLE IF EXISTS {qualified}"))
        connection.execute(
            text(
                f"""
                CREATE TABLE {qualified} (
                    observed_at TIMESTAMPTZ NOT NULL,
                    unscoped_at TIMESTAMPTZ NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                f"""
                INSERT INTO {qualified} (observed_at, unscoped_at)
                VALUES
                    ('2026-07-20T11:00:00Z', '2026-07-20T09:00:00Z'),
                    ('2026-07-20T12:00:00Z', '2026-07-20T10:00:00Z')
                """
            )
        )
    policy = ProfileAnalysisPolicy(
        version="POSTGRES_FRESHNESS_SCOPE_TEST_V1",
        top_n_limit=2,
        high_cardinality_threshold=4,
        advanced_sample_size=8,
        sampling_strategy=ProfileSamplingStrategy.DETERMINISTIC_HASH,
        sampling_seed=20260730,
        enabled_outlier_methods=(OutlierMethod.IQR,),
        iqr_multiplier=1.5,
        robust_z_score_threshold=3.5,
        minimum_numeric_sample=2,
        comparison_window=2,
        minimum_history=2,
        volume_ratio_threshold=1.0,
        null_ratio_delta_threshold=1.0,
        distinct_ratio_delta_threshold=1.0,
        category_loss_ratio_threshold=1.0,
        numeric_mean_ratio_threshold=1.0,
        numeric_median_ratio_threshold=1.0,
        freshness_delay_seconds_threshold=3600,
        schema_change_detection_enabled=True,
        freshness_field_names=("observed_at",),
    )
    dataset = Dataset(
        data_source_id="synthetic-freshness-source",
        namespace=db_settings.schema,
        name=table_name,
    )
    fields = (
        DataField(
            dataset_id=dataset.dataset_id,
            name="observed_at",
            native_data_type="TIMESTAMP WITH TIME ZONE",
        ),
        DataField(
            dataset_id=dataset.dataset_id,
            name="unscoped_at",
            native_data_type="TIMESTAMP WITH TIME ZONE",
        ),
    )
    options = ProfileOptions(
        method=ProfileMethod.AGGREGATE,
        analysis_policy=policy,
        policy_version=policy.version,
    )
    url = db_settings.url
    driver = SQLAlchemyPostgreSQLDriver()
    unsafe_policy = replace(
        policy,
        version="POSTGRES_UNSAFE_FRESHNESS_SCOPE_TEST_V1",
        freshness_field_names=("observed_at; DROP TABLE synthetic",),
    )
    with pytest.raises(ValidationError, match="must exist in metadata"):
        driver.profile_dataset(
            config={},
            credentials={},
            dataset=dataset,
            fields=fields,
            options=replace(
                options,
                analysis_policy=unsafe_policy,
                policy_version=unsafe_policy.version,
            ),
        )
    with pytest.raises(ValidationError, match="timezone-safe date/time type"):
        driver.profile_dataset(
            config={},
            credentials={},
            dataset=dataset,
            fields=(replace(fields[0], native_data_type="TEXT"), fields[1]),
            options=options,
        )

    def run_profile(profile_id: str) -> DataProfile:
        result = driver.profile_dataset(
            config={
                "host": url.host,
                "port": url.port or 5432,
                "database": url.database,
                "ssl_mode": "disable",
                "connect_timeout_seconds": 5,
                "statement_timeout_ms": 5000,
            },
            credentials={"username": url.username, "password": url.password},
            dataset=dataset,
            fields=fields,
            options=options,
        )
        metrics = dict(result.metrics)
        metrics["profile_contract"] = build_profile_contract(
            fields=fields,
            method=ProfileMethod.AGGREGATE,
            sample_ratio=None,
            scope={},
            query_version=options.query_version,
            connector_version=options.connector_version,
            policy=policy,
            data_observed_at=None,
            category_fingerprint_algorithm=None,
            category_fingerprint_key_id=None,
            analysis_execution=metrics["analysis_execution"],
        )
        return DataProfile(
            profile_id=profile_id,
            dataset_id=dataset.dataset_id,
            execution_id=f"execution-{profile_id}",
            method=ProfileMethod.AGGREGATE,
            metrics=metrics,
            status=result.status,
        )

    try:
        baseline = run_profile("postgres-freshness-baseline")
        with engine.begin() as connection:
            connection.execute(text(f"TRUNCATE TABLE {qualified}"))
            connection.execute(
                text(
                    f"""
                    INSERT INTO {qualified} (observed_at, unscoped_at)
                    VALUES
                        ('2026-07-20T09:00:00Z', '2026-07-20T06:00:00Z'),
                        ('2026-07-20T10:00:00Z', '2026-07-20T07:00:00Z')
                    """
                )
            )
        current = run_profile("postgres-freshness-current")
    finally:
        with engine.begin() as connection:
            connection.execute(text(f"DROP TABLE IF EXISTS {qualified}"))
        engine.dispose()

    comparison = compare_profile_snapshots(
        baseline=baseline,
        current=current,
        history=(baseline, current),
        policy=policy,
    )
    freshness_signals = [
        signal
        for signal in comparison.result["signals"]
        if signal["kind"] == "FRESHNESS_DELAY"
    ]

    assert baseline.metrics["fields"]["observed_at"]["freshness_max"].endswith("+00:00")
    assert "freshness_max" not in baseline.metrics["fields"]["unscoped_at"]
    assert freshness_signals[0]["field"] == "observed_at"
    assert freshness_signals[0]["delay_seconds"] == 7200.0
    assert freshness_signals[0]["breached"] is True


def test_profile_comparison_repository_persists_with_transactional_audit(
    repository: PostgreSQLDataSourceRepository,
    audit_outbox: PostgreSQLTransactionalAudit,
    sample_data_source: DataSource,
) -> None:
    repository.add_data_source(
        sample_data_source,
        audit_event=_prepare_event(audit_outbox, "DATA_SOURCE_CREATED"),
        audit_outbox=audit_outbox,
    )
    dataset = Dataset(
        dataset_id=str(uuid4()),
        data_source_id=sample_data_source.data_source_id,
        namespace="public",
        name="profile_test",
    )
    field = DataField(
        data_field_id=str(uuid4()),
        dataset_id=dataset.dataset_id,
        name="amount",
        native_data_type="NUMERIC",
    )
    discovery = MetadataDiscoveryResult(
        data_source_id=sample_data_source.data_source_id,
        succeeded=True,
        duration_ms=1,
        datasets=(dataset,),
        fields=(field,),
    )
    repository.replace_metadata(
        sample_data_source.data_source_id,
        [dataset],
        {dataset.dataset_id: [field]},
        discovery,
        audit_event=_prepare_event(audit_outbox, "DATA_SOURCE_METADATA_DISCOVERED"),
        audit_outbox=audit_outbox,
    )
    now = datetime.now(timezone.utc)
    profiles = [
        DataProfile(
            dataset_id=dataset.dataset_id,
            execution_id=str(uuid4()),
            method=ProfileMethod.FULL,
            metrics={"record_count": count},
            status=ProfileStatus.COMPLETED,
            started_at=now,
            finished_at=now,
        )
        for count in (100, 80)
    ]
    for profile in profiles:
        repository.add_data_profile(
            profile,
            audit_event=_prepare_event(audit_outbox, "DATASET_PROFILE_CREATED"),
            audit_outbox=audit_outbox,
        )
    comparison = ProfileComparison(
        dataset_id=dataset.dataset_id,
        baseline_profile_id=profiles[0].profile_id,
        current_profile_id=profiles[1].profile_id,
        policy_version="PROFILE_POLICY_TEST_V1",
        status=ProfileComparisonStatus.COMPLETED,
        anomaly_candidate=True,
        result={"signals": [{"kind": "VOLUME_CHANGE", "breached": True}]},
        created_at=now,
    )

    repository.add_profile_comparison(
        comparison,
        audit_event=_prepare_event(audit_outbox, "DATASET_PROFILES_COMPARED"),
        audit_outbox=audit_outbox,
    )

    assert repository.list_profile_comparisons(dataset.dataset_id) == [comparison]


def test_masked_category_drift_survives_service_reconstruction(
    session_factory: type,
    db_settings: DatabaseSettings,
    audit_outbox: PostgreSQLTransactionalAudit,
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "postgresql-persistent-category-drift.csv"
    csv_file.write_text(
        "segment\nretail\nretail\ncommercial\n",
        encoding="utf-8",
    )
    policy = ProfileAnalysisPolicy(
        version="PROFILE_POLICY_PERSISTENCE_TEST_V1",
        top_n_limit=10,
        high_cardinality_threshold=10,
        advanced_sample_size=20,
        sampling_strategy=ProfileSamplingStrategy.DETERMINISTIC_HASH,
        sampling_seed=20260729,
        enabled_outlier_methods=(OutlierMethod.IQR,),
        iqr_multiplier=1.5,
        robust_z_score_threshold=3.5,
        minimum_numeric_sample=3,
        comparison_window=2,
        minimum_history=2,
        volume_ratio_threshold=1.0,
        null_ratio_delta_threshold=1.0,
        distinct_ratio_delta_threshold=1.0,
        category_loss_ratio_threshold=0.0,
        numeric_mean_ratio_threshold=1.0,
        numeric_median_ratio_threshold=1.0,
        freshness_delay_seconds_threshold=3600.0,
        schema_change_detection_enabled=True,
    )
    fingerprint_key = b"postgresql-stable-fingerprint-key-01"
    fingerprint_key_id = "postgresql-fingerprint-test-v1"

    def build_service() -> DataSourceService:
        classification = DefaultClassificationPolicy()
        return DataSourceService(
            PostgreSQLDataSourceRepository(session_factory, schema=db_settings.schema),
            ConnectorRegistry([CSVConnector()]),
            audit_sink=_NoopAuditSink(),
            transactional_audit=audit_outbox,
            classification_policy=classification,
            masking_policy=DefaultMaskingPolicy(
                classification,
                category_fingerprint_key=fingerprint_key,
                category_fingerprint_key_id=fingerprint_key_id,
            ),
            profile_policy_resolver=InMemoryProfilePolicyResolver(
                (policy,),
                active_version=policy.version,
            ),
        )

    first_service = build_service()
    source = first_service.create_data_source(
        actor_id="user-1",
        name="Persistent Masked Category Drift CSV",
        source_type="CSV",
        connection_config={"file_path": str(csv_file)},
        secret_reference="secret://datasources/persistent-category-drift",
    )
    first_service.test_connection(
        actor_id="user-1",
        data_source_id=source.data_source_id,
    )
    dataset = Dataset(
        data_source_id=source.data_source_id,
        namespace=str(csv_file.parent),
        name=csv_file.name,
    )
    segment = DataField(
        dataset_id=dataset.dataset_id,
        name="segment",
        native_data_type="TEXT",
    )
    first_service.repository.replace_metadata(
        source.data_source_id,
        [dataset],
        {dataset.dataset_id: [segment]},
        MetadataDiscoveryResult(
            data_source_id=source.data_source_id,
            succeeded=True,
            duration_ms=1,
            datasets=(dataset,),
            fields=(segment,),
        ),
        audit_event=_prepare_event(audit_outbox, "DATA_SOURCE_METADATA_DISCOVERED"),
        audit_outbox=audit_outbox,
    )
    baseline = first_service.run_profile(
        actor_id="user-1",
        dataset_id=dataset.dataset_id,
    )

    second_service = build_service()
    csv_file.write_text("segment\nretail\nretail\nretail\n", encoding="utf-8")
    current = second_service.run_profile(
        actor_id="user-1",
        dataset_id=dataset.dataset_id,
    )
    comparison = second_service.compare_profiles(
        actor_id="user-1",
        dataset_id=dataset.dataset_id,
        baseline_profile_id=baseline.profile_id,
        current_profile_id=current.profile_id,
    )

    signals = {signal["kind"]: signal for signal in comparison.result["signals"]}
    assert comparison.status is ProfileComparisonStatus.COMPLETED
    assert comparison.anomaly_candidate is True
    assert signals["CATEGORY_LOSS"]["lost_category_count"] == 1
    assert signals["CATEGORY_LOSS"]["breached"] is True
    assert len(second_service.repository.list_data_profiles(dataset.dataset_id)) == 2
    assert second_service.repository.list_profile_comparisons(dataset.dataset_id) == [
        comparison
    ]
    assert "retail" not in str(baseline.metrics)
    assert "commercial" not in str(baseline.metrics)


def test_add_and_get_data_source(
    repository: PostgreSQLDataSourceRepository,
    audit_outbox: PostgreSQLTransactionalAudit,
    sample_data_source: DataSource,
) -> None:
    """FR-007: Veri kaynagi olusturma ve okuma."""
    prepared = _prepare_event(audit_outbox, "DATA_SOURCE_CREATED")
    stored = repository.add_data_source(
        sample_data_source, audit_event=prepared, audit_outbox=audit_outbox
    )
    assert stored.data_source_id == sample_data_source.data_source_id
    assert stored.status is DataSourceStatus.TEST_PENDING

    retrieved = repository.get_data_source(sample_data_source.data_source_id)
    assert retrieved.name == sample_data_source.name
    assert retrieved.source_type == sample_data_source.source_type


def test_list_data_sources(
    repository: PostgreSQLDataSourceRepository,
    audit_outbox: PostgreSQLTransactionalAudit,
    sample_data_source: DataSource,
) -> None:
    """FR-007: Veri kaynagi listeleme."""
    prepared = _prepare_event(audit_outbox, "DATA_SOURCE_CREATED")
    repository.add_data_source(sample_data_source, audit_event=prepared, audit_outbox=audit_outbox)
    allowed = frozenset({sample_data_source.data_source_id})
    sources = repository.list_data_sources(allowed)
    assert len(sources) == 1
    assert sources[0].data_source_id == sample_data_source.data_source_id

    empty = repository.list_data_sources(frozenset())
    assert empty == []


def test_add_and_get_connection_revision(
    repository: PostgreSQLDataSourceRepository,
    audit_outbox: PostgreSQLTransactionalAudit,
    sample_data_source: DataSource,
) -> None:
    """FR-012: Baglanti revizyonu olusturma ve okuma."""
    prepared = _prepare_event(audit_outbox, "DATA_SOURCE_CREATED")
    repository.add_data_source(sample_data_source, audit_event=prepared, audit_outbox=audit_outbox)

    next_rev = repository.next_connection_revision(sample_data_source.data_source_id)
    assert next_rev == 2  # Initial revision is 1

    revision = DataSourceConnectionRevision(
        data_source_id=sample_data_source.data_source_id,
        revision=next_rev,
        base_revision=1,
        connection_config={"host": "new-host", "port": 5432},
        secret_reference="secret://datasources/new",
        prepared_by_actor_id="test-actor",
        policy_version="TEST_V1",
        reason_code="DATA_SOURCE.CHANGE",
        created_at=datetime.now(timezone.utc),
    )
    rev_prepared = _prepare_event(audit_outbox, "CONNECTION_REVISION_CREATED")
    stored = repository.add_connection_revision(
        revision, audit_event=rev_prepared, audit_outbox=audit_outbox
    )
    assert stored.revision == next_rev
    assert stored.status is ConnectionRevisionStatus.PENDING_TEST


def test_activation_request_lifecycle(
    repository: PostgreSQLDataSourceRepository,
    audit_outbox: PostgreSQLTransactionalAudit,
    sample_data_source: DataSource,
) -> None:
    """FR-010: Aktivasyon istegi olusturma, karar verme ve okuma."""
    prepared = _prepare_event(audit_outbox, "DATA_SOURCE_CREATED")
    repository.add_data_source(sample_data_source, audit_event=prepared, audit_outbox=audit_outbox)

    # Source must be TEST_SUCCEEDED before activation
    test_result = ConnectionTestResult(
        data_source_id=sample_data_source.data_source_id,
        succeeded=True,
        duration_ms=100,
        tested_at=datetime.now(timezone.utc),
    )
    test_prepared = _prepare_event(audit_outbox, "CONNECTION_TEST_SUCCEEDED")
    repository.update_connection_test(
        test_result, audit_event=test_prepared, audit_outbox=audit_outbox
    )

    request = DataSourceActivationRequest(
        data_source_id=sample_data_source.data_source_id,
        data_source_revision=1,
        maker_actor_id="maker-001",
        policy_version="TEST_V1",
        requested_at=datetime.now(timezone.utc),
    )
    req_prepared = _prepare_event(audit_outbox, "ACTIVATION_REQUESTED")
    stored = repository.add_activation_request(
        request, audit_event=req_prepared, audit_outbox=audit_outbox
    )
    assert stored.status is DataSourceActivationStatus.PENDING

    # Decide: approve
    approved = DataSourceActivationRequest(
        activation_request_id=stored.activation_request_id,
        data_source_id=stored.data_source_id,
        data_source_revision=stored.data_source_revision,
        maker_actor_id=stored.maker_actor_id,
        checker_actor_id="checker-001",
        policy_version=stored.policy_version,
        status=DataSourceActivationStatus.APPROVED,
        decision_reason_code="DATA_SOURCE.ACTIVATION.APPROVED",
        requested_at=stored.requested_at,
        target_at=stored.target_at,
        expires_at=stored.expires_at,
        business_calendar_version=stored.business_calendar_version,
        decided_at=datetime.now(timezone.utc),
    )
    dec_prepared = _prepare_event(audit_outbox, "ACTIVATION_DECIDED")
    decided = repository.decide_activation_request(
        approved, activate_source=True, audit_event=dec_prepared, audit_outbox=audit_outbox
    )
    assert decided.status is DataSourceActivationStatus.APPROVED

    # Source should be ACTIVE
    source = repository.get_data_source(sample_data_source.data_source_id)
    assert source.status is DataSourceStatus.ACTIVE


def test_connection_test_update(
    repository: PostgreSQLDataSourceRepository,
    audit_outbox: PostgreSQLTransactionalAudit,
    sample_data_source: DataSource,
) -> None:
    """FR-008: Baglanti testi sonucu kaydetme ve sorgulama."""
    prepared = _prepare_event(audit_outbox, "DATA_SOURCE_CREATED")
    repository.add_data_source(sample_data_source, audit_event=prepared, audit_outbox=audit_outbox)

    now = datetime.now(timezone.utc)
    result = ConnectionTestResult(
        data_source_id=sample_data_source.data_source_id,
        succeeded=True,
        duration_ms=120,
        error_class=None,
        message="Connection successful.",
        source_info={"version": "15"},
        data_source_revision=1,
        tested_at=now,
    )
    test_prepared = _prepare_event(audit_outbox, "CONNECTION_TESTED")
    repository.update_connection_test(result, audit_event=test_prepared, audit_outbox=audit_outbox)

    latest = repository.latest_connection_test(sample_data_source.data_source_id)
    assert latest is not None
    assert latest.succeeded is True
    assert latest.duration_ms == 120

    source = repository.get_data_source(sample_data_source.data_source_id)
    assert source.status is DataSourceStatus.TEST_SUCCEEDED


def test_get_data_source_not_found(repository: PostgreSQLDataSourceRepository) -> None:
    """Bulunamayan kaynak NotFoundError firlatir."""
    from veri_kalitesi.data_sources.errors import NotFoundError

    with pytest.raises(NotFoundError, match="not found"):
        repository.get_data_source("nonexistent")


def test_get_dataset_not_found(repository: PostgreSQLDataSourceRepository) -> None:
    """Bulunamayan dataset NotFoundError firlatir."""
    from veri_kalitesi.data_sources.errors import NotFoundError

    with pytest.raises(NotFoundError, match="not found"):
        repository.get_dataset("nonexistent")


def test_get_data_field_not_found(repository: PostgreSQLDataSourceRepository) -> None:
    """Bulunamayan data field NotFoundError firlatir."""
    from veri_kalitesi.data_sources.errors import NotFoundError

    with pytest.raises(NotFoundError, match="not found"):
        repository.get_data_field("nonexistent")


def test_list_due_activation_requests(
    repository: PostgreSQLDataSourceRepository,
    audit_outbox: PostgreSQLTransactionalAudit,
    sample_data_source: DataSource,
) -> None:
    """FR-010: Zamani gecmis aktivasyon istekleri dogru listelenir."""
    prepared = _prepare_event(audit_outbox, "DATA_SOURCE_CREATED")
    repository.add_data_source(sample_data_source, audit_event=prepared, audit_outbox=audit_outbox)

    now = datetime.now(timezone.utc)
    request = DataSourceActivationRequest(
        data_source_id=sample_data_source.data_source_id,
        data_source_revision=1,
        maker_actor_id="maker-001",
        policy_version="TEST_V1",
        requested_at=now,
        expires_at=now,
    )
    req_prepared = _prepare_event(audit_outbox, "ACTIVATION_REQUESTED")
    repository.add_activation_request(request, audit_event=req_prepared, audit_outbox=audit_outbox)

    # Due requests should be found
    due = repository.list_due_activation_requests(now)
    assert len(due) == 1
    assert due[0].data_source_id == sample_data_source.data_source_id

    # Non-due requests should not be found
    past = datetime(now.year - 1, 1, 1, tzinfo=timezone.utc)
    not_due = repository.list_due_activation_requests(past)
    assert len(not_due) == 0
