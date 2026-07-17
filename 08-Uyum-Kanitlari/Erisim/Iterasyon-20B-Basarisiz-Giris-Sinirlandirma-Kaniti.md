---
control_ids:
  - BFR-IAM-004
requirement_ids:
  - FR-006
  - UC-001
  - NFR-SEC-010
  - AC-002
status: TechnicallyVerified
version: iteration-20b-local
executed_at: 2026-07-17
---

# Iterasyon 20B Basarisiz Giris Sinirlandirma Kaniti

## Degisiklik

- Iterasyon: 20B - yapilandirilabilir ve kalici basarisiz giris sinirlandirmasi
- Commit/Artifact: Git deposu bulunmadigi icin commit yok; yerel calisma agaci
- Bilesen: `veri_kalitesi.identity`, `veri_kalitesi.audit`
- Kontrol/Gereksinim: FR-006, UC-001, NFR-SEC-010, AC-002 ve BFR-IAM-004 alt kapsami

## Dogrulama

- Komut: `pytest -q`
- Ortam: Python 3.10.12, yerel prototip, fake LDAP adaptoru ve sentetik opak anahtarlar
- Sentetik veri seti: Credential reddi, LDAP teknik arizasi, iki kullanici/istemci kapsami, kalici SQLite sayaci, 15 dakikalik zaman ilerletme ve kapali depo
- Beklenen: En gec besinci credential reddinde kullanici ve istemci kapsamlari en az 15 dakika engellenir; aktif engel LDAP cagrisindan once reddedilir; LDAP teknik hatasi sayaci artirmaz; basari sayaci sifirlar; ham kimlik girdileri saklanmaz.
- Gerceklesen: 237 test gecti. Kimlik hedef grubu 25 testle gecti; besinci rette iki kapsam engellendi ve sonraki cagri LDAP'a ulasmadi.
- Sonuc: PASS

Ek kontroller:

- `ruff check 03-Backend/src 06-Testler`: PASS
- Degisen alti Python dosyasinda `ruff format --check ...`: PASS
- `python3 -m compileall -q 03-Backend/src`: PASS
- Tam depo format kontrolu, bu iterasyonda degismeyen dort eski dosyanin mevcut format farklari nedeniyle PASS degildir.

## Guvenlik

- Guven siniri: Principal ve istemci referansi, enjekte edilen guvenilir anahtar saglayici tarafindan opak kullanici/istemci anahtarina donusturulur.
- Deny-by-default: Anahtar uretimi veya throttle deposu kullanilamazsa LDAP cagrisi ve context uretimi yapilmaz.
- Hata ayrimi: Yalniz credential reddi sayilir; LDAP teknik ve beklenmeyen hatalari giris sayacini degistirmez.
- Kalicilik: Kullanici ve istemci sayaclari ayri SQLite satirlarinda atomik guncellenir ve repository yeniden acildiginda engel korunur.
- Veri minimizasyonu: Principal, istemci referansi ve credential throttle deposuna veya audit ozetine yazilmaz; audit yalniz politika surumleri, sayac ve engel ozetini tasir.
- Maker-checker etkisi: Bu dilimde politika olusturma/degistirme API'si yoktur; politika yalniz baslangicta enjekte edilir. Uretim politika degisikligi onayi ve gorevler ayriligi `OPEN-BNK-019` altinda aciktir.
- Geri alma: LDAP servisi throttle bagimliligi olmadan kurulamaz; guvenli pasiflestirme ancak banka onayli daha kisitlayici olmayan yeni politika ve kontrollu migration ile yapilmalidir.
- Kalan risk: Uretim anahtar saglayicisi, secret manager, istemci referansinin guvenilir ag siniri, paylasimli uretim deposu ve LDAP lockout deger uyumu banka karari gerektirir.

## Onaylar

- Teknik dogrulayan: Codex teknik uygulama ajani
- Bilgi guvenligi: ComplianceReviewRequired
- IAM: ComplianceReviewRequired
- Ic kontrol: ComplianceReviewRequired
- Hukuk/uyum: ComplianceReviewRequired

Bu kanit teknik uygulama sonucudur; BDDK/KVKK uyumu veya banka onayi anlamina gelmez.
