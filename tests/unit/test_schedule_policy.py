"""Tablo zamanlılık niteliği bazlı job aralığı öneri ve bant testleri."""

from __future__ import annotations

import pytest

from veri_kalitesi.data_sources.models import TimelinessNature
from veri_kalitesi.executions.schedule_policy import (
    band_description,
    is_within_band,
    recommend_for,
)
from veri_kalitesi.executions.scheduling import ScheduleType


def test_near_time_recommendations_are_5_10_15_minute_intervals() -> None:
    proposals = recommend_for(TimelinessNature.NEAR_TIME)

    assert [p.schedule_type for p in proposals] == [ScheduleType.INTERVAL] * 3
    assert [p.interval_minutes for p in proposals] == [5, 10, 15]


def test_real_time_recommendation_is_instant_minute_interval() -> None:
    proposals = recommend_for(TimelinessNature.REAL_TIME)

    assert len(proposals) == 1
    assert proposals[0].schedule_type is ScheduleType.INTERVAL
    assert proposals[0].interval_minutes == 1


def test_batch_time_recommendations_are_daily_weekly_monthly() -> None:
    proposals = recommend_for(TimelinessNature.BATCH_TIME)

    assert [p.schedule_type for p in proposals] == [
        ScheduleType.DAILY,
        ScheduleType.WEEKLY,
        ScheduleType.MONTHLY,
    ]


@pytest.mark.parametrize(
    ("schedule_type", "interval_minutes", "expected"),
    [
        (ScheduleType.INTERVAL, 5, True),
        (ScheduleType.INTERVAL, 10, True),
        (ScheduleType.INTERVAL, 15, True),
        (ScheduleType.INTERVAL, 3, False),
        (ScheduleType.INTERVAL, 30, False),
        (ScheduleType.INTERVAL, None, False),
        (ScheduleType.DAILY, None, False),
    ],
)
def test_near_time_band_accepts_only_5_to_15_minutes(
    schedule_type: ScheduleType, interval_minutes: int | None, expected: bool
) -> None:
    assert is_within_band(TimelinessNature.NEAR_TIME, schedule_type, interval_minutes) is expected


@pytest.mark.parametrize(
    ("schedule_type", "interval_minutes", "expected"),
    [
        (ScheduleType.INTERVAL, 1, True),
        (ScheduleType.INTERVAL, 2, False),
        (ScheduleType.DAILY, None, False),
    ],
)
def test_real_time_band_accepts_only_instant_interval(
    schedule_type: ScheduleType, interval_minutes: int | None, expected: bool
) -> None:
    assert is_within_band(TimelinessNature.REAL_TIME, schedule_type, interval_minutes) is expected


@pytest.mark.parametrize(
    ("schedule_type", "interval_minutes", "expected"),
    [
        (ScheduleType.DAILY, None, True),
        (ScheduleType.WEEKLY, None, True),
        (ScheduleType.MONTHLY, None, True),
        (ScheduleType.INTERVAL, 5, False),
        (ScheduleType.ONCE, None, False),
    ],
)
def test_batch_time_band_accepts_only_periodic_types(
    schedule_type: ScheduleType, interval_minutes: int | None, expected: bool
) -> None:
    assert is_within_band(TimelinessNature.BATCH_TIME, schedule_type, interval_minutes) is expected


def test_band_descriptions_cover_all_natures() -> None:
    assert band_description(TimelinessNature.NEAR_TIME) == "INTERVAL 5-15 dakika"
    assert band_description(TimelinessNature.REAL_TIME) == "INTERVAL 1 dakika (anlık)"
    assert band_description(TimelinessNature.BATCH_TIME) == "DAILY / WEEKLY / MONTHLY"
