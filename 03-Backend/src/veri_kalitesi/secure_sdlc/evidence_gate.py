"""Fail-closed drift gate for a stored technical evidence manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
import sys
from collections.abc import Sequence
from pathlib import Path, PurePosixPath
from typing import TextIO

from veri_kalitesi.secure_sdlc.errors import (
    EvidenceManifestTechnicalError,
    EvidenceManifestValidationError,
)
from veri_kalitesi.secure_sdlc.evidence import TechnicalEvidenceManifestBuilder
from veri_kalitesi.secure_sdlc.models import (
    EvidenceManifestVerification,
    EvidenceManifestVerificationStatus,
)


EVIDENCE_MANIFEST_GATE_POLICY_VERSION = "29B-v1"

_MAX_STORED_MANIFEST_SIZE_BYTES = 2_097_152
_MANIFEST_ROOT = PurePosixPath("08-Uyum-Kanitlari/Surum-Paketleri")


class TechnicalEvidenceManifestGate:
    """Regenerate and byte-compare a repository-scoped evidence manifest."""

    policy_version = EVIDENCE_MANIFEST_GATE_POLICY_VERSION

    def __init__(self, builder: TechnicalEvidenceManifestBuilder | None = None) -> None:
        self._builder = builder or TechnicalEvidenceManifestBuilder()

    def verify(
        self,
        catalog_path: Path | str,
        stored_manifest_path: str,
        repository_root: Path | str,
    ) -> EvidenceManifestVerification:
        root = _validate_repository_root(Path(repository_root))
        stored = _read_stored_manifest(root, stored_manifest_path)
        catalog = self._builder.read_catalog(catalog_path)
        generated = self._builder.serialize(self._builder.build(catalog, root))
        status = (
            EvidenceManifestVerificationStatus.MATCH
            if stored == generated
            else EvidenceManifestVerificationStatus.DRIFT
        )
        return EvidenceManifestVerification(
            policy_version=self.policy_version,
            status=status,
            stored_manifest_sha256=hashlib.sha256(stored).hexdigest(),
            generated_manifest_sha256=hashlib.sha256(generated).hexdigest(),
        )

    @staticmethod
    def to_document(result: EvidenceManifestVerification) -> dict[str, str]:
        return {
            "policy_version": result.policy_version,
            "status": result.status.value,
            "stored_manifest_sha256": result.stored_manifest_sha256,
            "generated_manifest_sha256": result.generated_manifest_sha256,
        }


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    output = stdout or sys.stdout
    error_output = stderr or sys.stderr
    parser = argparse.ArgumentParser(
        description="Verify a stored technical evidence manifest against repository evidence."
    )
    parser.add_argument("catalog", type=Path)
    parser.add_argument("stored_manifest")
    parser.add_argument("repository_root", nargs="?", default=Path("."), type=Path)
    arguments = parser.parse_args(argv)
    gate = TechnicalEvidenceManifestGate()

    try:
        result = gate.verify(
            arguments.catalog,
            arguments.stored_manifest,
            arguments.repository_root,
        )
    except EvidenceManifestValidationError as exc:
        _write_error(error_output, "VALIDATION_ERROR", exc.reason_code)
        return 2
    except EvidenceManifestTechnicalError as exc:
        _write_error(error_output, "TECHNICAL_ERROR", exc.operation_code)
        return 2

    output.write(json.dumps(gate.to_document(result), sort_keys=True))
    output.write("\n")
    return 0 if result.status is EvidenceManifestVerificationStatus.MATCH else 1


def _validate_repository_root(path: Path) -> Path:
    if path.is_symlink():
        raise EvidenceManifestValidationError("EVIDENCE_GATE_ROOT_SYMLINK_REJECTED")
    try:
        root_stat = path.stat()
    except FileNotFoundError as exc:
        raise EvidenceManifestValidationError("EVIDENCE_GATE_ROOT_NOT_FOUND") from exc
    except OSError as exc:
        raise EvidenceManifestTechnicalError("EVIDENCE_GATE_ROOT_STAT_FAILED") from exc
    if not stat.S_ISDIR(root_stat.st_mode):
        raise EvidenceManifestValidationError("EVIDENCE_GATE_ROOT_NOT_DIRECTORY")
    return path.resolve()


def _read_stored_manifest(root: Path, value: str) -> bytes:
    normalized = _validate_manifest_path(value)
    candidate = root.joinpath(*normalized.parts)
    current = root
    for part in normalized.parts:
        current = current / part
        if current.is_symlink():
            raise EvidenceManifestValidationError("EVIDENCE_STORED_MANIFEST_SYMLINK_REJECTED")
    try:
        manifest_stat = candidate.stat()
    except FileNotFoundError as exc:
        raise EvidenceManifestValidationError("EVIDENCE_STORED_MANIFEST_NOT_FOUND") from exc
    except OSError as exc:
        raise EvidenceManifestTechnicalError("EVIDENCE_STORED_MANIFEST_STAT_FAILED") from exc
    if not stat.S_ISREG(manifest_stat.st_mode):
        raise EvidenceManifestValidationError("EVIDENCE_STORED_MANIFEST_NOT_REGULAR_FILE")
    if manifest_stat.st_size > _MAX_STORED_MANIFEST_SIZE_BYTES:
        raise EvidenceManifestValidationError("EVIDENCE_STORED_MANIFEST_TOO_LARGE")
    try:
        return candidate.read_bytes()
    except OSError as exc:
        raise EvidenceManifestTechnicalError("EVIDENCE_STORED_MANIFEST_READ_FAILED") from exc


def _validate_manifest_path(value: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value:
        raise EvidenceManifestValidationError("EVIDENCE_STORED_MANIFEST_PATH_INVALID")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or path.parts[: len(_MANIFEST_ROOT.parts)] != _MANIFEST_ROOT.parts
        or len(path.parts) <= len(_MANIFEST_ROOT.parts)
        or any(part in {"", ".", ".."} for part in path.parts)
        or path.as_posix() != value
        or path.suffix != ".json"
    ):
        raise EvidenceManifestValidationError("EVIDENCE_STORED_MANIFEST_PATH_INVALID")
    return path


def _write_error(stream: TextIO, status: str, reason_code: str) -> None:
    stream.write(json.dumps({"status": status, "reason_code": reason_code}, sort_keys=True))
    stream.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
