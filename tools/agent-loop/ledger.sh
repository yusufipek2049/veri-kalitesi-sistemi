#!/usr/bin/env bash
# tools/agent-loop/ledger.sh
#
# Kalıcı görev defteri, claim kilidi, test kanıtı ve review kaydı. Bu dosya
# SIDE-EFFECT ÜRETMEZ: yalnız fonksiyon tanımlar.
#
# Ayrım (tek durum kaynağı ilkesi):
#   .agent/            KALICI ve İZLENEN: yapılandırma, görev defteri, handoff,
#                      review kaydı, test kanıtı özeti, şablonlar.
#   .agent-handoff/    RUNTIME ve İGNORE EDİLEN: state, prompt snapshot, ham log,
#                      aşama girdileri. Her çalışmada yeniden kurulur.
#   $GIT_COMMON_DIR/   Worktree'ler arası claim kilitleri (çalışma ağacında
#                      değildir, asla commit edilmez).
#
# Görev defteri dosyaları HER SENKRONDA YENİDEN ÜRETİLİR (idempotent). Böylece
# defter ile controller state'i arasında elle düzeltme gerektiren drift oluşmaz.
#
# shellcheck shell=bash

# --- yollar -----------------------------------------------------------------

ledger_init() {
  # Yollar HER init'te ROOT'tan yeniden hesaplanır: aynı kabukta birden fazla
  # repo/worktree ile çalışıldığında eski yol sızmaz. Açık override yalnız
  # *_OVERRIDE değişkenleriyle yapılır.
  AGENT_STATE_ROOT="${AGENT_STATE_ROOT_OVERRIDE:-$ROOT/.agent}"
  AGENT_ROLES_FILE="${AGENT_ROLES_FILE_OVERRIDE:-$AGENT_STATE_ROOT/config/agents.yaml}"
  LEDGER_DIR="$AGENT_STATE_ROOT/tasks"
  LEDGER_ACTIVE="$LEDGER_DIR/active"
  LEDGER_COMPLETED="$LEDGER_DIR/completed"
  LEDGER_BLOCKED="$LEDGER_DIR/blocked"
  LEDGER_TEMPLATES="$LEDGER_DIR/templates"
  HANDOFF_DIR="$AGENT_STATE_ROOT/handoffs"
  REVIEW_DIR="$AGENT_STATE_ROOT/reviews"
  EVIDENCE_DIR="$AGENT_STATE_ROOT/evidence/tests"

  # Claim kilitleri worktree'ler arası görünür olmalıdır: ortak git dizini
  # bütün worktree'lerde aynıdır, çalışma ağacının parçası değildir.
  local common
  common="$(git -C "$ROOT" rev-parse --path-format=absolute --git-common-dir 2>/dev/null || true)"
  [[ -n "$common" ]] || common="$ROOT/.git"
  CLAIM_DIR="${AGENT_CLAIM_DIR:-$common/agent-claims}"

  mkdir -p "$LEDGER_ACTIVE" "$LEDGER_COMPLETED" "$LEDGER_BLOCKED" \
           "$HANDOFF_DIR" "$REVIEW_DIR" "$EVIDENCE_DIR" "$CLAIM_DIR"
}

# --- görev yaşam döngüsü ----------------------------------------------------

# Controller state'i (stage/status) kanonik yaşam döngüsü durumuna çevirir.
# İkinci bir durum deposu tutulmaz; defter türetilmiş görünümdür.
#   READY IN_PROGRESS CLAIMED IMPLEMENTED TESTING REVIEW
#   CHANGES_REQUESTED APPROVED BLOCKED COMPLETED
lifecycle_state() {
  local stage="$1" status="$2" repair="${3:-0}" review="${4:-}"

  case "$status" in
    WAITING_HUMAN) printf 'BLOCKED'; return 0 ;;
    WAITING_AGENT) printf 'CLAIMED'; return 0 ;;
  esac

  case "$stage" in
    COMPLETED)
      if [[ "$review" == "APPROVED" ]]; then printf 'APPROVED'; else printf 'COMPLETED'; fi
      return 0 ;;
    IMPLEMENTER)
      if [[ "$status" == "FAILED" ]]; then printf 'IN_PROGRESS'
      elif (( repair > 0 ));      then printf 'CHANGES_REQUESTED'
      else                             printf 'READY'; fi
      return 0 ;;
    TESTER)
      if [[ "$status" == "FAILED" ]]; then printf 'TESTING'; else printf 'IMPLEMENTED'; fi
      return 0 ;;
    REVIEWER)   printf 'REVIEW'; return 0 ;;
    PLANNER)    printf 'READY'; return 0 ;;
  esac
  printf 'UNKNOWN'
}

