"""Hazır kural şablonlarının doğrulama ve yürütme planları."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from veri_kalitesi.data_sources.postgresql import is_read_only_sql
from veri_kalitesi.rules.errors import RuleValidationError
from veri_kalitesi.rules.models import RuleType


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
    }
    return builders[rule_type](parameters)


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
    return {"operator": "CUSTOM_SQL", "sql": sql.strip()}


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
