---
type: architecture-design
status: target-design
project: Veri Kalitesi İzleme ve Skorlama Sistemi
created_at: 2026-07-21
tags:
  - architecture
  - scoring
  - measurement-qualification
  - governance
---

# Veri Kalitesi Skorlama ve Ölçüm Yeterliliği

## 1. Amaç ve Yetki Sınırı

Bu belge `DQ-SCR-001`–`DQ-SCR-033`, `FR-046`–`FR-053`, `RULE-003`–`RULE-007`
ve `ADR-015` için kanonik teknik tasarımdır. Kalite skorunun nasıl hesaplandığını,
ölçümün hangi koşullarda karar vermeye yeterli olduğunu ve sonuçların hangi
operasyonel akışları tetikleyebileceğini tanımlar.

Bu hedef tasarım mevcut runtime davranışının uygulanmış veya banka tarafından
onaylanmış olduğu anlamına gelmez. Üretim eşikleri, skor tavanları, ağırlıklar,
minimum kapsam, örneklem güveni, geçerlilik süreleri, remediation hedefleri,
bloke etme yetkileri ve onay rolleri `TBD`'dir.

Skor personel performansı veya cezalandırıcı KPI değildir. Skor; veri durumunu
göstermek, bozulmayı erken bulmak, riski önceliklendirmek, aksiyon üretmek ve
eğilimi izlemek için kullanılır.

## 2. Kanonik Kavramlar

| Kavram | Tanım | Ayrı tutulduğu kavram |
| --- | --- | --- |
| `RuleScore` | Gerçekten değerlendirilen kayıtlardaki başarı oranı | Teknik çalışma durumu |
| `DimensionScore` | Aynı uygulanabilir kalite boyutundaki kural skorlarının sürümlü ağırlıklı ortalaması | Boyut uygulanabilirliği |
| `RawQualityScore` | Uygulanabilir boyut skorlarının sürümlü ağırlıklı ortalaması | Kritiklik, risk ve yeterlilik |
| `FinalQualityScore` | Ham skora yalnız onaylı kritik kural politikasının deterministik tavan etkisi uygulanmış sonuç | Manuel override |
| `QualityStatus` | Nihai skoru sürümlü eşik politikasına göre açıklayan kalite durumu | Teknik veya yeterlilik durumu |
| `CriticalRuleStatus` | Zorunlu kritik kontrollerin bağımsız sonucu | Ağırlıklı ortalama |
| `MeasurementQualificationStatus` | Ölçümün operasyonel karar için kanıt bakımından yeterliliği | Kalite skoru |
| `ExecutionStatus` | Worker ve kaynak erişiminin teknik sonucu | Veri kalitesi başarısızlığı |
| `CoverageRate` | Ölçülen kapsamın tanımlı evrene oranı | Kalite ve güven |
| `ConfidenceLevel` | Örneklem/yöntem ve kanıtın ölçüme sağladığı güven | Kalite skoru |
| `UsageDecision` | Belirli kullanım bağlamında sonucun kullanılabilirlik kararı | Ham ve nihai skor |

Kanonik İngilizce alan adları API ve veri modelinde kullanılır. Kullanıcıya görünen
Türkçe karşılıklar aynı anlamı korur. Eski fiziksel enum ve alanların eşlemesi
ayrı migration sürümüyle yapılır; tarihsel kayıtlar sessizce değiştirilmez.

## 3. Kural Evreni ve Sayaçlar

Her oran tabanlı kural sonucu aşağıdaki sayaçları ayrı taşır:

| Alan | Tanım |
| --- | --- |
| `PopulationCount` | İş tarihi ve snapshot kapsamındaki toplam aday kayıt |
| `EligibleCount` | Uygulanabilirlik koşulunu sağlayan ve değerlendirilmesi beklenen kayıt |
| `EvaluatedCount` | Kural sonucunun gerçekten başarı/başarısızlık olarak üretildiği kayıt |
| `PassedCount` | Değerlendirilen ve kuralı karşılayan kayıt |
| `FailedCount` | Değerlendirilen ve kuralı karşılamayan kayıt |
| `ExcludedCount` | Kapsam dışı veya geçerli, süreli istisna nedeniyle dışlanan kayıt |
| `TechnicalErrorCount` | Uygulanabilir olduğu hâlde teknik nedenle değerlendirilemeyen kayıt |
| `UnknownCount` | Uygulanabilirliği iş verisi veya referans eksikliği nedeniyle belirlenemeyen kayıt |

Temel değişmezler:

```text
PopulationCount = EligibleCount + ExcludedCount + UnknownCount
EligibleCount = EvaluatedCount + TechnicalErrorCount
EvaluatedCount = PassedCount + FailedCount
RuleScore = PassedCount / EvaluatedCount * 100
```