ledger_task_id() {
  jq -r '.task.id // ""' "$TASK" 2>/dev/null || true
}

# Görev dosyasının bulunduğu kova (varsa) yolunu yazdırır.
ledger_find() {
  local id="$1" bucket
  for bucket in "$LEDGER_ACTIVE" "$LEDGER_BLOCKED" "$LEDGER_COMPLETED"; do
    [[ -f "$bucket/$id.md" ]] && { printf '%s' "$bucket/$id.md"; return 0; }
  done
  return 1
}

_ledger_review_result() {
  local file="$H/ARCHITECT_REVIEW.md" first
  [[ -s "$file" ]] || { printf ''; return 0; }
  first="$(head -n 1 "$file" | tr -d '\r')"
  case "$first" in
    "STATUS: APPROVED")         printf 'APPROVED' ;;
    "STATUS: CHANGES_REQUIRED") printf 'CHANGES_REQUESTED' ;;
    "STATUS: HUMAN_DECISION")   printf 'HUMAN_DECISION' ;;
    *)                          printf '' ;;
  esac
}

# ledger_sync
# Aktif kontrat + controller state'ten görev dosyasını yeniden üretir ve doğru
# kovaya yerleştirir. Bootstrap kontratında hiçbir şey yazılmaz.
ledger_sync() {
  local id iteration stage status repair review lifecycle bucket target existing
  local title objective sources reason wp branch head created start_time
  local impl_agent impl_reason test_agent review_agent evidence handoff

  id="$(ledger_task_id)"
  [[ -n "$id" && "$id" != "BOOTSTRAP" && "$id" != "null" ]] || return 0

  iteration="$(state_field iteration)"
  stage="$(state_field stage)"
  status="$(state_field status)"
  repair="$(state_field repair_round)"
  review="$(_ledger_review_result)"
  lifecycle="$(lifecycle_state "$stage" "$status" "$repair" "$review")"

  case "$lifecycle" in
    APPROVED|COMPLETED) bucket="$LEDGER_COMPLETED" ;;
    BLOCKED)            bucket="$LEDGER_BLOCKED" ;;
    *)                  bucket="$LEDGER_ACTIVE" ;;
  esac
  target="$bucket/$id.md"

  title="$(jq -r '.task.title // ""' "$TASK")"
  objective="$(jq -r '.task.objective // ""' "$TASK")"
  sources="$(jq -r '(.task.source_docs // []) | join(", ")' "$TASK")"
  reason="$(jq -r '.task.priority_reason // ""' "$TASK")"
  wp="$(jq -r '.task.source_work_package // ""' "$TASK")"
  branch="$(git -C "$ROOT" branch --show-current 2>/dev/null || echo unknown)"
  head="$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || echo unknown)"
  created="$(jq -r '.created_at // ""' "$TASK")"

  # Önceki dosyadaki başlangıç zamanı korunur (yeniden üretim onu kaybetmemeli).
  start_time="$created"
  if existing="$(ledger_find "$id" 2>/dev/null)"; then
    local prev
    prev="$(sed -n 's/^started_at:[[:space:]]*//p' "$existing" | head -n 1)"
    [[ -n "$prev" ]] && start_time="$prev"
  fi

  impl_agent="${LEDGER_IMPLEMENTER_AGENT:-$(_ledger_role_agent implementer)}"
  impl_reason="${LEDGER_FALLBACK_REASON:-}"
  # Aşama tarafından verilmediyse güncel yapılandırmadan türet (defter neden
  # yedek ajanla çalışıldığını her zaman göstermelidir).
  if [[ -z "$impl_reason" ]] && declare -F role_resolve >/dev/null 2>&1 && roles_active; then
    local saved_reason="${ROLE_RESOLUTION_REASON:-}"
    role_resolve implementer >/dev/null 2>&1 && impl_reason="${ROLE_RESOLUTION_REASON:-}"
    ROLE_RESOLUTION_REASON="$saved_reason"
  fi
  test_agent="$(_ledger_role_agent tester)"
  review_agent="$(_ledger_role_agent reviewer)"
  evidence="$(ls -1 "$EVIDENCE_DIR/$id"/*.json 2>/dev/null | sort | tail -n 1 || true)"
  handoff="$(ls -1 "$HANDOFF_DIR/$id"-*.md 2>/dev/null | sort | tail -n 1 || true)"
  # Yollar depo göreli YAZILIR (defter worktree yolundan bağımsız okunmalı),
  # ancak okuma mutlak yolla yapılır (cwd'ye bağımlı olmamak için).
  local evidence_abs="$evidence"
  evidence="${evidence#"$ROOT"/}"
  handoff="${handoff#"$ROOT"/}"

  mkdir -p "$bucket"
  {
    printf '%s\n' '---'
    printf 'type: agent-task\n'
    printf 'task_id: %s\n' "$id"
    printf 'lifecycle_state: %s\n' "$lifecycle"
    printf 'controller_stage: %s\n' "$stage"
    printf 'controller_status: %s\n' "$status"
    printf 'iteration: %s\n' "$iteration"
    printf 'repair_round: %s\n' "$repair"
    printf 'implementer_agent: %s\n' "${impl_agent:-unresolved}"
    printf 'tester_agent: %s\n' "${test_agent:-unresolved}"
    printf 'reviewer_agent: %s\n' "${review_agent:-unresolved}"
    printf 'fallback_reason: %s\n' "${impl_reason:-none}"
    printf 'branch: %s\n' "$branch"
    printf 'worktree: %s\n' "$ROOT"
    printf 'head: %s\n' "$head"
    printf 'source_work_package: %s\n' "${wp:-none}"
    printf 'started_at: %s\n' "$start_time"
    printf 'updated_at: %s\n' "$(now)"
    printf 'review_result: %s\n' "${review:-pending}"
    printf 'evidence: %s\n' "${evidence:-none}"
    printf 'handoff: %s\n' "${handoff:-none}"
    printf '%s\n\n' '---'

    printf '# %s — %s\n\n' "$id" "${title:-$id}"
    printf '> Bu dosya `tools/agent-loop` tarafından **otomatik üretilir**. Elle\n'
    printf '> düzenleme sonraki senkronda kaybolur; kalıcı bilgi kanonik dokümana yazılır.\n\n'

    printf '## Amaç\n\n%s\n\n' "${objective:-(kontratta yok)}"
    printf '## Kaynak\n\n- Backlog/kaynak doküman: %s\n- Öncelik gerekçesi: %s\n- Çalışma paketi: %s\n\n' \
      "${sources:-(yok)}" "${reason:-(yok)}" "${wp:-(yok)}"

    printf '## Kapsam\n\n### Kapsam içi\n\n'
    jq -r '(.scope.hint // []) | if length == 0 then "- (kontratta dosya ipucu yok; implementer minimal kapsamı türetir)" else (.[] | "- `" + . + "`") end' "$TASK"
    printf '\n### Kapsam dışı\n\n'
    printf -- '- Görevle ilgisiz dosya, modül ve doküman değişikliği.\n'
    printf -- '- Yasak git işlemleri: %s\n\n' "$(jq -r '(.scope.forbidden_git_operations // []) | join(", ")' "$TASK")"

    printf '## Kabul kriterleri\n\n'
    jq -r '(.acceptance_criteria // []) | .[] | "- **" + .id + "** " + .requirement' "$TASK"
    printf '\n## Test planı\n\n'
    printf -- '- Birim: `python3 -m pytest -q %s` (her görevde).\n' "$UNIT_TEST_DIR"
    printf -- '- Entegrasyon: yalnız görev PostgreSQL/migration/uygulama kaynağı etkilediğinde;\n'
    printf -- '  PG preflight zorunlu, başarısızsa `ENVIRONMENT_FAILURE` (sahte PASS yok).\n'
    printf -- '- Testler controller kabuğunda çalışır; uygulayıcının test beyanı kanıt değildir.\n\n'

    printf '## Riskler\n\n'
    printf -- '- Kapsam genişlemesi: kontrat dosya ipucu bağlayıcı bir üst sınır değildir, gözden geçir.\n'
    printf -- '- Ortam bağımlılığı: PostgreSQL/Docker yokluğu ürün hatası olarak raporlanmamalıdır.\n\n'

    printf '## Uygulama özeti\n\n'
    if [[ -s "$H/CODEX_RESULT.md" ]]; then
      sed -n '1,40p' "$H/CODEX_RESULT.md"
    else
      printf '(henüz uygulama sonucu yok)\n'
    fi

    printf '\n## Test kanıtları\n\n'
    if [[ -n "$evidence" ]]; then
      printf -- '- Kanıt kaydı: `%s`\n' "$evidence"
      jq -r '"- Komut: `" + .command + "` exit=" + (.exit_code|tostring)
             + " passed=" + (.passed|tostring) + " failed=" + (.failed|tostring)
             + " skipped=" + (.skipped|tostring)
             + (if .failure_class then " sınıf=" + .failure_class else "" end)' "$evidence_abs" 2>/dev/null || true
    else
      printf '(henüz test kanıtı yok)\n'
    fi

    printf '\n## Review sonucu\n\n'
    if [[ -s "$H/ARCHITECT_REVIEW.md" ]]; then
      printf -- '- Reviewer ajanı: %s\n- Sonuç: %s\n\n' "${review_agent:-unresolved}" "${review:-pending}"
      sed -n '1,40p' "$H/ARCHITECT_REVIEW.md"
    else
      printf '(henüz bağımsız review yok — görev tamamlanmış sayılamaz)\n'
    fi
    printf '\n'
  } > "$target.tmp"
  mv -f "$target.tmp" "$target"

  # Kova değiştiyse eski kopyayı kaldır: bir görev tek kovada bulunur.
  local other
  for other in "$LEDGER_ACTIVE" "$LEDGER_BLOCKED" "$LEDGER_COMPLETED"; do
    [[ "$other" == "$bucket" ]] && continue
    rm -f "$other/$id.md"
  done
  printf '%s\n' "$target"
}

