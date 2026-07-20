"""SQLite skor gecmisi icin salt okunur rapor onizleme reader'i."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from decimal import Decimal
from threading import RLock

from veri_kalitesi.reporting.models import ReportScoreObservation
from veri_kalitesi.scoring.models import ScoreLevel, ScoreScopeType, ScoreStatus


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
            WITH ranked_scores AS (
                SELECT scope_id, score_value, score_status, level, calculated_at,
                    ROW_NUMBER() OVER (
                        PARTITION BY scope_id
                        ORDER BY julianday(calculated_at) DESC, quality_score_id DESC
                    ) AS row_rank
                FROM quality_scores
                WHERE scope_type = ?
                  AND julianday(calculated_at) >= julianday(?)
                  AND julianday(calculated_at) <= julianday(?)
                  AND scope_id IN ({placeholders})
            )
            SELECT scope_id, score_value, score_status, level, calculated_at
            FROM ranked_scores
            WHERE row_rank = 1
            ORDER BY scope_id
        """
        with self._lock:
            rows = self.connection.execute(statement, parameters).fetchall()
        return tuple(_row_to_observation(row) for row in rows)


def _row_to_observation(row: sqlite3.Row) -> ReportScoreObservation:
    return ReportScoreObservation(
        source_id=row["scope_id"],
        score_value=Decimal(row["score_value"]) if row["score_value"] is not None else None,
        score_status=ScoreStatus(row["score_status"]),
        level=ScoreLevel(row["level"]) if row["level"] is not None else None,
        calculated_at=datetime.fromisoformat(row["calculated_at"]),
    )
