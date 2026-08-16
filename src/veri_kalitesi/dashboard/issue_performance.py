"""Dashboard 6 — Issue ve Iyilestirme performans sorgu servisi."""

from __future__ import annotations

from collections import defaultdict
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
from veri_kalitesi.dashboard.postgresql_insights import ANALYTICS_ROW_LIMIT
from veri_kalitesi.identity import ActorContext, AuthorizationService, IdentityError

OPEN_STATUSES = frozenset({"NEW", "ASSIGNED", "INVESTIGATING", "WAITING_FOR_RESOLUTION"})
AGE_BUCKETS = [
    ("0-1", 0, 1),
    ("2-3", 2, 3),
    ("4-7", 4, 7),
    ("8-14", 8, 14),
    ("15+", 15, None),
]
MAX_ITEMS = 100


class IssuePerformanceReader(Protocol):
    def list_issues_for_scopes(
        self,
        *,
        permitted_source_ids: frozenset[str],
        permitted_dataset_ids: frozenset[str],
        start_at: datetime,
        end_at: datetime,
    ) -> list[Any]: ...

    def list_history_for_issues(self, *, issue_ids: frozenset[str]) -> list[Any]: ...

    def list_issue_relationships(self, *, issue_ids: frozenset[str]) -> list[Any]: ...


