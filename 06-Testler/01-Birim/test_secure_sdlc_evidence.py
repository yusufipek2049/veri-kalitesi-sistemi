"""BFR-SDLC-002, BRULE-004/005 and NFR-CMP-002/005 evidence manifest tests."""

from __future__ import annotations

import hashlib
import io
import json
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from typing import cast
from uuid import UUID

import pytest

from veri_kalitesi.secure_sdlc.evidence import (
    EVIDENCE_MANIFEST_POLICY_VERSION,
    TechnicalEvidenceManifestBuilder,
    main,
)
from veri_kalitesi.secure_sdlc.errors import (
    EvidenceManifestValidationError,
)
from veri_kalitesi.secure_sdlc.models import (
    ControlEvidenceRecord,
    EvidenceReviewStatus,
    EvidenceTechnicalStatus,
    TechnicalEvidenceCatalog,
)


CONTROL_A = "CTRL-BDDK-IAM-001"
CONTROL_B = "CTRL-KVKK-DEL-001"
EVIDENCE_A = "08-Uyum-Kanitlari/Erisim/synthetic-evidence.md"
DECISION_REFERENCE = UUID("10000000-0000-4000-8000-000000000001")


def test_builds_deterministic_data_minimum_manifest(tmp_path: Path) -> None:
    _write_evidence(tmp_path, EVIDENCE_A, b"synthetic technical evidence\n")
    catalog = _catalog(records=(_record(), _missing_record()))
    builder = TechnicalEvidenceManifestBuilder()

    first = builder.build(catalog, tmp_path)
    second = builder.build(
        replace(catalog, records=tuple(reversed(catalog.records))),
        tmp_path,
    )

    assert first == second
    assert first.policy_version == EVIDENCE_MANIFEST_POLICY_VERSION
    assert first.required_control_count == 2
    assert first.control_count == 2
    assert first.unique_evidence_artifact_count == 1
    assert first.missing_control_ids == (CONTROL_B,)
    assert first.blocked_control_ids == (CONTROL_B,)
    assert first.compliance_review_required_control_ids == (CONTROL_A, CONTROL_B)
    assert dict(first.technical_status_counts) == {
        "TechnicallyVerified": 1,
        "Partial": 0,
        "Missing": 1,
    }
    assert len(first.controls_digest) == 64


def test_manifest_hashes_artifact_without_copying_content(tmp_path: Path) -> None:
    sensitive_marker = b"Synthetic-Report-Detail-Must-Remain-In-Artifact"
    _write_evidence(tmp_path, EVIDENCE_A, sensitive_marker)

    manifest = TechnicalEvidenceManifestBuilder().build(
        _catalog(records=(_record(), _missing_record())),
        tmp_path,
    )
    document = TechnicalEvidenceManifestBuilder.to_document(manifest)
    serialized = json.dumps(document, sort_keys=True)
    artifact = manifest.controls[0].evidence_artifacts[0]

    assert artifact.sha256 == hashlib.sha256(sensitive_marker).hexdigest()
    assert sensitive_marker.decode() not in serialized
    assert set(document) == {
        "schema_version",
        "policy_version",
        "catalog_version",
        "scope",
        "required_control_count",
        "control_count",
        "unique_evidence_artifact_count",
        "technical_status_counts",
        "review_status_counts",
        "missing_control_ids",
        "blocked_control_ids",
        "compliance_review_required_control_ids",
        "controls",
        "controls_digest",
    }


def test_artifact_change_changes_control_digest(tmp_path: Path) -> None:
    evidence_path = _write_evidence(tmp_path, EVIDENCE_A, b"first")
    builder = TechnicalEvidenceManifestBuilder()
    catalog = _catalog(records=(_record(), _missing_record()))
    first = builder.build(catalog, tmp_path)

    evidence_path.write_bytes(b"second")
    second = builder.build(catalog, tmp_path)

    assert first.controls_digest != second.controls_digest


def test_reads_exact_json_catalog_contract(tmp_path: Path) -> None:
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps(_catalog_document()), encoding="utf-8")

    catalog = TechnicalEvidenceManifestBuilder().read_catalog(catalog_path)

    assert catalog == _catalog(records=(_record(), _missing_record()))


