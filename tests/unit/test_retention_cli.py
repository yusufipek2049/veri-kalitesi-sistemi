"""Retention veri-minimum CLI uçtan uca testleri."""

from __future__ import annotations

from io import StringIO
import json

from veri_kalitesi.retention.cli import main


def test_retention_cli_evaluates_against_explicit_hold_database_without_identifier_leak(
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
    output = StringIO()

    result = main(
        (
            "--legal-hold-database",
            str(tmp_path / "legal-holds.sqlite3"),
            "--record-reference-id",
            "customer-sensitive-reference",
            "--record-class",
            "BANKING_RECORD",
            "--retention-trigger-at",
            "2020-01-01T00:00:00+00:00",
            "--as-of",
            "2026-08-14T00:00:00+00:00",
        ),
        stdout=output,
    )

    payload = json.loads(output.getvalue())
    assert result == 0
    assert payload["status"] == "EVALUATED"
    assert payload["disposition"] == "RETAIN"
    assert payload["policy_version"] == "RETENTION_POLICY_2026_07_PROVISIONAL_V1"
    assert "record_reference_id" not in payload
    assert "customer-sensitive-reference" not in output.getvalue()


def test_retention_cli_fails_closed_for_naive_timestamps(tmp_path) -> None:  # type: ignore[no-untyped-def]
    errors = StringIO()

    result = main(
        (
            "--legal-hold-database",
            str(tmp_path / "legal-holds.sqlite3"),
            "--record-reference-id",
            "record-1",
            "--record-class",
            "BANKING_RECORD",
            "--retention-trigger-at",
            "2020-01-01T00:00:00",
            "--as-of",
            "2026-08-14T00:00:00+00:00",
        ),
        stderr=errors,
    )

    assert result == 2
    assert json.loads(errors.getvalue()) == {
        "status": "BLOCKED",
        "error_class": "RetentionValidationError",
    }
