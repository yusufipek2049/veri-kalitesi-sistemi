"""Skor/scores alanı HTTP route kayıtları."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Any, Protocol

from fastapi import FastAPI, Query as FastApiQuery, Request

from veri_kalitesi.api.models import (
    ScoreComparisonResponse,
    ScoreDetailResponse,
    ScoreItemResponse,
    ScoreListResponse,
    ScorePublicationResponse,
    ScoreRuleHistoryResponse,
    ScoreTrendPointResponse,
    ScoreTrendResponse,
)
from veri_kalitesi.dashboard import DashboardQueryError
from veri_kalitesi.identity import ActorContext
from veri_kalitesi.scoring.models import ScoreScopeType, thaw
from veri_kalitesi.scoring.query import ScoreQueryService


class _Resolver(Protocol):
    def resolve(self, request: Request) -> ActorContext | None: ...


class _CatalogReader(Protocol):
    """Katalog okuma için minimal protokol — dataset/source çözümleme."""

    def get_dataset(self, dataset_id: str) -> object: ...
    def get_data_source(self, data_source_id: str) -> object: ...


class _RuleVersionReader(Protocol):
    """Kural sürüm okuma için minimal protokol — rule code çözümleme."""

    def get_version(self, rule_version_id: str) -> object: ...


@dataclass(frozen=True)
class _ScopeDisplayInfo:
    """Çözümlenmiş kapsam gösterim bilgisi."""

    display_name: str | None
    parent_name: str | None


def _resolve_scope_display(
    scope_type: str,
    scope_id: str | None,
    rule_version_id: str | None,
    *,
    catalog_reader: _CatalogReader | None,
    rule_version_reader: _RuleVersionReader | None,
) -> _ScopeDisplayInfo:
    """Skor kapsamına göre insan-okunur isim ve üst kapsam adını çözümler."""
    if scope_id is None:
        return _ScopeDisplayInfo(display_name=None, parent_name=None)

    display_name: str | None
    try:
        if scope_type == ScoreScopeType.DATASET.value and catalog_reader is not None:
            dataset = catalog_reader.get_dataset(scope_id)
            display_name = f"{dataset.namespace}.{dataset.name}"  # type: ignore[attr-defined]
            parent_name: str | None = None
            try:
                source = catalog_reader.get_data_source(dataset.data_source_id)  # type: ignore[attr-defined]
                parent_name = source.name  # type: ignore[attr-defined]
            except Exception:
                pass
            return _ScopeDisplayInfo(display_name=display_name, parent_name=parent_name)

        if scope_type == ScoreScopeType.SOURCE.value and catalog_reader is not None:
            source = catalog_reader.get_data_source(scope_id)
            return _ScopeDisplayInfo(display_name=source.name, parent_name=None)  # type: ignore[attr-defined]

        if scope_type == ScoreScopeType.RULE.value:
            display_name = None
            if rule_version_id is not None and rule_version_reader is not None:
                try:
                    version = rule_version_reader.get_version(rule_version_id)
                    display_name = version.definition.get("code") or version.rule_version_id  # type: ignore[attr-defined]
                except Exception:
                    pass
            return _ScopeDisplayInfo(display_name=display_name, parent_name=None)

    except Exception:
        return _ScopeDisplayInfo(display_name=None, parent_name=None)

    return _ScopeDisplayInfo(display_name=None, parent_name=None)


def _resolve_component_name(
    component: dict[str, Any],
    *,
    catalog_reader: _CatalogReader | None,
    rule_version_reader: _RuleVersionReader | None,
) -> str | None:
    """Katkı bileşeninin referansını insan-okunur isme çözümler."""
    component_type = component.get("component_type")
    try:
        if component_type == "RULE" and rule_version_reader is not None:
            rule_version_id = component.get("rule_version_id")
            if isinstance(rule_version_id, str) and rule_version_id:
                version = rule_version_reader.get_version(rule_version_id)
                definition = version.definition  # type: ignore[attr-defined]
                name = definition.get("name") or definition.get("code")
                if isinstance(name, str) and name:
                    return name
        elif component_type == "DATASET" and catalog_reader is not None:
            dataset_id = component.get("dataset_id")
            if isinstance(dataset_id, str) and dataset_id:
                dataset = catalog_reader.get_dataset(dataset_id)
                return f"{dataset.namespace}.{dataset.name}"  # type: ignore[attr-defined]
        elif component_type == "SOURCE" and catalog_reader is not None:
            data_source_id = component.get("data_source_id")
            if isinstance(data_source_id, str) and data_source_id:
                source = catalog_reader.get_data_source(data_source_id)
                return source.name  # type: ignore[attr-defined,no-any-return]
    except Exception:
        return None
    return None


def _enrich_contribution_graph(
    graph: dict[str, Any],
    *,
    catalog_reader: _CatalogReader | None,
    rule_version_reader: _RuleVersionReader | None,
) -> dict[str, Any]:
    """Katkı grafiği bileşenlerine insan-okunur isim ekler."""
    enriched_graph = dict(graph)
    components = graph.get("components")
    if isinstance(components, list):
        enriched_components: list[Any] = []
        for component in components:
            if isinstance(component, dict):
                enriched_component = dict(component)
                enriched_component["component_name"] = _resolve_component_name(
                    component,
                    catalog_reader=catalog_reader,
                    rule_version_reader=rule_version_reader,
                )
                enriched_components.append(enriched_component)
            else:
                enriched_components.append(component)
        enriched_graph["components"] = enriched_components
    return enriched_graph


def _apply_scope_display(
    item: ScoreItemResponse,
    *,
    catalog_reader: _CatalogReader | None,
    rule_version_reader: _RuleVersionReader | None,
) -> ScoreItemResponse:
    """ScoreItemResponse'a kapsam gösterim bilgisini ekler."""
    info = _resolve_scope_display(
        item.scope_type,
        item.scope_id,
        item.rule_version_id,
        catalog_reader=catalog_reader,
        rule_version_reader=rule_version_reader,
    )
    return item.with_scope_display(
        scope_display_name=info.display_name,
        scope_parent_name=info.parent_name,
    )


