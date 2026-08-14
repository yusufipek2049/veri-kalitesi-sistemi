"""Worker process environment settings."""

from __future__ import annotations

from dataclasses import dataclass
import os
from datetime import timedelta

from veri_kalitesi.persistence import DatabaseSettings


@dataclass(frozen=True)
class PersistentJobSettings:
    """Worker süreci için gerekli yapılandırma değerleri."""

    worker_id: str
    hostname: str
    capacity: int
    lease_duration_seconds: int
    idle_wait_seconds: float
    shutdown_grace_seconds: float
    database: DatabaseSettings
    schedule_trigger_interval_seconds: float = 5.0
    local_secret_dir: str | None = None
    issue_policy_version: str = "ISSUE_ACCESS_POLICY_V1"
    actor_policy_version: str = "DASHBOARD_POLICY_V1"

    def __post_init__(self) -> None:
        if not isinstance(self.worker_id, str) or not self.worker_id.strip():
            raise ValueError("Worker id must not be blank.")
        if not isinstance(self.hostname, str) or not self.hostname.strip():
            raise ValueError("Worker hostname must not be blank.")
        if (
            not isinstance(self.capacity, int)
            or isinstance(self.capacity, bool)
            or self.capacity <= 0
        ):
            raise ValueError("Worker capacity must be a positive integer.")
        if self.lease_duration_seconds <= 0:
            raise ValueError("Worker lease duration must be positive.")
        if self.idle_wait_seconds <= 0:
            raise ValueError("Worker idle wait must be positive.")
        if self.shutdown_grace_seconds < 0:
            raise ValueError("Worker shutdown grace must not be negative.")
        if self.schedule_trigger_interval_seconds <= 0:
            raise ValueError("Schedule trigger interval must be positive.")
        if not self.issue_policy_version.strip():
            raise ValueError("Issue policy version must not be blank.")
        if not self.actor_policy_version.strip():
            raise ValueError("Actor policy version must not be blank.")

    @property
    def lease_policy_duration(self) -> timedelta:
        return timedelta(seconds=self.lease_duration_seconds)

    @classmethod
    def from_environment(cls) -> "PersistentJobSettings":
        return cls(
            worker_id=os.environ.get("DQ_WORKER_ID", "worker-01"),
            hostname=os.environ.get("DQ_WORKER_HOSTNAME", "localhost"),
            capacity=int(os.environ.get("DQ_WORKER_CAPACITY", "1")),
            lease_duration_seconds=int(os.environ.get("DQ_WORKER_LEASE_SECONDS", "300")),
            idle_wait_seconds=float(os.environ.get("DQ_WORKER_IDLE_WAIT_SECONDS", "0.5")),
            shutdown_grace_seconds=float(os.environ.get("DQ_WORKER_SHUTDOWN_GRACE_SECONDS", "5.0")),
            database=DatabaseSettings.from_environment(),
            schedule_trigger_interval_seconds=float(
                os.environ.get("DQ_SCHEDULE_TRIGGER_INTERVAL_SECONDS", "5.0")
            ),
            local_secret_dir=os.environ.get("DATA_QUALITY_LOCAL_SECRET_DIR"),
            issue_policy_version=os.environ.get(
                "DATA_QUALITY_ISSUE_POLICY_VERSION",
                "ISSUE_ACCESS_POLICY_V1",
            ),
            actor_policy_version=os.environ.get(
                "DATA_QUALITY_ACTOR_POLICY_VERSION", "DASHBOARD_POLICY_V1"
            ),
        )
