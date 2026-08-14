#!/usr/bin/env python3
"""scripts/compute_pagerank.py

Kişiselleştirilmiş PageRank ile kod grafiği üzerinde alaka sıralaması.

Seed tanımlayıcılara yüksek ağırlık vererek, grafikle ilişkili kod bloklarını
sıralar. Token bütçesine göre sonuçları kırpılır.

Bağımlılık: networkx (yüklü değilse açık hata mesajı verir).

Kullanım:
    python3 scripts/compute_pagerank.py --seeds "node_id1,node_id2"
                                         [--graph graphify-out/graph.json]
                                         [--budget 4000]
                                         [--alpha 0.85]
                                         [--top 20]

Çıktı:
    JSON dizisi: [{node_id, score, source_file, source_location, label,
                    community_name}, ...]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _load_graph(graph_path: Path) -> dict[str, Any]:
    """graph.json'u yükler."""
    if not graph_path.is_file():
        print(f"Grafik dosyası bulunamadı: {graph_path}", file=sys.stderr)
        sys.exit(1)
    with open(graph_path, encoding="utf-8") as f:
        return json.load(f)


def _build_networkx_graph(
    data: dict[str, Any],
) -> tuple[Any, dict[str, dict[str, Any]]]:
    """graph.json verisinden networkx DiGraph ve düğüm haritası oluşturur."""
    try:
        import networkx as nx
    except ImportError:
        print(
            "HATA: networkx yüklü değil.\n"
            "Kurulum: pip install networkx\n"
            "Bu script personalized PageRank için networkx gerektirir.",
            file=sys.stderr,
        )
        sys.exit(1)

    G = nx.DiGraph()
    node_map: dict[str, dict[str, Any]] = {}

    for node in data.get("nodes", []):
        nid = node.get("id", "")
        if not nid:
            continue
        G.add_node(nid)
        node_map[nid] = node

    for link in data.get("links", []):
        src = link.get("source", "")
        tgt = link.get("target", "")
        if not src or not tgt:
            continue
        weight = float(link.get("weight", 1.0))
        if G.has_edge(src, tgt):
            # Mevcut kenarın ağırlığını artır (çoklu kenarları birleştir).
            G[src][tgt]["weight"] += weight
        else:
            G.add_edge(src, tgt, weight=weight)

    return G, node_map


def _resolve_seeds(
    seed_str: str,
    node_map: dict[str, dict[str, Any]],
) -> dict[str, float]:
    """Seed dizgesini düğüm kimliği -> ağırlık haritasına dönüştürür.

    Tam eşleşme önceliklidir; eşleşmeyen seed'ler için prefix/contains
    araması yapılır.
    """
    seeds: dict[str, float] = {}
    seed_tokens = [s.strip() for s in seed_str.split(",") if s.strip()]

    for token in seed_tokens:
        # Tam eşleşme.
        if token in node_map:
            seeds[token] = 10.0
            continue

        # Prefix veya içerik eşleşmesi.
        matched = False
        for nid in node_map:
            if token.lower() in nid.lower():
                seeds[nid] = 5.0
                matched = True

        # Hiç eşleşme yoksa seed'i yine de ekle (düşük ağırlıkla).
        if not matched:
            seeds[token] = 1.0

    return seeds


def _estimate_bytes(node_data: dict[str, Any]) -> int:
    """Bir düğümün prompt'a eklendiğinde kaplayacağı baytı tahmin eder."""
    label = node_data.get("label", "")
    source_file = node_data.get("source_file", "")
    # Her düğüm için yaklaşık: dosya yolu + konum + label + boşluk.
    return len(source_file) + len(label) + 60


def compute_pagerank(
    graph_path: Path,
    seeds: str,
    budget: int = 4000,
    alpha: float = 0.85,
    top: int = 20,
) -> list[dict[str, Any]]:
    """Kişiselleştirilmiş PageRank hesaplar ve sonuçları döndürür."""
    data = _load_graph(graph_path)
    G, node_map = _build_networkx_graph(data)

    if len(G.nodes) == 0:
        return []

    seed_weights = _resolve_seeds(seeds, node_map)

    if not seed_weights:
        return []

    # networkx personalization: tüm düğümlere ağırlık, seed'lere yüksek ağırlık.
    personalization: dict[str, float] = {}
    for nid in G.nodes:
        personalization[nid] = 0.1  # Arka plan ağırlığı.
    for nid, weight in seed_weights.items():
        if nid in personalization:
            personalization[nid] = weight

    try:
        import networkx as nx

        scores = nx.pagerank(G, alpha=alpha, personalization=personalization, max_iter=200)
    except Exception as exc:
        print(f"PageRank hesaplama hatası: {exc}", file=sys.stderr)
        return []

    # Seed düğümleri sonuçlara dahil etme (onlar zaten biliniyor).
    ranked = [
        (nid, score)
        for nid, score in sorted(scores.items(), key=lambda x: -x[1])
        if nid not in seed_weights
    ]

    # Bütçe ve top sınırlarıyla kırp.
    results: list[dict[str, Any]] = []
    used_bytes = 0
    for nid, score in ranked[: top * 3]:  # Fazla aday al, bütçeyle kırp.
        if used_bytes >= budget:
            break
        node_data = node_map.get(nid, {})
        entry = {
            "node_id": nid,
            "score": round(score, 6),
            "source_file": node_data.get("source_file", ""),
            "source_location": node_data.get("source_location", ""),
            "label": node_data.get("label", ""),
            "community_name": node_data.get("community_name", ""),
        }
        results.append(entry)
        used_bytes += _estimate_bytes(node_data)
        if len(results) >= top:
            break

    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Kişiselleştirilmiş PageRank ile kod grafiği sıralaması."
    )
    parser.add_argument(
        "--seeds",
        required=True,
        help="Seed düğüm kimlikleri (virgülle ayrılmış).",
    )
    parser.add_argument(
        "--graph",
        default="graphify-out/graph.json",
        help="Grafik dosyası yolu (varsayılan: graphify-out/graph.json).",
    )
    parser.add_argument(
        "--budget",
        type=int,
        default=4000,
        help="Maksimum bayt bütçesi (varsayılan: 4000).",
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=0.85,
        help="Damping faktörü (varsayılan: 0.85).",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=20,
        help="Maksimum sonuç sayısı (varsayılan: 20).",
    )
    args = parser.parse_args()

    results = compute_pagerank(
        graph_path=Path(args.graph),
        seeds=args.seeds,
        budget=args.budget,
        alpha=args.alpha,
        top=args.top,
    )

    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
