# Surum-Paketleri

Sürüm bazlı kontrol ve test kanıt paketleri.

Gerçek banka verisi veya secret eklenmez.

## Teknik Artifact'lar

- [İterasyon 28B - Proje 0.1.0 Doğrudan Bağımlılık SBOM'u](Iterasyon-28B-SBOM.cdx.json)
  - Biçim: CycloneDX 1.5 JSON
  - SHA-256: `cb74c19807ed7bff58cc7d8c474df24a0e15c7bbe8b7850007887e8338afc38b`
  - Kapsam: PEP 621 ile beyan edilmiş doğrudan çalışma zamanı bağımlılıkları
- [İterasyon 29A - Teknik Kanıt Kataloğu](Iterasyon-29A-Teknik-Kanit-Katalogu.json)
  - Biçim: Sürümlü veri-minimum JSON katalog
  - SHA-256: `6ba1f9b7460cddf92863ec8e57ed2df9d3317b096b42510daa0e2e3b727c0546`
- [İterasyon 29A - Teknik Kanıt Manifesti](Iterasyon-29A-Teknik-Kanit-Manifesti.json)
  - Biçim: Deterministik JSON manifest
  - SHA-256: `e83a5e1664c03c5d3506871f64b83f82237b2128b2a8d533dcb30d3571ed5db9`
  - Kapsam: 15 BDDK/KVKK kontrolü, 36 benzersiz teknik kanıt artifact'ı
- [İterasyon 29A - Teknik Kanıt Manifest Kanıtı](Iterasyon-29A-Teknik-Kanit-Manifest-Kaniti.md)
  - Durum: `TechnicallyVerified`; kontrol seviyesinde banka onayı değildir
- [İterasyon 29B - Teknik Kanıt Manifest Drift Kapısı Kanıtı](Iterasyon-29B-Teknik-Kanit-Manifest-Drift-Kapisi-Kaniti.md)
  - Durum: `TechnicallyVerified`; gerçek 29A manifesti byte düzeyinde `MATCH`
  - Politika: `29B-v1`; drift, doğrulama hatası ve teknik hata ayrı sonuçlardır
- [İterasyon 29C - Birleşik Yerel Sürüm Ön Kontrol Kanıtı](Iterasyon-29C-Birlesik-Yerel-Surum-On-Kontrol-Kaniti.md)
  - Durum: `TechnicallyVerified`; altı yerel kontrol sentetik rapor paketiyle birleştirilmiştir
  - Politika: `29C-v1`; gerçek scanner, CI/CD veya banka kabul kanıtı değildir
