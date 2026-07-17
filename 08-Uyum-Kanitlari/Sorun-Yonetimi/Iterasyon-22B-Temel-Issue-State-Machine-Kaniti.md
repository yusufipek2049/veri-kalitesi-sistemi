---
control_ids:
  - BFR-IAM-001
  - BFR-IAM-002
  - BFR-DATA-003
  - CTRL-KVKK-SEC-001
requirement_ids:
  - FR-064
  - FR-065
  - FR-066
  - FR-070
  - UC-011
  - UC-013
  - RULE-006
  - RULE-011
  - AC-015
  - AC-016
  - NFR-REL-005
  - NFR-REL-006
  - NFR-SEC-001
  - NFR-SEC-005
  - NFR-SEC-008
status: TechnicallyVerified
version: iteration-22b-local
executed_at: 2026-07-17
---

# Iterasyon 22B Temel Issue State Machine Kaniti

## Degisiklik

- Iterasyon: 22B - otomatik sahipli issue, deduplication ve `ASSIGNED -> INVESTIGATING` gecisi
- Commit/Artifact: Git deposu bulunmadigi icin commit yok; yerel calisma agaci
- Bilesen: `veri_kalitesi.issues`, `veri_kalitesi.notifications`, `veri_kalitesi.audit`, `veri_kalitesi.identity`
- Kontrol/Gereksinim: FR-064, FR-065 ilk atama, FR-066 temel gecis, FR-070 gecmis; UC-011/013, RULE-006/011, AC-015/016, NFR-REL-005/006, NFR-SEC-001/005/008 ve BFR-IAM-001/002, BFR-DATA-003 alt kapsami

## Dogrulama

- Komut: `pytest -q`
- Ortam: Python 3.10.12, yerel prototip, bellek ici SQLite ve sentetik UUID referanslari
- Sentetik veri seti: Kalite/teknik trigger, 100 tekrar, payload cakismasi, assignment resolver/depo/audit/bildirim arizasi, farkli assignee, eksik scope, servis ve ayricalikli context
- Beklenen: Guvenilir servis sahipli issue olusturur; 100 tekrar tek issue/bildirimde birlesir; issue/gecmis/audit atomiktir; bildirim hatasinda issue korunur; yalniz assignee kapsam icinde incelemeyi baslatir.
- Gerceklesen: 306 test gecti. Issue hedef grubu 24 testle gecti; 24 yeni test eklendi.
- Sonuc: PASS

Ek kontroller:

- `ruff check 03-Backend/src 06-Testler`: PASS
- Degisen Python dosyalarinda `ruff format --check ...`: PASS
- `python3 -m compileall -q 03-Backend/src`: PASS
- Tam depo format kontrolu, bu iterasyonda degismeyen dort eski dosyanin mevcut format farklari nedeniyle PASS degildir.

## Guvenlik

- Guven siniri: Issue uretimi guvenilir standart servis context'i, inceleme gecisi guvenilir standart kullanici context'i gerektirir. Serbest actor/assignee/scope yetki kaniti degildir.
- Atama: Assignee ve oncelik yalniz enjekte edilen guvenilir assignment resolver'dan gelir; UUID ve enum disi degerler reddedilir.
- Yetki: Yalniz kayitli assignee ve ActorContext'teki ilgili dataset/source scope'u incelemeyi baslatabilir. Baska kullanici, eksik scope, servis ve ayricalikli context reddedilir.
- Veri minimizasyonu: Issue serbest aciklama, kok neden, kayit ornegi veya hata detayi saklamaz. Dedup anahtari SHA-256 ozetiyle saklanir.
- Audit: Trigger islemi ve durum gecisi merkezi redactor ile hazirlanir. Assignee, scope, dedup anahtari ve acik session kimligi audit ozetinden cikarilir.
- Atomiklik: Issue/gecmis ve redakte audit outbox ayni SQLite transaction'indadir; stage arizasi rollback olur. Gecmis monoton sequence ile degismez siralanir; SQLite enum ve foreign key kisitlari etkindir.
- Idempotency: Dedup ozetinden deterministik issue UUID'si uretilir; ayni payload sayac/son gorulme zamanini gunceller, farkli payload cakisir ve mevcut durum geriye alinmaz.
- Bildirim: 22A servisi issue commitinden sonra cagrilir. Teknik veya politika hatasinda issue korunur ve hata issue kimligiyle siniflandirilir; retry/DLQ sonraki dilimdedir.
- Maker-checker etkisi: Bu dilimde serbest politika/konfigurasyon degisikligi yoktur. Assignment politikasi yonetim yuzeyi eklendiginde kritik degisiklik degerlendirmesi gerekir.
- Geri alma: `issues` paketi ve yeni SQLite tablolari bagimsizdir; trigger tuketimi devre disi birakilip onceki surume donulebilir. Kaynak sisteme yazim yoktur.
- Kalan risk: Gercek assignment/fallback kuyruk adaptoru, yeniden atama, cozum/dogrulama/kapatma, yorum/ek, bildirim retry/DLQ, saklama-imha, ServiceNow ve HTTP/UI kapsam disidir.

## Onaylar

- Teknik dogrulayan: Codex teknik uygulama ajani
- Bilgi guvenligi: ComplianceReviewRequired
- Veri yonetisimi: ComplianceReviewRequired
- Ic kontrol: ComplianceReviewRequired
- Hukuk/uyum: ComplianceReviewRequired

Bu kanit teknik uygulama sonucudur; BDDK/KVKK uyumu veya banka onayi anlamina gelmez.
