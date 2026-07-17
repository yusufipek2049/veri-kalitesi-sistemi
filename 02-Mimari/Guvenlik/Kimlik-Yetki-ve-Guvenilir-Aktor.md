# Kimlik, Yetki ve Güvenilir Aktör

## Hedef Model

```text
AuthenticationAdapter -> IdentityAssertion -> ActorContext
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
5. LDAP adaptörünü en son değil, context sözleşmesi sabitlendikten sonra bağla.

## Fail-Closed

Kimlik doğrulama sonucu var ancak rol/scope eşlemesi yoksa erişim reddedilir. LDAP erişilemezse mevcut session politikası banka kararıyla uygulanır; yeni oturum açılmaz.
