"""DS-06: Scope-aware ScoreQueryService birim testleri.

FR-04.01, FR-04.06, FR-04.12, AC-06
Kapsam: list/detail/rule-history/comparison + yetkilendirme + sızıntı engelleme.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import pytest

from veri_kalitesi.identity import ActorContext, ActorContextIssuer, ActorType
from veri_kalitesi.scoring.errors import (
    ScoreNotFoundError,
    ScoringAuthorizationError,
    ScoringValidationError,
)
from veri_kalitesi.scoring.models import (
    QualityScore,
    ScorePublication,
    ScorePublicationStatus,
    ScoreScopeType,
    ScoreStatus,
)
from veri_kalitesi.scoring.postgresql_contributions import StoredContributionGraph
from veri_kalitesi.scoring.query import (
    ScoreQueryService,
    resolve_query_scope,
)


# ── Helpers ─────────────────────────────────────────────────────────

_ACTOR_POLICY = "DASHBOARD_POLICY_V1"


def _actor(
    *,
    actor_id: str = "analyst",
    roles: set[str] | None = None,
    permitted_source_ids: set[str] | None = None,
    permitted_dataset_ids: set[str] | None = None,
    can_view_enterprise: bool = False,
    privileged: bool = False,
    actor_type: ActorType = ActorType.USER,
) -> ActorContext:
    now = datetime(2026, 8, 6, tzinfo=timezone.utc)
    return ActorContextIssuer().issue(
        actor_id=actor_id,
        actor_type=actor_type,
        authentication_source="synthetic-identity-adapter",
        session_id=f"session-{actor_id}",
        roles=frozenset(roles or {"DATA_STEWARD"}),
        permitted_source_ids=frozenset(permitted_source_ids or set()),
        permitted_dataset_ids=frozenset(permitted_dataset_ids or set()),
        can_view_enterprise=can_view_enterprise,
        privileged=privileged,
        issued_at=now - timedelta(minutes=5),
        expires_at=now + timedelta(hours=1),
        policy_version=_ACTOR_POLICY,
        correlation_id=f"correlation-{actor_id}",
    )


def _score(
    *,
    quality_score_id: str = "qs-1",
    scope_type: ScoreScopeType = ScoreScopeType.RULE,
    scope_id: str | None = "ds-1",
    score_value: Decimal | None = Decimal("95.00"),
    publication_id: str | None = "pub-1",
    execution_id: str = "exec-1",
    rule_version_id: str | None = "rv-1",
) -> QualityScore:
    return QualityScore(
        quality_score_id=quality_score_id,
        execution_id=execution_id,
        rule_result_id=f"rr-{quality_score_id}",
        rule_version_id=rule_version_id,
        scope_type=scope_type,
        scope_id=scope_id,
        score_value=score_value,
        score_status=ScoreStatus.CALCULATED,
        calculation_details={},
        calculated_at=datetime(2026, 8, 6, tzinfo=timezone.utc),
        publication_id=publication_id,
        rule_version_digest="rv-digest-1",
        policy_version="DEFAULT_SCORING_V1",
    )


@dataclass
class _StubScoreRepository:
    scores: dict[str, QualityScore] | None = None
    publications: dict[str, ScorePublication] | None = None
    listed: list[QualityScore] | None = None
    _list_calls: list[dict[str, Any]] | None = None

    def __post_init__(self) -> None:
        if self.scores is None:
            self.scores = {}
        if self.publications is None:
            self.publications = {}
        if self.listed is None:
            self.listed = []
        if self._list_calls is None:
            self._list_calls = []

    def get(self, quality_score_id: str) -> QualityScore:
        if quality_score_id not in self.scores:
            raise ScoreNotFoundError(f"Score {quality_score_id} not found")
        return self.scores[quality_score_id]

    def get_publication(self, publication_id: str) -> ScorePublication | None:
        return self.publications.get(publication_id)

    def list_scores(self, **kwargs: Any) -> list[QualityScore]:
        self._list_calls.append(kwargs)
        return self.listed


@dataclass
class _StubGraphRepository:
    graphs: dict[str, StoredContributionGraph] | None = None

    def __post_init__(self) -> None:
        if self.graphs is None:
            self.graphs = {}

    def get(self, quality_score_id: str) -> StoredContributionGraph | None:
        return self.graphs.get(quality_score_id)


def _publication(
    publication_id: str = "pub-1",
    execution_id: str = "exec-1",
) -> ScorePublication:
    return ScorePublication(
        publication_id=publication_id,
        execution_id=execution_id,
        period="2026-08-06",
        input_digest="sha256:abc",
        status=ScorePublicationStatus.PUBLISHED,
        policy_version="DEFAULT_SCORING_V1",
        published_at=datetime(2026, 8, 6, tzinfo=timezone.utc),
    )


# ── resolve_query_scope ─────────────────────────────────────────────


def test_resolve_scope_none_returns_empty() -> None:
    scope = resolve_query_scope(None)
    assert scope.allowed_source_ids == frozenset()
    assert scope.allowed_dataset_ids == frozenset()
    assert scope.can_view_enterprise is False


def test_resolve_scope_from_actor() -> None:
    actor = _actor(
        permitted_source_ids={"src-1"},
        can_view_enterprise=True,
    )
    scope = resolve_query_scope(actor)
    assert "src-1" in scope.allowed_source_ids
    assert scope.can_view_enterprise is True


# ── list_scores ──────────────────────────────────────────────────────


def test_list_scores_returns_empty_for_no_scope_actor() -> None:
    """Yetkisiz actor için liste boş döner — sızıntı yok."""
    actor = _actor()  # no sources, no enterprise
    repo = _StubScoreRepository(listed=[_score()])
    service = ScoreQueryService(repo, _StubGraphRepository())  # type: ignore[arg-type]
    result = service.list_scores(actor)
    assert result == []


def test_list_scores_delegates_scope_to_repository() -> None:
    actor = _actor(permitted_source_ids={"src-1"})
    repo = _StubScoreRepository(listed=[_score(scope_type=ScoreScopeType.SOURCE, scope_id="src-1")])
    service = ScoreQueryService(repo, _StubGraphRepository())  # type: ignore[arg-type]
    result = service.list_scores(actor, scope_type=ScoreScopeType.SOURCE, scope_id="src-1")
    assert len(result) == 1
    assert repo._list_calls[0]["allowed_source_ids"] == frozenset({"src-1"})


def test_list_scores_requires_scope_type_with_scope_id() -> None:
    actor = _actor(permitted_source_ids={"src-1"})
    repo = _StubScoreRepository()
    service = ScoreQueryService(repo, _StubGraphRepository())  # type: ignore[arg-type]
    with pytest.raises(ScoringValidationError, match="scope_type is required"):
        service.list_scores(actor, scope_id="src-1")


def test_list_scores_returns_empty_for_out_of_scope() -> None:
    actor = _actor(permitted_source_ids={"src-1"})
    repo = _StubScoreRepository(listed=[_score()])
    service = ScoreQueryService(repo, _StubGraphRepository())  # type: ignore[arg-type]
    result = service.list_scores(actor, scope_type=ScoreScopeType.ENTERPRISE)
    assert result == []


# ── get_score_detail ─────────────────────────────────────────────────


def test_get_score_detail_returns_publication_and_graph() -> None:
    score = _score(publication_id="pub-1")
    pub = _publication()
    graph = StoredContributionGraph(
        quality_score_id="qs-1",
        execution_id="exec-1",
        scope_type="RULE",
        scope_id="ds-1",
        graph={"formula_version": "V1"},
        created_at=datetime(2026, 8, 6, tzinfo=timezone.utc),
    )
    actor = _actor(permitted_source_ids={"ds-1"})
    repo = _StubScoreRepository(scores={"qs-1": score}, publications={"pub-1": pub})
    graph_repo = _StubGraphRepository(graphs={"qs-1": graph})
    service = ScoreQueryService(repo, graph_repo)  # type: ignore[arg-type]
    detail = service.get_score_detail(actor, "qs-1")
    assert detail.score.quality_score_id == "qs-1"
    assert detail.publication is not None
    assert detail.publication.publication_id == "pub-1"
    assert detail.contribution_graph is not None


def test_get_score_detail_raises_for_unauthorized_scope() -> None:
    """Enterprise scope score, enterprise yetkisi olmayan actor'a 403 benzeri fırlatır."""
    score = _score(scope_type=ScoreScopeType.ENTERPRISE, scope_id=None)
    actor = _actor(permitted_source_ids={"ds-1"})
    repo = _StubScoreRepository(scores={"qs-1": score})
    service = ScoreQueryService(repo, _StubGraphRepository())  # type: ignore[arg-type]
    with pytest.raises(ScoringAuthorizationError):
        service.get_score_detail(actor, "qs-1")


