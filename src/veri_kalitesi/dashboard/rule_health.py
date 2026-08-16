"""Dashboard 4 — Kural Kapsama ve Guvenilirlik sorgu servisi."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from veri_kalitesi.dashboard.analytics_models import (
    AnalyticsEnvelope,
    AnalyticsFilterParams,
    MetricRatio,
    ratio_to_dict,
)
from veri_kalitesi.dashboard.errors import (
    DashboardAuthorizationError,
    DashboardValidationError,
)
from veri_kalitesi.dashboard.models import DashboardAccessScope
from veri_kalitesi.identity import ActorContext, AuthorizationService, IdentityError


# ── Protocol ──


class RuleHealthReader(Protocol):
    def list_active_datasets(
        self,
        *,
        permitted_source_ids: frozenset[str],
        permitted_dataset_ids: frozenset[str],
        source_id: str | None = None,
    ) -> list[Any]: ...

    def list_active_fields(self, *, dataset_ids: frozenset[str]) -> list[Any]: ...

    def list_active_rules(self, *, dataset_ids: frozenset[str]) -> list[Any]: ...

    def list_latest_versions(self, *, rule_ids: frozenset[str]) -> list[Any]: ...

    def list_scores_for_rules(
        self,
        *,
        rule_version_ids: frozenset[str],
        start_at: datetime,
        end_at: datetime,
    ) -> list[Any]: ...


# ── Service ──

OPEN_STATUSES = frozenset({"CALCULATED", "PARTIAL"})
TECHNICAL_ERROR_STATUSES = frozenset(
    {"NOT_CALCULATED_TECHNICAL_ERROR", "CONFIG_ERROR"}
)
FLAKY_TRANSITION_THRESHOLD = 2
FLAKY_WINDOW = 10
MAX_ITEMS = 100


class RuleHealthQueryService:
    """Kural kapsama ve guvenilirlik metriklerini hesaplar."""

    def __init__(
        self,
        reader: RuleHealthReader,
        authorization_service: AuthorizationService,
    ) -> None:
        self._reader = reader
        self._auth = authorization_service

    def get_rule_health(
        self,
        actor_context: ActorContext | None,
        params: AnalyticsFilterParams,
        *,
        dimension: str | None = None,
        criticality: str | None = None,
        rule_status: str | None = None,
    ) -> AnalyticsEnvelope:
        access_scope, correlation_id = self._authorize(actor_context)
        self._validate_window(params)

        datasets = self._reader.list_active_datasets(
            permitted_source_ids=access_scope.allowed_source_ids,
            permitted_dataset_ids=access_scope.allowed_dataset_ids,
            source_id=params.source_id,
        )
        dataset_ids = frozenset(d.dataset_id for d in datasets)
        fields = self._reader.list_active_fields(dataset_ids=dataset_ids)
        rules = self._reader.list_active_rules(dataset_ids=dataset_ids)

        # Optional filters
        if dimension:
            rules = [r for r in rules if r.primary_dimension == dimension]
        if rule_status:
            rules = [r for r in rules if r.status == rule_status]

        rule_ids = frozenset(r.quality_rule_id for r in rules)
        versions = self._reader.list_latest_versions(rule_ids=rule_ids)
        version_map = {v.quality_rule_id: v for v in versions}

        if criticality:
            versions_filtered = [v for v in versions if v.criticality == criticality]
            version_ids = frozenset(v.rule_version_id for v in versions_filtered)
        else:
            version_ids = frozenset(v.rule_version_id for v in versions)

        scores = self._reader.list_scores_for_rules(
            rule_version_ids=version_ids,
            start_at=params.start_at,
            end_at=params.end_at,
        )

        # ── Coverage metrics ──
        eligible_dataset_count = len(datasets)
        covered_dataset_ids = frozenset(r.dataset_id for r in rules)
        covered_dataset_count = len(covered_dataset_ids & dataset_ids)

        all_active_field_ids = frozenset(f.data_field_id for f in fields)
        covered_field_ids: set[str] = set()
        for rule in rules:
            covered_field_ids.update(rule.field_ids)
        covered_field_ids &= all_active_field_ids

        high_crit_datasets = frozenset(
            d.dataset_id for d in datasets if d.criticality in ("HIGH", "CRITICAL")
        )
        critical_covered = frozenset()
        if high_crit_datasets:
            high_crit_rules = [
                r
                for r in rules
                if r.dataset_id in high_crit_datasets
                and version_map.get(r.quality_rule_id)
                and version_map[r.quality_rule_id].criticality in ("HIGH", "CRITICAL")
            ]
            critical_covered = frozenset(r.dataset_id for r in high_crit_rules)

        dataset_coverage = MetricRatio(
            numerator=covered_dataset_count,
            denominator=eligible_dataset_count,
            reason_code="NO_ELIGIBLE_ITEMS" if eligible_dataset_count == 0 else None,
        )
        field_coverage = MetricRatio(
            numerator=len(covered_field_ids),
            denominator=len(all_active_field_ids),
            reason_code="NO_ELIGIBLE_ITEMS" if not all_active_field_ids else None,
        )
        critical_coverage = MetricRatio(
            numerator=len(critical_covered),
            denominator=len(high_crit_datasets),
            reason_code="NO_ELIGIBLE_ITEMS" if not high_crit_datasets else None,
        )

        # ── Reliability metrics ──
        never_executed_rules = self._compute_never_executed(rules, version_map, scores)
        tech_error_scores = [
            s for s in scores if s.score_status in TECHNICAL_ERROR_STATUSES
        ]
        all_observations = len(scores)
        tech_error_ratio = MetricRatio(
            numerator=len(tech_error_scores),
            denominator=all_observations,
            reason_code="NO_ELIGIBLE_ITEMS" if all_observations == 0 else None,
        )

        # Success rate: official numeric scores where score_value >= threshold
        official_scores = [
            s
            for s in scores
            if s.score_value is not None
            and s.score_status == "CALCULATED"
            and s.rule_version_id is not None
        ]
        rv_threshold_map = {v.rule_version_id: v.threshold for v in versions}
        passing = sum(
            1
            for s in official_scores
            if s.score_value is not None
            and rv_threshold_map.get(s.rule_version_id) is not None
            and s.score_value >= rv_threshold_map[s.rule_version_id]
        )
        success_rate = MetricRatio(
            numerator=passing,
            denominator=len(official_scores),
            reason_code="NO_ELIGIBLE_ITEMS" if not official_scores else None,
        )

        # Flaky rules: last N=10 official observations, >= 2 transitions
        flaky_rule_ids = self._compute_flaky_rules(
            official_scores, rv_threshold_map
        )

        # ── Items: top risky rules ──
        items = self._build_items(
            rules, version_map, scores, flaky_rule_ids, datasets
        )

        # ── Breakdowns ──
        dim_breakdown: dict[str, int] = {}
        status_breakdown: dict[str, int] = {}
        crit_breakdown: dict[str, int] = {}
        for rule in rules:
            dim_breakdown[rule.primary_dimension] = (
                dim_breakdown.get(rule.primary_dimension, 0) + 1
            )
            status_breakdown[rule.status] = (
                status_breakdown.get(rule.status, 0) + 1
            )
        for v in versions:
            crit_breakdown[v.criticality] = (
                crit_breakdown.get(v.criticality, 0) + 1
            )

        summary = {
            "dataset_coverage": ratio_to_dict(dataset_coverage),
            "field_coverage": ratio_to_dict(field_coverage),
            "critical_coverage": ratio_to_dict(critical_coverage),
            "active_rule_count": len(rules),
            "never_executed_count": len(never_executed_rules),
            "flaky_rule_count": len(flaky_rule_ids),
            "technical_error_ratio": ratio_to_dict(tech_error_ratio),
            "success_rate": ratio_to_dict(success_rate),
        }
        breakdowns = {
            "by_dimension": dim_breakdown,
            "by_status": status_breakdown,
            "by_criticality": crit_breakdown,
        }
        return AnalyticsEnvelope(
            summary=summary,
            breakdowns=breakdowns,
            items=items[:MAX_ITEMS],
        )

    # ── Private helpers ──

    def _authorize(
        self, actor_context: ActorContext | None
    ) -> tuple[DashboardAccessScope, str]:
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

    @staticmethod
    def _compute_never_executed(
        rules: list[Any],
        version_map: dict[str, Any],
        scores: list[Any],
    ) -> frozenset[str]:
        scored_rule_version_ids = frozenset(
            s.rule_version_id for s in scores if s.rule_version_id is not None
        )
        never: set[str] = set()
        for rule in rules:
            version = version_map.get(rule.quality_rule_id)
            if version is None:
                never.add(rule.quality_rule_id)
            elif version.rule_version_id not in scored_rule_version_ids:
                never.add(rule.quality_rule_id)
        return frozenset(never)

    @staticmethod
    def _compute_flaky_rules(
        official_scores: list[Any],
        rv_threshold_map: dict[str, float],
    ) -> frozenset[str]:
        # Group scores by rule_version_id, ordered by calculated_at
        from collections import defaultdict

        by_rv: dict[str, list[Any]] = defaultdict(list)
        for s in official_scores:
            if s.rule_version_id is not None:
                by_rv[s.rule_version_id].append(s)

        flaky: set[str] = set()
        for rv_id, rv_scores in by_rv.items():
            rv_scores.sort(key=lambda s: s.calculated_at)
            last_n = rv_scores[-FLAKY_WINDOW:]
            threshold = rv_threshold_map.get(rv_id)
            if threshold is None or len(last_n) < 2:
                continue
            transitions = 0
            first_val = last_n[0].score_value
            prev_pass = (
                first_val >= threshold if first_val is not None else None
            )
            for s in last_n[1:]:
                if s.score_value is None:
                    continue
                curr_pass = s.score_value >= threshold
                if prev_pass is not None and curr_pass != prev_pass:
                    transitions += 1
                prev_pass = curr_pass
            if transitions >= FLAKY_TRANSITION_THRESHOLD:
                flaky.add(rv_id)
        return frozenset(flaky)

    @staticmethod
    def _build_items(
        rules: list[Any],
        version_map: dict[str, Any],
        scores: list[Any],
        flaky_rule_ids: frozenset[str],
        datasets: list[Any],
    ) -> list[dict[str, Any]]:
        dataset_name_map = {d.dataset_id: d.name for d in datasets}
        from collections import defaultdict

        scores_by_rv: dict[str, list[Any]] = defaultdict(list)
        for s in scores:
            if s.rule_version_id:
                scores_by_rv[s.rule_version_id].append(s)

        items: list[dict[str, Any]] = []
        for rule in rules:
            version = version_map.get(rule.quality_rule_id)
            if version is None:
                items.append(
                    {
                        "quality_rule_id": rule.quality_rule_id,
                        "rule_version_id": None,
                        "code": rule.code,
                        "dataset_id": rule.dataset_id,
                        "dataset_name": dataset_name_map.get(rule.dataset_id),
                        "dimension": rule.primary_dimension,
                        "criticality": None,
                        "last_score_at": None,
                        "last_score_value": None,
                        "success_rate": None,
                        "technical_error_count": 0,
                        "transition_count": 0,
                        "reason_code": "NO_VERSION",
                    }
                )
                continue

            rv_scores = scores_by_rv.get(version.rule_version_id, [])
            last_score = rv_scores[-1] if rv_scores else None
            tech_errors = sum(
                1 for s in rv_scores if s.score_status in TECHNICAL_ERROR_STATUSES
            )
            is_flaky = version.rule_version_id in flaky_rule_ids

            # Determine reason codes
            reason_codes: list[str] = []
            if not rv_scores:
                reason_codes.append("NEVER_EXECUTED")
            if tech_errors > 0:
                reason_codes.append("TECHNICAL_ERRORS")
            if is_flaky:
                reason_codes.append("FLAKY_RULE")
            if not reason_codes:
                reason_codes.append("OK")

            items.append(
                {
                    "quality_rule_id": rule.quality_rule_id,
                    "rule_version_id": version.rule_version_id,
                    "code": rule.code,
                    "dataset_id": rule.dataset_id,
                    "dataset_name": dataset_name_map.get(rule.dataset_id),
                    "dimension": rule.primary_dimension,
                    "criticality": version.criticality,
                    "last_score_at": (
                        last_score.calculated_at.isoformat()
                        if last_score
                        else None
                    ),
                    "last_score_value": (
                        last_score.score_value if last_score else None
                    ),
                    "success_rate": None,  # computed per-rule if needed
                    "technical_error_count": tech_errors,
                    "transition_count": FLAKY_TRANSITION_THRESHOLD if is_flaky else 0,
                    "reason_code": reason_codes[0],
                }
            )
        # Sort by risk: never_executed and flaky first
        priority = {
            "NO_VERSION": 0,
            "NEVER_EXECUTED": 1,
            "FLAKY_RULE": 2,
            "TECHNICAL_ERRORS": 3,
            "OK": 99,
        }
        items.sort(key=lambda i: priority.get(i["reason_code"], 50))
        return items
