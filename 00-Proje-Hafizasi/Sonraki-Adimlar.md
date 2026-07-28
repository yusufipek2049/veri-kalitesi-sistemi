---
type: delivery-backlog
status: active
project: Veri Kalitesi İzleme ve Skorlama Sistemi
last_updated: 2026-07-27
---

# Sonraki Adımlar

Tek uygulanabilir sıradaki paket:
[Kalıcı İş Kuyruğu ve Worker Dayanıklılığı](../NEXT_STEP.md).

## Aktif Backlog

| Sıra | İş | Durum | Tamamlanma ölçütü |
| --- | --- | --- | --- |
| 1 | Kalıcı iş kuyruğu ve worker dayanıklılığı | `Next` | Kalıcı kuyruk, lease/heartbeat, worker kaybı toparlama, politika kontrollü kota/pencere/timeout/retry, iptal/idempotency ve dead-letter/audit çıkış kapıları [NEXT_STEP](../NEXT_STEP.md) içinde geçer. |
| 2 | 36F scheduling/policy PostgreSQL kalıcılığı | `Completed` / `TechnicallyVerified` | PostgreSQL repository/migration mevcut; SQLite scheduling/policy repository'leri runtime export'tan çıkarılmıştır. |
| 3 | 36G güvenli rapor üretimi ve indirme | `Completed` / `TechnicallyVerified` | PDF/XLSX/CSV, zamanlanmış rapor, politika framework'ü, PostgreSQL repository, API ve frontend kanıtı kapanış kaydındadır. |
| 4 | 36B5 kapatma/yeniden açma doğrulama kaydı | `Completed` / `TechnicallyVerified` | PostgreSQL mutasyon ve entegrasyon kanıtı iterasyon kaydında tamamlanmıştır. |
| 5 | Kurumsal production adaptörleri | `ExternalDependency` | IdP, PAM/secret manager, HA veri/session, broker, SIEM/WORM, ServiceNow ve DR kanıtları. |

## Son Yedi İterasyonun Konsolide Çıktısı

Issue domaini PostgreSQL'e taşındı; seçici SQLite aktarımı tamamlandı ve issue
runtime fallback'i kaldırıldı. İnceleme, yeniden atama, korumalı çözüm, farklı
aktörle doğrulama ve kapatma UI/API akışları mevcuttur. Kapatma/yeniden açma
`36B5` kaydıyla teknik olarak doğrulanmıştır.

Execution PostgreSQL cutover (36E) tamamlanmıştır: `PostgreSQLExecutionRepository`
production composition root'unda, `SQLiteExecutionRepository` runtime export'tan
çıkarılmıştır. Scheduling/source-usage policy PostgreSQL kalıcılığı (36F) ile
güvenli rapor üretimi/indirme (36G) de tamamlanmıştır.

Sıradaki tek paket kalıcı iş kuyruğu ve worker dayanıklılığıdır.

Tamamlanmış eski backlog ayrıntıları [iterasyon arşivindedir](../archive/iterations/README.md).
