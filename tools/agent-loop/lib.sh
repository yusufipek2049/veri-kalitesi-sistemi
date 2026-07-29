#!/usr/bin/env bash
# tools/agent-loop/lib.sh
#
# Kalıcı agent-loop controller kütüphanesi. Bu dosya SIDE-EFFECT ÜRETMEZ:
# yalnız fonksiyon tanımlar. Çağıran (controller.sh veya testler) önce
# `agentloop_init <repo-root> <tools-dir>` çağırır, sonra fonksiyonları kullanır.
#
# Tasarım ilkeleri:
#   - Kalıcı/kaynak kod burada (tools/agent-loop, Git'te izlenir).
#   - Runtime state, log ve prompt snapshot'ları .agent-handoff altında üretilir
#     (Git tarafından ignore edilir; canonical bilgi kaynağı DEĞİLDİR).
#   - Her agent aşaması fresh `codex exec` ile başlar; eski session resume edilmez.
#   - Geniş testler controller kabuğunda çalışır, Codex process'ine bağlanmaz.
#   - State atomik (mktemp + mv) yazılır; tek instance flock ile korunur.
#
# shellcheck shell=bash

# --- init ------------------------------------------------------------------

agentloop_init() {
  ROOT="$1"
  TOOLS_DIR="$2"

  H="$ROOT/.agent-handoff"
  STATE="$H/state/SESSION.json"
  TASK="$H/CURRENT_TASK.json"
  SRC_PROMPTS="$TOOLS_DIR/prompts"
  PROMPTS="$H/prompts"
  LOGS="$H/logs"

  mkdir -p "$LOGS" "$H/state" "$PROMPTS"

  # Kaynak (izlenen) promptları runtime snapshot'ına kopyala: agent girdisi
  # her zaman izlenen kaynaktan üretilir, elle düzenlenmiş runtime kopyasından
  # değil.
  if [[ -d "$SRC_PROMPTS" ]]; then
    cp -f "$SRC_PROMPTS"/*.md "$PROMPTS"/ 2>/dev/null || true
  fi

  # Yapılandırma varsayılanları (env veya env-file ile override edilebilir).
  : "${TEST_TIMEOUT_SECONDS:=900}"
  : "${CODEX_STAGE_TIMEOUT_SECONDS:=2700}"
  : "${MAX_REPAIR_ROUNDS:=1}"
  : "${HUMAN_WAIT_SECONDS:=600}"
  : "${CODEX_BIN:=codex}"
  : "${UNIT_TEST_DIR:=06-Testler/01-Birim}"
  : "${INTEGRATION_TEST_DIR:=06-Testler/02-Entegrasyon}"
  : "${OPTIONAL_INTEGRATION_TEST:=$INTEGRATION_TEST_DIR/test_synthetic_postgresql_integration.py}"

  # PostgreSQL değişkenleri set -u altında güvenli olsun diye boş default.
  : "${DATA_QUALITY_POSTGRES_TEST_URL:=}"
  : "${DATA_QUALITY_DATABASE_SCHEMA:=}"

  # Runtime state yoksa temiz başlangıç: iteration 0 / COMPLETED.
  # Böylece ilk `devam` planner'ı tetikler.
  if [[ ! -f "$STATE" ]]; then
    printf '%s\n' \
      '{"iteration":0,"stage":"COMPLETED","status":"COMPLETED","repair_round":0,"last_error":null,"updated_at":null}' \
      > "$STATE"
  fi

  # İlk iterasyonda henüz kontrat yoksa planner için minimal placeholder üret.
  if [[ ! -f "$TASK" ]]; then
    printf '%s\n' \
      '{"schema_version":2,"contract_status":"BOOTSTRAP","iteration":0,"task":{"id":"BOOTSTRAP","title":"bootstrap","objective":"bootstrap","selection_mode":"bootstrap","source_docs":[],"priority_reason":null},"repository":{"root":"'"$ROOT"'"},"acceptance_criteria":[]}' \
      > "$TASK"
  fi
}

# --- küçük yardımcılar ------------------------------------------------------

now() {
  date -u +%Y-%m-%dT%H:%M:%SZ
}

state_field() {
  jq -r ".$1" "$STATE"
}

# Atomik state yazımı: geçici dosya + jq doğrulaması + mv.
state_update() {
  local stage="$1" status="$2" error="${3:-}" tmp
  tmp="$(mktemp "$H/state/SESSION.json.tmp.XXXXXX")"
  jq \
    --arg stage "$stage" \
    --arg status "$status" \
    --arg error "$error" \
    --arg now "$(now)" '
      .stage = $stage
      | .status = $status
      | .updated_at = $now
      | .last_error = (if $error == "" then null else $error end)
    ' "$STATE" > "$tmp"
  jq empty "$tmp"
  mv -f "$tmp" "$STATE"
}

# Atomik iteration/repair güncellemesi (jq filtresiyle).
state_patch() {
  local filter="$1"
  shift
  local tmp
  tmp="$(mktemp "$H/state/SESSION.json.tmp.XXXXXX")"
  jq "$@" "$filter" "$STATE" > "$tmp"
  jq empty "$tmp"
  mv -f "$tmp" "$STATE"
}

# base_ref yalnız bilgilendirmedir; her aşamadan önce güncel HEAD ile yenilenir.
# Tarihsel HEAD eşitliği HİÇBİR ZAMAN kapı değildir.
refresh_contract() {
  local head branch tmp
  head="$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || echo unknown)"
  branch="$(git -C "$ROOT" branch --show-current 2>/dev/null || echo unknown)"
  tmp="$(mktemp "$H/CURRENT_TASK.json.tmp.XXXXXX")"
  jq \
    --arg head "$head" \
    --arg branch "$branch" \
    --arg now "$(now)" '
      .repository.base_ref = $head
      | .repository.branch = $branch
      | .repository.base_ref_policy = "Bilgilendirme amaçlıdır ve her aşamadan önce güncel HEAD ile yenilenir. HEAD eşitliği kabul kriteri değildir."
      | .updated_at = $now
    ' "$TASK" > "$tmp"
  jq empty "$tmp"
  mv -f "$tmp" "$TASK"
}

# --- test kapsamı keşfi -----------------------------------------------------

# Görevin dokunduğu dosyalar: izlenen değişiklikler + untracked (runtime hariç).
discover_changed_files() {
  {
    git -C "$ROOT" diff --name-only HEAD 2>/dev/null
    git -C "$ROOT" ls-files --others --exclude-standard 2>/dev/null
  } | sort -u
}

# Görev etkisi PostgreSQL/entegrasyon gerektiriyor mu?
# Yalnız uygulama kaynağı, Alembic yapılandırması/migration'ı veya entegrasyon
# testi değiştiyse gerekir. Backend/veritabanı indeks ve runbook belgeleri
# PostgreSQL davranış değişikliği değildir.
integration_required() {
  local files
  files="$(discover_changed_files)"
  grep -Eq '^(03-Backend/src/|05-Veritabani/alembic|'"$INTEGRATION_TEST_DIR"'/)' <<<"$files"
}

# Çalıştırılacak entegrasyon hedefleri: değişen entegrasyon testleri, yoksa
# zorunlu entegrasyon dizini. Ayrı ortam değişkenleri isteyen opsiyonel suite,
# geniş kapıda dışlanır; kendisi değiştirildiyse doğrudan hedeflenir ve skip
# edilmesi yine kapıyı düşürür.
discover_integration_targets() {
  local changed
  changed="$(discover_changed_files | grep -E '^'"$INTEGRATION_TEST_DIR"'/.*\.py$' || true)"
  if [[ -n "$changed" ]]; then
    printf '%s\n' "$changed"
  else
    if [[ -n "${OPTIONAL_INTEGRATION_TEST:-}" ]]; then
      printf '%s\n' "--ignore=$OPTIONAL_INTEGRATION_TEST"
    fi
    printf '%s\n' "$INTEGRATION_TEST_DIR"
  fi
}

# pytest çıktısında gerçek skip var mı? (zorunlu entegrasyon skip'i PASS sayılmaz)
integration_has_skips() {
  local log="$1"
  grep -Eiq '(^|[ ,])[1-9][0-9]* skipped' "$log"
}

# --- PostgreSQL preflight ---------------------------------------------------

postgres_preflight() {
  if [[ -z "${DATA_QUALITY_POSTGRES_TEST_URL:-}" ]]; then
    echo "DATA_QUALITY_POSTGRES_TEST_URL ayarlı değil." >&2
    return 41
  fi
  if [[ -z "${DATA_QUALITY_DATABASE_SCHEMA:-}" ]]; then
    echo "DATA_QUALITY_DATABASE_SCHEMA ayarlı değil." >&2
    return 42
  fi
  python3 - <<'PY'
import os
from sqlalchemy import create_engine, text

engine = create_engine(
    os.environ["DATA_QUALITY_POSTGRES_TEST_URL"],
    pool_pre_ping=True,
    connect_args={"connect_timeout": 5},
)
with engine.connect() as connection:
    database, user = connection.execute(
        text("select current_database(), current_user")
    ).one()
print(f"POSTGRES_PREFLIGHT_OK database={database} user={user}")
engine.dispose()
PY
}

# --- fresh codex exec -------------------------------------------------------
#
# Her çağrı yeni bir `codex exec` başlatır. Eski session/thread resume edilmez.
# Sonuç dosyası yalnız (a) exit 0, (b) boş değil, (c) beklenen STATUS satırı
# doğrulandıktan SONRA atomik olarak görünür yapılır. Aksi halde bayat/kısmi
# sonuç asla okunmaz.
run_codex() {
  local role="$1" input="$2" result="$3" allowed_regex="$4"
  local iteration repair stdout_log stderr_log failure_log tmp_result
  local model="" reasoning="" rc first_line
  local args

  iteration="$(state_field iteration)"
  repair="$(state_field repair_round)"
  stdout_log="$LOGS/${role}-i${iteration}-r${repair}.stdout.log"
  stderr_log="$LOGS/${role}-i${iteration}-r${repair}.stderr.log"
  failure_log="$LOGS/${role}-failures.log"
  tmp_result="$(mktemp "$H/${role}.result.tmp.XXXXXX")"

  : > "$stdout_log"
  : > "$stderr_log"
  rm -f "$result"

  # Aşama başına model ve reasoning-effort maliyet kaldıracı: planner/reviewer için
  # düşük effort, implementer için varsayılan (config) bırakılabilir.
  case "$role" in
    implementer) model="${CODEX_IMPLEMENTER_MODEL:-}"; reasoning="${CODEX_IMPLEMENTER_REASONING:-}" ;;
    reviewer)    model="${CODEX_REVIEWER_MODEL:-}";    reasoning="${CODEX_REVIEWER_REASONING:-}" ;;
    planner)     model="${CODEX_PLANNER_MODEL:-}";     reasoning="${CODEX_PLANNER_REASONING:-}" ;;
  esac

  args=( "$CODEX_BIN" --ask-for-approval never --sandbox danger-full-access -C "$ROOT" )
  [[ -n "$model" ]] && args+=( -m "$model" )
  [[ -n "$reasoning" ]] && args+=( -c "model_reasoning_effort=$reasoning" )
  args+=( exec -o "$tmp_result" - )

  {
    echo "ROLE=$role"
    echo "ITERATION=$iteration"
    echo "REPAIR_ROUND=$repair"
    echo "STARTED_AT=$(now)"
    echo "PG_ENV_FORWARDED=${DATA_QUALITY_POSTGRES_TEST_URL:+yes}"
    echo "PG_SCHEMA=${DATA_QUALITY_DATABASE_SCHEMA:-unset}"
  } | tee -a "$stdout_log"

  env \
    PYTHONUNBUFFERED=1 \
    DATA_QUALITY_POSTGRES_TEST_URL="${DATA_QUALITY_POSTGRES_TEST_URL:-}" \
    DATA_QUALITY_DATABASE_SCHEMA="${DATA_QUALITY_DATABASE_SCHEMA:-}" \
    TEST_TIMEOUT_SECONDS="${TEST_TIMEOUT_SECONDS}" \
    timeout --signal=INT --kill-after=30s "${CODEX_STAGE_TIMEOUT_SECONDS}s" \
      "${args[@]}" \
      < "$input" \
      > >(tee -a "$stdout_log") \
      2> >(tee -a "$stderr_log" >&2)
  rc=$?

  if [[ "$rc" -ne 0 ]]; then
    {
      echo "FAILED_AT=$(now)"
      echo "ROLE=$role EXIT=$rc"
      echo "STDERR=$stderr_log"
      echo "----- STDERR -----"
      cat "$stderr_log"
    } | tee -a "$failure_log" >&2
    rm -f "$tmp_result" "$result"
    return 33
  fi

  if [[ ! -s "$tmp_result" ]]; then
    echo "$role boş sonuç üretti." | tee -a "$failure_log" >&2
    rm -f "$tmp_result" "$result"
    return 34
  fi

  first_line="$(head -n 1 "$tmp_result" | tr -d '\r')"
  if [[ ! "$first_line" =~ $allowed_regex ]]; then
    {
      echo "ROLE=$role UNEXPECTED_STATUS=$first_line"
    } | tee -a "$failure_log" >&2
    cp "$tmp_result" "$LOGS/${role}-invalid-result.md"
    rm -f "$tmp_result" "$result"
    return 21
  fi

  mv -f "$tmp_result" "$result"
  echo "$first_line"
  return 0
}

# --- test gate (controller kabuğunda) --------------------------------------

run_logged_test() {
  local log="$1"
  shift
  : > "$log"
  (
    cd "$ROOT" || exit 1
    PYTHONUNBUFFERED=1 \
    timeout --signal=INT --kill-after=30s "${TEST_TIMEOUT_SECONDS}s" \
      stdbuf -oL -eL "$@"
  ) > >(tee -a "$log") 2>&1
  return $?
}

# --- pipeline aşamaları -----------------------------------------------------

run_implementer() {
  local iteration repair input result rc need_pg
  iteration="$(state_field iteration)"
  repair="$(state_field repair_round)"
  input="$LOGS/implementer-i${iteration}-r${repair}.input.md"
  result="$H/CODEX_RESULT.md"

  refresh_contract

  # PostgreSQL preflight yalnız görev PG gerektiriyorsa.
  if integration_required; then
    need_pg=yes
  else
    need_pg=no
  fi
  if [[ "$need_pg" == "yes" ]]; then
    if ! postgres_preflight | tee "$LOGS/postgres-preflight-i${iteration}.log"; then
      state_update "IMPLEMENTER" "FAILED" "PostgreSQL preflight başarısız (görev PG gerektiriyor)."
      return 1
    fi
  fi

  {
    cat "$PROMPTS/implementer.md"
    printf '\n## Runtime context\n\nRepository root: `%s`\nTask contract: `%s`\nPostgreSQL required: `%s`\n' "$ROOT" "$TASK" "$need_pg"
    printf 'Suggested scope hint (start here, expand minimally only if needed): %s\n\n' \
      "$(jq -r '(.scope.hint // []) | join(", ") | if . == "" then "(yok — kontrattan türet)" else . end' "$TASK")"
    printf '## Current task contract\n\n'
    cat "$TASK"
    if [[ -s "$H/ARCHITECT_REVIEW.md" ]]; then
      printf '\n\n## Current reviewer feedback\n\n'; cat "$H/ARCHITECT_REVIEW.md"
    fi
    if [[ -s "$H/HUMAN_RESPONSE.md" ]]; then
      printf '\n\n## Operator response\n\n'; cat "$H/HUMAN_RESPONSE.md"
    fi
  } > "$input"

  echo "[1/3] Fresh Codex implementer"
  run_codex "implementer" "$input" "$result" '^STATUS: SUCCESS$'
  rc=$?
  if [[ "$rc" -ne 0 ]]; then
    state_update "IMPLEMENTER" "FAILED" "Implementer başarısız; loglar kaydedildi."
    return "$rc"
  fi
  rm -f "$H/HUMAN_RESPONSE.md"
  state_update "TESTER" "READY" ""
  return 0
}

run_tests() {
  local iteration unit_log integration_log unit_rc integration_rc skipped report
  local need_pg targets t
  iteration="$(state_field iteration)"
  unit_log="$LOGS/unit-tests-i${iteration}.log"
  integration_log="$LOGS/integration-tests-i${iteration}.log"
  report="$H/TEST_REPORT.md"

  refresh_contract
  echo "[2/3] Controller test gates"

  # Unit testler her zaman.
  run_logged_test "$unit_log" python3 -m pytest -q -p no:cacheprovider "$UNIT_TEST_DIR"
  unit_rc=$?

  integration_rc=0
  skipped="n/a"
  if integration_required; then
    need_pg=yes
    # Entegrasyon gerekiyorsa PG preflight zorunlu; başarısızsa SAHTE PASS YOK.
    if ! postgres_preflight | tee "$LOGS/postgres-preflight-tests-i${iteration}.log"; then
      state_update "TESTER" "FAILED" "PostgreSQL preflight başarısız; entegrasyon PASS sayılamaz (ENVIRONMENT_BLOCK)."
      return 1
    fi
    mapfile -t targets < <(discover_integration_targets)
    run_logged_test "$integration_log" python3 -m pytest -q -p no:cacheprovider "${targets[@]}"
    integration_rc=$?
    if integration_has_skips "$integration_log"; then
      skipped="yes"
    else
      skipped="no"
    fi
  else
    need_pg=no
  fi

  {
    echo "# Test Report"
    echo
    echo "Generated: $(now)"
    echo
    echo "Integration required: $need_pg"
    echo
    echo "## Unit tests"
    echo "Command: python3 -m pytest -q -p no:cacheprovider $UNIT_TEST_DIR"
    echo "Exit code: $unit_rc"
    echo "Log: $unit_log"
    echo
    echo "## Integration tests"
    if [[ "$need_pg" == "yes" ]]; then
      echo "Targets: $(discover_integration_targets | tr '\n' ' ')"
      echo "Exit code: $integration_rc"
      echo "Skipped detected: $skipped"
      echo "Log: $integration_log"
    else
      echo "Bu görev PostgreSQL/entegrasyon etkisi içermiyor; entegrasyon kapısı çalıştırılmadı."
    fi
  } > "$report"

  if [[ "$unit_rc" -ne 0 ]]; then
    state_update "TESTER" "FAILED" "Birim testleri başarısız."
    return 1
  fi
  if [[ "$integration_rc" -ne 0 ]]; then
    state_update "TESTER" "FAILED" "PostgreSQL entegrasyon testleri başarısız."
    return 1
  fi
  if [[ "$skipped" == "yes" ]]; then
    state_update "TESTER" "FAILED" "Zorunlu entegrasyon testlerinde skip tespit edildi."
    return 1
  fi

  state_update "REVIEWER" "READY" ""
  return 0
}

run_reviewer() {
  local iteration repair input result rc first_line next_repair
  iteration="$(state_field iteration)"
  repair="$(state_field repair_round)"
  input="$LOGS/reviewer-i${iteration}-r${repair}.input.md"
  result="$H/ARCHITECT_REVIEW.md"

  refresh_contract
  {
    cat "$PROMPTS/reviewer.md"
    printf '\n## Current task contract\n\n'; cat "$TASK"
    printf '\n\n## Fresh implementer result\n\n'; cat "$H/CODEX_RESULT.md"
    printf '\n\n## Fresh controller test report\n\n'; cat "$H/TEST_REPORT.md"
    printf '\n\n## Current Git status\n\n```text\n'; git -C "$ROOT" status --short; printf '```\n'
    printf '\n## Current diff stat\n\n```text\n'; git -C "$ROOT" diff --stat; printf '```\n'
  } > "$input"

  echo "[3/3] Fresh Codex reviewer"
  run_codex "reviewer" "$input" "$result" '^STATUS: (APPROVED|CHANGES_REQUIRED|HUMAN_DECISION)$'
  rc=$?
  if [[ "$rc" -ne 0 ]]; then
    state_update "REVIEWER" "FAILED" "Reviewer başarısız; loglar kaydedildi."
    return "$rc"
  fi

  first_line="$(head -n 1 "$result" | tr -d '\r')"
  case "$first_line" in
    "STATUS: APPROVED")
      state_update "COMPLETED" "COMPLETED" ""
      echo; echo "Tamamlandı ve onaylandı."
      ;;
    "STATUS: CHANGES_REQUIRED")
      next_repair=$((repair + 1))
      if (( next_repair > MAX_REPAIR_ROUNDS )); then
        state_update "REVIEWER" "WAITING_HUMAN" "Azami otomatik onarım turu aşıldı."
        echo; echo "İnsan kararı gerekiyor. Yanıt: devam \"kararın\""
        return 0
      fi
      state_patch '
        .repair_round = $repair
        | .stage = "IMPLEMENTER"
        | .status = "READY"
        | .last_error = null
        | .updated_at = $now
      ' --argjson repair "$next_repair" --arg now "$(now)"
      echo "Reviewer düzeltme istedi; otomatik onarım turu: $next_repair"
      ;;
    "STATUS: HUMAN_DECISION")
      state_update "REVIEWER" "WAITING_HUMAN" "Reviewer insan kararı istedi."
      echo; echo "İnsan kararı gerekiyor. Yanıt: devam \"kararın\""
      ;;
  esac
  return 0
}

# Maliyet kaldıracı: canonical NEXT_STEP.md sıradaki görevi zaten deterministik
# tanımlar. Bunu 0 token ile bash'te okuyup seçeriz; LLM planner yalnız NEXT_STEP
# eksik/bayat olduğunda çalışır (AGENTS.md görev seçim algoritmasıyla birebir).
# Guard: NEXT_STEP work_package az önce tamamlanan görevle aynıysa (NEXT_STEP
# ilerletilmemiş = bayat) LLM planner'a düşülür; böylece DONE görev tekrar seçilmez.
# Başarı: PLANNED_* ve SELECTED_* set edilir, 0 döner. Aksi halde 1 döner.
select_next_task_from_docs() {
  local nextstep="$ROOT/NEXT_STEP.md"
  [[ -f "$nextstep" ]] || return 1

  local status wp title last_wp hint
  status="$(sed -n 's/^status:[[:space:]]*//p' "$nextstep" | head -n 1)"
  wp="$(sed -n 's/^work_package:[[:space:]]*//p' "$nextstep" | head -n 1)"

  [[ "$status" == "active" ]] || return 1
  [[ -n "$wp" ]] || return 1

  # Bayatlık guard'ı: son kontrattaki work package ile aynıysa NEXT_STEP güncel değil.
  last_wp="$(jq -r '.task.source_work_package // ""' "$TASK" 2>/dev/null || echo "")"
  if [[ -n "$last_wp" && "$last_wp" == "$wp" ]]; then
    return 1
  fi

  title="$(sed -n 's/^#[[:space:]]\+//p' "$nextstep" | head -n 1)"
  title="${title#Sıradaki Adım — }"
  [[ -n "$title" ]] || title="$wp"

  # Scope hint: NEXT_STEP içindeki kod/test/migration link yolları (0 token).
  hint="$(grep -oE '\(([0-9]{2}-[A-Za-z][^)]*\.(py|ts|tsx))\)' "$nextstep" \
          | tr -d '()' \
          | grep -E '^(01-SRS|03-Backend|04-Frontend|05-Veritabani|06-Testler)/' \
          | sort -u | paste -sd, - || true)"

  PLANNED_TASK_ID="$wp"
  PLANNED_TITLE="$title"
  PLANNED_OBJECTIVE="$title"
  PLANNED_SOURCE_DOCS="NEXT_STEP.md"
  PLANNED_PRIORITY_REASON="NEXT_STEP.md canonical sıradaki adım; deterministik seçim (0 token)."
  SELECTED_WORK_PACKAGE="$wp"
  SELECTED_SCOPE_HINT="$hint"

  echo "[0/3] Sıradaki görev NEXT_STEP.md'den deterministik seçildi (0 token): $title"
  return 0
}

