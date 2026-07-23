---
type: project-memory
status: open
project: Veri Kalitesi İzleme ve Skorlama Sistemi
last_updated: 2026-07-22
tags:
  - proje
  - acik-konu
  - uygulama-bagimliligi
---

# Açık Konular

Ayrıntılı ve bağlayıcı liste: [SRS — Açık Konular ve Varsayımlar](../01-SRS/15-Acik-Konular.md).

`KararAlındı` durumundaki teknik yönler [Alınan Kararlar](Alinan-Kararlar.md)
belgesindedir. Bu dosya yalnız `Açık` veya kurumsal/banka incelemesi gerektiren
belirsizlikleri ve
kararın uygulanmasını engelleyen dış bağımlılıkları tutar.

## Geliştirmeyi En Çok Etkileyen Açık Konular

1. PostgreSQL-only uygulama kalıcılığı, `psycopg 3`, SQLAlchemy 2 ve Alembic
   karara bağlanmıştır. Mevcut SQLite repository'lerin bağımlılık sıralı
   migration'ı, PostgreSQL test izolasyonu ve SQLite fallback'lerin kaldırılması
   henüz uygulanmamıştır.
2. Worker/kota/pencere/CPU/IO/timeout/rate değerleri aktif sürümlü kaynak politikasından çözülecektir; kapasite testinden üretilmiş üretim politika kaydı ve CPU/IO/rate ölçüm adaptörü henüz yoktur.
3. Kurumsal secret manager/PAM kullanımı karara bağlanmıştır; seçilen kurumsal hizmetin servis/workload identity eşlemesi ve gerçek adaptörü beklenmektedir.
4. Kurumsal IdP üzerinden OIDC veya SAML, MFA, PAM ve çift onaylı break-glass karara bağlanmıştır; endpoint, grup-rol-scope değerleri ve üretim rol eşlemeleri beklenmektedir.
5. `AC-008` için veri sahibi onayı, anonimleştirilmiş üretim örneği, yeniden kimliklendirme risk değerlendirmesi ve test ortamı henüz hazırlanmamıştır.
6. ServiceNow gerçek tablo/alan/durum eşlemesi, servis hesabı, endpoint/TLS ve veri aktarım onayı açıktır.
7. Teknik saklama matrisi ile normal/kritik RPO/RTO hedefleri karara bağlanmıştır; mevzuat eşlemesi, banka incelemesi, yedek şifreleme ve restore sıklığı kanıtı beklenmektedir.
8. Pilot VM/konteyner; üretimde kurumsal OpenShift/Kubernetes eşdeğeri, yüksek erişilebilir PostgreSQL ve kurumsal broker/RabbitMQ fallback'i karara bağlanmıştır. Kalıcı dosya deposunun kurum hizmet eşlemesi ve altyapı kurulumu beklenmektedir.
9. PostgreSQL transactional outbox ve ayrı publisher worker karara bağlanmıştır; kapasite testiyle üretilmiş alarm/eşik politikası ve üretim işletim kanıtı beklenmektedir.
10. Kısmi resmî skorun koşulları sürümlü/onaylı dataset politikasından çözülecektir; banka onaylı üretim politika kayıtlarının oluşturulması beklenmektedir.
11. Dashboard güvenilir `ActorContext` ve `AuthorizationService` sınırına taşındı; diğer servislerdeki serbest `actor_id` kullanımı ile context issuer'ın gerçek LDAP/session adaptörüne bağlanması İterasyon 20 ve sonraki modül geçişlerini gerektirir.
13. Yerel `data_quality` PostgreSQL veritabanı mevcuttur. Kurum içi kalıcı
    entegrasyon/üretim veritabanı erişimi, yüksek erişilebilir küme ve seçilen
    sürücü/havuz yaklaşımının kurum standardı onayı beklenmektedir.
