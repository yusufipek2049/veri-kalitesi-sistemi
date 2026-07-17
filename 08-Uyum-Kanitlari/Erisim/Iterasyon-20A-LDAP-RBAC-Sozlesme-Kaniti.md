---
control_ids:
  - BFR-IAM-001
  - BFR-IAM-003
  - BFR-IAM-004
  - BFR-IAM-006
  - BRULE-001
  - BRULE-005
requirement_ids:
  - FR-001
  - FR-002
  - FR-003
  - UC-001
  - NFR-SEC-001
  - NFR-SEC-005
  - NFR-SEC-008
status: TechnicallyVerified
version: iteration-20a-local
executed_at: 2026-07-17
---

# Iterasyon 20A LDAP RBAC Sozlesme Kaniti

## Degisiklik

- Iterasyon: 20A - LDAP/RBAC adaptor sozlesmesi ve guvenilir grup iddiasi siniri
- Commit/Artifact: Git deposu bulunmadigi icin commit yok; yerel calisma agaci
- Bilesen: `veri_kalitesi.identity`, `veri_kalitesi.audit`
- Kontrol/Gereksinim: FR-001-003, UC-001, NFR-SEC-001/005/008, BFR-IAM-001/003/004/006, BRULE-001/005 alt kapsami

## Dogrulama

- Komut: `PYTHONPATH=03-Backend/src python3 -m pytest -q`
- Ortam: Python 3.10.12, yerel prototip, fake LDAP adaptoru ve sentetik kimlik verisi
- Sentetik veri seti: Teknik subject, sentetik principal, gecici bayt credential, eslenen/eslenmeyen grup, pasif kimlik, servis hesabi ve LDAP/audit arizasi
- Beklenen: Yalniz guvenilir adaptor iddiasi surumlu politikayla role/scope uretir; eslenmeyen grup yetki vermez; ret ve teknik hata context olusturmadan ayrilir; ozet hassas kimlik girdilerini tasimaz.
- Gerceklesen: 224 test gecti. Kimlik hedef grubu 12 testle gecti; context mevcut dashboard authorization politikasina basariyla baglandi.
- Sonuc: PASS

Ek kontroller:

- Degisen bes Python dosyasinda `python3 -m ruff format --check ...`: PASS
- `python3 -m ruff check 03-Backend/src 06-Testler`: PASS
- `python3 -m compileall -q 03-Backend/src 06-Testler`: PASS
- Hassas desen taramasi: PASS; gercek LDAP URL, kullanici, credential, token veya banka grup kodu kullanilmadi.
- Tam depo format kontrolu, bu iterasyonda degismeyen 4 eski dosyanin mevcut format farklari nedeniyle PASS degildir.

## Guvenlik

- Guven siniri: Uygulama actor, rol veya scope'u giris isteginden almaz; LDAP adaptorunun dondurdugu iddia ve surumlu policy kullanilir.
- Deny-by-default: Eslenmeyen grup, pasif kimlik, izin verilmeyen actor tipi ve gecersiz adaptor iddiasi context uretmez.
- Hata ayrimi: Credential reddi `DENIED`, LDAP teknik veya beklenmeyen adaptor hatasi `FAILURE` olarak ayrilir.
- Servis hesabi: Kullanici LDAP akisinda servis hesabi reddedilir; ayri amac/scope modeli banka karari olarak aciktir.
- Audit: Basari, ret ve teknik hata kaydedilir; audit yazilamazsa context dondurulmez.
- Veri minimizasyonu: Principal, credential, LDAP grup kodlari ve kaynak/dataset kimlikleri audit ozetine girmez; session yalniz digest olur.
- Dashboard bagi: ActorContext policy surumu ve izinli kaynak kapsami mevcut authorization servisi tarafindan tuketilir.
- Kalan risk: Gercek LDAP endpoint/TLS/sertifika, banka grup-role-scope degerleri, session/lockout, MFA/PAM/break-glass ve issuer process siniri bu kanitin disindadir.

## Onaylar

- Teknik dogrulayan: Codex teknik uygulama ajani
- Bilgi guvenligi: ComplianceReviewRequired
- IAM: ComplianceReviewRequired
- Ic kontrol: ComplianceReviewRequired
- Hukuk/uyum: ComplianceReviewRequired

Bu kanit teknik uygulama sonucudur; BDDK/KVKK uyumu veya banka onayi anlamina gelmez.
