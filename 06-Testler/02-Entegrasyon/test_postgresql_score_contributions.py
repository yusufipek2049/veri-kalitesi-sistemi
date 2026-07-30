"""Skor katkı grafiği migration/repository PostgreSQL entegrasyon kanıtı."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.exc import IntegrityError

from veri_kalitesi.audit import (
    AuditEventInput,
    AuditRedactor,
    AuditResult,
    PostgreSQLTransactionalAudit,
    PreparedAuditEvent,
    build_default_redaction_policy,
)
from veri_kalitesi.persistence import (
    DatabaseSettings,
    SessionFactory,
    create_session_factory,
)
from veri_kalitesi.scoring import (
    PostgreSQLContributionGraphRepository,
    QualityScore,
    ScoreScopeType,
    ScoreStatus,
    ScoringValidationError,
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
        schema=f"test_score_graph_{uuid4().hex[:8]}",
    )
    session_factory = create_session_factory(settings)
    engine = create_engine(settings.url)
    alembic_cfg = Config(str(ROOT / "05-Veritabani" / "alembic.ini"))
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


def test_graph_snapshot_and_audit_outbox_are_atomic_and_immutable(
    pg: PgFixture,
) -> None:
    repository = PostgreSQLContributionGraphRepository(
        pg.session_factory,
        schema=pg.schema,
    )
    audit = _audit(pg)
    score = _score("score-1", "88.00")
    event = _event(audit, score.quality_score_id)

    stored = repository.add_score(
        score,
        created_at=NOW,
        audit_event=event,
        audit_outbox=audit,
    )

    assert stored.graph["raw_quality_score"] == "88.00"
    assert repository.get(score.quality_score_id) == stored
    with pg.session_factory() as session:
        assert session.scalar(
            select(func.count()).select_from(audit.table)
        ) == 1

    changed = _score("score-1", "91.00")
    with pytest.raises(ScoringValidationError, match="immutable"):
        repository.add_score(
            changed,
            created_at=NOW,
            audit_event=_event(audit, changed.quality_score_id),
            audit_outbox=audit,
        )

    second = _score("score-2", "79.00")
    with pytest.raises(IntegrityError):
        repository.add_score(
            second,
            created_at=NOW,
            audit_event=event,
            audit_outbox=audit,
        )
    assert repository.get(second.quality_score_id) is None


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
    quality_score_id: str,
) -> PreparedAuditEvent:
    return audit.prepare(
        AuditEventInput(
            actor_id="score-worker",
            actor_type="SERVICE",
            correlation_id="score-graph-correlation",
            action="SCORE_CONTRIBUTION_GRAPH_STORED",
            object_type="ScoreContributionGraph",
            object_id=quality_score_id,
            result=AuditResult.SUCCESS,
            reason_code="SCORE_GRAPH_CREATED",
            old_values={},
            new_values={"quality_score_id": quality_score_id},
            occurred_at=NOW,
            session_id=None,
        )
    )


def _score(quality_score_id: str, value: str) -> QualityScore:
    return QualityScore(
        quality_score_id=quality_score_id,
        execution_id="execution-1",
        rule_version_id=None,
        scope_type=ScoreScopeType.SOURCE,
        scope_id="source-1",
        score_value=Decimal(value),
        score_status=ScoreStatus.CALCULATED,
        calculation_details={
            "included_in_official_aggregation": True,
            "rule_set_version": "rule-set-v1",
            "formula_version": "source-model-v1",
            "configuration_version": "score-policy-v1",
            "qualification_policy_version": "qualification-v1",
            "profile_version": "profile-v1",
            "governance_version": "governance-v1",
            "included_components": [
                {
                    "quality_score_id": "dataset-score-1",
                    "dataset_id": "dataset-1",
                    "score": value,
                    "weight": "1",
                }
            ],
            "weight_sum": "1",
        },
        calculated_at=NOW,
    )
