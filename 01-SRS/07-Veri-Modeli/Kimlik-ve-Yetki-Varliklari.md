---
type: data-dictionary-group
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_document: Veri_Kalitesi_Izleme_ve_Skorlama_Sistemi_SRS_v0.1.md
source_version: "0.1"
source_section: "User, Role, Permission"
created_at: 2026-07-16
tags:
  - srs
  - data-dictionary
  - identity
---

# Kimlik ve Yetki Varlıkları

## User

| Alan adı | Veri tipi | Uzunluk | Zorunluluk | Benzersizlik | Varsayılan değer | Açıklama | Hassas veri durumu | Doğrulama kuralı |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| user_id | UUID | 36 | Evet | Evet | Otomatik | Yerel kullanıcı anahtarı | Hayır | Geçerli UUID |
| identity_subject | VARCHAR | 255 | Evet | Koşullu benzersiz | Yok | Kurumsal IdP subject kimliği | Kişisel | Issuer ile birlikte benzersiz; normalize edilmiş |
| identity_issuer | VARCHAR | 500 | Evet | Hayır | Yok | Kurumsal IdP issuer referansı | Hassas olabilir | Onaylı IdP |
| display_name | VARCHAR | 200 | Evet | Hayır | Yok | Görünen ad | Kişisel | Kontrol karakteri içermez |
| email | VARCHAR | 254 | Hayır | Hayır | NULL | Kurumsal e-posta; bildirim kanalı olarak kullanılmaz | Kişisel | Geçerli kurumsal format |
| status | ENUM | 20 | Evet | Hayır | ACTIVE | ACTIVE/PASSIVE/LOCKED | Hayır | İzinli enum |
| last_login_at | TIMESTAMP | — | Hayır | Hayır | NULL | Son başarılı giriş UTC | Kişisel | Gelecek tarih olamaz |

## IdentityGroupRoleMapping

| Alan adı | Veri tipi | Uzunluk | Zorunluluk | Benzersizlik | Varsayılan değer | Açıklama | Hassas veri durumu | Doğrulama kuralı |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mapping_id | UUID | 36 | Evet | Evet | Otomatik | Eşleme anahtarı | Hayır | UUID |
| external_group_reference | VARCHAR | 500 | Evet | Hayır | Yok | IdP/dizin grup referansı | Hassas olabilir | Onaylı issuer kapsamı |
| role_id | UUID | 36 | Evet | Hayır | Yok | Uygulama rolü | Hayır | Aktif Role |
| priority | INTEGER | — | Evet | Hayır | Yok | Deterministik çatışma önceliği | Hayır | Benzersiz veya açık ret politikası |
| conflict_policy | ENUM | 20 | Evet | Hayır | DENY | PRIORITY/DENY | Hayır | İzinli enum |
| policy_version | VARCHAR | 80 | Evet | Hayır | Yok | Eşleme politikası sürümü | Hayır | Değişmez sürüm |
| status | ENUM | 20 | Evet | Hayır | ACTIVE | ACTIVE/PASSIVE | Hayır | İzinli geçiş |

## Role

| Alan adı | Veri tipi | Uzunluk | Zorunluluk | Benzersizlik | Varsayılan değer | Açıklama | Hassas veri durumu | Doğrulama kuralı |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| role_id | UUID | 36 | Evet | Evet | Otomatik | Rol anahtarı | Hayır | Geçerli UUID |
| role_code | VARCHAR | 80 | Evet | Evet | Yok | Makinece okunur rol kodu | Hayır | Büyük harf/alt çizgi |
| role_name | VARCHAR | 150 | Evet | Hayır | Yok | Rol adı | Hayır | 1–150 karakter |
| description | VARCHAR | 500 | Evet | Hayır | Yok | Rol açıklaması | Hayır | HTML temizlenir |
| is_active | BOOLEAN | 1 | Evet | Hayır | TRUE | Rol etkinliği | Hayır | Boolean |

## Permission

| Alan adı | Veri tipi | Uzunluk | Zorunluluk | Benzersizlik | Varsayılan değer | Açıklama | Hassas veri durumu | Doğrulama kuralı |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| permission_id | UUID | 36 | Evet | Evet | Otomatik | İzin anahtarı | Hayır | UUID |
| permission_code | VARCHAR | 120 | Evet | Evet | Yok | RESOURCE.ACTION biçimli izin | Hayır | Tanımlı sözlükte bulunur |
| scope_type | ENUM | 30 | Evet | Hayır | GLOBAL | GLOBAL/DOMAIN/SOURCE/DATASET | Hayır | İzinli enum |
| description | VARCHAR | 500 | Evet | Hayır | Yok | İzin açıklaması | Hayır | HTML temizlenir |

## NormalUserSessionPolicy

`OPEN-BNK-020` banka onaylıdır. Politika değişmez sürüm ve audit referansıyla
saklanır; üretim davranışı çağıranın gönderdiği değerlerden türetilemez.

