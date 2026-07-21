"""Fail-closed, read-only retention eligibility evaluation."""

from __future__ import annotations

from calendar import monthrange
from datetime import datetime, timedelta
from typing import Protocol

from veri_kalitesi.retention.errors import RetentionTechnicalError, RetentionValidationError
from veri_kalitesi.retention.models import (
    CalendarDuration,
    DisposalMethod,
    LegalHold,
    RetentionDisposition,
    RetentionEvaluation,
    RetentionPolicy,
    RetentionPolicyCatalog,
    RetentionRecordClass,
    RetentionRecordReference,
    RetentionReviewStatus,
)


class LegalHoldResolver(Protocol):
    def list_active_holds(
        self,
        record_reference: RetentionRecordReference,
        *,
        as_of: datetime,
    ) -> tuple[LegalHold, ...]: ...


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