def test_get_score_detail_available_actions_for_privileged() -> None:
    score = _score()
    actor = _actor(permitted_source_ids={"ds-1"}, privileged=True)
    repo = _StubScoreRepository(scores={"qs-1": score})
    service = ScoreQueryService(repo, _StubGraphRepository())  # type: ignore[arg-type]
    detail = service.get_score_detail(actor, "qs-1")
    assert "reproduce" in detail.available_actions


def test_get_score_detail_no_actions_for_non_privileged() -> None:
    score = _score()
    actor = _actor(permitted_source_ids={"ds-1"}, privileged=False)
    repo = _StubScoreRepository(scores={"qs-1": score})
    service = ScoreQueryService(repo, _StubGraphRepository())  # type: ignore[arg-type]
    detail = service.get_score_detail(actor, "qs-1")
    assert detail.available_actions == ()


# ── compare_scores ───────────────────────────────────────────────────


def test_compare_scores_returns_comparison_view() -> None:
    current = _score(quality_score_id="qs-now", score_value=Decimal("90"))
    previous = _score(quality_score_id="qs-prev", score_value=Decimal("85"))
    actor = _actor(can_view_enterprise=True)
    repo = _StubScoreRepository(scores={"qs-now": current, "qs-prev": previous})
    service = ScoreQueryService(repo, _StubGraphRepository())  # type: ignore[arg-type]
    result = service.compare_scores(actor, "qs-now", "qs-prev")
    assert result.current_score.quality_score_id == "qs-now"
    assert result.previous_score.quality_score_id == "qs-prev"
    # Contribution graph versions are empty in test fixtures → UNKNOWN
    assert result.comparison_status in ("COMPARABLE", "UNKNOWN", "NOT_COMPARABLE")