15. `AC-008` için veri sahibi onaylı, anonimleştirilmiş üretim örneği, yeniden kimliklendirme risk değerlendirmesi ve donanım gözlemli performans testi henüz hazırlanmadı; birim testleri yalnız SAMPLE sözleşmesini doğruluyor.
16. `RuleTestExecutor` için PostgreSQL/CSV kaynak adaptörleri, sorgu maliyet tahmini ve regex çalışma timeoutu henüz uygulanmadı; mevcut iterasyon güvenli domain sözleşmesini, şablon planlarını ve test geçmişini doğruluyor.
17. Kurumsal broker veya RabbitMQ fallback'i ve PostgreSQL transactional outbox
    karara bağlandı; çoklu worker lease/heartbeat, kayıp worker recovery ve
    kapasite profili henüz uygulanmadı. Yerel prototip SQLite üzerinde süreç içi
    kilitle kalıcı kuyruk davranışını doğruluyor.
18. Bağlantı, sorgu ve toplam timeout değerleri worker yürütücü sözleşmesinde ayrı taşınıyor ve iptal adaptörü tanımlandı; gerçek PostgreSQL/CSV adaptörlerinde sorgu iptali ile duvar saati zorlaması henüz uygulanmadı.
21. Yeni `SOURCE_EQUAL_DATASET_QUALITY_V2` kaynak kalite agregasyonu dataset
    kritikliğini kalite formülünden çıkardı ve ayrı profil kanıtı taşır. Tarihsel
    `SOURCE_WEIGHTED_V1` kayıtlarının yeni modelle replay/backfill ilişkisi,
    trend sürüm sınırı ve ayrı risk/güven/yeterlilik/kullanım sonuçları henüz
    uygulanmamıştır.
22. Kurum skorunda kaynaklar arası ham kalite agregasyon politikası onaylanmadı; mevcut `ENTERPRISE` formülü kaynakları eşit ağırlıklandırıyor. Yeni politika kritiklik ve veri riskini kalite skoruna karıştırmamalı, ayrı sürümlenmelidir.
23. Eski SQLite `audit_records` için salt okunur envanter ve idempotent merkezi aktarım sözleşmesi sentetik verilerle teknik olarak doğrulandı. Gerçek ortam envanteri/koşusu, yedek ve geri dönüş planı, değişiklik penceresi ve operasyon onayı henüz tamamlanmadı.
24. `DURABLE_BUFFER` sözleşmesi ve hata yolu test edildi; üretim kalıcı tampon teknolojisi, sahipliği, şifrelemesi, yeniden oynatma ve idempotency davranışı henüz uygulanmadı.
25. SQLite outbox için üretim publisher worker'ı, claim/eşzamanlılık, retry/backoff, alarm metrikleri, kapasite sınırı ve saklama/temizleme politikası henüz uygulanmadı.
26. `CLASSIFICATION_POLICY_V1`, fail-closed profil politikası, sürümlü `BFR-DATA-004` işleme envanteri ve kişisel/özel nitelikli kişisel alanlar için salt okunur tamlık kontrolü uygulandı. Teknik kodların banka sözlüğüyle eşlemesi ve referansların kurumsal kayıtlarla doğrulanması açık kalır.
27. Gerçek banka iş günü/tatil kaynağı, onay süre aşımı worker işletimi,
    hazırlayanı bilinmeyen legacy kritik sürümlerin geçiş prosedürü, kaynak
    kritiklik sözlüğü, üretim migration/çoklu instance eşzamanlılığı, çalışan
    işin tamamlanması/iptali politikası, operasyon bildirimi ve banka onaylı
    maker/checker/deactivator/worker rol kodları açık kalır.
28. Başarısız giriş sınırlandırması opak kullanıcı/istemci anahtarlarıyla teknik olarak uygulandı. Üretim anahtar türetme/rotasyon yöntemi, secret manager bağlantısı, güvenilir istemci referansının proxy/ağ sınırı, paylaşımlı depo ürünü ve LDAP ile uyumlu nihai eşik/pencere/süre onayı açık kalır.
30. Dashboard trendi güvenilir scope ile sabit son 30 UTC gün için uygulandı;
    21B yerel/test FastAPI özetini ve bağlı grafik/tablo görünümünü, 20E ise
    banka onaylı BFF cookie/CSRF HTTP sınırını doğruladı. Serbest tarih
    aralığı/periyot seçimi, operasyon listeleri, gerçek OIDC/SAML callback ve
    state/nonce, banka grup-rol eşlemesi, HA session store ve üretim şifreleme
    bağlantısı açık kalır.
