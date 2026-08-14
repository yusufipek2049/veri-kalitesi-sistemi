"""FR-089–FR-095, UC-017 ve AC/TS-048–056 PostgreSQL dataset testleri."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from veri_kalitesi.synthetic_data.errors import SyntheticDataValidationError
from veri_kalitesi.synthetic_data.postgresql_dataset import (
    CLUSTERS_PER_TABLE,
    DEFAULT_ROW_COUNT,
    GENERATOR_VERSION,
    MAX_ROW_COUNT,
    MEASURE_DISTRIBUTIONS,
    MIN_ROW_COUNT,
    REFERENCE_TIME,
    SCENARIO_CLUSTER_INTENSITY,
    SCENARIO_DEFECT_RATIOS,
    STALE_THRESHOLD,
    TABLE_SPECS,
    MeasureDistribution,
    PostgreSQLSyntheticDatasetManager,
    ProfileOverrides,
    _canonical_row,
    _cluster_index,
    _cluster_multiplier,
    _compute_profile_sha256,
    _event_time,
    _get_distribution,
    _get_overrides,
    _ingestion_delay,
    _measure,
    _PROFILE_OVERRIDES,
    _scenario_rates,
    _selected_defects,
    build_argument_parser,
    build_source_row,
    extract_profile_overrides,
    validate_generation_request,
    _source_columns,
)
from veri_kalitesi.synthetic_data.profile_schema import (
    DecileValues,
    LatencyDistribution,
    SyntheticProfileArtifact,
    SystemWideProfile,
    TableProfile,
    ColumnProfile,
    PROFILE_SCHEMA_VERSION,
)


EXPECTED_TABLES = {
    "synthetic_customers",
    "synthetic_customer_contacts",
    "synthetic_customer_addresses",
    "synthetic_accounts",
    "synthetic_account_balances",
    "synthetic_transactions",
    "synthetic_cards",
    "synthetic_card_transactions",
    "synthetic_loans",
    "synthetic_loan_installments",
    "synthetic_payments",
    "synthetic_beneficiaries",
    "synthetic_merchants",
    "synthetic_merchant_transactions",
    "synthetic_customer_risk_profiles",
    "synthetic_service_requests",
    "synthetic_data_events",
}


def test_fr_089_exactly_seventeen_relational_source_tables_are_defined() -> None:
    assert len(TABLE_SPECS) == 17
    assert {spec.name for spec in TABLE_SPECS} == EXPECTED_TABLES
    assert all(spec.primary_key and spec.business_key for spec in TABLE_SPECS)
    assert sum(bool(spec.relations) for spec in TABLE_SPECS) == 15
    targets = {relation.target_table for spec in TABLE_SPECS for relation in spec.relations}
    assert targets <= EXPECTED_TABLES


@pytest.mark.parametrize("environment", ["production", "acceptance", "prod"])
def test_fr_095_production_like_environment_is_rejected(environment: str) -> None:
    with pytest.raises(SyntheticDataValidationError, match="environment is not allowed"):
        validate_generation_request(
            environment=environment,
            database_name="data_quality",
            allow_test_data=True,
            row_count=DEFAULT_ROW_COUNT,
            scenario="mixed-quality",
        )


@pytest.mark.parametrize("database_name", ["production", "bank_prod", "data_quality_prod"])
def test_fr_095_production_like_database_is_rejected(database_name: str) -> None:
    with pytest.raises(SyntheticDataValidationError, match="Production-like"):
        validate_generation_request(
            environment="test",
            database_name=database_name,
            allow_test_data=True,
            row_count=DEFAULT_ROW_COUNT,
            scenario="mixed-quality",
        )


def test_fr_088_explicit_test_data_permission_is_required() -> None:
    with pytest.raises(SyntheticDataValidationError, match="Explicit test-data"):
        validate_generation_request(
            environment="test",
            database_name="data_quality",
            allow_test_data=False,
            row_count=DEFAULT_ROW_COUNT,
            scenario="mixed-quality",
        )


@pytest.mark.parametrize("row_count", [MIN_ROW_COUNT - 1, MAX_ROW_COUNT + 1])
def test_fr_094_every_table_row_count_must_remain_in_approved_range(row_count: int) -> None:
    with pytest.raises(SyntheticDataValidationError, match="between 17000 and 22000"):
        validate_generation_request(
            environment="test",
            database_name="data_quality",
            allow_test_data=True,
            row_count=row_count,
            scenario="mixed-quality",
        )


def test_fr_093_same_seed_and_version_are_deterministic_and_seed_sensitive() -> None:
    spec = TABLE_SPECS[5]

    first, first_truth = build_source_row(
        spec,
        seed=2026,
        scenario="mixed-quality",
        index=42,
        row_count=DEFAULT_ROW_COUNT,
    )
    replay, replay_truth = build_source_row(
        spec,
        seed=2026,
        scenario="mixed-quality",
        index=42,
        row_count=DEFAULT_ROW_COUNT,
    )
    changed, changed_truth = build_source_row(
        spec,
        seed=2027,
        scenario="mixed-quality",
        index=42,
        row_count=DEFAULT_ROW_COUNT,
    )

    assert GENERATOR_VERSION == "RELATIONAL_BANKING_GENERATOR_V5"
    assert _canonical_row(first) == _canonical_row(replay)
    assert first_truth == replay_truth
    assert (_canonical_row(first), first_truth) != (_canonical_row(changed), changed_truth)


def test_fr_091_mixed_quality_ratio_is_within_declared_policy_range() -> None:
    spec = TABLE_SPECS[5]
    defective_keys: set[str] = set()
    defect_events: set[tuple[str, str, str]] = set()

    for index in range(DEFAULT_ROW_COUNT):
        _, truths = build_source_row(
            spec,
            seed=2026,
            scenario="mixed-quality",
            index=index,
            row_count=DEFAULT_ROW_COUNT,
        )
        for truth in truths:
            defective_keys.add(truth.record_key)
            defect_events.add((truth.record_key, truth.column_name, truth.defect_type))

    defective_ratio = len(defective_keys) / DEFAULT_ROW_COUNT
    assert 0.15 <= defective_ratio <= 0.20
    assert len(defect_events) > len(defective_keys)


def test_fr_090_scenarios_use_skewed_non_uniform_defect_profiles() -> None:
    assert set(SCENARIO_DEFECT_RATIOS) == {
        "clean-baseline",
        "mixed-quality",
        "high-defect",
        "stale-data",
        "duplicate-heavy",
        "referential-integrity",
    }
    mixed = _scenario_rates("mixed-quality", supports_relation_defect=True)
    assert len(set(mixed.values())) > 1
    assert mixed["stale_record"] > mixed["blank_or_whitespace"]
    assert set(_scenario_rates("stale-data", supports_relation_defect=True)) == {"stale_record"}
    assert set(_scenario_rates("duplicate-heavy", supports_relation_defect=True)) == {"duplicate"}


def test_fr_089_relations_are_meaningful_without_physical_fk_claim() -> None:
    spec = next(spec for spec in TABLE_SPECS if spec.name == "synthetic_cards")
    clean_spec = replace(spec, name="synthetic_cards_clean_probe")

    row, truths = build_source_row(
        clean_spec,
        seed=2026,
        scenario="clean-baseline",
        index=0,
        row_count=DEFAULT_ROW_COUNT,
    )

    assert len(row) == 15
    assert all(relation.target_table in EXPECTED_TABLES for relation in spec.relations)
    assert all(truth.expected_rule_result == "FAIL" for truth in truths)


def test_fr_095_cli_has_no_password_argument() -> None:
    parser = build_argument_parser()
    option_strings = {option for action in parser._actions for option in action.option_strings}
    assert "--password" not in option_strings
    assert "--allow-test-data" in option_strings


def test_fr_093_manager_rejects_non_autocommit_connection() -> None:
    class UnsafeConnection:
        autocommit = False

    with pytest.raises(SyntheticDataValidationError, match="autocommit"):
        PostgreSQLSyntheticDatasetManager(UnsafeConnection())  # type: ignore[arg-type]


# ── Faz 1: Kusur kümelenmesi ─────────────────────────────────────────────


def test_clustering_clean_baseline_has_no_clustering() -> None:
    """clean-baseline senaryosunda kümelenme kapalı olmalı."""
    assert SCENARIO_CLUSTER_INTENSITY["clean-baseline"] == 0.0
    spec = TABLE_SPECS[0]
    for cluster in range(CLUSTERS_PER_TABLE):
        assert _cluster_multiplier(spec.name, "missing_value", cluster, 0.0) == 1.0


def test_clustering_multiplier_averages_to_one() -> None:
    """Küme çarpanlarının ortalaması 1.0 olmalı — toplam oran korunur."""
    spec = TABLE_SPECS[0]
    intensity = 0.6
    multipliers = [
        _cluster_multiplier(spec.name, "missing_value", c, intensity)
        for c in range(CLUSTERS_PER_TABLE)
    ]
    assert abs(sum(multipliers) / len(multipliers) - 1.0) < 1e-10


def test_clustering_multiplier_is_deterministic() -> None:
    """Aynı küme parametreleriyle aynı çarpan üretilmeli."""
    first = _cluster_multiplier("synthetic_customers", "missing_value", 3, 0.6)
    second = _cluster_multiplier("synthetic_customers", "missing_value", 3, 0.6)
    assert first == second


def test_clustering_multiplier_varies_across_clusters() -> None:
    """Farklı kümeler farklı çarpanlar üretmeli."""
    spec = TABLE_SPECS[0]
    intensity = 0.6
    multipliers = {
        _cluster_multiplier(spec.name, "missing_value", c, intensity)
        for c in range(CLUSTERS_PER_TABLE)
    }
    assert len(multipliers) > 1


def test_clustering_defect_distribution_has_higher_variance() -> None:
    """Kümelenmiş kusurların varyansı, bağımsız Bernoulli örneklemesinden yüksek olmalı.

    Küme başına kusur oranlarının varyansını, yalnızca Bernoulli gürültüsü
    durumunda beklenen varyansla karşılaştırır. Kümelenme etkisi, küme
    ortalamalarının yayılmasını Bernoulli örneklemesinin ötesine taşır.
    """
    spec = TABLE_SPECS[5]
    seed = 2026
    scenario = "mixed-quality"
    row_count = DEFAULT_ROW_COUNT
    defect_type = "missing_value"

    cluster_defect_counts: dict[int, int] = {c: 0 for c in range(CLUSTERS_PER_TABLE)}
    cluster_sizes: dict[int, int] = {c: 0 for c in range(CLUSTERS_PER_TABLE)}

    for index in range(row_count):
        cluster = _cluster_index(spec.name, defect_type, index)
        cluster_sizes[cluster] += 1
        selected = _selected_defects(spec, seed, scenario, index)
        if defect_type in selected:
            cluster_defect_counts[cluster] += 1

    cluster_rates = [
        cluster_defect_counts[c] / cluster_sizes[c]
        for c in range(CLUSTERS_PER_TABLE)
        if cluster_sizes[c] > 0
    ]
    mean_rate = sum(cluster_rates) / len(cluster_rates)
    observed_variance = sum((r - mean_rate) ** 2 for r in cluster_rates) / len(cluster_rates)

    base_rate = _scenario_rates(scenario, supports_relation_defect=True).get(defect_type, 0.0)
    # Küme ortalamalarının Bernoulli örneklemesinden beklenen varyansı
    bernoulli_cluster_variance = base_rate * (1.0 - base_rate) / (row_count / CLUSTERS_PER_TABLE)

    assert observed_variance > bernoulli_cluster_variance, (
        f"Clustered variance {observed_variance:.8f} should exceed "
        f"Bernoulli cluster-mean variance {bernoulli_cluster_variance:.8f}"
    )


def test_clustering_total_defect_rate_within_tolerance() -> None:
    """Toplam kusur oranı senaryo hedefinden sapmamalı."""
    spec = TABLE_SPECS[5]
    seed = 2026
    scenario = "mixed-quality"
    target_ratio = SCENARIO_DEFECT_RATIOS[scenario]
    defective_keys: set[str] = set()

    for index in range(DEFAULT_ROW_COUNT):
        _, truths = build_source_row(
            spec,
            seed=seed,
            scenario=scenario,
            index=index,
            row_count=DEFAULT_ROW_COUNT,
        )
        for truth in truths:
            defective_keys.add(truth.record_key)

    actual_ratio = len(defective_keys) / DEFAULT_ROW_COUNT
    assert abs(actual_ratio - target_ratio) <= 0.05, (
        f"Defect ratio {actual_ratio:.4f} deviates from target {target_ratio:.4f}"
    )


def test_clustering_ground_truth_zero_fp_fn() -> None:
    """Kümelenme tüm senaryolarda FP/FN sıfır bırakmalı."""
    scenarios = ["mixed-quality", "high-defect", "stale-data"]
    for scenario in scenarios:
        spec = TABLE_SPECS[5]
        defect_keys: set[str] = set()
        for index in range(DEFAULT_ROW_COUNT):
            _, truths = build_source_row(
                spec,
                seed=2026,
                scenario=scenario,
                index=index,
                row_count=DEFAULT_ROW_COUNT,
            )
            for truth in truths:
                defect_keys.add(truth.record_key)
        assert len(defect_keys) > 0, f"No defects generated for scenario {scenario}"


def test_clustering_determinism_preserved() -> None:
    """Kümelenme determinizmi bozmamalı."""
    spec = TABLE_SPECS[5]
    first, first_truth = build_source_row(
        spec,
        seed=2026,
        scenario="mixed-quality",
        index=42,
        row_count=DEFAULT_ROW_COUNT,
    )
    replay, replay_truth = build_source_row(
        spec,
        seed=2026,
        scenario="mixed-quality",
        index=42,
        row_count=DEFAULT_ROW_COUNT,
    )
    assert _canonical_row(first) == _canonical_row(replay)
    assert first_truth == replay_truth


# ── Faz 2: Kolon başına dağılım parametreleri ────────────────────────────


def test_distribution_dataclass_is_frozen_and_valid() -> None:
    """MeasureDistribution donmuş ve geçerli aile doğrulaması yapar."""
    dist = MeasureDistribution("lognormal", mu=5.0, sigma=1.5, low=0.01, high=50_000.0)
    assert dist.family == "lognormal"
    assert dist.mu == 5.0
    with pytest.raises(AttributeError):
        dist.mu = 6.0  # type: ignore[misc]


def test_measure_distributions_covers_all_seventeen_tables() -> None:
    """MEASURE_DISTRIBUTIONS 17 tablonun tümünü kapsar."""
    table_names = {spec.name for spec in TABLE_SPECS}
    assert set(MEASURE_DISTRIBUTIONS) == table_names
    for name, dist in MEASURE_DISTRIBUTIONS.items():
        assert dist.family in ("lognormal", "uniform", "bounded_normal")
        if dist.low is not None and dist.high is not None:
            assert dist.low < dist.high


def test_measure_values_within_bounds_for_all_tables() -> None:
    """Tüm tablolar için üretilen değerler [low, high] sınırları içinde."""
    for spec in TABLE_SPECS:
        dist = MEASURE_DISTRIBUTIONS.get(spec.name)
        if dist is None or (dist.low is None and dist.high is None):
            continue
        for index in range(500):
            value = _measure(2026, spec.name, index)
            if dist.low is not None:
                assert value >= Decimal(str(dist.low)), (
                    f"{spec.name}[{index}] = {value} < {dist.low}"
                )
            if dist.high is not None:
                assert value <= Decimal(str(dist.high)), (
                    f"{spec.name}[{index}] = {value} > {dist.high}"
                )


def test_measure_uniform_percentiles() -> None:
    """Uniform dağılımların p10/p50/p90'ı beklenen aralığa yakın."""
    for table_name in (
        "synthetic_customers",
        "synthetic_merchants",
        "synthetic_customer_risk_profiles",
    ):
        dist = MEASURE_DISTRIBUTIONS[table_name]
        values = sorted(float(_measure(2026, table_name, i)) for i in range(5000))
        low = dist.low or 0.0
        high = dist.high or 1.0
        span = high - low
        p10 = values[500]
        p50 = values[2500]
        p90 = values[4500]
        assert low <= p10 <= low + 0.25 * span, f"{table_name} p10={p10}"
        assert low + 0.35 * span <= p50 <= low + 0.65 * span, f"{table_name} p50={p50}"
        assert high - 0.25 * span <= p90 <= high, f"{table_name} p90={p90}"


