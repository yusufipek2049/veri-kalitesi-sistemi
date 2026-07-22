---
type: architecture
project: Veri Kalitesi İzleme ve Skorlama Sistemi
status: target-design
last_updated: 2026-07-21
tags:
  - architecture
  - synthetic-data
  - privacy
  - testing
---

# Sentetik Veri ve Gizlilik Stratejisi

## Amaç ve Yetki Sınırı

Bu belge, sentetik test verisinin yapılandırma tabanlı üretimi, doğrulanması,
kullanımı ve imhası için kanonik hedef tasarımdır. Başarı; yapısal ve
istatistiksel benzerlik, veri kalitesi sistemi açısından görev faydası ve gizlilik
riski arasında birlikte değerlendirilir.

Sentetik veri üretmek tek başına anonimlik kanıtı değildir. Sentetik veri,
anonimleştirilmiş veri, maskelenmiş veri, takma adlandırılmış veri ve test verisi
birbirinin yerine kullanılmaz. `OPEN-014` kapsamındaki 20 milyon satırlık nihai
performans kabulü, veri sahibi onaylı ve yeniden kimliklendirme riski
değerlendirilmiş anonimleştirilmiş üretim örneğiyle ayrıca yapılır. Sentetik
performans profili bu kabulün ön doğrulamasıdır, yerine geçmez.

Bu belge hedef mimariyi tanımlar; üretici, veri deposu veya üçüncü taraf ürün
seçimi yapmaz ve mevcut runtime'da uygulanmış davranış iddiası taşımaz.

## Kavram Ayrımları

| Kavram | Tanım | Güvenlik sonucu |
| --- | --- | --- |
| Sentetik veri | Tanımlı şema, ilişki, dağılım ve senaryodan üretilen yapay kayıtlar | Anonimlik otomatik kabul edilmez; gizlilik kapısından geçer. |
| Anonimleştirilmiş veri | Yeniden tanımlama riski yetkili süreçte değerlendirilmiş veri | Hukuki ve güvenlik onayı ayrı kanıt gerektirir. |
| Maskelenmiş veri | Görünürlüğü azaltılmış fakat kaynağı gerçek olabilen veri | Kişisel veri niteliğini otomatik kaybetmez. |
| Takma adlandırılmış veri | Doğrudan tanımlayıcısı başka değerle değiştirilmiş veri | Yeniden bağlama riski nedeniyle anonim sayılmaz. |
| Ground truth | Sentetik senaryonun bağımsız beklenen kural, skor ve olay sonucu | İş verisinden ve sistemin gerçekleşen çıktısından ayrı tutulur. |

## Tasarım İlkeleri

1. Üretim verisinin birebir kopyası, gerçek kimlik veya müşteri numarası üretim
   girdisi ya da örnek sabit olarak kullanılmaz.
2. Şema sürümü; tip, uzunluk/hassasiyet, nullability, anahtar, referans veri,
   zaman, para/ölçü birimi, durum geçişi ve iş kuralı anlamlarını taşır.
3. Kolonlar bağımsız üretilmez; segment, korelasyon, koşullu olasılık ve ilişkisel
   bütünlük senaryo tarafından korunur.
4. Normal kayıt, nadir fakat geçerli kayıt, sınırda geçerli kayıt, biçimsel olarak
   geçerli iş hatası ve açık geçersiz kayıt ayrı etiketlenir.
5. Normal veri üretimi ile kusur enjeksiyonu ayrı aşamalardır. İlişki veya kısıt
   ihlali yalnız senaryo açıkça istediğinde oluşturulur.
6. Aynı kanonik konfigürasyon, üretici sürümü ve `random_seed` aynı çıktıyı
   üretmelidir. Deterministik olmayan dış bağımlılık kullanılamaz.
7. Sentetik üretici beklenen sonucu üretir, kural/skor motoru veriyi bağımsız
   değerlendirir, karşılaştırıcı beklenen ile gerçekleşeni kıyaslar.
8. Skor motorunun çıktısı ground truth olarak geri beslenmez. Beklenen skor,
   bağımsız formül/oracle ve sürümlü test politikasıyla hesaplanır.
