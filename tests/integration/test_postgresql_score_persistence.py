"""DS-06 PostgreSQL skor repository kalıcılık entegrasyon kanıtı.

Score publication, configuration okuma, contribution graph FK ve
audit outbox shared transaction doğrulaması.
"""

from __future__ import annotations

import json
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
from sqlalchemy import create_engine, text

from veri_kalitesi.audit.models import (
    AuditEventInput,
    AuditResult,
    PreparedAuditEvent,
)
from veri_kalitesi.audit.policies import build_default_redaction_policy
from veri_kalitesi.audit.postgresql_outbox import PostgreSQLTransactionalAudit
from veri_kalitesi.audit.redaction import AuditRedactor
from veri_kalitesi.persistence import (
    DatabaseSettings,
    SessionFactory,
    create_session_factory,
    transactional_session,
)
from veri_kalitesi.scoring.models import (
    QualityScore,
    ScorePublicationStatus,
    ScoreScopeType,
    ScoreStatus,
)
from veri_kalitesi.scoring.postgresql_contributions import PostgreSQLContributionGraphRepository
from veri_kalitesi.scoring.postgresql_repository import PostgreSQLScoreRepository

POSTGRES_TEST_URL = os.environ.get("DATA_QUALITY_POSTGRES_TEST_URL")
pytestmark = pytest.mark.skipif(
    not POSTGRES_TEST_URL,
    reason="DATA_QUALITY_POSTGRES_TEST_URL is required for PostgreSQL integration.",
)
ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc)


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
        schema=f"test_ds06persist_{uuid4().hex[:8]}",
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


def _audit(pg: PgFixture) -> PostgreSQLTransactionalAudit:
    from conftest import FakePreparedAuditRepository

    return PostgreSQLTransactionalAudit(
        pg.session_factory,
        AuditRedactor(build_default_redaction_policy()),
        FakePreparedAuditRepository(),
        policy_version="DS06_PERSIST_AUDIT_V1",
        schema=pg.schema,
    )


def _prepare_event(
    audit: PostgreSQLTransactionalAudit,
    *,
    action: str,
    object_id: str,
) -> PreparedAuditEvent:
    return audit.prepare(
        AuditEventInput(
            actor_id="score-worker",
            actor_type="SERVICE",
            correlation_id=f"ds06-correlation-{uuid4().hex[:8]}",
            action=action,
            object_type="ScorePublication",
            object_id=object_id,
            result=AuditResult.SUCCESS,
            reason_code="DS06_PUBLICATION_STORED",
            old_values={},
            new_values={"publication_id": object_id},
            occurred_at=NOW,
            session_id=None,
        )
    )


def _insert_execution(pg: PgFixture, execution_id: str) -> None:
    """Insert a minimal rule_execution row so FK references resolve."""
    with transactional_session(pg.session_factory) as session:
        session.execute(
            text(
                f'INSERT INTO "{pg.schema}".rule_executions '
                "(execution_id, execution_type, status, idempotency_key_hash, "
                "payload_hash, rule_version_ids, scope, triggered_by, correlation_id, "
                "source_ids, workload_class, execution_mode, error_class, "
                "attempt_count, created_at, started_at, finished_at) "
                "VALUES (:eid, 'OFFICIAL', 'SUCCESS', :idemp, :payload, "
                "'[]', '{}', 'system', :corr, '[]', 'LIGHT', 'OFFICIAL', "
                "NULL, 0, :now, :now, :now)"
            ),
            {
                "eid": execution_id,
                "idemp": f"idemp-{execution_id}",
                "payload": f"payload-{execution_id}",
                "corr": f"corr-{execution_id}",
                "now": NOW,
            },
        )


def _score(
    quality_score_id: str,
    execution_id: str,
    *,
    scope_type: ScoreScopeType = ScoreScopeType.DATASET,
    scope_id: str | None = "dataset-1",
    value: str = "85.00",
) -> QualityScore:
    return QualityScore(
        quality_score_id=quality_score_id,
        execution_id=execution_id,
        rule_version_id=None,
        scope_type=scope_type,
        scope_id=scope_id,
        score_value=Decimal(value),
        score_status=ScoreStatus.CALCULATED,
        calculation_details={
            "formula_version": "DS06-PERSIST-V1",
            "configuration_version": "DEFAULT_SCORING_V1",
            "included_in_official_aggregation": True,
        },
        calculated_at=NOW,
    )


def test_get_active_configuration_returns_seeded_default(pg: PgFixture) -> None:
    """Migration seed'lediği varsayılan konfigürasyon okunabilir."""
    repository = PostgreSQLScoreRepository(pg.session_factory, schema=pg.schema)
    config = repository.get_active_configuration()
    assert config.version == "DEFAULT_SCORING_V1"
    assert config.is_active is True
    assert config.threshold_set.version == "DEFAULT_THRESHOLDS_V1"


