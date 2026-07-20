"""Combined fail-closed local release preflight for existing secure SDLC checks."""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
import sys
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from pathlib import Path, PurePosixPath
from typing import Any, TextIO, cast
from uuid import UUID

from veri_kalitesi.secure_sdlc.errors import (
    DependencyInventoryTechnicalError,
    DependencyInventoryValidationError,
    DependencyVulnerabilityGateBlockedError,
    DependencyVulnerabilityGateTechnicalError,
    DependencyVulnerabilityGateValidationError,
    EvidenceManifestTechnicalError,
    EvidenceManifestValidationError,
    PentestTrackingBlockedError,
    PentestTrackingTechnicalError,
    PentestTrackingValidationError,
    ReleasePreflightBlockedError,
    ReleasePreflightTechnicalError,
    ReleasePreflightValidationError,
    SastGateBlockedError,
    SastGateTechnicalError,
    SastGateValidationError,
    SecretScanTechnicalError,
    SecretScanValidationError,
)
from veri_kalitesi.secure_sdlc.evidence_gate import TechnicalEvidenceManifestGate
from veri_kalitesi.secure_sdlc.models import (
    DependencyVulnerabilityScanReport,
    DependencyVulnerabilityScanStatus,
    EvidenceManifestVerificationStatus,
    PentestAssessmentReport,
    PentestAssessmentStatus,
    PentestFindingRecord,
    PentestFindingStatus,
    PentestRetestOutcome,
    PentestSeverity,
    PythonProjectInventory,
    ReleasePreflightCheck,
    ReleasePreflightInput,
    ReleasePreflightReport,
    SastScanReport,
    SastScanStatus,
)
from veri_kalitesi.secure_sdlc.pentest import PentestFindingTracker
from veri_kalitesi.secure_sdlc.sast import SastReleaseGate, parse_finding
from veri_kalitesi.secure_sdlc.sbom import PythonDependencyInventoryBuilder
from veri_kalitesi.secure_sdlc.scanner import RepositorySecretScanner
from veri_kalitesi.secure_sdlc.vulnerabilities import (
    DependencyVulnerabilityReleaseGate,
    parse_dependency_vulnerability_finding,
)


RELEASE_PREFLIGHT_POLICY_VERSION = "29C-v1"

_MAX_REPORT_BUNDLE_SIZE_BYTES = 2_097_152
_MAX_STORED_ARTIFACT_SIZE_BYTES = 2_097_152
_REPORT_BUNDLE_FIELDS = frozenset({"schema_version", "sast", "dependency_vulnerability", "pentest"})
_SAST_REPORT_FIELDS = frozenset({"scanner_id", "scanner_version", "status", "findings"})
_VULNERABILITY_REPORT_FIELDS = frozenset(
    {
        "scanner_id",
        "scanner_version",
        "advisory_source",
        "advisory_source_version",
        "status",
        "findings",
    }
)
_PENTEST_REPORT_FIELDS = frozenset({"assessment_reference", "status", "findings"})
_PENTEST_FINDING_FIELDS = frozenset(
    {
        "assessment_reference",
        "finding_reference",
        "severity",
        "action_reference",
        "responsible_reference",
        "status",
        "revision",
        "retest_outcome",
        "retest_evidence_reference",
    }
)

_PROJECT_MANIFEST = "pyproject.toml"
_STORED_SBOM = "08-Uyum-Kanitlari/Surum-Paketleri/Iterasyon-28B-SBOM.cdx.json"
_EVIDENCE_CATALOG = "08-Uyum-Kanitlari/Surum-Paketleri/Iterasyon-29A-Teknik-Kanit-Katalogu.json"
_STORED_EVIDENCE_MANIFEST = (
    "08-Uyum-Kanitlari/Surum-Paketleri/Iterasyon-29A-Teknik-Kanit-Manifesti.json"
)


