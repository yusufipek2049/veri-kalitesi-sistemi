"""FR-089–FR-095, UC-017 ve AC/TS-048–056 PostgreSQL dataset testleri."""

from __future__ import annotations

from dataclasses import replace

import pytest

from veri_kalitesi.synthetic_data.errors import SyntheticDataValidationError
from veri_kalitesi.synthetic_data.postgresql_dataset import (
    DEFAULT_ROW_COUNT,
    GENERATOR_VERSION,
    MAX_ROW_COUNT,
    MIN_ROW_COUNT,
    SCENARIO_DEFECT_RATIOS,
    TABLE_SPECS,
    PostgreSQLSyntheticDatasetManager,
    _canonical_row,
    _scenario_rates,
    build_argument_parser,
    build_source_row,
    validate_generation_request,
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

    assert GENERATOR_VERSION == "RELATIONAL_BANKING_GENERATOR_V1"
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
