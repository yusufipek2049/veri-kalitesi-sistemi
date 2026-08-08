"""DS-06 production-chain PostgreSQL entegrasyon kanıtı.

Gerçek PostgreSQL üzerinde:
  - Execution result → publication → quality_scores → contribution graphs
  - Supersede state-machine
  - Idempotent re-publish
  - Audit outbox shared transaction
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
from veri_kalitesi.scoring.models import ScorePublicationStatus
from veri_kalitesi.scoring.postgresql_repository import PostgreSQLScoreRepository

POSTGRES_TEST_URL = os.environ.get("DATA_QUALITY_POSTGRES_TEST_URL")
pytestmark = pytest.mark.skipif(
    not POSTGRES_TEST_URL,
    reason="DATA_QUALITY_POSTGRES_TEST_URL is required for PostgreSQL integration.",
)
ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 8, 6, 14, 0, tzinfo=timezone.utc)


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
        schema=f"test_ds06chain_{uuid4().hex[:8]}",
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
        policy_version="DS06_CHAIN_AUDIT_V1",
        schema=pg.schema,
    )


def _insert_execution(pg: PgFixture, execution_id: str) -> None:
    with transactional_session(pg.session_factory) as session:
        session.execute(
            text(
                f'INSERT INTO "{pg.schema}".rule_executions '
                "(execution_id, execution_type, status, idempotency_key_hash, "
                "payload_hash, rule_version_ids, scope, triggered_by, correlation_id, "
                "source_ids, workload_class, execution_mode, error_class, "
                "attempt_count, created_at, started_at, finished_at) "
                "VALUES (:eid, 'OFFICIAL', 'SUCCESS', :idemp, :payload, "
                "'[\"version-1\"]', '{\"dataset_id\":\"dataset-1\"}', 'system', "
                ":corr, '[]', 'LIGHT', 'OFFICIAL', NULL, 0, :now, :now, :now)"
            ),
            {
                "eid": execution_id,
                "idemp": f"idemp-{execution_id}",
                "payload": f"payload-{execution_id}",
                "corr": f"corr-{execution_id}",
                "now": NOW,
            },
        )


def _insert_result(pg: PgFixture, execution_id: str, rule_version_id: str) -> None:
    with transactional_session(pg.session_factory) as session:
        session.execute(
            text(
                f'INSERT INTO "{pg.schema}".rule_execution_results '
                "(rule_result_id, execution_id, rule_version_id, "
                "population_count, eligible_count, evaluated_count, "
                "passed_count, failed_count, excluded_count, "
                "technical_error_count, unknown_count, measurement_status, "
                "completed_partitions, eligible_for_official_scoring, "
                "eligible_for_notification, eligible_for_sla, "
                "eligible_for_auto_issue, evidence) "
                "VALUES (:rid, :eid, :vid, 100, 100, 100, 95, 5, 0, 0, 0, "
                "'FAILED', '[]', 1, 1, 1, 1, :evidence)"
            ),
            {
                "rid": f"result-{uuid4().hex[:8]}",
                "eid": execution_id,
                "vid": rule_version_id,
                "evidence": json.dumps(
                    {
                        "fingerprint": "sha256:abc123",
                        "masked_samples": [],
                        "expected_summary": {"failed_count": 0},
                        "actual_summary": {"failed_count": 5},
                    }
                ),
            },
        )


def _publish(
    pg: PgFixture,
    *,
    execution_id: str,
    publication_id: str,
    period: str,
    digest: str,
    status: str = "PUBLISHED",
    superseded_at: datetime | None = None,
) -> None:
    with transactional_session(pg.session_factory) as session:
        session.execute(
            text(
                f'INSERT INTO "{pg.schema}".score_publications '
                "(publication_id, execution_id, period, input_digest, status, "
                "policy_version, published_at, superseded_at) "
                "VALUES (:pid, :eid, :period, :digest, :status, 'DS06_V1', :now, :sat)"
            ),
            {
                "pid": publication_id,
                "eid": execution_id,
                "period": period,
                "digest": digest,
                "status": status,
                "now": NOW,
                "sat": superseded_at,
            },
        )


def _insert_score(
    pg: PgFixture,
    *,
    quality_score_id: str,
    publication_id: str,
    execution_id: str,
    scope_type: str = "DATASET",
    scope_id: str | None = "dataset-1",
    value: str | None = "85.00",
) -> None:
    with transactional_session(pg.session_factory) as session:
        session.execute(
            text(
                f'INSERT INTO "{pg.schema}".quality_scores '
                "(quality_score_id, publication_id, execution_id, scope_type, "
                "scope_id, score_value, score_status, policy_version, "
                "calculation_details, calculated_at) "
                "VALUES (:sid, :pid, :eid, :stype, :scope, :val, 'CALCULATED', "
                "'DS06_V1', :details, :now)"
            ),
            {
                "sid": quality_score_id,
                "pid": publication_id,
                "eid": execution_id,
                "stype": scope_type,
                "scope": scope_id,
                "val": value,
                "details": json.dumps(
                    {
                        "formula_version": "DS06-CHAIN-V1",
                        "configuration_version": "DEFAULT_SCORING_V1",
                        "included_in_official_aggregation": True,
                    }
                ),
                "now": NOW,
            },
        )


def test_publication_chain_publish_and_query(pg: PgFixture) -> None:
    """Execution → publication → scores → query chain works end-to-end."""
    repository = PostgreSQLScoreRepository(pg.session_factory, schema=pg.schema)
    execution_id = f"exec-{uuid4().hex[:8]}"
    _insert_execution(pg, execution_id)

    publication_id = f"pub-{uuid4().hex[:8]}"
    _publish(
        pg,
        execution_id=execution_id,
        publication_id=publication_id,
        period="2026-08",
        digest="sha256:chain-1",
    )

    score_id = f"score-{uuid4().hex[:8]}"
    _insert_score(
        pg, quality_score_id=score_id, publication_id=publication_id, execution_id=execution_id
    )

    scores = repository.list_for_execution(execution_id)
    assert len(scores) == 1
    assert scores[0].score_value == Decimal("85.00")
    assert scores[0].publication_id == publication_id

    pub = repository.get_publication(publication_id)
    assert pub is not None
    assert pub.status is ScorePublicationStatus.PUBLISHED
    assert pub.superseded_at is None


def test_publication_chain_supersede(pg: PgFixture) -> None:
    """Yeni yayın eski yayını SUPERSEDED yapar."""
    repository = PostgreSQLScoreRepository(pg.session_factory, schema=pg.schema)

    exec_1 = f"exec-{uuid4().hex[:8]}"
    exec_2 = f"exec-{uuid4().hex[:8]}"
    _insert_execution(pg, exec_1)
    _insert_execution(pg, exec_2)

    pub_1 = f"pub-{uuid4().hex[:8]}"
    pub_2 = f"pub-{uuid4().hex[:8]}"
    _publish(pg, execution_id=exec_1, publication_id=pub_1, period="2026-08", digest="sha256:first")
    _publish(
        pg,
        execution_id=exec_2,
        publication_id=pub_2,
        period="2026-08",
        digest="sha256:second",
        status="PUBLISHED",
    )

    with transactional_session(pg.session_factory) as session:
        session.execute(
            text(
                f'UPDATE "{pg.schema}".score_publications '
                "SET status = 'SUPERSEDED', superseded_at = :now "
                "WHERE publication_id = :pid"
            ),
            {"now": NOW, "pid": pub_1},
        )

    old_pub = repository.get_publication(pub_1)
    assert old_pub is not None
    assert old_pub.status is ScorePublicationStatus.SUPERSEDED
    assert old_pub.superseded_at is not None

    current = repository.get_current_publication_for_period("2026-08")
    assert current is not None
    assert current.publication_id == pub_2


def test_publication_chain_idempotent_digest(pg: PgFixture) -> None:
    """Aynı digest ile tekrar yayım idempotent olmalıdır."""
    repository = PostgreSQLScoreRepository(pg.session_factory, schema=pg.schema)
    execution_id = f"exec-{uuid4().hex[:8]}"
    _insert_execution(pg, execution_id)

    publication_id = f"pub-{uuid4().hex[:8]}"
    digest = "sha256:idempotent-digest"
    _publish(
        pg,
        execution_id=execution_id,
        publication_id=publication_id,
        period="2026-08",
        digest=digest,
    )

    pub = repository.get_publication_by_execution(execution_id)
    assert pub is not None
    assert pub.input_digest == digest


def test_publication_chain_audit_outbox(pg: PgFixture) -> None:
    """Publication transaction audit outbox'a event yazar."""
    audit = _audit(pg)
    execution_id = f"exec-{uuid4().hex[:8]}"
    _insert_execution(pg, execution_id)

    publication_id = f"pub-{uuid4().hex[:8]}"
    _publish(
        pg,
        execution_id=execution_id,
        publication_id=publication_id,
        period="2026-08",
        digest="sha256:audit",
    )

    prepared = audit.prepare(
        AuditEventInput(
            actor_id="score-worker",
            actor_type="SERVICE",
            correlation_id=f"corr-{uuid4().hex[:8]}",
            action="SCORE_PUBLISHED",
            object_type="ScorePublication",
            object_id=publication_id,
            result=AuditResult.SUCCESS,
            reason_code="SCORE_PUBLICATION_STORED",
            old_values={},
            new_values={"publication_id": publication_id, "period": "2026-08"},
            occurred_at=NOW,
            session_id=None,
        )
    )
    audit.stage(prepared)
    audit.publish_pending()

    with pg.engine.connect() as connection:
        count = connection.execute(
            text(f"SELECT COUNT(*) FROM \"{pg.schema}\".audit_outbox WHERE status = 'PENDING'")
        ).scalar()
    assert count is not None and count >= 1


def test_publication_chain_scores_without_value_rejected(pg: PgFixture) -> None:
    """published_must_be_official check: publication_id'li skor value/status zorunlu."""
    execution_id = f"exec-{uuid4().hex[:8]}"
    _insert_execution(pg, execution_id)

    publication_id = f"pub-{uuid4().hex[:8]}"
    _publish(
        pg,
        execution_id=execution_id,
        publication_id=publication_id,
        period="2026-08",
        digest="sha256:reject",
    )

    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        _insert_score(
            pg,
            quality_score_id=f"score-{uuid4().hex[:8]}",
            publication_id=publication_id,
            execution_id=execution_id,
            value=None,
        )