_ledger_role_agent() {
  if declare -F roles_active >/dev/null 2>&1 && roles_active; then
    role_agent "$1" 2>/dev/null || printf 'unresolved'
  else
    printf '%s' "${AGENT_BACKEND:-unresolved}"
  fi
}

# --- claim kilidi (aynı görevde iki uygulayıcıyı engeller) -------------------

claim_owner_file() {
  printf '%s/%s.json' "$CLAIM_DIR" "$1"
}

# claim_acquire <task_id> <agent>
#   0  -> kilit bu worktree'de (yeni alındı veya yeniden giriş)
#   37 -> başka bir worktree/süreç sahibi
claim_acquire() {
  local id="$1" agent="${2:-unknown}" file lock_owner_wt lock_pid
  [[ -n "$id" && "$id" != "BOOTSTRAP" ]] || return 0
  [[ "${RUNTIME_PREVENT_PARALLEL_WRITERS:-true}" == "true" ]] || return 0
  file="$(claim_owner_file "$id")"

  if [[ -f "$file" ]]; then
    lock_owner_wt="$(jq -r '.worktree // ""' "$file" 2>/dev/null || true)"
    lock_pid="$(jq -r '.pid // 0' "$file" 2>/dev/null || echo 0)"
    if [[ "$lock_owner_wt" == "$ROOT" ]]; then
      return 0   # yeniden giriş: aynı worktree kaldığı yerden sürdürür
    fi
    if [[ "$lock_pid" =~ ^[0-9]+$ ]] && (( lock_pid > 0 )) && kill -0 "$lock_pid" 2>/dev/null; then
      echo "Görev $id zaten claim edilmiş: worktree=$lock_owner_wt pid=$lock_pid" >&2
      return 37
    fi
    echo "Görev $id için sahipsiz (bayat) claim bulundu: $lock_owner_wt pid=$lock_pid" >&2
    echo "Devralmak için: tools/agent-loop/agentctl.sh cleanup --task $id" >&2
    return 37
  fi

  local tmp
  tmp="$(mktemp "$file.tmp.XXXXXX")"
  jq -n --arg id "$id" --arg agent "$agent" --arg wt "$ROOT" \
        --arg branch "$(git -C "$ROOT" branch --show-current 2>/dev/null || echo unknown)" \
        --arg now "$(now)" --argjson pid "$$" \
        '{task_id:$id, agent:$agent, worktree:$wt, branch:$branch, pid:$pid, claimed_at:$now}' \
    > "$tmp"
  jq empty "$tmp"
  # noclobber: iki süreç aynı anda gelirse yalnız biri kazanır.
  if ( set -o noclobber; true > "$file" ) 2>/dev/null; then
    mv -f "$tmp" "$file"
    return 0
  fi
  rm -f "$tmp"
  echo "Görev $id claim yarışında kaybedildi." >&2
  return 37
}

