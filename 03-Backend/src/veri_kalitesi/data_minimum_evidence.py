"""Veri-minimum ihlal kanıtı ve güvenli opaque referans doğrulaması."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


class DataMinimumEvidenceError(ValueError):
    """Kanıt sözleşmesi güvenli ve sınırlı biçime uymadığında üretilir."""


_REFERENCE_MAX_LENGTH = 200
_REFERENCE_SEGMENT = r"[A-Za-z0-9](?:[A-Za-z0-9._~-]{0,62}[A-Za-z0-9])?"
_REFERENCE_PATH_PATTERN = re.compile(
    rf"^(?:{_REFERENCE_SEGMENT})(?:/{_REFERENCE_SEGMENT})*$"
)
_HMAC_REFERENCE_PATTERN = re.compile(
    rf"^hmac-sha256://{_REFERENCE_SEGMENT}/[0-9a-f]{{64}}$"
)
_SHA256_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_FORBIDDEN_REFERENCE_TERMS = {
    "alter",
    "api",
    "authorization",
    "bind",
    "create",
    "credential",
    "delete",
    "drop",
    "explain",
    "from",
    "insert",
    "password",
    "secret",
    "select",
    "sql",
    "token",
    "union",
    "update",
    "where",
}
_EVIDENCE_FIELDS = {
    "fingerprint",
    "masked_samples",
    "expected_summary",
    "actual_summary",
    "query_reference",
    "plan_reference",
}
_AGGREGATE_COUNTERS = {
    "population_count",
    "eligible_count",
    "evaluated_count",
    "passed_count",
    "failed_count",
    "excluded_count",
    "technical_error_count",
    "unknown_count",
}
_MAX_COUNTER_VALUE = 9_223_372_036_854_775_807
_MAX_MASKED_SAMPLES = 10


def validate_query_reference(value: Any) -> str:
    return _validate_opaque_reference(value, "query-template://")


def validate_plan_reference(value: Any) -> str:
    return _validate_opaque_reference(value, "plan://")


def validate_violation_evidence(
    evidence: Mapping[str, Any],
    *,
    required: bool,
) -> dict[str, Any]:
    if not isinstance(evidence, Mapping):
        raise DataMinimumEvidenceError("Violation evidence fields are invalid.")
    if not evidence:
        if required:
            raise DataMinimumEvidenceError("Violation evidence is required.")
        return {}
    if set(evidence) != _EVIDENCE_FIELDS:
        raise DataMinimumEvidenceError("Violation evidence fields are invalid.")

    fingerprint = _validate_fingerprint(evidence["fingerprint"])
    samples = _validate_masked_samples(evidence["masked_samples"])
    expected = _validate_aggregate_summary(evidence["expected_summary"])
    actual = _validate_aggregate_summary(evidence["actual_summary"])
    query_reference = validate_query_reference(evidence["query_reference"])
    plan_reference = validate_plan_reference(evidence["plan_reference"])
    return {
        "fingerprint": fingerprint,
        "masked_samples": samples,
        "expected_summary": expected,
        "actual_summary": actual,
        "query_reference": query_reference,
        "plan_reference": plan_reference,
    }


def _validate_opaque_reference(value: Any, scheme: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) > _REFERENCE_MAX_LENGTH
        or not value.startswith(scheme)
    ):
        raise DataMinimumEvidenceError("Evidence reference format is invalid.")
    path = value[len(scheme) :]
    if not _REFERENCE_PATH_PATTERN.fullmatch(path):
        raise DataMinimumEvidenceError("Evidence reference format is invalid.")
    terms = {
        term
        for segment in path.lower().split("/")
        for term in re.split(r"[._~-]+", segment)
    }
    if terms & _FORBIDDEN_REFERENCE_TERMS:
        raise DataMinimumEvidenceError("Evidence reference format is invalid.")
    return value


def _validate_fingerprint(value: Any) -> str:
    if not isinstance(value, str) or not (
        _SHA256_DIGEST_PATTERN.fullmatch(value)
        or _HMAC_REFERENCE_PATTERN.fullmatch(value)
    ):
        raise DataMinimumEvidenceError("Evidence fingerprint format is invalid.")
    return value


def _validate_masked_samples(value: Any) -> list[str]:
    if (
        not isinstance(value, tuple | list)
        or len(value) > _MAX_MASKED_SAMPLES
        or any(
            not isinstance(item, str) or not _HMAC_REFERENCE_PATTERN.fullmatch(item)
            for item in value
        )
    ):
        raise DataMinimumEvidenceError("Evidence sample references are invalid.")
    return list(value)


def _validate_aggregate_summary(value: Any) -> dict[str, int]:
    if (
        not isinstance(value, Mapping)
        or not value
        or len(value) > len(_AGGREGATE_COUNTERS)
        or not set(value).issubset(_AGGREGATE_COUNTERS)
        or any(
            isinstance(count, bool)
            or not isinstance(count, int)
            or count < 0
            or count > _MAX_COUNTER_VALUE
            for count in value.values()
        )
    ):
        raise DataMinimumEvidenceError("Evidence aggregate summary is invalid.")
    return {str(name): int(count) for name, count in value.items()}