31. Sistem içi bildirim domain yaşam döngüsü sabit veri-minimum şablon ve güvenilir resolver protokolüyle uygulandı. Gerçek sahiplik/fallback grup kaynağı, şablon yönetimi, susturma/eskalasyon politikası, asenkron retry/DLQ, saklama-imha ve HTTP/UI yüzeyi açık kalır.
32. Otomatik issue oluşturma, atama/inceleme, korunan çözüm, başarısız/teknik doğrulama, farklı aktörle başarılı `VERIFIED`, doğrulama bağlı `CLOSED`, aynı başarısızlıkla yeniden açma ve yeni kalite başarısızlığını append-only ilişkilendirme uygulandı. Gerçek assignment/kullanıcı dizini, çözüm koruma, doğrulama ve ilişki resolver adaptörleri; banka onaylı çözen/doğrulayan rol eşlemesi, bildirim retry/DLQ, saklama-imha ve ServiceNow açık kalır.
34. ServiceNow ticket oluşturma allowlist projeksiyon, güvenilir servis context'i ve idempotent fake adaptörle teknik olarak doğrulandı. Gerçek endpoint/credential, banka alan-durum eşlemesi, servis hesabı yetkilendirmesi, timeout/retry/backoff, durum senkronizasyonu ve `OPEN-BNK-009` onayı açık kalır.
36. ServiceNow senkron geçici/429 retry politikası toplam en fazla üç deneme, üstel backoff ve `Retry-After` ile teknik olarak doğrulandı. Gerçek timeout/ağ adaptörü ve operasyon alarmı açık kalır.
37. ServiceNow kalıcı retry işi, tek worker claim'i, due-time yeniden planlama, dead-letter ve auditli yeniden kuyruğa alma SQLite prototipinde doğrulandı. Gerçek broker, çoklu süreç lease/heartbeat ve kayıp worker recovery, kuyruk kapasitesi/saklama ve operasyon alarmı açık kalır.
38. ServiceNow circuit breaker beş ardışık geçici hata, beş dakikalık açık durum ve tek half-open probe ile SQLite prototipinde doğrulandı. Dağıtık/çoklu instance state deposu, üretim eşik onayı, metrik/alarm sahipliği ve gerçek ServiceNow endpoint/credential kararı açık kalır; `OPEN-BNK-009` geçerlidir.
39. Audit inceleme sorgusu ve `/audit` ekranı güvenilir `AUDIT_VIEWER`
    context'i, 31 günlük senkron pencere, snapshot cursor, parametreli filtre,
    bütünlük sonucu, veri-minimum DTO ve auditli görüntülemeyle doğrulandı.
    Banka onaylı auditor rol/grup eşlemesi, istemci bilgisi alanı, çevrimiçi
    saklama penceresini aşan asenkron arşiv raporu ve hassas dışa aktarma
    politikası açık kalır; `OPEN-BNK-002`, `OPEN-BNK-008` ve `OPEN-BNK-014`
    geçerlidir.
