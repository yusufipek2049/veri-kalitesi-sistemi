#!/usr/bin/env bash
# scripts/verify_context_engineering.sh
# İterasyon 1 değişikliklerini doğrula
set -euo pipefail

echo "=== Context Engineering İterasyon 1 Doğrulama ==="
echo

# 1. --sort-keys kullanımı
echo "1. refresh_contract() içinde --sort-keys kullanımı:"
if grep -q "jq --sort-keys" tools/agent-loop/lib.sh; then
  echo "   ✓ --sort-keys parametresi eklendi"
else
  echo "   ✗ --sort-keys parametresi BULUNAMADI"
  exit 1
fi
echo

# 2. collect_error_evidence() fonksiyonu
echo "2. collect_error_evidence() fonksiyonu:"
if grep -q "collect_error_evidence()" tools/agent-loop/lib.sh; then
  echo "   ✓ Fonksiyon tanımlandı"
else
  echo "   ✗ Fonksiyon BULUNAMADI"
  exit 1
fi
echo

# 3. collect_error_evidence() çağrısı
echo "3. run_implementer() içinde collect_error_evidence() çağrısı:"
if grep -q "collect_error_evidence \"\$iteration\"" tools/agent-loop/lib.sh; then
  echo "   ✓ Fonksiyon çağrılıyor"
else
  echo "   ✗ Fonksiyon ÇAĞRILMIYOR"
  exit 1
fi
echo

# 4. Prompt template güncellemesi
echo "4. implementer.md prompt template güncellemesi:"
if grep -q "Error Evidence" tools/agent-loop/prompts/implementer.md; then
  echo "   ✓ Error Evidence bölümü eklendi"
else
  echo "   ✗ Error Evidence bölümü BULUNAMADI"
  exit 1
fi
echo

# 5. Cache politika dokümanı
echo "5. Context-Cache-Politikasi.md dokümanı:"
if [[ -f "docs/architecture/Context-Cache-Politikasi.md" ]]; then
  echo "   ✓ Doküman oluşturuldu"
else
  echo "   ✗ Doküman OLUŞTURULMADI"
  exit 1
fi
echo

# --- İterasyon 2: SBAR Devir Teslim ---
echo "=== Context Engineering İterasyon 2 Doğrulama (SBAR) ==="
echo

# 6. SBAR şablon fonksiyonu
echo "6. sbar_template_json() fonksiyonu:"
if grep -q "sbar_template_json()" tools/agent-loop/ledger.sh; then
  echo "   ✓ Fonksiyon tanımlandı"
else
  echo "   ✗ Fonksiyon BULUNAMADI"
  exit 1
fi
echo

# 7. sbar_validate() fonksiyonu
echo "7. sbar_validate() fonksiyonu:"
if grep -q "sbar_validate()" tools/agent-loop/ledger.sh; then
  echo "   ✓ Fonksiyon tanımlandı"
else
  echo "   ✗ Fonksiyon BULUNAMADI"
  exit 1
fi
echo

# 8. handoff_write() SBAR slotları
echo "8. handoff_write() SBAR şema kullanımı:"
if grep -q "sbar_schema: v1" tools/agent-loop/ledger.sh; then
  echo "   ✓ SBAR şema başlığı handoff'e yazılıyor"
else
  echo "   ✗ SBAR şema başlığı BULUNAMADI"
  exit 1
fi

if grep -q '## Situation (Durum)' tools/agent-loop/ledger.sh; then
  echo "   ✓ Situation slotu mevcut"
else
  echo "   ✗ Situation slotu BULUNAMADI"
  exit 1
fi

if grep -q '## Background (Bağlam)' tools/agent-loop/ledger.sh; then
  echo "   ✓ Background slotu mevcut"
else
  echo "   ✗ Background slotu BULUNAMADI"
  exit 1
fi

if grep -q '## Assessment (Değerlendirme)' tools/agent-loop/ledger.sh; then
  echo "   ✓ Assessment slotu mevcut"
else
  echo "   ✗ Assessment slotu BULUNAMADI"
  exit 1
fi

if grep -q '## Recommendation (Öneri)' tools/agent-loop/ledger.sh; then
  echo "   ✓ Recommendation slotu mevcut"
else
  echo "   ✗ Recommendation slotu BULUNAMADI"
  exit 1
fi

if grep -q '## Other (Ek Bilgiler)' tools/agent-loop/ledger.sh; then
  echo "   ✓ Other slotu mevcut"
