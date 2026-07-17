---
control_ids:
  - BFR-EXT-001
  - BFR-EXT-002
  - BFR-EXT-003
requirement_ids:
  - FR-087
  - UC-013
  - RULE-011
  - NFR-REL-001
  - NFR-REL-005
  - NFR-REL-006
  - NFR-REL-007
status: TechnicallyVerified
version: 8127e9c
executed_at: 2026-07-17
---

# Iterasyon 23C ServiceNow Kalici Retry Kuyrugu Kaniti

## Degisiklik

- Iterasyon: 23C - ServiceNow kalici retry kuyrugu, claim ve dead-letter
- Commit/Artifact: `8127e9c` (`origin/main`)
- Bilesen: `veri_kalitesi.servicenow`, `veri_kalitesi.audit`, `veri_kalitesi.identity`
- Kontrol/Gereksinim: FR-087, UC-013, RULE-011, NFR-REL-001/005/006/007 ve BFR-EXT-001/002/003 alt kapsami

## Dogrulama

- Komut: `PYTHONPATH=03-Backend/src python3 -m pytest -q`
- Ortam: Python 3.10.12, yerel prototip, bellek ici SQLite, fake ServiceNow adaptoru ve enjekte edilebilir saat
- Sentetik veri seti: Senkron retry tukenmesi, replay, cift claim, gecici/kalici/kimlik hatasi, due-time, dead-letter, requeue, yetkisiz worker ve audit-stage arizasi
- Beklenen: Tukenmis gecici istek tek kalici veri-minimum job uretir; tek worker claim eder; basari atomik tamamlar; tukenme silinmeden dead-letter olur ve auditli yeniden islenebilir.
- Gerceklesen: 417 test gecti; ServiceNow hedef grubu 37 testle gecti ve 11 yeni vaka eklendi.
- Sonuc: PASS

Ek kontroller:

- `ruff check 03-Backend/src 06-Testler`: PASS
- ServiceNow yuzeyinde `ruff format --check ...`: PASS
- `python3 -m compileall -q 03-Backend/src 06-Testler`: PASS
- ServiceNow paketi ve testinde `mypy --follow-imports=skip ...`: PASS
- Tam depo format kontrolu, degisiklik disindaki dort eski dosyanin bicim farki nedeniyle PASS degildir.
- Tam mypy kontrolu, degisiklik disindaki dokuz dosyada 29 mevcut hata nedeniyle PASS degildir.

## Guvenlik

- Guven siniri: Worker ve dead-letter requeue yalniz guvenilir, gecerli, ayricaliksiz SERVICE context'iyle calisir; user ve privileged service claim oncesi reddedilir.
- Veri minimizasyonu: Job yalniz ozetlenmis istemci anahtari ve sabit allowlist request alanlarini tutar; issue metni, assignee, scope, ham hata, SQL ve secret saklamaz.
- Teknik hata ayrimi: Gecici hata yeniden planlanir; kimlik/kalici/bilinmeyen hata kalite sonucu sayilmaz ve dogrudan dead-letter olur.
- Atomiklik: Enqueue, yeniden planlama, dead-letter, requeue ve basarili link tamamlama redakte audit outbox ile ayni SQLite transaction'indadir.
- Idempotency: Ayni issue/anahtar/payload tek job uretir; audit hatasi sonrasi harici basari ayni adaptor anahtariyla tekrarlandiginda cift ticket olusmaz.
- Claim: Due-time sirali kosullu guncelleme ayni SQLite deposunda tek worker sahipligi saglar; dagitik lease/heartbeat iddiasi yoktur.
- Maker-checker etkisi: Teknik teslimatin yeniden islenmesi kritik konfigrasyon onayi degildir; banka rol ve operasyon onaylari `ComplianceReviewRequired` kalir.
- Geri alma: Worker durdurularak yeni claim engellenebilir; pending/dead-letter kayitlari silinmez. Retry politikasi tek denemeye indirilebilir.
- Kalan risk: Gercek broker, coklu surec lease/heartbeat recovery, kuyruk kapasitesi/saklama, operasyon alarmi, circuit breaker, gercek ag/TLS/credential ve `OPEN-BNK-009` kapsam disidir.

## Onaylar

- Teknik dogrulayan: Codex teknik uygulama ajani
- Bilgi guvenligi: ComplianceReviewRequired
- Veri yonetisimi: ComplianceReviewRequired
- Ic kontrol: ComplianceReviewRequired
- Hukuk/uyum: ComplianceReviewRequired

Bu kanit teknik uygulama sonucudur; BDDK/KVKK uyumu veya banka onayi anlamina gelmez.
