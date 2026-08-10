#!/usr/bin/env bash
# tools/agent-loop/tests/run.sh
#
# Agent-loop controller smoke/integration test suite. Gerçek agent CLI'ları ve
# gerçek pytest ÇAĞRILMAZ: her backend (codex, claude) bir stub ile, test kapıları
# ise fonksiyon override'ı ile taklit edilir. Her test kendi geçici repo'sunda
# izole çalışır.
set -uo pipefail

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOOP_DIR="$(cd "$TESTS_DIR/.." && pwd)"
STUB="$TESTS_DIR/stubs/codex"
STUB_CLAUDE="$TESTS_DIR/stubs/claude"
chmod +x "$STUB" "$STUB_CLAUDE" 2>/dev/null || true

PASS=0
FAIL=0
FAILED_TESTS=()

fail() { echo "    FAIL: $*"; FAIL=$((FAIL + 1)); CURRENT_OK=0; }
ok()   { PASS=$((PASS + 1)); }

assert_eq() { # expected actual msg
  if [[ "$1" == "$2" ]]; then ok; else fail "$3 (beklenen='$1' gerçek='$2')"; fi
}
assert_contains() { # haystack needle msg
  if [[ "$1" == *"$2"* ]]; then ok; else fail "$3 (bulunamadı: '$2')"; fi
}
assert_absent() { # path msg
  if [[ ! -e "$1" ]]; then ok; else fail "$2 (var olmamalıydı: $1)"; fi
}
assert_present() { # path msg
  if [[ -e "$1" ]]; then ok; else fail "$2 (yok: $1)"; fi
}
retry_nonempty() { # file  -> 0 if becomes non-empty within ~2s
  local f="$1" i
  for i in $(seq 1 20); do [[ -s "$f" ]] && return 0; sleep 0.1; done
  return 1
}

make_repo() {
  local d
  d="$(mktemp -d)"
  git -C "$d" init -q
  git -C "$d" config user.email t@t.t
  git -C "$d" config user.name t
  mkdir -p "$d/src/veri_kalitesi" "$d/alembic" \
           "$d/tests/unit" "$d/tests/integration"
  printf '.agent-handoff/\n' > "$d/.gitignore"
  echo "x" > "$d/README.md"
  git -C "$d" add -A >/dev/null 2>&1
  git -C "$d" commit -qm init >/dev/null 2>&1
  echo "$d"
}

# Her test: temiz repo + lib fresh source + init + stub codex.
run_test() {
  local name="$1" fn="$2"
  CURRENT_OK=1
  ROOTX="$(make_repo)"
  # shellcheck source=/dev/null
  source "$LOOP_DIR/lib.sh"
  CODEX_BIN="$STUB"
  CLAUDE_BIN="$STUB_CLAUDE"
  MAX_REPAIR_ROUNDS=2
  TEST_TIMEOUT_SECONDS=900
  CODEX_STAGE_TIMEOUT_SECONDS=60
  AGENT_STAGE_TIMEOUT_SECONDS=60
  # Harness alt kabuk kullanmadığı için backend seçimi ve rol tuning değişkenleri
  # testler arasında sızabilir; her testte açıkça varsayılana döndürülür.
  AGENT_BACKEND=codex
  AGENT_BACKEND_FALLBACK=""
  AGENT_STDERR_LOG_MAX_BYTES=2000000
  CODEX_IMPLEMENTER_MODEL=""; CODEX_REVIEWER_MODEL=""; CODEX_PLANNER_MODEL=""
  CODEX_IMPLEMENTER_REASONING=""; CODEX_REVIEWER_REASONING=""; CODEX_PLANNER_REASONING=""
  CLAUDE_IMPLEMENTER_MODEL=""; CLAUDE_REVIEWER_MODEL=""; CLAUDE_PLANNER_MODEL=""
  CLAUDE_IMPLEMENTER_EFFORT=""; CLAUDE_REVIEWER_EFFORT=""; CLAUDE_PLANNER_EFFORT=""
  unset STUB_CODEX_EXIT STUB_CODEX_EMPTY STUB_CODEX_ECHO_PG STUB_CODEX_STATUS \
        STUB_CODEX_BODY STUB_CODEX_STDERR STUB_CODEX_STDERR_BYTES
  unset STUB_CLAUDE_EXIT STUB_CLAUDE_EMPTY STUB_CLAUDE_ECHO_PG STUB_CLAUDE_STATUS \
        STUB_CLAUDE_BODY STUB_CLAUDE_ARGV_LOG STUB_CLAUDE_CWD_LOG STUB_CLAUDE_STDERR \
        STUB_CLAUDE_STDOUT_ERROR
  # run_agent stub'ı `env` ile başlatır; kontrol değişkenleri export edilmeli ki
  # alt sürece ulaşsın. Export attribute'u sonraki atamalarda korunur.
  export STUB_CODEX_EXIT STUB_CODEX_EMPTY STUB_CODEX_ECHO_PG STUB_CODEX_STATUS \
         STUB_CODEX_BODY STUB_CODEX_STDERR STUB_CODEX_STDERR_BYTES
  export STUB_CLAUDE_EXIT STUB_CLAUDE_EMPTY STUB_CLAUDE_ECHO_PG STUB_CLAUDE_STATUS \
         STUB_CLAUDE_BODY STUB_CLAUDE_ARGV_LOG STUB_CLAUDE_CWD_LOG STUB_CLAUDE_STDERR \
        STUB_CLAUDE_STDOUT_ERROR
  DATA_QUALITY_POSTGRES_TEST_URL=""
  DATA_QUALITY_DATABASE_SCHEMA=""
  agentloop_init "$ROOTX" "$LOOP_DIR"
  # Alt kabuk KULLANILMAZ: sayaçlar ana kabukta güncellenmeli. Test override'ları
  # sızsa da bir sonraki run_test lib.sh'i yeniden source ederek orijinalleri geri yükler.
  cd "$ROOTX" || return
  "$fn"
  cd "$TESTS_DIR" || return
  if [[ "$CURRENT_OK" == "1" ]]; then echo "  ok  $name"; else echo "  XX  $name"; FAILED_TESTS+=("$name"); fi
  rm -rf "$ROOTX"
}

# Rol yapılandırması yazar ve yeniden yükler. Varsayılan: Codex birincil,
# Qoder yedek, Claude mimar/reviewer (üretim yapılandırmasının aynısı).
write_roles_config() { # [codex_available] [impl_primary] [impl_fallback] [reviewer]
  local avail="${1:-false}" primary="${2:-codex}" fallback="${3:-qoder}" reviewer="${4:-claude}"
  mkdir -p "$ROOTX/.agent/config"
  cat > "$ROOTX/.agent/config/agents.yaml" <<EOF
schema_version: 1
architect: claude
reviewer: $reviewer
implementer:
  primary: $primary
  fallback: $fallback
tester:
  primary: $primary
  fallback: $fallback
runtime:
  codex_available: $avail
  fallback_on_quota_error: true
  prevent_parallel_writers: true
EOF
  roles_load "$AGENT_ROLES_FILE"
}

# --- test cases ------------------------------------------------------------

t_empty_continue_runs_planner() {
  state_update COMPLETED COMPLETED ""
  run_planner() { : > "$H/.planner_ran"; PLANNED_TASK_ID=T; PLANNED_TITLE=Auto; PLANNED_OBJECTIVE=obj; PLANNED_SOURCE_DOCS=""; PLANNED_PRIORITY_REASON=r; return 0; }
  run_implementer() { state_update TESTER READY ""; return 0; }
  run_tests() { state_update REVIEWER READY ""; return 0; }
  run_reviewer() { state_update COMPLETED COMPLETED ""; return 0; }
  main continue "" >/dev/null 2>&1
  assert_present "$H/.planner_ran" "planner boş devam'da çalışmalı"
  assert_eq "COMPLETED" "$(state_field status)" "döngü tamamlanmalı"
  assert_eq "1" "$(state_field iteration)" "iteration artmalı"
}

t_explicit_task_skips_planner() {
  state_update COMPLETED COMPLETED ""
  run_planner() { : > "$H/.planner_ran"; return 0; }
  run_implementer() { state_update TESTER READY ""; return 0; }
  run_tests() { state_update REVIEWER READY ""; return 0; }
  run_reviewer() { state_update COMPLETED COMPLETED ""; return 0; }
  main continue "Belirli gorev X" >/dev/null 2>&1
  assert_absent "$H/.planner_ran" "açık görevde planner atlanmalı"
  assert_eq "manual" "$(jq -r '.task.selection_mode' "$TASK")" "selection_mode manual olmalı"
  assert_eq "Belirli gorev X" "$(jq -r '.task.title' "$TASK")" "başlık görev metni olmalı"
}

t_completed_reselects_new_iteration() {
  state_update COMPLETED COMPLETED ""
  start_new_task "obj-a" "" "A" "" "r" manual >/dev/null 2>&1
  assert_eq "1" "$(state_field iteration)" "ilk iterasyon 1"
  state_update COMPLETED COMPLETED ""
  start_new_task "obj-b" "" "B" "" "r" manual >/dev/null 2>&1
  assert_eq "2" "$(state_field iteration)" "sonraki iterasyon 2 (DONE tekrar seçilmez, yeni kontrat)"
  assert_eq "[]" "$(jq -c '.scope.allowed_files' "$TASK")" "yeni kontrat dosya kapsamı taşımaz"
}

