#!/usr/bin/env python3
"""Validate active Markdown structure without external dependencies."""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import unquote

LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
ID_RE = re.compile(r"\b(?:BR-\d{3}|FR-\d{3}|UC-\d{3}|RULE-\d{3}|AC-\d{3}|TS-\d{3}|NFR-[A-Z]+-\d{3}|ADR-\d{3}|OPEN-BNK-\d{3}|OPEN-\d{3}|DQ-(?:SCR|CAP)-\d{3}|API-\d{3}|FE-(?:DEC|DS)-\d{3}|PG-MIG-\d{3}|UI-WRITE-\d{3})\b")
EXCLUDED_DIRS = {'.git', '.venv', 'node_modules', '__pycache__', '.pytest_cache'}
ARCHIVE_PREFIXES = ('archive/', 'docs/archive/', 'docs/technical/')
DUPLICATE_SCAN_EXCLUDED_PREFIXES = ('08-Uyum-Kanitlari/', '09-Iterasyonlar/')


def all_markdown(root: Path):
    for path in root.rglob('*.md'):
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        yield path


def active_markdown(root: Path):
    for path in root.rglob('*.md'):
        rel = path.relative_to(root).as_posix()
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        if rel.startswith(ARCHIVE_PREFIXES):
            continue
        yield path


def resolve_link(source: Path, target: str) -> Path | None:
    target = target.strip()
    if not target or target.startswith(('#', 'http://', 'https://', 'mailto:')):
        return None
    target = target.split('#', 1)[0].split('?', 1)[0]
    if not target:
        return None
    return (source.parent / unquote(target)).resolve()



