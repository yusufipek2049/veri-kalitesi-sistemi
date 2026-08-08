"""Lineage/governance alanı HTTP route kayıtları."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Protocol

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from veri_kalitesi.api.exception_handlers import problem as _problem
from veri_kalitesi.identity import ActorContext
from veri_kalitesi.lineage import (
    PostgreSQLGovernanceProfileReader,
    PostgreSQLLineageEvidenceRepository,
    governance_projection,
    resolve_active_profile,
)


class _Resolver(Protocol):
    def resolve(self, request: Request) -> ActorContext | None: ...


def register_lineage_routes(
    app: FastAPI,
    *,
    lineage_evidence_repository: PostgreSQLLineageEvidenceRepository | None,
    governance_profile_reader: PostgreSQLGovernanceProfileReader | None,
    resolver: _Resolver,
    data_origin: str,
    clock: Callable[[], datetime],
) -> None:
    """Lineage/governance alanının route'larını FastAPI uygulamasına kaydeder."""

    @app.get(
        "/api/v1/lineage/snapshots/{snapshot_id}",
        tags=["lineage"],
    )
    async def get_lineage_snapshot(
        snapshot_id: str,
        request: Request,
    ) -> JSONResponse:
        """Salt okunur lineage/yönetişim/etki kanıt snapshot'ı."""
        actor_context = resolver.resolve(request)
        if actor_context is None:
            return _problem(
                request,
                status=401,
                title="Authentication required",
                detail="A trusted actor context is required.",
                correlation_id=request.state.correlation_id,
            )
        if lineage_evidence_repository is None:
            return _problem(
                request,
                status=503,
                title="Lineage evidence unavailable",
                detail="Lineage evidence repository is not configured.",
                correlation_id=request.state.correlation_id,
            )
        stored = lineage_evidence_repository.get(snapshot_id)
        if stored is None:
            return _problem(
                request,
                status=404,
                title="Snapshot not found",
                detail=f"Lineage evidence snapshot '{snapshot_id}' not found.",
                correlation_id=request.state.correlation_id,
            )
        if not actor_context.can_view_enterprise and (
            stored.subject_ref not in actor_context.permitted_source_ids
            and stored.subject_ref not in actor_context.permitted_dataset_ids
        ):
            return _problem(
                request,
                status=403,
                title="Access denied",
                detail="The requested evidence scope is not available.",
                correlation_id=request.state.correlation_id,
            )
        return JSONResponse(
            {
                "api_version": "v1",
                "data_origin": data_origin,
                "correlation_id": request.state.correlation_id,
                "snapshot_id": stored.snapshot_id,
                "snapshot_kind": stored.snapshot_kind,
                "subject_ref": stored.subject_ref,
                "version_label": stored.version_label,
                "digest": stored.digest,
                "created_at": stored.created_at.isoformat(),
                "payload": stored.payload,
            },
            headers={"Cache-Control": "no-store"},
        )

    @app.get(
        "/api/v1/governance/{asset_ref}/projection",
        tags=["lineage"],
    )
    async def get_governance_projection(
        asset_ref: str,
        request: Request,
    ) -> JSONResponse:
        """Salt okunur yönetişim projeksiyonu; kanıt yoksa UNKNOWN döner."""
        actor_context = resolver.resolve(request)
        if actor_context is None:
            return _problem(
                request,
                status=401,
                title="Authentication required",
                detail="A trusted actor context is required.",
                correlation_id=request.state.correlation_id,
            )
        if not actor_context.can_view_enterprise and (
            asset_ref not in actor_context.permitted_source_ids
            and asset_ref not in actor_context.permitted_dataset_ids
        ):
            return _problem(
                request,
                status=403,
                title="Access denied",
                detail="The requested governance scope is not available.",
                correlation_id=request.state.correlation_id,
            )
        if lineage_evidence_repository is None or governance_profile_reader is None:
            return _problem(
                request,
                status=503,
                title="Governance evidence unavailable",
                detail="Lineage evidence repository is not configured.",
                correlation_id=request.state.correlation_id,
            )
        profiles = governance_profile_reader.list_governance_profiles(asset_ref)
        now = clock()
        projection = governance_projection(resolve_active_profile(profiles, now))
        return JSONResponse(
            {
                "api_version": "v1",
                "data_origin": data_origin,
                "correlation_id": request.state.correlation_id,
                "asset_ref": asset_ref,
                **projection,
            },
            headers={"Cache-Control": "no-store"},
        )