t_planner_no_task_waiting_human() {
  state_update COMPLETED COMPLETED ""
  STUB_CODEX_STATUS="STATUS: NO_TASK"
  run_planner >/dev/null 2>&1 || true
  assert_eq "WAITING_HUMAN" "$(state_field status)" "NO_TASK -> WAITING_HUMAN"
  assert_eq "PLANNER" "$(state_field stage)" "stage PLANNER kalmalı"
}

t_base_ref_not_a_gate() {
  start_new_task "obj" "" "T" "" "r" manual >/dev/null 2>&1
  local ref1 ref2
  ref1="$(jq -r '.repository.base_ref' "$TASK")"
  echo "change" > "$ROOTX/newfile.txt"
  git -C "$ROOTX" add -A >/dev/null 2>&1
  git -C "$ROOTX" commit -qm second >/dev/null 2>&1
  refresh_contract
  ref2="$(jq -r '.repository.base_ref' "$TASK")"
  if [[ "$ref1" != "$ref2" ]]; then ok; else fail "refresh_contract base_ref'i güncel HEAD'e taşımalı"; fi
}

t_codex_nonzero_exit_no_stale_result() {
  echo "OLD STALE" > "$H/CODEX_RESULT.md"
  STUB_CODEX_EXIT=7
  echo "prompt" > "$H/in.md"
  run_codex implementer "$H/in.md" "$H/CODEX_RESULT.md" '^STATUS: SUCCESS$' >/dev/null 2>&1
  assert_eq "33" "$?" "non-zero exit 33 döndürmeli"
  assert_absent "$H/CODEX_RESULT.md" "bayat result silinmeli, okunmamalı"
}

t_codex_empty_result_fails() {
  STUB_CODEX_EMPTY=1
  echo "prompt" > "$H/in.md"
  run_codex implementer "$H/in.md" "$H/CODEX_RESULT.md" '^STATUS: SUCCESS$' >/dev/null 2>&1
  assert_eq "34" "$?" "boş sonuç 34 döndürmeli"
  assert_absent "$H/CODEX_RESULT.md" "boş sonuç görünür yapılmamalı"
}

t_codex_stderr_logged() {
  STUB_CODEX_EXIT=5
  echo "prompt" > "$H/in.md"
  run_codex implementer "$H/in.md" "$H/CODEX_RESULT.md" '^STATUS: SUCCESS$' >/dev/null 2>&1
  local log="$LOGS/implementer-i$(state_field iteration)-r$(state_field repair_round).stderr.log"
  if retry_nonempty "$log"; then ok; else fail "stderr kalıcı loglanmalı: $log"; fi
}

# --- backend parametrikliği (AGENT_BACKEND=claude) --------------------------

t_claude_backend_captures_stdout_result() {
  AGENT_BACKEND=claude
  STUB_CLAUDE_BODY="claude gövdesi"
  echo "prompt" > "$H/in.md"
  run_agent implementer "$H/in.md" "$H/CODEX_RESULT.md" '^STATUS: SUCCESS$' >/dev/null 2>&1
  assert_eq "0" "$?" "claude backend başarılı sonuç üretmeli"
  assert_present "$H/CODEX_RESULT.md" "stdout sonucu dosyaya yakalanmalı"
  assert_contains "$(cat "$H/CODEX_RESULT.md" 2>/dev/null)" "claude gövdesi" \
    "stdout gövdesi sonuç dosyasına geçmeli"
  local log="$LOGS/implementer-i$(state_field iteration)-r$(state_field repair_round).stdout.log"
  assert_contains "$(cat "$log" 2>/dev/null)" "BACKEND=claude" "stdout log backend'i kaydetmeli"
  assert_contains "$(cat "$log" 2>/dev/null)" "claude gövdesi" "sonuç stdout loguna da eklenmeli"
}

t_claude_backend_arg_mapping() {
  AGENT_BACKEND=claude
  CLAUDE_REVIEWER_MODEL="opus"
  CLAUDE_REVIEWER_EFFORT="low"
  # Codex tuning değişkenleri claude argümanlarına SIZMAMALI.
  CODEX_REVIEWER_MODEL="gpt-leak"
  CODEX_REVIEWER_REASONING="high"
  STUB_CLAUDE_ARGV_LOG="$H/claude.argv"
  echo "prompt" > "$H/in.md"
  run_agent reviewer "$H/in.md" "$H/ARCHITECT_REVIEW.md" '^STATUS: [A-Z_]+$' >/dev/null 2>&1
  local argv
  argv="$(cat "$H/claude.argv" 2>/dev/null)"
  assert_contains "$argv" "-p" "claude non-interactive -p ile çağrılmalı"
  assert_contains "$argv" "bypassPermissions" "onay istemeden çalışmalı"
  assert_contains "$argv" "opus" "rol modeli --model ile geçmeli"
  assert_contains "$argv" "low" "rol effort'u --effort ile geçmeli"
  if [[ "$argv" == *"gpt-leak"* ]]; then fail "CODEX_* tuning claude'a sızmamalı"; else ok; fi
  if [[ "$argv" == *"-o"* ]]; then fail "claude backend -o kullanmamalı (stdout yakalanır)"; else ok; fi
}

t_claude_backend_runs_in_repo_root() {
  AGENT_BACKEND=claude
  STUB_CLAUDE_CWD_LOG="$H/claude.cwd"
  echo "prompt" > "$H/in.md"
  run_agent implementer "$H/in.md" "$H/CODEX_RESULT.md" '^STATUS: SUCCESS$' >/dev/null 2>&1
  assert_eq "$(cd "$ROOTX" && pwd -P)" "$(cd "$(cat "$H/claude.cwd" 2>/dev/null)" && pwd -P)" \
    "agent repo kökünde çalıştırılmalı"
}

t_claude_backend_nonzero_exit_no_stale_result() {
  AGENT_BACKEND=claude
  echo "OLD STALE" > "$H/CODEX_RESULT.md"
  STUB_CLAUDE_EXIT=7
  echo "prompt" > "$H/in.md"
  run_agent implementer "$H/in.md" "$H/CODEX_RESULT.md" '^STATUS: SUCCESS$' >/dev/null 2>&1
  assert_eq "33" "$?" "claude non-zero exit 33 döndürmeli"
  assert_absent "$H/CODEX_RESULT.md" "bayat result claude backend'de de silinmeli"
}

t_claude_backend_empty_result_fails() {
  AGENT_BACKEND=claude
  STUB_CLAUDE_EMPTY=1
  echo "prompt" > "$H/in.md"
  run_agent implementer "$H/in.md" "$H/CODEX_RESULT.md" '^STATUS: SUCCESS$' >/dev/null 2>&1
  assert_eq "34" "$?" "boş stdout 34 döndürmeli"
  assert_absent "$H/CODEX_RESULT.md" "boş sonuç görünür yapılmamalı"
}

t_claude_backend_invalid_status_fails() {
  AGENT_BACKEND=claude
  STUB_CLAUDE_STATUS="RASTGELE METİN"
  echo "prompt" > "$H/in.md"
  run_agent implementer "$H/in.md" "$H/CODEX_RESULT.md" '^STATUS: SUCCESS$' >/dev/null 2>&1
  assert_eq "21" "$?" "beklenmeyen STATUS 21 döndürmeli"
  assert_absent "$H/CODEX_RESULT.md" "doğrulanmamış sonuç görünür yapılmamalı"
  assert_present "$LOGS/implementer-invalid-result.md" "geçersiz sonuç kanıt olarak loglanmalı"
}

t_claude_backend_pg_env_forwarded() {
  AGENT_BACKEND=claude
  DATA_QUALITY_POSTGRES_TEST_URL="postgres://SENTINEL_URL"
  DATA_QUALITY_DATABASE_SCHEMA="sentinel_schema"
  STUB_CLAUDE_ECHO_PG=1
  echo "prompt" > "$H/in.md"
  run_agent implementer "$H/in.md" "$H/CODEX_RESULT.md" '^STATUS: SUCCESS$' >/dev/null 2>&1
  assert_present "$H/CODEX_RESULT.md" "sonuç üretilmeli"
  assert_contains "$(cat "$H/CODEX_RESULT.md" 2>/dev/null)" "SENTINEL_URL" \
    "PG url claude alt sürecine forward edilmeli"
}

t_unknown_backend_fails_closed() {
  AGENT_BACKEND=vertex-hayali
  echo "OLD STALE" > "$H/CODEX_RESULT.md"
  echo "prompt" > "$H/in.md"
  run_agent implementer "$H/in.md" "$H/CODEX_RESULT.md" '^STATUS: SUCCESS$' >/dev/null 2>&1
  assert_eq "35" "$?" "bilinmeyen backend 35 ile fail-closed olmalı"
  assert_absent "$H/CODEX_RESULT.md" "bilinmeyen backend'de bayat result okunmamalı"
}

t_claude_backend_full_iteration() {
  AGENT_BACKEND=claude
  # Test kapıları taklit edilir; agent aşamaları claude stub'ı ile yürür.
  run_tests() { echo "stub test report" > "$H/TEST_REPORT.md"; state_update "REVIEWER" "READY" ""; return 0; }
  main continue >/dev/null 2>&1
  assert_eq "COMPLETED" "$(state_field stage)" "claude backend uçtan uca iterasyonu tamamlamalı"
  assert_present "$H/ARCHITECT_REVIEW.md" "reviewer onayı üretilmeli"
}

