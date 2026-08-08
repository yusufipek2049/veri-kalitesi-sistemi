#!/usr/bin/env bash
# Inspect a readability/dead-code candidate against the repository call graph.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GRAPH_PATH="${GRAPHIFY_GRAPH:-$ROOT/build/graphify/graph.json}"

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <symbol>" >&2
  exit 2
fi

if [ ! -f "$GRAPH_PATH" ]; then
  echo "Graph not found at $GRAPH_PATH; run ./scripts/check_quality.sh --advisory first." >&2
  exit 1
fi

SYMBOL="$1"

echo "Candidate explanation"
graphify explain "$SYMBOL" --graph "$GRAPH_PATH"

echo
echo "Callers and affected nodes (depth 2)"
graphify affected "$SYMBOL" --relation calls --depth 2 --graph "$GRAPH_PATH"
