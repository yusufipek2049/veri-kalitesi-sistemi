---
type: project-memory
status: open
project: Veri Kalitesi İzleme ve Skorlama Sistemi
last_updated: 2026-07-21
tags:
  - proje
  - acik-konu
  - tbd
---

# Açık Konular

Ayrıntılı ve bağlayıcı liste: [SRS — Açık Konular ve Varsayımlar](../01-SRS/15-Acik-Konular.md).

## Geliştirmeyi En Çok Etkileyen Kararlar

1. Bağlayıcı geliştirme sırası kesinleşti; ilk ve ikinci ilişkisel veritabanı ürünleri, gerçek sürücü paketleri ve canlı entegrasyon ortamı TBD'dir.
2. Kaynak kullanım politika modeli, sürümlü SQLite deposu, global/kaynak override çözümlemesi, claim sırasında worker/sorgu kotası ve çalışma/yasaklı pencere koruması ile sorgu timeout/retry yürütmesi teknik olarak uygulandı. Üretim worker/kota/pencere/CPU/IO/timeout/rate değerleri ile CPU/IO ve hız sınırı çalışma zamanı uygulaması TBD'dir.
3. Kurumsal secret manager ve servis/workload identity yönü kesinleşti; ürün ve erişim eşlemesi TBD'dir.
4. Kurumsal IdP/SSO, OIDC veya SAML ve tüm kullanıcılar için MFA kesinleşti; ürün, grup-rol eşleme değerleri ve break-glass ayrıntıları TBD'dir.
5. 20 milyon satırlık testin onaylı anonimleştirilmiş üretim örneğiyle yapılması kesinleşti; veri sahibi onayı, dataset ve test ortamı henüz hazırlanmadı.
6. ServiceNow ara entegrasyon modeli kesinleşti; gerçek tablo/alan/durum eşleme, servis hesabı, endpoint/TLS ve veri aktarım kararı açık.
7. Kayıt sınıfı bazlı saklama ve bileşen bazlı RPO/RTO kesinleşti; süreler iş etki analizi ve kurum onaylarına kadar TBD'dir.
8. Hibrit dağıtım yönü kesinleşti; kurumsal konteyner platformu, yüksek erişilebilirlik veritabanı, broker ve kalıcı dosya depolama ürünleri TBD'dir.
9. Audit olay sınıfı davranışı kesinleşti; üretim outbox/kuyruk, alarm ve kapasite değerleri TBD'dir.
10. Kısmi resmî skor dataset politika koşullarına bağlandı; kurumsal eşik değerleri ve onaylı politika kayıtları TBD'dir.
11. Dashboard güvenilir `ActorContext` ve `AuthorizationService` sınırına taşındı; diğer servislerdeki serbest `actor_id` kullanımı ile context issuer'ın gerçek LDAP/session adaptörüne bağlanması İterasyon 20 ve sonraki modül geçişlerini gerektirir.
13. PostgreSQL için üretim sürücüsü, bağlantı havuzu yaklaşımı ve canlı entegrasyon test veritabanı henüz seçilmedi.
14. Şema değişikliğinde aktif kuralları “inceleme gerekli” durumuna alma davranışı, kural yönetimi modülü uygulanınca metadata değişim bayrağına bağlanmalıdır.
15. `AC-008` için veri sahibi onaylı, anonimleştirilmiş üretim örneği, yeniden kimliklendirme risk değerlendirmesi ve donanım gözlemli performans testi henüz hazırlanmadı; birim testleri yalnız SAMPLE sözleşmesini doğruluyor.
16. `RuleTestExecutor` için PostgreSQL/CSV kaynak adaptörleri, sorgu maliyet tahmini ve regex çalışma timeoutu henüz uygulanmadı; mevcut iterasyon güvenli domain sözleşmesini, şablon planlarını ve test geçmişini doğruluyor.
17. Üretim iş kuyruğu/broker ürünü, çoklu worker claim stratejisi ve worker sayısı henüz seçilmedi; yerel prototip SQLite üzerinde süreç içi kilitle kalıcı kuyruk davranışını doğruluyor.
18. Bağlantı, sorgu ve toplam timeout değerleri worker yürütücü sözleşmesinde ayrı taşınıyor ve iptal adaptörü tanımlandı; gerçek PostgreSQL/CSV adaptörlerinde sorgu iptali ile duvar saati zorlaması henüz uygulanmadı.
19. Genel cron ifadesi desteği için kullanılacak doğrulanmış parser/kütüphane ve kabul edilen cron grameri henüz seçilmedi; mevcut zamanlama yalnız ONCE/DAILY/WEEKLY/MONTHLY türlerini destekliyor.
20. QualityDimension için ayrı kalıcı UUID varlığı henüz uygulanmadı; boyut skoru kapsam kimliği geçici olarak değişmez enum kodunu (`COMPLETENESS` vb.) kullanıyor.
21. Mevcut runtime dataset kritikliğini `SOURCE` kalite agregasyonuna katıyor; `DQ-SCR-018` ve `ADR-015` bu yaklaşımı hedef modelde `Superseded` yapmıştır. Kritiklik profilinin ayrı taşınacağı migration, replay ve trend sürüm sınırı uygulanmalıdır.
22. Kurum skorunda kaynaklar arası ham kalite agregasyon politikası onaylanmadı; mevcut `ENTERPRISE` formülü kaynakları eşit ağırlıklandırıyor. Yeni politika kritiklik ve veri riskini kalite skoruna karıştırmamalı, ayrı sürümlenmelidir.
23. Eski SQLite `audit_records` için salt okunur envanter ve idempotent merkezi aktarım sözleşmesi sentetik verilerle teknik olarak doğrulandı. Gerçek ortam envanteri/koşusu, yedek ve geri dönüş planı, değişiklik penceresi ve operasyon onayı henüz tamamlanmadı.
24. `DURABLE_BUFFER` sözleşmesi ve hata yolu test edildi; üretim kalıcı tampon teknolojisi, sahipliği, şifrelemesi, yeniden oynatma ve idempotency davranışı henüz uygulanmadı.
25. SQLite outbox için üretim publisher worker'ı, claim/eşzamanlılık, retry/backoff, alarm metrikleri, kapasite sınırı ve saklama/temizleme politikası henüz uygulanmadı.
26. `CLASSIFICATION_POLICY_V1`, fail-closed profil politikası, sürümlü `BFR-DATA-004` işleme envanteri ve kişisel/özel nitelikli kişisel alanlar için salt okunur tamlık kontrolü uygulandı. Teknik kodların banka sözlüğüyle eşlemesi ve referansların kurumsal kayıtlarla doğrulanması açık kalır.
27. Kritik kural aktivasyonu için 19A, skor konfigürasyonu için 19B, kural onay isteği geri çekme için 19C, 3/10 iş günlük kural süre aşımı için 19D, veri kaynağı aktivasyonu için 19E, kaynak onay geri çekme/süre aşımı için 19F, bağlantı revizyonu/onay geçersizleştirme için 19G ve kontrollü kaynak pasifleştirme için 19H uygulandı. Gerçek banka iş günü/tatil kaynağı, worker işletimi, hazırlayanı bilinmeyen legacy kritik sürümlerin geçiş prosedürü, kaynak kritiklik sözlüğü, üretim migration/çoklu instance eşzamanlılığı, çalışan işin tamamlanması/iptali politikası, operasyon bildirimi ve banka onaylı maker/checker/deactivator/worker rol kodları açık kalır.
28. Başarısız giriş sınırlandırması opak kullanıcı/istemci anahtarlarıyla teknik olarak uygulandı. Üretim anahtar türetme/rotasyon yöntemi, secret manager bağlantısı, güvenilir istemci referansının proxy/ağ sınırı, paylaşımlı depo ürünü ve LDAP ile uyumlu nihai eşik/pencere/süre onayı açık kalır.
29. Normal kullanıcı oturumu kalıcı ve iptal edilebilir olarak uygulandı. Eş zamanlı oturum limiti, banka onaylı mutlak süre, HTTP cookie veya eşdeğer token taşıma/CSRF modeli, üretim deposu ve at-rest şifreleme, bir yıllık session geçmişi saklama/imha onayı açık kalır.
30. Dashboard trendi güvenilir scope ile sabit son 30 UTC gün için uygulandı. Serbest tarih aralığı/periyot seçimi, operasyon listeleri, grafik/tablo sunumu ve HTTP taşıma katmanı açık kalır; 21B `OPEN-BNK-020` ve geçiş kapısına bağlıdır.
31. Sistem içi bildirim domain yaşam döngüsü sabit veri-minimum şablon ve güvenilir resolver protokolüyle uygulandı. Gerçek sahiplik/fallback grup kaynağı, şablon yönetimi, susturma/eskalasyon politikası, asenkron retry/DLQ, saklama-imha ve HTTP/UI yüzeyi açık kalır.
32. Otomatik issue oluşturma, atama/inceleme, korunan çözüm, başarısız/teknik doğrulama, farklı aktörle başarılı `VERIFIED`, doğrulama bağlı `CLOSED`, aynı başarısızlıkla yeniden açma ve yeni kalite başarısızlığını append-only ilişkilendirme uygulandı. Gerçek assignment/kullanıcı dizini, çözüm koruma, doğrulama ve ilişki resolver adaptörleri; banka onaylı çözen/doğrulayan rol eşlemesi, bildirim retry/DLQ, saklama-imha ve ServiceNow açık kalır.
34. ServiceNow ticket oluşturma allowlist projeksiyon, güvenilir servis context'i ve idempotent fake adaptörle teknik olarak doğrulandı. Gerçek endpoint/credential, banka alan-durum eşlemesi, servis hesabı yetkilendirmesi, timeout/retry/backoff, durum senkronizasyonu ve `OPEN-BNK-009` onayı açık kalır.
36. ServiceNow senkron geçici/429 retry politikası toplam en fazla üç deneme, üstel backoff ve `Retry-After` ile teknik olarak doğrulandı. Gerçek timeout/ağ adaptörü ve operasyon alarmı açık kalır.
37. ServiceNow kalıcı retry işi, tek worker claim'i, due-time yeniden planlama, dead-letter ve auditli yeniden kuyruğa alma SQLite prototipinde doğrulandı. Gerçek broker, çoklu süreç lease/heartbeat ve kayıp worker recovery, kuyruk kapasitesi/saklama ve operasyon alarmı açık kalır.
38. ServiceNow circuit breaker beş ardışık geçici hata, beş dakikalık açık durum ve tek half-open probe ile SQLite prototipinde doğrulandı. Dağıtık/çoklu instance state deposu, üretim eşik onayı, metrik/alarm sahipliği ve gerçek ServiceNow endpoint/credential kararı açık kalır; `OPEN-BNK-009` geçerlidir.
39. Audit inceleme sorgusu güvenilir `AUDIT_VIEWER` context'i, 31 günlük senkron pencere, snapshot cursor, parametreli filtre ve auditli görüntüleme ile doğrulandı. Banka onaylı auditor rol/grup eşlemesi, istemci bilgisi alanı, çevrimiçi saklama penceresini aşan asenkron arşiv raporu ve hassas dışa aktarma politikası açık kalır; `OPEN-BNK-002`, `OPEN-BNK-008` ve `OPEN-BNK-014` geçerlidir.
40. Rapor önizleme güvenilir rol/source kapsamı, 31 günlük pencere, 500 source sınırı, salt okunur latest-score sorgusu ve veri-minimum audit ile doğrulandı. PDF/XLSX/CSV, Report yaşam döngüsü, asenkron üretim, indirme, DLP/watermark, dosya saklama/imha ve banka onaylı dışa aktarma/maker-checker politikası açık kalır; `OPEN-BNK-002`, `OPEN-BNK-007`, `OPEN-BNK-008` ve `OPEN-BNK-014` geçerlidir.
41. Güvenlik olayı, kişisel veri ihlali şüphesi, 72 saat hedefi, veri işleyen bildirim kanıt referansı ve farklı aktörle insan kararı teknik olarak uygulandı. Banka olay/rol sözlüğü, gerçek SIEM/SOC akışı, hukuk/uyum karar içeriği, dış bildirim, saklama/imha ve tatbikat kanıtı açık kalır; `OPEN-BNK-001`, `OPEN-BNK-002`, `OPEN-BNK-004`, `OPEN-BNK-008` ve `OPEN-BNK-010` geçerlidir.
42. İhlal zaman çizelgesi güvenilir privacy rolü ve incident scope'u ile veri-minimum görüntülenebilir; 72 saat durumu ve görüntüleme auditi teknik olarak doğrulandı. Listeleme/arama, HTTP/UI, kanıt içeriğine ayrı erişim, gerçek SIEM/SOC, banka rol eşlemesi ve saklama/imha açık kalır; `OPEN-BNK-002`, `OPEN-BNK-008` ve `OPEN-BNK-010` geçerlidir.
43. Yerel `28A-v1` secret taraması teknik olarak doğrulandı. Kurumsal scanner/CI-CD ürünü, secret bulgu eşiği, istisna ve risk kabulü, geçmiş commit taraması, pipeline zorlaması ve banka bilgi güvenliği onayı açık kalır.
44. `28B` doğrudan bağımlılık envanteri ve sürüm bağlı CycloneDX 1.5 SBOM'u teknik olarak doğrulandı. Transitive bağımlılık/lock, artifact hash'i, lisans, zafiyet veritabanı, harici scanner/SBOM ürünü, CI/CD zorlaması ve banka eşik/istisna onayı açık kalır.
45. `28C-v1` veri-minimum SAST bulgu zarfı, tamamlanmamış tarama teknik hata yolu ve kritik bulguda fail-closed sürüm kapısı teknik olarak doğrulandı. Gerçek SAST scanner/repository taraması, CI/CD zorlaması, kritik olmayan banka eşikleri, istisna/risk kabulü, release maker-checker, DAST ve pentest açık kalır.
46. Frontend görsel tasarım ve dashboard dokümantasyon tabanı oluşturuldu. Frontend
    framework/component/chart kütüphanesi, kurumsal font, koyu tema teslim kapsamı,
    visual diff eşiği, Storybook/Playwright dependency kurulumu ve banka marka
    onayı açık kalır. Dashboard uygulaması ayrıca 21B güvenli HTTP/API sınırı ile
    bankacılık geçiş kapısına bağlıdır.
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
64. Üretim normalizasyon formülleri, eşik/ağırlık değerleri, kritik kural
    veto/tavan/blokaj davranışları, kapsam/güven ve veri risk katsayıları `TBD`'dir.
    Karar sahipleri Veri Yönetişimi, Risk Yönetimi ve İç Kontrol'dür;
    `OPEN-BNK-004` ve `OPEN-BNK-013` kapanmadan değer uydurulmayacaktır.
