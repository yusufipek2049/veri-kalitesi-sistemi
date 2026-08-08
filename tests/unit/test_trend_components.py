"""DQ-SCR-027 trend bilesenleri birim testleri.

AC-01: Her bilesen dogru hesaplanir
AC-02: Politika yoklugunda fail-closed Unknown
AC-03: Yalnizca resmî skorlar katilir
AC-04: Sürüm siniri isaretlenir
AC-05: Yetersiz gecmis Unknown
AC-06: Determinizm ve politika sürümü tasimasi
AC-07: Gecmis skor degisikligi yok
AC-08: Her senaryo için test
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pytest

from veri_kalitesi.scoring.models import (
    QualityScore,
    ScoreLevel,
    ScoreScopeType,
    ScoreStatus,
)
from veri_kalitesi.scoring.trends import (
    TrendPolicy,
    compute_trend_components,
)

_POLICY = TrendPolicy(
    version="TEST_TREND_V1",
    moving_average_window=3,
    consecutive_deterioration_count=3,
    sudden_deterioration_threshold=Decimal("10"),
    below_threshold_value=Decimal("50"),
    time_below_threshold_periods=3,
    improvement_persistence_periods=3,
    minimum_observations=2,
)

_VERSION_FIELDS = {
    "formula_version": "RULE_SCORE_V2",
    "configuration_version": "CFG_V1",
    "threshold_version": "THR_V1",
    "qualification_policy_version": "QP_V1",
    "profile_version": "PROF_V1",
    "governance_version": "GOV_V1",
}


def _score(
    *,
    score_value: Decimal | None,
    calculated_at: datetime,
    scope_id: str = "source-a",
    score_status: ScoreStatus = ScoreStatus.CALCULATED,
    official: bool = True,
    versions: dict[str, str] | None = None,
) -> QualityScore:
    details: dict[str, Any] = {
        "included_in_official_aggregation": official,
        **_VERSION_FIELDS,
    }
    if versions:
        details.update(versions)
    return QualityScore(
        execution_id="exec-1",
        rule_version_id="rv-1",
        scope_id=scope_id,
        score_status=score_status,
        calculation_details=details,
        score_value=score_value,
        level=ScoreLevel.GOOD
        if score_value is not None and score_value >= 75
        else ScoreLevel.ACCEPTABLE,
        scope_type=ScoreScopeType.SOURCE,
        calculated_at=calculated_at,
    )


def _at(day: int) -> datetime:
    return datetime(2026, 7, day, 12, 0, tzinfo=timezone.utc)


# --- AC-01: Hareketli ortalama ---


class TestMovingAverage:
    def test_basic_moving_average(self) -> None:
        scores = [
            _score(score_value=Decimal("80"), calculated_at=_at(1)),
            _score(score_value=Decimal("85"), calculated_at=_at(2)),
            _score(score_value=Decimal("90"), calculated_at=_at(3)),
        ]
        result = compute_trend_components(scores, _POLICY)
        # window=3, son 3 skor: (80+85+90)/3 = 85
        assert result[scores[2].quality_score_id].moving_average == Decimal("85")

    def test_moving_average_partial_window(self) -> None:
        scores = [
            _score(score_value=Decimal("80"), calculated_at=_at(1)),
            _score(score_value=Decimal("90"), calculated_at=_at(2)),
            _score(score_value=Decimal("70"), calculated_at=_at(3)),
            _score(score_value=Decimal("60"), calculated_at=_at(4)),
        ]
        result = compute_trend_components(scores, _POLICY)
        # window=3, son 3: (90+70+60)/3 = ~73.33
        last = result[scores[3].quality_score_id]
        assert last.moving_average is not None
        assert abs(last.moving_average - Decimal("73.33")) < Decimal("0.1")

    def test_moving_average_insufficient_for_window(self) -> None:
        scores = [
            _score(score_value=Decimal("80"), calculated_at=_at(1)),
            _score(score_value=Decimal("90"), calculated_at=_at(2)),
        ]
        result = compute_trend_components(scores, _POLICY)
        # minimum_observations=2 karsilanir ama window=3 icin yeterli degil
        last = result[scores[1].quality_score_id]
        assert last.moving_average is None


# --- AC-01: ArdIsik kotuleSme ---


class TestConsecutiveDeterioration:
    def test_consecutive_drops(self) -> None:
        scores = [
            _score(score_value=Decimal("90"), calculated_at=_at(1)),
            _score(score_value=Decimal("85"), calculated_at=_at(2)),
            _score(score_value=Decimal("80"), calculated_at=_at(3)),
            _score(score_value=Decimal("75"), calculated_at=_at(4)),
        ]
        result = compute_trend_components(scores, _POLICY)
        # Son 3 adimda sürekli düsüs: 3
        assert result[scores[3].quality_score_id].consecutive_deterioration_count == 3

    def test_consecutive_drops_broken(self) -> None:
        scores = [
            _score(score_value=Decimal("90"), calculated_at=_at(1)),
            _score(score_value=Decimal("85"), calculated_at=_at(2)),
            _score(score_value=Decimal("88"), calculated_at=_at(3)),  # iyileşme
            _score(score_value=Decimal("82"), calculated_at=_at(4)),
        ]
        result = compute_trend_components(scores, _POLICY)
        # Son adimda düsüs var ama önceki adimda iyileşme: count=1
        assert result[scores[3].quality_score_id].consecutive_deterioration_count == 1

    def test_no_deterioration(self) -> None:
        scores = [
            _score(score_value=Decimal("80"), calculated_at=_at(1)),
            _score(score_value=Decimal("85"), calculated_at=_at(2)),
            _score(score_value=Decimal("90"), calculated_at=_at(3)),
        ]
        result = compute_trend_components(scores, _POLICY)
        assert result[scores[2].quality_score_id].consecutive_deterioration_count == 0


# --- AC-01: Ani kotuleSme ---


class TestSuddenDeterioration:
    def test_sudden_drop(self) -> None:
        scores = [
            _score(score_value=Decimal("90"), calculated_at=_at(1)),
            _score(score_value=Decimal("75"), calculated_at=_at(2)),  # 15 puan düsüs
        ]
        result = compute_trend_components(scores, _POLICY)
        # threshold=10, drop=15 >= 10 → True
        assert result[scores[1].quality_score_id].sudden_deterioration is True

    def test_gradual_drop_not_sudden(self) -> None:
        scores = [
            _score(score_value=Decimal("90"), calculated_at=_at(1)),
            _score(score_value=Decimal("85"), calculated_at=_at(2)),  # 5 puan düsüs
        ]
        result = compute_trend_components(scores, _POLICY)
        # threshold=10, drop=5 < 10 → False
        assert result[scores[1].quality_score_id].sudden_deterioration is False

    def test_improvement_not_sudden(self) -> None:
        scores = [
            _score(score_value=Decimal("70"), calculated_at=_at(1)),
            _score(score_value=Decimal("85"), calculated_at=_at(2)),
        ]
        result = compute_trend_components(scores, _POLICY)
        assert result[scores[1].quality_score_id].sudden_deterioration is False


# --- AC-01: Esik altinda kalma suresi ---


class TestTimeBelowThreshold:
    def test_below_threshold_consecutive(self) -> None:
        scores = [
            _score(score_value=Decimal("60"), calculated_at=_at(1)),
            _score(score_value=Decimal("45"), calculated_at=_at(2)),  # < 50
            _score(score_value=Decimal("40"), calculated_at=_at(3)),  # < 50
            _score(score_value=Decimal("30"), calculated_at=_at(4)),  # < 50
        ]
        result = compute_trend_components(scores, _POLICY)
        # Son 3 skor esik altinda
        assert result[scores[3].quality_score_id].time_below_threshold_periods == 3

    def test_below_threshold_broken(self) -> None:
        scores = [
            _score(score_value=Decimal("60"), calculated_at=_at(1)),
            _score(score_value=Decimal("45"), calculated_at=_at(2)),  # < 50
            _score(score_value=Decimal("55"), calculated_at=_at(3)),  # >= 50
            _score(score_value=Decimal("48"), calculated_at=_at(4)),  # < 50
        ]
        result = compute_trend_components(scores, _POLICY)
        # Son skor esik altinda ama önceki üstünde: count=1
        assert result[scores[3].quality_score_id].time_below_threshold_periods == 1

    def test_not_below_threshold(self) -> None:
        scores = [
            _score(score_value=Decimal("60"), calculated_at=_at(1)),
            _score(score_value=Decimal("70"), calculated_at=_at(2)),
        ]
        result = compute_trend_components(scores, _POLICY)
        assert result[scores[1].quality_score_id].time_below_threshold_periods == 0


# --- AC-01: Iyileşme kaliciligi ---


class TestImprovementPersistence:
    def test_consecutive_improvements(self) -> None:
        scores = [
            _score(score_value=Decimal("70"), calculated_at=_at(1)),
            _score(score_value=Decimal("75"), calculated_at=_at(2)),
            _score(score_value=Decimal("80"), calculated_at=_at(3)),
            _score(score_value=Decimal("85"), calculated_at=_at(4)),
        ]
        result = compute_trend_components(scores, _POLICY)
        # Son 3 adimda sürekli iyileşme: 3
        assert result[scores[3].quality_score_id].improvement_persistence == 3

    def test_improvement_broken(self) -> None:
        scores = [
            _score(score_value=Decimal("70"), calculated_at=_at(1)),
            _score(score_value=Decimal("75"), calculated_at=_at(2)),
            _score(score_value=Decimal("72"), calculated_at=_at(3)),  # düsüs
            _score(score_value=Decimal("80"), calculated_at=_at(4)),
        ]
        result = compute_trend_components(scores, _POLICY)
        # Son adimda iyileşme ama önceki adimda düsüs: count=1
        assert result[scores[3].quality_score_id].improvement_persistence == 1


# --- AC-02: Politika yoklugunda fail-closed ---


class TestNoPolicy:
    def test_no_policy_returns_unknown(self) -> None:
        scores = [
            _score(score_value=Decimal("80"), calculated_at=_at(1)),
            _score(score_value=Decimal("90"), calculated_at=_at(2)),
        ]
        result = compute_trend_components(scores, None)
        for score_id, component in result.items():
            assert component.moving_average is None
            assert component.consecutive_deterioration_count is None
            assert component.sudden_deterioration is None
            assert component.time_below_threshold_periods is None
            assert component.improvement_persistence is None
            assert component.policy_version is None

    def test_empty_scores_no_policy(self) -> None:
        result = compute_trend_components([], None)
        assert result == {}


# --- AC-03: Yalnizca resmî skorlar ---


class TestOfficialOnly:
    def test_non_official_excluded(self) -> None:
        scores = [
            _score(score_value=Decimal("90"), calculated_at=_at(1)),
            _score(
                score_value=Decimal("50"),
                calculated_at=_at(2),
                official=False,  # provizyonel
            ),
            _score(score_value=Decimal("85"), calculated_at=_at(3)),
        ]
        result = compute_trend_components(scores, _POLICY)
        # Resmi olmayan skor Unknown alir
        non_official_result = result[scores[1].quality_score_id]
        assert non_official_result.moving_average is None
        assert non_official_result.policy_version == _POLICY.version

    def test_technical_failure_excluded(self) -> None:
        scores = [
            _score(score_value=Decimal("90"), calculated_at=_at(1)),
            _score(
                score_value=None,
                calculated_at=_at(2),
                score_status=ScoreStatus.NOT_CALCULATED_TECHNICAL_ERROR,
                official=False,
            ),
            _score(score_value=Decimal("85"), calculated_at=_at(3)),
        ]
        result = compute_trend_components(scores, _POLICY)
        tech_failure = result[scores[1].quality_score_id]
        assert tech_failure.moving_average is None


# --- AC-04: Sürüm siniri ---


class TestVersionBoundary:
    def test_version_change_marks_boundary(self) -> None:
        scores = [
            _score(score_value=Decimal("90"), calculated_at=_at(1)),
            _score(
                score_value=Decimal("85"),
                calculated_at=_at(2),
                versions={"configuration_version": "CFG_V2"},
            ),
            _score(
                score_value=Decimal("80"),
                calculated_at=_at(3),
                versions={"configuration_version": "CFG_V2"},
            ),
        ]
        result = compute_trend_components(scores, _POLICY)
        # İkinci skor sürüm siniri
        assert result[scores[1].quality_score_id].version_boundary is True
        assert result[scores[0].quality_score_id].version_boundary is False

    def test_version_boundary_breaks_comparable_segment(self) -> None:
        scores = [
            _score(score_value=Decimal("90"), calculated_at=_at(1)),
            _score(
                score_value=Decimal("85"),
                calculated_at=_at(2),
                versions={"configuration_version": "CFG_V2"},
            ),
            _score(
                score_value=Decimal("80"),
                calculated_at=_at(3),
                versions={"configuration_version": "CFG_V2"},
            ),
            _score(
                score_value=Decimal("75"),
                calculated_at=_at(4),
                versions={"configuration_version": "CFG_V2"},
            ),
        ]
        result = compute_trend_components(scores, _POLICY)
        # Son skor için comparable segment: [CFG_V2] skorları (idx 1-3)
        # MA window=3, segment'te 3 skor var: (85+80+75)/3 = 80
        last = result[scores[3].quality_score_id]
        assert last.moving_average == Decimal("80")


# --- AC-05: Yetersiz gecmis ---


class TestInsufficientHistory:
    def test_single_score_unknown(self) -> None:
        scores = [
            _score(score_value=Decimal("80"), calculated_at=_at(1)),
        ]
        result = compute_trend_components(scores, _POLICY)
        # minimum_observations=2, tek skor yetersiz
        component = result[scores[0].quality_score_id]
        assert component.moving_average is None
        assert component.consecutive_deterioration_count is None
        assert component.sudden_deterioration is None

    def test_empty_scores(self) -> None:
        result = compute_trend_components([], _POLICY)
        assert result == {}


# --- AC-06: Determinizm ve politika sürümü ---


class TestDeterminism:
    def test_same_input_same_output(self) -> None:
        scores = [
            _score(score_value=Decimal("80"), calculated_at=_at(1)),
            _score(score_value=Decimal("85"), calculated_at=_at(2)),
            _score(score_value=Decimal("90"), calculated_at=_at(3)),
        ]
        result1 = compute_trend_components(scores, _POLICY)
        result2 = compute_trend_components(scores, _POLICY)
        for score_id in result1:
            assert result1[score_id] == result2[score_id]

    def test_policy_version_carried(self) -> None:
        scores = [
            _score(score_value=Decimal("80"), calculated_at=_at(1)),
            _score(score_value=Decimal("90"), calculated_at=_at(2)),
        ]
        result = compute_trend_components(scores, _POLICY)
        for component in result.values():
            assert component.policy_version == "TEST_TREND_V1"


# --- AC-07: Gecmis skor degisikligi yok ---


class TestNoScoreModification:
    def test_scores_not_modified(self) -> None:
        scores = [
            _score(score_value=Decimal("80"), calculated_at=_at(1)),
            _score(score_value=Decimal("70"), calculated_at=_at(2)),
            _score(score_value=Decimal("60"), calculated_at=_at(3)),
        ]
        original_values = [(s.quality_score_id, s.score_value) for s in scores]
        compute_trend_components(scores, _POLICY)
        for score, (qid, value) in zip(scores, original_values):
            assert score.quality_score_id == qid
            assert score.score_value == value


# --- TrendPolicy dogrulama ---


class TestTrendPolicyValidation:
    def test_blank_version_rejected(self) -> None:
        with pytest.raises(ValueError, match="version"):
            TrendPolicy(
                version="  ",
                moving_average_window=3,
                consecutive_deterioration_count=3,
                sudden_deterioration_threshold=Decimal("10"),
                below_threshold_value=Decimal("50"),
                time_below_threshold_periods=3,
                improvement_persistence_periods=3,
                minimum_observations=2,
            )

    def test_zero_window_rejected(self) -> None:
        with pytest.raises(ValueError, match="moving_average_window"):
            TrendPolicy(
                version="V1",
                moving_average_window=0,
                consecutive_deterioration_count=3,
                sudden_deterioration_threshold=Decimal("10"),
                below_threshold_value=Decimal("50"),
                time_below_threshold_periods=3,
                improvement_persistence_periods=3,
                minimum_observations=2,
            )

    def test_negative_threshold_rejected(self) -> None:
        with pytest.raises(ValueError, match="sudden_deterioration_threshold"):
            TrendPolicy(
                version="V1",
                moving_average_window=3,
                consecutive_deterioration_count=3,
                sudden_deterioration_threshold=Decimal("-5"),
                below_threshold_value=Decimal("50"),
                time_below_threshold_periods=3,
                improvement_persistence_periods=3,
                minimum_observations=2,
            )

    def test_lookback_count(self) -> None:
        assert _POLICY.lookback_count == 4  # max(3, 3+1, 3+1, 3+1, 2)


# --- Farkli kapsam gruplari ---


class TestMultipleScopes:
    def test_separate_scope_computation(self) -> None:
        scores = [
            _score(score_value=Decimal("90"), calculated_at=_at(1), scope_id="source-a"),
            _score(score_value=Decimal("80"), calculated_at=_at(1), scope_id="source-b"),
            _score(score_value=Decimal("85"), calculated_at=_at(2), scope_id="source-a"),
            _score(score_value=Decimal("75"), calculated_at=_at(2), scope_id="source-b"),
        ]
        result = compute_trend_components(scores, _POLICY)
        # Her kapsam kendi grubunda hesaplanir
        a_result = result[scores[2].quality_score_id]
        b_result = result[scores[3].quality_score_id]
        # source-a: (90+85)/2 = 87.5 (window=3 ama sadece 2 skor var)
        # moving_average None cünkü window=3 > len(segment)=2
        assert a_result.moving_average is None
        # source-b: (80+75)/2 = 77.5
        assert b_result.moving_average is None
        # Ama minimum_observations=2 karsilanir
        assert a_result.consecutive_deterioration_count is not None
        assert b_result.consecutive_deterioration_count is not None
