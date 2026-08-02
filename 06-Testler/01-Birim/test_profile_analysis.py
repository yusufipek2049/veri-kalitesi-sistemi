from datetime import datetime, timezone

from veri_kalitesi.data_sources import (
    DataProfile,
    OutlierMethod,
    ProfileAnalysisPolicy,
    ProfileComparisonStatus,
    ProfileMethod,
    ProfileStatus,
    ProfileSamplingStrategy,
)
from veri_kalitesi.data_sources.profiling import compare_profile_snapshots


def test_dq_cap_006_compares_all_deterministic_signal_families() -> None:
    policy = ProfileAnalysisPolicy(
        version="DRIFT_POLICY_TEST_V1",
        top_n_limit=3,
        high_cardinality_threshold=4,
        advanced_sample_size=8,
        sampling_strategy=ProfileSamplingStrategy.DETERMINISTIC_HASH,
        sampling_seed=20260729,
        enabled_outlier_methods=(OutlierMethod.IQR,),
        iqr_multiplier=1.5,
        robust_z_score_threshold=3.5,
        minimum_numeric_sample=4,
        comparison_window=2,
        minimum_history=2,
        volume_ratio_threshold=0.1,
        null_ratio_delta_threshold=0.1,
        distinct_ratio_delta_threshold=0.1,
        category_loss_ratio_threshold=0.3,
        numeric_mean_ratio_threshold=0.1,
        numeric_median_ratio_threshold=0.1,
        freshness_delay_seconds_threshold=60,
        schema_change_detection_enabled=True,
        freshness_field_names=("amount",),
    )
    baseline = _profile(
        "profile-1",
        policy.version,
        record_count=100,
        null_ratio=0.05,
        distinct_ratio=0.8,
        categories=("A", "B"),
        mean=10,
        median_value=10,
        freshness="2026-07-20T12:00:00+00:00",
        schema={"amount": {"native_data_type": "NUMERIC", "is_nullable": True}},
    )
    current = _profile(
        "profile-2",
        policy.version,
        record_count=70,
        null_ratio=0.25,
        distinct_ratio=0.5,
        categories=("B",),
        mean=15,
        median_value=15,
        freshness="2026-07-20T11:00:00+00:00",
        schema={
            "amount": {"native_data_type": "NUMERIC", "is_nullable": False},
            "new_field": {"native_data_type": "TEXT", "is_nullable": True},
        },
    )

    comparison = compare_profile_snapshots(
        baseline=baseline,
        current=current,
        history=(baseline, current),
        policy=policy,
    )

    assert comparison.status is ProfileComparisonStatus.COMPLETED
    assert comparison.anomaly_candidate is True
    signals = {signal["kind"]: signal for signal in comparison.result["signals"]}
    assert {
        "VOLUME_CHANGE",
        "NULL_RATIO_CHANGE",
        "DISTINCT_RATIO_CHANGE",
        "CATEGORY_LOSS",
        "NUMERIC_MEAN_CHANGE",
        "NUMERIC_MEDIAN_CHANGE",
        "FRESHNESS_DELAY",
        "SCHEMA_CHANGE",
    } <= set(signals)
    assert signals["CATEGORY_LOSS"]["lost_category_count"] == 1
    assert signals["SCHEMA_CHANGE"]["added_fields"] == ["new_field"]
    assert signals["SCHEMA_CHANGE"]["changed_fields"] == ["amount"]
    assert all(signal["result_kind"] == "ANOMALY_CANDIDATE" for signal in signals.values())


def test_dq_cap_006_rejects_different_connector_versions() -> None:
    policy = ProfileAnalysisPolicy(
        version="DRIFT_POLICY_TEST_V1",
        top_n_limit=3,
        high_cardinality_threshold=4,
        advanced_sample_size=8,
        sampling_strategy=ProfileSamplingStrategy.DETERMINISTIC_HASH,
        sampling_seed=20260729,
        enabled_outlier_methods=(OutlierMethod.IQR,),
        iqr_multiplier=1.5,
        robust_z_score_threshold=3.5,
        minimum_numeric_sample=4,
        comparison_window=2,
        minimum_history=2,
        volume_ratio_threshold=0.1,
        null_ratio_delta_threshold=0.1,
        distinct_ratio_delta_threshold=0.1,
        category_loss_ratio_threshold=0.3,
        numeric_mean_ratio_threshold=0.1,
        numeric_median_ratio_threshold=0.1,
        freshness_delay_seconds_threshold=60,
        schema_change_detection_enabled=True,
    )
    baseline = _profile(
        "profile-1",
        policy.version,
        record_count=100,
        null_ratio=0.0,
        distinct_ratio=0.5,
        categories=("A",),
        mean=10,
        median_value=10,
        freshness="2026-07-20T12:00:00+00:00",
        schema={"amount": {"native_data_type": "NUMERIC", "is_nullable": True}},
    )
    current = _profile(
        "profile-2",
        policy.version,
        record_count=100,
        null_ratio=0.0,
        distinct_ratio=0.5,
        categories=("A",),
        mean=10,
        median_value=10,
        freshness="2026-07-20T12:00:00+00:00",
        schema={"amount": {"native_data_type": "NUMERIC", "is_nullable": True}},
        connector_version="CONNECTOR_V2",
    )

    comparison = compare_profile_snapshots(
        baseline=baseline,
        current=current,
        history=(baseline, current),
        policy=policy,
    )

    assert comparison.status is ProfileComparisonStatus.INSUFFICIENT_HISTORY
    assert comparison.anomaly_candidate is None
    assert comparison.result["reason"] == "MINIMUM_COMPATIBLE_HISTORY_NOT_MET"


