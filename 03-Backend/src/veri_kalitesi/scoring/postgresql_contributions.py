"""PostgreSQL skor katkı grafiği snapshot repository'si."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping

from sqlalchemy import Column, DateTime, MetaData, String, Table, insert, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import RowMapping

from veri_kalitesi.audit import PostgreSQLTransactionalAudit, PreparedAuditEvent
from veri_kalitesi.persistence import (
    DEFAULT_SCHEMA_NAME,
    SessionFactory,
    transactional_session,
)
from veri_kalitesi.scoring.contributions import contribution_graph
from veri_kalitesi.scoring.errors import ScoringValidationError
from veri_kalitesi.scoring.models import QualityScore


@dataclass(frozen=True)
class StoredContributionGraph:
    quality_score_id: str
    execution_id: str
    scope_type: str
    scope_id: str | None
    graph: Mapping[str, Any]
    created_at: datetime


def contribution_graph_table(schema: str = DEFAULT_SCHEMA_NAME) -> Table:
    return Table(
        "score_contribution_graphs",
        MetaData(schema=schema),
        Column("quality_score_id", String(36), primary_key=True),
        Column("execution_id", String(36), nullable=False),
        Column("scope_type", String(20), nullable=False),
        Column("scope_id", String(128)),
        Column("graph", JSONB, nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
    )


class PostgreSQLContributionGraphRepository:
    """Grafik ve audit outbox kaydını aynı transaction'da değişmez yazar."""

    def __init__(
        self, session_factory: SessionFactory, *, schema: str = DEFAULT_SCHEMA_NAME
    ) -> None:
        self._session_factory = session_factory
        self._table = contribution_graph_table(schema)

    def add_score(
        self,
        score: QualityScore,
        *,
        created_at: datetime,
        audit_event: PreparedAuditEvent,
        audit_outbox: PostgreSQLTransactionalAudit,
    ) -> StoredContributionGraph:
        if created_at.tzinfo is None or created_at.utcoffset() is None:
            raise ScoringValidationError("Contribution graph created_at must be timezone-aware.")
        if audit_outbox.session_factory is not self._session_factory:
            raise ScoringValidationError(
                "Audit outbox must share the contribution graph transaction."
            )
        snapshot = StoredContributionGraph(
            quality_score_id=score.quality_score_id,
            execution_id=score.execution_id,
            scope_type=score.scope_type.value,
            scope_id=score.scope_id,
            graph=contribution_graph(score),
            created_at=created_at,
        )
        with transactional_session(self._session_factory) as session:
            existing = (
                session.execute(
                    select(self._table).where(
                        self._table.c.quality_score_id == snapshot.quality_score_id
                    )
                )
                .mappings()
                .one_or_none()
            )
            if existing is not None:
                if dict(existing["graph"]) != dict(snapshot.graph):
                    raise ScoringValidationError(
                        "Contribution graph is immutable for a quality score."
                    )
                return _from_row(existing)
            session.execute(
                insert(self._table).values(
                    quality_score_id=snapshot.quality_score_id,
                    execution_id=snapshot.execution_id,
                    scope_type=snapshot.scope_type,
                    scope_id=snapshot.scope_id,
                    graph=dict(snapshot.graph),
                    created_at=snapshot.created_at,
                )
            )
            audit_outbox.stage(audit_event, session=session)
        return snapshot

    def get(self, quality_score_id: str) -> StoredContributionGraph | None:
        with transactional_session(self._session_factory) as session:
            row = (
                session.execute(
                    select(self._table).where(self._table.c.quality_score_id == quality_score_id)
                )
                .mappings()
                .one_or_none()
            )
        return _from_row(row) if row is not None else None


def _from_row(row: RowMapping) -> StoredContributionGraph:
    return StoredContributionGraph(
        quality_score_id=str(row["quality_score_id"]),
        execution_id=str(row["execution_id"]),
        scope_type=str(row["scope_type"]),
        scope_id=str(row["scope_id"]) if row["scope_id"] is not None else None,
        graph=dict(row["graph"]),
        created_at=row["created_at"],
    )