40. Rapor önizleme güvenilir rol/source kapsamı, 31 günlük servis sınırı, sabit 30 günlük HTTP/UI penceresi, 500 source sınırı, salt okunur latest-score sorgusu, veri-minimum audit ve toplulaştırılmış ekranla doğrulandı. PDF/XLSX/CSV, Report yaşam döngüsü, asenkron üretim, indirme, DLP/watermark, dosya saklama/imha ve banka onaylı dışa aktarma/maker-checker politikası açık kalır; `OPEN-BNK-002`, `OPEN-BNK-007`, `OPEN-BNK-008` ve `OPEN-BNK-014` geçerlidir.
41. Güvenlik olayı, kişisel veri ihlali şüphesi, 72 saat hedefi, veri işleyen bildirim kanıt referansı ve farklı aktörle insan kararı teknik olarak uygulandı. Banka olay/rol sözlüğü, gerçek SIEM/SOC akışı, hukuk/uyum karar içeriği, dış bildirim, saklama/imha ve tatbikat kanıtı açık kalır; `OPEN-BNK-001`, `OPEN-BNK-002`, `OPEN-BNK-004`, `OPEN-BNK-008` ve `OPEN-BNK-010` geçerlidir.
42. İhlal zaman çizelgesi güvenilir privacy rolü ve incident scope'u ile veri-minimum görüntülenebilir; 72 saat durumu ve görüntüleme auditi teknik olarak doğrulandı. Listeleme/arama, HTTP/UI, kanıt içeriğine ayrı erişim, gerçek SIEM/SOC, banka rol eşlemesi ve saklama/imha açık kalır; `OPEN-BNK-002`, `OPEN-BNK-008` ve `OPEN-BNK-010` geçerlidir.
43. Yerel `28A-v1` secret taraması teknik olarak doğrulandı. Kurumsal scanner/CI-CD ürünü, secret bulgu eşiği, istisna ve risk kabulü, geçmiş commit taraması, pipeline zorlaması ve banka bilgi güvenliği onayı açık kalır.
44. `28B` doğrudan bağımlılık envanteri ve sürüm bağlı CycloneDX 1.5 SBOM'u teknik olarak doğrulandı. Transitive bağımlılık/lock, artifact hash'i, lisans, zafiyet veritabanı, harici scanner/SBOM ürünü, CI/CD zorlaması ve banka eşik/istisna onayı açık kalır.
45. `28C-v1` veri-minimum SAST bulgu zarfı, tamamlanmamış tarama teknik hata yolu ve kritik bulguda fail-closed sürüm kapısı teknik olarak doğrulandı. Gerçek SAST scanner/repository taraması, CI/CD zorlaması, kritik olmayan banka eşikleri, istisna/risk kabulü, release maker-checker, DAST ve pentest açık kalır.
46. Frontend görsel tasarım tabanı ile React, TypeScript, Vite, MUI, ECharts,
    Storybook ve Playwright paketleri kuruldu; sentetik dashboard, açık/koyu
    tema, tema tercihi, referansla uyumlu navigasyon grupları ve hizalı Lucide
    ikonları teknik olarak doğrulandı. `FE-DEC-001`–`FE-DEC-004` ile ikon,
    routing, tema tercihi ve dashboard KPI zaman/snapshot kararları kesinleşti.
    35A ile `react-router-dom` route kabuğu ve veri kaynağı ekranı; 35B ile
    dataset scope filtreli, veri-minimum kural API'si ve salt okunur Kurallar
    ekranı; 35C ile kaynak scope filtreli, veri-minimum çalışma API'si ve salt
    okunur Çalıştırmalar ekranı; 35D ile kaynak/dataset scope filtreli,
    veri-minimum sorun API'si ve salt okunur Sorunlar ekranı; 35E ile rol/source
    kapsamlı, toplulaştırılmış rapor önizleme API'si ve salt okunur Raporlar
    ekranı; 35F ile `AUDIT_VIEWER` rol kontrollü, bütünlük gösterimli ve
    snapshot sayfalı Denetim ekranı teknik olarak doğrulandı. Kurumsal font, onaylı görsel
    baseline/diff eşiği, performans bütçesi ve banka marka onayı henüz
    tamamlanmamıştır. 21B yerel/test API bağlantısını eklemiştir; üretim dashboard
    ve alan ekranları gerçek IdP bağlantısı, yüksek
    erişilebilir session store, PostgreSQL repository bağlantıları ve bankacılık
    geçiş kapısına bağlıdır.
47. `28D-v1` doğrudan bağımlılık zafiyet bulgu zarfı, tamamlanmamış tarama teknik
    hata yolu, tam envanter eşleşmesi ve kritik bulguda fail-closed sürüm kapısı
    teknik olarak doğrulandı. Gerçek zafiyet veritabanı/ağ scanner'ı, transitive
    lock/artifact doğrulaması, kritik olmayan banka eşikleri, istisna/risk kabulü,
    CI/CD, release maker-checker, DAST ve pentest açık kalır.