claim_release() {
  local id="$1" file owner
  [[ -n "$id" ]] || return 0
  file="$(claim_owner_file "$id")"
  [[ -f "$file" ]] || return 0
  owner="$(jq -r '.worktree // ""' "$file" 2>/dev/null || true)"
  if [[ "$owner" == "$ROOT" || "${CLAIM_FORCE:-0}" == "1" ]]; then
    rm -f "$file"
    return 0
  fi
  echo "Claim başka worktree'ye ait, bırakılmadı: $owner" >&2
  return 1
}

# --- test kanıtı ------------------------------------------------------------

# Başarısız test sınıflandırması. PostgreSQL/Docker/dış servis yokluğu ÜRÜN HATASI
# değildir; ayrı sınıfa girer.
classify_test_failure() {
  local log="$1" rc="$2"
  if [[ "$rc" == "0" ]]; then printf 'NONE'; return 0; fi
  case "$rc" in
    124|125|137) printf 'ENVIRONMENT_FAILURE'; return 0 ;;
  esac
  [[ -f "$log" ]] || { printf 'UNKNOWN'; return 0; }

  if grep -qiE 'could not connect|connection refused|could not translate host|no such host|operationalerror.*(connect|server closed)|psycopg[0-9]*\.OperationalError|docker.*(not running|cannot connect)|ldap.*(server down|connect error)' "$log"; then
    printf 'ENVIRONMENT_FAILURE'; return 0
  fi
  if grep -qiE 'ModuleNotFoundError|ImportError while loading|No module named|pkg_resources\.DistributionNotFound|version conflict' "$log"; then
    printf 'DEPENDENCY_FAILURE'; return 0
  fi
  if grep -qiE 'is not set|missing (required )?(env|environment) variable|KeyError: .(DATA_QUALITY|DATABASE)|ValidationError.*settings|alembic\.util\.exc\.CommandError' "$log"; then
    printf 'CONFIGURATION_FAILURE'; return 0
  fi
  if grep -qiE 'fixture .* not found|ERROR collecting|errors during collection|INTERNALERROR' "$log"; then
    printf 'TEST_DEFECT'; return 0
  fi
  if grep -qiE '^(FAILED|E  +assert)|AssertionError|assert ' "$log"; then
    printf 'PRODUCT_DEFECT'; return 0
  fi
  printf 'UNKNOWN'
}