def test_fr_021_missing_policy_preserves_schema_evidence_without_drift_verdict() -> None:
    baseline = _profile(
        "profile-1",
        "MISSING_POLICY_V1",
        record_count=100,
        null_ratio=0.0,
        distinct_ratio=0.5,
        categories=("A",),
        mean=10,
        median_value=10,
        freshness="2026-07-20T12:00:00+00:00",
        schema={
            "amount": {"native_data_type": "NUMERIC", "is_nullable": True},
            "removed_field": {"native_data_type": "TEXT", "is_nullable": True},
        },
    )
    current = _profile(
        "profile-2",
        "MISSING_POLICY_V1",
        record_count=50,
        null_ratio=0.5,
        distinct_ratio=0.1,
        categories=("B",),
        mean=20,
        median_value=20,
        freshness="2026-07-20T10:00:00+00:00",
        schema={
            "amount": {"native_data_type": "BIGINT", "is_nullable": False},
            "added_field": {"native_data_type": "TEXT", "is_nullable": False},
        },
    )

    comparison = compare_profile_snapshots(
        baseline=baseline,
        current=current,
        history=(baseline, current),
        policy=None,
    )

    assert comparison.status is ProfileComparisonStatus.CONFIGURATION_ERROR
    assert comparison.anomaly_candidate is None
    assert comparison.result["configuration_error"] == "ACTIVE_PROFILE_POLICY_MISSING"
    assert comparison.result["signals"] == [
        {
            "kind": "SCHEMA_CHANGE",
            "added_fields": ["added_field"],
            "removed_fields": ["removed_field"],
            "changed_fields": ["amount"],
        }
    ]


def test_dq_cap_006_incompatible_history_cannot_satisfy_minimum_history() -> None:
    policy = _policy(comparison_window=3, minimum_history=3)
    baseline = _profile(
        "profile-compatible-baseline",
        policy.version,
        record_count=100,
        null_ratio=0.0,
        distinct_ratio=0.5,
        categories=("A",),
        mean=10,
        median_value=10,
        freshness="2026-07-20T12:00:00+00:00",
        schema={"amount": {"native_data_type": "NUMERIC", "is_nullable": True}},
    )
    incompatible = _profile(
        "profile-incompatible",
        policy.version,
        record_count=90,
        null_ratio=0.0,
        distinct_ratio=0.5,
        categories=("A",),
        mean=10,
        median_value=10,
        freshness="2026-07-20T12:00:00+00:00",
        schema={"amount": {"native_data_type": "NUMERIC", "is_nullable": True}},
        connector_version="CONNECTOR_V2",
    )
    current = _profile(
        "profile-compatible-current",
        policy.version,
        record_count=80,
        null_ratio=0.0,
        distinct_ratio=0.5,
        categories=("A",),
        mean=10,
        median_value=10,
        freshness="2026-07-20T12:00:00+00:00",
        schema={"amount": {"native_data_type": "NUMERIC", "is_nullable": True}},
    )

    comparison = compare_profile_snapshots(
        baseline=baseline,
        current=current,
        history=(baseline, incompatible, current),
        policy=policy,
    )

    assert comparison.status is ProfileComparisonStatus.INSUFFICIENT_HISTORY
    assert comparison.anomaly_candidate is None
    assert comparison.result == {
        "reason": "MINIMUM_COMPATIBLE_HISTORY_NOT_MET",
        "signals": [],
    }


def test_dq_cap_006_incompatible_snapshots_do_not_displace_compatible_baseline() -> None:
    policy = _policy(comparison_window=2, minimum_history=2)
    baseline = _profile(
        "profile-compatible-old",
        policy.version,
        record_count=100,
        null_ratio=0.0,
        distinct_ratio=0.5,
        categories=("A",),
        mean=10,
        median_value=10,
        freshness="2026-07-20T12:00:00+00:00",
        schema={"amount": {"native_data_type": "NUMERIC", "is_nullable": True}},
    )
    incompatible_1 = _incompatible_profile("profile-incompatible-new-1", policy)
    incompatible_2 = _incompatible_profile("profile-incompatible-new-2", policy)
    current = _profile(
        "profile-compatible-current",
        policy.version,
        record_count=50,
        null_ratio=0.0,
        distinct_ratio=0.5,
        categories=("A",),
        mean=10,
        median_value=10,
        freshness="2026-07-20T12:00:00+00:00",
        schema={"amount": {"native_data_type": "NUMERIC", "is_nullable": True}},
    )

    comparison = compare_profile_snapshots(
        baseline=baseline,
        current=current,
        history=(baseline, incompatible_1, incompatible_2, current),
        policy=policy,
    )

    assert comparison.status is ProfileComparisonStatus.COMPLETED
    assert comparison.baseline_profile_id == baseline.profile_id


