---
type: delivery-backlog
status: active
project: Veri Kalitesi İzleme ve Skorlama Sistemi
last_updated: 2026-07-29
---

# Sonraki Adımlar

Bağımlılıkları tamamlanmış `Next`/`READY` teknik paket yoktur.
[ENTERPRISE-LAB-03](../NEXT_STEP.md) sentetik/non-production canlı Compose
adaptör kabul kapısı olarak `PrototypeVerified` kapanmıştır. Kalan production
başlıkları dış bağımlılıklardır.

## Aktif Backlog

| Sıra | İş | Durum | Tamamlanma ölçütü |
| --- | --- | --- | --- |
| 1 | ENTERPRISE-LAB-03 canlı Compose adaptör kabulü | `Completed` / `PrototypeVerified` | Sekiz healthy servis ve gerçek container ağında 14 olumlu/negatif adapter senaryosu [kapanış kaydında](../09-Iterasyonlar/ENTERPRISE-LAB-03-Canli-Compose-Uctan-Uca-Dogrulama.md); production/banka onayı değildir. |
| 2 | ENTERPRISE-LAB-02 uygulama adaptör bağlantıları | `Completed` / `PrototypeVerified` | Sentetik Keycloak, yerel secret manager, fake ServiceNow ve SIEM için fail-closed/veri-minimum/idempotent bağlantılar [kapanış kaydında](../09-Iterasyonlar/ENTERPRISE-LAB-02-Uygulama-Adaptor-Baglantilari.md); production/banka onayı değildir. |
| 3 | ENTERPRISE-LAB-01 prototip entegrasyon laboratuvarı | `Completed` / `PrototypeVerified` | Sentetik/non-production Compose, sekiz healthy servis, fail-closed ortam kapısı ve streaming PostgreSQL standby [kapanış kaydında](../09-Iterasyonlar/ENTERPRISE-LAB-01-Prototip-Kurumsal-Entegrasyon-Laboratuvari.md); production/banka onayı değildir. |
| 4 | İş yürütme yaşam döngüsü (36H2) | `Completed` / `TechnicallyVerified` | Bounded timeout/iptal, production reaper, atomik execution+job iptali; controller `1172 passed` birim ve skip'siz `41 passed` PostgreSQL kapıları ile reviewer `APPROVED` kararı [36H2 kaydındadır](../09-Iterasyonlar/Iterasyon-36H2-Is-Yurutme-Yasam-Dongusu.md). |
| 5 | 36H1 kalıcı iş kuyruğu çekirdeği | `Completed` / `TechnicallyVerified` | `veri_kalitesi/jobs` idempotent enqueue, deterministik lease claim, sahip-only heartbeat, süresi geçen claim toparlama, optimistic version concurrency ve `background_jobs` migration'ı iterasyon kaydındadır. |
| 6 | 36F scheduling/policy PostgreSQL kalıcılığı | `Completed` / `TechnicallyVerified` | PostgreSQL repository/migration mevcut; SQLite scheduling/policy repository'leri runtime export'tan çıkarılmıştır. |
| 7 | Kurumsal production adaptörleri | `ExternalDependency` | Gerçek IdP, PAM/secret manager, HA veri/session, broker, SIEM/WORM, ServiceNow ve DR kanıtları; prototip lab bunların yerine geçmez. |

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
