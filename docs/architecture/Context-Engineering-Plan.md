# Context Engineering Plan for AI Agent Loop

Bu plan, [`context-engineering-solutions.json`](../../context-engineering-solutions.json) dosyasındaki çözümleri bu projenin agent-loop mimarisine kademeli olarak entegre etmek için hazırlanmıştır. Her iterasyon, bir öncekinin çıktılarını tüketir.

## Prensip Eşleşmesi

| Prensip | İlgili Çözümler | İterasyon |
|---------|----------------|-----------|
| P1: Pozisyon = dikkat ağırlığı | S03, S12 | 3, 6 |
| P2: Bozulma eşikli ilerler | S09, S12 | 4, 6 |
| P3: Yamalamak korur, yeniden yazmak aşındırır | S01, S02 | 2, 5 |
| P4: Ekleme/çıkarma = maliyet kararı | S04, S05, S13 | 1, 6 |

---

## İterasyon 1: KV-Cache Koruması ve Hata Koruma

**Süre:** 1-2 gün  
**Çözümler:** S04, S06  
**Anti-pattern engelleri:** A2, A6  
**Maliyet:** Düşük

### S04 — Append-Only Context

**Gerekçe:** `run_implementer()` fonksiyonu her turda prompt'u sıfırdan oluşturuyor. Prompt'un kendisi stabil (timestamp yok), ancak `CURRENT_TASK.json` dosyası her `refresh_contract()` çağrısında yeniden yazılıyor. JSON key sırası deterministik değilse, aynı içerik farklı byte sequence olarak cache'i kırar.

**Değişiklikler:**

1. **`refresh_contract()` — deterministik JSON sıralama**
   - Dosya: [`tools/agent-loop/lib.sh`](../../tools/agent-loop/lib.sh)
   - `jq` komutlarına `--sort-keys` ekle
   ```bash
   # Önceki:
   jq --arg head "$head" ...
   # Sonrası:
   jq --sort-keys --arg head "$head" ...
   ```

2. **Cache politikası dokümanı**
   - Yeni dosya: `docs/architecture/Context-Cache-Politikasi.md`
   - Kurallar:
     - Sistem promptu (template dosyaları) asla değişmez
     - `CURRENT_TASK.json` append-only eklenir, geçmiş sürümler silinmez
     - Tool çıktıları sonradan düzenlenmez veya kırpılmaz
     - JSON anahtar sırası her zaman deterministik (`--sort-keys`)

3. **Denetim kuralı**
   - Prompt template'lerde timestamp, rastgele ID veya değişken alan eklenmesini önleyen lint kuralı
   - `scripts/check_context_stability.sh` — template dosyalarında dinamik pattern ara

### S06 — Hataları Context'te Bırak

**Gerekçe:** Başarısız tool call ve stack trace'ler loglanıyor ama bir sonraki turda implementer prompt'una eklenmiyor. Model aynı hatayı tekrarlayabiliyor.

**Değişiklikler:**