else
  echo "   ✗ Other slotu BULUNAMADI"
  exit 1
fi
echo

# 9. SBAR JSON bloğu
echo "9. SBAR JSON bloğu üretimi:"
if grep -q '```sbar' tools/agent-loop/ledger.sh; then
  echo "   ✓ SBAR JSON fence'i eklendi"
else
  echo "   ✗ SBAR JSON fence'i BULUNAMADI"
  exit 1
fi
echo

# 10. implementer.md SBAR yönergesi
echo "10. implementer.md SBAR Handoff Schema bölümü:"
if grep -q "SBAR Handoff Schema" tools/agent-loop/prompts/implementer.md; then
  echo "   ✓ SBAR yönergesi eklendi"
else
  echo "   ✗ SBAR yönergesi BULUNAMADI"
  exit 1
fi
echo

# 11. ledger_init SBAR şablon yazımı
echo "11. ledger_init() SBAR şablon dosyası yazımı:"
if grep -q 'sbar-handoff.json' tools/agent-loop/ledger.sh; then
  echo "   ✓ Şablon dosyası init'te oluşturuluyor"
else
  echo "   ✗ Şablon dosyası BULUNAMADI"
  exit 1
fi
echo

# --- İterasyon 3: Hedef Tekrarlama (Recitation) ---
echo "=== Context Engineering İterasyon 3 Doğrulama (Recitation) ==="
echo

# 12. should_recite_goal() fonksiyonu
echo "12. should_recite_goal() fonksiyonu:"
if grep -q "should_recite_goal()" tools/agent-loop/lib.sh; then
  echo "   ✓ Fonksiyon tanımlandı"
else
  echo "   ✗ Fonksiyon BULUNAMADI"
  exit 1
fi
echo

# 13. ACTIVE GOAL REMINDER bloğu
echo "13. run_implementer() içinde ACTIVE GOAL REMINDER bloğu:"
if grep -q "ACTIVE GOAL REMINDER" tools/agent-loop/lib.sh; then
  echo "   ✓ Recitation bloğu eklendi"
else
  echo "   ✗ Recitation bloğu BULUNAMADI"
  exit 1
fi
echo

# 14. implementer.md Active Goal Reminder yönergesi
echo "14. implementer.md Active Goal Reminder yönergesi:"
if grep -q "Active Goal Reminder" tools/agent-loop/prompts/implementer.md; then
  echo "   ✓ Yönerge eklendi"
else
  echo "   ✗ Yönerge BULUNAMADI"
  exit 1
fi
echo

# --- İterasyon 4: Katmanlı Sıkıştırma Bütçesi ---
echo "=== Context Engineering İterasyon 4 Doğrulama (Compaction) ==="
echo

# 15. compaction.sh modülü
echo "15. tools/agent-loop/compaction.sh modülü:"
if [[ -f "tools/agent-loop/compaction.sh" ]]; then
  echo "   ✓ Modül oluşturuldu"
else
  echo "   ✗ Modül OLUŞTURULMADI"
  exit 1
fi
echo

# 16. compact_segment.py scripti
echo "16. scripts/compact_segment.py scripti:"
if [[ -f "scripts/compact_segment.py" ]]; then
  echo "   ✓ Script oluşturuldu"
else
  echo "   ✗ Script OLUŞTURULMADI"
  exit 1
fi
echo

# 17. Context-Compaction-Politikasi.md dokümanı
echo "17. Context-Compaction-Politikasi.md dokümanı:"
if [[ -f "docs/architecture/Context-Compaction-Politikasi.md" ]]; then
  echo "   ✓ Doküman oluşturuldu"
else
  echo "   ✗ Doküman OLUŞTURULMADI"
  exit 1
fi
echo

# 18. compaction.sh source edilmesi
echo "18. lib.sh'de compaction.sh source edilmesi:"
if grep -q 'source.*compaction.sh' tools/agent-loop/lib.sh; then
  echo "   ✓ compaction.sh source ediliyor"
else
  echo "   ✗ compaction.sh SOURCE EDİLMİYOR"
  exit 1
fi
echo

# 19. compaction_needed() çağrısı
echo "19. run_implementer() içinde compaction_needed() çağrısı:"
if grep -q "compaction_needed" tools/agent-loop/lib.sh; then
  echo "   ✓ compaction_needed() çağrılıyor"
