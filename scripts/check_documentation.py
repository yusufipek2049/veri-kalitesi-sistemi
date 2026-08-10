#!/usr/bin/env python3
"""Validate Markdown documentation structure and links.

Default scope: README.md + documentation/**
With --legacy: also includes docs/** and other root-level documents.

The canonical-ID registry check (SRS/ADR/UC/FR references) is only active
in --legacy mode, since the new documentation/ tree does not use those IDs.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import unquote

LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
FENCED_BLOCK_RE = re.compile(r"^```.*$", re.MULTILINE)
ID_RE = re.compile(
    r"\b(?:BR-\d{3}|FR-\d{3}|UC-\d{3}|RULE-\d{3}|AC-\d{3}|TS-\d{3}|NFR-[A-Z]+-\d{3}|ADR-\d{3}|OPEN-BNK-\d{3}|OPEN-\d{3}|DQ-(?:SCR|CAP)-\d{3}|API-\d{3}|FE-(?:DEC|DS)-\d{3}|PG-MIG-\d{3}|UI-WRITE-\d{3})\b"
)
EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".agent",
    ".agents",
    ".agent-handoff",
    ".codex",
    ".qoder",
    ".mypy_cache",
    ".ruff_cache",
    "tools",
}
# Root-level agent/tool instruction files are not validated.
ROOT_TOOL_FILES = {"AGENTS.md", "CLAUDE.md", "CODEX-KULLANIM.md"}
ARCHIVE_PREFIXES = ("archive/", "docs/archive/", "docs/technical/")
DUPLICATE_SCAN_EXCLUDED_PREFIXES = ("docs/compliance/", "docs/iterations/")


def _is_excluded(path: Path) -> bool:
    return any(part in EXCLUDED_DIRS for part in path.parts)


def _strip_fenced_blocks(text: str) -> str:
    """Remove fenced code blocks (``` ... ```) so their contents are not scanned."""
    lines = text.splitlines()
    result: list[str] = []
    inside = False
    for line in lines:
        if line.lstrip().startswith("```"):
            inside = not inside
            result.append("")  # placeholder to preserve line numbers
            continue
        if inside:
            result.append("")
        else:
            result.append(line)
    return "\n".join(result)


def _is_root_tool(path: Path, root: Path) -> bool:
    return path.parent == root and path.name in ROOT_TOOL_FILES


def default_markdown(root: Path):
    """Yield Markdown files in the default scope: README.md + documentation/**."""
    readme = root / "README.md"
    if readme.exists():
        yield readme
    doc_dir = root / "documentation"
    if doc_dir.is_dir():
        for path in sorted(doc_dir.rglob("*.md")):
            if not _is_excluded(path):
                yield path


def legacy_markdown(root: Path):
    """Yield all non-excluded Markdown files (legacy scope)."""
    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(root).as_posix()
        if _is_excluded(path):
            continue
        if _is_root_tool(path, root):
            continue
        if rel.startswith(ARCHIVE_PREFIXES):
            continue
        yield path


def resolve_link(source: Path, target: str) -> Path | None:
    target = target.strip()
    if not target or target.startswith(("#", "http://", "https://", "mailto:")):
        return None
    target = target.split("#", 1)[0].split("?", 1)[0]
    if not target:
        return None
    return (source.parent / unquote(target)).resolve()


def canonical_id_definitions(root: Path) -> dict[str, list[str]]:
    """Collect definitions only from the declared canonical registries.

    Only used in --legacy mode.
    """
    definitions: dict[str, list[str]] = defaultdict(list)

    def scan_table(path: Path, pattern: re.Pattern[str]) -> None:
        if not path.exists():
            return
        rel = path.relative_to(root).as_posix()
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            match = pattern.match(line)
            if match:
                for identifier in match.groups():
                    if identifier:
                        definitions[identifier].append(f"{rel}:{line_no}")

    scan_table(root / "docs/srs/03-Is-Gereksinimleri.md", re.compile(r"^\|\s*`?(BR-\d{3})`?\s*\|"))
    scan_table(root / "docs/srs/06-Is-Kurallari.md", re.compile(r"^\|\s*`?(RULE-\d{3})`?\s*\|"))
    scan_table(
        root / "docs/srs/10-Kabul-Kriterleri.md",
        re.compile(r"^\|\s*`?(AC-\d{3})`?\s*\|\s*`?(TS-\d{3})`?\s*\|"),
    )
    scan_table(
        root / "docs/srs/04-Fonksiyonel-Gereksinimler/04.06-Skorlama.md",
        re.compile(r"^\|\s*`?(DQ-SCR-\d{3})`?\s*\|"),
    )

    nfr_dir = root / "docs/srs/09-Fonksiyonel-Olmayan-Gereksinimler"
    if nfr_dir.is_dir():
        for path in nfr_dir.rglob("*.md"):
            scan_table(path, re.compile(r"^\|\s*`?(NFR-[A-Z]+-\d{3})`?\s*\|"))

    func_dir = root / "docs/srs/04-Fonksiyonel-Gereksinimler"
    if func_dir.is_dir():
        for path in func_dir.rglob("*.md"):
            rel = path.relative_to(root).as_posix()
            for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                match = re.match(r"^#{1,6}\s+(FR-\d{3})\b", line)
                if match:
                    definitions[match.group(1)].append(f"{rel}:{line_no}")

    uc_dir = root / "docs/srs/05-Kullanim-Senaryolari"
    if uc_dir.is_dir():
        for path in uc_dir.glob("UC-*.md"):
            rel = path.relative_to(root).as_posix()
            for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                match = re.match(r"^#\s+(UC-\d{3})\b", line)
                if match:
                    definitions[match.group(1)].append(f"{rel}:{line_no}")

    adr_path = root / "docs/architecture/Mimari-Kararlar.md"
    if adr_path.exists():
        adr_rel = adr_path.relative_to(root).as_posix()
        adr_headings: set[str] = set()
        lines = adr_path.read_text(encoding="utf-8").splitlines()
        for line_no, line in enumerate(lines, 1):
            match = re.match(r"^##\s+(ADR-\d{3})\b", line)
            if match:
                adr_headings.add(match.group(1))
                definitions[match.group(1)].append(f"{adr_rel}:{line_no}")
        for line_no, line in enumerate(lines, 1):
            match = re.match(r"^\|\s*(ADR-\d{3})\s*\|", line)
            if match and match.group(1) not in adr_headings:
                definitions[match.group(1)].append(f"{adr_rel}:{line_no}")

    decision_dir = root / "docs/memory/Karar-Kayitlari"
    decision_paths: list[Path] = []
    if decision_dir.is_dir():
        decision_paths.extend(decision_dir.glob("*.md"))
    open_issues = root / "docs/memory/Acik-Konular.md"
    if open_issues.exists():
        decision_paths.append(open_issues)
    decision_pattern = re.compile(
        r"^\|\s*`?((?:OPEN(?:-BNK)?|DQ-CAP|API|FE-(?:DEC|DS)|PG-MIG|UI-WRITE)-\d{3})`?\s*\|"
    )
    for path in decision_paths:
        scan_table(path, decision_pattern)

    return definitions


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Markdown documentation structure and links."
    )
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument(
        "--legacy",
        action="store_true",
        help="also validate docs/** and other legacy Markdown files",
    )
    parser.add_argument(
        "--include-archives",
        action="store_true",
        help="also validate file links in archive/snapshot Markdown (imples --legacy)",
    )
    args = parser.parse_args()
    root = Path(args.root).resolve()
    legacy = args.legacy or args.include_archives
    errors: list[str] = []
    warnings: list[str] = []

    # Select file scope
    if legacy:
        scope_files = list(legacy_markdown(root))
    else:
        scope_files = list(default_markdown(root))

    # For link checking, optionally include all markdown
    if args.include_archives:
        link_files = list(legacy_markdown(root))
    else:
        link_files = scope_files

    checked_links = 0

    # --- Link validation ---
    for path in link_files:
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(root).as_posix()
        for raw in LINK_RE.findall(text):
            resolved = resolve_link(path, raw)
            if resolved is None:
                continue
            checked_links += 1
            if not resolved.exists():
                errors.append(f"{rel}: broken link -> {raw}")

    # --- H1 validation ---
    for path in scope_files:
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(root).as_posix()
        h1s = H1_RE.findall(_strip_fenced_blocks(text))
        if len(h1s) != 1:
            errors.append(f"{rel}: expected exactly one H1, found {len(h1s)}")

    # --- Canonical ID checks (legacy only) ---
    if legacy:
        definitions = canonical_id_definitions(root)
        duplicate_definitions = {key: value for key, value in definitions.items() if len(value) > 1}
        for identifier, locations in sorted(duplicate_definitions.items()):
            errors.append(
                f"duplicate canonical ID definition: {identifier} -> {', '.join(locations)}"
            )

        references: set[str] = set()
        for path in scope_files:
            text = path.read_text(encoding="utf-8")
            references.update(ID_RE.findall(text))
        undefined = sorted(references - set(definitions))
        for identifier in undefined:
            errors.append(f"undefined explicit ID reference: {identifier}")

    # --- Required files ---
    if legacy:
        required = [
            "README.md",
            "DOCUMENTATION_INDEX.md",
            "DOCUMENTATION_AUDIT.md",
            "docs/memory/Mevcut-Durum.md",
            "docs/memory/Acik-Konular.md",
        ]
    else:
        required = [
            "README.md",
            "documentation/README.md",
        ]
    for rel in required:
        if not (root / rel).exists():
            errors.append(f"missing required document: {rel}")

    # --- Duplicate paragraph detection ---
    paragraphs: Counter[str] = Counter()
    for path in scope_files:
        rel = path.relative_to(root).as_posix()
        if rel.startswith(DUPLICATE_SCAN_EXCLUDED_PREFIXES):
            continue
        text = path.read_text(encoding="utf-8")
        for para in re.split(r"\n\s*\n", text):
            norm = re.sub(r"\s+", " ", para.strip())
            if len(norm) >= 180 and not norm.startswith(("#", "|", "```")):
                paragraphs[norm] += 1
    duplicates = sum(count - 1 for count in paragraphs.values() if count > 1)
    if duplicates:
        warnings.append(f"{duplicates} repeated long paragraph occurrence(s) remain")

    # --- Report ---
    scope_label = "legacy (all)" if legacy else "default (README.md + documentation/**)"
    print(f"Scope: {scope_label}")
    print(f"Markdown files checked: {len(scope_files)}")
    print(f"Local links checked: {checked_links}")
    if legacy:
        print(f"Canonical IDs defined: {len(definitions)}")
        print(f"Explicit ID references resolved: {len(references)}")
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