class LocalReleasePreflight:
    """Run all existing local release checks in a deterministic order."""

    policy_version = RELEASE_PREFLIGHT_POLICY_VERSION

    def read_input(self, report_bundle_path: Path | str) -> ReleasePreflightInput:
        document = _read_json_document(
            Path(report_bundle_path),
            _MAX_REPORT_BUNDLE_SIZE_BYTES,
            "PREFLIGHT_REPORT_BUNDLE",
        )
        return _parse_input(document)

    def run(
        self,
        repository_root: Path | str,
        preflight_input: ReleasePreflightInput,
    ) -> ReleasePreflightReport:
        root = _validate_repository_root(Path(repository_root))
        if not isinstance(preflight_input, ReleasePreflightInput):
            raise ReleasePreflightValidationError("INPUT", "PREFLIGHT_INPUT_INVALID")

        checks: list[ReleasePreflightCheck] = []
        checks.append(self._run_secret_scan(root))
        inventory, sbom_check = self._run_sbom_check(root)
        checks.append(sbom_check)
        checks.append(self._run_sast_gate(inventory, preflight_input.sast_report))
        checks.append(
            self._run_vulnerability_gate(
                inventory,
                preflight_input.dependency_vulnerability_report,
            )
        )
        checks.append(self._run_pentest_gate(preflight_input.pentest_report))
        checks.append(self._run_manifest_gate(root))
        return ReleasePreflightReport(
            policy_version=self.policy_version,
            project_name=inventory.name,
            project_version=inventory.version,
            checks=tuple(checks),
        )

    @staticmethod
    def to_document(report: ReleasePreflightReport) -> dict[str, object]:
        return {
            "policy_version": report.policy_version,
            "status": "PASS",
            "project_name": report.project_name,
            "project_version": report.project_version,
            "checks": [asdict(check) for check in report.checks],
        }

    @staticmethod
    def _run_secret_scan(root: Path) -> ReleasePreflightCheck:
        check_id = "SECRET_SCAN"
        try:
            report = RepositorySecretScanner().scan(root)
        except SecretScanValidationError as exc:
            raise ReleasePreflightValidationError(check_id, exc.reason_code) from exc
        except SecretScanTechnicalError as exc:
            raise ReleasePreflightTechnicalError(check_id, exc.operation_code) from exc
        if not report.passed:
            raise ReleasePreflightBlockedError(check_id, "SECRET_FINDINGS_PRESENT")
        digest = _digest(
            {
                "policy_version": report.policy_version,
                "scanned_file_count": report.scanned_file_count,
                "skipped_file_count": report.skipped_file_count,
                "finding_count": 0,
            }
        )
        return ReleasePreflightCheck(check_id, report.policy_version, digest)

    @staticmethod
    def _run_sbom_check(root: Path) -> tuple[PythonProjectInventory, ReleasePreflightCheck]:
        check_id = "SBOM"
        builder = PythonDependencyInventoryBuilder()
        try:
            inventory = builder.read(root / _PROJECT_MANIFEST)
        except DependencyInventoryValidationError as exc:
            raise ReleasePreflightValidationError(check_id, exc.reason_code) from exc
        except DependencyInventoryTechnicalError as exc:
            raise ReleasePreflightTechnicalError(check_id, exc.operation_code) from exc
        generated = builder.serialize(inventory)
        stored = _read_repository_artifact(root, _STORED_SBOM, check_id)
        if stored != generated:
            raise ReleasePreflightBlockedError(check_id, "SBOM_DRIFT")
        return inventory, ReleasePreflightCheck(
            check_id,
            "28B-v1",
            hashlib.sha256(generated).hexdigest(),
        )

    @staticmethod
    def _run_sast_gate(
        inventory: PythonProjectInventory,
        report: SastScanReport,
    ) -> ReleasePreflightCheck:
        check_id = "SAST"
        gate = SastReleaseGate()
        try:
            evidence = gate.issue_evidence(inventory, report)
        except SastGateValidationError as exc:
            raise ReleasePreflightValidationError(check_id, exc.reason_code) from exc
        except SastGateTechnicalError as exc:
            raise ReleasePreflightTechnicalError(check_id, exc.reason_code) from exc
        except SastGateBlockedError as exc:
            raise ReleasePreflightBlockedError(check_id, exc.reason_code) from exc
        return ReleasePreflightCheck(check_id, gate.policy_version, _digest(asdict(evidence)))

    @staticmethod
    def _run_vulnerability_gate(
        inventory: PythonProjectInventory,
        report: DependencyVulnerabilityScanReport,
    ) -> ReleasePreflightCheck:
        check_id = "DEPENDENCY_VULNERABILITY"
        gate = DependencyVulnerabilityReleaseGate()
        try:
            evidence = gate.issue_evidence(inventory, report)
        except DependencyVulnerabilityGateValidationError as exc:
            raise ReleasePreflightValidationError(check_id, exc.reason_code) from exc
        except DependencyVulnerabilityGateTechnicalError as exc:
            raise ReleasePreflightTechnicalError(check_id, exc.reason_code) from exc
        except DependencyVulnerabilityGateBlockedError as exc:
            raise ReleasePreflightBlockedError(check_id, exc.reason_code) from exc
        return ReleasePreflightCheck(check_id, gate.policy_version, _digest(asdict(evidence)))

    @staticmethod
    def _run_pentest_gate(report: PentestAssessmentReport) -> ReleasePreflightCheck:
        check_id = "PENTEST"
        tracker = PentestFindingTracker()
        try:
            evidence = tracker.issue_evidence(report)
        except PentestTrackingValidationError as exc:
            raise ReleasePreflightValidationError(check_id, exc.reason_code) from exc
        except PentestTrackingTechnicalError as exc:
            raise ReleasePreflightTechnicalError(check_id, exc.reason_code) from exc
        except PentestTrackingBlockedError as exc:
            raise ReleasePreflightBlockedError(check_id, exc.reason_code) from exc
        return ReleasePreflightCheck(check_id, tracker.policy_version, _digest(asdict(evidence)))

    @staticmethod
    def _run_manifest_gate(root: Path) -> ReleasePreflightCheck:
        check_id = "EVIDENCE_MANIFEST"
        gate = TechnicalEvidenceManifestGate()
        try:
            verification = gate.verify(
                root / _EVIDENCE_CATALOG,
                _STORED_EVIDENCE_MANIFEST,
                root,
            )
        except EvidenceManifestValidationError as exc:
            raise ReleasePreflightValidationError(check_id, exc.reason_code) from exc
        except EvidenceManifestTechnicalError as exc:
            raise ReleasePreflightTechnicalError(check_id, exc.operation_code) from exc
        if verification.status is EvidenceManifestVerificationStatus.DRIFT:
            raise ReleasePreflightBlockedError(check_id, "EVIDENCE_MANIFEST_DRIFT")
        return ReleasePreflightCheck(
            check_id,
            verification.policy_version,
            verification.generated_manifest_sha256,
        )


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    output = stdout or sys.stdout
    error_output = stderr or sys.stderr
    parser = argparse.ArgumentParser(description="Run the combined local release preflight.")
    parser.add_argument("report_bundle", type=Path)
    parser.add_argument("repository_root", nargs="?", default=Path("."), type=Path)
    arguments = parser.parse_args(argv)
    preflight = LocalReleasePreflight()
    try:
        preflight_input = preflight.read_input(arguments.report_bundle)
        report = preflight.run(arguments.repository_root, preflight_input)
    except ReleasePreflightBlockedError as exc:
        _write_failure(error_output, "BLOCKED", exc.check_id, exc.reason_code)
        return 1
    except ReleasePreflightValidationError as exc:
        _write_failure(error_output, "VALIDATION_ERROR", exc.check_id, exc.reason_code)
        return 2
    except ReleasePreflightTechnicalError as exc:
        _write_failure(error_output, "TECHNICAL_ERROR", exc.check_id, exc.reason_code)
        return 2

    output.write(json.dumps(preflight.to_document(report), sort_keys=True))
    output.write("\n")
    return 0


