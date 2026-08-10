#!/usr/bin/env bash
# tools/agent-loop/compaction.sh
#
# Katmanlı sıkıştırma bütçesi (S09). Prompt girdisi segmentlere ayrılır,
# her segment kendi oranıyla sıkıştırılır. Amaç: token eşiği aşıldığında
# bilgi kaybını minimize ederken prompt'u bütçe içinde tutmak.
#
# Segment tanımları ve sıkıştırma oranları (keep_ratio):
#   instruction    — 1.0  (asla sıkıştırılmaz; kurallar ve talimatlar)
#   example        — 0.3  (agresif; örnekler tamamlayıcıdır)
#   task_contract  — 1.0  (asla sıkıştırılmaz; görev gereksinimleri)
#   tool_output    — 0.5  (orta; bulgular korunur, tekrarlar atılır)
#
# Bu dosya SIDE-EFFECT ÜRETMEZ: yalnız fonksiyon tanımlar.
# Çağıran (lib.sh veya controller) compaction_needed() ve compact_prompt()
# fonksiyonlarını kullanır.
#
# shellcheck shell=bash

_COMPACTION_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- segment oranları (env ile override edilebilir) -------------------------

: "${COMPACTION_RATIO_INSTRUCTION:=100}"   # yüzde (100 = sıkıştırma yok)
: "${COMPACTION_RATIO_EXAMPLE:=30}"
: "${COMPACTION_RATIO_TASK_CONTRACT:=100}"
: "${COMPACTION_RATIO_TOOL_OUTPUT:=50}"

# --- segment etiketleri -----------------------------------------------------
# Prompt'ta segment sınırları bu marker'larla belirlenir.
# Marker format: <!-- COMPACTION-SEGMENT: <type> -->

SEGMENT_MARKER_RE='^<!-- COMPACTION-SEGMENT: ([a-z_]+) -->$'

# --- yardımcılar ------------------------------------------------------------

# Verilen dosyanın bayt cinsinden boyutunu döndürür.
_file_bytes() {
  wc -c < "$1" 2>/dev/null || echo 0
}

# --- ana fonksiyonlar -------------------------------------------------------

# Prompt bütçe aşımı var mı? Bayt proxy kullanır (token sayımı yok;
# ölçülemeyen iyileştirme iddiası kanıtsızdır).
# Dönüş: 0 = sıkıştırma gerekli, 1 = gerekmiyor.
compaction_needed() {
  local input_file="$1"
  local max_bytes="${2:-${AGENT_PROMPT_MAX_BYTES:-262144}}"
  local size
  size="$(_file_bytes "$input_file")"
  (( size > max_bytes ))
}

# Prompt'u segmentlere ayırır ve her birini compact_segment.py ile sıkıştırır.
# Girdi: $1 = input dosyası, $2 = output dosyası.
# Segment marker'ları olmayan satırlar "instruction" segmentine atanır
# (varsayılan: sıkıştırılmaz).
compact_prompt() {
  local input_file="$1" output_file="$2"
  local script="$_COMPACTION_LIB_DIR/../../scripts/compact_segment.py"

  [[ -f "$input_file" ]] || return 1
  [[ -x "$script" ]] || script="python3 $script"

  local current_segment="instruction"
  local tmp_segment
  tmp_segment="$(mktemp "${TMPDIR:-/tmp}/compaction_seg.XXXXXX")"

  # Output dosyasını temizle
  : > "$output_file"

  while IFS= read -r line || [[ -n "$line" ]]; do
    # Segment marker kontrolü
    if [[ "$line" =~ $SEGMENT_MARKER_RE ]]; then
      # Önceki segmenti sıkıştır ve yaz
      if [[ -s "$tmp_segment" ]]; then
        _compact_flush_segment "$tmp_segment" "$current_segment" "$output_file" "$script"
      fi
      current_segment="${BASH_REMATCH[1]}"
      # Marker'ı output'a olduğu gibi yaz (bilgi kaybı yok)
      printf '%s\n' "$line" >> "$output_file"
      : > "$tmp_segment"
    else
      printf '%s\n' "$line" >> "$tmp_segment"
    fi
  done < "$input_file"

  # Son segmenti flush et
  if [[ -s "$tmp_segment" ]]; then
    _compact_flush_segment "$tmp_segment" "$current_segment" "$output_file" "$script"
  fi

  rm -f "$tmp_segment"
}

# Tek segmenti sıkıştırıp output'a yazar.
# $1 = segment dosyası, $2 = segment tipi, $3 = output dosyası, $4 = python script
_compact_flush_segment() {
  local seg_file="$1" seg_type="$2" output="$3" script="$4"
  local ratio preserve_structured="--preserve-structured"

  case "$seg_type" in
    instruction)    ratio="$COMPACTION_RATIO_INSTRUCTION" ;;
    example)        ratio="$COMPACTION_RATIO_EXAMPLE" ;;
    task_contract)  ratio="$COMPACTION_RATIO_TASK_CONTRACT" ;;
    tool_output)    ratio="$COMPACTION_RATIO_TOOL_OUTPUT" ;;
    *)              ratio=100 ;;  # bilinmeyen segment: sıkıştırma
  esac

  # Oran 100 ise sıkıştırma yok (doğrudan kopyala)
  if (( ratio >= 100 )); then
    cat "$seg_file" >> "$output"
    return 0
  fi

  # Python script ile sıkıştır
  $script --ratio "$ratio" $preserve_structured < "$seg_file" >> "$output" 2>/dev/null \
    || cat "$seg_file" >> "$output"
}