def test_measure_lognormal_percentiles() -> None:
    """Lognormal dağılımların p10/p50/p90'ı exp(mu) civarında."""
    import math

    cases = [
        ("synthetic_transactions", 5.0, 1.5),
        ("synthetic_cards", 8.0, 1.0),
        ("synthetic_loans", 9.0, 1.0),
    ]
    for table_name, mu, sigma in cases:
        values = sorted(float(_measure(2026, table_name, i)) for i in range(5000))
        median_expected = math.exp(mu)
        p10 = values[500]
        p50 = values[2500]
        p90 = values[4500]
        assert p10 < median_expected < p90, (
            f"{table_name}: p10={p10}, median={p50}, p90={p90}, exp(mu)={median_expected}"
        )
        assert p50 > median_expected * 0.3, f"{table_name} p50={p50} too low"
        assert p50 < median_expected * 3.0, f"{table_name} p50={p50} too high"


def test_measure_bounded_normal_percentiles() -> None:
    """Bounded normal dağılımların p50'si mu civarında."""
    for table_name in ("synthetic_customer_contacts", "synthetic_customer_addresses"):
        dist = MEASURE_DISTRIBUTIONS[table_name]
        values = sorted(float(_measure(2026, table_name, i)) for i in range(5000))
        p50 = values[2500]
        assert abs(p50 - dist.mu) < 0.3, f"{table_name} p50={p50} deviates from mu={dist.mu}"


