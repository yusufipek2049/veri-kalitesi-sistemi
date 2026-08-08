"""Lineage/yönetişim kanıtı migration ve repository PostgreSQL entegrasyon kanıtı."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.exc import IntegrityError

from veri_kalitesi.audit.models import (
    AuditEventInput,
    AuditResult,
    PreparedAuditEvent,
)
from veri_kalitesi.audit.policies import build_default_redaction_policy
from veri_kalitesi.audit.postgresql_outbox import PostgreSQLTransactionalAudit
from veri_kalitesi.audit.redaction import AuditRedactor
from veri_kalitesi.lineage import (
    ColumnLineageEdge,
    GovernanceAssetKind,
    GovernanceReference,
    LineageDatasetRef,
    LineageEvent,
    LineageEventType,
    LineageSnapshotKind,
    LineageValidationError,
    PostgreSQLLineageEvidenceRepository,
    build_governance_profile,
    governance_profile_snapshot,
    lineage_snapshot,
)
from veri_kalitesi.persistence import (
    DatabaseSettings,
    SessionFactory,
    create_session_factory,
)


POSTGRES_TEST_URL = os.environ.get("DATA_QUALITY_POSTGRES_TEST_URL")
pytestmark = pytest.mark.skipif(
    not POSTGRES_TEST_URL,
    reason="DATA_QUALITY_POSTGRES_TEST_URL is required for PostgreSQL integration.",
)
ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 7, 30, 12, 0, tzinfo=timezone.utc)


@dataclass
class PgFixture:
    session_factory: SessionFactory
    schema: str
    engine: Any


@pytest.fixture
def pg() -> Iterator[PgFixture]:
    assert POSTGRES_TEST_URL is not None
    settings = DatabaseSettings.from_url(
        POSTGRES_TEST_URL,
        schema=f"test_lineage_{uuid4().hex[:8]}",
    )
    session_factory = create_session_factory(settings)
    engine = create_engine(settings.url)
    alembic_cfg = Config(str(ROOT / "alembic.ini"))
    alembic_cfg.set_main_option(
        "sqlalchemy.url",
        settings.url.render_as_string(hide_password=False),
    )
    alembic_cfg.set_main_option("data_quality_schema", settings.schema)
    command.upgrade(alembic_cfg, "head")
    yield PgFixture(session_factory, settings.schema, engine)
    with engine.begin() as connection:
        connection.execute(text(f'DROP SCHEMA IF EXISTS "{settings.schema}" CASCADE'))
    engine.dispose()


def test_lineage_evidence_snapshot_and_audit_outbox_are_atomic_and_immutable(
    pg: PgFixture,
) -> None:
    repository = PostgreSQLLineageEvidenceRepository(
        pg.session_factory,
        schema=pg.schema,
    )
    audit = _audit(pg)
    payload = governance_profile_snapshot(_profile(criticality="HIGH"))
    event = _event(audit, "GOVERNANCE_PROFILE", "dataset-1")

    stored = repository.add_snapshot(
        LineageSnapshotKind.GOVERNANCE_PROFILE,
        "dataset-1",
        "1",
        payload,
        created_at=NOW,
        audit_event=event,
        audit_outbox=audit,
    )

    assert stored.digest == payload["digest"]
    assert repository.get(stored.snapshot_id) == stored
    assert (
        repository.get_version(LineageSnapshotKind.GOVERNANCE_PROFILE, "dataset-1", "1") == stored
    )
    with pg.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(audit.table)) == 1

    changed = governance_profile_snapshot(_profile(criticality="LOW"))
    with pytest.raises(IntegrityError):
        repository.add_snapshot(
            LineageSnapshotKind.GOVERNANCE_PROFILE,
            "dataset-1",
            "1",
            changed,
            created_at=NOW,
            audit_event=_event(audit, "GOVERNANCE_PROFILE", "dataset-1-changed"),
            audit_outbox=audit,
        )
    assert (
        repository.get_version(LineageSnapshotKind.GOVERNANCE_PROFILE, "dataset-1", "1").digest
        == payload["digest"]
    )

    repeated = repository.add_snapshot(
        LineageSnapshotKind.GOVERNANCE_PROFILE,
        "dataset-1",
        "1",
        payload,
        created_at=NOW,
        audit_event=_event(audit, "GOVERNANCE_PROFILE", "dataset-1-repeat"),
        audit_outbox=audit,
    )
    assert repeated == stored
    with pg.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(audit.table)) == 1


def test_lineage_snapshot_kinds_and_digest_constraints_are_enforced(
    pg: PgFixture,
) -> None:
    repository = PostgreSQLLineageEvidenceRepository(
        pg.session_factory,
        schema=pg.schema,
    )
    audit = _audit(pg)
    snapshot = lineage_snapshot(
        (_lineage_event(),),
        as_of=NOW,
        freshness_limit=timedelta(days=1),
        freshness_policy_version="LINEAGE_FRESHNESS_V1",
    )

    stored = repository.add_snapshot(
        LineageSnapshotKind.LINEAGE_EVENTS,
        "synthetic:curated.customer",
        snapshot["snapshot_contract_version"],
        snapshot,
        created_at=NOW,
        audit_event=_event(audit, "LINEAGE_EVENTS", "synthetic-curated-customer"),
        audit_outbox=audit,
    )

    assert stored.payload["coverage_status"] == "COMPLETE"
    assert stored.snapshot_kind == "LINEAGE_EVENTS"
    with pytest.raises(LineageValidationError, match="sha256 digest"):
        repository.add_snapshot(
            LineageSnapshotKind.IMPACT_ASSESSMENT,
            "issue-1",
            "DQ_SOURCED_IMPACT_V1",
            {"digest": "md5:0"},
            created_at=NOW,
            audit_event=_event(audit, "IMPACT_ASSESSMENT", "issue-1"),
            audit_outbox=audit,
        )
    with pytest.raises(LineageValidationError, match="timezone-aware"):
        repository.add_snapshot(
            LineageSnapshotKind.IMPACT_ASSESSMENT,
            "issue-1",
            "DQ_SOURCED_IMPACT_V1",
            snapshot,
            created_at=NOW.replace(tzinfo=None),
            audit_event=_event(audit, "IMPACT_ASSESSMENT", "issue-1"),
            audit_outbox=audit,
        )
    with pg.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(audit.table)) == 1


def _audit(pg: PgFixture) -> PostgreSQLTransactionalAudit:
    from conftest import FakePreparedAuditRepository  # type: ignore[import-untyped]

    return PostgreSQLTransactionalAudit(
        pg.session_factory,
        AuditRedactor(build_default_redaction_policy()),
        FakePreparedAuditRepository(),
        policy_version="TEST_AUDIT_V1",
        schema=pg.schema,
    )


def _event(
    audit: PostgreSQLTransactionalAudit,
    object_type: str,
    object_id: str,
) -> PreparedAuditEvent:
    return audit.prepare(
        AuditEventInput(
            actor_id="lineage-worker",
            actor_type="SERVICE",
            correlation_id="lineage-evidence-correlation",
            action="LINEAGE_EVIDENCE_SNAPSHOT_STORED",
            object_type=object_type,
            object_id=object_id,
            result=AuditResult.SUCCESS,
            reason_code="LINEAGE_EVIDENCE_CREATED",
            old_values={},
            new_values={"subject_ref": object_id},
            occurred_at=NOW,
            session_id=None,
        )
    )


def _profile(*, criticality: str):
    return build_governance_profile(
        asset_ref="dataset-1",
        asset_kind=GovernanceAssetKind.DATASET,
        version_number=1,
        effective_from=NOW - timedelta(days=1),
        attributes={
            "criticality": GovernanceReference(
                source_system="SYNTHETIC_GOVERNANCE_REGISTRY",
                field_path="synthetic_registry.criticality",
                value=criticality,
            )
        },
        profile_id="profile-1",
    )


def _lineage_event() -> LineageEvent:
    curated = LineageDatasetRef("synthetic", "curated.customer")
    raw = LineageDatasetRef("synthetic", "raw.customer")
    return LineageEvent(
        event_type=LineageEventType.COMPLETE,
        event_time=NOW - timedelta(hours=1),
        run_id="run-1",
        job_namespace="synthetic",
        job_name="load-customer",
        producer="https://veri-kalitesi.local/synthetic-lineage/producer",
        schema_url="https://openlineage.io/spec/RunEvent.json",
        source_authority="SYNTHETIC_LINEAGE_REGISTRY",
        observed_at=NOW,
        inputs=(raw,),
        outputs=(curated,),
        column_edges=(
            ColumnLineageEdge(
                output_dataset=curated,
                output_field="customer_id",
                input_dataset=raw,
                input_field="id",
                transformation_ref="transform:identity",
            ),
        ),
    )