# pytest özet satırından sayıları çıkarır (bulunamazsa -1: uydurma sayı üretilmez).
_pytest_count() {
  local log="$1" key="$2" value
  value="$(grep -oE "[0-9]+ $key" "$log" 2>/dev/null | tail -n 1 | grep -oE '^[0-9]+' || true)"
  [[ -n "$value" ]] || value="-1"
  printf '%s' "$value"
}

# evidence_write <task_id> <suite> <command> <exit_code> <duration> <log> <notes> [sınıf]
# Sekizinci argüman verilirse hata sınıfı log metninden çıkarım yerine doğrudan
# kullanılır: bazı hatalar (ör. PostgreSQL preflight bloğu) tanım gereği ortam
# hatasıdır ve log sözcüklerine bağlı bırakılmaz.
evidence_write() {
  local id="$1" suite="$2" command="$3" rc="$4" duration="$5" log="$6" notes="${7:-}"
  local forced_class="${8:-}"
  local dir file tmp passed failed skipped klass runner
  [[ -n "$id" && "$id" != "BOOTSTRAP" ]] || return 0
  dir="$EVIDENCE_DIR/$id"
  mkdir -p "$dir"
  file="$dir/i$(state_field iteration)-$suite.json"

  passed="$(_pytest_count "$log" passed)"
  failed="$(_pytest_count "$log" failed)"
  skipped="$(_pytest_count "$log" skipped)"
  if [[ -n "$forced_class" ]]; then
    klass="$forced_class"
  else
    klass="$(classify_test_failure "$log" "$rc")"
  fi
  runner="$(_ledger_role_agent tester)"

  tmp="$(mktemp "$file.tmp.XXXXXX")"
  jq -n \
    --arg task_id "$id" --arg suite "$suite" --arg runner "$runner" \
    --arg ts "$(now)" --arg wd "$ROOT" \
    --arg branch "$(git -C "$ROOT" branch --show-current 2>/dev/null || echo unknown)" \
    --arg commit "$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || echo unknown)" \
    --arg command "$command" --arg log "${log#"$ROOT"/}" \
    --arg notes "$notes" --arg klass "$klass" \
    --argjson rc "$rc" --argjson duration "$duration" \
    --argjson passed "$passed" --argjson failed "$failed" --argjson skipped "$skipped" \
    '{
       task_id: $task_id,
       suite: $suite,
       runner: "controller-shell",
       tester_agent: $runner,
       runner_role: "tester",
       timestamp: $ts,
       working_directory: $wd,
       git_branch: $branch,
       git_commit: $commit,
       command: $command,
       exit_code: $rc,
       duration: $duration,
       passed: $passed,
       failed: $failed,
       skipped: $skipped,
       stdout_log: $log,
       stderr_log: $log,
       environment_notes: $notes,
       failure_class: $klass,
       evidence_rule: "Sayaç -1 ise pytest özeti okunamadı; sayı uydurulmaz. Testler controller kabuğunda çalıştırılır, uygulayıcı beyanı kanıt değildir."
     }' > "$tmp"
  jq empty "$tmp"
  mv -f "$tmp" "$file"
  printf '%s\n' "$file"
}

