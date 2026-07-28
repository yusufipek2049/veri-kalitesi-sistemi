#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
H="$ROOT/.agent-handoff"
PROMPTS="$H/prompts"
SCHEMAS="$H/schemas"
LOGS="$H/logs"
mkdir -p "$LOGS"

need() { command -v "$1" >/dev/null 2>&1 || { echo "Missing command: $1" >&2; exit 10; }; }
need git; need jq; need sha256sum; need claude; need codex
[[ -f "$H/REQUEST.md" ]] || { echo "Missing $H/REQUEST.md" >&2; exit 11; }
[[ -z "$(git status --porcelain=v1 --untracked-files=all -- . ':(exclude).agent-handoff' ':(exclude).agent-handoff/**')" ]] || {
  echo "Worktree already has production changes. Use a clean task worktree or review them manually." >&2
  exit 12
}

BRANCH="$(git branch --show-current)"
BASE_REF="${BASE_REF:-HEAD}"

make_change_artifacts() {
  git status --short --untracked-files=all | grep -v '^?? \.agent-handoff/' > "$H/GIT_CHANGE_SUMMARY.txt" || true
  {
    git diff --binary -- . ':(exclude).agent-handoff/**'
    while IFS= read -r -d '' f; do
      [[ "$f" == .agent-handoff/* ]] && continue
      git diff --no-index --binary /dev/null "$f" || true
    done < <(git ls-files --others --exclude-standard -z)
  } > "$H/GIT_DIFF.patch"
}

check_contract() {
  jq -e '
    .schema_version == "1.0" and
    .contract_status == "READY" and
    .safety.no_commit == true and
    .safety.no_push == true and
    .safety.no_merge == true and
    .safety.no_pull_request == true and
    .gates.retry_policy.max_automatic_fix_rounds == 1 and
    (.context.active_iterations | length) <= 7
  ' "$H/CURRENT_TASK.json" >/dev/null
}

run_architect() {
  echo "[1/4] Claude architect"
  local schema prompt raw
  schema="$(jq -c . "$SCHEMAS/CURRENT_TASK.schema.json")"
  prompt="$(cat "$PROMPTS/claude-architect.md")

Repository root: $ROOT
Worktree: $ROOT
Branch: $BRANCH
Base ref: $BASE_REF
User request file: $H/REQUEST.md"
  local args=(claude -p --permission-mode plan --allowedTools "Read,Glob,Grep" --max-turns 24 --output-format json --json-schema "$schema")
  [[ -n "${CLAUDE_ARCHITECT_MODEL:-}" ]] && args+=(--model "$CLAUDE_ARCHITECT_MODEL")
  raw="$LOGS/claude-architect.raw.json"
  "${args[@]}" "$prompt" > "$raw"
  jq -e '.structured_output' "$raw" > "$H/CURRENT_TASK.json"
  check_contract || { echo "Architect contract is not READY or violates hard gates." >&2; exit 20; }
}

run_implementer() {
  local round="$1"
  echo "[2/4] Codex implementer ($round)"
  local input="$LOGS/codex-implementer-$round.input.md"
  {
    cat "$PROMPTS/codex-implementer.md"
    printf '\nRepository root: `%s`\n' "$ROOT"
    printf 'Task contract: `%s`\n' "$H/CURRENT_TASK.json"
    if [[ "$round" != "initial" ]]; then
      printf 'Apply only the remediations in: `%s`\n' "$H/ARCHITECT_REVIEW.md"
    fi
  } > "$input"
  local args=(codex --ask-for-approval never --sandbox workspace-write -C "$ROOT")
  [[ -n "${CODEX_IMPLEMENTER_MODEL:-}" ]] && args+=(-m "$CODEX_IMPLEMENTER_MODEL")
  args+=(exec -o "$H/CODEX_RESULT.md" -)
  "${args[@]}" < "$input"
  grep -qx 'STATUS: SUCCESS' <(head -n 1 "$H/CODEX_RESULT.md") || {
    echo "Implementer gate failed." >&2; exit 21;
  }
  cp "$H/CODEX_RESULT.md" "$LOGS/CODEX_RESULT-$round.md"
}

run_tester() {
  local round="$1"
  echo "[3/4] Independent Codex tester ($round)"
  make_change_artifacts
  sha256sum "$H/GIT_DIFF.patch" | awk '{print $1}' > "$H/DIFF_BEFORE_TESTER.sha256"
  local input="$LOGS/codex-tester-$round.input.md"
  {
    cat "$PROMPTS/codex-tester.md"
    printf '\nRepository root: `%s`\n' "$ROOT"
  } > "$input"
  local args=(codex --ask-for-approval never --sandbox workspace-write -C "$ROOT")
  [[ -n "${CODEX_TESTER_MODEL:-}" ]] && args+=(-m "$CODEX_TESTER_MODEL")
  args+=(exec -o "$H/TEST_REPORT.md" -)
  "${args[@]}" < "$input"
  make_change_artifacts
  sha256sum "$H/GIT_DIFF.patch" | awk '{print $1}' > "$H/DIFF_AFTER_TESTER.sha256"
  if ! cmp -s "$H/DIFF_BEFORE_TESTER.sha256" "$H/DIFF_AFTER_TESTER.sha256"; then
    {
      echo 'STATUS: FAIL'
      echo
      echo '## Independent Findings'
      echo 'Tester changed the production diff; mutation gate failed.'
      echo
      tail -n +2 "$H/TEST_REPORT.md" || true
    } > "$H/TEST_REPORT.mutated.md"
    mv "$H/TEST_REPORT.mutated.md" "$H/TEST_REPORT.md"
  fi
  cp "$H/TEST_REPORT.md" "$LOGS/TEST_REPORT-$round.md"
}

run_reviewer() {
  local round="$1"
  echo "[4/4] Claude architecture reviewer ($round)"
  make_change_artifacts
  local prompt
  prompt="$(cat "$PROMPTS/claude-reviewer.md")

Repository root: $ROOT
Read the six input files listed above from this worktree."
  local args=(claude -p --permission-mode plan --allowedTools "Read,Glob,Grep" --max-turns 20)
  [[ -n "${CLAUDE_REVIEWER_MODEL:-}" ]] && args+=(--model "$CLAUDE_REVIEWER_MODEL")
  "${args[@]}" "$prompt" > "$H/ARCHITECT_REVIEW.md"
  cp "$H/ARCHITECT_REVIEW.md" "$LOGS/ARCHITECT_REVIEW-$round.md"

  local test_status decision
  test_status="$(sed -n '1s/^STATUS: //p' "$H/TEST_REPORT.md")"
  decision="$(sed -n '1s/^DECISION: //p' "$H/ARCHITECT_REVIEW.md")"
  if [[ "$decision" == "APPROVED" && "$test_status" != "PASS" ]]; then
    echo "Invalid approval: tester status is $test_status." >&2
    exit 30
  fi
  printf '%s\n' "$decision"
}

if [[ "${REUSE_CURRENT_TASK:-0}" == "1" && -f "$H/CURRENT_TASK.json" ]]; then
  echo "[1/4] Existing Claude architect contract reused"
  check_contract || {
    echo "Existing architect contract violates hard gates." >&2
    exit 20
  }
else
  run_architect
fi

run_implementer initial
run_tester initial
DECISION="$(run_reviewer initial | tail -n 1)"

case "$DECISION" in
  APPROVED)
    [[ "$(sed -n '1s/^STATUS: //p' "$H/TEST_REPORT.md")" == "PASS" ]] || exit 31
    echo "PIPELINE_STATUS: APPROVED"
    ;;
  BLOCKED)
    echo "PIPELINE_STATUS: BLOCKED — human decision required"
    exit 40
    ;;
  CHANGES_REQUIRED)
    echo "One automatic correction round starts."
    run_implementer fix-1
    run_tester fix-1
    DECISION="$(run_reviewer fix-1 | tail -n 1)"
    if [[ "$DECISION" == "APPROVED" && "$(sed -n '1s/^STATUS: //p' "$H/TEST_REPORT.md")" == "PASS" ]]; then
      echo "PIPELINE_STATUS: APPROVED_AFTER_ONE_FIX"
    else
      echo "PIPELINE_STATUS: STOPPED_AFTER_ONE_FIX ($DECISION)"
      exit 41
    fi
    ;;
  *)
    echo "Unknown reviewer decision: $DECISION" >&2
    exit 42
    ;;
esac

echo "No commit, push, merge or PR was performed."
