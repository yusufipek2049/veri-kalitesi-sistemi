"""PostgreSQL salt-okunur analytics sorgu adaptörleri."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    JSON,
    MetaData,
    Numeric,
    String,
    Table,
    and_,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB

from veri_kalitesi.persistence import DEFAULT_SCHEMA_NAME, SessionFactory, transactional_session


@dataclass(frozen=True)
class _DatasetRow:
    dataset_id: str
    data_source_id: str
    name: str
    namespace: str
    criticality: str
    owner_user_id: str | None
    status: str
    updated_at: datetime


@dataclass(frozen=True)
class _FieldRow:
    data_field_id: str
    dataset_id: str
    name: str
    is_sensitive: bool
    classification: str
    classification_policy_version: str
    status: str
    updated_at: datetime


@dataclass(frozen=True)
class _RuleRow:
    quality_rule_id: str
    code: str
    name: str
    dataset_id: str
    field_ids: tuple[str, ...]
    primary_dimension: str
    status: str


@dataclass(frozen=True)
class _RuleVersionRow:
    rule_version_id: str
    quality_rule_id: str
    version_no: int
    rule_type: str
    threshold: float
    criticality: str
    created_at: datetime


@dataclass(frozen=True)
class _ScoreRow:
    quality_score_id: str
    rule_version_id: str | None
    scope_type: str
    scope_id: str | None
    score_value: float | None
    score_status: str
    measurement_status: str | None
    level: str | None
    policy_version: str | None
    calculated_at: datetime
    calculation_details: dict[str, Any]


@dataclass(frozen=True)
class _IssueRow:
    issue_id: str
    scope_type: str
    scope_id: str
    status: str
    priority: str
    trigger_type: str
    occurrence_count: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class _IssueHistoryRow:
    issue_id: str
    action: str
    new_status: str
    occurred_at: datetime


@dataclass(frozen=True)
class _IssueRelationshipRow:
    predecessor_issue_id: str
    successor_issue_id: str
    relationship_type: str


@dataclass(frozen=True)
class _ConfigurationRow:
    configuration_id: str
    version: str
    threshold_version: str
    critical_upper_exclusive: float
    risky_upper_exclusive: float
    acceptable_upper_exclusive: float
    dimension_weights: dict[str, float]
    criticality_weights: dict[str, float]
    is_active: bool
    created_at: datetime


@dataclass(frozen=True)
class _ContributionGraphRow:
    quality_score_id: str
    graph_version: str
    official: bool
    graph_data: dict[str, Any]


# ── Table definitions (read-only projections) ──


def _analytics_tables(schema: str) -> dict[str, Table]:
    metadata = MetaData(schema=schema)
    datasets = Table(
        "datasets",
        metadata,
        Column("dataset_id", String(36)),
        Column("data_source_id", String(36)),
        Column("name", String(400)),
        Column("namespace", String(200)),
        Column("criticality", String(20)),
        Column("owner_user_id", String(128)),
        Column("status", String(20)),
        Column("updated_at", DateTime(timezone=True)),
    )
    fields = Table(
        "data_fields",
        metadata,
        Column("data_field_id", String(36)),
        Column("dataset_id", String(36)),
        Column("name", String(400)),
        Column("is_sensitive", Boolean),
        Column("classification", String(40)),
        Column("classification_policy_version", String(40)),
        Column("status", String(20)),
        Column("updated_at", DateTime(timezone=True)),
    )
    rules = Table(
        "quality_rules",
        metadata,
        Column("quality_rule_id", String(36)),
        Column("code", String(200)),
        Column("name", String(400)),
        Column("dataset_id", String(36)),
        Column("field_ids", JSON),
        Column("primary_dimension", String(40)),
        Column("status", String(30)),
    )
    versions = Table(
        "rule_versions",
        metadata,
        Column("rule_version_id", String(36)),
        Column("quality_rule_id", String(36)),
        Column("version_no", Integer),
        Column("rule_type", String(40)),
        Column("threshold", Numeric(12, 4)),
        Column("criticality", String(20)),
        Column("created_at", DateTime(timezone=True)),
    )
    scores = Table(
        "quality_scores",
        metadata,
        Column("quality_score_id", String(36)),
        Column("rule_version_id", String(36)),
        Column("scope_type", String(20)),
        Column("scope_id", String(128)),
        Column("score_value", Numeric(7, 4)),
        Column("score_status", String(40)),
        Column("measurement_status", String(30)),
        Column("level", String(20)),
        Column("policy_version", String(80)),
        Column("calculated_at", DateTime(timezone=True)),
        Column("calculation_details", JSONB),
    )
    issues = Table(
        "data_quality_issues",
        metadata,
        Column("issue_id", String(36)),
        Column("scope_type", String(20)),
        Column("scope_id", String(36)),
        Column("status", String(30)),
        Column("priority", String(20)),
        Column("trigger_type", String(40)),
        Column("occurrence_count", Integer),
        Column("created_at", DateTime(timezone=True)),
        Column("updated_at", DateTime(timezone=True)),
    )
    history = Table(
        "issue_history",
        metadata,
        Column("issue_id", String(36)),
        Column("action", String(120)),
        Column("new_status", String(30)),
        Column("occurred_at", DateTime(timezone=True)),
    )
    relationships = Table(
        "issue_relationships",
        metadata,
        Column("predecessor_issue_id", String(36)),
        Column("successor_issue_id", String(36)),
        Column("relationship_type", String(40)),
    )
    configurations = Table(
        "scoring_configurations",
        metadata,
        Column("configuration_id", String(36)),
        Column("version", String(80)),
        Column("threshold_version", String(80)),
        Column("critical_upper_exclusive", Numeric(7, 4)),
        Column("risky_upper_exclusive", Numeric(7, 4)),
        Column("acceptable_upper_exclusive", Numeric(7, 4)),
        Column("dimension_weights", JSONB),
        Column("criticality_weights", JSONB),
        Column("is_active", Boolean),
        Column("created_at", DateTime(timezone=True)),
    )
    contribution_graphs = Table(
        "score_contribution_graphs",
        metadata,
        Column("quality_score_id", String(36)),
        Column("graph_version", String(40)),
        Column("official", Boolean),
        Column("graph_data", JSONB),
    )
    return {
        "datasets": datasets,
        "fields": fields,
        "rules": rules,
        "versions": versions,
        "scores": scores,
        "issues": issues,
        "history": history,
        "relationships": relationships,
        "configurations": configurations,
        "contribution_graphs": contribution_graphs,
    }


#: F-09: Tarih araligi genisledikce sinirsiz buyuyen analytics sorgulari icin
#: ust sinir. Sorgular bilerek ``ANALYTICS_ROW_LIMIT + 1`` satir ceker: fazladan
#: satir gelmesi tavanin asildigini kanitlar ve cagiran katman sonucu sessizce
#: kirpmak yerine "truncated" olarak isaretler.
ANALYTICS_ROW_LIMIT = 50_000


class PostgreSQLInsightsReader:
    """Analytics dashboard sorgulari icin salt-okunur PostgreSQL adaptoru."""

    def __init__(
        self,
        session_factory: SessionFactory,
        *,
        schema: str = DEFAULT_SCHEMA_NAME,
    ) -> None:
        self._session_factory = session_factory
        self._t = _analytics_tables(schema)

    # ── Dataset queries ──

    def list_active_datasets(
        self,
        *,
        permitted_source_ids: frozenset[str],
        permitted_dataset_ids: frozenset[str],
        source_id: str | None = None,
    ) -> list[_DatasetRow]:
        if not permitted_dataset_ids:
            return []
        t = self._t["datasets"]
        conditions = [
            t.c.status == "ACTIVE",
            t.c.dataset_id.in_(sorted(permitted_dataset_ids)),
        ]
        if source_id:
            conditions.append(t.c.data_source_id == source_id)
        elif permitted_source_ids:
            conditions.append(t.c.data_source_id.in_(sorted(permitted_source_ids)))
        with transactional_session(self._session_factory) as session:
            rows = (
                session.execute(select(t).where(and_(*conditions)).order_by(t.c.name))
                .mappings()
                .all()
            )
        return [
            _DatasetRow(
                dataset_id=str(r["dataset_id"]),
                data_source_id=str(r["data_source_id"]),
                name=str(r["name"]),
                namespace=str(r["namespace"]),
                criticality=str(r["criticality"]),
                owner_user_id=str(r["owner_user_id"]) if r["owner_user_id"] else None,
                status=str(r["status"]),
                updated_at=r["updated_at"],
            )
            for r in rows
        ]

    # ── Field queries ──

    def list_active_fields(
        self,
        *,
        dataset_ids: frozenset[str],
    ) -> list[_FieldRow]:
        if not dataset_ids:
            return []
        t = self._t["fields"]
        with transactional_session(self._session_factory) as session:
            rows = (
                session.execute(
                    select(t)
                    .where(
                        and_(
                            t.c.status == "ACTIVE",
                            t.c.dataset_id.in_(sorted(dataset_ids)),
                        )
                    )
                    .order_by(t.c.dataset_id, t.c.name)
                )
                .mappings()
                .all()
            )
        return [
            _FieldRow(
                data_field_id=str(r["data_field_id"]),
                dataset_id=str(r["dataset_id"]),
                name=str(r["name"]),
                is_sensitive=bool(r["is_sensitive"]),
                classification=str(r["classification"]),
                classification_policy_version=str(r["classification_policy_version"]),
                status=str(r["status"]),
                updated_at=r["updated_at"],
            )
            for r in rows
        ]

    # ── Rule queries ──

    def list_active_rules(
        self,
        *,
        dataset_ids: frozenset[str],
    ) -> list[_RuleRow]:
        if not dataset_ids:
            return []
        t = self._t["rules"]
        with transactional_session(self._session_factory) as session:
            rows = (
                session.execute(
                    select(t)
                    .where(
                        and_(
                            t.c.status == "ACTIVE",
                            t.c.dataset_id.in_(sorted(dataset_ids)),
                        )
                    )
                    .order_by(t.c.code)
                )
                .mappings()
                .all()
            )
        return [
            _RuleRow(
                quality_rule_id=str(r["quality_rule_id"]),
                code=str(r["code"]),
                name=str(r["name"]),
                dataset_id=str(r["dataset_id"]),
                field_ids=tuple(r["field_ids"]) if r["field_ids"] else (),
                primary_dimension=str(r["primary_dimension"]),
                status=str(r["status"]),
            )
            for r in rows
        ]

    def list_latest_versions(
        self,
        *,
        rule_ids: frozenset[str],
    ) -> list[_RuleVersionRow]:
        if not rule_ids:
            return []
        v = self._t["versions"]
        with transactional_session(self._session_factory) as session:
            # F-09: Eskiden her kuralin tum gecmis versiyonlari cekilip Python'da
            # eleniyordu; DISTINCT ON ile secim tamamen veritabaninda yapilir ve
            # kural basina yalniz bir satir aktarilir.
            rows = (
                session.execute(
                    select(v)
                    .where(v.c.quality_rule_id.in_(sorted(rule_ids)))
                    .distinct(v.c.quality_rule_id)
                    .order_by(v.c.quality_rule_id, v.c.version_no.desc())
                )
                .mappings()
                .all()
            )
        return [
            _RuleVersionRow(
                rule_version_id=str(r["rule_version_id"]),
                quality_rule_id=str(r["quality_rule_id"]),
                version_no=int(r["version_no"]),
                rule_type=str(r["rule_type"]),
                threshold=float(r["threshold"]) if r["threshold"] is not None else 0.0,
                criticality=str(r["criticality"]),
                created_at=r["created_at"],
            )
            for r in rows
        ]

    # ── Score queries ──

    def list_scores_for_rules(
        self,
        *,
        rule_version_ids: frozenset[str],
        start_at: datetime,
        end_at: datetime,
    ) -> list[_ScoreRow]:
        if not rule_version_ids:
            return []
        t = self._t["scores"]
        with transactional_session(self._session_factory) as session:
            rows = (
                session.execute(
                    select(t)
                    .where(
                        and_(
                            t.c.scope_type == "RULE",
                            t.c.rule_version_id.in_(sorted(rule_version_ids)),
                            t.c.calculated_at >= start_at,
                            t.c.calculated_at <= end_at,
                        )
                    )
                    .order_by(t.c.rule_version_id, t.c.calculated_at)
                )
                .mappings()
                .all()
            )
        return [_map_score_row(r) for r in rows]

    def list_scores_by_policy_version(
        self,
        *,
        start_at: datetime,
        end_at: datetime,
    ) -> list[_ScoreRow]:
        t = self._t["scores"]
        with transactional_session(self._session_factory) as session:
            rows = (
                session.execute(
                    select(t)
                    .where(
                        and_(
                            t.c.calculated_at >= start_at,
                            t.c.calculated_at <= end_at,
                        )
                    )
                    .order_by(t.c.policy_version, t.c.scope_type, t.c.calculated_at)
                    .limit(ANALYTICS_ROW_LIMIT + 1)
                )
                .mappings()
                .all()
            )
        return [_map_score_row(r) for r in rows]

    # ── Issue queries ──

    def list_issues_for_scopes(
        self,
        *,
        permitted_source_ids: frozenset[str],
        permitted_dataset_ids: frozenset[str],
        start_at: datetime,
        end_at: datetime,
    ) -> list[_IssueRow]:
        if not permitted_source_ids and not permitted_dataset_ids:
            return []
        t = self._t["issues"]
        conditions = [t.c.created_at >= start_at, t.c.created_at <= end_at]
        scope_filters = []
        if permitted_source_ids:
            scope_filters.append(
                and_(
                    t.c.scope_type == "SOURCE",
                    t.c.scope_id.in_(sorted(permitted_source_ids)),
                )
            )
        if permitted_dataset_ids:
            scope_filters.append(
                and_(
                    t.c.scope_type == "DATASET",
                    t.c.scope_id.in_(sorted(permitted_dataset_ids)),
                )
            )
        from sqlalchemy import or_

        conditions.append(or_(*scope_filters))
        with transactional_session(self._session_factory) as session:
            rows = (
                session.execute(
                    select(t)
                    .where(and_(*conditions))
                    .order_by(t.c.created_at.desc())
                    .limit(ANALYTICS_ROW_LIMIT + 1)
                )
                .mappings()
                .all()
            )
        return [
            _IssueRow(
                issue_id=str(r["issue_id"]),
                scope_type=str(r["scope_type"]),
                scope_id=str(r["scope_id"]),
                status=str(r["status"]),
                priority=str(r["priority"]),
                trigger_type=str(r["trigger_type"]),
                occurrence_count=int(r["occurrence_count"]),
                created_at=r["created_at"],
                updated_at=r["updated_at"],
            )
            for r in rows
        ]

    def list_history_for_issues(
        self,
        *,
        issue_ids: frozenset[str],
    ) -> list[_IssueHistoryRow]:
        if not issue_ids:
            return []
        t = self._t["history"]
        with transactional_session(self._session_factory) as session:
            rows = (
                session.execute(
                    select(t)
                    .where(t.c.issue_id.in_(sorted(issue_ids)))
                    .order_by(t.c.issue_id, t.c.occurred_at)
                )
                .mappings()
                .all()
            )
        return [
            _IssueHistoryRow(
                issue_id=str(r["issue_id"]),
                action=str(r["action"]),
                new_status=str(r["new_status"]),
                occurred_at=r["occurred_at"],
            )
            for r in rows
        ]

    def list_issue_relationships(
        self,
        *,
        issue_ids: frozenset[str],
    ) -> list[_IssueRelationshipRow]:
        if not issue_ids:
            return []
        from sqlalchemy import or_

        t = self._t["relationships"]
        with transactional_session(self._session_factory) as session:
            rows = (
                session.execute(
                    select(t).where(
                        or_(
                            t.c.predecessor_issue_id.in_(sorted(issue_ids)),
                            t.c.successor_issue_id.in_(sorted(issue_ids)),
                        )
                    )
                )
                .mappings()
                .all()
            )
        return [
            _IssueRelationshipRow(
                predecessor_issue_id=str(r["predecessor_issue_id"]),
                successor_issue_id=str(r["successor_issue_id"]),
                relationship_type=str(r["relationship_type"]),
            )
            for r in rows
        ]

    # ── Configuration queries ──

    def list_configurations(self) -> list[_ConfigurationRow]:
        t = self._t["configurations"]
        with transactional_session(self._session_factory) as session:
            rows = (
                session.execute(
                    select(t).order_by(t.c.created_at, t.c.version, t.c.configuration_id)
                )
                .mappings()
                .all()
            )
        return [_map_config_row(r) for r in rows]

    def get_configuration_by_id(self, configuration_id: str) -> _ConfigurationRow | None:
        t = self._t["configurations"]
        with transactional_session(self._session_factory) as session:
            row = (
                session.execute(select(t).where(t.c.configuration_id == configuration_id))
                .mappings()
                .one_or_none()
            )
        if row is None:
            return None
        return _map_config_row(row)

    def get_active_configuration(self) -> _ConfigurationRow | None:
        t = self._t["configurations"]
        with transactional_session(self._session_factory) as session:
            row = session.execute(select(t).where(t.c.is_active.is_(True))).mappings().one_or_none()
        if row is None:
            return None
        return _map_config_row(row)

    # ── Contribution graph queries ──

    def list_contribution_graphs(
        self,
        *,
        score_ids: frozenset[str],
    ) -> list[_ContributionGraphRow]:
        if not score_ids:
            return []
        t = self._t["contribution_graphs"]
        with transactional_session(self._session_factory) as session:
            rows = (
                session.execute(select(t).where(t.c.quality_score_id.in_(sorted(score_ids))))
                .mappings()
                .all()
            )
        return [
            _ContributionGraphRow(
                quality_score_id=str(r["quality_score_id"]),
                graph_version=str(r["graph_version"]),
                official=bool(r["official"]),
                graph_data=dict(r["graph_data"]) if r["graph_data"] else {},
            )
            for r in rows
        ]


# ── Row mappers ──


def _map_score_row(r: Any) -> _ScoreRow:
    return _ScoreRow(
        quality_score_id=str(r["quality_score_id"]),
        rule_version_id=str(r["rule_version_id"]) if r["rule_version_id"] else None,
        scope_type=str(r["scope_type"]),
        scope_id=str(r["scope_id"]) if r["scope_id"] is not None else None,
        score_value=float(r["score_value"]) if r["score_value"] is not None else None,
        score_status=str(r["score_status"]),
        measurement_status=(str(r["measurement_status"]) if r["measurement_status"] else None),
        level=str(r["level"]) if r["level"] else None,
        policy_version=str(r["policy_version"]) if r["policy_version"] else None,
        calculated_at=r["calculated_at"],
        calculation_details=dict(r["calculation_details"]) if r["calculation_details"] else {},
    )


def _map_config_row(r: Any) -> _ConfigurationRow:
    return _ConfigurationRow(
        configuration_id=str(r["configuration_id"]),
        version=str(r["version"]),
        threshold_version=str(r["threshold_version"]),
        critical_upper_exclusive=float(r["critical_upper_exclusive"]),
        risky_upper_exclusive=float(r["risky_upper_exclusive"]),
        acceptable_upper_exclusive=float(r["acceptable_upper_exclusive"]),
        dimension_weights=(dict(r["dimension_weights"]) if r["dimension_weights"] else {}),
        criticality_weights=(dict(r["criticality_weights"]) if r["criticality_weights"] else {}),
        is_active=bool(r["is_active"]),
        created_at=r["created_at"],
    )
