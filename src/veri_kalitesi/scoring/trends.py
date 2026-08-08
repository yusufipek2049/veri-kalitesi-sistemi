"""DQ-SCR-027 trend bilesenleri hesaplama modulu.

Son olcum, donem farki, hareketli ortalama, ardIsik kotuleSme,
ani kotuleSme, esik altinda kalma suresi ve iyileSme kaliciligi.
Tum parametreler surumlu politikadan gelir; politika yoklugunda
fail-closed Unknown doner.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence

from veri_kalitesi.scoring.models import QualityScore, ScoreScopeType


@dataclass(frozen=True)
class TrendPolicy:
    """DQ-SCR-027 trend hesaplama parametreleri (surumlu).

    Tum alanlar politika kaydindan gelir; ortuk varsayilan yoktur.
    """

    version: str
    moving_average_window: int
    consecutive_deterioration_count: int
    sudden_deterioration_threshold: Decimal
    below_threshold_value: Decimal
    time_below_threshold_periods: int
    improvement_persistence_periods: int
    minimum_observations: int

    def __post_init__(self) -> None:
        if not self.version.strip():
            raise ValueError("TrendPolicy version must not be blank.")
        if self.moving_average_window < 1:
            raise ValueError("moving_average_window must be >= 1.")
        if self.consecutive_deterioration_count < 1:
            raise ValueError("consecutive_deterioration_count must be >= 1.")
        if self.sudden_deterioration_threshold <= 0:
            raise ValueError("sudden_deterioration_threshold must be > 0.")
        if self.time_below_threshold_periods < 1:
            raise ValueError("time_below_threshold_periods must be >= 1.")
        if self.improvement_persistence_periods < 1:
            raise ValueError("improvement_persistence_periods must be >= 1.")
        if self.minimum_observations < 1:
            raise ValueError("minimum_observations must be >= 1.")

    @property
    def lookback_count(self) -> int:
        """Trend hesabi icin gereken maksimum gecmis gözlem sayisi."""
        return max(
            self.moving_average_window,
            self.consecutive_deterioration_count + 1,
            self.time_below_threshold_periods + 1,
            self.improvement_persistence_periods + 1,
            self.minimum_observations,
        )


@dataclass(frozen=True)
class TrendComponentResult:
    """Tek gözlem için DQ-SCR-027 trend bilesenleri.

    Her alan ya hesaplanmis değer ya da None (Unknown / yetersiz gecmis).
    """

    moving_average: Decimal | None
    consecutive_deterioration_count: int | None
    sudden_deterioration: bool | None
    time_below_threshold_periods: int | None
    improvement_persistence: int | None
    version_boundary: bool
    policy_version: str | None


_UNKNOWN_RESULT = TrendComponentResult(
    moving_average=None,
    consecutive_deterioration_count=None,
    sudden_deterioration=None,
    time_below_threshold_periods=None,
    improvement_persistence=None,
    version_boundary=False,
    policy_version=None,
)


def compute_trend_components(
    scores: Sequence[QualityScore],
    policy: TrendPolicy | None,
) -> dict[str, TrendComponentResult]:
    """DQ-SCR-027 trend bilesenlerini hesaplar.

    Girdi kapsam icinde kronolojik siralanir. Yalnizca resmî
    (``is_official_score``) ve ``score_value``'su olan gözlemler seriye
    alinir; provizyonel, ``TechnicalFailure`` ve ``NOT_COMPARABLE``
    gözlemler seriye sokulmaz (AC-03).

    Returns:
        ``quality_score_id`` → ``TrendComponentResult`` esleSmesi.
        Politika yoksa tüm bilesenler Unknown (AC-02).
    """

    if not scores or policy is None:
        return {s.quality_score_id: _unknown(policy) for s in scores}

    sorted_scores = sorted(scores, key=lambda s: (s.calculated_at, s.quality_score_id))

    official = [s for s in sorted_scores if _is_official_with_value(s)]

    groups: dict[tuple[ScoreScopeType, str | None], list[QualityScore]] = defaultdict(list)
    for score in official:
        groups[(score.scope_type, score.scope_id)].append(score)

    result_map: dict[str, TrendComponentResult] = {}

    for non_official in sorted_scores:
        if non_official not in official:
            result_map[non_official.quality_score_id] = _unknown(policy)

    for _scope_key, group in groups.items():
        _compute_group_trends(group, policy, result_map)

    for score in sorted_scores:
        if score.quality_score_id not in result_map:
            result_map[score.quality_score_id] = _unknown(policy)

    return result_map


def _compute_group_trends(
    group: list[QualityScore],
    policy: TrendPolicy,
    result_map: dict[str, TrendComponentResult],
) -> None:
    """Tek kapsam grubu için trend bilesenlerini hesaplar."""

    boundary_indices = _find_version_boundaries(group)

    for idx, score in enumerate(group):
        is_boundary = idx in boundary_indices

        comparable_start = _find_comparable_segment_start(idx, boundary_indices)
        segment = group[comparable_start : idx + 1]

        if len(segment) < policy.minimum_observations:
            result_map[score.quality_score_id] = TrendComponentResult(
                moving_average=None,
                consecutive_deterioration_count=None,
                sudden_deterioration=None,
                time_below_threshold_periods=None,
                improvement_persistence=None,
                version_boundary=is_boundary,
                policy_version=policy.version,
            )
            continue

        result_map[score.quality_score_id] = TrendComponentResult(
            moving_average=_moving_average(segment, policy),
            consecutive_deterioration_count=_consec_deterioration(segment, policy),
            sudden_deterioration=_sudden_deterioration(score, segment, policy),
            time_below_threshold_periods=_time_below(segment, policy),
            improvement_persistence=_improvement_persistence(segment, policy),
            version_boundary=is_boundary,
            policy_version=policy.version,
        )


def _find_version_boundaries(group: list[QualityScore]) -> set[int]:
    """ArdIsik resmi skor ciftleri arasında sürüm sinirlarini belirler."""

    boundaries: set[int] = set()
    for i in range(1, len(group)):
        if _versions_changed(group[i - 1], group[i]):
            boundaries.add(i)
    return boundaries


def _find_comparable_segment_start(
    idx: int,
    boundary_indices: set[int],
) -> int:
    """Geriye dogru en yakin sürüm sinirindan sonraki konumu döndürür.

    boundary_indices'deki j degeri, group[j] ile group[j-1] arasinda
    sürüm degisikligi oldugunu gösterir. group[j] yeni sürümün ilk elemanidir
    ve karsilastirilabilir segmente dahildir.
    """

    for j in range(idx, 0, -1):
        if j in boundary_indices:
            return j
    return 0


def _versions_changed(current: QualityScore, previous: QualityScore) -> bool:
    """Iki skor arasindaki sürüm alanlari farkli mi?"""

    current_v = _extract_versions(current)
    previous_v = _extract_versions(previous)
    for key in _VERSION_KEYS:
        if current_v.get(key) and previous_v.get(key) and current_v[key] != previous_v[key]:
            return True
    return False


_VERSION_KEYS = (
    "formula_version",
    "configuration_version",
    "threshold_version",
    "qualification_policy_version",
    "profile_version",
    "governance_version",
)


def _extract_versions(score: QualityScore) -> dict[str, str | None]:
    """Skorun hesaplama detayindan sürüm alanlarini çikarir."""

    details = score.calculation_details
    return {
        "formula_version": _str_or_none(details.get("formula_version")),
        "configuration_version": _str_or_none(details.get("configuration_version")),
        "threshold_version": _str_or_none(details.get("threshold_version")),
        "qualification_policy_version": _str_or_none(
            details.get("qualification_policy_version")
            or details.get("partial_score_policy_version")
        ),
        "profile_version": _str_or_none(details.get("profile_version")),
        "governance_version": _str_or_none(details.get("governance_version")),
    }


def _moving_average(
    segment: list[QualityScore],
    policy: TrendPolicy,
) -> Decimal | None:
    """Son ``moving_average_window`` gözlemin ortalamasi."""

    window = policy.moving_average_window
    if len(segment) < window:
        return None
    values = [s.score_value for s in segment[-window:] if s.score_value is not None]
    if len(values) < window:
        return None
    return sum(values) / len(values)


def _consec_deterioration(
    segment: list[QualityScore],
    policy: TrendPolicy,
) -> int | None:
    """Son gözlemden geriye dogru ardIsik düSüS sayisi."""

    if len(segment) < 2:
        return 0
    count = 0
    for i in range(len(segment) - 1, 0, -1):
        current_val = segment[i].score_value
        prev_val = segment[i - 1].score_value
        if current_val is not None and prev_val is not None and current_val < prev_val:
            count += 1
        else:
            break
    return count


def _sudden_deterioration(
    score: QualityScore,
    segment: list[QualityScore],
    policy: TrendPolicy,
) -> bool | None:
    """Son gözlemin öncekine göre ani düSüs gösterip göstermedigini belirler."""

    if len(segment) < 2:
        return False
    current_val = score.score_value
    prev_val = segment[-2].score_value
    if current_val is None or prev_val is None:
        return None
    drop = prev_val - current_val
    return drop >= policy.sudden_deterioration_threshold


def _time_below(
    segment: list[QualityScore],
    policy: TrendPolicy,
) -> int | None:
    """Son gözlemin esik altinda kaç ardIsik dönemdir kaldigini sayar."""

    if len(segment) < 2:
        return 0
    count = 0
    for i in range(len(segment) - 1, -1, -1):
        val = segment[i].score_value
        if val is not None and val < policy.below_threshold_value:
            count += 1
        else:
            break
    return count


def _improvement_persistence(
    segment: list[QualityScore],
    policy: TrendPolicy,
) -> int | None:
    """Son gözlemden geriye dogru ardIsik iyileSme sayisi."""

    if len(segment) < 2:
        return 0
    count = 0
    for i in range(len(segment) - 1, 0, -1):
        current_val = segment[i].score_value
        prev_val = segment[i - 1].score_value
        if current_val is not None and prev_val is not None and current_val > prev_val:
            count += 1
        else:
            break
    return count


def _is_official_with_value(score: QualityScore) -> bool:
    """Resmî skor ve score_value'si var mi?"""

    from veri_kalitesi.scoring.models import is_official_score

    return is_official_score(score) and score.score_value is not None


def _unknown(policy: TrendPolicy | None) -> TrendComponentResult:
    """Politika yokluğunda fail-closed Unknown döner (AC-02)."""

    return TrendComponentResult(
        moving_average=None,
        consecutive_deterioration_count=None,
        sudden_deterioration=None,
        time_below_threshold_periods=None,
        improvement_persistence=None,
        version_boundary=False,
        policy_version=policy.version if policy else None,
    )


def _str_or_none(value: object) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else None
    return None
