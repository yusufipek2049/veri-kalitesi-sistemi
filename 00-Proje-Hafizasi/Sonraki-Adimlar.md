---
type: delivery-backlog
status: active
project: Veri Kalitesi İzleme ve Skorlama Sistemi
last_updated: 2026-07-30
---

# Sonraki Adımlar

Bağımlılıkları tamamlanmış `Next`/`READY` teknik paket yoktur.
[DQ-CAP-PROTOTYPE-02](../NEXT_STEP.md) sentetik/yerel ortak kural IR, SHADOW
yürütme ve veri-minimum kanıt çekirdeği olarak `PrototypeVerified` kapanmıştır.
Kalan production ve ürünleştirme başlıkları açık kalır.

## Aktif Backlog

| Sıra | İş | Durum | Tamamlanma ölçütü |
| --- | --- | --- | --- |
| 1 | DQ-CAP-PROTOTYPE-02 kural IR/SHADOW/kanıt | `Completed` / `PrototypeVerified` | Ortak sürümlü IR, yedi kapsam, yaşam döngüsünden ayrı SHADOW ve veri-minimum kanıt [kapanış kaydındadır](../09-Iterasyonlar/DQ-CAP-PROTOTYPE-02-Kural-IR-Shadow-ve-Kanit.md); production/banka onayı değildir. |
| 2 | DQ-CAP-PROTOTYPE-01 deterministik profilleme/drift | `Completed` / `PrototypeVerified` | Politika kontrollü bounded CSV örneği, salt-okunur PostgreSQL source aggregate gelişmiş metrikleri, yedi drift ailesi, fail-closed politika/fingerprint yokluğu ve atomik karşılaştırma kalıcılığı [kapanış kaydındadır](../09-Iterasyonlar/DQ-CAP-PROTOTYPE-01-Deterministik-Profilleme-ve-Drift.md); production/banka onayı değildir. |
| 3 | ENTERPRISE-LAB-03 canlı Compose adaptör kabulü | `Completed` / `PrototypeVerified` | Sekiz healthy servis ve gerçek container ağında 14 olumlu/negatif adapter senaryosu [kapanış kaydında](../09-Iterasyonlar/ENTERPRISE-LAB-03-Canli-Compose-Uctan-Uca-Dogrulama.md); production/banka onayı değildir. |
| 4 | ENTERPRISE-LAB-02 uygulama adaptör bağlantıları | `Completed` / `PrototypeVerified` | Sentetik Keycloak, yerel secret manager, fake ServiceNow ve SIEM için fail-closed/veri-minimum/idempotent bağlantılar [kapanış kaydında](../09-Iterasyonlar/ENTERPRISE-LAB-02-Uygulama-Adaptor-Baglantilari.md); production/banka onayı değildir. |
| 5 | ENTERPRISE-LAB-01 prototip entegrasyon laboratuvarı | `Completed` / `PrototypeVerified` | Sentetik/non-production Compose, sekiz healthy servis, fail-closed ortam kapısı ve streaming PostgreSQL standby [kapanış kaydında](../09-Iterasyonlar/ENTERPRISE-LAB-01-Prototip-Kurumsal-Entegrasyon-Laboratuvari.md); production/banka onayı değildir. |
| 6 | İş yürütme yaşam döngüsü (36H2) | `Completed` / `TechnicallyVerified` | Bounded timeout/iptal, production reaper, atomik execution+job iptali; controller `1172 passed` birim ve skip'siz `41 passed` PostgreSQL kapıları ile reviewer `APPROVED` kararı [36H2 kaydındadır](../09-Iterasyonlar/Iterasyon-36H2-Is-Yurutme-Yasam-Dongusu.md). |
| 7 | 36H1 kalıcı iş kuyruğu çekirdeği | `Completed` / `TechnicallyVerified` | `veri_kalitesi/jobs` idempotent enqueue, deterministik lease claim, sahip-only heartbeat, süresi geçen claim toparlama, optimistic version concurrency ve `background_jobs` migration'ı iterasyon kaydındadır. |
| 8 | DQ profilleme production ürünleştirme | `ExternalDependency` | Onaylı politika/kalibrasyon, production envanteri ölçek/yük kanıtı, PostgreSQL composition/operasyon, ekran ve kurumsal gözlemlenebilirlik; prototip bunların yerine geçmez. |
| 9 | Kurumsal production adaptörleri | `ExternalDependency` | Gerçek IdP, PAM/secret manager, HA veri/session, broker, SIEM/WORM, ServiceNow ve DR kanıtları; prototip lab bunların yerine geçmez. |

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

DQ-CAP-PROTOTYPE-02 mevcut kural ve çalıştırma çekirdeğini ortak sürümlü IR,
SHADOW downstream dışlaması ve veri-minimum kanıtla genişletmiştir.

Tamamlanmış eski backlog ayrıntıları [iterasyon arşivindedir](../archive/iterations/README.md).