def _parse_input(document: object) -> ReleasePreflightInput:
    payload = _exact_mapping(
        document, _REPORT_BUNDLE_FIELDS, "PREFLIGHT_REPORT_BUNDLE_FIELDS_INVALID"
    )
    if payload.get("schema_version") != 1:
        raise ReleasePreflightValidationError("INPUT", "PREFLIGHT_SCHEMA_VERSION_INVALID")
    return ReleasePreflightInput(
        sast_report=_parse_sast_report(payload.get("sast")),
        dependency_vulnerability_report=_parse_vulnerability_report(
            payload.get("dependency_vulnerability")
        ),
        pentest_report=_parse_pentest_report(payload.get("pentest")),
    )


def _parse_sast_report(value: object) -> SastScanReport:
    payload = _exact_mapping(value, _SAST_REPORT_FIELDS, "PREFLIGHT_SAST_REPORT_FIELDS_INVALID")
    try:
        status = SastScanStatus(_required_text(payload, "status", "PREFLIGHT_SAST_STATUS_INVALID"))
        findings = tuple(parse_finding(item) for item in _required_list(payload, "findings"))
    except SastGateValidationError as exc:
        raise ReleasePreflightValidationError("SAST", exc.reason_code) from exc
    except ValueError as exc:
        raise ReleasePreflightValidationError("SAST", "PREFLIGHT_SAST_STATUS_INVALID") from exc
    return SastScanReport(
        scanner_id=_required_text(payload, "scanner_id", "PREFLIGHT_SAST_SCANNER_ID_INVALID"),
        scanner_version=_required_text(
            payload, "scanner_version", "PREFLIGHT_SAST_SCANNER_VERSION_INVALID"
        ),
        status=status,
        findings=findings,
    )


