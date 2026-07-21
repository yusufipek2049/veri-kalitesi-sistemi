"""SQLite skor gecmisi icin salt okunur rapor onizleme reader'i."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from decimal import Decimal
from threading import RLock

from veri_kalitesi.reporting.models import ReportScoreObservation
from veri_kalitesi.scoring.models import (
    QualityScore,
    ScoreLevel,
    ScoreScopeType,
    ScoreStatus,
    is_official_observation,
)


class SQLiteReportPreviewReader:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.row_factory = sqlite3.Row
        self._lock = RLock()

    def latest_source_scores(
        self,
        start_at: datetime,
        end_at: datetime,
        allowed_source_ids: frozenset[str],
    ) -> tuple[ReportScoreObservation, ...]:
        if not allowed_source_ids:
            return ()
        placeholders = ", ".join("?" for _ in allowed_source_ids)
        parameters: list[object] = [
            ScoreScopeType.SOURCE.value,
            start_at.isoformat(),
            end_at.isoformat(),
            *sorted(allowed_source_ids),
        ]
        statement = f"""
            SELECT quality_score_id, execution_id, rule_version_id, rule_result_id,
                scope_id, score_value, score_status, level, calculation_details,
                calculated_at
            FROM quality_scores
            WHERE scope_type = ?
              AND julianday(calculated_at) >= julianday(?)
              AND julianday(calculated_at) <= julianday(?)
              AND scope_id IN ({placeholders})
            ORDER BY scope_id, julianday(calculated_at) DESC, quality_score_id DESC
        """
        with self._lock:
            rows = self.connection.execute(statement, parameters).fetchall()
        latest: dict[str, ReportScoreObservation] = {}
        for row in rows:
            source_id = row["scope_id"]
            if source_id not in latest and is_official_observation(_row_to_score(row)):
                latest[source_id] = _row_to_observation(row)
        return tuple(latest[source_id] for source_id in sorted(latest))


def _row_to_score(row: sqlite3.Row) -> QualityScore:
    return QualityScore(
        quality_score_id=row["quality_score_id"],
        execution_id=row["execution_id"],
        rule_version_id=row["rule_version_id"],
        rule_result_id=row["rule_result_id"],
        scope_type=ScoreScopeType.SOURCE,
        scope_id=row["scope_id"],
        score_value=Decimal(row["score_value"]) if row["score_value"] is not None else None,
        score_status=ScoreStatus(row["score_status"]),
        level=ScoreLevel(row["level"]) if row["level"] is not None else None,
        calculation_details=json.loads(row["calculation_details"]),
        calculated_at=datetime.fromisoformat(row["calculated_at"]),
    )


def _row_to_observation(row: sqlite3.Row) -> ReportScoreObservation:
    return ReportScoreObservation(
        source_id=row["scope_id"],
        score_value=Decimal(row["score_value"]) if row["score_value"] is not None else None,
        score_status=ScoreStatus(row["score_status"]),
        level=ScoreLevel(row["level"]) if row["level"] is not None else None,
        calculated_at=datetime.fromisoformat(row["calculated_at"]),
    )