`RuleScore` paydasına yalnız `EvaluatedCount` girer. Koşullu kural tüm dataset
yerine yalnız `EligibleCount` kapsamını ölçer. `ExcludedCount`; kapsam dışı ve
istisnalı kayıt alt kırılımlarını ayrıca saklar. Sayaç kaynağı teknik hata nedeniyle
belirlenemiyorsa tahmini sıfır yazılmaz; ilgili alan `NULL`, execution teknik
durumu ve güvenli hata kodu birlikte tutulur.

### Sıfır Payda Kararı

| Koşul | Kural skoru | Ölçüm durumu | Yeterlilik etkisi |
| --- | --- | --- | --- |
| Politika gereği kural uygulanamaz | `NULL` | `NotApplicable` | `NotApplicable` |
| Beklenen dönemde veri yok | `NULL` | `NoData` | Politika değerlendirmesine göre `NotQualified` veya `Stale`; değer `TBD` |
| Uygulanabilir kayıt var, ölçüm başlatılmadı | `NULL` | `NotMeasured` | `NotQualified` veya `ValidationRequired` |
| Teknik çalışma tamamlanmadı | `NULL` | `TechnicalError` | `TechnicalFailure` |
| Tüm uygun kayıtlar geçerli istisnada | `NULL` | `SuppressedByException` | Varsayılan `Qualified` değildir; politika ve istisna kanıtı değerlendirilir |

`NoData` otomatik başarı veya başarısızlık değildir. Beklenen verinin gelmemesi
ayrı tamlık veya zamanlılık kuralıyla kalite problemi oluşturabilir.

## 4. Boyut ve Dataset Skoru

Değerlendirilebilen boyutlar Tamlık, Geçerlilik, Tutarlılık, Benzersizlik,
Doğruluk, Güncellik/Zamanlılık ve Bütünlüktür. `DQ-SCR-003` kapsamındaki çekirdek
altı boyuta ek olarak Bütünlük, Mutabakat, Referans Bütünlüğü ve İzlenebilirlik
onaylı sözlükte kullanılabilir. Hiçbir boyut her dataset için kendiliğinden
zorunlu değildir; uygulanabilirlik sürümlü dataset politikasıyla belirlenir.

```text
DimensionScore = sum(RuleScore * RuleWeight) / sum(RuleWeight)
RawDatasetScore = sum(DimensionScore * DimensionWeight) / sum(DimensionWeight)
```

- Yalnız uygulanabilir ve sayısal sonucu bulunan kurallar/boyutlar aritmetik
  paydaya girer.
- `NotApplicable`, `NotMeasured`, `NoData`, `TechnicalError` ve
  `SuppressedByException` değerleri sıfır gibi eklenmez.
- Dışlanan bir bileşenin kimliği, durumu, ağırlığı ve dışlama gerekçesi açıklama
  kaydında korunur.
- Eksik zorunlu veya kritik bileşen, kalan sayısal skorun hesaplanmasını zorunlu
  olarak engellemeyebilir; fakat kapsamı ve ölçüm yeterliliğini düşürür.
- Ağırlıklar dataset türü, iş kritiklik profili ve kullanım bağlamına göre
  sürümlü politikadan çözülür. Dataset kritikliği ham skorun içine katılmaz.

## 5. Kritik Kural Kapısı ve Nihai Sonuç

Proje için seçilen model, sürümlü politika tarafından yönetilen katmanlı kritik
kural kapısıdır. Kritik başarısızlık yalnız ağırlıklı ortalamaya bırakılmaz.

| Değerlendirilen mekanizma | Kullanım kararı |
| --- | --- |
| Skor tavanı | Ham skoru koruyup nihai skorun kritik başarısızlığı gizlememesini sağlar; politika tanımlarsa uygulanır |
| Bloke edici kural | Sayısal skordan bağımsız `UsageDecision` üretir; kullanım bağlamı ve yetki politikası zorunludur |
| Minimum zorunlu boyut skoru | Dataset politikası ilgili boyutu zorunlu kılmışsa yeterlilik/kullanım kapısı olabilir |
| Kritik hata toleransı | Yalnız açık, sürümlü ve onaylı toleransla kullanılabilir; örtük tolerans yoktur |
| Kritik kural geçiş zorunluluğu | Zorunlu kritik kural değerlendirilememiş veya başarısızsa olumlu yeterlilik kararı verilmez |
| Kullanım amacı bazlı uygunluk | Aynı ölçümün farklı kullanım bağlamlarında farklı kullanım kararı almasını sağlar |

Bu mekanizmalar birbirinin alternatifi olarak tek bir sabit seçeneğe indirgenmez.
Proje için seçilen katmanlı model; ham skoru değişmez tutar, onaylıysa tavanlı
nihai skor üretir ve kritik durum ile kullanım kararını ayrı alanlarda taşır.

Politika aşağıdaki etkileri birlikte veya ayrı tanımlayabilir:

1. `FinalQualityScore` için ham skordan düşük veya ona eşit bir skor tavanı,
2. `QualityStatus` için zorunlu başarısızlık durumu,
3. `UsageDecision` için koşullu kullanım veya blokaj,
4. kritik kalite alarmı ve remediation kaydı,
5. kullanım devamı için risk bazlı maker-checker kararı.