def _parse_vulnerability_report(value: object) -> DependencyVulnerabilityScanReport:
    payload = _exact_mapping(
        value,
        _VULNERABILITY_REPORT_FIELDS,
        "PREFLIGHT_DEPENDENCY_REPORT_FIELDS_INVALID",
    )
    try:
        status = DependencyVulnerabilityScanStatus(
            _required_text(payload, "status", "PREFLIGHT_DEPENDENCY_STATUS_INVALID")
        )
        findings = tuple(
            parse_dependency_vulnerability_finding(item)
            for item in _required_list(payload, "findings")
        )
    except DependencyVulnerabilityGateValidationError as exc:
        raise ReleasePreflightValidationError("DEPENDENCY_VULNERABILITY", exc.reason_code) from exc
    except ValueError as exc:
        raise ReleasePreflightValidationError(
            "DEPENDENCY_VULNERABILITY",
            "PREFLIGHT_DEPENDENCY_STATUS_INVALID",
        ) from exc
    return DependencyVulnerabilityScanReport(
        scanner_id=_required_text(payload, "scanner_id", "PREFLIGHT_DEPENDENCY_SCANNER_ID_INVALID"),
        scanner_version=_required_text(
            payload, "scanner_version", "PREFLIGHT_DEPENDENCY_SCANNER_VERSION_INVALID"
        ),
        advisory_source=_required_text(
            payload, "advisory_source", "PREFLIGHT_ADVISORY_SOURCE_INVALID"
        ),
        advisory_source_version=_required_text(
            payload,
            "advisory_source_version",
            "PREFLIGHT_ADVISORY_SOURCE_VERSION_INVALID",
        ),
        status=status,
        findings=findings,
    )


def _parse_pentest_report(value: object) -> PentestAssessmentReport:
    payload = _exact_mapping(
        value,
        _PENTEST_REPORT_FIELDS,
        "PREFLIGHT_PENTEST_REPORT_FIELDS_INVALID",
    )
    assessment_reference = _required_uuid(
        payload,
        "assessment_reference",
        "PREFLIGHT_PENTEST_ASSESSMENT_REFERENCE_INVALID",
    )
    try:
        status = PentestAssessmentStatus(
            _required_text(payload, "status", "PREFLIGHT_PENTEST_STATUS_INVALID")
        )
        findings = tuple(
            _parse_pentest_record(item) for item in _required_list(payload, "findings")
        )
    except ValueError as exc:
        raise ReleasePreflightValidationError(
            "PENTEST", "PREFLIGHT_PENTEST_STATUS_INVALID"
        ) from exc
    return PentestAssessmentReport(assessment_reference, status, findings)


