"""PostgreSQL skor, yayın, konfigürasyon ve kısmi politika repository'si."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    and_,
    literal_column,
    or_,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import RowMapping

from veri_kalitesi.data_sources.models import Criticality
from veri_kalitesi.executions.models import MeasurementStatus
from veri_kalitesi.persistence import (
    DEFAULT_SCHEMA_NAME,
    SessionFactory,
    transactional_session,
)
from veri_kalitesi.rules.models import QualityDimension
from veri_kalitesi.scoring.errors import (
    ScoreNotFoundError,
    ScoringValidationError,
)
from veri_kalitesi.scoring.models import (
    QualityScore,
    ScoreLevel,
    ScorePublication,
    ScorePublicationStatus,
    ScoreScopeType,
    ScoreStatus,
    ScoringConfiguration,
    ThresholdSet,
    is_official_observation,
)


@dataclass(frozen=True)
class ScoreTables:
    quality_scores: Table
    score_publications: Table
    scoring_configurations: Table
    scoring_configuration_approvals: Table
    dataset_partial_score_policies: Table


def score_tables(schema: str = DEFAULT_SCHEMA_NAME) -> ScoreTables:
    metadata = MetaData(schema=schema)
    quality_scores = Table(
        "quality_scores",
        metadata,
        Column("quality_score_id", String(36), primary_key=True),
        Column("publication_id", String(36)),
        Column("execution_id", String(36), nullable=False),
        Column("rule_result_id", String(36)),
        Column("rule_version_id", String(36)),
        Column("scope_type", String(20), nullable=False),
        Column("scope_id", String(128)),
        Column("score_value", Numeric(7, 4)),
        Column("score_status", String(40), nullable=False),
        Column("measurement_status", String(30)),
        Column("level", String(20)),
        Column("rule_version_digest", String(71)),
        Column("policy_version", String(80), nullable=False),
        Column("included_component_count", Integer),
        Column("excluded_component_count", Integer),
        Column("calculation_details", JSONB, nullable=False),
        Column("calculated_at", DateTime(timezone=True), nullable=False),
    )
    score_publications = Table(
        "score_publications",
        metadata,
        Column("publication_id", String(36), primary_key=True),
        Column("execution_id", String(36), nullable=False, unique=True),
        Column("period", String(80), nullable=False),
        Column("input_digest", String(71), nullable=False),
        Column("status", String(20), nullable=False),
        Column("policy_version", String(80), nullable=False),
        Column("published_at", DateTime(timezone=True), nullable=False),
        Column("superseded_at", DateTime(timezone=True)),
    )
    scoring_configurations = Table(
        "scoring_configurations",
        metadata,
        Column("configuration_id", String(36), primary_key=True),
        Column("version", String(80), nullable=False, unique=True),
        Column("threshold_version", String(80), nullable=False),
        Column("critical_upper_exclusive", Numeric(7, 4), nullable=False),
        Column("risky_upper_exclusive", Numeric(7, 4), nullable=False),
        Column("acceptable_upper_exclusive", Numeric(7, 4), nullable=False),
        Column("dimension_weights", JSONB, nullable=False),
        Column("criticality_weights", JSONB, nullable=False),
        Column("created_by", String(128), nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("is_active", Integer, nullable=False),
        Column("activated_at", DateTime(timezone=True)),
    )
    scoring_configuration_approvals = Table(
        "scoring_configuration_approvals",
        metadata,
        Column("approval_id", String(36), primary_key=True),
        Column(
            "configuration_id",
            String(36),
            nullable=False,
            unique=True,
        ),
        Column("maker_actor_id", String(128), nullable=False),
        Column("checker_actor_id", String(128)),
        Column("policy_version", String(80), nullable=False),
        Column("status", String(20), nullable=False),
        Column("decision_reason_code", String(120)),
        Column("requested_at", DateTime(timezone=True), nullable=False),
        Column("decided_at", DateTime(timezone=True)),
    )
    dataset_partial_score_policies = Table(
        "dataset_partial_score_policies",
        metadata,
        Column("policy_id", String(36), primary_key=True),
        Column("dataset_id", String(36), nullable=False),
        Column("policy_version", String(80), nullable=False),
        Column("allow_official_partial_score", Integer, nullable=False),
        Column("minimum_coverage_ratio", Numeric(7, 6), nullable=False),
        Column("required_critical_rule_ids", JSONB, nullable=False),
        Column("required_partitions", JSONB, nullable=False),
        Column("maximum_missing_record_ratio", Numeric(7, 6), nullable=False),
        Column("maximum_technical_error_ratio", Numeric(7, 6), nullable=False),
        Column("minimum_successful_rule_ratio", Numeric(7, 6), nullable=False),
        Column("effective_from", DateTime(timezone=True), nullable=False),
        Column("approval_status", String(20), nullable=False),
        Column("created_by", String(128), nullable=False),
        Column("approved_by", String(128)),
        Column("audit_reference", String(128)),
        Column("created_at", DateTime(timezone=True), nullable=False),
    )
    return ScoreTables(
        quality_scores=quality_scores,
        score_publications=score_publications,
        scoring_configurations=scoring_configurations,
        scoring_configuration_approvals=scoring_configuration_approvals,
        dataset_partial_score_policies=dataset_partial_score_policies,
    )


class PostgreSQLScoreRepository:
    """Production skor, yayın, konfigürasyon ve kısmi politika repository'si.

    ScoreReader protokolünü sağlar; yazma metodları publication transaction'ı
    ile audit outbox'ı aynı session'da birleştirir.
    """

    def __init__(
        self,
        session_factory: SessionFactory,
        *,
        schema: str = DEFAULT_SCHEMA_NAME,
    ) -> None:
        self._session_factory = session_factory
        self._tables = score_tables(schema)

    # ── ScoreReader protocol ──

    def list_for_execution(self, execution_id: str) -> list[QualityScore]:
        with transactional_session(self._session_factory) as session:
            t = self._tables.quality_scores
            rows = (
                session.execute(
                    select(t)
                    .where(t.c.execution_id == execution_id)
                    .order_by(t.c.scope_type, t.c.scope_id)
                )
                .mappings()
                .all()
            )
        return [_row_to_score(row) for row in rows]

    def list_for_dashboard_trend(
        self,
        start_at: datetime,
        end_at: datetime,
        allowed_source_ids: frozenset[str],
        include_enterprise: bool,
    ) -> list[QualityScore]:
        if (
            start_at.tzinfo is None
            or start_at.utcoffset() is None
            or end_at.tzinfo is None
            or end_at.utcoffset() is None
            or start_at >= end_at
        ):
            raise ScoringValidationError("Dashboard trend time range is invalid.")
        t = self._tables.quality_scores
        scope_clauses: list[Any] = []
        if allowed_source_ids:
            scope_clauses.append(
                and_(
                    t.c.scope_type == ScoreScopeType.SOURCE.value,
                    t.c.scope_id.in_(sorted(allowed_source_ids)),
                )
            )
        if include_enterprise:
            scope_clauses.append(
                and_(
                    t.c.scope_type == ScoreScopeType.ENTERPRISE.value,
                    t.c.scope_id.is_(None),
                )
            )
        if not scope_clauses:
            return []
        with transactional_session(self._session_factory) as session:
            rows = (
                session.execute(
                    select(t)
                    .where(
                        and_(
                            t.c.calculated_at >= start_at,
                            t.c.calculated_at <= end_at,
                            or_(*scope_clauses),
                        )
                    )
                    .order_by(t.c.calculated_at, t.c.scope_type, t.c.scope_id)
                )
                .mappings()
                .all()
            )
        return [score for row in rows if is_official_observation(score := _row_to_score(row))]

    # ── Score query ──

    def get(self, quality_score_id: str) -> QualityScore:
        with transactional_session(self._session_factory) as session:
            t = self._tables.quality_scores
            row = (
                session.execute(select(t).where(t.c.quality_score_id == quality_score_id))
                .mappings()
                .one_or_none()
            )
        if row is None:
            raise ScoreNotFoundError("QualityScore not found.")
        return _row_to_score(row)

    def get_by_publication(self, publication_id: str) -> list[QualityScore]:
        with transactional_session(self._session_factory) as session:
            t = self._tables.quality_scores
            rows = (
                session.execute(
                    select(t)
                    .where(t.c.publication_id == publication_id)
                    .order_by(t.c.scope_type, t.c.scope_id)
                )
                .mappings()
                .all()
            )
        return [_row_to_score(row) for row in rows]

    def list_scores(
        self,
        *,
        scope_type: ScoreScopeType | None = None,
        scope_id: str | None = None,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
        score_status: str | None = None,
        limit: int = 50,
        allowed_source_ids: frozenset[str] | None = None,
        allowed_dataset_ids: frozenset[str] | None = None,
        can_view_enterprise: bool = False,
    ) -> list[QualityScore]:
        t = self._tables.quality_scores
        conditions: list[Any] = [
            t.c.publication_id.isnot(None),
            t.c.score_value.isnot(None),
        ]
        if scope_type is not None:
            conditions.append(t.c.scope_type == scope_type.value)
        if scope_id is not None:
            conditions.append(t.c.scope_id == scope_id)
        if period_start is not None:
            conditions.append(t.c.calculated_at >= period_start)
        if period_end is not None:
            conditions.append(t.c.calculated_at <= period_end)
        if score_status is not None:
            conditions.append(t.c.score_status == score_status)
        scope_filters = _build_scope_filter(
            t, allowed_source_ids, allowed_dataset_ids, can_view_enterprise
        )
        conditions.extend(scope_filters)
        with transactional_session(self._session_factory) as session:
            rows = (
                session.execute(
                    select(t)
                    .where(and_(*conditions))
                    .order_by(t.c.calculated_at.desc(), t.c.scope_type, t.c.scope_id)
                    .limit(limit)
                )
                .mappings()
                .all()
            )
        return [_row_to_score(row) for row in rows]

    # ── Publication ──

    def get_publication(self, publication_id: str) -> ScorePublication | None:
        with transactional_session(self._session_factory) as session:
            t = self._tables.score_publications
            row = (
                session.execute(select(t).where(t.c.publication_id == publication_id))
                .mappings()
                .one_or_none()
            )
        return _row_to_publication(row) if row else None

    def get_current_publication_for_period(self, period: str) -> ScorePublication | None:
        with transactional_session(self._session_factory) as session:
            t = self._tables.score_publications
            row = (
                session.execute(
                    select(t).where(
                        and_(
                            t.c.period == period,
                            t.c.status == ScorePublicationStatus.PUBLISHED.value,
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
        return _row_to_publication(row) if row else None

    def get_publication_by_execution(self, execution_id: str) -> ScorePublication | None:
        with transactional_session(self._session_factory) as session:
            t = self._tables.score_publications
            row = (
                session.execute(select(t).where(t.c.execution_id == execution_id))
                .mappings()
                .one_or_none()
            )
        return _row_to_publication(row) if row else None

    # ── Configuration ──

    def get_active_configuration(self) -> ScoringConfiguration:
        with transactional_session(self._session_factory) as session:
            t = self._tables.scoring_configurations
            row = session.execute(select(t).where(t.c.is_active == 1)).mappings().one_or_none()
        if row is None:
            raise ScoreNotFoundError("Active ScoringConfiguration not found.")
        return _row_to_configuration(row)

    def get_configuration(self, version: str) -> ScoringConfiguration:
        with transactional_session(self._session_factory) as session:
            t = self._tables.scoring_configurations
            row = session.execute(select(t).where(t.c.version == version)).mappings().one_or_none()
        if row is None:
            raise ScoreNotFoundError("ScoringConfiguration not found.")
        return _row_to_configuration(row)


# ── Row mappers ──


def _row_to_score(row: RowMapping) -> QualityScore:
    return QualityScore(
        quality_score_id=str(row["quality_score_id"]),
        execution_id=str(row["execution_id"]),
        rule_result_id=str(row["rule_result_id"]) if row["rule_result_id"] else None,
        rule_version_id=str(row["rule_version_id"]) if row["rule_version_id"] else None,
        scope_type=ScoreScopeType(str(row["scope_type"])),
        scope_id=str(row["scope_id"]) if row["scope_id"] is not None else None,
        score_value=Decimal(str(row["score_value"])) if row["score_value"] is not None else None,
        score_status=ScoreStatus(str(row["score_status"])),
        measurement_status=(
            MeasurementStatus(str(row["measurement_status"]))
            if row["measurement_status"] is not None
            else None
        ),
        level=ScoreLevel(str(row["level"])) if row["level"] else None,
        calculation_details=dict(row["calculation_details"]),
        calculated_at=row["calculated_at"],
        publication_id=str(row["publication_id"]) if row["publication_id"] else None,
        rule_version_digest=str(row["rule_version_digest"]) if row["rule_version_digest"] else None,
        policy_version=str(row["policy_version"]) if row["policy_version"] else None,
        included_component_count=row["included_component_count"],
        excluded_component_count=row["excluded_component_count"],
    )


def _row_to_publication(row: RowMapping) -> ScorePublication:
    return ScorePublication(
        publication_id=str(row["publication_id"]),
        execution_id=str(row["execution_id"]),
        period=str(row["period"]),
        input_digest=str(row["input_digest"]),
        status=ScorePublicationStatus(str(row["status"])),
        policy_version=str(row["policy_version"]),
        published_at=row["published_at"],
        superseded_at=row["superseded_at"],
    )


def _row_to_configuration(row: RowMapping) -> ScoringConfiguration:
    weights = dict(row["dimension_weights"])
    criticality_weights = dict(row["criticality_weights"])
    return ScoringConfiguration(
        configuration_id=str(row["configuration_id"]),
        version=str(row["version"]),
        threshold_set=ThresholdSet(
            version=str(row["threshold_version"]),
            critical_upper_exclusive=Decimal(str(row["critical_upper_exclusive"])),
            risky_upper_exclusive=Decimal(str(row["risky_upper_exclusive"])),
            acceptable_upper_exclusive=Decimal(str(row["acceptable_upper_exclusive"])),
        ),
        dimension_weights={
            QualityDimension(dimension): Decimal(str(weight))
            for dimension, weight in weights.items()
        },
        criticality_weights={
            Criticality(criticality): Decimal(str(weight))
            for criticality, weight in criticality_weights.items()
        },
        created_by=str(row["created_by"]),
        created_at=row["created_at"],
        is_active=bool(row["is_active"]),
        activated_at=row["activated_at"],
    )


def _build_scope_filter(
    table: Table,
    allowed_source_ids: frozenset[str] | None,
    allowed_dataset_ids: frozenset[str] | None,
    can_view_enterprise: bool,
) -> list[Any]:
    """ActorContext scope'una göre skor filtreleri üretir."""
    permitted: list[Any] = []
    if allowed_source_ids:
        permitted.append(
            and_(
                table.c.scope_type == ScoreScopeType.SOURCE.value,
                table.c.scope_id.in_(sorted(allowed_source_ids)),
            )
        )
    if allowed_dataset_ids:
        permitted.append(
            and_(
                table.c.scope_type.in_(
                    [
                        ScoreScopeType.DATASET.value,
                        ScoreScopeType.RULE.value,
                        ScoreScopeType.DIMENSION.value,
                    ]
                ),
                or_(
                    table.c.scope_id.is_(None),
                    table.c.scope_id.in_(sorted(allowed_dataset_ids)),
                ),
            )
        )
    if can_view_enterprise:
        permitted.append(
            and_(
                table.c.scope_type == ScoreScopeType.ENTERPRISE.value,
                table.c.scope_id.is_(None),
            )
        )
    if not permitted:
        return [literal_column("false")]
    return [or_(*permitted)]
