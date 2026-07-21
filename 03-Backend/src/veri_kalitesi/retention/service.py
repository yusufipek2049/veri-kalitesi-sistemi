"""Fail-closed retention evaluation and legal hold lifecycle services."""

from __future__ import annotations

from calendar import monthrange
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Protocol
from uuid import uuid4

from veri_kalitesi.audit import (
    AuditEventInput,
    AuditResult,
    PreparedAuditEvent,
    SQLiteTransactionalAudit,
)
from veri_kalitesi.identity import ActorContext, ActorType, is_trusted_actor_context

from veri_kalitesi.retention.errors import (
    RetentionAuthorizationError,
    RetentionError,
    RetentionTechnicalError,
    RetentionValidationError,
)
from veri_kalitesi.retention.models import (
    CalendarDuration,
    DisposalMethod,
    LegalHold,
    LegalHoldAccessPolicy,
    LegalHoldEvent,
    LegalHoldEventType,
    LegalHoldTarget,
    RetentionDisposition,
    RetentionEvaluation,
    RetentionPolicy,
    RetentionPolicyCatalog,
    RetentionRecordClass,
    RetentionRecordReference,
    RetentionReviewStatus,
    RetentionScopeType,
)
from veri_kalitesi.retention.repository import SQLiteLegalHoldRepository


_CODE_PATTERN = re.compile(r"[A-Z0-9_.-]{1,120}")


class LegalHoldResolver(Protocol):
    def list_active_holds(
        self,
        record_reference: RetentionRecordReference,
        *,
        as_of: datetime,
    ) -> tuple[LegalHold, ...]: ...


