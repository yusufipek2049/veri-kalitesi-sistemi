#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# scripts/check_quality.sh — Unified quality gate for veri-kalitesi-sistemi.
#
# Usage:
#   ./scripts/check_quality.sh              # blocking checks only
#   ./scripts/check_quality.sh --all        # blocking + advisory
#   ./scripts/check_quality.sh --advisory   # advisory only
#
# Blocking checks (exit non-zero on failure):
#   1. ruff check (E, F)
#   2. ruff format --check
#   3. pytest -q
#   4. mypy src
#   5. frontend: npm run typecheck
#   6. frontend: npm test
#   7. frontend: npm run build
#
# Advisory checks (always exit 0; findings reported to stdout):
#   A. ruff extended rules, including structural complexity
#   B. complexipy cognitive complexity
#   C. vulture src/ --min-confidence 80
#   D. custom Semgrep anti-bloat rules
#   E. frontend: eslint readability rules
#   F. frontend: knip (dead-code)
#   G. jscpd (copy-paste)
#   H. graphify update for candidate call-site verification
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# ── Helpers ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
pass() { echo -e "  ${GREEN}✓${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; }
warn() { echo -e "  ${YELLOW}△${NC} $1"; }
section() { echo -e "\n━━━ $1 ━━━"; }

BLOCKING_EXIT=0
ADVISORY_MODE=false
BLOCKING_MODE=true

# Parse args
for arg in "$@"; do
  case $arg in
    --all)       ADVISORY_MODE=true ;;
    --advisory)  ADVISORY_MODE=true; BLOCKING_MODE=false ;;
  esac
done

# ── Load nvm for Node tools ──────────────────────────────────────────────────
export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
[ -s "$NVM_DIR/nvm.sh" ] && source "$NVM_DIR/nvm.sh"
nvm use 20 --silent 2>/dev/null || true

# ══════════════════════════════════════════════════════════════════════════════
# BLOCKING CHECKS
# ══════════════════════════════════════════════════════════════════════════════
if $BLOCKING_MODE; then
  section "Blocking checks"

  # 1. ruff check
  if ruff check . --quiet 2>/dev/null; then
    pass "ruff check (E, F)"
  else
    fail "ruff check"; BLOCKING_EXIT=1
  fi

  # 2. ruff format
  if ruff format --check . --quiet 2>/dev/null; then
    pass "ruff format"
  else
    fail "ruff format"; BLOCKING_EXIT=1
  fi

  # 3. pytest
  if pytest -q --no-header --tb=line 2>&1 | tail -1; then
    pass "pytest"
  else
    fail "pytest"; BLOCKING_EXIT=1
  fi

  # 4. mypy
  if mypy src 2>&1 | tail -1; then
    pass "mypy src"
  else
    fail "mypy src"; BLOCKING_EXIT=1
  fi

  # 5-7. Frontend
  section "Frontend checks"
  cd frontend

  if npm run typecheck --silent 2>/dev/null; then
    pass "tsc typecheck"
  else
    fail "tsc typecheck"; BLOCKING_EXIT=1
  fi

  if npm test 2>&1 | tail -1; then
    pass "vitest"
  else
    fail "vitest"; BLOCKING_EXIT=1
  fi

  if npm run build --silent 2>/dev/null; then
    pass "vite build"
  else
    fail "vite build"; BLOCKING_EXIT=1
  fi

  cd "$ROOT"
fi

# ══════════════════════════════════════════════════════════════════════════════
# ADVISORY CHECKS
# ══════════════════════════════════════════════════════════════════════════════
if $ADVISORY_MODE; then
  section "Advisory checks (non-blocking)"
  READABILITY_REPORT_DIR="$ROOT/build/readability"
  mkdir -p "$READABILITY_REPORT_DIR"

  # A. Extended ruff rules
  warn "ruff extended rules (including structural complexity):"
  ruff check --select W,I,B,UP,SIM,TCH,A,PTH,RUF,C90,PLR0911,PLR0912,PLR0913,PLR0915 . 2>&1 | tail -1 || true

  # B. Cognitive complexity (human-readability oriented)
  warn "complexipy (cognitive complexity > 15):"
  if command -v complexipy >/dev/null 2>&1; then
    complexipy src --failed --suggest-refactors --ignore-complexity \
      --output-format json --output "$READABILITY_REPORT_DIR/complexipy.json" >/dev/null 2>&1 || true
    python3 -c 'import json,sys; print("  {} functions above threshold".format(len(json.load(open(sys.argv[1], encoding="utf-8")))))' \
      "$READABILITY_REPORT_DIR/complexipy.json"
    echo "  Report: build/readability/complexipy.json"
  else
    warn "complexipy is not installed; install the project's test extras"
  fi

  # C. Vulture
  warn "vulture (dead code, min-confidence=80):"
  vulture src/ --min-confidence 80 2>&1 | wc -l | xargs -I{} echo "  {} findings" || true

  # D. Semgrep — rule tests (blocking) + scan (advisory)
  if [ -d "tools/semgrep/rules" ]; then
    if semgrep test tools/semgrep 2>&1 | grep -q "All tests passed"; then
      pass "semgrep rule tests"
    else
      fail "semgrep rule tests"; BLOCKING_EXIT=1
    fi
    warn "semgrep scan (anti-bloat rules; very-low-precision class heuristic excluded):"
    semgrep scan --config tools/semgrep/rules/ src/ frontend/src/ \
      --exclude-rule tools.semgrep.rules.single-method-adapter.single-method-adapter \
      --json --metrics=off > "$READABILITY_REPORT_DIR/semgrep.json" 2>/dev/null || true
    python3 -c 'import json,sys; print("  {} findings".format(len(json.load(open(sys.argv[1], encoding="utf-8")).get("results", []))))' \
      "$READABILITY_REPORT_DIR/semgrep.json"
    echo "  Report: build/readability/semgrep.json"
  else
    warn "semgrep: no custom rules in tools/semgrep/rules/ — skipping"
  fi

  # E. ESLint
  cd frontend
  warn "eslint (advisory):"
  npx eslint src/ --format json > "$READABILITY_REPORT_DIR/eslint.json" 2>/dev/null || true
  python3 -c 'import json,sys; data=json.load(open(sys.argv[1], encoding="utf-8")); messages=[m for f in data for m in f.get("messages", [])]; readability={"complexity", "max-depth", "max-lines-per-function"}; print("  {} readability findings ({} total)".format(sum(m.get("ruleId") in readability for m in messages), len(messages)))' \
    "$READABILITY_REPORT_DIR/eslint.json"
  echo "  Report: build/readability/eslint.json"

  # F. Knip
  warn "knip (dead-code):"
  npx knip 2>&1 | tail -5 || true

  # G. jscpd
  cd "$ROOT"
  warn "jscpd (copy-paste):"
  npx jscpd --config .jscpd.json src/ frontend/src/ 2>&1 | \
    sed -n 's/.*\(Found [0-9][0-9]* clones\.\).*/  \1/p' | tail -1 || true

  # H. Graphify
  warn "graphify update:"
  if GRAPHIFY_OUT=build/graphify graphify update . 2>&1 | tail -3; then
    pass "graphify call graph refreshed"
    echo "  Review a candidate: ./scripts/review_readability_candidate.sh <symbol>"
  else
    warn "graphify update failed"
  fi
fi

exit $BLOCKING_EXIT
