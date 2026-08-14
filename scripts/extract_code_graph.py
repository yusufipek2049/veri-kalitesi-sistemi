#!/usr/bin/env python3
"""scripts/extract_code_graph.py

tree-sitter benzeri AST çıkarma — Python stdlib ``ast`` modülü ile tanım ve
referans düğümlerini çıkarır, graphify-out/graph.json'u günceller.

Kullanım:
    python3 scripts/extract_code_graph.py [--graph graphify-out/graph.json]
                                           [--src src/] [--tests tests/]

Çıktı:
    graph.json dosyasına _origin="ast" düğümleri ve kenarları ekler/günceller.
    Mevcut düğümler/kenarlar korunur; çakışan AST düğümleri üzerine yazılır.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Any


def _sanitize_id(path: str) -> str:
    """Dosya yolu ve tanımlayıcıyı güvenli bir düğüm kimliğine dönüştürür."""
    return re.sub(r"[^a-zA-Z0-9_]", "_", path)


def _node_id(source_file: str, name: str) -> str:
    """Benzersiz düğüm kimliği üret: <dosya>_<tanım>."""
    file_part = Path(source_file).stem
    parent_dir = Path(source_file).parent
    prefix = _sanitize_id(str(parent_dir)).rstrip("_") + "_" if str(parent_dir) != "." else ""
    return _sanitize_id(f"{prefix}{file_part}_{name}")


def _walk_py_files(directories: list[Path]) -> list[Path]:
    """Verilen dizinler altındaki tüm .py dosyalarını döndürür."""
    files: list[Path] = []
    for d in directories:
        if not d.is_dir():
            continue
        files.extend(sorted(d.rglob("*.py")))
    return files


class _GraphBuilder(ast.NodeVisitor):
    """Tek bir Python dosyası için AST'den düğüm ve kenar çıkarır."""

    def __init__(self, source_file: str) -> None:
        self.source_file = source_file
        self.nodes: list[dict[str, Any]] = []
        self.edges: list[dict[str, Any]] = []
        self._scope_stack: list[str] = []
        self._seen_node_ids: set[str] = set()

    def _current_scope(self) -> str:
        return ".".join(self._scope_stack) if self._scope_stack else ""

    def _add_node(self, name: str, lineno: int, node_type: str) -> str:
        nid = _node_id(self.source_file, name)
        if nid in self._seen_node_ids:
            return nid
        self._seen_node_ids.add(nid)
        self.nodes.append(
            {
                "id": nid,
                "label": f"{name}()",
                "file_type": "code",
                "source_file": self.source_file,
                "source_location": f"L{lineno}",
                "_origin": "ast",
                "node_type": node_type,
            }
        )
        return nid

    def _add_edge(self, source: str, target: str, relation: str) -> None:
        self.edges.append(
            {
                "source": source,
                "target": target,
                "relation": relation,
                "confidence": "EXTRACTED",
                "confidence_score": 1.0,
                "weight": 1.0,
                "_origin": "ast",
                "source_file": self.source_file,
            }
        )

    # --- ziyaretçiler ---

    def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        scope = self._current_scope()
        qualified = f"{scope}.{node.name}" if scope else node.name
        nid = self._add_node(qualified, node.lineno, "function")

        # Scope içine gir: içerideki çağrıları bu fonksiyona bağla.
        self._scope_stack.append(node.name)
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                call_name = _call_name(child)
                if call_name:
                    target_id = _node_id(self.source_file, call_name)
                    self._add_edge(nid, target_id, "calls")
        self._scope_stack.pop()
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        scope = self._current_scope()
        qualified = f"{scope}.{node.name}" if scope else node.name
        nid = self._add_node(qualified, node.lineno, "class")

        # Kalıtım kenarları.
        for base in node.bases:
            base_name = _attr_name(base)
            if base_name:
                target_id = _node_id(self.source_file, base_name)
                self._add_edge(nid, target_id, "inherits")

        self._scope_stack.append(node.name)
        self.generic_visit(node)
        self._scope_stack.pop()

    def visit_Import(self, node: ast.Import) -> None:
        file_module_id = _node_id(self.source_file, "__module__")
        if file_module_id not in self._seen_node_ids:
            self._add_node("__module__", 1, "module")
        for alias in node.names:
            target_id = _sanitize_id(f"module_{alias.name}")
            self._add_edge(file_module_id, target_id, "imports")

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if not node.module:
            return
        file_module_id = _node_id(self.source_file, "__module__")
        if file_module_id not in self._seen_node_ids:
            self._add_node("__module__", 1, "module")
        target_id = _sanitize_id(f"module_{node.module}")
        self._add_edge(file_module_id, target_id, "imports")


