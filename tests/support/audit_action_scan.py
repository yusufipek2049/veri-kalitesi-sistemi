"""Kaynak agacinda gercekten emit edilen audit aksiyonlarini AST ile toplar.

Registry butunluk testleri bu tarayiciyi kullanir. Tarama iki adimlidir:

1. `AuditEventInput(action="...")` cagrilarindaki literal aksiyonlar.
2. Govdesinde `AuditEventInput` kuran ve `action` parametresi alan yardimci
   fonksiyonlarin cagri yerlerindeki literal aksiyonlar.

Ikinci adim sayesinde `_build_audit_event(..., action="X", ...)` gibi dolayli
emit yerleri de yakalanir; buna karsilik audit ile ilgisi olmayan `action=`
alanlari (ornegin `IssueHistoryEntry.action`) kapsam disinda kalir.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

AUDIT_EVENT_FACTORY = "AuditEventInput"


@dataclass(frozen=True)
class AuditActionEmit:
    """Tek bir emit yeri: aksiyon kodu + kaynak konumu."""

    action: str
    module: str
    line: int


def source_files(source_root: Path) -> list[Path]:
    return sorted(path for path in source_root.rglob("*.py") if "__pycache__" not in path.parts)


def scan_emitted_actions(source_root: Path) -> tuple[AuditActionEmit, ...]:
    """`source_root` altindaki tum emit yerlerini dondurur."""

    trees = {path: ast.parse(path.read_text(encoding="utf-8")) for path in source_files(source_root)}
    emits: list[AuditActionEmit] = []
    for path, tree in trees.items():
        module = _module_name(path, source_root)
        # Yardimci adlari modul yerel cozulur; `_audit` gibi ayni ad farkli
        # modullerde farkli imzalarla tanimlanabiliyor.
        helpers = _audit_helper_action_positions(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            callee = _callee_name(node)
            if callee == AUDIT_EVENT_FACTORY:
                actions = _keyword_actions(node)
            elif callee in helpers:
                actions = _keyword_actions(node) or _positional_actions(node, helpers[callee])
            else:
                continue
            emits.extend(AuditActionEmit(action, module, node.lineno) for action in actions)
    return tuple(emits)


def emitted_action_codes(source_root: Path) -> frozenset[str]:
    return frozenset(emit.action for emit in scan_emitted_actions(source_root))


def _audit_helper_action_positions(tree: ast.Module) -> dict[str, int | None]:
    """`action` parametresi alip govdesinde AuditEventInput kuran fonksiyonlar.

    Deger, `action` parametresinin pozisyonel indeksidir (`self` haric);
    parametre yalnizca anahtar kelimeyle veriliyorsa `None` olur.
    """

    candidates: list[tuple[ast.FunctionDef | ast.AsyncFunctionDef, int | None]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        positional = [
            argument.arg
            for argument in (*node.args.posonlyargs, *node.args.args)
            if argument.arg != "self"
        ]
        keyword_only = {argument.arg for argument in node.args.kwonlyargs}
        if "action" not in positional and "action" not in keyword_only:
            continue
        candidates.append((node, positional.index("action") if "action" in positional else None))

    # Dolayli zincirleri de yakalamak icin sabit noktaya kadar yayilir:
    # `_transition(action=...)` -> `_build_audit_event(action=...)` -> AuditEventInput.
    helpers: dict[str, int | None] = {}
    known = {AUDIT_EVENT_FACTORY}
    while True:
        discovered = {
            node.name: index
            for node, index in candidates
            if node.name not in helpers
            and any(
                isinstance(inner, ast.Call) and _callee_name(inner) in known
                for inner in ast.walk(node)
            )
        }
        if not discovered:
            return helpers
        helpers.update(discovered)
        known.update(discovered)


def _positional_actions(node: ast.Call, index: int | None) -> tuple[str, ...]:
    if index is None or index >= len(node.args):
        return ()
    return _literal_actions(node.args[index])


def _keyword_actions(node: ast.Call) -> tuple[str, ...]:
    for keyword in node.keywords:
        if keyword.arg == "action":
            return _literal_actions(keyword.value)
    return ()


def _literal_actions(node: ast.expr) -> tuple[str, ...]:
    """Literal aksiyonu cozer; kosullu ifadelerde her iki dal da sayilir."""

    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return (node.value,)
    if isinstance(node, ast.IfExp):
        return (*_literal_actions(node.body), *_literal_actions(node.orelse))
    return ()


def _callee_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _module_name(path: Path, source_root: Path) -> str:
    return ".".join(path.relative_to(source_root).with_suffix("").parts)
