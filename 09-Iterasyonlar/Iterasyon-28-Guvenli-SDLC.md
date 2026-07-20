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

## 28C — Yerel SAST bulgu ve sürüm kapısı sözleşmesi

Durum: `TechnicallyVerified`

### Gereksinimler

- `BFR-SDLC-001`
- `BFR-SDLC-002`
- `BFR-SDLC-003`
- `NFR-SEC-012`

### Kabul Sonucu

- Ürün bağımsız SAST bulgusu yalnız scanner kimliği/sürümü, kural kodu, önem
  derecesi ve repository-relative satır/sütun konumunu kabul eder.
- Kaynak satırı, snippet, scanner mesajı, açıklama, secret ve mutlak/üst dizine
  çıkan konum allowlist dışı olarak fail-closed reddedilir.
- Tamamlanmamış tarama ayrı `SastGateTechnicalError` üretir ve sürüm kanıtı vermez.
- Tamamlanmış taramadaki her `CRITICAL` bulgu sürüm kanıtını
  `SastGateBlockedError` ile engeller; kritik olmayan bulgular sayılır ve kanonik
  bulgu özetine bağlanır.
- Başarılı kanıt PEP 621 proje adı/sürümü, `28C-v1` politika ve scanner sürümünü
  deterministik SHA-256 özetiyle ilişkilendirir; bulgu yolu/kural kodunu kanıta
  açık metin taşımaz.
- 26 sentetik vakayla toplam 556 birim testi geçmiştir.

### Kapsam Dışı

- Gerçek SAST scanner ürünü ve repository taraması
- CI/CD/pipeline zorlaması ve artifact üretimi
- Kritik olmayan banka eşikleri, istisna ve risk kabul onayı
- DAST, container/IaC taraması ve penetrasyon testi
- Release maker-checker ve banka onayı

## 28D — Yerel bağımlılık zafiyet bulgu zarfı ve sürüm kapısı sözleşmesi

Durum: `TechnicallyVerified`

### Gereksinimler

- `BFR-SDLC-001`
- `BFR-SDLC-002`
- `BFR-SDLC-003`
- `BFR-SDLC-004`
- `NFR-SEC-012`

### Kabul Sonucu

- Ürün bağımsız bulgu yalnız scanner/advisory kimliği ve sürümü, advisory kimliği,
  önem derecesi ile kanonik doğrudan bağımlılık adı/sürümünü kabul eder.
- Açıklama, mesaj, advisory URL, düzeltme sürümü, yerel yol ve secret allowlist dışı
  olarak fail-closed reddedilir.
- Bulgu yalnız 28B envanterindeki tam kanonik paket/sürüm çiftiyle eşleşebilir;
  bilinmeyen veya farklı sürümdeki paket reddedilir.
- Tamamlanmamış tarama ayrı teknik hata üretir; `CRITICAL` bulgu sürüm kanıtını
  fail-closed engeller. Kritik olmayan bulgular yalnız sayım ve digest'e bağlanır.
- Başarılı kanıt proje sürümü, `declared-direct-dependencies` kapsamı,
  scanner/advisory sürümleri ve deterministik envanter/bulgu SHA-256 özetlerini taşır.
- 37 sentetik vakayla toplam 593 birim testi geçmiştir.

### Kapsam Dışı

- Gerçek zafiyet veritabanı, ağ erişimi ve dependency scanner ürünü
- Transitive çözümleme/lock ve artifact doğrulaması
- Kritik olmayan banka eşikleri ile istisna/risk kabul onayı
- CI/CD zorlaması, release maker-checker ve banka onayı
- DAST, container/IaC taraması ve penetrasyon testi

## Önerilen Sonraki Dilim

**28E — Veri-minimum sızma testi bulgu takip sözleşmesi.**

`BFR-SDLC-003/005` kapsamında sızma testi bulgusunu önem, veri-minimum aksiyon ve
sorumlu referansı ile tekrar test kanıtına bağla. Gerçek test hizmeti, banka kapsamı,
takvim/sıklık, scanner ürünü, serbest rapor içeriği ve banka onayı kapsam dışında kalsın.
