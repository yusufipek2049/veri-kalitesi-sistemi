---
type: delivery-backlog
status: active
project: Veri Kalitesi İzleme ve Skorlama Sistemi
last_updated: 2026-07-29
---

# Sonraki Adımlar

Bağımlılıkları tamamlanmış `Next`/`READY` teknik paket yoktur.
[ENTERPRISE-LAB-01](../NEXT_STEP.md) sentetik/non-production laboratuvar olarak
`PrototypeVerified` kapanmıştır. Kalan production başlıkları dış bağımlılıklardır.

## Aktif Backlog

| Sıra | İş | Durum | Tamamlanma ölçütü |
| --- | --- | --- | --- |
| 1 | ENTERPRISE-LAB-01 prototip entegrasyon laboratuvarı | `Completed` / `PrototypeVerified` | Sentetik/non-production Compose, sekiz healthy servis, fail-closed ortam kapısı ve streaming PostgreSQL standby [kapanış kaydında](../09-Iterasyonlar/ENTERPRISE-LAB-01-Prototip-Kurumsal-Entegrasyon-Laboratuvari.md); production/banka onayı değildir. |
| 2 | İş yürütme yaşam döngüsü (36H2) | `Completed` / `TechnicallyVerified` | Bounded timeout/iptal, production reaper, atomik execution+job iptali; controller `1172 passed` birim ve skip'siz `41 passed` PostgreSQL kapıları ile reviewer `APPROVED` kararı [36H2 kaydındadır](../09-Iterasyonlar/Iterasyon-36H2-Is-Yurutme-Yasam-Dongusu.md). |
| 3 | 36H1 kalıcı iş kuyruğu çekirdeği | `Completed` / `TechnicallyVerified` | `veri_kalitesi/jobs` idempotent enqueue, deterministik lease claim, sahip-only heartbeat, süresi geçen claim toparlama, optimistic version concurrency ve `background_jobs` migration'ı iterasyon kaydındadır. |
| 4 | 36F scheduling/policy PostgreSQL kalıcılığı | `Completed` / `TechnicallyVerified` | PostgreSQL repository/migration mevcut; SQLite scheduling/policy repository'leri runtime export'tan çıkarılmıştır. |
| 5 | 36G güvenli rapor üretimi ve indirme | `Completed` / `TechnicallyVerified` | PDF/XLSX/CSV, zamanlanmış rapor, politika framework'ü, PostgreSQL repository, API ve frontend kanıtı kapanış kaydındadır. |
| 6 | Kurumsal production adaptörleri | `ExternalDependency` | Gerçek IdP, PAM/secret manager, HA veri/session, broker, SIEM/WORM, ServiceNow ve DR kanıtları; prototip lab bunların yerine geçmez. |

## Son Yedi İterasyonun Konsolide Çıktısı

Issue domaini PostgreSQL'e taşındı; seçici SQLite aktarımı tamamlandı ve issue
runtime fallback'i kaldırıldı. İnceleme, yeniden atama, korumalı çözüm, farklı
aktörle doğrulama ve kapatma UI/API akışları mevcuttur. Kapatma/yeniden açma
`36B5` kaydıyla teknik olarak doğrulanmıştır.

Execution PostgreSQL cutover (36E) tamamlanmıştır: `PostgreSQLExecutionRepository`
production composition root'unda, `SQLiteExecutionRepository` runtime export'tan
çıkarılmıştır. Scheduling/source-usage policy PostgreSQL kalıcılığı (36F) ile
güvenli rapor üretimi/indirme (36G) de tamamlanmıştır. Kalıcı iş kuyruğu çekirdeği
(36H1) `veri_kalitesi/jobs` modülünde eklenmiştir.

36H1 çekirdeğinin üstündeki iş yürütme yaşam döngüsü (36H2) bounded handler
wait, production reaper, atomik iptal ve controller entegrasyon kapsamıyla
tamamlanmış; reviewer `APPROVED` kararıyla `TechnicallyVerified` olmuştur.

Tamamlanmış eski backlog ayrıntıları [iterasyon arşivindedir](../archive/iterations/README.md).
