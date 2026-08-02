---
type: delivery-backlog
status: active
project: Veri Kalitesi İzleme ve Skorlama Sistemi
last_updated: 2026-07-31
---

# Sonraki Adımlar

Son tamamlanan çalışma paketi [DQ-CAP-PROTOTYPE-05](../09-Iterasyonlar/DQ-CAP-PROTOTYPE-05-Bildirim-Kanal-Lab-Kapisi-Strateji-Motoru.md)
commit edilmiştir (6d79e06, 2026-07-31); birim testleri yeşildir ancak modüller
henüz composition'a bağlı değildir ve bağımsız review `CHANGES_REQUESTED`
durumundadır. Sıradaki `READY` teknik paket tanımlı değildir; production ve
ürünleştirme başlıkları `ExternalDependency` olarak açık kalır.

## Aktif Backlog

| Sıra | İş | Durum | Tamamlanma ölçütü |
| --- | --- | --- | --- |
| 0 | DQ-CAP-PROTOTYPE-05 bildirim kanal adaptörleri, lab güvenlik kapısı ve deterministik yürütme strateji motoru | `Committed` / review `CHANGES_REQUESTED` | Kanal adaptörleri, `LabAdapterGate` ve `strategy_engine` commit edildi (6d79e06); birim testleri yeşil. Modüller henüz composition'a bağlı değil; bağımsız review bağlantı, SLA/escalation, eşik ve PARTITION resume değişiklikleri istedi [kapanış kaydındadır](../09-Iterasyonlar/DQ-CAP-PROTOTYPE-05-Bildirim-Kanal-Lab-Kapisi-Strateji-Motoru.md); production/banka onayı değildir. |
| 1 | DQ-CAP-PROTOTYPE-04 sentetik lineage, sahiplik profili ve kaynaklı etki hipotezi | `Completed` / `PrototypeVerified` | Sürümlü `DataAssetGovernanceProfile` (fail-closed routing), OpenLineage uyumlu değişmez lineage snapshot'ı, hipotez olarak sunulan kök neden ve `Observed/Calculated/Estimated/Unknown` kaynaklı etki bileşenleri [kapanış kaydındadır](../09-Iterasyonlar/DQ-CAP-PROTOTYPE-04-Sentetik-Lineage-ve-Yonetisim-Profili.md); production/banka onayı değildir. |
| 2 | DQ-CAP-PROTOTYPE-03 skor katkısı/tarih/rol dashboardu | `Completed` / `PrototypeVerified` | Yeniden üretilebilir katkı grafiği, fail-closed karşılaştırma ve ortak yetkili API rol görünümü [kapanış kaydındadır](../09-Iterasyonlar/DQ-CAP-PROTOTYPE-03-Skor-Katki-ve-Rol-Dashboard.md); production/banka onayı değildir. |
| 3 | DQ-CAP-PROTOTYPE-02 kural IR/SHADOW/kanıt | `Completed` / `PrototypeVerified` | Ortak sürümlü IR, yedi kapsam, yaşam döngüsünden ayrı SHADOW ve veri-minimum kanıt [kapanış kaydındadır](../09-Iterasyonlar/DQ-CAP-PROTOTYPE-02-Kural-IR-Shadow-ve-Kanit.md); production/banka onayı değildir. |
| 4 | DQ-CAP-PROTOTYPE-01 deterministik profilleme/drift | `Completed` / `PrototypeVerified` | Politika kontrollü bounded CSV örneği, salt-okunur PostgreSQL source aggregate gelişmiş metrikleri, yedi drift ailesi, fail-closed politika/fingerprint yokluğu ve atomik karşılaştırma kalıcılığı [kapanış kaydındadır](../09-Iterasyonlar/DQ-CAP-PROTOTYPE-01-Deterministik-Profilleme-ve-Drift.md); production/banka onayı değildir. |
| 5 | ENTERPRISE-LAB-03 canlı Compose adaptör kabulü | `Completed` / `PrototypeVerified` | Sekiz healthy servis ve gerçek container ağında 14 olumlu/negatif adapter senaryosu [kapanış kaydında](../09-Iterasyonlar/ENTERPRISE-LAB-03-Canli-Compose-Uctan-Uca-Dogrulama.md); production/banka onayı değildir. |
| 6 | ENTERPRISE-LAB-02 uygulama adaptör bağlantıları | `Completed` / `PrototypeVerified` | Sentetik Keycloak, yerel secret manager, fake ServiceNow ve SIEM için fail-closed/veri-minimum/idempotent bağlantılar [kapanış kaydında](../09-Iterasyonlar/ENTERPRISE-LAB-02-Uygulama-Adaptor-Baglantilari.md); production/banka onayı değildir. |
| 7 | ENTERPRISE-LAB-01 prototip entegrasyon laboratuvarı | `Completed` / `PrototypeVerified` | Sentetik/non-production Compose, sekiz healthy servis, fail-closed ortam kapısı ve streaming PostgreSQL standby [kapanış kaydında](../archive/iterations/ENTERPRISE-LAB/ENTERPRISE-LAB-01-Prototip-Kurumsal-Entegrasyon-Laboratuvari.md); production/banka onayı değildir. |
| 8 | İş yürütme yaşam döngüsü (36H2) | `Completed` / `TechnicallyVerified` | Bounded timeout/iptal, production reaper, atomik execution+job iptali; controller `1172 passed` birim ve skip'siz `41 passed` PostgreSQL kapıları ile reviewer `APPROVED` kararı [36H2 kaydındadır](../archive/iterations/36/Iterasyon-36H2-Is-Yurutme-Yasam-Dongusu.md). |
| 9 | 36H1 kalıcı iş kuyruğu çekirdeği | `Completed` / `TechnicallyVerified` | `veri_kalitesi/jobs` idempotent enqueue, deterministik lease claim, sahip-only heartbeat, süresi geçen claim toparlama, optimistic version concurrency ve `background_jobs` migration'ı iterasyon kaydındadır. |
| 10 | DQ profilleme production ürünleştirme | `ExternalDependency` | Onaylı politika/kalibrasyon, production envanteri ölçek/yük kanıtı, PostgreSQL composition/operasyon, ekran ve kurumsal gözlemlenebilirlik; prototip bunların yerine geçmez. |
| 11 | Kurumsal production adaptörleri | `ExternalDependency` | Gerçek IdP, PAM/secret manager, HA veri/session, broker, SIEM/WORM, ServiceNow ve DR kanıtları; prototip lab bunların yerine geçmez. |

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

DQ-CAP-PROTOTYPE-03 mevcut skor geçmişi ve dashboardu yeniden üretilebilir
katkı grafiği, fail-closed dönem karşılaştırması ve rol görünümüyle genişletmiştir.

Tamamlanmış eski backlog ayrıntıları [iterasyon arşivindedir](../archive/iterations/README.md).
