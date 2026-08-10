# Subagent Keşif Protokolü (S10)

Salt-okunur alt-ajan keşif protokolü. Ana agent-loop tarafından, büyük kod
tabanında hedefli keşif yapmak için spawning edilir.

## Amaç

Ana implementer ajanı, görev kapsamını belirlerken geniş bir kod tabanında
doğru dosya ve fonksiyonları bulmakta zorlanabilir. Subagent keşif protokolü,
salt-okunur yetkiyle çalışan alt ajanların yapılandırılmış keşif sonuçları
döndürmesini sağlar.

## Kısıtlamalar

Subagent'ler aşağıdaki kısıtlamalara tabidir:

1. **Salt-okunur yetki**: Dosya sistemi üzerinde hiçbir değişiklik yapamaz.
   Yalnız okuma, arama ve analiz işlemleri gerçekleştirebilir.
2. **Yan etki yasağı**: Hiçbir dış servis çağrısı, veritabanı işlemi veya
   ağ isteği yapamaz.
3. **Zaman sınırı**: Her keşif görevi azami 5 dakika içinde tamamlanmalıdır.
4. **Kapsam daraltma**: Yalnız istenen konuyu araştırmalı; ilgisiz dosya ve
   modülleri raporlamamalıdır.

## Dönüş Formatı (SBAR Uyumlu)

Subagent dönüşleri, İterasyon 2'de tanımlanan SBAR şemasıyla uyumludur.
Şablon: `.agent/tasks/templates/subagent-return.json`

| Slot | Açıklama |
|------|----------|
| `situation` | Keşfin bağlamı: hangi görev/kapsam için araştırma yapıldı. |
| `background` | İncelenen modüller ve mevcut yapı hakkında özet bilgi. |
| `assessment` | Bulgular: incelenen dosyalar, kilit bulgular, bağımlılıklar, riskler. |
| `recommendation` | Önerilen aksiyon: hangi dosyalar değiştirilmeli, hangi kalıplar izlenmeli. |
| `other` | Ek bilgiler: graph-ranked düğümler, güven skoru, kapsam önerisi. |

## Ne Zaman Kullanılır

- **Büyük kod tabanı navigasyonu**: 50+ dosyaya sahip modüller arası keşif.
- **Çapraz modül etki analizi**: Bir değişikliğin hangi modülleri etkileyeceğini
  belirleme.
- **Bağımlılık keşfi**: Bir fonksiyonun çağrı zincirini ve etkilediği bileşenleri
  haritalama.
- **PageRank destekli bağlam**: `select_relevant_code()` ile grafikle sıralanmış
  kod bloklarının otomatik prompt'a eklenmesi.

## Entegrasyon

### select_relevant_code() ile Otomatik Keşif

`tools/agent-loop/lib.sh` içindeki `select_relevant_code()` fonksiyonu,
scope hint'leri seed olarak kullanarak `compute_pagerank.py` ile graph-ranked
kod bloklarını döndürür. Bu, manuel subagent spawning'e gerek kalmadan
otomatik bağlam seçimi sağlar.

```bash
# lib.sh içindeki kullanım (run_implementer prompt montajı):
graph_ctx="$(select_relevant_code "$SELECTED_SCOPE_HINT" 4000)"
```

### Manuel Subagent Spawning

Karmaşık keşif görevleri için ana ajan, alt ajan başlatabilir:

1. Keşif görevini tanımla (hangi modüller, hangi sorular).
2. Subagent'i salt-okunur yetkiyle başlat.
3. Dönüş formatına uygun SBAR raporu al.
4. Raporu implementer prompt'una ekle.

## Örnek Kullanım

### Graph-Ranked Bağlam (Otomatik)

```bash
# Scope hint'lerden seed çıkar:
#   "src/veri_kalitesi/api/main.py" -> seed: "src_veri_kalitesi_api_main"
# PageRank ile sırala:
python3 scripts/compute_pagerank.py \
  --seeds "src_veri_kalitesi_api_main" \
  --budget 4000 \
  --graph graphify-out/graph.json
```

### Manuel Keşif Raporu

```json
{
  "schema": "subagent-return",
  "version": 1,
  "status": "COMPLETED",
  "situation": "Scoring modülündeki calculate_score fonksiyonunun çağrı zinciri araştırıldı.",
  "background": "scoring/service.py ana giriş noktası; scoring/engine.py hesap motoru.",
  "assessment": {
    "files_examined": [
      "src/veri_kalitesi/scoring/service.py",
      "src/veri_kalitesi/scoring/engine.py",
      "src/veri_kalitesi/scoring/__init__.py"
    ],
    "key_findings": [
      "calculate_score() 3 farklı scorer sınıfını çağırır",
      "Her scorer RuleRepository'ye bağımlıdır"
    ],
    "dependencies": ["RuleRepository", "ScoreWeight", "ClassificationCode"],
    "risks": ["Ağırlık değişiklikleri tüm scorer'ları etkiler"]
  },
  "recommendation": "scoring/engine.py içindeki WeightedScorer sınıfından başla; RuleRepository mock'la.",
  "other": {
    "graph_ranked_nodes": ["scoring_engine_WeightedScorer", "scoring_service_calculate_score"],
    "confidence": 0.85,
    "scope_suggestion": ["src/veri_kalitesi/scoring/engine.py"]
  }
}
```

## Güvenlik

- Subagent'ler worktree izolasyonu içinde çalışır; ana branch'e doğrudan yazamaz.
- Dönüş verileri JSON şemasıyla doğrulanır; geçersiz alanlar reddedilir.
- Keşif sonuçları kanıt olarak saklanır (`.agent-handoff/logs/`).
