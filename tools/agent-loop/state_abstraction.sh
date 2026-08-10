#!/usr/bin/env bash
# tools/agent-loop/state_abstraction.sh
#
# Durum soyutlama katmanı (S11). Tool çıktılarını compact摘要'ya dönüştürür,
# önceki ve mevcut durum arasındaki delta'yı hesaplar.
#
# Bu dosya SIDE-EFFECT ÜRETMEZ: yalnız fonksiyon tanımlar.
# Çağıran (lib.sh veya controller) abstract_tool_output() ve print_state_delta()
# fonksiyonlarını kullanır.
#
# shellcheck shell=bash

# --- Tool çıktısı soyutlama -------------------------------------------------

# pytest çıktısını soyut özet'e dönüştürür.
# Girdi: stdin veya $1 = dosya yolu
# Çıktı: {passed: N, failed: N, errors: N, summary: "..."}
abstract_pytest_output() {
  local input="${1:--}"
  local content
  if [[ "$input" == "-" ]]; then
    content="$(cat)"
  else
    [[ -f "$input" ]] || { printf '{"passed":0,"failed":0,"errors":0,"summary":"dosya yok"}\n'; return; }
    content="$(cat "$input")"
  fi

  local passed=0 failed=0 errors=0
  # pytest summary satırını parse et: "X passed, Y failed, Z errors"
  if [[ "$content" =~ ([0-9]+)\ passed ]]; then
    passed="${BASH_REMATCH[1]}"
  fi
  if [[ "$content" =~ ([0-9]+)\ failed ]]; then
    failed="${BASH_REMATCH[1]}"
  fi
  if [[ "$content" =~ ([0-9]+)\ error ]]; then
    errors="${BASH_REMATCH[1]}"
  fi

  local total=$(( passed + failed + errors ))
  local summary
  if (( failed == 0 && errors == 0 )); then
    summary="tüm testler geçti ($passed test)"
  else
    summary="$failed başarısız, $errors hata ($total toplam)"
  fi

  jq -n \
    --argjson passed "$passed" \
    --argjson failed "$failed" \
    --argjson errors "$errors" \
    --arg summary "$summary" \
    '{passed: $passed, failed: $failed, errors: $errors, summary: $summary}'
}

# git diff çıktısını soyut dosya listesine dönüştürür.
# Girdi: stdin veya $1 = dosya yolu (git diff --name-status çıktısı)
# Çıktı: {added: [...], modified: [...], deleted: [...], total: N}
abstract_git_diff() {
  local input="${1:--}"
  local content
  if [[ "$input" == "-" ]]; then
    content="$(cat)"
  else
    [[ -f "$input" ]] || { printf '{"added":[],"modified":[],"deleted":[],"total":0}\n'; return; }
    content="$(cat "$input")"
  fi

  local added=() modified=() deleted=()
  while IFS=$'\t' read -r status file; do
    [[ -n "$file" ]] || continue
    case "$status" in
      A*) added+=("$file") ;;
      M*) modified+=("$file") ;;
      D*) deleted+=("$file") ;;
      *)  modified+=("$file") ;;  # R, C vs.
    esac
  done <<< "$content"

  local total=$(( ${#added[@]} + ${#modified[@]} + ${#deleted[@]} ))

  # JSON dizileri oluştur
  local added_json modified_json deleted_json
  added_json="$(printf '%s\n' "${added[@]}" 2>/dev/null | jq -R . | jq -s . 2>/dev/null || echo '[]')"
  modified_json="$(printf '%s\n' "${modified[@]}" 2>/dev/null | jq -R . | jq -s . 2>/dev/null || echo '[]')"
  deleted_json="$(printf '%s\n' "${deleted[@]}" 2>/dev/null | jq -R . | jq -s . 2>/dev/null || echo '[]')"

  jq -n \
    --argjson added "$added_json" \
    --argjson modified "$modified_json" \
    --argjson deleted "$deleted_json" \
    --argjson total "$total" \
    '{added: $added, modified: $modified, deleted: $deleted, total: $total}'
}

# Genel tool çıktısını soyutlar (tip tespiti ile).
# $1 = tool adı (pytest, git_diff, lint, generic)
# $2 = girdi dosyası (opsiyonel, stdin kullanılır)
abstract_tool_output() {
  local tool_name="$1" input_file="${2:--}"
  case "$tool_name" in
    pytest|py.test|test)
      abstract_pytest_output "$input_file"
      ;;
    git_diff|git-diff|diff)
      abstract_git_diff "$input_file"
      ;;
    lint|ruff|flake8|mypy)
      # Lint çıktısı: hata sayısı + ilk N satır
      local content error_count
      if [[ "$input_file" == "-" ]]; then
        content="$(cat)"
      else
        content="$(cat "$input_file" 2>/dev/null || echo "")"
      fi
      error_count="$(echo "$content" | grep -cE ':\d+:' 2>/dev/null || echo 0)"
      jq -n \
        --arg tool "$tool_name" \
        --argjson errors "$error_count" \
        --arg preview "$(echo "$content" | head -5)" \
        '{tool: $tool, error_count: $errors, preview: $preview}'
      ;;
    *)
      # Generic: ilk 10 satır + satır sayısı
      local content line_count
      if [[ "$input_file" == "-" ]]; then
        content="$(cat)"
      else
        content="$(cat "$input_file" 2>/dev/null || echo "")"
      fi
      line_count="$(echo "$content" | wc -l)"
      jq -n \
        --arg tool "$tool_name" \
        --argjson lines "$line_count" \
        --arg preview "$(echo "$content" | head -10)" \
        '{tool: $tool, line_count: $lines, preview: $preview}'
      ;;
  esac
}

# --- Delta-only güncelleme (S01) --------------------------------------------

# İki JSON dosyası arasındaki farkı hesaplar (basit diff).
# $1 = eski dosya, $2 = yeni dosya
# Çıktı: delta JSON (eklenen/değişen/silinen anahtarlar)
print_state_delta() {
  local old_file="$1" new_file="$2"
  [[ -f "$old_file" && -f "$new_file" ]] || {
    echo '{"error":"dosya bulunamadı"}' >&2
    return 1
  }

  # jq ile basit object diff: yeni eklenen/değişen alanlar
  jq -n \
    --slurpfile old "$old_file" \
    --slurpfile new "$new_file" '
      ($old[0] // {}) as $o | ($new[0] // {}) as $n |
      {
        added: [ $n | to_entries[] | select(.key as $k | $o | has($k) | not) ],
        modified: [ $n | to_entries[] | select(.key as $k | $o | has($k) and ($o[$k] != .value)) ],
        removed: [ $o | to_entries[] | select(.key as $k | $n | has($k) | not) ]
      }
    '
}

# Delta'yı human-readable formata çevirir.
# $1 = delta JSON dosyası veya stdin
format_state_delta() {
  local input="${1:--}"
  local content
  if [[ "$input" == "-" ]]; then
    content="$(cat)"
  else
    content="$(cat "$input")"
  fi

  echo "$content" | jq -r '
    "=== Durum Değişiklikleri ===",
    (if (.added | length) > 0 then
      "\nEklenen:",
      (.added[] | "  + \(.key): \(.value)")
    else empty end),
    (if (.modified | length) > 0 then
      "\nDeğişen:",
      (.modified[] | "  ~ \(.key): \(.value)")
    else empty end),
    (if (.removed | length) > 0 then
      "\nSilinen:",
      (.removed[] | "  - \(.key)")
    else empty end),
    (if (.added | length) == 0 and (.modified | length) == 0 and (.removed | length) == 0 then
      "  (değişiklik yok)"
    else empty end)
  '
}
