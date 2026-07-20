# İterasyon 28 — Güvenli SDLC ve Güvenlik Testi Hazırlığı

## 28A — Yerel veri-minimum secret tarama sözleşmesi

Durum: `TechnicallyVerified`

### Gereksinimler

- `BFR-SDLC-001`
- `BFR-SDLC-002`
- `NFR-SEC-005`
- `NFR-SEC-012`

### Kabul Sonucu

- Repository metin dosyaları salt okunur ve deterministik taranır.
- `.git`, cache, build ve bağımlılık dizinleri; binary, büyük, düzenli olmayan ve
  sembolik bağlantılı dosyalar dışlanır.
- Sonuç yalnız göreli dosya yolu, satır/sütun ve kural kodu taşır; eşleşen değer,
  satır içeriği ve ham teknik hata yoktur.
- Temiz, bulgulu ve teknik olarak tamamlanamayan taramalar ayrı çıkış kodlarına sahiptir.
- 13 sentetik birim testi ve temiz yerel repository taramasıyla doğrulanmıştır.

### Kapsam Dışı

- CI/CD ürünü ve pipeline zorlaması
- Harici secret scanner servisi ve geçmiş commit taraması
- Bağımlılık/SAST/DAST taraması
- SBOM üretimi ve sürüm bağlantısı
- Pentest ürünü, kapsamı ve banka onayı

## Önerilen Sonraki Dilim

**28B — Deterministik yerel bağımlılık envanteri ve SBOM başlangıç paketi.**

Yalnız repository'deki beyan edilmiş Python bağımlılıklarını salt okunur ve
deterministik bir bileşen listesine dönüştür; ağ tabanlı zafiyet sorgusu, CI/CD
zorlaması ve banka ürün seçimini kapsam dışında tut.
