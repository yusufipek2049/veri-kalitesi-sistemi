---
control_ids:
  - BFR-IAM-001
  - BFR-IAM-002
  - BFR-IAM-004
  - BFR-IAM-005
  - BFR-IAM-006
  - CTRL-BDDK-IAM-001
requirement_ids:
  - FR-001
  - FR-005
  - UC-001
  - NFR-SEC-005
  - NFR-SEC-009
  - AC-001
status: TechnicallyVerified
version: iteration-20c-local
executed_at: 2026-07-17
---

# Iterasyon 20C Guvenli Oturum Yasam Dongusu Kaniti

## Degisiklik

- Iterasyon: 20C - kalici, iptal edilebilir ve idle-timeout kontrollu kullanici oturumu
- Commit/Artifact: Git deposu bulunmadigi icin commit yok; yerel calisma agaci
- Bilesen: `veri_kalitesi.identity`, `veri_kalitesi.audit`
- Kontrol/Gereksinim: FR-001/005, UC-001, NFR-SEC-005/009, AC-001 ve BFR-IAM-001/002/004/005/006 alt kapsami

## Dogrulama

- Komut: `pytest -q`
- Ortam: Python 3.10.12, yerel prototip, fake LDAP adaptoru ve sentetik kullanici verisi
- Sentetik veri seti: Guvenilir/guvenilmez/expired context, 32 bayt session credential, idle ve mutlak sure ilerletme, cikis, degistirilmis credential, kalici SQLite kaydi, depo ve audit arizasi
- Beklenen: Yalniz guvenilir LDAP context'i oturum acar; credential acik saklanmaz; 30 dakikada idle timeout, mutlak timeout ve cikis oturumu kalici gecersizlestirir; teknik ariza context dondurmez.
- Gerceklesen: 254 test gecti. Kimlik hedef grubu 42 testle gecti; 17 yeni oturum testi eklendi.
- Sonuc: PASS

Ek kontroller:

- `ruff check 03-Backend/src 06-Testler`: PASS
- Degisen alti Python dosyasinda `ruff format --check ...`: PASS
- `python3 -m compileall -q 03-Backend/src`: PASS
- Tam depo format kontrolu, bu iterasyonda degismeyen dort eski dosyanin mevcut format farklari nedeniyle PASS degildir.

## Guvenlik

- Guven siniri: Session servisi serbest actor/rol/scope almaz; yalniz guvenilir ve halen gecerli `ActorContext` kabul eder.
- Credential: Yuksek entropili credential yalniz bir kez `SessionGrant` icinde dondurulur; SQLite ve audit yalniz SHA-256/session digest tasir.
- Deny-by-default: Bilinmeyen, degistirilmis, expired veya revoked credential context uretmez. Depo ya da audit arizasi fail-closed kapanir.
- Zaman: Surumlu politika varsayilan 30 dakika idle timeoutu uygular; daha siki deger desteklenir. Ayrica enjekte edilen mutlak timeout aktiviteyle uzatilmaz.
- Cikis: Ilk cikis kalici `REVOKED`, tekrar cikis idempotenttir; credential daha sonra kullanilamaz.
- Hesap ayrimi: Normal kullanici session servisi servis hesabi ve ayricalikli kullaniciyi reddeder; break-glass/servis oturumu bu dilimde tahmin edilmez.
- Audit: Olusturma, dogrulama, timeout, cikis ve ret olaylari allowlist ozetle kaydedilir; ham credential ve acik session ID audit ozetine girmez.
- Maker-checker etkisi: Bu dilimde politika degistirme yuzeyi yoktur; uretim timeout/es zamanli oturum politika onayi `OPEN-BNK-020` altinda aciktir.
- Geri alma: Session servisi LDAP basarisinda zorunludur. Guvenli pasiflestirme yerine oturumlar `REVOKED` yapilip onceki surume kontrollu donulmelidir.
- Kalan risk: HTTP cookie/token tasimasi, CSRF, es zamanli oturum limiti, mutlak sure, uretim deposu/sifreleme ve saklama suresi banka karari gerektirir.

## Onaylar

- Teknik dogrulayan: Codex teknik uygulama ajani
- Bilgi guvenligi: ComplianceReviewRequired
- IAM: ComplianceReviewRequired
- Ic kontrol: ComplianceReviewRequired
- Hukuk/uyum: ComplianceReviewRequired

Bu kanit teknik uygulama sonucudur; BDDK/KVKK uyumu veya banka onayi anlamina gelmez.