else
  echo "   ✗ compaction_needed() ÇAĞRILMIYOR"
  exit 1
fi
echo

# 20. compact_prompt() çağrısı
echo "20. run_implementer() içinde compact_prompt() çağrısı:"
if grep -q "compact_prompt" tools/agent-loop/lib.sh; then
  echo "   ✓ compact_prompt() çağrılıyor"
else
  echo "   ✗ compact_prompt() ÇAĞRILMIYOR"
  exit 1
fi
echo

# --- İterasyon 5: Delta Compaction + Durum Soyutlaması ---
echo "=== Context Engineering İterasyon 5 Doğrulama (Delta + Soyutlama) ==="
echo

# 21. bullet_init() fonksiyonu
echo "21. bullet_init() fonksiyonu:"
if grep -q "bullet_init()" tools/agent-loop/compaction.sh; then
  echo "   ✓ Fonksiyon tanımlandı"
else
  echo "   ✗ Fonksiyon BULUNAMADI"
  exit 1
fi
echo

# 22. apply_delta_operations() fonksiyonu
echo "22. apply_delta_operations() fonksiyonu:"
if grep -q "apply_delta_operations()" tools/agent-loop/compaction.sh; then
  echo "   ✓ Fonksiyon tanımlandı"
else
  echo "   ✗ Fonksiyon BULUNAMADI"
  exit 1
fi
echo

# 23. state_abstraction.sh modülü
echo "23. tools/agent-loop/state_abstraction.sh modülü:"
if [[ -f "tools/agent-loop/state_abstraction.sh" ]]; then
  echo "   ✓ Modül oluşturuldu"
else
  echo "   ✗ Modül OLUŞTURULMADI"
  exit 1
fi
echo

# 24. abstract_tool_output() fonksiyonu
echo "24. abstract_tool_output() fonksiyonu:"
if grep -q "abstract_tool_output()" tools/agent-loop/state_abstraction.sh; then
  echo "   ✓ Fonksiyon tanımlandı"
else
  echo "   ✗ Fonksiyon BULUNAMADI"
  exit 1
fi
echo

# 25. print_state_delta() fonksiyonu
echo "25. print_state_delta() fonksiyonu:"
if grep -q "print_state_delta()" tools/agent-loop/state_abstraction.sh; then
  echo "   ✓ Fonksiyon tanımlandı"
else
  echo "   ✗ Fonksiyon BULUNAMADI"
  exit 1
fi
echo

# 26. state_abstraction.sh source edilmesi
echo "26. lib.sh'de state_abstraction.sh source edilmesi:"
if grep -q 'source.*state_abstraction.sh' tools/agent-loop/lib.sh; then
  echo "   ✓ state_abstraction.sh source ediliyor"
else
  echo "   ✗ state_abstraction.sh SOURCE EDİLMİYOR"
  exit 1
fi
echo

# 27. CONTEXT_BULLETS_FILE init
echo "27. agentloop_init() içinde CONTEXT_BULLETS_FILE init:"
if grep -q "CONTEXT_BULLETS_FILE=" tools/agent-loop/lib.sh; then
  echo "   ✓ CONTEXT_BULLETS_FILE tanımlandı"
else
  echo "   ✗ CONTEXT_BULLETS_FILE BULUNAMADI"
  exit 1
fi
echo

# --- İterasyon 6: Semantik Yakınlık + Biçim Varyasyonu ---
echo "=== Context Engineering İterasyon 6 Doğrulama (Evidence Injection + Format Varyasyonu) ==="
echo

# 28. serialize_tool_output() fonksiyonu
echo "28. serialize_tool_output() fonksiyonu:"
if grep -q "serialize_tool_output()" tools/agent-loop/lib.sh; then
  echo "   ✓ Fonksiyon tanımlandı"
else
  echo "   ✗ Fonksiyon BULUNAMADI"
  exit 1
fi
echo

# 29. Format varyasyonu desteği (3 format)
echo "29. serialize_tool_output() format varyasyonu desteği:"
if grep -q 'case "\$format_variant" in' tools/agent-loop/lib.sh; then
  echo "   ✓ 3 format varyasyonu destekleniyor"
else
  echo "   ✗ Format varyasyonu BULUNAMADI"
  exit 1
fi
echo

# 30. random_format_variant() fonksiyonu
echo "30. random_format_variant() fonksiyonu:"
if grep -q "random_format_variant()" tools/agent-loop/lib.sh; then
  echo "   ✓ Fonksiyon tanımlandı"
