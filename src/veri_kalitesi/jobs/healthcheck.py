"""Container healthcheck for the non-HTTP worker process."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os

from sqlalchemy import select

from veri_kalitesi.jobs.models import JobStatus, WorkerState
from veri_kalitesi.jobs.postgresql_repository import job_tables
from veri_kalitesi.jobs.settings import PersistentJobSettings
from veri_kalitesi.persistence import create_session_factory


def worker_is_healthy(settings: PersistentJobSettings, *, max_age_seconds: float) -> bool:
    if max_age_seconds <= 0:
        return False
    session_factory = create_session_factory(settings.database)
    tables = job_tables(settings.database.schema)
    worker = tables.workers
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=max_age_seconds)
    with session_factory() as session:
        row = session.execute(
            select(worker.c.state, worker.c.last_seen_at).where(
                worker.c.worker_id == settings.worker_id
            )
        ).one_or_none()
        active_job = session.execute(
            select(tables.background_jobs.c.job_id)
            .where(
                tables.background_jobs.c.claimed_by == settings.worker_id,
                tables.background_jobs.c.status.in_(
                    (JobStatus.RUNNING.value, JobStatus.CANCEL_REQUESTED.value)
                ),
                tables.background_jobs.c.last_heartbeat_at >= cutoff,
            )
            .limit(1)
        ).one_or_none()
    idle_heartbeat_is_fresh = bool(
        row is not None
        and row.state in {WorkerState.STARTING.value, WorkerState.RUNNING.value}
        and row.last_seen_at is not None
        and row.last_seen_at >= cutoff
    )
    return idle_heartbeat_is_fresh or active_job is not None


def main() -> int:
    try:
        settings = PersistentJobSettings.from_environment()
        max_age = float(
            os.environ.get(
                "DQ_WORKER_HEALTH_MAX_AGE_SECONDS",
                str(settings.lease_duration_seconds),
            )
        )
        return 0 if worker_is_healthy(settings, max_age_seconds=max_age) else 1
    except Exception:
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
