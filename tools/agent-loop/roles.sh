#!/usr/bin/env bash
# tools/agent-loop/roles.sh
#
# Ajan rol çözümü. Bu dosya SIDE-EFFECT ÜRETMEZ: yalnız fonksiyon tanımlar.
#
# Canonical rol kaynağı TEK dosyadır: .agent/config/agents.yaml
# Rol → ajan eşlemesi başka hiçbir yerde tanımlanmaz; dokümanlar bu dosyaya
# referans verir.
#
# Tasarım ilkeleri:
#   - Rol sabit, ajan değişkendir. Codex kotası bittiğinde MİMARİ değişmez;
#     yalnız agents.yaml `runtime.codex_available` alanı değişir.
#   - Belirsizlik fail-closed'dur: config varsa ve ayrıştırılamıyorsa hiçbir ajan
#     çalıştırılmaz (exit 36). Sessizce eski davranışa düşülmez.
#   - Handoff ajanı (Qoder) otomatik çalıştırılamaz; controller onun için görev
#     paketi üretir ve WAITING_AGENT durumunda durur.
#
# shellcheck shell=bash

# --- ajan kaydı -------------------------------------------------------------

# Bilinen ajanlar. Yeni ajan eklemek buraya + agent_attempt'e dokunmayı gerektirir.
roles_known_agent() {
  case "$1" in
    codex|claude|qoder) return 0 ;;
    *)                  return 1 ;;
  esac
}

# Otomatik (headless) çalıştırılabilen ajanlar: controller süreç başlatır.
roles_runnable_agent() {
  case "$1" in
    codex|claude) return 0 ;;
    *)            return 1 ;;
  esac
}

# Handoff ajanı: CLI ile headless çalıştırılamaz (Qoder Pro IDE tabanlıdır).
# Controller görev paketi üretir, operatör IDE'de çalıştırır, sonuç controller
# test kapılarıyla doğrulanır. Tam otomasyon varmış gibi davranılmaz.
roles_handoff_agent() {
  case "$1" in
    qoder) return 0 ;;
    *)     return 1 ;;
  esac
}

roles_agent_label() {
  case "$1" in
    claude) printf 'Claude' ;;
    codex)  printf 'Codex' ;;
    qoder)  printf 'Qoder' ;;
    *)      printf '%s' "$1" ;;
  esac
}

# --- yapılandırma ayrıştırma ------------------------------------------------

# agents.yaml'ın desteklenen alt kümesi:
#   key: value                  (tek seviye)
#   parent:                     (blok başlığı)
#     key: value                (iki seviye -> parent.key)
#   # yorum satırları ve satır sonu yorumları
# Liste, çok satırlı değer, anchor veya üç seviye desteklenmez; karşılaşılırsa
# fail-closed hata döner (sessiz yanlış yorumlama yerine açık hata).
_roles_flatten() {
  awk '
    {
      line = $0
      sub(/[[:space:]]*#.*$/, "", line)
      if (line ~ /^[[:space:]]*$/) next
      if (line ~ /^---[[:space:]]*$/) next

      if (line ~ /^[A-Za-z_][A-Za-z0-9_]*:[[:space:]]*$/) {
        parent = line; sub(/:.*$/, "", parent); next
      }
      if (line ~ /^[A-Za-z_][A-Za-z0-9_]*:[[:space:]]*[^[:space:]]/) {
        k = line; sub(/:.*$/, "", k)
        v = line; sub(/^[^:]*:[[:space:]]*/, "", v)
        sub(/[[:space:]]+$/, "", v); gsub(/^"|"$/, "", v); gsub(/^'\''|'\''$/, "", v)
        parent = ""
        print k "=" v
        next
      }
      if (line ~ /^[[:space:]]+[A-Za-z_][A-Za-z0-9_]*:[[:space:]]*[^[:space:]]/) {
        if (parent == "") { print "__ERROR__=nested_key_without_parent"; exit 1 }
        k = line; sub(/^[[:space:]]+/, "", k); sub(/:.*$/, "", k)
        v = line; sub(/^[[:space:]]*[^:]*:[[:space:]]*/, "", v)
        sub(/[[:space:]]+$/, "", v); gsub(/^"|"$/, "", v); gsub(/^'\''|'\''$/, "", v)
        print parent "." k "=" v
        next
      }
      print "__ERROR__=unsupported_yaml_line"; exit 1
    }' "$1"
}

roles_reset() {
  ROLES_LOADED=0
  ROLES_FILE_USED=""
  ROLE_ARCHITECT=""
  ROLE_REVIEWER=""
  ROLE_IMPLEMENTER_PRIMARY=""
  ROLE_IMPLEMENTER_FALLBACK=""
  ROLE_TESTER_PRIMARY=""
  ROLE_TESTER_FALLBACK=""
  RUNTIME_CODEX_AVAILABLE="true"
  RUNTIME_FALLBACK_ON_QUOTA_ERROR="false"
  RUNTIME_PREVENT_PARALLEL_WRITERS="true"
  ROLE_RESOLUTION_REASON=""
}

_roles_bool() {
  case "$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')" in
    true|yes|1)  printf 'true' ;;
    false|no|0)  printf 'false' ;;
    *)           printf 'invalid' ;;
  esac
}