@pytest.mark.parametrize("extra_field", ("approved", "notes", "owner", "secret"))
def test_rejects_extra_catalog_fields(extra_field: str, tmp_path: Path) -> None:
    document = _catalog_document()
    document[extra_field] = "Synthetic-Sensitive-Value"
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(EvidenceManifestValidationError, match="EVIDENCE_CATALOG_FIELDS_INVALID"):
        TechnicalEvidenceManifestBuilder().read_catalog(catalog_path)


@pytest.mark.parametrize("extra_field", ("description", "approval_note", "username", "token"))
def test_rejects_extra_record_fields(extra_field: str, tmp_path: Path) -> None:
    document = _catalog_document()
    records = document["records"]
    assert isinstance(records, list)
    record = records[0]
    assert isinstance(record, dict)
    record[extra_field] = "Synthetic-Sensitive-Value"
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(EvidenceManifestValidationError, match="EVIDENCE_RECORD_FIELDS_INVALID"):
        TechnicalEvidenceManifestBuilder().read_catalog(catalog_path)


@pytest.mark.parametrize(
    ("field", "value", "reason_code"),
    (
        ("catalog_version", "bad version", "EVIDENCE_CATALOG_VERSION_INVALID"),
        ("scope", "Bank Scope", "EVIDENCE_SCOPE_INVALID"),
        ("required_control_ids", (CONTROL_A, CONTROL_A), "EVIDENCE_REQUIRED_CONTROL_IDS_INVALID"),
        (
            "required_control_ids",
            ("BFR-AUD-001", CONTROL_B),
            "EVIDENCE_REQUIRED_CONTROL_IDS_INVALID",
        ),
    ),
)
def test_rejects_invalid_catalog_values(
    field: str,
    value: object,
    reason_code: str,
) -> None:
    catalog = _replace_catalog_field(
        _catalog(records=(_record(), _missing_record())),
        field,
        value,
    )

    with pytest.raises(EvidenceManifestValidationError, match=reason_code):
        TechnicalEvidenceManifestBuilder().build(catalog, ".")


def test_requires_exact_control_coverage() -> None:
    missing_record = _catalog(records=(_record(),))
    duplicate_record = _catalog(records=(_record(), _record()))

    with pytest.raises(
        EvidenceManifestValidationError,
        match="EVIDENCE_CONTROL_COVERAGE_INCOMPLETE",
    ):
        TechnicalEvidenceManifestBuilder().build(missing_record, ".")
    with pytest.raises(
        EvidenceManifestValidationError,
        match="EVIDENCE_DUPLICATE_CONTROL_RECORD",
    ):
        TechnicalEvidenceManifestBuilder().build(duplicate_record, ".")


@pytest.mark.parametrize(
    ("field", "value", "reason_code"),
    (
        (
            "technical_status",
            EvidenceTechnicalStatus.MISSING,
            "EVIDENCE_MISSING_STATUS_HAS_ARTIFACT",
        ),
        (
            "evidence_paths",
            (),
            "EVIDENCE_TECHNICAL_STATUS_REQUIRES_ARTIFACT",
        ),
        (
            "evidence_paths",
            (EVIDENCE_A, EVIDENCE_A),
            "EVIDENCE_PATHS_INVALID",
        ),
        (
            "blocker_ids",
            ("OPEN-BNK-001", "OPEN-BNK-001"),
            "EVIDENCE_BLOCKER_IDS_INVALID",
        ),
        (
            "blocker_ids",
            ("INCIDENT-001",),
            "EVIDENCE_BLOCKER_IDS_INVALID",
        ),
    ),
)
def test_rejects_inconsistent_control_records(
    field: str,
    value: object,
    reason_code: str,
) -> None:
    record = _replace_record_field(_record(), field, value)
    catalog = _catalog(records=(record, _missing_record()))

    with pytest.raises(EvidenceManifestValidationError, match=reason_code):
        TechnicalEvidenceManifestBuilder().build(catalog, ".")


@pytest.mark.parametrize(
    "review_status",
    (EvidenceReviewStatus.APPROVED_BY_BANK, EvidenceReviewStatus.NOT_APPLICABLE),
)
def test_bank_or_not_applicable_status_requires_opaque_decision_reference(
    review_status: EvidenceReviewStatus,
) -> None:
    record = replace(_record(), review_status=review_status)

    with pytest.raises(
        EvidenceManifestValidationError,
        match="EVIDENCE_DECISION_REFERENCE_REQUIRED",
    ):
        TechnicalEvidenceManifestBuilder().build(
            _catalog(records=(record, _missing_record())),
            ".",
        )