def test_published_scores_are_queryable_by_execution(pg: PgFixture) -> None:
    """Yayınlanan skorlar execution_id ile sorgulanabilir."""
    repository = PostgreSQLScoreRepository(pg.session_factory, schema=pg.schema)
    execution_id = f"exec-{uuid4().hex[:8]}"
    _insert_execution(pg, execution_id)

    score_1 = _score(f"score-{uuid4().hex[:8]}", execution_id)
    score_2 = _score(
        f"score-{uuid4().hex[:8]}",
        execution_id,
        scope_type=ScoreScopeType.SOURCE,
        scope_id="source-1",
        value="92.50",
    )

    publication_id = f"pub-{uuid4().hex[:8]}"
    with transactional_session(pg.session_factory) as session:
        session.execute(
            text(
                f'INSERT INTO "{pg.schema}".score_publications '
                "(publication_id, execution_id, period, input_digest, status, "
                "policy_version, published_at) "
                "VALUES (:pid, :eid, '2026-08', :digest, 'PUBLISHED', 'DS06_V1', :now)"
            ),
            {
                "pid": publication_id,
                "eid": execution_id,
                "digest": "sha256:abc123",
                "now": NOW,
            },
        )
        for score in (score_1, score_2):
            session.execute(
                text(
                    f'INSERT INTO "{pg.schema}".quality_scores '
                    "(quality_score_id, publication_id, execution_id, scope_type, "
                    "scope_id, score_value, score_status, policy_version, "
                    "calculation_details, calculated_at) "
                    "VALUES (:sid, :pid, :eid, :stype, :sid_val, :val, 'CALCULATED', "
                    "'DS06_V1', :details, :now)"
                ),
                {
                    "sid": score.quality_score_id,
                    "pid": publication_id,
                    "eid": execution_id,
                    "stype": score.scope_type.value,
                    "sid_val": score.scope_id,
                    "val": str(score.score_value),
                    "details": json.dumps(score.calculation_details),
                    "now": NOW,
                },
            )

    results = repository.list_for_execution(execution_id)
    assert len(results) == 2
    values = {s.score_value for s in results}
    assert Decimal("85.00") in values
    assert Decimal("92.50") in values


def test_publication_lookup_by_period(pg: PgFixture) -> None:
    """Aktif dönem yayını sorgulanabilir."""
    repository = PostgreSQLScoreRepository(pg.session_factory, schema=pg.schema)
    execution_id = f"exec-{uuid4().hex[:8]}"
    _insert_execution(pg, execution_id)

    publication_id = f"pub-{uuid4().hex[:8]}"
    with transactional_session(pg.session_factory) as session:
        session.execute(
            text(
                f'INSERT INTO "{pg.schema}".score_publications '
                "(publication_id, execution_id, period, input_digest, status, "
                "policy_version, published_at) "
                "VALUES (:pid, :eid, '2026-08', :digest, 'PUBLISHED', 'DS06_V1', :now)"
            ),
            {
                "pid": publication_id,
                "eid": execution_id,
                "digest": "sha256:def456",
                "now": NOW,
            },
        )

    current = repository.get_current_publication_for_period("2026-08")
    assert current is not None
    assert current.publication_id == publication_id
    assert current.status is ScorePublicationStatus.PUBLISHED


def test_contribution_graph_stored_alongside_publication(pg: PgFixture) -> None:
    """Publication transaction'ında contribution graph da yazılır."""
    graph_repo = PostgreSQLContributionGraphRepository(pg.session_factory, schema=pg.schema)
    execution_id = f"exec-{uuid4().hex[:8]}"
    _insert_execution(pg, execution_id)

    score = _score(f"score-{uuid4().hex[:8]}", execution_id)
    publication_id = f"pub-{uuid4().hex[:8]}"

    with transactional_session(pg.session_factory) as session:
        session.execute(
            text(
                f'INSERT INTO "{pg.schema}".score_publications '
                "(publication_id, execution_id, period, input_digest, status, "
                "policy_version, published_at) "
                "VALUES (:pid, :eid, '2026-08', :digest, 'PUBLISHED', 'DS06_V1', :now)"
            ),
            {
                "pid": publication_id,
                "eid": execution_id,
                "digest": "sha256:graph-test",
                "now": NOW,
            },
        )
        session.execute(
            text(
                f'INSERT INTO "{pg.schema}".quality_scores '
                "(quality_score_id, publication_id, execution_id, scope_type, "
                "scope_id, score_value, score_status, policy_version, "
                "calculation_details, calculated_at) "
                "VALUES (:sid, :pid, :eid, :stype, :sid_val, :val, 'CALCULATED', "
                "'DS06_V1', :details, :now)"
            ),
            {
                "sid": score.quality_score_id,
                "pid": publication_id,
                "eid": execution_id,
                "stype": score.scope_type.value,
                "sid_val": score.scope_id,
                "val": str(score.score_value),
                "details": json.dumps(score.calculation_details),
                "now": NOW,
            },
        )

    audit = _audit(pg)
    event = _prepare_event(audit, action="SCORE_GRAPH_STORED", object_id=score.quality_score_id)
    graph = graph_repo.add_score(score, created_at=NOW, audit_event=event, audit_outbox=audit)
    assert graph.graph["raw_quality_score"] == str(score.score_value)

    fetched = graph_repo.get(score.quality_score_id)
    assert fetched is not None
    assert fetched.quality_score_id == score.quality_score_id