```text
FinalQualityScore = min(RawQualityScore, ApplicableScoreCap)
```

Skor tavanı yoksa `FinalQualityScore = RawQualityScore` olur. Bloke edici kural
skoru değiştirmek zorunda değildir; blokaj `UsageDecision` alanında görünür.
Manuel değerlendirme/override ham veya nihai skoru değiştirmez.

| Sonuç | Anlam |
| --- | --- |
| `RawQualityScore` | İki aşamalı ağırlıklı ölçüm sonucu |
| `FinalQualityScore` | Kritik tavan uygulanmış sayısal sonuç |
| `QualityStatus` | Sürümlü eşik ve kritik durum etiketi |
| `CriticalRuleStatus` | `Passed`, `Failed`, `NotEvaluated`, `NotApplicable` |
| `UsageDecision` | `Allowed`, `ConditionallyAllowed`, `Blocked`, `Undetermined` |

Kritik politika bulunamazsa sistem olumlu kullanım kararı üretmez;
`UsageDecision=Undetermined` ve `MeasurementQualificationStatus=NotQualified`
uygulanır. Hangi aktörün hangi kullanım bağlamını bloke edebileceği `TBD`'dir.

## 6. Ölçüm Yeterliliği

Ölçüm yeterliliği kalite skorundan bağımsız, açıklanabilir bir kapıdır:

| Durum | Koşul özeti |
| --- | --- |
| `Qualified` | Tüm zorunlu anlam, kapsam, örneklem, teknik başarı, güncellik, sürüm, kanıt, kritik kontrol, test ve onay koşulları sağlanır |
| `ProvisionallyQualified` | Onaylı politika kısmi/sınırlı sonucu süreli ve açık kısıtlarla belirli kullanımda kabul eder |
| `LimitedCoverage` | Sayısal skor vardır fakat onaylı minimum kapsam veya örneklem yeterliliği sağlanmaz |
| `Stale` | Sonuç `ValidUntil` zamanını aşmıştır veya gerekli güncel ölçüm yoktur |
| `ValidationRequired` | İş anlamı, veri sahibi doğrulaması, backtest veya gerekli onay tamamlanmamıştır |
| `TechnicalFailure` | Çalıştırma teknik olarak tamamlanmadığı için güncel ölçüm üretilememiştir |
| `NotQualified` | Zorunlu politika, sürüm, kanıt, kritik kontrol veya güvenlik koşulu sağlanmamıştır |
| `NotApplicable` | Ölçüm bu dataset/kullanım bağlamı için politika gereği uygulanamaz |

### Değerlendirme Önceliği

1. Kapsam uygulanamazsa `NotApplicable`.
2. Güncel çalışma teknik olarak tamamlanamadıysa `TechnicalFailure`.
3. Zorunlu politika, izlenebilirlik veya kritik kontrol eksikse `NotQualified`.
4. İş doğrulaması, test veya onay eksikse `ValidationRequired`.
5. Geçerlilik süresi dolduysa `Stale`.
6. Kapsam/örneklem eşiği sağlanmadıysa `LimitedCoverage`.
7. Onaylı kısmi kullanım politikası tüm koşulları sağlıyorsa
   `ProvisionallyQualified`.
8. Tüm zorunlu koşullar sağlanıyorsa `Qualified`.

Yüksek kalite skoru bu sıralamayı aşamaz. Önceki başarılı skor görüntülenebilir,
ancak yeni ölçüm gibi işlenmez; kendi ölçüm zamanı ve yeterlilik durumu korunur.

### Durum Geçişleri

| Mevcut | Olay | Sonraki | Koşul |
| --- | --- | --- | --- |
| Her durum | Kapsamın uygulanamaz olması | `NotApplicable` | Sürümlü uygulanabilirlik politikası |
| `ValidationRequired` | Zorunlu doğrulama/onay tamamlandı | Yeniden değerlendirme | Yeni yeterlilik kaydı oluşturulur |
| `LimitedCoverage` | Yeterli kapsamlı yeniden ölçüm | `Qualified` veya `ProvisionallyQualified` | Tüm diğer kapılar sağlanır |
| `Qualified` | `ValidUntil` aşılır | `Stale` | Zaman kaynağı ve politika sürümü sabittir |
| Her ölçülebilir durum | Teknik yeniden çalışma başarısız | `TechnicalFailure` | Önceki kayıt değiştirilmez |
| Her durum | Kural/politika/referans sürümü değişir | `ValidationRequired` | Etki analizine göre yeniden ölçüm gerekir |
| Her yetersiz durum | Başarılı yeniden ölçüm | Yeniden değerlendirme | Eski kayıt korunur, yeni kayıt bağlanır |

## 7. Kapsam, Örnekleme, Güven ve Güncellik

