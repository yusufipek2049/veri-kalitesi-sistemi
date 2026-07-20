"""Deterministic, data-minimum technical evidence package manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any, TextIO, cast
from uuid import UUID

from veri_kalitesi.secure_sdlc.errors import (
    EvidenceManifestTechnicalError,
    EvidenceManifestValidationError,
)
from veri_kalitesi.secure_sdlc.models import (
    ControlEvidenceRecord,
    EvidenceArtifact,
    EvidenceReviewStatus,
    EvidenceTechnicalStatus,
    ManifestControlRecord,
    TechnicalEvidenceCatalog,
    TechnicalEvidenceManifest,
)


EVIDENCE_MANIFEST_POLICY_VERSION = "29A-v1"
EVIDENCE_MANIFEST_SCHEMA_VERSION = 1

_MAX_CATALOG_SIZE_BYTES = 1_048_576
_MAX_EVIDENCE_SIZE_BYTES = 2_097_152
_CATALOG_FIELDS = frozenset({"catalog_version", "scope", "required_control_ids", "records"})
_RECORD_FIELDS = frozenset(
    {
        "control_id",
        "technical_status",
        "review_status",
        "evidence_paths",
        "blocker_ids",
        "decision_reference",
    }
)
_CONTROL_ID_PATTERN = re.compile(r"CTRL-(?:BDDK|KVKK)-[A-Z]+-[0-9]{3}")
_BLOCKER_ID_PATTERN = re.compile(r"OPEN-BNK-[0-9]{3}")
_VERSION_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}")
_SCOPE_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]{0,79}")
_ALLOWED_EVIDENCE_SUFFIXES = frozenset({".json", ".md"})
_EVIDENCE_ROOT = PurePosixPath("08-Uyum-Kanitlari")


class TechnicalEvidenceManifestBuilder:
    """Validate a control catalog and hash referenced evidence without modifying it."""

    policy_version = EVIDENCE_MANIFEST_POLICY_VERSION
    schema_version = EVIDENCE_MANIFEST_SCHEMA_VERSION

    def read_catalog(self, catalog_path: Path | str) -> TechnicalEvidenceCatalog:
        path = Path(catalog_path)
        if path.is_symlink():
            raise EvidenceManifestValidationError("EVIDENCE_CATALOG_SYMLINK_REJECTED")
        try:
            catalog_stat = path.stat()
        except FileNotFoundError as exc:
            raise EvidenceManifestValidationError("EVIDENCE_CATALOG_NOT_FOUND") from exc
        except OSError as exc:
            raise EvidenceManifestTechnicalError("EVIDENCE_CATALOG_STAT_FAILED") from exc
        if not stat.S_ISREG(catalog_stat.st_mode):
            raise EvidenceManifestValidationError("EVIDENCE_CATALOG_NOT_REGULAR_FILE")
        if catalog_stat.st_size > _MAX_CATALOG_SIZE_BYTES:
            raise EvidenceManifestValidationError("EVIDENCE_CATALOG_TOO_LARGE")

        try:
            content = path.read_bytes()
        except OSError as exc:
            raise EvidenceManifestTechnicalError("EVIDENCE_CATALOG_READ_FAILED") from exc
        try:
            document = json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise EvidenceManifestValidationError("EVIDENCE_CATALOG_PARSE_FAILED") from exc
        return _parse_catalog(document)

    def build(
        self,
        catalog: TechnicalEvidenceCatalog,
        repository_root: Path | str,
    ) -> TechnicalEvidenceManifest:
        _validate_catalog(catalog)
        root = _validate_repository_root(Path(repository_root))
        controls = tuple(
            self._build_control(record, root)
            for record in sorted(catalog.records, key=lambda item: item.control_id)
        )
        technical_counts = Counter(item.technical_status.value for item in controls)
        review_counts = Counter(item.review_status.value for item in controls)
        artifact_paths = {
            artifact.relative_path
            for control in controls
            for artifact in control.evidence_artifacts
        }

        return TechnicalEvidenceManifest(
            schema_version=self.schema_version,
            policy_version=self.policy_version,
            catalog_version=catalog.catalog_version,
            scope=catalog.scope,
            required_control_count=len(catalog.required_control_ids),
            control_count=len(controls),
            unique_evidence_artifact_count=len(artifact_paths),
            technical_status_counts=tuple(
                (status.value, technical_counts[status.value]) for status in EvidenceTechnicalStatus
            ),
            review_status_counts=tuple(
                (status.value, review_counts[status.value]) for status in EvidenceReviewStatus
            ),
            missing_control_ids=tuple(
                item.control_id
                for item in controls
                if item.technical_status is EvidenceTechnicalStatus.MISSING
            ),
            blocked_control_ids=tuple(item.control_id for item in controls if item.blocker_ids),
            compliance_review_required_control_ids=tuple(
                item.control_id
                for item in controls
                if item.review_status is EvidenceReviewStatus.COMPLIANCE_REVIEW_REQUIRED
            ),
            controls=controls,
            controls_digest=_controls_digest(controls),
        )

    @staticmethod
    def to_document(manifest: TechnicalEvidenceManifest) -> dict[str, object]:
        return {
            "schema_version": manifest.schema_version,
            "policy_version": manifest.policy_version,
            "catalog_version": manifest.catalog_version,
            "scope": manifest.scope,
            "required_control_count": manifest.required_control_count,
            "control_count": manifest.control_count,
            "unique_evidence_artifact_count": manifest.unique_evidence_artifact_count,
            "technical_status_counts": dict(manifest.technical_status_counts),
            "review_status_counts": dict(manifest.review_status_counts),
            "missing_control_ids": list(manifest.missing_control_ids),
            "blocked_control_ids": list(manifest.blocked_control_ids),
            "compliance_review_required_control_ids": list(
                manifest.compliance_review_required_control_ids
            ),
            "controls": [_control_document(item) for item in manifest.controls],
            "controls_digest": manifest.controls_digest,
        }

    @staticmethod
    def _build_control(
        record: ControlEvidenceRecord,
        root: Path,
    ) -> ManifestControlRecord:
        artifacts = tuple(
            sorted(
                (_read_evidence_artifact(root, path) for path in record.evidence_paths),
                key=lambda item: item.relative_path,
            )
        )
        return ManifestControlRecord(
            control_id=record.control_id,
            technical_status=record.technical_status,
            review_status=record.review_status,
            evidence_artifacts=artifacts,
            blocker_ids=tuple(sorted(record.blocker_ids)),
            decision_reference=record.decision_reference,
        )


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    output = stdout or sys.stdout
    error_output = stderr or sys.stderr
    parser = argparse.ArgumentParser(
        description="Generate a deterministic technical evidence control manifest."
    )
    parser.add_argument("catalog", type=Path)
    parser.add_argument("repository_root", nargs="?", default=Path("."), type=Path)
    arguments = parser.parse_args(argv)
    builder = TechnicalEvidenceManifestBuilder()

    try:
        catalog = builder.read_catalog(arguments.catalog)
        manifest = builder.build(catalog, arguments.repository_root)
    except EvidenceManifestValidationError as exc:
        _write_error(error_output, "VALIDATION_ERROR", exc.reason_code)
        return 2
    except EvidenceManifestTechnicalError as exc:
        _write_error(error_output, "TECHNICAL_ERROR", exc.operation_code)
        return 2

    output.write(
        json.dumps(builder.to_document(manifest), ensure_ascii=True, indent=2, sort_keys=True)
    )
    output.write("\n")
    return 0


def _parse_catalog(document: object) -> TechnicalEvidenceCatalog:
    if not isinstance(document, Mapping) or set(document) != _CATALOG_FIELDS:
        raise EvidenceManifestValidationError("EVIDENCE_CATALOG_FIELDS_INVALID")
    payload = cast(Mapping[str, Any], document)
    records_value = payload.get("records")
    if not isinstance(records_value, list):
        raise EvidenceManifestValidationError("EVIDENCE_RECORDS_INVALID")
    return TechnicalEvidenceCatalog(
        catalog_version=_required_text(
            payload,
            "catalog_version",
            "EVIDENCE_CATALOG_VERSION_INVALID",
        ),
        scope=_required_text(payload, "scope", "EVIDENCE_SCOPE_INVALID"),
        required_control_ids=_string_tuple(
            payload.get("required_control_ids"),
            "EVIDENCE_REQUIRED_CONTROL_IDS_INVALID",
        ),
        records=tuple(_parse_record(item) for item in records_value),
    )


def _parse_record(value: object) -> ControlEvidenceRecord:
    if not isinstance(value, Mapping) or set(value) != _RECORD_FIELDS:
        raise EvidenceManifestValidationError("EVIDENCE_RECORD_FIELDS_INVALID")
    payload = cast(Mapping[str, Any], value)
    try:
        technical_status = EvidenceTechnicalStatus(
            _required_text(payload, "technical_status", "EVIDENCE_TECHNICAL_STATUS_INVALID")
        )
    except ValueError as exc:
        raise EvidenceManifestValidationError("EVIDENCE_TECHNICAL_STATUS_INVALID") from exc
    try:
        review_status = EvidenceReviewStatus(
            _required_text(payload, "review_status", "EVIDENCE_REVIEW_STATUS_INVALID")
        )
    except ValueError as exc:
        raise EvidenceManifestValidationError("EVIDENCE_REVIEW_STATUS_INVALID") from exc

    decision_value = payload.get("decision_reference")
    decision_reference: UUID | None = None
    if decision_value is not None:
        if not isinstance(decision_value, str):
            raise EvidenceManifestValidationError("EVIDENCE_DECISION_REFERENCE_INVALID")
        try:
            decision_reference = UUID(decision_value)
        except ValueError as exc:
            raise EvidenceManifestValidationError("EVIDENCE_DECISION_REFERENCE_INVALID") from exc

    return ControlEvidenceRecord(
        control_id=_required_text(payload, "control_id", "EVIDENCE_CONTROL_ID_INVALID"),
        technical_status=technical_status,
        review_status=review_status,
        evidence_paths=_string_tuple(
            payload.get("evidence_paths"),
            "EVIDENCE_PATHS_INVALID",
        ),
        blocker_ids=_string_tuple(payload.get("blocker_ids"), "EVIDENCE_BLOCKER_IDS_INVALID"),
        decision_reference=decision_reference,
    )


def _validate_catalog(catalog: TechnicalEvidenceCatalog) -> None:
    if not isinstance(catalog, TechnicalEvidenceCatalog):
        raise EvidenceManifestValidationError("EVIDENCE_CATALOG_INVALID")
    if not _VERSION_PATTERN.fullmatch(catalog.catalog_version):
        raise EvidenceManifestValidationError("EVIDENCE_CATALOG_VERSION_INVALID")
    if not _SCOPE_PATTERN.fullmatch(catalog.scope):
        raise EvidenceManifestValidationError("EVIDENCE_SCOPE_INVALID")
    required = _validate_identifiers(
        catalog.required_control_ids,
        _CONTROL_ID_PATTERN,
        "EVIDENCE_REQUIRED_CONTROL_IDS_INVALID",
    )
    if not required:
        raise EvidenceManifestValidationError("EVIDENCE_REQUIRED_CONTROL_IDS_INVALID")
    if not isinstance(catalog.records, tuple):
        raise EvidenceManifestValidationError("EVIDENCE_RECORDS_INVALID")

    record_ids: set[str] = set()
    for record in catalog.records:
        _validate_record(record)
        if record.control_id in record_ids:
            raise EvidenceManifestValidationError("EVIDENCE_DUPLICATE_CONTROL_RECORD")
        record_ids.add(record.control_id)
    if record_ids != required:
        raise EvidenceManifestValidationError("EVIDENCE_CONTROL_COVERAGE_INCOMPLETE")


def _validate_record(record: ControlEvidenceRecord) -> None:
    if not isinstance(record, ControlEvidenceRecord):
        raise EvidenceManifestValidationError("EVIDENCE_RECORD_INVALID")
    if not _CONTROL_ID_PATTERN.fullmatch(record.control_id):
        raise EvidenceManifestValidationError("EVIDENCE_CONTROL_ID_INVALID")
    if not isinstance(record.technical_status, EvidenceTechnicalStatus):
        raise EvidenceManifestValidationError("EVIDENCE_TECHNICAL_STATUS_INVALID")
    if not isinstance(record.review_status, EvidenceReviewStatus):
        raise EvidenceManifestValidationError("EVIDENCE_REVIEW_STATUS_INVALID")
    paths = _validate_unique_strings(record.evidence_paths, "EVIDENCE_PATHS_INVALID")
    _validate_identifiers(
        record.blocker_ids,
        _BLOCKER_ID_PATTERN,
        "EVIDENCE_BLOCKER_IDS_INVALID",
    )
    if record.technical_status is EvidenceTechnicalStatus.MISSING:
        if paths:
            raise EvidenceManifestValidationError("EVIDENCE_MISSING_STATUS_HAS_ARTIFACT")
    elif not paths:
        raise EvidenceManifestValidationError("EVIDENCE_TECHNICAL_STATUS_REQUIRES_ARTIFACT")

    requires_decision = record.review_status in {
        EvidenceReviewStatus.APPROVED_BY_BANK,
        EvidenceReviewStatus.NOT_APPLICABLE,
    }
    if requires_decision:
        if not isinstance(record.decision_reference, UUID) or record.decision_reference.int == 0:
            raise EvidenceManifestValidationError("EVIDENCE_DECISION_REFERENCE_REQUIRED")
    elif record.decision_reference is not None:
        raise EvidenceManifestValidationError("EVIDENCE_DECISION_REFERENCE_NOT_ALLOWED")


def _validate_repository_root(path: Path) -> Path:
    if path.is_symlink():
        raise EvidenceManifestValidationError("EVIDENCE_REPOSITORY_ROOT_SYMLINK_REJECTED")
    try:
        root_stat = path.stat()
    except FileNotFoundError as exc:
        raise EvidenceManifestValidationError("EVIDENCE_REPOSITORY_ROOT_NOT_FOUND") from exc
    except OSError as exc:
        raise EvidenceManifestTechnicalError("EVIDENCE_REPOSITORY_ROOT_STAT_FAILED") from exc
    if not stat.S_ISDIR(root_stat.st_mode):
        raise EvidenceManifestValidationError("EVIDENCE_REPOSITORY_ROOT_NOT_DIRECTORY")
    return path.resolve()


def _read_evidence_artifact(root: Path, relative_path: str) -> EvidenceArtifact:
    normalized = _validate_evidence_path(relative_path)
    candidate = root.joinpath(*normalized.parts)
    current = root
    for part in normalized.parts:
        current = current / part
        if current.is_symlink():
            raise EvidenceManifestValidationError("EVIDENCE_ARTIFACT_SYMLINK_REJECTED")
    try:
        artifact_stat = candidate.stat()
    except FileNotFoundError as exc:
        raise EvidenceManifestValidationError("EVIDENCE_ARTIFACT_NOT_FOUND") from exc
    except OSError as exc:
        raise EvidenceManifestTechnicalError("EVIDENCE_ARTIFACT_STAT_FAILED") from exc
    if not stat.S_ISREG(artifact_stat.st_mode):
        raise EvidenceManifestValidationError("EVIDENCE_ARTIFACT_NOT_REGULAR_FILE")
    if artifact_stat.st_size > _MAX_EVIDENCE_SIZE_BYTES:
        raise EvidenceManifestValidationError("EVIDENCE_ARTIFACT_TOO_LARGE")
    try:
        content = candidate.read_bytes()
    except OSError as exc:
        raise EvidenceManifestTechnicalError("EVIDENCE_ARTIFACT_READ_FAILED") from exc
    return EvidenceArtifact(
        relative_path=normalized.as_posix(),
        sha256=hashlib.sha256(content).hexdigest(),
    )


def _validate_evidence_path(value: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value:
        raise EvidenceManifestValidationError("EVIDENCE_PATH_INVALID")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or path.parts[:1] != (_EVIDENCE_ROOT.as_posix(),)
        or any(part in {"", ".", ".."} for part in path.parts)
        or path.as_posix() != value
        or path.suffix not in _ALLOWED_EVIDENCE_SUFFIXES
    ):
        raise EvidenceManifestValidationError("EVIDENCE_PATH_INVALID")
    return path


def _controls_digest(controls: tuple[ManifestControlRecord, ...]) -> str:
    canonical = json.dumps(
        [_control_document(control) for control in controls],
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _control_document(control: ManifestControlRecord) -> dict[str, object]:
    return {
        "control_id": control.control_id,
        "technical_status": control.technical_status.value,
        "review_status": control.review_status.value,
        "evidence_artifacts": [
            {"relative_path": item.relative_path, "sha256": item.sha256}
            for item in control.evidence_artifacts
        ],
        "blocker_ids": list(control.blocker_ids),
        "decision_reference": (
            str(control.decision_reference) if control.decision_reference is not None else None
        ),
    }


def _validate_identifiers(
    values: object,
    pattern: re.Pattern[str],
    reason_code: str,
) -> set[str]:
    strings = _validate_unique_strings(values, reason_code)
    if any(pattern.fullmatch(item) is None for item in strings):
        raise EvidenceManifestValidationError(reason_code)
    return strings


def _validate_unique_strings(values: object, reason_code: str) -> set[str]:
    if not isinstance(values, tuple) or any(not isinstance(item, str) for item in values):
        raise EvidenceManifestValidationError(reason_code)
    result = set(values)
    if len(result) != len(values):
        raise EvidenceManifestValidationError(reason_code)
    return result


def _string_tuple(value: object, reason_code: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise EvidenceManifestValidationError(reason_code)
    return tuple(value)


def _required_text(payload: Mapping[str, Any], key: str, reason_code: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise EvidenceManifestValidationError(reason_code)
    return value


def _write_error(stream: TextIO, status: str, reason_code: str) -> None:
    stream.write(json.dumps({"status": status, "reason_code": reason_code}, sort_keys=True))
    stream.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