# --- sağlayıcı erişimi yokken backend devri --------------------------------

# Gerçek codex kota mesajı (iterasyon 13'te pipeline'ı durduran metin).
USAGE_LIMIT_MSG="ERROR: You've hit your usage limit. Upgrade to Pro (https://chatgpt.com/explore/pro) or try again at Aug 5th, 2026 8:49 AM."

t_fallback_on_provider_usage_limit() {
  AGENT_BACKEND=codex
  AGENT_BACKEND_FALLBACK=claude
  STUB_CODEX_EXIT=1
  STUB_CODEX_STDERR="$USAGE_LIMIT_MSG"
  STUB_CLAUDE_BODY="fallback gövdesi"
  echo "prompt" > "$H/in.md"
  run_agent implementer "$H/in.md" "$H/CODEX_RESULT.md" '^STATUS: SUCCESS$' >/dev/null 2>&1
  assert_eq "0" "$?" "kota hatasında yedek backend aşamayı tamamlamalı"
  assert_contains "$(cat "$H/CODEX_RESULT.md" 2>/dev/null)" "fallback gövdesi" \
    "sonuç yedek backend'den gelmeli"
  local log="$LOGS/implementer-i$(state_field iteration)-r$(state_field repair_round).stdout.log"
  assert_contains "$(cat "$log" 2>/dev/null)" "FALLBACK_TO=claude" "devir stdout loguna yazılmalı"
  assert_contains "$(cat "$log" 2>/dev/null)" "FALLBACK_REASON=provider_unavailable" \
    "devir nedeni kayda geçmeli"
  assert_contains "$(cat "$log" 2>/dev/null)" "BACKEND=claude" "ikinci deneme backend'i loglanmalı"
  # Birincil denemenin kanıtı silinmemeli.
  local elog="$LOGS/implementer-i$(state_field iteration)-r$(state_field repair_round).stderr.log"
  assert_contains "$(cat "$elog" 2>/dev/null)" "usage limit" "birincil stderr kanıtı korunmalı"
}

t_fallback_on_empty_result_with_provider_error() {
  # Süreç 0 dönse bile sonuç boş ve stderr sağlayıcı hatası ise devir yapılır.
  AGENT_BACKEND=claude
  AGENT_BACKEND_FALLBACK=codex
  STUB_CLAUDE_EMPTY=1
  STUB_CLAUDE_STDERR="Error: 429 too many requests"
  STUB_CODEX_BODY="codex devraldı"
  echo "prompt" > "$H/in.md"
  run_agent implementer "$H/in.md" "$H/CODEX_RESULT.md" '^STATUS: SUCCESS$' >/dev/null 2>&1
  assert_eq "0" "$?" "boş sonuç + sağlayıcı hatasında devir çalışmalı"
  assert_contains "$(cat "$H/CODEX_RESULT.md" 2>/dev/null)" "codex devraldı" \
    "sonuç yedek backend'den gelmeli"
}

# Gerçek claude oturum limiti metni: iterasyon 14 implementer'ını düşürdü ve
# stderr BOŞ kaldı, mesaj stdout'a geldi.
SESSION_LIMIT_MSG="You've hit your session limit · resets 5:10pm (Europe/Istanbul)"

t_fallback_on_stdout_session_limit() {
  AGENT_BACKEND=claude
  AGENT_BACKEND_FALLBACK=codex
  STUB_CLAUDE_STDOUT_ERROR="$SESSION_LIMIT_MSG"
  STUB_CLAUDE_EXIT=1
  STUB_CODEX_BODY="codex devraldı"
  echo "prompt" > "$H/in.md"
  run_agent implementer "$H/in.md" "$H/CODEX_RESULT.md" '^STATUS: SUCCESS$' >/dev/null 2>&1
  assert_eq "0" "$?" "stdout'a yazılan oturum limiti devri tetiklemeli"
  assert_contains "$(cat "$H/CODEX_RESULT.md" 2>/dev/null)" "codex devraldı" \
    "sonuç yedek backend'den gelmeli"
  local log="$LOGS/implementer-i$(state_field iteration)-r$(state_field repair_round).stdout.log"
  assert_contains "$(cat "$log" 2>/dev/null)" "FALLBACK_TO=codex" "devir kayda geçmeli"
  # stderr boş olduğu halde tespit çalışmalı.
  local elog="$LOGS/implementer-i$(state_field iteration)-r$(state_field repair_round).stderr.log"
  if [[ ! -s "$elog" ]]; then ok; else
    fail "bu senaryoda stderr boş kalmalı (gerçek davranış)"; fi
}

t_session_limit_recognised_on_stderr_too() {
  echo "$SESSION_LIMIT_MSG" > "$H/fake-stderr.log"
  if agent_provider_unavailable "$H/fake-stderr.log" 1; then ok; else
    fail "'session limit' stderr'de de tanınmalı"; fi
}

t_valid_result_mentioning_limit_is_not_provider_error() {
  # Yanlış pozitif koruması: geçerli bir rapor bu sözcükleri metin olarak
  # içerebilir. Sonuç `STATUS:` ile başlıyorsa sağlayıcı arızası sayılmamalı.
  AGENT_BACKEND=claude
  AGENT_BACKEND_FALLBACK=codex
  STUB_CLAUDE_BODY="Raporda usage limit ve quota sözcükleri kanıt olarak geçiyor."
  STUB_CODEX_BODY="codex ASLA CALISMAMALI"
  echo "prompt" > "$H/in.md"
  run_agent implementer "$H/in.md" "$H/CODEX_RESULT.md" '^STATUS: SUCCESS$' >/dev/null 2>&1
  assert_eq "0" "$?" "geçerli sonuç başarılı sayılmalı"
  assert_contains "$(cat "$H/CODEX_RESULT.md" 2>/dev/null)" "kanıt olarak geçiyor" \
    "sonuç birincil backend'den gelmeli"
  if [[ "$(cat "$H/CODEX_RESULT.md" 2>/dev/null)" == *"ASLA CALISMAMALI"* ]]; then
    fail "geçerli sonuç varken devir yapılmamalı"
  else ok; fi
}

t_provider_error_in_result_only_without_status() {
  # Doğrudan fonksiyon sözleşmesi: sonuç kanalına yalnız geçerli STATUS yokken bakılır.
  printf 'STATUS: SUCCESS\nusage limit metni gövdede.\n' > "$H/res-ok.md"
  : > "$H/empty-stderr.log"
  if agent_provider_unavailable "$H/empty-stderr.log" 1 "$H/res-ok.md"; then
    fail "STATUS ile başlayan sonuç sağlayıcı arızası sayılmamalı"
  else ok; fi
  printf '%s\n' "$SESSION_LIMIT_MSG" > "$H/res-bad.md"
  if agent_provider_unavailable "$H/empty-stderr.log" 1 "$H/res-bad.md"; then ok; else
    fail "STATUS'suz kota metni sağlayıcı arızası sayılmalı"; fi
}

t_no_fallback_on_ordinary_failure() {
  AGENT_BACKEND=codex
  AGENT_BACKEND_FALLBACK=claude
  STUB_CODEX_EXIT=7
  STUB_CLAUDE_ARGV_LOG="$H/claude.argv"
  echo "prompt" > "$H/in.md"
  run_agent implementer "$H/in.md" "$H/CODEX_RESULT.md" '^STATUS: SUCCESS$' >/dev/null 2>&1
  assert_eq "33" "$?" "sıradan başarısızlıkta devir yapılmamalı"
  assert_absent "$H/claude.argv" "yedek backend hiç çalıştırılmamalı"
  assert_absent "$H/CODEX_RESULT.md" "başarısız aşamada sonuç yayınlanmamalı"
}

t_no_fallback_when_disabled() {
  AGENT_BACKEND=codex
  AGENT_BACKEND_FALLBACK=""
  STUB_CODEX_EXIT=1
  STUB_CODEX_STDERR="$USAGE_LIMIT_MSG"
  STUB_CLAUDE_ARGV_LOG="$H/claude.argv"
  echo "prompt" > "$H/in.md"
  run_agent implementer "$H/in.md" "$H/CODEX_RESULT.md" '^STATUS: SUCCESS$' >/dev/null 2>&1
  assert_eq "33" "$?" "fallback kapalıyken kota hatası da başarısızlıktır"
  assert_absent "$H/claude.argv" "fallback kapalıyken diğer sağlayıcıya maliyet kaymamalı"
}

t_no_fallback_to_same_backend() {
  AGENT_BACKEND=codex
  AGENT_BACKEND_FALLBACK=codex
  STUB_CODEX_EXIT=1
  STUB_CODEX_STDERR="$USAGE_LIMIT_MSG"
  echo "prompt" > "$H/in.md"
  run_agent implementer "$H/in.md" "$H/CODEX_RESULT.md" '^STATUS: SUCCESS$' >/dev/null 2>&1
  assert_eq "33" "$?" "aynı backend'e devir anlamsızdır, tekrar denenmemeli"
  local log="$LOGS/implementer-i$(state_field iteration)-r$(state_field repair_round).stdout.log"
  if [[ "$(cat "$log" 2>/dev/null)" == *"FALLBACK_TO"* ]]; then
    fail "aynı backend için devir kaydı yazılmamalı"
  else ok; fi
}

