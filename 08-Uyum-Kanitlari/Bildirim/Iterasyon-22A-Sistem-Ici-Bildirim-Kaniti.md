---
control_ids:
  - BFR-IAM-001
  - BFR-IAM-002
  - BFR-DATA-003
  - CTRL-KVKK-SEC-001
requirement_ids:
  - FR-059
  - FR-060
  - FR-063
  - UC-012
  - RULE-006
  - RULE-011
  - AC-010
  - AC-015
  - AC-016
  - NFR-REL-006
status: TechnicallyVerified
version: iteration-22a-local
executed_at: 2026-07-17
---

# Iterasyon 22A Sistem Ici Bildirim Kaniti

## Degisiklik

- Iterasyon: 22A - veri-minimum, idempotent ve okunabilir sistem ici bildirim yasam dongusu
- Commit/Artifact: Git deposu bulunmadigi icin commit yok; yerel calisma agaci
- Bilesen: `veri_kalitesi.notifications`, `veri_kalitesi.audit`, `veri_kalitesi.identity`
- Kontrol/Gereksinim: FR-059/060/063, UC-012, RULE-006/011, AC-010/015/016, NFR-REL-006, BFR-IAM-001/002 ve BFR-DATA-003 alt kapsami

## Dogrulama

- Komut: `pytest -q`
- Ortam: Python 3.10.12, yerel prototip, bellek ici SQLite ve sentetik UUID referanslari
- Sentetik veri seti: Kalite esigi, kritik kural ve teknik hata; tekrar/cakisma; alicisiz olay; resolver/depo/audit arizasi; farkli alici; guvenilmez, expired, servis ve ayricalikli context
- Beklenen: Sabit veri-minimum bildirim dogru guvenilir aliciya bes dakika hedefi icinde yazilir; kalite/teknik olay ayrilir; tekrar tek kaydi gunceller; yalniz alici okuyabilir; audit-stage arizasi kaydi rollback eder.
- Gerceklesen: 282 test gecti. Bildirim hedef grubu 17 testle gecti; 17 yeni test eklendi.
- Sonuc: PASS

Ek kontroller:

- `ruff check 03-Backend/src 06-Testler`: PASS
- Degisen Python dosyalarinda `ruff format --check ...`: PASS
- `python3 -m compileall -q 03-Backend/src`: PASS
- Tam depo format kontrolu, bu iterasyonda degismeyen dort eski dosyanin mevcut format farklari nedeniyle PASS degildir.

## Guvenlik

- Guven siniri: Alici kimligi olay girdisinden alinmaz; enjekte edilen guvenilir sahiplik resolver protokolunden gelir. Uretim guvenilir servis context'i, okuma guvenilir ve gecerli normal kullanici context'i gerektirir.
- Deny-by-default: Baska alici, guvenilmez/expired context, servis hesabi ve ayricalikli context standart bildirim merkezine erisemez.
- Veri minimizasyonu: Baslik ve govde yalniz event-type allowlist'indeki sabit metinlerden uretilir; scope/event/hata payloadi govdeye tasinmaz.
- Deduplication: Anahtar acik saklanmaz; SHA-256 ozeti recipient ile benzersizdir. Ayni payload sayac/son gorulme zamanini gunceller, farkli payload cakisir.
- Audit: Olusturma ve `READ` gecisi merkezi redactor ile hazirlanir. Scope, dedup anahtari ve acik session kimligi audit ozetinden cikarilir.
- Atomiklik: Bildirim veya durum gecisi ile redakte audit outbox olayi ayni SQLite transaction'indadir; stage arizasi rollback olur.
- Sonuc ayrimi: Alici yoklugu yapilandirma/owner problemi; resolver, depo ve audit arizasi redakte teknik hata olarak ayrilir.
- Maker-checker etkisi: Bu dilimde politika veya serbest sablon degistirme yuzeyi yoktur. Ileride sablon/alici politikasi yonetimi kritik degisiklik degerlendirmesi gerektirir.
- Geri alma: `notifications` paketi ve yeni SQLite tablosu bagimsizdir; tetikleyiciler devre disi birakilip onceki surume donulebilir. Kaynak sisteme yazim yoktur.
- Kalan risk: Gercek sahiplik/fallback grup adaptoru, asenkron retry/DLQ, susturma/eskalasyon, sablon yonetimi, saklama-imha, issue ve HTTP/UI kapsam disidir.

## Onaylar

- Teknik dogrulayan: Codex teknik uygulama ajani
- Bilgi guvenligi: ComplianceReviewRequired
- Veri yonetisimi: ComplianceReviewRequired
- Ic kontrol: ComplianceReviewRequired
- Hukuk/uyum: ComplianceReviewRequired

Bu kanit teknik uygulama sonucudur; BDDK/KVKK uyumu veya banka onayi anlamina gelmez.