run_planner() {
  local iteration input result rc first_line scope_hint
  iteration="$(state_field iteration)"
  input="$LOGS/planner-after-i${iteration}.input.md"
  result="$H/NEXT_TASK.md"

  refresh_contract
  {
    cat "$PROMPTS/planner.md"
    printf '\n## Runtime context\n\nRepository root: `%s`\nCurrent iteration: `%s`\n' "$ROOT" "$iteration"
    printf '\n## Last completed task summary\n\n'
    jq '{task: .task, repository: .repository, acceptance_criteria: .acceptance_criteria}' "$TASK" 2>/dev/null || echo '{}'
    if [[ -s "$H/ARCHITECT_REVIEW.md" ]]; then
      printf '\n\n## Latest approval\n\n'; cat "$H/ARCHITECT_REVIEW.md"
    fi
  } > "$input"

  echo "[0/3] Dokümanlardan sıradaki görev seçiliyor"
  run_codex "planner" "$input" "$result" '^STATUS: (READY|NO_TASK)$'
  rc=$?
  if [[ "$rc" -ne 0 ]]; then
    state_update "PLANNER" "FAILED" "Planner sıradaki görevi seçemedi; loglar kaydedildi."
    return "$rc"
  fi

  first_line="$(head -n 1 "$result" | tr -d '\r')"
  if [[ "$first_line" == "STATUS: NO_TASK" ]]; then
    state_update "PLANNER" "WAITING_HUMAN" "Dokümanlarda uygulanabilir sıradaki görev bulunamadı."
    echo; cat "$result"; echo
    echo 'Elle görev vermek için: devam "görev açıklaması"'
    return 20
  fi

  PLANNED_TASK_ID="$(sed -n 's/^TASK_ID:[[:space:]]*//p' "$result" | head -n 1)"
  PLANNED_TITLE="$(sed -n 's/^TITLE:[[:space:]]*//p' "$result" | head -n 1)"
  PLANNED_OBJECTIVE="$(sed -n 's/^OBJECTIVE:[[:space:]]*//p' "$result" | head -n 1)"
  PLANNED_SOURCE_DOCS="$(sed -n 's/^SOURCE_DOCS:[[:space:]]*//p' "$result" | head -n 1)"
  PLANNED_PRIORITY_REASON="$(sed -n 's/^PRIORITY_REASON:[[:space:]]*//p' "$result" | head -n 1)"
  scope_hint="$(sed -n 's/^SCOPE_HINT:[[:space:]]*//p' "$result" | head -n 1)"

  if [[ -z "$PLANNED_TASK_ID" || -z "$PLANNED_TITLE" || -z "$PLANNED_OBJECTIVE" ]]; then
    state_update "PLANNER" "FAILED" "Planner eksik görev tanımı üretti."
    echo "Planner çıktısı eksik:" >&2; cat "$result" >&2
    return 22
  fi

  # LLM planner yolunda work_package guard'ı için değer taşımayız (boş);
  # scope hint varsa implementer keşfini daraltmak için taşınır.
  SELECTED_WORK_PACKAGE=""
  SELECTED_SCOPE_HINT="$scope_hint"

  echo; echo "Seçilen görev: $PLANNED_TITLE"
  echo "Neden: $PLANNED_PRIORITY_REASON"
  echo "Kaynaklar: $PLANNED_SOURCE_DOCS"; echo
  return 0
}

