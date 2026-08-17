"""Skorlama konfigürasyonu maker-checker HTTP route kayıtları.

Aktif skorlama konfigürasyonunun listelenmesi, yeni konfigürasyon
önerisi gönderilmesi ve bekleyen onayın karar bağlanmasını sunar.
Tüm güvenlik kontrolleri ScoringConfigurationService içinde
fail-closed uygulanır.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Protocol

from fastapi import FastAPI, HTTPException, Request, Response

from veri_kalitesi.api.models import (
    ScoringConfigurationApprovalItemResponse,
    ScoringConfigurationCreateRequest,
    ScoringConfigurationDecisionRequest,
    ScoringConfigurationDetailResponse,
    ScoringConfigurationEntryResponse,
    ScoringConfigurationItemResponse,
    ScoringConfigurationListResponse,
)
from veri_kalitesi.governance import GovernanceQueryTechnicalError
from veri_kalitesi.identity import ActorContext, is_trusted_actor_context
from veri_kalitesi.scoring.errors import ScoringValidationError
from veri_kalitesi.scoring.models import (
    ScoringApprovalStatus,
    ScoringConfiguration,
    ScoringConfigurationApproval,
    ThresholdSet,
)
from veri_kalitesi.scoring.service import ScoringConfigurationService


class _Resolver(Protocol):
    """Aktor cozumleyici yuzeyi; ActorContextResolver bunu karsilar."""

    def resolve(self, request: Request) -> ActorContext | None: ...


class _ConfigurationReader(Protocol):
    """Konfigürasyon listesi için salt-okunur repository yüzeyi."""

    def get_active_configuration(self) -> ScoringConfiguration: ...

    def list_configurations(self) -> list[ScoringConfiguration]: ...

    def list_configuration_approvals(self) -> list[ScoringConfigurationApproval]: ...


def register_scoring_configuration_routes(
    app: FastAPI,
    *,
    scoring_configuration_service: ScoringConfigurationService | None,
    configuration_reader: _ConfigurationReader | None,
    resolver: _Resolver,
    data_origin: str,
) -> None:
    """Skorlama konfigürasyon route'larını FastAPI uygulamasına kaydeder."""

    @app.get(
        "/api/v1/scoring-configurations",
        response_model=ScoringConfigurationListResponse,
        tags=["scores"],
    )
    async def list_scoring_configurations(
        request: Request, response: Response, dataset_id: str | None = None
    ) -> ScoringConfigurationListResponse:
        reader = _reader(configuration_reader, request)
        actor_context = resolver.resolve(request)
        if (
            actor_context is None
            or not is_trusted_actor_context(actor_context)
            or not actor_context.can_view_enterprise
        ):
            raise HTTPException(status_code=403, detail="Scoring configuration access denied.")
        configurations = reader.list_configurations()
        if dataset_id is not None:
            configurations = [
                c for c in configurations
                if c.dataset_id == dataset_id or c.dataset_id is None
            ]
        approvals_by_configuration = {
            approval.configuration_id: approval
            for approval in reader.list_configuration_approvals()
        }
        active_configuration_id: str | None = None
        for configuration in configurations:
            if configuration.is_active:
                active_configuration_id = configuration.configuration_id
        pending_approval = next(
            (
                approval
                for approval in approvals_by_configuration.values()
                if approval.status is ScoringApprovalStatus.PENDING
            ),
            None,
        )
        response.headers["Cache-Control"] = "no-store"
        return ScoringConfigurationListResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            active_configuration_id=active_configuration_id,
            pending_approval=(
                ScoringConfigurationApprovalItemResponse.from_domain(pending_approval)
                if pending_approval is not None
                else None
            ),
            items=tuple(
                ScoringConfigurationEntryResponse(
                    configuration=ScoringConfigurationItemResponse.from_domain(configuration),
                    approval=(
                        ScoringConfigurationApprovalItemResponse.from_domain(approval)
                        if (
                            approval := approvals_by_configuration.get(
                                configuration.configuration_id
                            )
                        )
                        is not None
                        else None
                    ),
                )
                for configuration in configurations
            ),
        )

    @app.post(
        "/api/v1/scoring-configurations",
        response_model=ScoringConfigurationDetailResponse,
        status_code=201,
        tags=["scores"],
    )
    async def create_scoring_configuration(
        payload: ScoringConfigurationCreateRequest,
        request: Request,
        response: Response,
    ) -> ScoringConfigurationDetailResponse:
        service = _service(scoring_configuration_service, request)
        reader = _reader(configuration_reader, request)
        actor_context = _mutation_actor(request, resolver)
        baseline = reader.get_active_configuration()
        threshold_set = ThresholdSet(
            version=payload.threshold_version or baseline.threshold_set.version,
            critical_upper_exclusive=(
                _parse_threshold(payload.critical_upper_exclusive)
                if payload.critical_upper_exclusive is not None
                else baseline.threshold_set.critical_upper_exclusive
            ),
            risky_upper_exclusive=(
                _parse_threshold(payload.risky_upper_exclusive)
                if payload.risky_upper_exclusive is not None
                else baseline.threshold_set.risky_upper_exclusive
            ),
            acceptable_upper_exclusive=(
                _parse_threshold(payload.acceptable_upper_exclusive)
                if payload.acceptable_upper_exclusive is not None
                else baseline.threshold_set.acceptable_upper_exclusive
            ),
        )
        dimension_weights = (
            payload.parse_dimension_weights()
            if payload.dimension_weights is not None
            else dict(baseline.dimension_weights)
        )
        criticality_weights = (
            payload.parse_criticality_weights()
            if payload.criticality_weights is not None
            else dict(baseline.criticality_weights)
        )
        configuration, approval = service.create_and_submit(
            actor_context=actor_context,
            version=payload.version,
            threshold_set=threshold_set,
            dimension_weights=dimension_weights,
            criticality_weights=criticality_weights,
            dataset_id=payload.dataset_id,
        )
        response.headers["Cache-Control"] = "no-store"
        return ScoringConfigurationDetailResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            configuration=ScoringConfigurationItemResponse.from_domain(configuration),
            approval=ScoringConfigurationApprovalItemResponse.from_domain(approval),
        )

    @app.post(
        "/api/v1/scoring-configurations/approvals/{approval_id}/decision",
        response_model=ScoringConfigurationDetailResponse,
        tags=["scores"],
    )
    async def decide_scoring_configuration_approval(
        approval_id: str,
        payload: ScoringConfigurationDecisionRequest,
        request: Request,
        response: Response,
    ) -> ScoringConfigurationDetailResponse:
        service = _service(scoring_configuration_service, request)
        actor_context = _mutation_actor(request, resolver)
        configuration, approval = service.decide_configuration_approval(
            actor_context=actor_context,
            approval_id=approval_id,
            decision=payload.decision,
            reason_code=payload.reason_code,
        )
        response.headers["Cache-Control"] = "no-store"
        return ScoringConfigurationDetailResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            configuration=ScoringConfigurationItemResponse.from_domain(configuration),
            approval=ScoringConfigurationApprovalItemResponse.from_domain(approval),
        )


def _parse_threshold(value: str) -> Decimal:
    try:
        return Decimal(value)
    except Exception as exc:
        raise ScoringValidationError("Scoring configuration threshold is invalid.") from exc


def _service(
    scoring_configuration_service: ScoringConfigurationService | None,
    request: Request,
) -> ScoringConfigurationService:
    if scoring_configuration_service is None:
        raise GovernanceQueryTechnicalError(
            "Scoring configuration service is unavailable.", request.state.correlation_id
        )
    return scoring_configuration_service


def _reader(
    configuration_reader: _ConfigurationReader | None,
    request: Request,
) -> _ConfigurationReader:
    if configuration_reader is None:
        raise GovernanceQueryTechnicalError(
            "Scoring configuration service is unavailable.", request.state.correlation_id
        )
    return configuration_reader


def _mutation_actor(request: Request, resolver: _Resolver) -> ActorContext | None:
    actor_context = getattr(request.state, "actor_context", None)
    if actor_context is None:
        actor_context = resolver.resolve(request)
    return actor_context
