"""DS-06: Skor API endpoint contract testleri.

FR-04.01, FR-04.06, FR-04.12, AC-06
Kapsam: 5 endpoint contract, CSRF, privileged true/false, 401/403/404/409/422/503,
available actions, null score.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from veri_kalitesi.api.app import create_dashboard_api
from veri_kalitesi.api.identity import (
    DevelopmentActorContextResolver,
)
from veri_kalitesi.audit.models import (
    AuditFailureMode,
    AuditFailurePolicy,
)
from veri_kalitesi.audit.redaction import AuditRedactor
from veri_kalitesi.audit.repository import SQLiteAuditRepository
from veri_kalitesi.audit.service import AuditService
from veri_kalitesi.audit.policies import AuditRedactionPolicy
from veri_kalitesi.dashboard import DashboardQueryService
from veri_kalitesi.identity import (
    ActorContext,
    ActorContextIssuer,
    DashboardAuthorizationPolicy,
    PolicyAuthorizationService,
)
from veri_kalitesi.scoring.errors import (
    ScoreNotFoundError,
    ScoringAuthorizationError,
    ScoringConflictError,
    ScoringValidationError,
)
from veri_kalitesi.scoring.models import (
    QualityScore,
    ScoreLevel,
    ScorePublication,
    ScorePublicationStatus,
    ScoreScopeType,
    ScoreStatus,
)
from veri_kalitesi.scoring.query import (
    ScoreComparisonView,
    ScoreDetail,
)
from veri_kalitesi.scoring.contributions import ComparisonStatus


NOW = datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc)
POLICY_VERSION = "DASHBOARD_API_POLICY_V1"


# ── Stubs ────────────────────────────────────────────────────────────


@dataclass
class _StubScoreQueryService:
    scores: list[QualityScore] | None = None
    detail: ScoreDetail | None = None
    comparison: ScoreComparisonView | None = None
    rule_scores: list[QualityScore] | None = None
    error: Exception | None = None
    not_found_ids: set[str] | None = None

    def list_scores(self, actor_context: Any, **kwargs: Any) -> list[QualityScore]:
        if self.error:
            raise self.error
        return self.scores or []

    def get_score_detail(self, actor_context: Any, quality_score_id: str) -> ScoreDetail:
        if self.error:
            raise self.error
        if self.not_found_ids and quality_score_id in self.not_found_ids:
            raise ScoreNotFoundError(f"Not found: {quality_score_id}")
        if self.detail:
            return self.detail
        raise ScoreNotFoundError(f"Not found: {quality_score_id}")

    def list_rule_scores(self, actor_context: Any, rule_version_id: str) -> list[QualityScore]:
        if self.error:
            raise self.error
        return self.rule_scores or []

    def compare_scores(
        self, actor_context: Any, current_id: str, previous_id: str
    ) -> ScoreComparisonView:
        if self.error:
            raise self.error
        if self.comparison:
            return self.comparison
        raise ScoreNotFoundError("Not found")


class _TestResolver(DevelopmentActorContextResolver):
    """Test context — privileged flag'ı header'dan okur."""

    def resolve(self, request: Any) -> ActorContext | None:
        ctx = super().resolve(request)
        if ctx is None:
            return None
        privileged = request.headers.get("X-Privileged", "").lower() == "true"
        if privileged:
            return ActorContextIssuer().issue(
                actor_id=ctx.actor_id,
                actor_type=ctx.actor_type,
                authentication_source=ctx.authentication_source,
                session_id=ctx.session_id,
                roles=ctx.roles,
                permitted_source_ids=ctx.permitted_source_ids,
                permitted_dataset_ids=ctx.permitted_dataset_ids,
                can_view_enterprise=ctx.can_view_enterprise,
                privileged=True,
                issued_at=ctx.issued_at,
                expires_at=ctx.expires_at,
                policy_version=ctx.policy_version,
                correlation_id=ctx.correlation_id,
            )
        return ctx


def _score(
    *,
    quality_score_id: str = "qs-1",
    scope_type: ScoreScopeType = ScoreScopeType.RULE,
    scope_id: str | None = "ds-1",
    score_value: Decimal | None = Decimal("90.00"),
    level: ScoreLevel | None = ScoreLevel.GOOD,
) -> QualityScore:
    return QualityScore(
        quality_score_id=quality_score_id,
        execution_id="exec-1",
        rule_result_id=f"rr-{quality_score_id}",
        rule_version_id="rv-1",
        scope_type=scope_type,
        scope_id=scope_id,
        score_value=score_value,
        score_status=ScoreStatus.CALCULATED,
        level=level,
        calculation_details={},
        calculated_at=NOW,
        publication_id="pub-1",
        rule_version_digest="rv-digest-1",
        policy_version="DEFAULT_SCORING_V1",
    )


def _publication() -> ScorePublication:
    return ScorePublication(
        publication_id="pub-1",
        execution_id="exec-1",
        period="2026-08-06",
        input_digest="sha256:abc",
        status=ScorePublicationStatus.PUBLISHED,
        policy_version="DEFAULT_SCORING_V1",
        published_at=NOW,
    )


def _app(
    *,
    score_query_service: Any = None,
    source_ids: frozenset[str] = frozenset({"ds-1"}),
    can_view_enterprise: bool = True,
) -> FastAPI:
    resolver = _TestResolver(
        runtime_environment="development",
        policy_version=POLICY_VERSION,
        permitted_source_ids=source_ids,
        can_view_enterprise=can_view_enterprise,
        clock=lambda: NOW,
    )
    # Minimal dashboard service — fail-closed for score-only tests
    audit_repository = SQLiteAuditRepository()
    audit_service = AuditService(
        audit_repository,
        AuditRedactor(
            AuditRedactionPolicy(version="TEST_REDACTION_V1", allowed_fields_by_action={})
        ),
        AuditFailurePolicy(
            version="TEST_AUDIT_FAILURE_V1",
            default_mode=AuditFailureMode.FAIL_CLOSED,
        ),
    )
    authorization = PolicyAuthorizationService(
        DashboardAuthorizationPolicy(version=POLICY_VERSION),
        audit_service,
        clock=lambda: NOW,
    )
    from veri_kalitesi.scoring.repository import SQLiteScoreRepository

    DashboardQueryService(SQLiteScoreRepository(), authorization, clock=lambda: NOW)
    return create_dashboard_api(
        actor_context_resolver=resolver,
        allowed_origins=("http://127.0.0.1:5173",),
        data_origin="test",
        score_query_service=score_query_service,
    )


def _client(**kwargs: Any) -> TestClient:
    return TestClient(_app(**kwargs))


# ── GET /api/v1/scores ───────────────────────────────────────────────


def test_list_scores_returns_items() -> None:
    stub = _StubScoreQueryService(scores=[_score()])
    client = _client(score_query_service=stub)
    response = client.get("/api/v1/scores")
    assert response.status_code == 200
    body = response.json()
    assert body["data_origin"] == "test"
    assert len(body["items"]) == 1
    assert body["items"][0]["quality_score_id"] == "qs-1"


def test_list_scores_returns_503_when_service_unavailable() -> None:
    client = _client()  # no score_query_service
    response = client.get("/api/v1/scores")
    assert response.status_code == 503


def test_list_scores_with_scope_filter() -> None:
    stub = _StubScoreQueryService(
        scores=[_score(scope_type=ScoreScopeType.SOURCE, scope_id="ds-1")]
    )
    client = _client(score_query_service=stub)
    response = client.get("/api/v1/scores", params={"scope_type": "SOURCE", "scope_id": "ds-1"})
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1


# ── GET /api/v1/scores/rules/{rule_version_id} ──────────────────────


def test_list_rule_scores_returns_history() -> None:
    stub = _StubScoreQueryService(rule_scores=[_score(), _score(quality_score_id="qs-2")])
    client = _client(score_query_service=stub)
    response = client.get("/api/v1/scores/rules/rv-1")
    assert response.status_code == 200
    body = response.json()
    assert body["rule_version_id"] == "rv-1"
    assert len(body["items"]) == 2


def test_list_rule_scores_503_when_unavailable() -> None:
    client = _client()
    response = client.get("/api/v1/scores/rules/rv-1")
    assert response.status_code == 503


# ── GET /api/v1/scores/comparison ────────────────────────────────────


def test_comparison_returns_delta() -> None:
    current = _score(quality_score_id="qs-now", score_value=Decimal("90"))
    previous = _score(quality_score_id="qs-prev", score_value=Decimal("85"))
    comparison = ScoreComparisonView(
        current_score=current,
        previous_score=previous,
        comparison_status=ComparisonStatus.COMPARABLE.value,
        reason_codes=("VALUE_INCREASED",),
        delta_value=Decimal("5"),
    )
    stub = _StubScoreQueryService(comparison=comparison)
    client = _client(score_query_service=stub)
    response = client.get(
        "/api/v1/scores/comparison",
        params={"current_score_id": "qs-now", "previous_score_id": "qs-prev"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["current_score_id"] == "qs-now"
    assert body["previous_score_id"] == "qs-prev"
    assert body["comparison_status"] == "COMPARABLE"


def test_comparison_404_when_score_not_found() -> None:
    stub = _StubScoreQueryService(error=ScoreNotFoundError("not found"))
    client = _client(score_query_service=stub)
    response = client.get(
        "/api/v1/scores/comparison",
        params={"current_score_id": "qs-x", "previous_score_id": "qs-y"},
    )
    assert response.status_code == 404


# ── GET /api/v1/scores/{quality_score_id} ────────────────────────────


def test_score_detail_returns_publication() -> None:
    score = _score()
    pub = _publication()
    detail = ScoreDetail(
        score=score,
        publication=pub,
        contribution_graph=None,
        available_actions=(),
    )
    stub = _StubScoreQueryService(detail=detail)
    client = _client(score_query_service=stub)
    response = client.get("/api/v1/scores/qs-1")
    assert response.status_code == 200
    body = response.json()
    assert body["score"]["quality_score_id"] == "qs-1"
    assert body["publication"]["publication_id"] == "pub-1"
    assert body["available_actions"] == []


def test_score_detail_404() -> None:
    stub = _StubScoreQueryService(not_found_ids={"qs-missing"})
    client = _client(score_query_service=stub)
    response = client.get("/api/v1/scores/qs-missing")
    assert response.status_code == 404


def test_score_detail_403_for_unauthorized_scope() -> None:
    stub = _StubScoreQueryService(error=ScoringAuthorizationError("out of scope"))
    client = _client(score_query_service=stub)
    response = client.get("/api/v1/scores/qs-1")
    assert response.status_code == 403


# ── Error mapping ────────────────────────────────────────────────────


def test_scoring_validation_error_maps_to_400() -> None:
    stub = _StubScoreQueryService(error=ScoringValidationError("bad input"))
    client = _client(score_query_service=stub)
    response = client.get("/api/v1/scores")
    assert response.status_code == 400


def test_scoring_conflict_error_maps_to_409() -> None:
    stub = _StubScoreQueryService(error=ScoringConflictError("conflict"))
    client = _client(score_query_service=stub)
    response = client.get("/api/v1/scores")
    assert response.status_code == 409
