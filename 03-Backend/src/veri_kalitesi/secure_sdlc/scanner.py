"""Read-only, data-minimum repository secret scanner."""

from __future__ import annotations

import os
import re
import stat
from pathlib import Path

from veri_kalitesi.secure_sdlc.errors import (
    SecretScanTechnicalError,
    SecretScanValidationError,
)
from veri_kalitesi.secure_sdlc.models import (
    SecretFinding,
    SecretScanPolicy,
    SecretScanReport,
)

_PRIVATE_KEY_PATTERN = re.compile(r"-----BEGIN (?:[A-Z0-9]+ )?PRIVATE KEY-----")
_CLOUD_ACCESS_KEY_PATTERN = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
_GITHUB_TOKEN_PATTERN = re.compile(
    r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"
)
_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(?:password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|private[_-]?key)\b"
    r"\s*[:=]\s*(['\"])(?P<value>[^'\"]+)\1"
)
_SAFE_LITERAL_VALUES = frozenset(
    {
        "changeme",
        "example",
        "example-only",
        "not-real",
        "placeholder",
        "synthetic",
        "test",
    }
)
_SAFE_LITERAL_PREFIXES = ("${", "$", "env:", "secret://", "vault:")


class RepositorySecretScanner:
    """Scan text files without returning matched values or changing source files."""

    def __init__(self, policy: SecretScanPolicy | None = None) -> None:
        self._policy = policy or SecretScanPolicy()
        self._validate_policy(self._policy)

    def scan(self, root: Path | str) -> SecretScanReport:
        scan_root = Path(root)
        try:
            root_stat = scan_root.stat()
        except FileNotFoundError:
            raise SecretScanValidationError("SCAN_ROOT_NOT_FOUND")
        except OSError as exc:
            raise SecretScanTechnicalError("SCAN_ROOT_STAT_FAILED", ".") from exc
        if not stat.S_ISDIR(root_stat.st_mode):
            raise SecretScanValidationError("SCAN_ROOT_NOT_DIRECTORY")

        try:
            scan_root = scan_root.resolve(strict=True)
        except OSError as exc:
            raise SecretScanTechnicalError("SCAN_ROOT_RESOLVE_FAILED", ".") from exc
        findings: list[SecretFinding] = []
        scanned_file_count = 0
        skipped_file_count = 0

        def handle_walk_error(exc: OSError) -> None:
            failed_path = Path(exc.filename) if exc.filename else scan_root
            try:
                relative_path = failed_path.relative_to(scan_root).as_posix()
            except ValueError:
                relative_path = "."
            raise SecretScanTechnicalError("DIRECTORY_READ_FAILED", relative_path) from exc

        for directory, directory_names, file_names in os.walk(
            scan_root, topdown=True, onerror=handle_walk_error, followlinks=False
        ):
            directory_path = Path(directory)
            included_directories: list[str] = []
            for name in sorted(directory_names):
                path = directory_path / name
                if name in self._policy.excluded_directories or path.is_symlink():
                    continue
                included_directories.append(name)
            directory_names[:] = included_directories

            for name in sorted(file_names):
                path = directory_path / name
                relative_path = path.relative_to(scan_root).as_posix()
                if path.is_symlink():
                    skipped_file_count += 1
                    continue
                try:
                    file_stat = path.stat()
                except OSError as exc:
                    raise SecretScanTechnicalError("FILE_STAT_FAILED", relative_path) from exc
                if not stat.S_ISREG(file_stat.st_mode):
                    skipped_file_count += 1
                    continue
                if file_stat.st_size > self._policy.max_file_size_bytes:
                    skipped_file_count += 1
                    continue

                content = self._read_candidate(path, relative_path)
                if content is None:
                    skipped_file_count += 1
                    continue
                scanned_file_count += 1
                findings.extend(self._inspect_text(relative_path, content))

        return SecretScanReport(
            policy_version=self._policy.version,
            scanned_file_count=scanned_file_count,
            skipped_file_count=skipped_file_count,
            findings=tuple(sorted(findings)),
        )

    @staticmethod
    def _read_candidate(path: Path, relative_path: str) -> str | None:
        try:
            content = path.read_bytes()
        except OSError as exc:
            raise SecretScanTechnicalError("FILE_READ_FAILED", relative_path) from exc
        if b"\x00" in content:
            return None
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError:
            return None

    @staticmethod
    def _inspect_text(relative_path: str, content: str) -> list[SecretFinding]:
        findings: list[SecretFinding] = []
        for line_number, line in enumerate(content.splitlines(), start=1):
            for rule_code, pattern in (
                ("PRIVATE_KEY_MATERIAL", _PRIVATE_KEY_PATTERN),
                ("CLOUD_ACCESS_KEY_ID", _CLOUD_ACCESS_KEY_PATTERN),
                ("SOURCE_CONTROL_TOKEN", _GITHUB_TOKEN_PATTERN),
            ):
                for match in pattern.finditer(line):
                    findings.append(
                        SecretFinding(
                            relative_path=relative_path,
                            line_number=line_number,
                            column_number=match.start() + 1,
                            rule_code=rule_code,
                        )
                    )
            for match in _ASSIGNMENT_PATTERN.finditer(line):
                if _is_safe_literal(match.group("value")):
                    continue
                findings.append(
                    SecretFinding(
                        relative_path=relative_path,
                        line_number=line_number,
                        column_number=match.start() + 1,
                        rule_code="HARDCODED_SECRET_ASSIGNMENT",
                    )
                )
        return findings

    @staticmethod
    def _validate_policy(policy: SecretScanPolicy) -> None:
        if not policy.version.strip():
            raise SecretScanValidationError("POLICY_VERSION_REQUIRED")
        if policy.max_file_size_bytes <= 0:
            raise SecretScanValidationError("MAX_FILE_SIZE_INVALID")
        if not policy.excluded_directories or any(
            not name or "/" in name or "\\" in name for name in policy.excluded_directories
        ):
            raise SecretScanValidationError("EXCLUDED_DIRECTORY_INVALID")


def _is_safe_literal(value: str) -> bool:
    normalized = value.strip().lower()
    return normalized in _SAFE_LITERAL_VALUES or normalized.startswith(_SAFE_LITERAL_PREFIXES)
