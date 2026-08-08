"""Veri kaynağı ve profil alanı HTTP route kayıtları."""

from __future__ import annotations

from typing import Any, Protocol

from fastapi import FastAPI, Query as FastApiQuery, Request, Response

from veri_kalitesi.api.data_source_commands import DataSourceCommandResult
from veri_kalitesi.api.identity import DevelopmentActorContextResolver
from veri_kalitesi.api.models_data_sources import (
    DataSourceActivationDecisionRequest,
    DataSourceCreateRequest,
    DataSourceListItemResponse,
    DataSourceListResponse,
    DataSourceMutationResponse,
    DataSourcePassivationRequest,
    DriftJudgmentResponse,
    ProfileComparisonItemResponse,
    ProfileComparisonRequest,
    ProfileComparisonResponse,
    ProfileSnapshotDetailResponse,
    ProfileSnapshotListItemResponse,
    ProfileSnapshotListResponse,
)
from veri_kalitesi.api.bff import CSRF_HEADER_NAME
from veri_kalitesi.data_sources.models import ProfileComparison
from veri_kalitesi.data_sources.query import (
    DataSourceQueryService,
    DataSourceQueryTechnicalError,
    ProfileSnapshotQueryService,
)
from veri_kalitesi.identity import ActorContext


class DataSourceMutationService(Protocol):
    """Veri kaynağı mutasyonları için protokol."""

    def create(
        self,
        *,
        payload: DataSourceCreateRequest,
        actor_context: ActorContext | None,
    ) -> DataSourceCommandResult: ...

    def test_connection(
        self, *, data_source_id: str, actor_context: ActorContext | None
    ) -> DataSourceCommandResult: ...

    def request_activation(
        self, *, data_source_id: str, actor_context: ActorContext | None
    ) -> DataSourceCommandResult: ...

    def decide_activation(
        self,
        *,
        activation_request_id: str,
        decision: str,
        reason_code: str,
        actor_context: ActorContext | None,
    ) -> DataSourceCommandResult: ...

    def passivate(
        self,
        *,
        data_source_id: str,
        reason_code: str,
        actor_context: ActorContext | None,
    ) -> DataSourceCommandResult: ...


class ProfileComparisonService(Protocol):
    """Yetkiyi güvenilir actor context ile uygulayan profil karşılaştırma sınırı."""

    def compare(
        self,
        *,
        actor_context: ActorContext | None,
        dataset_id: str,
        baseline_profile_id: str,
        current_profile_id: str,
        policy_version: str | None,
        correlation_id: str,
    ) -> ProfileComparison: ...


class _Resolver(Protocol):
    def resolve(self, request: Request) -> Any: ...


