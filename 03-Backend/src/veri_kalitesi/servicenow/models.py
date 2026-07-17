"""Data-minimum ServiceNow integration models."""

from __future__ import annotations

import re
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
