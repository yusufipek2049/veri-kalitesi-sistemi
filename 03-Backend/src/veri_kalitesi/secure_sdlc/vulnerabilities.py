"""Product-neutral dependency vulnerability finding and release gate contract."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping

from packaging.markers import InvalidMarker, Marker
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.utils import InvalidName, canonicalize_name
from packaging.version import InvalidVersion, Version

from veri_kalitesi.secure_sdlc.errors import (
    DependencyVulnerabilityGateBlockedError,
    DependencyVulnerabilityGateTechnicalError,
    DependencyVulnerabilityGateValidationError,
)
from veri_kalitesi.secure_sdlc.models import (
    DeclaredDependency,
    DependencyVulnerabilityFinding,
    DependencyVulnerabilityReleaseEvidence,
    DependencyVulnerabilityScanReport,
    DependencyVulnerabilityScanStatus,
    PythonProjectInventory,
    VulnerabilitySeverity,
)


DEPENDENCY_VULNERABILITY_GATE_POLICY_VERSION = "28D-v1"
DEPENDENCY_INVENTORY_SCOPE = "declared-direct-dependencies"

_FINDING_FIELDS = frozenset(
    {
        "scanner_id",
        "scanner_version",
        "advisory_source",
        "advisory_source_version",
        "advisory_id",
        "severity",
        "dependency_name",
        "dependency_version",
    }
)
_CODE_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:+-]{0,119}")


def parse_dependency_vulnerability_finding(
    payload: Mapping[str, object],
) -> DependencyVulnerabilityFinding:
    """Parse only the allowlisted, data-minimum vulnerability finding fields."""

    if not isinstance(payload, Mapping) or set(payload) != _FINDING_FIELDS:
        raise DependencyVulnerabilityGateValidationError(
            "DEPENDENCY_VULNERABILITY_FINDING_FIELDS_INVALID"
        )
    severity_value = _required_text(
        payload,
        "severity",
        "DEPENDENCY_VULNERABILITY_SEVERITY_INVALID",
    )
    try:
        severity = VulnerabilitySeverity(severity_value)
    except ValueError as exc:
        raise DependencyVulnerabilityGateValidationError(
            "DEPENDENCY_VULNERABILITY_SEVERITY_INVALID"
        ) from exc

    finding = DependencyVulnerabilityFinding(
        scanner_id=_required_text(
            payload,
            "scanner_id",
            "DEPENDENCY_VULNERABILITY_SCANNER_ID_INVALID",
        ),
        scanner_version=_required_text(
            payload,
            "scanner_version",
            "DEPENDENCY_VULNERABILITY_SCANNER_VERSION_INVALID",
        ),
        advisory_source=_required_text(
            payload,
            "advisory_source",
            "DEPENDENCY_VULNERABILITY_ADVISORY_SOURCE_INVALID",
        ),
        advisory_source_version=_required_text(
            payload,
            "advisory_source_version",
            "DEPENDENCY_VULNERABILITY_ADVISORY_SOURCE_VERSION_INVALID",
        ),
        advisory_id=_required_text(
            payload,
            "advisory_id",
            "DEPENDENCY_VULNERABILITY_ADVISORY_ID_INVALID",
        ),
        severity=severity,
        dependency_name=_normalize_dependency_name(
            _required_text(
                payload,
                "dependency_name",
                "DEPENDENCY_VULNERABILITY_DEPENDENCY_NAME_INVALID",
            )
        ),
        dependency_version=_normalize_version(
            _required_text(
                payload,
                "dependency_version",
                "DEPENDENCY_VULNERABILITY_DEPENDENCY_VERSION_INVALID",
            ),
            "DEPENDENCY_VULNERABILITY_DEPENDENCY_VERSION_INVALID",
        ),
    )
    _validate_finding(finding)
    return finding


class DependencyVulnerabilityReleaseGate:
    """Issue evidence only for complete direct-dependency scans without critical findings."""

    policy_version = DEPENDENCY_VULNERABILITY_GATE_POLICY_VERSION

    def issue_evidence(
        self,
        inventory: PythonProjectInventory,
        report: DependencyVulnerabilityScanReport,
    ) -> DependencyVulnerabilityReleaseEvidence:
        dependencies = _validate_inventory(inventory)
        findings = _validate_report(report, dependencies)
        if report.status is DependencyVulnerabilityScanStatus.TECHNICAL_ERROR:
            raise DependencyVulnerabilityGateTechnicalError(
                "DEPENDENCY_VULNERABILITY_SCAN_NOT_COMPLETED"
            )

        critical_count = sum(
            finding.severity is VulnerabilitySeverity.CRITICAL for finding in findings
        )
        if critical_count:
            raise DependencyVulnerabilityGateBlockedError(
                "DEPENDENCY_VULNERABILITY_CRITICAL_FINDINGS_PRESENT",
                critical_count,
            )

        return DependencyVulnerabilityReleaseEvidence(
            project_name=inventory.name,
            project_version=inventory.version,
            gate_policy_version=self.policy_version,
            inventory_scope=DEPENDENCY_INVENTORY_SCOPE,
            dependency_count=len(inventory.dependencies),
            dependency_inventory_digest=_inventory_digest(inventory),
            scanner_id=report.scanner_id,
            scanner_version=report.scanner_version,
            advisory_source=report.advisory_source,
            advisory_source_version=report.advisory_source_version,
            finding_count=len(findings),
            critical_finding_count=0,
            findings_digest=_findings_digest(findings),
        )


def _validate_report(
    report: DependencyVulnerabilityScanReport,
    dependencies: frozenset[tuple[str, str]],
) -> tuple[DependencyVulnerabilityFinding, ...]:
    if not isinstance(report, DependencyVulnerabilityScanReport):
        raise DependencyVulnerabilityGateValidationError("DEPENDENCY_VULNERABILITY_REPORT_INVALID")
    _validate_code(
        report.scanner_id,
        "DEPENDENCY_VULNERABILITY_SCANNER_ID_INVALID",
    )
    _validate_code(
        report.scanner_version,
        "DEPENDENCY_VULNERABILITY_SCANNER_VERSION_INVALID",
    )
    _validate_code(
        report.advisory_source,
        "DEPENDENCY_VULNERABILITY_ADVISORY_SOURCE_INVALID",
    )
    _validate_code(
        report.advisory_source_version,
        "DEPENDENCY_VULNERABILITY_ADVISORY_SOURCE_VERSION_INVALID",
    )
    if not isinstance(report.status, DependencyVulnerabilityScanStatus):
        raise DependencyVulnerabilityGateValidationError(
            "DEPENDENCY_VULNERABILITY_SCAN_STATUS_INVALID"
        )
    if not isinstance(report.findings, tuple):
        raise DependencyVulnerabilityGateValidationError(
            "DEPENDENCY_VULNERABILITY_FINDINGS_INVALID"
        )
    for finding in report.findings:
        _validate_finding(finding)
        if (
            finding.scanner_id != report.scanner_id
            or finding.scanner_version != report.scanner_version
            or finding.advisory_source != report.advisory_source
            or finding.advisory_source_version != report.advisory_source_version
        ):
            raise DependencyVulnerabilityGateValidationError(
                "DEPENDENCY_VULNERABILITY_SOURCE_IDENTITY_MISMATCH"
            )
        if (finding.dependency_name, finding.dependency_version) not in dependencies:
            raise DependencyVulnerabilityGateValidationError(
                "DEPENDENCY_VULNERABILITY_DEPENDENCY_NOT_IN_INVENTORY"
            )
    if len(set(report.findings)) != len(report.findings):
        raise DependencyVulnerabilityGateValidationError(
            "DEPENDENCY_VULNERABILITY_DUPLICATE_FINDING"
        )
    return tuple(sorted(report.findings, key=_finding_sort_key))


def _validate_finding(finding: DependencyVulnerabilityFinding) -> None:
    if not isinstance(finding, DependencyVulnerabilityFinding):
        raise DependencyVulnerabilityGateValidationError("DEPENDENCY_VULNERABILITY_FINDING_INVALID")
    _validate_code(
        finding.scanner_id,
        "DEPENDENCY_VULNERABILITY_SCANNER_ID_INVALID",
    )
    _validate_code(
        finding.scanner_version,
        "DEPENDENCY_VULNERABILITY_SCANNER_VERSION_INVALID",
    )
    _validate_code(
        finding.advisory_source,
        "DEPENDENCY_VULNERABILITY_ADVISORY_SOURCE_INVALID",
    )
    _validate_code(
        finding.advisory_source_version,
        "DEPENDENCY_VULNERABILITY_ADVISORY_SOURCE_VERSION_INVALID",
    )
    _validate_code(
        finding.advisory_id,
        "DEPENDENCY_VULNERABILITY_ADVISORY_ID_INVALID",
    )
    if not isinstance(finding.severity, VulnerabilitySeverity):
        raise DependencyVulnerabilityGateValidationError(
            "DEPENDENCY_VULNERABILITY_SEVERITY_INVALID"
        )
    if finding.dependency_name != _normalize_dependency_name(finding.dependency_name):
        raise DependencyVulnerabilityGateValidationError(
            "DEPENDENCY_VULNERABILITY_DEPENDENCY_NAME_INVALID"
        )
    if finding.dependency_version != _normalize_version(
        finding.dependency_version,
        "DEPENDENCY_VULNERABILITY_DEPENDENCY_VERSION_INVALID",
    ):
        raise DependencyVulnerabilityGateValidationError(
            "DEPENDENCY_VULNERABILITY_DEPENDENCY_VERSION_INVALID"
        )


def _validate_inventory(
    inventory: PythonProjectInventory,
) -> frozenset[tuple[str, str]]:
    if not isinstance(inventory, PythonProjectInventory):
        raise DependencyVulnerabilityGateValidationError(
            "DEPENDENCY_VULNERABILITY_PROJECT_INVENTORY_INVALID"
        )
    if inventory.name != _normalize_project_name(inventory.name):
        raise DependencyVulnerabilityGateValidationError(
            "DEPENDENCY_VULNERABILITY_PROJECT_NAME_INVALID"
        )
    if inventory.version != _normalize_version(
        inventory.version,
        "DEPENDENCY_VULNERABILITY_PROJECT_VERSION_INVALID",
    ):
        raise DependencyVulnerabilityGateValidationError(
            "DEPENDENCY_VULNERABILITY_PROJECT_VERSION_INVALID"
        )
    if not isinstance(inventory.requires_python, str) or not inventory.requires_python.strip():
        raise DependencyVulnerabilityGateValidationError(
            "DEPENDENCY_VULNERABILITY_REQUIRES_PYTHON_INVALID"
        )
    try:
        SpecifierSet(inventory.requires_python)
    except InvalidSpecifier as exc:
        raise DependencyVulnerabilityGateValidationError(
            "DEPENDENCY_VULNERABILITY_REQUIRES_PYTHON_INVALID"
        ) from exc
    if not isinstance(inventory.dependencies, tuple):
        raise DependencyVulnerabilityGateValidationError(
            "DEPENDENCY_VULNERABILITY_INVENTORY_DEPENDENCIES_INVALID"
        )

    dependencies: set[tuple[str, str]] = set()
    dependency_names: set[str] = set()
    for dependency in inventory.dependencies:
        _validate_declared_dependency(dependency)
        if dependency.canonical_name in dependency_names:
            raise DependencyVulnerabilityGateValidationError(
                "DEPENDENCY_VULNERABILITY_INVENTORY_DUPLICATE_DEPENDENCY"
            )
        dependency_names.add(dependency.canonical_name)
        dependencies.add((dependency.canonical_name, dependency.version))
    return frozenset(dependencies)


def _validate_declared_dependency(dependency: DeclaredDependency) -> None:
    if not isinstance(dependency, DeclaredDependency):
        raise DependencyVulnerabilityGateValidationError(
            "DEPENDENCY_VULNERABILITY_INVENTORY_DEPENDENCY_INVALID"
        )
    if dependency.canonical_name != _normalize_dependency_name(dependency.canonical_name):
        raise DependencyVulnerabilityGateValidationError(
            "DEPENDENCY_VULNERABILITY_INVENTORY_DEPENDENCY_INVALID"
        )
    if dependency.version != _normalize_version(
        dependency.version,
        "DEPENDENCY_VULNERABILITY_INVENTORY_DEPENDENCY_INVALID",
    ):
        raise DependencyVulnerabilityGateValidationError(
            "DEPENDENCY_VULNERABILITY_INVENTORY_DEPENDENCY_INVALID"
        )
    if dependency.environment_marker is not None:
        if not isinstance(dependency.environment_marker, str):
            raise DependencyVulnerabilityGateValidationError(
                "DEPENDENCY_VULNERABILITY_INVENTORY_DEPENDENCY_INVALID"
            )
        try:
            Marker(dependency.environment_marker)
        except InvalidMarker as exc:
            raise DependencyVulnerabilityGateValidationError(
                "DEPENDENCY_VULNERABILITY_INVENTORY_DEPENDENCY_INVALID"
            ) from exc


def _required_text(payload: Mapping[str, object], key: str, reason_code: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise DependencyVulnerabilityGateValidationError(reason_code)
    return value


def _validate_code(value: str, reason_code: str) -> None:
    if not isinstance(value, str) or not _CODE_PATTERN.fullmatch(value):
        raise DependencyVulnerabilityGateValidationError(reason_code)


def _normalize_project_name(value: str) -> str:
    try:
        return canonicalize_name(value, validate=True)
    except (InvalidName, TypeError) as exc:
        raise DependencyVulnerabilityGateValidationError(
            "DEPENDENCY_VULNERABILITY_PROJECT_NAME_INVALID"
        ) from exc


def _normalize_dependency_name(value: str) -> str:
    try:
        return canonicalize_name(value, validate=True)
    except (InvalidName, TypeError) as exc:
        raise DependencyVulnerabilityGateValidationError(
            "DEPENDENCY_VULNERABILITY_DEPENDENCY_NAME_INVALID"
        ) from exc


def _normalize_version(value: str, reason_code: str) -> str:
    try:
        return str(Version(value))
    except (InvalidVersion, TypeError) as exc:
        raise DependencyVulnerabilityGateValidationError(reason_code) from exc


def _finding_sort_key(finding: DependencyVulnerabilityFinding) -> tuple[str, ...]:
    return (
        finding.dependency_name,
        finding.dependency_version,
        finding.advisory_source,
        finding.advisory_source_version,
        finding.advisory_id,
        finding.severity.value,
        finding.scanner_id,
        finding.scanner_version,
    )


def _inventory_digest(inventory: PythonProjectInventory) -> str:
    payload = {
        "dependencies": [
            {
                "environment_marker": dependency.environment_marker,
                "name": dependency.canonical_name,
                "version": dependency.version,
            }
            for dependency in sorted(inventory.dependencies)
        ],
        "inventory_scope": DEPENDENCY_INVENTORY_SCOPE,
        "project_name": inventory.name,
        "project_version": inventory.version,
        "requires_python": inventory.requires_python,
    }
    return _sha256(payload)


def _findings_digest(findings: tuple[DependencyVulnerabilityFinding, ...]) -> str:
    payload = [
        {
            "advisory_id": finding.advisory_id,
            "advisory_source": finding.advisory_source,
            "advisory_source_version": finding.advisory_source_version,
            "dependency_name": finding.dependency_name,
            "dependency_version": finding.dependency_version,
            "scanner_id": finding.scanner_id,
            "scanner_version": finding.scanner_version,
            "severity": finding.severity.value,
        }
        for finding in findings
    ]
    return _sha256(payload)


def _sha256(payload: object) -> str:
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
