"""Surumlu veri siniflandirma ve profil minimizasyon politikalari."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol

from veri_kalitesi.data_protection.errors import ClassificationValidationError


CLASSIFICATION_POLICY_VERSION = "CLASSIFICATION_POLICY_V1"
MASKING_POLICY_VERSION = "PROFILE_MASKING_POLICY_V1"


class ClassificationCode(str, Enum):
    UNCLASSIFIED = "UNCLASSIFIED"
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    PERSONAL_DATA = "PERSONAL_DATA"
    SPECIAL_CATEGORY_PERSONAL_DATA = "SPECIAL_CATEGORY_PERSONAL_DATA"
    CUSTOMER_SECRET = "CUSTOMER_SECRET"
    BANK_SECRET = "BANK_SECRET"
    HIGHLY_RESTRICTED = "HIGHLY_RESTRICTED"


@dataclass(frozen=True)
class ClassificationDecision:
    classification: ClassificationCode
    raw_value_eligible: bool
    aggregate_metrics_allowed: bool
    reason_code: str
    policy_version: str


class ClassificationPolicy(Protocol):
    version: str

    def normalize(self, value: ClassificationCode | str | None) -> ClassificationCode:
        """Harici sinif kodunu onayli sozluge normalize et."""

    def decide(self, classification: ClassificationCode) -> ClassificationDecision:
        """Sinif icin ham ve toplulastirilmis veri kararini ver."""


class MaskingPolicy(Protocol):
    version: str

    def protect_profile_metrics(
        self,
        metrics: Mapping[str, Any],
        classifications: Mapping[str, ClassificationCode],
    ) -> dict[str, Any]:
        """Profil payloadini kalicilastirmadan once minimize et."""


class DefaultClassificationPolicy:
    version = CLASSIFICATION_POLICY_VERSION

    def normalize(self, value: ClassificationCode | str | None) -> ClassificationCode:
        if value is None or (isinstance(value, str) and not value.strip()):
            return ClassificationCode.UNCLASSIFIED
        if isinstance(value, ClassificationCode):
            return value
        try:
            return ClassificationCode(value.strip().upper())
        except (AttributeError, ValueError) as exc:
            raise ClassificationValidationError(
                "Classification must use an approved policy code."
            ) from exc

    def decide(self, classification: ClassificationCode) -> ClassificationDecision:
        raw_eligible = classification in {
            ClassificationCode.PUBLIC,
            ClassificationCode.INTERNAL,
        }
        return ClassificationDecision(
            classification=classification,
            raw_value_eligible=raw_eligible,
            aggregate_metrics_allowed=True,
            reason_code=(
                "CLASSIFICATION_ALLOWS_AUTHORIZED_RAW_REVIEW"
                if raw_eligible
                else "RAW_VALUE_DENIED_BY_CLASSIFICATION"
            ),
            policy_version=self.version,
        )


class DefaultMaskingPolicy:
    version = MASKING_POLICY_VERSION

    _TOP_LEVEL_KEYS = frozenset({"record_count", "sampled_count", "method", "sample_ratio"})
    _FIELD_AGGREGATE_KEYS = frozenset(
        {
            "null_count",
            "null_ratio",
            "distinct_count",
            "distinct_ratio",
            "min",
            "max",
            "average",
        }
    )
    _COUNT_KEYS = frozenset({"null_count", "distinct_count"})
    _NUMERIC_KEYS = frozenset({"null_ratio", "distinct_ratio", "min", "max", "average"})
    _DUPLICATE_KEYS = frozenset(
        {
            "key_fields",
            "duplicate_group_count",
            "duplicate_record_count",
            "duplicate_ratio",
        }
    )
    _PROFILE_METHODS = frozenset({"FULL", "SAMPLE", "PARTITION", "AGGREGATE"})

    def __init__(self, classification_policy: ClassificationPolicy) -> None:
        self.classification_policy = classification_policy

    def protect_profile_metrics(
        self,
        metrics: Mapping[str, Any],
        classifications: Mapping[str, ClassificationCode],
    ) -> dict[str, Any]:
        protected = {
            key: metrics[key]
            for key in self._TOP_LEVEL_KEYS
            if key in metrics and self._is_safe_top_level_value(key, metrics[key])
        }
        protected["classification_policy_version"] = self.classification_policy.version
        protected["masking_policy_version"] = self.version

        duplicates = metrics.get("duplicates")
        if isinstance(duplicates, Mapping):
            protected["duplicates"] = {
                key: duplicates[key]
                for key in self._DUPLICATE_KEYS
                if key in duplicates
                and self._is_safe_duplicate_value(key, duplicates[key], frozenset(classifications))
            }

        protected_fields: dict[str, Any] = {}
        fields = metrics.get("fields")
        if isinstance(fields, Mapping):
            for field_name, field_metrics in fields.items():
                if not isinstance(field_name, str) or not isinstance(field_metrics, Mapping):
                    continue
                classification = classifications.get(field_name, ClassificationCode.UNCLASSIFIED)
                decision = self.classification_policy.decide(classification)
                safe_metrics = {
                    key: field_metrics[key]
                    for key in self._FIELD_AGGREGATE_KEYS
                    if key in field_metrics
                    and self._is_safe_aggregate_value(key, field_metrics[key])
                }
                safe_metrics.update(
                    {
                        "classification": classification.value,
                        "raw_values_included": False,
                        "masked": not decision.raw_value_eligible,
                        "protection_reason": decision.reason_code,
                    }
                )
                protected_fields[field_name] = safe_metrics
        protected["fields"] = protected_fields
        return protected

    def _is_safe_aggregate_value(self, key: str, value: Any) -> bool:
        if key in self._COUNT_KEYS:
            return isinstance(value, int) and not isinstance(value, bool) and value >= 0
        if key in self._NUMERIC_KEYS:
            return value is None or (
                isinstance(value, (int, float)) and not isinstance(value, bool)
            )
        return False

    def _is_safe_top_level_value(self, key: str, value: Any) -> bool:
        if key in {"record_count", "sampled_count"}:
            return isinstance(value, int) and not isinstance(value, bool) and value >= 0
        if key == "method":
            return isinstance(value, str) and value in self._PROFILE_METHODS
        if key == "sample_ratio":
            return value is None or (
                isinstance(value, (int, float)) and not isinstance(value, bool) and 0 < value <= 1
            )
        return False

    def _is_safe_duplicate_value(
        self,
        key: str,
        value: Any,
        field_names: frozenset[str],
    ) -> bool:
        if key == "key_fields":
            return isinstance(value, list) and all(
                isinstance(item, str) and item in field_names for item in value
            )
        if key in {"duplicate_group_count", "duplicate_record_count"}:
            return isinstance(value, int) and not isinstance(value, bool) and value >= 0
        if key == "duplicate_ratio":
            return value is None or (
                isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value <= 1
            )
        return False
