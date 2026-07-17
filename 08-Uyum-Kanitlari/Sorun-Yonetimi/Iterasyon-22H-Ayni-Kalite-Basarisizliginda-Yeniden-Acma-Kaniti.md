---
control_ids:
  - BFR-IAM-001
  - BFR-IAM-002
  - BFR-DATA-003
requirement_ids:
  - FR-064
  - FR-069
  - FR-070
  - UC-014
  - RULE-003
  - RULE-011
  - RULE-013
  - AC-016
  - AC-018
  - NFR-REL-005
  - NFR-REL-006
status: TechnicallyVerified
version: 990faf5
executed_at: 2026-07-17
---

# Iterasyon 22H Ayni Kalite Basarisizliginda Yeniden Acma Kaniti

## Degisiklik

- Iterasyon: 22H - ayni kalite basarisizligiyla `CLOSED -> WAITING_FOR_RESOLUTION` gecisi
- Commit/Artifact: `990faf5` (`origin/main`)
- Bilesen: `veri_kalitesi.issues`, `veri_kalitesi.audit`, `veri_kalitesi.identity`
- Kontrol/Gereksinim: FR-064, FR-069, FR-070, UC-014, RULE-003, RULE-011, RULE-013, AC-016, AC-018, NFR-REL-005/006 ve BFR-IAM-001/002, BFR-DATA-003 alt kapsami

## Dogrulama

- Komut: `pytest -q`
- Ortam: Python 3.10.12, yerel prototip, bellek ici SQLite ve sentetik UUID referanslari
- Sentetik veri seti: Ayni kalite olayi, kapanistan eski replay, teknik olay, farkli payload, yuz tekrar ve audit-stage arizasi
- Beklenen: Yalniz ayni deduplication anahtari/payload ile kapanis anindan eski olmayan guvenilir kalite olayi mevcut kapali issue'yu yeni kayit olusturmadan yeniden acar.
- Gerceklesen: 371 test gecti. Issue hedef grubu 89 testle gecti; 6 yeni test vakasi eklendi.
- Sonuc: PASS

Ek kontroller:

- `ruff check 03-Backend/src 06-Testler`: PASS
- Degisen uc dosyada `ruff format --check ...`: PASS
- `python3 -m compileall -q 03-Backend/src`: PASS
- Tam depo format kontrolu, degisiklik disindaki dort eski dosyanin bicim farki nedeniyle PASS degildir.
- Tam `mypy` kontrolu, degisiklik disindaki `audit/repository.py`, `identity/sessions.py` ve `identity/ldap.py` dosyalarinda ayni 13 mevcut hata nedeniyle PASS degildir.

## Guvenlik

- Guven siniri: Yeniden acma yalniz mevcut `ISSUE_PRODUCER` guvenilir servis context'i ve kalici deduplication/payload ozeti uzerinden calisir.
- Olay zamani: Kaynak olay zamani kapanis guncelleme anindan eskiyse sorun kapali kalir; eski replay kapanis zaman sinirini ileri tasimaz.
- Teknik hata ayrimi: Teknik olay kalite basarisizligi sayilmaz ve kapali issue'yu bu akisla yeniden acmaz.
- Veri minimizasyonu: Audit yalniz eski/yeni durum ile olay/tetik turunu tutar; scope ve deduplication degeri audit ozetine girmez.
- Atomiklik: Durum, occurrence sayaci, gecmis ve redakte audit outbox ayni SQLite transaction'indadir; audit-stage arizasinda tum yazimlar rollback olur.
- Idempotency: Yuz ayni tekrar tek issue ve tek yeniden acma gecmisi uretir; farkli payload kontrollu cakisma olarak reddedilir.
- Maker-checker etkisi: Otomatik guvenilir olay tuketimi yeni bir insan onayi veya kritik konfigrasyon aktivasyonu degildir; banka onayli rol/politika kararlari `ComplianceReviewRequired` kalir.
- Geri alma: Yeniden acma kosulu pasiflestirilerek onceki tekrar davranisina donulebilir; append-only gecmis silinmez ve kaynak sisteme yazim yapilmaz.
- Kalan risk: Yeni/farkli kalite basarisizliginin mevcut issue ile iliskisi, gercek adaptorler, ServiceNow, saklama-imha ve HTTP/UI kapsam disidir.

## Onaylar

- Teknik dogrulayan: Codex teknik uygulama ajani
- Bilgi guvenligi: ComplianceReviewRequired
- Veri yonetisimi: ComplianceReviewRequired
- Ic kontrol: ComplianceReviewRequired
- Hukuk/uyum: ComplianceReviewRequired

Bu kanit teknik uygulama sonucudur; BDDK/KVKK uyumu veya banka onayi anlamina gelmez.