9. Test olayları yalnız izole fake/sandbox adaptörlerine yönelir. Gerçek kişi,
   gerçek ServiceNow veya üretim SIEM hedefi fail-closed reddedilir.
10. Dataset politikası yoksa üretim reddedilir; kod içi dağınık varsayılanlar
    politika yerine geçmez.

## Sentetik Veri Profilleri

| Profil | Amaç | Zorunlu özellik |
| --- | --- | --- |
| Golden Dataset | Tüm temel iş kurallarının bilinen sonucunu doğrulamak | Kusursuz temel, kesin ground truth, geçerli sınır değerleri |
| Normal Operasyon Dataset'i | Gündelik düşük yoğunluklu kalite kusurlarını modellemek | Segment ve zaman davranışı, parametrik düşük bozulma |
| Bozulmuş Dataset | Belirli kaynak, tarih, kolon, ürün veya segmentte kümeli kusur üretmek | Kümelenme kapsamı ve açık etkilenen boyut |
| Stress Dataset'i | Hacim ve sorgu davranışını sınamak | Yüksek kardinalite/tekrar, geniş tablo, bölümleme, maliyetli kural |
| Drift Dataset'i | Zamana bağlı dağılım değişimini sınamak | Trend, sezonsallık, yeni kategori, ani yapısal kırılma |
| Şema Değişikliği Dataset'i | Metadata ve bağımlılık etkisini sınamak | Ekleme, silme, yeniden adlandırma, tip ve kategori değişimi |
| Nadir Olay Dataset'i | Geçerli düşük frekanslı kayıtların yanlış alarm üretmemesini sınamak | Her olay için `is_valid_edge_case` ve beklenen geçiş sonucu |
| Gizlilik Test Dataset'i | Benzerlik ve yeniden tanımlama riskini ölçmek | Kontrollü risk senaryosu; normal test kullanıcılarına kapalı kapsam |
| Olay Yönetimi Dataset'i | Bildirim, issue ve SLA yaşam döngüsünü sınamak | İzole hedef, beklenen önem/atama/eskalasyon/kapanış |

Hacim profili ayrıca küçük fonksiyonel, entegrasyon, performans, yüksek
kardinalite, yüksek tekrar, bölümlü büyük tablo, geniş kolon, yoğun zaman serisi,
JSON/yarı yapılandırılmış, geç/sırasız akış ve paralel yük senaryolarını
destekler. Kayıt sayısı ve kaynak bütçeleri sürümlü politikadan gelir.

## Gerçekçilik Modeli

### Yapısal ve İş Anlamı

`Schema and Constraint Loader`, onaylı sentetik şema sürümünden tablo/kolon,
veri tipi, uzunluk/hassasiyet, zorunluluk, tekillik, birincil/yabancı anahtar,
referans kodu, durum geçişi, kaynak sistemi ve zaman metadata sözleşmesini yükler.
Üretim şemasına erişim gerekiyorsa erişim salt okunur, ayrı servis kimliğiyle ve
asgari kapsamla yapılır; ham kayıt okunmaz veya kopyalanmaz.

### İstatistiksel ve İlişkisel Model

Dağılım profili ortalama, medyan, standart sapma, min/max, yüzdelikler, kategorik
sıklık, sıfır ağırlığı, uzun kuyruk, sınıf dengesizliği, segment davranışı,
korelasyon ve koşullu olasılıkları tanımlar. Sayısal benzerlik eşikleri aktif,
sürümlü sentetik politika kaydında zorunludur; eksikse doğrulama `BLOCKED` olur.

`Relationship Generator`; müşteri, hesap, ürün, işlem, kaynak sistemi, şube,
organizasyon, kural ve dataset ilişkilerini ebeveyn önce üretim veya eşdeğer
deterministik çözümle kurar. Yetim kayıt, mükerrer kimlik ve çelişkili durum normal
profillerde üretilmez.

### Zaman ve Eksiklik Modeli

