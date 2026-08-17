from __future__ import annotations

import pytest

from veri_kalitesi.executions.errors import ExecutionTechnicalError
from veri_kalitesi.executions.violation_sql import (
    _BUILDERS,
    FORMAT_PATTERNS,
    alias_relation,
    build_violation_query,
    quote_literal,
    requires_reference,
)
from veri_kalitesi.rules.models import RuleType
from veri_kalitesi.rules.templates import build_rule_plan


TABLE = '"dq"."accounts"'
SCOPED = (
    '(SELECT * FROM "dq"."accounts" WHERE "observed_on" = DATE \'2026-08-01\') AS "scoped_data"'
)


def _query(rule_type: RuleType, parameters: dict, **kwargs) -> str:
    """Şablonun ürettiği gerçek IR planından sorgu derler."""
    plan = build_rule_plan(rule_type, parameters)
    return build_violation_query(
        rule_type=rule_type, definition=plan, table=kwargs.pop("table", TABLE), **kwargs
    )


# ── Sütun kuralları ─────────────────────────────────────────────────────


def test_required_counts_null_rows() -> None:
    assert _query(RuleType.REQUIRED, {"field_id": "iban"}) == (
        'SELECT COUNT(*) FROM "dq"."accounts" WHERE "iban" IS NULL'
    )


def test_range_applies_both_bounds_and_skips_nulls() -> None:
    sql = _query(RuleType.RANGE, {"field_id": "bakiye", "minimum": 0, "maximum": 100})

    assert sql == (
        'SELECT COUNT(*) FROM "dq"."accounts" '
        'WHERE "bakiye" IS NOT NULL AND ("bakiye" < 0 OR "bakiye" > 100)'
    )


def test_range_with_single_bound_emits_single_condition() -> None:
    sql = _query(RuleType.RANGE, {"field_id": "bakiye", "minimum": 0})

    assert '"bakiye" < 0' in sql
    assert ">" not in sql.split("AND", 1)[1]


def test_allowed_values_casts_to_text_and_escapes_quotes() -> None:
    sql = _query(
        RuleType.ALLOWED_VALUES,
        {"field_id": "durum", "allowed_values": ["AKTIF", "PAS'IF"]},
    )

    assert sql == (
        'SELECT COUNT(*) FROM "dq"."accounts" '
        "WHERE \"durum\" IS NOT NULL AND (\"durum\"::text NOT IN ('AKTIF', 'PAS''IF'))"
    )


def test_length_check_measures_text_length() -> None:
    sql = _query(RuleType.LENGTH_CHECK, {"field_id": "tckn", "min_length": 11, "max_length": 11})

    assert 'LENGTH("tckn"::text) < 11' in sql
    assert 'LENGTH("tckn"::text) > 11' in sql


def test_format_check_uses_system_pattern() -> None:
    sql = _query(RuleType.FORMAT_CHECK, {"field_id": "eposta", "format_type": "EMAIL"})

    assert f'"eposta"::text !~ {quote_literal(FORMAT_PATTERNS["EMAIL"])}' in sql


@pytest.mark.parametrize("format_type", sorted(FORMAT_PATTERNS))
def test_every_known_format_type_compiles(format_type: str) -> None:
    sql = _query(RuleType.FORMAT_CHECK, {"field_id": "alan", "format_type": format_type})

    assert sql.startswith('SELECT COUNT(*) FROM "dq"."accounts"')
    assert "\\" not in sql


def test_regex_escapes_pattern_quotes() -> None:
    sql = _query(RuleType.REGEX, {"field_id": "ad", "pattern": "^o'brien$"})

    assert "'^o''brien$'" in sql


def test_freshness_uses_max_age_interval() -> None:
    sql = _query(
        RuleType.FRESHNESS,
        {"field_id": "guncellendi", "max_age_minutes": 60, "timezone": "Europe/Istanbul"},
    )

    assert "\"guncellendi\" < NOW() - INTERVAL '60 minutes'" in sql


# ── Veri kümesi kuralları ───────────────────────────────────────────────