def test_dq_cap_006_uses_requested_baseline_after_compatible_history_is_sufficient() -> None:
    policy = _policy(comparison_window=3, minimum_history=3)
    baseline = _profile(
        "profile-compatible-baseline",
        policy.version,
        record_count=100,
        null_ratio=0.0,
        distinct_ratio=0.5,
        categories=("A",),
        mean=10,
        median_value=10,
        freshness="2026-07-20T12:00:00+00:00",
        schema={"amount": {"native_data_type": "NUMERIC", "is_nullable": True}},
    )
    compatible_middle = _profile(
        "profile-compatible-middle",
        policy.version,
        record_count=90,
        null_ratio=0.0,
        distinct_ratio=0.5,
        categories=("A",),
        mean=10,
        median_value=10,
        freshness="2026-07-20T12:00:00+00:00",
        schema={"amount": {"native_data_type": "NUMERIC", "is_nullable": True}},
    )
    incompatible = _incompatible_profile("profile-incompatible-new", policy)
    current = _profile(
        "profile-compatible-current",
        policy.version,
        record_count=50,
        null_ratio=0.0,
        distinct_ratio=0.5,
        categories=("A",),
        mean=10,
        median_value=10,
        freshness="2026-07-20T12:00:00+00:00",
        schema={"amount": {"native_data_type": "NUMERIC", "is_nullable": True}},
    )

    comparison = compare_profile_snapshots(
        baseline=baseline,
        current=current,
        history=(baseline, compatible_middle, incompatible, current),
        policy=policy,
    )

    volume_signal = next(
        signal for signal in comparison.result["signals"] if signal["kind"] == "VOLUME_CHANGE"
    )
    assert comparison.status is ProfileComparisonStatus.COMPLETED
    assert comparison.baseline_profile_id == baseline.profile_id
    assert volume_signal["baseline"] == 100
    assert volume_signal["current"] == 50


def _profile(
    profile_id: str,
    policy_version: str,
    *,
    record_count: int,
    null_ratio: float,
    distinct_ratio: float,
    categories: tuple[str, ...],
    mean: float,
    median_value: float,
    freshness: str,
    schema: dict,
    connector_version: str = "CONNECTOR_V1",
) -> DataProfile:
    now = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
    return DataProfile(
        profile_id=profile_id,
        dataset_id="dataset-1",
        execution_id=f"execution-{profile_id}",
        method=ProfileMethod.FULL,
        status=ProfileStatus.COMPLETED,
        metrics={
            "record_count": record_count,
            "fields": {
                "amount": {
                    "null_ratio": null_ratio,
                    "distinct_ratio": distinct_ratio,
                    "top_values": [
                        {"rank": rank, "value": value, "count": 1, "masked": False}
                        for rank, value in enumerate(categories, start=1)
                    ],
                    "numeric_summary": {"mean": mean, "median": median_value},
                    "freshness_max": freshness,
                }
            },
            "profile_contract": {
                "snapshot_version": "DQ_PROFILE_SNAPSHOT_V1",
                "method": "FULL",
                "sample_ratio": None,
                "scope": {},
                "query_version": "QUERY_V1",
                "connector_version": connector_version,
                "policy_version": policy_version,
                "schema": schema,
            },
        },
        started_at=now,
        finished_at=now,
    )


def _policy(*, comparison_window: int, minimum_history: int) -> ProfileAnalysisPolicy:
    return ProfileAnalysisPolicy(
        version="DRIFT_POLICY_TEST_V1",
        top_n_limit=3,
        high_cardinality_threshold=4,
        advanced_sample_size=8,
        sampling_strategy=ProfileSamplingStrategy.DETERMINISTIC_HASH,
        sampling_seed=20260729,
        enabled_outlier_methods=(OutlierMethod.IQR,),
        iqr_multiplier=1.5,
        robust_z_score_threshold=3.5,
        minimum_numeric_sample=4,
        comparison_window=comparison_window,
        minimum_history=minimum_history,
        volume_ratio_threshold=0.1,
        null_ratio_delta_threshold=0.1,
        distinct_ratio_delta_threshold=0.1,
        category_loss_ratio_threshold=0.3,
        numeric_mean_ratio_threshold=0.1,
        numeric_median_ratio_threshold=0.1,
        freshness_delay_seconds_threshold=60,
        schema_change_detection_enabled=True,
    )


def _incompatible_profile(
    profile_id: str,
    policy: ProfileAnalysisPolicy,
) -> DataProfile:
    return _profile(
        profile_id,
        policy.version,
        record_count=90,
        null_ratio=0.0,
        distinct_ratio=0.5,
        categories=("A",),
        mean=10,
        median_value=10,
        freshness="2026-07-20T12:00:00+00:00",
        schema={"amount": {"native_data_type": "NUMERIC", "is_nullable": True}},
        connector_version="CONNECTOR_V2",
    )