| Alan | Zorunlu davranış |
| --- | --- |
| `CoverageRate` | Ölçüm yöntemine göre politika tanımlı ölçülen kapsam / tanımlı evren oranıdır; kesin pay/payda sözleşmesi ve üretim eşiği `OPEN-023` kapsamında `TBD`'dir |
| `CoverageStatus` | `Sufficient`, `Limited`, `Unknown`, `NotApplicable`; kesin eşikler `TBD` |
| `SamplingMethod` | `FullScan`, `Sample`, `Incremental`, `Partitioned`, `SourceAggregate` |
| `SampleSize` / `PopulationSize` | Biliniyorsa saklanır; tahminse yöntem ve hata payı belirtilir |
| `ConfidenceLevel` | Yalnız doğrulanmış örnekleme yöntemi üretebilir; kesin minimum `TBD` |
| `EvidenceCompleteness` | Sayaç, sürüm, snapshot ve audit kanıtının tamamlık durumu |
| `LastSuccessfulRunAt` | Son teknik olarak başarılı ve skor üreten çalışma zamanı |
| `ValidUntil` | Ölçüm politikası ve iş tarihi üzerinden üretilen geçerlilik sonu; süre `TBD` |

Tam tarama, kontrollü örnekleme, artımlı kontrol, bölümleme ve kaynakta toplulaştırma
aynı güven iddiasıyla sunulmaz. Örnekleme yöntemi, büyüklüğü, kapsanan dönem,
dağılım ve güven düzeyi yeniden üretilebilir kanıtın parçasıdır.

## 8. Teknik Çalışma Durumu

Kanonik teknik durumlar:

| Durum | Skor davranışı |
| --- | --- |
| `Completed` | Sayaçlar doğrulanır ve skor/yeterlilik hesaplanabilir |
| `PartialSuccess` | Yalnız onaylı kısmi politika kapsamında sayısal sonuç üretilebilir |
| `TechnicalFailure` | Güncel kalite skoru `NULL`; teknik olay üretilir |
| `TimedOut` | Güncel skor varsayılan olarak `NULL`; tamamlanan bölüm varsa kısmi politika değerlendirilir |
| `AccessDenied` | Skor yok; güvenlik/teknik olay ve veri-minimum audit |
| `SourceUnavailable` | Skor yok; retry ve teknik alarm politikası |
| `Cancelled` | Yeni skor yok; iptal nedeni ve aktör/audit referansı |

Fiziksel runtime enumları bu sözlüğe sürümlü adapter ile eşlenir. Teknik hata
sayısal sıfıra veya kalite alarmına dönüştürülmez.

## 9. Politika Modeli

Mevcut `ScoringPolicy` ve `DatasetPartialScorePolicy` genişletilir; paralel bir
politika altyapısı kurulmaz.

| Alan grubu | Alanlar |
| --- | --- |
| Kapsam | `dataset_id`, `dataset_type`, `business_criticality`, `usage_context`, `rule_id`, `dimension` |
| Ağırlık ve eşik | `rule_weight`, `dimension_weight`, `minimum_acceptable_score`, `warning_threshold`, `critical_threshold` |
| Kritik davranış | `criticality`, `blocking_flag`, `score_cap`, zorunlu kritik kural/boyut |
| Uygulanabilirlik | `applicability_condition`, istisna sınıfı, bilinmeyen kayıt davranışı |
| Ölçüm yeterliliği | `minimum_coverage_rate`, `sampling_policy`, `minimum_confidence_level`, `evidence_requirements` |
| Güncellik | `freshness_sla`, `result_validity_period`, `freshness_hard_limit` |
| Teknik davranış | `technical_failure_behavior`, retry/timeout referansı, son başarılı skor gösterimi |
| Aksiyon | `notification_policy`, `remediation_sla`, kullanım kararı politikası |
| Yönetişim | `effective_from`, `effective_to`, `policy_version`, `approval_status`, gerekçe, maker/checker ve audit referansı |

Politika yokluğu, eksik sürüm veya çelişkili etkin kayıt fail-closed yeterlilik
kararı üretir: skor hesaplanabilse bile `NotQualified` ve `UsageDecision=Undetermined`.
Sayısal üretim değerleri açık kararlar tamamlanana kadar `TBD` kalır.

## 10. Veri Modeli ve İzlenebilirlik

Hedef model mevcut varlıkları genişletir:

| Varlık | Sorumluluk |
| --- | --- |
| `RuleExecution` | Teknik durum, dataset/snapshot/iş tarihi, başlangıç/bitiş ve uygulama sürümü |
| `RuleResult` | Evren, uygunluk, değerlendirme, başarı/başarısızlık, dışlama, teknik ve bilinmeyen sayaçlar |
| `QualityScore` | Ham/nihai skor, kalite ve kritik durum, kullanım kararı, tüm model/politika sürümleri |
| `MeasurementQualificationResult` | Yeterlilik durumu, başarısız kapılar, kapsam/güven, geçerlilik ve kanıt tamamlığı |
| `ScoreMeasurementSummary` | Kapsam ve örnekleme metrikleri; qualification kaydına girdi |
| `ScoringPolicy` | Hesaplama, kritik kapı, yeterlilik, güncellik ve aksiyon politikaları |
| `DataQualityException` | Süreli ve auditli dışlama |
| `ScoreAssessmentOverride` | Ham/nihai skoru değiştirmeyen onaylı değerlendirme |
| `FailedRecordEvidenceReference` | Maskeli özet, hash, kontrollü örnek veya opak güvenli kanıt referansı |
| `ApprovalRecord` | Kural/politika/yeterlilik değişikliği için maker-checker karar izi |
| `DataQualityIssue` | Kalite/teknik olay ayrımı, remediation ve yeniden ölçüm kanıtı |
| `Notification` / `EscalationRecord` | Ayrı olay türü, alıcı, deduplication, eskalasyon ve güvenli referans |

