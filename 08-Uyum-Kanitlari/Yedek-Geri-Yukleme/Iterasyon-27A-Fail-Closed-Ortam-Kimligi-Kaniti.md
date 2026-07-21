# İterasyon 27A — Fail-Closed Ortam Kimliği Kanıtı

## Kontrol Durumu

- Teknik durum: `TechnicallyVerified`
- Uyum durumu: `ComplianceReviewRequired`
- Tarih: 2026-07-21
- Üretici rolü: Codex geliştirme ajanı
- Kontroller: `CTRL-BDDK-OPS-001`, `CTRL-BDDK-SEC-001`
- Gereksinimler: `BFR-OPS-001`, `BFR-OPS-002`, `BRULE-004`, `BRULE-005`,
  `NFR-SEC-005`, `NFR-SEC-008`, `NFR-CMP-002`

## Teknik Kanıt

- Ortam kimliği yalnız sürümlü güvenilir konfigürasyon sağlayıcısından yüklenir;
  doğrudan konfigürasyon nesnesi veya yanlış güven sözleşmesi kaynak okunmadan
  reddedilir.
- `LOCAL`, `DEVELOPMENT`, `TEST`, `ACCEPTANCE` ve `PRODUCTION` ortamları ayrı
  sınıflardır. Secret kapsamı ortam sınıfıyla birebir eşleşmek zorundadır.
- Üretim dışı ortamda gerçek banka verisi kökeni ve üretim secret referansı
  fail-closed engellenir.
- Bozuk, kullanıcı bilgisi/sorgu taşıyan, bilinmeyen kapsamlı veya traversal içeren
  secret URI'si veri-minimum doğrulama hatası üretir.
- Sağlayıcı kesintisi politika ihlali veya temiz sonuç değildir; ayrı teknik hata
  üretir.
- Başarılı kanıt politika/revizyon, ortam, veri kökeni, secret kapsamı ve sabit
  kontrol kodlarını taşır. Secret referansı veya değeri kanıt modelinde bulunmaz.

## Doğrulama

- Hedef komut: `python3 -m pytest -q 06-Testler/01-Birim/test_environment_security.py`
- Hedef sonuç: 34 test geçti.
- Tam regresyon: 855 test geçti.
- Tam tip kontrolü: 127 kaynak dosyada sıfır hata.
- Ruff lint, değişen dosya format kontrolü ve derleme başarılıdır.

## Sınırlar

- Bu kapı gerçek veri kökenini taramaz, secret çözmez veya deployment platformunu
  doğrulamaz; güvenilir sağlayıcı adaptörünün doğru bileşime bağlanmasını gerektirir.
- Gerçek deployment platformu, kurumsal secret manager, konfigürasyon imzası ve
  attestation kaynağı `OPEN-BNK-012` ile açıktır.
- Yedek şifreleme, restore testi, RTO/RPO ve DR tatbikatı uygulanmadı;
  `CTRL-BDDK-BCP-001` `Missing` kalır ve `OPEN-BNK-011` geçerlidir.
- Bu teknik kanıt banka onayı veya mevzuat uyumluluğu sonucu değildir.

## Güvenli Geri Alma

27A kapısı bileşimden kaldırılabilir ancak bu durumda iş yükü için ortam ayrılığı
kanıtı üretilemez ve başlangıç varsayılan olarak engelli kabul edilmelidir. Önceki
ortam ayarına sessiz geri dönüş veya doğrulanmamış konfigürasyonla devam edilmez.