# Her görevde kontrat TAMAMEN yeniden üretilir. Önceki görevin dosya listesi,
# kabul kriteri veya test beklentisi taşınmaz.
start_new_task() {
  local objective="$1" task_id="${2:-}" title="${3:-}" source_docs="${4:-}"
  local priority_reason="${5:-}" selection_mode="${6:-manual}"
  local work_package="${SELECTED_WORK_PACKAGE:-}" scope_hint="${SELECTED_SCOPE_HINT:-}"
  local iteration head branch tmp now_value

  iteration=$(( $(state_field iteration) + 1 ))
  head="$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || echo unknown)"
  branch="$(git -C "$ROOT" branch --show-current 2>/dev/null || echo unknown)"
  now_value="$(now)"
  [[ -n "$task_id" ]] || task_id="ITERATION-$iteration"
  [[ -n "$title" ]] || title="$objective"

  tmp="$(mktemp "$H/CURRENT_TASK.json.tmp.XXXXXX")"
  jq -n \
    --arg task_id "$task_id" --arg title "$title" --arg objective "$objective" \
    --arg root "$ROOT" --arg branch "$branch" --arg head "$head" \
    --arg source_docs "$source_docs" --arg priority_reason "$priority_reason" \
    --arg selection_mode "$selection_mode" --arg now "$now_value" \
    --arg work_package "$work_package" --arg scope_hint "$scope_hint" \
    --argjson iteration "$iteration" '
      {
        schema_version: 2,
        contract_status: "READY",
        iteration: $iteration,
        task: {
          id: $task_id, title: $title, objective: $objective,
          selection_mode: $selection_mode,
          source_docs: (
            if $source_docs == "" then []
            else $source_docs | split(",")
              | map(gsub("^[[:space:]]+|[[:space:]]+$"; ""))
              | map(select(length > 0))
            end),
          priority_reason: (if $priority_reason == "" then null else $priority_reason end),
          source_work_package: (if $work_package == "" then null else $work_package end)
        },
        repository: {
          root: $root, branch: $branch, base_ref: $head,
          base_ref_policy: "Bilgilendirme amaçlıdır. HEAD eşitliği kabul kriteri değildir."
        },
        scope: {
          discovery_required: true, files: [],
          hint: (
            if $scope_hint == "" then []
            else $scope_hint | split(",")
              | map(gsub("^[[:space:]]+|[[:space:]]+$"; ""))
              | map(select(length > 0))
            end),
          rule: "Implementer scope.hint ile başlar, gerekiyorsa minimal genişletir; en dar dosya kapsamını korur.",
          forbidden_git_operations: ["checkout","reset","rebase","force-push"]
        },
        acceptance_criteria: [
          {id:"AC-01", requirement:"Görev objektifi ve kaynak gereksinim dokümanları uygulanmalıdır."},
          {id:"AC-02", requirement:"Değişen davranışlar için uygun testler eklenmeli veya güncellenmelidir."},
          {id:"AC-03", requirement:"Mevcut birim test paketi exit 0 ile tamamlanmalıdır."},
          {id:"AC-04", requirement:"PostgreSQL davranışı etkileniyorsa ilgili entegrasyon testleri exit 0 vermeli ve skip edilmemelidir."},
          {id:"AC-05", requirement:"Görevle ilgisiz repository değişikliği yapılmamalıdır."},
          {id:"AC-06", requirement:"Görev canonical backlog/Sonraki-Adım güncellemesi gerektiriyorsa dokümanlar da güncellenmelidir."},
          {id:"AC-07", requirement:"Reviewer güncel kod, test ve kaynak dokümanlar üzerinden onay vermelidir."}
        ],
        runtime_rules: [
          "Her agent aşaması fresh codex exec ile başlatılır.",
          "Eski Codex sessionları resume edilmez.",
          "Eski handoff raporları güncel gerçeklik sayılmaz.",
          "Geniş test paketleri controller kabuğunda çalıştırılır.",
          "Tarihsel HEAD eşitliği görev kapısı değildir.",
          "Canonical repository dokümanları görev gereksinimlerinin kaynağıdır."
        ],
        created_at: $now, updated_at: $now
      }' > "$tmp"
  jq empty "$tmp"
  mv -f "$tmp" "$TASK"

  # Önceki iterasyonun runtime çıktıları temizlenir (iteration-bazlı loglar kalır).
  rm -f "$H/CODEX_RESULT.md" "$H/TEST_REPORT.md" "$H/ARCHITECT_REVIEW.md" \
        "$H/HUMAN_RESPONSE.md" "$H/NEXT_TASK.md"

  state_patch '
    .iteration = $iteration
    | .stage = "IMPLEMENTER"
    | .status = "READY"
    | .repair_round = 0
    | .last_error = null
    | .updated_at = $now
  ' --argjson iteration "$iteration" --arg now "$now_value"

  echo "Yeni iterasyon oluşturuldu: $iteration"
  echo "Görev: $title"
}

