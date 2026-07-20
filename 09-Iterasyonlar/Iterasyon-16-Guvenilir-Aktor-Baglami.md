---
iteration: 16
status: technically-verified
primary_module: identity-and-dashboard
---

# İterasyon 16 — Güvenilir Aktör Bağlamı

## Kullanıcı/Sistem Değeri

Yetki kararları serbest `actor_id` veya çağıranın oluşturduğu `DashboardAccessScope` yerine güvenilir ve değişmez kimlik bağlamından üretilir.

## Mevcut Koda Dayalı Problem

- Servis metotları `actor_id: str` alıyor.
- Dashboard doğrudan `DashboardAccessScope` alıyor.
- Gerçek LDAP/RBAC adaptörü yok.
- Bu yapı domain testleri için yararlı olsa da API yüzeyinde güven sınırı oluşturmaz.

## Kapsam

1. Ortak `ActorContext` ve `ActorType`.
2. `AuthorizationService` protokolü.
3. Dashboard için `ActorContext -> DashboardAccessScope` üretimi.
4. Güvenilir context olmadan sorgunun repository'ye ulaşmadan reddedilmesi.
5. Eski scope tabanlı çağrı için internal/deprecated geçiş adaptörü.
6. Correlation ID ve policy version.
7. Birim testleri ve kanıt kaydı.

## Kapsam Dışı

- Gerçek LDAP bağlantısı.
- Session/token HTTP katmanı.
- Tüm servislerdeki actor_id parametrelerinin tek turda kaldırılması.
- Maker-checker.

## Gereksinimler

- FR-002, FR-004, RULE-001, RULE-009
- BFR-IAM-001, BFR-IAM-002, BFR-IAM-004
- BRULE-001

## Kabul Kriterleri

1. Geçerli ActorContext ile izinli SOURCE sonucu döner.
2. ActorContext olmadan istek reddedilir ve repository çağrılmaz.
3. Çağıranın eklediği sahte source scope yetki yükseltemez.
4. Süresi dolmuş veya policy version'ı geçersiz context reddedilir.
5. ENTERPRISE görünürlüğü explicit izin olmadan açılmaz.
6. Mevcut 129 test ve yeni testler geçer.

## Kapanış

- **Tamamlanma tarihi:** 2026-07-16
- **Teknik durum:** TechnicallyVerified
- **Regresyon sonucu:** 139 test geçti.
- **Negatif testler:** Eksik/sahte/süresi dolmus/eski policy context, sahte scope, servis hesabı ve audit hatası fail-closed reddedildi.
- **Audit/redaksiyon:** Authorization karar özeti ham rol, session veya source/dataset kimliği taşımıyor.
- **Kanıt:** [Iterasyon-16-Guvenilir-Aktor-Kaniti](../08-Uyum-Kanitlari/Erisim/Iterasyon-16-Guvenilir-Aktor-Kaniti.md)
- **Banka onayı:** ComplianceReviewRequired
- **Geri alma:** Yeni HTTP yüzeyi bulunmadığından güvenli pasifleştirme composition katmanında dashboard servisinin bağlanmaması ile yapılır; ınternal legacy adapter yalnız kontrollü geçiş testleri içindir.
- **Sonraki iterasyon:** İterasyon 17 - Merkezi Audit Bütünlüğü
