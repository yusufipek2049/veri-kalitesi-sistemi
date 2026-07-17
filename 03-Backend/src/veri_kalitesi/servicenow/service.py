"""Trusted, data-minimum ServiceNow ticket creation service."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
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
    ServiceNowExportPolicy,
    ServiceNowIssueProjection,
    ServiceNowRetryPolicy,
    ServiceNowTicketCommand,
    ServiceNowTicketHistoryEntry,
    ServiceNowTicketLink,
    ServiceNowTicketRequest,
    ServiceNowTicketResponse,
    ServiceNowTicketStatus,
    validate_command,
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
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        sleeper: Callable[[float], None] = sleep,
    ) -> None:
        validate_policy(export_policy)
        validate_retry_policy(retry_policy)
        self.repository = repository
        self.issue_resolver = issue_resolver
        self.adapter = adapter
        self.transactional_audit = transactional_audit
        self.export_policy = export_policy
        self.retry_policy = retry_policy
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

        now = self._now()
        link_id = str(uuid4())
        audit_event = self._prepare_audit_event(
            command,
            context,
            projection,
            link_id,
            now,
        )
        response = self._call_adapter(request, command.correlation_id)
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
    ) -> ServiceNowTicketResponse:
        for attempt_no in range(1, self.retry_policy.max_attempts + 1):
            try:
                response = self.adapter.create_ticket(request)
                validate_response(response)
                return response
            except ServiceNowAdapterError as exc:
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
                raise ServiceNowTechnicalError(
                    "ServiceNow adapter returned an invalid response.",
                    correlation_id,
                    ServiceNowAdapterErrorKind.PERMANENT,
                    attempt_count=attempt_no,
                ) from exc
            except Exception as exc:
                raise ServiceNowTechnicalError(
                    "ServiceNow adapter request failed.",
                    correlation_id,
                    attempt_count=attempt_no,
                ) from exc
        raise AssertionError("ServiceNow retry loop completed without a result.")

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
