---
iteration: 20
status: technically-verified
primary_module: identity
---

# İterasyon 20 — LDAP/RBAC Entegrasyonu

## Ön Koşul Kararları

- LDAP endpoint/topoloji
- TLS ve sertifika doğrulama
- Grup-rol-scope eşleme
- Kullanıcı yaşam döngüsü kaynağı
- MFA/PAM/break-glass
- Session timeout
- Servis hesabı modeli

## Kapsam

- LDAP adapter protokolü ve üretim adaptörü sınırı.
- Grup-rol-scope policy version.
- Login sonucu ActorContext.
- Fail-closed ve teknik hata ayrımı.
- Fake LDAP sözleşme testleri.
- Gerçek secret veya banka hesabı kullanılmaz.

## Kabul

- Eşlenmeyen grup yetki üretmez.
- LDAP teknik hatası hatalı parola gibi raporlanmaz.
- Başarısız giriş audit/güvenlik olayı üretir.
- ActorContext doğrudan dashboard authorization'a bağlanır.

## Dilim 20A Kapanisi

`TechnicallyVerified` kapsam:

- LDAP adaptör protokolü credential değerini yalnız geçici çağrı girdisi olarak alır ve doğrulanmış subject/grup iddiası döndürür.
- Sürümlü grup-rol-scope politikası yalnız eşlenen gruplardan değişmez `ActorContext` üretir; eşlenmeyen grup yetki vermez.
- Credential reddi, pasif/eşlemesiz kimlik ve LDAP teknik hatası ayrı fail-closed sonuçlardır; servis hesabı kullanıcı akışında reddedilir.
- Başarı/ret/teknik hata audit edilir; principal, credential, grup ve kapsam kimlikleri audit özetine girmez. Audit hatasında context döndürülmez.
- Üretilen context mevcut dashboard authorization servisine doğrudan bağlanır.
- On iki yeni testle toplam 224 test geçti; kimlik hedef grubu 12 testle geçti.

Gerçek LDAP endpoint/TLS/sertifika adaptörü, banka grup değerleri, session/lockout, MFA/PAM/break-glass, servis hesabı amacı ve issuer süreç sahipliği açık kalır; `ComplianceReviewRequired` durumundadır.

## Dilim 20B Kapanisi

`TechnicallyVerified` kapsam:

- Sürümlü throttle politikası en fazla beş credential reddi ve en az 15 dakikalık engel tabanını doğrular; eşik, pencere ve süre dışarıdan enjekte edilir.
- Kullanıcı ve istemci opak anahtarları ayrı, kalıcı SQLite sayaçlarında atomik güncellenir; aktif kapsamlardan biri sonraki LDAP çağrısını engeller.
- Başarılı giriş ilgili sayaçları güvenli biçimde sıfırlar; LDAP teknik/öngörülmeyen hataları sayılmaz.
- Anahtar üretici veya sayaç deposu arızası fail-closed kapanır ve teknik audit olayı üretir.
- Principal, istemci referansı ve credential sayaç deposunda veya audit özetinde saklanmaz.
- On üç yeni testle toplam 237 test; kimlik hedef grubu 25 testle geçti.

Üretim opak anahtar üreticisi/secret manager, güvenilir istemci referansı sınırı, paylaşımlı üretim deposu, LDAP politikasıyla nihai değer uyumu ve banka onayları açık kalır; `ComplianceReviewRequired` durumundadır.

## Dilim 20C Kapanisi

`TechnicallyVerified` kapsam:

- LDAP başarı akışı çağırandan session kimliği veya süre kabul etmez; yalnız güvenilir doğrulama context'ini zorunlu session servisine aktarır.
- İterasyonun mevcut runtime sürümü 30 dakikalık idle timeout tabanını ve enjekte
  edilen mutlak süreyi uygular; aktivite mutlak süreyi uzatmaz. Sonraki banka
  onaylı `OPEN-BNK-020` politika sürümü `PT1H` idle ve `PT10H` mutlak süreyi
  zorunlu kılar; runtime geçişi ayrı artımdır.
- Yüksek entropili credential yalnız bir kez döndürülür; kalıcı SQLite kaydında yalnız özeti tutulur.
- Aktif oturum doğrulaması güvenilir `ActorContext` üretir; timeout ve çıkış geçmişi fiziksel silinmeden `EXPIRED`/`REVOKED` kalır.
- Servis hesabı, ayrıcalıklı kullanıcı, güvenilmez/süresi dolmuş context, bozuk credential ve depo/audit hataları normal kullanıcı oturumunda fail-closed reddedilir.
- On yedi yeni testle toplam 254 test; kimlik hedef grubu 42 testle geçti.

Bu iterasyon kapanışında gerçek LDAP, HTTP cookie/token/CSRF sınırı, eş zamanlı
oturum limiti, mutlak süre, banka grup/ayrıcalık kararları, üretim
deposu/şifreleme ve saklama onayı açık kalmıştı. `OPEN-BNK-020` sonradan
`ApprovedByBank` olarak kapandı; BFF/cookie/CSRF, merkezi iptal, üretim store,
şifreleme ve `P90D` saklama davranışının uygulanması açıktır.
