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

# İterasyon 20A LDAP RBAC Sözleşme Kanıtı

## Değişiklik

- İterasyon: 20A - LDAP/RBAC adaptör sözleşmesi ve güvenilir grup iddiası sınırı
- Commit/Artifact: Git deposu bulunmadığı için commit yok; yerel çalışma ağacı
- Bileşen: `veri_kalitesi.identity`, `veri_kalitesi.audit`
- Kontrol/Gereksinim: FR-001-003, UC-001, NFR-SEC-001/005/008, BFR-IAM-001/003/004/006, BRULE-001/005 alt kapsamı

## Doğrulama

- Komut: `PYTHONPATH=03-Backend/src python3 -m pytest -q`
- Ortam: Python 3.10.12, yerel prototip, fake LDAP adaptörü ve sentetik kimlik verisi
- Sentetik veri seti: Teknik subject, sentetik principal, geçici bayt credential, eşlenen/eşlenmeyen grup, pasif kimlik, servis hesabı ve LDAP/audit arızası
- Beklenen: Yalnız güvenilir adaptör iddiası sürümlü politikayla role/scope üretir; eşlenmeyen grup yetki vermez; ret ve teknik hata context oluşturmadan ayrılır; özet hassas kimlik girdilerini taşımaz.
- Gerçekleşen: 224 test geçti. Kimlik hedef grubu 12 testle geçti; context mevcut dashboard authorization politikasına başarıyla bağlandı.
- Sonuç: PASS

Ek kontroller:

- Değişen beş Python dosyasında `python3 -m ruff format --check ...`: PASS
- `python3 -m ruff check 03-Backend/src 06-Testler`: PASS
- `python3 -m compileall -q 03-Backend/src 06-Testler`: PASS
- Hassas desen taraması: PASS; gerçek LDAP URL, kullanıcı, credential, token veya banka grup kodu kullanılmadı.
- Tam depo format kontrolü, bu iterasyonda değişmeyen 4 eski dosyanın mevcut format farkları nedeniyle PASS değildir.

## Güvenlik

- Güven sınırı: Uygulama actor, rol veya scope'u giriş isteğinden almaz; LDAP adaptorunun döndürdüğü iddia ve sürümlü policy kullanılır.
- Deny-by-default: Eşlenmeyen grup, pasif kimlik, izin verilmeyen actor tipi ve geçersiz adaptör iddiası context üretmez.
- Hata ayrımı: Credential reddi `DENIED`, LDAP teknik veya beklenmeyen adaptör hatası `FAILURE` olarak ayrılır.
- Servis hesabı: Kullanıcı LDAP akışında servis hesabı reddedilir; ayrı amaç/scope modeli banka kararı olarak açıktır.
- Audit: Başarı, ret ve teknik hata kaydedilir; audit yazılamazsa context döndürülmez.
- Veri minimizasyonu: Principal, credential, LDAP grup kodları ve kaynak/dataset kimlikleri audit özetine girmez; session yalnız digest olur.
- Dashboard bağı: ActorContext policy sürümü ve izinli kaynak kapsamı mevcut authorization servisi tarafından tüketilir.
- Kalan risk: Gerçek LDAP endpoint/TLS/sertifika, banka grup-role-scope değerleri, session/lockout, MFA/PAM/break-glass ve issuer process sınırı bu kanıtın dışındadır.

## Onaylar

- Teknik doğrulayan: Codex teknik uygulama ajanı
- Bilgi güvenliği: ComplianceReviewRequired
- IAM: ComplianceReviewRequired
- İç kontrol: ComplianceReviewRequired
- Hukuk/uyum: ComplianceReviewRequired

Bu kanıt teknik uygulama sonucudur; BDDK/KVKK uyumu veya banka onayı anlamına gelmez.