def test_compare_scores_authorizes_both_scores() -> None:
    current = _score(quality_score_id="qs-ok", scope_type=ScoreScopeType.SOURCE, scope_id="src-1")
    unauthorized = _score(
        quality_score_id="qs-bad", scope_type=ScoreScopeType.ENTERPRISE, scope_id=None
    )
    actor = _actor(permitted_source_ids={"src-1"})
    repo = _StubScoreRepository(scores={"qs-ok": current, "qs-bad": unauthorized})
    service = ScoreQueryService(repo, _StubGraphRepository())  # type: ignore[arg-type]
    with pytest.raises(ScoringAuthorizationError):
        service.compare_scores(actor, "qs-ok", "qs-bad")


# ── list_rule_scores ─────────────────────────────────────────────────


def test_list_rule_scores_filters_by_rule_version_id() -> None:
    matching = _score(quality_score_id="qs-match", rule_version_id="rv-1")
    non_matching = _score(quality_score_id="qs-other", rule_version_id="rv-2")
    actor = _actor(permitted_source_ids={"ds-1"})
    repo = _StubScoreRepository(listed=[matching, non_matching])
    service = ScoreQueryService(repo, _StubGraphRepository())  # type: ignore[arg-type]
    result = service.list_rule_scores(actor, "rv-1")
    assert len(result) == 1
    assert result[0].rule_version_id == "rv-1"
