# Context Engineering — Oturum Bazlı Uygulama Rehberi

Her iterasyonu ayrı bir oturumda uygula. Her oturum sonunda doğrulama yap ve commit'le.

---

## Oturum 1: KV-Cache Koruması + Hata Koruma ✓ TAMAMLANDI

**Süre:** 15 dakika  
**Çözümler:** S04, S06

### Yapılanlar
- [x] `tools/agent-loop/lib.sh` → `refresh_contract()` içine `jq --sort-keys` eklendi
- [x] `tools/agent-loop/lib.sh` → `collect_error_evidence()` fonksiyonu eklendi
- [x] `tools/agent-loop/lib.sh` → `run_implementer()` içinde `collect_error_evidence "$iteration"` çağrısı eklendi
- [x] `tools/agent-loop/prompts/implementer.md` → Error Evidence bölümü eklendi
- [x] `docs/architecture/Context-Cache-Politikasi.md` → Yeni doküman oluşturuldu

### Doğrulama
```bash
bash scripts/verify_context_engineering.sh
```

---

## Oturum 2: SBAR Devir Teslim Şeması ✓ TAMAMLANDI

**Süre:** 30-45 dakika  
**Çözüm:** S02  
**Dosyalar:** `ledger.sh`, yeni şablon, `implementer.md`

### Adımlar

1. **SBAR şablonu oluştur**
   ```bash
   # Yeni dosya: .agent/tasks/templates/sbar-handoff.json
   ```
   İçerik: situation, background, assessment, recommendation, other slotları

2. **`handoff_write()` fonksiyonunu güncelle**
   ```bash
   # Dosya: tools/agent-loop/ledger.sh
   # Mevcut 9 bölümü SBAR slotlarına eşle
   # jq ile SBAR JSON'u üret
   ```

3. **`sbar_validate()` fonksiyonu ekle**
   ```bash
   # Dosya: tools/agent-loop/ledger.sh
   # Boş slot kontrolü — "yok" ile doldurulmamış slot uyarısı ver
   ```

4. **Prompt template güncelle**
   ```bash
   # Dosya: tools/agent-loop/prompts/implementer.md
   # SBAR şeması yönergesi ekle
   ```

5. **Doğrulama scripti güncelle**
   ```bash
   # scripts/verify_context_engineering.sh içine SBAR kontrolleri ekle
   ```

### Yapılanlar
- [x] `tools/agent-loop/ledger.sh` → `sbar_template_json()` fonksiyonu eklendi
- [x] `tools/agent-loop/ledger.sh` → `sbar_validate()` fonksiyonu eklendi
- [x] `tools/agent-loop/ledger.sh` → `handoff_write()` SBAR şemasına dönüştürüldü (5 slot: situation, background, assessment, recommendation, other)
- [x] `tools/agent-loop/ledger.sh` → `ledger_init()` SBAR şablon dosyasını oluşturur
- [x] `tools/agent-loop/prompts/implementer.md` → SBAR Handoff Schema yönergesi eklendi
- [x] `scripts/verify_context_engineering.sh` → 6 yeni SBAR doğrulama kontrolü eklendi

### Doğrulama
```bash
bash scripts/verify_context_engineering.sh
```

---

## Oturum 3: Hedef Tekrarlama (Recitation)

**Süre:** 20-30 dakika  
**Çözüm:** S03  
**Dosyalar:** `lib.sh`, `implementer.md`

### Adımlar

1. **`should_recite_goal()` fonksiyonu ekle**
   ```bash
   # Dosya: tools/agent-loop/lib.sh
   # Her N turda (varsayılan 5) true döndür
   should_recite_goal() {
     local iteration="$1"
     local interval="${AGENT_LOOP_RECITATION_INTERVAL:-5}"
     (( iteration > 0 && iteration % interval == 0 ))
   }
   ```

2. **Recitation bloğunu `run_implementer()` içine ekle**
   ```bash
   # Dosya: tools/agent-loop/lib.sh
   # should_recite_goal true dönerse prompt sonuna hedef özetini ekle
   if should_recite_goal "$iteration"; then
     printf '\n## ACTIVE GOAL REMINDER\n\n'
     printf 'Objective: %s\n\n' "$(jq -r '.task.objective' "$TASK")"
     printf 'Acceptance criteria still to satisfy:\n'
     jq -r '.acceptance_criteria[] | "- [ ] \(.requirement)"' "$TASK"
     printf '\nFocus on the above. Do not drift.\n'
   fi
   ```