# roles_load [dosya]
#   0  -> yüklendi ve doğrulandı (ROLES_LOADED=1)
#   1  -> dosya yok (legacy AGENT_BACKEND yolu kullanılabilir)
#   2  -> dosya var ama geçersiz (FAIL-CLOSED: çağıran ajan çalıştırmamalı)
roles_load() {
  local file="${1:-${AGENT_ROLES_FILE:-}}" flat line key value bad=""
  roles_reset
  [[ -n "$file" ]] || return 1
  [[ -f "$file" ]] || return 1

  if ! flat="$(_roles_flatten "$file" 2>/dev/null)"; then
    echo "agents.yaml ayrıştırılamadı (desteklenmeyen sözdizimi): $file" >&2
    return 2
  fi
  if [[ "$flat" == *"__ERROR__="* ]]; then
    echo "agents.yaml ayrıştırılamadı: $file ($(printf '%s' "$flat" | grep -o '__ERROR__=.*' | head -n 1))" >&2
    return 2
  fi

  while IFS= read -r line; do
    [[ -n "$line" ]] || continue
    key="${line%%=*}"
    value="${line#*=}"
    case "$key" in
      architect)             ROLE_ARCHITECT="$value" ;;
      reviewer)              ROLE_REVIEWER="$value" ;;
      implementer.primary)   ROLE_IMPLEMENTER_PRIMARY="$value" ;;
      implementer.fallback)  ROLE_IMPLEMENTER_FALLBACK="$value" ;;
      tester.primary)        ROLE_TESTER_PRIMARY="$value" ;;
      tester.fallback)       ROLE_TESTER_FALLBACK="$value" ;;
      runtime.codex_available)           RUNTIME_CODEX_AVAILABLE="$(_roles_bool "$value")" ;;
      runtime.fallback_on_quota_error)   RUNTIME_FALLBACK_ON_QUOTA_ERROR="$(_roles_bool "$value")" ;;
      runtime.prevent_parallel_writers)  RUNTIME_PREVENT_PARALLEL_WRITERS="$(_roles_bool "$value")" ;;
      schema_version|description)        : ;;
      *) bad="${bad}bilinmeyen alan: $key; " ;;
    esac
  done <<< "$flat"

  # --- doğrulama (fail-closed) ---
  local r
  for r in ROLE_ARCHITECT ROLE_REVIEWER ROLE_IMPLEMENTER_PRIMARY ROLE_TESTER_PRIMARY; do
    if [[ -z "${!r}" ]]; then bad="${bad}zorunlu alan boş: $r; "; fi
  done
  for r in ROLE_ARCHITECT ROLE_REVIEWER ROLE_IMPLEMENTER_PRIMARY ROLE_IMPLEMENTER_FALLBACK \
           ROLE_TESTER_PRIMARY ROLE_TESTER_FALLBACK; do
    if [[ -n "${!r}" ]] && ! roles_known_agent "${!r}"; then
      bad="${bad}bilinmeyen ajan: $r=${!r}; "
    fi
  done
  # Mimar ve reviewer otomatik çalışmak zorundadır: bağımsız review handoff'a
  # bırakılamaz (uygulayıcı kendi işini onaylamış olurdu).
  for r in ROLE_ARCHITECT ROLE_REVIEWER; do
    if [[ -n "${!r}" ]] && ! roles_runnable_agent "${!r}"; then
      bad="${bad}$r otomatik çalıştırılabilir bir ajan olmalı (codex|claude), verilen: ${!r}; "
    fi
  done
  for r in RUNTIME_CODEX_AVAILABLE RUNTIME_FALLBACK_ON_QUOTA_ERROR RUNTIME_PREVENT_PARALLEL_WRITERS; do
    if [[ "${!r}" == "invalid" ]]; then bad="${bad}boolean beklenirdi: $r; "; fi
  done

  if [[ -n "$bad" ]]; then
    echo "agents.yaml geçersiz: ${bad%; }" >&2
    roles_reset
    return 2
  fi

  ROLES_LOADED=1
  ROLES_FILE_USED="$file"
  return 0
}

roles_active() {
  [[ "${ROLES_LOADED:-0}" == "1" ]]
}

