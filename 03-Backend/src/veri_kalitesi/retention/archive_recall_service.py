"""Authorized archive recall request and decision service."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

from veri_kalitesi.audit import (
    AuditEventInput,
    AuditResult,
    PreparedAuditEvent,
    SQLiteTransactionalAudit,
)
from veri_kalitesi.identity import ActorContext, ActorType, is_trusted_actor_context
from veri_kalitesi.retention.archive_recall_repository import SQLiteArchiveRecallRepository
from veri_kalitesi.retention.errors import (
    RetentionAuthorizationError,
    RetentionConflictError,
    RetentionError,
    RetentionTechnicalError,
    RetentionValidationError,
)
from veri_kalitesi.retention.models import (
    ArchiveRecallAccessPolicy,
    ArchiveRecallDecision,
    ArchiveRecallDecisionType,
    ArchiveRecallRequest,
    ArchiveRecordType,
    RetentionScopeType,
)


_CODE_PATTERN = re.compile(r"[A-Z0-9_.:-]{1,160}")


class ArchiveRecallService:
    """Authorizes recall metadata without reading or moving archive content."""

    def __init__(
        self,
        repository: SQLiteArchiveRecallRepository,
        transactional_audit: SQLiteTransactionalAudit,
        access_policy: ArchiveRecallAccessPolicy,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        _validate_access_policy(access_policy)
        self.repository = repository
        self.transactional_audit = transactional_audit
        self.access_policy = access_policy
        self.clock = clock

    def request_recall(
        self,
        *,
        archive_reference: str,
        record_type: ArchiveRecordType,
        scope_type: RetentionScopeType,
        scope_id: str | None,
        purpose_code: str,
        idempotency_key: str,
        actor_context: ActorContext | None,
    ) -> ArchiveRecallRequest:
        context, actor_role, now = self._authorize(
            actor_context,
            required_roles=self.access_policy.request_roles,
        )
        _validate_opaque_value(archive_reference, "Archive reference", maximum=256)
        _validate_opaque_value(idempotency_key, "Archive recall idempotency key", maximum=256)
        _validate_scope(scope_type, scope_id)
        _authorize_scope(context, scope_type, scope_id)
        if purpose_code not in self.access_policy.purpose_codes:
            raise RetentionValidationError("Archive recall purpose is not allowed.")

        idempotency_digest = _digest_text(idempotency_key)
        payload_digest = _digest_payload(
            {
                "archive_reference_digest": _digest_text(archive_reference),
                "record_type": record_type.value,
                "scope_type": scope_type.value,
                "scope_digest": _digest_text(scope_id) if scope_id is not None else None,
                "purpose_code": purpose_code,
            }
        )
        try:
            existing = self.repository.get_by_idempotency_digest(idempotency_digest)
        except RetentionError:
            raise
        except Exception as exc:
            raise RetentionTechnicalError(
                "Archive recall idempotency state could not be read."
            ) from exc
        if existing is not None:
            if existing.payload_digest != payload_digest:
                raise RetentionConflictError(
                    "Archive recall idempotency key was reused with a different payload."
                )
            self.transactional_audit.publish_pending()
            return existing

        request = ArchiveRecallRequest(
            request_id=str(uuid4()),
            idempotency_key_digest=idempotency_digest,
            payload_digest=payload_digest,
            archive_reference_digest=_digest_text(archive_reference),
            record_type=record_type,
            scope_type=scope_type,
            scope_digest=_digest_text(scope_id) if scope_id is not None else None,
            purpose_code=purpose_code,
            requested_by_actor_id=context.actor_id,
            requested_by_role=actor_role,
            requested_at=now,
        )
        audit_event = self._prepare_audit(
            context,
            action="ARCHIVE_RECALL_REQUESTED",
            request=request,
            reason_code=purpose_code,
            old_status="NONE",
            new_values={
                "status": request.status.value,
                "record_type": request.record_type.value,
                "scope_type": request.scope_type.value,
            },
            occurred_at=now,
        )
        try:
            stored = self.repository.create(
                request,
                audit_event=audit_event,
                audit_outbox=self.transactional_audit,
            )
        except RetentionError:
            raise
        except Exception as exc:
            raise RetentionTechnicalError("Archive recall request could not be persisted.") from exc
        self.transactional_audit.publish_pending()
        return stored

    def decide_recall(
        self,
        request_id: str,
        *,
        decision: ArchiveRecallDecisionType,
        reason_code: str,
        actor_context: ActorContext | None,
    ) -> ArchiveRecallRequest:
        context, actor_role, now = self._authorize(
            actor_context,
            required_roles=self.access_policy.decision_roles,
        )
        _validate_opaque_value(request_id, "Archive recall request ID", maximum=128)
        allowed_reasons = (
            self.access_policy.approval_reason_codes
            if decision is ArchiveRecallDecisionType.APPROVED
            else self.access_policy.rejection_reason_codes
        )
        if reason_code not in allowed_reasons:
            raise RetentionValidationError("Archive recall decision reason is not allowed.")
        try:
            request = self.repository.get(request_id)
        except RetentionError:
            raise
        except Exception as exc:
            raise RetentionTechnicalError("Archive recall request could not be read.") from exc
        if context.actor_id == request.requested_by_actor_id:
            raise RetentionAuthorizationError(
                "Archive recall requester cannot decide the same request."
            )
        _authorize_stored_scope(context, request)
        if request.decision is not None:
            if (
                request.decision.decision is not decision
                or request.decision.reason_code != reason_code
                or request.decision.decided_by_actor_id != context.actor_id
            ):
                raise RetentionConflictError(
                    "Archive recall request already has a different decision."
                )
            self.transactional_audit.publish_pending()
            return request

        decision_event = ArchiveRecallDecision(
            decision_id=str(uuid4()),
            request_id=request.request_id,
            decision=decision,
            reason_code=reason_code,
            decided_by_actor_id=context.actor_id,
            decided_by_role=actor_role,
            decided_at=now,
        )
        audit_event = self._prepare_audit(
            context,
            action="ARCHIVE_RECALL_DECIDED",
            request=request,
            reason_code=reason_code,
            old_status=request.status.value,
            new_values={
                "status": decision.value,
                "record_type": request.record_type.value,
                "scope_type": request.scope_type.value,
            },
            occurred_at=now,
            audit_result=(
                AuditResult.SUCCESS
                if decision is ArchiveRecallDecisionType.APPROVED
                else AuditResult.DENIED
            ),
        )
        try:
            stored = self.repository.decide(
                decision_event,
                audit_event=audit_event,
                audit_outbox=self.transactional_audit,
            )
        except RetentionError:
            raise
        except Exception as exc:
            raise RetentionTechnicalError(
                "Archive recall decision could not be persisted."
            ) from exc
        self.transactional_audit.publish_pending()
        return stored

    def _authorize(
        self,
        context: ActorContext | None,
        *,
        required_roles: frozenset[str],
    ) -> tuple[ActorContext, str, datetime]:
        now = self.clock()
        _require_aware(now, "Archive recall clock")
        if not is_trusted_actor_context(context):
            raise RetentionAuthorizationError("Trusted actor context is required.")
        assert context is not None
        if context.issued_at > now or context.expires_at <= now:
            raise RetentionAuthorizationError("Actor context is not currently valid.")
        if context.policy_version != self.access_policy.actor_policy_version:
            raise RetentionAuthorizationError("Actor context policy version is not accepted.")
        if context.actor_type not in self.access_policy.allowed_actor_types:
            raise RetentionAuthorizationError("Actor type cannot manage archive recall.")
        roles = sorted(context.roles.intersection(required_roles))
        if not roles:
            raise RetentionAuthorizationError(
                "Actor does not have the required archive recall role."
            )
        return context, roles[0], now

    def _prepare_audit(
        self,
        context: ActorContext,
        *,
        action: str,
        request: ArchiveRecallRequest,
        reason_code: str,
        old_status: str,
        new_values: dict[str, Any],
        occurred_at: datetime,
        audit_result: AuditResult = AuditResult.SUCCESS,
    ) -> PreparedAuditEvent:
        try:
            return self.transactional_audit.prepare(
                AuditEventInput(
                    actor_id=context.actor_id,
                    actor_type=context.actor_type.value,
                    correlation_id=context.correlation_id,
                    action=action,
                    object_type="ArchiveRecallRequest",
                    object_id=request.request_id,
                    result=audit_result,
                    reason_code=reason_code,
                    old_values={"status": old_status},
                    new_values=new_values,
                    occurred_at=occurred_at,
                    session_id=context.session_id,
                )
            )
        except Exception as exc:
            raise RetentionTechnicalError(
                "Archive recall audit event could not be prepared."
            ) from exc


def _validate_access_policy(policy: ArchiveRecallAccessPolicy) -> None:
    if not policy.version.strip() or not policy.actor_policy_version.strip():
        raise RetentionValidationError("Archive recall access policy is incomplete.")
    collections = (
        policy.request_roles,
        policy.decision_roles,
        policy.purpose_codes,
        policy.approval_reason_codes,
        policy.rejection_reason_codes,
        policy.allowed_actor_types,
    )
    if any(not values for values in collections):
        raise RetentionValidationError("Archive recall access policy is incomplete.")
    for values in collections[:-1]:
        if any(not _CODE_PATTERN.fullmatch(value) for value in values):
            raise RetentionValidationError("Archive recall policy code is invalid.")
    if any(not isinstance(value, ActorType) for value in policy.allowed_actor_types):
        raise RetentionValidationError("Archive recall actor type is invalid.")


def _validate_scope(scope_type: RetentionScopeType, scope_id: str | None) -> None:
    if scope_type is RetentionScopeType.ENTERPRISE:
        if scope_id is not None:
            raise RetentionValidationError("Enterprise recall must not have a scope ID.")
    elif scope_id is None or not scope_id.strip() or len(scope_id) > 128:
        raise RetentionValidationError("Archive recall scope ID is invalid.")


def _authorize_scope(
    context: ActorContext,
    scope_type: RetentionScopeType,
    scope_id: str | None,
) -> None:
    if scope_type is RetentionScopeType.ENTERPRISE:
        allowed = context.can_view_enterprise
    elif scope_type is RetentionScopeType.DATASET:
        allowed = scope_id in context.permitted_dataset_ids
    else:
        allowed = scope_id in context.permitted_source_ids
    if not allowed:
        raise RetentionAuthorizationError("Actor is outside the archive recall scope.")


def _authorize_stored_scope(
    context: ActorContext,
    request: ArchiveRecallRequest,
) -> None:
    if request.scope_type is RetentionScopeType.ENTERPRISE:
        if not context.can_view_enterprise:
            raise RetentionAuthorizationError("Actor is outside the archive recall scope.")
        return
    candidates = (
        context.permitted_dataset_ids
        if request.scope_type is RetentionScopeType.DATASET
        else context.permitted_source_ids
    )
    if not any(_digest_text(value) == request.scope_digest for value in candidates):
        raise RetentionAuthorizationError("Actor is outside the archive recall scope.")


def _validate_opaque_value(value: str, label: str, *, maximum: int) -> None:
    if not value.strip() or len(value) > maximum:
        raise RetentionValidationError(f"{label} is invalid.")


def _require_aware(value: datetime, label: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise RetentionValidationError(f"{label} must be timezone-aware.")


def _digest_payload(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return _digest_text(canonical)


def _digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