# --- ana state-machine ------------------------------------------------------

main() {
  local action="${1:-continue}" note="" stage status
  [[ $# -gt 0 ]] && shift
  note="$*"
  status="$(state_field status)"
  stage="$(state_field stage)"

  # Görev seçim globalleri her turda sıfırlanır (önceki turdan sızma olmasın).
  SELECTED_WORK_PACKAGE=""; SELECTED_SCOPE_HINT=""

  if [[ "$status" == "COMPLETED" ]]; then
    if [[ -z "$note" ]]; then
      PLANNED_TASK_ID=""; PLANNED_TITLE=""; PLANNED_OBJECTIVE=""
      PLANNED_SOURCE_DOCS=""; PLANNED_PRIORITY_REASON=""
      # Önce 0-token deterministik seçim (NEXT_STEP.md); olmazsa LLM planner.
      if ! select_next_task_from_docs; then
        run_planner || return $?
      fi
      start_new_task "$PLANNED_OBJECTIVE" "$PLANNED_TASK_ID" "$PLANNED_TITLE" \
        "$PLANNED_SOURCE_DOCS" "$PLANNED_PRIORITY_REASON" "automatic"
    else
      start_new_task "$note" "" "$note" "" "Operator tarafından doğrudan verildi." "manual"
    fi
  elif [[ "$status" == "WAITING_HUMAN" ]]; then
    if [[ -z "$note" ]]; then
      echo "İnsan kararı bekleniyor (varsayılan pencere ${HUMAN_WAIT_SECONDS}s; state kalıcı, süre sınırı yok)."
      echo
      cat "$H/ARCHITECT_REVIEW.md" 2>/dev/null || cat "$H/NEXT_TASK.md" 2>/dev/null || true
      echo; echo 'Yanıt vermek için: devam "kararın veya görevin"'
      return 0
    fi
    if [[ "$stage" == "PLANNER" ]]; then
      start_new_task "$note" "" "$note" "" "Planner görev bulamadığı için operatör tarafından verildi." "manual"
    else
      printf '%s\n' "$note" > "$H/HUMAN_RESPONSE.md"
      # İnsan kararı onarım kilidini kırar: taze onarım bütçesiyle başla.
      state_patch '
        .stage = "IMPLEMENTER" | .status = "READY"
        | .repair_round = 0 | .last_error = null | .updated_at = $now
      ' --arg now "$(now)"
      echo "Karar kaydedildi; taze onarım bütçesiyle implementer yeniden başlatılıyor."
    fi
  elif [[ "$status" == "FAILED" ]]; then
    echo "Önceki başarısız aşama yeniden deneniyor: $stage"
    state_update "$stage" "READY" ""
  fi

  while true; do
    stage="$(state_field stage)"
    status="$(state_field status)"
    case "$status:$stage" in
      READY:IMPLEMENTER) run_implementer || return $? ;;
      READY:TESTER)      run_tests || return $? ;;
      READY:REVIEWER)    run_reviewer || return $? ;;
      COMPLETED:COMPLETED) echo "Pipeline tamamlandı."; return 0 ;;
      WAITING_HUMAN:*)
        echo "İnsan kararı bekleniyor. Yanıt: devam \"kararın veya görevin\""
        return 0 ;;
      *)
        echo "Beklenmeyen state: status=$status stage=$stage" >&2
        return 70 ;;
    esac
  done
}
