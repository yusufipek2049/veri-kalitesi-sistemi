"""Yetki filtreli ve veri-minimum rapor onizleme modelleri."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum

from veri_kalitesi.scoring.models import ScoreLevel, ScoreStatus


class ReportType(str, Enum):
    SUMMARY = "SUMMARY"


@dataclass(frozen=True)
class ReportPreviewAccessPolicy:
    version: str
    actor_policy_version: str
    allowed_roles: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {"DATA_OWNER", "DATA_STEWARD", "DATA_GOVERNANCE_SPECIALIST", "AUDITOR"}
        )
    )
    max_window_days: int = 31
    max_source_count: int = 500


@dataclass(frozen=True)
class ReportPreviewRequest:
    start_at: datetime
    end_at: datetime
    reason_code: str
    requested_source_ids: frozenset[str] | None = None
    report_type: ReportType = ReportType.SUMMARY


@dataclass(frozen=True)
class ReportScoreObservation:
    source_id: str
    score_value: Decimal | None
    score_status: ScoreStatus
    level: ScoreLevel | None
    calculated_at: datetime


@dataclass(frozen=True)
class ReportSummaryRow:
    source_id: str
    score_value: Decimal | None
    score_status: ScoreStatus
    level: ScoreLevel | None
    calculated_at: datetime


@dataclass(frozen=True)
class ReportPreviewFilter:
    start_at: datetime
    end_at: datetime
    source_ids: tuple[str, ...]


@dataclass(frozen=True)
class ReportPreview:
    report_type: ReportType
    created_at: datetime
    filters: ReportPreviewFilter
    rows: tuple[ReportSummaryRow, ...]
    source_count: int
    calculated_source_count: int
    average_score: Decimal | None
    policy_version: str
    masking_mode: str = "AGGREGATED_ONLY"