def _call_name(node: ast.Call) -> str | None:
    """ast.Call düğümünden çağrılan adı çıkarır."""
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _attr_name(node: ast.expr) -> str | None:
    """ast.expr düğümünden nitelik/adını çıkarır."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _extract_file(filepath: Path) -> tuple[list[dict], list[dict]]:
    """Tek dosya için AST çıkarma yapar."""
    try:
        source = filepath.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError:
        return [], []

    builder = _GraphBuilder(str(filepath))
    builder.visit(tree)
    return builder.nodes, builder.edges


def _load_graph(graph_path: Path) -> dict[str, Any]:
    """Mevcut graph.json'u yükler; yoksa boş bir iskelet döndürür."""
    if graph_path.is_file():
        with open(graph_path, encoding="utf-8") as f:
            return json.load(f)
    return {
        "directed": False,
        "multigraph": False,
        "graph": {},
        "nodes": [],
        "links": [],
    }


def _merge_graph(
    existing: dict[str, Any],
    new_nodes: list[dict],
    new_edges: list[dict],
) -> dict[str, Any]:
    """AST düğümlerini/kenarlarını mevcut grafikle birleştirir.

    Aynı id'ye sahip AST düğümleri güncellenir; diğerleri korunur.
    """
    # Mevcut düğümleri id -> index olarak haritala.
    node_index: dict[str, int] = {}
    for i, node in enumerate(existing.get("nodes", [])):
        node_index[node.get("id", "")] = i

    for node in new_nodes:
        nid = node["id"]
        if nid in node_index:
            idx = node_index[nid]
            # AST kökenli düğümleri güncelle; diğer kökenlileri koru.
            if existing["nodes"][idx].get("_origin") == "ast":
                existing["nodes"][idx] = node
        else:
            node_index[nid] = len(existing["nodes"])
            existing["nodes"].append(node)

    # Kenarları birleştir: aynı (source, target, relation) AST kenarı güncellenir.
    existing_links: list[dict] = existing.get("links", [])
    edge_key_set: set[tuple[str, str, str]] = set()
    for link in existing_links:
        if link.get("_origin") == "ast":
            edge_key_set.add((link["source"], link["target"], link["relation"]))

    for edge in new_edges:
        key = (edge["source"], edge["target"], edge["relation"])
        if key in edge_key_set:
            # Mevcut AST kenarını güncelle.
            for link in existing_links:
                if (
                    link.get("_origin") == "ast"
                    and link["source"] == edge["source"]
                    and link["target"] == edge["target"]
                    and link["relation"] == edge["relation"]
                ):
                    link.update(edge)
                    break
        else:
            edge_key_set.add(key)
            existing_links.append(edge)

    existing["links"] = existing_links
    return existing


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Python AST'den kod grafiği çıkarır ve graph.json'u günceller."
    )
    parser.add_argument(
        "--graph",
        default="graphify-out/graph.json",
        help="Hedef grafik dosyası (varsayılan: graphify-out/graph.json)",
    )
    parser.add_argument(
        "--src",
        default="src/",
        help="Kaynak dizini (varsayılan: src/)",
    )
    parser.add_argument(
        "--tests",
        default="tests/",
        help="Test dizini (varsayılan: tests/)",
    )
    args = parser.parse_args()

    root = Path(".")
    graph_path = root / args.graph
    directories = [root / args.src, root / args.tests]

    py_files = _walk_py_files(directories)
    if not py_files:
        print("Hiçbir .py dosyası bulunamadı.", file=sys.stderr)
        return 1

    all_nodes: list[dict] = []
    all_edges: list[dict] = []
    for fpath in py_files:
        nodes, edges = _extract_file(fpath)
        all_nodes.extend(nodes)
        all_edges.extend(edges)

    existing = _load_graph(graph_path)
    merged = _merge_graph(existing, all_nodes, all_edges)

    # Atomik yazım: geçici dosya + rename.
    tmp_path = graph_path.with_suffix(".json.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    tmp_path.rename(graph_path)

    print(
        f"extract_code_graph: {len(py_files)} dosya, "
        f"{len(all_nodes)} düğüm, {len(all_edges)} kenar çıkarıldı."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
