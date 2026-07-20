---
control_ids:
  - BFR-IR-001
  - BFR-IR-002
  - BFR-IR-003
  - BFR-IR-004
  - CTRL-KVKK-BREACH-001
requirement_ids:
  - NFR-OBS-001
  - NFR-OBS-003
  - NFR-PRV-001
  - NFR-PRV-002
  - NFR-PRV-005
  - NFR-SEC-001
  - NFR-SEC-005
  - NFR-SEC-008
  - NFR-SEC-011
status: TechnicallyVerified
version: ITERATION_26A
executed_at: 2026-07-20
---

# İterasyon 26A Veri Minimum İhlal Şüphesi Kanıtı

## Değişiklik

- İterasyon: 26A - Veri-minimum güvenlik olayı ve ihlal şüphesi ayrımı
- Commit/Artifact: `ITERATION_26A` (`origin/main`)
- Bileşen: `veri_kalitesi.incident_response`, `veri_kalitesi.identity`, `veri_kalitesi.audit`
- Kontrol/Gereksinim: `BFR-IR-001`–`BFR-IR-004`, `CTRL-KVKK-BREACH-001`, `NFR-OBS-001/003`, `NFR-PRV-001/002/005`, `NFR-SEC-001/005/008/011`

## Doğrulama

- Komut: `python3 -m pytest -q`
- Ortam: Python 3.10, yerel prototip, bellek içi SQLite, sentetik UUID kanıt referansları ve güvenilir fake actor context
- Sentetik kapsam: Ayrı güvenlik olayı/ihlal şüphesi, 72 saat hesabı, veri işleyen kanıtı, farklı checker kararı, scope yükseltme, sahte/servis/ayrıcalıklı context, audit rollback ve teknik depo arızası
- Beklenen: Teknik olay otomatik ihlal olmaz; şüphe ve karar append-only izlenir; dış bildirim gönderilmez; yetkisiz erişim reddedilir; audit veri-minimumdur.
- Gerçekleşen: 482 test geçti; incident response hedef grubu 23 testle geçti.
- Sonuç: PASS

Ek kontroller:

- `python3 -m ruff check .`: PASS
- Incident response yüzeyinde `python3 -m ruff format --check ...`: PASS
- `python3 -m mypy --follow-imports=skip ...`: PASS
- `python3 -m compileall -q 03-Backend/src 06-Testler`: PASS
- Tam depo format kontrolü, değişiklik dışındaki dört eski dosyanın biçim farkı nedeniyle PASS değildir.
- Tam mypy kontrolü, yedi eski dosyada 27 hata nedeniyle PASS değildir.

## Güvenlik ve Gizlilik

- Güven sınırı: Yalnız güvenilir, geçerli, ayrıcalıksız `USER` context'ı ve sürümlü rolde izin verilir; servis ve ayrıcalıklı context reddedilir.
- Scope: SOURCE/DATASET/ENTERPRISE kapsamı güvenilir context üzerinden denetlenir; scope kimliği audit özetine yazılmaz.
- Veri minimizasyonu: Serbest olay/ihlal açıklaması veya kanıt içeriği yoktur. Kodlar, kategori enumları ve UUID kanıt referansları saklanır.
- Audit: Domain kayıtları, zaman çizelgesi ve redakte outbox atomiktir; audit-stage arızasında rollback ölür.
- Maker-checker: Şüpheyi kaydeden kendi bildirim kararını kaydedemez. Banka rol eşlemesi `ComplianceReviewRequired` kalır.
- Dış bildirim: Karar kaydı yapısal olarak `external_notification_dispatched=false` taşır; Kurul/ilgili kişi/SIEM adaptörü yoktur.
- Teknik hata ayrımı: Depo ve audit arızası teknik hata olarak kalır; ihlal veya veri kalitesi başarısızlığına dönüştürülmez.
- Geri alma: Incident response servis çağrıları pasifleştirilebilir; append-only olay, şüphe, karar ve audit geçmişi silinmez.
- Kalan risk: `OPEN-BNK-001/002/004/008/010`, gerçek SIEM/SOC, saklama/imha, hukuk/uyum kararı, tatbikat ve dış bildirim kapsam dışıdır.

## Onaylar

- Teknik doğrulayan: Codex teknik uygulama ajanı
- Bilgi güvenliği: ComplianceReviewRequired
- KVKK/Hukuk/Uyum: ComplianceReviewRequired
- İç kontrol: ComplianceReviewRequired
- SOC/Operasyon: ComplianceReviewRequired

Bu kanıt teknik uygulama sonucudur; BDDK/KVKK uyumu veya banka onayı anlamına gelmez.