def register_data_sources_routes(
    app: FastAPI,
    *,
    data_source_query_service: DataSourceQueryService | None,
    data_source_mutation_service: DataSourceMutationService | None,
    profile_comparison_service: ProfileComparisonService | None,
    profile_snapshot_query_service: ProfileSnapshotQueryService | None,
    resolver: _Resolver,
    data_origin: str,
) -> None:
    """Veri kaynağı ve profil alanının route'larını FastAPI uygulamasına kaydeder."""

    # ── Sorgu route'ları ──

    @app.get(
        "/api/v1/data-sources",
        response_model=DataSourceListResponse,
        tags=["data-sources"],
    )
    async def get_data_sources(request: Request, response: Response) -> DataSourceListResponse:
        if data_source_query_service is None:
            raise DataSourceQueryTechnicalError(
                "Data source service is unavailable.", request.state.correlation_id
            )
        actor_context = resolver.resolve(request)
        sources = data_source_query_service.list_views_for_actor(actor_context)
        response.headers["Cache-Control"] = "no-store"
        if isinstance(resolver, DevelopmentActorContextResolver):
            response.headers[CSRF_HEADER_NAME] = resolver.request_proof
        return DataSourceListResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            items=tuple(DataSourceListItemResponse.from_view(source) for source in sources),
        )

    @app.post(
        "/api/v1/profile-comparisons",
        response_model=ProfileComparisonResponse,
        tags=["data-sources"],
    )
    async def compare_profiles(
        payload: ProfileComparisonRequest,
        request: Request,
        response: Response,
    ) -> ProfileComparisonResponse:
        if profile_comparison_service is None:
            raise DataSourceQueryTechnicalError(
                "Profile comparison service is unavailable.",
                request.state.correlation_id,
            )
        actor_context = getattr(request.state, "actor_context", None)
        if actor_context is None:
            actor_context = resolver.resolve(request)
        comparison = profile_comparison_service.compare(
            actor_context=actor_context,
            dataset_id=payload.dataset_id,
            baseline_profile_id=payload.baseline_profile_id,
            current_profile_id=payload.current_profile_id,
            policy_version=payload.policy_version,
            correlation_id=request.state.correlation_id,
        )
        response.headers["Cache-Control"] = "no-store"
        return ProfileComparisonResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            item=ProfileComparisonItemResponse.from_domain(comparison),
        )

    @app.get(
        "/api/v1/profile-snapshots",
        response_model=ProfileSnapshotListResponse,
        tags=["data-sources"],
    )
    async def get_profile_snapshots(
        request: Request,
        response: Response,
        dataset_id: str = FastApiQuery(..., min_length=1),
    ) -> ProfileSnapshotListResponse:
        if profile_snapshot_query_service is None:
            raise DataSourceQueryTechnicalError(
                "Profile snapshot service is unavailable.",
                request.state.correlation_id,
            )
        actor_context = getattr(request.state, "actor_context", None)
        if actor_context is None:
            actor_context = resolver.resolve(request)
        snapshots = profile_snapshot_query_service.list_snapshots(
            actor_context=actor_context,
            dataset_id=dataset_id,
            correlation_id=request.state.correlation_id,
        )
        response.headers["Cache-Control"] = "no-store"
        return ProfileSnapshotListResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            dataset_id=dataset_id,
            limit=profile_snapshot_query_service.MAX_SNAPSHOTS,
            items=tuple(ProfileSnapshotListItemResponse.from_domain(s) for s in snapshots),
        )

    @app.get(
        "/api/v1/profile-snapshots/{profile_id}",
        response_model=ProfileSnapshotDetailResponse,
        tags=["data-sources"],
    )
    async def get_profile_snapshot(
        profile_id: str,
        request: Request,
        response: Response,
    ) -> ProfileSnapshotDetailResponse:
        if profile_snapshot_query_service is None:
            raise DataSourceQueryTechnicalError(
                "Profile snapshot service is unavailable.",
                request.state.correlation_id,
            )
        actor_context = getattr(request.state, "actor_context", None)
        if actor_context is None:
            actor_context = resolver.resolve(request)
        snapshot = profile_snapshot_query_service.get_snapshot(
            actor_context=actor_context,
            profile_id=profile_id,
            correlation_id=request.state.correlation_id,
        )
        response.headers["Cache-Control"] = "no-store"
        return ProfileSnapshotDetailResponse.from_domain(
            snapshot,
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
        )

    @app.get(
        "/api/v1/profile-snapshots/{profile_id}/drift",
        response_model=DriftJudgmentResponse,
        tags=["data-sources"],
    )
    async def get_drift_judgments(
        profile_id: str,
        request: Request,
        response: Response,
        baseline_profile_id: str | None = FastApiQuery(default=None),
    ) -> DriftJudgmentResponse:
        if profile_snapshot_query_service is None:
            raise DataSourceQueryTechnicalError(
                "Profile drift service is unavailable.",
                request.state.correlation_id,
            )
        actor_context = getattr(request.state, "actor_context", None)
        if actor_context is None:
            actor_context = resolver.resolve(request)
        comparison = profile_snapshot_query_service.get_drift_judgments(
            actor_context=actor_context,
            profile_id=profile_id,
            baseline_profile_id=baseline_profile_id,
            correlation_id=request.state.correlation_id,
        )
        response.headers["Cache-Control"] = "no-store"
        return DriftJudgmentResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            item=ProfileComparisonItemResponse.from_domain(comparison),
        )

    # ── Mutasyon route'ları ──

    @app.post(
        "/api/v1/data-sources",
        response_model=DataSourceMutationResponse,
        status_code=201,
        tags=["data-sources"],
    )
    async def create_data_source(
        payload: DataSourceCreateRequest,
        request: Request,
        response: Response,
    ) -> DataSourceMutationResponse:
        if data_source_mutation_service is None:
            raise DataSourceQueryTechnicalError(
                "Data source mutation service is unavailable.", request.state.correlation_id
            )
        actor_context = getattr(request.state, "actor_context", None)
        result = data_source_mutation_service.create(
            payload=payload,
            actor_context=actor_context,
        )
        response.headers["Cache-Control"] = "no-store"
        return DataSourceMutationResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            item=DataSourceListItemResponse.from_view(result.view),
        )

    @app.post(
        "/api/v1/data-sources/{data_source_id}/test",
        response_model=DataSourceMutationResponse,
        tags=["data-sources"],
    )
    async def test_data_source(
        data_source_id: str,
        request: Request,
        response: Response,
    ) -> DataSourceMutationResponse:
        if data_source_mutation_service is None:
            raise DataSourceQueryTechnicalError(
                "Data source mutation service is unavailable.", request.state.correlation_id
            )
        actor_context = getattr(request.state, "actor_context", None)
        result = data_source_mutation_service.test_connection(
            data_source_id=data_source_id,
            actor_context=actor_context,
        )
        response.headers["Cache-Control"] = "no-store"
        return DataSourceMutationResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            item=DataSourceListItemResponse.from_view(result.view),
        )

    @app.post(
        "/api/v1/data-sources/{data_source_id}/activation",
        response_model=DataSourceMutationResponse,
        tags=["data-sources"],
    )
    async def request_data_source_activation(
        data_source_id: str,
        request: Request,
        response: Response,
    ) -> DataSourceMutationResponse:
        if data_source_mutation_service is None:
            raise DataSourceQueryTechnicalError(
                "Data source mutation service is unavailable.", request.state.correlation_id
            )
        actor_context = getattr(request.state, "actor_context", None)
        result = data_source_mutation_service.request_activation(
            data_source_id=data_source_id,
            actor_context=actor_context,
        )
        response.status_code = 201
        response.headers["Cache-Control"] = "no-store"
        return DataSourceMutationResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            item=DataSourceListItemResponse.from_view(result.view),
            activation_request_status=(
                result.activation_request.status.value
                if result.activation_request is not None
                else None
            ),
        )

    @app.post(
        "/api/v1/data-source-activation-requests/{activation_request_id}/decision",
        response_model=DataSourceMutationResponse,
        tags=["data-sources"],
    )
    async def decide_data_source_activation(
        activation_request_id: str,
        payload: DataSourceActivationDecisionRequest,
        request: Request,
        response: Response,
    ) -> DataSourceMutationResponse:
        if data_source_mutation_service is None:
            raise DataSourceQueryTechnicalError(
                "Data source mutation service is unavailable.", request.state.correlation_id
            )
        actor_context = getattr(request.state, "actor_context", None)
        result = data_source_mutation_service.decide_activation(
            activation_request_id=activation_request_id,
            decision=payload.decision,
            reason_code=payload.reason_code,
            actor_context=actor_context,
        )
        response.headers["Cache-Control"] = "no-store"
        return DataSourceMutationResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            item=DataSourceListItemResponse.from_view(result.view),
            activation_request_status=(
                result.activation_request.status.value
                if result.activation_request is not None
                else None
            ),
            replayed=result.replayed,
        )

    @app.post(
        "/api/v1/data-sources/{data_source_id}/passivation",
        response_model=DataSourceMutationResponse,
        tags=["data-sources"],
    )
    async def passivate_data_source(
        data_source_id: str,
        payload: DataSourcePassivationRequest,
        request: Request,
        response: Response,
    ) -> DataSourceMutationResponse:
        if data_source_mutation_service is None:
            raise DataSourceQueryTechnicalError(
                "Data source mutation service is unavailable.", request.state.correlation_id
            )
        actor_context = getattr(request.state, "actor_context", None)
        result = data_source_mutation_service.passivate(
            data_source_id=data_source_id,
            reason_code=payload.reason_code,
            actor_context=actor_context,
        )
        response.headers["Cache-Control"] = "no-store"
        return DataSourceMutationResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            item=DataSourceListItemResponse.from_view(result.view),
        )