def test_unique_counts_excess_rows_for_composite_key() -> None:
    sql = _query(RuleType.UNIQUE, {"field_ids": ["musteri_no", "urun_kodu"]})

    assert sql == (
        'SELECT COALESCE(SUM("dq_group_count" - 1), 0)::bigint FROM ('
        'SELECT COUNT(*) AS "dq_group_count" FROM "dq"."accounts" '
        'WHERE "musteri_no" IS NOT NULL AND "urun_kodu" IS NOT NULL '
        'GROUP BY "musteri_no", "urun_kodu" HAVING COUNT(*) > 1'
        ') AS "dq_duplicate_groups"'
    )


def test_unique_accepts_legacy_single_field_definition() -> None:
    sql = build_violation_query(
        rule_type=RuleType.UNIQUE,
        definition={"operator": "UNIQUE", "field_id": "musteri_no"},
        table=TABLE,
    )

    assert 'GROUP BY "musteri_no"' in sql


# ── Referans kuralları ──────────────────────────────────────────────────


_REFERENCE_PARAMETERS = {
    "source_field_ids": ["musteri_no"],
    "reference_dataset_id": "dataset-2",
    "reference_field_ids": ["no"],
}


def test_referential_integrity_counts_orphan_rows() -> None:
    sql = _query(
        RuleType.REFERENTIAL_INTEGRITY,
        dict(_REFERENCE_PARAMETERS),
        reference_table='"dq"."customers"',
    )

    assert sql == (
        'SELECT COUNT(*) FROM "dq"."accounts" AS "dq_source" '
        'WHERE "dq_source"."musteri_no" IS NOT NULL AND NOT EXISTS ('
        'SELECT 1 FROM "dq"."customers" AS "dq_reference" '
        'WHERE "dq_reference"."no" = "dq_source"."musteri_no")'
    )


def test_cross_table_not_equals_inverts_existence() -> None:
    sql = _query(
        RuleType.CROSS_TABLE_CONSISTENCY,
        dict(_REFERENCE_PARAMETERS) | {"comparison": "NOT_EQUALS"},
        reference_table='"dq"."customers"',
    )

    assert "AND EXISTS (" in sql
    assert "NOT EXISTS" not in sql


def test_reference_rule_reuses_scoped_relation_alias() -> None:
    sql = _query(
        RuleType.REFERENTIAL_INTEGRITY,
        dict(_REFERENCE_PARAMETERS),
        table=SCOPED,
        reference_table='"dq"."customers"',
    )

    assert '"observed_on" = DATE \'2026-08-01\') AS "dq_source"' in sql
    assert "scoped_data" not in sql


def test_reference_rule_without_reference_table_fails_closed() -> None:
    with pytest.raises(ExecutionTechnicalError, match="requires a reference relation"):
        _query(RuleType.REFERENTIAL_INTEGRITY, dict(_REFERENCE_PARAMETERS))


# ── Güvenlik ve fail-closed davranışı ───────────────────────────────────


@pytest.mark.parametrize(
    "field_id",
    ['iban" IS NULL OR "1', "1_alan", "", "alan; DROP TABLE dq.accounts", "a" * 64],
)
def test_invalid_field_identifier_fails_closed(field_id: str) -> None:
    with pytest.raises(ExecutionTechnicalError):
        build_violation_query(
            rule_type=RuleType.REQUIRED,
            definition={"field_id": field_id},
            table=TABLE,
        )


def test_custom_sql_is_not_compiled_from_a_template() -> None:
    with pytest.raises(ExecutionTechnicalError, match="Unsupported template rule type"):
        build_violation_query(rule_type=RuleType.CUSTOM_SQL, definition={}, table=TABLE)


def test_every_template_rule_type_has_a_builder() -> None:
    """CUSTOM_SQL dışındaki her tür yürütülebilir olmalı.

    Plan üretip yürütememek kabul edilemez.
    """
    template_types = {item for item in RuleType if item is not RuleType.CUSTOM_SQL}

    assert set(_BUILDERS) == template_types


def test_requires_reference_marks_only_two_way_rules() -> None:
    assert requires_reference(RuleType.REFERENTIAL_INTEGRITY)
    assert requires_reference(RuleType.CROSS_TABLE_CONSISTENCY)
    assert not requires_reference(RuleType.REQUIRED)


def test_alias_relation_quotes_plain_table() -> None:
    assert alias_relation(TABLE, "dq_source") == '"dq"."accounts" AS "dq_source"'
