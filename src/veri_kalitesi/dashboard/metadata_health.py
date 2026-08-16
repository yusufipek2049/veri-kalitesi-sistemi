"""Dashboard 5 — Metadata ve Siniflandirma sorgu servisi."""

from __future__ import annotations

from datetime import timedelta
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

SENSITIVE_CLASSES = frozenset(
    {
        "PERSONAL_DATA",
        "SPECIAL_CATEGORY_PERSONAL_DATA",
        "CUSTOMER_SECRET",
        "BANK_SECRET",
        "HIGHLY_RESTRICTED",
    }
)
NON_SENSITIVE_WITH_FLAG = frozenset({"PUBLIC", "UNCLASSIFIED"})
MAX_ITEMS = 100

# ── Protocol ──


class MetadataHealthReader(Protocol):
    def list_active_datasets(
        self,
        *,
        permitted_source_ids: frozenset[str],
        permitted_dataset_ids: frozenset[str],
        source_id: str | None = None,
    ) -> list[Any]: ...

    def list_active_fields(self, *, dataset_ids: frozenset[str]) -> list[Any]: ...


# ── Service ──


class MetadataHealthQueryService:
    """Metadata tamligi ve siniflandirma metriklerini hesaplar."""

    def __init__(
        self,
        reader: MetadataHealthReader,
        authorization_service: AuthorizationService,
        *,
        stale_after_days: int = 30,
        classification_policy_version: str = "CLASSIFICATION_POLICY_V1",
    ) -> None:
        self._reader = reader
        self._auth = authorization_service
        self._stale_after_days = stale_after_days
        self._policy_version = classification_policy_version

    def get_metadata_health(
        self,
        actor_context: ActorContext | None,
        params: AnalyticsFilterParams,
        *,
        classification: str | None = None,
        criticality: str | None = None,
        ownership_status: str | None = None,
    ) -> AnalyticsEnvelope:
        access_scope, correlation_id = self._authorize(actor_context)
        self._validate_window(params)
        as_of = params.end_at

        datasets = self._reader.list_active_datasets(
            permitted_source_ids=access_scope.allowed_source_ids,
            permitted_dataset_ids=access_scope.allowed_dataset_ids,
            source_id=params.source_id,
        )
        dataset_ids = frozenset(d.dataset_id for d in datasets)
        fields = self._reader.list_active_fields(dataset_ids=dataset_ids)

        # Optional filters
        if criticality:
            datasets = [d for d in datasets if d.criticality == criticality]

        # ── Ownership completeness ──
        owned = sum(1 for d in datasets if d.owner_user_id and d.owner_user_id.strip())
        ownership = MetricRatio(
            numerator=owned,
            denominator=len(datasets),
            reason_code="NO_ELIGIBLE_ITEMS" if not datasets else None,
        )

        # ── Classification completeness ──
        classified_fields = [f for f in fields if f.classification != "UNCLASSIFIED"]
        classification_completeness = MetricRatio(
            numerator=len(classified_fields),
            denominator=len(fields),
            reason_code="NO_ELIGIBLE_ITEMS" if not fields else None,
        )

        # ── Sensitive marking completeness ──
        sensitive_candidates = [
            f
            for f in fields
            if f.classification in SENSITIVE_CLASSES or f.is_sensitive
        ]
        consistent_sensitive = sum(
            1
            for f in sensitive_candidates
            if (f.classification in SENSITIVE_CLASSES and f.is_sensitive)
            or (f.classification not in SENSITIVE_CLASSES and not f.is_sensitive)
        )
        sensitive_marking = MetricRatio(
            numerator=consistent_sensitive,
            denominator=len(sensitive_candidates),
            reason_code="NO_ELIGIBLE_ITEMS" if not sensitive_candidates else None,
        )

        # ── Policy currency ──
        current_policy = [
            f for f in fields if f.classification_policy_version == self._policy_version
        ]
        policy_currency = MetricRatio(
            numerator=len(current_policy),
            denominator=len(fields),
            reason_code="NO_ELIGIBLE_ITEMS" if not fields else None,
        )

        # ── Stale metadata ──
        stale_cutoff = as_of - timedelta(days=self._stale_after_days)
        stale_datasets = [d for d in datasets if d.updated_at < stale_cutoff]
        stale_fields = [f for f in fields if f.updated_at < stale_cutoff]

        # ── Critical gaps ──
        high_crit_datasets = [
            d for d in datasets if d.criticality in ("HIGH", "CRITICAL")
        ]
        critical_gap_items: list[dict[str, Any]] = []
        critical_gap_count = 0
        for d in high_crit_datasets:
            gaps: list[str] = []
            if not d.owner_user_id or not d.owner_user_id.strip():
                gaps.append("MISSING_DATASET_OWNER")
            if d.updated_at < stale_cutoff:
                gaps.append("STALE_DATASET_METADATA")
            if gaps:
                critical_gap_count += 1
                for reason in gaps:
                    critical_gap_items.append(
                        {
                            "object_type": "dataset",
                            "object_id": d.dataset_id,
                            "display_name": d.name,
                            "data_source_id": d.data_source_id,
                            "criticality": d.criticality,
                            "reason_code": reason,
                        }
                    )

        # Field-level gaps
        dataset_crit_map = {d.dataset_id: d.criticality for d in datasets}
        dataset_name_map = {d.dataset_id: d.name for d in datasets}
        for f in fields:
            ds_crit = dataset_crit_map.get(f.dataset_id)
            if ds_crit not in ("HIGH", "CRITICAL"):
                continue
            gaps: list[str] = []
            if f.classification == "UNCLASSIFIED":
                gaps.append("UNCLASSIFIED_FIELD")
            if f.classification in NON_SENSITIVE_WITH_FLAG and f.is_sensitive:
                gaps.append("CLASSIFICATION_FLAG_MISMATCH")
            if f.classification_policy_version != self._policy_version:
                gaps.append("CLASSIFICATION_POLICY_OUTDATED")
            if f.updated_at < stale_cutoff:
                gaps.append("STALE_FIELD_METADATA")
            for reason in gaps:
                critical_gap_items.append(
                    {
                        "object_type": "field",
                        "object_id": f.data_field_id,
                        "display_name": f.name,
                        "dataset_id": f.dataset_id,
                        "dataset_name": dataset_name_map.get(f.dataset_id),
                        "criticality": ds_crit,
                        "classification": f.classification,
                        "is_sensitive": f.is_sensitive,
                        "reason_code": reason,
                    }
                )

        # Add dataset-level unclassified/missing owner to gaps
        for d in datasets:
            if d.criticality not in ("HIGH", "CRITICAL"):
                continue
            if not d.owner_user_id or not d.owner_user_id.strip():
                pass  # already counted above
            ds_fields = [f for f in fields if f.dataset_id == d.dataset_id]
            for f in ds_fields:
                pass  # already handled above

        # ── Breakdowns ──
        class_breakdown: dict[str, int] = {}
        for f in fields:
            class_breakdown[f.classification] = (
                class_breakdown.get(f.classification, 0) + 1
            )
        crit_ds_breakdown: dict[str, int] = {}
        for d in datasets:
            crit_ds_breakdown[d.criticality] = (
                crit_ds_breakdown.get(d.criticality, 0) + 1
            )
        reason_breakdown: dict[str, int] = {}
        for item in critical_gap_items:
            rc = item["reason_code"]
            reason_breakdown[rc] = reason_breakdown.get(rc, 0) + 1

        summary = {
            "ownership_completeness": ratio_to_dict(ownership),
            "classification_completeness": ratio_to_dict(classification_completeness),
            "sensitive_marking_completeness": ratio_to_dict(sensitive_marking),
            "policy_currency": ratio_to_dict(policy_currency),
            "stale_dataset_count": len(stale_datasets),
            "stale_field_count": len(stale_fields),
            "critical_gap_count": critical_gap_count,
            "stale_after_days": self._stale_after_days,
        }
        breakdowns = {
            "by_classification": class_breakdown,
            "by_criticality": crit_ds_breakdown,
            "by_reason_code": reason_breakdown,
        }
        return AnalyticsEnvelope(
            summary=summary,
            breakdowns=breakdowns,
            items=critical_gap_items[:MAX_ITEMS],
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