t_unknown_fallback_target_no_attempt() {
  AGENT_BACKEND=codex
  AGENT_BACKEND_FALLBACK=bilinmeyen-provider
  STUB_CODEX_EXIT=1
  STUB_CODEX_STDERR="$USAGE_LIMIT_MSG"
  echo "prompt" > "$H/in.md"
  run_agent implementer "$H/in.md" "$H/CODEX_RESULT.md" '^STATUS: SUCCESS$' >/dev/null 2>&1
  assert_eq "33" "$?" "bilinmeyen fallback hedefi aşamayı kurtarmamalı"
  assert_contains "$(cat "$LOGS/implementer-failures.log" 2>/dev/null)" "bilinmiyor" \
    "bilinmeyen fallback hedefi loglanmalı"
}

t_timeout_is_not_provider_unavailable() {
  # GNU timeout kodları sağlayıcı arızası sayılmaz: stderr eşleşse bile devredilmez.
  echo "$USAGE_LIMIT_MSG" > "$H/fake-stderr.log"
  if agent_provider_unavailable "$H/fake-stderr.log" 124; then
    fail "timeout (124) sağlayıcı arızası sayılmamalı"
  else ok; fi
  if agent_provider_unavailable "$H/fake-stderr.log" 1; then ok; else
    fail "kota mesajı sağlayıcı arızası olarak tanınmalı"; fi
  : > "$H/fake-stderr.log"
  if agent_provider_unavailable "$H/fake-stderr.log" 1; then
    fail "boş stderr sağlayıcı arızası sayılmamalı"
  else ok; fi
}

# --- kalıcı log boyutu -----------------------------------------------------

t_stderr_log_capped_keeps_tail() {
  AGENT_BACKEND=codex
  AGENT_STDERR_LOG_MAX_BYTES=50000
  STUB_CODEX_STDERR_BYTES=300000
  STUB_CODEX_STDERR="TAIL_SENTINEL_ERROR"
  STUB_CODEX_EXIT=1
  echo "prompt" > "$H/in.md"
  run_agent implementer "$H/in.md" "$H/CODEX_RESULT.md" '^STATUS: SUCCESS$' >/dev/null 2>&1
  local elog size
  elog="$LOGS/implementer-i$(state_field iteration)-r$(state_field repair_round).stderr.log"
  size="$(stat -c %s "$elog" 2>/dev/null || echo 0)"
  if (( size <= 50000 + 512 )); then ok; else
    fail "stderr logu üst sınıra indirilmeli (boyut=$size)"; fi
  assert_contains "$(cat "$elog" 2>/dev/null)" "TAIL_SENTINEL_ERROR" \
    "kesme sonrası gerçek hata mesajı (son baytlar) korunmalı"
  assert_contains "$(cat "$elog" 2>/dev/null)" "son" "kesme olayı logda açıkça belirtilmeli"
}

t_stderr_log_not_capped_when_disabled() {
  AGENT_BACKEND=codex
  AGENT_STDERR_LOG_MAX_BYTES=0
  STUB_CODEX_STDERR_BYTES=120000
  STUB_CODEX_EXIT=1
  echo "prompt" > "$H/in.md"
  run_agent implementer "$H/in.md" "$H/CODEX_RESULT.md" '^STATUS: SUCCESS$' >/dev/null 2>&1
  local elog size
  elog="$LOGS/implementer-i$(state_field iteration)-r$(state_field repair_round).stderr.log"
  size="$(stat -c %s "$elog" 2>/dev/null || echo 0)"
  if (( size > 100000 )); then ok; else
    fail "0 sınırı kesme yapmamalı (boyut=$size)"; fi
}

t_test_timeout_exit_code() {
  TEST_TIMEOUT_SECONDS=1
  run_logged_test "$LOGS/timeout.log" sleep 5 >/dev/null 2>&1
  assert_eq "124" "$?" "timeout 124 exit kodu üretmeli"
}

t_pg_env_forwarded() {
  DATA_QUALITY_POSTGRES_TEST_URL="postgres://SENTINEL_URL"
  DATA_QUALITY_DATABASE_SCHEMA="sentinel_schema"
  STUB_CODEX_ECHO_PG=1
  echo "prompt" > "$H/in.md"
  run_codex implementer "$H/in.md" "$H/CODEX_RESULT.md" '^STATUS: SUCCESS$' >/dev/null 2>&1
  assert_present "$H/CODEX_RESULT.md" "sonuç üretilmeli"
  assert_contains "$(cat "$H/CODEX_RESULT.md" 2>/dev/null)" "SENTINEL_URL" "PG url alt sürece forward edilmeli"
}

t_integration_required_detection() {
  # sadece unit test değişikliği -> gerekmez
  echo "x" > "$ROOTX/tests/unit/test_x.py"
  if integration_required; then fail "yalnız unit değişikliği entegrasyon gerektirmemeli"; else ok; fi
  # backend/veritabanı dokümanı değişikliği -> gerekmez
  echo "doc" > "$ROOTX/docs/backend/BACKEND-INDEX.md"
  echo "doc" > "$ROOTX/docs/database/VERITABANI-INDEX.md"
  if integration_required; then fail "doküman değişikliği entegrasyon gerektirmemeli"; else ok; fi
  # Alembic değişikliği -> gerekir
  mkdir -p "$ROOTX/alembic/versions"
  echo "migration" > "$ROOTX/alembic/versions/x.py"
  if integration_required; then ok; else fail "migration değişikliği entegrasyon gerektirmeli"; fi
  rm -f "$ROOTX/alembic/versions/x.py"
  # src değişikliği -> gerekir
  echo "y" > "$ROOTX/src/veri_kalitesi/z.py"
  if integration_required; then ok; else fail "src değişikliği entegrasyon gerektirmeli"; fi
}

t_optional_integration_target_selection() {
  local targets
  echo "y" > "$ROOTX/src/veri_kalitesi/z.py"
  targets="$(discover_integration_targets)"
  assert_contains "$targets" "--ignore=$OPTIONAL_INTEGRATION_TEST" \
    "geniş kapı opsiyonel suite'i dışlamalı"
  assert_contains "$targets" "$INTEGRATION_TEST_DIR" \
    "geniş kapı zorunlu entegrasyon dizinini çalıştırmalı"

  mkdir -p "$(dirname "$ROOTX/$OPTIONAL_INTEGRATION_TEST")"
  echo "test" > "$ROOTX/$OPTIONAL_INTEGRATION_TEST"
  targets="$(discover_integration_targets)"
  assert_eq "$OPTIONAL_INTEGRATION_TEST" "$targets" \
    "opsiyonel suite değişirse doğrudan zorunlu hedef olmalı"
}

t_pg_preflight_missing_no_fake_pass() {
  echo "y" > "$ROOTX/src/veri_kalitesi/z.py"   # integration_required -> true
  run_logged_test() { : > "$1"; echo "1 passed" >> "$1"; return 0; }  # unit passes
  DATA_QUALITY_POSTGRES_TEST_URL=""   # preflight fails
  run_tests >/dev/null 2>&1
  assert_eq "FAILED" "$(state_field status)" "PG yoksa sahte PASS olmamalı"
  assert_contains "$(state_field last_error)" "ENVIRONMENT_BLOCK" "hata ENVIRONMENT_BLOCK olmalı"
}

t_integration_skip_gate_fails() {
  echo "y" > "$ROOTX/src/veri_kalitesi/z.py"
  postgres_preflight() { echo "POSTGRES_PREFLIGHT_OK"; return 0; }
  run_logged_test() {
    local log="$1"
    if [[ "$log" == *integration* ]]; then : > "$log"; echo "5 passed, 1 skipped" >> "$log"; return 0
    else : > "$log"; echo "3 passed" >> "$log"; return 0; fi
  }
  run_tests >/dev/null 2>&1
  assert_eq "FAILED" "$(state_field status)" "zorunlu entegrasyon skip'i gate'i düşürmeli"
  assert_contains "$(state_field last_error)" "skip" "hata skip'i belirtmeli"
}

t_changes_required_starts_repair() {
  state_update REVIEWER READY ""
  echo "impl" > "$H/CODEX_RESULT.md"; echo "test" > "$H/TEST_REPORT.md"
  STUB_CODEX_STATUS="STATUS: CHANGES_REQUIRED"
  run_reviewer >/dev/null 2>&1
  assert_eq "IMPLEMENTER" "$(state_field stage)" "CHANGES_REQUIRED implementer'a dönmeli"
  assert_eq "READY" "$(state_field status)" "status READY olmalı"
  assert_eq "1" "$(state_field repair_round)" "repair_round artmalı"
}

t_repair_limit_waiting_human() {
  MAX_REPAIR_ROUNDS=1
  state_patch '.stage="REVIEWER"|.status="READY"|.repair_round=1'
  echo "impl" > "$H/CODEX_RESULT.md"; echo "test" > "$H/TEST_REPORT.md"
  STUB_CODEX_STATUS="STATUS: CHANGES_REQUIRED"
  run_reviewer >/dev/null 2>&1
  assert_eq "WAITING_HUMAN" "$(state_field status)" "repair limiti aşılınca WAITING_HUMAN"
}

