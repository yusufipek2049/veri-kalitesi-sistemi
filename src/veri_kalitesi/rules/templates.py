"""Hazır kural şablonlarının doğrulama ve yürütme planları."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from veri_kalitesi.data_minimum_evidence import (
    DataMinimumEvidenceError,
    validate_query_reference,
)
from veri_kalitesi.data_sources.postgresql import is_read_only_sql
from veri_kalitesi.rules.errors import RuleValidationError
from veri_kalitesi.rules.models import RuleDefinitionSource, RuleScopeType, RuleType


def build_rule_plan(rule_type: RuleType, parameters: Mapping[str, Any]) -> dict[str, Any]:
    builders = {
        RuleType.REQUIRED: _required_plan,
        RuleType.UNIQUE: _unique_plan,
        RuleType.RANGE: _range_plan,
        RuleType.REGEX: _regex_plan,
        RuleType.FRESHNESS: _freshness_plan,
        RuleType.REFERENTIAL_INTEGRITY: _referential_plan,
        RuleType.CROSS_TABLE_CONSISTENCY: _cross_table_plan,
        RuleType.CUSTOM_SQL: _custom_sql_plan,
        RuleType.ALLOWED_VALUES: _allowed_values_plan,
        RuleType.LENGTH_CHECK: _length_check_plan,
        RuleType.FORMAT_CHECK: _format_check_plan,
    }
    plan = builders[rule_type](parameters)
    scope_type = _scope_type(rule_type, parameters)
    plan.update(
        {
            "ir_version": "DQ_RULE_IR_V1",
            "definition_source": (
                RuleDefinitionSource.CUSTOM_SQL.value
                if rule_type is RuleType.CUSTOM_SQL
                else RuleDefinitionSource.TEMPLATE.value
            ),
            "scope_type": scope_type.value,
            "evidence_contract": "DQ_VIOLATION_EVIDENCE_V1",
        }
    )
    return plan


def referenced_fields(plan: Mapping[str, Any]) -> tuple[str, ...]:
    values: list[str] = []
    for key in ("field_id", "field_ids", "source_field_ids"):
        value = plan.get(key)
        if isinstance(value, str):
            values.append(value)
        elif isinstance(value, tuple | list):
            values.extend(str(item) for item in value)
    return tuple(dict.fromkeys(values))


def reference_scope(plan: Mapping[str, Any]) -> tuple[str, tuple[str, ...]] | None:
    dataset_id = plan.get("reference_dataset_id")
    field_ids = plan.get("reference_field_ids")
    if not isinstance(dataset_id, str) or not isinstance(field_ids, tuple | list):
        return None
    return dataset_id, tuple(str(item) for item in field_ids)


def _required_plan(parameters: Mapping[str, Any]) -> dict[str, Any]:
    return {"operator": "IS_NOT_NULL", "field_id": _identifier(parameters, "field_id")}


def _unique_plan(parameters: Mapping[str, Any]) -> dict[str, Any]:
    return {"operator": "UNIQUE", "field_ids": _identifiers(parameters, "field_ids")}


def _range_plan(parameters: Mapping[str, Any]) -> dict[str, Any]:
    field_id = _identifier(parameters, "field_id")
    minimum = parameters.get("minimum")
    maximum = parameters.get("maximum")
    if minimum is None and maximum is None:
        raise RuleValidationError("Range rule requires minimum or maximum.")
    if minimum is not None and not _is_number(minimum):
        raise RuleValidationError("Range minimum must be numeric.")
    if maximum is not None and not _is_number(maximum):
        raise RuleValidationError("Range maximum must be numeric.")
    if minimum is not None and maximum is not None and minimum > maximum:
        raise RuleValidationError("Range minimum must not exceed maximum.")
    return {"operator": "BETWEEN", "field_id": field_id, "minimum": minimum, "maximum": maximum}


def _regex_plan(parameters: Mapping[str, Any]) -> dict[str, Any]:
    field_id = _identifier(parameters, "field_id")
    pattern = parameters.get("pattern")
    if not isinstance(pattern, str) or not pattern or len(pattern) > 500:
        raise RuleValidationError("Regex pattern must contain 1 to 500 characters.")
    try:
        re.compile(pattern)
    except re.error as exc:
        raise RuleValidationError("Regex pattern is invalid.") from exc
    return {"operator": "REGEX_MATCH", "field_id": field_id, "pattern": pattern}


def _freshness_plan(parameters: Mapping[str, Any]) -> dict[str, Any]:
    field_id = _identifier(parameters, "field_id")
    max_age_minutes = parameters.get("max_age_minutes")
    if (
        isinstance(max_age_minutes, bool)
        or not isinstance(max_age_minutes, int)
        or max_age_minutes <= 0
    ):
        raise RuleValidationError("Freshness max_age_minutes must be a positive integer.")
    timezone_name = parameters.get("timezone")
    if not isinstance(timezone_name, str) or not timezone_name:
        raise RuleValidationError("Freshness timezone is required.")
    try:
        ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise RuleValidationError("Freshness timezone must be a valid IANA timezone.") from exc
    return {
        "operator": "MAX_AGE",
        "field_id": field_id,
        "max_age_minutes": max_age_minutes,
        "timezone": timezone_name,
    }


def _referential_plan(parameters: Mapping[str, Any]) -> dict[str, Any]:
    return _reference_plan("REFERENCE_EXISTS", parameters)


def _cross_table_plan(parameters: Mapping[str, Any]) -> dict[str, Any]:
    plan = _reference_plan("CROSS_TABLE_EQUALS", parameters)
    comparison = parameters.get("comparison", "EQUALS")
    if comparison not in {"EQUALS", "NOT_EQUALS"}:
        raise RuleValidationError("Cross-table comparison is invalid.")
    plan["comparison"] = comparison
    return plan


def _reference_plan(operator: str, parameters: Mapping[str, Any]) -> dict[str, Any]:
    source_fields = _identifiers(parameters, "source_field_ids")
    reference_fields = _identifiers(parameters, "reference_field_ids")
    if len(source_fields) != len(reference_fields):
        raise RuleValidationError("Source and reference field counts must match.")
    return {
        "operator": operator,
        "source_field_ids": source_fields,
        "reference_dataset_id": _identifier(parameters, "reference_dataset_id"),
        "reference_field_ids": reference_fields,
    }


def _custom_sql_plan(parameters: Mapping[str, Any]) -> dict[str, Any]:
    sql = parameters.get("sql")
    if not isinstance(sql, str) or not is_read_only_sql(sql):
        raise RuleValidationError("Custom SQL must be a single read-only statement.")
    timeout_seconds = parameters.get("timeout_seconds")
    row_limit = parameters.get("row_limit")
    query_reference = parameters.get("query_reference")
    if (
        isinstance(timeout_seconds, bool)
        or not isinstance(timeout_seconds, int)
        or timeout_seconds <= 0
    ):
        raise RuleValidationError("Custom SQL timeout_seconds must be a positive integer.")
    if isinstance(row_limit, bool) or not isinstance(row_limit, int) or row_limit <= 0:
        raise RuleValidationError("Custom SQL row_limit must be a positive integer.")
    if _contains_bind_value(parameters):
        raise RuleValidationError("Custom SQL bind values must not be persisted in rule IR.")
    try:
        safe_query_reference = validate_query_reference(query_reference)
    except DataMinimumEvidenceError as exc:
        raise RuleValidationError("Custom SQL query_reference is invalid.") from exc
    return {
        "operator": "CUSTOM_SQL",
        "sql": sql.strip(),
        "timeout_seconds": timeout_seconds,
        "row_limit": row_limit,
        "query_reference": safe_query_reference,
    }


# ── ALLOWED_VALUES ─────────────────────────────────────────────────────

_KNOWN_FORMAT_TYPES: frozenset[str] = frozenset(
    {"EMAIL", "IBAN", "PHONE", "URL", "IP_V4", "IP_V6", "UUID", "DATE_ISO", "TIMESTAMP_ISO"}
)


def _allowed_values_plan(parameters: Mapping[str, Any]) -> dict[str, Any]:
    field_id = _identifier(parameters, "field_id")
    allowed = parameters.get("allowed_values")
    if not isinstance(allowed, list | tuple) or not allowed:
        raise RuleValidationError("allowed_values must contain at least one value.")
    string_values = tuple(str(item) for item in allowed)
    if len(set(string_values)) != len(string_values):
        raise RuleValidationError("allowed_values must contain unique entries.")
    return {"operator": "IN_SET", "field_id": field_id, "allowed_values": string_values}


# ── LENGTH_CHECK ───────────────────────────────────────────────────────


def _length_check_plan(parameters: Mapping[str, Any]) -> dict[str, Any]:
    field_id = _identifier(parameters, "field_id")
    min_length = parameters.get("min_length")
    max_length = parameters.get("max_length")
    if min_length is None and max_length is None:
        raise RuleValidationError("Length rule requires min_length or max_length.")
    if min_length is not None and (
        isinstance(min_length, bool) or not isinstance(min_length, int) or min_length < 0
    ):
        raise RuleValidationError("Length min_length must be a non-negative integer.")
    if max_length is not None and (
        isinstance(max_length, bool) or not isinstance(max_length, int) or max_length < 0
    ):
        raise RuleValidationError("Length max_length must be a non-negative integer.")
    if min_length is not None and max_length is not None and min_length > max_length:
        raise RuleValidationError("Length min_length must not exceed max_length.")
    return {
        "operator": "LENGTH_BETWEEN",
        "field_id": field_id,
        "min_length": min_length,
        "max_length": max_length,
    }


# ── FORMAT_CHECK ───────────────────────────────────────────────────────


def _format_check_plan(parameters: Mapping[str, Any]) -> dict[str, Any]:
    field_id = _identifier(parameters, "field_id")
    format_type = parameters.get("format_type")
    if not isinstance(format_type, str) or not format_type.strip():
        raise RuleValidationError("format_type is required.")
    format_type = format_type.strip().upper()
    if format_type not in _KNOWN_FORMAT_TYPES:
        raise RuleValidationError(f"format_type must be one of {sorted(_KNOWN_FORMAT_TYPES)}.")
    return {"operator": "FORMAT_MATCH", "field_id": field_id, "format_type": format_type}


def _scope_type(rule_type: RuleType, parameters: Mapping[str, Any]) -> RuleScopeType:
    defaults = {
        RuleType.REQUIRED: RuleScopeType.COLUMN,
        RuleType.UNIQUE: RuleScopeType.DATASET,
        RuleType.RANGE: RuleScopeType.COLUMN,
        RuleType.REGEX: RuleScopeType.COLUMN,
        RuleType.FRESHNESS: RuleScopeType.TIME_SERIES,
        RuleType.REFERENTIAL_INTEGRITY: RuleScopeType.REFERENCE,
        RuleType.CROSS_TABLE_CONSISTENCY: RuleScopeType.CROSS_TABLE,
        RuleType.ALLOWED_VALUES: RuleScopeType.COLUMN,
        RuleType.LENGTH_CHECK: RuleScopeType.COLUMN,
        RuleType.FORMAT_CHECK: RuleScopeType.COLUMN,
    }
    if rule_type is not RuleType.CUSTOM_SQL:
        return defaults[rule_type]
    value = parameters.get("scope_type")
    try:
        return RuleScopeType(str(value))
    except (TypeError, ValueError) as exc:
        raise RuleValidationError(
            "Custom SQL scope_type must explicitly identify a supported rule scope."
        ) from exc


def _contains_bind_value(parameters: Mapping[str, Any]) -> bool:
    forbidden = {"bind", "binds", "bind_value", "bind_values", "parameters", "params"}
    return any(str(key).lower() in forbidden for key in parameters)


def _identifier(parameters: Mapping[str, Any], key: str) -> str:
    value = parameters.get(key)
    if not isinstance(value, str) or not value.strip():
        raise RuleValidationError(f"{key} is required.")
    return value.strip()


def _identifiers(parameters: Mapping[str, Any], key: str) -> tuple[str, ...]:
    value = parameters.get(key)
    if not isinstance(value, list | tuple) or not value:
        raise RuleValidationError(f"{key} must contain at least one field.")
    identifiers = tuple(str(item).strip() for item in value)
    if any(not item for item in identifiers) or len(set(identifiers)) != len(identifiers):
        raise RuleValidationError(f"{key} must contain unique field identifiers.")
    return identifiers


def _is_number(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, int | float)