Zaman profili gün içi/hafta sonu/dönem sonu/tatil etkisi, batch zamanı, kaynak
gecikmesi, geç ve sırasız kayıt, geriye dönük düzeltme, yeniden işlenen dosya,
kesinti, sezonsallık, trend ve drift'i destekler. `event_time`,
`source_created_at`, `source_updated_at`, `ingestion_time`, `processing_time` ve
`quality_check_time` anlamları birbirine dönüştürülmez.

Eksiklik profili; tamamen rastgele, başka alana bağlı, değerin kendisine bağlı,
kaynak/kolon kombinasyonu/tarih/batch ve operasyonel kesinti kaynaklı eksikliği
ayrı türler olarak tanımlar. Parametreler konfigürasyon sürümüne bağlıdır.

## Kusur Enjeksiyonu

`Defect Injection Engine`; tamlık, geçerlilik, doğruluk, tutarlılık, tekillik,
referans bütünlüğü, güncellik, zamanlılık, şema uygunluğu, makullük, süreklilik,
dağılım kayması ve kaynak sistem uyumu boyutlarını destekler. Zorunlu alan
eksikliği, geçersiz tarih/kod, anlamsız tutar, duplicate, yetim yabancı anahtar,
kaynak çelişkisi, eski snapshot, geç kayıt, kısmi yükleme, eksik zaman dilimi,
oran değişimi, yeni kategori, şema değişimi, ölçü/para birimi uyuşmazlığı, kaynak
kesintisi ve biçimsel olarak geçerli yanlış değer ayrı kusur kodlarıdır.

Her kusur `LOW`, `MEDIUM`, `HIGH` veya `CRITICAL` yoğunluk sınıfı alır. Bu
sınıfların sayısal oranları dataset politikasında zorunludur; eksikse kusur
enjeksiyonu başlatılmaz. Yoğunluk ile beklenen skor düşüşü doğrusal varsayılmaz;
kural uygulanabilirliği, ağırlığı ve kritik davranış politikası hesaba katılır.
Dataset kritikliği kalite skoruna ağırlık olarak katılmaz; beklenen risk ve olay
önceliğini ayrı etkiler (`DQ-SCR-018`, `ADR-015`). Teknik kesinti veri kalitesi
kusuru olarak enjekte edilmez; ayrı teknik test olgusu üretir.

## Ground Truth ve Bağımsız Karşılaştırma

`SyntheticGroundTruth` en az şu alanları taşır:

| Alan | Açıklama |
| --- | --- |
| `synthetic_record_id` | İş kaydından ayrı sentetik kayıt referansı |
| `scenario_id`, `generation_run_id` | Senaryo ve üretim çalışması bağı |
| `generator_version`, `random_seed` | Tekrarlanabilirlik kanıtı |
| `source_system`, `dataset_id` | Sentetik kaynak ve hedef dataset kapsamı |
| `injected_defect` | Kusur kodu; kusursuz/geçerli uç durumda boş olabilir |
| `affected_dimension`, `affected_rule_id` | Beklenen etki kapsamı |
| `expected_rule_result`, `expected_severity` | Bağımsız beklenen kural/önem sonucu |
| `expected_dataset_score` | Bağımsız oracle ile hesaplanan beklenen skor |
| `expected_notification`, `expected_escalation` | İzole olay davranışı |
| `injection_timestamp`, `is_valid_edge_case` | Enjeksiyon zamanı ve geçerli uç ayrımı |
| `ground_truth_version` | Değişmez ground truth sürümü |

Beklenen skor; aynı kural, normalizasyon, ağırlık, yuvarlama ve kritik davranış
politika sürümlerini okuyan fakat runtime skorlama implementasyonunu çağırmayan
bağımsız karşılaştırıcı tarafından hesaplanır. `expected_score_tolerance` aktif
politika alanıdır; eksikse karşılaştırma `BLOCKED` olur. Gerçekleşen sonuç ile ground
truth farkı ayrı `SyntheticValidationResult` kaydıdır; ground truth değiştirilmez.

## Dataset Politikası

Mevcut politika katmanına `SyntheticDatasetPolicy` eklenir; `RetentionPolicy`,
`ScoringPolicy`, sınıflandırma ve kritiklik kayıtlarına referans verir, bunları
kopyalamaz.

