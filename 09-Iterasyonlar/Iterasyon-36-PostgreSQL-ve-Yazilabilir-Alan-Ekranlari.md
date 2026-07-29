---
iteration: 36
status: in_progress
completed_at: null
decision_reference: USER-DECLARATION-2026-07-23-POSTGRESQL-WRITABLE-UI
---

# İterasyon 36 — PostgreSQL-only ve Yazılabilir Alan Ekranları

## Amaç

SQLite kalıcılığını domain bazlı kaldırmak ve uygulamanın sahip olduğu metadata,
politika, iş akışı, sonuç ve audit kayıtlarını güvenilir mutasyon sınırlarıyla
yönetmek. Kaynak sistemler salt okunur kalır.

## Konsolide Durum

| Alan | Durum | Kalan sınır |
| --- | --- | --- |
| Issue PostgreSQL temeli ve aktarımı | `TechnicallyVerified` | Üretim banka/altyapı onayı ayrı. |
| Issue inceleme, atama, çözüm, doğrulama | `TechnicallyVerified` | Gerçek IdP/dizin bağlantısı açık. |
| Issue kapatma ve yeniden açma | `TechnicallyVerified` | 36B5 güncel birim ve PostgreSQL kanıtıyla kapandı; production banka/altyapı onayı ayrı. |
| Kural ve veri kaynağı yazımları | Uygulama yüzeyi mevcut | Banka onaylı production wiring ve kurumsal politika/rol kanıtı ayrıca doğrulanmalı. |
| Çalıştırma PostgreSQL cutover | `TechnicallyVerified` | PostgreSQL migration/repository, API adaptörleri ve testler tamamlandı. `SQLiteExecutionRepository` runtime export'tan çıkarıldı. |
| Güvenli rapor üretimi/indirme | `TechnicallyVerified` | 36G ile PDF/XLSX/CSV, politika framework'ü, zamanlanmış rapor, PostgreSQL repository ve frontend UI tamamlandı; kurumsal DLP/watermark adaptörleri ayrı. |
| Kalıcı iş kuyruğu ve yürütme yaşam döngüsü | `TechnicallyVerified` | 36H1 kuyruk çekirdeği ile 36H2 worker/reaper, deadline, iptal, retry/dead-letter ve auditli yaşam döngüsü tamamlandı; production HA/broker/operasyon kanıtı ayrı. |

## Değişmez Tamamlama Koşulları

- Mutasyonlar güvenilir aktör, rol/scope, BFF/CSRF ve sayısal sürüm kontrolünden geçer.
- Kritik yazım audit/outbox ile atomiktir; audit üretilemezse fail-closed sonuçlanır.
- Teknik hata veri kalitesi ihlali olarak sunulmaz.
- PostgreSQL'e taşınan production domaininde SQLite fallback bırakılmaz.
- Gerçek banka verisi, kimliği veya secret'ı geliştirme/test ortamına yazılmaz.

## Sıradaki Durum

[Son tamamlanan paket](../NEXT_STEP.md) ENTERPRISE-LAB-03'tür ve yalnız
`PrototypeVerified` durumundadır; `ComplianceReviewRequired` kalır ve
production-ready değildir. Bağımlılıkları tamamlanmış yeni bir `Next`/`READY`
teknik paket yoktur; kalan production readiness başlıkları dış bağımlılık ve
banka/operasyon kanıtıdır.