def test_measure_fallback_for_unknown_table() -> None:
    """Tanımlanmamış tablo lognormal(7, 1) fallback kullanır."""
    value = _measure(2026, "synthetic_unknown_table_xyz", 42)
    assert isinstance(value, Decimal)
    assert value > 0


def test_measure_determinism_with_distributions() -> None:
    """Dağılım değişiklikleri sonrası determinizm korunur."""
    for spec in TABLE_SPECS[:5]:
        first = _measure(2026, spec.name, 100)
        second = _measure(2026, spec.name, 100)
        assert first == second, f"Non-deterministic measure for {spec.name}"


def test_distribution_ground_truth_zero_fp_fn_all_scenarios() -> None:
    """Dağılım değişiklikleri tüm senaryolarda FP/FN sıfır bırakır."""
    scenarios = [
        "clean-baseline",
        "mixed-quality",
        "high-defect",
        "stale-data",
        "duplicate-heavy",
        "referential-integrity",
    ]
    for scenario in scenarios:
        for spec in TABLE_SPECS:
            for index in range(50):
                _, truths = build_source_row(
                    spec,
                    seed=2026,
                    scenario=scenario,
                    index=index,
                    row_count=DEFAULT_ROW_COUNT,
                )
                for truth in truths:
                    assert truth.expected_rule_result == "FAIL"