| Alan | Açıklama |
| --- | --- |
| `dataset_id` | Hedef sentetik dataset |
| `synthetic_generation_allowed` | Üretim izni; yok/false ise fail-closed |
| `synthetic_profile`, `volume_profile` | Senaryo ve hacim profili |
| `distribution_profile`, `missingness_profile` | Sürümlü gerçekçilik profilleri |
| `defect_injection_profile`, `privacy_profile` | Kusur ve gizlilik değerlendirme profili |
| `retention_policy_id` | Ortak `RetentionPolicy` referansı |
| `ground_truth_enabled`, `seed_strategy` | Ground truth ve deterministik seed davranışı |
| `expected_score_tolerance` | Bağımsız karşılaştırma toleransı; zorunlu, eksikse `BLOCKED` |
| `criticality_profile_id` | Ayrı `DatasetCriticalityProfile` referansı |
| `notification_test_enabled` | Yalnız izole adaptör hedefleme izni |
| `schema_version`, `policy_version` | Şema ve değişmez politika sürümü |
| `effective_from`, `effective_to` | Geçerlilik aralığı |
| `approved_by`, `approval_status` | Risk bazlı onay ve görevler ayrılığı kanıtı |

Gizlilik profili, sınıflandırma veya saklama politikası bulunmadan gerçek profilden
türetilen üretim başlatılamaz. Üretim skoru etkileyen politika değişiklikleri
`RULE-005` maker-checker kapsamındadır.

## Mantıksal Bileşenler

Yeni mikroservis kurulmaz. Mevcut modüler monolit içinde aşağıdaki sorumluluklar
ayrılır:

| Bileşen | Sorumluluk | Girdi | Çıktı / hata |
| --- | --- | --- | --- |
| Synthetic Data Orchestrator | Yaşam döngüsü ve adım sırasını yönetir | Politika, senaryo, seed | Çalışma kaydı; doğrulama/teknik hata ayrımı |
| Schema and Constraint Loader | Sürümlü yapısal sözleşmeyi yükler | Şema referansı | Kanonik kısıt modeli; eksikte fail-closed |
| Distribution/Relationship/Temporal Generators | Gerçekçi temel kayıtları üretir | Profil ve seed | Kusur enjekte edilmemiş temel dataset |
| Defect Injection Engine | Kontrollü kusur uygular | Temel dataset, kusur profili | Etiketli kusurlu dataset ve enjeksiyon kanıtı |
| Ground Truth/Run Registry | Beklenen sonucu ve lineage'ı korur | Senaryo, politika, üretici sürümü | Değişmez ground truth ve run metadata |
| Privacy Risk Evaluator | Benzerlik ve çıkarım risk kapısını değerlendirir | Sentetik çıktı, yalnız onaylı referans özeti | `PASS/BLOCKED/TECHNICAL_ERROR`; aktif eşik kaydı yoksa `BLOCKED` |
| Synthetic Dataset Validator | Yapı, istatistik, görev faydası ve teknik doğrulama | Dataset ve sözleşmeler | Sürümlü doğrulama sonucu |
| Expected-versus-Actual Comparator | Bağımsız beklenen ile runtime sonucunu karşılaştırır | Ground truth ve gerçekleşen sonuç | Kural/skor/olay sapmaları |
| Synthetic Dataset Catalog | Datasetin test kökenini ve kullanım iznini sunar | Run ve doğrulama kayıtları | Yetki filtreli katalog kaydı |

Tüm bileşenler güvenilir `ActorContext` veya servis/workload identity, RBAC/scope,
veri-minimum audit ve kurumsal secret manager sınırına tabidir.

## Gizlilik ve Güvenlik Kapısı

Gizlilik değerlendirmesi birebir/aşırı yakın eşleşme, nadir kombinasyon, en yakın
komşu mesafesi, üyelik/özellik çıkarımı, bağlantı kurma, model ezberleme ve dolaylı
tanımlayıcı birleşimini kapsar. Nicel eşikler aktif sentetik politika kaydı olmadan
üretim verisiyle eğitilmiş veya profillenmiş bir çıktı genel test kullanımına
onaylanamaz.

