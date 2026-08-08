"""BFR-SDLC-001/002/003/004 and NFR-SEC-012 dependency gate tests."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, replace

import pytest

from veri_kalitesi.secure_sdlc import (
    DEPENDENCY_INVENTORY_SCOPE,
    DEPENDENCY_VULNERABILITY_GATE_POLICY_VERSION,
    DeclaredDependency,
    DependencyVulnerabilityFinding,
    DependencyVulnerabilityGateBlockedError,
    DependencyVulnerabilityGateTechnicalError,
    DependencyVulnerabilityGateValidationError,
    DependencyVulnerabilityReleaseGate,
    DependencyVulnerabilityScanReport,
    DependencyVulnerabilityScanStatus,
    PythonProjectInventory,
    VulnerabilitySeverity,
    parse_dependency_vulnerability_finding,
)


def test_parses_only_data_minimum_vulnerability_finding_fields() -> None:
    finding = parse_dependency_vulnerability_finding(_payload())

    assert finding == DependencyVulnerabilityFinding(
        scanner_id="synthetic-dependency-scanner",
        scanner_version="1.2.3",
        advisory_source="synthetic-advisories",
        advisory_source_version="2026.07.20",
        advisory_id="CVE-2099-0001",
        severity=VulnerabilitySeverity.HIGH,
        dependency_name="sample-lib",
        dependency_version="2.3.4",
    )
    assert {item.name for item in fields(finding)} == {
        "scanner_id",
        "scanner_version",
        "advisory_source",
        "advisory_source_version",
        "advisory_id",
        "severity",
        "dependency_name",
        "dependency_version",
    }


@pytest.mark.parametrize(
    "extra_field",
    ("description", "message", "advisory_url", "fixed_version", "local_path", "secret"),
)
def test_rejects_non_allowlisted_vulnerability_payload_fields(extra_field: str) -> None:
    payload = _payload()
    sensitive_value = "Synthetic-Sensitive-Advisory-Value"
    payload[extra_field] = sensitive_value

    with pytest.raises(DependencyVulnerabilityGateValidationError) as exc_info:
        parse_dependency_vulnerability_finding(payload)

    assert exc_info.value.reason_code == "DEPENDENCY_VULNERABILITY_FINDING_FIELDS_INVALID"
    assert sensitive_value not in str(exc_info.value)


def test_rejects_missing_finding_fields_without_exposing_payload() -> None:
    payload = _payload()
    del payload["advisory_id"]

    with pytest.raises(
        DependencyVulnerabilityGateValidationError,
        match="DEPENDENCY_VULNERABILITY_FINDING_FIELDS_INVALID",
    ):
        parse_dependency_vulnerability_finding(payload)


def test_normalizes_scanner_package_name_and_version() -> None:
    finding = parse_dependency_vulnerability_finding(
        _payload(dependency_name="Sample_Lib", dependency_version="2.3.4.0")
    )

    assert finding.dependency_name == "sample-lib"
    assert finding.dependency_version == "2.3.4.0"


@pytest.mark.parametrize(
    ("field_name", "value", "reason_code"),
    (
        ("scanner_id", "", "DEPENDENCY_VULNERABILITY_SCANNER_ID_INVALID"),
        (
            "scanner_version",
            "version with spaces",
            "DEPENDENCY_VULNERABILITY_SCANNER_VERSION_INVALID",
        ),
        (
            "advisory_source",
            "source/value",
            "DEPENDENCY_VULNERABILITY_ADVISORY_SOURCE_INVALID",
        ),
        (
            "advisory_source_version",
            "",
            "DEPENDENCY_VULNERABILITY_ADVISORY_SOURCE_VERSION_INVALID",
        ),
        ("advisory_id", "CVE 2099", "DEPENDENCY_VULNERABILITY_ADVISORY_ID_INVALID"),
        ("severity", "BLOCKER", "DEPENDENCY_VULNERABILITY_SEVERITY_INVALID"),
        (
            "dependency_name",
            "invalid/name",
            "DEPENDENCY_VULNERABILITY_DEPENDENCY_NAME_INVALID",
        ),
        (
            "dependency_version",
            "not a version",
            "DEPENDENCY_VULNERABILITY_DEPENDENCY_VERSION_INVALID",
        ),
    ),
)
def test_rejects_invalid_finding_values(
    field_name: str,
    value: object,
    reason_code: str,
) -> None:
    payload = _payload()
    payload[field_name] = value

    with pytest.raises(DependencyVulnerabilityGateValidationError, match=reason_code):
        parse_dependency_vulnerability_finding(payload)


def test_issues_version_and_inventory_linked_evidence_for_completed_clean_scan() -> None:
    inventory = _inventory()

    evidence = DependencyVulnerabilityReleaseGate().issue_evidence(
        inventory,
        _report(findings=()),
    )

    assert evidence.project_name == "synthetic-application"
    assert evidence.project_version == "1.2.3"
    assert evidence.gate_policy_version == DEPENDENCY_VULNERABILITY_GATE_POLICY_VERSION
    assert evidence.inventory_scope == DEPENDENCY_INVENTORY_SCOPE
    assert evidence.dependency_count == 2
    assert evidence.scanner_id == "synthetic-dependency-scanner"
    assert evidence.advisory_source_version == "2026.07.20"
    assert evidence.finding_count == 0
    assert evidence.critical_finding_count == 0
    assert len(evidence.dependency_inventory_digest) == 64
    assert evidence.findings_digest == (
        "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"
    )


def test_noncritical_findings_are_counted_without_exposing_advisory_details() -> None:
    finding = parse_dependency_vulnerability_finding(_payload(severity="HIGH"))

    evidence = DependencyVulnerabilityReleaseGate().issue_evidence(
        _inventory(),
        _report(findings=(finding,)),
    )

    assert evidence.finding_count == 1
    assert evidence.critical_finding_count == 0
    assert finding.advisory_id not in repr(evidence)
    assert finding.dependency_name not in repr(evidence)


def test_critical_findings_fail_closed_without_release_evidence() -> None:
    first = parse_dependency_vulnerability_finding(_payload(severity="CRITICAL"))
    second = parse_dependency_vulnerability_finding(
        _payload(
            advisory_id="CVE-2099-0002",
            severity="CRITICAL",
            dependency_name="second-lib",
            dependency_version="5.6.7",
        )
    )

    with pytest.raises(DependencyVulnerabilityGateBlockedError) as exc_info:
        DependencyVulnerabilityReleaseGate().issue_evidence(
            _inventory(),
            _report(findings=(first, second)),
        )

    assert exc_info.value.reason_code == ("DEPENDENCY_VULNERABILITY_CRITICAL_FINDINGS_PRESENT")
    assert exc_info.value.blocking_finding_count == 2
    assert first.advisory_id not in str(exc_info.value)
    assert first.dependency_name not in str(exc_info.value)


def test_incomplete_scan_is_a_separate_technical_failure() -> None:
    report = _report(
        findings=(),
        status=DependencyVulnerabilityScanStatus.TECHNICAL_ERROR,
    )

    with pytest.raises(DependencyVulnerabilityGateTechnicalError) as exc_info:
        DependencyVulnerabilityReleaseGate().issue_evidence(_inventory(), report)

    assert exc_info.value.reason_code == "DEPENDENCY_VULNERABILITY_SCAN_NOT_COMPLETED"


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("scanner_id", "different-scanner"),
        ("scanner_version", "9.9.9"),
        ("advisory_source", "different-advisories"),
        ("advisory_source_version", "2099.01.01"),
    ),
)
def test_rejects_scanner_or_advisory_identity_mismatch(field_name: str, value: str) -> None:
    finding = parse_dependency_vulnerability_finding(_payload())
    report = _replace_report_identity(_report(findings=(finding,)), field_name, value)

    with pytest.raises(
        DependencyVulnerabilityGateValidationError,
        match="DEPENDENCY_VULNERABILITY_SOURCE_IDENTITY_MISMATCH",
    ):
        DependencyVulnerabilityReleaseGate().issue_evidence(_inventory(), report)


@pytest.mark.parametrize(
    ("dependency_name", "dependency_version"),
    (("unknown-lib", "2.3.4"), ("sample-lib", "2.3.5")),
)
def test_rejects_finding_outside_exact_direct_dependency_inventory(
    dependency_name: str,
    dependency_version: str,
) -> None:
    finding = parse_dependency_vulnerability_finding(
        _payload(
            dependency_name=dependency_name,
            dependency_version=dependency_version,
        )
    )

    with pytest.raises(
        DependencyVulnerabilityGateValidationError,
        match="DEPENDENCY_VULNERABILITY_DEPENDENCY_NOT_IN_INVENTORY",
    ):
        DependencyVulnerabilityReleaseGate().issue_evidence(
            _inventory(),
            _report(findings=(finding,)),
        )


def test_rejects_duplicate_findings() -> None:
    finding = parse_dependency_vulnerability_finding(_payload())

    with pytest.raises(
        DependencyVulnerabilityGateValidationError,
        match="DEPENDENCY_VULNERABILITY_DUPLICATE_FINDING",
    ):
        DependencyVulnerabilityReleaseGate().issue_evidence(
            _inventory(),
            _report(findings=(finding, finding)),
        )


def test_evidence_is_deterministic_for_scanner_output_and_inventory_order() -> None:
    first = parse_dependency_vulnerability_finding(_payload())
    second = parse_dependency_vulnerability_finding(
        _payload(
            advisory_id="GHSA-2222-3333-4444",
            severity="MEDIUM",
            dependency_name="second-lib",
            dependency_version="5.6.7",
        )
    )
    inventory = _inventory()
    reversed_inventory = replace(inventory, dependencies=tuple(reversed(inventory.dependencies)))
    gate = DependencyVulnerabilityReleaseGate()

    forward = gate.issue_evidence(inventory, _report(findings=(first, second)))
    reverse = gate.issue_evidence(reversed_inventory, _report(findings=(second, first)))

    assert forward == reverse


@pytest.mark.parametrize("changed_field", ("version", "requires_python", "dependencies"))
def test_inventory_digest_changes_with_versioned_inventory_scope(changed_field: str) -> None:
    inventory = _inventory()
    baseline = DependencyVulnerabilityReleaseGate().issue_evidence(
        inventory,
        _report(findings=()),
    )
    replacements: dict[str, object] = {
        "version": "1.2.4",
        "requires_python": ">=3.11",
        "dependencies": (
            DeclaredDependency("sample-lib", "2.3.4", "python_version >= '3.11'"),
            DeclaredDependency("second-lib", "5.6.7"),
        ),
    }

    if changed_field == "version":
        changed_inventory = replace(inventory, version=str(replacements[changed_field]))
    elif changed_field == "requires_python":
        changed_inventory = replace(inventory, requires_python=str(replacements[changed_field]))
    else:
        changed_inventory = replace(
            inventory,
            dependencies=(
                DeclaredDependency("sample-lib", "2.3.4", "python_version >= '3.11'"),
                DeclaredDependency("second-lib", "5.6.7"),
            ),
        )
    changed = DependencyVulnerabilityReleaseGate().issue_evidence(
        changed_inventory,
        _report(findings=()),
    )

    assert changed.dependency_inventory_digest != baseline.dependency_inventory_digest


@pytest.mark.parametrize(
    "inventory",
    (
        PythonProjectInventory("Invalid Name", "1.2.3", ">=3.10", ()),
        PythonProjectInventory("synthetic-application", "invalid", ">=3.10", ()),
        PythonProjectInventory("synthetic-application", "1.2.3", "", ()),
        PythonProjectInventory(
            "synthetic-application",
            "1.2.3",
            ">=3.10",
            (
                DeclaredDependency("sample-lib", "2.3.4"),
                DeclaredDependency("sample-lib", "2.3.4"),
            ),
        ),
    ),
)
def test_rejects_malformed_direct_dependency_inventory(
    inventory: PythonProjectInventory,
) -> None:
    with pytest.raises(DependencyVulnerabilityGateValidationError):
        DependencyVulnerabilityReleaseGate().issue_evidence(
            inventory,
            _report(findings=()),
        )


def test_models_are_immutable() -> None:
    finding = parse_dependency_vulnerability_finding(_payload())

    with pytest.raises(FrozenInstanceError):
        finding.advisory_id = "CHANGED"  # type: ignore[misc]


def _payload(
    *,
    advisory_id: str = "CVE-2099-0001",
    severity: str = "HIGH",
    dependency_name: str = "sample-lib",
    dependency_version: str = "2.3.4",
) -> dict[str, object]:
    return {
        "scanner_id": "synthetic-dependency-scanner",
        "scanner_version": "1.2.3",
        "advisory_source": "synthetic-advisories",
        "advisory_source_version": "2026.07.20",
        "advisory_id": advisory_id,
        "severity": severity,
        "dependency_name": dependency_name,
        "dependency_version": dependency_version,
    }


def _report(
    *,
    findings: tuple[DependencyVulnerabilityFinding, ...],
    status: DependencyVulnerabilityScanStatus = DependencyVulnerabilityScanStatus.COMPLETED,
) -> DependencyVulnerabilityScanReport:
    return DependencyVulnerabilityScanReport(
        scanner_id="synthetic-dependency-scanner",
        scanner_version="1.2.3",
        advisory_source="synthetic-advisories",
        advisory_source_version="2026.07.20",
        status=status,
        findings=findings,
    )


def _replace_report_identity(
    report: DependencyVulnerabilityScanReport,
    field_name: str,
    value: str,
) -> DependencyVulnerabilityScanReport:
    if field_name == "scanner_id":
        return replace(report, scanner_id=value)
    if field_name == "scanner_version":
        return replace(report, scanner_version=value)
    if field_name == "advisory_source":
        return replace(report, advisory_source=value)
    return replace(report, advisory_source_version=value)


def _inventory() -> PythonProjectInventory:
    return PythonProjectInventory(
        name="synthetic-application",
        version="1.2.3",
        requires_python=">=3.10",
        dependencies=(
            DeclaredDependency("sample-lib", "2.3.4"),
            DeclaredDependency("second-lib", "5.6.7"),
        ),
    )
