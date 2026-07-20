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

## 28B — Deterministik yerel bağımlılık envanteri ve SBOM başlangıç paketi

Durum: `TechnicallyVerified`

### Gereksinimler

- `BFR-SDLC-001`
- `BFR-SDLC-002`
- `BFR-SDLC-004`
- `NFR-SEC-012`

### Kabul Sonucu

- PEP 621 proje adı, `0.1.0` sürümü, Python sınırı ve doğrudan çalışma zamanı
  bağımlılıkları açıkça beyan edilmiştir.
- Yalnız tam sürüme sabitlenmiş paketler kabul edilir; dinamik, URL/path tabanlı,
  extras içeren veya yinelenen beyanlar başarısız olur.
- CycloneDX 1.5 çıktı deterministiktir; proje sürümü ve doğrudan bağımlılık
  grafiğini taşır, zaman damgası/seri numarası/yerel yol içermez.
- Sürüm artifact'ı yeniden üretilen çıktıyla byte düzeyinde eşleşmiş ve resmî
  CycloneDX 1.5 JSON şemasını geçmiştir.
- 19 yeni sentetik vakayla toplam 530 birim testi geçmiştir.

### Kapsam Dışı

- Transitive bağımlılık çözümleme ve lock dosyası
- Paket/artifact hash'i ve lisans doğrulaması
- Ağ tabanlı zafiyet sorgusu
- CI/CD zorlaması ve harici SBOM/dependency scanner ürünü
- Banka eşik, istisna ve risk kabulü

## Önerilen Sonraki Dilim

**28C — Yerel SAST bulgu ve sürüm kapısı sözleşmesi.**

Ürün bağımsız, veri-minimum bir SAST bulgu zarfı ve kritik bulgu bulunduğunda
üretim adayı kanıtını reddeden yerel sürüm kapısı oluştur; gerçek scanner ürünü,
CI/CD entegrasyonu, istisna onayı ve DAST kapsam dışında kalsın.
