"""Production preflight sabitleri ile Alembic migration zinciri arasindaki sozlesme.

F-01: ``CURRENT_MIGRATION_HEAD`` migration 25'te takili kalmisti; migration 26
uygulanmis bir veritabaninda production composition baslamayi reddediyordu ve
tablo envanterinde ``issue_evidence_files`` yoktu. Bu testler iki sabiti
migration dosyalarindan turetilen gercege baglar.
"""

from __future__ import annotations

import ast
from pathlib import Path

from veri_kalitesi.api.composition import CURRENT_MIGRATION_HEAD, REQUIRED_TABLES

VERSIONS_DIR = Path(__file__).resolve().parents[2] / "alembic" / "versions"


def _migration_modules() -> list[tuple[Path, ast.Module]]:
    return [
        (path, ast.parse(path.read_text(encoding="utf-8")))
        for path in sorted(VERSIONS_DIR.glob("*.py"))
    ]


def _module_constant(tree: ast.Module, name: str) -> object:
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError(f"Migration module has no {name!r} constant.")


def _revision_chain() -> list[str]:
    down_by_revision = {
        _module_constant(tree, "revision"): _module_constant(tree, "down_revision")
        for _, tree in _migration_modules()
    }
    parents = {parent for parent in down_by_revision.values() if parent is not None}
    heads = sorted(set(down_by_revision) - parents)
    assert len(heads) == 1, f"Alembic zinciri tek head icermeli, bulunan: {heads}"
    chain: list[str] = []
    cursor: str | None = heads[0]
    while cursor is not None:
        chain.append(cursor)
        cursor = down_by_revision[cursor]
    chain.reverse()
    assert len(chain) == len(down_by_revision), "Migration zincirinde kopukluk var."
    return chain


def _tables_created_by_migrations() -> set[str]:
    """upgrade() ve yardimcilarinin olusturdugu tablolar; downgrade haric."""

    created: set[str] = set()
    for _, tree in _migration_modules():
        for function in tree.body:
            if not isinstance(function, ast.FunctionDef) or function.name == "downgrade":
                continue
            for node in ast.walk(function):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "create_table"
                    and node.args
                ):
                    created.add(ast.literal_eval(node.args[0]))
    return created


def test_current_migration_head_matches_alembic_head() -> None:
    assert CURRENT_MIGRATION_HEAD == _revision_chain()[-1]


def test_required_tables_match_migration_inventory() -> None:
    expected = _tables_created_by_migrations()
    assert REQUIRED_TABLES == expected, (
        f"Preflight envanterinde eksik: {sorted(expected - REQUIRED_TABLES)}; "
        f"fazla: {sorted(REQUIRED_TABLES - expected)}"
    )


def test_preflight_requires_latest_evidence_and_governance_tables() -> None:
    assert "issue_evidence_files" in REQUIRED_TABLES
    assert "governance_approval_requests" in REQUIRED_TABLES