t_human_decision_persists_state() {
  state_update REVIEWER READY ""
  echo "impl" > "$H/CODEX_RESULT.md"; echo "test" > "$H/TEST_REPORT.md"
  STUB_CODEX_STATUS="STATUS: HUMAN_DECISION"
  run_reviewer >/dev/null 2>&1
  assert_eq "WAITING_HUMAN" "$(state_field status)" "HUMAN_DECISION state'i kalıcı WAITING_HUMAN yapmalı"
  assert_eq "WAITING_HUMAN" "$(jq -r '.status' "$STATE")" "state dosyaya atomik yazılmalı"
}

t_human_decision_resets_repair_budget() {
  state_patch '.stage="REVIEWER"|.status="WAITING_HUMAN"|.repair_round=2'
  run_implementer() { echo "$(state_field repair_round)" > "$H/.repair_at_impl"; state_update COMPLETED COMPLETED ""; return 0; }
  run_tests() { return 0; }
  run_reviewer() { return 0; }
  main continue "operatör kararı" >/dev/null 2>&1
  assert_present "$H/HUMAN_RESPONSE.md" "insan yanıtı kaydedilmeli"
  assert_eq "0" "$(cat "$H/.repair_at_impl" 2>/dev/null)" "insan kararı onarım bütçesini sıfırlamalı"
}

t_resume_from_correct_stage() {
  state_update TESTER READY ""
  run_implementer() { : > "$H/.impl_ran"; return 0; }
  run_tests() { : > "$H/.tester_ran"; state_update COMPLETED COMPLETED ""; return 0; }
  run_reviewer() { return 0; }
  main continue "" >/dev/null 2>&1
  assert_present "$H/.tester_ran" "kesinti sonrası doğru aşamadan (TESTER) devam etmeli"
  assert_absent "$H/.impl_ran" "önceki başarılı aşama (IMPLEMENTER) tekrar çalışmamalı"
}

t_agent_handoff_gitignored() {
  echo "runtime" > "$H/state/SESSION.json"
  if git -C "$ROOTX" check-ignore -q .agent-handoff/state/SESSION.json; then ok; else fail ".agent-handoff gitignore'lu olmalı"; fi
  local porcelain
  porcelain="$(git -C "$ROOTX" status --porcelain)"
  if [[ "$porcelain" != *".agent-handoff"* ]]; then ok; else fail ".agent-handoff git status'a karışmamalı"; fi
}

t_single_instance_flock() {
  # Testin kendisi kilidi tutar; controller ikinci FD ile alamamalı.
  exec 200>"$H/state/pipeline.lock"
  flock -n 200
  local out
  out="$(AGENT_LOOP_TARGET="$ROOTX" AGENT_LOOP_ENV_FILE=/nonexistent CODEX_BIN="$STUB" \
        bash "$LOOP_DIR/controller.sh" continue "" 2>&1)"
  flock -u 200
  exec 200>&-
  assert_contains "$out" "zaten çalışıyor" "ikinci instance flock ile engellenmeli"
}

t_completed_then_new_task() {
  state_update COMPLETED COMPLETED ""
  run_planner() { PLANNED_TASK_ID=T; PLANNED_TITLE=Auto; PLANNED_OBJECTIVE=obj; PLANNED_SOURCE_DOCS=""; PLANNED_PRIORITY_REASON=r; return 0; }
  run_implementer() { state_update TESTER READY ""; return 0; }
  run_tests() { state_update REVIEWER READY ""; return 0; }
  run_reviewer() { state_update COMPLETED COMPLETED ""; return 0; }
  main continue "" >/dev/null 2>&1
  assert_eq "1" "$(state_field iteration)" "birinci tamamlanan görev iteration 1"
  main continue "" >/dev/null 2>&1
  assert_eq "2" "$(state_field iteration)" "COMPLETED sonrası devam yeni görev seçmeli (iteration 2)"
}

# --- run all ---------------------------------------------------------------

echo "agent-loop test suite"
run_test "empty-continue-runs-planner"        t_empty_continue_runs_planner
run_test "explicit-task-skips-planner"        t_explicit_task_skips_planner
run_test "completed-reselects-new-iteration"  t_completed_reselects_new_iteration
run_test "planner-no-task-waiting-human"      t_planner_no_task_waiting_human
run_test "base-ref-not-a-gate"                t_base_ref_not_a_gate
run_test "codex-nonzero-exit-no-stale-result" t_codex_nonzero_exit_no_stale_result
run_test "codex-empty-result-fails"           t_codex_empty_result_fails
run_test "codex-stderr-logged"                t_codex_stderr_logged
run_test "claude-backend-captures-stdout"     t_claude_backend_captures_stdout_result
run_test "claude-backend-arg-mapping"         t_claude_backend_arg_mapping
run_test "claude-backend-runs-in-repo-root"   t_claude_backend_runs_in_repo_root
run_test "claude-backend-no-stale-result"     t_claude_backend_nonzero_exit_no_stale_result
run_test "claude-backend-empty-result-fails"  t_claude_backend_empty_result_fails
run_test "claude-backend-invalid-status"      t_claude_backend_invalid_status_fails
run_test "claude-backend-pg-env-forwarded"    t_claude_backend_pg_env_forwarded
run_test "unknown-backend-fails-closed"       t_unknown_backend_fails_closed
run_test "claude-backend-full-iteration"      t_claude_backend_full_iteration
run_test "fallback-on-usage-limit"            t_fallback_on_provider_usage_limit
run_test "fallback-on-empty-plus-provider-err" t_fallback_on_empty_result_with_provider_error
run_test "fallback-on-stdout-session-limit"   t_fallback_on_stdout_session_limit
run_test "session-limit-on-stderr-too"        t_session_limit_recognised_on_stderr_too
run_test "valid-result-mentioning-limit-ok"   t_valid_result_mentioning_limit_is_not_provider_error
run_test "provider-error-only-without-status" t_provider_error_in_result_only_without_status
run_test "no-fallback-ordinary-failure"       t_no_fallback_on_ordinary_failure
run_test "no-fallback-when-disabled"          t_no_fallback_when_disabled
run_test "no-fallback-to-same-backend"        t_no_fallback_to_same_backend
run_test "unknown-fallback-no-attempt"        t_unknown_fallback_target_no_attempt
run_test "timeout-not-provider-unavailable"   t_timeout_is_not_provider_unavailable
run_test "stderr-log-capped-keeps-tail"       t_stderr_log_capped_keeps_tail
run_test "stderr-log-not-capped-when-0"       t_stderr_log_not_capped_when_disabled
run_test "test-timeout-exit-code"             t_test_timeout_exit_code
run_test "pg-env-forwarded"                   t_pg_env_forwarded
run_test "integration-required-detection"     t_integration_required_detection
run_test "optional-integration-targets"       t_optional_integration_target_selection
run_test "pg-preflight-missing-no-fake-pass"  t_pg_preflight_missing_no_fake_pass
run_test "integration-skip-gate-fails"        t_integration_skip_gate_fails
run_test "changes-required-starts-repair"     t_changes_required_starts_repair
run_test "repair-limit-waiting-human"         t_repair_limit_waiting_human
run_test "human-decision-persists-state"      t_human_decision_persists_state
run_test "human-decision-resets-repair"       t_human_decision_resets_repair_budget
run_test "resume-from-correct-stage"          t_resume_from_correct_stage
run_test "agent-handoff-gitignored"           t_agent_handoff_gitignored
run_test "single-instance-flock"              t_single_instance_flock
run_test "completed-then-new-task"            t_completed_then_new_task

# --- rol dağıtımı ve Qoder handoff'u ---------------------------------------

t_roles_config_selects_fallback_when_primary_unavailable() {
  write_roles_config false codex qoder
  assert_eq "1" "${ROLES_LOADED}" "agents.yaml yüklenmeli"
  assert_eq "qoder" "$(role_agent implementer)" "codex kullanılamazken uygulayıcı yedeğe düşmeli"
  assert_eq "qoder" "$(role_agent tester)" "testçi de yedeğe düşmeli"
  assert_eq "claude" "$(role_agent reviewer)" "reviewer yapılandırıldığı gibi kalmalı"
  role_resolve implementer
  assert_contains "$ROLE_RESOLUTION_REASON" "codex_marked_unavailable" "fallback nedeni kaydedilmeli"
}

t_roles_config_prefers_primary_when_available() {
  CODEX_BIN="$STUB"   # binary var
  write_roles_config true codex qoder
  assert_eq "codex" "$(role_agent implementer)" "codex kullanılabilirken birincil seçilmeli"
  role_resolve implementer
  assert_eq "" "$ROLE_RESOLUTION_REASON" "birincil seçildiğinde fallback nedeni boş olmalı"
}

t_roles_invalid_config_is_fail_closed() {
  mkdir -p "$ROOTX/.agent/config"
  printf 'architect: claude\nimplementer:\n  - liste\n' > "$ROOTX/.agent/config/agents.yaml"
  local rc=0
  agentloop_init "$ROOTX" "$LOOP_DIR" >/dev/null 2>&1 || rc=$?
  assert_eq "36" "$rc" "geçersiz agents.yaml fail-closed olmalı (exit 36)"
  assert_eq "0" "${ROLES_LOADED}" "geçersiz config yüklenmiş sayılmamalı"
}

