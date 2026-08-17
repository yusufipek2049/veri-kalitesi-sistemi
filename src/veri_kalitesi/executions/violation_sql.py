"""DQ_RULE_IR_V1 planlarının PostgreSQL ihlal sorgularına derlenmesi.

Her kural türü kendi ihlal tanımına sahiptir; SQL kural başına değil tür başına
yazılır. Burada üretilen sorgular tek sütunlu bir sayım döndürür ve ihlal eden
satır sayısını ifade eder. Tüm tanımlayıcılar ve değişmezler kaçışlanır,
desteklenmeyen tür fail-closed reddedilir.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Callable

from veri_kalitesi.executions.errors import ExecutionTechnicalError
from veri_kalitesi.rules.models import RuleType


SQL_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,62}")

SOURCE_ALIAS = "dq_source"
REFERENCE_ALIAS = "dq_reference"

# Biçim aileleri sistem tarafından tanımlanır; kullanıcı regex yazmaz.
# Desenler POSIX ARE söz dizimindedir ve ters bölü içermez, böylece
# standard_conforming_strings ayarından bağımsız olarak aynı anlamı taşırlar.
FORMAT_PATTERNS: Mapping[str, str] = {
    "EMAIL": r"^[^[:space:]@]+@[^[:space:]@]+[.][A-Za-z]{2,}$",
    "IBAN": r"^[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}$",
    "PHONE": r"^[+]?[0-9][0-9 ()-]{6,19}$",
    "URL": r"^https?://[^[:space:]]+$",
    "IP_V4": (
        r"^((25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])[.]){3}"
        r"(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])$"
    ),
    "IP_V6": (
        r"^(([0-9A-Fa-f]{1,4}:){7}[0-9A-Fa-f]{1,4}"
        r"|([0-9A-Fa-f]{1,4}:){1,7}:"
        r"|:(:[0-9A-Fa-f]{1,4}){1,7}"
        r"|([0-9A-Fa-f]{1,4}:){1,6}(:[0-9A-Fa-f]{1,4}){1}"
        r"|([0-9A-Fa-f]{1,4}:){1,5}(:[0-9A-Fa-f]{1,4}){1,2}"
        r"|([0-9A-Fa-f]{1,4}:){1,4}(:[0-9A-Fa-f]{1,4}){1,3}"
        r"|([0-9A-Fa-f]{1,4}:){1,3}(:[0-9A-Fa-f]{1,4}){1,4}"
        r"|([0-9A-Fa-f]{1,4}:){1,2}(:[0-9A-Fa-f]{1,4}){1,5}"
        r"|[0-9A-Fa-f]{1,4}:(:[0-9A-Fa-f]{1,4}){1,6}"
        r"|::)$"
    ),
    "UUID": r"^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$",
    "DATE_ISO": r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$",
    "TIMESTAMP_ISO": (
        r"^[0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9]{2}:[0-9]{2}:[0-9]{2}"
        r"([.][0-9]{1,6})?(Z|[+-][0-9]{2}:?[0-9]{2})?$"
    ),
}

# Kaynağın yanında ikinci bir veri kümesi gerektiren türler.
REFERENCE_RULE_TYPES = frozenset({RuleType.REFERENTIAL_INTEGRITY, RuleType.CROSS_TABLE_CONSISTENCY})


def requires_reference(rule_type: RuleType) -> bool:
    """Kural türünün ikinci bir veri kümesine ihtiyaç duyup duymadığını bildirir."""
    return rule_type in REFERENCE_RULE_TYPES


def quote_identifier(name: Any) -> str:
    """Tanımlayıcıyı doğrular ve çift tırnak içine alır."""
    if not isinstance(name, str) or not SQL_IDENTIFIER.fullmatch(name):
        raise ExecutionTechnicalError(f"Rule identifier is invalid: {name!r}", retryable=False)
    return f'"{name}"'


def quote_literal(value: Any) -> str:
    """Metin değişmezini kaçışlar."""
    text = str(value)
    if "\x00" in text:
        raise ExecutionTechnicalError("Rule literal contains a null byte.", retryable=False)
    escaped = text.replace("'", "''")
    return f"'{escaped}'"


def alias_relation(relation: str, alias: str) -> str:
    """İlişkiye takma ad verir; kapsamlanmış alt sorgunun mevcut adını değiştirir."""
    quoted = quote_identifier(alias)
    scoped_suffix = ' AS "scoped_data"'
    if relation.endswith(scoped_suffix):
        return f"{relation[: -len(scoped_suffix)]} AS {quoted}"
    return f"{relation} AS {quoted}"


def build_violation_query(
    *,
    rule_type: RuleType,
    definition: Mapping[str, Any],
    table: str,
    reference_table: str | None = None,
) -> str:
    """Kural türü ve IR planından ihlal sayım sorgusunu derler."""
    builder = _BUILDERS.get(rule_type)
    if builder is None:
        raise ExecutionTechnicalError(
            f"Unsupported template rule type: {rule_type.value}",
            retryable=False,
        )
    if requires_reference(rule_type) and not reference_table:
        raise ExecutionTechnicalError(
            f"Rule type {rule_type.value} requires a reference relation.",
            retryable=False,
        )
    return builder(_SqlContext(definition=definition, table=table, reference_table=reference_table))


@dataclass(frozen=True)
class _SqlContext:
    definition: Mapping[str, Any]
    table: str
    reference_table: str | None


# ── Tek alanlı sütun kuralları ──────────────────────────────────────────


def _required(ctx: _SqlContext) -> str:
    field = _field(ctx)
    return f"SELECT COUNT(*) FROM {ctx.table} WHERE {field} IS NULL"


def _range(ctx: _SqlContext) -> str:
    field = _field(ctx)
    conditions: list[str] = []
    minimum = _number(ctx.definition.get("minimum"), "minimum")
    maximum = _number(ctx.definition.get("maximum"), "maximum")
    if minimum is not None:
        conditions.append(f"{field} < {minimum}")
    if maximum is not None:
        conditions.append(f"{field} > {maximum}")
    if not conditions:
        raise ExecutionTechnicalError("Range rule lacks minimum and maximum.", retryable=False)
    return _column_violation(ctx.table, field, " OR ".join(conditions))


def _regex(ctx: _SqlContext) -> str:
    field = _field(ctx)
    pattern = ctx.definition.get("pattern")
    if not isinstance(pattern, str) or not pattern:
        raise ExecutionTechnicalError("Regex rule lacks a pattern.", retryable=False)
    return _column_violation(ctx.table, field, f"{field}::text !~ {quote_literal(pattern)}")


def _freshness(ctx: _SqlContext) -> str:
    field = _field(ctx)
    max_age_minutes = ctx.definition.get("max_age_minutes")
    if (
        isinstance(max_age_minutes, bool)
        or not isinstance(max_age_minutes, int)
        or max_age_minutes <= 0
    ):
        raise ExecutionTechnicalError(
            "Freshness rule lacks a positive max_age_minutes.",
            retryable=False,
        )
    threshold = f"NOW() - INTERVAL '{max_age_minutes} minutes'"
    return _column_violation(ctx.table, field, f"{field} < {threshold}")


def _allowed_values(ctx: _SqlContext) -> str:
    field = _field(ctx)
    allowed = ctx.definition.get("allowed_values")
    if not isinstance(allowed, list | tuple) or not allowed:
        raise ExecutionTechnicalError("Allowed values rule lacks a value set.", retryable=False)
    values = ", ".join(quote_literal(item) for item in allowed)
    return _column_violation(ctx.table, field, f"{field}::text NOT IN ({values})")


def _length_check(ctx: _SqlContext) -> str:
    field = _field(ctx)
    conditions: list[str] = []
    minimum = _bound(ctx.definition.get("min_length"), "min_length")
    maximum = _bound(ctx.definition.get("max_length"), "max_length")
    if minimum is not None:
        conditions.append(f"LENGTH({field}::text) < {minimum}")
    if maximum is not None:
        conditions.append(f"LENGTH({field}::text) > {maximum}")
    if not conditions:
        raise ExecutionTechnicalError(
            "Length rule lacks min_length and max_length.",
            retryable=False,
        )
    return _column_violation(ctx.table, field, " OR ".join(conditions))


def _format_check(ctx: _SqlContext) -> str:
    field = _field(ctx)
    format_type = ctx.definition.get("format_type")
    pattern = FORMAT_PATTERNS.get(format_type) if isinstance(format_type, str) else None
    if pattern is None:
        raise ExecutionTechnicalError(
            f"Unsupported format type: {format_type!r}",
            retryable=False,
        )
    return _column_violation(ctx.table, field, f"{field}::text !~ {quote_literal(pattern)}")


# ── Veri kümesi kuralları ───────────────────────────────────────────────


def _unique(ctx: _SqlContext) -> str:
    fields = _unique_fields(ctx.definition)
    columns = ", ".join(fields)
    not_null = " AND ".join(f"{field} IS NOT NULL" for field in fields)
    group_count = quote_identifier("dq_group_count")
    groups = quote_identifier("dq_duplicate_groups")
    return (
        f"SELECT COALESCE(SUM({group_count} - 1), 0)::bigint FROM ("
        f"SELECT COUNT(*) AS {group_count} FROM {ctx.table} "
        f"WHERE {not_null} GROUP BY {columns} HAVING COUNT(*) > 1"
        f") AS {groups}"
    )


# ── Referans kuralları ──────────────────────────────────────────────────


def _referential_integrity(ctx: _SqlContext) -> str:
    return _reference_violation(ctx, matched_is_violation=False)


def _cross_table_consistency(ctx: _SqlContext) -> str:
    comparison = ctx.definition.get("comparison", "EQUALS")
    if comparison not in {"EQUALS", "NOT_EQUALS"}:
        raise ExecutionTechnicalError(
            f"Unsupported cross-table comparison: {comparison!r}",
            retryable=False,
        )
    # EQUALS: eşleşen satır bulunmaması ihlaldir.
    # NOT_EQUALS: eşleşen satır bulunması ihlaldir.
    return _reference_violation(ctx, matched_is_violation=comparison == "NOT_EQUALS")


def _reference_violation(ctx: _SqlContext, *, matched_is_violation: bool) -> str:
    source_fields = _identifiers(ctx.definition, "source_field_ids")
    reference_fields = _identifiers(ctx.definition, "reference_field_ids")
    if len(source_fields) != len(reference_fields):
        raise ExecutionTechnicalError(
            "Source and reference field counts must match.",
            retryable=False,
        )
    source = alias_relation(ctx.table, SOURCE_ALIAS)
    reference = alias_relation(str(ctx.reference_table), REFERENCE_ALIAS)
    source_alias = quote_identifier(SOURCE_ALIAS)
    reference_alias = quote_identifier(REFERENCE_ALIAS)
    not_null = " AND ".join(f"{source_alias}.{field} IS NOT NULL" for field in source_fields)
    pairs = " AND ".join(
        f"{reference_alias}.{reference_field} = {source_alias}.{source_field}"
        for source_field, reference_field in zip(source_fields, reference_fields)
    )
    existence = "EXISTS" if matched_is_violation else "NOT EXISTS"
    return (
        f"SELECT COUNT(*) FROM {source} "
        f"WHERE {not_null} AND {existence} ("
        f"SELECT 1 FROM {reference} WHERE {pairs}"
        f")"
    )


# ── Yardımcılar ─────────────────────────────────────────────────────────


def _column_violation(table: str, field: str, condition: str) -> str:
    """NULL değerleri kapsam dışı bırakan sütun ihlali sayımı."""
    return f"SELECT COUNT(*) FROM {table} WHERE {field} IS NOT NULL AND ({condition})"


def _field(ctx: _SqlContext) -> str:
    field_id = ctx.definition.get("field_id")
    if not field_id:
        raise ExecutionTechnicalError(
            "Rule definition lacks field_id for template query.",
            retryable=False,
        )
    return quote_identifier(field_id)


def _unique_fields(definition: Mapping[str, Any]) -> tuple[str, ...]:
    field_ids = definition.get("field_ids")
    if isinstance(field_ids, list | tuple) and field_ids:
        return tuple(quote_identifier(item) for item in field_ids)
    field_id = definition.get("field_id")
    if field_id:
        return (quote_identifier(field_id),)
    raise ExecutionTechnicalError("Unique rule lacks field identifiers.", retryable=False)


def _identifiers(definition: Mapping[str, Any], key: str) -> tuple[str, ...]:
    values = definition.get(key)
    if not isinstance(values, list | tuple) or not values:
        raise ExecutionTechnicalError(f"Rule definition lacks {key}.", retryable=False)
    return tuple(quote_identifier(item) for item in values)


def _number(value: Any, key: str) -> int | float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ExecutionTechnicalError(f"Range {key} must be numeric.", retryable=False)
    return value


def _bound(value: Any, key: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ExecutionTechnicalError(
            f"Length {key} must be a non-negative integer.",
            retryable=False,
        )
    return value


_BUILDERS: Mapping[RuleType, Callable[[_SqlContext], str]] = {
    RuleType.REQUIRED: _required,
    RuleType.UNIQUE: _unique,
    RuleType.RANGE: _range,
    RuleType.REGEX: _regex,
    RuleType.FRESHNESS: _freshness,
    RuleType.ALLOWED_VALUES: _allowed_values,
    RuleType.LENGTH_CHECK: _length_check,
    RuleType.FORMAT_CHECK: _format_check,
    RuleType.REFERENTIAL_INTEGRITY: _referential_integrity,
    RuleType.CROSS_TABLE_CONSISTENCY: _cross_table_consistency,
}
