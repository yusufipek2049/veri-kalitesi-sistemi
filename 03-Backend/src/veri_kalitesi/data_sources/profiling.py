"""DQ-CAP-001/002/006 deterministik profil ve drift çekirdeği."""

from __future__ import annotations

import math
import re
from hashlib import sha256
from heapq import heappush, heapreplace
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from statistics import median
from typing import Any, Protocol, TypeGuard

from veri_kalitesi.data_sources.errors import ValidationError
from veri_kalitesi.data_sources.models import (
    DataField,
    DataProfile,
    OutlierMethod,
    ProfileAnalysisPolicy,
    ProfileComparison,
    ProfileComparisonStatus,
    ProfileMethod,
    ProfilePolicyResolutionStatus,
    ProfileSamplingStrategy,
    ProfileStatus,
)

PROFILE_SNAPSHOT_VERSION = "DQ_PROFILE_SNAPSHOT_V1"

_INTEGER_PATTERN = re.compile(r"^[+-]?\d+$")
_DECIMAL_PATTERN = re.compile(r"^[+-]?(?:\d+\.\d*|\d*\.\d+)$")
_ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ISO_DATETIME_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?$"
)


class ProfilePolicyResolver(Protocol):
    def resolve(self, version: str | None = None) -> ProfileAnalysisPolicy | None: ...


class InMemoryProfilePolicyResolver:
    """Test/prototip composition root'u için açık sürüm seçen resolver."""

    def __init__(
        self,
        policies: Sequence[ProfileAnalysisPolicy] = (),
        *,
        active_version: str | None = None,
    ) -> None:
        self._policies = {policy.version: policy for policy in policies}
        self._active_version = active_version
        for policy in policies:
            validate_profile_policy(policy)
        if active_version is not None and active_version not in self._policies:
            raise ValidationError("Active profile policy version could not be resolved.")

    def resolve(self, version: str | None = None) -> ProfileAnalysisPolicy | None:
        selected = version or self._active_version
        return self._policies.get(selected) if selected is not None else None


def validate_profile_policy(policy: ProfileAnalysisPolicy) -> None:
    if not policy.version or not policy.version.strip():
        raise ValidationError("Profile policy version is required.")
    if (
        isinstance(policy.top_n_limit, bool)
        or not isinstance(policy.top_n_limit, int)
        or policy.top_n_limit < 1
    ):
        raise ValidationError("Profile policy top_n_limit must be positive.")
    if (
        isinstance(policy.high_cardinality_threshold, bool)
        or not isinstance(policy.high_cardinality_threshold, int)
        or policy.high_cardinality_threshold < 1
        or isinstance(policy.advanced_sample_size, bool)
        or not isinstance(policy.advanced_sample_size, int)
        or policy.advanced_sample_size < policy.top_n_limit
        or policy.high_cardinality_threshold > policy.advanced_sample_size
        or policy.sampling_strategy is not ProfileSamplingStrategy.DETERMINISTIC_HASH
        or isinstance(policy.sampling_seed, bool)
        or not isinstance(policy.sampling_seed, int)
        or policy.sampling_seed < 0
    ):
        raise ValidationError("Profile policy sampling strategy and limits are invalid.")
    if not policy.enabled_outlier_methods or len(set(policy.enabled_outlier_methods)) != len(
        policy.enabled_outlier_methods
    ):
        raise ValidationError("Profile policy outlier methods must be non-empty and unique.")
    if any(not isinstance(method, OutlierMethod) for method in policy.enabled_outlier_methods):
        raise ValidationError("Profile policy contains an unsupported outlier method.")
    if (
        not _positive_number(policy.iqr_multiplier)
        or not _positive_number(policy.robust_z_score_threshold)
        or isinstance(policy.minimum_numeric_sample, bool)
        or not isinstance(policy.minimum_numeric_sample, int)
        or policy.minimum_numeric_sample < 1
        or isinstance(policy.comparison_window, bool)
        or not isinstance(policy.comparison_window, int)
        or policy.comparison_window < 1
        or isinstance(policy.minimum_history, bool)
        or not isinstance(policy.minimum_history, int)
        or policy.minimum_history < 2
        or policy.minimum_history > policy.comparison_window
    ):
        raise ValidationError("Profile policy statistical and history parameters are invalid.")
    for value in (
        policy.volume_ratio_threshold,
        policy.null_ratio_delta_threshold,
        policy.distinct_ratio_delta_threshold,
        policy.category_loss_ratio_threshold,
        policy.numeric_mean_ratio_threshold,
        policy.numeric_median_ratio_threshold,
        policy.freshness_delay_seconds_threshold,
    ):
        if not _non_negative_number(value):
            raise ValidationError("Profile policy drift thresholds must be non-negative.")
    if not isinstance(policy.schema_change_detection_enabled, bool):
        raise ValidationError("Profile policy schema change flag must be boolean.")
    if any(
        not isinstance(name, str) or not name or not name.strip() or name != name.strip()
        for name in policy.freshness_field_names
    ) or len(set(policy.freshness_field_names)) != len(policy.freshness_field_names):
        raise ValidationError(
            "Profile policy freshness field names must be non-blank, normalized and unique."
        )


