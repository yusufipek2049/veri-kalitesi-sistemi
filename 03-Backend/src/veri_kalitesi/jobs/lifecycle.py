"""Dead-letter yetkilendirme ve yeniden işleme servisi."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from veri_kalitesi.audit import AuditEventInput, AuditResult, PostgreSQLTransactionalAudit
from veri_kalitesi.identity import ActorContext, ActorType
from veri_kalitesi.identity.models import is_trusted_actor_context
from veri_kalitesi.jobs.errors import JobAuthorizationError, JobNotFoundError
from veri_kalitesi.jobs.models import BackgroundJob
from veri_kalitesi.jobs.postgresql_repository import PostgreSQLJobQueueRepository


@dataclass(frozen=True)
class DeadLetterReprocessPolicy:
    version: str
    allowed_roles: frozenset[str]

    def __post_init__(self) -> None:
        if (
            not self.version.strip()
            or not self.allowed_roles
            or any(not role.strip() for role in self.allowed_roles)
        ):
            raise ValueError("Dead-letter reprocess policy must be explicit and versioned.")


class DeadLetterReprocessService:
    def __init__(
        self,
        repository: PostgreSQLJobQueueRepository,
        transactional_audit: PostgreSQLTransactionalAudit,
        policy: DeadLetterReprocessPolicy,
    ) -> None:
        self._repository = repository
        self._transactional_audit = transactional_audit
        self._policy = policy

    def reprocess(
        self,
        dead_letter_id: str,
        actor_context: ActorContext | None,
        *,
        now: datetime | None = None,
    ) -> BackgroundJob:
        occurred_at = now or datetime.now(timezone.utc)
        if (
            not is_trusted_actor_context(actor_context)
            or actor_context is None
            or actor_context.actor_type is not ActorType.USER
            or actor_context.issued_at > occurred_at
            or actor_context.expires_at <= occurred_at
            or actor_context.privileged
            or actor_context.policy_version != self._policy.version
            or not actor_context.roles.intersection(self._policy.allowed_roles)
        ):
            raise JobAuthorizationError("Dead-letter reprocessing is not authorized.")
        letters = {
            item.dead_letter_id: item for item in self._repository.list_dead_letters()
        }
        letter = letters.get(dead_letter_id)
        if letter is None:
            raise JobNotFoundError("Open job dead-letter record not found.")
        audit = self._transactional_audit.prepare(
            AuditEventInput(
                actor_id=actor_context.actor_id,
                actor_type=actor_context.actor_type.value,
                correlation_id=actor_context.correlation_id,
                action="JOB_DEAD_LETTER_REPROCESSED",
                object_type="BackgroundJob",
                object_id=letter.job_id,
                result=AuditResult.SUCCESS,
                reason_code="AUTHORIZED_REPROCESS",
                old_values={
                    "dead_letter_status": letter.status.value,
                    "attempt_count": letter.attempt_count,
                },
                new_values={"job_status": "QUEUED"},
                occurred_at=occurred_at,
                session_id=actor_context.session_id,
            )
        )
        return self._repository.reprocess_dead_letter(
            dead_letter_id,
            actor_id=actor_context.actor_id,
            now=occurred_at,
            audit_event=audit,
            audit_outbox=self._transactional_audit,
        )
