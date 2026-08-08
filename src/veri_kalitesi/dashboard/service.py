"""Yetki filtreli dashboard skor agaci okuma servisi."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Callable, Protocol

from veri_kalitesi.dashboard.errors import (
    DashboardAuthorizationError,
    DashboardNotFoundError,
    DashboardQueryError,
    DashboardValidationError,
)
from veri_kalitesi.dashboard.models import (
    AppliedDashboardFilters,
    DashboardAccessScope,
    DashboardCriticalControlIndicator,
    DashboardFilterLevel,
    DashboardFilterParams,
    DashboardFilterScoreStatus,
    DashboardFilterScopeType,
    DashboardMeasurementQualificationIndicator,
    DashboardOperationalIndicators,
    DashboardOverview,
    DashboardScoreNode,
    DashboardScoreTrend,
    DashboardScoreTree,
    DashboardTechnicalErrorIndicator,
    DashboardTrendComponents,
    DashboardTrendPeriod,
    CriticalControlIndicatorStatus,
    MeasurementQualificationIndicatorStatus,
)
from veri_kalitesi.identity import ActorContext, AuthorizationService, IdentityError
from veri_kalitesi.lineage.governance import (
    DataAssetGovernanceProfile,
    governance_projection,
    resolve_active_profile,
)
from veri_kalitesi.scoring.models import (
    QualityScore,
    ScoreScopeType,
    ScoreStatus,
    is_official_score,
)
from veri_kalitesi.scoring.contributions import compare_scores, contribution_graph
from veri_kalitesi.scoring.trends import (
    TrendComponentResult,
    TrendPolicy,
    compute_trend_components,
)


class ScoreReader(Protocol):
    def list_for_execution(self, execution_id: str) -> list[QualityScore]: ...

    def list_for_dashboard_trend(
        self,
        start_at: datetime,
        end_at: datetime,
        allowed_source_ids: frozenset[str],
        include_enterprise: bool,
    ) -> list[QualityScore]: ...


class GovernanceProfileReader(Protocol):
    def list_governance_profiles(self, asset_ref: str) -> list[DataAssetGovernanceProfile]: ...


class DashboardQueryService:
    def __init__(
        self,
        score_reader: ScoreReader,
        authorization_service: AuthorizationService,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        governance_reader: GovernanceProfileReader | None = None,
        trend_policy: TrendPolicy | None = None,
    ) -> None:
        self.score_reader = score_reader
        self.authorization_service = authorization_service
        self.clock = clock
        self.governance_reader = governance_reader
        self.trend_policy = trend_policy

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
        filters: DashboardFilterParams | None = None,
    ) -> DashboardOverview:
        access_scope, correlation_id = self._authorize(actor_context)
        now = self.clock()
        if now.tzinfo is None or now.utcoffset() is None:
            raise DashboardValidationError("Dashboard trend clock must be timezone-aware.")
        as_of = now.astimezone(timezone.utc)
        current_day = as_of.replace(hour=0, minute=0, second=0, microsecond=0)

        # --- FR-057: Tarih aralığı filtresi ---
        if filters and (filters.start_date or filters.end_date):
            window_start = _resolve_filter_start(filters, current_day)
            window_end = _resolve_filter_end(filters, as_of)
            if window_start >= window_end:
                raise DashboardValidationError(
                    "Dashboard filter date range is invalid: start must be before end."
                )
        else:
            window_start = current_day - timedelta(days=29)
            window_end = as_of

        # --- FR-057: Kapsam filtresi yetki doğrulaması (AC-03) ---
        query_source_ids = access_scope.allowed_source_ids
        if filters and filters.scope_id:
            if filters.scope_type is DashboardFilterScopeType.ENTERPRISE:
                if not access_scope.can_view_enterprise:
                    raise DashboardAuthorizationError(
                        "Enterprise scope is outside the authorized dashboard scope.",
                        correlation_id,
                    )
            else:
                if filters.scope_id not in access_scope.allowed_source_ids:
                    raise DashboardAuthorizationError(
                        "Requested scope_id is outside the authorized dashboard scope.",
                        correlation_id,
                    )
                query_source_ids = frozenset({filters.scope_id})
        elif filters and filters.scope_type is DashboardFilterScopeType.ENTERPRISE:
            if not access_scope.can_view_enterprise:
                raise DashboardAuthorizationError(
                    "Enterprise scope is outside the authorized dashboard scope.",
                    correlation_id,
                )
        elif filters and filters.scope_type is DashboardFilterScopeType.SOURCE:
            if not access_scope.allowed_source_ids:
                raise DashboardAuthorizationError(
                    "Source scope is outside the authorized dashboard scope.",
                    correlation_id,
                )

        # --- DQ-SCR-027: Trend hesabi için sorgu penceresini genislet ---
        trend_policy = self.trend_policy
        if trend_policy is not None:
            lookback_days = max(trend_policy.lookback_count, 1)
            query_start = window_start - timedelta(days=lookback_days)
        else:
            query_start = window_start

        try:
            scores = self.score_reader.list_for_dashboard_trend(
                query_start,
                window_end,
                query_source_ids,
                access_scope.can_view_enterprise
                and (not filters or filters.scope_type is not DashboardFilterScopeType.SOURCE),
            )
        except (sqlite3.Error, OSError) as exc:
            raise DashboardQueryError(
                "Dashboard trend query could not be completed.", correlation_id
            ) from exc
        scored_at = tuple((score, _score_time_utc(score)) for score in scores)
        all_authorized = tuple(
            (score, calculated_at)
            for score, calculated_at in scored_at
            if query_start <= calculated_at <= window_end
            and (
                (score.scope_type is ScoreScopeType.SOURCE and score.scope_id in query_source_ids)
                or (
                    score.scope_type is ScoreScopeType.ENTERPRISE
                    and access_scope.can_view_enterprise
                    and (not filters or filters.scope_type is not DashboardFilterScopeType.SOURCE)
                )
            )
        )
        # Goruntü penceresi (trend hesabi genisletilmis pencereden bagimsiz)
        authorized_scores = tuple(
            (score, calculated_at)
            for score, calculated_at in all_authorized
            if window_start <= calculated_at <= window_end
        )

        # --- FR-057: Skor-düzeyi filtreler (AC-06) ---
        if filters and (filters.score_status or filters.level):
            authorized_scores = _apply_score_filters(
                authorized_scores,
                score_status_filter=filters.score_status,
                level_filter=filters.level,
            )

        day_count = max((window_end - window_start).days + 1, 1)
        periods = []
        for day_offset in range(day_count):
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
        role_view = (
            "ENGINEER"
            if actor_context is not None and "DATA_ENGINEER" in actor_context.roles
            else "EXECUTIVE"
        )
        periods = _decorate_comparisons(
            periods,
            authorized_scores,
            include_graph=role_view == "ENGINEER",
            access_scope=access_scope,
            governance_reader=self.governance_reader,
            correlation_id=correlation_id,
        )

        # --- DQ-SCR-027: Trend bilesenlerini hesapla ve ekle ---
        if trend_policy is not None:
            trend_scores = [score for score, _ in all_authorized]
            trend_map = compute_trend_components(trend_scores, trend_policy)
            periods = _attach_trend_components(periods, trend_map)

        trend = DashboardScoreTrend(as_of=as_of, periods=tuple(periods))
        applied_filters = AppliedDashboardFilters(
            window_start=window_start,
            window_end=window_end,
            scope_type=filters.scope_type.value if filters and filters.scope_type else None,
            scope_id=filters.scope_id if filters and filters.scope_id else None,
            score_status=filters.score_status.value if filters and filters.score_status else None,
            level=filters.level.value if filters and filters.level else None,
        )
        return DashboardOverview(
            trend=trend,
            operational_indicators=_build_operational_indicators(authorized_scores),
            role_view=role_view,
            applied_filters=applied_filters,
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
                allowed_dataset_ids=decision.permitted_dataset_ids,
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
    if any(not dataset_id.strip() for dataset_id in access_scope.allowed_dataset_ids):
        raise DashboardValidationError("Authorized dataset IDs must not be blank.")


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


def _decorate_comparisons(
    periods: list[DashboardTrendPeriod],
    authorized_scores: tuple[tuple[QualityScore, datetime], ...],
    *,
    include_graph: bool,
    access_scope: DashboardAccessScope,
    governance_reader: GovernanceProfileReader | None = None,
    correlation_id: str = "",
) -> list[DashboardTrendPeriod]:
    previous_by_scope: dict[tuple[ScoreScopeType, str | None], QualityScore] = {}
    decorated: dict[str, DashboardScoreNode] = {}
    for score, _ in sorted(authorized_scores, key=lambda item: item[1]):
        key = (score.scope_type, score.scope_id)
        previous = previous_by_scope.get(key)
        comparison = compare_scores(score, previous) if previous is not None else None
        graph = contribution_graph(score)
        if comparison is not None:
            comparison_status = comparison.status.value
            comparison_reason_codes = comparison.reason_codes
            change = comparison.delta
        elif is_official_score(score):
            comparison_status = "UNKNOWN"
            comparison_reason_codes = ("NO_PREVIOUS_OBSERVATION",)
            change = None
        else:
            comparison_status = "NOT_COMPARABLE"
            comparison_reason_codes = ("NON_OFFICIAL_RESULT",)
            change = None
        graph["deterioration_status"] = _deterioration_status(
            comparison_status,
            change,
        )
        _apply_governance(
            graph,
            score,
            governance_reader=governance_reader,
            correlation_id=correlation_id,
        )
        decorated[score.quality_score_id] = DashboardScoreNode(
            quality_score_id=score.quality_score_id,
            scope_type=score.scope_type,
            scope_id=score.scope_id,
            score_value=score.score_value,
            score_status=score.score_status,
            level=score.level,
            calculated_at=score.calculated_at,
            comparison_status=comparison_status,
            comparison_reason_codes=comparison_reason_codes,
            change=change,
            contribution_graph=(
                _filter_engineer_graph(graph, access_scope)
                if include_graph
                else {
                    "graph_version": graph["graph_version"],
                    "official": graph["official"],
                    "measurement_qualification": graph["measurement_qualification"],
                    "critical_rule_status": graph["critical_rule_status"],
                    "critical_asset_status": graph["critical_asset_status"],
                    "deterioration_status": graph["deterioration_status"],
                    "risk_status": graph["risk_status"],
                    "sla_status": graph["sla_status"],
                    "usage_decision": graph["usage_decision"],
                    "coverage_status": graph["coverage_status"],
                    "governance": graph["governance"],
                }
            ),
        )
        if is_official_score(score):
            previous_by_scope[key] = score
    return [
        DashboardTrendPeriod(
            period_start=period.period_start,
            period_end=period.period_end,
            observations=tuple(decorated[node.quality_score_id] for node in period.observations),
        )
        for period in periods
    ]


def _apply_governance(
    graph: dict[str, object],
    score: QualityScore,
    *,
    governance_reader: GovernanceProfileReader | None,
    correlation_id: str,
) -> None:
    """Yalnız kanıtı olan kritik asset/risk/SLA alanlarını profil ile besler."""

    if governance_reader is None or score.scope_id is None:
        graph["governance"] = {
            "governance_profile_status": "NO_ACTIVE_PROFILE",
            "governance_reason_codes": ["NO_GOVERNANCE_SOURCE"],
            "governance_version": None,
            "governance_asset_ref": None,
        }
        return
    try:
        profiles = governance_reader.list_governance_profiles(score.scope_id)
    except (sqlite3.Error, OSError) as exc:
        raise DashboardQueryError(
            "Dashboard governance profile query could not be completed.",
            correlation_id,
        ) from exc
    projection = governance_projection(resolve_active_profile(profiles, score.calculated_at))
    for key in ("critical_asset_status", "risk_status", "sla_status"):
        if graph.get(key) == "UNKNOWN":
            graph[key] = projection[key]
    graph["governance"] = {
        "governance_profile_status": projection["governance_profile_status"],
        "governance_reason_codes": projection["governance_reason_codes"],
        "governance_version": projection["governance_version"],
        "governance_asset_ref": projection["governance_asset_ref"],
    }


def _deterioration_status(
    comparison_status: str,
    change: object,
) -> str:
    if comparison_status != "COMPARABLE" or not isinstance(change, Decimal):
        return "UNKNOWN"
    if change < 0:
        return "DETERIORATING"
    if change > 0:
        return "IMPROVING"
    return "STABLE"


def _filter_engineer_graph(
    graph: dict[str, object],
    access_scope: DashboardAccessScope,
) -> dict[str, object]:
    components = graph.get("components")
    if not isinstance(components, list):
        return {**graph, "components": []}
    visible = []
    for component in components:
        if not isinstance(component, dict):
            continue
        dataset_id = component.get("dataset_id")
        source_id = component.get("data_source_id")
        if isinstance(dataset_id, str) and dataset_id not in access_scope.allowed_dataset_ids:
            continue
        if isinstance(source_id, str) and source_id not in access_scope.allowed_source_ids:
            continue
        visible.append(component)
    return {**graph, "components": visible}


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


def _resolve_filter_start(
    filters: DashboardFilterParams,
    default: datetime,
) -> datetime:
    """Filtre başlangıcını çözer; belirtilmediyse varsayılan 30 gün öncesi."""
    if filters.start_date is not None:
        start = filters.start_date
        if start.tzinfo is None or start.utcoffset() is None:
            raise DashboardValidationError("Dashboard filter start_date must be timezone-aware.")
        return start.astimezone(timezone.utc)
    return default - timedelta(days=29)


def _resolve_filter_end(
    filters: DashboardFilterParams,
    default: datetime,
) -> datetime:
    """Filtre bitişini çözer; belirtilmediyse mevcut zaman."""
    if filters.end_date is not None:
        end = filters.end_date
        if end.tzinfo is None or end.utcoffset() is None:
            raise DashboardValidationError("Dashboard filter end_date must be timezone-aware.")
        return end.astimezone(timezone.utc)
    return default


def _apply_score_filters(
    authorized_scores: tuple[tuple[QualityScore, datetime], ...],
    *,
    score_status_filter: DashboardFilterScoreStatus | None,
    level_filter: DashboardFilterLevel | None,
) -> tuple[tuple[QualityScore, datetime], ...]:
    """AC-06: Skor-düzeyi filtreler; durum/sezgi ayrımı korunur."""
    result = []
    for score, calculated_at in authorized_scores:
        if score_status_filter is not None:
            if score.score_status.value != score_status_filter.value:
                continue
        if level_filter is not None:
            score_level_value = score.level.value if score.level is not None else None
            if score_level_value != level_filter.value:
                continue
        result.append((score, calculated_at))
    return tuple(result)


def _attach_trend_components(
    periods: list[DashboardTrendPeriod],
    trend_map: dict[str, TrendComponentResult],
) -> list[DashboardTrendPeriod]:
    """Trend bilesenlerini mevcut DashboardScoreNode'lara ekler."""

    return [
        DashboardTrendPeriod(
            period_start=period.period_start,
            period_end=period.period_end,
            observations=tuple(
                _with_trend(node, trend_map.get(node.quality_score_id))
                for node in period.observations
            ),
        )
        for period in periods
    ]


def _with_trend(
    node: DashboardScoreNode,
    result: TrendComponentResult | None,
) -> DashboardScoreNode:
    """DashboardScoreNode'a trend bilesenlerini ekler."""

    if result is None:
        return node
    return DashboardScoreNode(
        quality_score_id=node.quality_score_id,
        scope_type=node.scope_type,
        scope_id=node.scope_id,
        score_value=node.score_value,
        score_status=node.score_status,
        level=node.level,
        calculated_at=node.calculated_at,
        comparison_status=node.comparison_status,
        comparison_reason_codes=node.comparison_reason_codes,
        change=node.change,
        contribution_graph=node.contribution_graph,
        trend=_to_dashboard_trend(result),
    )


def _to_dashboard_trend(result: TrendComponentResult) -> DashboardTrendComponents:
    """TrendComponentResult'i dashboard modeline dönüştürür."""

    return DashboardTrendComponents(
        moving_average=result.moving_average,
        consecutive_deterioration_count=result.consecutive_deterioration_count,
        sudden_deterioration=result.sudden_deterioration,
        time_below_threshold_periods=result.time_below_threshold_periods,
        improvement_persistence=result.improvement_persistence,
        version_boundary=result.version_boundary,
        policy_version=result.policy_version,
    )
