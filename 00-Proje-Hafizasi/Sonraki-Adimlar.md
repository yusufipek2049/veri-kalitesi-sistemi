---
type: delivery-backlog
status: active
project: Veri Kalitesi İzleme ve Skorlama Sistemi
last_updated: 2026-08-03
---

# Sonraki Adımlar

Sıradaki `READY` teknik paket [MAINT-04](../NEXT_STEP.md)'tür. MAINT-03 kapanmıştır;
MAINT-02 kısmen tamamlanmıştır (eşik gate'den kaldırıldı, composition köküne taşındı;
kaynaksız değer hâlâ koddadır, sürümlü politikaya bağlanması MAINT-04 ile takip edilir);
kalıcı iş kuyruğu entegrasyon kapısı ilk kez skip'siz geçmiştir (32 test). Ürün yeteneği
kapsamındaki paketler kalan bakım işi (MAINT-04) kapanana kadar başlatılmaz; production ve
ürünleştirme başlıkları `ExternalDependency` olarak açık kalır.

Sürüm kontrolü tarafında ayrı bir açık madde vardır: `main` dalı 2026-07-27'den
beri hareketsizdir ve çalışma dalında 26 commit birikmiştir. Bu depoda hiç merge
yapılmamıştır. Merge işlemi ajan görevi değildir; operatör kararıyla yürütülür.

## Aktif Backlog

