"""Yetki filtreli ve veri-minimum rapor onizleme ve guvenli rapor modelleri."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum

from veri_kalitesi.scoring.models import ScoreLevel, ScoreStatus


class ReportType(str, Enum):
    SUMMARY = "SUMMARY"
    DETAIL = "DETAIL"
    TREND = "TREND"
    UNIT = "UNIT"
    OWNER = "OWNER"
    CRITICAL_DATA = "CRITICAL_DATA"
    ISSUE_PERFORMANCE = "ISSUE_PERFORMANCE"


class ReportStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    READY = "READY"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


class ReportFormat(str, Enum):
    PDF = "PDF"
    XLSX = "XLSX"
    CSV = "CSV"


@dataclass(frozen=True)
class Report:
    report_id: str
    report_type: ReportType
    format: ReportFormat
    requested_by: str
    parameters: dict
    status: ReportStatus
    sensitivity_level: str | None = None
    retention_policy_id: str | None = None
    online_file_reference: str | None = None
    file_size: int | None = None
    expires_at: datetime | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None
    failure_reason: str | None = None
    version: int = 1


@dataclass(frozen=True)
class ReportRequest:
    report_type: ReportType
    format: ReportFormat
    parameters: dict
    reason_code: str
    sensitivity_level: str | None = None


@dataclass(frozen=True)
class ReportExportPolicy:
    version: str
    policy_name: str
    sensitivity_level: str | None
    max_file_size: int
    online_duration_seconds: int
    require_justification: bool
    require_maker_checker: bool
    watermark_enabled: bool
    dlp_enabled: bool
    allowed_formats: frozenset[ReportFormat]


@dataclass(frozen=True)
class ExportDecision:
    allowed: bool
    reason_code: str
    require_maker_checker: bool
    policy_version: str


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