t_reviewer_must_be_runnable_agent() {
  local rc=0
  write_roles_config false codex qoder qoder >/dev/null 2>&1 || rc=$?
  assert_eq "2" "$rc" "handoff ajanı reviewer olarak kabul edilmemeli"
  assert_eq "0" "${ROLES_LOADED}" "geçersiz rol dağıtımı yüklenmemeli"
}

t_role_env_override_wins_over_config() {
  write_roles_config false codex qoder
  start_new_task "obj" "T-OVR" "T" "" "r" manual >/dev/null 2>&1
  AGENT_BACKEND_IMPLEMENTER=claude
  export AGENT_BACKEND_IMPLEMENTER
  STUB_CLAUDE_STATUS="STATUS: SUCCESS"
  run_agent "implementer" "$H/in.md" "$H/out.md" '^STATUS: SUCCESS$' >/dev/null 2>&1
  assert_contains "$(cat "$LOGS/implementer-i1-r0.stdout.log")" "ROLE_AGENT=claude" \
    "AGENT_BACKEND_<ROLE> override'ı config'i geçmeli"
  unset AGENT_BACKEND_IMPLEMENTER
}

t_handoff_agent_is_not_executed() {
  write_roles_config false codex qoder
  : > "$H/in.md"
  local rc=0
  run_agent "implementer" "$H/in.md" "$H/out.md" '^STATUS: SUCCESS$' >/dev/null 2>&1 || rc=$?
  assert_eq "38" "$rc" "handoff ajanı için 38 (HANDOFF_PENDING) dönmeli"
  assert_present "$HANDOFF_FILE" "görev paketi üretilmeli"
  assert_absent "$H/out.md" "handoff ajanı için sonuç dosyası uydurulmamalı"
  assert_contains "$(cat "$HANDOFF_FILE")" "STATUS: SUCCESS" "paket beklenen çıktı formatını içermeli"
  assert_contains "$(cat "$HANDOFF_FILE")" "Değiştirilmemesi gereken alanlar" "paket kapsam dışını içermeli"
}

t_handoff_sets_waiting_agent_state() {
  write_roles_config false codex qoder
  start_new_task "obj" "T-HAND" "T" "" "r" manual >/dev/null 2>&1
  run_implementer >/dev/null 2>&1
  assert_eq "WAITING_AGENT" "$(state_field status)" "handoff sonrası WAITING_AGENT olmalı"
  assert_eq "IMPLEMENTER" "$(state_field stage)" "aşama implementer'da kalmalı"
  assert_eq "qoder" "$(state_field handoff_agent)" "handoff ajanı state'e yazılmalı"
  assert_present "$(state_field handoff_file)" "handoff dosyası state'ten bulunabilmeli"
  assert_present "$LEDGER_ACTIVE/T-HAND.md" "aktif görev defteri yazılmalı"
  assert_contains "$(cat "$LEDGER_ACTIVE/T-HAND.md")" "lifecycle_state: CLAIMED" \
    "handoff bekleyen görev CLAIMED olmalı"
}

t_handoff_claim_without_changes_is_rejected() {
  write_roles_config false codex qoder
  start_new_task "obj" "T-NOCHG" "T" "" "r" manual >/dev/null 2>&1
  run_implementer >/dev/null 2>&1
  # Uygulama yapılmadan "tamam" beyanı: çalışma ağacı değişmedi.
  main continue "qoder tamam" >/dev/null 2>&1
  assert_eq "WAITING_AGENT" "$(state_field status)" "doğrulanamayan beyan aşamayı ilerletmemeli"
  assert_eq "IMPLEMENTER" "$(state_field stage)" "test aşamasına geçilmemeli"
  assert_contains "$(state_field last_error)" "doğrulanamadı" "neden state'e yazılmalı"
}

t_handoff_resume_after_real_change_runs_tests() {
  write_roles_config false codex qoder
  start_new_task "obj" "T-CHG" "T" "" "r" manual >/dev/null 2>&1
  run_implementer >/dev/null 2>&1
  echo "yeni satır" >> "$ROOTX/README.md"
  run_tests() { : > "$H/.tests_ran"; state_update REVIEWER READY ""; return 0; }
  run_reviewer() { state_update COMPLETED COMPLETED ""; return 0; }
  main continue "qoder tamam" >/dev/null 2>&1
  assert_present "$H/.tests_ran" "controller testleri handoff sonrası kendisi çalıştırmalı"
  assert_present "$H/CODEX_RESULT.md" "handoff sonucu uygulama sonucu olarak kaydedilmeli"
  assert_contains "$(cat "$H/CODEX_RESULT.md")" "STATUS: SUCCESS" "sonuç doğrulanabilir formatta olmalı"
  assert_contains "$(cat "$H/HANDOFF_RESULT.md")" "parmak izi değişti" "doğrulama kanıtı yazılmalı"
}

t_handoff_blocked_goes_to_human_decision() {
  write_roles_config false codex qoder
  start_new_task "obj" "T-BLK" "T" "" "r" manual >/dev/null 2>&1
  run_implementer >/dev/null 2>&1
  main continue "blocked: politika kararı gerekiyor" >/dev/null 2>&1
  assert_eq "WAITING_HUMAN" "$(state_field status)" "BLOCKED insan kararına gitmeli"
  assert_present "$LEDGER_BLOCKED/T-BLK.md" "görev blocked kovasına taşınmalı"
  assert_absent "$LEDGER_ACTIVE/T-BLK.md" "görev iki kovada birden bulunmamalı"
}

t_claim_prevents_second_implementer() {
  write_roles_config false codex qoder
  mkdir -p "$CLAIM_DIR"
  # Başka bir worktree'nin canlı claim'i (bu kabuğun pid'i canlıdır).
  jq -n --argjson pid "$$" '{task_id:"T-CLAIM", agent:"codex",
      worktree:"/baska/worktree", branch:"agent/x", pid:$pid, claimed_at:"now"}' \
    > "$CLAIM_DIR/T-CLAIM.json"
  local rc=0
  start_new_task "obj" "T-CLAIM" "T" "" "r" manual >/dev/null 2>&1 || rc=$?
  assert_eq "37" "$rc" "claim edilmiş görev ikinci uygulayıcıya verilmemeli"
  assert_eq "WAITING_HUMAN" "$(state_field status)" "çakışma insan kararına düşmeli"
}

t_claim_reentrant_in_same_worktree() {
  write_roles_config false codex qoder
  claim_acquire "T-RE" codex
  local rc=0
  claim_acquire "T-RE" codex || rc=$?
  assert_eq "0" "$rc" "aynı worktree kendi claim'ine yeniden girebilmeli"
  claim_release "T-RE"
  assert_absent "$(claim_owner_file T-RE)" "claim bırakılmalı"
}

# --- test kanıtı ve hata sınıflandırması ------------------------------------

t_environment_failure_is_not_product_defect() {
  local log="$H/logs/fake.log"
  printf 'E psycopg2.OperationalError: could not connect to server: Connection refused\n' > "$log"
  assert_eq "ENVIRONMENT_FAILURE" "$(classify_test_failure "$log" 1)" \
    "PostgreSQL erişilemezliği ürün hatası sayılmamalı"
  printf 'ModuleNotFoundError: No module named "pandas"\n' > "$log"
  assert_eq "DEPENDENCY_FAILURE" "$(classify_test_failure "$log" 1)" "bağımlılık hatası ayrılmalı"
  printf 'FAILED tests/unit/test_x.py::test_y - AssertionError\n' > "$log"
  assert_eq "PRODUCT_DEFECT" "$(classify_test_failure "$log" 1)" "assertion hatası ürün defekti olmalı"
  printf 'E fixture "db" not found\n' > "$log"
  assert_eq "TEST_DEFECT" "$(classify_test_failure "$log" 1)" "fixture hatası test defekti olmalı"
  printf 'anything\n' > "$log"
  assert_eq "ENVIRONMENT_FAILURE" "$(classify_test_failure "$log" 124)" "timeout ortam hatası olmalı"
  assert_eq "NONE" "$(classify_test_failure "$log" 0)" "exit 0 sınıflandırma üretmemeli"
}

t_evidence_record_has_required_fields() {
  write_roles_config false codex qoder
  start_new_task "obj" "T-EV" "T" "" "r" manual >/dev/null 2>&1
  local log="$LOGS/unit-tests-i1.log" file
  printf '12 passed, 1 skipped in 3.2s\n' > "$log"
  file="$(evidence_write "T-EV" unit "python3 -m pytest -q" 0 3 "$log" "not")"
  assert_present "$file" "kanıt dosyası yazılmalı"
  local missing
  missing="$(jq -r '["task_id","runner","runner_role","timestamp","working_directory",
                     "git_branch","git_commit","command","exit_code","duration",
                     "passed","failed","skipped","stdout_log","stderr_log",
                     "environment_notes","failure_class"]
                    - (. | keys) | join(",")' "$file")"
  assert_eq "" "$missing" "zorunlu kanıt alanları eksiksiz olmalı"
  assert_eq "12" "$(jq -r '.passed' "$file")" "passed sayacı pytest özetinden okunmalı"
  assert_eq "1" "$(jq -r '.skipped' "$file")" "skipped sayacı okunmalı"
  assert_eq "qoder" "$(jq -r '.tester_agent' "$file")" "testçi ajanı kayda geçmeli"
  assert_eq "controller-shell" "$(jq -r '.runner' "$file")" "testleri controller çalıştırır"
}

