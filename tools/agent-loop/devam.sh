#!/usr/bin/env bash
# tools/agent-loop/devam.sh
#
# `devam` CLI dispatcher. Kalıcı ve izlenen giriş noktasıdır.
# ~/.local/bin/devam bu dosyayı exec eder.
#
# Komutlar:
#   devam                    Canonical dokümanlardan sıradaki görevi seç ve pipeline'ı çalıştır.
#   devam "görev"            Verilen görevi yeni kontratla doğrudan çalıştır.
#   devam "insan kararı"     WAITING_HUMAN aşamasındaki kararı kaydet ve devam et.
#   devam durum              Iteration, stage, status, görev ve son hatayı göster (ajan başlatmaz).
#   devam log                Mevcut aşamanın son log dosyalarını göster (ajan başlatmaz).
#
# Not: "görev" ve "insan kararı" bağlamdan (state) ayırt edilir; ikisi de serbest
# metindir. `durum` ve `log` rezerve alt komutlardır.
set -uo pipefail

TOOLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${AGENT_LOOP_ENV_FILE:-$HOME/.config/veri-kalitesi/agent-loop.env}"

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
fi

ROOT="${AGENT_LOOP_TARGET:-$(cd "$TOOLS_DIR/../.." && pwd)}"
H="$ROOT/.agent-handoff"
STATE="$H/state/SESSION.json"
LOGS="$H/logs"

show_status() {
  if [[ ! -f "$STATE" ]]; then
    echo "Henüz çalıştırılmamış (state yok). Başlatmak için: devam"
    return 0
  fi
  local iteration stage status repair err task title mode
  iteration="$(jq -r '.iteration' "$STATE")"
  stage="$(jq -r '.stage' "$STATE")"
  status="$(jq -r '.status' "$STATE")"
  repair="$(jq -r '.repair_round' "$STATE")"
  err="$(jq -r '.last_error // "-"' "$STATE")"
  task="-"; title="-"; mode="-"
  if [[ -f "$H/CURRENT_TASK.json" ]]; then
    task="$(jq -r '.task.id // "-"' "$H/CURRENT_TASK.json")"
    title="$(jq -r '.task.title // "-"' "$H/CURRENT_TASK.json")"
    mode="$(jq -r '.task.selection_mode // "-"' "$H/CURRENT_TASK.json")"
  fi
  # Rol dağıtımı canonical kaynaktan okunur (agents.yaml); burada tekrar tanımlanmaz.
  local roles_file="$ROOT/.agent/config/agents.yaml"
  # shellcheck source=tools/agent-loop/roles.sh
  source "$TOOLS_DIR/roles.sh"
  local impl tester reviewer lifecycle handoff
  if roles_load "$roles_file" >/dev/null 2>&1; then
    impl="$(role_agent implementer 2>/dev/null || echo unresolved)"
    tester="$(role_agent tester 2>/dev/null || echo unresolved)"
    reviewer="$(role_agent reviewer 2>/dev/null || echo unresolved)"
  else
    impl="legacy:${AGENT_BACKEND:-codex}"; tester="$impl"; reviewer="$impl"
  fi
  # shellcheck source=tools/agent-loop/ledger.sh
  source "$TOOLS_DIR/ledger.sh"
  lifecycle="$(lifecycle_state "$stage" "$status" "$repair" "")"
  handoff="$(jq -r '.handoff_file // "-"' "$STATE")"

  printf 'Lifecycle : %s\n' "$lifecycle"
  printf 'Iteration : %s\n' "$iteration"
  printf 'Stage     : %s\n' "$stage"
  printf 'Status    : %s\n' "$status"
  printf 'Repair    : %s\n' "$repair"
  printf 'Task      : %s (%s)\n' "$task" "$mode"
  printf 'Title     : %s\n' "$title"
  printf 'Roller    : implementer=%s tester=%s reviewer=%s\n' "$impl" "$tester" "$reviewer"
  [[ "$handoff" != "-" && "$handoff" != "null" ]] && printf 'Handoff   : %s\n' "$handoff"
  printf 'Last error: %s\n' "$err"
}

show_log() {
  if [[ ! -f "$STATE" ]]; then
    echo "Henüz log yok." >&2
    return 0
  fi
  local iteration stage role
  iteration="$(jq -r '.iteration' "$STATE")"
  stage="$(jq -r '.stage' "$STATE")"
  case "$stage" in
    IMPLEMENTER) role="implementer" ;;
    REVIEWER)    role="reviewer" ;;
    PLANNER)     role="planner" ;;
    TESTER)      role="" ;;
    *)           role="" ;;
  esac
  echo "== Mevcut aşama: $stage (iteration $iteration) =="
  if [[ "$stage" == "TESTER" || "$stage" == "COMPLETED" ]]; then
    for f in "$LOGS/unit-tests-i${iteration}.log" "$LOGS/integration-tests-i${iteration}.log"; do
      [[ -f "$f" ]] && { echo "--- $f (son 40 satır) ---"; tail -n 40 "$f"; }
    done
  fi
  if [[ -n "$role" ]]; then
    local latest
    latest="$(ls -1t "$LOGS/${role}-i${iteration}-"*.stderr.log 2>/dev/null | head -n 1 || true)"
    [[ -n "$latest" ]] && { echo "--- $latest (son 40 satır) ---"; tail -n 40 "$latest"; }
  fi
  echo "Tüm loglar: $LOGS"
}

case "${1:-}" in
  durum|status)
    show_status
    ;;
  log|logs)
    show_log
    ;;
  *)
    exec "$TOOLS_DIR/controller.sh" continue "$@"
    ;;
esac
