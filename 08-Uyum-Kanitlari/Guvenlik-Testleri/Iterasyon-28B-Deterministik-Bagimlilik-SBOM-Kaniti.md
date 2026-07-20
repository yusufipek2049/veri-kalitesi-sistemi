---
type: technical-evidence
status: TechnicallyVerified
control_ids:
  - BFR-SDLC-001
  - BFR-SDLC-002
  - BFR-SDLC-004
  - NFR-SEC-012
version: ITERATION_28B
date: 2026-07-20
producer_role: Codex
---

# İterasyon 28B Deterministik Bağımlılık ve SBOM Kanıtı

## Kapsam

- İterasyon: 28B - Deterministik yerel bağımlılık envanteri ve SBOM başlangıç paketi
- Commit/Artifact: `ITERATION_28B` (`origin/main`)
- Proje sürümü: `0.1.0`
- SBOM: `08-Uyum-Kanitlari/Surum-Paketleri/Iterasyon-28B-SBOM.cdx.json`
- SHA-256: `b97b67b2a8bc8f9ec574f0ab953710325399aa3ed7dae7434212f83d8ea209d3`
- Test: `06-Testler/01-Birim/test_secure_sdlc_sbom.py`

## Çalıştırılan Kontroller

```bash
python3 -m pytest -q
python3 -m ruff check .
python3 -m ruff format --check 03-Backend/src/veri_kalitesi/secure_sdlc 06-Testler/01-Birim/test_secure_sdlc.py 06-Testler/01-Birim/test_secure_sdlc_sbom.py
python3 -m mypy 03-Backend/src/veri_kalitesi/secure_sdlc 06-Testler/01-Birim/test_secure_sdlc.py 06-Testler/01-Birim/test_secure_sdlc_sbom.py
python3 -m compileall -q 03-Backend/src 06-Testler
PYTHONPATH=03-Backend/src python3 -m veri_kalitesi.secure_sdlc.sbom pyproject.toml
PYTHONPATH=03-Backend/src python3 -m veri_kalitesi.secure_sdlc .
```

## Sonuç

- 530 birim testi geçti; yeni SBOM hedef grubu 19 sentetik vaka içerir.
- Depo lint, hedef format, hedef mypy ve derleme kontrolleri geçti.
- Gerçek repository manifesti proje `0.1.0` ve iki doğrudan bağımlılık için
  deterministik CycloneDX 1.5 JSON üretti.
- Üretilen çıktı resmî CycloneDX 1.5 JSON şemasına karşı doğrulandı.
- Depodaki artifact yeniden üretilen çıktı ile byte düzeyinde eşleşti.
- Yerel secret taraması `CLEAN` sonucu verdi.
- Tam depo format kontrolünde değişiklik dışındaki dört eski dosya; tam mypy
  kontrolünde yedi eski dosyadaki 27 hata sürmektedir. Hedefteki dokuz Python dosyası
  hedef format ve mypy kontrolünden geçmiştir.

## Güvenlik ve Veri Gizliliği

- Üretici manifesti salt okunur işler ve ağ çağrısı yapmaz.
- SBOM ve güvenli hata çıktıları secret, yerel yol, kullanıcı bilgisi veya ham
  parser/işletim sistemi hatası içermez.
- Eksik/dinamik sürüm, sabitlenmemiş/URL tabanlı ve yinelenen bağımlılıklar
  başarısız olur; eksik envanter temiz sonuç sayılmaz.

## Sınırlar ve Kalan Risk

- Bu kayıt yerel teknik doğrulamadır; banka onayı veya mevzuat uyumluluğu sonucu değildir.
- SBOM yalnız beyan edilmiş doğrudan bağımlılıkları kapsar; transitive paket,
  artifact hash'i, lisans ve zafiyet sonucu içermez.
- CI/CD zorlaması, harici SBOM/dependency scanner ürünü ve istisna/onay politikası
  `ComplianceReviewRequired` durumundadır.
- Güvenli pasifleştirme: üretici state veya migration oluşturmaz; komut ve sürüm
  artifact'ı kaldırılabilir, kaynak manifest değişmeden kalır.
