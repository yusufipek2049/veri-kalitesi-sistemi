---
type: technical-evidence
status: TechnicallyVerified
control_ids:
  - BFR-SDLC-001
  - BFR-SDLC-002
  - BFR-SDLC-003
  - NFR-SEC-012
version: ITERATION_28C
date: 2026-07-20
producer_role: Codex
---

# İterasyon 28C Yerel SAST Bulgu ve Sürüm Kapısı Kanıtı

## Kapsam

- İterasyon: 28C - Yerel SAST bulgu ve sürüm kapısı sözleşmesi
- Commit/Artifact: `ITERATION_28C` (`origin/main`)
- Politika: `28C-v1`
- Test: `06-Testler/01-Birim/test_secure_sdlc_sast.py`

## Çalıştırılan Kontroller

```bash
python3 -m pytest -q
python3 -m ruff check .
python3 -m ruff format --check 03-Backend/src/veri_kalitesi/secure_sdlc 06-Testler/01-Birim/test_secure_sdlc.py 06-Testler/01-Birim/test_secure_sdlc_sbom.py 06-Testler/01-Birim/test_secure_sdlc_sast.py
python3 -m mypy 03-Backend/src/veri_kalitesi/secure_sdlc 06-Testler/01-Birim/test_secure_sdlc.py 06-Testler/01-Birim/test_secure_sdlc_sbom.py 06-Testler/01-Birim/test_secure_sdlc_sast.py
python3 -m compileall -q 03-Backend/src 06-Testler
PYTHONPATH=03-Backend/src python3 -m veri_kalitesi.secure_sdlc .
```

## Sonuç

- 26 yeni sentetik vakayla toplam 556 birim testi geçti.
- Depo lint, hedef format, hedef mypy ve derleme kontrolleri geçti.
- Allowlist dışı scanner mesajı/snippet/source line/secret alanları reddedildi.
- Mutlak, Windows, traversal, backslash ve normalize olmayan yollar reddedildi.
- Scanner kimliği/sürümü uyuşmazlığı ve yinelenen bulgu temiz sonuç sayılamadı.
- `TECHNICAL_ERROR`, kritik bulgudan ayrı teknik hata olarak sürüm kanıtını engelledi.
- Her `CRITICAL` bulgu fail-closed bloklandı; kritik olmayan bulgular kanıtta yalnız
  sayım ve deterministik digest ile temsil edildi.
- Repository secret taraması 319 metin dosyasında `CLEAN` sonucu verdi.
- Tam depo format kontrolündeki dört eski dosya ve tam mypy kontrolündeki yedi
  dosyada 27 eski hata değişmedi; yeni hedef 11 Python dosyası mypy'dan geçti.

## Güvenlik ve Veri Gizliliği

- Tüm fixture'lar sentetiktir; gerçek source bulgusu, secret, kullanıcı veya banka
  verisi yoktur.
- SAST payload'ı güvenilmez girdidir; yalnız yedi allowlist alanı kabul edilir.
- Sürüm kanıtı bulgu yolu, rule code, source line, snippet veya scanner mesajı taşımaz.
- Actor/RBAC yüzeyi bu yerel build-time sözleşmede bulunmaz; bu durum banka onaylı
  `NotApplicable` kararı değildir. Release onayı ve görevler ayrılığı kapsam dışıdır.

## Sınırlar ve Kalan Risk

- Gerçek SAST scanner çalıştırılmamış ve repository için SAST temizliği iddia edilmemiştir.
- CI/CD zorlaması, scanner ürünü, kritik olmayan eşikler, istisna/risk kabulü,
  release maker-checker, DAST ve pentest açık kalır.
- Teknik kontrol banka onayı veya mevzuat uyumluluğu sonucu değildir;
  `ComplianceReviewRequired` durumu sürer.
- Güvenli pasifleştirme: sözleşme kalıcı state veya migration oluşturmaz;
  `secure_sdlc/sast.py`, exportları ve hedef testleri geri alınabilir. 28A/28B
  secret/SBOM davranışları etkilenmez.