def register_scores_routes(
    app: FastAPI,
    *,
    score_query_service: ScoreQueryService | None,
    resolver: _Resolver,
    data_origin: str,
    catalog_reader: _CatalogReader | None = None,
    rule_version_reader: _RuleVersionReader | None = None,
) -> None:
    """Skor alanının route'larını FastAPI uygulamasına kaydeder."""

    def _enrich(item: ScoreItemResponse) -> ScoreItemResponse:
        return _apply_scope_display(
            item,
            catalog_reader=catalog_reader,
            rule_version_reader=rule_version_reader,
        )

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
        score_status: Annotated[str | None, FastApiQuery()] = None,
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
            score_status=score_status,
            limit=limit,
        )
        return ScoreListResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            items=tuple(_enrich(ScoreItemResponse.from_domain(s)) for s in scores),
        )

    @app.get(
        "/api/v1/scores/trend",
        response_model=ScoreTrendResponse,
        tags=["scores"],
    )
    async def get_score_trend(
        request: Request,
        scope_type: Annotated[str, FastApiQuery()],
        scope_id: Annotated[str | None, FastApiQuery()] = None,
        period_start: Annotated[datetime | None, FastApiQuery()] = None,
        period_end: Annotated[datetime | None, FastApiQuery()] = None,
        granularity: Annotated[str, FastApiQuery()] = "day",
    ) -> ScoreTrendResponse:
        if score_query_service is None:
            raise DashboardQueryError(
                "Score query service is not available.", request.state.correlation_id
            )
        if granularity not in ("day", "week", "month"):
            raise DashboardQueryError(
                f"Invalid granularity '{granularity}'. Must be day, week, or month.",
                request.state.correlation_id,
            )
        actor_context = resolver.resolve(request)
        parsed_scope_type = ScoreScopeType(scope_type)
        trend_data = score_query_service.get_score_trend(
            actor_context,
            scope_type=parsed_scope_type,
            scope_id=scope_id,
            period_start=period_start,
            period_end=period_end,
            granularity=granularity,  # type: ignore[arg-type]
        )
        return ScoreTrendResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            scope_type=scope_type,
            scope_id=scope_id,
            granularity=granularity,
            items=tuple(
                ScoreTrendPointResponse(
                    timestamp=point["timestamp"],
                    score_value=point["score_value"],
                    level=point["level"],
                    change=point["change"],
                    score_count=point["score_count"],
                )
                for point in trend_data
            ),
        )

    @app.get(
        "/api/v1/rules/{quality_rule_id}/scores",
        response_model=ScoreRuleHistoryResponse,
        tags=["rules", "scores"],
    )
    async def list_rule_scores_by_rule(
        request: Request,
        quality_rule_id: str,
    ) -> ScoreRuleHistoryResponse:
        """Belirli bir kuralın tüm execution'lardaki skorlarını döndürür."""
        if score_query_service is None:
            raise DashboardQueryError(
                "Score query service is not available.", request.state.correlation_id
            )
        actor_context = resolver.resolve(request)
        # quality_rule_id'yi rule_version_id olarak kullan
        scores = score_query_service.list_rule_scores(actor_context, quality_rule_id)
        return ScoreRuleHistoryResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            rule_version_id=quality_rule_id,
            items=tuple(_enrich(ScoreItemResponse.from_domain(s)) for s in scores),
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
            items=tuple(_enrich(ScoreItemResponse.from_domain(s)) for s in scores),
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
            score=_enrich(ScoreItemResponse.from_domain(detail.score)),
            publication=pub_response,
            available_actions=detail.available_actions,
            has_contribution_graph=detail.contribution_graph is not None,
            calculation_details=(
                thaw(detail.score.calculation_details) if detail.score.calculation_details else None
            ),
            contribution_graph=(
                _enrich_contribution_graph(
                    dict(detail.contribution_graph.graph),
                    catalog_reader=catalog_reader,
                    rule_version_reader=rule_version_reader,
                )
                if detail.contribution_graph is not None
                else None
            ),
        )