Her dataset sonucu en az `execution_id`, `dataset_id`, `snapshot_id`,
`business_date`, `rule_set_version`, `policy_version`, `reference_data_version`,
`scoring_algorithm_version`, `application_version`, `started_at`, `completed_at`,
sayaçlar, ham/nihai skor, yeterlilik ve teknik durum bağlarını taşır.

Başarısız kayıtların tamamı varsayılan olarak saklanmaz. Yetki dâhilinde maskeli
özet, hash, kontrollü örnek veya opak güvenli referans kullanılır. Kanıt kaydı ham
kişisel veri, müşteri sırrı, banka sırrı, secret, kaynak SQL veya stack trace içermez.

## 11. İş Akışları

1. **Kural tanımlama:** İş anlamı, uygulanabilirlik, boyut, sahip ve sürümle taslak oluşturulur.
2. **Kural doğrulama:** Teknik test, örnek veri testi, backtest ve veri sahibi doğrulaması kaydedilir.
3. **Kural onaylama:** Risk bazlı maker-checker sonrası kural sürümü etkinleşir.
4. **Politika atama:** Dataset/kullanım bağlamına uygun, sürümlü ve onaylı politika çözülür; yokluk fail-closed olur.
5. **Zamanlanmış ölçüm:** Zamanlama, snapshot ve iş tarihiyle güvenilir execution başlatılır.
6. **İsteğe bağlı ölçüm:** Yetkili istek idempotency ve kaynak kullanım politikasıyla execution başlatır.
7. **Teknik başarısızlık yönetimi:** Teknik durum, güvenli hata kodu, retry ve alarm üretilir; kalite başarısızlığı yazılmaz.
8. **Kalite başarısızlığı yönetimi:** Sayaçlar doğrulanır; kural, boyut ve dataset kalite sonucu ile kalite olayı üretilir.
9. **Kritik kural başarısızlığı:** Kritik kapı nihai skor, kritik durum ve kullanım kararını politikaya göre ayrı üretir.
10. **Bildirim:** Kalite, teknik ve yeterlilik olayları farklı türlerde, idempotent ve veri-minimum bildirim oluşturur.
11. **Düzeltme görevi:** Issue kök neden, sorumlu, hedef ve kanıt gereksinimiyle açılır; ServiceNow gerekiyorsa dayanıklı outbound kullanır.
12. **Eskalasyon:** Çözülmeyen olay politika süresi ve sahiplik kuralıyla eskale edilir; süre ve alıcı değerleri `TBD` olabilir.
13. **Yeniden ölçüm:** Eski sonucu değiştirmeyen yeni execution/score/qualification zinciri oluşturulur.
14. **Kapanış ve kanıt:** Yalnız politika gerektirdiği doğrulama, kalıcılık ve yeterli yeniden ölçüm kanıtı tamamlanınca kapanış yapılır.
15. **Değişiklik sonrası yeniden değerlendirme:** Kural, politika veya referans sürümü değişince tarihsel sonuçlar sessizce yazılmaz; etkilenen kapsam için yeniden değerlendirme ihtiyacı oluşturulur.

## 12. API Sözleşme Yüzeyi

Skor okuma yanıtı tek `score` alanıyla sınırlanmaz:

```text
execution_status
measurement_status
measurement_qualification_status
raw_quality_score
final_quality_score
quality_status
critical_rule_status
usage_decision
coverage_rate
coverage_status
sampling_method
sample_size
population_size
confidence_level
evidence_completeness
last_successful_run_at
valid_until
dimension_scores
contributing_rules
excluded_components
policy_version
rule_set_version
reference_data_version
scoring_algorithm_version
application_version
```

API; kural/boyut/dataset sonucu, kritik başarısızlık, katkı açıklaması, politika
ve sürüm, kontrollü hata örneği, geçmiş karşılaştırma, yeniden ölçüm, remediation
ve kapanış sorgularını yetki kapsamıyla sunar. Yeniden ölçüm idempotent olur.
Hassas kanıt erişimi ayrı yetki, gerekçe ve audit gerektirir.

## 13. UI ve Raporlama

Dashboard ve raporlar şu bilgileri ayrı gösterir:

