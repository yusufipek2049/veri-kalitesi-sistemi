# İterasyon 29 — Teknik Kontrol ve Banka Kabul Kanıt Paketi

## 29A — Teknik kanıt paketi manifesti ve eksik kontrol raporu

Durum: `TechnicallyVerified`

### Gereksinimler

- `BFR-SDLC-002`
- `BRULE-004`
- `BRULE-005`
- `NFR-CMP-002`
- `NFR-CMP-005`
- BDDK ve KVKK matrislerindeki 15 `CTRL-*` kaydı

### Kabul Sonucu

- Sürümlü JSON katalog tam 8 BDDK ve 7 KVKK kontrolünü kapsar; eksik veya fazla
  kontrol kaydı fail-closed reddedilir.
- Kanıt yolları yalnız `08-Uyum-Kanitlari/` altındaki göreli `.md/.json`
  artifact'larına açılır; traversal, mutlak yol, symlink, büyük ve eksik dosya
  reddedilir.
- Manifest her artifact'ı SHA-256 ile bağlar ve kontrol sırasından bağımsız,
  deterministik JSON üretir; kanıt içeriğini manifestte çoğaltmaz.
- Teknik durum, banka inceleme durumu ve açık `OPEN-BNK-*` engelleri ayrı tutulur.
- `ApprovedByBank` ve `NotApplicable` yalnız opak karar referansıyla kabul edilir.
- Mevcut katalog 15 kontrolün 12'sini `Partial`, 3'ünü `Missing`, 14'ünü açık
  kararlarla engelli ve tamamını `ComplianceReviewRequired` olarak raporlar.
- 37 yeni sentetik vakayla toplam 667 birim testi geçmiştir.

### Kapsam Dışı

- Banka adına kontrol onayı veya mevzuat uyumluluğu kararı
- Elektronik imza, WORM, HSM veya kurumsal kanıt deposu
- CI/CD artifact yayınlama ve drift kapısı
- Eksik DR, imha, aktarım, gerçek scanner/pentest ve üretim entegrasyonlarının uygulanması
- Onaylayan kimlik çözümleyicisi, maker-checker ve banka iş akışı

## 29B — Teknik kanıt manifesti drift doğrulama kapısı

Durum: `TechnicallyVerified`

### Gereksinimler

- `BFR-SDLC-002`
- `BRULE-004`
- `BRULE-005`
- `NFR-CMP-002`
- `NFR-CMP-005`

### Kabul Sonucu

- `29B-v1` kapısı 29A katalog ve kanıtlarından manifesti kanonik baytlarla yeniden
  üretir ve depodaki sürüm manifestiyle bayt düzeyinde karşılaştırır.
- Eşleşme `MATCH` ve çıkış kodu `0`, drift `DRIFT` ve çıkış kodu `1`, doğrulama
  veya teknik hata veri-minimum neden koduyla çıkış kodu `2` üretir.
- Depodaki manifest yalnız `08-Uyum-Kanitlari/Surum-Paketleri/` altındaki kanonik
  `.json` yolundan okunur; traversal, mutlak yol, symlink, eksik, düzenli olmayan
  ve 2 MiB üzeri dosya fail-closed reddedilir.
- Sonuç yalnız politika, durum ve saklanan/üretilen SHA-256 özetlerini taşır;
  manifest veya kanıt içeriğini çoğaltmaz.
- Gerçek 29A artifact'ı `MATCH` sonucu ve aynı
  `8909af184797ffe493082f2a9a8ebbfbad818c987416830a76732ec15eaa8a24`
  özetiyle doğrulanmıştır.
- 15 yeni sentetik vakayla toplam 682 birim testi geçmiştir.

### Kapsam Dışı

- CI/CD ürünü veya pipeline zorlaması
- Elektronik imza, WORM, HSM veya kurumsal kanıt deposu
- İstisna/risk kabulü ve release maker-checker akışı
- Banka adına kontrol onayı veya mevzuat uyumluluğu kararı

## Önerilen Sonraki Dilim

**29C — Birleşik yerel sürüm ön kontrolü.**

Mevcut secret taraması, SBOM yeniden üretimi, veri-minimum güvenlik kapıları ve 29B
manifest drift doğrulamasını tek fail-closed yerel komutta sırayla çalıştır. Yeni
scanner, CI/CD ürünü, istisna/risk kabulü, imzalama ve banka onayı eklenmesin.