48. `28E-v1` veri-minimum sızma testi bulgu zarfı, değişmez tekrar test yaşam
    döngüsü, teknik hata ayrımı ve kapanmamış kritik bulguda fail-closed kanıt
    kapısı teknik olarak doğrulandı. Gerçek pentest hizmeti, banka kapsamı/sıklığı,
    bağımsızlık şartı, kimlik ve kanıt resolver'ları, kalıcı depo, CI/CD, release
    maker-checker ve banka onayı açık kalır.
49. `29A-v1` teknik kanıt kataloğu/manifesti 15 kontrolü deterministik olarak
    raporladı: 13 `Partial`, 2 `Missing`, 14 açık engelli ve 15
    `ComplianceReviewRequired`. `CTRL-BDDK-BCP-001` ve `CTRL-KVKK-XFER-001`
    için teknik kanıt yoktur. İmzalama/WORM, kurumsal kanıt
    deposu, CI/CD zorlaması, banka karar referansı doğrulaması ve eksik
    kontrollerin uygulanması açık kalır.
50. `29B-v1` saklanan manifest drift kapısı byte düzeyinde `MATCH/DRIFT` ve ayrı
    doğrulama/teknik hata yollarıyla teknik olarak doğrulandı. Gerçek CI/CD ürünü
    ve zorlaması, artifact imzası/değişmez kurumsal depo, istisna/risk kabulü,
    release maker-checker ve banka kabul iş akışı açık kalır.
51. `29C-v1` altı mevcut yerel güvenli SDLC kontrolünü veri-minimum, fail-closed
    preflight komutunda birleştirdi. Gerçek scanner ve pentest çalıştırıcıları,
    kurumsal CI/CD ürünü/zorlaması, artifact imzası/değişmez depo, banka eşikleri,
    istisna/risk kabulü ve release maker-checker açık kalır; 29D `OPEN-BNK-012`
    ve bilgi güvenliği/iç kontrol kararlarını bekler.
52. `25A-v1` altı zaman bazlı saklama sınıfını takvimsel, sürümlü ve
    `ComplianceReviewRequired` katalogla salt okunur değerlendirir; aktif legal
    hold ve resolver arızası imha uygunluğunu fail-closed engeller. Hukuk/KVKK
    komitesi/iç denetim onayı, gerçek kayıt türü eşlemesi, idempotent imha/audit,
    arşiv geri çağırma ve yedek re-delete açık kalır.
53. `25B-v1` append-only legal hold oluşturma/serbest bırakma geçmişini, farklı
    yetkili aktörü, rol/kapsam kontrolünü ve atomik veri-minimum audit outbox'ı
    teknik olarak doğruladı. Banka LDAP rol/reason code eşlemesi, üretim
    PostgreSQL/WORM yetkileri, çoklu süreç eşzamanlılığı, fiziksel imha,
    arşiv geri çağırma ve yedek re-delete açık kalır.
54. `25C-v1` idempotent ve append-only imha işi/sonuç kanıtı sözleşmesini,
    kullanıcı-servis görev ayrılığını, hold yeniden kontrolünü ve atomik
    veri-minimum audit outbox'ı teknik olarak doğruladı. Fiziksel
    silme/anonimleştirme/arşivleme adaptörü, gerçek onay/kanıt resolver'ı,
    üretim PostgreSQL/WORM yetkileri, çoklu süreç claim/lease, banka rol/reason
    code eşlemesi, yedek re-delete ve arşiv geri çağırma açık kalır.
55. `25D-v1` audit/kalite skoru arşivleri için idempotent talep, farklı karar
    aktörü, rol/kapsam kontrolü ve atomik veri-minimum audit outbox sözleşmesini
    teknik olarak doğruladı. Gerçek arşiv deposu/resolver'ı, veri getirme/taşıma,
    erişim süresi, indirme/DLP, üretim rol/gerekçe eşlemesi, PostgreSQL/WORM
    yetkileri ve geri çağrılan kopyanın yeniden imhası açık kalır.
56. `27A-v1` güvenilir sağlayıcı sözleşmeli ortam kimliği, ortam-secret kapsamı
    eşleşmesi ve üretim dışı gerçek banka verisi/üretim secret engelini teknik
    olarak doğruladı. Gerçek deployment/attestation sağlayıcısı, konfigürasyon
    imzası, kurumsal secret manager bağlantısı, veri hazırlama/provenance kanıtı
    ve ortam bazlı ağ/IAM ayrımı açık kalır.