- ham ve nihai kalite skoru,
- kalite, kritik kural, yeterlilik ve teknik çalışma durumları,
- kullanım kararı,
- kapsam ve güven,
- son başarılı ölçüm ve `ValidUntil`,
- en çok etki eden kurallar ve başarısız boyutlar,
- istisna/override ve sürüm sınırları,
- trend ve yeniden ölçüm bağlantısı.

`TechnicalFailure`, `Stale`, `LimitedCoverage`, `ValidationRequired` ve
`NotQualified` düşük kalite skoru gibi kırmızı yüzdeye çevrilmez. Renk yanında
ikon ve metin kullanılır; grafiklerin erişilebilir tablo karşılığı bulunur.

## 14. Güvenlik ve Bankacılık Kontrolleri

- Kaynak sorguları salt okunur ve kaynak kullanım politikası kontrollüdür.
- Kural, eşik, ağırlık, kritik davranış, kapsam, yeterlilik, istisna ve override
  değişiklikleri yetki matrisi ve risk bazlı maker-checker ile korunur.
- Ham/nihai skor doğrudan kullanıcı girdisiyle değiştirilemez.
- Yetkisiz detay erişimi repository sorgusundan önce reddedilir.
- Audit yazma veya kalıcı outbox kritik değişiklikte başarısızsa işlem fail-closed
  olur.
- Kanıt, log, bildirim, rapor ve ServiceNow payloadı veri-minimumdur.
- Saklama ve imha kayıt sınıfı politikasından gelir; süreler `TBD` olabilir.
- Break-glass veya ayrıcalıklı erişim olağan yeterlilik/onay kontrolünü sessizce
  aşamaz; ayrı gerekçe, süre ve audit gerektirir.
- `OPEN-BNK` kayıtları teknik tasarımla otomatik kapanmaz.

## 15. Test Yaklaşımı

Zorunlu test sınıfları:

1. Sayaç değişmezleri, koşullu uygunluk ve sıfır payda,
2. kural, boyut, ham ve nihai dataset formülleri,
3. kritik tavan, blokaj ve politika yokluğu,
4. sekiz ölçüm ve sekiz yeterlilik durumu,
5. teknik durumların kalite sonucundan ayrılması,
6. kapsam, örneklem, güven, güncellik ve `ValidUntil`,
7. politika/kural/referans/algoritma sürümleri ve replay,
8. yetkisiz erişim, maker=checker, audit rollback ve maskeleme,
9. bildirim, remediation, eskalasyon, yeniden ölçüm ve kapanış,
10. büyük veri/örnekleme için tekrarlanabilir performans kanıtı.

Sentetik kabul verisinde expected sonuç runtime kural veya skor motorundan
türetilmez. `SyntheticGroundTruth`, aynı sürümlü politika ve yuvarlama
sözleşmesini bağımsız oracle ile uygular; expected-versus-actual karşılaştırıcı
kural sonucu, ham/nihai skor, önem ve olay sapmasını ölçer. Geçerli nadir/sınır
değerler skoru düşürmemeli; teknik arıza kalite başarısızlığına çevrilmemelidir.
Nicel skor toleransı `OPEN-024` sonuçlanana kadar `TBD`'dir. Ayrıntılar
[Sentetik Veri ve Gizlilik Stratejisi](Sentetik-Veri-ve-Gizlilik-Stratejisi.md)
belgesindedir.

## 16. Sentetik Hesaplama Örneği

Bu değerler yalnız formülü göstermek içindir; üretim politikası değildir.

```text
PopulationCount = 1000
EligibleCount = 800
ExcludedCount = 150
UnknownCount = 50
EvaluatedCount = 780
TechnicalErrorCount = 20
PassedCount = 741
FailedCount = 39
RuleScore = 741 / 780 * 100 = 95.00
IllustrativeCoverageRate = 780 / 1000 * 100 = 78.00
```

İki kural skoru `95` ve `80`, ağırlıkları `2` ve `1` ise boyut skoru `90.00`;
iki boyut skoru `90` ve `85`, ağırlıkları `2` ve `1` ise ham dataset skoru
`88.33` olur. Sentetik kritik politika tavanı `60` ise nihai skor `60.00` olur;
ham skor `88.33` olarak korunur. Yalnız bu örnek için seçilen sentetik minimum
kapsam `80` iken gösterim amaçlı kapsam `78`
ise kalite skoru var olsa da yeterlilik `LimitedCoverage` olur. Bu `60` ve `80`
değerleri üretim için bağlayıcı değildir.

## 17. İzlenebilirlik Özeti

