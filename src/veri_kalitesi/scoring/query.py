"""Scope-aware skor sorgu servisi — actor yetki ve kapsam filtreli."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Literal

from veri_kalitesi.identity import ActorContext
from veri_kalitesi.rules.models import QualityRule
from veri_kalitesi.scoring.contributions import compare_scores
from veri_kalitesi.scoring.errors import (
    ScoringAuthorizationError,
    ScoringValidationError,
)
from veri_kalitesi.scoring.models import (
    QualityScore,
    ScorePublication,
    ScoreScopeType,
)
from veri_kalitesi.scoring.postgresql_contributions import (
    PostgreSQLContributionGraphRepository,
    StoredContributionGraph,
)
from veri_kalitesi.scoring.postgresql_repository import PostgreSQLScoreRepository


class ScoreQueryRuleCatalog:
    """Rule chain resolution için minimal protokol."""

    def get_rule(self, quality_rule_id: str) -> QualityRule:
        raise NotImplementedError


@dataclass(frozen=True)
class ScoreQueryScope:
    """Actor'ın erişebildiği skor kapsamları."""

    allowed_source_ids: frozenset[str]
    allowed_dataset_ids: frozenset[str]
    can_view_enterprise: bool


@dataclass(frozen=True)
class ScoreDetail:
    """Tek skor detay görünümü."""

    score: QualityScore
    publication: ScorePublication | None
    contribution_graph: StoredContributionGraph | None
    available_actions: tuple[str, ...]


@dataclass(frozen=True)
class ScoreComparisonView:
    """İki skor karşılaştırma görünümü."""

    current_score: QualityScore
    previous_score: QualityScore
    comparison_status: str
    reason_codes: tuple[str, ...]
    delta_value: Decimal | None


@dataclass(frozen=True)
class ScoreReproductionView:
    """Yeniden üretim doğrulama görünümü."""

    original_score_id: str
    matches: bool
    delta_value: Decimal | None
    delta_level: bool
    reason_codes: tuple[str, ...]
    reproduced_value: Decimal | None
    reproduced_level: str | None


def resolve_query_scope(actor_context: ActorContext | None) -> ScoreQueryScope:
    """ActorContext'ten skor sorgu kapsamını çıkarır."""
    if actor_context is None:
        return ScoreQueryScope(
            allowed_source_ids=frozenset(),
            allowed_dataset_ids=frozenset(),
            can_view_enterprise=False,
        )
    return ScoreQueryScope(
        allowed_source_ids=actor_context.permitted_source_ids,
        allowed_dataset_ids=actor_context.permitted_dataset_ids,
        can_view_enterprise=actor_context.can_view_enterprise,
    )


