"""Katalog ve metadata keşfi alanı HTTP route kayıtları."""

from __future__ import annotations

from typing import Any, Protocol

from fastapi import FastAPI, Request, Response

from veri_kalitesi.api.models import ScoreItemResponse, ScoreListResponse
from veri_kalitesi.api.models_catalog import (
    CatalogDatasetDetailResponse,
    CatalogDatasetListResponse,
    CatalogDatasetResponse,
    CatalogFieldDetailResponse,
    CatalogFieldListResponse,
    CatalogFieldResponse,
    DatasetUpdateRequest,
    DiffApplicationRequest,
    DiffApplicationResponse,
    DiscoveryDiffResponse,
    DiscoveryRequest,
    DiscoveryResponse,
    DiscoveryScopeRequest,
    DiscoveryScopeResponse,
    DiscoveryStatusResponse,
    FieldUpdateRequest,
)
from veri_kalitesi.data_sources.query import (
    DataSourceQueryTechnicalError,
)
from veri_kalitesi.identity import ActorContext


from veri_kalitesi.scoring.models import ScoreScopeType
from veri_kalitesi.scoring.query import ScoreQueryService


class MetadataCommandService(Protocol):
    """Metadata keşfi ve diff uygulama komut servisi."""

    def request_discovery(
        self,
        *,
        actor_context: ActorContext,
        data_source_id: str,
        idempotency_key: str | None,
        correlation_id: str,
    ) -> Any: ...

    def update_discovery_scope(
        self,
        *,
        actor_context: ActorContext,
        data_source_id: str,
        include_patterns: list[str],
        exclude_patterns: list[str],
        page_size: int,
        max_objects: int,
        timeout_seconds: int,
        expected_version: int,
        policy_version: str,
        correlation_id: str,
    ) -> Any: ...

    def apply_diff(
        self,
        *,
        actor_context: ActorContext,
        metadata_diff_id: str,
        reason_code: str,
        expected_version: int,
        correlation_id: str,
    ) -> Any: ...

    def update_dataset(
        self,
        *,
        dataset_id: str,
        updates: dict[str, Any],
        expected_version: int,
        actor_context: ActorContext,
        correlation_id: str,
    ) -> Any: ...

    def update_field(
        self,
        *,
        field_id: str,
        updates: dict[str, Any],
        expected_version: int,
        actor_context: ActorContext,
        correlation_id: str,
    ) -> Any: ...


class CatalogQueryService(Protocol):
    """Katalog sorgu servisi."""

    def get_discovery_scope(
        self, data_source_id: str, *, permitted_source_ids: frozenset
    ) -> Any | None: ...
    def get_discovery(self, discovery_id: int, *, permitted_source_ids: frozenset) -> Any: ...
    def get_discovery_diff(
        self, discovery_id: int, *, permitted_source_ids: frozenset
    ) -> Any | None: ...
    def list_datasets_for_actor(
        self,
        *,
        permitted_source_ids: frozenset,
        status_filter: str | None,
        name_contains: str | None,
        limit: int,
    ) -> list: ...
    def get_dataset_view(self, dataset_id: str, *, permitted_source_ids: frozenset) -> Any: ...
    def list_fields_for_dataset(
        self, dataset_id: str, *, permitted_source_ids: frozenset
    ) -> list: ...
    def get_field_view(self, data_field_id: str, *, permitted_source_ids: frozenset) -> Any: ...


class _Resolver(Protocol):
    def resolve(self, request: Request) -> Any: ...