| Zincir | Bağlantı |
| --- | --- |
| İş hedefi → gereksinim | BR-001/002/005/006 → FR-046–FR-053 |
| Gereksinim → politika | FR-047–FR-052 → ScoringPolicy / DatasetPartialScorePolicy |
| Politika → veri modeli | Politika sürümü → RuleResult / QualityScore / MeasurementQualificationResult |
| Veri modeli → API/UI | Skor ve yeterlilik alanları → FR-080 / Dashboard ekran sözleşmesi |
| Gereksinim → test | FR-046–FR-053 → AC/TS-027–AC/TS-047 |
| Kural → boyut → dataset | RuleResult → DimensionScore → Raw/Final DatasetScore |
| Ölçüm koşulu → yeterlilik | Kapsam/örneklem/güncellik/sürüm/kanıt → MeasurementQualificationStatus |
| Kritik sonuç → iş akışı | CriticalRuleStatus → UsageDecision → alarm/issue/remediation/eskalasyon |
| Sentetik senaryo → bağımsız kabul | SyntheticGroundTruth → Expected-versus-Actual Comparator → AC/TS-050–052 |

## 18. Impact Matrix

| Kaynak dosya | Etkilenen bölüm | İlişki türü | Gerekli değişiklik | Gerekçe |
| --- | --- | --- | --- | --- |
| `01-SRS/04-Fonksiyonel-Gereksinimler/04.06-Skorlama.md` | FR-046–FR-053 | Doğrudan | Sayaç, ham/nihai skor ve yeterlilik | Bağlayıcı gereksinim |
| `01-SRS/05-Kullanim-Senaryolari/UC-009-Veri-kalite-skorunun-hesaplanmasi.md` | Akışlar | İş akışı | Ölçüm yeterliliği ve kullanım kararı | Uçtan uca hesaplama |
| `01-SRS/07-Veri-Modeli/Kural-ve-Calistirma-Varliklari.md` | Sonuç/politika varlıkları | Veri modeli | Yeni alan ve yeterlilik sonucu | Kalıcı izlenebilirlik |
| `01-SRS/07-Veri-Modeli/Veri-Modeli-Genel.md` | Varlık/ilişki haritası | Veri modeli | Yeterlilik ve ayrı sonuç ilişkileri | Model bütünlüğü |
| `01-SRS/07-Veri-Modeli/Sorun-Bildirim-ve-Audit-Varliklari.md` | Notification/Issue | Veri modeli ve iş akışı | Yeterlilik olayı ve sonuç bağı | Olay ayrımı |
| `01-SRS/04-Fonksiyonel-Gereksinimler/04.12-API-ve-Entegrasyon.md` | Skor API | API | Bağlamlı skor yanıtı | Tek skor alanını engelleme |
| `04-Frontend/03-Dashboard/Dashboard-Ekran-Sozlesmesi.md` | KPI/durumlar | UI | Yeterlilik, geçerlilik, ham/nihai skor | Yanıltıcı gösterimi engelleme |
| `01-SRS/10-Kabul-Kriterleri.md` | AC-039–AC-047 | Test | Ölçülebilir senaryolar | Doğrulanabilirlik |
| `01-SRS/11-Izlenebilirlik-Matrisi.md` | Skorlama zinciri | İzlenebilirlik | Kanonik belge ve yeni AC/TS bağları | Denetlenebilirlik |
| `06-Testler/TEST-INDEX.md` | Skorlama testleri | Test | Qualification test sınıfları | Otomasyon backlogu |
| `02-Mimari/Mantiksal-Mimari.md` | Skorlama motoru | Mimari | Ölçüm yeterliliği kapısı | Bileşen sorumluluğu |
| `02-Mimari/Sistem-Baglami.md` | Sistem davranışı | Mimari bağlam | Skor/yeterlilik/kullanım ayrımı | Sistem sınırı |
| `02-Mimari/Mimari-Kararlar.md` | ADR-015 | Mimari karar | Katmanlı kritik kapı ve yeterlilik | Karar kaynağı |
| `03-Backend/06-Skorlama/AGENTS.md` | Uygulama kuralları | Agent | Kanonik terim ve ayrım | Gelecek kod tutarlılığı |
| `04-Frontend/03-Dashboard/AGENTS.md` | Dashboard uygulama kuralları | Agent | Ayrı durum ve skor yüzeyleri | Gelecek UI tutarlılığı |
| `01-SRS/06-Is-Kurallari.md` | RULE-003–RULE-007 | İş kuralı | Sayaç, yeterlilik, olay ve sürüm | Domain tutarlılığı |
| `01-SRS/04-Fonksiyonel-Gereksinimler/04.07-Dashboard.md` | FR-054–FR-058 | UI gereksinimi | Ayrı skor/yeterlilik/kullanım/teknik görünümü | Yanıltıcı sunumu engelleme |
| `01-SRS/04-Fonksiyonel-Gereksinimler/04.08-Bildirim.md` | FR-059–FR-063 | İş akışı | Yeterlilik ve teknik olay ayrımı | Doğru bildirim sınıfı |
| `01-SRS/04-Fonksiyonel-Gereksinimler/04.09-Sorun-Yonetimi.md` | FR-064–FR-071 | İş akışı | Remediation ve yeterli kapanış kanıtı | Erken kapanışı engelleme |
| `01-SRS/04-Fonksiyonel-Gereksinimler/04.10-Raporlama.md` | FR-072–FR-076 | Raporlama | Ayrı skor/durum/geçerlilik alanları | Denetlenebilir rapor |
| `01-SRS/08-Harici-Arayuzler.md` | Dashboard/skor ekranı | Kavram ve UI uyumu | Kanonik alan ve durumlar | Arayüz tutarlılığı |
| `07-Operasyon/Surum-ve-Degisiklik-Yonetimi.md` | Skorlama değişiklik kapısı | Operasyon | Yeterlilik sürümü, regresyon ve rollback | Kontrollü üretim geçişi |
| `02-Mimari/Guvenlik/Maker-Checker.md` | Yüksek etkili değişiklikler | Güvenlik/yönetişim | Yeterlilik ve kullanım politikası değişikliği | Anti-gaming ve görevler ayrılığı |
| `docs/technical/02-Domain-ve-Veri-Modeli.md` | Hedef/runtime farkı | Teknik analiz | Yeni hedef varlık ve açık farklar | Uygulanmışlık doğruluğu |
| `docs/technical/03-API-ve-Entegrasyonlar.md` | Hedef API | Teknik analiz | Ayrı skor/yeterlilik/kullanım alanları | API backlog doğruluğu |
| `docs/technical/04-Guvenlik-ve-Uyumluluk.md` | Maker-checker hedefi | Teknik analiz | Yeterlilik politikası güvenlik farkı | Uygulanmışlık doğruluğu |
| `docs/technical/07-Riskler-ve-Yol-Haritasi.md` | Risk/backlog | Teknik analiz | Yetersiz ölçümün yanlış kullanımı | Risk görünürlüğü |
| `docs/technical/README.md` | Özellik durumu | Teknik analiz | Mevcut alt küme/hedef farkı | Uygulanmışlık doğruluğu |
| `00-Proje-Hafizasi/Mevcut-Durum.md` | Güncel durum | Proje hafızası | Tasarım ve runtime farkı | Yanlış tamamlandı iddiasını önleme |
| `00-Proje-Hafizasi/Alinan-Kararlar.md` | Karar kaydı | Proje hafızası | Ayrı yeterlilik hedefi | Karar izi |
| `00-Proje-Hafizasi/Acik-Konular.md` | Engeller | Proje hafızası | Runtime ve üretim değerleri | Belirsizlik görünürlüğü |
| `00-Proje-Hafizasi/Sonraki-Adimlar.md` | Backlog | Proje hafızası | Küçük runtime dilimleri | Artımlı geçiş |
| `00-Proje-Hafizasi/Bankacilik-Gecis-Durumu.md` | Geçiş boşluğu | Proje hafızası | Banka kararlarını açık koruma | Onay sınırı |
| `00-Proje-Hafizasi/Proje-Ozeti.md` | Skorlama ilkesi | Proje hafızası | Kanonik kısa tanım | Terminoloji |
| `01-SRS/15-Acik-Konular.md` | OPEN-022/023 | Açık karar | Migration ve yeterlilik değerleri | Değer uydurmayı engelleme |
| `README.md`, `01-SRS/SRS-INDEX.md`, `02-Mimari/MIMARI-INDEX.md`, `03-Backend/BACKEND-INDEX.md`, `04-Frontend/FRONTEND-INDEX.md` | Dizin bağlantıları | Referans | Kanonik belgeyi erişilebilir kılma | Doküman keşfi |