| Alan adı | Veri tipi | Zorunluluk | Varsayılan/karar | Doğrulama kuralı |
| --- | --- | --- | --- | --- |
| policy_id | UUID | Evet | Otomatik | UUID |
| policy_version | VARCHAR | Evet | Yok | Değişmez ve benzersiz sürüm |
| status | ENUM | Evet | ACTIVE | DRAFT/ACTIVE/RETIRED; tek aktif sürüm |
| max_active_sessions | INTEGER | Evet | 1 | Pozitif; normal kullanıcı kapsamı |
| on_new_login | ENUM | Evet | REVOKE_PREVIOUS_SESSION | Yeni giriş engellenmez; önceki aktif oturum iptal edilir |
| idle_timeout | DURATION | Evet | `PT1H` | Arka plan istekleri ve otomatik polling süreyi yenilemez |
| absolute_timeout | DURATION | Evet | `PT10H` | Token yenileme süreyi uzatmaz; bitişte yeniden kimlik doğrulama gerekir |
| architecture_model | ENUM | Evet | BFF | Token'lar yalnız sunucu tarafında tutulur |
| browser_credential | ENUM | Evet | OPAQUE_SESSION_COOKIE | Tarayıcı access/refresh token'a erişemez |
| cookie_name | VARCHAR | Evet | `__Host-session` | `__Host-` kurallarıyla uyumlu |
| cookie_secure / cookie_http_only | BOOLEAN | Evet | TRUE / TRUE | Daima true |
| cookie_same_site | ENUM | Evet | LAX | İzinli SameSite değeri |
| cookie_path / cookie_domain | VARCHAR | Evet/Hayır | `/` / NULL | Domain tanımlanamaz |
| rotate_on_login / rotate_on_privilege_change | BOOLEAN | Evet | TRUE / TRUE | Session fixation önleme |
| csrf_model | ENUM | Evet | SYNCHRONIZER_TOKEN | State-changing istekte custom header zorunlu |
| validate_origin / validate_referer / validate_fetch_metadata | BOOLEAN | Evet | TRUE / TRUE / TRUE | Doğrulama başarısızsa istek reddedilir |
| cors_allowlist_required | BOOLEAN | Evet | TRUE | Wildcard credential origin kullanılamaz |
| allow_state_change_via_get | BOOLEAN | Evet | FALSE | `GET` durum değiştiremez |
| production_store_preference | ENUM | Evet | INSTITUTION_APPROVED_HA_CENTRAL_STORE | Kurum hizmeti yoksa PostgreSQL fallback; süreç belleği yasak |
| store_session_id_as_hash | BOOLEAN | Evet | TRUE | Açık session ID saklanamaz |
| transport_encryption | ENUM | Evet | TLS | Kurum TLS politikası uygulanır |
| at_rest_encryption / key_management | VARCHAR | Evet | Kurum onaylı | Kurum onaylı şifreleme ve KMS/HSM referansı zorunlu |
| security_metadata_retention | DURATION | Evet | `P90D` | Legal hold uzatabilir; imha kanıtı zorunlu |
| approval_reference | VARCHAR | Evet | Yok | Banka onay kanıtı referansı |
| audit_reference | VARCHAR | Evet | Yok | Secret/token içermeyen değişiklik auditi |

## NormalUserSession

| Alan adı | Veri tipi | Zorunluluk | Açıklama | Doğrulama kuralı |
| --- | --- | --- | --- | --- |
| session_id | UUID | Evet | İç oturum anahtarı | UUID |
| session_credential_hash | VARCHAR | Aktifken evet | Opak browser credential özeti | Açık credential saklanamaz; sonlandırmada silinir |
| user_id | UUID | Evet | Normal kullanıcı | Servis/ayrıcalıklı hesap olamaz |
| policy_version | VARCHAR | Evet | Uygulanan session politikası | Aktif/olay anında geçerli sürüm |
| created_at / last_activity_at | TIMESTAMP | Evet | UTC yaşam döngüsü zamanları | Arka plan isteği last activity'yi güncellemez |
| idle_expires_at / absolute_expires_at | TIMESTAMP | Evet | `PT1H` ve `PT10H` sınırları | Mutlak bitiş ileri taşınamaz |
| status | ENUM | Evet | ACTIVE/REVOKED/EXPIRED | İzinli terminal geçişler |
| revocation_reason | ENUM | Terminal durumda evet | LOGOUT/IDLE_TIMEOUT/ABSOLUTE_TIMEOUT/NEW_LOGIN/USER_DISABLED/CRITICAL_ROLE_CHANGE/SECURITY_INCIDENT/IDP_REVOCATION | Onaylı neden sözlüğü |
| terminated_at | TIMESTAMP | Terminal durumda evet | UTC kapanış zamanı | Gelecek zaman olamaz |
| audit_reference | VARCHAR | Evet | Veri-minimum audit/outbox referansı | Session sırrı veya token içeremez |

Aktif credential yalnız kurum onaylı yüksek erişilebilir merkezi depoda, bu
hizmet yoksa PostgreSQL'de tutulur. Süreç belleği üretim deposu olamaz. Access ve
refresh token arşivlenmez; sonlandırılmış kayıtta yalnız veri-minimum güvenlik
metadatası `P90D` saklanır.
