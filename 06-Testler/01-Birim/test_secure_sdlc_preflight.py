"""BFR-SDLC-001..005, BRULE-004/005 and NFR-CMP-002/005 preflight tests."""

from __future__ import annotations

import io
import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from veri_kalitesi.secure_sdlc.evidence import TechnicalEvidenceManifestBuilder
from veri_kalitesi.secure_sdlc.errors import (
    ReleasePreflightBlockedError,
    ReleasePreflightTechnicalError,
    ReleasePreflightValidationError,
)
from veri_kalitesi.secure_sdlc.preflight import (
    RELEASE_PREFLIGHT_POLICY_VERSION,
    LocalReleasePreflight,
    main,
)
from veri_kalitesi.secure_sdlc.sbom import PythonDependencyInventoryBuilder


EVIDENCE_PATH = "08-Uyum-Kanitlari/Erisim/synthetic-evidence.md"
SBOM_PATH = "08-Uyum-Kanitlari/Surum-Paketleri/Iterasyon-28B-SBOM.cdx.json"
CATALOG_PATH = "08-Uyum-Kanitlari/Surum-Paketleri/Iterasyon-29A-Teknik-Kanit-Katalogu.json"
MANIFEST_PATH = "08-Uyum-Kanitlari/Surum-Paketleri/Iterasyon-29A-Teknik-Kanit-Manifesti.json"


def test_runs_six_existing_checks_in_fail_closed_order(tmp_path: Path) -> None:
    root, bundle = _prepare_repository(tmp_path)
    preflight = LocalReleasePreflight()

    report = preflight.run(root, preflight.read_input(bundle))

    assert report.policy_version == RELEASE_PREFLIGHT_POLICY_VERSION
    assert report.project_name == "synthetic-application"
    assert report.project_version == "1.2.3"
    assert [item.check_id for item in report.checks] == [
        "SECRET_SCAN",
        "SBOM",
        "SAST",
        "DEPENDENCY_VULNERABILITY",
        "PENTEST",
        "EVIDENCE_MANIFEST",
    ]
    assert all(len(item.evidence_digest) == 64 for item in report.checks)


def test_success_output_is_deterministic_and_data_minimum(tmp_path: Path) -> None:
    sensitive_path = "03-Backend/src/sensitive-location.py"
    sensitive_advisory = "CVE-2099-0001"
    sensitive_reference = "20000000-0000-4000-8000-000000000001"
    root, bundle = _prepare_repository(tmp_path)
    document = _bundle_document()
    document["sast"]["findings"] = [_sast_finding("HIGH", sensitive_path)]  # type: ignore[index]
    document["dependency_vulnerability"]["findings"] = [  # type: ignore[index]
        _vulnerability_finding("HIGH", sensitive_advisory)
    ]
    document["pentest"]["findings"] = [_pentest_finding("HIGH")]  # type: ignore[index]
    bundle.write_text(json.dumps(document), encoding="utf-8")
    preflight = LocalReleasePreflight()

    first = preflight.to_document(preflight.run(root, preflight.read_input(bundle)))
    second = preflight.to_document(preflight.run(root, preflight.read_input(bundle)))
    serialized = json.dumps(first, sort_keys=True)

    assert first == second
    assert first["status"] == "PASS"
    assert sensitive_path not in serialized
    assert sensitive_advisory not in serialized
    assert sensitive_reference not in serialized


@pytest.mark.parametrize(
    ("section", "reason_code"),
    (
        ("sast", "SAST_CRITICAL_FINDINGS_PRESENT"),
        (
            "dependency_vulnerability",
            "DEPENDENCY_VULNERABILITY_CRITICAL_FINDINGS_PRESENT",
        ),
        ("pentest", "PENTEST_UNRESOLVED_CRITICAL_FINDINGS_PRESENT"),
    ),
)
def test_critical_security_results_block_release(
    section: str,
    reason_code: str,
    tmp_path: Path,
) -> None:
    root, bundle = _prepare_repository(tmp_path)
    document = _bundle_document()
    report = document[section]
    assert isinstance(report, dict)
    if section == "sast":
        report["findings"] = [_sast_finding("CRITICAL")]
    elif section == "dependency_vulnerability":
        report["findings"] = [_vulnerability_finding("CRITICAL")]
    else:
        report["findings"] = [_pentest_finding("CRITICAL")]
    bundle.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ReleasePreflightBlockedError) as exc_info:
        LocalReleasePreflight().run(root, LocalReleasePreflight().read_input(bundle))

    assert exc_info.value.reason_code == reason_code


@pytest.mark.parametrize(
    ("section", "check_id", "reason_code"),
    (
        ("sast", "SAST", "SAST_SCAN_NOT_COMPLETED"),
        (
            "dependency_vulnerability",
            "DEPENDENCY_VULNERABILITY",
            "DEPENDENCY_VULNERABILITY_SCAN_NOT_COMPLETED",
        ),
        ("pentest", "PENTEST", "PENTEST_ASSESSMENT_NOT_COMPLETED"),
    ),
)
def test_incomplete_security_reports_are_technical_errors(
    section: str,
    check_id: str,
    reason_code: str,
    tmp_path: Path,
) -> None:
    root, bundle = _prepare_repository(tmp_path)
    document = _bundle_document()
    report = document[section]
    assert isinstance(report, dict)
    report["status"] = "TECHNICAL_ERROR"
    bundle.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ReleasePreflightTechnicalError) as exc_info:
        LocalReleasePreflight().run(root, LocalReleasePreflight().read_input(bundle))

    assert exc_info.value.check_id == check_id
    assert exc_info.value.reason_code == reason_code