# Sıkıştırma öncesi/sonrası boyut bilgisini loglar.
# Dönüş: 0 (her zaman başarılı; bilgi amaçlı).
compaction_report() {
  local before="$1" after="$2"
  local b_size a_size savings
  b_size="$(_file_bytes "$before")"
  a_size="$(_file_bytes "$after")"
  if (( b_size > 0 )); then
    savings=$(( (b_size - a_size) * 100 / b_size ))
  else
    savings=0
  fi
  printf '[compaction] before=%d after=%d savings=%d%%\n' "$b_size" "$a_size" "$savings"
}

# --- Delta Compaction (S01) -------------------------------------------------
# Bullet koleksiyonu: durum bilgisi JSON array'de saklanır, delta operasyonları
# ile güncellenir. Bu sayede her seferinde tam durum yazımı yerine yalnızca
# değişiklikler iletilir.

# Bullet koleksiyonu dosya yolu (agentloop_init sonrası $H/state altında).
# Ortam değişkeni ile override edilebilir (testler için).
: "${CONTEXT_BULLETS_FILE:=}"

# Bullet koleksiyonunu başlatır (yoksa boş array ile oluşturur).
# $1 = dosya yolu (opsiyonel, CONTEXT_BULLETS_FILE kullanılır)
bullet_init() {
  local file="${1:-$CONTEXT_BULLETS_FILE}"
  [[ -n "$file" ]] || return 1
  if [[ ! -f "$file" ]]; then
    printf '{"bullets":[],"schema_version":1}\n' > "$file"
  fi
}

# Yeni bullet ekler.
# $1 = category, $2 = content, $3 = dosya yolu (opsiyonel)
bullet_add() {
  local category="$1" content="$2" file="${3:-$CONTEXT_BULLETS_FILE}"
  local id tmp
  id="b_$(date +%s)_$RANDOM"
  tmp="$(mktemp "${file}.tmp.XXXXXX")"
  jq --arg id "$id" \
     --arg cat "$category" \
     --arg content "$content" \
     --arg now "$(date -u +%Y-%m-%dT%H:%M:%SZ)" '
       .bullets += [{
         id: $id,
         category: $cat,
         content: $content,
         status: "active",
         created_at: $now,
         last_updated: $now
       }]
     ' "$file" > "$tmp" && mv -f "$tmp" "$file"
}

# Bullet günceller (id ile).
# $1 = id, $2 = yeni content, $3 = dosya yolu (opsiyonel)
bullet_update() {
  local id="$1" content="$2" file="${3:-$CONTEXT_BULLETS_FILE}"
  local tmp
  tmp="$(mktemp "${file}.tmp.XXXXXX")"
  jq --arg id "$id" \
     --arg content "$content" \
     --arg now "$(date -u +%Y-%m-%dT%H:%M:%SZ)" '
       .bullets |= map(
         if .id == $id then
           .content = $content | .last_updated = $now
         else . end
       )
     ' "$file" > "$tmp" && mv -f "$tmp" "$file"
}

# Bullet siler (id ile).
# $1 = id, $2 = dosya yolu (opsiyonel)
bullet_delete() {
  local id="$1" file="${2:-$CONTEXT_BULLETS_FILE}"
  local tmp
  tmp="$(mktemp "${file}.tmp.XXXXXX")"
  jq --arg id "$id" '
       .bullets |= map(select(.id != $id))
     ' "$file" > "$tmp" && mv -f "$tmp" "$file"
}

# Delta operasyonlarını uygular (toplu).
# $1 = delta JSON dosyası (format: [{"op":"ADD|UPDATE|DELETE","id":"...","category":"...","content":"..."}])
# $2 = hedef bullet dosyası (opsiyonel)
apply_delta_operations() {
  local delta_file="$1" file="${2:-$CONTEXT_BULLETS_FILE}"
  [[ -f "$delta_file" ]] || return 1
  bullet_init "$file"

  local op_count
  op_count="$(jq 'length' "$delta_file")"

  local i=0
  while (( i < op_count )); do
    local op id category content
    op="$(jq -r ".[$i].op" "$delta_file")"
    id="$(jq -r ".[$i].id // empty" "$delta_file")"
    category="$(jq -r ".[$i].category // empty" "$delta_file")"
    content="$(jq -r ".[$i].content // empty" "$delta_file")"

    case "$op" in
      ADD)
        bullet_add "$category" "$content" "$file"
        ;;
      UPDATE)
        [[ -n "$id" ]] || { (( i++ )); continue; }
        bullet_update "$id" "$content" "$file"
        ;;
      DELETE)
        [[ -n "$id" ]] || { (( i++ )); continue; }
        bullet_delete "$id" "$file"
        ;;
      *)
        echo "[delta] bilinmeyen operasyon: $op" >&2
        ;;
    esac
    (( i++ ))
  done
}

# Bullet koleksiyonunu JSON olarak stdout'a yazdırır.
# $1 = dosya yolu (opsiyonel)
bullet_dump() {
  local file="${1:-$CONTEXT_BULLETS_FILE}"
  [[ -f "$file" ]] && cat "$file" || printf '{"bullets":[]}\n'
}