1. **`collect_error_evidence()` fonksiyonu**
   - Dosya: [`tools/agent-loop/lib.sh`](../../tools/agent-loop/lib.sh)
   - Önceki turdan hata loglarını oku, implementer prompt'una ekle
   ```bash
   collect_error_evidence() {
     local iteration="$1"
     local prev=$((iteration - 1))
     local stderr_log="$LOGS/implementer-i${prev}-*.stderr.log"
     for f in $stderr_log; do
       [[ -s "$f" ]] || continue
       printf '\n## Error Evidence (iteration %d — do not repeat)\n\n```\n' "$prev"
       tail -n 80 "$f"
       printf '\n```\n'
     done
   }
   ```

2. **Prompt template güncellemesi**
   - Dosya: [`tools/agent-loop/prompts/implementer.md`](../../tools/agent-loop/prompts/implementer.md)
   ```markdown
   ## Error Evidence
   
   Previous errors are shown above as evidence of what does not work.
   Analyze them before acting. Do not repeat the same approaches.
   Only errors that are resolved and no longer relevant may be ignored.
   ```

3. **Tekrar eden hata eşiği**
   - Aynı hata 3 kez tekrarlanırsa, sonraki turlarda özetle değiştir
   - `collect_error_evidence()` içinde: benzer hata 3+ kez geçiyorsa tek satır özet

**Kanıt:**
- Test: `tests/integration/test_error_evidence_preservation.sh`
- Başarısız tur çalıştır → hata logunun sonraki turda prompt'ta göründüğünü doğrula

---

## İterasyon 2: SBAR Yapısal Devir Teslim

**Süre:** 2-3 gün  
**Çözüm:** S02  
**Anti-pattern engeli:** A1  
**Maliyet:** Düşük

### S02 — SBAR Devir Teslim Şeması

**Gerekçe:** Handoff paketleri şu anda 9 bölümlük serbest format. Boş bırakılan alanlar sessizce atlanıyor. SBAR şeması, atlanan bilgiyi yapısal olarak görünür kılar.

**Değişiklikler:**

1. **SBAR şablonu**
   - Yeni dosya: `.agent/tasks/templates/sbar-handoff.json`
   ```json
   {
     "schema_version": 1,
     "situation": {
       "task_id": "",
       "current_stage": "",
       "objective": "",
       "blocked_reason": null
     },
     "background": {
       "how_we_got_here": "",
       "key_decisions": [],
       "decision_rationale": ""
     },
     "assessment": {
       "current_state": "",
       "known_risks": [],
       "open_questions": []
     },
     "recommendation": {
       "next_concrete_step": "",
       "do_not_touch": [],
       "critical_constraints": []
     },
     "other": null
   }
   ```

2. **`handoff_write()` güncellemesi**
   - Dosya: [`tools/agent-loop/ledger.sh`](../../tools/agent-loop/ledger.sh)
   - Mevcut 9 bölümü SBAR slotlarına eşle
   - Boş slot uyarısı: `sbar_validate()` fonksiyonu

3. **Boş slot zorunluluğu**
   - Boş slot `"yok"` olarak doldurulur; sessiz atlama yasak
   - `other` slotu domain-specific bilgi için ayrılır

4. **Prompt yönergesi**
   - Dosya: [`tools/agent-loop/prompts/implementer.md`](../../tools/agent-loop/prompts/implementer.md)
   ```markdown
   ## Handoff Context (SBAR schema)
   
   If a handoff file is present, it uses the SBAR structure.
   Empty slots marked "yok" are explicit gaps — investigate them.
   Do not ignore empty slots; they indicate missing information.
   ```

**Kanıt:**
- Test: `tests/integration/test_sbar_handoff_validation.sh`
- SBAR şeması doğrulama + boş slot uyarı testi

---

## İterasyon 3: Hedef Tekrarlama (Recitation)

**Süre:** 1-2 gün  
**Çözüm:** S03  
**Anti-pattern engeli:** A4  
**Maliyet:** Düşük

### S03 — Hedef Recitation

**Gerekçe:** 50+ tool call süren görevlerde task contract prompt'un ortasında kalır, U-şeklinde dikkat yanlılığı nedeniyle model hedefi kaybeder. Hedefi periyodik olarak context'in sonuna taşımak, yüksek dikkatli bölgede tutar.

**Değişiklikler:**

1. **`should_recite_goal()` fonksiyonu**
   - Dosya: [`tools/agent-loop/lib.sh`](../../tools/agent-loop/lib.sh)
   ```bash
   should_recite_goal() {
     local iteration="$1"
     local interval="${AGENT_LOOP_RECITATION_INTERVAL:-5}"
     (( iteration > 0 && iteration % interval == 0 ))
   }
   ```

2. **Recitation bloğu**
   - `run_implementer()` içinde, her N turda task contract'ın özetini prompt'un **sonuna** ekle
   ```bash
   if should_recite_goal "$iteration"; then
     printf '\n## ACTIVE GOAL REMINDER\n\n'
     printf 'Objective: %s\n\n' "$(jq -r '.task.objective' "$TASK")"
     printf 'Acceptance criteria still to satisfy:\n'
     jq -r '.acceptance_criteria[] | "- [ ] \(.requirement)"' "$TASK"
     printf '\nFocus on the above. Do not drift.\n'
   fi
   ```

3. **TODO durum dosyası**
   - Yeni dosya: `.agent-handoff/state/TODO.json`
   - Tamamlanan/kalan kabul kriterlerini tutar
   - Her turda güncellenir, recitation ile birlikte prompt'a eklenir

**Kanıt:**
- Test: `tests/integration/test_goal_recitation.sh`
- 5. turda recitation bloğunun prompt'ta göründüğünü doğrula

---

## İterasyon 4: Katmanlı Sıkıştırma Bütçesi

**Süre:** 3-4 gün  
**Çözüm:** S09  
**Anti-pattern engeli:** A1  
**Maliyet:** Orta

### S09 — Katmanlı Sıkıştırma

**Gerekçe:** Context'in tamamına aynı sıkıştırma uygulamak, kritik talimatı gereksiz örnek kadar kırpar. Bilgi yoğunluğuna göre bütçe dağıtımı gerekir.

**Değişiklikler:**

1. **Compaction modülü**
   - Yeni dosya: `tools/agent-loop/compaction.sh`
   - Segment tanımları ve sıkıştırma oranları:

   | Segment | Sıkıştırma | Gerekçe |
   |---------|-----------|---------|
   | Talimatlar (system prompt) | %10-20 | Netlik korunmalı |
   | Örnekler / demonstrasyonlar | %60-80 | Yüksek redundans |
   | Task contract (aktif görev) | %0-10 | Niyet bozulmamalı |
   | Tool çıktıları | %30-50 | Orta bilgi yoğunluğu |

2. **Segment bazlı sıkıştırma**
   ```bash
   compact_segment() {
     local segment="$1"
     local ratio="$2"
     # LLMLingua benzeri perplexity-tabanlı kırpma
     # Kod ve tablo gibi düşük-perplexity ama yüksek-önem içerik korunur
     python3 "$ROOT/scripts/compact_segment.py" \
       --input "$segment" --ratio "$ratio" \
       --preserve-structured
   }
   ```

3. **Politika dokümanı**
   - Yeni dosya: `docs/architecture/Context-Compaction-Politikasi.md`
   - Compaction bir özetleme değil, diff uygulama problemi
   - Perplexity tabanlı kırpma uyarıları

**Kanıt:**
- Test: `tests/integration/test_layered_compaction.sh`
- Uzun context ver → sıkıştır → task contract'ın bozulmadığını doğrula

---

## İterasyon 5: Delta Compaction ve Durum Soyutlaması

**Süre:** 5-7 gün  
**Çözümler:** S01, S11  
**Anti-pattern engeli:** A1  
**Maliyet:** Orta-Yüksek

### S01 — Delta Compaction (ACE modeli)

**Gerekçe:** Tam yeniden yazdırma her turda detay aşındırır (context collapse). Maddelenmiş, kimliklendirilmiş bullet koleksiyonu ile yalnızca ADD/UPDATE/DELETE operasyonları uygulanır.

**Değişiklikler:**

1. **Bullet koleksiyonu durumu**
   - Yeni dosya: `.agent-handoff/state/CONTEXT_BULLETS.json`
   ```json
   {
     "schema_version": 1,
     "bullets": [
       {
         "id": "ctx-001",
         "category": "decision",
         "content": "PostgreSQL migration kullanıldı",
         "status": "active",
         "created_at": "...",
         "last_updated": "..."
       }
     ]
   }
   ```

2. **Delta operasyonları**
   - Modelden özet değil, operasyon listesi iste
   - Operasyonları deterministik kodla uygula (modele uygulatma)
   - Silme yalnızca açık DELETE ile; sessiz düşme yok

3. **Yaşlanma politikası**
   - Madde sayısı sınırsız büyürse P2 devreye girer
   - N turdir güncellenmeyen maddeler arşivlenir

### S11 — Programatik Durum Soyutlaması

**Gerekçe:** Ham gözlemleri context'e dökmek, modele durum tahminini de yaptırmaktır. Deterministik kodla yapılandırılmış duruma indirgemek token başına getiriyi artırır.

**Değişiklikler:**

1. **Durum soyutlama katmanı**
   - Tool çıktılarını deterministik kodla yapılandırılmış duruma indir
   - Değişmeyen alanları her turda yeniden basma, yalnızca deltayı bas
   ```bash
   abstract_tool_output() {
     local tool="$1" output="$2"
     case "$tool" in
       "pytest")
         jq -n --argjson summary "$(parse_pytest_summary "$output")" \
           '{passed: $summary.passed, failed: $summary.failed, errors: $summary.errors}'
         ;;
       "git_diff")
         echo "$output" | grep '^+++' | sed 's/^+++ b\///'
         ;;
     esac
   }
   ```

**Kanıt:**
- Test: `tests/integration/test_delta_compaction.sh`
- Test: `tests/integration/test_state_abstraction.sh`

---

## İterasyon 6: Semantik Yakınlık ve Biçim Varyasyonu

**Süre:** 2-3 gün  
**Çözümler:** S12, S13  
**Maliyet:** Düşük

### S12 — Semantik Yakınlık Kontrolü

**Gerekçe:** Uzun context'te bilgi ile sorgu arasındaki semantik benzerlik düştükçe bozulma hızlanır. Enjekte edilen kanıtı görev terminolojisiyle etiketlemek benzerliği artırır.

**Değişiklikler:**

1. **Kanıt enjeksiyon rehberi**
   - Yeni dosya: `docs/architecture/Evidence-Injection-Rehberi.md`
   - Kurallar:
     - Kanıt bloğunun başlığında görev terimini tekrarla
     - Distraktör ekleme — yakın ama yanlış içerik, alakalı olandan daha zararlı
     - Kanıtı görevde kullanılan terminolojiyle yeniden etiketle

### S13 — Kontrollü Biçim Varyasyonu

**Gerekçe:** Tekdüze action-observation çiftleri few-shot kalıbı oluşturur; model kalıbı taklit ederek sürüklenir. Kasıtlı varyasyon kalıp kilitlenmesini kırar.

**Değişiklikler:**

1. **Varyasyon mekanizması**
   - Tool çıktısı serileştirmede kontrollü rastgelelik
   - Varyasyon KV-cache prefix'ini etkilemeyecek konuma yerleştir
   - Semantik değişmez; yalnızca ifade biçimi değişir

**Kanıt:**
- Test: `tests/integration/test_format_variation.sh`

---

## İterasyon 7: Grafik-Sıralı Context ve Subagent Fan-Out

**Süre:** 7-10 gün  
**Çözümler:** S08, S10  
**Anti-pattern engeli:** A5  
**Maliyet:** Yüksek

### S08 — PageRank Repo Map

**Gerekçe:** Hangi kod parçasının context'e gireceğine modele karar verdirmek, modelin henüz görmediği dosyalar hakkında karar vermesini istemektir. Alaka düzeyi kod grafiğinden hesaplanır.

**Değişiklikler:**

1. **tree-sitter entegrasyonu**
   - Yeni script: `scripts/extract_code_graph.py`
   - Tanım ve referans etiketlerini çıkar → `graphify-out/graph.json` güncelle

2. **Personalized PageRank**
   - Yeni script: `scripts/compute_pagerank.py`
   - Sohbetde geçen tanımlayıcılara yüksek kişiselleştirme ağırlığı
   - Token bütçesine kadar kes

3. **Prompt entegrasyonu**
   - Graph-ranked kod bloklarını implementer prompt'una ekle

### S10 — Salt-Okunur Subagent Fan-Out

**Gerekçe:** Keşif maliyeti ayrı pencerelere dışsallaştırılır; ana pencereye yalnızca damıtılmış sonuç döner.

**Değişiklikler:**

1. **Keşif protokolü**
   - Yeni dosya: `docs/architecture/Subagent-Kesif-Protokolu.md`
   - Subagent'lara yalnızca okuma yetkisi
   - Dönüş formatı SBAR şemasıyla sabit (S02 ile uyumlu)
   - Yazma/üretim paralelleştirilmez (A5)

2. **Subagent dönüş şablonu**
   - `.agent/tasks/templates/subagent-return.json`
   - SBAR slotlarıyla eşleşen keşif sonucu

**Kanıt:**
- Test: `tests/integration/test_pagerank_context_selection.sh`
- Test: `tests/integration/test_subagent_readonly_return.sh`

---

## Uygulama Özeti

| # | İterasyon | Çözümler | Süre | Maliyet | Öncelik |
|---|-----------|----------|------|---------|---------|
| 1 | KV-Cache + Hata Koruma | S04, S06 | 1-2 gün | Düşük | İlk |
| 2 | SBAR Devir Teslim | S02 | 2-3 gün | Düşük | Yüksek |
| 3 | Hedef Recitation | S03 | 1-2 gün | Düşük | Yüksek |
| 4 | Katmanlı Sıkıştırma | S09 | 3-4 gün | Orta | Orta |
| 5 | Delta Compaction + POMDP | S01, S11 | 5-7 gün | Orta-Yüksek | Orta |
| 6 | Semantik Yakınlık + Varyasyon | S12, S13 | 2-3 gün | Düşük | Düşük |
| 7 | PageRank + Subagent Fan-Out | S08, S10 | 7-10 gün | Yüksek | Son |

**Toplam:** ~21-31 gün  
**İlk değer:** İterasyon 1-3 (4-7 gün) temel korumayı sağlar.

## Çözüm → Dosya Eşleşmesi

| Çözüm | Değişen Dosyalar |
|--------|-----------------|
| S01 | `tools/agent-loop/compaction.sh` (yeni), `lib.sh` |
| S02 | `tools/agent-loop/ledger.sh`, `.agent/tasks/templates/sbar-handoff.json` (yeni) |
| S03 | `tools/agent-loop/lib.sh`, `prompts/implementer.md` |
| S04 | `tools/agent-loop/lib.sh`, `docs/architecture/Context-Cache-Politikasi.md` (yeni) |
| S06 | `tools/agent-loop/lib.sh`, `prompts/implementer.md` |
| S08 | `scripts/extract_code_graph.py` (yeni), `scripts/compute_pagerank.py` (yeni) |
| S09 | `tools/agent-loop/compaction.sh` (yeni), `docs/architecture/Context-Compaction-Politikasi.md` (yeni) |
| S10 | `docs/architecture/Subagent-Kesif-Protokolu.md` (yeni) |
| S11 | `tools/agent-loop/state_abstraction.sh` (yeni) |
| S12 | `docs/architecture/Evidence-Injection-Rehberi.md` (yeni) |
| S13 | `tools/agent-loop/lib.sh` |

## Kaynaklar

Tüm çözüm detayları, kanıt seviyeleri ve kaynak URL'leri için: [`context-engineering-solutions.json`](../../context-engineering-solutions.json)
