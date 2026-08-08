"""Skor/scores alanı HTTP route kayıtları."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Protocol

from fastapi import FastAPI, Query as FastApiQuery, Request, Response

from veri_kalitesi.api.models import (
    ScoreComparisonResponse,
    ScoreDetailResponse,
    ScoreItemResponse,
    ScoreListResponse,
    ScorePublicationResponse,
    ScoreReproductionResponse,
    ScoreRuleHistoryResponse,
)
from veri_kalitesi.dashboard import DashboardQueryError
from veri_kalitesi.identity import ActorContext
from veri_kalitesi.scoring.errors import ScoringAuthorizationError
from veri_kalitesi.scoring.models import ScoreScopeType
from veri_kalitesi.scoring.query import ScoreQueryService


class _Resolver(Protocol):
    def resolve(self, request: Request) -> ActorContext | None: ...


def register_scores_routes(
    app: FastAPI,
    *,
    score_query_service: ScoreQueryService | None,
    score_publication_service: Any | None,
    resolver: _Resolver,
    data_origin: str,
) -> None:
    """Skor alanının route'larını FastAPI uygulamasına kaydeder."""

    @app.get(
        "/api/v1/scores",
        response_model=ScoreListResponse,
        tags=["scores"],
    )
    async def list_scores(
        request: Request,
        scope_type: Annotated[str | None, FastApiQuery()] = None,
        scope_id: Annotated[str | None, FastApiQuery()] = None,
        period_start: Annotated[datetime | None, FastApiQuery()] = None,
        period_end: Annotated[datetime | None, FastApiQuery()] = None,
        limit: Annotated[int, FastApiQuery(ge=1, le=200)] = 50,
    ) -> ScoreListResponse:
        if score_query_service is None:
            raise DashboardQueryError(
                "Score query service is not available.", request.state.correlation_id
            )
        actor_context = resolver.resolve(request)
        parsed_scope_type = ScoreScopeType(scope_type) if scope_type else None
        scores = score_query_service.list_scores(
            actor_context,
            scope_type=parsed_scope_type,
            scope_id=scope_id,
            period_start=period_start,
            period_end=period_end,
            limit=limit,
        )
        return ScoreListResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            items=tuple(ScoreItemResponse.from_domain(s) for s in scores),
        )

    @app.get(
        "/api/v1/scores/rules/{rule_version_id}",
        response_model=ScoreRuleHistoryResponse,
        tags=["scores"],
    )
    async def list_rule_scores(
        request: Request,
        rule_version_id: str,
    ) -> ScoreRuleHistoryResponse:
        if score_query_service is None:
            raise DashboardQueryError(
                "Score query service is not available.", request.state.correlation_id
            )
        actor_context = resolver.resolve(request)
        scores = score_query_service.list_rule_scores(actor_context, rule_version_id)
        return ScoreRuleHistoryResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            rule_version_id=rule_version_id,
            items=tuple(ScoreItemResponse.from_domain(s) for s in scores),
        )

    @app.get(
        "/api/v1/scores/comparison",
        response_model=ScoreComparisonResponse,
        tags=["scores"],
    )
    async def compare_score_endpoint(
        request: Request,
        current_score_id: Annotated[str, FastApiQuery()],
        previous_score_id: Annotated[str, FastApiQuery()],
    ) -> ScoreComparisonResponse:
        if score_query_service is None:
            raise DashboardQueryError(
                "Score query service is not available.", request.state.correlation_id
            )
        actor_context = resolver.resolve(request)
        result = score_query_service.compare_scores(
            actor_context, current_score_id, previous_score_id
        )
        return ScoreComparisonResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            current_score_id=result.current_score.quality_score_id,
            previous_score_id=result.previous_score.quality_score_id,
            comparison_status=result.comparison_status,
            reason_codes=result.reason_codes,
            delta_value=float(result.delta_value) if result.delta_value is not None else None,
        )

    @app.get(
        "/api/v1/scores/{quality_score_id}",
        response_model=ScoreDetailResponse,
        tags=["scores"],
    )
    async def get_score_detail(
        request: Request,
        quality_score_id: str,
    ) -> ScoreDetailResponse:
        if score_query_service is None:
            raise DashboardQueryError(
                "Score query service is not available.", request.state.correlation_id
            )
        actor_context = resolver.resolve(request)
        detail = score_query_service.get_score_detail(actor_context, quality_score_id)
        pub_response = None
        if detail.publication is not None:
            pub_response = ScorePublicationResponse(
                publication_id=detail.publication.publication_id,
                execution_id=detail.publication.execution_id,
                period=detail.publication.period,
                status=detail.publication.status.value,
                policy_version=detail.publication.policy_version,
                published_at=detail.publication.published_at,
                superseded_at=detail.publication.superseded_at,
            )
        return ScoreDetailResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            score=ScoreItemResponse.from_domain(detail.score),
            publication=pub_response,
            available_actions=detail.available_actions,
            has_contribution_graph=detail.contribution_graph is not None,
        )

    @app.post(
        "/api/v1/scores/{quality_score_id}/reproduction",
        response_model=ScoreReproductionResponse,
        tags=["scores"],
    )
    async def reproduce_score(
        request: Request,
        response: Response,
        quality_score_id: str,
    ) -> ScoreReproductionResponse:
        if score_publication_service is None:
            raise DashboardQueryError(
                "Score publication service is not available.", request.state.correlation_id
            )
        actor_context = resolver.resolve(request)
        if actor_context is None or not getattr(actor_context, "privileged", False):
            raise ScoringAuthorizationError(
                "Privileged actor context is required for reproduction."
            )
        result = score_publication_service.reproduce_score(quality_score_id)
        return ScoreReproductionResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            original_score_id=result.original_score_id,
            matches=result.matches,
            delta_value=result.delta_value,
            delta_level=result.delta_level,
            reason_codes=result.reason_codes,
            reproduced_value=result.reproduced_score.score_value,
            reproduced_level=(
                result.reproduced_score.level.value if result.reproduced_score.level else None
            ),
        )
