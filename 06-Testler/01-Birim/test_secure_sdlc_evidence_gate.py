"""BFR-SDLC-002, BRULE-004/005 and NFR-CMP-002/005 manifest drift tests."""

from __future__ import annotations

import hashlib
import io
import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from veri_kalitesi.secure_sdlc.evidence import TechnicalEvidenceManifestBuilder
from veri_kalitesi.secure_sdlc.evidence_gate import (
    EVIDENCE_MANIFEST_GATE_POLICY_VERSION,
    TechnicalEvidenceManifestGate,
    main,
)
from veri_kalitesi.secure_sdlc.errors import (
    EvidenceManifestTechnicalError,
    EvidenceManifestValidationError,
)
from veri_kalitesi.secure_sdlc.models import EvidenceManifestVerificationStatus


CONTROL_ID = "CTRL-BDDK-IAM-001"
EVIDENCE_PATH = "08-Uyum-Kanitlari/Erisim/synthetic-evidence.md"
MANIFEST_PATH = "08-Uyum-Kanitlari/Surum-Paketleri/synthetic-manifest.json"


def test_matches_canonical_stored_manifest(tmp_path: Path) -> None:
    catalog, stored = _prepare_package(tmp_path)

    result = TechnicalEvidenceManifestGate().verify(catalog, MANIFEST_PATH, tmp_path)

    assert result.policy_version == EVIDENCE_MANIFEST_GATE_POLICY_VERSION
    assert result.status is EvidenceManifestVerificationStatus.MATCH
    assert result.stored_manifest_sha256 == result.generated_manifest_sha256
    assert result.stored_manifest_sha256 == hashlib.sha256(stored.read_bytes()).hexdigest()


def test_reports_stored_manifest_drift_without_content(tmp_path: Path) -> None:
    sensitive_marker = "Synthetic-Sensitive-Manifest-Detail"
    catalog, stored = _prepare_package(tmp_path)
    stored.write_text(sensitive_marker, encoding="utf-8")

    result = TechnicalEvidenceManifestGate().verify(catalog, MANIFEST_PATH, tmp_path)
    document = TechnicalEvidenceManifestGate.to_document(result)

    assert result.status is EvidenceManifestVerificationStatus.DRIFT
    assert result.stored_manifest_sha256 != result.generated_manifest_sha256
    assert sensitive_marker not in json.dumps(document)
    assert set(document) == {
        "policy_version",
        "status",
        "stored_manifest_sha256",
        "generated_manifest_sha256",
    }


def test_reports_evidence_artifact_drift(tmp_path: Path) -> None:
    catalog, _ = _prepare_package(tmp_path)
    (tmp_path / EVIDENCE_PATH).write_bytes(b"changed evidence")

    result = TechnicalEvidenceManifestGate().verify(catalog, MANIFEST_PATH, tmp_path)

    assert result.status is EvidenceManifestVerificationStatus.DRIFT


def test_reports_catalog_drift(tmp_path: Path) -> None:
    catalog, _ = _prepare_package(tmp_path)
    document = json.loads(catalog.read_text(encoding="utf-8"))
    document["catalog_version"] = "29B-catalog-v2"
    catalog.write_text(json.dumps(document), encoding="utf-8")

    result = TechnicalEvidenceManifestGate().verify(catalog, MANIFEST_PATH, tmp_path)

    assert result.status is EvidenceManifestVerificationStatus.DRIFT


def test_cli_separates_match_drift_and_validation_error(tmp_path: Path) -> None:
    catalog, stored = _prepare_package(tmp_path)

    match_stdout, match_stderr = io.StringIO(), io.StringIO()
    assert (
        main(
            [str(catalog), MANIFEST_PATH, str(tmp_path)],
            stdout=match_stdout,
            stderr=match_stderr,
        )
        == 0
    )
    assert json.loads(match_stdout.getvalue())["status"] == "MATCH"
    assert match_stderr.getvalue() == ""

    stored.write_bytes(b"drift")
    drift_stdout, drift_stderr = io.StringIO(), io.StringIO()
    assert (
        main(
            [str(catalog), MANIFEST_PATH, str(tmp_path)],
            stdout=drift_stdout,
            stderr=drift_stderr,
        )
        == 1
    )
    assert json.loads(drift_stdout.getvalue())["status"] == "DRIFT"
    assert drift_stderr.getvalue() == ""

    catalog.write_text("{}", encoding="utf-8")
    error_stdout, error_stderr = io.StringIO(), io.StringIO()
    assert (
        main(
            [str(catalog), MANIFEST_PATH, str(tmp_path)],
            stdout=error_stdout,
            stderr=error_stderr,
        )
        == 2
    )
    assert error_stdout.getvalue() == ""
    assert json.loads(error_stderr.getvalue()) == {
        "reason_code": "EVIDENCE_CATALOG_FIELDS_INVALID",
        "status": "VALIDATION_ERROR",
    }
    assert str(tmp_path) not in error_stderr.getvalue()


