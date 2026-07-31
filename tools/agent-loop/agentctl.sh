#!/usr/bin/env bash
# tools/agent-loop/agentctl.sh
#
# Ajan orkestrasyonu için operatör CLI'ı. `devam` otomatik akıştır; `agentctl`
# ise durumu incelemek, görev/worktree/handoff üretmek ve elle müdahale etmek
# içindir. Ayrı bir framework kurmaz: aynı dosya tabanlı state'i kullanır.
#
# Kullanım: tools/agent-loop/agentctl.sh <komut> [seçenekler]
#           tools/agent-loop/agentctl.sh --help
set -euo pipefail

TOOLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${AGENT_LOOP_ENV_FILE:-$HOME/.config/veri-kalitesi/agent-loop.env}"
if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
fi
ROOT="${AGENT_LOOP_TARGET:-$(cd "$TOOLS_DIR/../.." && pwd)}"

DRY_RUN=0
QUIET=0

die() { echo "hata: $*" >&2; exit 1; }
info() { [[ "$QUIET" == "1" ]] || echo "$*"; }
run() {
  if [[ "$DRY_RUN" == "1" ]]; then
    printf '[dry-run] '; printf '%q ' "$@"; printf '\n'
    return 0
  fi
  "$@"
}

require_deps() {
  local missing=() d
  for d in git jq awk sed flock; do
    command -v "$d" >/dev/null 2>&1 || missing+=("$d")
  done
  (( ${#missing[@]} == 0 )) || die "eksik bağımlılık: ${missing[*]}"
}

load_lib() {
  # shellcheck source=tools/agent-loop/lib.sh
  source "$TOOLS_DIR/lib.sh"
  agentloop_init "$ROOT" "$TOOLS_DIR" \
    || die "rol yapılandırması geçersiz: $ROOT/.agent/config/agents.yaml"
}

usage() {
  cat <<'EOF'
agentctl — ajan orkestrasyonu operatör CLI'ı

Komutlar:
  status                     Rol dağıtımı, yaşam döngüsü durumu, aktif görev ve claim'ler.
  next-task                  Sıradaki görevi (deterministik seçim) ajan çalıştırmadan gösterir.
  create-task <id> <başlık>  Şablondan aktif görev dosyası oluşturur (elle görev açma).
  claim-task <id>            Görevi bu worktree adına claim eder.
  select-runner <rol>        Rolü karşılayacak ajanı ve varsa fallback nedenini yazdırır.
  create-worktree <kisa-ad>  Güvenli worktree + branch oluşturur (çakışma kontrollü).
  build-handoff [rol]        Mevcut kontrattan görev paketi üretir (varsayılan: implementer).
  record-tests <suite>       Testleri çalıştırıp kanıt kaydı yazar (unit|integration).
  review                     Bağımsız reviewer aşamasını çalıştırır.
  complete-task              Review APPROVED ise görevi kapatır ve claim'i bırakır.
  cleanup [--task <id>]      Bayat claim, geçici dosya ve tüketilmiş handoff'ları temizler.

Seçenekler:
  --dry-run    Hiçbir dosya yazmaz/komut çalıştırmaz, yapacağını gösterir.
  --quiet      Yalnız makine okunur çıktı.
  --help       Bu yardım.

Rol dağıtımının tek kaynağı: .agent/config/agents.yaml
Kurallar: AGENTS.md, CLAUDE.md, .qoder/rules/
EOF
}

# --- komutlar ---------------------------------------------------------------

cmd_status() {
  load_lib
  local stage status repair id lifecycle
  stage="$(state_field stage)"; status="$(state_field status)"
  repair="$(state_field repair_round)"; id="$(ledger_task_id)"
  lifecycle="$(lifecycle_state "$stage" "$status" "$repair" "$(_ledger_review_result)")"

  echo "Worktree      : $ROOT"
  echo "Branch        : $(git -C "$ROOT" branch --show-current 2>/dev/null || echo unknown)"
  echo "Rol config    : ${AGENT_ROLES_FILE#"$ROOT"/} (${AGENT_ROLES_STATUS})"
  if roles_active; then
    echo "Architect     : $ROLE_ARCHITECT"
    echo "Reviewer      : $ROLE_REVIEWER"
    printf 'Implementer   : %s (birincil=%s yedek=%s)\n' \
      "$(role_agent implementer 2>/dev/null || echo UNRESOLVED)" \
      "$ROLE_IMPLEMENTER_PRIMARY" "${ROLE_IMPLEMENTER_FALLBACK:-yok}"
    printf 'Tester        : %s (birincil=%s yedek=%s)\n' \
      "$(role_agent tester 2>/dev/null || echo UNRESOLVED)" \
      "$ROLE_TESTER_PRIMARY" "${ROLE_TESTER_FALLBACK:-yok}"
    echo "codex_available: $RUNTIME_CODEX_AVAILABLE"
    role_resolve implementer >/dev/null 2>&1 || true
    echo "Fallback neden : ${ROLE_RESOLUTION_REASON:-yok (birincil kullanılıyor)}"
  else
    echo "Rol config yok; geriye dönük tek backend: ${AGENT_BACKEND:-codex}"
  fi
  echo
  echo "Lifecycle     : $lifecycle"
  echo "Stage/Status  : $stage / $status (repair=$repair)"
  echo "Görev         : ${id:-yok}"
  local ledger
  if [[ -n "$id" ]] && ledger="$(ledger_find "$id" 2>/dev/null)"; then
    echo "Defter        : ${ledger#"$ROOT"/}"
  fi
  local handoff
  handoff="$(state_field handoff_file)"
  [[ "$handoff" != "null" && -n "$handoff" ]] && echo "Handoff       : ${handoff#"$ROOT"/}"
  echo
  echo "Aktif claim'ler:"
  local f found=0
  for f in "$CLAIM_DIR"/*.json; do
    [[ -f "$f" ]] || continue
    found=1
    jq -r '"  - " + .task_id + " agent=" + .agent + " pid=" + (.pid|tostring)
           + " worktree=" + .worktree' "$f"
  done
  (( found == 1 )) || echo "  (yok)"
}

cmd_next_task() {
  load_lib
  if select_next_task_from_docs; then
    echo "TASK_ID=$PLANNED_TASK_ID"
    echo "TITLE=$PLANNED_TITLE"
    echo "SOURCE=$PLANNED_SOURCE_DOCS"
    echo "REASON=$PLANNED_PRIORITY_REASON"
    echo "SCOPE_HINT=${SELECTED_SCOPE_HINT:-yok}"
  else
    echo "NEXT_STEP.md deterministik seçim vermedi (eksik, bayat veya status != active)."
    echo "Bu durumda 'devam' LLM planner'ı çalıştırır; agentctl ajan başlatmaz."
    return 3
  fi
}

cmd_create_task() {
  local id="${1:-}" title="${2:-}"
  [[ -n "$id" && -n "$title" ]] || die "kullanım: create-task <TASK-ID> <başlık>"
  load_lib
  local target="$LEDGER_ACTIVE/$id.md"
  if existing="$(ledger_find "$id" 2>/dev/null)"; then
    info "Görev zaten var: ${existing#"$ROOT"/} (idempotent: değiştirilmedi)"
    return 0
  fi
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "[dry-run] oluşturulacak: ${target#"$ROOT"/}"
    return 0
  fi
  sed -e "s|^task_id: .*|task_id: $id|" \
      -e "s|^branch: .*|branch: $(git -C "$ROOT" branch --show-current 2>/dev/null || echo unknown)|" \
      -e "s|^worktree: .*|worktree: $ROOT|" \
      -e "s|^started_at: .*|started_at: $(now)|" \
      -e "s|^updated_at: .*|updated_at: $(now)|" \
      -e "s|^# DQ-2026-XXX — <başlık>|# $id — $title|" \
      "$LEDGER_TEMPLATES/task.md" > "$target"
  info "Görev dosyası oluşturuldu: ${target#"$ROOT"/}"
  info "Not: pipeline görevi 'devam' ile başlatılır; bu dosya elle planlama içindir."
}

cmd_claim_task() {
  local id="${1:-}"
  [[ -n "$id" ]] || die "kullanım: claim-task <TASK-ID>"
  load_lib
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "[dry-run] claim edilecek: $id -> $ROOT"
    return 0
  fi
  claim_acquire "$id" "$(_ledger_role_agent implementer)" \
    || die "claim alınamadı (başka worktree sahibi olabilir): $id"
  info "Claim alındı: $id ($ROOT)"
}

cmd_select_runner() {
  local role="${1:-implementer}"
  load_lib
  roles_active || { echo "AGENT=${AGENT_BACKEND:-codex} (rol config yok)"; return 0; }
  role_resolve "$role" || die "rol karşılanamadı: $role"
  echo "ROLE=$role"
  echo "AGENT=$RESOLVED_AGENT"
  echo "PRIMARY=$RESOLVED_ROLE_PRIMARY"
  echo "FALLBACK_REASON=${ROLE_RESOLUTION_REASON:-none}"
  if roles_handoff_agent "$RESOLVED_AGENT"; then
    echo "MODE=handoff (otomatik çalıştırılamaz; görev paketi üretilir)"
  else
    echo "MODE=headless"
  fi
}

cmd_create_worktree() {
  local name="${1:-}"
  [[ -n "$name" ]] || die "kullanım: create-worktree <kisa-ad>"
  local branch="agent/$name"
  local base_root wt common
  # Worktree'ler her zaman ANA depo kökünden türetilir; başka bir worktree
  # içinden çalıştırıldığında iç içe yol üretilmez.
  common="$(git -C "$ROOT" rev-parse --path-format=absolute --git-common-dir 2>/dev/null || true)"
  if [[ -n "$common" ]]; then
    base_root="$(dirname "$common")"
  else
    base_root="$(cd "$TOOLS_DIR/../.." && pwd)"
  fi
  wt="$(dirname "$base_root")/$(basename "$base_root")-worktrees/$name"

  if [[ -d "$wt" ]]; then
    info "Worktree zaten var (idempotent): $wt"
    return 0
  fi
  if git -C "$base_root" show-ref --verify --quiet "refs/heads/$branch"; then
    die "branch zaten var: $branch — farklı bir kısa ad seç veya mevcut worktree'yi kullan"
  fi
  # Kirli ana çalışma ağacına dokunulmaz: worktree add mevcut değişiklikleri etkilemez,
  # ancak yine de kullanıcıya durum bildirilir.
  if [[ -n "$(git -C "$base_root" status --porcelain)" ]]; then
    info "Not: ana çalışma ağacı kirli. Worktree ekleme mevcut değişiklikleri etkilemez;"
    info "     hiçbir reset/clean/checkout yapılmaz."
  fi
  run git -C "$base_root" worktree add -b "$branch" "$wt" HEAD
  if [[ "$DRY_RUN" == "1" ]]; then
    info "[dry-run] oluşacak worktree: $wt (branch $branch)"
    return 0
  fi
  info "Worktree hazır: $wt (branch $branch)"
  info "Kullanmak için: AGENT_LOOP_TARGET=$wt devam"
}

cmd_build_handoff() {
  local role="${1:-implementer}"
  load_lib
  local id agent
  id="$(ledger_task_id)"
  [[ -n "$id" && "$id" != "BOOTSTRAP" ]] || die "aktif kontrat yok; önce 'devam' ile görev başlat"
  roles_active || die "rol config yok; handoff paketi rol dağıtımı gerektirir"
  # role_resolve (subshell değil): fallback nedeni pakete yazılabilmelidir.
  role_resolve "$role" || die "rol karşılanamadı: $role"
  agent="$RESOLVED_AGENT"
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "[dry-run] handoff üretilecek: rol=$role ajan=$agent görev=$id"
    return 0
  fi
  local file
  file="$(handoff_write "$role" "$agent" "$LOGS/${role}-manual.input.md")"
  echo "${file#"$ROOT"/}"
}

cmd_record_tests() {
  local suite="${1:-unit}"
  load_lib
  local id log cmd rc started duration
  id="$(ledger_task_id)"
  [[ -n "$id" && "$id" != "BOOTSTRAP" ]] || die "aktif kontrat yok"
  case "$suite" in
    unit)
      log="$LOGS/unit-tests-manual.log"
      cmd=(python3 -m pytest -q -p no:cacheprovider "$UNIT_TEST_DIR") ;;
    integration)
      log="$LOGS/integration-tests-manual.log"
      mapfile -t targets < <(discover_integration_targets)
      cmd=(python3 -m pytest -q -p no:cacheprovider "${targets[@]}") ;;
    *) die "suite unit veya integration olmalı" ;;
  esac
  if [[ "$DRY_RUN" == "1" ]]; then
    printf '[dry-run] çalıştırılacak: '; printf '%q ' "${cmd[@]}"; printf '\n'
    return 0
  fi
  started="$SECONDS"
  set +e
  run_logged_test "$log" "${cmd[@]}"
  rc=$?
  set -e
  duration=$(( SECONDS - started ))
  local file
  file="$(evidence_write "$id" "$suite" "${cmd[*]}" "$rc" "$duration" "$log" \
    "agentctl record-tests ile elle çalıştırıldı.")"
  echo "${file#"$ROOT"/}"
  echo "exit_code=$rc failure_class=$(classify_test_failure "$log" "$rc")"
  return 0
}

cmd_review() {
  load_lib
  [[ "$DRY_RUN" == "0" ]] || { echo "[dry-run] reviewer aşaması çalıştırılacak"; return 0; }
  local stage
  stage="$(state_field stage)"
  [[ "$stage" == "REVIEWER" ]] || info "Not: controller aşaması $stage; review yine de çalıştırılıyor."
  run_reviewer
}

cmd_complete_task() {
  load_lib
  local id review
  id="$(ledger_task_id)"
  [[ -n "$id" && "$id" != "BOOTSTRAP" ]] || die "aktif kontrat yok"
  review="$(_ledger_review_result)"
  [[ "$review" == "APPROVED" ]] \
    || die "görev kapatılamaz: bağımsız review sonucu '${review:-yok}' (APPROVED gerekli)"
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "[dry-run] kapatılacak: $id (review=APPROVED)"
    return 0
  fi
  state_update "COMPLETED" "COMPLETED" ""
  ledger_sync >/dev/null
  claim_release "$id" || true
  info "Görev kapatıldı: $id"
  info "Defter: $(ledger_find "$id" 2>/dev/null | sed "s|^$ROOT/||")"
}

cmd_cleanup() {
  local only_task=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --task) only_task="${2:-}"; shift 2 ;;
      *) die "bilinmeyen cleanup seçeneği: $1" ;;
    esac
  done
  load_lib
  local f id pid owner released=0
  for f in "$CLAIM_DIR"/*.json; do
    [[ -f "$f" ]] || continue
    id="$(jq -r '.task_id' "$f")"
    pid="$(jq -r '.pid // 0' "$f")"
    owner="$(jq -r '.worktree // ""' "$f")"
    [[ -z "$only_task" || "$only_task" == "$id" ]] || continue
    if [[ "$pid" =~ ^[0-9]+$ ]] && (( pid > 0 )) && kill -0 "$pid" 2>/dev/null; then
      info "Canlı claim korunuyor: $id (pid=$pid worktree=$owner)"
      continue
    fi
    info "Bayat claim bırakılıyor: $id (pid=$pid worktree=$owner)"
    run rm -f "$f"
    released=$(( released + 1 ))
  done
  # Yarıda kalmış geçici dosyalar (atomik yazımdan artakalan).
  local tmpcount
  tmpcount="$(find "$H" -maxdepth 3 -name '*.tmp.*' 2>/dev/null | wc -l)"
  if (( tmpcount > 0 )); then
    info "Artık geçici dosya: $tmpcount"
    if [[ "$DRY_RUN" == "0" ]]; then
      find "$H" -maxdepth 3 -name '*.tmp.*' -delete
    fi
  fi
  info "Temizlik tamam (bırakılan claim: $released). Hiçbir git reset/clean çalıştırılmadı."
}

# --- argüman ayrıştırma -----------------------------------------------------

ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    --quiet)   QUIET=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) ARGS+=("$1"); shift ;;
  esac
done

require_deps
set -- "${ARGS[@]:-}"
CMD="${1:-status}"
[[ $# -gt 0 ]] && shift || true

case "$CMD" in
  status)          cmd_status "$@" ;;
  next-task)       cmd_next_task "$@" ;;
  create-task)     cmd_create_task "$@" ;;
  claim-task)      cmd_claim_task "$@" ;;
  select-runner)   cmd_select_runner "$@" ;;
  create-worktree) cmd_create_worktree "$@" ;;
  build-handoff)   cmd_build_handoff "$@" ;;
  record-tests)    cmd_record_tests "$@" ;;
  review)          cmd_review "$@" ;;
  complete-task)   cmd_complete_task "$@" ;;
  cleanup)         cmd_cleanup "$@" ;;
  ""|help)         usage ;;
  *) die "bilinmeyen komut: $CMD (yardım: --help)" ;;
esac