else
  echo "   ✗ Fonksiyon BULUNAMADI"
  exit 1
fi
echo

# 31. Evidence-Injection-Rehberi.md dokümanı
echo "31. Evidence-Injection-Rehberi.md dokümanı:"
if [[ -f "docs/architecture/Evidence-Injection-Rehberi.md" ]]; then
  echo "   ✓ Doküman oluşturuldu"
else
  echo "   ✗ Doküman OLUŞTURULMADI"
  exit 1
fi
echo

# 32. implementer.md Evidence Injection yönergesi
echo "32. implementer.md Evidence Injection (S12) yönergesi:"
if grep -q "Evidence Injection (S12)" tools/agent-loop/prompts/implementer.md; then
  echo "   ✓ Evidence Injection yönergesi eklendi"
else
  echo "   ✗ Evidence Injection yönergesi BULUNAMADI"
  exit 1
fi
echo

# 33. Terminoloji eşleştirme kuralı
echo "33. implementer.md terminoloji eşleştirme kuralı:"
if grep -q "Terminology Matching" tools/agent-loop/prompts/implementer.md; then
  echo "   ✓ Terminoloji eşleştirme kuralı eklendi"
else
  echo "   ✗ Terminoloji eşleştirme kuralı BULUNAMADI"
  exit 1
fi
echo

# 34. Distraktör yasağı kuralı
echo "34. implementer.md distraktör yasağı kuralı:"
if grep -q "Distractor Prohibition" tools/agent-loop/prompts/implementer.md; then
  echo "   ✓ Distraktör yasağı kuralı eklendi"
else
  echo "   ✗ Distraktör yasağı kuralı BULUNAMADI"
  exit 1
fi
echo

# 35. Format varyasyonu yönergesi
echo "35. implementer.md format varyasyonu yönergesi:"
if grep -q "Format Variation" tools/agent-loop/prompts/implementer.md; then
  echo "   ✓ Format varyasyonu yönergesi eklendi"
else
  echo "   ✗ Format varyasyonu yönergesi BULUNAMADI"
  exit 1
fi
echo

# --- İterasyon 7: PageRank + Subagent Fan-Out ---
echo "=== Context Engineering İterasyon 7 Doğrulama (PageRank + Subagent) ==="
echo

# 36. extract_code_graph.py scripti
echo "36. scripts/extract_code_graph.py scripti:"
if [[ -f "scripts/extract_code_graph.py" ]]; then
  echo "   ✓ Script oluşturuldu"
else
  echo "   ✗ Script OLUŞTURULMADI"
  exit 1
fi
echo

# 37. compute_pagerank.py scripti
echo "37. scripts/compute_pagerank.py scripti:"
if [[ -f "scripts/compute_pagerank.py" ]]; then
  echo "   ✓ Script oluşturuldu"
else
  echo "   ✗ Script OLUŞTURULMADI"
  exit 1
fi
echo

# 38. select_relevant_code() fonksiyonu
echo "38. select_relevant_code() fonksiyonu:"
if grep -q "select_relevant_code()" tools/agent-loop/lib.sh; then
  echo "   ✓ Fonksiyon tanımlandı"
else
  echo "   ✗ Fonksiyon BULUNAMADI"
  exit 1
fi
echo

# 39. AGENT_GRAPH_CONTEXT kill-switch
echo "39. AGENT_GRAPH_CONTEXT kill-switch:"
if grep -q 'AGENT_GRAPH_CONTEXT' tools/agent-loop/lib.sh; then
  echo "   ✓ Kill-switch tanımlandı"
else
  echo "   ✗ Kill-switch BULUNAMADI"
  exit 1
fi
echo

# 40. select_relevant_code çağrısı (run_implementer içinde)
echo "40. run_implementer() içinde select_relevant_code() çağrısı:"
if grep -q 'select_relevant_code "\$SELECTED_SCOPE_HINT"' tools/agent-loop/lib.sh; then
  echo "   ✓ Fonksiyon çağrılıyor"
else
  echo "   ✗ Fonksiyon ÇAĞRILMIYOR"
  exit 1
fi
echo

# 41. Subagent keşif protokolü dokümanı
echo "41. Subagent-Kesif-Protokolu.md dokümanı:"
if [[ -f "docs/architecture/Subagent-Kesif-Protokolu.md" ]]; then
  echo "   ✓ Doküman oluşturuldu"
