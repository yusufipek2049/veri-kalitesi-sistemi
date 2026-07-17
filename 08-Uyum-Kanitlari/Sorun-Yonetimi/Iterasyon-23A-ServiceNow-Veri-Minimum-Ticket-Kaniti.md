---
control_ids:
  - BFR-EXT-001
  - BFR-EXT-002
  - BFR-EXT-003
requirement_ids:
  - FR-071
  - FR-084
  - FR-087
  - AC-019
  - RULE-011
  - NFR-REL-005
  - NFR-REL-006
status: TechnicallyVerified
version: 6b53c53
executed_at: 2026-07-17
---

# Iterasyon 23A ServiceNow Veri-Minimum Ticket Kaniti

## Degisiklik

- Iterasyon: 23A - ServiceNow veri-minimum adaptor sozlesmesi ve idempotent ticket olusturma
- Commit/Artifact: `6b53c53` (`origin/main`)
- Bilesen: `veri_kalitesi.servicenow`, `veri_kalitesi.audit`, `veri_kalitesi.identity`
- Kontrol/Gereksinim: FR-071, FR-084, FR-087, AC-019, RULE-011, NFR-REL-005/006 ve BFR-EXT-001/002/003 alt kapsami

## Dogrulama

- Komut: `PYTHONPATH=03-Backend/src python3 -m pytest -q`
- Ortam: Python 3.10.12, yerel prototip, bellek ici SQLite, fake ServiceNow adaptoru ve sentetik UUID referanslari
- Sentetik veri seti: Guvenilir/guvenilmez aktorler, politika disi issue, allowlist ihlali, 100 replay, payload cakismasi, adaptor/audit arizalari
- Beklenen: Yalniz guvenilir standart servis context'i ve veri-minimum projeksiyon ticket uretir; ayni issue/idempotency tekrarinda tek ticket kalir.
- Gerceklesen: 398 test gecti; 18 yeni ServiceNow test vakasi eklendi.
- Sonuc: PASS

Ek kontroller:

- `ruff check 03-Backend/src 06-Testler`: PASS
- Degisen alti dosyada `ruff format --check ...`: PASS
- `python3 -m compileall -q 03-Backend/src 06-Testler`: PASS
- ServiceNow paketi ve testinde `mypy --follow-imports=skip ...`: PASS
- Tam depo format kontrolu, degisiklik disindaki dort eski dosyanin bicim farki nedeniyle PASS degildir.
- Tam mypy kontrolu, degisiklik disindaki dokuz dosyada 29 mevcut hata nedeniyle PASS degildir.

## Guvenlik

- Guven siniri: Ticket yalniz guvenilir, gecerli, ayricaliksiz `SERVICE` context'i ve `SERVICENOW_TICKET_PRODUCER` roluyle olusturulur.
- Veri minimizasyonu: Dis istek sabit issue referansi, olay turu, oncelik, opak detay referansi, correlation ve ozetlenmis istemci anahtariyla sinirlidir; serbest metin ve ham kayit alani yoktur.
- Fail-closed: Yetki, export politikasi, projeksiyon ve audit redaksiyon politikasi dis cagri oncesi dogrulanir.
- Teknik hata ayrimi: Adaptor kimlik dogrulama, hiz siniri, gecici ve kalici hata siniflari kalite sonucuna donusturulmez; ham hata govdesi saklanmaz.
- Atomiklik: Yerel link, append-only gecmis ve audit outbox ayni SQLite transaction'indadir; audit-stage arizasinda yerel yazim rollback olur.
- Idempotency: 100 tekrar tek ticket/link/gecmis/audit uretir; ayni anahtarin farkli payload ile kullanimi cakismadir.
- Maker-checker etkisi: Otomatik ticket olusturma kritik konfigrasyon onayi degildir; servis hesabi ve banka alan politikasi `ComplianceReviewRequired` kalir.
- Geri alma: Adaptor baglantisi pasiflestirilerek yeni ticket olusturma durdurulabilir; mevcut append-only link/gecmis silinmez ve kaynak veri sistemlerine yazim yapilmaz.
- Kalan risk: Gercek endpoint/TLS/credential, retry/backoff, durum senkronizasyonu, HTTP/UI ve `OPEN-BNK-009` kapsam disidir.

## Onaylar

- Teknik dogrulayan: Codex teknik uygulama ajani
- Bilgi guvenligi: ComplianceReviewRequired
- Veri yonetisimi: ComplianceReviewRequired
- Ic kontrol: ComplianceReviewRequired
- Hukuk/uyum: ComplianceReviewRequired

Bu kanit teknik uygulama sonucudur; BDDK/KVKK uyumu veya banka onayi anlamina gelmez.
