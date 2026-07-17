---
control_ids:
  - BFR-EXT-001
  - BFR-EXT-002
  - BFR-EXT-003
requirement_ids:
  - FR-087
  - UC-013
  - AC-019
  - NFR-REL-001
  - NFR-REL-005
  - NFR-REL-006
status: TechnicallyVerified
version: 7e24946
executed_at: 2026-07-17
---

# Iterasyon 23B ServiceNow Retry ve Backoff Kaniti

## Degisiklik

- Iterasyon: 23B - ServiceNow siniflandirilmis retry ve kontrollu backoff
- Commit/Artifact: `7e24946` (`origin/main`)
- Bilesen: `veri_kalitesi.servicenow`
- Kontrol/Gereksinim: FR-087, UC-013, AC-019, NFR-REL-001/005/006 ve BFR-EXT-001/002/003 alt kapsami

## Dogrulama

- Komut: `PYTHONPATH=03-Backend/src python3 -m pytest -q`
- Ortam: Python 3.10.12, yerel prototip, bellek ici SQLite, fake ServiceNow adaptoru ve enjekte edilebilir sleeper
- Sentetik veri seti: 401/kalici/bilinmeyen hata, gecici hata dizisi, 429 ve Retry-After, eksik Retry-After, retry tukenmesi, gecersiz politika ve replay
- Beklenen: Yalniz gecici/429 hata en fazla uc toplam denemeyle tekrar edilir; 401 tekrar edilmez; tum denemeler ayni idempotency kimligini kullanir.
- Gerceklesen: 406 test gecti; ServiceNow hedef grubu 26 testle gecti ve 8 yeni vaka eklendi.
- Sonuc: PASS

Ek kontroller:

- `ruff check 03-Backend/src 06-Testler`: PASS
- ServiceNow yuzeyinde `ruff format --check ...`: PASS
- `python3 -m compileall -q 03-Backend/src 06-Testler`: PASS
- ServiceNow paketi ve testinde `mypy --follow-imports=skip ...`: PASS
- Tam depo format kontrolu, degisiklik disindaki dort eski dosyanin bicim farki nedeniyle PASS degildir.
- Tam mypy kontrolu, degisiklik disindaki dokuz dosyada 29 mevcut hata nedeniyle PASS degildir.

## Guvenlik

- Guven siniri: 23A'nin guvenilir standart servis context'i ve allowlist export politikasi degistirilmedi.
- Veri minimizasyonu: Retry ayni sabit veri-minimum request'i kullanir; ham adaptor hata mesaji, response govdesi veya credential saklanmaz.
- Teknik hata ayrimi: Yalniz `TEMPORARY` ve gecerli `RATE_LIMIT` tekrar edilir; kimlik, kalici ve bilinmeyen hata kalite sonucuna donusturulmez ve tekrar edilmez.
- Idempotency: Gecici hata sonrasi basari ve replay tek harici ticket, tek yerel link ve tek audit olayi birakir.
- Sinirlilik: Politika toplam denemeyi 1-3 araliginda tutar; gecici hata 1 ve 2 saniyelik ustel gecikme, 429 tam Retry-After kullanir.
- Maker-checker etkisi: Retry teknik teslim davranisidir; kritik konfigrasyon onayi degildir. Banka politika/onaylari `ComplianceReviewRequired` kalir.
- Geri alma: Retry politikasi tek denemeye indirilerek senkron tekrar guvenli bicimde pasiflestirilebilir; mevcut link/gecmis silinmez.
- Kalan risk: Kalici retry kuyrugu/DLQ, circuit breaker, gercek timeout/TLS/credential, durum senkronizasyonu ve `OPEN-BNK-009` kapsam disidir.

## Onaylar

- Teknik dogrulayan: Codex teknik uygulama ajani
- Bilgi guvenligi: ComplianceReviewRequired
- Veri yonetisimi: ComplianceReviewRequired
- Ic kontrol: ComplianceReviewRequired
- Hukuk/uyum: ComplianceReviewRequired

Bu kanit teknik uygulama sonucudur; BDDK/KVKK uyumu veya banka onayi anlamina gelmez.
