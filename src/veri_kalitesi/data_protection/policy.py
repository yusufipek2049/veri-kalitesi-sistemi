"""Surumlu veri siniflandirma ve profil minimizasyon politikalari."""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Protocol

from veri_kalitesi.data_protection.errors import ClassificationValidationError


CLASSIFICATION_POLICY_VERSION = "CLASSIFICATION_POLICY_V1"
MASKING_POLICY_VERSION = "PROFILE_MASKING_POLICY_V2"
CATEGORY_FINGERPRINT_ALGORITHM = "HMAC_SHA256_V1"


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

    _TOP_LEVEL_KEYS = frozenset(
        {
            "record_count",
            "sampled_count",
            "method",
            "sample_ratio",
            "advanced_analysis",
            "analysis_execution",
        }
    )
    _FIELD_AGGREGATE_KEYS = frozenset(
        {
            "null_count",
            "null_ratio",
            "distinct_count",
            "distinct_ratio",
            "min",
            "max",
            "average",
            "type_distribution",
            "format_distribution",
            "numeric_summary",
            "outlier_candidates",
            "freshness_max",
            "distinct_measurement",
            "sampling",
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

    def __init__(
        self,
        classification_policy: ClassificationPolicy,
        *,
        category_fingerprint_key: bytes | None = None,
        category_fingerprint_key_id: str | None = None,
    ) -> None:
        self.classification_policy = classification_policy
        if (category_fingerprint_key is None) != (category_fingerprint_key_id is None):
            raise ClassificationValidationError(
                "Category fingerprint key and key id must be configured together."
            )
        if category_fingerprint_key is not None and (
            not isinstance(category_fingerprint_key, bytes) or len(category_fingerprint_key) < 32
        ):
            raise ClassificationValidationError(
                "Category fingerprint key must contain at least 32 bytes."
            )
        if category_fingerprint_key_id is not None and (
            not isinstance(category_fingerprint_key_id, str)
            or not category_fingerprint_key_id.strip()
        ):
            raise ClassificationValidationError("Category fingerprint key id is required.")
        self._category_fingerprint_key = category_fingerprint_key
        self.category_fingerprint_key_id = category_fingerprint_key_id

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
        if self._category_fingerprint_key is not None:
            protected["category_fingerprint_algorithm"] = CATEGORY_FINGERPRINT_ALGORITHM
            protected["category_fingerprint_key_id"] = self.category_fingerprint_key_id

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
                top_values = field_metrics.get("top_values")
                if isinstance(top_values, list):
                    protected_top_values = self._protect_top_values(
                        top_values,
                        field_name=field_name,
                        raw_value_eligible=decision.raw_value_eligible,
                    )
                    if protected_top_values:
                        safe_metrics["top_values"] = protected_top_values
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
        if key in {"type_distribution", "format_distribution"}:
            allowed_labels = (
                {
                    "EMPTY",
                    "BOOLEAN",
                    "INTEGER",
                    "DECIMAL",
                    "DATE",
                    "DATETIME",
                    "TEXT",
                }
                if key == "type_distribution"
                else {
                    "EMPTY",
                    "EMAIL_LIKE",
                    "ISO_DATETIME",
                    "ISO_DATE",
                    "INTEGER",
                    "DECIMAL",
                    "ALPHA",
                    "ALPHANUMERIC",
                    "OTHER",
                }
            )
            return isinstance(value, Mapping) and all(
                label in allowed_labels
                and isinstance(count, int)
                and not isinstance(count, bool)
                and count >= 0
                for label, count in value.items()
            )
        if key == "numeric_summary":
            return self._is_safe_numeric_summary(value)
        if key == "outlier_candidates":
            return isinstance(value, list) and all(self._is_safe_outlier(item) for item in value)
        if key == "freshness_max":
            if not isinstance(value, str) or len(value) > 64:
                return False
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return False
            return parsed.tzinfo is not None and parsed.utcoffset() is not None
        if key == "distinct_measurement":
            return value in {
                "EXACT",
                "BOUNDED_SAMPLE",
                "CONFIGURATION_REQUIRED",
                "SOURCE_AGGREGATE",
            }
        if key == "sampling":
            return (
                isinstance(value, Mapping)
                and set(value).issubset(
                    {
                        "strategy",
                        "seed",
                        "sample_size_limit",
                        "high_cardinality_threshold",
                        "observed_non_null_count",
                        "advanced_sample_size",
                        "advanced_sample_ratio",
                        "high_cardinality",
                        "raw_rows_transferred",
                    }
                )
                and all(
                    isinstance(item, (str, int, float, bool)) or item is None
                    for item in value.values()
                )
            )
        return False

    def _is_safe_numeric_summary(self, value: Any) -> bool:
        if not isinstance(value, Mapping):
            return False
        allowed_numeric = {
            "count",
            "min",
            "max",
            "mean",
            "median",
            "q1",
            "q3",
            "mad",
            "observed_count",
            "minimum_required",
        }
        if not set(value).issubset(allowed_numeric | {"status"}):
            return False
        return all(
            (
                name == "status"
                and item == "INSUFFICIENT_SAMPLE"
                or name in allowed_numeric
                and isinstance(item, (int, float))
                and not isinstance(item, bool)
            )
            for name, item in value.items()
        )

    def _is_safe_outlier(self, value: Any) -> bool:
        if not isinstance(value, Mapping):
            return False
        if not set(value).issubset(
            {
                "method",
                "parameters",
                "candidate_count",
                "candidate_ratio",
                "lower_bound",
                "upper_bound",
                "state",
                "result_kind",
            }
        ):
            return False
        if value.get("method") not in {"IQR", "ROBUST_Z_SCORE"}:
            return False
        if value.get("result_kind") != "OUTLIER_CANDIDATE":
            return False
        required = {
            "method",
            "parameters",
            "candidate_count",
            "candidate_ratio",
            "result_kind",
        }
        if not required.issubset(value):
            return False
        if value["method"] == "IQR" and not {"lower_bound", "upper_bound"}.issubset(value):
            return False
        if value["method"] == "ROBUST_Z_SCORE" and "state" not in value:
            return False
        if "state" in value and value["state"] not in {"EVALUATED", "ZERO_MAD"}:
            return False
        parameters = value.get("parameters")
        if not isinstance(parameters, Mapping) or not set(parameters).issubset(
            {"iqr_multiplier", "threshold"}
        ):
            return False
        numeric_keys = {
            "candidate_count",
            "candidate_ratio",
            "lower_bound",
            "upper_bound",
        }
        return all(
            isinstance(item, (int, float)) and not isinstance(item, bool)
            for name, item in value.items()
            if name in numeric_keys
        ) and all(
            isinstance(item, (int, float)) and not isinstance(item, bool)
            for item in parameters.values()
        )

    def _protect_top_values(
        self,
        values: list[Any],
        *,
        field_name: str,
        raw_value_eligible: bool,
    ) -> list[dict[str, Any]]:
        protected: list[dict[str, Any]] = []
        for item in values:
            if not isinstance(item, Mapping):
                continue
            rank = item.get("rank")
            count = item.get("count")
            if (
                not isinstance(rank, int)
                or isinstance(rank, bool)
                or rank < 1
                or not isinstance(count, int)
                or isinstance(count, bool)
                or count < 0
            ):
                continue
            entry: dict[str, Any] = {"rank": rank, "count": count}
            raw_value = item.get("value")
            if raw_value_eligible and isinstance(raw_value, str):
                entry["value"] = raw_value
                entry["masked"] = False
            else:
                entry["value"] = "***"
                entry["masked"] = True
                if isinstance(raw_value, str) and self._category_fingerprint_key is not None:
                    entry["category_fingerprint"] = hmac.new(
                        self._category_fingerprint_key,
                        f"{field_name}\0{raw_value}".encode(),
                        hashlib.sha256,
                    ).hexdigest()
            protected.append(entry)
        return protected

    def _is_safe_top_level_value(self, key: str, value: Any) -> bool:
        if key in {"record_count", "sampled_count"}:
            return isinstance(value, int) and not isinstance(value, bool) and value >= 0
        if key == "method":
            return isinstance(value, str) and value in self._PROFILE_METHODS
        if key == "sample_ratio":
            return value is None or (
                isinstance(value, (int, float)) and not isinstance(value, bool) and 0 < value <= 1
            )
        if key == "advanced_analysis":
            return (
                isinstance(value, Mapping)
                and set(value) == {"status", "reason"}
                and value.get("status") in {"RESOLVED", "CONFIGURATION_ERROR"}
                and (
                    value.get("reason") is None
                    or value.get("reason") == "ACTIVE_PROFILE_POLICY_MISSING"
                )
            )
        if key == "analysis_execution":
            return (
                isinstance(value, Mapping)
                and set(value).issubset(
                    {
                        "method",
                        "strategy",
                        "sample_size_limit",
                        "sampling_seed",
                        "query_version",
                        "raw_rows_transferred",
                    }
                )
                and all(
                    isinstance(item, (str, int, bool)) and not isinstance(item, float)
                    for item in value.values()
                )
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