def canonical_id_definitions(root: Path) -> dict[str, list[str]]:
    """Collect definitions only from the declared canonical registries."""
    definitions: dict[str, list[str]] = defaultdict(list)

    def scan_table(path: Path, pattern: re.Pattern[str]) -> None:
        rel = path.relative_to(root).as_posix()
        for line_no, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
            match = pattern.match(line)
            if match:
                for identifier in match.groups():
                    if identifier:
                        definitions[identifier].append(f'{rel}:{line_no}')

    scan_table(root / '01-SRS/03-Is-Gereksinimleri.md', re.compile(r'^\|\s*`?(BR-\d{3})`?\s*\|'))
    scan_table(root / '01-SRS/06-Is-Kurallari.md', re.compile(r'^\|\s*`?(RULE-\d{3})`?\s*\|'))
    scan_table(root / '01-SRS/10-Kabul-Kriterleri.md', re.compile(r'^\|\s*`?(AC-\d{3})`?\s*\|\s*`?(TS-\d{3})`?\s*\|'))
    scan_table(root / '01-SRS/04-Fonksiyonel-Gereksinimler/04.06-Skorlama.md', re.compile(r'^\|\s*`?(DQ-SCR-\d{3})`?\s*\|'))

    for path in (root / '01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler').rglob('*.md'):
        scan_table(path, re.compile(r'^\|\s*`?(NFR-[A-Z]+-\d{3})`?\s*\|'))

    for path in (root / '01-SRS/04-Fonksiyonel-Gereksinimler').rglob('*.md'):
        rel = path.relative_to(root).as_posix()
        for line_no, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
            match = re.match(r'^#{1,6}\s+(FR-\d{3})\b', line)
            if match:
                definitions[match.group(1)].append(f'{rel}:{line_no}')

    for path in (root / '01-SRS/05-Kullanim-Senaryolari').glob('UC-*.md'):
        rel = path.relative_to(root).as_posix()
        for line_no, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
            match = re.match(r'^#\s+(UC-\d{3})\b', line)
            if match:
                definitions[match.group(1)].append(f'{rel}:{line_no}')

    adr_path = root / '02-Mimari/Mimari-Kararlar.md'
    adr_rel = adr_path.relative_to(root).as_posix()
    adr_headings: set[str] = set()
    lines = adr_path.read_text(encoding='utf-8').splitlines()
    for line_no, line in enumerate(lines, 1):
        match = re.match(r'^##\s+(ADR-\d{3})\b', line)
        if match:
            adr_headings.add(match.group(1))
            definitions[match.group(1)].append(f'{adr_rel}:{line_no}')
    for line_no, line in enumerate(lines, 1):
        match = re.match(r'^\|\s*(ADR-\d{3})\s*\|', line)
        if match and match.group(1) not in adr_headings:
            definitions[match.group(1)].append(f'{adr_rel}:{line_no}')

    decision_paths = list((root / '00-Proje-Hafizasi/Karar-Kayitlari').glob('*.md'))
    decision_paths.append(root / '00-Proje-Hafizasi/Acik-Konular.md')
    decision_pattern = re.compile(r'^\|\s*`?((?:OPEN(?:-BNK)?|DQ-CAP|API|FE-(?:DEC|DS)|PG-MIG|UI-WRITE)-\d{3})`?\s*\|')
    for path in decision_paths:
        scan_table(path, decision_pattern)

    return definitions

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('root', nargs='?', default='.')
    parser.add_argument('--include-archives', action='store_true',
                        help='also validate file links in archive/snapshot Markdown')
    args = parser.parse_args()
    root = Path(args.root).resolve()
    errors: list[str] = []
    warnings: list[str] = []
    active_files = list(active_markdown(root))
    link_files = list(all_markdown(root)) if args.include_archives else active_files
    checked_links = 0

    for path in link_files:
        text = path.read_text(encoding='utf-8')
        rel = path.relative_to(root).as_posix()
        for raw in LINK_RE.findall(text):
            resolved = resolve_link(path, raw)
            if resolved is None:
                continue
            checked_links += 1
            if not resolved.exists():
                errors.append(f'{rel}: broken link -> {raw}')

    for path in active_files:
        text = path.read_text(encoding='utf-8')
        rel = path.relative_to(root).as_posix()
        h1s = H1_RE.findall(text)
        if len(h1s) != 1:
            errors.append(f'{rel}: expected exactly one H1, found {len(h1s)}')

    definitions = canonical_id_definitions(root)
    duplicate_definitions = {key: value for key, value in definitions.items() if len(value) > 1}
    for identifier, locations in sorted(duplicate_definitions.items()):
        errors.append(f'duplicate canonical ID definition: {identifier} -> {", ".join(locations)}')

    references: set[str] = set()
    for path in active_files:
        text = path.read_text(encoding='utf-8')
        references.update(ID_RE.findall(text))
    undefined = sorted(references - set(definitions))
    for identifier in undefined:
        errors.append(f'undefined explicit ID reference: {identifier}')

    required = ['README.md', 'AGENTS.md', 'DOCUMENTATION_INDEX.md',
                'DOCUMENTATION_AUDIT.md', '00-Proje-Hafizasi/Mevcut-Durum.md',
                '00-Proje-Hafizasi/Acik-Konular.md']
    for rel in required:
        if not (root / rel).exists():
            errors.append(f'missing required document: {rel}')

    # Report, but do not fail, when the same exact long paragraph remains repeated.
    paragraphs: Counter[str] = Counter()
    for path in active_files:
        rel = path.relative_to(root).as_posix()
        if rel.startswith(DUPLICATE_SCAN_EXCLUDED_PREFIXES):
            continue
        text = path.read_text(encoding='utf-8')
        for para in re.split(r'\n\s*\n', text):
            norm = re.sub(r'\s+', ' ', para.strip())
            if len(norm) >= 180 and not norm.startswith(('#', '|', '```')):
                paragraphs[norm] += 1
    duplicates = sum(count - 1 for count in paragraphs.values() if count > 1)
    if duplicates:
        warnings.append(f'{duplicates} repeated long paragraph occurrence(s) remain')

    print(f'Active Markdown files: {len(active_files)}')
    if args.include_archives:
        print(f'All Markdown files linked-scanned: {len(link_files)}')
    print(f'Local links checked: {checked_links}')
    print(f'Canonical IDs defined: {len(definitions)}')
    print(f'Explicit ID references resolved: {len(references)}')
    for warning in warnings:
        print(f'WARNING: {warning}')
    for error in errors:
        print(f'ERROR: {error}')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