| Sıra | İş | Durum | Tamamlanma ölçütü |
| --- | --- | --- | --- |
| 0 | MAINT-04 lab kanıt ömrü eşiğinin sürümlü politikaya/lab yapılandırmasına bağlanması | `READY` | `adapters.py` içindeki `max_evidence_age_seconds=3600` değeri kanonik kaynaktan yoksundur; sürümlü politika veya lab yapılandırmasına bağlanarak boşluk kapatılır. MAINT-02'nin devamıdır. |
| 1 | MAINT-03 kabul kriteri şablonuna entegrasyon maddesi | `Completed` | Görev şablonuna (`tools/agent-loop/lib.sh`) `AC-08` kabul kriteri eklendi: "Teslim edilen modül composition kökünde kayıtlı olmalı ve en az bir üretim çağrı yolundan erişilebilir olmalıdır; yalnız testlerden çağrılan modül tamamlanmış sayılmaz." Aynı teslim standardı ADR-021 olarak [Mimari Kararlar](../02-Mimari/Mimari-Kararlar.md) içinde kayıtlıdır. Standart geriye dönük kapanmış paketleri yeniden açmaz. |
| 2 | MAINT-01 test bağımlılıklarının beyanı ve sürüm pinleri | `Completed` | `pydantic==2.12.5` ve `starlette==1.0.0` çalışma zamanı bağımlılığı olarak pinlendi; `httpx`, `pytest`, `python-dotenv` proje manifestosunda test grubu olarak beyan edildi; iş akışı manifestodan okuyor ve ön uç çalışma ortamı yerelde doğrulanmış sürüme çekildi. Sürekli entegrasyon toplama aşaması geçti. |
| 3 | MAINT-02 kaynaksız eşiklerin kaldırılması | `Partially completed` | `lab_gate.py` içindeki kanıt tazelik sabiti kaldırıldı ve `max_evidence_age_seconds` zorunlu parametre olarak composition köküne taşındı; `channel_adapters.py` tekilleştirme penceresi ve `strategy_engine.py` zaman aşımı alanları varsayılansız zorunlu parametreye çevrildi. Kaynaksız değer (3600) hâlâ `adapters.py` composition kökünde koddadır ve sürümlü politikaya/lab yapılandırmasına bağlanması MAINT-04 ile açık iş olarak takip edilir. [Ürün Yetenekleri Prototip Kararları](Karar-Kayitlari/Urun-Yetenekleri-Prototip-Kararlari.md) `DQ-CAP-009` gereği bu değerler artık yalnız sürümlü politikadan gelir. |
| 4 | Kalıcı iş kuyruğu entegrasyon kapısı | `Completed` | `test_postgresql_job_queue.py` içindeki `alembic_up_to_date` fixture'ı, dönüş değeri olmayan bir Alembic çağrısını doğrulama olarak kullandığı için 30 testi her ortamda hataya düşürüyordu. Bozuk doğrulama bloğu kaldırıldı; dosyadaki **32 testin tamamı PostgreSQL ile skip'siz geçer** (ilk kez doğrulanmıştır). |
| 5 | DQ-CAP-PROTOTYPE-05 bildirim kanal adaptörleri, lab güvenlik kapısı ve deterministik yürütme strateji motoru | `Committed` / review `CHANGES_REQUESTED` | Kanal adaptörleri, `LabAdapterGate` ve `strategy_engine` commit edildi (6d79e06); birim testleri yeşil. Modüller henüz composition'a bağlı değil; bağımsız review bağlantı, SLA/escalation, eşik ve PARTITION resume değişiklikleri istedi [kapanış kaydındadır](../09-Iterasyonlar/DQ-CAP-PROTOTYPE-05-Bildirim-Kanal-Lab-Kapisi-Strateji-Motoru.md); production/banka onayı değildir. |
| 6 | DQ-CAP-PROTOTYPE-04 sentetik lineage, sahiplik profili ve kaynaklı etki hipotezi | `Completed` / `PrototypeVerified` | Sürümlü `DataAssetGovernanceProfile` (fail-closed routing), OpenLineage uyumlu değişmez lineage snapshot'ı, hipotez olarak sunulan kök neden ve `Observed/Calculated/Estimated/Unknown` kaynaklı etki bileşenleri [kapanış kaydındadır](../09-Iterasyonlar/DQ-CAP-PROTOTYPE-04-Sentetik-Lineage-ve-Yonetisim-Profili.md); production/banka onayı değildir. |
| 7 | DQ-CAP-PROTOTYPE-03 skor katkısı/tarih/rol dashboardu | `Completed` / `PrototypeVerified` | Yeniden üretilebilir katkı grafiği, fail-closed karşılaştırma ve ortak yetkili API rol görünümü [kapanış kaydındadır](../09-Iterasyonlar/DQ-CAP-PROTOTYPE-03-Skor-Katki-ve-Rol-Dashboard.md); production/banka onayı değildir. |
| 8 | DQ-CAP-PROTOTYPE-02 kural IR/SHADOW/kanıt | `Completed` / `PrototypeVerified` | Ortak sürümlü IR, yedi kapsam, yaşam döngüsünden ayrı SHADOW ve veri-minimum kanıt [kapanış kaydındadır](../09-Iterasyonlar/DQ-CAP-PROTOTYPE-02-Kural-IR-Shadow-ve-Kanit.md); production/banka onayı değildir. |
| 9 | DQ-CAP-PROTOTYPE-01 deterministik profilleme/drift | `Completed` / `PrototypeVerified` | Politika kontrollü bounded CSV örneği, salt-okunur PostgreSQL source aggregate gelişmiş metrikleri, yedi drift ailesi, fail-closed politika/fingerprint yokluğu ve atomik karşılaştırma kalıcılığı [kapanış kaydındadır](../09-Iterasyonlar/DQ-CAP-PROTOTYPE-01-Deterministik-Profilleme-ve-Drift.md); production/banka onayı değildir. |
| 10 | ENTERPRISE-LAB-03 canlı Compose adaptör kabulü | `Completed` / `PrototypeVerified` | Sekiz healthy servis ve gerçek container ağında 14 olumlu/negatif adapter senaryosu [kapanış kaydında](../09-Iterasyonlar/ENTERPRISE-LAB-03-Canli-Compose-Uctan-Uca-Dogrulama.md); production/banka onayı değildir. |
| 11 | ENTERPRISE-LAB-02 uygulama adaptör bağlantıları | `Completed` / `PrototypeVerified` | Sentetik Keycloak, yerel secret manager, fake ServiceNow ve SIEM için fail-closed/veri-minimum/idempotent bağlantılar [kapanış kaydında](../09-Iterasyonlar/ENTERPRISE-LAB-02-Uygulama-Adaptor-Baglantilari.md); production/banka onayı değildir. |
| 12 | ENTERPRISE-LAB-01 prototip entegrasyon laboratuvarı | `Completed` / `PrototypeVerified` | Sentetik/non-production Compose, sekiz healthy servis, fail-closed ortam kapısı ve streaming PostgreSQL standby [kapanış kaydında](../archive/iterations/ENTERPRISE-LAB/ENTERPRISE-LAB-01-Prototip-Kurumsal-Entegrasyon-Laboratuvari.md); production/banka onayı değildir. |
| 13 | İş yürütme yaşam döngüsü (36H2) | `Completed` / `TechnicallyVerified` | Bounded timeout/iptal, production reaper, atomik execution+job iptali; controller `1172 passed` birim ve skip'siz `41 passed` PostgreSQL kapıları ile reviewer `APPROVED` kararı [36H2 kaydındadır](../archive/iterations/36/Iterasyon-36H2-Is-Yurutme-Yasam-Dongusu.md). |
| 14 | 36H1 kalıcı iş kuyruğu çekirdeği | `Completed` / `TechnicallyVerified` | `veri_kalitesi/jobs` idempotent enqueue, deterministik lease claim, sahip-only heartbeat, süresi geçen claim toparlama, optimistic version concurrency ve `background_jobs` migration'ı iterasyon kaydındadır. |
| 15 | DQ profilleme production ürünleştirme | `ExternalDependency` | Onaylı politika/kalibrasyon, production envanteri ölçek/yük kanıtı, PostgreSQL composition/operasyon, ekran ve kurumsal gözlemlenebilirlik; prototip bunların yerine geçmez. |
| 16 | Kurumsal production adaptörleri | `ExternalDependency` | Gerçek IdP, PAM/secret manager, HA veri/session, broker, SIEM/WORM, ServiceNow ve DR kanıtları; prototip lab bunların yerine geçmez. |

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
