---
control_ids:
  - BFR-IAM-001
  - BFR-IAM-002
  - BFR-DATA-003
  - CTRL-KVKK-SEC-001
requirement_ids:
  - FR-065
  - FR-070
  - UC-013
  - AC-017
  - NFR-REL-006
  - NFR-SEC-001
  - NFR-SEC-005
  - NFR-SEC-008
status: TechnicallyVerified
version: iteration-22c-local
executed_at: 2026-07-17
---

# Iterasyon 22C Guvenilir Issue Yeniden Atama Kaniti

## Degisiklik

- Iterasyon: 22C - guvenilir kullanici diziniyle issue yeniden atama, oncelik, gecmis, audit ve sistem ici bildirim
- Commit/Artifact: Git deposu bulunmadigi icin commit yok; yerel calisma agaci
- Bilesen: `veri_kalitesi.issues`, `veri_kalitesi.notifications`, `veri_kalitesi.audit`, `veri_kalitesi.identity`
- Kontrol/Gereksinim: FR-065, FR-070, UC-013, AC-017, NFR-REL-006, NFR-SEC-001/005/008 ve BFR-IAM-001/002, BFR-DATA-003 alt kapsami

## Dogrulama

- Komut: `PYTHONPATH=03-Backend/src pytest -q`
- Ortam: Python 3.10.12, yerel prototip, bellek ici SQLite ve sentetik UUID referanslari
- Sentetik veri seti: Yetkili Data Steward, aktif/pasif ve kapsam ici/disi atanan profilleri, servis/ayricalikli/rolesiz/scope disi context, dizin/audit/bildirim arizalari
- Beklenen: Yalniz yetkili ve issue kapsamindaki Data Steward guvenilir dizindeki aktif kapsam ici kullaniciya atama yapar; durum `ASSIGNED`, gecmis/audit ve yeni atanana sistem ici bildirim olusur.
- Gerceklesen: 318 test gecti. Issue hedef grubu 36 testle gecti; 12 yeni test eklendi.
- Sonuc: PASS

Ek kontroller:

- `ruff check 03-Backend/src 06-Testler`: PASS
- Degisen Python dosyalarinda `ruff format --check ...`: PASS
- `python3 -m compileall -q 03-Backend/src 06-Testler`: PASS
- Hassas anahtar sozcuk taramasi yalniz iki sentetik negatif test girdisini buldu; bunlar hata redaksiyonunu dogrular ve kalici ciktida yer almaz.
- Tam depo format kontrolu, bu iterasyonda degismeyen dort eski dosyanin mevcut format farklari nedeniyle PASS degildir.

## Guvenlik

- Guven siniri: Atama guvenilir, gecerli, normal kullanici `ActorContext` ve `DATA_STEWARD`/`DATA_GOVERNANCE_SPECIALIST` rolune dayanir. Serbest actor, rol veya scope yetki kaniti degildir.
- Atanan dogrulamasi: Hedef kullanicinin kimligi, aktifligi ve dataset/source kapsami enjekte edilen guvenilir dizin profilinden gelir; pasif, bulunamayan ve kapsam disi kullanici reddedilir.
- Yetki: Eksik context, servis hesabi, ayricalikli kullanici, rolesiz kullanici ve issue scope'u disindaki kullanici repository yazimindan once fail-closed reddedilir.
- Atomiklik: Atanan, oncelik, durum, eski/yeni degerli issue gecmisi ve redakte audit outbox ayni SQLite transaction'indadir; stage arizasi tum atamayi rollback eder.
- Audit ve veri minimizasyonu: Audit allowlist'i yalniz durum ve onceligi tutar. Atanan kimligi, scope ve session acik degeri audit ozetine girmez; bildirim sabit veri-minimum sablon kullanir.
- Bildirim: Yerel atama commitinden sonra guvenilir servis context'iyle `ISSUE_ASSIGNED` olayi uretilir ve alici degismez atama gecmisi kaydindan cozulur. Bildirim arizasinda yerel atama korunur ve hata siniflandirilir.
- Teknik hata ayrimi: Dizin veya depo arizasi redakte teknik hata; pasif/kapsam disi kullanici domain atama hatasidir.
- Maker-checker etkisi: Atama bir kritik konfigurasyon aktivasyonu veya onay karari degildir; bu nedenle maker-checker eklenmedi. Rol/scope ve audit kontrolleri zorunludur.
- Geri alma: Manuel atama cagri yolu pasiflestirilip onceki issue servis surumune donulebilir. Ek gecmis kolonlari nullable ve geriye uyumludur; kaynak sisteme yazim yoktur.
- Kalan risk: Gercek LDAP/sahiplik dizini, cozum/dogrulama/kapatma, bildirim retry/DLQ, saklama-imha, ServiceNow ve HTTP/UI kapsam disidir.

## Onaylar

- Teknik dogrulayan: Codex teknik uygulama ajani
- Bilgi guvenligi: ComplianceReviewRequired
- Veri yonetisimi: ComplianceReviewRequired
- Ic kontrol: ComplianceReviewRequired
- Hukuk/uyum: ComplianceReviewRequired

Bu kanit teknik uygulama sonucudur; BDDK/KVKK uyumu veya banka onayi anlamina gelmez.