3. **Prompt template güncelle**
   ```bash
   # Dosya: tools/agent-loop/prompts/implementer.md
   # Recitation bölümü yönergesi ekle
   ```

4. **Doğrulama scripti güncelle**

### Doğrulama
```bash
bash scripts/verify_context_engineering.sh
```

---

## Oturum 4: Katmanlı Sıkıştırma Bütçesi

**Süre:** 1-2 saat  
**Çözüm:** S09  
**Dosyalar:** Yeni `compaction.sh`, yeni Python script, politika dokümanı

### Adımlar

1. **Compaction modülü oluştur**
   ```bash
   # Yeni dosya: tools/agent-loop/compaction.sh
   # Segment tanımları: talimat, örnek, task contract, tool çıktısı
   # Her segment için farklı sıkıştırma oranı
   ```

2. **Segment sıkıştırma scripti**
   ```bash
   # Yeni dosya: scripts/compact_segment.py
   # Perplexity-tabanlı kırpma (basit versiyon: uzunluk bazlı)
   # --preserve-structured: kod ve tablo korunur
   ```

3. **Politika dokümanı**
   ```bash
   # Yeni dosya: docs/architecture/Context-Compaction-Politikasi.md
   # Segment tanımları, sıkıştırma oranları, uyarılar
   ```

4. **Entegrasyon**
   ```bash
   # tools/agent-loop/lib.sh içinde run_implementer() öncesi
   # Token eşiği aşılıyorsa compaction çağrısı
   ```

5. **Doğrulama scripti güncelle**

### Doğrulama
```bash
bash scripts/verify_context_engineering.sh
```

---

## Oturum 5: Delta Compaction + Durum Soyutlaması ✓ TAMAMLANDI

**Süre:** 2-3 saat  
**Çözümler:** S01, S11  
**Dosyalar:** `compaction.sh` genişletme, yeni `state_abstraction.sh`

### Adımlar

1. **Bullet koleksiyonu durumu**
   ```bash
   # Yeni dosya: .agent-handoff/state/CONTEXT_BULLETS.json
   # Her madde: id, category, content, status, created_at, last_updated
   ```

2. **Delta operasyonları**
   ```bash
   # tools/agent-loop/compaction.sh içine
   # apply_delta_operations() fonksiyonu
   # ADD / UPDATE / DELETE operasyonları
   # Deterministik jq ile uygula
   ```

3. **Durum soyutlama katmanı**
   ```bash
   # Yeni dosya: tools/agent-loop/state_abstraction.sh
   # abstract_tool_output() fonksiyonu
   # pytest → {passed, failed, errors}
   # git_diff → değişen dosya listesi
   ```

4. **Delta-only güncelleme**
   ```bash
   # print_state_delta() fonksiyonu
   # Önceki ve mevcut durum arasındaki fark
   ```

5. **Entegrasyon ve doğrulama**

### Yapılanlar
- [x] `tools/agent-loop/compaction.sh` → `bullet_init()` fonksiyonu eklendi
- [x] `tools/agent-loop/compaction.sh` → `bullet_add/update/delete()` fonksiyonları eklendi
- [x] `tools/agent-loop/compaction.sh` → `apply_delta_operations()` fonksiyonu eklendi (ADD/UPDATE/DELETE)
- [x] `tools/agent-loop/state_abstraction.sh` → Yeni modül oluşturuldu
- [x] `tools/agent-loop/state_abstraction.sh` → `abstract_tool_output()` fonksiyonu eklendi (pytest, git_diff, lint, generic)
- [x] `tools/agent-loop/state_abstraction.sh` → `print_state_delta()` fonksiyonu eklendi
- [x] `tools/agent-loop/state_abstraction.sh` → `format_state_delta()` fonksiyonu eklendi
- [x] `tools/agent-loop/lib.sh` → `state_abstraction.sh` source edildi
- [x] `tools/agent-loop/lib.sh` → `agentloop_init()` içinde `CONTEXT_BULLETS_FILE` init eklendi
- [x] `scripts/verify_context_engineering.sh` → 7 yeni Session 5 doğrulama kontrolü eklendi

### Doğrulama
```bash
bash scripts/verify_context_engineering.sh
```

