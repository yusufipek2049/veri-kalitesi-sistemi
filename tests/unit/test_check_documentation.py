"""Tests for scripts/check_documentation.py.

Covers default vs legacy scope, link resolution, H1 validation,
required-file checks, and canonical-ID gating.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_documentation.py"


def _load_module():
    """Load check_documentation.py as a module via importlib."""
    spec = importlib.util.spec_from_file_location("check_documentation", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _run(root: Path, *extra_args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(root), *extra_args],
        capture_output=True,
        text=True,
    )


# ---------------------------------------------------------------------------
# resolve_link
# ---------------------------------------------------------------------------


class TestResolveLink:
    """Unit tests for the resolve_link helper."""

    def test_relative_link(self, tmp_path: Path) -> None:
        mod = _load_module()
        source = tmp_path / "docs" / "page.md"
        _write(source, "[link](other.md)")

        resolved = mod.resolve_link(source, "other.md")
        assert resolved is not None
        assert resolved == (tmp_path / "docs" / "other.md").resolve()

    def test_anchor_only_returns_none(self, tmp_path: Path) -> None:
        mod = _load_module()
        source = tmp_path / "page.md"
        _write(source, "[link](#section)")

        assert mod.resolve_link(source, "#section") is None

    def test_http_link_returns_none(self, tmp_path: Path) -> None:
        mod = _load_module()
        source = tmp_path / "page.md"
        _write(source, "[link](https://example.com)")

        assert mod.resolve_link(source, "https://example.com") is None

    def test_mailto_returns_none(self, tmp_path: Path) -> None:
        mod = _load_module()
        source = tmp_path / "page.md"
        _write(source, "[mail](mailto:a@b.com)")

        assert mod.resolve_link(source, "mailto:a@b.com") is None

    def test_link_with_anchor_strips_fragment(self, tmp_path: Path) -> None:
        mod = _load_module()
        source = tmp_path / "page.md"
        _write(source, "[link](other.md#section)")

        resolved = mod.resolve_link(source, "other.md#section")
        assert resolved is not None
        assert resolved.name == "other.md"

    def test_empty_link_returns_none(self, tmp_path: Path) -> None:
        mod = _load_module()
        source = tmp_path / "page.md"
        _write(source, "[link]()")

        assert mod.resolve_link(source, "") is None

    def test_parent_relative_link(self, tmp_path: Path) -> None:
        mod = _load_module()
        source = tmp_path / "documentation" / "sub" / "page.md"
        _write(source, "[back](../../README.md)")

        resolved = mod.resolve_link(source, "../../README.md")
        assert resolved is not None
        assert resolved == (tmp_path / "README.md").resolve()


# ---------------------------------------------------------------------------
# default_markdown vs legacy_markdown scope
# ---------------------------------------------------------------------------


class TestMarkdownScope:
    """Verify that default and legacy scopes select the correct files."""

    def test_default_scope_includes_readme_and_documentation(self, tmp_path: Path) -> None:
        mod = _load_module()
        _write(tmp_path / "README.md", "# Root")
        _write(tmp_path / "documentation" / "guide.md", "# Guide")
        _write(tmp_path / "documentation" / "sub" / "deep.md", "# Deep")
        _write(tmp_path / "docs" / "legacy.md", "# Legacy")
        _write(tmp_path / "ARCHITECTURE.md", "# Arch")

        files = list(mod.default_markdown(tmp_path))
        rel_names = {p.relative_to(tmp_path).as_posix() for p in files}
        assert "README.md" in rel_names
        assert "documentation/guide.md" in rel_names
        assert "documentation/sub/deep.md" in rel_names
        # Legacy locations must NOT appear in default scope
        assert "docs/legacy.md" not in rel_names
        assert "ARCHITECTURE.md" not in rel_names

    def test_default_scope_excludes_excluded_dirs(self, tmp_path: Path) -> None:
        mod = _load_module()
        _write(tmp_path / "README.md", "# Root")
        _write(tmp_path / "documentation" / "ok.md", "# Ok")
        _write(tmp_path / "documentation" / "__pycache__" / "cached.md", "# Cached")

        files = list(mod.default_markdown(tmp_path))
        rel_names = {p.relative_to(tmp_path).as_posix() for p in files}
        assert "documentation/__pycache__/cached.md" not in rel_names

    def test_default_scope_handles_missing_documentation_dir(self, tmp_path: Path) -> None:
        mod = _load_module()
        _write(tmp_path / "README.md", "# Root")

        files = list(mod.default_markdown(tmp_path))
        assert len(files) == 1
        assert files[0].name == "README.md"

    def test_default_scope_handles_missing_readme(self, tmp_path: Path) -> None:
        mod = _load_module()
        _write(tmp_path / "documentation" / "guide.md", "# Guide")

        files = list(mod.default_markdown(tmp_path))
        assert len(files) == 1
        assert files[0].name == "guide.md"

    def test_legacy_scope_includes_all_non_excluded(self, tmp_path: Path) -> None:
        mod = _load_module()
        _write(tmp_path / "README.md", "# Root")
        _write(tmp_path / "documentation" / "guide.md", "# Guide")
        _write(tmp_path / "docs" / "legacy.md", "# Legacy")
        _write(tmp_path / ".git" / "internal.md", "# Internal")

        files = list(mod.legacy_markdown(tmp_path))
        rel_names = {p.relative_to(tmp_path).as_posix() for p in files}
        assert "README.md" in rel_names
        assert "documentation/guide.md" in rel_names
        assert "docs/legacy.md" in rel_names
        assert ".git/internal.md" not in rel_names

    def test_legacy_scope_excludes_archives(self, tmp_path: Path) -> None:
        mod = _load_module()
        _write(tmp_path / "README.md", "# Root")
        _write(tmp_path / "archive" / "old.md", "# Old")
        _write(tmp_path / "docs" / "archive" / "snap.md", "# Snap")

        files = list(mod.legacy_markdown(tmp_path))
        rel_names = {p.relative_to(tmp_path).as_posix() for p in files}
        assert "archive/old.md" not in rel_names
        assert "docs/archive/snap.md" not in rel_names


# ---------------------------------------------------------------------------
# Integration: main() via subprocess
# ---------------------------------------------------------------------------


class TestMainDefaultMode:
    """End-to-end tests for the default (non-legacy) mode."""

    def test_clean_documentation_tree_passes(self, tmp_path: Path) -> None:
        _write(tmp_path / "README.md", "# Project\n\n[guide](documentation/guide.md)\n")
        _write(tmp_path / "documentation" / "README.md", "# Documentation Index\n")
        _write(tmp_path / "documentation" / "guide.md", "# Guide\n\n[back](../README.md)\n")

        result = _run(tmp_path)
        assert result.returncode == 0, result.stdout + result.stderr
        assert "Scope: default" in result.stdout

    def test_missing_readme_is_error(self, tmp_path: Path) -> None:
        _write(tmp_path / "documentation" / "README.md", "# Doc Index\n")

        result = _run(tmp_path)
        assert result.returncode == 1
        assert "missing required document: README.md" in result.stdout

    def test_missing_documentation_readme_is_error(self, tmp_path: Path) -> None:
        _write(tmp_path / "README.md", "# Root\n")

        result = _run(tmp_path)
        assert result.returncode == 1
        assert "missing required document: documentation/README.md" in result.stdout

    def test_broken_link_is_error(self, tmp_path: Path) -> None:
        _write(tmp_path / "README.md", "# Root\n\n[broken](documentation/missing.md)\n")
        _write(tmp_path / "documentation" / "README.md", "# Doc Index\n")

        result = _run(tmp_path)
        assert result.returncode == 1
        assert "broken link" in result.stdout

    def test_multiple_h1_is_error(self, tmp_path: Path) -> None:
        _write(tmp_path / "README.md", "# First\n\n# Second\n")
        _write(tmp_path / "documentation" / "README.md", "# Doc Index\n")

        result = _run(tmp_path)
        assert result.returncode == 1
        assert "expected exactly one H1" in result.stdout

    def test_zero_h1_is_error(self, tmp_path: Path) -> None:
        _write(tmp_path / "README.md", "No heading here\n")
        _write(tmp_path / "documentation" / "README.md", "# Doc Index\n")

        result = _run(tmp_path)
        assert result.returncode == 1
        assert "expected exactly one H1" in result.stdout

    def test_http_links_are_not_checked(self, tmp_path: Path) -> None:
        _write(
            tmp_path / "README.md",
            "# Root\n\n[external](https://example.com)\n",
        )
        _write(tmp_path / "documentation" / "README.md", "# Doc Index\n")

        result = _run(tmp_path)
        assert result.returncode == 0

    def test_anchor_links_are_not_checked(self, tmp_path: Path) -> None:
        _write(
            tmp_path / "README.md",
            "# Root\n\n[section](#section)\n\n## Section\n",
        )
        _write(tmp_path / "documentation" / "README.md", "# Doc Index\n")

        result = _run(tmp_path)
        assert result.returncode == 0

    def test_valid_relative_links_pass(self, tmp_path: Path) -> None:
        _write(
            tmp_path / "README.md",
            "# Root\n\n[doc](documentation/README.md)\n",
        )
        _write(tmp_path / "documentation" / "README.md", "# Index\n\n[back](../README.md)\n")

        result = _run(tmp_path)
        assert result.returncode == 0
        assert "broken link" not in result.stdout


class TestMainLegacyMode:
    """End-to-end tests for the --legacy mode."""

    def test_legacy_scans_docs_directory(self, tmp_path: Path) -> None:
        _write(tmp_path / "README.md", "# Root\n")
        _write(tmp_path / "documentation" / "README.md", "# Doc Index\n")
        _write(tmp_path / "docs" / "legacy.md", "# Legacy\n")

        result = _run(tmp_path, "--legacy")
        assert "Scope: legacy" in result.stdout

    def test_legacy_requires_legacy_files(self, tmp_path: Path) -> None:
        _write(tmp_path / "README.md", "# Root\n")
        _write(tmp_path / "documentation" / "README.md", "# Doc Index\n")

        result = _run(tmp_path, "--legacy")
        assert result.returncode == 1
        assert "missing required document: DOCUMENTATION_INDEX.md" in result.stdout

    def test_default_mode_does_not_require_legacy_files(self, tmp_path: Path) -> None:
        _write(tmp_path / "README.md", "# Root\n")
        _write(tmp_path / "documentation" / "README.md", "# Doc Index\n")

        result = _run(tmp_path)
        assert result.returncode == 0
        assert "DOCUMENTATION_INDEX" not in result.stdout


class TestDuplicateParagraphWarning:
    """Duplicate long paragraph detection."""

    def test_duplicate_paragraph_produces_warning(self, tmp_path: Path) -> None:
        long_para = (
            "This is a sufficiently long paragraph that should trigger the "
            "duplicate detection mechanism when it appears more than once "
            "in the documentation tree across multiple files for testing."
        )
        _write(tmp_path / "README.md", f"# Root\n\nIntro line.\n\n{long_para}\n")
        _write(tmp_path / "documentation" / "README.md", f"# Doc Index\n\nOther.\n\n{long_para}\n")

        result = _run(tmp_path)
        assert "repeated long paragraph" in result.stdout


class TestCanonicalIdLegacyOnly:
    """Canonical ID checks should only run in --legacy mode."""

    def test_default_mode_does_not_check_ids(self, tmp_path: Path) -> None:
        _write(tmp_path / "README.md", "# Root\n\nReferences BR-001 and FR-001.\n")
        _write(tmp_path / "documentation" / "README.md", "# Doc Index\n")

        result = _run(tmp_path)
        assert result.returncode == 0
        assert "undefined explicit ID reference" not in result.stdout

    def test_legacy_mode_reports_canonical_ids(self, tmp_path: Path) -> None:
        _write(tmp_path / "README.md", "# Root\n\nReferences BR-001.\n")
        _write(tmp_path / "documentation" / "README.md", "# Doc Index\n")
        _write(tmp_path / "DOCUMENTATION_INDEX.md", "# Index\n")
        _write(tmp_path / "DOCUMENTATION_AUDIT.md", "# Audit\n")
        _write(tmp_path / "docs" / "memory" / "Mevcut-Durum.md", "# Mevcut\n")
        _write(tmp_path / "docs" / "memory" / "Acik-Konular.md", "# Acik\n")

        result = _run(tmp_path, "--legacy")
        assert "Canonical IDs defined" in result.stdout