else
  echo "   ✗ Doküman OLUŞTURULMADI"
  exit 1
fi
echo

# 42. subagent-return.json şablonu (geçerli JSON)
echo "42. subagent-return.json şablonu:"
if [[ -f ".agent/tasks/templates/subagent-return.json" ]] \
   && jq empty ".agent/tasks/templates/subagent-return.json" 2>/dev/null; then
  echo "   ✓ Şablon oluşturuldu ve geçerli JSON"
else
  echo "   ✗ Şablon OLUŞTURULMADI veya geçersiz JSON"
  exit 1
fi
echo

# 43. subagent-return.json SBAR slotları
echo "43. subagent-return.json SBAR slotları:"
sbar_ok=true
for slot in situation background assessment recommendation; do
  if jq -e ".$slot" ".agent/tasks/templates/subagent-return.json" >/dev/null 2>&1; then
    echo "   ✓ '$slot' slotu mevcut"
  else
    echo "   ✗ '$slot' slotu BULUNAMADI"
    sbar_ok=false
  fi
done
if [[ "$sbar_ok" != "true" ]]; then
  exit 1
fi
echo

echo "=== Tüm doğrulamalar başarılı ==="
echo
echo "İterasyon 1 değişiklikleri:"
echo "  - tools/agent-loop/lib.sh: --sort-keys + collect_error_evidence()"
echo "  - tools/agent-loop/prompts/implementer.md: Error Evidence bölümü"
echo "  - docs/architecture/Context-Cache-Politikasi.md: Yeni doküman"
echo
echo "İterasyon 2 değişiklikleri:"
echo "  - tools/agent-loop/ledger.sh: sbar_template_json() + sbar_validate()"
echo "  - tools/agent-loop/ledger.sh: handoff_write() SBAR şemasına dönüştürüldü"
echo "  - tools/agent-loop/prompts/implementer.md: SBAR Handoff Schema yönergesi"
echo
echo "İterasyon 3 değişiklikleri (Hedef Tekrarlama / Recitation):"
echo "  - tools/agent-loop/lib.sh: should_recite_goal() fonksiyonu"
echo "  - tools/agent-loop/lib.sh: ACTIVE GOAL REMINDER bloğu run_implementer() içinde"
echo "  - tools/agent-loop/prompts/implementer.md: Active Goal Reminder yönergesi"
echo
echo "İterasyon 4 değişiklikleri (Katmanlı Sıkıştırma Bütçesi):"
echo "  - tools/agent-loop/compaction.sh: Yeni modül"
echo "  - scripts/compact_segment.py: Yeni script"
echo "  - docs/architecture/Context-Compaction-Politikasi.md: Yeni doküman"
echo "  - tools/agent-loop/lib.sh: compaction.sh source + entegrasyon"
echo
echo "İterasyon 5 değişiklikleri (Delta Compaction + Durum Soyutlaması):"
echo "  - tools/agent-loop/compaction.sh: bullet_init/add/update/delete + apply_delta_operations()"
echo "  - tools/agent-loop/state_abstraction.sh: Yeni modül (abstract_tool_output, print_state_delta)"
echo "  - tools/agent-loop/lib.sh: state_abstraction.sh source + CONTEXT_BULLETS_FILE init"
echo
echo "İterasyon 6 değişiklikleri (Semantik Yakınlık + Biçim Varyasyonu):"
echo "  - tools/agent-loop/lib.sh: serialize_tool_output() + random_format_variant()"
echo "  - tools/agent-loop/prompts/implementer.md: Evidence Injection (S12) yönergesi"
echo "  - docs/architecture/Evidence-Injection-Rehberi.md: Yeni doküman"
echo
echo "İterasyon 7 değişiklikleri (PageRank + Subagent Fan-Out):"
echo "  - scripts/extract_code_graph.py: AST tabanlı kod grafiği çıkarma"
echo "  - scripts/compute_pagerank.py: Kişiselleştirilmiş PageRank sıralaması"
echo "  - tools/agent-loop/lib.sh: select_relevant_code() + AGENT_GRAPH_CONTEXT kill-switch"
echo "  - docs/architecture/Subagent-Kesif-Protokolu.md: Salt-okunur keşif protokolü"
echo "  - .agent/tasks/templates/subagent-return.json: SBAR uyumlu dönüş şablonu"
echo
echo "Tüm 7 iterasyon tamamlandı."
