"""BFR-SDLC-001/002/003 and NFR-SEC-012 local SAST release gate tests."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields

import pytest

from veri_kalitesi.secure_sdlc import (
    PythonProjectInventory,
    SAST_GATE_POLICY_VERSION,
    SastFinding,
    SastGateBlockedError,
    SastGateTechnicalError,
    SastGateValidationError,
    SastReleaseEvidence,
    SastReleaseGate,
    SastScanReport,
    SastScanStatus,
    SastSeverity,
    parse_finding,
)


def test_parses_only_data_minimum_finding_fields() -> None:
    finding = parse_finding(_payload())

    assert finding == SastFinding(
        scanner_id="synthetic-sast",
        scanner_version="1.2.3",
        rule_code="PY-SYNTHETIC-001",
        severity=SastSeverity.HIGH,
        relative_path="03-Backend/src/sample.py",
        line_number=17,
        column_number=9,
    )
    assert {item.name for item in fields(finding)} == {
        "scanner_id",
        "scanner_version",
        "rule_code",
        "severity",
        "relative_path",
        "line_number",
        "column_number",
    }


@pytest.mark.parametrize("extra_field", ("message", "source_line", "code_snippet", "secret"))
def test_rejects_non_allowlisted_scanner_payload_fields(extra_field: str) -> None:
    payload = _payload()
    sensitive_value = "Synthetic-Sensitive-Scanner-Value"
    payload[extra_field] = sensitive_value

    with pytest.raises(SastGateValidationError) as exc_info:
        parse_finding(payload)

    assert exc_info.value.reason_code == "SAST_FINDING_FIELDS_INVALID"
    assert sensitive_value not in str(exc_info.value)


def test_rejects_missing_finding_fields_without_exposing_payload() -> None:
    payload = _payload()
    del payload["rule_code"]

    with pytest.raises(SastGateValidationError, match="SAST_FINDING_FIELDS_INVALID"):
        parse_finding(payload)


@pytest.mark.parametrize(
    "relative_path",
    (
        "/etc/application.py",
        "../application.py",
        "src/../application.py",
        "C:/workspace/application.py",
        "src\\application.py",
        "./src/application.py",
        "src//application.py",
    ),
)
def test_rejects_non_repository_relative_locations(relative_path: str) -> None:
    payload = _payload(relative_path=relative_path)

    with pytest.raises(SastGateValidationError, match="SAST_LOCATION_INVALID"):
        parse_finding(payload)


@pytest.mark.parametrize(
    ("field_name", "value", "reason_code"),
    (
        ("scanner_id", "", "SAST_SCANNER_ID_INVALID"),
        ("scanner_version", "version with spaces", "SAST_SCANNER_VERSION_INVALID"),
        ("rule_code", "rule/value", "SAST_RULE_CODE_INVALID"),
        ("severity", "BLOCKER", "SAST_SEVERITY_INVALID"),
        ("line_number", 0, "SAST_LOCATION_INVALID"),
        ("column_number", True, "SAST_LOCATION_INVALID"),
    ),
)
def test_rejects_invalid_finding_values(field_name: str, value: object, reason_code: str) -> None:
    payload = _payload()
    payload[field_name] = value

    with pytest.raises(SastGateValidationError, match=reason_code):
        parse_finding(payload)


def test_issues_version_linked_evidence_for_completed_clean_scan() -> None:
    evidence = SastReleaseGate().issue_evidence(
        _inventory(),
        _report(findings=()),
    )

    assert evidence == SastReleaseEvidence(
        project_name="synthetic-application",
        project_version="1.2.3",
        gate_policy_version=SAST_GATE_POLICY_VERSION,
        scanner_id="synthetic-sast",
        scanner_version="1.2.3",
        finding_count=0,
        critical_finding_count=0,
        findings_digest="4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    )


def test_noncritical_findings_are_counted_without_exposing_locations_in_evidence() -> None:
    finding = parse_finding(_payload(severity="HIGH"))

    evidence = SastReleaseGate().issue_evidence(
        _inventory(),
        _report(findings=(finding,)),
    )

    assert evidence.finding_count == 1
    assert evidence.critical_finding_count == 0
    assert finding.relative_path not in repr(evidence)
    assert finding.rule_code not in repr(evidence)


def test_critical_findings_fail_closed_without_release_evidence() -> None:
    first = parse_finding(_payload(severity="CRITICAL"))
    second = parse_finding(
        _payload(
            severity="CRITICAL",
            relative_path="03-Backend/src/second.py",
            line_number=4,
        )
    )

    with pytest.raises(SastGateBlockedError) as exc_info:
        SastReleaseGate().issue_evidence(
            _inventory(),
            _report(findings=(first, second)),
        )

    assert exc_info.value.reason_code == "SAST_CRITICAL_FINDINGS_PRESENT"
    assert exc_info.value.blocking_finding_count == 2
    assert first.relative_path not in str(exc_info.value)


def test_incomplete_scan_is_a_separate_technical_failure() -> None:
    report = SastScanReport(
        scanner_id="synthetic-sast",
        scanner_version="1.2.3",
        status=SastScanStatus.TECHNICAL_ERROR,
        findings=(),
    )

    with pytest.raises(SastGateTechnicalError) as exc_info:
        SastReleaseGate().issue_evidence(_inventory(), report)

    assert exc_info.value.reason_code == "SAST_SCAN_NOT_COMPLETED"


def test_rejects_scanner_identity_mismatch_and_duplicate_findings() -> None:
    finding = parse_finding(_payload())
    mismatch = SastScanReport(
        scanner_id="different-scanner",
        scanner_version="1.2.3",
        status=SastScanStatus.COMPLETED,
        findings=(finding,),
    )
    with pytest.raises(SastGateValidationError, match="SAST_SCANNER_IDENTITY_MISMATCH"):
        SastReleaseGate().issue_evidence(_inventory(), mismatch)

    duplicate = _report(findings=(finding, finding))
    with pytest.raises(SastGateValidationError, match="SAST_DUPLICATE_FINDING"):
        SastReleaseGate().issue_evidence(_inventory(), duplicate)


def test_evidence_digest_is_deterministic_for_scanner_output_order() -> None:
    first = parse_finding(_payload(relative_path="src/z.py", line_number=8))
    second = parse_finding(_payload(relative_path="src/a.py", line_number=3))
    gate = SastReleaseGate()

    forward = gate.issue_evidence(_inventory(), _report(findings=(first, second)))
    reverse = gate.issue_evidence(_inventory(), _report(findings=(second, first)))

    assert forward == reverse
    assert len(forward.findings_digest) == 64


def test_models_are_immutable() -> None:
    finding = parse_finding(_payload())

    with pytest.raises(FrozenInstanceError):
        finding.rule_code = "CHANGED"  # type: ignore[misc]


def _payload(
    *,
    severity: str = "HIGH",
    relative_path: str = "03-Backend/src/sample.py",
    line_number: int = 17,
) -> dict[str, object]:
    return {
        "scanner_id": "synthetic-sast",
        "scanner_version": "1.2.3",
        "rule_code": "PY-SYNTHETIC-001",
        "severity": severity,
        "relative_path": relative_path,
        "line_number": line_number,
        "column_number": 9,
    }


def _report(*, findings: tuple[SastFinding, ...]) -> SastScanReport:
    return SastScanReport(
        scanner_id="synthetic-sast",
        scanner_version="1.2.3",
        status=SastScanStatus.COMPLETED,
        findings=findings,
    )


def _inventory() -> PythonProjectInventory:
    return PythonProjectInventory(
        name="synthetic-application",
        version="1.2.3",
        requires_python=">=3.10",
        dependencies=(),
    )
