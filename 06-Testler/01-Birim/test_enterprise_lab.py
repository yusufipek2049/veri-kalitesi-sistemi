from __future__ import annotations

import json
from pathlib import Path

import pytest

from veri_kalitesi.enterprise_lab import (
    EnterpriseLabConfigurationError,
    verify_enterprise_lab_configuration,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CONFIGURATION_PATH = (
    REPOSITORY_ROOT / "infrastructure" / "enterprise-lab" / "config" / "environment.json"
)


def test_enterprise_lab_01_accepts_pinned_synthetic_non_production_configuration() -> None:
    evidence = verify_enterprise_lab_configuration(CONFIGURATION_PATH)

    assert evidence.status == "PASSED"
    assert evidence.classification == "PrototypeVerified"
    assert evidence.environment == "LOCAL"
    assert evidence.data_origin == "SYNTHETIC"
    assert evidence.endpoint_count == 8
    assert not hasattr(evidence, "secret_reference")
    assert "http://" not in repr(evidence)


@pytest.mark.parametrize(
    ("field", "value", "reason_code"),
    [
        ("environment", "PRODUCTION", "PRODUCTION_ENVIRONMENT_FORBIDDEN"),
        ("data_origin", "BANK_PRODUCTION", "NON_SYNTHETIC_DATA_FORBIDDEN"),
        (
            "secret_reference",
            "secret://production/lab",
            "PRODUCTION_SECRET_FORBIDDEN_OUTSIDE_PRODUCTION",
        ),
        ("classification", "ApprovedByBank", "LAB_CLASSIFICATION_INVALID"),
    ],
)
def test_enterprise_lab_01_fails_closed_for_production_or_overclaim(
    tmp_path: Path,
    field: str,
    value: str,
    reason_code: str,
) -> None:
    payload = json.loads(CONFIGURATION_PATH.read_text(encoding="utf-8"))
    payload[field] = value
    candidate = tmp_path / "environment.json"
    candidate.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(EnterpriseLabConfigurationError) as error:
        verify_enterprise_lab_configuration(candidate)

    assert error.value.reason_code == reason_code


def test_enterprise_lab_01_rejects_external_endpoint_without_disclosing_it(
    tmp_path: Path,
) -> None:
    payload = json.loads(CONFIGURATION_PATH.read_text(encoding="utf-8"))
    payload["endpoints"]["siem"] = "https://production.example.invalid/collector"
    candidate = tmp_path / "environment.json"
    candidate.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(EnterpriseLabConfigurationError) as error:
        verify_enterprise_lab_configuration(candidate)

    assert error.value.reason_code == "EXTERNAL_OR_SECRET_ENDPOINT_FORBIDDEN"
    assert "example" not in str(error.value)


def test_enterprise_lab_01_rejects_allowlisted_endpoint_assigned_to_wrong_role(
    tmp_path: Path,
) -> None:
    payload = json.loads(CONFIGURATION_PATH.read_text(encoding="utf-8"))
    payload["endpoints"]["identity"] = payload["endpoints"]["evidence_store"]
    candidate = tmp_path / "environment.json"
    candidate.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(EnterpriseLabConfigurationError) as error:
        verify_enterprise_lab_configuration(candidate)

    assert error.value.reason_code == "LAB_ENDPOINT_ROLE_MISMATCH"
