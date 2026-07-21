---
iteration: 32
status: TechnicallyVerified
completed_at: 2026-07-21
---

# İterasyon 32 — Kısmi Skor Politikası

## 32A — Dataset kısmi skor politika kararı

- **İterasyon adı:** Dataset kısmi skor politika kararı
- **Kullanıcı/sistem değeri:** Kısmi çalışma, onaylı dataset politikasındaki tüm
  koşullar sağlanmadan resmî kabul edilemez; karar nedenleri deterministik ve
  açıklanabilirdir.
- **Mevcut FR/UC/RULE:** `FR-048`, `UC-009`, `OPEN-012`, `OPEN-018`
- **BFR/CTRL:** Yeni eşleme yoktur.
- **Değiştirilen dosyalar:** Skorlama hata/paket yüzeyi, yeni kısmi skor politika
  modeli/deposu/servisi, birim testleri ve proje hafızası.
- **Migration/config:** SQLite `dataset_partial_score_policies` tablosu eklendi.
  Üretim eşik değeri veya ürün adı eklenmedi; test değerleri yalnız sentetiktir.
- **Eklenen testler:** Sürüm/geçerlilik çözümleme, tüm koşullarda resmî karar,
  yedi ayrı koşul ihlalinde provizyonel karar, politikasız fail-closed davranış,
  onaysız politika dışlama, maker-checker ayrımı, çelişkili olgu doğrulaması ve
  depo teknik hatası.
- **Çalıştırılan komutlar:** `pytest -q`, `mypy 03-Backend/src
  06-Testler/01-Birim`, `ruff check .`, hedefli `ruff format` ve `python3 -m
  compileall -q 03-Backend/src`.
- **Mevcut regresyon sonucu:** 888 test geçti; mypy 131 dosyada, Ruff ve derleme
  hatasız tamamlandı.
- **Yetkisiz/negatif test sonucu:** Onaysız politika etkili seçilmedi; maker kendi
  politikasını onaylayamadı; politika yokluğu ve her koşul ihlali provizyonel
  kararla sonuçlandı.
- **Audit/redaksiyon sonucu:** Politika yalnız opak kural/partition, aktör ve audit
  referansları ile oranları taşır; ham kayıt, secret veya bağlantı bilgisi içermez.
- **Kanıt yolları:** `06-Testler/01-Birim/test_partial_score_policies.py`.
- **Teknik durum:** `TechnicallyVerified`
- **Banka onayı:** `ComplianceReviewRequired`
- **Kalan risk:** Ölçülmüş olguların worker/execution tarafından üretilmesi,
  kararın `QualityScore`, resmî agregasyon, trend, SLA ve raporlamaya bağlanması,
  politika yaşam döngüsünün merkezi audit outbox'ı ve banka rol eşlemesi.
- **Geri alma yaklaşımı:** Kısmi politika servisi skor akışına henüz bağlı değildir;
  modül kaldırıldığında mevcut tüm kısmi sonuçları resmî skordan dışlayan güvenli
  davranış değişmeden kalır. SQLite tablosu silinmez.
- **Sonraki iterasyon:** 32B, kısmi skor politika kararının `QualityScore`
  üretimine ve resmî agregasyon dışlama bilgisine bağlanması.