class LegalHoldService:
    def __init__(
        self,
        repository: SQLiteLegalHoldRepository,
        transactional_audit: SQLiteTransactionalAudit,
        catalog: RetentionPolicyCatalog,
        access_policy: LegalHoldAccessPolicy,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        _validate_catalog(catalog)
        _validate_access_policy(access_policy)
        self.repository = repository
        self.transactional_audit = transactional_audit
        self.catalog = catalog
        self.access_policy = access_policy
        self.clock = clock
        self._policies = {policy.record_class: policy for policy in catalog.policies}

    def place_hold(
        self,
        target: LegalHoldTarget,
        *,
        reason_code: str,
        actor_context: ActorContext | None,
    ) -> LegalHold:
        _validate_target(target)
        if reason_code not in self.access_policy.placement_reason_codes:
            raise RetentionValidationError("Legal hold placement reason is not allowed.")
        context, actor_role, now = self._authorize_actor(
            actor_context,
            self.access_policy.placement_roles,
        )
        self._authorize_scope(context, target)
        policy = self._policies.get(target.record_class)
        if policy is None:
            raise RetentionValidationError("Retention policy is not defined for record class.")
        event = LegalHoldEvent(
            event_id=str(uuid4()),
            hold_reference_id=str(uuid4()),
            event_type=LegalHoldEventType.PLACED,
            record_reference_id=target.record_reference_id,
            record_class=target.record_class,
            policy_version=policy.version,
            scope_type=target.scope_type,
            scope_id=target.scope_id,
            actor_id=context.actor_id,
            actor_role=actor_role,
            reason_code=reason_code,
            created_at=now,
        )
        audit_event = self._prepare_audit(
            context,
            event,
            action="LEGAL_HOLD_PLACED",
            old_values={"status": "NONE"},
            new_values={
                "status": "ACTIVE",
                "record_class": target.record_class.value,
                "policy_version": policy.version,
                "scope_type": target.scope_type.value,
            },
        )
        try:
            stored = self.repository.place(
                event,
                audit_event=audit_event,
                audit_outbox=self.transactional_audit,
            )
        except RetentionError:
            raise
        except Exception as exc:
            raise RetentionTechnicalError("Legal hold could not be persisted.") from exc
        self.transactional_audit.publish_pending()
        return stored

    def release_hold(
        self,
        hold_reference_id: str,
        *,
        reason_code: str,
        actor_context: ActorContext | None,
    ) -> LegalHold:
        if not hold_reference_id.strip():
            raise RetentionValidationError("Legal hold reference is required.")
        if reason_code not in self.access_policy.release_reason_codes:
            raise RetentionValidationError("Legal hold release reason is not allowed.")
        context, actor_role, now = self._authorize_actor(
            actor_context,
            self.access_policy.release_roles,
        )
        try:
            hold = self.repository.get(hold_reference_id)
        except RetentionError:
            raise
        except (sqlite3.Error, OSError) as exc:
            raise RetentionTechnicalError("Legal hold could not be read.") from exc
        if hold.released_at is not None:
            raise RetentionValidationError("Legal hold is already released.")
        if hold.scope_type is None:
            raise RetentionValidationError("Legal hold scope is invalid.")
        target = LegalHoldTarget(
            record_reference_id=hold.record_reference_id,
            record_class=hold.record_class,
            scope_type=hold.scope_type,
            scope_id=hold.scope_id,
        )
        self._authorize_scope(context, target)
        if context.actor_id == hold.placed_by_actor_id:
            raise RetentionAuthorizationError(
                "Legal hold must be released by a different authorized actor."
            )
        event = LegalHoldEvent(
            event_id=str(uuid4()),
            hold_reference_id=hold.hold_reference_id,
            event_type=LegalHoldEventType.RELEASED,
            record_reference_id=hold.record_reference_id,
            record_class=hold.record_class,
            policy_version=hold.policy_version,
            scope_type=target.scope_type,
            scope_id=target.scope_id,
            actor_id=context.actor_id,
            actor_role=actor_role,
            reason_code=reason_code,
            created_at=now,
        )
        audit_event = self._prepare_audit(
            context,
            event,
            action="LEGAL_HOLD_RELEASED",
            old_values={"status": "ACTIVE", "policy_version": hold.policy_version},
            new_values={"status": "RELEASED", "policy_version": hold.policy_version},
        )
        try:
            stored = self.repository.release(
                event,
                audit_event=audit_event,
                audit_outbox=self.transactional_audit,
            )
        except RetentionError:
            raise
        except Exception as exc:
            raise RetentionTechnicalError("Legal hold release could not be persisted.") from exc
        self.transactional_audit.publish_pending()
        return stored

    def _authorize_actor(
        self,
        context: ActorContext | None,
        required_roles: frozenset[str],
    ) -> tuple[ActorContext, str, datetime]:
        now = self.clock()
        _require_aware(now, "Legal hold clock")
        if not is_trusted_actor_context(context):
            raise RetentionAuthorizationError("Trusted actor context is required.")
        assert context is not None
        if context.issued_at > now or context.expires_at <= now:
            raise RetentionAuthorizationError("Actor context is not currently valid.")
        if context.policy_version != self.access_policy.actor_policy_version:
            raise RetentionAuthorizationError("Actor context policy version is not accepted.")
        if context.actor_type not in self.access_policy.allowed_actor_types:
            raise RetentionAuthorizationError("Actor type cannot manage legal holds.")
        matching_roles = sorted(context.roles.intersection(required_roles))
        if not matching_roles:
            raise RetentionAuthorizationError("Actor does not have a legal hold role.")
        return context, matching_roles[0], now

    @staticmethod
    def _authorize_scope(context: ActorContext, target: LegalHoldTarget) -> None:
        if not _has_scope(context, target):
            raise RetentionAuthorizationError("Actor is outside the legal hold scope.")

    def _prepare_audit(
        self,
        context: ActorContext,
        event: LegalHoldEvent,
        *,
        action: str,
        old_values: dict[str, Any],
        new_values: dict[str, Any],
    ) -> PreparedAuditEvent:
        try:
            return self.transactional_audit.prepare(
                AuditEventInput(
                    actor_id=context.actor_id,
                    actor_type=context.actor_type.value,
                    correlation_id=context.correlation_id,
                    action=action,
                    object_type="LegalHold",
                    object_id=event.hold_reference_id,
                    result=AuditResult.SUCCESS,
                    reason_code=event.reason_code,
                    old_values=old_values,
                    new_values=new_values,
                    occurred_at=event.created_at,
                    session_id=context.session_id,
                )
            )
        except Exception as exc:
            raise RetentionTechnicalError("Legal hold audit event could not be prepared.") from exc


class RetentionEvaluator:
    def __init__(
        self,
        catalog: RetentionPolicyCatalog,
        legal_hold_resolver: LegalHoldResolver,
    ) -> None:
        _validate_catalog(catalog)
        self.catalog = catalog
        self.legal_hold_resolver = legal_hold_resolver
        self._policies = {policy.record_class: policy for policy in catalog.policies}

    def evaluate(
        self,
        record_reference: RetentionRecordReference,
        *,
        as_of: datetime,
    ) -> RetentionEvaluation:
        _validate_record_reference(record_reference)
        _require_aware(as_of, "Retention evaluation time")
        policy = self._policies.get(record_reference.record_class)
        if policy is None:
            raise RetentionValidationError("Retention policy is not defined for record class.")
        retention_until = add_calendar_duration(
            record_reference.retention_trigger_at,
            policy.duration,
        )
        try:
            holds = self.legal_hold_resolver.list_active_holds(
                record_reference,
                as_of=as_of,
            )
        except RetentionValidationError:
            raise
        except Exception as exc:
            raise RetentionTechnicalError("Legal hold status could not be resolved.") from exc
        _validate_holds(holds, record_reference, policy, as_of)
        if holds:
            disposition = RetentionDisposition.LEGAL_HOLD
        elif as_of < retention_until:
            disposition = RetentionDisposition.RETAIN
        elif policy.review_status is not RetentionReviewStatus.APPROVED_BY_BANK:
            disposition = RetentionDisposition.COMPLIANCE_REVIEW_REQUIRED
        else:
            disposition = RetentionDisposition.ELIGIBLE_FOR_DISPOSAL
        return RetentionEvaluation(
            record_reference_id=record_reference.record_reference_id,
            record_class=record_reference.record_class,
            policy_code=policy.code,
            policy_version=policy.version,
            retention_until=retention_until,
            disposition=disposition,
            legal_hold_count=len(holds),
        )


def provisional_retention_catalog() -> RetentionPolicyCatalog:
    version = "RETENTION_POLICY_2026_07_PROVISIONAL_V1"
    review = RetentionReviewStatus.COMPLIANCE_REVIEW_REQUIRED
    return RetentionPolicyCatalog(
        version=version,
        maximum_disposal_interval_days=180,
        policies=(
            RetentionPolicy(
                code="RET-10Y-BANKING",
                record_class=RetentionRecordClass.BANKING_RECORD,
                duration=CalendarDuration(years=10),
                disposal_method=DisposalMethod.CONTROLLED_DESTRUCTION,
                version=version,
                review_status=review,
            ),
            RetentionPolicy(
                code="RET-5Y-REGLOG",
                record_class=RetentionRecordClass.REGULATORY_LOG,
                duration=CalendarDuration(years=5),
                disposal_method=DisposalMethod.CONTROLLED_DESTRUCTION,
                version=version,
                review_status=review,
            ),
            RetentionPolicy(
                code="RET-3Y-ERASURE",
                record_class=RetentionRecordClass.ERASURE_EVIDENCE,
                duration=CalendarDuration(years=3),
                disposal_method=DisposalMethod.CONTROLLED_DESTRUCTION,
                version=version,
                review_status=review,
            ),
            RetentionPolicy(
                code="RET-1Y-OPS",
                record_class=RetentionRecordClass.OPERATIONAL_RECORD,
                duration=CalendarDuration(years=1),
                disposal_method=DisposalMethod.SECURE_DELETION,
                version=version,
                review_status=review,
            ),
            RetentionPolicy(
                code="RET-90D-TRANSIENT",
                record_class=RetentionRecordClass.TRANSIENT_RECORD,
                duration=CalendarDuration(days=90),
                disposal_method=DisposalMethod.SECURE_DELETION,
                version=version,
                review_status=review,
            ),
            RetentionPolicy(
                code="RET-30D-EXPORT",
                record_class=RetentionRecordClass.EXPORT_ARTIFACT,
                duration=CalendarDuration(days=30),
                disposal_method=DisposalMethod.CRYPTOGRAPHIC_ERASURE,
                version=version,
                review_status=review,
            ),
        ),
    )


def add_calendar_duration(start_at: datetime, duration: CalendarDuration) -> datetime:
    _require_aware(start_at, "Retention trigger time")
    _validate_duration(duration)
    target_year = start_at.year + duration.years
    target_day = min(start_at.day, monthrange(target_year, start_at.month)[1])
    return start_at.replace(year=target_year, day=target_day) + timedelta(days=duration.days)


def _validate_catalog(catalog: RetentionPolicyCatalog) -> None:
    if not catalog.version.strip():
        raise RetentionValidationError("Retention catalog version is required.")
    if not 1 <= catalog.maximum_disposal_interval_days <= 180:
        raise RetentionValidationError("Disposal interval must be between 1 and 180 days.")
    if not catalog.policies:
        raise RetentionValidationError("Retention catalog must contain policies.")
    record_classes = [policy.record_class for policy in catalog.policies]
    if len(record_classes) != len(set(record_classes)):
        raise RetentionValidationError("Retention record classes must be unique.")
    for policy in catalog.policies:
        if not policy.code.strip() or policy.version != catalog.version:
            raise RetentionValidationError("Retention policy identity is invalid.")
        if policy.review_status is RetentionReviewStatus.APPROVED_BY_BANK and (
            policy.approval_reference is None or not policy.approval_reference.strip()
        ):
            raise RetentionValidationError("Approved retention policy requires approval evidence.")
        _validate_duration(policy.duration)


def _validate_access_policy(policy: LegalHoldAccessPolicy) -> None:
    values = (
        policy.version,
        policy.actor_policy_version,
    )
    collections = (
        policy.placement_roles,
        policy.release_roles,
        policy.placement_reason_codes,
        policy.release_reason_codes,
    )
    if (
        any(not value.strip() for value in values)
        or any(not items for items in collections)
        or not policy.allowed_actor_types
    ):
        raise RetentionValidationError("Legal hold access policy is incomplete.")
    if any(not _CODE_PATTERN.fullmatch(value) for items in collections for value in items):
        raise RetentionValidationError("Legal hold access policy code is invalid.")
    if any(not isinstance(actor_type, ActorType) for actor_type in policy.allowed_actor_types):
        raise RetentionValidationError("Legal hold actor type is invalid.")


def _validate_target(target: LegalHoldTarget) -> None:
    if not target.record_reference_id.strip() or len(target.record_reference_id) > 128:
        raise RetentionValidationError("Opaque record reference is invalid.")
    if target.scope_type is RetentionScopeType.ENTERPRISE:
        if target.scope_id is not None:
            raise RetentionValidationError("Enterprise legal hold must not have a scope ID.")
    elif target.scope_id is None or not target.scope_id.strip():
        raise RetentionValidationError("Legal hold scope ID is required.")


def _has_scope(context: ActorContext, target: LegalHoldTarget) -> bool:
    if target.scope_type is RetentionScopeType.ENTERPRISE:
        return context.can_view_enterprise
    if target.scope_type is RetentionScopeType.DATASET:
        return target.scope_id in context.permitted_dataset_ids
    return target.scope_id in context.permitted_source_ids


def _validate_duration(duration: CalendarDuration) -> None:
    if (
        isinstance(duration.years, bool)
        or isinstance(duration.days, bool)
        or not isinstance(duration.years, int)
        or not isinstance(duration.days, int)
        or duration.years < 0
        or duration.days < 0
        or (duration.years == 0 and duration.days == 0)
    ):
        raise RetentionValidationError("Retention duration must be a positive calendar period.")


def _validate_record_reference(record_reference: RetentionRecordReference) -> None:
    if not record_reference.record_reference_id.strip():
        raise RetentionValidationError("Opaque record reference is required.")
    _require_aware(record_reference.retention_trigger_at, "Retention trigger time")


def _validate_holds(
    holds: tuple[LegalHold, ...],
    record_reference: RetentionRecordReference,
    policy: RetentionPolicy,
    as_of: datetime,
) -> None:
    for hold in holds:
        _require_aware(hold.effective_at, "Legal hold effective time")
        if hold.released_at is not None:
            _require_aware(hold.released_at, "Legal hold release time")
        if (
            not hold.hold_reference_id.strip()
            or not hold.decision_owner_role.strip()
            or hold.record_reference_id != record_reference.record_reference_id
            or hold.record_class is not record_reference.record_class
            or hold.policy_version != policy.version
            or hold.effective_at > as_of
            or hold.released_at is not None
        ):
            raise RetentionValidationError("Legal hold resolver returned an invalid active hold.")


def _require_aware(value: datetime, label: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise RetentionValidationError(f"{label} must be timezone-aware.")