## 19. Açık Kararlar

- Üretim eşik, ağırlık, kritik tavan ve zorunlu boyut değerleri,
- ölçüm yöntemine göre kapsam pay/payda sözleşmesi, minimum kapsam ve örneklem güven seviyesi,
- `Qualified` için zorunlu kanıt ve onay matrisi,
- dataset/kullanım bağlamı bazlı `ValidUntil` süreleri,
- `UsageDecision` blokaj yetkileri ve downstream uygulama biçimi,
- remediation hedefleri ve eskalasyon süreleri,
- fiziksel enum/alan migration, backfill ve geriye alma planı,
- düzenleyici raporlama/risk zinciri kapsamı.

Bu konular `OPEN-019`–`OPEN-023` ve ilişkili `OPEN-BNK` kayıtlarıyla yönetilir.

## 20. Runtime Geçiş Durumu

`SOURCE_EQUAL_DATASET_QUALITY_V2`, yeni kaynak kalite skorlarında yalnız resmî
dataset kalite skorlarını eşit kalite ağırlığıyla toplar. Dataset kritikliği
hesaplama girdisi değildir; bileşen açıklamasında ayrı profil olarak ve
`used_in_quality_score=false` kanıtıyla taşınır. Formül ve ağırlık politikası
sonuç kaydında sürümlüdür.

Tarihsel `SOURCE_WEIGHTED_V1` kayıtları yerinde korunur ve sessizce yeniden
yazılmaz. Yeni modelle replay/backfill, orijinal skor ilişkisi, trend sürüm
sınırı, ayrı risk/güven/yeterlilik ve kullanım kararı alanları henüz runtime'a
taşınmamıştır; bunlar `OPEN-022/023` kapsamında kalır.
