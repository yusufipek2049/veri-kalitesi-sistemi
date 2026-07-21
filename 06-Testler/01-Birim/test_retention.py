from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from veri_kalitesi.retention import (
    LegalHold,
    RetentionDisposition,
    RetentionEvaluator,
    RetentionPolicyCatalog,
    RetentionRecordClass,
    RetentionRecordReference,
    RetentionReviewStatus,
    RetentionTechnicalError,
    RetentionValidationError,
    add_calendar_duration,
    provisional_retention_catalog,
)


UTC = timezone.utc
TRIGGER_AT = datetime(2020, 2, 29, 12, 0, tzinfo=UTC)
AS_OF = datetime(2030, 3, 1, 12, 0, tzinfo=UTC)


class FakeLegalHoldResolver:
    def __init__(self, holds: tuple[LegalHold, ...] = (), error: Exception | None = None) -> None:
        self.holds = holds
        self.error = error

    def list_active_holds(
        self,
        record_reference: RetentionRecordReference,
        *,
        as_of: datetime,
    ) -> tuple[LegalHold, ...]:
        if self.error is not None:
            raise self.error
        return self.holds


def test_bfr_lcm_001_provisional_catalog_uses_record_specific_calendar_periods() -> None:
    catalog = provisional_retention_catalog()

    assert catalog.maximum_disposal_interval_days == 180
    assert {policy.code for policy in catalog.policies} == {
        "RET-10Y-BANKING",
        "RET-5Y-REGLOG",
        "RET-3Y-ERASURE",
        "RET-1Y-OPS",
        "RET-90D-TRANSIENT",
        "RET-30D-EXPORT",
    }
    assert all(
        policy.review_status is RetentionReviewStatus.COMPLIANCE_REVIEW_REQUIRED
        for policy in catalog.policies
    )
    banking = next(
        policy
        for policy in catalog.policies
        if policy.record_class is RetentionRecordClass.BANKING_RECORD
    )
    assert add_calendar_duration(TRIGGER_AT, banking.duration) == datetime(
        2030, 2, 28, 12, 0, tzinfo=UTC
    )


def test_bfr_lcm_001_record_is_retained_before_policy_deadline() -> None:
    evaluator = RetentionEvaluator(provisional_retention_catalog(), FakeLegalHoldResolver())

    result = evaluator.evaluate(
        _record(RetentionRecordClass.BANKING_RECORD),
        as_of=datetime(2030, 2, 27, 12, 0, tzinfo=UTC),
    )

    assert result.disposition is RetentionDisposition.RETAIN
    assert result.policy_code == "RET-10Y-BANKING"
    assert result.legal_hold_count == 0


def test_nfr_cmp_001_due_provisional_policy_never_authorizes_disposal() -> None:
    evaluator = RetentionEvaluator(provisional_retention_catalog(), FakeLegalHoldResolver())

    result = evaluator.evaluate(
        _record(RetentionRecordClass.BANKING_RECORD),
        as_of=AS_OF,
    )

    assert result.disposition is RetentionDisposition.COMPLIANCE_REVIEW_REQUIRED


def test_bfr_lcm_002_active_legal_hold_blocks_approved_policy() -> None:
    catalog = _approved_catalog(RetentionRecordClass.BANKING_RECORD)
    record = _record(RetentionRecordClass.BANKING_RECORD)
    hold = LegalHold(
        hold_reference_id="hold-ref-1",
        record_reference_id=record.record_reference_id,
        record_class=record.record_class,
        policy_version=catalog.version,
        decision_owner_role="LEGAL_HOLD_AUTHORITY",
        effective_at=datetime(2029, 1, 1, tzinfo=UTC),
    )
    evaluator = RetentionEvaluator(catalog, FakeLegalHoldResolver((hold,)))

    result = evaluator.evaluate(record, as_of=AS_OF)

    assert result.disposition is RetentionDisposition.LEGAL_HOLD
    assert result.legal_hold_count == 1


def test_bfr_lcm_001_approved_due_record_is_only_marked_eligible() -> None:
    evaluator = RetentionEvaluator(
        _approved_catalog(RetentionRecordClass.BANKING_RECORD),
        FakeLegalHoldResolver(),
    )

    result = evaluator.evaluate(
        _record(RetentionRecordClass.BANKING_RECORD),
        as_of=AS_OF,
    )

    assert result.disposition is RetentionDisposition.ELIGIBLE_FOR_DISPOSAL
    assert not hasattr(evaluator, "delete")
    assert not hasattr(evaluator, "archive")


def test_nfr_cmp_001_approved_policy_requires_approval_evidence() -> None:
    catalog = provisional_retention_catalog()
    policy = replace(
        catalog.policies[0],
        review_status=RetentionReviewStatus.APPROVED_BY_BANK,
    )

    with pytest.raises(RetentionValidationError, match="approval evidence"):
        RetentionEvaluator(
            replace(catalog, policies=(policy, *catalog.policies[1:])),
            FakeLegalHoldResolver(),
        )


@pytest.mark.parametrize(
    "record",
    [
        RetentionRecordReference(
            record_reference_id=" ",
            record_class=RetentionRecordClass.BANKING_RECORD,
            retention_trigger_at=TRIGGER_AT,
        ),
        RetentionRecordReference(
            record_reference_id="record-ref-1",
            record_class=RetentionRecordClass.BANKING_RECORD,
            retention_trigger_at=datetime(2020, 1, 1),
        ),
    ],
)
def test_bfr_lcm_001_invalid_record_metadata_fails_closed(
    record: RetentionRecordReference,
) -> None:
    evaluator = RetentionEvaluator(provisional_retention_catalog(), FakeLegalHoldResolver())

    with pytest.raises(RetentionValidationError):
        evaluator.evaluate(record, as_of=AS_OF)


def test_bfr_lcm_002_legal_hold_resolver_failure_is_technical_error() -> None:
    evaluator = RetentionEvaluator(
        provisional_retention_catalog(),
        FakeLegalHoldResolver(error=RuntimeError("synthetic resolver outage")),
    )

    with pytest.raises(RetentionTechnicalError, match="could not be resolved"):
        evaluator.evaluate(_record(RetentionRecordClass.BANKING_RECORD), as_of=AS_OF)


def _record(record_class: RetentionRecordClass) -> RetentionRecordReference:
    return RetentionRecordReference(
        record_reference_id="opaque-record-ref-1",
        record_class=record_class,
        retention_trigger_at=TRIGGER_AT,
    )


def _approved_catalog(record_class: RetentionRecordClass) -> RetentionPolicyCatalog:
    catalog = provisional_retention_catalog()
    policies = tuple(
        replace(
            policy,
            review_status=RetentionReviewStatus.APPROVED_BY_BANK,
            approval_reference="synthetic-bank-approval-reference",
        )
        if policy.record_class is record_class
        else policy
        for policy in catalog.policies
    )
    return replace(catalog, policies=policies)
