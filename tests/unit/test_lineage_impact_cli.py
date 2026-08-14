"""Lineage impact kanıt CLI uçtan uca testi."""

from __future__ import annotations

from io import StringIO
import json

from veri_kalitesi.lineage.cli import main


def test_lineage_impact_cli_emits_sourced_non_aggregated_evidence(tmp_path) -> None:  # type: ignore[no-untyped-def]
    input_path = tmp_path / "impact.json"
    input_path.write_text(
        json.dumps(
            {
                "policy": {
                    "version": "IMPACT_POLICY_V1",
                    "authoritative_monetary_source_refs": ["ledger:loss"],
                    "approved_formula_refs": ["formula:resolution-cost"],
                },
                "components": [
                    {
                        "component_code": "FINANCIAL",
                        "status": "OBSERVED",
                        "value": "125.50",
                        "unit": "TRY",
                        "source_ref": "ledger:loss",
                        "data_time": "2026-08-14T10:00:00+00:00",
                        "confidence_ref": "confidence:verified",
                    },
                    {"component_code": "CUSTOMER", "status": "UNKNOWN"},
                ],
            }
        ),
        encoding="utf-8",
    )
    output = StringIO()

    result = main((str(input_path),), stdout=output)

    payload = json.loads(output.getvalue())
    assert result == 0
    assert payload["supported_totals_by_unit"]["TRY"] == {
        "aggregated_statuses": ["CALCULATED", "OBSERVED"],
        "component_codes": ["FINANCIAL"],
        "total": "125.50",
    }
    assert payload["unknown_component_codes"] == ["CUSTOMER"]
    assert payload["total_impact_value"] is None
    assert payload["digest"].startswith("sha256:")


def test_lineage_impact_cli_downgrades_unsourced_observation_to_unknown(tmp_path) -> None:  # type: ignore[no-untyped-def]
    input_path = tmp_path / "impact.json"
    input_path.write_text(
        json.dumps(
            {
                "policy": {"version": "IMPACT_POLICY_V1"},
                "components": [
                    {
                        "component_code": "FINANCIAL",
                        "status": "OBSERVED",
                        "value": "125.50",
                        "unit": "TRY",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    output = StringIO()

    result = main((str(input_path),), stdout=output)

    assert result == 0
    payload = json.loads(output.getvalue())
    assert payload["unknown_component_codes"] == ["FINANCIAL"]
    assert payload["supported_totals_by_unit"] == {}
    assert "MISSING_SOURCE" in payload["components"][0]["reason_codes"]