def validate_freshness_field_scope(
    policy: ProfileAnalysisPolicy | None,
    fields: Sequence[DataField],
    *,
    selected_field_names: Sequence[str] = (),
) -> None:
    """Politika kapsamındaki freshness alanlarını metadata/yürütme kapsamına bağla."""

    if policy is None or not policy.freshness_field_names:
        return
    available = {field.name for field in fields}
    if set(policy.freshness_field_names) - available:
        raise ValidationError("Profile policy freshness fields must exist in metadata.")
    if selected_field_names and set(policy.freshness_field_names) - set(selected_field_names):
        raise ValidationError(
            "Profile policy freshness fields must be included in the profile field scope."
        )


def infer_value_type(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        return "EMPTY"
    lowered = normalized.lower()
    if lowered in {"true", "false"}:
        return "BOOLEAN"
    if _INTEGER_PATTERN.fullmatch(normalized):
        return "INTEGER"
    if _DECIMAL_PATTERN.fullmatch(normalized):
        return "DECIMAL"
    if _ISO_DATE_PATTERN.fullmatch(normalized):
        return "DATE"
    if _ISO_DATETIME_PATTERN.fullmatch(normalized):
        return "DATETIME"
    return "TEXT"


def infer_format(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        return "EMPTY"
    if "@" in normalized and "." in normalized.rsplit("@", 1)[-1]:
        return "EMAIL_LIKE"
    if _ISO_DATETIME_PATTERN.fullmatch(normalized):
        return "ISO_DATETIME"
    if _ISO_DATE_PATTERN.fullmatch(normalized):
        return "ISO_DATE"
    if _INTEGER_PATTERN.fullmatch(normalized):
        return "INTEGER"
    if _DECIMAL_PATTERN.fullmatch(normalized):
        return "DECIMAL"
    if normalized.isalpha():
        return "ALPHA"
    if normalized.isalnum():
        return "ALPHANUMERIC"
    return "OTHER"


def build_advanced_field_metrics(
    values: Sequence[str],
    numeric_values: Sequence[float],
    policy: ProfileAnalysisPolicy,
) -> dict[str, Any]:
    """Ham değerleri yalnız çağrı ömründe kullanıp saklanabilir toplulaştırma üretir."""

    type_counts = Counter(infer_value_type(value) for value in values)
    format_counts = Counter(infer_format(value) for value in values)
    top_values = sorted(Counter(values).items(), key=lambda item: (-item[1], item[0]))[
        : policy.top_n_limit
    ]
    result: dict[str, Any] = {
        "type_distribution": dict(sorted(type_counts.items())),
        "format_distribution": dict(sorted(format_counts.items())),
        "top_values": [
            {"rank": rank, "value": value, "count": count}
            for rank, (value, count) in enumerate(top_values, start=1)
        ],
    }
    if len(numeric_values) >= policy.minimum_numeric_sample:
        ordered = sorted(float(value) for value in numeric_values)
        numeric_summary = {
            "count": len(ordered),
            "min": ordered[0],
            "max": ordered[-1],
            "mean": sum(ordered) / len(ordered),
            "median": median(ordered),
            "q1": _quantile(ordered, 0.25),
            "q3": _quantile(ordered, 0.75),
        }
        numeric_summary["mad"] = median(
            [abs(value - numeric_summary["median"]) for value in ordered]
        )
        result["numeric_summary"] = numeric_summary
        result["outlier_candidates"] = _outlier_candidates(ordered, numeric_summary, policy)
    else:
        result["numeric_summary"] = {
            "status": "INSUFFICIENT_SAMPLE",
            "observed_count": len(numeric_values),
            "minimum_required": policy.minimum_numeric_sample,
        }
        result["outlier_candidates"] = []
    return result


class BoundedDeterministicSample:
    """Politika boyutunu aşmadan yeniden üretilebilir satır örneği tutar."""

    def __init__(self, *, field_name: str, policy: ProfileAnalysisPolicy) -> None:
        self._field_name = field_name
        self._policy = policy
        self._heap: list[tuple[int, int, str]] = []
        self.observed_count = 0

    def add(self, value: str, *, row_index: int) -> None:
        self.observed_count += 1
        digest = sha256(
            f"{self._policy.sampling_seed}:{self._field_name}:{row_index}".encode()
        ).digest()
        score = int.from_bytes(digest[:16], "big")
        item = (-score, -row_index, value)
        if len(self._heap) < self._policy.advanced_sample_size:
            heappush(self._heap, item)
        elif item > self._heap[0]:
            heapreplace(self._heap, item)

    def values(self) -> list[str]:
        return [item[2] for item in sorted(self._heap, reverse=True)]

    def evidence(self) -> dict[str, Any]:
        sample_size = len(self._heap)
        return {
            "strategy": self._policy.sampling_strategy.value,
            "seed": self._policy.sampling_seed,
            "sample_size_limit": self._policy.advanced_sample_size,
            "high_cardinality_threshold": self._policy.high_cardinality_threshold,
            "observed_non_null_count": self.observed_count,
            "advanced_sample_size": sample_size,
            "advanced_sample_ratio": (
                sample_size / self.observed_count if self.observed_count else None
            ),
            "high_cardinality": (self.observed_count > self._policy.high_cardinality_threshold),
        }


def build_profile_contract(
    *,
    fields: Sequence[DataField],
    method: ProfileMethod,
    sample_ratio: float | None,
    scope: Mapping[str, Any],
    query_version: str,
    connector_version: str,
    policy: ProfileAnalysisPolicy | None,
    data_observed_at: datetime | None,
    category_fingerprint_algorithm: str | None,
    category_fingerprint_key_id: str | None,
    analysis_execution: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "snapshot_version": PROFILE_SNAPSHOT_VERSION,
        "policy_resolution_status": (
            ProfilePolicyResolutionStatus.RESOLVED.value
            if policy is not None
            else ProfilePolicyResolutionStatus.MISSING.value
        ),
        "policy_version": policy.version if policy is not None else None,
        "method": method.value,
        "sample_ratio": sample_ratio,
        "scope": dict(scope),
        "query_version": query_version,
        "connector_version": connector_version,
        "category_fingerprint_algorithm": category_fingerprint_algorithm,
        "category_fingerprint_key_id": category_fingerprint_key_id,
        "freshness_field_names": (
            sorted(policy.freshness_field_names) if policy is not None else []
        ),
        "data_observed_at": (
            data_observed_at.astimezone(timezone.utc).isoformat()
            if data_observed_at is not None
            else None
        ),
        "analysis_execution": dict(analysis_execution or {}),
        "schema": {
            field.name: {
                "native_data_type": field.native_data_type,
                "is_nullable": field.is_nullable,
            }
            for field in sorted(fields, key=lambda item: item.name)
        },
    }


def compare_profile_snapshots(
    *,
    baseline: DataProfile,
    current: DataProfile,
    history: Sequence[DataProfile],
    policy: ProfileAnalysisPolicy | None,
) -> ProfileComparison:
    if baseline.dataset_id != current.dataset_id:
        raise ValidationError("Profile comparison requires the same dataset.")
    if policy is None:
        return ProfileComparison(
            dataset_id=current.dataset_id,
            baseline_profile_id=baseline.profile_id,
            current_profile_id=current.profile_id,
            status=ProfileComparisonStatus.CONFIGURATION_ERROR,
            result={
                "configuration_error": "ACTIVE_PROFILE_POLICY_MISSING",
                "signals": [
                    _schema_signal(
                        baseline.metrics.get("profile_contract"),
                        current.metrics.get("profile_contract"),
                        verdict_enabled=False,
                    )
                ],
            },
            message="Anomaly verdict was not produced because profile policy is missing.",
        )
    validate_profile_policy(policy)
    baseline_contract = baseline.metrics.get("profile_contract")
    current_contract = current.metrics.get("profile_contract")
    if _masked_categories_present(baseline, current) and (
        not _fingerprint_contract_configured(baseline_contract)
        or not _fingerprint_contract_configured(current_contract)
    ):
        return ProfileComparison(
            dataset_id=current.dataset_id,
            baseline_profile_id=baseline.profile_id,
            current_profile_id=current.profile_id,
            status=ProfileComparisonStatus.CONFIGURATION_ERROR,
            policy_version=policy.version,
            result={
                "configuration_error": "CATEGORY_FINGERPRINT_KEY_UNAVAILABLE",
                "signals": [],
            },
            message=(
                "Anomaly verdict was not produced because persistent category "
                "fingerprint configuration is unavailable."
            ),
        )
    compatible = [
        profile
        for profile in history
        if profile.dataset_id == current.dataset_id
        and profile.status in {ProfileStatus.COMPLETED, ProfileStatus.NO_DATA}
        and _compatible_contracts(
            profile.metrics.get("profile_contract"),
            current_contract,
            policy,
        )
    ]
    window = compatible[-policy.comparison_window :]
    if len(window) < policy.minimum_history:
        return _non_verdict(
            baseline,
            current,
            policy,
            ProfileComparisonStatus.INSUFFICIENT_HISTORY,
            "MINIMUM_COMPATIBLE_HISTORY_NOT_MET",
        )
    if baseline not in window or current not in window:
        return _non_verdict(
            baseline,
            current,
            policy,
            ProfileComparisonStatus.INCOMPATIBLE,
            "PROFILE_OUTSIDE_POLICY_WINDOW",
        )
    if not _compatible_contracts(baseline_contract, current_contract, policy):
        return _non_verdict(
            baseline,
            current,
            policy,
            ProfileComparisonStatus.INCOMPATIBLE,
            "PROFILE_CONTRACTS_INCOMPATIBLE",
        )

    signals: list[dict[str, Any]] = []
    _append_ratio_signal(
        signals,
        "VOLUME_CHANGE",
        baseline.metrics.get("record_count"),
        current.metrics.get("record_count"),
        policy.volume_ratio_threshold,
    )
    baseline_fields = _mapping(baseline.metrics.get("fields"))
    current_fields = _mapping(current.metrics.get("fields"))
    for field_name in sorted(set(baseline_fields) & set(current_fields)):
        before = _mapping(baseline_fields[field_name])
        after = _mapping(current_fields[field_name])
        _append_delta_signal(
            signals,
            "NULL_RATIO_CHANGE",
            field_name,
            before.get("null_ratio"),
            after.get("null_ratio"),
            policy.null_ratio_delta_threshold,
        )
        _append_delta_signal(
            signals,
            "DISTINCT_RATIO_CHANGE",
            field_name,
            before.get("distinct_ratio"),
            after.get("distinct_ratio"),
            policy.distinct_ratio_delta_threshold,
        )
        _append_category_signal(signals, field_name, before, after, policy)
        _append_numeric_signals(signals, field_name, before, after, policy)
        if field_name in policy.freshness_field_names:
            _append_freshness_signal(signals, field_name, before, after, policy)
    if policy.schema_change_detection_enabled:
        signals.append(_schema_signal(baseline_contract, current_contract))
    return ProfileComparison(
        dataset_id=current.dataset_id,
        baseline_profile_id=baseline.profile_id,
        current_profile_id=current.profile_id,
        status=ProfileComparisonStatus.COMPLETED,
        policy_version=policy.version,
        anomaly_candidate=any(signal.get("breached") is True for signal in signals),
        result={"signals": signals},
        message="Deterministic profile comparison completed.",
    )


def _outlier_candidates(
    values: Sequence[float],
    summary: Mapping[str, Any],
    policy: ProfileAnalysisPolicy,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for method in policy.enabled_outlier_methods:
        if method is OutlierMethod.IQR:
            iqr = float(summary["q3"]) - float(summary["q1"])
            lower = float(summary["q1"]) - policy.iqr_multiplier * iqr
            upper = float(summary["q3"]) + policy.iqr_multiplier * iqr
            count = sum(value < lower or value > upper for value in values)
            candidates.append(
                {
                    "method": method.value,
                    "parameters": {"iqr_multiplier": policy.iqr_multiplier},
                    "candidate_count": count,
                    "candidate_ratio": count / len(values),
                    "lower_bound": lower,
                    "upper_bound": upper,
                    "result_kind": "OUTLIER_CANDIDATE",
                }
            )
        elif method is OutlierMethod.ROBUST_Z_SCORE:
            mad = float(summary["mad"])
            center = float(summary["median"])
            if mad == 0:
                count = 0
                state = "ZERO_MAD"
            else:
                count = sum(
                    abs(0.6745 * (value - center) / mad) > policy.robust_z_score_threshold
                    for value in values
                )
                state = "EVALUATED"
            candidates.append(
                {
                    "method": method.value,
                    "parameters": {
                        "threshold": policy.robust_z_score_threshold,
                    },
                    "candidate_count": count,
                    "candidate_ratio": count / len(values),
                    "state": state,
                    "result_kind": "OUTLIER_CANDIDATE",
                }
            )
    return candidates


def _non_verdict(
    baseline: DataProfile,
    current: DataProfile,
    policy: ProfileAnalysisPolicy,
    status: ProfileComparisonStatus,
    reason: str,
) -> ProfileComparison:
    return ProfileComparison(
        dataset_id=current.dataset_id,
        baseline_profile_id=baseline.profile_id,
        current_profile_id=current.profile_id,
        status=status,
        policy_version=policy.version,
        anomaly_candidate=None,
        result={"reason": reason, "signals": []},
        message="Anomaly verdict was not produced.",
    )


def _compatible_contracts(
    baseline: Any,
    current: Any,
    policy: ProfileAnalysisPolicy,
) -> bool:
    if not isinstance(baseline, Mapping) or not isinstance(current, Mapping):
        return False
    keys = (
        "snapshot_version",
        "method",
        "sample_ratio",
        "scope",
        "query_version",
        "connector_version",
        "category_fingerprint_algorithm",
        "category_fingerprint_key_id",
        "freshness_field_names",
    )
    return (
        all(baseline.get(key) == current.get(key) for key in keys)
        and baseline.get("policy_version") == policy.version
        and current.get("policy_version") == policy.version
    )


def _masked_categories_present(*profiles: DataProfile) -> bool:
    for profile in profiles:
        fields = profile.metrics.get("fields")
        if not isinstance(fields, Mapping):
            continue
        for field in fields.values():
            if not isinstance(field, Mapping):
                continue
            top_values = field.get("top_values")
            if isinstance(top_values, list) and any(
                isinstance(item, Mapping) and item.get("masked") is True for item in top_values
            ):
                return True
    return False


def _fingerprint_contract_configured(contract: Any) -> bool:
    return (
        isinstance(contract, Mapping)
        and isinstance(contract.get("category_fingerprint_algorithm"), str)
        and bool(contract["category_fingerprint_algorithm"].strip())
        and isinstance(contract.get("category_fingerprint_key_id"), str)
        and bool(contract["category_fingerprint_key_id"].strip())
    )


def _append_ratio_signal(
    signals: list[dict[str, Any]],
    kind: str,
    baseline: Any,
    current: Any,
    threshold: float,
) -> None:
    if not _number(baseline) or not _number(current):
        return
    if float(baseline) == 0:
        change = None
        breached = float(current) != 0
    else:
        change = abs(float(current) - float(baseline)) / abs(float(baseline))
        breached = change > threshold
    signals.append(
        {
            "kind": kind,
            "baseline": baseline,
            "current": current,
            "absolute_ratio_change": change,
            "threshold": threshold,
            "breached": breached,
            "result_kind": "ANOMALY_CANDIDATE",
        }
    )


def _append_delta_signal(
    signals: list[dict[str, Any]],
    kind: str,
    field_name: str,
    baseline: Any,
    current: Any,
    threshold: float,
) -> None:
    if not _number(baseline) or not _number(current):
        return
    delta = abs(float(current) - float(baseline))
    signals.append(
        {
            "kind": kind,
            "field": field_name,
            "absolute_delta": delta,
            "threshold": threshold,
            "breached": delta > threshold,
            "result_kind": "ANOMALY_CANDIDATE",
        }
    )


def _append_category_signal(
    signals: list[dict[str, Any]],
    field_name: str,
    baseline: Mapping[str, Any],
    current: Mapping[str, Any],
    policy: ProfileAnalysisPolicy,
) -> None:
    before = _top_value_set(baseline.get("top_values"))
    after = _top_value_set(current.get("top_values"))
    if before is None or after is None:
        return
    loss_ratio = len(before - after) / len(before) if before else 0.0
    signals.append(
        {
            "kind": "CATEGORY_LOSS",
            "field": field_name,
            "baseline_category_count": len(before),
            "lost_category_count": len(before - after),
            "loss_ratio": loss_ratio,
            "threshold": policy.category_loss_ratio_threshold,
            "breached": loss_ratio > policy.category_loss_ratio_threshold,
            "result_kind": "ANOMALY_CANDIDATE",
        }
    )


def _append_numeric_signals(
    signals: list[dict[str, Any]],
    field_name: str,
    baseline: Mapping[str, Any],
    current: Mapping[str, Any],
    policy: ProfileAnalysisPolicy,
) -> None:
    before = _mapping(baseline.get("numeric_summary"))
    after = _mapping(current.get("numeric_summary"))
    for metric, threshold, kind in (
        ("mean", policy.numeric_mean_ratio_threshold, "NUMERIC_MEAN_CHANGE"),
        ("median", policy.numeric_median_ratio_threshold, "NUMERIC_MEDIAN_CHANGE"),
    ):
        before_value = before.get(metric)
        after_value = after.get(metric)
        if not _number(before_value) or not _number(after_value):
            continue
        denominator = abs(float(before_value))
        ratio = abs(float(after_value) - float(before_value)) / denominator if denominator else None
        signals.append(
            {
                "kind": kind,
                "field": field_name,
                "absolute_ratio_change": ratio,
                "threshold": threshold,
                "breached": float(after_value) != 0 if ratio is None else ratio > threshold,
                "result_kind": "ANOMALY_CANDIDATE",
            }
        )


def _append_freshness_signal(
    signals: list[dict[str, Any]],
    field_name: str,
    baseline: Mapping[str, Any],
    current: Mapping[str, Any],
    policy: ProfileAnalysisPolicy,
) -> None:
    before = _parse_time(baseline.get("freshness_max"))
    after = _parse_time(current.get("freshness_max"))
    if before is None or after is None:
        return
    delay = max(0.0, (before - after).total_seconds())
    signals.append(
        {
            "kind": "FRESHNESS_DELAY",
            "field": field_name,
            "delay_seconds": delay,
            "threshold": policy.freshness_delay_seconds_threshold,
            "breached": delay > policy.freshness_delay_seconds_threshold,
            "result_kind": "ANOMALY_CANDIDATE",
        }
    )


def _schema_signal(
    baseline_contract: Any,
    current_contract: Any,
    *,
    verdict_enabled: bool = True,
) -> dict[str, Any]:
    before = _mapping(_mapping(baseline_contract).get("schema"))
    after = _mapping(_mapping(current_contract).get("schema"))
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    changed = sorted(name for name in set(before) & set(after) if before[name] != after[name])
    signal: dict[str, Any] = {
        "kind": "SCHEMA_CHANGE",
        "added_fields": added,
        "removed_fields": removed,
        "changed_fields": changed,
    }
    if verdict_enabled:
        signal.update(
            {
                "breached": bool(added or removed or changed),
                "result_kind": "ANOMALY_CANDIDATE",
            }
        )
    return signal


def _top_value_set(value: Any) -> set[str] | None:
    if not isinstance(value, list):
        return None
    result: set[str] = set()
    for item in value:
        if not isinstance(item, Mapping):
            return None
        if item.get("masked") is True:
            fingerprint = item.get("category_fingerprint")
            if not isinstance(fingerprint, str) or not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
                return None
            result.add(fingerprint)
            continue
        raw = item.get("value")
        if not isinstance(raw, str):
            return None
        result.add(raw)
    return result


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None and parsed.utcoffset() is not None else None


def _quantile(values: Sequence[float], probability: float) -> float:
    position = (len(values) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return values[lower]
    fraction = position - lower
    return values[lower] * (1 - fraction) + values[upper] * fraction


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _number(value: Any) -> TypeGuard[int | float]:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _positive_number(value: Any) -> bool:
    return _number(value) and value > 0


def _non_negative_number(value: Any) -> bool:
    return _number(value) and value >= 0