# Ajan gerçekten kullanılabilir mi? (yapılandırma + binary varlığı)
roles_agent_usable() {
  local agent="$1"
  case "$agent" in
    codex)
      [[ "${RUNTIME_CODEX_AVAILABLE:-true}" == "true" ]] || return 1
      command -v "${CODEX_BIN:-codex}" >/dev/null 2>&1 || return 1
      return 0 ;;
    claude)
      command -v "${CLAUDE_BIN:-claude}" >/dev/null 2>&1 || return 1
      return 0 ;;
    qoder)
      # Handoff ajanı için CLI gerekmez; görev paketi her zaman üretilebilir.
      return 0 ;;
    *) return 1 ;;
  esac
}

roles_agent_unusable_reason() {
  local agent="$1"
  case "$agent" in
    codex)
      [[ "${RUNTIME_CODEX_AVAILABLE:-true}" == "true" ]] \
        || { printf 'codex_marked_unavailable (agents.yaml runtime.codex_available=false)'; return 0; }
      command -v "${CODEX_BIN:-codex}" >/dev/null 2>&1 \
        || { printf 'codex_binary_missing (%s)' "${CODEX_BIN:-codex}"; return 0; }
      ;;
    claude)
      command -v "${CLAUDE_BIN:-claude}" >/dev/null 2>&1 \
        || { printf 'claude_binary_missing (%s)' "${CLAUDE_BIN:-claude}"; return 0; }
      ;;
  esac
  printf 'unknown'
}

# role_resolve <planner|implementer|tester|reviewer>
# Rolü karşılayan ajanı GLOBAL değişkenlere yazar (subshell kullanılmaz, çünkü
# fallback nedeni çağırana ulaşmak zorundadır):
#   RESOLVED_AGENT           seçilen ajan
#   RESOLVED_ROLE_PRIMARY    yapılandırmadaki birincil ajan
#   ROLE_RESOLUTION_REASON   yedeğe düşülduyse neden, aksi halde boş
role_resolve() {
  local role="$1" primary="" fallback=""
  RESOLVED_AGENT=""
  RESOLVED_ROLE_PRIMARY=""
  ROLE_RESOLUTION_REASON=""

  case "$role" in
    planner|architect) primary="$ROLE_ARCHITECT" ;;
    reviewer)          primary="$ROLE_REVIEWER" ;;
    implementer)       primary="$ROLE_IMPLEMENTER_PRIMARY"; fallback="$ROLE_IMPLEMENTER_FALLBACK" ;;
    tester)            primary="$ROLE_TESTER_PRIMARY";      fallback="$ROLE_TESTER_FALLBACK" ;;
    *) echo "Bilinmeyen rol: $role" >&2; return 1 ;;
  esac

  RESOLVED_ROLE_PRIMARY="$primary"

  if roles_agent_usable "$primary"; then
    RESOLVED_AGENT="$primary"
    return 0
  fi
  if [[ -n "$fallback" ]] && roles_agent_usable "$fallback"; then
    RESOLVED_AGENT="$fallback"
    ROLE_RESOLUTION_REASON="primary_unusable: ${primary} -> $(roles_agent_unusable_reason "$primary")"
    return 0
  fi
  echo "Rol karşılanamadı: $role (birincil=$primary neden=$(roles_agent_unusable_reason "$primary") yedek=${fallback:-yok})" >&2
  return 1
}

# Yalnız ajan adı gerektiğinde kullanılan ince sarmalayıcı (subshell güvenli).
role_agent() {
  role_resolve "$1" || return 1
  printf '%s' "$RESOLVED_AGENT"
}

# Aynı rol için çalışma anı (kota/kimlik hatası) devir hedefi. Yalnız
# runtime.fallback_on_quota_error=true ise ve hedef otomatik çalışabiliyorsa.
role_runtime_fallback() {
  local role="$1" chosen="$2" fallback=""
  [[ "${RUNTIME_FALLBACK_ON_QUOTA_ERROR:-false}" == "true" ]] || return 0
  case "$role" in
    implementer) fallback="$ROLE_IMPLEMENTER_FALLBACK" ;;
    tester)      fallback="$ROLE_TESTER_FALLBACK" ;;
    *)           return 0 ;;
  esac
  [[ -n "$fallback" && "$fallback" != "$chosen" ]] || return 0
  # Çalışma anı devri yalnız otomatik ajanlar arasında yapılabilir; handoff
  # ajanına devir aşama içinde değil, ayrı bir WAITING_AGENT turunda olur.
  roles_runnable_agent "$fallback" || return 0
  roles_agent_usable "$fallback" || return 0
  printf '%s' "$fallback"
}

# Rol için gösterilecek etiket (loglar ve operatör çıktısı).
role_label() {
  local role="$1" agent
  if roles_active && agent="$(role_agent "$role" 2>/dev/null)"; then
    roles_agent_label "$agent"
  else
    printf '%s' "${AGENT_BACKEND:-agent}"
  fi
}
