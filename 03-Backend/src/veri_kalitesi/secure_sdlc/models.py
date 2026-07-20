"""Data-minimum models for local repository secret scanning."""

from __future__ import annotations

from dataclasses import dataclass, field


DEFAULT_EXCLUDED_DIRECTORIES = frozenset(
    {
        ".cache",
        ".git",
        ".mypy_cache",
        ".nox",
        ".npm",
        ".pnpm-store",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        ".yarn",
        "__pycache__",
        "artifacts",
        "build",
        "dist",
        "node_modules",
        "site-packages",
        "vendor",
        "venv",
    }
)


@dataclass(frozen=True)
class SecretScanPolicy:
    version: str = "28A-v1"
    max_file_size_bytes: int = 1_048_576
    excluded_directories: frozenset[str] = field(
        default_factory=lambda: DEFAULT_EXCLUDED_DIRECTORIES
    )


@dataclass(frozen=True, order=True)
class SecretFinding:
    relative_path: str
    line_number: int
    column_number: int
    rule_code: str


@dataclass(frozen=True)
class SecretScanReport:
    policy_version: str
    scanned_file_count: int
    skipped_file_count: int
    findings: tuple[SecretFinding, ...]

    @property
    def passed(self) -> bool:
        return not self.findings


@dataclass(frozen=True, order=True)
class DeclaredDependency:
    canonical_name: str
    version: str
    environment_marker: str | None = None


@dataclass(frozen=True)
class PythonProjectInventory:
    name: str
    version: str
    requires_python: str
    dependencies: tuple[DeclaredDependency, ...]
