"""Kaynaklı etki değerlendirmesi için çevrimdışı kanıt CLI'ı."""

from __future__ import annotations

import argparse
from datetime import datetime
from decimal import Decimal
import json
from pathlib import Path
from typing import Any, Mapping, Sequence, TextIO
import sys

from veri_kalitesi.lineage.errors import LineageValidationError
from veri_kalitesi.lineage.impact import (
    ImpactComponent,
    ImpactEvidenceStatus,
    ImpactSourcePolicy,
    assess_impact,
)


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """JSON bileşenlerinden sürümlü, kaynaklı etki kanıtı üretir."""

    output = stdout or sys.stdout
    error_output = stderr or sys.stderr
    parser = argparse.ArgumentParser(description="Build a sourced impact assessment.")
    parser.add_argument("input", type=Path)
    arguments = parser.parse_args(argv)
    try:
        payload = json.loads(arguments.input.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise LineageValidationError("Impact input must be an object.")
        raw_components = payload.get("components")
        if not isinstance(raw_components, list):
            raise LineageValidationError("Impact components must be a list.")
        policy = _policy(payload.get("policy"))
        document = assess_impact(
            tuple(_component(item) for item in raw_components),
            policy=policy,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, LineageValidationError, ValueError) as exc:
        _write_json(error_output, {"status": "BLOCKED", "error_class": type(exc).__name__})
        return 2
    _write_json(output, document)
    return 0


def _component(value: object) -> ImpactComponent:
    if not isinstance(value, dict):
        raise LineageValidationError("Impact component must be an object.")
    payload: Mapping[str, Any] = value
    raw_value = payload.get("value")
    raw_time = payload.get("data_time")
    return ImpactComponent(
        component_code=str(payload.get("component_code", "")),
        status=ImpactEvidenceStatus(str(payload.get("status", ""))),
        value=Decimal(str(raw_value)) if raw_value is not None else None,
        unit=str(payload["unit"]) if payload.get("unit") is not None else None,
        source_ref=(str(payload["source_ref"]) if payload.get("source_ref") is not None else None),
        formula_ref=(
            str(payload["formula_ref"])
            if payload.get("formula_ref") is not None
            else None
        ),
        data_time=datetime.fromisoformat(str(raw_time)) if raw_time is not None else None,
        confidence_ref=(
            str(payload["confidence_ref"])
            if payload.get("confidence_ref") is not None
            else None
        ),
    )


def _policy(value: object) -> ImpactSourcePolicy | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise LineageValidationError("Impact policy must be an object.")
    return ImpactSourcePolicy(
        version=str(value.get("version", "")),
        authoritative_monetary_source_refs=frozenset(
            str(item) for item in value.get("authoritative_monetary_source_refs", ())
        ),
        approved_formula_refs=frozenset(
            str(item) for item in value.get("approved_formula_refs", ())
        ),
    )


def _write_json(stream: TextIO, payload: object) -> None:
    stream.write(json.dumps(payload, ensure_ascii=True, sort_keys=True))
    stream.write("\n")
