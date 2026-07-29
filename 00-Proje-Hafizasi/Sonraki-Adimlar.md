---
type: delivery-backlog
status: active
project: Veri Kalitesi İzleme ve Skorlama Sistemi
last_updated: 2026-07-29
---

# Sonraki Adımlar

Tek uygulanabilir sıradaki paket: [36H2 iş yürütme yaşam döngüsü doğrulaması](../NEXT_STEP.md)
— kod yüzeyi mevcut ama review açık correctness bulguları tespit etti; doğrulanana
kadar tamamlanmış sayılmaz.

## Aktif Backlog

| Sıra | İş | Durum | Tamamlanma ölçütü |
| --- | --- | --- | --- |
| 1 | İş yürütme yaşam döngüsü doğrulaması (36H2 açık bulguları) | `Next` / `VerificationPending` | Timeout/iptalde bounded handler wait, reaper'ın production worker'a bağlanması, atomik execution+job iptali ve eksik entegrasyon testleri [NEXT_STEP](../NEXT_STEP.md) çıkış kapıları geçilip reviewer `APPROVED` verince [36H2](../09-Iterasyonlar/Iterasyon-36H2-Is-Yurutme-Yasam-Dongusu.md) `TechnicallyVerified` olur. |
| 2 | 36H1 kalıcı iş kuyruğu çekirdeği | `Completed` / `TechnicallyVerified` | `veri_kalitesi/jobs` idempotent enqueue, deterministik lease claim, sahip-only heartbeat, süresi geçen claim toparlama, optimistic version concurrency ve `background_jobs` migration'ı iterasyon kaydındadır. |
| 3 | 36F scheduling/policy PostgreSQL kalıcılığı | `Completed` / `TechnicallyVerified` | PostgreSQL repository/migration mevcut; SQLite scheduling/policy repository'leri runtime export'tan çıkarılmıştır. |
| 4 | 36G güvenli rapor üretimi ve indirme | `Completed` / `TechnicallyVerified` | PDF/XLSX/CSV, zamanlanmış rapor, politika framework'ü, PostgreSQL repository, API ve frontend kanıtı kapanış kaydındadır. |
| 5 | Kurumsal production adaptörleri | `ExternalDependency` | IdP, PAM/secret manager, HA veri/session, broker, SIEM/WORM, ServiceNow ve DR kanıtları. |

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

36H1 çekirdeğinin üstündeki iş yürütme yaşam döngüsü (36H2) kod yüzeyi eklendi
ancak review açık correctness bulguları tespit etti (bounded handler wait, reaper
bağlama, atomik iptal, eksik entegrasyon testi). Sıradaki tek iş bu bulguları
kapatıp controller test kapılarını geçirmektir.

Tamamlanmış eski backlog ayrıntıları [iterasyon arşivindedir](../archive/iterations/README.md).
