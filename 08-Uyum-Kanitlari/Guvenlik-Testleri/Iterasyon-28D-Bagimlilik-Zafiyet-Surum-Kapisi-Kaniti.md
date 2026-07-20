# İterasyon 28D — Bağımlılık Zafiyet Sürüm Kapısı Kanıtı

- **Kontrol durumu:** `TechnicallyVerified`
- **Tarih:** 2026-07-20
- **Üretici rolü:** Teknik geliştirme ve test otomasyonu
- **Gereksinimler:** `BFR-SDLC-001`, `BFR-SDLC-002`, `BFR-SDLC-003`,
  `BFR-SDLC-004`, `NFR-SEC-012`
- **Kontrol bağlantısı:** `CTRL-BDDK-OPS-001` (`ComplianceReviewRequired`)
- **Politika sürümü:** `28D-v1`

## Doğrulanan Teknik Davranış

- Scanner/advisory çıktısı güvenilmez kabul edilir ve sekiz alanlı allowlist dışındaki
  açıklama, mesaj, URL, düzeltme sürümü, yerel yol ve secret reddedilir.
- Bulgular yalnız 28B `declared-direct-dependencies` envanterindeki tam kanonik
  paket/sürüm çiftleriyle eşleşebilir.
- `TECHNICAL_ERROR` temiz sonuç değildir ve sürüm kanıtı üretemez.
- Tamamlanmış rapordaki her `CRITICAL` bulgu sürüm kanıtını fail-closed engeller.
- Başarılı kanıt proje, gate, scanner ve advisory sürümlerini deterministik envanter
  ve bulgu SHA-256 özetleriyle bağlar; advisory/paket ayrıntısını açık metin taşımaz.
- Bulgu ve envanter sırası kanıt sonucunu değiştirmez.

## Çalıştırılan Kontroller

```bash
python3 -m pytest -q 06-Testler/01-Birim/test_secure_sdlc_vulnerabilities.py
python3 -m pytest -q
python3 -m ruff check .
python3 -m compileall -q 03-Backend/src 06-Testler/01-Birim
python3 -m mypy 03-Backend/src/veri_kalitesi/secure_sdlc/vulnerabilities.py 06-Testler/01-Birim/test_secure_sdlc_vulnerabilities.py
PYTHONPATH=03-Backend/src python3 -m veri_kalitesi.secure_sdlc .
```

Sonuç: 28D hedefinde 37 sentetik vaka, tam regresyonda 593 test geçti. Ruff,
hedef mypy ve derleme kontrolleri hatasız tamamlandı. Secret taraması 326 dosyada
`CLEAN` sonuçlandı. 28B SBOM yeniden üretimi mevcut artifact ile byte düzeyinde
eşleşti; SHA-256 `b97b67b2a8bc8f9ec574f0ab953710325399aa3ed7dae7434212f83d8ea209d3` kaldı.

## Kanıt Sınırı ve Kalan Risk

Bu kayıt gerçek zafiyet veritabanı sorgusu, ağ taraması, kurumsal scanner ürünü,
transitive lock/artifact doğrulaması, CI/CD zorlaması, istisna/risk kabulü, release
maker-checker, sızma testi veya banka onayı değildir. Banka bilgi güvenliği ve uyum
incelemesi `ComplianceReviewRequired` kalır. Güvenli pasifleştirme, bu yerel kapının
release akışına bağlanmaması; geri alma ise modül ve çağıran entegrasyonunun önceki
28B/28C sözleşmelerine döndürülmesidir.