57. `31A` sürümlü kaynak kullanım politikası, aktif sürüm değişimi, globalden
    kaynak türü/kaynağa override ve fail-closed claim kotasını teknik olarak
    doğruladı. Üretim politika değerleri, PostgreSQL migration/çoklu instance
    eşzamanlılığı, CPU/IO ve hız sınırı ölçümü ile politika değişikliği audit
    olayının merkezi outbox'a bağlanması açık kalır.
58. `31B` IANA saat dilimli izinli/yasaklı çalışma penceresini, gece yarısını
    aşan aralığı, yasaklı pencere önceliğini ve pencere dışı fail-closed claim
    kararını teknik olarak doğruladı. Üretim pencere değerleri, tatil/istisna
    günleri, `REJECT` için terminal durum modeli, politika karar metriği/alarmı ve
    banka onaylı yoğun saat davranış sözlüğü açık kalır.
59. `31C` kaynak politikasındaki sorgu timeoutu, retry sayısı ve gecikmesini tek
    snapshot üzerinden worker yürütmesine bağladı. Gerçek bağlayıcılarda duvar
    saati timeout/iptal zorlaması, üretim sayısal değerleri, retry metriği/alarmı
    ve çoklu instance politika önbelleği açık kalır.
60. `31D` hız sınırı artımı için sayaç birimi, pencere türü, tüketim anı ve
    kalıcı/dağıtık sayaç davranışı SRS'de tanımlı değildir. Bu semantik ve kabul
    kriterleri kesinleşmeden çalışma zamanı hız sınırı uygulanmayacaktır.
61. `32A`–`32D` sürümlü/onaylı dataset kısmi skor politikasını, fail-closed
    karar servisini ve kararın `QualityScore`, resmî agregasyon, trend ile rapor
    önizlemesine uygulanmasını; güvenilir actor, maker-checker onay/ret ve atomik
    audit outbox ile maker'a ait geri çekme akışını teknik olarak doğruladı.
    `PartialExecutionFacts` olgularının execution/worker tarafından güvenilir
    üretilmesi, politika talebi süre aşımı, SLA ve resmî denetim
    çıktısı adaptörleri ile banka rol eşlemesi açık kalır.
62. Kapsama oranı ile eksik kayıt oranının beklenen/gerçek sayaçlardan nasıl
    hesaplanacağı SRS'de tanımlı değildir. Bu formüller, veri kökeni ve worker
    kanıt sözleşmesi kesinleşmeden `PartialExecutionFacts` otomatik üretilmez.
63. `DQ-SCR-001`–`DQ-SCR-033` dokümantasyon sözleşmesi kesinleşti. İterasyon 33A
    standart sekiz ölçüm durumu, sekiz kanonik sayaç ve değerlendirilen kayıt
    paydasını uyguladı. Runtime; dışlama alt kırılımları, veri öğesi seviyesi,
    ayrı kapsam/güven/risk/kritiklik/teknik sağlık varlıkları, kritik veto/tavan,
    sürümlü normalizasyon, istisna/override ve replay sözleşmesinin kalanını henüz
    uygulamamaktadır.
64. Üretim normalizasyon, eşik/ağırlık, kritik veto/tavan/blokaj, kapsam/güven
    ve veri risk değerleri aktif, sürümlü ve onaylı politika kaydından
    çözülecektir. Politika yoksa ilgili yeterlilik/risk/kullanım sonucu
    fail-closed üretilmeyecektir; üretim politika kayıtlarının oluşturulması
    beklenmektedir.
65. `SOURCE_EQUAL_DATASET_QUALITY_V2` kritiklik ağırlığını kaynak kalite
    skorundan çıkarmıştır. Tarihsel `SOURCE_WEIGHTED_V1` kayıtlarının yeni
    modelle replay/backfill ilişkisi, trend sürüm sınırı ve geri alma planı
    henüz uygulanmamıştır.