65. Dataset kritikliğini `SOURCE` kalite skoruna ağırlık olarak katan mevcut
    teknik davranış `ADR-015` ile hedef mimaride `Superseded` olmuştur. Yeni model
    sürümü, migration/backfill, trend sürüm sınırı, yeniden hesaplama ve geri alma
    planı uygulanmadan mevcut skor geçmişi değiştirilmeyecektir.
66. İstisna ve ham skordan ayrı değerlendirme/override için banka rol matrisi,
    izinli türler, azami süre, risk kabul ve raporlama politikası açık kalır;
    `OPEN-BNK-004`, `OPEN-BNK-005`, `OPEN-BNK-006` ve `OPEN-BNK-008` geçerlidir.
67. Kanonik skorlama ve ölçüm yeterliliği hedef tasarımı dokümante edildi;
    population/eligible/evaluated dahil sekiz sayaç ve sekiz ölçüm durumu 33A ile
    runtime'a taşındı. Eski kanoniksiz sonuçların backfill/sürüm geçişi, ham/nihai
    skor ayrımı, yeterlilik durumları, geçerlilik kapısı ve ayrı kullanım kararı
    henüz uygulanmadı; geçiş `OPEN-022` sonrası küçük dilimlerle yürütülmelidir.
68. Ölçüm yöntemine göre kapsam pay/payda sözleşmesi, üretim minimum kapsamı ve
    örneklem güveni, yeterlilik kanıt/onay matrisi, geçerlilik süreleri,
    kullanım/blokaj yetkileri ile remediation/eskalasyon
    hedefleri `TBD`'dir. Bu değerler `OPEN-023` ve `OPEN-BNK-004/008/010/013/017`
    kararı olmadan kodlanmamalıdır.
