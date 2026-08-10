# Context Compaction Politikası (S09)

**Durum:** Aktif  
**İlk sürüm:** 2026-08-08  
**Çözüm:** S09 — Katmanlı Sıkıştırma Bütçesi

---

## Amaç

Agent prompt girdisi büyüdüğünde (token eşiği aşımı), bilgi kaybını
minimize ederek prompt'u bütçe içinde tutmak. Ölçülemeyen iyileştirme
iddiası kanıtsızdır; bu politika bayt-proxy tabanlı ölçüm ve şeffaf
kırpma belirteçleri ile çalışır.

---

## Segment Tanımları

Prompt dört segment tipine ayrılır. Her segmentin sıkıştırma oranı
ayrıdır; oranlar `compaction.sh` içinde tanımlı ve env ile override
edilebilir.

| Segment         | Varsayılan Oran | Açıklama                                       |
|-----------------|-----------------|------------------------------------------------|
| `instruction`   | 100% (korunur)  | Kurallar, talimatlar, sistem promptları        |
| `example`       | 30%             | Örnekler, referans çıktılar (tamamlayıcı)      |
| `task_contract` | 100% (korunur)  | Görev gereksinimleri, kabul kriterleri         |
| `tool_output`   | 50%             | Tool çıktıları, log parçaları, hata kanıtları  |

### Segment Sınırları

Segment sınırları HTML comment marker'ları ile belirlenir:

```html
<!-- COMPACTION-SEGMENT: instruction -->
...talimatlar...

<!-- COMPACTION-SEGMENT: tool_output -->
...log/çıktı...
```

Marker bulunmayan satırlar `instruction` segmentine atanır (varsayılan:
sıkıştırma yok).

---

## Sıkıştırma Algoritması

### Uzunluk-Tabanlı Kırpma (Mevcut)

`scripts/compact_segment.py` head-biased kırpma kullanır:

1. **Head-biased**: Başlangıç satırları daha önemlidir (özet genelde
   baştadır). İlk satır her zaman korunur; kalan kota son satırlardan
   ortalanır.
2. **Yapısal koruma** (`--preserve-structured`):
   - ` ``` ` ile çevrili kod blokları olduğu gibi korunur.
   - `|` ile başlayan tablo satırları olduğu gibi korunur.
   - Korunan bloklar hedef uzunluk hesabına dahil edilmez; önce
     ayrılıp sonra geri yerleştirilir.
3. **Kırpma belirteci**: Sıkıştırılan her prose bloğuna
   `[... N satır sıkıştırıldı ...]` satırı eklenir (bilgi kaybı
   şeffaftır).

### Gelecek: Perplexity-Tabanlı Kırpma

Gerçek perplexity entegrasyonu için model çağrısı gerekir. Bu script
o bağımlılığı kasten almaz; uzunluk-tabanlı yaklaşım yeterli olduğu
sürece tercih edilir (deterministik, hızlı, bağımsız).

---

## Entegrasyon Noktası

```bash
# tools/agent-loop/lib.sh — run_implementer() öncesi
source "$TOOLS_DIR/compaction.sh"

if compaction_needed "$input"; then
  compacted="${input%.md}.compacted.md"
  compact_prompt "$input" "$compacted"
  compaction_report "$input" "$compacted" >> "$LOGS/compaction.log"
  input="$compacted"
fi
```

---

## Kill-Switch'ler

Her segment oranı env ile override edilebilir:

```bash
export COMPACTION_RATIO_INSTRUCTION=100  # varsayılan: koru
export COMPACTION_RATIO_EXAMPLE=30       # varsayılan: %30 koru
export COMPACTION_RATIO_TASK_CONTRACT=100 # varsayılan: koru
export COMPACTION_RATIO_TOOL_OUTPUT=50   # varsayılan: %50 koru
```

Tüm sıkıştırmayı kapatmak için oranları 100'e set edin.

---

## Uyarılar

1. **instruction ve task_contract asla sıkıştırılmaz.** Bu segmentler
   100% korunur; sıkıştırma yalnızca example ve tool_output'u etkiler.
2. **Kod blokları korunur.** `--preserve-structured` ile kod ve tablo
   blokları kırpılmaz. Yalnız serbest metin (prose) kırpılır.
3. **Bilgi kaybı şeffaftır.** Her kırpma `[... N satır sıkıştırıldı ...]`
   ile işaretlenir; gizli veri kaybı yoktur.
4. **Bayt-proxy kullanılır.** Token sayımı yoktur; ölçülemeyen iyileştirme
   iddiası kanıtsızdır. `AGENT_PROMPT_MAX_BYTES` bayt eşiği ile çalışır.
5. **Compaction geri dönüşümlüdür.** Orijinal input dosyası silinmez;
   sıkıştırılmış versiyonu `.compacted.md` uzantısıyla yazılır.

---

## Dosyalar

| Dosya | Sorumluluk |
|-------|-----------|
| `tools/agent-loop/compaction.sh` | Segment tanımları, orkestrasyon |
| `scripts/compact_segment.py` | Tek-segment sıkıştırıcı |
| `docs/architecture/Context-Compaction-Politikasi.md` | Bu doküman |
