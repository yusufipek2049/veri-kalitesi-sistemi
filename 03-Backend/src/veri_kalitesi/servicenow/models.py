"""Data-minimum ServiceNow integration models."""

from __future__ import annotations

import re
import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from veri_kalitesi.identity import ActorType
from veri_kalitesi.issues import IssuePriority, IssueSourceEventType, IssueStatus
from veri_kalitesi.servicenow.errors import ServiceNowValidationError


_CODE_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,199}")
_FORBIDDEN_TEXT = (
    "password",
    "passwd",
    "secret",
    "token",
    "credential",
    "authorization",
)


class ServiceNowTicketStatus(str, Enum):
    CREATED = "CREATED"


class ServiceNowRetryJobStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    DEAD_LETTER = "DEAD_LETTER"


@dataclass(frozen=True)
class ServiceNowTicketCommand:
    issue_id: str
    idempotency_key: str
    correlation_id: str


@dataclass(frozen=True)
class ServiceNowIssueProjection:
    issue_id: str
    issue_reference: str
    source_event_type: IssueSourceEventType
    status: IssueStatus
    priority: IssuePriority
    detail_reference_id: str


@dataclass(frozen=True)
class ServiceNowTicketRequest:
    client_request_id: str
    issue_reference: str
    source_event_type: str
    priority: str
    detail_reference_id: str
    correlation_id: str


@dataclass(frozen=True)
class ServiceNowTicketResponse:
    external_ticket_id: str
    ticket_number: str


@dataclass(frozen=True)
class ServiceNowTicketLink:
    issue_id: str
    external_ticket_id: str
    ticket_number: str
    idempotency_key_digest: str
    payload_digest: str
    status: ServiceNowTicketStatus
    created_at: datetime
    link_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(frozen=True)
class ServiceNowTicketHistoryEntry:
    link_id: str
    issue_id: str
    action: str
    actor_id: str
    old_status: ServiceNowTicketStatus | None
    new_status: ServiceNowTicketStatus
    occurred_at: datetime
    history_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(frozen=True)
class ServiceNowExportPolicy:
    version: str
    actor_policy_version: str
    eligible_statuses: frozenset[IssueStatus]
    eligible_priorities: frozenset[IssuePriority]
    allowed_producer_actor_types: frozenset[ActorType] = field(
        default_factory=lambda: frozenset({ActorType.SERVICE})
    )


@dataclass(frozen=True)
class ServiceNowRetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: float = 1.0


@dataclass(frozen=True)
class ServiceNowRetryJob:
    issue_id: str
    request: ServiceNowTicketRequest
    payload_digest: str
    status: ServiceNowRetryJobStatus
    attempt_count: int
    next_attempt_at: datetime
    last_error_kind: str
    created_at: datetime
    updated_at: datetime
    job_id: str = field(default_factory=lambda: str(uuid4()))
    link_id: str | None = None


def validate_command(command: ServiceNowTicketCommand) -> None:
    _validate_uuid("issue_id", command.issue_id)
    _validate_code("idempotency_key", command.idempotency_key)
    _validate_code("correlation_id", command.correlation_id)


def validate_projection(projection: ServiceNowIssueProjection) -> None:
    _validate_uuid("projection.issue_id", projection.issue_id)
    _validate_code("projection.issue_reference", projection.issue_reference)
    if not isinstance(projection.source_event_type, IssueSourceEventType):
        raise ServiceNowValidationError("projection.source_event_type is invalid.")
    if not isinstance(projection.status, IssueStatus):
        raise ServiceNowValidationError("projection.status is invalid.")
    if not isinstance(projection.priority, IssuePriority):
        raise ServiceNowValidationError("projection.priority is invalid.")
    _validate_uuid("projection.detail_reference_id", projection.detail_reference_id)


def validate_response(response: ServiceNowTicketResponse) -> None:
    _validate_code("response.external_ticket_id", response.external_ticket_id)
    _validate_code("response.ticket_number", response.ticket_number)


def validate_policy(policy: ServiceNowExportPolicy) -> None:
    _validate_code("policy.version", policy.version)
    _validate_code("policy.actor_policy_version", policy.actor_policy_version)
    if not policy.eligible_statuses or not all(
        isinstance(status, IssueStatus) for status in policy.eligible_statuses
    ):
        raise ServiceNowValidationError("policy.eligible_statuses is invalid.")
    if not policy.eligible_priorities or not all(
        isinstance(priority, IssuePriority) for priority in policy.eligible_priorities
    ):
        raise ServiceNowValidationError("policy.eligible_priorities is invalid.")
    if policy.allowed_producer_actor_types != frozenset({ActorType.SERVICE}):
        raise ServiceNowValidationError("Only service actors can produce ServiceNow tickets.")


def validate_retry_policy(policy: ServiceNowRetryPolicy) -> None:
    if (
        isinstance(policy.max_attempts, bool)
        or not isinstance(policy.max_attempts, int)
        or not 1 <= policy.max_attempts <= 3
    ):
        raise ServiceNowValidationError("Retry policy must allow between 1 and 3 attempts.")
    if (
        isinstance(policy.base_delay_seconds, bool)
        or not isinstance(policy.base_delay_seconds, (int, float))
        or not math.isfinite(policy.base_delay_seconds)
        or policy.base_delay_seconds < 0
    ):
        raise ServiceNowValidationError("Retry base delay must be a finite non-negative number.")


def validate_retry_job(job: ServiceNowRetryJob) -> None:
    _validate_uuid("retry_job.job_id", job.job_id)
    _validate_uuid("retry_job.issue_id", job.issue_id)
    _validate_code("retry_job.request.client_request_id", job.request.client_request_id)
    _validate_code("retry_job.request.issue_reference", job.request.issue_reference)
    _validate_code("retry_job.request.source_event_type", job.request.source_event_type)
    _validate_code("retry_job.request.priority", job.request.priority)
    _validate_uuid("retry_job.request.detail_reference_id", job.request.detail_reference_id)
    _validate_code("retry_job.request.correlation_id", job.request.correlation_id)
    _validate_code("retry_job.payload_digest", job.payload_digest)
    if not isinstance(job.status, ServiceNowRetryJobStatus):
        raise ServiceNowValidationError("retry_job.status is invalid.")
    if (
        isinstance(job.attempt_count, bool)
        or not isinstance(job.attempt_count, int)
        or job.attempt_count < 0
    ):
        raise ServiceNowValidationError("retry_job.attempt_count is invalid.")
    _validate_code("retry_job.last_error_kind", job.last_error_kind)
    _validate_aware_datetime("retry_job.next_attempt_at", job.next_attempt_at)
    _validate_aware_datetime("retry_job.created_at", job.created_at)
    _validate_aware_datetime("retry_job.updated_at", job.updated_at)
    if job.link_id is not None:
        _validate_uuid("retry_job.link_id", job.link_id)


def _validate_uuid(field_name: str, value: str) -> None:
    try:
        UUID(value)
    except (AttributeError, TypeError, ValueError) as exc:
        raise ServiceNowValidationError(f"{field_name} must be a UUID.") from exc


def _validate_code(field_name: str, value: str) -> None:
    if not isinstance(value, str) or not _CODE_PATTERN.fullmatch(value):
        raise ServiceNowValidationError(f"{field_name} is invalid.")
    normalized = value.lower()
    if any(part in normalized for part in _FORBIDDEN_TEXT):
        raise ServiceNowValidationError(f"{field_name} contains forbidden content.")


def _validate_aware_datetime(field_name: str, value: datetime) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ServiceNowValidationError(f"{field_name} must be timezone-aware.")
