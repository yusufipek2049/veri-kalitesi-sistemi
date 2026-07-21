"""Fail-closed disposal job preparation and result evidence service."""

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
from veri_kalitesi.retention.disposal_repository import SQLiteDisposalJobRepository
from veri_kalitesi.retention.errors import (
    RetentionAuthorizationError,
    RetentionConflictError,
    RetentionError,
    RetentionTechnicalError,
    RetentionValidationError,
)
from veri_kalitesi.retention.models import (
    DisposalJob,
    DisposalJobAccessPolicy,
    DisposalJobResult,
    DisposalJobStatus,
    LegalHoldTarget,
    RetentionDisposition,
    RetentionPolicy,
    RetentionRecordReference,
    RetentionScopeType,
)
from veri_kalitesi.retention.service import RetentionEvaluator, _has_scope, _require_aware


_REFERENCE_PATTERN = re.compile(r"[A-Z0-9_.:-]{1,160}")


class DisposalJobService:
    """Records disposal intent and evidence without invoking a destructive adapter."""

    def __init__(
        self,
        repository: SQLiteDisposalJobRepository,
        transactional_audit: SQLiteTransactionalAudit,
        evaluator: RetentionEvaluator,
        access_policy: DisposalJobAccessPolicy,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        _validate_access_policy(access_policy)
        self.repository = repository
        self.transactional_audit = transactional_audit
        self.evaluator = evaluator
        self.access_policy = access_policy
        self.clock = clock

    def prepare_job(
        self,
        record_reference: RetentionRecordReference,
        *,
        scope_type: RetentionScopeType,
        scope_id: str | None,
        approval_reference: str,
        reason_code: str,
        idempotency_key: str,
        actor_context: ActorContext | None,
    ) -> DisposalJob:
        _validate_record_reference(record_reference)
        context, actor_role, now = self._authorize(
            actor_context,
            required_roles=self.access_policy.preparation_roles,
            allowed_actor_types=self.access_policy.allowed_preparer_types,
        )
        target = LegalHoldTarget(
            record_reference_id=record_reference.record_reference_id,
            record_class=record_reference.record_class,
            scope_type=scope_type,
            scope_id=scope_id,
        )
        _validate_scope(target)
        if not _has_scope(context, target):
            raise RetentionAuthorizationError("Actor is outside the disposal scope.")
        _validate_reference(approval_reference, "Disposal approval reference")
        _validate_idempotency_key(idempotency_key)
        if reason_code not in self.access_policy.preparation_reason_codes:
            raise RetentionValidationError("Disposal preparation reason is not allowed.")

        policy = self._policy_for(record_reference)
        idempotency_digest = _digest_text(idempotency_key)
        payload_digest = _payload_digest(
            record_reference,
            scope_type=scope_type,
            scope_id=scope_id,
            approval_reference=approval_reference,
            reason_code=reason_code,
            policy_code=policy.code,
            policy_version=policy.version,
            disposal_method=policy.disposal_method.value,
        )
        try:
            existing = self.repository.get_by_idempotency_digest(idempotency_digest)
        except RetentionError:
            raise
        except Exception as exc:
            raise RetentionTechnicalError("Disposal idempotency state could not be read.") from exc
        if existing is not None:
            if existing.payload_digest != payload_digest:
                raise RetentionConflictError(
                    "Disposal idempotency key was reused with a different payload."
                )
            self.transactional_audit.publish_pending()
            return existing

        evaluation = self.evaluator.evaluate(record_reference, as_of=now)
        if evaluation.disposition is not RetentionDisposition.ELIGIBLE_FOR_DISPOSAL:
            raise RetentionValidationError(
                f"Disposal is not authorized by retention evaluation: "
                f"{evaluation.disposition.value}."
            )
        job = DisposalJob(
            job_id=str(uuid4()),
            idempotency_key_digest=idempotency_digest,
            payload_digest=payload_digest,
            record_reference_digest=_digest_text(record_reference.record_reference_id),
            record_class=record_reference.record_class,
            policy_code=evaluation.policy_code,
            policy_version=evaluation.policy_version,
            disposal_method=policy.disposal_method,
            scope_type=scope_type,
            scope_digest=_digest_text(scope_id) if scope_id is not None else None,
            approval_reference=approval_reference,
            reason_code=reason_code,
            prepared_by_actor_id=context.actor_id,
            prepared_by_role=actor_role,
            prepared_at=now,
        )
        audit_event = self._prepare_audit(
            context,
            action="DISPOSAL_JOB_PREPARED",
            job=job,
            audit_result=AuditResult.SUCCESS,
            occurred_at=now,
            old_status="NONE",
            new_values={
                "status": job.status.value,
                "record_class": job.record_class.value,
                "policy_version": job.policy_version,
                "disposal_method": job.disposal_method.value,
                "scope_type": job.scope_type.value,
            },
        )
        try:
            stored = self.repository.create(
                job,
                audit_event=audit_event,
                audit_outbox=self.transactional_audit,
            )
        except RetentionError:
            raise
        except Exception as exc:
            raise RetentionTechnicalError("Disposal job could not be persisted.") from exc
        self.transactional_audit.publish_pending()
        return stored

    def record_result(
        self,
        job_id: str,
        record_reference: RetentionRecordReference,
        *,
        status: DisposalJobStatus,
        affected_record_count: int,
        failed_record_count: int,
        evidence_reference: str,
        technical_error_code: str | None,
        actor_context: ActorContext | None,
    ) -> DisposalJob:
        context, actor_role, now = self._authorize(
            actor_context,
            required_roles=self.access_policy.result_roles,
            allowed_actor_types=self.access_policy.allowed_result_actor_types,
        )
        if not job_id.strip():
            raise RetentionValidationError("Disposal job ID is required.")
        _validate_reference(evidence_reference, "Disposal evidence reference")
        _validate_result(
            status,
            affected_record_count=affected_record_count,
            failed_record_count=failed_record_count,
            technical_error_code=technical_error_code,
            allowed_error_codes=self.access_policy.technical_error_codes,
        )
        try:
            job = self.repository.get(job_id)
        except RetentionError:
            raise
        except Exception as exc:
            raise RetentionTechnicalError("Disposal job could not be read.") from exc
        if context.actor_id == job.prepared_by_actor_id:
            raise RetentionAuthorizationError(
                "Disposal result must be recorded by a different trusted actor."
            )
        target = LegalHoldTarget(
            record_reference_id=record_reference.record_reference_id,
            record_class=record_reference.record_class,
            scope_type=job.scope_type,
            scope_id=None,
        )
        if job.scope_type is not RetentionScopeType.ENTERPRISE:
            raise_if_scope_digest_missing(job.scope_digest)
            target = LegalHoldTarget(
                record_reference_id=record_reference.record_reference_id,
                record_class=record_reference.record_class,
                scope_type=job.scope_type,
                scope_id=_matching_scope_id(context, job.scope_type, job.scope_digest),
            )
        if not _has_scope(context, target):
            raise RetentionAuthorizationError("Actor is outside the disposal scope.")
        self._validate_job_identity(job, record_reference)

        result_digest = _result_digest(
            status=status,
            affected_record_count=affected_record_count,
            failed_record_count=failed_record_count,
            evidence_reference=evidence_reference,
            technical_error_code=technical_error_code,
        )
        if job.result is not None:
            if job.result.result_digest != result_digest:
                raise RetentionConflictError(
                    "Disposal job already has a different terminal result."
                )
            self.transactional_audit.publish_pending()
            return job

        evaluation = self.evaluator.evaluate(record_reference, as_of=now)
        if evaluation.disposition is not RetentionDisposition.ELIGIBLE_FOR_DISPOSAL:
            raise RetentionValidationError(
                f"Disposal result cannot be recorded after retention evaluation: "
                f"{evaluation.disposition.value}."
            )
        policy = self._policy_for(record_reference)
        if (
            evaluation.policy_code != job.policy_code
            or evaluation.policy_version != job.policy_version
            or policy.disposal_method is not job.disposal_method
        ):
            raise RetentionValidationError("Disposal job policy is no longer current.")

        result = DisposalJobResult(
            result_id=str(uuid4()),
            job_id=job.job_id,
            status=status,
            affected_record_count=affected_record_count,
            failed_record_count=failed_record_count,
            evidence_reference=evidence_reference,
            technical_error_code=technical_error_code,
            result_digest=result_digest,
            recorded_by_actor_id=context.actor_id,
            recorded_by_role=actor_role,
            recorded_at=now,
        )
        audit_event = self._prepare_audit(
            context,
            action="DISPOSAL_JOB_RESULT_RECORDED",
            job=job,
            audit_result=(
                AuditResult.SUCCESS
                if status is DisposalJobStatus.SUCCEEDED
                else AuditResult.FAILURE
            ),
            occurred_at=now,
            old_status=job.status.value,
            new_values={
                "status": status.value,
                "disposal_method": job.disposal_method.value,
                "affected_record_count": affected_record_count,
                "failed_record_count": failed_record_count,
                "technical_error_code": technical_error_code,
            },
        )
        try:
            stored = self.repository.record_result(
                result,
                audit_event=audit_event,
                audit_outbox=self.transactional_audit,
            )
        except RetentionError:
            raise
        except Exception as exc:
            raise RetentionTechnicalError("Disposal result could not be persisted.") from exc
        self.transactional_audit.publish_pending()
        return stored

    def _authorize(
        self,
        context: ActorContext | None,
        *,
        required_roles: frozenset[str],
        allowed_actor_types: frozenset[ActorType],
    ) -> tuple[ActorContext, str, datetime]:
        now = self.clock()
        _require_aware(now, "Disposal clock")
        if not is_trusted_actor_context(context):
            raise RetentionAuthorizationError("Trusted actor context is required.")
        assert context is not None
        if context.issued_at > now or context.expires_at <= now:
            raise RetentionAuthorizationError("Actor context is not currently valid.")
        if context.policy_version != self.access_policy.actor_policy_version:
            raise RetentionAuthorizationError("Actor context policy version is not accepted.")
        if context.actor_type not in allowed_actor_types:
            raise RetentionAuthorizationError("Actor type cannot perform this disposal action.")
        roles = sorted(context.roles.intersection(required_roles))
        if not roles:
            raise RetentionAuthorizationError("Actor does not have the required disposal role.")
        return context, roles[0], now

    def _policy_for(self, record_reference: RetentionRecordReference) -> RetentionPolicy:
        for policy in self.evaluator.catalog.policies:
            if policy.record_class is record_reference.record_class:
                return policy
        raise RetentionValidationError("Retention policy is not defined for record class.")

    @staticmethod
    def _validate_job_identity(
        job: DisposalJob,
        record_reference: RetentionRecordReference,
    ) -> None:
        if (
            job.record_class is not record_reference.record_class
            or job.record_reference_digest != _digest_text(record_reference.record_reference_id)
        ):
            raise RetentionValidationError("Disposal job record reference does not match.")

    def _prepare_audit(
        self,
        context: ActorContext,
        *,
        action: str,
        job: DisposalJob,
        audit_result: AuditResult,
        occurred_at: datetime,
        old_status: str,
        new_values: dict[str, Any],
    ) -> PreparedAuditEvent:
        try:
            return self.transactional_audit.prepare(
                AuditEventInput(
                    actor_id=context.actor_id,
                    actor_type=context.actor_type.value,
                    correlation_id=context.correlation_id,
                    action=action,
                    object_type="DisposalJob",
                    object_id=job.job_id,
                    result=audit_result,
                    reason_code=job.reason_code,
                    old_values={"status": old_status},
                    new_values=new_values,
                    occurred_at=occurred_at,
                    session_id=context.session_id,
                )
            )
        except Exception as exc:
            raise RetentionTechnicalError("Disposal audit event could not be prepared.") from exc


def _validate_access_policy(policy: DisposalJobAccessPolicy) -> None:
    collections = (
        policy.preparation_roles,
        policy.result_roles,
        policy.preparation_reason_codes,
        policy.technical_error_codes,
        policy.allowed_preparer_types,
        policy.allowed_result_actor_types,
    )
    if (
        not policy.version.strip()
        or not policy.actor_policy_version.strip()
        or any(not values for values in collections)
    ):
        raise RetentionValidationError("Disposal access policy is incomplete.")
    for values in (
        policy.preparation_roles,
        policy.result_roles,
        policy.preparation_reason_codes,
        policy.technical_error_codes,
    ):
        if any(not _REFERENCE_PATTERN.fullmatch(value) for value in values):
            raise RetentionValidationError("Disposal access policy code is invalid.")


def _validate_scope(target: LegalHoldTarget) -> None:
    if target.scope_type is RetentionScopeType.ENTERPRISE:
        if target.scope_id is not None:
            raise RetentionValidationError("Enterprise disposal must not have a scope ID.")
    elif target.scope_id is None or not target.scope_id.strip():
        raise RetentionValidationError("Disposal scope ID is required.")


def _validate_record_reference(record_reference: RetentionRecordReference) -> None:
    if (
        not record_reference.record_reference_id.strip()
        or len(record_reference.record_reference_id) > 128
    ):
        raise RetentionValidationError("Opaque record reference is invalid.")
    _require_aware(record_reference.retention_trigger_at, "Retention trigger time")


def _validate_reference(value: str, label: str) -> None:
    if not _REFERENCE_PATTERN.fullmatch(value):
        raise RetentionValidationError(f"{label} is invalid.")


def _validate_idempotency_key(value: str) -> None:
    if not value.strip() or len(value) > 256:
        raise RetentionValidationError("Disposal idempotency key is invalid.")


def _validate_result(
    status: DisposalJobStatus,
    *,
    affected_record_count: int,
    failed_record_count: int,
    technical_error_code: str | None,
    allowed_error_codes: frozenset[str],
) -> None:
    if status not in {DisposalJobStatus.SUCCEEDED, DisposalJobStatus.FAILED_TECHNICAL}:
        raise RetentionValidationError("Disposal result must be terminal.")
    counts = (affected_record_count, failed_record_count)
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in counts):
        raise RetentionValidationError("Disposal result counts must be non-negative integers.")
    if status is DisposalJobStatus.SUCCEEDED:
        if failed_record_count != 0 or technical_error_code is not None:
            raise RetentionValidationError("Successful disposal result cannot contain failures.")
    elif technical_error_code not in allowed_error_codes:
        raise RetentionValidationError("Disposal technical error code is not allowed.")