# --- review kaydı -----------------------------------------------------------

review_record() {
  local id="$1" result="$2" dir file
  [[ -n "$id" && "$id" != "BOOTSTRAP" ]] || return 0
  [[ -s "$H/ARCHITECT_REVIEW.md" ]] || return 0
  dir="$REVIEW_DIR/$id"
  mkdir -p "$dir"
  file="$dir/i$(state_field iteration)-r$(state_field repair_round).md"
  {
    printf '%s\n' '---'
    printf 'type: agent-review\ntask_id: %s\nresult: %s\n' "$id" "$result"
    printf 'reviewer_agent: %s\n' "$(_ledger_role_agent reviewer)"
    printf 'implementer_agent: %s\n' "${LEDGER_IMPLEMENTER_AGENT:-$(_ledger_role_agent implementer)}"
    printf 'iteration: %s\nrepair_round: %s\n' "$(state_field iteration)" "$(state_field repair_round)"
    printf 'reviewed_at: %s\n' "$(now)"
    printf 'independence_rule: "Uygulayıcı kendi işini onaylamaz; review ayrı ajan sürecidir."\n'
    printf '%s\n\n' '---'
    cat "$H/ARCHITECT_REVIEW.md"
  } > "$file.tmp"
  mv -f "$file.tmp" "$file"
  printf '%s\n' "$file"
}

# --- handoff paketi (otomatik çalıştırılamayan ajanlar için) -----------------