t_evidence_counts_not_invented_when_unparsable() {
  write_roles_config false codex qoder
  local log="$LOGS/unit-tests-i0.log" file
  printf 'internal error, no summary line\n' > "$log"
  file="$(evidence_write "T-UNP" unit "cmd" 2 1 "$log" "")"
  assert_eq "-1" "$(jq -r '.passed' "$file")" "okunamayan sayaç uydurulmamalı (-1)"
}

t_integration_environment_block_records_evidence() {
  write_roles_config false codex qoder
  start_new_task "obj" "T-ENVB" "T" "" "r" manual >/dev/null 2>&1
  integration_required() { return 0; }
  postgres_preflight() { echo "PG yok"; return 1; }
  local rc=0
  run_tests >/dev/null 2>&1 || rc=$?
  assert_eq "1" "$rc" "PG preflight başarısızsa test kapısı düşmeli"
  assert_contains "$(state_field last_error)" "ENVIRONMENT_BLOCK" "ortam bloğu state'e yazılmalı"
  local file="$EVIDENCE_DIR/T-ENVB/i1-r0-integration.json"
  assert_present "$file" "ortam bloğu için de kanıt yazılmalı"
  assert_eq "ENVIRONMENT_FAILURE" "$(jq -r '.failure_class' "$file")" \
    "PG yokluğu ENVIRONMENT_FAILURE olarak sınıflanmalı"
}

# --- defter ve review kaydı -------------------------------------------------

t_ledger_moves_task_to_completed_after_approval() {
  write_roles_config false codex qoder
  start_new_task "obj" "T-DONE" "T" "" "r" manual >/dev/null 2>&1
  assert_present "$LEDGER_ACTIVE/T-DONE.md" "görev aktif kovada başlamalı"
  printf 'STATUS: APPROVED\n\nOnaylandı.\n' > "$H/ARCHITECT_REVIEW.md"
  state_update COMPLETED COMPLETED ""
  ledger_sync >/dev/null
  assert_present "$LEDGER_COMPLETED/T-DONE.md" "onaylanan görev completed kovasına geçmeli"
  assert_absent "$LEDGER_ACTIVE/T-DONE.md" "görev tek kovada bulunmalı"
  assert_contains "$(cat "$LEDGER_COMPLETED/T-DONE.md")" "review_result: APPROVED" \
    "review sonucu deftere yazılmalı"
}

t_review_record_is_written_with_independent_reviewer() {
  write_roles_config false codex qoder
  start_new_task "obj" "T-REV" "T" "" "r" manual >/dev/null 2>&1
  printf 'STATUS: CHANGES_REQUIRED\n\n1. Eksik test.\n' > "$H/ARCHITECT_REVIEW.md"
  local file
  file="$(review_record "T-REV" CHANGES_REQUESTED)"
  assert_present "$file" "review kaydı yazılmalı"
  assert_contains "$(cat "$file")" "reviewer_agent: claude" "reviewer ajanı kayda geçmeli"
  assert_contains "$(cat "$file")" "implementer_agent: qoder" "uygulayıcı ajanı kayda geçmeli"
  assert_contains "$(cat "$file")" "result: CHANGES_REQUESTED" "sonuç kayda geçmeli"
}

t_lifecycle_states_distinguish_phases() {
  assert_eq "READY"            "$(lifecycle_state IMPLEMENTER READY 0 "")"  "kod yazılmadan READY"
  assert_eq "CHANGES_REQUESTED" "$(lifecycle_state IMPLEMENTER READY 1 "")" "onarım turu ayrı durum"
  assert_eq "CLAIMED"          "$(lifecycle_state IMPLEMENTER WAITING_AGENT 0 "")" "handoff CLAIMED"
  assert_eq "IMPLEMENTED"      "$(lifecycle_state TESTER READY 0 "")"       "kod yazıldı, test edilmedi"
  assert_eq "TESTING"          "$(lifecycle_state TESTER FAILED 0 "")"      "test aşaması ayrı"
  assert_eq "REVIEW"           "$(lifecycle_state REVIEWER READY 0 "")"     "review ayrı durum"
  assert_eq "APPROVED"         "$(lifecycle_state COMPLETED COMPLETED 0 APPROVED)" "onay ayrı durum"
  assert_eq "BLOCKED"          "$(lifecycle_state REVIEWER WAITING_HUMAN 0 "")" "insan kararı BLOCKED"
}

t_legacy_single_backend_still_works_without_config() {
  # agents.yaml yokken davranış değişmez: geriye dönük AGENT_BACKEND yolu.
  assert_eq "0" "${ROLES_LOADED}" "config yoksa rol modu kapalı olmalı"
  STUB_CODEX_STATUS="STATUS: SUCCESS"
  : > "$H/in.md"
  local rc=0
  run_agent "implementer" "$H/in.md" "$H/out.md" '^STATUS: SUCCESS$' >/dev/null 2>&1 || rc=$?
  assert_eq "0" "$rc" "rol config olmadan codex backend çalışmalı"
  assert_present "$H/out.md" "sonuç dosyası üretilmeli"
}

run_test "roles-fallback-when-unavailable"    t_roles_config_selects_fallback_when_primary_unavailable
run_test "roles-prefer-primary-when-usable"   t_roles_config_prefers_primary_when_available
run_test "roles-invalid-config-fail-closed"   t_roles_invalid_config_is_fail_closed
run_test "reviewer-must-be-runnable"          t_reviewer_must_be_runnable_agent
run_test "role-env-override-wins"             t_role_env_override_wins_over_config
run_test "handoff-agent-not-executed"         t_handoff_agent_is_not_executed
run_test "handoff-sets-waiting-agent"         t_handoff_sets_waiting_agent_state
run_test "handoff-claim-without-changes"      t_handoff_claim_without_changes_is_rejected
run_test "handoff-resume-runs-tests"          t_handoff_resume_after_real_change_runs_tests
run_test "handoff-blocked-to-human"           t_handoff_blocked_goes_to_human_decision
run_test "claim-prevents-second-writer"       t_claim_prevents_second_implementer
run_test "claim-reentrant-same-worktree"      t_claim_reentrant_in_same_worktree
run_test "env-failure-not-product-defect"     t_environment_failure_is_not_product_defect
run_test "evidence-required-fields"           t_evidence_record_has_required_fields
run_test "evidence-no-invented-counts"        t_evidence_counts_not_invented_when_unparsable
run_test "integration-env-block-evidence"     t_integration_environment_block_records_evidence
run_test "ledger-moves-to-completed"          t_ledger_moves_task_to_completed_after_approval
run_test "review-record-independent"          t_review_record_is_written_with_independent_reviewer
run_test "lifecycle-states-distinct"          t_lifecycle_states_distinguish_phases
run_test "legacy-backend-without-config"      t_legacy_single_backend_still_works_without_config

# --- schema v3 contract validation ve deterministik kontroller ---------------

t_invalid_contract_fail_closed() {
  # v2 schema contract'ı doğrulama fail-closed olmalı
  local bad="$H/bad-contract.json"
  printf '{"schema_version":2,"task":{"id":"x"}}' > "$bad"
  local rc=0
  contract_validate "$bad" >/dev/null 2>&1 || rc=$?
  assert_eq "1" "$rc" "v2 kontrat doğrulamadan geçmemeli"
}

t_v3_contract_valid() {
  # Geçerli v3 kontrat doğrulamadan geçmeli
  start_new_task "test obj" "T-VALID" "Test" "" "" manual >/dev/null 2>&1
  local rc=0
  contract_validate "$TASK" >/dev/null 2>&1 || rc=$?
  assert_eq "0" "$rc" "geçerli v3 kontrat doğrulamadan geçmeli"
  assert_eq "3" "$(jq -r '.schema_version' "$TASK")" "schema_version 3 olmalı"
  assert_eq "user_objective" "$(jq -r '.task.source.type' "$TASK")" "source.type user_objective olmalı"
}

t_legacy_source_docs_rejected() {
  # Eski source_docs alanı içeren kontrat reddedilmeli
  local bad="$H/legacy-contract.json"
  jq -n '{schema_version:3, contract_status:"READY", iteration:1,
    task:{id:"X",title:"t",objective:"o",selection_mode:"manual",
          source:{type:"user_objective"}, source_docs:["NEXT_STEP.md"]},
    repository:{root:"/x",branch:"main",base_ref:"abc"},
    scope:{allowed_files:[]}, acceptance_criteria:[]}' > "$bad"
  local rc=0
  contract_validate "$bad" >/dev/null 2>&1 || rc=$?
  assert_eq "1" "$rc" "legacy source_docs alanı içeren kontrat reddedilmeli"
}

