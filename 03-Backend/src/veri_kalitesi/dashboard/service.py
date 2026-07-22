"""Yetki filtreli dashboard skor agaci okuma servisi."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Callable, Protocol

from veri_kalitesi.dashboard.errors import (
    DashboardAuthorizationError,
    DashboardNotFoundError,
    DashboardQueryError,
    DashboardValidationError,
)
from veri_kalitesi.dashboard.models import (
    DashboardAccessScope,
    DashboardCriticalControlIndicator,
    DashboardMeasurementQualificationIndicator,
    DashboardOperationalIndicators,
    DashboardOverview,
    DashboardScoreNode,
    DashboardScoreTrend,
    DashboardScoreTree,
    DashboardTechnicalErrorIndicator,
    DashboardTrendPeriod,
    CriticalControlIndicatorStatus,
    MeasurementQualificationIndicatorStatus,
)
from veri_kalitesi.identity import ActorContext, AuthorizationService, IdentityError
from veri_kalitesi.scoring.models import QualityScore, ScoreScopeType, ScoreStatus


class ScoreReader(Protocol):
    def list_for_execution(self, execution_id: str) -> list[QualityScore]: ...

    def list_for_dashboard_trend(
        self,
        start_at: datetime,
        end_at: datetime,
        allowed_source_ids: frozenset[str],
        include_enterprise: bool,
    ) -> list[QualityScore]: ...


class DashboardQueryService:
    def __init__(
        self,
        score_reader: ScoreReader,
        authorization_service: AuthorizationService,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self.score_reader = score_reader
        self.authorization_service = authorization_service
        self.clock = clock

    def get_score_tree(
        self,
        execution_id: str,
        actor_context: ActorContext | None,
    ) -> DashboardScoreTree:
        access_scope, correlation_id = self._authorize(actor_context)
        return _read_score_tree(
            self.score_reader,
            execution_id,
            access_scope,
            correlation_id,
        )

    def get_source_detail(
        self,
        execution_id: str,
        data_source_id: str,
        actor_context: ActorContext | None,
    ) -> DashboardScoreNode:
        access_scope, correlation_id = self._authorize(actor_context)
        _validate_scoped_request(execution_id, access_scope, correlation_id)
        if not data_source_id.strip():
            raise DashboardValidationError("data_source_id is required.")
        if data_source_id not in access_scope.allowed_source_ids:
            raise DashboardAuthorizationError(
                "Data source is outside the authorized dashboard scope.",
                correlation_id,
            )
        tree = _read_score_tree(
            self.score_reader,
            execution_id,
            access_scope,
            correlation_id,
        )
        for source in tree.sources:
            if source.scope_id == data_source_id:
                return source
        raise DashboardNotFoundError("Dashboard source score not found.")

    def get_score_trend(
        self,
        actor_context: ActorContext | None,
    ) -> DashboardScoreTrend:
        return self.get_overview(actor_context).trend

    def get_overview(
        self,
        actor_context: ActorContext | None,
    ) -> DashboardOverview:
        access_scope, correlation_id = self._authorize(actor_context)
        now = self.clock()
        if now.tzinfo is None or now.utcoffset() is None:
            raise DashboardValidationError("Dashboard trend clock must be timezone-aware.")
        as_of = now.astimezone(timezone.utc)
        current_day = as_of.replace(hour=0, minute=0, second=0, microsecond=0)
        window_start = current_day - timedelta(days=29)
        try:
            scores = self.score_reader.list_for_dashboard_trend(
                window_start,
                as_of,
                access_scope.allowed_source_ids,
                access_scope.can_view_enterprise,
            )
        except (sqlite3.Error, OSError) as exc:
            raise DashboardQueryError(
                "Dashboard trend query could not be completed.", correlation_id
            ) from exc
        scored_at = tuple((score, _score_time_utc(score)) for score in scores)
        authorized_scores = tuple(
            (score, calculated_at)
            for score, calculated_at in scored_at
            if window_start <= calculated_at <= as_of
            and (
                (
                    score.scope_type is ScoreScopeType.SOURCE
                    and score.scope_id in access_scope.allowed_source_ids
                )
                or (
                    score.scope_type is ScoreScopeType.ENTERPRISE
                    and access_scope.can_view_enterprise
                )
            )
        )
        periods = []
        for day_offset in range(30):
            period_start = window_start + timedelta(days=day_offset)
            period_end = period_start + timedelta(days=1)
            observations = tuple(
                _to_node(score)
                for score, calculated_at in authorized_scores
                if period_start <= calculated_at < period_end
            )
            periods.append(
                DashboardTrendPeriod(
                    period_start=period_start,
                    period_end=period_end,
                    observations=observations,
                )
            )
        trend = DashboardScoreTrend(as_of=as_of, periods=tuple(periods))
        return DashboardOverview(
            trend=trend,
            operational_indicators=_build_operational_indicators(authorized_scores),
        )

    def _authorize(self, actor_context: ActorContext | None) -> tuple[DashboardAccessScope, str]:
        try:
            decision = self.authorization_service.authorize_dashboard(actor_context)
        except IdentityError as exc:
            raise DashboardAuthorizationError(
                "Dashboard authorization could not be established.",
                getattr(exc, "correlation_id", "authorization-denied"),
            ) from exc
        assert actor_context is not None
        return (
            DashboardAccessScope(
                allowed_source_ids=decision.permitted_source_ids,
                can_view_enterprise=decision.can_view_enterprise,
            ),
            actor_context.correlation_id,
        )


def _validate_scoped_request(
    execution_id: str,
    access_scope: DashboardAccessScope,
    correlation_id: str,
) -> None:
    if not execution_id.strip():
        raise DashboardValidationError("execution_id is required.")
    if not isinstance(access_scope, DashboardAccessScope):
        raise DashboardValidationError("access_scope is invalid.")
    if not correlation_id.strip():
        raise DashboardValidationError("correlation_id is required.")
    if any(not source_id.strip() for source_id in access_scope.allowed_source_ids):
        raise DashboardValidationError("Authorized source IDs must not be blank.")


def _read_score_tree(
    score_reader: ScoreReader,
    execution_id: str,
    access_scope: DashboardAccessScope,
    correlation_id: str,
) -> DashboardScoreTree:
    _validate_scoped_request(execution_id, access_scope, correlation_id)
    try:
        scores = score_reader.list_for_execution(execution_id)
    except (sqlite3.Error, OSError) as exc:
        raise DashboardQueryError(
            "Dashboard score query could not be completed.", correlation_id
        ) from exc

    enterprise = next(
        (_to_node(score) for score in scores if score.scope_type is ScoreScopeType.ENTERPRISE),
        None,
    )
    if not access_scope.can_view_enterprise:
        enterprise = None
    sources = tuple(
        sorted(
            (
                _to_node(score)
                for score in scores
                if score.scope_type is ScoreScopeType.SOURCE
                and score.scope_id in access_scope.allowed_source_ids
            ),
            key=lambda node: node.scope_id or "",
        )
    )
    return DashboardScoreTree(
        execution_id=execution_id,
        enterprise=enterprise,
        sources=sources,
    )


def _to_node(score: QualityScore) -> DashboardScoreNode:
    return DashboardScoreNode(
        quality_score_id=score.quality_score_id,
        scope_type=score.scope_type,
        scope_id=score.scope_id,
        score_value=score.score_value,
        score_status=score.score_status,
        level=score.level,
        calculated_at=score.calculated_at,
    )


def _score_time_utc(score: QualityScore) -> datetime:
    calculated_at = score.calculated_at
    if calculated_at.tzinfo is None or calculated_at.utcoffset() is None:
        raise DashboardValidationError("Score calculated_at must be timezone-aware.")
    return calculated_at.astimezone(timezone.utc)


def _build_operational_indicators(
    authorized_scores: tuple[tuple[QualityScore, datetime], ...],
) -> DashboardOperationalIndicators:
    latest_by_scope: dict[tuple[ScoreScopeType, str | None], tuple[QualityScore, datetime]] = {}
    for score, calculated_at in authorized_scores:
        scope_key = (score.scope_type, score.scope_id)
        current = latest_by_scope.get(scope_key)
        if current is None or current[1] < calculated_at:
            latest_by_scope[scope_key] = (score, calculated_at)

    latest_scores = tuple(item[0] for item in latest_by_scope.values())
    if not latest_scores:
        qualification = DashboardMeasurementQualificationIndicator(
            status=MeasurementQualificationIndicatorStatus.NO_DATA,
            evaluated_scope_count=0,
            reason_codes=("NO_AUTHORIZED_MEASUREMENT",),
        )
    elif any(
        score.score_status is ScoreStatus.NOT_CALCULATED_TECHNICAL_ERROR for score in latest_scores
    ):
        qualification = DashboardMeasurementQualificationIndicator(
            status=MeasurementQualificationIndicatorStatus.TECHNICAL_FAILURE,
            evaluated_scope_count=len(latest_scores),
            reason_codes=("LATEST_MEASUREMENT_TECHNICAL_FAILURE",),
        )
    else:
        qualification = DashboardMeasurementQualificationIndicator(
            status=MeasurementQualificationIndicatorStatus.VALIDATION_REQUIRED,
            evaluated_scope_count=len(latest_scores),
            reason_codes=("QUALIFICATION_POLICY_UNAVAILABLE",),
        )

    technical_scores = tuple(
        (score, calculated_at)
        for score, calculated_at in authorized_scores
        if score.score_status is ScoreStatus.NOT_CALCULATED_TECHNICAL_ERROR
    )
    technical_errors = DashboardTechnicalErrorIndicator(
        observation_count=len(technical_scores),
        execution_count=len({score.execution_id for score, _ in technical_scores}),
        affected_source_count=len(
            {
                score.scope_id
                for score, _ in technical_scores
                if score.scope_type is ScoreScopeType.SOURCE and score.scope_id is not None
            }
        ),
        last_occurred_at=max(
            (calculated_at for _, calculated_at in technical_scores),
            default=None,
        ),
    )
    return DashboardOperationalIndicators(
        measurement_qualification=qualification,
        critical_controls=DashboardCriticalControlIndicator(
            status=CriticalControlIndicatorStatus.NOT_AVAILABLE,
            reason_code="CRITICAL_RULE_RESULT_NOT_AVAILABLE",
        ),
        technical_errors=technical_errors,
    )