class IssuePerformanceQueryService:
    """Issue yasam dongusu metriklerini issue_history olaylarindan hesaplar."""

    def __init__(
        self,
        reader: IssuePerformanceReader,
        authorization_service: AuthorizationService,
    ) -> None:
        self._reader = reader
        self._auth = authorization_service

    def get_issue_performance(
        self,
        actor_context: ActorContext | None,
        params: AnalyticsFilterParams,
        *,
        priority: str | None = None,
        status: str | None = None,
        trigger_type: str | None = None,
    ) -> AnalyticsEnvelope:
        access_scope, correlation_id = self._authorize(actor_context)
        self._validate_window(params)
        as_of = params.end_at

        issues = self._reader.list_issues_for_scopes(
            permitted_source_ids=access_scope.allowed_source_ids,
            permitted_dataset_ids=access_scope.allowed_dataset_ids,
            start_at=params.start_at,
            end_at=params.end_at,
        )
        # F-09: Depo tavanin bir fazlasini ceker; fazlalik geldiginde metrikler
        # tam veri uzerinde hesaplanmis gibi sunulmaz, sonuc kesik isaretlenir.
        truncated = len(issues) > ANALYTICS_ROW_LIMIT
        if truncated:
            issues = issues[:ANALYTICS_ROW_LIMIT]

        # Optional filters
        if priority:
            issues = [i for i in issues if i.priority == priority]
        if status:
            issues = [i for i in issues if i.status == status]
        if trigger_type:
            issues = [i for i in issues if i.trigger_type == trigger_type]

        issue_ids = frozenset(i.issue_id for i in issues)
        history = self._reader.list_history_for_issues(issue_ids=issue_ids)
        relationships = self._reader.list_issue_relationships(issue_ids=issue_ids)

        # Group history by issue_id
        history_by_issue: dict[str, list[Any]] = defaultdict(list)
        for h in history:
            history_by_issue[h.issue_id].append(h)
        # Sort each issue's history by occurred_at
        for iid in history_by_issue:
            history_by_issue[iid].sort(key=lambda h: h.occurred_at)

        # ── Open issues ──
        open_issues = [i for i in issues if i.status in OPEN_STATUSES]
        critical_open = [i for i in open_issues if i.priority in ("HIGH", "CRITICAL")]

        # ── MTTA: created_at -> first ISSUE_INVESTIGATION_STARTED ──
        mtta_values: list[float] = []
        missing_timeline_count = 0
        for issue in issues:
            ih = history_by_issue.get(issue.issue_id, [])
            first_investigation = next(
                (h for h in ih if h.action == "ISSUE_INVESTIGATION_STARTED"),
                None,
            )
            if first_investigation is not None:
                delta = (first_investigation.occurred_at - issue.created_at).total_seconds()
                if delta >= 0:
                    mtta_values.append(delta)
            elif issue.status not in OPEN_STATUSES:
                # Closed/resolved without investigation — missing timeline
                missing_timeline_count += 1

        # ── MTTR: created_at -> first ISSUE_RESOLVED ──
        mttr_values: list[float] = []
        unresolved_count = 0
        for issue in issues:
            ih = history_by_issue.get(issue.issue_id, [])
            first_resolved = next(
                (h for h in ih if h.action == "ISSUE_RESOLVED"),
                None,
            )
            if first_resolved is not None:
                delta = (first_resolved.occurred_at - issue.created_at).total_seconds()
                if delta >= 0:
                    mttr_values.append(delta)
            else:
                unresolved_count += 1

        # ── Verification time: first RESOLVED -> first VERIFIED ──
        verification_values: list[float] = []
        for issue in issues:
            ih = history_by_issue.get(issue.issue_id, [])
            first_resolved = next(
                (h for h in ih if h.action == "ISSUE_RESOLVED"),
                None,
            )
            first_verified = next(
                (h for h in ih if h.action == "ISSUE_VERIFIED"),
                None,
            )
            if first_resolved is not None and first_verified is not None:
                delta = (first_verified.occurred_at - first_resolved.occurred_at).total_seconds()
                if delta >= 0:
                    verification_values.append(delta)

        # ── Resolution success rate ──
        verified_issues = [
            i
            for i in issues
            if any(h.action == "ISSUE_VERIFIED" for h in history_by_issue.get(i.issue_id, []))
        ]
        verified_with_result = [
            i
            for i in verified_issues
            if any(h.action == "ISSUE_VERIFIED" for h in history_by_issue.get(i.issue_id, []))
        ]
        verification_success = MetricRatio(
            numerator=len(verified_with_result),
            denominator=len(verified_issues) if verified_issues else 0,
            reason_code="NO_ELIGIBLE_ITEMS" if not verified_issues else None,
        )

        # ── Recurring issues ──
        recurrence_set: set[str] = set()
        for rel in relationships:
            if rel.relationship_type == "RECURRENCE":
                recurrence_set.add(rel.predecessor_issue_id)
                recurrence_set.add(rel.successor_issue_id)
        recurring_issues = [
            i for i in issues if i.occurrence_count > 1 or i.issue_id in recurrence_set
        ]

        # ── Reopened: ISSUE_VERIFICATION_FAILED history ──
        reopened_count = sum(
            1
            for i in issues
            if any(
                h.action == "ISSUE_VERIFICATION_FAILED"
                for h in history_by_issue.get(i.issue_id, [])
            )
        )

        # ── Aging buckets ──
        age_buckets: dict[str, int] = {label: 0 for label, _, _ in AGE_BUCKETS}
        for issue in open_issues:
            age_days = (as_of - issue.created_at).total_seconds() / 86400
            for label, low, high in AGE_BUCKETS:
                if high is None:
                    if age_days >= low:
                        age_buckets[label] += 1
                        break
                elif low <= age_days <= high:
                    age_buckets[label] += 1
                    break

        # ── Oldest / most-recurring items ──
        items: list[dict[str, Any]] = []
        for issue in issues:
            ih = history_by_issue.get(issue.issue_id, [])
            first_resolved = next((h for h in ih if h.action == "ISSUE_RESOLVED"), None)
            first_investigation = next(
                (h for h in ih if h.action == "ISSUE_INVESTIGATION_STARTED"),
                None,
            )
            age_seconds = (as_of - issue.created_at).total_seconds()
            tta = (
                (first_investigation.occurred_at - issue.created_at).total_seconds()
                if first_investigation
                else None
            )
            ttr = (
                (first_resolved.occurred_at - issue.created_at).total_seconds()
                if first_resolved
                else None
            )
            recurrence_rels = sum(
                1
                for rel in relationships
                if (
                    rel.predecessor_issue_id == issue.issue_id
                    or rel.successor_issue_id == issue.issue_id
                )
                and rel.relationship_type == "RECURRENCE"
            )
            items.append(
                {
                    "issue_id": issue.issue_id,
                    "scope_type": issue.scope_type,
                    "scope_id": issue.scope_id,
                    "status": issue.status,
                    "priority": issue.priority,
                    "trigger_type": issue.trigger_type,
                    "age_seconds": age_seconds,
                    "time_to_ack_seconds": tta,
                    "time_to_resolve_seconds": ttr,
                    "recurrence_count": max(issue.occurrence_count - 1, 0) + recurrence_rels,
                    "reason_codes": [],
                }
            )
        # Sort: oldest open first, then most recurring
        items.sort(
            key=lambda i: (
                0 if i["status"] in OPEN_STATUSES else 1,
                -(i["age_seconds"]),
                -(i["recurrence_count"]),
            )
        )

        # ── Breakdowns ──
        status_breakdown: dict[str, int] = {}
        for i in issues:
            status_breakdown[i.status] = status_breakdown.get(i.status, 0) + 1
        priority_breakdown: dict[str, int] = {}
        for i in issues:
            priority_breakdown[i.priority] = priority_breakdown.get(i.priority, 0) + 1
        trigger_breakdown: dict[str, int] = {}
        for i in issues:
            trigger_breakdown[i.trigger_type] = trigger_breakdown.get(i.trigger_type, 0) + 1

        summary = {
            "open_issue_count": len(open_issues),
            "critical_open_count": len(critical_open),
            "mtta_p50": _percentile(mtta_values, 50),
            "mtta_p95": _percentile(mtta_values, 95),
            "mtta_sample_count": len(mtta_values),
            "mttr_p50": _percentile(mttr_values, 50),
            "mttr_p95": _percentile(mttr_values, 95),
            "mttr_sample_count": len(mttr_values),
            "unresolved_count": unresolved_count,
            "verification_success_rate": ratio_to_dict(verification_success),
            "recurring_issue_count": len(recurring_issues),
            "reopened_count": reopened_count,
            "aging_issue_count": len(open_issues),
            "missing_timeline_count": missing_timeline_count,
            "result_truncated": truncated,
            "result_row_limit": ANALYTICS_ROW_LIMIT,
        }
        breakdowns = {
            "by_status": status_breakdown,
            "by_priority": priority_breakdown,
            "by_trigger_type": trigger_breakdown,
            "by_age_bucket": age_buckets,
        }
        return AnalyticsEnvelope(
            summary=summary,
            breakdowns=breakdowns,
            items=items[:MAX_ITEMS],
        )

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


def _percentile(values: list[float], pct: int) -> float | None:
    """Sorted-list yuzdelik dilimi; orneklem yoksa None."""
    if not values:
        return None
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    if n == 1:
        return sorted_vals[0]
    k = (pct / 100) * (n - 1)
    f = int(k)
    c = f + 1 if f + 1 < n else f
    d = k - f
    return sorted_vals[f] + d * (sorted_vals[c] - sorted_vals[f])