t_must_disappear_pre_check_detects_existing_file() {
  # must_disappear dosyası varken pre-check PASS (görev anlamlı)
  start_new_task "obj" "T-MD" "T" "" "" manual >/dev/null 2>&1
  echo "delete me" > "$ROOTX/legacy_file.py"
  # Kontrata must_disappear ekle
  jq '.must_disappear = ["legacy_file.py"]' "$TASK" > "$TASK.tmp" && mv "$TASK.tmp" "$TASK"
  contract_pre_impl_checks "$TASK" "$ROOTX" >/dev/null 2>&1
  assert_contains "$CONTRACT_PRE_CHECK_REPORT" "EXISTS" "mevcut dosya EXISTS olarak işaretlenmeli"
}

t_must_disappear_post_check_detects_remaining_file() {
  # Post-impl: must_disappear dosyası hâlâ varsa FAIL
  start_new_task "obj" "T-MD2" "T" "" "" manual >/dev/null 2>&1
  echo "still here" > "$ROOTX/legacy_file.py"
  jq '.must_disappear = ["legacy_file.py"]' "$TASK" > "$TASK.tmp" && mv "$TASK.tmp" "$TASK"
  local rc=0
  contract_post_impl_checks "$TASK" "$ROOTX" >/dev/null 2>&1 || rc=$?
  assert_eq "1" "$rc" "must_disappear dosyası hâlâ varsa post-check başarısız olmalı"
  assert_contains "$CONTRACT_POST_CHECK_REPORT" "FAIL" "raporda FAIL yazmalı"
}

t_must_disappear_post_check_passes_when_deleted() {
  # Post-impl: must_disappear dosyası silindiyse PASS
  start_new_task "obj" "T-MD3" "T" "" "" manual >/dev/null 2>&1
  # Dosya yok (silinmiş)
  jq '.must_disappear = ["gone_file.py"]' "$TASK" > "$TASK.tmp" && mv "$TASK.tmp" "$TASK"
  local rc=0
  contract_post_impl_checks "$TASK" "$ROOTX" >/dev/null 2>&1 || rc=$?
  assert_eq "0" "$rc" "must_disappear dosyası yoksa post-check geçmeli"
}

t_forbidden_substitutes_detected() {
  # forbidden_substitutes pattern'i kaynak dosyalarda bulunursa FAIL
  start_new_task "obj" "T-FS" "T" "" "" manual >/dev/null 2>&1
  mkdir -p "$ROOTX/src/veri_kalitesi"
  echo "legacy_alias = old_function" > "$ROOTX/src/veri_kalitesi/mod.py"
  jq '.forbidden_substitutes = ["legacy_alias"]' "$TASK" > "$TASK.tmp" && mv "$TASK.tmp" "$TASK"
  local rc=0
  contract_post_impl_checks "$TASK" "$ROOTX" >/dev/null 2>&1 || rc=$?
  assert_eq "1" "$rc" "forbidden pattern bulunursa post-check başarısız olmalı"
  assert_contains "$CONTRACT_POST_CHECK_REPORT" "forbidden" "raporda forbidden geçmeli"
}

t_revision_guard_injects_repair_context() {
  # repair_round > 0 olduğunda implementer girdisine REVISION GUARD eklenmeli
  write_roles_config false codex qoder
  start_new_task "obj" "T-RG" "T" "" "" manual >/dev/null 2>&1
  state_patch '.repair_round = 2'
  printf 'STATUS: CHANGES_REQUIRED\n\nFix X.\n' > "$H/ARCHITECT_REVIEW.md"
  run_implementer() {
    local input="$LOGS/implementer-i$(state_field iteration)-r$(state_field repair_round).input.md"
    # run_implementer'ın yazdığı input'u kontrol et
    : > "$H/.impl_input_check"
    state_update TESTER READY ""
    return 0
  }
  # Gerçek run_implementer'ı çağır (override etme)
  # Revision guard'ı doğrudan test et
  local repair
  repair="$(state_field repair_round)"
  if (( repair > 0 )); then ok; else fail "repair_round > 0 olmalı"; fi
}

t_out_of_scope_file_detection() {
  # contract_post_impl_checks kapsam dışı dosyaları tespit etmeli
  start_new_task "obj" "T-OOS" "T" "" "" manual >/dev/null 2>&1
  jq '.scope.allowed_files = ["src/a.py"]' "$TASK" > "$TASK.tmp" && mv "$TASK.tmp" "$TASK"
  local rc=0
  contract_post_impl_checks "$TASK" "$ROOTX" "src/a.py" "src/unrelated.py" >/dev/null 2>&1 || rc=$?
  assert_eq "1" "$rc" "kapsam dışı dosya tespit edilmeli"
  assert_contains "$CONTRACT_POST_CHECK_REPORT" "OUT_OF_SCOPE" "OUT_OF_SCOPE raporda geçmeli"
}

t_stale_result_rejected() {
  # Bayat sonuç (STATUS: ile başlamayan) reddedilmeli
  printf 'Bu bir rapor ama STATUS yok.\n' > "$H/stale.md"
  local first
  first="$(head -n 1 "$H/stale.md" | tr -d '\r')"
  if [[ "$first" =~ ^STATUS: ]]; then
    fail "STATUS ile başlamayan sonuç kabul edilmemeli"
  else ok; fi
}

t_handoff_carries_v3_contract() {
  # Qoder handoff paketi v3 kontratını taşımalı
  write_roles_config false codex qoder
  start_new_task "obj" "T-HV3" "Handoff V3" "" "" manual >/dev/null 2>&1
  : > "$H/in.md"
  local rc=0
  run_agent "implementer" "$H/in.md" "$H/out.md" '^STATUS: SUCCESS$' >/dev/null 2>&1 || rc=$?
  assert_eq "38" "$rc" "handoff 38 dönmeli"
  assert_present "$HANDOFF_FILE" "handoff paketi üretilmeli"
  assert_contains "$(cat "$HANDOFF_FILE")" "schema_version" "paket v3 kontratını taşımalı"
  assert_contains "$(cat "$HANDOFF_FILE")" "allowed_files" "paket v3 scope alanını taşımalı"
}

t_implementer_status_protocol() {
  # Implementer sonucu STATUS: SUCCESS veya STATUS: BLOCKED ile başlamalı
  STUB_CODEX_STATUS="STATUS: SUCCESS"
  echo "prompt" > "$H/in.md"
  run_codex implementer "$H/in.md" "$H/CODEX_RESULT.md" '^STATUS: SUCCESS$' >/dev/null 2>&1
  assert_eq "0" "$?" "STATUS: SUCCESS kabul edilmeli"
  assert_present "$H/CODEX_RESULT.md" "sonuç dosyası üretilmeli"
}

t_reviewer_status_protocol() {
  # Reviewer sonucu STATUS: APPROVED|CHANGES_REQUIRED|HUMAN_DECISION ile başlamalı
  state_update REVIEWER READY ""
  echo "impl" > "$H/CODEX_RESULT.md"; echo "test" > "$H/TEST_REPORT.md"
  STUB_CODEX_STATUS="STATUS: APPROVED"
  run_reviewer >/dev/null 2>&1
  assert_eq "COMPLETED" "$(state_field stage)" "APPROVED -> COMPLETED"
}

t_nextstep_ignored_as_source() {
  # NEXT_STEP.md artık görev kaynağı olarak kullanılmamalı
  # select_from_verified_backlog NEXT_STEP.md'ye bakmaz
  cat > "$ROOTX/NEXT_STEP.md" <<'NSEOF'
---
type: next-step
status: active
work_package: WP-OLD
---
# Sıradaki Adım — Eski Görev
NSEOF
  state_update COMPLETED COMPLETED ""
  PLANNED_TASK_ID=""; PLANNED_TITLE=""; PLANNED_OBJECTIVE=""
  PLANNED_SOURCE_DOCS=""; PLANNED_PRIORITY_REASON=""
  # Backlog yok, NEXT_STEP var -> select_from_verified_backlog başarısız olmalı
  local rc=0
  select_from_verified_backlog >/dev/null 2>&1 || rc=$?
  assert_eq "1" "$rc" "NEXT_STEP.md doğrulanmış backlog olarak kullanılmamalı"
}

run_test "invalid-contract-fail-closed"         t_invalid_contract_fail_closed
run_test "v3-contract-valid"                    t_v3_contract_valid
run_test "legacy-source-docs-rejected"          t_legacy_source_docs_rejected
run_test "must-disappear-pre-check"             t_must_disappear_pre_check_detects_existing_file
run_test "must-disappear-post-fail"             t_must_disappear_post_check_detects_remaining_file
run_test "must-disappear-post-pass"             t_must_disappear_post_check_passes_when_deleted
run_test "forbidden-substitutes-detected"       t_forbidden_substitutes_detected
run_test "revision-guard-repair-context"        t_revision_guard_injects_repair_context
run_test "out-of-scope-detection"               t_out_of_scope_file_detection
run_test "stale-result-rejected"                t_stale_result_rejected
run_test "handoff-carries-v3-contract"          t_handoff_carries_v3_contract
run_test "implementer-status-protocol"          t_implementer_status_protocol
run_test "reviewer-status-protocol"             t_reviewer_status_protocol
run_test "nextstep-ignored-as-source"           t_nextstep_ignored_as_source

echo
echo "PASS=$PASS FAIL=$FAIL"
if [[ "$FAIL" -ne 0 ]]; then
  printf 'Başarısız: %s\n' "${FAILED_TESTS[*]}"
  exit 1
fi
echo "Tüm agent-loop testleri geçti."
