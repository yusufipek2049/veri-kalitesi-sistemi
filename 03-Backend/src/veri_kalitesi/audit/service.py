"""Merkezi audit yazma siniri ve acik hata politikasi."""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Callable, Protocol

from veri_kalitesi.audit.errors import (
    AuditQueryAuthorizationError,
    AuditQueryTechnicalError,
    AuditQueryValidationError,
    AuditValidationError,
    AuditWriteError,
)
from veri_kalitesi.audit.models import (
    AuditAccessPolicy,
    AuditEvent,
    AuditEventInput,
    AuditFailureMode,
    AuditFailurePolicy,
    AuditIntegrityResult,
    AuditQuery,
    AuditQueryPage,
    AuditResult,
    PreparedAuditEvent,
)
from veri_kalitesi.audit.redaction import AuditRedactor

if TYPE_CHECKING:
    from veri_kalitesi.identity.models import ActorContext


_CODE_PATTERN = re.compile(r"[A-Z0-9_.-]{1,120}")


class AuditEventRepository(Protocol):
    def append(self, prepared: PreparedAuditEvent) -> AuditEvent: ...


class DurableAuditBuffer(Protocol):
    def append(self, prepared: PreparedAuditEvent) -> None: ...


class AuditSink(Protocol):
    def append(self, event: AuditEventInput) -> AuditEvent | None: ...


class AuditQueryRepository(Protocol):
    def query_events(self, query: AuditQuery) -> tuple[tuple[AuditEvent, ...], bool]: ...

    def latest_sequence_no(self) -> int: ...

    def verify_integrity(self) -> AuditIntegrityResult: ...


class AuditService:
    def __init__(
        self,
        repository: AuditEventRepository,
        redactor: AuditRedactor,
        failure_policy: AuditFailurePolicy,
        *,
        durable_buffer: DurableAuditBuffer | None = None,
    ) -> None:
        if not failure_policy.version.strip():
            raise AuditValidationError("Audit failure policy version is required.")
        if (
            failure_policy.default_mode is AuditFailureMode.DURABLE_BUFFER
            or AuditFailureMode.DURABLE_BUFFER in failure_policy.action_modes.values()
        ) and durable_buffer is None:
            raise AuditValidationError("Durable audit mode requires a configured durable buffer.")
        self.repository = repository
        self.redactor = redactor
        self.failure_policy = failure_policy
        self.durable_buffer = durable_buffer

    def append(self, event: AuditEventInput) -> AuditEvent | None:
        prepared = self.redactor.prepare(event)
        try:
            return self.repository.append(prepared)
        except Exception as exc:
            mode = self.failure_policy.mode_for(event.action)
            if mode is AuditFailureMode.FAIL_CLOSED:
                raise AuditWriteError("Critical audit event could not be written.") from exc
            assert self.durable_buffer is not None
            try:
                self.durable_buffer.append(prepared)
            except Exception as buffer_exc:
                raise AuditWriteError(
                    "Audit event could not be written or buffered."
                ) from buffer_exc
            return None