Üretim profili veya örneği kullanımı varsayılan olarak kapalıdır. Ayrı veri
sahibi, hukuk/KVKK ve bilgi güvenliği onaylı politika etkinleştirilirse gerçek
veri; üreticiden, geliştiriciden ve test kullanıcısından ayrı ortam/ağ/IAM
sınırında, salt okunur ve amaçla sınırlı erişilir. Log, hata, audit ve rapor ham
değer taşımaz. Sentetik köken etiketi silinemez; dışa aktarım sınıflandırma ve
saklama politikasına tabidir. Break-glass erişimi varsa mevcut süreli, auditli ve
kurum onaylı IAM sürecini kullanır; bu belge yeni rol tanımlamaz.

## Yaşam Döngüsü ve Saklama

Durumlar `CREATED → VALIDATED → APPROVED → IN_USE → ARCHIVED → EXPIRED →
DESTROYED` akışını izler. Başarısız gizlilik veya görev faydası doğrulaması
`BLOCKED`, altyapı/çalıştırıcı arızası `TECHNICAL_ERROR` üretir. Yeniden üretim
yeni `generation_run_id` oluşturur; önceki run veya ground truth değiştirilmez.

Sentetik dataset, ground truth, üretim çalışması, doğrulama ve hata/retry kayıtları
ayrı kayıt sınıflarıdır. Süre, çevrimiçi/arşiv ayrımı ve imha yöntemi ortak
`RetentionPolicy` ile yönetilir. Fiziksel sentetik çıktı `RET-30D-EXPORT`,
operasyonel run/ground truth/doğrulama kaydı `RET-1Y-OPS`, resmî kabul kanıtı
`RET-10Y-BANKING` kapsamındadır. Sentetik olduğu gerekçesiyle sınırsız saklama
uygulanmaz.

## Test ve Kabul Modeli

| Test sınıfı | Zorunlu doğrulama |
| --- | --- |
| Yapısal | Şema/tip, zorunlu alan, anahtar, referans veri ve ilişki bütünlüğü |
| İstatistiksel | Dağılım, kategori, korelasyon, yüzdelik, segment ve zaman davranışı; aktif eşik kaydı yoksa `BLOCKED` |
| Görev faydası | Kural sonucu, hata yakalama, yanlış alarm, false positive/negative, skor sapması, önem, bildirim ve eskalasyon |
| Gizlilik | Birebir/yakın eşleşme, nadir kombinasyon, üyelik/özellik çıkarımı ve bağlantı riski; aktif eşik kaydı yoksa `BLOCKED` |
| Teknik | Hacim, paralellik, deterministik replay, idempotency, devam/retry, kesinti, şema değişimi, timeout ve örnekleme |

Kabul senaryoları `AC/TS-048–056` içindedir. Nicel benzerlik, gizlilik, görev
faydası, skor toleransı ve bozulma oranları yalnız aktif, sürümlü ve gerekli
onayı taşıyan sentetik politika kaydıyla kullanılabilir.

## İzlenebilirlik ve Etki

- Gereksinimler: `FR-088–FR-096`, `UC-017`, `RULE-016`, `RULE-017`.
- NFR: `NFR-PERF-010`, `NFR-PRV-007`.
- Kabul: `AC/TS-048–056`.
- Skorlama: `DQ-SCR-004`–`DQ-SCR-006`, `DQ-SCR-014`–`DQ-SCR-018`,
  `DQ-SCR-025`, `DQ-SCR-028`, `DQ-SCR-032`.
- Karar: `ADR-016`; açık kararlar `OPEN-024`, `OPEN-025`, `OPEN-014`.
- Risk: `RISK-016`, `RISK-017`.

## Güvenli Pasifleştirme

Sentetik üretim ayrı özellik/politika kapısıyla kapatılabilir. Kapı kapandığında
mevcut üretim, skor, kaynak bağlayıcı ve operasyon işleri etkilenmez; yeni sentetik
run kabul edilmez. Arşiv ve imha işlemleri `RetentionPolicy` kapsamında devam eder.