class ScoreQueryService:
    """Actor scope-safe skor sorgulama servisi.

    List, detail, rule history ve comparison sorgularını yetkilendirir.
    """

    def __init__(
        self,
        score_repository: PostgreSQLScoreRepository,
        contribution_graph_repository: PostgreSQLContributionGraphRepository,
        *,
        rule_catalog: ScoreQueryRuleCatalog | None = None,
    ) -> None:
        self.score_repository = score_repository
        self.contribution_graph_repository = contribution_graph_repository
        self.rule_catalog = rule_catalog

    def list_scores(
        self,
        actor_context: ActorContext | None,
        *,
        scope_type: ScoreScopeType | None = None,
        scope_id: str | None = None,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
        score_status: str | None = None,
        limit: int = 50,
    ) -> list[QualityScore]:
        scope = resolve_query_scope(actor_context)
        if not _has_any_scope(scope):
            return []
        if scope_id is not None and scope_type is None:
            raise ScoringValidationError("scope_type is required with scope_id.")
        if scope_type is not None and not _scope_permitted(scope_type, scope_id, scope):
            return []
        return self.score_repository.list_scores(
            scope_type=scope_type,
            scope_id=scope_id,
            period_start=period_start,
            period_end=period_end,
            score_status=score_status,
            limit=limit,
            allowed_source_ids=scope.allowed_source_ids or None,
            allowed_dataset_ids=scope.allowed_dataset_ids or None,
            can_view_enterprise=scope.can_view_enterprise,
        )

    def get_score_detail(
        self,
        actor_context: ActorContext | None,
        quality_score_id: str,
    ) -> ScoreDetail:
        scope = resolve_query_scope(actor_context)
        score = self.score_repository.get(quality_score_id)
        _assert_score_in_scope(score, scope)
        publication = None
        if score.publication_id:
            publication = self.score_repository.get_publication(score.publication_id)
        graph = self.contribution_graph_repository.get(quality_score_id)
        available_actions = _compute_available_actions(actor_context, score, scope)
        return ScoreDetail(
            score=score,
            publication=publication,
            contribution_graph=graph,
            available_actions=available_actions,
        )

    def list_rule_scores(
        self,
        actor_context: ActorContext | None,
        rule_version_id: str,
    ) -> list[QualityScore]:
        scope = resolve_query_scope(actor_context)
        if self.rule_catalog is not None:
            self._assert_rule_in_scope(rule_version_id, scope)
        all_scores = self.score_repository.list_scores(
            scope_type=ScoreScopeType.RULE,
            scope_id=None,
            limit=200,
            allowed_source_ids=scope.allowed_source_ids or None,
            allowed_dataset_ids=scope.allowed_dataset_ids or None,
            can_view_enterprise=scope.can_view_enterprise,
        )
        return [s for s in all_scores if s.rule_version_id == rule_version_id]

    def compare_scores(
        self,
        actor_context: ActorContext | None,
        current_score_id: str,
        previous_score_id: str,
    ) -> ScoreComparisonView:
        scope = resolve_query_scope(actor_context)
        current = self.score_repository.get(current_score_id)
        previous = self.score_repository.get(previous_score_id)
        _assert_score_in_scope(current, scope)
        _assert_score_in_scope(previous, scope)
        comparison = compare_scores(current, previous)
        return ScoreComparisonView(
            current_score=current,
            previous_score=previous,
            comparison_status=comparison.status.value,
            reason_codes=comparison.reason_codes,
            delta_value=comparison.delta,
        )

    def get_score_trend(
        self,
        actor_context: ActorContext | None,
        *,
        scope_type: ScoreScopeType,
        scope_id: str | None = None,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
        granularity: Literal["day", "week", "month"] = "day",
    ) -> list[dict]:
        """Return aggregated score trend for a scope over a time range."""
        scores = self.list_scores(
            actor_context,
            scope_type=scope_type,
            scope_id=scope_id,
            period_start=period_start,
            period_end=period_end,
            limit=1000,
        )
        if not scores:
            return []
        # Sort by calculated_at ascending
        scores.sort(key=lambda s: s.calculated_at)
        # Group by granularity bucket
        buckets: dict[datetime, list[QualityScore]] = {}
        for score in scores:
            key = _bucket_key(score.calculated_at, granularity)
            buckets.setdefault(key, []).append(score)
        # Build trend points
        result: list[dict] = []
        prev_value: Decimal | None = None
        for key in sorted(buckets.keys()):
            bucket_scores = buckets[key]
            # Use the last score in the bucket as the representative value
            latest = bucket_scores[-1]
            value = latest.score_value
            level = latest.level.value if latest.level else None
            change: Decimal | None = None
            if value is not None and prev_value is not None:
                change = value - prev_value
            result.append(
                {
                    "timestamp": key,
                    "score_value": float(value) if value is not None else None,
                    "level": level,
                    "change": float(change) if change is not None else None,
                    "score_count": len(bucket_scores),
                }
            )
            if value is not None:
                prev_value = value
        return result

    def _assert_rule_in_scope(self, rule_version_id: str, scope: ScoreQueryScope) -> None:
        if self.rule_catalog is None:
            return
        try:
            rule = self.rule_catalog.get_rule(rule_version_id)
        except Exception:
            return
        dataset_id = rule.dataset_id
        if scope.allowed_dataset_ids and dataset_id in scope.allowed_dataset_ids:
            return
        if scope.allowed_source_ids:
            return
        if scope.can_view_enterprise:
            return
        raise ScoringAuthorizationError("Actor does not have scope for the requested rule.")


def _has_any_scope(scope: ScoreQueryScope) -> bool:
    return bool(scope.allowed_source_ids or scope.allowed_dataset_ids or scope.can_view_enterprise)


def _scope_permitted(
    scope_type: ScoreScopeType,
    scope_id: str | None,
    scope: ScoreQueryScope,
) -> bool:
    if scope_type is ScoreScopeType.ENTERPRISE:
        return scope.can_view_enterprise
    if scope_type is ScoreScopeType.SOURCE:
        return bool(scope.allowed_source_ids and scope_id in scope.allowed_source_ids)
    if scope_type in (
        ScoreScopeType.RULE,
        ScoreScopeType.DATASET,
        ScoreScopeType.DIMENSION,
    ):
        return bool(
            scope.allowed_dataset_ids
            and (scope_id is None or scope_id in scope.allowed_dataset_ids)
        )
    return False


def _assert_score_in_scope(score: QualityScore, scope: ScoreQueryScope) -> None:
    if score.scope_type is ScoreScopeType.ENTERPRISE:
        if not scope.can_view_enterprise:
            raise ScoringAuthorizationError("Actor does not have enterprise score scope.")
        return
    if score.scope_type is ScoreScopeType.SOURCE:
        if scope.allowed_source_ids and score.scope_id in scope.allowed_source_ids:
            return
        raise ScoringAuthorizationError("Actor does not have source score scope.")
    if score.scope_type in (
        ScoreScopeType.RULE,
        ScoreScopeType.DATASET,
        ScoreScopeType.DIMENSION,
    ):
        if scope.allowed_dataset_ids and (
            score.scope_id is None or score.scope_id in scope.allowed_dataset_ids
        ):
            return
        if scope.allowed_source_ids:
            return
        if scope.can_view_enterprise:
            return
        raise ScoringAuthorizationError("Actor does not have dataset/rule score scope.")


def _compute_available_actions(
    actor_context: ActorContext | None,
    score: QualityScore,
    scope: ScoreQueryScope,
) -> tuple[str, ...]:
    return ()


def _bucket_key(dt: datetime, granularity: Literal["day", "week", "month"]) -> datetime:
    """Truncate a datetime to the start of its granularity bucket."""
    if granularity == "day":
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)
    if granularity == "week":
        # Week starts on Monday
        start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        days_since_monday = start.weekday()
        return start - timedelta(days=days_since_monday)
    if granularity == "month":
        return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)