---

## Oturum 6: Semantik Yakınlık + Biçim Varyasyonu

**Süre:** 30-45 dakika  
**Çözümler:** S12, S13  
**Dosyalar:** Yeni rehber dokümanı, `lib.sh` varyasyon

### Adımlar

1. **Kanıt enjeksiyon rehberi**
   ```bash
   # Yeni dosya: docs/architecture/Evidence-Injection-Rehberi.md
   # Kurallar: terminoloji eşleştirme, distraktör yasağı
   ```

2. **Biçim varyasyon mekanizması**
   ```bash
   # tools/agent-loop/lib.sh içine
   # serialize_tool_output() fonksiyonu
   # 3 farklı format varyasyonu (RANDOM % 3)
   # KV-cache prefix'ini etkilemeyecek konuma yerleştir
   ```

3. **Prompt yönergesi**
   ```bash
   # tools/agent-loop/prompts/implementer.md
   # Evidence injection ve format varyasyon yönergesi
   ```

4. **Doğrulama scripti güncelle**

### Doğrulama
```bash
bash scripts/verify_context_engineering.sh
```

---

## Oturum 7: PageRank + Subagent Fan-Out ✓ TAMAMLANDI

**Süre:** 3-4 saat  
**Çözümler:** S08, S10  
**Dosyalar:** Yeni Python scriptleri, yeni dokümanlar

### Adımlar

1. **tree-sitter entegrasyonu**
   ```bash
   # Yeni dosya: scripts/extract_code_graph.py
   # tree-sitter ile tanım/referans etiketlerini çıkar
   # graphify-out/graph.json güncelle
   ```

2. **Personalized PageRank**
   ```bash
   # Yeni dosya: scripts/compute_pagerank.py
   # networkx ile personalized PageRank
   # Seed tanımlayıcılara yüksek ağırlık
   # Token bütçesine göre kes
   ```

3. **Context selection entegrasyonu**
   ```bash
   # tools/agent-loop/lib.sh içine
   # select_relevant_code() fonksiyonu
   # Graph-ranked kod bloklarını prompt'a ekle
   ```

4. **Subagent keşif protokolü**
   ```bash
   # Yeni dosya: docs/architecture/Subagent-Kesif-Protokolu.md
   # Salt-okunur yetki, SBAR dönüş formatı
   ```

5. **Subagent dönüş şablonu**
   ```bash
   # Yeni dosya: .agent/tasks/templates/subagent-return.json
   # SBAR slotlarıyla eşleşen keşif sonucu
   ```

6. **Doğrulama scripti güncelle**

### Yapılanlar
- [x] `scripts/extract_code_graph.py` → AST tabanlı kod grafiği çıkarma (Python stdlib `ast`)
- [x] `scripts/compute_pagerank.py` → Kişiselleştirilmiş PageRank (networkx, seed ağırlıklı)
- [x] `tools/agent-loop/lib.sh` → `select_relevant_code()` fonksiyonu eklendi
- [x] `tools/agent-loop/lib.sh` → `AGENT_GRAPH_CONTEXT` kill-switch eklendi
- [x] `tools/agent-loop/lib.sh` → `run_implementer()` içine graph-ranked bağlam entegrasyonu
- [x] `docs/architecture/Subagent-Kesif-Protokolu.md` → Salt-okunur keşif protokolü
- [x] `.agent/tasks/templates/subagent-return.json` → SBAR uyumlu dönüş şablonu
- [x] `scripts/verify_context_engineering.sh` → 8 yeni Session 7 doğrulama kontrolü eklendi

### Doğrulama
```bash
bash scripts/verify_context_engineering.sh
```

---

## Genel Kurallar

1. **Her oturum başında:**
   - Önceki oturumun doğrulamasını çalıştır
   - `git status` ile temiz başla

2. **Her oturum sonunda:**
   - `bash scripts/verify_context_engineering.sh` çalıştır
   - Tüm kontroller geçmeli
   - `git add -A && git commit -m "context-eng: iterasyon N — SXX açıklaması"`

3. **Test stratejisi:**
   - Her iterasyon için `tests/integration/test_*.sh` ekle
   - Controller test suite'i bozulmamalı

4. **Geri alma:**
   - Her iterasyon bağımsız geri alınabilir
   - `git revert` ile önceki iterasyona dönülebilir
