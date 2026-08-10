# Context Cache Politikası

Bu doküman, agent-loop'un context window kullanımında KV-cache koruma kurallarını tanımlar.

## Temel Prensip

**Append-only context:** Context'e yalnızca ekleme yapılır; geçmiş gözlemler düzenlenmez veya yeniden sıralanmaz.

## Kurallar

### 1. Sistem Promptu Sabit Kalır

- `tools/agent-loop/prompts/*.md` dosyaları runtime'da değiştirilmez
- Dinamik bilgi (timestamp, rastgele ID) sistem promptuna eklenmez
- Prompt template'lerde `{{timestamp}}`, `{{random_id}}` gibi pattern'ler yasaktır

### 2. Task Contract Append-Only

- `CURRENT_TASK.json` dosyası her turda güncellenir ama geçmiş sürümler silinmez
- JSON anahtar sırası deterministik olmalı (`jq --sort-keys`)
- Aynı içerik farklı byte sequence olarak cache'i kırmaz

### 3. Tool Çıktıları Düzenlenmez

- Başarısız tool call ve stderr logları context'ten çıkarılmaz (S06)
- Tool çıktılarının sırası korunur
- Kırpma veya özetleme yalnızca compaction aşamasında yapılır (İterasyon 4+)

### 4. JSON Key Ordering

- Tüm `jq` komutlarında `--sort-keys` kullanılır
- Manuel JSON üretimi