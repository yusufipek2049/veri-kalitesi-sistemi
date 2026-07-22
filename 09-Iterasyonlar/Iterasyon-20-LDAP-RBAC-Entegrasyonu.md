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

## Dilim 20D Kapanışı

`TechnicallyVerified` kapsam:

- `OPEN-BNK-020` için banka onaylı `PT1H` idle ve `PT10H` mutlak süre üst
  sınırları runtime politikasında uygulanır; daha sıkı politika sürümleri
  desteklenir.
- Kullanıcı başına tek aktif normal oturum kuralı depo transaction'ında
  uygulanır. Yeni başarılı giriş önceki aktif oturumu iptal eder, credential
  özetini siler ve yeni oturumu aynı atomik işlemde kaydeder.
- Logout, timeout, yeni giriş ve oluşturma auditi arızasıyla terminal duruma
  geçen oturumların credential özeti tutulmaz; veri-minimum durum, zaman ve
  neden metadatası korunur.
- Oturum servisi `SessionRepository` protokolüne bağlanır. SQLite prototipi eski
  `credential_digest NOT NULL` şemasını nullable şemaya açılışta geçirir.
- Yalnız `USER_INTERACTION` idle aktivitesini yeniler; `BACKGROUND` ve
  `TOKEN_REFRESH` doğrulamaları idle süresini uzatmaz. Güvenilmeyen aktivite
  sınıfı reddedilir.
- Kimlik hedefinde 47, tam depoda 993 test geçti. Tam mypy, Ruff lint/format,
  `compileall` ve `git diff --check` kontrolleri hatasızdır.

Bu dilim HTTP/BFF cookie taşımasını, synchronizer-token CSRF kontrollerini,
kullanıcı pasifleştirme/rol değişimi/güvenlik olayı/IdP kaynaklı merkezi iptal
adaptörlerini, yüksek erişilebilir üretim session store'unu, at-rest
şifreleme/KMS-HSM bağlantısını veya `P90D` fiziksel saklama/imha kanıtını
uygulamaz. Bu kapsamlar birbirinden bağımsız sonraki ürün artımlarıdır.

## Dilim 20E Kapanışı

`TechnicallyVerified` kapsam:

- `SessionGrant`, session credential'dan ayrı yüksek entropili CSRF token üretir;
  SQLite prototipinde yalnız SHA-256 özeti saklanır. Eski şemalar nullable
  `csrf_token_digest` alanıyla geriye uyumlu genişletilir.
- `__Host-session` taşıması `Secure`, `HttpOnly`, `SameSite=Lax`, `Path=/` ve
  domainsiz cookie olarak uygulanır. CSRF token cookie'ye konmaz; güvenilir IdP
  callback adaptörünün kullanacağı no-store response header'ıyla döndürülür.
- Dashboard resolver'ı aktör/rol/scope header'ı kabul etmeden cookie credential'ı
  mevcut `SessionService` üzerinden güvenilir `ActorContext`e dönüştürür. Okuma
  isteği `BACKGROUND` olarak idle süresini uzatmaz.
- Durum değiştiren isteklerde custom CSRF header, Origin, Referer, Fetch Metadata
  ve CORS allowlist kontrolleri fail-closed uygulanır. `POST /api/v1/session/logout`
  doğru kanıtla oturumu iptal eder ve cookie'yi siler; `GET` logout yapamaz.
- Eksik/değiştirilmiş cookie veya CSRF, güvenilmeyen request metadata ve session
  store arızası güvenli 401/403/503 Problem Details yanıtlarına ayrılır.
- 14 yeni testle tam depoda 1029 test geçti; iki gerçek PostgreSQL testi opt-in
  kaldı. Mypy 159 dosyada, Ruff, format, `compileall`, frontend type-check/test/build
  ve secret taraması geçti.

Bu dilim gerçek OIDC/SAML callback ve state/nonce doğrulamasını, banka grup-rol
değerlerini, ayrıcalıklı/servis oturumunu, diğer merkezi iptal tetiklerini,
yüksek erişilebilir üretim store'unu, at-rest şifreleme/KMS-HSM bağlantısını veya
`P90D` fiziksel saklama/imha kanıtını uygulamaz.