def _parse_pentest_record(value: object) -> PentestFindingRecord:
    payload = _exact_mapping(
        value,
        _PENTEST_FINDING_FIELDS,
        "PREFLIGHT_PENTEST_FINDING_FIELDS_INVALID",
    )
    try:
        severity = PentestSeverity(
            _required_text(payload, "severity", "PREFLIGHT_PENTEST_SEVERITY_INVALID")
        )
        status = PentestFindingStatus(
            _required_text(payload, "status", "PREFLIGHT_PENTEST_FINDING_STATUS_INVALID")
        )
        outcome_value = payload.get("retest_outcome")
        if outcome_value is None:
            outcome = None
        elif isinstance(outcome_value, str):
            outcome = PentestRetestOutcome(outcome_value)
        else:
            raise ReleasePreflightValidationError(
                "PENTEST",
                "PREFLIGHT_PENTEST_RETEST_OUTCOME_INVALID",
            )
    except ValueError as exc:
        raise ReleasePreflightValidationError(
            "PENTEST", "PREFLIGHT_PENTEST_FINDING_INVALID"
        ) from exc
    revision = payload.get("revision")
    if isinstance(revision, bool) or not isinstance(revision, int):
        raise ReleasePreflightValidationError("PENTEST", "PREFLIGHT_PENTEST_REVISION_INVALID")
    evidence_value = payload.get("retest_evidence_reference")
    evidence_reference = (
        _uuid_value(evidence_value, "PREFLIGHT_PENTEST_EVIDENCE_REFERENCE_INVALID")
        if evidence_value is not None
        else None
    )
    return PentestFindingRecord(
        assessment_reference=_required_uuid(
            payload, "assessment_reference", "PREFLIGHT_PENTEST_ASSESSMENT_REFERENCE_INVALID"
        ),
        finding_reference=_required_uuid(
            payload, "finding_reference", "PREFLIGHT_PENTEST_FINDING_REFERENCE_INVALID"
        ),
        severity=severity,
        action_reference=_required_uuid(
            payload, "action_reference", "PREFLIGHT_PENTEST_ACTION_REFERENCE_INVALID"
        ),
        responsible_reference=_required_uuid(
            payload, "responsible_reference", "PREFLIGHT_PENTEST_RESPONSIBLE_REFERENCE_INVALID"
        ),
        status=status,
        revision=revision,
        retest_outcome=outcome,
        retest_evidence_reference=evidence_reference,
    )


def _read_json_document(path: Path, max_size: int, prefix: str) -> object:
    if path.is_symlink():
        raise ReleasePreflightValidationError("INPUT", f"{prefix}_SYMLINK_REJECTED")
    try:
        file_stat = path.stat()
    except FileNotFoundError as exc:
        raise ReleasePreflightValidationError("INPUT", f"{prefix}_NOT_FOUND") from exc
    except OSError as exc:
        raise ReleasePreflightTechnicalError("INPUT", f"{prefix}_STAT_FAILED") from exc
    if not stat.S_ISREG(file_stat.st_mode):
        raise ReleasePreflightValidationError("INPUT", f"{prefix}_NOT_REGULAR_FILE")
    if file_stat.st_size > max_size:
        raise ReleasePreflightValidationError("INPUT", f"{prefix}_TOO_LARGE")
    try:
        content = path.read_bytes()
    except OSError as exc:
        raise ReleasePreflightTechnicalError("INPUT", f"{prefix}_READ_FAILED") from exc
    try:
        return json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReleasePreflightValidationError("INPUT", f"{prefix}_PARSE_FAILED") from exc