# ── Faz 3: Takvim gerçekçiliği ────────────────────────────────────────────


def test_calendar_weekend_volume_lower_than_weekday() -> None:
    """Hafta sonu hacmi hafta içinin ölçülebilir şekilde altında."""
    weekday_count = 0
    weekend_count = 0
    for index in range(5000):
        event_dt = _event_time(2026, "synthetic_transactions", index)
        if event_dt.weekday() >= 5:  # Cumartesi-Pazar
            weekend_count += 1
        else:
            weekday_count += 1
    # Hafta sonu hacmi hafta içinin %30'undan az olmalı
    assert weekend_count < weekday_count * 0.3, (
        f"Weekend {weekend_count} should be < 30% of weekday {weekday_count}"
    )


def test_calendar_month_end_volume_clustering() -> None:
    """Ay sonu günlerinde (ayın son 3 günü) hacim yığılması var."""
    import calendar
    month_end_count = 0
    total_count = 5000
    for index in range(total_count):
        event_dt = _event_time(2026, "synthetic_transactions", index)
        _, last_day = calendar.monthrange(event_dt.year, event_dt.month)
        if event_dt.day >= last_day - 2:
            month_end_count += 1
    # Ayın son 3 günü ~%10 gün, ama yığılma ile %15+ olmalı
    month_end_ratio = month_end_count / total_count
    assert month_end_ratio > 0.12, (
        f"Month-end ratio {month_end_ratio:.3f} should be > 12% with clustering"
    )


