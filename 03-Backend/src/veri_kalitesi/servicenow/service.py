"""Trusted, data-minimum ServiceNow ticket creation service."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from time import sleep
from typing import Callable, Protocol
from uuid import uuid4

from veri_kalitesi.audit import (
    AuditError,
    AuditEventInput,
    AuditResult,
    PreparedAuditEvent,
    SQLiteTransactionalAudit,
)
from veri_kalitesi.identity import ActorContext, is_trusted_actor_context
from veri_kalitesi.servicenow.errors import (
    ServiceNowAdapterError,
    ServiceNowAdapterErrorKind,
    ServiceNowAuthorizationError,
    ServiceNowConflictError,
    ServiceNowError,
    ServiceNowPolicyError,
    ServiceNowTechnicalError,
    ServiceNowValidationError,
)
from veri_kalitesi.servicenow.models import (
    ServiceNowCircuitBreakerPolicy,
    ServiceNowCircuitSnapshot,
    ServiceNowCircuitState,
    ServiceNowExportPolicy,
    ServiceNowIssueProjection,
    ServiceNowRetryJob,
    ServiceNowRetryJobStatus,
    ServiceNowRetryPolicy,
    ServiceNowTicketCommand,
    ServiceNowTicketHistoryEntry,
    ServiceNowTicketLink,
    ServiceNowTicketRequest,
    ServiceNowTicketResponse,
    ServiceNowTicketStatus,
    validate_command,
    validate_circuit_breaker_policy,
    validate_policy,
    validate_projection,
    validate_response,
    validate_retry_policy,
)
from veri_kalitesi.servicenow.repository import SQLiteServiceNowRepository


class ServiceNowIssueResolver(Protocol):
    def resolve_issue(self, issue_id: str) -> ServiceNowIssueProjection | None: ...


class ServiceNowAdapter(Protocol):
    def create_ticket(self, request: ServiceNowTicketRequest) -> ServiceNowTicketResponse: ...


class ServiceNowService:
    def __init__(
        self,
        repository: SQLiteServiceNowRepository,
        issue_resolver: ServiceNowIssueResolver,
        adapter: ServiceNowAdapter,
        transactional_audit: SQLiteTransactionalAudit,
        export_policy: ServiceNowExportPolicy,
        *,
        retry_policy: ServiceNowRetryPolicy = ServiceNowRetryPolicy(),
        circuit_breaker_policy: ServiceNowCircuitBreakerPolicy = ServiceNowCircuitBreakerPolicy(),
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        sleeper: Callable[[float], None] = sleep,
    ) -> None:
        validate_policy(export_policy)
        validate_retry_policy(retry_policy)
        validate_circuit_breaker_policy(circuit_breaker_policy)
        self.repository = repository
        self.issue_resolver = issue_resolver
        self.adapter = adapter
        self.transactional_audit = transactional_audit
        self.export_policy = export_policy
        self.retry_policy = retry_policy
        self.circuit_breaker_policy = circuit_breaker_policy
        self.clock = clock
        self.sleeper = sleeper

    def create_ticket(
        self,
        command: ServiceNowTicketCommand,
        actor_context: ActorContext | None,
    ) -> ServiceNowTicketLink:
        validate_command(command)
        context = self._authorize_actor(actor_context)
        projection = self._resolve_projection(command)
        self._enforce_export_policy(projection)

        idempotency_digest = _digest_text(command.idempotency_key)
        request = ServiceNowTicketRequest(
            client_request_id=idempotency_digest,
            issue_reference=projection.issue_reference,
            source_event_type=projection.source_event_type.value,
            priority=projection.priority.value,
            detail_reference_id=projection.detail_reference_id,
            correlation_id=command.correlation_id,
        )
        payload_digest = _payload_digest(projection, request)
        try:
            existing = self.repository.resolve_existing(
                command.issue_id,
                idempotency_digest,
                payload_digest,
            )
        except ServiceNowConflictError:
            raise
        except (sqlite3.Error, OSError) as exc:
            raise ServiceNowTechnicalError(
                "ServiceNow ticket state could not be read.", command.correlation_id
            ) from exc
        if existing is not None:
            return existing

        try:
            queued = self.repository.resolve_retry_job(
                command.issue_id,
                idempotency_digest,
                payload_digest,
            )
        except ServiceNowConflictError:
            raise
        except (sqlite3.Error, OSError) as exc:
            raise ServiceNowTechnicalError(
                "ServiceNow retry state could not be read.", command.correlation_id
            ) from exc
        if queued is not None:
            try:
                queued_error_kind = ServiceNowAdapterErrorKind(queued.last_error_kind)
            except ValueError:
                queued_error_kind = ServiceNowAdapterErrorKind.UNKNOWN
            raise ServiceNowTechnicalError(
                "ServiceNow ticket request is already queued.",
                command.correlation_id,
                queued_error_kind,
                attempt_count=queued.attempt_count,
                retry_job_id=queued.job_id,
            )

        now = self._now()
        link_id = str(uuid4())
        audit_event = self._prepare_audit_event(
            command,
            context,
            projection,
            link_id,
            now,
        )
        try:
            response = self._call_adapter(request, command.correlation_id, context)
        except ServiceNowTechnicalError as exc:
            if (
                exc.error_kind
                in {
                    ServiceNowAdapterErrorKind.TEMPORARY,
                    ServiceNowAdapterErrorKind.RATE_LIMIT,
                }
                and exc.attempt_count >= self.retry_policy.max_attempts
            ) or exc.error_kind is ServiceNowAdapterErrorKind.CIRCUIT_OPEN:
                queued_job = self._enqueue_retry(
                    command.issue_id,
                    request,
                    payload_digest,
                    exc.error_kind,
                    context,
                    now,
                )
                raise ServiceNowTechnicalError(
                    "ServiceNow ticket request was queued for deferred delivery.",
                    command.correlation_id,
                    exc.error_kind,
                    attempt_count=exc.attempt_count,
                    retry_job_id=queued_job.job_id,
                ) from exc
            raise
        link = ServiceNowTicketLink(
            link_id=link_id,
            issue_id=command.issue_id,
            external_ticket_id=response.external_ticket_id,
            ticket_number=response.ticket_number,
            idempotency_key_digest=idempotency_digest,
            payload_digest=payload_digest,
            status=ServiceNowTicketStatus.CREATED,
            created_at=now,
        )
        history = ServiceNowTicketHistoryEntry(
            link_id=link.link_id,
            issue_id=link.issue_id,
            action="SERVICENOW_TICKET_CREATED",
            actor_id=context.actor_id,
            old_status=None,
            new_status=ServiceNowTicketStatus.CREATED,
            occurred_at=now,
        )
        try:
            stored = self.repository.add(
                link,
                history,
                audit_event=audit_event,
                audit_outbox=self.transactional_audit,
            )
        except ServiceNowConflictError:
            raise
        except (sqlite3.Error, OSError) as exc:
            raise ServiceNowTechnicalError(
                "ServiceNow ticket link could not be persisted.",
                command.correlation_id,
            ) from exc
        self.transactional_audit.publish_pending()
        return stored

    def process_next_retry(
        self,
        actor_context: ActorContext | None,
    ) -> ServiceNowRetryJob | None:
        context = self._authorize_actor(actor_context)
        now = self._now()
        try:
            job = self.repository.claim_next_retry(now)
        except (sqlite3.Error, OSError) as exc:
            raise ServiceNowTechnicalError(
                "ServiceNow retry job could not be claimed.",
                context.correlation_id,
            ) from exc
        if job is None:
            return None

        try:
            self._acquire_circuit(context, job.request.correlation_id, job.attempt_count)
        except ServiceNowTechnicalError:
            self._release_retry_claim(job, now)
            raise

        try:
            response = self.adapter.create_ticket(job.request)
            validate_response(response)
            self._record_circuit_non_transient(context, job.request.correlation_id, now)
        except ServiceNowAdapterError as exc:
            try:
                if exc.error_kind in {
                    ServiceNowAdapterErrorKind.TEMPORARY,
                    ServiceNowAdapterErrorKind.RATE_LIMIT,
                }:
                    self._record_circuit_failure(
                        context,
                        job.request.correlation_id,
                        exc.error_kind,
                        now,
                    )
                else:
                    self._record_circuit_non_transient(
                        context,
                        job.request.correlation_id,
                        now,
                    )
            except ServiceNowTechnicalError:
                self._release_retry_claim(job, now)
                raise
            return self._record_retry_failure(job, exc, context, now)
        except ServiceNowValidationError:
            try:
                self._record_circuit_non_transient(context, job.request.correlation_id, now)
            except ServiceNowTechnicalError:
                self._release_retry_claim(job, now)
                raise
            return self._record_retry_failure(
                job,
                ServiceNowAdapterError(ServiceNowAdapterErrorKind.PERMANENT),
                context,
                now,
            )
        except ServiceNowTechnicalError:
            self._release_retry_claim(job, now)
            raise
        except Exception:
            try:
                self._record_circuit_non_transient(context, job.request.correlation_id, now)
            except ServiceNowTechnicalError:
                self._release_retry_claim(job, now)
                raise
            return self._record_retry_failure(
                job,
                ServiceNowAdapterError(ServiceNowAdapterErrorKind.UNKNOWN),
                context,
                now,
            )

        link = ServiceNowTicketLink(
            issue_id=job.issue_id,
            external_ticket_id=response.external_ticket_id,
            ticket_number=response.ticket_number,
            idempotency_key_digest=job.request.client_request_id,
            payload_digest=job.payload_digest,
            status=ServiceNowTicketStatus.CREATED,
            created_at=now,
        )
        history = ServiceNowTicketHistoryEntry(
            link_id=link.link_id,
            issue_id=link.issue_id,
            action="SERVICENOW_TICKET_CREATED",
            actor_id=context.actor_id,
            old_status=None,
            new_status=ServiceNowTicketStatus.CREATED,
            occurred_at=now,
        )
        try:
            audit_event = self._prepare_created_audit(
                context,
                job.request,
                link.link_id,
                now,
            )
            completed, _ = self.repository.complete_retry(
                job,
                link,
                history,
                audit_event=audit_event,
                audit_outbox=self.transactional_audit,
            )
        except (AuditError, sqlite3.Error, OSError, ServiceNowTechnicalError) as exc:
            self._release_retry_claim(job, now)
            raise ServiceNowTechnicalError(
                "ServiceNow retry completion could not be persisted.",
                job.request.correlation_id,
            ) from exc
        self.transactional_audit.publish_pending()
        return completed

    def requeue_dead_letter(
        self,
        job_id: str,
        actor_context: ActorContext | None,
    ) -> ServiceNowRetryJob:
        context = self._authorize_actor(actor_context)
        now = self._now()
        audit_event = self._prepare_retry_audit(
            action="SERVICENOW_RETRY_REQUEUED",
            context=context,
            job_id=job_id,
            status=ServiceNowRetryJobStatus.PENDING,
            attempt_count=0,
            error_kind="REQUEUED",
            correlation_id=context.correlation_id,
            occurred_at=now,
        )
        try:
            job = self.repository.requeue_dead_letter(
                job_id,
                requeued_at=now,
                audit_event=audit_event,
                audit_outbox=self.transactional_audit,
            )
        except (sqlite3.Error, OSError) as exc:
            raise ServiceNowTechnicalError(
                "ServiceNow dead-letter job could not be requeued.",
                context.correlation_id,
            ) from exc
        self.transactional_audit.publish_pending()
        return job

    def _enqueue_retry(
        self,
        issue_id: str,
        request: ServiceNowTicketRequest,
        payload_digest: str,
        error_kind: ServiceNowAdapterErrorKind,
        context: ActorContext,
        now: datetime,
    ) -> ServiceNowRetryJob:
        job = ServiceNowRetryJob(
            issue_id=issue_id,
            request=request,
            payload_digest=payload_digest,
            status=ServiceNowRetryJobStatus.PENDING,
            attempt_count=0,
            next_attempt_at=now,
            last_error_kind=error_kind.value,
            created_at=now,
            updated_at=now,
        )
        audit_event = self._prepare_retry_audit(
            action="SERVICENOW_RETRY_ENQUEUED",
            context=context,
            job_id=job.job_id,
            status=job.status,
            attempt_count=job.attempt_count,
            error_kind=error_kind.value,
            correlation_id=request.correlation_id,
            occurred_at=now,
        )
        try:
            stored = self.repository.enqueue_retry(
                job,
                audit_event=audit_event,
                audit_outbox=self.transactional_audit,
            )
        except ServiceNowConflictError:
            raise
        except (sqlite3.Error, OSError) as exc:
            raise ServiceNowTechnicalError(
                "ServiceNow retry job could not be persisted.",
                request.correlation_id,
            ) from exc
        self.transactional_audit.publish_pending()
        return stored

    def _record_retry_failure(
        self,
        job: ServiceNowRetryJob,
        error: ServiceNowAdapterError,
        context: ActorContext,
        now: datetime,
    ) -> ServiceNowRetryJob:
        delay = self._retry_delay(error, job.attempt_count)
        status = (
            ServiceNowRetryJobStatus.PENDING
            if delay is not None
            else ServiceNowRetryJobStatus.DEAD_LETTER
        )
        next_attempt_at = now + timedelta(seconds=delay or 0)
        action = (
            "SERVICENOW_RETRY_SCHEDULED"
            if status is ServiceNowRetryJobStatus.PENDING
            else "SERVICENOW_RETRY_DEAD_LETTERED"
        )
        try:
            audit_event = self._prepare_retry_audit(
                action=action,
                context=context,
                job_id=job.job_id,
                status=status,
                attempt_count=job.attempt_count,
                error_kind=error.error_kind.value,
                correlation_id=job.request.correlation_id,
                occurred_at=now,
            )
            updated = self.repository.record_retry_failure(
                job.job_id,
                status=status,
                next_attempt_at=next_attempt_at,
                error_kind=error.error_kind.value,
                updated_at=now,
                audit_event=audit_event,
                audit_outbox=self.transactional_audit,
            )
        except (AuditError, sqlite3.Error, OSError, ServiceNowTechnicalError) as exc:
            self._release_retry_claim(job, now)
            raise ServiceNowTechnicalError(
                "ServiceNow retry state could not be persisted.",
                job.request.correlation_id,
            ) from exc
        self.transactional_audit.publish_pending()
        return updated

    def _release_retry_claim(self, job: ServiceNowRetryJob, released_at: datetime) -> None:
        try:
            self.repository.release_retry_claim(job.job_id, released_at)
        except (sqlite3.Error, OSError) as exc:
            raise ServiceNowTechnicalError(
                "ServiceNow retry claim recovery failed.",
                job.request.correlation_id,
            ) from exc

    def _prepare_retry_audit(
        self,
        *,
        action: str,
        context: ActorContext,
        job_id: str,
        status: ServiceNowRetryJobStatus,
        attempt_count: int,
        error_kind: str,
        correlation_id: str,
        occurred_at: datetime,
    ) -> PreparedAuditEvent:
        try:
            return self.transactional_audit.prepare(
                AuditEventInput(
                    actor_id=context.actor_id,
                    actor_type=context.actor_type.value,
                    correlation_id=correlation_id,
                    action=action,
                    object_type="ServiceNowRetryJob",
                    object_id=job_id,
                    result=AuditResult.SUCCESS,
                    reason_code=error_kind,
                    old_values={},
                    new_values={
                        "status": status.value,
                        "attempt_count": attempt_count,
                        "error_kind": error_kind,
                    },
                    occurred_at=occurred_at,
                    session_id=context.session_id,
                )
            )
        except AuditError as exc:
            raise ServiceNowTechnicalError(
                "ServiceNow retry audit event could not be prepared.",
                correlation_id,
            ) from exc

    def _prepare_audit_event(
        self,
        command: ServiceNowTicketCommand,
        context: ActorContext,
        projection: ServiceNowIssueProjection,
        link_id: str,
        occurred_at: datetime,
    ) -> PreparedAuditEvent:
        try:
            return self.transactional_audit.prepare(
                AuditEventInput(
                    actor_id=context.actor_id,
                    actor_type=context.actor_type.value,
                    correlation_id=command.correlation_id,
                    action="SERVICENOW_TICKET_CREATED",
                    object_type="ServiceNowTicketLink",
                    object_id=link_id,
                    result=AuditResult.SUCCESS,
                    reason_code="ALLOWLIST_PAYLOAD_ACCEPTED",
                    old_values={},
                    new_values={
                        "status": ServiceNowTicketStatus.CREATED.value,
                        "source_event_type": projection.source_event_type.value,
                        "priority": projection.priority.value,
                        "adapter_result": "CREATED",
                    },
                    occurred_at=occurred_at,
                    session_id=context.session_id,
                )
            )
        except AuditError as exc:
            raise ServiceNowTechnicalError(
                "ServiceNow audit event could not be prepared.",
                command.correlation_id,
            ) from exc

    def _prepare_created_audit(
        self,
        context: ActorContext,
        request: ServiceNowTicketRequest,
        link_id: str,
        occurred_at: datetime,
    ) -> PreparedAuditEvent:
        try:
            return self.transactional_audit.prepare(
                AuditEventInput(
                    actor_id=context.actor_id,
                    actor_type=context.actor_type.value,
                    correlation_id=request.correlation_id,
                    action="SERVICENOW_TICKET_CREATED",
                    object_type="ServiceNowTicketLink",
                    object_id=link_id,
                    result=AuditResult.SUCCESS,
                    reason_code="ALLOWLIST_PAYLOAD_ACCEPTED",
                    old_values={},
                    new_values={
                        "status": ServiceNowTicketStatus.CREATED.value,
                        "source_event_type": request.source_event_type,
                        "priority": request.priority,
                        "adapter_result": "CREATED",
                    },
                    occurred_at=occurred_at,
                    session_id=context.session_id,
                )
            )
        except AuditError as exc:
            raise ServiceNowTechnicalError(
                "ServiceNow audit event could not be prepared.",
                request.correlation_id,
            ) from exc

    def _resolve_projection(
        self,
        command: ServiceNowTicketCommand,
    ) -> ServiceNowIssueProjection:
        try:
            projection = self.issue_resolver.resolve_issue(command.issue_id)
        except ServiceNowError:
            raise
        except Exception as exc:
            raise ServiceNowTechnicalError(
                "ServiceNow issue resolution failed.", command.correlation_id
            ) from exc
        if projection is None or projection.issue_id != command.issue_id:
            raise ServiceNowPolicyError("Issue is not available for ServiceNow export.")
        validate_projection(projection)
        return projection

    def _enforce_export_policy(self, projection: ServiceNowIssueProjection) -> None:
        if projection.status not in self.export_policy.eligible_statuses:
            raise ServiceNowPolicyError("Issue status is not eligible for ServiceNow export.")
        if projection.priority not in self.export_policy.eligible_priorities:
            raise ServiceNowPolicyError("Issue priority is not eligible for ServiceNow export.")

    def _call_adapter(
        self,
        request: ServiceNowTicketRequest,
        correlation_id: str,
        context: ActorContext,
    ) -> ServiceNowTicketResponse:
        for attempt_no in range(1, self.retry_policy.max_attempts + 1):
            self._acquire_circuit(context, correlation_id, attempt_no)
            try:
                response = self.adapter.create_ticket(request)
                validate_response(response)
                self._record_circuit_non_transient(context, correlation_id, self._now())
                return response
            except ServiceNowAdapterError as exc:
                if exc.error_kind in {
                    ServiceNowAdapterErrorKind.TEMPORARY,
                    ServiceNowAdapterErrorKind.RATE_LIMIT,
                }:
                    snapshot = self._record_circuit_failure(
                        context,
                        correlation_id,
                        exc.error_kind,
                        self._now(),
                    )
                    if snapshot.state is ServiceNowCircuitState.OPEN:
                        raise ServiceNowTechnicalError(
                            "ServiceNow circuit opened after temporary failures.",
                            correlation_id,
                            ServiceNowAdapterErrorKind.CIRCUIT_OPEN,
                            attempt_count=attempt_no,
                        ) from exc
                else:
                    self._record_circuit_non_transient(context, correlation_id, self._now())
                delay = self._retry_delay(exc, attempt_no)
                if delay is None:
                    raise ServiceNowTechnicalError(
                        "ServiceNow adapter request failed.",
                        correlation_id,
                        exc.error_kind,
                        attempt_count=attempt_no,
                    ) from exc
                try:
                    self.sleeper(delay)
                except Exception as sleep_error:
                    raise ServiceNowTechnicalError(
                        "ServiceNow retry scheduling failed.",
                        correlation_id,
                        ServiceNowAdapterErrorKind.UNKNOWN,
                        attempt_count=attempt_no,
                    ) from sleep_error
            except ServiceNowValidationError as exc:
                self._record_circuit_non_transient(context, correlation_id, self._now())
                raise ServiceNowTechnicalError(
                    "ServiceNow adapter returned an invalid response.",
                    correlation_id,
                    ServiceNowAdapterErrorKind.PERMANENT,
                    attempt_count=attempt_no,
                ) from exc
            except ServiceNowTechnicalError:
                raise
            except Exception as exc:
                self._record_circuit_non_transient(context, correlation_id, self._now())
                raise ServiceNowTechnicalError(
                    "ServiceNow adapter request failed.",
                    correlation_id,
                    attempt_count=attempt_no,
                ) from exc
        raise AssertionError("ServiceNow retry loop completed without a result.")

    def _acquire_circuit(
        self,
        context: ActorContext,
        correlation_id: str,
        attempt_count: int,
    ) -> None:
        now = self._now()
        audit_event = self._prepare_circuit_audit(
            action="SERVICENOW_CIRCUIT_HALF_OPENED",
            context=context,
            state=ServiceNowCircuitState.HALF_OPEN,
            correlation_id=correlation_id,
            occurred_at=now,
        )
        try:
            allowed, snapshot = self.repository.try_acquire_circuit(
                now,
                self.circuit_breaker_policy,
                half_open_audit_event=audit_event,
                audit_outbox=self.transactional_audit,
            )
        except (sqlite3.Error, OSError) as exc:
            raise ServiceNowTechnicalError(
                "ServiceNow circuit state could not be acquired.",
                correlation_id,
            ) from exc
        self.transactional_audit.publish_pending()
        if not allowed:
            raise ServiceNowTechnicalError(
                "ServiceNow circuit is open.",
                correlation_id,
                ServiceNowAdapterErrorKind.CIRCUIT_OPEN,
                attempt_count=attempt_count,
            )

    def _record_circuit_failure(
        self,
        context: ActorContext,
        correlation_id: str,
        error_kind: ServiceNowAdapterErrorKind,
        now: datetime,
    ) -> ServiceNowCircuitSnapshot:
        audit_event = self._prepare_circuit_audit(
            action="SERVICENOW_CIRCUIT_OPENED",
            context=context,
            state=ServiceNowCircuitState.OPEN,
            correlation_id=correlation_id,
            occurred_at=now,
            error_kind=error_kind.value,
        )
        try:
            snapshot = self.repository.record_circuit_failure(
                now,
                self.circuit_breaker_policy,
                opened_audit_event=audit_event,
                audit_outbox=self.transactional_audit,
            )
        except (sqlite3.Error, OSError) as exc:
            raise ServiceNowTechnicalError(
                "ServiceNow circuit failure state could not be persisted.",
                correlation_id,
            ) from exc
        self.transactional_audit.publish_pending()
        return snapshot

    def _record_circuit_non_transient(
        self,
        context: ActorContext,
        correlation_id: str,
        now: datetime,
    ) -> ServiceNowCircuitSnapshot:
        audit_event = self._prepare_circuit_audit(
            action="SERVICENOW_CIRCUIT_CLOSED",
            context=context,
            state=ServiceNowCircuitState.CLOSED,
            correlation_id=correlation_id,
            occurred_at=now,
        )
        try:
            snapshot = self.repository.record_circuit_non_transient_result(
                now,
                closed_audit_event=audit_event,
                audit_outbox=self.transactional_audit,
            )
        except (sqlite3.Error, OSError) as exc:
            raise ServiceNowTechnicalError(
                "ServiceNow circuit success state could not be persisted.",
                correlation_id,
            ) from exc
        self.transactional_audit.publish_pending()
        return snapshot

    def _prepare_circuit_audit(
        self,
        *,
        action: str,
        context: ActorContext,
        state: ServiceNowCircuitState,
        correlation_id: str,
        occurred_at: datetime,
        error_kind: str = "NONE",
    ) -> PreparedAuditEvent:
        try:
            return self.transactional_audit.prepare(
                AuditEventInput(
                    actor_id=context.actor_id,
                    actor_type=context.actor_type.value,
                    correlation_id=correlation_id,
                    action=action,
                    object_type="ServiceNowCircuitBreaker",
                    object_id="SERVICENOW_DEFAULT",
                    result=AuditResult.SUCCESS,
                    reason_code=error_kind,
                    old_values={},
                    new_values={
                        "state": state.value,
                        "error_kind": error_kind,
                        "policy_version": self.circuit_breaker_policy.version,
                    },
                    occurred_at=occurred_at,
                    session_id=context.session_id,
                )
            )
        except AuditError as exc:
            raise ServiceNowTechnicalError(
                "ServiceNow circuit audit event could not be prepared.",
                correlation_id,
            ) from exc

    def _retry_delay(
        self,
        error: ServiceNowAdapterError,
        attempt_no: int,
    ) -> float | None:
        if attempt_no >= self.retry_policy.max_attempts:
            return None
        if error.error_kind is ServiceNowAdapterErrorKind.TEMPORARY:
            return self.retry_policy.base_delay_seconds * (2 ** (attempt_no - 1))
        if error.error_kind is not ServiceNowAdapterErrorKind.RATE_LIMIT:
            return None
        retry_after = error.retry_after_seconds
        if isinstance(retry_after, bool) or not isinstance(retry_after, int) or retry_after < 0:
            return None
        return float(retry_after)

    def _authorize_actor(self, context: ActorContext | None) -> ActorContext:
        now = self._now()
        if not is_trusted_actor_context(context):
            raise ServiceNowAuthorizationError("Trusted actor context is required.")
        assert context is not None
        if context.issued_at > now or context.expires_at <= now:
            raise ServiceNowAuthorizationError("Actor context is not currently valid.")
        if context.policy_version != self.export_policy.actor_policy_version:
            raise ServiceNowAuthorizationError("Actor context policy version is not accepted.")
        if context.actor_type not in self.export_policy.allowed_producer_actor_types:
            raise ServiceNowAuthorizationError("Actor type cannot create ServiceNow tickets.")
        if context.privileged:
            raise ServiceNowAuthorizationError(
                "Privileged context cannot use the standard ServiceNow flow."
            )
        if "SERVICENOW_TICKET_PRODUCER" not in context.roles:
            raise ServiceNowAuthorizationError("ServiceNow producer role is required.")
        return context

    def _now(self) -> datetime:
        now = self.clock()
        if now.tzinfo is None or now.utcoffset() is None:
            raise ServiceNowValidationError("Service clock must return timezone-aware values.")
        return now


def _payload_digest(
    projection: ServiceNowIssueProjection,
    request: ServiceNowTicketRequest,
) -> str:
    payload = {
        "issue_id": projection.issue_id,
        "issue_reference": request.issue_reference,
        "source_event_type": request.source_event_type,
        "priority": request.priority,
        "detail_reference_id": request.detail_reference_id,
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
