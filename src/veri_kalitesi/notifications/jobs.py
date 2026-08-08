"""DS-09 notification delivery job enqueue ve handler.

NOTIFICATION_DELIVERY job'ları, batch staging sırasında oluşturulur ve
worker tarafından işlenir. Handler, NotificationDeliveryService üzerinden
teslimat durum makinesi geçişlerini yönetir.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from veri_kalitesi.jobs.models import BackgroundJob, JobCompletionOutcome
from veri_kalitesi.jobs.worker import PermanentJobError
from veri_kalitesi.notifications.delivery_service import NotificationDeliveryService
from veri_kalitesi.notifications.errors import NotificationDeliveryError
from veri_kalitesi.persistence import DEFAULT_SCHEMA_NAME, SessionFactory, transactional_session


# ---------------------------------------------------------------------------
# Job payload
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NotificationDeliveryJobPayload:
    """NOTIFICATION_DELIVERY job payload."""

    delivery_id: str
    event_id: str

    def to_dict(self) -> dict[str, str]:
        return {
            "delivery_id": self.delivery_id,
            "event_id": self.event_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NotificationDeliveryJobPayload:
        delivery_id = data.get("delivery_id")
        event_id = data.get("event_id")
        if not isinstance(delivery_id, str) or not delivery_id.strip():
            raise PermanentJobError("INVALID_NOTIFICATION_DELIVERY_JOB_PAYLOAD")
        if not isinstance(event_id, str) or not event_id.strip():
            raise PermanentJobError("INVALID_NOTIFICATION_DELIVERY_JOB_PAYLOAD")
        return cls(delivery_id=delivery_id, event_id=event_id)


def notification_delivery_idempotency_key(delivery_id: str) -> str:
    """Deterministik idempotency key — delivery başına tek job."""
    return f"notif-delivery:{delivery_id}"


# ---------------------------------------------------------------------------
# Job enqueuer
# ---------------------------------------------------------------------------


class NotificationDeliveryJobEnqueuer:
    """Notification delivery job enqueue — session-aware.

    Batch staging sırasında issue transaction'ına katılır; session verilirse
    mevcut transaction'a, aksi hâlde yeni transaction açar.
    """

    def __init__(
        self,
        session_factory: SessionFactory,
        *,
        schema: str = DEFAULT_SCHEMA_NAME,
    ) -> None:
        self._session_factory = session_factory
        self._schema = schema

    def enqueue_delivery(
        self,
        delivery_id: str,
        event_id: str,
        *,
        session: Any = None,
    ) -> BackgroundJob:
        """NOTIFICATION_DELIVERY job'ı enqueue eder."""
        payload = NotificationDeliveryJobPayload(
            delivery_id=delivery_id,
            event_id=event_id,
        )
        job = BackgroundJob(
            job_type="NOTIFICATION_DELIVERY",
            payload=payload.to_dict(),
            idempotency_key=notification_delivery_idempotency_key(delivery_id),
        )
        if session is not None:
            from veri_kalitesi.jobs.postgresql_repository import PostgreSQLJobQueueRepository

            repo = PostgreSQLJobQueueRepository(self._session_factory, schema=self._schema)
            repo.enqueue(job, session=session)
        else:
            with transactional_session(self._session_factory) as active_session:
                from veri_kalitesi.jobs.postgresql_repository import PostgreSQLJobQueueRepository

                repo = PostgreSQLJobQueueRepository(self._session_factory, schema=self._schema)
                repo.enqueue(job, session=active_session)
        return job


# ---------------------------------------------------------------------------
# Job handler
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NotificationDeliveryJobHandler:
    """NOTIFICATION_DELIVERY job → NotificationDeliveryService adapter."""

    delivery_service: NotificationDeliveryService

    def __call__(
        self,
        job: BackgroundJob,
        *,
        connection_timeout_seconds: int,
        query_timeout_seconds: int,
        total_timeout_seconds: int,
        cancellation_event: Any,
        progress_callback: Any = lambda _percent: None,
    ) -> JobCompletionOutcome:
        payload = NotificationDeliveryJobPayload.from_dict(job.payload)
        try:
            self.delivery_service.attempt_delivery(payload.delivery_id)
        except NotificationDeliveryError:
            raise
        except PermanentJobError:
            raise
        except Exception as exc:
            raise PermanentJobError(f"NOTIFICATION_DELIVERY_FAILED: {exc}") from exc
        return JobCompletionOutcome.SUCCESS