# handoff_write <role> <agent> <aşama girdisi>
# Görev paketini izlenen bir dosyaya yazar ve yolunu döndürür. Sır, token veya
# parola yazılmaz: yalnız repo içi yollar ve kontrat alanları kullanılır.
handoff_write() {
  local role="$1" agent="$2" input="$3" id file iteration repair
  id="$(ledger_task_id)"
  [[ -n "$id" ]] || id="UNKNOWN"
  iteration="$(state_field iteration)"
  repair="$(state_field repair_round)"
  file="$HANDOFF_DIR/$id-$role-i$iteration-r$repair.md"

  {
    printf '%s\n' '---'
    printf 'type: agent-handoff\ntask_id: %s\nrole: %s\nagent: %s\n' "$id" "$role" "$agent"
    printf 'iteration: %s\nrepair_round: %s\ncreated_at: %s\n' "$iteration" "$repair" "$(now)"
    printf 'worktree: %s\nbranch: %s\n' "$ROOT" \
      "$(git -C "$ROOT" branch --show-current 2>/dev/null || echo unknown)"
    printf 'fallback_reason: %s\n' "${ROLE_RESOLUTION_REASON:-none}"
    printf 'status: PENDING\n'
    printf '%s\n\n' '---'

    printf '# Görev paketi — %s (%s)\n\n' "$id" "$(roles_agent_label "$agent")"
    printf 'Bu paket controller tarafından üretildi. Kuralların tamamı `AGENTS.md`\n'
    printf 've `.qoder/rules/` dosyalarındadır; burada tekrar edilmez.\n\n'

    printf '## 1. Amaç\n\n%s\n\n' "$(jq -r '.task.objective // "(yok)"' "$TASK")"

    printf '## 2. Gereksinim referansları\n\n'
    jq -r '(.task.source_docs // []) | if length == 0 then "- (kontratta kaynak doküman yok; NEXT_STEP.md ve backlog'"'"'a bak)" else (.[] | "- `" + . + "`") end' "$TASK"
    printf '\n'

    printf '## 3. Değiştirilebilecek alanlar\n\n'
    jq -r '(.scope.hint // []) | if length == 0 then "- Kontratta dosya ipucu yok: en dar kapsamı kendin türet ve handoff sonucunda listele." else (.[] | "- `" + . + "`") end' "$TASK"
    printf '\n- Gerekiyorsa ilgili test dosyaları (`%s`, `%s`).\n\n' "$UNIT_TEST_DIR" "$INTEGRATION_TEST_DIR"

    printf '## 4. Değiştirilmemesi gereken alanlar\n\n'
    printf -- '- Bu worktree dışındaki hiçbir dizin: yalnız `%s` içinde yaz.\n' "$ROOT"
    printf -- '- Görevle ilgisiz modül, migration, doküman ve yapılandırma.\n'
    printf -- '- `.agent/config/agents.yaml` (rol dağıtımı mimari karardır).\n'
    printf -- '- Yasak git işlemleri: %s. Commit, merge, push ve PR yapma.\n\n' \
      "$(jq -r '(.scope.forbidden_git_operations // []) | join(", ")' "$TASK")"

    printf '## 5. Kabul kriterleri\n\n'
    jq -r '(.acceptance_criteria // []) | .[] | "- **" + .id + "** " + .requirement' "$TASK"
    printf '\n'

    printf '## 6. Çalıştırılacak testler\n\n'
    printf -- '```bash\npython3 -m pytest -q %s\n```\n\n' "$UNIT_TEST_DIR"
    printf 'PostgreSQL/migration/uygulama kaynağı etkilendiyse ek olarak `%s`\n' "$INTEGRATION_TEST_DIR"
    printf 'altındaki ilgili testler. Bu testler ayrıca controller tarafından bağımsız\n'
    printf 'olarak yeniden çalıştırılır: senin beyanın kanıt sayılmaz.\n\n'
    printf 'Test başarısızsa kodu yeniden tasarlamadan önce hata sınıfını belirle:\n'
    printf '`PRODUCT_DEFECT`, `TEST_DEFECT`, `ENVIRONMENT_FAILURE`, `DEPENDENCY_FAILURE`,\n'
    printf '`CONFIGURATION_FAILURE`, `UNKNOWN`. Ortam hatasını ürün hatası gibi düzeltmeye çalışma.\n\n'

    printf '## 7. Güvenlik ve veri kuralları\n\n'
    printf -- '- Secret, token, parola ve hassas veri koda, loga veya depoya yazılmaz.\n'
    printf -- '- Kaynak sistem erişimi salt okunurdur; kimlik/rol/scope yalnız IdP/BFF sınırında çözülür.\n'
    printf -- '- Kritik yazım audit/outbox olmadan tamamlanmaz; belirsiz politika fail-closed.\n'
    printf -- '- Yeni gereksinim, eşik, teknoloji veya iş kuralı uydurulmaz.\n'
    printf -- '- Mimari karar alma: belirsizlikte görevi BLOCKED yap ve nedeni yaz.\n\n'

    printf '## 8. Beklenen çıktı formatı\n\n'
    printf 'Yanıtının **ilk satırı** tam olarak şunlardan biri olmalı:\n\n'
    printf -- '```text\nSTATUS: SUCCESS\nSTATUS: BLOCKED\n```\n\n'
    printf 'Ardından: değiştirilen dosyalar (yol listesi), yapılan değişikliğin özeti,\n'
    printf 'çalıştırdığın komutlar ve exit kodları, kalan riskler.\n\n'

    printf '## 9. Kontrat (tam)\n\n```json\n'
    cat "$TASK"
    printf '```\n\n'

    if [[ -s "$H/ARCHITECT_REVIEW.md" ]]; then
      printf '## 10. Reviewer geri bildirimi (bu turda giderilmeli)\n\n'
      cat "$H/ARCHITECT_REVIEW.md"
      printf '\n'
    fi
    if [[ -s "$H/HUMAN_RESPONSE.md" ]]; then
      printf '## 11. Operatör kararı\n\n'
      cat "$H/HUMAN_RESPONSE.md"
      printf '\n'
    fi
    printf '## Ek: controller aşama girdisi\n\nAyrıntılı runtime girdisi: `%s`\n' "${input#"$ROOT"/}"
  } > "$file.tmp"
  mv -f "$file.tmp" "$file"
  printf '%s\n' "$file"
}

