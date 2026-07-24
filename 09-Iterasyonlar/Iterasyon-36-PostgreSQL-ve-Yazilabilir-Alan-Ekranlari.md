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
| Issue kapatma ve yeniden açma | `VerificationPending` | Kod/test kanıtı mevcut; güncel hedefli ve PostgreSQL koşusu kayda bağlanmalı. |
| Kural ve veri kaynağı yazımları | Uygulama yüzeyi mevcut | Production composition root ve kurumsal politika/rol kanıtı ayrıca doğrulanmalı. |
| Çalıştırma PostgreSQL cutover | `TechnicallyVerified` | PostgreSQL migration/repository, API adaptörleri ve testler tamamlandı. `SQLiteExecutionRepository` runtime export'tan çıkarıldı. |
| Güvenli rapor üretimi/indirme | `Blocked` | DLP, watermark, gerekçe, maker-checker ve kurumsal karar kapıları açık. |

## Değişmez Tamamlama Koşulları

- Mutasyonlar güvenilir aktör, rol/scope, BFF/CSRF ve sayısal sürüm kontrolünden geçer.
- Kritik yazım audit/outbox ile atomiktir; audit üretilemezse fail-closed sonuçlanır.
- Teknik hata veri kalitesi ihlali olarak sunulmaz.
- PostgreSQL'e taşınan production domaininde SQLite fallback bırakılmaz.
- Gerçek banka verisi, kimliği veya secret'ı geliştirme/test ortamına yazılmaz.

## Sıradaki İş

[Execution politika ve worker dayanıklılığı](../NEXT_STEP.md) — kota, pencere,
timeout, retry, iptal ve idempotency sürümlü politikadan/kalıcı kuyruktan
çözülmesi. 36B5 doğrulama kaydı paralel dokümantasyon/test borcudur.
