# Surum-Paketleri

Sürüm bazlı kontrol ve test kanıt paketleri.

Gerçek banka verisi veya secret eklenmez.

## Teknik Artifact'lar

- [İterasyon 28B - Proje 0.1.0 Doğrudan Bağımlılık SBOM'u](Iterasyon-28B-SBOM.cdx.json)
  - Biçim: CycloneDX 1.5 JSON
  - SHA-256: `b97b67b2a8bc8f9ec574f0ab953710325399aa3ed7dae7434212f83d8ea209d3`
  - Kapsam: PEP 621 ile beyan edilmiş doğrudan çalışma zamanı bağımlılıkları
- [İterasyon 29A - Teknik Kanıt Kataloğu](Iterasyon-29A-Teknik-Kanit-Katalogu.json)
  - Biçim: Sürümlü veri-minimum JSON katalog
  - SHA-256: `1ff1e643da61a44ed6a87a7d28a146b67fa43813adc62b86c52bceefe38ce3a0`
- [İterasyon 29A - Teknik Kanıt Manifesti](Iterasyon-29A-Teknik-Kanit-Manifesti.json)
  - Biçim: Deterministik JSON manifest
  - SHA-256: `8909af184797ffe493082f2a9a8ebbfbad818c987416830a76732ec15eaa8a24`
  - Kapsam: 15 BDDK/KVKK kontrolü, 26 benzersiz teknik kanıt artifact'ı
- [İterasyon 29A - Teknik Kanıt Manifest Kanıtı](Iterasyon-29A-Teknik-Kanit-Manifest-Kaniti.md)
  - Durum: `TechnicallyVerified`; kontrol seviyesinde banka onayı değildir
- [İterasyon 29B - Teknik Kanıt Manifest Drift Kapısı Kanıtı](Iterasyon-29B-Teknik-Kanit-Manifest-Drift-Kapisi-Kaniti.md)
  - Durum: `TechnicallyVerified`; gerçek 29A manifesti byte düzeyinde `MATCH`
  - Politika: `29B-v1`; drift, doğrulama hatası ve teknik hata ayrı sonuçlardır
- [İterasyon 29C - Birleşik Yerel Sürüm Ön Kontrol Kanıtı](Iterasyon-29C-Birlesik-Yerel-Surum-On-Kontrol-Kaniti.md)
  - Durum: `TechnicallyVerified`; altı yerel kontrol sentetik rapor paketiyle birleştirilmiştir
  - Politika: `29C-v1`; gerçek scanner, CI/CD veya banka kabul kanıtı değildir
