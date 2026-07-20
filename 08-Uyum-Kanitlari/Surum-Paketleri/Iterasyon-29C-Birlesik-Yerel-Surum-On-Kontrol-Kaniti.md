---
type: technical-evidence
status: TechnicallyVerified
control_ids:
  - BFR-SDLC-001
  - BFR-SDLC-002
  - BFR-SDLC-003
  - BFR-SDLC-004
  - BFR-SDLC-005
  - NFR-CMP-002
  - NFR-CMP-005
version: ITERATION_29C
date: 2026-07-20
producer_role: Codex
---

# İterasyon 29C Birleşik Yerel Sürüm Ön Kontrol Kanıtı

## Kapsam

- Politika: `29C-v1`
- Komut: `python3 -m veri_kalitesi.secure_sdlc.preflight`
- Kontroller: `SECRET_SCAN`, `SBOM`, `SAST`, `DEPENDENCY_VULNERABILITY`,
  `PENTEST`, `EVIDENCE_MANIFEST`

## Doğrulanan Teknik Davranış

- Altı mevcut kontrol sabit sırada ve fail-closed çalıştırılır.
- SAST, bağımlılık zafiyeti ve pentest raporları zorunlu, sürümlü JSON paketten
  exact-field allowlist ile alınır; ek/eksik alan ve tamamlanmamış rapor reddedilir.
- Secret veya kritik güvenlik bulgusu ile SBOM/manifest drift'i `BLOCKED`; girdi
  hatası `VALIDATION_ERROR`; tamamlanamayan kontrol `TECHNICAL_ERROR` olur.
- Başarılı sonuç yalnız proje sürümü ile kontrol kimliği, politika ve kanıt
  SHA-256 özetini taşır. Bulgu konumu, advisory, pentest UUID veya ham rapor
  içeriği sonuçta çoğaltılmaz.
- Alt kontrollerin mevcut teknik hata ve güvenlik blokaj kararları değiştirilmez.

## Rapor Paketi Sözleşmesi

```json
{
  "schema_version": 1,
  "sast": {
    "scanner_id": "synthetic-sast",
    "scanner_version": "1.2.3",
    "status": "COMPLETED",
    "findings": []
  },
  "dependency_vulnerability": {
    "scanner_id": "synthetic-dependency-scanner",
    "scanner_version": "1.2.3",
    "advisory_source": "synthetic-advisories",
    "advisory_source_version": "2026.07.20",
    "status": "COMPLETED",
    "findings": []
  },
  "pentest": {
    "assessment_reference": "10000000-0000-4000-8000-000000000001",
    "status": "COMPLETED",
    "findings": []
  }
}
```

Örnek yalnız sözleşme gösterimidir; temiz gerçek tarama veya banka onayı değildir.

## Çalıştırılan Kontroller

```bash
pytest -q 06-Testler/01-Birim/test_secure_sdlc_preflight.py
pytest -q
ruff check .
ruff format --check 03-Backend/src/veri_kalitesi/secure_sdlc/preflight.py 03-Backend/src/veri_kalitesi/secure_sdlc/sbom.py 03-Backend/src/veri_kalitesi/secure_sdlc/models.py 03-Backend/src/veri_kalitesi/secure_sdlc/errors.py 06-Testler/01-Birim/test_secure_sdlc_preflight.py
mypy 03-Backend/src/veri_kalitesi/secure_sdlc/preflight.py 03-Backend/src/veri_kalitesi/secure_sdlc/sbom.py 03-Backend/src/veri_kalitesi/secure_sdlc/models.py 03-Backend/src/veri_kalitesi/secure_sdlc/errors.py 06-Testler/01-Birim/test_secure_sdlc_preflight.py
python3 -m compileall -q 03-Backend/src 06-Testler
PYTHONPATH=03-Backend/src python3 -m veri_kalitesi.secure_sdlc .
cmp -s <(PYTHONPATH=03-Backend/src python3 -m veri_kalitesi.secure_sdlc.sbom pyproject.toml) 08-Uyum-Kanitlari/Surum-Paketleri/Iterasyon-28B-SBOM.cdx.json
PYTHONPATH=03-Backend/src python3 -m veri_kalitesi.secure_sdlc.evidence_gate 08-Uyum-Kanitlari/Surum-Paketleri/Iterasyon-29A-Teknik-Kanit-Katalogu.json 08-Uyum-Kanitlari/Surum-Paketleri/Iterasyon-29A-Teknik-Kanit-Manifesti.json .
```

Hedefte 20, güvenli SDLC grubunda 204 ve tam regresyonda 702 test geçti. Ruff
lint, hedef format/mypy ve derleme kontrolleri başarılıdır. Yerel secret taraması
341 dosyada sıfır bulguyla `CLEAN`; SBOM byte karşılaştırması ve 29B manifest
kontrolü `MATCH` tamamlandı. Tam depo formatında dört eski dosya ve tam mypy'de
yedi dosyada 27 eski hata değişmemiştir.

## Güvenlik, Sınırlar ve Geri Alma

Rapor paketi gerçek müşteri/banka verisi, secret, ham scanner mesajı veya serbest
pentest açıklaması kabul etmez. Bu teknik sözleşme gerçek scanner/pentest çalışması,
CI/CD zorlaması, imza/WORM, risk kabulü, BDDK/KVKK uyumu veya banka onayı değildir.
Güvenli pasifleştirme preflight komutunu release sürecine bağlamamaktır; geri alma
`preflight.py`, ilgili model/hata/export, SBOM serileştirme ve testleri tek commit
üzerinden kaldırmaktır. Altı mevcut kontrol bağımsız çalışmaya devam eder.
