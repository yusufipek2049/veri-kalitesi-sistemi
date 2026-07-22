# Kimlik, Yetki ve Güvenilir Aktör

## Hedef Model

```text
CorporateIdPAdapter (OIDC | SAML) -> IdentityAssertion + MFA Evidence -> ActorContext
ActorContext + AuthorizationPolicy -> AuthorizationDecision
AuthorizationDecision -> Domain command/query
```

## ActorContext Önerisi

- actor_id
- actor_type: USER | SERVICE | BREAK_GLASS
- authentication_source
- session_id
- roles
- permitted_source_ids
- permitted_dataset_ids
- can_view_enterprise
- privileged
- issued_at
- expires_at
- policy_version
- correlation_id

Context değişmez olmalıdır. Domain katmanı actor_id'yi ayrı serbest parametre olarak kabul etmemelidir.

## Geçiş Stratejisi

1. Ortak context modeli ve authorization protokolü ekle.
2. Dashboard dikey dilimini yeni context'e taşı.
3. Eski `DashboardAccessScope` kurucusunu internal/deprecated yap.
4. Diğer servisleri iterasyonlarla yeni context'e geçir.
5. LDAP destekli kurumsal IdP adaptörünü context sözleşmesi sabitlendikten sonra bağla; uygulamayı LDAP şemasına bağımlı kılma.

## Kurumsal Kimlik Politikası

- İlk fazdan itibaren tüm insan kullanıcılar için SSO ve MFA zorunludur; MFA uygulama içinde yeniden geliştirilmez.
- Birden fazla IdP/dizin grubu desteklenir. Grup-rol çatışması sürümlü politikadaki deterministik öncelikle çözülür veya varsayılan reddedilir.
- IdP erişilemezse güvenliksiz yerel girişe otomatik geçiş yapılmaz ve yeni oturum açılmaz.
- Gerekli ise yalnız kontrollü, süreli ve audit edilen `BREAK_GLASS` kimliği ayrı politika ve yetkiyle kullanılabilir.

## Fail-Closed

Kimlik doğrulama sonucu var ancak MFA kanıtı veya rol/scope eşlemesi yoksa erişim reddedilir. Kurumsal IdP erişilemezse yeni oturum açılmaz.

## Banka Onaylı Normal Kullanıcı Oturum Sınırı

`OPEN-BNK-020` `ApprovedByBank` durumundadır.

- Web oturumu BFF modelindedir. Access ve refresh token yalnız sunucu tarafında
  tutulur; tarayıcıya yalnız opak `__Host-session` cookie'si verilir.
- Cookie `Secure`, `HttpOnly`, `SameSite=Lax`, `Path=/` ve domainsizdir; girişte
  ve ayrıcalık değişikliğinde döndürülür.
- State-changing istekler synchronizer token custom header, Origin/Referer,
  Fetch Metadata ve CORS allowlist doğrulamasından geçer. `GET` durum değiştirmez.
- Normal kullanıcı başına tek aktif oturum vardır. Yeni başarılı giriş önceki
  oturumu merkezi olarak iptal eder; yeni giriş engellenmez.
- Idle timeout `PT1H`, mutlak timeout `PT10H`'dir. Arka plan istekleri idle
  süresini, token yenileme mutlak süreyi uzatmaz.
- Logout, süre aşımı, yeni giriş, kullanıcı pasifleştirme, kritik rol değişikliği,
  güvenlik olayı ve IdP iptali merkezi revocation üretir. İptal edilen credential
  yeniden kullanılamaz.
- Üretim oturum deposu kurum onaylı yüksek erişilebilir merkezi hizmettir;
  yoksa PostgreSQL kullanılır. Süreç belleği üretimde yasaktır. Session ID özeti
  saklanır; aktarım TLS, at-rest şifreleme ve anahtar yönetimi kurum onaylı
  KMS/HSM ile sağlanır.
- Oturum sırrı sonlandırmada derhal silinir; access/refresh token arşivlenmez.
  Veri-minimum güvenlik metadatası `P90D` saklanır ve legal hold ile uzatılabilir.