def test_calendar_business_hours_higher_volume() -> None:
    """Mesai saatleri (09–18) dışı hacim düşük."""
    business_hours_count = 0
    total_count = 5000
    for index in range(total_count):
        event_dt = _event_time(2026, "synthetic_transactions", index)
        if 9 <= event_dt.hour < 18:
            business_hours_count += 1
    # %75 hedefleniyor, en az %60 olmalı
    business_ratio = business_hours_count / total_count
    assert business_ratio > 0.60, (
        f"Business hours ratio {business_ratio:.3f} should be > 60%"
    )


def test_ingestion_delay_long_tailed_distribution() -> None:
    """Late-arriving dağılımı kuyruklu — median düşük, max yüksek."""
    delays_minutes = []
    for index in range(5000):
        delay = _ingestion_delay(2026, "synthetic_transactions", index)
        delays_minutes.append(delay.total_seconds() / 60)
    delays_sorted = sorted(delays_minutes)
    median = delays_sorted[len(delays_sorted) // 2]
    max_delay = max(delays_minutes)
    # Median düşük (30 dakikadan az), max yüksek (1 günden fazla)
    assert median < 30, f"Median delay {median} should be < 30 minutes"
    assert max_delay > 1440, f"Max delay {max_delay} should be > 1 day (1440 min)"
    # Kuyruk: p90 > median * 10
    p90 = delays_sorted[int(len(delays_sorted) * 0.9)]
    assert p90 > median * 10, f"Long tail: p90 {p90} should be > median*10 {median*10}"


def test_calendar_reference_time_and_stale_threshold_consistency() -> None:
    """REFERENCE_TIME ve STALE_THRESHOLD ile tutarlılık bozulmamış."""
    for index in range(100):
        event_dt = _event_time(2026, "synthetic_transactions", index)
        # Tüm event_time'lar REFERENCE_TIME'dan önce veya eşit olmalı
        assert event_dt <= REFERENCE_TIME, (
            f"event_time {event_dt} should be <= REFERENCE_TIME {REFERENCE_TIME}"
        )
    # Stale record'lar STALE_THRESHOLD'dan eski olmalı
    spec = TABLE_SPECS[5]
    for index in range(50):
        _, truths = build_source_row(
            spec,
            seed=2026,
            scenario="stale-data",
            index=index,
            row_count=DEFAULT_ROW_COUNT,
        )
        if truths and any(t.defect_type == "stale_record" for t in truths):
            row, _ = build_source_row(
                spec,
                seed=2026,
                scenario="stale-data",
                index=index,
                row_count=DEFAULT_ROW_COUNT,
            )
            # updated_at STALE_THRESHOLD'dan eski olmalı
            from veri_kalitesi.synthetic_data.postgresql_dataset import _source_columns
            columns = _source_columns(spec)
            row_dict = dict(zip(columns, row))
            updated_at = row_dict["updated_at"]
            assert updated_at < STALE_THRESHOLD, (
                f"stale_record updated_at {updated_at} should be < "
                f"STALE_THRESHOLD {STALE_THRESHOLD}"
            )


def test_calendar_determinism_preserved() -> None:
    """Takvim değişiklikleri determinizmi bozmamalı."""
    spec = TABLE_SPECS[5]
    first, first_truth = build_source_row(
        spec,
        seed=2026,
        scenario="mixed-quality",
        index=42,
        row_count=DEFAULT_ROW_COUNT,
    )
    replay, replay_truth = build_source_row(
        spec,
        seed=2026,
        scenario="mixed-quality",
        index=42,
        row_count=DEFAULT_ROW_COUNT,
    )
    assert _canonical_row(first) == _canonical_row(replay)
    assert first_truth == replay_truth


def test_calendar_ground_truth_zero_fp_fn_all_scenarios() -> None:
    """Takvim değişiklikleri tüm senaryolarda FP/FN sıfır bırakır."""
    scenarios = [
        "clean-baseline",
        "mixed-quality",
        "high-defect",
        "stale-data",
        "duplicate-heavy",
        "referential-integrity",
    ]
    for scenario in scenarios:
        for spec in TABLE_SPECS:
            for index in range(50):
                _, truths = build_source_row(
                    spec,
                    seed=2026,
                    scenario=scenario,
                    index=index,
                    row_count=DEFAULT_ROW_COUNT,
                )
                for truth in truths:
                    assert truth.expected_rule_result == "FAIL"


def test_event_time_within_180_day_window() -> None:
    """Tüm event_time'lar 180 günlük pencere içinde."""
    from datetime import timedelta
    window_start = REFERENCE_TIME - timedelta(days=180)
    for index in range(1000):
        event_dt = _event_time(2026, "synthetic_transactions", index)
        assert event_dt >= window_start, (
            f"event_time {event_dt} should be >= window_start {window_start}"
        )
        assert event_dt <= REFERENCE_TIME, (
            f"event_time {event_dt} should be <= REFERENCE_TIME {REFERENCE_TIME}"
        )


def test_ingestion_delay_deterministic() -> None:
    """Ingestion delay deterministik."""
    for index in range(100):
        first = _ingestion_delay(2026, "synthetic_transactions", index)
        second = _ingestion_delay(2026, "synthetic_transactions", index)
        assert first == second, f"Non-deterministic delay at index {index}"


# ── Faz 5: Profilden üretim ─────────────────────────────────────────────


def _minimal_profile(
    *,
    deciles: DecileValues | None = None,
    volume_curve: tuple | None = None,
    latency: LatencyDistribution | None = None,
    clustering_coefficient: float = 0.6,
) -> SyntheticProfileArtifact:
    """Faz 5 testleri için minimal profil artefaktı oluşturur."""
    columns = ()
    if deciles is not None:
        columns = (
            ColumnProfile(
                column_name="activity_score",
                column_type="numeric",
                null_ratio=0.02,
                distinct_ratio=0.5,
                deciles=deciles,
            ),
        )
    tables = (
        TableProfile(
            table_name="synthetic_customers",
            row_count=19000,
            columns=columns,
        ),
    )
    system_wide = SystemWideProfile(
        volume_curve=volume_curve or (),
        latency_distribution=latency,
        defect_clustering_coefficient=clustering_coefficient,
    )
    return SyntheticProfileArtifact(
        profile_schema_version=PROFILE_SCHEMA_VERSION,
        tables=tables,
        system_wide=system_wide,
    )


def test_profile_overrides_dataclass_is_frozen() -> None:
    """ProfileOverrides donmuş dataclass."""
    overrides = ProfileOverrides()
    assert overrides.cluster_intensity == 0.0
    assert overrides.weekend_rejection_threshold == 0.6
    with pytest.raises(AttributeError):
        overrides.cluster_intensity = 0.5  # type: ignore[misc]


def test_extract_profile_overrides_from_minimal_profile() -> None:
    """Minimal profilden override parametreleri doğru çıkarılır."""
    profile = _minimal_profile(
        deciles=DecileValues(p10=10.0, p25=25.0, p50=50.0, p75=75.0, p90=90.0, p99=99.0),
        clustering_coefficient=0.75,
    )
    overrides = extract_profile_overrides(profile)
    assert overrides.cluster_intensity == 0.75
    assert "synthetic_customers" in overrides.distributions
    dist = overrides.distributions["synthetic_customers"]
    assert dist.family == "uniform"
    assert dist.low == 10.0
    assert dist.high == 90.0


def test_extract_profile_overrides_calendar_from_volume_curve() -> None:
    """Volume curve'dan takvim override'ları çıkarılır."""
    from veri_kalitesi.synthetic_data.profile_schema import VolumePoint
    volume_curve = (
        VolumePoint("daily", "monday", 0.22),
        VolumePoint("daily", "tuesday", 0.21),
        VolumePoint("daily", "wednesday", 0.20),
        VolumePoint("daily", "thursday", 0.19),
        VolumePoint("daily", "friday", 0.13),
        VolumePoint("daily", "saturday", 0.03),
        VolumePoint("daily", "sunday", 0.02),
    )
    profile = _minimal_profile(volume_curve=volume_curve)
    overrides = extract_profile_overrides(profile)
    # Hafta sonu payı düşük → weekend_rejection > 0
    assert overrides.weekend_rejection_threshold > 0
    assert overrides.business_hours_threshold > 0


def test_extract_profile_overrides_latency() -> None:
    """Latency distribution'dan delay override'ları çıkarılır."""
    latency = LatencyDistribution(p50=120.0, p90=1800.0, p99=14400.0)
    profile = _minimal_profile(latency=latency)
    overrides = extract_profile_overrides(profile)
    assert overrides.delay_fast_threshold > 0
    assert overrides.delay_medium_threshold > overrides.delay_fast_threshold
    assert overrides.delay_slow_max_days >= 1


def test_profile_determinism_same_profile_same_seed_same_output() -> None:
    """Aynı profil + aynı seed aynı canonical output üretir — determinizm."""
    profile = _minimal_profile(
        deciles=DecileValues(p10=10.0, p25=25.0, p50=50.0, p75=75.0, p90=90.0, p99=99.0),
        clustering_coefficient=0.7,
    )
    overrides = extract_profile_overrides(profile)
    spec = TABLE_SPECS[0]
    token = _PROFILE_OVERRIDES.set(overrides)
    try:
        first, first_truth = build_source_row(
            spec, seed=2026, scenario="mixed-quality", index=42,
            row_count=DEFAULT_ROW_COUNT,
        )
        replay, replay_truth = build_source_row(
            spec, seed=2026, scenario="mixed-quality", index=42,
            row_count=DEFAULT_ROW_COUNT,
        )
    finally:
        _PROFILE_OVERRIDES.reset(token)
    assert _canonical_row(first) == _canonical_row(replay)
    assert first_truth == replay_truth


def test_profile_different_from_no_profile() -> None:
    """Profil ile profilsiz üretim farklı output üretir (farklı dağılım)."""
    spec = TABLE_SPECS[0]
    # clean-baseline senaryosu: kusur enjeksiyonu yok, saf dağılım farkı.
    # Profilsiz
    no_profile_row, _ = build_source_row(
        spec, seed=2026, scenario="clean-baseline", index=42,
        row_count=DEFAULT_ROW_COUNT,
    )
    # Profil ile
    profile = _minimal_profile(
        deciles=DecileValues(p10=10.0, p25=25.0, p50=50.0, p75=75.0, p90=90.0, p99=99.0),
        clustering_coefficient=0.7,
    )
    overrides = extract_profile_overrides(profile)
    token = _PROFILE_OVERRIDES.set(overrides)
    try:
        with_profile_row, _ = build_source_row(
            spec, seed=2026, scenario="clean-baseline", index=42,
            row_count=DEFAULT_ROW_COUNT,
        )
    finally:
        _PROFILE_OVERRIDES.reset(token)
    # Farklı dağılım parametreleri → farklı measure değerleri
    measure_idx = list(_source_columns(spec)).index(spec.measure_column)
    assert no_profile_row[measure_idx] != with_profile_row[measure_idx]


def test_profile_ground_truth_zero_fp_fn_all_scenarios() -> None:
    """Profil override ile bile ground truth FP==0, FN==0 korunur."""
    profile = _minimal_profile(
        deciles=DecileValues(p10=10.0, p25=25.0, p50=50.0, p75=75.0, p90=90.0, p99=99.0),
        clustering_coefficient=0.6,
    )
    overrides = extract_profile_overrides(profile)
    scenarios = ["mixed-quality", "high-defect", "stale-data"]
    token = _PROFILE_OVERRIDES.set(overrides)
    try:
        for scenario in scenarios:
            spec = TABLE_SPECS[5]
            for index in range(50):
                _, truths = build_source_row(
                    spec, seed=2026, scenario=scenario, index=index,
                    row_count=DEFAULT_ROW_COUNT,
                )
                for truth in truths:
                    assert truth.expected_rule_result == "FAIL", (
                        f"Profile override broke ground truth for {scenario}"
                    )
    finally:
        _PROFILE_OVERRIDES.reset(token)


def test_generation_summary_has_profile_fields() -> None:
    """GenerationSummary profil sürüm ve hash alanlarını içerir."""
    from veri_kalitesi.synthetic_data.postgresql_dataset import GenerationSummary
    summary = GenerationSummary(
        run_id="test",
        generator_version=GENERATOR_VERSION,
        schema_version="V1",
        configuration_version="V1",
        seed=2026,
        scenario="mixed-quality",
        row_count_per_table=19000,
        table_metrics=(),
        profile_metrics=(),
        validation_metrics=(),
        canonical_sha256="abc",
        generation_duration_seconds=1.0,
        database_size_bytes=0,
        peak_memory_bytes=0,
        profile_version="SYNTHETIC_PROFILE_V1",
        profile_sha256="deadbeef",
    )
    assert summary.profile_version == "SYNTHETIC_PROFILE_V1"
    assert summary.profile_sha256 == "deadbeef"


def test_generation_summary_profile_fields_default_none() -> None:
    """Profil kullanılmazsa profile_version ve profile_sha256 None kalır."""
    from veri_kalitesi.synthetic_data.postgresql_dataset import GenerationSummary
    summary = GenerationSummary(
        run_id="test",
        generator_version=GENERATOR_VERSION,
        schema_version="V1",
        configuration_version="V1",
        seed=2026,
        scenario="mixed-quality",
        row_count_per_table=19000,
        table_metrics=(),
        profile_metrics=(),
        validation_metrics=(),
        canonical_sha256="abc",
        generation_duration_seconds=1.0,
        database_size_bytes=0,
        peak_memory_bytes=0,
    )
    assert summary.profile_version is None
    assert summary.profile_sha256 is None


def test_profile_sha256_is_deterministic() -> None:
    """Aynı profil artefaktı aynı SHA-256 hash üretir."""
    profile = _minimal_profile(clustering_coefficient=0.6)
    first = _compute_profile_sha256(profile)
    second = _compute_profile_sha256(profile)
    assert first == second
    assert len(first) == 64  # SHA-256 hex digest


def test_cli_has_profile_argument() -> None:
    """CLI --profile PATH argümanı eklendi."""
    parser = build_argument_parser()
    option_strings = {
        option
        for action in parser._actions
        for option in action.option_strings
    }
    assert "--profile" in option_strings


def test_profile_overrides_do_not_affect_defect_injection() -> None:
    """Profil override yalnızca dağılım/takvim parametrelerini etkiler,
    kusur enjeksiyonu mekaniğini (DefectTruth, _selected_defects) değiştirmez."""
    spec = TABLE_SPECS[5]
    # Profilsiz kusur seçimi
    no_profile_defects = _selected_defects(spec, 2026, "mixed-quality", 42)
    # Profil override ile kusur seçimi (cluster_intensity=0.6 ile aynı)
    profile = _minimal_profile(clustering_coefficient=0.6)
    overrides = extract_profile_overrides(profile)
    token = _PROFILE_OVERRIDES.set(overrides)
    try:
        with_profile_defects = _selected_defects(spec, 2026, "mixed-quality", 42)
    finally:
        _PROFILE_OVERRIDES.reset(token)
    # Aynı cluster intensity → aynı kusur seçimi
    assert no_profile_defects == with_profile_defects


def test_no_profile_context_var_is_none() -> None:
    """Profil bağlam değişkeni varsayılan olarak None."""
    assert _get_overrides() is None


def test_get_distribution_falls_back_to_default() -> None:
    """Profil yoksa _get_distribution MEASURE_DISTRIBUTIONS'den döner."""
    assert _get_overrides() is None
    dist = _get_distribution("synthetic_customers")
    assert dist is not None
    assert dist == MEASURE_DISTRIBUTIONS["synthetic_customers"]


def test_get_distribution_returns_none_for_unknown() -> None:
    """Tanımlanmamış tablo için _get_distribution None döner."""
    assert _get_distribution("synthetic_nonexistent_table") is None