66. İstisna ve ham skordan ayrı değerlendirme/override için banka rol matrisi,
    izinli türler, azami süre, risk kabul ve raporlama politikası açık kalır;
    `OPEN-BNK-004`, `OPEN-BNK-005`, `OPEN-BNK-006` ve `OPEN-BNK-008` geçerlidir.
67. Kanonik skorlama ve ölçüm yeterliliği hedef tasarımı dokümante edildi;
    population/eligible/evaluated dahil sekiz sayaç ve sekiz ölçüm durumu 33A ile
    runtime'a taşındı. Eski kanoniksiz sonuçların backfill/sürüm geçişi, ham/nihai
    skor ayrımı, yeterlilik durumları, geçerlilik kapısı ve ayrı kullanım kararı
    henüz uygulanmadı; geçiş `OPEN-022` sonrası küçük dilimlerle yürütülmelidir.
68. Ölçüm yöntemine göre kapsam pay/payda sözleşmesi, minimum kapsam, örneklem
    güveni, yeterlilik kanıt/onay matrisi, geçerlilik, kullanım/blokaj ve
    remediation/eskalasyon değerleri aktif sürümlü politika kaydından
    çözülecektir. Kayıt yoksa olumlu yeterlilik veya kullanım kararı
    üretilmeyecektir; runtime politika modeli henüz tamamlanmamıştır.
69. Sentetik dataset politika, senaryo ve run kayıt çekirdeği 34A, tamamen yapay
    deterministik Golden ilişkisel üretici 34B, değişmez Golden yapısal ground
    truth ve bağımsız karşılaştırıcı 34C, kanonik çıktı/doğrulama referanslı
    append-only terminal run kanıtı 34D, append-only profilli deterministik çok
    dönemli zaman semantiği 34E ile runtime'a taşındı. Politika ve
    senaryo oluşturma/onay yaşam döngüsü, gerçek fiziksel çıktı/artifact deposu,
    sürümlü genel şema yükleyici, eksiklik/trend/sezonsallık/drift, geç/sırasız
    akış ve hacim profilleri, sayısal skor ground truth'u, runtime
    kural/skor/olay karşılaştırması ve gizlilik değerlendiricisi uygulanmadı.
    34F ile 17 tabloluk PostgreSQL dataset kataloğu, dokuz teknik kusur sınıfı,
    kayıt düzeyi ground truth ve bağımsız SQL oracle'ı eklendi.
    Dağılım/korelasyon/görev faydası/gizlilik eşikleri, kusur yoğunluğu oranları
    ve skor toleransı aktif sentetik politika kaydında zorunludur; eksik kayıt
    doğrulamayı `BLOCKED` yapar. Runtime politika uygulaması henüz yoktur.
70. Sentetik üretimde üretim profili veya örneğinden öğrenme varsayılan olarak
    yasaktır. Ayrı veri sahibi, hukuk/KVKK ve bilgi güvenliği onaylı politika;
    erişim/ortam ayrımı, minimizasyon, saklama ve yeniden tanımlama kontrolünü
    kanıtlamadan açılamaz. Bu onay ve gerçek adaptör henüz yoktur. Sentetik
    üretim anonimlik kanıtı veya `OPEN-014` nihai kabulünün yerine geçen kanıt
    sayılmayacaktır.
71. Uygulamanın metadata/profil ve kural yürütme adaptörlerinin 34F PostgreSQL
    kaynağına bağlanması, ayrıntılı kusur alt türleri, diğer beş senaryonun
    gerçek PostgreSQL ölçümü ve `OPEN-014` kapsamındaki 20 milyon satırlık
    anonimleştirilmiş kabul testi açık kalır.
72. `OPEN-026–OPEN-036` teknik yönleri kesinleşmiştir; kanıta dayalı karar
    sistemi runtime'da uygulanmış değildir. Kurumsal katalog/OpenLineage
    adaptörü, sürümlü kullanım/etki/tarama/kalite borcu politikaları, öneri ve
    remediation servisleri ile kanonik kanıt paketi uygulama backlogundadır.