def test_secret_finding_blocks_without_exposing_value(tmp_path: Path) -> None:
    sensitive_value = "Synthetic-Preflight-Value-48291"
    root, bundle = _prepare_repository(tmp_path)
    (root / "unsafe.conf").write_text(
        "pass" + f'word = "{sensitive_value}"',
        encoding="utf-8",
    )

    with pytest.raises(ReleasePreflightBlockedError) as exc_info:
        LocalReleasePreflight().run(root, LocalReleasePreflight().read_input(bundle))

    assert exc_info.value.check_id == "SECRET_SCAN"
    assert exc_info.value.reason_code == "SECRET_FINDINGS_PRESENT"
    assert sensitive_value not in str(exc_info.value)


@pytest.mark.parametrize(
    ("relative_path", "reason_code"),
    (
        (SBOM_PATH, "SBOM_DRIFT"),
        (EVIDENCE_PATH, "EVIDENCE_MANIFEST_DRIFT"),
    ),
)
def test_artifact_drift_blocks_release(
    relative_path: str,
    reason_code: str,
    tmp_path: Path,
) -> None:
    root, bundle = _prepare_repository(tmp_path)
    (root / relative_path).write_bytes(b"changed")

    with pytest.raises(ReleasePreflightBlockedError, match=reason_code):
        LocalReleasePreflight().run(root, LocalReleasePreflight().read_input(bundle))


@pytest.mark.parametrize("extra_field", ("message", "source", "secret", "approval"))
def test_rejects_extra_report_fields_without_exposing_value(
    extra_field: str,
    tmp_path: Path,
) -> None:
    sensitive_value = "Synthetic-Sensitive-Report-Value"
    _, bundle = _prepare_repository(tmp_path)
    document = _bundle_document()
    sast = document["sast"]
    assert isinstance(sast, dict)
    sast[extra_field] = sensitive_value
    bundle.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ReleasePreflightValidationError) as exc_info:
        LocalReleasePreflight().read_input(bundle)

    assert exc_info.value.reason_code == "PREFLIGHT_SAST_REPORT_FIELDS_INVALID"
    assert sensitive_value not in str(exc_info.value)


def test_rejects_missing_symlink_and_malformed_report_bundle(tmp_path: Path) -> None:
    preflight = LocalReleasePreflight()
    missing = tmp_path / "missing.json"
    with pytest.raises(ReleasePreflightValidationError, match="REPORT_BUNDLE_NOT_FOUND"):
        preflight.read_input(missing)

    malformed = tmp_path / "malformed.json"
    malformed.write_text("{", encoding="utf-8")
    with pytest.raises(ReleasePreflightValidationError, match="REPORT_BUNDLE_PARSE_FAILED"):
        preflight.read_input(malformed)

    target = tmp_path / "target.json"
    target.write_text(json.dumps(_bundle_document()), encoding="utf-8")
    link = tmp_path / "bundle-link.json"
    link.symlink_to(target)
    with pytest.raises(ReleasePreflightValidationError, match="SYMLINK_REJECTED"):
        preflight.read_input(link)


def test_rejects_symlink_stored_sbom(tmp_path: Path) -> None:
    root, bundle = _prepare_repository(tmp_path)
    stored = root / SBOM_PATH
    target = stored.with_name("target.json")
    stored.rename(target)
    stored.symlink_to(target)

    with pytest.raises(ReleasePreflightValidationError, match="SBOM_SYMLINK_REJECTED"):
        LocalReleasePreflight().run(root, LocalReleasePreflight().read_input(bundle))


def test_cli_returns_distinct_pass_blocked_and_validation_codes(tmp_path: Path) -> None:
    root, bundle = _prepare_repository(tmp_path)
    stdout, stderr = io.StringIO(), io.StringIO()
    assert main([str(bundle), str(root)], stdout=stdout, stderr=stderr) == 0
    assert json.loads(stdout.getvalue())["status"] == "PASS"
    assert stderr.getvalue() == ""

    (root / SBOM_PATH).write_bytes(b"drift")
    stdout, stderr = io.StringIO(), io.StringIO()
    assert main([str(bundle), str(root)], stdout=stdout, stderr=stderr) == 1
    assert stdout.getvalue() == ""
    assert json.loads(stderr.getvalue()) == {
        "check_id": "SBOM",
        "reason_code": "SBOM_DRIFT",
        "status": "BLOCKED",
    }

    stdout, stderr = io.StringIO(), io.StringIO()
    assert main([str(tmp_path / "missing.json"), str(root)], stdout=stdout, stderr=stderr) == 2
    assert stdout.getvalue() == ""
    assert json.loads(stderr.getvalue())["status"] == "VALIDATION_ERROR"