def test_accepts_bank_status_only_with_decision_reference(tmp_path: Path) -> None:
    _write_evidence(tmp_path, EVIDENCE_A, b"evidence")
    approved = replace(
        _record(),
        review_status=EvidenceReviewStatus.APPROVED_BY_BANK,
        decision_reference=DECISION_REFERENCE,
    )

    manifest = TechnicalEvidenceManifestBuilder().build(
        _catalog(records=(approved, _missing_record())),
        tmp_path,
    )

    assert manifest.controls[0].decision_reference == DECISION_REFERENCE
    assert manifest.controls[0].review_status is EvidenceReviewStatus.APPROVED_BY_BANK


def test_compliance_review_cannot_carry_false_approval_reference() -> None:
    record = replace(_record(), decision_reference=DECISION_REFERENCE)

    with pytest.raises(
        EvidenceManifestValidationError,
        match="EVIDENCE_DECISION_REFERENCE_NOT_ALLOWED",
    ):
        TechnicalEvidenceManifestBuilder().build(
            _catalog(records=(record, _missing_record())),
            ".",
        )


@pytest.mark.parametrize(
    "relative_path",
    (
        "/tmp/evidence.md",
        "08-Uyum-Kanitlari/../README.md",
        "08-Uyum-Kanitlari\\Erisim\\evidence.md",
        "README.md",
        "08-Uyum-Kanitlari/Erisim/evidence.txt",
        "08-Uyum-Kanitlari//Erisim/evidence.md",
    ),
)
def test_rejects_noncanonical_or_out_of_scope_evidence_paths(
    relative_path: str,
) -> None:
    record = replace(_record(), evidence_paths=(relative_path,))

    with pytest.raises(EvidenceManifestValidationError, match="EVIDENCE_PATH_INVALID"):
        TechnicalEvidenceManifestBuilder().build(
            _catalog(records=(record, _missing_record())),
            ".",
        )


def test_rejects_missing_directory_and_symlink_evidence(tmp_path: Path) -> None:
    missing_catalog = _catalog(records=(_record(), _missing_record()))
    with pytest.raises(EvidenceManifestValidationError, match="EVIDENCE_ARTIFACT_NOT_FOUND"):
        TechnicalEvidenceManifestBuilder().build(missing_catalog, tmp_path)

    target = _write_evidence(tmp_path, "08-Uyum-Kanitlari/Erisim/target.md", b"target")
    link = tmp_path / EVIDENCE_A
    link.symlink_to(target)
    with pytest.raises(
        EvidenceManifestValidationError,
        match="EVIDENCE_ARTIFACT_SYMLINK_REJECTED",
    ):
        TechnicalEvidenceManifestBuilder().build(missing_catalog, tmp_path)


def test_rejects_oversized_evidence(tmp_path: Path) -> None:
    _write_evidence(tmp_path, EVIDENCE_A, b"x" * 2_097_153)

    with pytest.raises(EvidenceManifestValidationError, match="EVIDENCE_ARTIFACT_TOO_LARGE"):
        TechnicalEvidenceManifestBuilder().build(
            _catalog(records=(_record(), _missing_record())),
            tmp_path,
        )


def test_rejects_malformed_and_symlink_catalog(tmp_path: Path) -> None:
    malformed = tmp_path / "malformed.json"
    malformed.write_text("{", encoding="utf-8")
    with pytest.raises(EvidenceManifestValidationError, match="EVIDENCE_CATALOG_PARSE_FAILED"):
        TechnicalEvidenceManifestBuilder().read_catalog(malformed)

    target = tmp_path / "target.json"
    target.write_text(json.dumps(_catalog_document()), encoding="utf-8")
    link = tmp_path / "catalog.json"
    link.symlink_to(target)
    with pytest.raises(
        EvidenceManifestValidationError,
        match="EVIDENCE_CATALOG_SYMLINK_REJECTED",
    ):
        TechnicalEvidenceManifestBuilder().read_catalog(link)