def register_catalog_routes(
    app: FastAPI,
    *,
    metadata_command_service: MetadataCommandService | None,
    catalog_query_service: CatalogQueryService | None,
    resolver: _Resolver,
    data_origin: str,
    score_query_service: ScoreQueryService | None = None,
) -> None:
    """Katalog ve metadata keşfi alanının route'larını FastAPI uygulamasına kaydeder."""

    @app.post(
        "/api/v1/data-sources/{data_source_id}/metadata-discoveries",
        status_code=202,
        tags=["catalog"],
    )
    async def request_metadata_discovery(
        data_source_id: str,
        payload: DiscoveryRequest,
        request: Request,
        response: Response,
    ) -> DiscoveryResponse:
        if metadata_command_service is None or catalog_query_service is None:
            raise DataSourceQueryTechnicalError(
                "Metadata command service is not configured. "
                "Ensure the application composition provides a PostgreSQLMetadataCommandService.",
                request.state.correlation_id,
            )
        actor_context = getattr(request.state, "actor_context", None)
        if actor_context is None:
            raise DataSourceQueryTechnicalError(
                "Actor context is missing from the request state. "
                "A trusted development or production session is required.",
                request.state.correlation_id,
            )
        result = metadata_command_service.request_discovery(
            actor_context=actor_context,
            data_source_id=data_source_id,
            idempotency_key=payload.idempotency_key,
            correlation_id=request.state.correlation_id,
        )
        response.headers["Cache-Control"] = "no-store"
        return DiscoveryResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            discovery_id=result.discovery_id,
            data_source_id=data_source_id,
            status=result.status.value,
            job_id=result.job_id,
        )

    @app.put(
        "/api/v1/data-sources/{data_source_id}/discovery-scope",
        tags=["catalog"],
    )
    async def update_discovery_scope(
        data_source_id: str,
        payload: DiscoveryScopeRequest,
        request: Request,
        response: Response,
    ) -> DiscoveryScopeResponse:
        if metadata_command_service is None or catalog_query_service is None:
            raise DataSourceQueryTechnicalError(
                "Metadata command service is not configured.",
                request.state.correlation_id,
            )
        actor_context = getattr(request.state, "actor_context", None)
        if actor_context is None:
            raise DataSourceQueryTechnicalError(
                "Actor context is missing from the request state.",
                request.state.correlation_id,
            )
        scope = metadata_command_service.update_discovery_scope(
            actor_context=actor_context,
            data_source_id=data_source_id,
            include_patterns=payload.include_patterns,
            exclude_patterns=payload.exclude_patterns,
            page_size=payload.page_size,
            max_objects=payload.max_objects,
            timeout_seconds=payload.timeout_seconds,
            expected_version=payload.expected_version,
            policy_version=payload.policy_version,
            correlation_id=request.state.correlation_id,
        )
        response.headers["Cache-Control"] = "no-store"
        return DiscoveryScopeResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            data_source_id=data_source_id,
            include_patterns=scope.include_patterns,
            exclude_patterns=scope.exclude_patterns,
            page_size=scope.page_size,
            max_objects=scope.max_objects,
            timeout_seconds=scope.timeout_seconds,
            version=scope.version,
        )

    @app.get(
        "/api/v1/data-sources/{data_source_id}/discovery-scope",
        tags=["catalog"],
    )
    async def get_discovery_scope(
        data_source_id: str,
        request: Request,
        response: Response,
    ) -> DiscoveryScopeResponse:
        if catalog_query_service is None:
            raise DataSourceQueryTechnicalError(
                "Catalog service is unavailable.",
                request.state.correlation_id,
            )
        actor_context = resolver.resolve(request)
        permitted = (
            frozenset()
            if not actor_context.can_view_enterprise
            else actor_context.permitted_source_ids
        )
        scope = catalog_query_service.get_discovery_scope(
            data_source_id, permitted_source_ids=permitted
        )
        if scope is None:
            return DiscoveryScopeResponse(
                data_origin=data_origin,
                correlation_id=request.state.correlation_id,
                data_source_id=data_source_id,
                include_patterns=(),
                exclude_patterns=(),
                page_size=1000,
                max_objects=100_000,
                timeout_seconds=60,
                version=1,
            )
        response.headers["Cache-Control"] = "no-store"
        return DiscoveryScopeResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            data_source_id=data_source_id,
            include_patterns=scope.include_patterns,
            exclude_patterns=scope.exclude_patterns,
            page_size=scope.page_size,
            max_objects=scope.max_objects,
            timeout_seconds=scope.timeout_seconds,
            version=scope.version,
        )

    @app.get(
        "/api/v1/metadata-discoveries/{discovery_id}",
        tags=["catalog"],
    )
    async def get_discovery_status(
        discovery_id: int,
        request: Request,
        response: Response,
    ) -> DiscoveryStatusResponse:
        if catalog_query_service is None:
            raise DataSourceQueryTechnicalError(
                "Catalog service is unavailable.",
                request.state.correlation_id,
            )
        actor_context = resolver.resolve(request)
        permitted = (
            frozenset()
            if not actor_context.can_view_enterprise
            else actor_context.permitted_source_ids
        )
        result = catalog_query_service.get_discovery(discovery_id, permitted_source_ids=permitted)
        response.headers["Cache-Control"] = "no-store"
        return DiscoveryStatusResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            discovery_id=result.discovery_id,
            data_source_id=result.data_source_id,
            status=result.status.value,
            scanned_object_count=result.scanned_object_count,
            completed_scope=result.completed_scope,
            partial_reason_code=result.partial_reason_code,
            started_at=result.started_at,
            finished_at=result.finished_at,
            discovery_correlation_id=result.correlation_id,
        )

    @app.get(
        "/api/v1/metadata-discoveries/{discovery_id}/diff",
        tags=["catalog"],
    )
    async def get_discovery_diff(
        discovery_id: int,
        request: Request,
        response: Response,
    ) -> DiscoveryDiffResponse:
        if catalog_query_service is None:
            raise DataSourceQueryTechnicalError(
                "Catalog service is unavailable.",
                request.state.correlation_id,
            )
        actor_context = resolver.resolve(request)
        permitted = (
            frozenset()
            if not actor_context.can_view_enterprise
            else actor_context.permitted_source_ids
        )
        result = catalog_query_service.get_discovery(discovery_id, permitted_source_ids=permitted)
        diff = catalog_query_service.get_discovery_diff(
            discovery_id, permitted_source_ids=permitted
        )
        response.headers["Cache-Control"] = "no-store"
        return DiscoveryDiffResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            metadata_diff_id=diff.metadata_diff_id if diff else None,
            discovery_id=discovery_id,
            data_source_id=result.data_source_id,
            status=diff.status.value if diff else "PENDING",
            added_objects=diff.added_objects if diff else (),
            changed_objects=diff.changed_objects if diff else (),
            removed_objects=diff.removed_objects if diff else (),
            requires_rule_review=diff.requires_rule_review if diff else False,
        )

    @app.post(
        "/api/v1/metadata-diffs/{metadata_diff_id}/application",
        tags=["catalog"],
    )
    async def apply_metadata_diff(
        metadata_diff_id: str,
        payload: DiffApplicationRequest,
        request: Request,
        response: Response,
    ) -> DiffApplicationResponse:
        if metadata_command_service is None:
            raise DataSourceQueryTechnicalError(
                "Metadata command service is not configured.",
                request.state.correlation_id,
            )
        actor_context = getattr(request.state, "actor_context", None)
        if actor_context is None:
            raise DataSourceQueryTechnicalError(
                "Actor context is missing from the request state.",
                request.state.correlation_id,
            )
        result = metadata_command_service.apply_diff(
            actor_context=actor_context,
            metadata_diff_id=metadata_diff_id,
            reason_code=payload.reason_code,
            expected_version=payload.expected_version,
            correlation_id=request.state.correlation_id,
        )
        response.headers["Cache-Control"] = "no-store"
        return DiffApplicationResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            metadata_diff_id=result.metadata_diff_id,
            status=result.status.value,
            applied_at=result.applied_at,
        )

    @app.get(
        "/api/v1/datasets",
        tags=["catalog"],
    )
    async def list_catalog_datasets(
        request: Request,
        response: Response,
        status: str | None = None,
        name_contains: str | None = None,
        limit: int = 200,
    ) -> CatalogDatasetListResponse:
        if catalog_query_service is None:
            raise DataSourceQueryTechnicalError(
                "Catalog service is unavailable.",
                request.state.correlation_id,
            )
        actor_context = resolver.resolve(request)
        permitted = (
            frozenset()
            if not actor_context.can_view_enterprise
            else actor_context.permitted_source_ids
        )
        views = catalog_query_service.list_datasets_for_actor(
            permitted_source_ids=permitted,
            status_filter=status,
            name_contains=name_contains,
            limit=limit,
        )
        response.headers["Cache-Control"] = "no-store"
        return CatalogDatasetListResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            items=tuple(
                CatalogDatasetResponse(
                    dataset_id=v.dataset.dataset_id,
                    data_source_id=v.dataset.data_source_id,
                    namespace=v.dataset.namespace,
                    name=v.dataset.name,
                    dataset_type=v.dataset.dataset_type.value,
                    status=v.dataset.status.value,
                    estimated_row_count=v.dataset.estimated_row_count,
                    field_count=v.field_count,
                    version=v.dataset.version,
                )
                for v in views
            ),
        )

    @app.get(
        "/api/v1/datasets/{dataset_id}",
        tags=["catalog"],
    )
    async def get_catalog_dataset(
        dataset_id: str,
        request: Request,
        response: Response,
    ) -> CatalogDatasetDetailResponse:
        if catalog_query_service is None:
            raise DataSourceQueryTechnicalError(
                "Catalog service is unavailable.",
                request.state.correlation_id,
            )
        actor_context = resolver.resolve(request)
        permitted = (
            frozenset()
            if not actor_context.can_view_enterprise
            else actor_context.permitted_source_ids
        )
        view = catalog_query_service.get_dataset_view(dataset_id, permitted_source_ids=permitted)
        response.headers["Cache-Control"] = "no-store"
        return CatalogDatasetDetailResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            dataset=CatalogDatasetResponse(
                dataset_id=view.dataset.dataset_id,
                data_source_id=view.dataset.data_source_id,
                namespace=view.dataset.namespace,
                name=view.dataset.name,
                dataset_type=view.dataset.dataset_type.value,
                status=view.dataset.status.value,
                estimated_row_count=view.dataset.estimated_row_count,
                field_count=view.field_count,
                version=view.dataset.version,
            ),
            data_source_name=view.data_source.name,
        )

    @app.get(
        "/api/v1/datasets/{dataset_id}/scores",
        response_model=ScoreListResponse,
        tags=["catalog"],
    )
    async def list_dataset_scores(
        dataset_id: str,
        request: Request,
        response: Response,
        limit: int = 200,
    ) -> ScoreListResponse:
        if score_query_service is None:
            raise DataSourceQueryTechnicalError(
                "Score query service is unavailable.",
                request.state.correlation_id,
            )
        actor_context = resolver.resolve(request)
        scores = score_query_service.list_scores(
            actor_context,
            scope_type=ScoreScopeType.DATASET,
            scope_id=dataset_id,
            limit=limit,
        )
        response.headers["Cache-Control"] = "no-store"
        return ScoreListResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            items=tuple(ScoreItemResponse.from_domain(s) for s in scores),
        )

    @app.get(
        "/api/v1/datasets/{dataset_id}/fields",
        tags=["catalog"],
    )
    async def list_catalog_fields(
        dataset_id: str,
        request: Request,
        response: Response,
    ) -> CatalogFieldListResponse:
        if catalog_query_service is None:
            raise DataSourceQueryTechnicalError(
                "Catalog service is unavailable.",
                request.state.correlation_id,
            )
        actor_context = resolver.resolve(request)
        permitted = (
            frozenset()
            if not actor_context.can_view_enterprise
            else actor_context.permitted_source_ids
        )
        fields = catalog_query_service.list_fields_for_dataset(
            dataset_id, permitted_source_ids=permitted
        )
        response.headers["Cache-Control"] = "no-store"
        return CatalogFieldListResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            items=tuple(
                CatalogFieldResponse(
                    data_field_id=f.data_field_id,
                    dataset_id=f.dataset_id,
                    name=f.name,
                    native_data_type=f.native_data_type,
                    is_nullable=f.is_nullable,
                    is_sensitive=f.is_sensitive,
                    classification=f.classification.value,
                    status=f.status.value,
                    version=f.version,
                )
                for f in fields
            ),
        )

    @app.get(
        "/api/v1/fields/{data_field_id}",
        tags=["catalog"],
    )
    async def get_catalog_field(
        data_field_id: str,
        request: Request,
        response: Response,
    ) -> CatalogFieldDetailResponse:
        if catalog_query_service is None:
            raise DataSourceQueryTechnicalError(
                "Catalog service is unavailable.",
                request.state.correlation_id,
            )
        actor_context = resolver.resolve(request)
        permitted = (
            frozenset()
            if not actor_context.can_view_enterprise
            else actor_context.permitted_source_ids
        )
        view = catalog_query_service.get_field_view(data_field_id, permitted_source_ids=permitted)
        response.headers["Cache-Control"] = "no-store"
        return CatalogFieldDetailResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            field=CatalogFieldResponse(
                data_field_id=view.field.data_field_id,
                dataset_id=view.field.dataset_id,
                name=view.field.name,
                native_data_type=view.field.native_data_type,
                is_nullable=view.field.is_nullable,
                is_sensitive=view.field.is_sensitive,
                classification=view.field.classification.value,
                status=view.field.status.value,
                version=view.field.version,
            ),
            dataset_name=view.dataset.name,
            data_source_name=view.data_source.name,
        )

    # ── PATCH endpoints (authorized editing) ──────────────────────────────

    @app.patch(
        "/api/v1/datasets/{dataset_id}",
        tags=["catalog"],
    )
    async def update_catalog_dataset(
        dataset_id: str,
        payload: DatasetUpdateRequest,
        request: Request,
        response: Response,
    ) -> CatalogDatasetDetailResponse:
        """Dataset bilgilerini güncelle — yetkili kullanıcılar için."""
        if metadata_command_service is None or catalog_query_service is None:
            raise DataSourceQueryTechnicalError(
                "Metadata command service is not configured.",
                request.state.correlation_id,
            )
        actor_context = resolver.resolve(request)
        permitted = (
            frozenset()
            if not actor_context.can_view_enterprise
            else actor_context.permitted_source_ids
        )
        # Verify access
        view = catalog_query_service.get_dataset_view(dataset_id, permitted_source_ids=permitted)
        # Build update dict from non-None fields
        updates: dict[str, Any] = {}
        if payload.name is not None:
            updates["name"] = payload.name
        if payload.namespace is not None:
            updates["namespace"] = payload.namespace
        if payload.status is not None:
            updates["status"] = payload.status
        if not updates:
            # No fields to update, return current state
            response.headers["Cache-Control"] = "no-store"
            return CatalogDatasetDetailResponse(
                data_origin=data_origin,
                correlation_id=request.state.correlation_id,
                dataset=CatalogDatasetResponse(
                    dataset_id=view.dataset.dataset_id,
                    data_source_id=view.dataset.data_source_id,
                    namespace=view.dataset.namespace,
                    name=view.dataset.name,
                    dataset_type=view.dataset.dataset_type.value,
                    status=view.dataset.status.value,
                    estimated_row_count=view.dataset.estimated_row_count,
                    field_count=view.field_count,
                    version=view.dataset.version,
                ),
                data_source_name=view.data_source.name,
            )
        # Perform update via repository
        updated_dataset = metadata_command_service.update_dataset(
            dataset_id=dataset_id,
            updates=updates,
            expected_version=payload.expected_version or view.dataset.version,
            actor_context=actor_context,
            correlation_id=request.state.correlation_id,
        )
        response.headers["Cache-Control"] = "no-store"
        return CatalogDatasetDetailResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            dataset=CatalogDatasetResponse(
                dataset_id=updated_dataset.dataset_id,
                data_source_id=updated_dataset.data_source_id,
                namespace=updated_dataset.namespace,
                name=updated_dataset.name,
                dataset_type=updated_dataset.dataset_type.value,
                status=updated_dataset.status.value,
                estimated_row_count=updated_dataset.estimated_row_count,
                field_count=view.field_count,
                version=updated_dataset.version,
            ),
            data_source_name=view.data_source.name,
        )

    @app.patch(
        "/api/v1/fields/{field_id}",
        tags=["catalog"],
    )
    async def update_catalog_field(
        field_id: str,
        payload: FieldUpdateRequest,
        request: Request,
        response: Response,
    ) -> CatalogFieldDetailResponse:
        """Field bilgilerini güncelle — yetkili kullanıcılar için."""
        if metadata_command_service is None or catalog_query_service is None:
            raise DataSourceQueryTechnicalError(
                "Metadata command service is not configured.",
                request.state.correlation_id,
            )
        actor_context = resolver.resolve(request)
        permitted = (
            frozenset()
            if not actor_context.can_view_enterprise
            else actor_context.permitted_source_ids
        )
        # Verify access
        view = catalog_query_service.get_field_view(field_id, permitted_source_ids=permitted)
        # Build update dict from non-None fields
        updates: dict[str, Any] = {}
        if payload.native_data_type is not None:
            updates["native_data_type"] = payload.native_data_type
        if payload.is_nullable is not None:
            updates["is_nullable"] = payload.is_nullable
        if payload.is_sensitive is not None:
            updates["is_sensitive"] = payload.is_sensitive
        if payload.classification is not None:
            updates["classification"] = payload.classification
        if payload.status is not None:
            updates["status"] = payload.status
        if not updates:
            # No fields to update, return current state
            response.headers["Cache-Control"] = "no-store"
            return CatalogFieldDetailResponse(
                data_origin=data_origin,
                correlation_id=request.state.correlation_id,
                field=CatalogFieldResponse(
                    data_field_id=view.field.data_field_id,
                    dataset_id=view.field.dataset_id,
                    name=view.field.name,
                    native_data_type=view.field.native_data_type,
                    is_nullable=view.field.is_nullable,
                    is_sensitive=view.field.is_sensitive,
                    classification=view.field.classification.value,
                    status=view.field.status.value,
                    version=view.field.version,
                ),
                dataset_name=view.dataset.name,
                data_source_name=view.data_source.name,
            )
        # Perform update via repository
        updated_field = metadata_command_service.update_field(
            field_id=field_id,
            updates=updates,
            expected_version=payload.expected_version or view.field.version,
            actor_context=actor_context,
            correlation_id=request.state.correlation_id,
        )
        response.headers["Cache-Control"] = "no-store"
        return CatalogFieldDetailResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            field=CatalogFieldResponse(
                data_field_id=updated_field.data_field_id,
                dataset_id=updated_field.dataset_id,
                name=updated_field.name,
                native_data_type=updated_field.native_data_type,
                is_nullable=updated_field.is_nullable,
                is_sensitive=updated_field.is_sensitive,
                classification=updated_field.classification.value,
                status=updated_field.status.value,
                version=updated_field.version,
            ),
            dataset_name=view.dataset.name,
            data_source_name=view.data_source.name,
        )
