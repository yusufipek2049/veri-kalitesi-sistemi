"""PostgreSQLDataSourceRepository icin PostgreSQL entegrasyon testleri.

Iteration 36D0 — Data sources PostgreSQL migration.
PostgreSQL gerektiren testler DATA_QUALITY_POSTGRES_TEST_URL ortam degiskeni
olmadan atlanir. Issues/postgresql_repository.py sablonunu izler.
"""

from __future__ import annotations

import os
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
from veri_kalitesi.audit.outbox import PreparedAuditRepository
from veri_kalitesi.data_sources.models import (
    ConnectionRevisionStatus,
    ConnectionTestResult,
    DataSource,
    DataSourceActivationRequest,
    DataSourceActivationStatus,
    DataSourceConnectionRevision,
    DataSourceStatus,
    SourceType,
)
from veri_kalitesi.data_sources.postgresql_repository import (
    PostgreSQLDataSourceRepository,
)
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
def repository(session_factory: type) -> PostgreSQLDataSourceRepository:
    return PostgreSQLDataSourceRepository(session_factory)


@pytest.fixture
def audit_outbox(session_factory: type) -> PostgreSQLTransactionalAudit:
    redactor = AuditRedactor(build_default_redaction_policy())
    repo = PreparedAuditRepository(session_factory)
    return PostgreSQLTransactionalAudit(
        session_factory=session_factory,
        redactor=redactor,
        repository=repo,
        policy_version="TEST_V1",
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


def test_add_and_get_data_source(
    repository: PostgreSQLDataSourceRepository,
    audit_outbox: PostgreSQLTransactionalAudit,
    sample_data_source: DataSource,
) -> None:
    """FR-007: Veri kaynagi olusturma ve okuma."""
    prepared = _prepare_event(audit_outbox, "DATA_SOURCE_CREATED")
    stored = repository.add_data_source(sample_data_source, audit_event=prepared, audit_outbox=audit_outbox)
    assert stored.data_source_id == sample_data_source.data_source_id
    assert stored.status is DataSourceStatus.PASSIVE

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