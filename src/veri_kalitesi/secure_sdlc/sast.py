"""Product-neutral, data-minimum SAST finding and release gate contract."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import PurePosixPath

from veri_kalitesi.secure_sdlc.errors import (
    SastGateBlockedError,
    SastGateTechnicalError,
    SastGateValidationError,
)
from veri_kalitesi.secure_sdlc.models import (
    PythonProjectInventory,
    SastFinding,
    SastReleaseEvidence,
    SastScanReport,
    SastScanStatus,
    SastSeverity,
)


SAST_GATE_POLICY_VERSION = "28C-v1"

_FINDING_FIELDS = frozenset(
    {
        "scanner_id",
        "scanner_version",
        "rule_code",
        "severity",
        "relative_path",
        "line_number",
        "column_number",
    }
)
_CODE_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:+-]{0,119}")
_MAX_LOCATION_VALUE = 2_147_483_647


def parse_finding(payload: Mapping[str, object]) -> SastFinding:
    """Parse only the allowlisted, data-minimum scanner finding fields."""

    if not isinstance(payload, Mapping) or set(payload) != _FINDING_FIELDS:
        raise SastGateValidationError("SAST_FINDING_FIELDS_INVALID")
    severity_value = _required_text(payload, "severity", "SAST_SEVERITY_INVALID")
    try:
        severity = SastSeverity(severity_value)
    except ValueError as exc:
        raise SastGateValidationError("SAST_SEVERITY_INVALID") from exc
    finding = SastFinding(
        scanner_id=_required_text(payload, "scanner_id", "SAST_SCANNER_ID_INVALID"),
        scanner_version=_required_text(payload, "scanner_version", "SAST_SCANNER_VERSION_INVALID"),
        rule_code=_required_text(payload, "rule_code", "SAST_RULE_CODE_INVALID"),
        severity=severity,
        relative_path=_required_text(payload, "relative_path", "SAST_LOCATION_INVALID"),
        line_number=_required_location_number(payload, "line_number"),
        column_number=_required_location_number(payload, "column_number"),
    )
    _validate_finding(finding)
    return finding


class SastReleaseGate:
    """Issue deterministic evidence only for complete scans without critical findings."""

    policy_version = SAST_GATE_POLICY_VERSION

    def issue_evidence(
        self,
        inventory: PythonProjectInventory,
        report: SastScanReport,
    ) -> SastReleaseEvidence:
        _validate_inventory(inventory)
        findings = _validate_report(report)
        if report.status is SastScanStatus.TECHNICAL_ERROR:
            raise SastGateTechnicalError("SAST_SCAN_NOT_COMPLETED")

        critical_count = sum(finding.severity is SastSeverity.CRITICAL for finding in findings)
        if critical_count:
            raise SastGateBlockedError("SAST_CRITICAL_FINDINGS_PRESENT", critical_count)

        return SastReleaseEvidence(
            project_name=inventory.name,
            project_version=inventory.version,
            gate_policy_version=self.policy_version,
            scanner_id=report.scanner_id,
            scanner_version=report.scanner_version,
            finding_count=len(findings),
            critical_finding_count=0,
            findings_digest=_findings_digest(findings),
        )


def _validate_report(report: SastScanReport) -> tuple[SastFinding, ...]:
    if not isinstance(report, SastScanReport):
        raise SastGateValidationError("SAST_REPORT_INVALID")
    _validate_code(report.scanner_id, "SAST_SCANNER_ID_INVALID")
    _validate_code(report.scanner_version, "SAST_SCANNER_VERSION_INVALID")
    if not isinstance(report.status, SastScanStatus):
        raise SastGateValidationError("SAST_SCAN_STATUS_INVALID")
    if not isinstance(report.findings, tuple):
        raise SastGateValidationError("SAST_FINDINGS_INVALID")
    for finding in report.findings:
        _validate_finding(finding)
        if (
            finding.scanner_id != report.scanner_id
            or finding.scanner_version != report.scanner_version
        ):
            raise SastGateValidationError("SAST_SCANNER_IDENTITY_MISMATCH")
    if len(set(report.findings)) != len(report.findings):
        raise SastGateValidationError("SAST_DUPLICATE_FINDING")
    return tuple(sorted(report.findings, key=_finding_sort_key))


def _validate_finding(finding: SastFinding) -> None:
    if not isinstance(finding, SastFinding):
        raise SastGateValidationError("SAST_FINDING_INVALID")
    _validate_code(finding.scanner_id, "SAST_SCANNER_ID_INVALID")
    _validate_code(finding.scanner_version, "SAST_SCANNER_VERSION_INVALID")
    _validate_code(finding.rule_code, "SAST_RULE_CODE_INVALID")
    if not isinstance(finding.severity, SastSeverity):
        raise SastGateValidationError("SAST_SEVERITY_INVALID")
    _validate_relative_path(finding.relative_path)
    _validate_location_number(finding.line_number)
    _validate_location_number(finding.column_number)


def _validate_inventory(inventory: PythonProjectInventory) -> None:
    if not isinstance(inventory, PythonProjectInventory):
        raise SastGateValidationError("SAST_PROJECT_INVENTORY_INVALID")
    _validate_code(inventory.name, "SAST_PROJECT_NAME_INVALID")
    _validate_code(inventory.version, "SAST_PROJECT_VERSION_INVALID")


def _required_text(payload: Mapping[str, object], key: str, reason_code: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise SastGateValidationError(reason_code)
    return value


def _required_location_number(payload: Mapping[str, object], key: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise SastGateValidationError("SAST_LOCATION_INVALID")
    return value


def _validate_code(value: str, reason_code: str) -> None:
    if not isinstance(value, str) or not _CODE_PATTERN.fullmatch(value):
        raise SastGateValidationError(reason_code)


def _validate_relative_path(value: str) -> None:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 500
        or "\\" in value
        or value.startswith("/")
        or re.match(r"^[A-Za-z]:", value)
    ):
        raise SastGateValidationError("SAST_LOCATION_INVALID")
    path = PurePosixPath(value)
    if path.as_posix() != value or any(part in {"", ".", ".."} for part in path.parts):
        raise SastGateValidationError("SAST_LOCATION_INVALID")


def _validate_location_number(value: int) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 1 <= value <= _MAX_LOCATION_VALUE
    ):
        raise SastGateValidationError("SAST_LOCATION_INVALID")


def _finding_sort_key(finding: SastFinding) -> tuple[object, ...]:
    return (
        finding.relative_path,
        finding.line_number,
        finding.column_number,
        finding.rule_code,
        finding.severity.value,
        finding.scanner_id,
        finding.scanner_version,
    )


def _findings_digest(findings: tuple[SastFinding, ...]) -> str:
    payload = [
        {
            "column_number": finding.column_number,
            "line_number": finding.line_number,
            "relative_path": finding.relative_path,
            "rule_code": finding.rule_code,
            "scanner_id": finding.scanner_id,
            "scanner_version": finding.scanner_version,
            "severity": finding.severity.value,
        }
        for finding in findings
    ]
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
