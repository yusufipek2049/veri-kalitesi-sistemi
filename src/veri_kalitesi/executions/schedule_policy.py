"""Tablo zamanlılık niteliğine göre job tekrarlama aralığı öneri ve bantları.

Jobs ekranı, seçilen veri setinin timeliness_nature değerine göre önerilen
tekrarlama aralıklarını sunar. Öneri bandının dışındaki tanımlar governance
talebi (SCHEDULE_INTERVAL_EXCEPTION) gerektirir.

Bantlar:
- NEAR_TIME: INTERVAL 5-15 dakika (öneriler 5, 10, 15)
- REAL_TIME: INTERVAL 1 dakika (anlık)
- BATCH_TIME: DAILY / WEEKLY / MONTHLY
"""

from __future__ import annotations

from dataclasses import dataclass

from veri_kalitesi.data_sources.models import TimelinessNature
from veri_kalitesi.executions.scheduling import ScheduleType


@dataclass(frozen=True)
class ScheduleProposal:
    """Nitelik bazlı önerilen tekrarlama tanımı."""

    schedule_type: ScheduleType
    interval_minutes: int | None = None
    label: str = ""


_NEAR_TIME_PROPOSALS = (
    ScheduleProposal(ScheduleType.INTERVAL, interval_minutes=5, label="Her 5 dakika"),
    ScheduleProposal(ScheduleType.INTERVAL, interval_minutes=10, label="Her 10 dakika"),
    ScheduleProposal(ScheduleType.INTERVAL, interval_minutes=15, label="Her 15 dakika"),
)

_REAL_TIME_PROPOSALS = (
    ScheduleProposal(ScheduleType.INTERVAL, interval_minutes=1, label="Her dakika (anlık)"),
)

_BATCH_TIME_PROPOSALS = (
    ScheduleProposal(ScheduleType.DAILY, label="Günlük"),
    ScheduleProposal(ScheduleType.WEEKLY, label="Haftalık"),
    ScheduleProposal(ScheduleType.MONTHLY, label="Aylık"),
)


def recommend_for(nature: TimelinessNature) -> tuple[ScheduleProposal, ...]:
    """Nitelik için önerilen tekrarlama aralıklarını döndürür."""

    if nature is TimelinessNature.NEAR_TIME:
        return _NEAR_TIME_PROPOSALS
    if nature is TimelinessNature.REAL_TIME:
        return _REAL_TIME_PROPOSALS
    return _BATCH_TIME_PROPOSALS


def is_within_band(
    nature: TimelinessNature,
    schedule_type: ScheduleType,
    interval_minutes: int | None = None,
) -> bool:
    """Verilen tanımın nitelik bandının içinde olup olmadığını değerlendirir."""

    if nature is TimelinessNature.NEAR_TIME:
        return (
            schedule_type is ScheduleType.INTERVAL
            and interval_minutes is not None
            and 5 <= interval_minutes <= 15
        )
    if nature is TimelinessNature.REAL_TIME:
        return schedule_type is ScheduleType.INTERVAL and interval_minutes == 1
    return schedule_type in (ScheduleType.DAILY, ScheduleType.WEEKLY, ScheduleType.MONTHLY)


def band_description(nature: TimelinessNature) -> str:
    """Kullanıcıya gösterilecek bant açıklaması."""

    if nature is TimelinessNature.NEAR_TIME:
        return "INTERVAL 5-15 dakika"
    if nature is TimelinessNature.REAL_TIME:
        return "INTERVAL 1 dakika (anlık)"
    return "DAILY / WEEKLY / MONTHLY"
