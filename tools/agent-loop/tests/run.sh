#!/usr/bin/env bash
# tools/agent-loop/tests/run.sh
#
# Agent-loop controller smoke/integration test suite. Gerçek Codex ve gerçek pytest
# ÇAĞRILMAZ: fresh `codex exec` bir stub ile, test kapıları ise fonksiyon override'ı
# ile taklit edilir. Her test kendi geçici repo'sunda izole çalışır.
set -uo pipefail

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOOP_DIR="$(cd "$TESTS_DIR/.." && pwd)"
STUB="$TESTS_DIR/stubs/codex"
chmod +x "$STUB" 2>/dev/null || true

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
  mkdir -p "$d/03-Backend/src/veri_kalitesi" "$d/05-Veritabani" \
           "$d/06-Testler/01-Birim" "$d/06-Testler/02-Entegrasyon"
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
  MAX_REPAIR_ROUNDS=2
  TEST_TIMEOUT_SECONDS=900
  CODEX_STAGE_TIMEOUT_SECONDS=60
  unset STUB_CODEX_EXIT STUB_CODEX_EMPTY STUB_CODEX_ECHO_PG STUB_CODEX_STATUS STUB_CODEX_BODY
  # run_codex stub'ı `env` ile başlatır; kontrol değişkenleri export edilmeli ki
  # alt sürece ulaşsın. Export attribute'u sonraki atamalarda korunur.
  export STUB_CODEX_EXIT STUB_CODEX_EMPTY STUB_CODEX_ECHO_PG STUB_CODEX_STATUS STUB_CODEX_BODY
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
  assert_eq "[]" "$(jq -c '.scope.files' "$TASK")" "yeni kontrat dosya kapsamı taşımaz"
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
  echo "x" > "$ROOTX/06-Testler/01-Birim/test_x.py"
  if integration_required; then fail "yalnız unit değişikliği entegrasyon gerektirmemeli"; else ok; fi
  # backend/veritabanı dokümanı değişikliği -> gerekmez
  echo "doc" > "$ROOTX/03-Backend/BACKEND-INDEX.md"
  echo "doc" > "$ROOTX/05-Veritabani/VERITABANI-INDEX.md"
  if integration_required; then fail "doküman değişikliği entegrasyon gerektirmemeli"; else ok; fi
  # Alembic değişikliği -> gerekir
  mkdir -p "$ROOTX/05-Veritabani/alembic/versions"
  echo "migration" > "$ROOTX/05-Veritabani/alembic/versions/x.py"
  if integration_required; then ok; else fail "migration değişikliği entegrasyon gerektirmeli"; fi
  rm -f "$ROOTX/05-Veritabani/alembic/versions/x.py"
  # src değişikliği -> gerekir
  echo "y" > "$ROOTX/03-Backend/src/veri_kalitesi/z.py"
  if integration_required; then ok; else fail "src değişikliği entegrasyon gerektirmeli"; fi
}

t_optional_integration_target_selection() {
  local targets
  echo "y" > "$ROOTX/03-Backend/src/veri_kalitesi/z.py"
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
  echo "y" > "$ROOTX/03-Backend/src/veri_kalitesi/z.py"   # integration_required -> true
  run_logged_test() { : > "$1"; echo "1 passed" >> "$1"; return 0; }  # unit passes
  DATA_QUALITY_POSTGRES_TEST_URL=""   # preflight fails
  run_tests >/dev/null 2>&1
  assert_eq "FAILED" "$(state_field status)" "PG yoksa sahte PASS olmamalı"
  assert_contains "$(state_field last_error)" "ENVIRONMENT_BLOCK" "hata ENVIRONMENT_BLOCK olmalı"
}

t_integration_skip_gate_fails() {
  echo "y" > "$ROOTX/03-Backend/src/veri_kalitesi/z.py"
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

write_next_step() { # work_package title extra_py_link
  cat > "$ROOTX/NEXT_STEP.md" <<EOF
---
type: next-step
status: active
work_package: $1
---

# Sıradaki Adım — $2

## Kapsam
- [kod](03-Backend/src/veri_kalitesi/jobs/worker.py) üzerinde çalış.
EOF
}

t_deterministic_planner_selects_from_nextstep() {
  write_next_step "WP-NEXT" "İş yürütme yaşam döngüsü"
  state_update COMPLETED COMPLETED ""
  run_planner() { : > "$H/.planner_ran"; return 0; }
  run_implementer() { state_update TESTER READY ""; return 0; }
  run_tests() { state_update REVIEWER READY ""; return 0; }
  run_reviewer() { state_update COMPLETED COMPLETED ""; return 0; }
  main continue "" >/dev/null 2>&1
  assert_absent "$H/.planner_ran" "NEXT_STEP güncelken LLM planner çağrılmamalı (0 token)"
  assert_eq "automatic" "$(jq -r '.task.selection_mode' "$TASK")" "mod automatic olmalı"
  assert_eq "WP-NEXT" "$(jq -r '.task.source_work_package' "$TASK")" "work_package kontrata yazılmalı"
  assert_contains "$(jq -r '.scope.hint | join(",")' "$TASK")" "worker.py" "scope hint NEXT_STEP linkinden çıkmalı"
}

t_deterministic_planner_guard_stale_falls_back() {
  # Son tamamlanan görev WP-SAME iken NEXT_STEP hâlâ WP-SAME gösteriyor => bayat.
  SELECTED_WORK_PACKAGE="WP-SAME"
  start_new_task "obj" "WP-SAME" "T" "" "r" automatic >/dev/null 2>&1
  SELECTED_WORK_PACKAGE=""
  write_next_step "WP-SAME" "Aynı iş paketi"
  state_update COMPLETED COMPLETED ""
  run_planner() { : > "$H/.planner_ran"; PLANNED_TASK_ID=X; PLANNED_TITLE=X; PLANNED_OBJECTIVE=x; PLANNED_SOURCE_DOCS=""; PLANNED_PRIORITY_REASON=r; return 0; }
  run_implementer() { state_update TESTER READY ""; return 0; }
  run_tests() { state_update REVIEWER READY ""; return 0; }
  run_reviewer() { state_update COMPLETED COMPLETED ""; return 0; }
  main continue "" >/dev/null 2>&1
  assert_present "$H/.planner_ran" "bayat NEXT_STEP (tamamlanan görevle aynı wp) LLM planner'a düşmeli"
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
run_test "deterministic-planner-selects"      t_deterministic_planner_selects_from_nextstep
run_test "deterministic-planner-guard-stale"  t_deterministic_planner_guard_stale_falls_back
run_test "completed-then-new-task"            t_completed_then_new_task

echo
echo "PASS=$PASS FAIL=$FAIL"
if [[ "$FAIL" -ne 0 ]]; then
  printf 'Başarısız: %s\n' "${FAILED_TESTS[*]}"
  exit 1
fi
echo "Tüm agent-loop testleri geçti."