# Handoff sonrası "uygulandı" beyanının doğrulanabilmesi için çalışma ağacı
# parmak izi. Beyan tek başına kabul edilmez: ağaç değişmediyse uygulama yok.
#
# Yalnız `status --porcelain` YETMEZ: o çıktı durum harfi ve dosya yolu listeler,
# içerik listelemez. Zaten `M` durumundaki bir dosya düzenlendiğinde çıktı aynı
# kalır ve gerçek uygulama "değişiklik yok" diye reddedilir. Onarım turları tanım
# gereği mevcut dosyaları düzenlediğinden bu, kapıyı işlevsiz bırakır.
# Bu yüzden içerik de karışıma girer: izlenen dosyalar için `diff HEAD`,
# izlenmeyenler için dosya bazlı sha256.
#
# Controller'ın kendi defteri (`.agent/`, `.agent-handoff/`) parmak izine
# GİRMEZ: handoff paketi, state ve loglar her aşamada controller tarafından
# yazılır; sayılsalardı ajan hiç çalışmadan da "değişiklik var" görünürdü.
worktree_fingerprint() {
  local -a excludes=()
  local path
  for path in "${AGENT_STATE_ROOT:-$ROOT/.agent}" "${H:-$ROOT/.agent-handoff}"; do
    case "$path" in
      "$ROOT"/*) excludes+=( ":(exclude)${path#"$ROOT"/}" ) ;;
    esac
  done
  {
    git -C "$ROOT" status --porcelain=v1 -- . "${excludes[@]}" 2>/dev/null
    git -C "$ROOT" diff HEAD --binary -- . "${excludes[@]}" 2>/dev/null
    git -C "$ROOT" ls-files --others --exclude-standard -z -- . "${excludes[@]}" 2>/dev/null \
      | xargs -0 -r sha256sum 2>/dev/null
  } | sha256sum | cut -d' ' -f1
}