def _validate_repository_root(path: Path) -> Path:
    if path.is_symlink():
        raise ReleasePreflightValidationError("REPOSITORY", "PREFLIGHT_ROOT_SYMLINK_REJECTED")
    try:
        root_stat = path.stat()
    except FileNotFoundError as exc:
        raise ReleasePreflightValidationError("REPOSITORY", "PREFLIGHT_ROOT_NOT_FOUND") from exc
    except OSError as exc:
        raise ReleasePreflightTechnicalError("REPOSITORY", "PREFLIGHT_ROOT_STAT_FAILED") from exc
    if not stat.S_ISDIR(root_stat.st_mode):
        raise ReleasePreflightValidationError("REPOSITORY", "PREFLIGHT_ROOT_NOT_DIRECTORY")
    return path.resolve()


def _read_repository_artifact(root: Path, relative_path: str, check_id: str) -> bytes:
    path = PurePosixPath(relative_path)
    candidate = root.joinpath(*path.parts)
    current = root
    for part in path.parts:
        current /= part
        if current.is_symlink():
            raise ReleasePreflightValidationError(check_id, f"{check_id}_SYMLINK_REJECTED")
    try:
        artifact_stat = candidate.stat()
    except FileNotFoundError as exc:
        raise ReleasePreflightValidationError(check_id, f"{check_id}_ARTIFACT_NOT_FOUND") from exc
    except OSError as exc:
        raise ReleasePreflightTechnicalError(check_id, f"{check_id}_ARTIFACT_STAT_FAILED") from exc
    if not stat.S_ISREG(artifact_stat.st_mode):
        raise ReleasePreflightValidationError(check_id, f"{check_id}_ARTIFACT_NOT_REGULAR_FILE")
    if artifact_stat.st_size > _MAX_STORED_ARTIFACT_SIZE_BYTES:
        raise ReleasePreflightValidationError(check_id, f"{check_id}_ARTIFACT_TOO_LARGE")
    try:
        return candidate.read_bytes()
    except OSError as exc:
        raise ReleasePreflightTechnicalError(check_id, f"{check_id}_ARTIFACT_READ_FAILED") from exc


def _exact_mapping(value: object, fields: frozenset[str], reason_code: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ReleasePreflightValidationError("INPUT", reason_code)
    return cast(Mapping[str, Any], value)


def _required_text(payload: Mapping[str, Any], key: str, reason_code: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ReleasePreflightValidationError("INPUT", reason_code)
    return value


def _required_list(payload: Mapping[str, Any], key: str) -> list[Mapping[str, object]]:
    value = payload.get(key)
    if not isinstance(value, list) or any(not isinstance(item, Mapping) for item in value):
        raise ReleasePreflightValidationError("INPUT", "PREFLIGHT_FINDINGS_INVALID")
    return cast(list[Mapping[str, object]], value)


def _required_uuid(payload: Mapping[str, Any], key: str, reason_code: str) -> UUID:
    return _uuid_value(payload.get(key), reason_code)


def _uuid_value(value: object, reason_code: str) -> UUID:
    if not isinstance(value, str):
        raise ReleasePreflightValidationError("PENTEST", reason_code)
    try:
        result = UUID(value)
    except ValueError as exc:
        raise ReleasePreflightValidationError("PENTEST", reason_code) from exc
    if result.int == 0:
        raise ReleasePreflightValidationError("PENTEST", reason_code)
    return result


def _digest(value: object) -> str:
    canonical = json.dumps(
        value,
        default=_json_default,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _json_default(value: object) -> str:
    if isinstance(value, UUID):
        return str(value)
    raise TypeError(f"Unsupported preflight digest value: {type(value).__name__}")


def _write_failure(stream: TextIO, status: str, check_id: str, reason_code: str) -> None:
    stream.write(
        json.dumps(
            {"status": status, "check_id": check_id, "reason_code": reason_code},
            sort_keys=True,
        )
    )
    stream.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
