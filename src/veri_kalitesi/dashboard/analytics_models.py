"""Analytics dashboard'larinin ortak salt-okunur modelleri."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class MetricRatio:
    """Pay/payda ve oran ucusu; payda sifirsa ratio=None, reason_code doner."""

    numerator: int
    denominator: int
    ratio: Decimal | None = None
    reason_code: str | None = None

    def __post_init__(self) -> None:
        if self.denominator == 0 and self.ratio is not None:
            object.__setattr__(self, "ratio", None)
        if self.denominator != 0 and self.ratio is None:
            object.__setattr__(
                self,
                "ratio",
                Decimal(self.numerator) / Decimal(self.denominator),
            )


@dataclass(frozen=True)
class AnalyticsFilterParams:
    """Ortak analytics filtre parametreleri — UTC, tam gun kapsar."""

    start_at: datetime
    end_at: datetime
    source_id: str | None = None
    dataset_id: str | None = None

    @property
    def window_days(self) -> int:
        return (self.end_at - self.start_at).days


@dataclass(frozen=True)
class AnalyticsEnvelope:
    """Standart analytics yanit zarfi."""

    summary: dict[str, Any]
    breakdowns: dict[str, Any] = field(default_factory=dict)
    items: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(
        self,
        *,
        api_version: str,
        data_origin: str,
        correlation_id: str,
        as_of: datetime,
        applied_filters: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "api_version": api_version,
            "data_origin": data_origin,
            "correlation_id": correlation_id,
            "as_of": as_of.isoformat(),
            "applied_filters": applied_filters,
            "summary": self.summary,
            "breakdowns": self.breakdowns,
            "items": self.items,
        }


def ratio_to_dict(ratio: MetricRatio) -> dict[str, Any]:
    """MetricRatio'yu JSON-uyumlu sozluqe donusturur."""
    return {
        "numerator": ratio.numerator,
        "denominator": ratio.denominator,
        "ratio": float(ratio.ratio) if ratio.ratio is not None else None,
        "reason_code": ratio.reason_code,
    }


def _decimal_or_none(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value)