def test_cli_reports_technical_error_separately(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, bundle = _prepare_repository(tmp_path)

    def fail_run(*args: object, **kwargs: object) -> None:
        raise ReleasePreflightTechnicalError("SAST", "SAST_SCAN_NOT_COMPLETED")

    monkeypatch.setattr(LocalReleasePreflight, "run", fail_run)
    stdout, stderr = io.StringIO(), io.StringIO()

    assert main([str(bundle), str(root)], stdout=stdout, stderr=stderr) == 2
    assert stdout.getvalue() == ""
    assert json.loads(stderr.getvalue()) == {
        "check_id": "SAST",
        "reason_code": "SAST_SCAN_NOT_COMPLETED",
        "status": "TECHNICAL_ERROR",
    }


def test_report_models_are_immutable(tmp_path: Path) -> None:
    root, bundle = _prepare_repository(tmp_path)
    report = LocalReleasePreflight().run(root, LocalReleasePreflight().read_input(bundle))

    with pytest.raises(FrozenInstanceError):
        report.policy_version = "changed"  # type: ignore[misc]


def _prepare_repository(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repository"
    root.mkdir()
    project_manifest = root / "pyproject.toml"
    project_manifest.write_text(
        """[project]
name = "synthetic-application"
version = "1.2.3"
requires-python = ">=3.10"
dependencies = ["packaging==26.0"]
""",
        encoding="utf-8",
    )
    sbom_builder = PythonDependencyInventoryBuilder()
    inventory = sbom_builder.read(project_manifest)
    stored_sbom = root / SBOM_PATH
    stored_sbom.parent.mkdir(parents=True)
    stored_sbom.write_bytes(sbom_builder.serialize(inventory))

    evidence = root / EVIDENCE_PATH
    evidence.parent.mkdir(parents=True)
    evidence.write_bytes(b"synthetic technical evidence\n")
    catalog = root / CATALOG_PATH
    catalog.write_text(json.dumps(_catalog_document()), encoding="utf-8")
    manifest_builder = TechnicalEvidenceManifestBuilder()
    manifest = manifest_builder.build(manifest_builder.read_catalog(catalog), root)
    (root / MANIFEST_PATH).write_bytes(manifest_builder.serialize(manifest))

    bundle = tmp_path / "report-bundle.json"
    bundle.write_text(json.dumps(_bundle_document()), encoding="utf-8")
    return root, bundle


def _bundle_document() -> dict[str, object]:
    return {
        "schema_version": 1,
        "sast": {
            "scanner_id": "synthetic-sast",
            "scanner_version": "1.2.3",
            "status": "COMPLETED",
            "findings": [],
        },
        "dependency_vulnerability": {
            "scanner_id": "synthetic-dependency-scanner",
            "scanner_version": "1.2.3",
            "advisory_source": "synthetic-advisories",
            "advisory_source_version": "2026.07.20",
            "status": "COMPLETED",
            "findings": [],
        },
        "pentest": {
            "assessment_reference": "10000000-0000-4000-8000-000000000001",
            "status": "COMPLETED",
            "findings": [],
        },
    }


def _sast_finding(
    severity: str,
    relative_path: str = "03-Backend/src/sample.py",
) -> dict[str, object]:
    return {
        "scanner_id": "synthetic-sast",
        "scanner_version": "1.2.3",
        "rule_code": "PY-SYNTHETIC-001",
        "severity": severity,
        "relative_path": relative_path,
        "line_number": 17,
        "column_number": 9,
    }


def _vulnerability_finding(severity: str, advisory_id: str = "CVE-2099-0001") -> dict[str, object]:
    return {
        "scanner_id": "synthetic-dependency-scanner",
        "scanner_version": "1.2.3",
        "advisory_source": "synthetic-advisories",
        "advisory_source_version": "2026.07.20",
        "advisory_id": advisory_id,
        "severity": severity,
        "dependency_name": "packaging",
        "dependency_version": "26.0",
    }


def _pentest_finding(severity: str) -> dict[str, object]:
    return {
        "assessment_reference": "10000000-0000-4000-8000-000000000001",
        "finding_reference": "20000000-0000-4000-8000-000000000001",
        "severity": severity,
        "action_reference": "30000000-0000-4000-8000-000000000001",
        "responsible_reference": "40000000-0000-4000-8000-000000000001",
        "status": "OPEN",
        "revision": 1,
        "retest_outcome": None,
        "retest_evidence_reference": None,
    }


def _catalog_document() -> dict[str, object]:
    return {
        "catalog_version": "29A-catalog-v1",
        "scope": "banking-control-technical-evidence",
        "required_control_ids": ["CTRL-BDDK-IAM-001"],
        "records": [
            {
                "control_id": "CTRL-BDDK-IAM-001",
                "technical_status": "TechnicallyVerified",
                "review_status": "ComplianceReviewRequired",
                "evidence_paths": [EVIDENCE_PATH],
                "blocker_ids": [],
                "decision_reference": None,
            }
        ],
    }
