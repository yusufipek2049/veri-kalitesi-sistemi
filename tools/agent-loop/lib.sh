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
#   - Her agent aşaması fresh agent process'i ile başlar (AGENT_BACKEND=codex|claude);
#     eski session/thread resume edilmez.
#   - Geniş testler controller kabuğunda çalışır, agent process'ine bağlanmaz.
#   - State atomik (mktemp + mv) yazılır; tek instance flock ile korunur.
#
# shellcheck shell=bash

# Kardeş kütüphaneler (yalnız fonksiyon tanımlar, yan etki üretmez):
#   roles.sh   rol → ajan çözümü (canonical kaynak .agent/config/agents.yaml)
#   ledger.sh  kalıcı görev defteri, claim kilidi, test kanıtı, review kaydı
_AGENTLOOP_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=tools/agent-loop/roles.sh
source "$_AGENTLOOP_LIB_DIR/roles.sh"
# shellcheck source=tools/agent-loop/ledger.sh
source "$_AGENTLOOP_LIB_DIR/ledger.sh"
# shellcheck source=tools/agent-loop/compaction.sh
source "$_AGENTLOOP_LIB_DIR/compaction.sh"
# shellcheck source=tools/agent-loop/state_abstraction.sh
source "$_AGENTLOOP_LIB_DIR/state_abstraction.sh"

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

  # Bullet koleksiyonu dosya yolu (delta compaction için)
  CONTEXT_BULLETS_FILE="$H/state/CONTEXT_BULLETS.json"
  bullet_init "$CONTEXT_BULLETS_FILE"

  # Kaynak (izlenen) promptları runtime snapshot'ına kopyala: agent girdisi
  # her zaman izlenen kaynaktan üretilir, elle düzenlenmiş runtime kopyasından
  # değil.
  if [[ -d "$SRC_PROMPTS" ]]; then
    cp -f "$SRC_PROMPTS"/*.md "$PROMPTS"/ 2>/dev/null || true
  fi

  # Yapılandırma varsayılanları (env veya env-file ile override edilebilir).
  : "${TEST_TIMEOUT_SECONDS:=900}"
  : "${CODEX_STAGE_TIMEOUT_SECONDS:=2700}"
  # Backend-bağımsız aşama timeout'u; eski CODEX_* adı geriye dönük varsayılandır.
  : "${AGENT_STAGE_TIMEOUT_SECONDS:=$CODEX_STAGE_TIMEOUT_SECONDS}"
  : "${MAX_REPAIR_ROUNDS:=1}"
  : "${HUMAN_WAIT_SECONDS:=600}"
  # Agent backend seçimi: codex (varsayılan) veya claude. Rol başına model/effort
  # değişkenleri backend başına ayrıdır, birbirine sızmaz.
  : "${AGENT_BACKEND:=codex}"
  # Sağlayıcı erişimi tümden yoksa (kota/kredi/kimlik) aşamayı bir kez tekrarlayacak
  # yedek backend. Boş bırakılırsa devir yapılmaz; maliyet başka sağlayıcıya sessizce
  # kaymaz.
  : "${AGENT_BACKEND_FALLBACK:=}"
  : "${CODEX_BIN:=codex}"
  : "${CLAUDE_BIN:=claude}"
  # Kalıcı stderr logu üst sınırı (0 = sınırsız). Aşılırsa son baytlar korunur.
  : "${AGENT_STDERR_LOG_MAX_BYTES:=2000000}"
  # Sağlayıcıya hiç ulaşılamadığını gösteren imzalar. Sağlayıcılar farklı sözcük
  # kullanır (codex "usage limit", claude "session limit"), bu yüzden desen geniş
  # ama yalnız erişim/kota/kimlik sınıfını kapsar.
  : "${AGENT_PROVIDER_ERROR_RE:=usage limit|session limit|rate limit|quota|insufficient_quota|credit balance|billing|too many requests|http (401|429)|\b(401|429)\b|unauthorized|authentication (failed|error)|not logged in|login required|invalid api key|expired token}"
  : "${UNIT_TEST_DIR:=tests/unit}"
  : "${INTEGRATION_TEST_DIR:=tests/integration}"
  : "${OPTIONAL_INTEGRATION_TEST:=$INTEGRATION_TEST_DIR/test_synthetic_postgresql_integration.py}"

  # --- prompt/konteks bütçesi -------------------------------------------------
  # Bu blok APPEND-ONLY'dir: yeni konteks kaldıraçları buraya eklenir, mevcut
  # satırlar taşınmaz. Her biri tek başına kapatılabilen bir kill-switch'tir,
  # böylece bir müdahale diğerlerinden bağımsız geri alınabilir.
  #
  # Prompt girdisi üst sınırı (bayt). Aşım engellenmez, yalnız loglanır ve
  # testlerle izlenir; sessiz kesme prompt'ta veri kaybı demek olurdu.
  : "${AGENT_PROMPT_MAX_BYTES:=262144}"
  # Reviewer'a verilen gerçek diff üst sınırı (0 = diff bloğu tamamen kapalı).
  : "${AGENT_REVIEW_DIFF_MAX_BYTES:=60000}"
  # Önceki başarısız denemelerin kanıtını prompt'a enjekte et (0 = kapalı).
  : "${AGENT_INJECT_FAILURE_EVIDENCE:=1}"
  # Prompt kuyruğuna sabit slotlu "aktif hedef" bloğu ekle (0 = kapalı).
  : "${AGENT_RECITATION:=1}"
  # S08: Graph-ranked kod bağlamı ekle (0 = kapalı).
  : "${AGENT_GRAPH_CONTEXT:=1}"
  # Kümülatif hata defterinden gösterilecek son satır sayısı.
  : "${AGENT_FAILURE_EVIDENCE_LINES:=80}"

  # PostgreSQL değişkenleri set -u altında güvenli olsun diye boş default.
  : "${DATA_QUALITY_POSTGRES_TEST_URL:=}"
  : "${DATA_QUALITY_DATABASE_SCHEMA:=}"

  # Kalıcı defter yolları + rol yapılandırması. Rol → ajan eşlemesinin TEK
  # kaynağı .agent/config/agents.yaml'dır; yoksa geriye dönük AGENT_BACKEND yolu
  # kullanılır. Dosya VAR ama geçersizse FAIL-CLOSED: hiçbir ajan çalıştırılmaz.
  ledger_init
  roles_load "$AGENT_ROLES_FILE"
  case "$?" in
    0) AGENT_ROLES_STATUS="loaded" ;;
    1) AGENT_ROLES_STATUS="absent" ;;
    *) AGENT_ROLES_STATUS="invalid"
       echo "Rol yapılandırması geçersiz: $AGENT_ROLES_FILE — ajan çalıştırılmadı." >&2
       return 36 ;;
  esac

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
  # --sort-keys: KV-cache koruması için JSON anahtar sırası deterministik olmalı (S04)
  jq --sort-keys \
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
  grep -Eq '^(src/|alembic|alembic\.ini|'"$INTEGRATION_TEST_DIR"'/)' <<<"$files"
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

# --- fresh agent exec -------------------------------------------------------
#
# Her çağrı yeni bir agent process'i başlatır (AGENT_BACKEND=codex|claude). Eski
# session/thread resume edilmez. Sonuç dosyası yalnız (a) exit 0, (b) boş değil,
# (c) beklenen STATUS satırı doğrulandıktan SONRA atomik olarak görünür yapılır.
# Aksi halde bayat/kısmi sonuç asla okunmaz.
#
# Backend farkı yalnız argüman kurulumu ve sonuç yakalama biçimindedir:
#   codex  -> `exec -o <dosya>`; nihai mesajı kendisi dosyaya yazar.
#   claude -> `-p`; prompt stdin'den verilir, nihai mesaj stdout'tan yakalanır.
# Doğrulama, atomik görünürlük ve log/timeout davranışı iki backend'de aynıdır.

agent_backend_label() {
  case "${AGENT_BACKEND}" in
    claude) printf 'Claude' ;;
    codex)  printf 'Codex' ;;
    *)      printf '%s' "${AGENT_BACKEND}" ;;
  esac
}

agent_backend_known() {
  case "$1" in
    codex|claude) return 0 ;;
    *)            return 1 ;;
  esac
}

# Sağlayıcı erişiminin tümden yokluğunu (kota/kredi/kimlik) gösteren stderr
# imzaları. Görev başarısızlığı, geçersiz sonuç ve timeout BU SINIFA GİRMEZ:
# yalnız sağlayıcıya hiç ulaşılamadığında diğer backend denenir. Aksi halde
# gerçek bir defekt sessizce ikinci sağlayıcıya devredilirdi.
agent_provider_unavailable() {
  local stderr_log="$1" rc="$2" result="${3:-}" first
  # GNU timeout kodları sağlayıcı arızası değildir.
  case "$rc" in
    124|125|137) return 1 ;;
  esac

  if [[ -s "$stderr_log" ]] && grep -qiE "${AGENT_PROVIDER_ERROR_RE}" "$stderr_log"; then
    return 0
  fi

  # Bazı backend'ler kota/oturum hatasını STDOUT'a yazar (`claude -p` böyle
  # yapar) ve bu kanal aynı zamanda sonuç kanalıdır. Yanlış pozitif riski var:
  # geçerli bir rapor bu sözcükleri metin olarak içerebilir. Bu yüzden sonuç
  # kanalına yalnız GEÇERLİ SONUÇ YOKKEN bakılır — gerçek sonuç her zaman
  # `STATUS:` satırıyla başlar.
  if [[ -n "$result" && -s "$result" ]]; then
    first="$(head -n 1 "$result" | tr -d '\r')"
    if [[ ! "$first" =~ ^STATUS: ]] \
       && grep -qiE "${AGENT_PROVIDER_ERROR_RE}" "$result"; then
      return 0
    fi
  fi
  return 1
}

# Kalıcı stderr logunu üst sınıra indirir. Hata mesajı sonda olduğu için SON
# baytlar korunur; kesme olayı logun başına açıkça yazılır (sessiz veri kaybı yok).
agent_cap_log() {
  local file="$1" max="$2" size prev="" tmp i
  [[ -f "$file" ]] || return 0
  [[ "$max" =~ ^[0-9]+$ ]] || return 0
  (( max > 0 )) || return 0

  # `tee` alt süreci hâlâ yazıyor olabilir: boyut sabitlenene kadar kısa bekle.
  for i in $(seq 1 10); do
    size="$(stat -c %s "$file" 2>/dev/null || echo 0)"
    [[ "$size" == "$prev" ]] && break
    prev="$size"
    sleep 0.1
  done

  size="$(stat -c %s "$file" 2>/dev/null || echo 0)"
  (( size > max )) || return 0
  tmp="$(mktemp "${file}.cap.XXXXXX")"
  {
    printf '[agent-loop] stderr logu %s bayta ulaştı; yalnız son %s bayt korundu.\n' \
      "$size" "$max"
    tail -c "$max" "$file"
  } > "$tmp"
  mv -f "$tmp" "$file"
}

# Tek deneme: argv'yi backend'e göre kurar, agent'ı çalıştırır ve ham exit
# kodunu döndürür. Doğrulama ve atomik yayınlama çağırana (run_agent) aittir.
# Bilinmeyen backend'de 35 döner ve hiçbir süreç başlatılmaz.
agent_attempt() {
  local backend="$1" role="$2" input="$3" tmp_result="$4" stdout_log="$5" stderr_log="$6"
  local model="" reasoning="" capture_stdout="no" rc
  local args runner

  # Aşama başına model ve reasoning-effort maliyet kaldıracı: planner/reviewer için
  # düşük effort, implementer için varsayılan (backend config) bırakılabilir.
  case "$backend" in
    codex)
      case "$role" in
        implementer) model="${CODEX_IMPLEMENTER_MODEL:-}"; reasoning="${CODEX_IMPLEMENTER_REASONING:-}" ;;
        reviewer)    model="${CODEX_REVIEWER_MODEL:-}";    reasoning="${CODEX_REVIEWER_REASONING:-}" ;;
        planner)     model="${CODEX_PLANNER_MODEL:-}";     reasoning="${CODEX_PLANNER_REASONING:-}" ;;
      esac
      args=( "$CODEX_BIN" --ask-for-approval never --sandbox danger-full-access -C "$ROOT" )
      [[ -n "$model" ]] && args+=( -m "$model" )
      [[ -n "$reasoning" ]] && args+=( -c "model_reasoning_effort=$reasoning" )
      args+=( exec -o "$tmp_result" - )
      ;;
    claude)
      case "$role" in
        implementer) model="${CLAUDE_IMPLEMENTER_MODEL:-}"; reasoning="${CLAUDE_IMPLEMENTER_EFFORT:-}" ;;
        reviewer)    model="${CLAUDE_REVIEWER_MODEL:-}";    reasoning="${CLAUDE_REVIEWER_EFFORT:-}" ;;
        planner)     model="${CLAUDE_PLANNER_MODEL:-}";     reasoning="${CLAUDE_PLANNER_EFFORT:-}" ;;
      esac
      args=( "$CLAUDE_BIN" -p --permission-mode bypassPermissions --add-dir "$ROOT" )
      [[ -n "$model" ]] && args+=( --model "$model" )
      [[ -n "$reasoning" ]] && args+=( --effort "$reasoning" )
      capture_stdout="yes"
      ;;
    *)
      return 35
      ;;
  esac

  # Önceki denemenin kısmi çıktısı asla ikinci denemeye taşınmaz.
  : > "$tmp_result"

  {
    echo "ROLE=$role"
    echo "BACKEND=$backend"
    echo "ITERATION=$(state_field iteration)"
    echo "REPAIR_ROUND=$(state_field repair_round)"
    echo "STARTED_AT=$(now)"
    # Konteks ölçüm iskelesi: token değil, bayt proxy'si. Sayı uydurulmaz —
    # ölçülemeyen bir iyileştirme iddiası kanıtsızdır.
    echo "PROMPT_BYTES=$(wc -c < "$input" 2>/dev/null || echo 0)"
    echo "PG_ENV_FORWARDED=${DATA_QUALITY_POSTGRES_TEST_URL:+yes}"
    echo "PG_SCHEMA=${DATA_QUALITY_DATABASE_SCHEMA:-unset}"
  } | tee -a "$stdout_log"

  runner=(
    env
      PYTHONUNBUFFERED=1
      DATA_QUALITY_POSTGRES_TEST_URL="${DATA_QUALITY_POSTGRES_TEST_URL:-}"
      DATA_QUALITY_DATABASE_SCHEMA="${DATA_QUALITY_DATABASE_SCHEMA:-}"
      TEST_TIMEOUT_SECONDS="${TEST_TIMEOUT_SECONDS}"
    timeout --signal=INT --kill-after=30s "${AGENT_STAGE_TIMEOUT_SECONDS}s"
      "${args[@]}"
  )

  # Agent her zaman repo kökünde çalıştırılır; codex ayrıca `-C` ile bağlanır.
  if [[ "$capture_stdout" == "yes" ]]; then
    # Sonuç stdout'tan yakalanır: log kopyası process bittikten sonra eklenir,
    # böylece tee ile yarış olmadan tam çıktı hem sonuçta hem logda bulunur.
    ( cd "$ROOT" && "${runner[@]}" ) \
      < "$input" \
      > "$tmp_result" \
      2> >(tee -a "$stderr_log" >&2)
    rc=$?
    cat "$tmp_result" >> "$stdout_log" 2>/dev/null || true
  else
    ( cd "$ROOT" && "${runner[@]}" ) \
      < "$input" \
      > >(tee -a "$stdout_log") \
      2> >(tee -a "$stderr_log" >&2)
    rc=$?
  fi
  return "$rc"
}

run_agent() {
  local role="$1" input="$2" result="$3" allowed_regex="$4"
  local iteration repair stdout_log stderr_log failure_log tmp_result
  local rc first_line fallback backend override_var

  iteration="$(state_field iteration)"
  repair="$(state_field repair_round)"
  stdout_log="$LOGS/${role}-i${iteration}-r${repair}.stdout.log"
  stderr_log="$LOGS/${role}-i${iteration}-r${repair}.stderr.log"
  failure_log="$LOGS/${role}-failures.log"
  tmp_result="$(mktemp "$H/${role}.result.tmp.XXXXXX")"

  : > "$stdout_log"
  : > "$stderr_log"
  rm -f "$result"

  # --- rol → ajan çözümü ---
  # Öncelik: (1) tek turluk AGENT_BACKEND_<ROLE> env override,
  #          (2) agents.yaml rol dağıtımı, (3) geriye dönük global AGENT_BACKEND.
  backend="${AGENT_BACKEND}"
  fallback="${AGENT_BACKEND_FALLBACK:-}"
  ROLE_RESOLUTION_REASON=""
  if roles_active; then
    override_var="AGENT_BACKEND_${role^^}"
    if [[ -n "${!override_var:-}" ]]; then
      backend="${!override_var}"
      ROLE_RESOLUTION_REASON="env_override: ${override_var}=${backend}"
    elif role_resolve "$role"; then
      backend="$RESOLVED_AGENT"
    else
      echo "ROLE_UNRESOLVED role=$role (agents.yaml)" | tee -a "$failure_log" >&2
      rm -f "$tmp_result" "$result"
      return 36
    fi
    fallback="$(role_runtime_fallback "$role" "$backend")"
  fi

  # Handoff ajanı headless çalıştırılamaz: görev paketi üretilir, aşama
  # WAITING_AGENT'ta durur. Tam otomasyon varmış gibi davranılmaz.
  if roles_handoff_agent "$backend"; then
    HANDOFF_AGENT="$backend"
    HANDOFF_ROLE="$role"
    HANDOFF_FILE="$(handoff_write "$role" "$backend" "$input")"
    {
      echo "ROLE=$role"
      echo "AGENT=$backend"
      echo "MODE=handoff"
      echo "HANDOFF_FILE=$HANDOFF_FILE"
      echo "FALLBACK_REASON=${ROLE_RESOLUTION_REASON:-none}"
      echo "CREATED_AT=$(now)"
    } | tee -a "$stdout_log"
    rm -f "$tmp_result"
    return 38
  fi

  {
    echo "ROLE_AGENT=$backend"
    echo "ROLE_RUNTIME_FALLBACK=${fallback:-none}"
    echo "ROLE_FALLBACK_REASON=${ROLE_RESOLUTION_REASON:-none}"
  } | tee -a "$stdout_log"

  agent_attempt "$backend" "$role" "$input" "$tmp_result" "$stdout_log" "$stderr_log"
  rc=$?

  if [[ "$rc" -eq 35 ]]; then
    echo "Bilinmeyen ajan backend=${backend} (codex|claude)." | tee -a "$failure_log" >&2
    rm -f "$tmp_result" "$result"
    return 35
  fi

  # Sağlayıcıya hiç ulaşılamadıysa aynı aşama diğer backend ile BİR kez tekrarlanır
  # (fresh süreç, aynı girdi, aynı doğrulama). Birincil denemenin stderr kanıtı
  # silinmez; devir stdout ve failure loguna açıkça yazılır.
  if [[ -n "$fallback" ]] && [[ "$fallback" != "$backend" ]] \
     && { [[ "$rc" -ne 0 ]] || [[ ! -s "$tmp_result" ]]; } \
     && agent_provider_unavailable "$stderr_log" "$rc" "$tmp_result"; then
    if agent_backend_known "$fallback"; then
      {
        echo "FALLBACK_FROM=${backend}"
        echo "FALLBACK_TO=$fallback"
        echo "FALLBACK_REASON=provider_unavailable"
        echo "FALLBACK_PRIMARY_EXIT=$rc"
      } | tee -a "$stdout_log" >> "$failure_log"
      # Etkin ajan değişti: defter ve review kaydı gerçekten çalışanı göstermeli.
      ROLE_RESOLUTION_REASON="runtime_provider_unavailable: ${backend} exit=${rc}"
      backend="$fallback"
      agent_attempt "$fallback" "$role" "$input" "$tmp_result" "$stdout_log" "$stderr_log"
      rc=$?
    else
      echo "Yedek ajan bilinmiyor: $fallback; devir denenmedi." \
        | tee -a "$failure_log" >&2
    fi
  fi

  ROLE_EFFECTIVE_AGENT="$backend"

  agent_cap_log "$stderr_log" "${AGENT_STDERR_LOG_MAX_BYTES}"

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

# Geriye dönük ad. Eski çağrı yüzeyi korunur; backend AGENT_BACKEND ile seçilir.
run_codex() {
  run_agent "$@"
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

# S06: Önceki turdan hata kanıtlarını topla — model aynı hatayı tekrarlamasın.
# Yalnızca çözülmüş ve bir daha ilgili olmayan hatalar yok sayılabilir.
collect_error_evidence() {
  local iteration="$1"
  local prev=$((iteration - 1))
  (( prev > 0 )) || return 0
  local found=0
  for f in "$LOGS"/implementer-i${prev}-*.stderr.log; do
    [[ -s "$f" ]] || continue
    if (( found == 0 )); then
      printf '\n## Error Evidence (iteration %d — do not repeat)\n\n' "$prev"
      found=1
    fi
    printf '```\n'
    tail -n 80 "$f"
    printf '\n```\n\n'
  done
}

# S12: Tool çıktısını biçim varyasyonu ile serileştir.
# Format varyasyonu KV-cache prefix'ini etkilemez; değişken içerik prompt'un
# sonunda tutulur (bkz. Evidence-Injection-Rehberi.md).
#
# Parametreler:
#   $1 - tool_name: Tool'un adı (örn: "pytest", "git_diff")
#   $2 - output: Tool çıktısı (stdin'den de okunabilir)
#   $3 - format_variant: 0, 1 veya 2 (RANDOM % 3 ile seçilir)
#
# Formatlar:
#   0 - Blok kod (varsayılan, en ayrıntılı)
#   1 - Inline özet (kısa, tek satır)
#   2 - YAML metadata + içerik (yapılandırılmış)
serialize_tool_output() {
  local tool_name="$1"
  local output="$2"
  local format_variant="${3:-0}"
  local line_count

  line_count="$(printf '%s' "$output" | wc -l)"

  case "$format_variant" in
    0)
      # Format 0: Blok kod (varsayılan)
      printf '\n## Tool Output: %s\n\n' "$tool_name"
      printf '```\n'
      printf '%s' "$output"
      printf '\n```\n'
      ;;
    1)
      # Format 1: Inline özet (kısa)
      local first_line
      first_line="$(printf '%s' "$output" | head -n 1 | head -c 120)"
      printf '\nTool çıktısı (%s): %s (toplam %d satır)\n' \
        "$tool_name" "$first_line" "$line_count"
      ;;
    2)
      # Format 2: YAML metadata + içerik
      local truncated="false"
      (( line_count > 100 )) && truncated="true"
      printf '\n---\n'
      printf 'tool: %s\n' "$tool_name"
      printf 'lines: %d\n' "$line_count"
      printf 'truncated: %s\n' "$truncated"
      printf '---\n'
      printf '%s' "$output"
      printf '\n'
      ;;
    *)
      # Bilinmeyen format: Format 0'a düş
      printf '\n## Tool Output: %s\n\n' "$tool_name"
      printf '```\n%s\n```\n' "$output"
      ;;
  esac
}

# Rastgele format varyasyonu seç (0, 1 veya 2).
# RANDOM % 3 kullanılır; deterministik tohum kullanılmaz çünkü amaç
# KV-cache koruma değil, modelin pattern matching davranışını kırmaktır.
random_format_variant() {
  echo $(( RANDOM % 3 ))
}

# S08: Graph-ranked kod bağlamı seçimi.
# Kişiselleştirilmiş PageRank ile seed tanımlayıcılara en ilgili kod bloklarını
# bulur ve prompt'a ekler. Kill-switch: AGENT_GRAPH_CONTEXT=0 ile kapatılabilir.
#
# Parametreler:
#   $1 - seeds: Virgülle ayrılmış seed düğüm kimlikleri (örn: scope hint'ler)
#   $2 - budget: Maksimum bayt bütçesi (varsayılan: 4000)
#
# Çıktı: JSON dizisi (boş dizi = ilgili bağlam bulunamadı).
select_relevant_code() {
  local seeds="$1"
  local budget="${2:-4000}"
  # Kill-switch: graph context tamamen kapatılabilir.
  [[ "${AGENT_GRAPH_CONTEXT:-1}" == "1" ]] || return 0
  [[ -n "$seeds" ]] || return 0

  local script="$ROOT/scripts/compute_pagerank.py"
  [[ -f "$script" ]] || return 0

  local graph_file="$ROOT/graphify-out/graph.json"
  [[ -f "$graph_file" ]] || return 0

  # networkx yoksa sessizce çık (graceful degradation).
  python3 "$script" --seeds "$seeds" --budget "$budget" \
    --graph "$graph_file" 2>/dev/null || true
}

# S03: Hedef tekrarlama (recitation) — her N turda bir aktif hedef özetini
# prompt'a ekleyerek ajanın görevden sapmasını önler.
# AGENT_RECITATION=0 ile tamamen kapatılabilir (kill-switch).
should_recite_goal() {
  local iteration="$1"
  # Kill-switch: recitation tamamen kapatılabilir.
  [[ "${AGENT_RECITATION:-1}" == "1" ]] || return 1
  local interval="${AGENT_LOOP_RECITATION_INTERVAL:-5}"
  (( iteration > 0 && iteration % interval == 0 ))
}

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
    if ! postgres_preflight | tee "$LOGS/postgres-preflight-i${iteration}-r${repair}.log"; then
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
    # S06: Önceki turdan hata kanıtlarını ekle
    collect_error_evidence "$iteration"
    # S08: Graph-ranked ilgili kod bağlamı (scope hint'leri seed olarak kullan).
    if [[ -n "${SELECTED_SCOPE_HINT:-}" ]]; then
      local graph_ctx
      graph_ctx="$(select_relevant_code "$SELECTED_SCOPE_HINT" 4000)"
      if [[ -n "$graph_ctx" && "$graph_ctx" != "[]" && "$graph_ctx" != "null" ]]; then
        printf '\n## Graph-Ranked Code Context (S08)\n\n'
        printf '%s\n' "$graph_ctx"
      fi
    fi
    # S03: Her N turda hedef tekrarlama (recitation) — ajanın sapmasını önler.
    if should_recite_goal "$iteration"; then
      printf '\n## ACTIVE GOAL REMINDER\n\n'
      printf 'Objective: %s\n\n' "$(jq -r '.task.objective' "$TASK")"
      printf 'Acceptance criteria still to satisfy:\n'
      jq -r '.acceptance_criteria[] | "- [ ] \(.requirement)"' "$TASK"
      printf '\nFocus on the above. Do not drift.\n'
    fi
  } > "$input"

  echo "[1/3] Fresh $(role_label implementer) implementer"

  # S09: Prompt bütçe aşımında katmanlı sıkıştırma uygula.
  # Orijinal input korunur; sıkıştırılmış versiyonu .compacted.md uzantısıyla
  # yazılır. Bilgi kaybı şeffaftır (bkz. Context-Compaction-Politikasi.md).
  if compaction_needed "$input"; then
    local compacted="${input%.md}.compacted.md"
    compact_prompt "$input" "$compacted"
    compaction_report "$input" "$compacted" >> "$LOGS/compaction.log"
    echo "[compaction] Bütçe aşımı tespit edildi; sıkıştırma uygulandı."
    input="$compacted"
  fi

  run_agent "implementer" "$input" "$result" '^STATUS: SUCCESS$'
  rc=$?

  # 38 = handoff bekliyor: uygulayıcı otomatik çalıştırılamayan bir ajandır
  # (Qoder). Görev paketi üretildi; operatör IDE'de çalıştırır. Durum kalıcıdır.
  if [[ "$rc" -eq 38 ]]; then
    # Parmak izi taban çizgisi tur başına BİR KEZ alınır. Paket yeniden
    # üretildiğinde yeniden alınırsa, ajan işi paketten önce yapmışsa taban
    # çizgisi o işi içerir ve beyan hiçbir zaman doğrulanamaz. Sıfırlama
    # noktaları: yeni görev (start_new_task) ve yeni onarım turu.
    state_patch '
      .stage = "IMPLEMENTER" | .status = "WAITING_AGENT"
      | .handoff_file = $file | .handoff_agent = $agent
      | .handoff_fingerprint = (
          if .handoff_fingerprint == null then $fp else .handoff_fingerprint end
        )
      | .last_error = null | .updated_at = $now
    ' --arg file "$HANDOFF_FILE" --arg agent "$HANDOFF_AGENT" \
      --arg fp "$(worktree_fingerprint)" --arg now "$(now)"
    LEDGER_IMPLEMENTER_AGENT="$HANDOFF_AGENT"
    LEDGER_FALLBACK_REASON="${ROLE_RESOLUTION_REASON:-none}"
    ledger_sync >/dev/null
    echo
    echo "Uygulayıcı rolü $(roles_agent_label "$HANDOFF_AGENT") ajanına devredildi."
    echo "Neden: ${ROLE_RESOLUTION_REASON:-yapılandırma}"
    echo "Görev paketi: ${HANDOFF_FILE#"$ROOT"/}"
    echo
    echo "Sıradaki adım: paketi $(roles_agent_label "$HANDOFF_AGENT") içinde çalıştır, sonra:"
    echo "  devam \"qoder tamam\"      (uygulandıysa; controller testleri kendisi çalıştırır)"
    echo "  devam \"blocked: <neden>\"  (ajan mimari karar gerekiyor dediyse)"
    return 0
  fi

  if [[ "$rc" -ne 0 ]]; then
    state_update "IMPLEMENTER" "FAILED" "Implementer başarısız; loglar kaydedildi."
    ledger_sync >/dev/null
    return "$rc"
  fi
  rm -f "$H/HUMAN_RESPONSE.md"
  LEDGER_IMPLEMENTER_AGENT="${ROLE_EFFECTIVE_AGENT:-}"
  LEDGER_FALLBACK_REASON="${ROLE_RESOLUTION_REASON:-none}"
  state_update "TESTER" "READY" ""
  ledger_sync >/dev/null
  return 0
}

run_tests() {
  local iteration repair unit_log integration_log unit_rc integration_rc skipped report
  local need_pg targets t task_id unit_cmd integration_cmd started duration
  local unit_evidence integration_evidence pg_log
  task_id="$(ledger_task_id)"
  iteration="$(state_field iteration)"
  # Log adları onarım turunu İÇERMEK ZORUNDA: run_logged_test hedefi truncate
  # ettiği için, tur numarası yoksa onarım turu 1 turu 0'ın stack trace'ini
  # siler. O kanıt onarım promptunun tek girdisidir (bkz. run_implementer).
  repair="$(state_field repair_round)"
  unit_log="$LOGS/unit-tests-i${iteration}-r${repair}.log"
  integration_log="$LOGS/integration-tests-i${iteration}-r${repair}.log"
  report="$H/TEST_REPORT.md"

  refresh_contract
  echo "[2/3] Controller test gates"

  # Unit testler her zaman.
  unit_cmd="python3 -m pytest -q -p no:cacheprovider $UNIT_TEST_DIR"
  started="$SECONDS"
  run_logged_test "$unit_log" python3 -m pytest -q -p no:cacheprovider "$UNIT_TEST_DIR"
  unit_rc=$?
  duration=$(( SECONDS - started ))
  unit_evidence="$(evidence_write "$task_id" "unit" "$unit_cmd" "$unit_rc" "$duration" \
    "$unit_log" "Birim testleri controller kabuğunda çalıştırıldı; dış servis gerekmez.")"

  integration_rc=0
  skipped="n/a"
  integration_evidence=""
  if integration_required; then
    need_pg=yes
    # Entegrasyon gerekiyorsa PG preflight zorunlu; başarısızsa SAHTE PASS YOK.
    pg_log="$LOGS/postgres-preflight-tests-i${iteration}-r${repair}.log"
    if ! postgres_preflight | tee "$pg_log"; then
      # Ortam yokluğu ürün hatası DEĞİLDİR: kanıt ENVIRONMENT_FAILURE olarak yazılır.
      evidence_write "$task_id" "integration" \
        "postgres_preflight (entegrasyon öncesi zorunlu kapı)" 1 0 "$pg_log" \
        "PostgreSQL erişilemedi; ENVIRONMENT_FAILURE. Ürün hatası olarak raporlanmaz." \
        "ENVIRONMENT_FAILURE" >/dev/null
      state_update "TESTER" "FAILED" "PostgreSQL preflight başarısız; entegrasyon PASS sayılamaz (ENVIRONMENT_BLOCK)."
      ledger_sync >/dev/null
      return 1
    fi
    mapfile -t targets < <(discover_integration_targets)
    integration_cmd="python3 -m pytest -q -p no:cacheprovider ${targets[*]}"
    started="$SECONDS"
    run_logged_test "$integration_log" python3 -m pytest -q -p no:cacheprovider "${targets[@]}"
    integration_rc=$?
    duration=$(( SECONDS - started ))
    if integration_has_skips "$integration_log"; then
      skipped="yes"
    else
      skipped="no"
    fi
    integration_evidence="$(evidence_write "$task_id" "integration" "$integration_cmd" \
      "$integration_rc" "$duration" "$integration_log" \
      "PG preflight geçti. Zorunlu entegrasyonda skip tespiti: $skipped")"
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
    echo "Command: $unit_cmd"
    echo "Exit code: $unit_rc"
    echo "Log: $unit_log"
    echo "Failure class: $(classify_test_failure "$unit_log" "$unit_rc")"
    echo "Evidence: ${unit_evidence:-none}"
    echo
    echo "## Integration tests"
    if [[ "$need_pg" == "yes" ]]; then
      echo "Targets: $(discover_integration_targets | tr '\n' ' ')"
      echo "Exit code: $integration_rc"
      echo "Skipped detected: $skipped"
      echo "Log: $integration_log"
      echo "Failure class: $(classify_test_failure "$integration_log" "$integration_rc")"
      echo "Evidence: ${integration_evidence:-none}"
    else
      echo "Bu görev PostgreSQL/entegrasyon etkisi içermiyor; entegrasyon kapısı çalıştırılmadı."
    fi
  } > "$report"

  if [[ "$unit_rc" -ne 0 ]]; then
    state_update "TESTER" "FAILED" \
      "Birim testleri başarısız ($(classify_test_failure "$unit_log" "$unit_rc"))."
    ledger_sync >/dev/null
    return 1
  fi
  if [[ "$integration_rc" -ne 0 ]]; then
    state_update "TESTER" "FAILED" \
      "PostgreSQL entegrasyon testleri başarısız ($(classify_test_failure "$integration_log" "$integration_rc"))."
    ledger_sync >/dev/null
    return 1
  fi
  if [[ "$skipped" == "yes" ]]; then
    state_update "TESTER" "FAILED" "Zorunlu entegrasyon testlerinde skip tespit edildi."
    ledger_sync >/dev/null
    return 1
  fi

  state_update "REVIEWER" "READY" ""
  ledger_sync >/dev/null
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

  echo "[3/3] Fresh $(role_label reviewer) reviewer"
  run_agent "reviewer" "$input" "$result" '^STATUS: (APPROVED|CHANGES_REQUIRED|HUMAN_DECISION)$'
  rc=$?
  if [[ "$rc" -ne 0 ]]; then
    state_update "REVIEWER" "FAILED" "Reviewer başarısız; loglar kaydedildi."
    ledger_sync >/dev/null
    return "$rc"
  fi

  first_line="$(head -n 1 "$result" | tr -d '\r')"
  local task_id
  task_id="$(ledger_task_id)"
  case "$first_line" in
    "STATUS: APPROVED")
      review_record "$task_id" "APPROVED" >/dev/null
      state_update "COMPLETED" "COMPLETED" ""
      ledger_sync >/dev/null
      # Görev kapandı: claim serbest bırakılır, aynı görev tekrar claim edilebilir.
      claim_release "$task_id" || true
      echo; echo "Tamamlandı ve bağımsız review ile onaylandı."
      ;;
    "STATUS: CHANGES_REQUIRED")
      review_record "$task_id" "CHANGES_REQUESTED" >/dev/null
      next_repair=$((repair + 1))
      if (( next_repair > MAX_REPAIR_ROUNDS )); then
        state_update "REVIEWER" "WAITING_HUMAN" "Azami otomatik onarım turu aşıldı."
        ledger_sync >/dev/null
        echo; echo "İnsan kararı gerekiyor. Yanıt: devam \"kararın\""
        return 0
      fi
      state_patch '
        .repair_round = $repair
        | .stage = "IMPLEMENTER"
        | .status = "READY"
        | .handoff_fingerprint = null
        | .last_error = null
        | .updated_at = $now
      ' --argjson repair "$next_repair" --arg now "$(now)"
      ledger_sync >/dev/null
      echo "Reviewer düzeltme istedi; otomatik onarım turu: $next_repair"
      ;;
    "STATUS: HUMAN_DECISION")
      review_record "$task_id" "HUMAN_DECISION" >/dev/null
      state_update "REVIEWER" "WAITING_HUMAN" "Reviewer insan kararı istedi."
      ledger_sync >/dev/null
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
          | grep -E '^(docs/srs|src|frontend|tests)/' \
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
  run_agent "planner" "$input" "$result" '^STATUS: (READY|NO_TASK)$'
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
          {id:"AC-07", requirement:"Reviewer güncel kod, test ve kaynak dokümanlar üzerinden onay vermelidir."},
          {id:"AC-08", requirement:"Teslim edilen modül composition kökünde kayıtlı olmalı ve en az bir üretim çağrı yolundan erişilebilir olmalıdır; yalnız testlerden çağrılan modül tamamlanmış sayılmaz."}
        ],
        runtime_rules: [
          "Her agent aşaması fresh agent süreci ile başlatılır.",
          "Eski agent sessionları resume edilmez.",
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
    | .handoff_file = null
    | .handoff_agent = null
    | .handoff_fingerprint = null
    | .updated_at = $now
  ' --argjson iteration "$iteration" --arg now "$now_value"

  # Claim: aynı görevi ikinci bir uygulayıcı (başka worktree/süreç) alamaz.
  # Kilit ortak git dizinindedir, çalışma ağacına yazılmaz.
  LEDGER_IMPLEMENTER_AGENT=""
  LEDGER_FALLBACK_REASON=""
  if ! claim_acquire "$task_id" "$(_ledger_role_agent implementer)"; then
    state_update "IMPLEMENTER" "WAITING_HUMAN" "Görev $task_id başka bir worktree tarafından claim edilmiş."
    echo "Görev claim edilemedi; ikinci uygulayıcı başlatılmadı." >&2
    return 37
  fi
  ledger_sync >/dev/null

  echo "Yeni iterasyon oluşturuldu: $iteration"
  echo "Görev: $title ($task_id)"
  echo "Uygulayıcı: $(role_label implementer) | Testçi: $(role_label tester) | Reviewer: $(role_label reviewer)"
}

# --- handoff'tan dönüş ------------------------------------------------------

# Handoff ajanı (Qoder) görevi IDE'de uyguladıktan sonra operatör `devam "..."`
# der. Uygulama BEYANI kanıt sayılmaz:
#   - çalışma ağacı parmak izi değişmediyse uygulama yoktur (aşama ilerlemez),
#   - değiştiyse controller kendi test kapılarını çalıştırır (TESTER),
#   - onay yine bağımsız reviewer ajanındadır.
resume_from_handoff() {
  local note="$1" file agent fp_before fp_now task_id
  file="$(state_field handoff_file)"
  agent="$(state_field handoff_agent)"
  fp_before="$(state_field handoff_fingerprint)"
  task_id="$(ledger_task_id)"

  if [[ -z "$note" ]]; then
    echo "Uygulayıcı rolü $(roles_agent_label "${agent:-handoff}") ajanında bekliyor."
    echo "Görev paketi: ${file#"$ROOT"/}"
    echo
    echo "Paketi ajana ver, işi bitince:"
    echo "  devam \"qoder tamam\"       (uygulama yapıldıysa)"
    echo "  devam \"blocked: <neden>\"   (ajan mimari karar gerekiyor dediyse)"
    return 1
  fi

  # Ajan belirsizlikte karar almaz: BLOCKED insan kararına gider.
  if [[ "$note" =~ ^[[:space:]]*(blocked|BLOCKED|engellendi) ]]; then
    printf '%s\n' "$note" > "$H/HANDOFF_RESULT.md"
    state_update "IMPLEMENTER" "WAITING_HUMAN" "Handoff ajanı BLOCKED bildirdi: $note"
    ledger_sync >/dev/null
    echo "Görev BLOCKED olarak işaretlendi; insan kararı bekleniyor."
    echo 'Karar vermek için: devam "kararın"'
    return 1
  fi

  fp_now="$(worktree_fingerprint)"
  if [[ -n "$fp_before" && "$fp_before" != "null" && "$fp_before" == "$fp_now" ]]; then
    echo "Çalışma ağacında değişiklik yok: '$note' beyanı doğrulanamadı." >&2
    echo "Uygulama gerçekten yapıldıysa dosyaları kaydettiğinden emin ol." >&2
    echo "Aşama WAITING_AGENT'ta bırakıldı; sahte ilerleme üretilmedi." >&2
    state_update "IMPLEMENTER" "WAITING_AGENT" "Handoff beyanı doğrulanamadı: çalışma ağacı değişmedi."
    ledger_sync >/dev/null
    return 1
  fi

  {
    printf 'STATUS: SUCCESS\n\n'
    printf '# Handoff uygulama sonucu (%s)\n\n' "$(roles_agent_label "${agent:-handoff}")"
    printf 'Operatör beyanı: %s\n\n' "$note"
    printf 'Görev paketi: `%s`\n\n' "${file#"$ROOT"/}"
    printf 'Doğrulama: çalışma ağacı parmak izi değişti (beyan tek başına yeterli değildir).\n'
    printf 'Öncesi: `%s`\nSonrası: `%s`\n\n' "${fp_before:0:12}" "${fp_now:0:12}"
    printf '## Değişen dosyalar (controller tespiti)\n\n```text\n'
    git -C "$ROOT" status --short
    printf '```\n'
  } > "$H/CODEX_RESULT.md"
  cp -f "$H/CODEX_RESULT.md" "$H/HANDOFF_RESULT.md"

  # Handoff dosyasının durumunu güncelle (izlenen kanıt: paket tüketildi).
  if [[ -n "$file" && "$file" != "null" && -f "$file" ]]; then
    sed -i 's/^status: PENDING$/status: IMPLEMENTED/' "$file"
  fi

  LEDGER_IMPLEMENTER_AGENT="${agent:-}"
  LEDGER_FALLBACK_REASON="handoff"
  rm -f "$H/HUMAN_RESPONSE.md"
  state_update "TESTER" "READY" ""
  ledger_sync >/dev/null
  echo "Handoff uygulaması alındı; controller test kapıları çalıştırılıyor."
  return 0
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
        "$PLANNED_SOURCE_DOCS" "$PLANNED_PRIORITY_REASON" "automatic" || return $?
    else
      start_new_task "$note" "" "$note" "" "Operator tarafından doğrudan verildi." "manual" || return $?
    fi
  elif [[ "$status" == "WAITING_AGENT" ]]; then
    # Operatör eylemi bekleniyor: temiz çıkış (WAITING_HUMAN ile aynı sözleşme).
    resume_from_handoff "$note" || return 0
  elif [[ "$status" == "WAITING_HUMAN" ]]; then
    if [[ -z "$note" ]]; then
      echo "İnsan kararı bekleniyor (varsayılan pencere ${HUMAN_WAIT_SECONDS}s; state kalıcı, süre sınırı yok)."
      echo
      cat "$H/ARCHITECT_REVIEW.md" 2>/dev/null || cat "$H/NEXT_TASK.md" 2>/dev/null || true
      echo; echo 'Yanıt vermek için: devam "kararın veya görevin"'
      return 0
    fi
    if [[ "$stage" == "PLANNER" ]]; then
      start_new_task "$note" "" "$note" "" "Planner görev bulamadığı için operatör tarafından verildi." "manual" || return $?
    else
      printf '%s\n' "$note" > "$H/HUMAN_RESPONSE.md"
      # İnsan kararı onarım kilidini kırar: taze onarım bütçesiyle başla.
      state_patch '
        .stage = "IMPLEMENTER" | .status = "READY"
        | .repair_round = 0 | .handoff_fingerprint = null
        | .last_error = null | .updated_at = $now
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
      WAITING_AGENT:*)
        # Handoff ajanı (Qoder) bekliyor: controller yeni yazıcı başlatmaz.
        echo "Handoff ajanı bekleniyor. Paket: $(state_field handoff_file)"
        echo 'İş bitince: devam "qoder tamam"'
        return 0 ;;
      WAITING_HUMAN:*)
        echo "İnsan kararı bekleniyor. Yanıt: devam \"kararın veya görevin\""
        return 0 ;;
      *)
        echo "Beklenmeyen state: status=$status stage=$stage" >&2
        return 70 ;;
    esac
  done
}