69. Sentetik veri hedef tasarımı dokümante edildi; üretici, politika/run/ground
    truth deposu, bağımsız karşılaştırıcı, gizlilik değerlendiricisi ve dataset
    kataloğu runtime'da uygulanmadı. Dağılım/korelasyon/görev faydası/gizlilik
    eşikleri, kusur yoğunluğu oranları, skor toleransı ve izinli üretim yöntemleri
    `OPEN-024` kapsamında `DecisionRequired` durumundadır.
70. Sentetik üretimde onaylı üretim profili veya örneği kullanılıp
    kullanılmayacağı; kullanılırsa erişim/ortam ayrımı, minimizasyon, saklama,
    yeniden tanımlama ve onay süreci `OPEN-025` kapsamında
    `ComplianceReviewRequired / LegalReviewRequired / SecurityReviewRequired`
    durumundadır. Sentetik üretim anonimlik kanıtı veya `OPEN-014` nihai kabulünün
    yerine geçen kanıt sayılmayacaktır.

## Bankacılık Geçiş Açık Konuları

| ID | Konu | Karar sahibi | Durum |
| --- | --- | --- | --- |
| OPEN-BNK-001 | BDDK bilgi sistemleri düzenlemelerinin bu uygulamaya uygulanabilir maddelerinin banka uyum/hukuk tarafından teyidi | Uyum / Hukuk / Bilgi Güvenliği | ComplianceReviewRequired |
| OPEN-BNK-002 | IdP grup-rol-scope eşleme tablosunun değerleri ve joiner/mover/leaver kaynağı | IAM / İnsan Kaynakları / Bilgi Güvenliği | Açık |
| OPEN-BNK-003 | Tüm kullanıcılar için IdP MFA kesinleşti; PAM ve kontrollü/süreli/auditli break-glass ürün ve rol ayrıntıları | Bilgi Güvenliği / IAM | ProvisionalDecision |
| OPEN-BNK-004 | Kritik işlem listesi ve maker-checker onay rolleri | Veri Yönetişimi / İç Kontrol | ProvisionalDecision |
| OPEN-BNK-005 | Kritik işlem fail-closed, rutin olay durable outbox olarak kesinleşti; üretim kuyruk/outbox, kapasite ve alarm ayrıntıları | Bilgi Güvenliği / Mimari / Operasyon | ProvisionalDecision |
| OPEN-BNK-006 | Audit bütünlüğü için WORM, hash-chain, imza veya kurumsal log platformu kararı | Bilgi Güvenliği / İç Denetim | Açık |
| OPEN-BNK-007 | Kurumsal katalog/DLP sınıflandırma kaynağı kesinleşti; ürün ve müşteri/banka sırrı etiket eşlemesi | Veri Yönetişimi / Hukuk / Bilgi Güvenliği | ProvisionalDecision |
| OPEN-BNK-008 | Kayıt türü bazlı politika taslağı, imha aralığı, append-only legal hold, idempotent imha kanıtı ve yetkili arşiv geri çağırma talep/kararı teknik olarak uygulandı; banka politika/rol/gerekçe onayı, gerçek resolver/adaptörler, fiziksel imha, yedek re-delete, erişim süresi ve geri çağrılan kopyanın yeniden imhası bekleniyor | Hukuk / KVKK Komitesi / İç Denetim | ProvisionalDecision |
| OPEN-BNK-009 | ServiceNow kurulum yeri, veri işleyen/alt işleyen durumu ve yurt dışı aktarım etkisi | Hukuk / Tedarik / Bilgi Güvenliği | Açık |
| OPEN-BNK-010 | SIEM ürün, olay sözlüğü, alarm seviyesi ve SOC eskalasyon akışı | SOC / Bilgi Güvenliği | Açık |
| OPEN-BNK-011 | Bileşen bazlı RTO/RPO modeli kesinleşti; iş etki analizi, hedef değerler, yedek şifreleme ve geri yükleme sıklığı | İş Sürekliliği / Operasyon | ComplianceReviewRequired |
| OPEN-BNK-012 | Hibrit dağıtım ve kurumsal secret manager yönü kesinleşti; ürünler, deployment/attestation sağlayıcısı, konfigürasyon imzası ve ortam bazlı ağ/IAM ayrımı bekleniyor | Mimari Kurul / Operasyon / Bilgi Güvenliği | ProvisionalDecision |
| OPEN-BNK-013 | Sistem risk verisi veya düzenleyici raporlama üretim zincirine girecek mi; BCBS 239 kapsamı | Risk Yönetimi / Veri Yönetişimi | Açık |
| OPEN-BNK-014 | Hassas rapor dışa aktarma için gerekçe, onay, DLP ve watermark politikası | Bilgi Güvenliği / Veri Sahibi | Açık |
| OPEN-BNK-015 | `ActorContext` kurumsal IdP/session adaptöründen üretilecek; issuer sahipliği ve OIDC/SAML session assertion doğrulaması henüz kesinleşmedi. | IAM / Bilgi Güvenliği / Mimari | ProvisionalDecision |
| OPEN-BNK-016 | Üretim audit durable-buffer teknolojisi, şifreleme, sahiplik, yeniden oynatma ve başarısız tampon davranışı | Mimari / Operasyon / Bilgi Güvenliği | Açık |
| OPEN-BNK-017 | Onay hedefi 3 iş günü ve otomatik sona erme 10 iş günü olarak teknik politikaya alındı; gerçek banka iş günü/tatil kaynağı, worker zamanlaması ve banka onaylı rol sahibi bekleniyor | Veri Yönetişimi / İç Kontrol / Mimari | ProvisionalDecision |
| OPEN-BNK-018 | Gerçek kurumsal IdP endpoint/protokol yapılandırması, LDAP arka uç topolojisi, TLS güveni, timeout ve teknik hata sahipliği | IAM / Altyapı / Bilgi Güvenliği | Açık |
| OPEN-BNK-019 | Başarısız giriş için banka/LDAP uyumlu eşik, pencere, süre ve politika değişikliği onay/görevler ayrılığı; opak anahtar üretimi/rotasyonu, güvenilir istemci referansı ve paylaşımlı üretim deposu | IAM / Bilgi Güvenliği / Mimari / Altyapı / İç Kontrol | ComplianceReviewRequired |
| OPEN-BNK-020 | Normal kullanıcı oturumunda eş zamanlı limit, mutlak süre, HTTP cookie/token ve CSRF modeli, üretim deposu/şifreleme, saklama-imha süresi ve politika değişikliği onayı | IAM / Bilgi Güvenliği / Mimari / Hukuk / İç Kontrol | ComplianceReviewRequired |

## Kullanım

Bir teknik karar kesinleştiğinde ilgili `OPEN-xxx` maddesini güncelle ve sonucu [Alınan Kararlar](Alinan-Kararlar.md) notuna taşı.