def test_cli_reports_technical_error_separately(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_verification(*args: object, **kwargs: object) -> None:
        raise EvidenceManifestTechnicalError("EVIDENCE_STORED_MANIFEST_READ_FAILED")

    monkeypatch.setattr(TechnicalEvidenceManifestGate, "verify", fail_verification)
    stdout, stderr = io.StringIO(), io.StringIO()

    assert main(["catalog.json", MANIFEST_PATH, "."], stdout=stdout, stderr=stderr) == 2
    assert stdout.getvalue() == ""
    assert json.loads(stderr.getvalue()) == {
        "reason_code": "EVIDENCE_STORED_MANIFEST_READ_FAILED",
        "status": "TECHNICAL_ERROR",
    }


@pytest.mark.parametrize(
    "manifest_path",
    (
        "/tmp/manifest.json",
        "08-Uyum-Kanitlari/Surum-Paketleri/../manifest.json",
        "08-Uyum-Kanitlari/Surum-Paketleri\\manifest.json",
        "08-Uyum-Kanitlari/Erisim/manifest.json",
        "08-Uyum-Kanitlari/Surum-Paketleri/manifest.md",
        "08-Uyum-Kanitlari/Surum-Paketleri//manifest.json",
    ),
)
def test_rejects_noncanonical_or_out_of_scope_manifest_paths(
    manifest_path: str,
    tmp_path: Path,
) -> None:
    catalog, _ = _prepare_package(tmp_path)

    with pytest.raises(
        EvidenceManifestValidationError,
        match="EVIDENCE_STORED_MANIFEST_PATH_INVALID",
    ):
        TechnicalEvidenceManifestGate().verify(catalog, manifest_path, tmp_path)


def test_rejects_missing_directory_and_symlink_manifest(tmp_path: Path) -> None:
    catalog, stored = _prepare_package(tmp_path)
    stored.unlink()
    with pytest.raises(
        EvidenceManifestValidationError,
        match="EVIDENCE_STORED_MANIFEST_NOT_FOUND",
    ):
        TechnicalEvidenceManifestGate().verify(catalog, MANIFEST_PATH, tmp_path)

    stored.mkdir()
    with pytest.raises(
        EvidenceManifestValidationError,
        match="EVIDENCE_STORED_MANIFEST_NOT_REGULAR_FILE",
    ):
        TechnicalEvidenceManifestGate().verify(catalog, MANIFEST_PATH, tmp_path)

    stored.rmdir()
    target = stored.with_name("target.json")
    target.write_bytes(b"target")
    stored.symlink_to(target)
    with pytest.raises(
        EvidenceManifestValidationError,
        match="EVIDENCE_STORED_MANIFEST_SYMLINK_REJECTED",
    ):
        TechnicalEvidenceManifestGate().verify(catalog, MANIFEST_PATH, tmp_path)


def test_rejects_oversized_stored_manifest(tmp_path: Path) -> None:
    catalog, stored = _prepare_package(tmp_path)
    stored.write_bytes(b"x" * 2_097_153)

    with pytest.raises(
        EvidenceManifestValidationError,
        match="EVIDENCE_STORED_MANIFEST_TOO_LARGE",
    ):
        TechnicalEvidenceManifestGate().verify(catalog, MANIFEST_PATH, tmp_path)


def test_verification_result_is_immutable(tmp_path: Path) -> None:
    catalog, _ = _prepare_package(tmp_path)
    result = TechnicalEvidenceManifestGate().verify(catalog, MANIFEST_PATH, tmp_path)

    with pytest.raises(FrozenInstanceError):
        result.status = EvidenceManifestVerificationStatus.DRIFT  # type: ignore[misc]


def _prepare_package(tmp_path: Path) -> tuple[Path, Path]:
    evidence = tmp_path / EVIDENCE_PATH
    evidence.parent.mkdir(parents=True)
    evidence.write_bytes(b"synthetic technical evidence\n")

    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps(_catalog_document()), encoding="utf-8")
    builder = TechnicalEvidenceManifestBuilder()
    manifest = builder.build(builder.read_catalog(catalog), tmp_path)

    stored = tmp_path / MANIFEST_PATH
    stored.parent.mkdir(parents=True)
    stored.write_bytes(builder.serialize(manifest))
    return catalog, stored


def _catalog_document() -> dict[str, object]:
    return {
        "catalog_version": "29A-catalog-v1",
        "scope": "banking-control-technical-evidence",
        "required_control_ids": [CONTROL_ID],
        "records": [
            {
                "control_id": CONTROL_ID,
                "technical_status": "TechnicallyVerified",
                "review_status": "ComplianceReviewRequired",
                "evidence_paths": [EVIDENCE_PATH],
                "blocker_ids": [],
                "decision_reference": None,
            }
        ],
    }