class AuditQueryService:
    def __init__(
        self,
        repository: AuditQueryRepository,
        audit_sink: AuditSink,
        policy: AuditAccessPolicy,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        _validate_access_policy(policy)
        self.repository = repository
        self.audit_sink = audit_sink
        self.policy = policy
        self.clock = clock

    def query(
        self,
        query: AuditQuery,
        actor_context: ActorContext | None,
    ) -> AuditQueryPage:
        context = self._authorize(actor_context)
        normalized = _validate_query(query, self.policy)
        try:
            through_sequence_no = (
                normalized.through_sequence_no
                if normalized.through_sequence_no is not None
                else self.repository.latest_sequence_no()
            )
            if through_sequence_no < normalized.after_sequence_no:
                raise AuditQueryValidationError("Audit query cursor exceeds its snapshot.")
            normalized = _with_snapshot(normalized, through_sequence_no)
            events, has_more = self.repository.query_events(normalized)
            integrity = self.repository.verify_integrity()
        except AuditQueryValidationError:
            raise
        except (sqlite3.Error, OSError, ValueError, TypeError) as exc:
            raise AuditQueryTechnicalError(context.correlation_id) from exc
        next_cursor = events[-1].sequence_no if has_more and events else None
        self._record_view(context, normalized, len(events), integrity.valid)
        return AuditQueryPage(
            events=events,
            integrity=integrity,
            next_after_sequence_no=next_cursor,
            through_sequence_no=through_sequence_no,
            policy_version=self.policy.version,
        )

    def _authorize(self, context: ActorContext | None) -> ActorContext:
        now = self.clock()
        if now.tzinfo is None or now.utcoffset() is None:
            raise AuditQueryValidationError("Audit query clock must be timezone-aware.")
        reason_code = _authorization_denial_reason(context, self.policy, now)
        if reason_code is not None:
            trusted = context if _is_trusted_actor_context(context) else None
            self._record_denial(trusted, reason_code, now)
            raise AuditQueryAuthorizationError(
                reason_code,
                trusted.correlation_id if trusted is not None else "audit-access-denied",
            )
        assert context is not None
        return context

    def _record_denial(
        self,
        context: ActorContext | None,
        reason_code: str,
        occurred_at: datetime,
    ) -> None:
        event = AuditEventInput(
            actor_id=context.actor_id if context is not None else "UNKNOWN",
            actor_type=context.actor_type.value if context is not None else None,
            correlation_id=(
                context.correlation_id if context is not None else "audit-access-denied"
            ),
            action="AUDIT_RECORDS_VIEW_AUTHORIZATION",
            object_type="AuthorizationDecision",
            object_id=None,
            result=AuditResult.DENIED,
            reason_code=reason_code,
            old_values={},
            new_values={
                "policy_version": self.policy.version,
                "reason_code": reason_code,
            },
            occurred_at=occurred_at,
            session_id=context.session_id if context is not None else None,
        )
        self._append_access_audit(event)

    def _record_view(
        self,
        context: ActorContext,
        query: AuditQuery,
        returned_count: int,
        integrity_valid: bool,
    ) -> None:
        event = AuditEventInput(
            actor_id=context.actor_id,
            actor_type=context.actor_type.value,
            correlation_id=context.correlation_id,
            action="AUDIT_RECORDS_VIEWED",
            object_type="AuditLog",
            object_id=None,
            result=AuditResult.SUCCESS,
            reason_code="QUERY_COMPLETED",
            old_values={},
            new_values={
                "policy_version": self.policy.version,
                "query_reason_code": query.reason_code,
                "filter_count": _filter_count(query),
                "page_size": query.page_size,
                "returned_count": returned_count,
                "integrity_valid": integrity_valid,
            },
            occurred_at=self.clock(),
            session_id=context.session_id,
        )
        self._append_access_audit(event)

    def _append_access_audit(self, event: AuditEventInput) -> None:
        try:
            self.audit_sink.append(event)
        except Exception as exc:
            raise AuditQueryTechnicalError(event.correlation_id) from exc


def _validate_access_policy(policy: AuditAccessPolicy) -> None:
    if not _CODE_PATTERN.fullmatch(policy.version):
        raise AuditQueryValidationError("Audit access policy version is invalid.")
    if not policy.context_policy_version.strip():
        raise AuditQueryValidationError("Audit context policy version is required.")
    if not _CODE_PATTERN.fullmatch(policy.required_role):
        raise AuditQueryValidationError("Audit access role is invalid.")
    if (
        isinstance(policy.max_sync_window_days, bool)
        or not isinstance(policy.max_sync_window_days, int)
        or not 1 <= policy.max_sync_window_days <= 366
    ):
        raise AuditQueryValidationError("Audit sync window must be between 1 and 366 days.")
    if (
        isinstance(policy.max_page_size, bool)
        or not isinstance(policy.max_page_size, int)
        or not 1 <= policy.max_page_size <= 1000
    ):
        raise AuditQueryValidationError("Audit page size policy is invalid.")


def _validate_query(query: AuditQuery, policy: AuditAccessPolicy) -> AuditQuery:
    if query.start_at.tzinfo is None or query.start_at.utcoffset() is None:
        raise AuditQueryValidationError("Audit query start time must be timezone-aware.")
    if query.end_at.tzinfo is None or query.end_at.utcoffset() is None:
        raise AuditQueryValidationError("Audit query end time must be timezone-aware.")
    start_at = query.start_at.astimezone(timezone.utc)
    end_at = query.end_at.astimezone(timezone.utc)
    if start_at > end_at:
        raise AuditQueryValidationError("Audit query start must not follow end time.")
    if end_at - start_at > timedelta(days=policy.max_sync_window_days):
        raise AuditQueryValidationError("Audit query requires asynchronous reporting.")
    if not _CODE_PATTERN.fullmatch(query.reason_code):
        raise AuditQueryValidationError("Audit query reason code is invalid.")
    if (
        isinstance(query.after_sequence_no, bool)
        or not isinstance(query.after_sequence_no, int)
        or query.after_sequence_no < 0
    ):
        raise AuditQueryValidationError("Audit query cursor is invalid.")
    if query.through_sequence_no is not None and (
        isinstance(query.through_sequence_no, bool)
        or not isinstance(query.through_sequence_no, int)
        or query.through_sequence_no < query.after_sequence_no
    ):
        raise AuditQueryValidationError("Audit query snapshot cursor is invalid.")
    if (
        isinstance(query.page_size, bool)
        or not isinstance(query.page_size, int)
        or query.page_size < 1
        or query.page_size > policy.max_page_size
    ):
        raise AuditQueryValidationError("Audit query page size is invalid.")
    for value in (
        query.actor_id,
        query.action,
        query.object_type,
        query.object_id,
        query.correlation_id,
    ):
        if value is not None and not value.strip():
            raise AuditQueryValidationError("Audit query filters must not be blank.")
    if query.action is not None and not _CODE_PATTERN.fullmatch(query.action):
        raise AuditQueryValidationError("Audit action filter is invalid.")
    if query.result is not None and not isinstance(query.result, AuditResult):
        raise AuditQueryValidationError("Audit result filter is invalid.")
    return AuditQuery(
        start_at=start_at,
        end_at=end_at,
        reason_code=query.reason_code,
        actor_id=query.actor_id,
        action=query.action,
        object_type=query.object_type,
        object_id=query.object_id,
        result=query.result,
        correlation_id=query.correlation_id,
        after_sequence_no=query.after_sequence_no,
        through_sequence_no=query.through_sequence_no,
        page_size=query.page_size,
    )


def _with_snapshot(query: AuditQuery, through_sequence_no: int) -> AuditQuery:
    return AuditQuery(
        start_at=query.start_at,
        end_at=query.end_at,
        reason_code=query.reason_code,
        actor_id=query.actor_id,
        action=query.action,
        object_type=query.object_type,
        object_id=query.object_id,
        result=query.result,
        correlation_id=query.correlation_id,
        after_sequence_no=query.after_sequence_no,
        through_sequence_no=through_sequence_no,
        page_size=query.page_size,
    )


def _authorization_denial_reason(
    context: ActorContext | None,
    policy: AuditAccessPolicy,
    now: datetime,
) -> str | None:
    from veri_kalitesi.identity.models import ActorType

    if not _is_trusted_actor_context(context):
        return "UNTRUSTED_CONTEXT"
    assert context is not None
    if context.issued_at > now:
        return "CONTEXT_NOT_YET_VALID"
    if context.expires_at <= now:
        return "CONTEXT_EXPIRED"
    if context.policy_version != policy.context_policy_version:
        return "POLICY_VERSION_MISMATCH"
    if context.actor_type is not ActorType.USER:
        return "ACTOR_TYPE_NOT_ALLOWED"
    if context.privileged:
        return "PRIVILEGED_CONTEXT_NOT_ALLOWED"
    if policy.required_role not in context.roles:
        return "AUDIT_ROLE_REQUIRED"
    return None


def _is_trusted_actor_context(context: object) -> bool:
    from veri_kalitesi.identity.models import is_trusted_actor_context

    return is_trusted_actor_context(context)


def _filter_count(query: AuditQuery) -> int:
    return sum(
        value is not None
        for value in (
            query.actor_id,
            query.action,
            query.object_type,
            query.object_id,
            query.result,
            query.correlation_id,
        )
    )