73. Üretim KMS/HSM imzası, WORM uyumlu kanıt deposu, kurumsal tokenizasyon,
    DLP/katalog erişimi ve kayıt sınıfı saklama/imha uygulaması mevcut değildir.
    İlgili `OPEN-BNK-*` incelemeleri geçerlidir; bu altyapı yokken hassas erişim,
    otomasyon ve kanıt dışa aktarma fail-closed kalır.
74. Dashboard 21C DTO'su politika yokluğunu ve teknik hatayı güvenli biçimde
    gösterir; gerçek `MeasurementQualificationResult`, kapsam/güven politikası,
    kritik kural sonuç özeti, kullanım kararı ve alarm runtime kaynakları henüz
    uygulanmadı. Bu kaynaklar yokken API olumlu yeterlilik veya sıfır kritik
    ihlal sayısı üretmez.
75. PostgreSQL-only hedefi ve 36A–36F yazılabilir arayüz sırası
    kesinleşmiştir. `PG-MIG-001–005` ve `UI-WRITE-001–007` teknik seçenekleri
    karara bağlanmıştır; yalnız ileri migration kullanılır. 36A öncesinde SQLite
    repository envanteri, tablo/constraint eşlemesi, Alembic baseline,
    `data_quality.dq` şeması ve PostgreSQL test izolasyonu uygulanmalıdır.
    36B–36F mutasyonları gerçek IdP, güvenilir aktör, BFF/CSRF, rol/kapsam,
    maker-checker ve audit önkoşullarını sağlamadan açılmaz. Denetim kayıtları
    değişmezdir; kaynak sistemlere yazma kapsam dışıdır.

## Bankacılık Geçiş Açık Konuları

| ID | Konu | Karar sahibi | Durum |
| --- | --- | --- | --- |
| OPEN-BNK-001 | BDDK bilgi sistemleri düzenlemelerinin bu uygulamaya uygulanabilir maddelerinin banka uyum/hukuk tarafından teyidi | Uyum / Hukuk / Bilgi Güvenliği | ComplianceReviewRequired |
| OPEN-BNK-002 | IdP grup-rol-scope eşleme tablosunun değerleri ve joiner/mover/leaver kaynağı | IAM / İnsan Kaynakları / Bilgi Güvenliği | Açık |
| OPEN-BNK-008 | Kayıt türü bazlı süre, gerekçe ve imha periyodu için hukuk/KVKK/bilgi güvenliği/iç denetim onayı; banka rol/gerekçe eşlemesi ve gerçek imha/arşiv adaptörleri | Hukuk / KVKK Komitesi / İç Denetim | ComplianceReviewRequired |
| OPEN-BNK-009 | ServiceNow kurulum yeri, veri işleyen/alt işleyen durumu ve yurt dışı aktarım etkisi | Hukuk / Tedarik / Bilgi Güvenliği | Açık |
| OPEN-BNK-011 | İş etki analizi, bileşen RPO/RTO hedef değerleri, yedek şifreleme ve geri yükleme test sıklığı | İş Sürekliliği / Operasyon | ComplianceReviewRequired |
| OPEN-BNK-013 | Sistem risk verisi veya düzenleyici raporlama üretim zincirine girecek mi; BCBS 239 kapsamı | Risk Yönetimi / Veri Yönetişimi | Açık |
| OPEN-BNK-018 | Gerçek kurumsal IdP endpoint/protokol yapılandırması, LDAP arka uç topolojisi, TLS güveni, timeout ve teknik hata sahipliği | IAM / Altyapı / Bilgi Güvenliği | Açık |
| OPEN-BNK-019 | Başarısız giriş için banka/LDAP uyumlu eşik, pencere, süre ve politika değişikliği onay/görevler ayrılığı; opak anahtar üretimi/rotasyonu, güvenilir istemci referansı ve paylaşımlı üretim deposu | IAM / Bilgi Güvenliği / Mimari / Altyapı / İç Kontrol | ComplianceReviewRequired |

## Kullanım

Bir teknik yön seçildiğinde ilgili kaydı, durumunu yükseltmeden
[Alınan Kararlar](Alinan-Kararlar.md) notuna taşı; bu dosyada yalnız gerçek açık
ve kurumsal inceleme kayıtlarını bırak.
