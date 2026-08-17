"""Dashboard 7 — Skorlama Politikasi Etkisi sorgu servisi."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Protocol

from veri_kalitesi.dashboard.analytics_models import (
    AnalyticsEnvelope,
    AnalyticsFilterParams,
)
from veri_kalitesi.dashboard.errors import (
    DashboardAuthorizationError,
    DashboardNotFoundError,
    DashboardValidationError,
)
from veri_kalitesi.dashboard.models import DashboardAccessScope
from veri_kalitesi.dashboard.postgresql_insights import ANALYTICS_ROW_LIMIT
from veri_kalitesi.identity import ActorContext, AuthorizationService, IdentityError

CONTRIBUTION_GRAPH_V1 = "DQ_SCORE_CONTRIBUTION_GRAPH_V1"
MAX_ITEMS = 100


class ScoringConfigurationReader(Protocol):
    def list_configurations(self) -> list[Any]: ...
    def get_configuration_by_id(self, configuration_id: str) -> Any | None: ...
    def get_active_configuration(self) -> Any | None: ...


class ScoringPolicyImpactQueryService:
    """Skorlama politikasi degisikliginin gozlenen ve simulasyon etkisini hesaplar."""

    def __init__(
        self,
        reader: ScoringConfigurationReader,
        score_reader: Any,  # PostgreSQLInsightsReader
        authorization_service: AuthorizationService,
    ) -> None:
        self._reader = reader
        self._score_reader = score_reader
        self._auth = authorization_service

    def get_scoring_policy_impact(
        self,
        actor_context: ActorContext | None,
        params: AnalyticsFilterParams,
        *,
        baseline_version: str | None = None,
        candidate_version: str | None = None,
    ) -> AnalyticsEnvelope:
        access_scope, correlation_id = self._authorize(actor_context)
        if not access_scope.can_view_enterprise:
            raise DashboardAuthorizationError(
                "Enterprise authorization is required for scoring policy impact.",
                correlation_id,
            )
        self._validate_window(params)

        configurations = self._reader.list_configurations()
        if not configurations:
            raise DashboardNotFoundError("No scoring configurations found.")

        active_config = next((c for c in configurations if c.is_active), None)
        inactive_configs = [c for c in configurations if not c.is_active]

        # Resolve baseline and candidate
        if baseline_version:
            baseline = next((c for c in configurations if c.version == baseline_version), None)
            if baseline is None:
                raise DashboardNotFoundError(
                    f"Baseline configuration version {baseline_version!r} not found."
                )
        else:
            baseline = active_config

        if candidate_version:
            candidate = next((c for c in configurations if c.version == candidate_version), None)
            if candidate is None:
                raise DashboardNotFoundError(
                    f"Candidate configuration version {candidate_version!r} not found."
                )
        else:
            candidate = inactive_configs[-1] if inactive_configs else baseline

        if baseline is None:
            raise DashboardNotFoundError("No active baseline configuration.")
        if candidate is None:
            # baseline'a dusulen dalda da None kalabilir; fail-closed.
            raise DashboardNotFoundError("No candidate configuration to compare.")

        # ── Observed impact ──
        all_scores = self._score_reader.list_scores_by_policy_version(
            start_at=params.start_at,
            end_at=params.end_at,
        )
        # F-09: Tavan asildiginda karsilastirma tam veri uzerinde yapilmis gibi
        # sunulmaz; sonuc kesik isaretlenir.
        truncated = len(all_scores) > ANALYTICS_ROW_LIMIT
        if truncated:
            all_scores = all_scores[:ANALYTICS_ROW_LIMIT]

        baseline_scores = [s for s in all_scores if s.policy_version == baseline.version]
        candidate_scores = [s for s in all_scores if s.policy_version == candidate.version]

        observed_items = self._compute_observed_impact(
            baseline_scores, candidate_scores, access_scope
        )

        # ── Simulated impact ──
        simulated_items = self._compute_simulated_impact(
            baseline_scores, baseline, candidate, access_scope
        )

        # ── Configuration diff ──
        config_diff = self._compute_config_diff(baseline, candidate)

        # ── Aggregate summary ──
        all_impact_items = observed_items + simulated_items
        improved = sum(1 for i in all_impact_items if (i.get("delta") or 0) > 0)
        deteriorated = sum(1 for i in all_impact_items if (i.get("delta") or 0) < 0)
        unchanged = sum(1 for i in all_impact_items if (i.get("delta") or 0) == 0)
        not_simulatable = sum(
            1 for i in simulated_items if i.get("reason_code") == "NOT_SIMULATABLE"
        )

        # Average deltas
        observed_deltas = [i["delta"] for i in observed_items if i.get("delta") is not None]
        simulated_deltas = [
            i["delta"]
            for i in simulated_items
            if i.get("delta") is not None and i.get("reason_code") != "NOT_SIMULATABLE"
        ]
        avg_observed = sum(observed_deltas) / len(observed_deltas) if observed_deltas else None
        avg_simulated = sum(simulated_deltas) / len(simulated_deltas) if simulated_deltas else None

        # Level changes
        level_changed = sum(
            1
            for i in all_impact_items
            if i.get("simulated_level") is not None
            and i.get("current_level") is not None
            and i["simulated_level"] != i["current_level"]
        )

        summary = {
            "active_version": active_config.version if active_config else None,
            "baseline_version": baseline.version,
            "candidate_version": candidate.version,
            "observed_average_delta": avg_observed,
            "simulated_average_delta": avg_simulated,
            "improved_count": improved,
            "deteriorated_count": deteriorated,
            "unchanged_count": unchanged,
            "level_changed_count": level_changed,
            "not_simulatable_count": not_simulatable,
            "result_truncated": truncated,
            "result_row_limit": ANALYTICS_ROW_LIMIT,
        }
        breakdowns = {
            "configuration_diff": config_diff,
        }

        # Merge and sort items by absolute delta descending
        all_items = observed_items + simulated_items
        all_items.sort(
            key=lambda i: abs(i.get("delta") or 0),
            reverse=True,
        )

        return AnalyticsEnvelope(
            summary=summary,
            breakdowns=breakdowns,
            items=all_items[:MAX_ITEMS],
        )

    # ── Observed impact ──

    def _compute_observed_impact(
        self,
        baseline_scores: list[Any],
        candidate_scores: list[Any],
        access_scope: DashboardAccessScope,
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        # Group by scope
        baseline_by_scope: dict[str, Any] = {}
        for s in baseline_scores:
            key = f"{s.scope_type}:{s.scope_id}"
            if s.scope_type == "SOURCE" and s.scope_id not in access_scope.allowed_source_ids:
                continue
            if s.scope_type == "DATASET" and s.scope_id not in access_scope.allowed_dataset_ids:
                continue
            baseline_by_scope[key] = s

        candidate_by_scope: dict[str, Any] = {}
        for s in candidate_scores:
            key = f"{s.scope_type}:{s.scope_id}"
            if s.scope_type == "SOURCE" and s.scope_id not in access_scope.allowed_source_ids:
                continue
            if s.scope_type == "DATASET" and s.scope_id not in access_scope.allowed_dataset_ids:
                continue
            candidate_by_scope[key] = s

        common_scopes = set(baseline_by_scope.keys()) & set(candidate_by_scope.keys())
        for scope_key in common_scopes:
            b = baseline_by_scope[scope_key]
            c = candidate_by_scope[scope_key]
            if b.score_value is not None and c.score_value is not None:
                delta = c.score_value - b.score_value
            else:
                delta = None
            items.append(
                {
                    "scope_type": b.scope_type,
                    "scope_id": b.scope_id,
                    "current_score": b.score_value,
                    "current_level": b.level,
                    # Gozlenen satirda karsilastirma degeri aday surumun gercek
                    # skorudur; tabloda ayni kolonda gosterilir.
                    "candidate_score": c.score_value,
                    "simulated_score": c.score_value,
                    "simulated_level": c.level,
                    "delta": delta,
                    "evidence_class": "OBSERVED",
                    "reason_code": "COMPARABLE",
                }
            )
        return items

    # ── Simulated impact ──

    def _compute_simulated_impact(
        self,
        baseline_scores: list[Any],
        baseline: Any,
        candidate: Any,
        access_scope: DashboardAccessScope,
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        score_ids = frozenset(
            s.quality_score_id for s in baseline_scores if s.score_value is not None
        )
        if not score_ids:
            return items

        graphs = self._score_reader.list_contribution_graphs(score_ids=score_ids)
        graph_map = {g.quality_score_id: g for g in graphs}

        for score in baseline_scores:
            if score.score_value is None:
                continue
            if (
                score.scope_type == "SOURCE"
                and score.scope_id not in access_scope.allowed_source_ids
            ):
                continue
            if (
                score.scope_type == "DATASET"
                and score.scope_id not in access_scope.allowed_dataset_ids
            ):
                continue

            graph = graph_map.get(score.quality_score_id)
            if graph is None:
                items.append(
                    {
                        "scope_type": score.scope_type,
                        "scope_id": score.scope_id,
                        "current_score": score.score_value,
                        "current_level": score.level,
                        "simulated_score": None,
                        "simulated_level": None,
                        "delta": None,
                        "evidence_class": "SIMULATED",
                        "reason_code": "MISSING_CONTRIBUTION_GRAPH",
                    }
                )
                continue

            if graph.graph_version != CONTRIBUTION_GRAPH_V1:
                items.append(
                    {
                        "scope_type": score.scope_type,
                        "scope_id": score.scope_id,
                        "current_score": score.score_value,
                        "current_level": score.level,
                        "simulated_score": None,
                        "simulated_level": None,
                        "delta": None,
                        "evidence_class": "SIMULATED",
                        "reason_code": "UNSUPPORTED_GRAPH_VERSION",
                    }
                )
                continue

            if not graph.official:
                items.append(
                    {
                        "scope_type": score.scope_type,
                        "scope_id": score.scope_id,
                        "current_score": score.score_value,
                        "current_level": score.level,
                        "simulated_score": None,
                        "simulated_level": None,
                        "delta": None,
                        "evidence_class": "SIMULATED",
                        "reason_code": "NO_OFFICIAL_BASELINE",
                    }
                )
                continue

            # Attempt simulation: reweight components
            simulated_result = self._simulate_score(score, graph, baseline, candidate)
            if simulated_result is None:
                items.append(
                    {
                        "scope_type": score.scope_type,
                        "scope_id": score.scope_id,
                        "current_score": score.score_value,
                        "current_level": score.level,
                        "simulated_score": None,
                        "simulated_level": None,
                        "delta": None,
                        "evidence_class": "SIMULATED",
                        "reason_code": "NOT_SIMULATABLE",
                    }
                )
                continue

            sim_score, sim_level = simulated_result
            delta = float(Decimal(str(sim_score)) - Decimal(str(score.score_value)))
            items.append(
                {
                    "scope_type": score.scope_type,
                    "scope_id": score.scope_id,
                    "current_score": score.score_value,
                    "current_level": score.level,
                    "simulated_score": sim_score,
                    "simulated_level": sim_level,
                    "delta": delta,
                    "evidence_class": "SIMULATED",
                    "reason_code": "COMPARABLE",
                }
            )
        return items

    @staticmethod
    def _simulate_score(
        score: Any,
        graph: Any,
        baseline: Any,
        candidate: Any,
    ) -> tuple[float, str | None] | None:
        """Deterministik yeniden-agirliklama; basarisizsa None."""
        components = graph.graph_data.get("components")
        if not isinstance(components, list) or not components:
            return None

        candidate_weights = candidate.dimension_weights
        if not candidate_weights:
            return None

        # Normalize candidate weights
        total_weight = sum(Decimal(str(w)) for w in candidate_weights.values())
        if total_weight <= 0:
            return None

        weighted_sum = Decimal("0")
        total_applied_weight = Decimal("0")
        for comp in components:
            if not isinstance(comp, dict):
                continue
            dimension = comp.get("dimension")
            # Katki grafigi bileseni skoru "score" alaninda tasir; "score_value"
            # eski yazimlar icin geriye donuk kabul edilir.
            comp_score = comp.get("score", comp.get("score_value"))
            if dimension is None or comp_score is None:
                continue
            weight = Decimal(str(candidate_weights.get(dimension, "0")))
            normalized_weight = weight / total_weight
            weighted_sum += Decimal(str(comp_score)) * normalized_weight
            total_applied_weight += normalized_weight

        if total_applied_weight <= 0:
            return None

        simulated_value = float(
            (weighted_sum / total_applied_weight).quantize(
                Decimal("0.0001"), rounding=ROUND_HALF_UP
            )
        )

        # Determine level from thresholds
        thresholds = candidate
        level = _compute_level(
            simulated_value,
            thresholds.critical_upper_exclusive,
            thresholds.risky_upper_exclusive,
            thresholds.acceptable_upper_exclusive,
        )
        return (simulated_value, level)

    # ── Config diff ──

    @staticmethod
    def _compute_config_diff(baseline: Any, candidate: Any) -> dict[str, Any]:
        diff: dict[str, Any] = {}
        # Thresholds
        diff["thresholds"] = {
            "critical_upper_exclusive": {
                "before": baseline.critical_upper_exclusive,
                "after": candidate.critical_upper_exclusive,
                "delta": candidate.critical_upper_exclusive - baseline.critical_upper_exclusive,
            },
            "risky_upper_exclusive": {
                "before": baseline.risky_upper_exclusive,
                "after": candidate.risky_upper_exclusive,
                "delta": candidate.risky_upper_exclusive - baseline.risky_upper_exclusive,
            },
            "acceptable_upper_exclusive": {
                "before": baseline.acceptable_upper_exclusive,
                "after": candidate.acceptable_upper_exclusive,
                "delta": candidate.acceptable_upper_exclusive - baseline.acceptable_upper_exclusive,
            },
        }
        # Dimension weights
        all_dims = set(baseline.dimension_weights.keys()) | set(candidate.dimension_weights.keys())
        dim_diff: dict[str, dict[str, Any]] = {}
        for dim in sorted(all_dims):
            before = baseline.dimension_weights.get(dim, 0)
            after = candidate.dimension_weights.get(dim, 0)
            dim_diff[dim] = {
                "before": float(before) if before else 0,
                "after": float(after) if after else 0,
                "delta": float(after - before) if before is not None and after is not None else 0,
            }
        diff["dimension_weights"] = dim_diff

        # Criticality weights
        all_crit = set(baseline.criticality_weights.keys()) | set(
            candidate.criticality_weights.keys()
        )
        crit_diff: dict[str, dict[str, Any]] = {}
        for crit in sorted(all_crit):
            before = baseline.criticality_weights.get(crit, 0)
            after = candidate.criticality_weights.get(crit, 0)
            crit_diff[crit] = {
                "before": float(before) if before else 0,
                "after": float(after) if after else 0,
                "delta": float(after - before) if before is not None and after is not None else 0,
            }
        diff["criticality_weights"] = crit_diff
        return diff

    # ── Private helpers ──

    def _authorize(self, actor_context: ActorContext | None) -> tuple[DashboardAccessScope, str]:
        try:
            decision = self._auth.authorize_dashboard(actor_context)
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

    @staticmethod
    def _validate_window(params: AnalyticsFilterParams) -> None:
        if params.start_at.tzinfo is None or params.start_at.utcoffset() is None:
            raise DashboardValidationError("start_at must be timezone-aware.")
        if params.end_at.tzinfo is None or params.end_at.utcoffset() is None:
            raise DashboardValidationError("end_at must be timezone-aware.")
        if params.window_days > 365:
            raise DashboardValidationError("Date range exceeds 365 days.")


def _compute_level(
    score: float,
    critical_upper: float,
    risky_upper: float,
    acceptable_upper: float,
) -> str:
    """Skor degerine gore seviye belirler."""
    if score < critical_upper:
        return "CRITICAL"
    if score < risky_upper:
        return "RISKY"
    if score < acceptable_upper:
        return "ACCEPTABLE"
    return "GOOD"
