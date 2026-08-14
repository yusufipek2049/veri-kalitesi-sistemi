#!/usr/bin/env python3
"""Çalıştırılabilir API/worker köklerinden AST import erişilebilirliğini ölç."""

from __future__ import annotations

import ast
from collections import defaultdict, deque
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
PACKAGE_ROOT = SOURCE_ROOT / "veri_kalitesi"
ENTRYPOINTS = (
    "veri_kalitesi.api.app",
    "veri_kalitesi.api.composition",
    "veri_kalitesi.jobs.entrypoint",
)


def _module_name(path: Path) -> str:
    relative = path.relative_to(SOURCE_ROOT).with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _resolve_imports(module: str, path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    dependencies: set[str] = set()
    package_parts = module.split(".")[:-1] if path.name != "__init__.py" else module.split(".")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            dependencies.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base_parts = package_parts[: len(package_parts) - node.level + 1]
                if node.module:
                    base_parts.extend(node.module.split("."))
                base = ".".join(base_parts)
            else:
                base = node.module or ""
            if base:
                dependencies.add(base)
            for alias in node.names:
                candidate = f"{base}.{alias.name}" if base else alias.name
                dependencies.add(candidate)
    return dependencies


def main() -> int:
    paths = {_module_name(path): path for path in PACKAGE_ROOT.rglob("*.py")}
    graph = {module: _resolve_imports(module, path) for module, path in paths.items()}
    reachable: set[str] = set()
    queue = deque(ENTRYPOINTS)
    while queue:
        module = queue.popleft()
        if module in reachable or module not in paths:
            continue
        reachable.add(module)
        for dependency in graph[module]:
            candidate = dependency
            while candidate and candidate not in paths:
                candidate = candidate.rpartition(".")[0]
            if candidate and candidate not in reachable:
                queue.append(candidate)

    module_lines: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    total = 0
    reached = 0
    for module, path in paths.items():
        lines = len(path.read_text(encoding="utf-8").splitlines())
        top_level = module.split(".")[1] if "." in module else module
        module_lines[top_level][0] += lines
        total += lines
        if module in reachable:
            module_lines[top_level][1] += lines
            reached += lines
    unreachable = total - reached
    payload = {
        "entrypoints": ENTRYPOINTS,
        "total_lines": total,
        "reachable_lines": reached,
        "unreachable_lines": unreachable,
        "unreachable_percent": round(unreachable * 100 / total, 2),
        "modules": {
            name: {
                "total_lines": values[0],
                "reachable_lines": values[1],
                "reachable_percent": round(values[1] * 100 / values[0], 2),
            }
            for name, values in sorted(module_lines.items())
        },
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