def test_cli_outputs_manifest_and_data_minimum_error(tmp_path: Path) -> None:
    _write_evidence(tmp_path, EVIDENCE_A, b"evidence")
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps(_catalog_document()), encoding="utf-8")
    stdout = io.StringIO()
    stderr = io.StringIO()

    assert main([str(catalog_path), str(tmp_path)], stdout=stdout, stderr=stderr) == 0
    assert json.loads(stdout.getvalue())["missing_control_ids"] == [CONTROL_B]
    assert stderr.getvalue() == ""

    catalog_path.write_text("{}", encoding="utf-8")
    stdout = io.StringIO()
    stderr = io.StringIO()
    assert main([str(catalog_path), str(tmp_path)], stdout=stdout, stderr=stderr) == 2
    assert stdout.getvalue() == ""
    assert json.loads(stderr.getvalue()) == {
        "reason_code": "EVIDENCE_CATALOG_FIELDS_INVALID",
        "status": "VALIDATION_ERROR",
    }
    assert str(tmp_path) not in stderr.getvalue()


def test_manifest_models_are_immutable(tmp_path: Path) -> None:
    _write_evidence(tmp_path, EVIDENCE_A, b"evidence")
    manifest = TechnicalEvidenceManifestBuilder().build(
        _catalog(records=(_record(), _missing_record())),
        tmp_path,
    )

    with pytest.raises(FrozenInstanceError):
        manifest.scope = "changed"  # type: ignore[misc]


def _catalog(*, records: tuple[ControlEvidenceRecord, ...]) -> TechnicalEvidenceCatalog:
    return TechnicalEvidenceCatalog(
        catalog_version="29A-catalog-v1",
        scope="banking-control-technical-evidence",
        required_control_ids=(CONTROL_A, CONTROL_B),
        records=records,
    )


def _record() -> ControlEvidenceRecord:
    return ControlEvidenceRecord(
        control_id=CONTROL_A,
        technical_status=EvidenceTechnicalStatus.TECHNICALLY_VERIFIED,
        review_status=EvidenceReviewStatus.COMPLIANCE_REVIEW_REQUIRED,
        evidence_paths=(EVIDENCE_A,),
    )


def _missing_record() -> ControlEvidenceRecord:
    return ControlEvidenceRecord(
        control_id=CONTROL_B,
        technical_status=EvidenceTechnicalStatus.MISSING,
        review_status=EvidenceReviewStatus.COMPLIANCE_REVIEW_REQUIRED,
        evidence_paths=(),
        blocker_ids=("OPEN-BNK-008",),
    )


def _catalog_document() -> dict[str, object]:
    return {
        "catalog_version": "29A-catalog-v1",
        "scope": "banking-control-technical-evidence",
        "required_control_ids": [CONTROL_A, CONTROL_B],
        "records": [
            {
                "control_id": CONTROL_A,
                "technical_status": "TechnicallyVerified",
                "review_status": "ComplianceReviewRequired",
                "evidence_paths": [EVIDENCE_A],
                "blocker_ids": [],
                "decision_reference": None,
            },
            {
                "control_id": CONTROL_B,
                "technical_status": "Missing",
                "review_status": "ComplianceReviewRequired",
                "evidence_paths": [],
                "blocker_ids": ["OPEN-BNK-008"],
                "decision_reference": None,
            },
        ],
    }


def _write_evidence(root: Path, relative_path: str, content: bytes) -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def _replace_catalog_field(
    catalog: TechnicalEvidenceCatalog,
    field: str,
    value: object,
) -> TechnicalEvidenceCatalog:
    if field == "catalog_version":
        return replace(catalog, catalog_version=cast(str, value))
    if field == "scope":
        return replace(catalog, scope=cast(str, value))
    if field == "required_control_ids":
        return replace(catalog, required_control_ids=cast(tuple[str, ...], value))
    raise AssertionError(field)


def _replace_record_field(
    record: ControlEvidenceRecord,
    field: str,
    value: object,
) -> ControlEvidenceRecord:
    if field == "technical_status":
        return replace(record, technical_status=cast(EvidenceTechnicalStatus, value))
    if field == "evidence_paths":
        return replace(record, evidence_paths=cast(tuple[str, ...], value))
    if field == "blocker_ids":
        return replace(record, blocker_ids=cast(tuple[str, ...], value))
    raise AssertionError(field)