def _matching_scope_id(
    context: ActorContext,
    scope_type: RetentionScopeType,
    scope_digest: str | None,
) -> str:
    candidates = (
        context.permitted_dataset_ids
        if scope_type is RetentionScopeType.DATASET
        else context.permitted_source_ids
    )
    matches = [value for value in candidates if _digest_text(value) == scope_digest]
    if len(matches) != 1:
        raise RetentionAuthorizationError("Actor is outside the disposal scope.")
    return matches[0]


def raise_if_scope_digest_missing(scope_digest: str | None) -> None:
    if scope_digest is None:
        raise RetentionValidationError("Disposal job scope digest is missing.")


def _payload_digest(
    record_reference: RetentionRecordReference,
    *,
    scope_type: RetentionScopeType,
    scope_id: str | None,
    approval_reference: str,
    reason_code: str,
    policy_code: str,
    policy_version: str,
    disposal_method: str,
) -> str:
    return _digest_payload(
        {
            "record_reference_digest": _digest_text(record_reference.record_reference_id),
            "record_class": record_reference.record_class.value,
            "retention_trigger_at": record_reference.retention_trigger_at.isoformat(),
            "scope_type": scope_type.value,
            "scope_digest": _digest_text(scope_id) if scope_id is not None else None,
            "approval_reference": approval_reference,
            "reason_code": reason_code,
            "policy_code": policy_code,
            "policy_version": policy_version,
            "disposal_method": disposal_method,
        }
    )


def _result_digest(
    *,
    status: DisposalJobStatus,
    affected_record_count: int,
    failed_record_count: int,
    evidence_reference: str,
    technical_error_code: str | None,
) -> str:
    return _digest_payload(
        {
            "status": status.value,
            "affected_record_count": affected_record_count,
            "failed_record_count": failed_record_count,
            "evidence_reference": evidence_reference,
            "technical_error_code": technical_error_code,
        }
    )


def _digest_payload(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return _digest_text(canonical)


def _digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
