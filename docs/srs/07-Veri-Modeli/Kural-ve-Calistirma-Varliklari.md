---
type: data-dictionary-group
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_document: Veri_Kalitesi_Izleme_ve_Skorlama_Sistemi_SRS_v0.1.md
source_version: "0.1"
source_section: "QualityRule, RuleVersion, RuleExecution, RuleResult, QualityScore, QualityDimension, Schedule"
created_at: 2026-07-16
tags:
  - srs
  - data-dictionary
  - execution
---

# Kural ve Çalıştırma Varlıkları

## QualityRule

| Alan adı | Veri tipi | Uzunluk | Zorunluluk | Benzersizlik | Varsayılan değer | Açıklama | Hassas veri durumu | Doğrulama kuralı |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| quality_rule_id | UUID | 36 | Evet | Evet | Otomatik | Mantıksal kural anahtarı | Hayır | UUID |
| code | VARCHAR | 120 | Evet | Evet | Yok | Kurumsal kural kodu | Hayır | Tanımlı biçim |
| name | VARCHAR | 250 | Evet | Hayır | Yok | Kural adı | Hayır | 1–250 karakter |
| business_justification | TEXT | — | Evet | Hayır | Yok | Kuralın iş gerekçesi | Hassas olabilir | Veri-minimum ve onaylı içerik |
| primary_dimension_id | UUID | 36 | Evet | Hayır | Yok | Birincil kalite boyutu | Hayır | Geçerli QualityDimension |
| owner_user_id | UUID | 36 | Aktif kuralda evet | Hayır | NULL | Veri sahibi/iş sahibi | Kişisel | Aktif User |
| technical_owner_user_id | UUID | 36 | Aktif kuralda evet | Hayır | NULL | Teknik uygulama sahibi | Kişisel | Aktif User |
| status | ENUM | 30 | Evet | Hayır | DRAFT | DRAFT/ACTIVE/PASSIVE/REVIEW_REQUIRED/ARCHIVED | Hayır | İzinli geçiş |

## RuleVersion

| Alan adı | Veri tipi | Uzunluk | Zorunluluk | Benzersizlik | Varsayılan değer | Açıklama | Hassas veri durumu | Doğrulama kuralı |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rule_version_id | UUID | 36 | Evet | Evet | Otomatik | Sürüm anahtarı | Hayır | UUID |
| quality_rule_id | UUID | 36 | Evet | Hayır | Yok | Kural referansı | Hayır | Geçerli QualityRule |
| version_no | INTEGER | 10 | Evet | Hayır | 1 | Artan sürüm | Hayır | >0 ve kural içinde benzersiz |
| rule_type | ENUM | 50 | Evet | Hayır | Yok | Şablon/SQL/regex vb. | Hayır | İzinli tür |
| definition | JSON/TEXT | — | Evet | Hayır | Yok | Kural mantığı ve parametreleri | Hassas olabilir | Salt okunur; şema doğrulaması |
| threshold_policy_version | VARCHAR | 80 | Evet | Hayır | Yok | Etkin eşik/tolerans politika sürümü | Hayır | Onaylı ve geçerli politika |
| weight_policy_version | VARCHAR | 80 | Evet | Hayır | Yok | Dataset kural ağırlığı politika sürümü | Hayır | Onaylı ve geçerli politika |
| threshold_snapshot | DECIMAL/JSON | — | Evet | Hayır | Yok | Çalıştırmada yeniden üretilebilirlik için uygulanan eşik/tolerans özeti | Hayır | Politika sürümüyle uyumlu |
| weight_snapshot | DECIMAL | 10,4 | Evet | Hayır | Yok | Çalıştırmada uygulanan pozitif ağırlık özeti | Hayır | >0 ve politika sürümüyle uyumlu |
| criticality | ENUM | 20 | Evet | Hayır | MEDIUM | Kritiklik | Hayır | İzinli enum |
| schedule_policy_reference | UUID/VARCHAR | — | Evet | Hayır | Yok | Ölçüm sıklığı/çalışma politikası referansı | Hayır | Onaylı ve sürümlü politika |
| effective_from / effective_to | TIMESTAMP | — | Evet/Hayır | Hayır | Yok/NULL | Kural sürümünün geçerlilik aralığı | Hayır | Başlangıç bitişten önce |
| approval_status / approved_by | ENUM/UUID | — | Evet/Koşullu | Hayır | DRAFT/NULL | Üretim etkinleştirme onayı | Kişisel olabilir | Risk bazlı maker-checker |
| created_at | TIMESTAMP | — | Evet | Hayır | Otomatik | Sürüm zamanı UTC | Hayır | Değişmez |

## RuleExecution

| Alan adı | Veri tipi | Uzunluk | Zorunluluk | Benzersizlik | Varsayılan değer | Açıklama | Hassas veri durumu | Doğrulama kuralı |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| execution_id | UUID | 36 | Evet | Evet | Otomatik | Çalıştırma anahtarı | Hayır | UUID |
| dataset_id | UUID | 36 | Evet | Hayır | Yok | Ölçülen dataset | Hayır | Geçerli Dataset |
| snapshot_id | VARCHAR | 200 | Koşullu | Hayır | NULL | Snapshot/partition veya doğrulama hash'i | Hassas olabilir | Ham veri içermeyen opak referans |
| business_date | DATE/TIMESTAMP | — | Evet | Hayır | Yok | Ölçümün iş tarihi/dönemi | Hayır | Politika saat dilimiyle uyumlu |
| execution_type | ENUM | 30 | Evet | Hayır | MANUAL | MANUAL/SCHEDULED/TEST/PROFILE | Hayır | İzinli enum |
| status | ENUM | 40 | Evet | Hayır | QUEUED | QUEUED/RUNNING/COMPLETED/PARTIAL_SUCCESS/TECHNICAL_FAILURE/TIMED_OUT/ACCESS_DENIED/SOURCE_UNAVAILABLE/CANCELLED | Hayır | Kanonik geçiş; mevcut fiziksel enum migration ile eşlenir |
| idempotency_key | VARCHAR | 200 | Evet | Koşullu benzersiz | Otomatik | Çift çalıştırma önleme anahtarı | Hassas olabilir | Payload hash ile eşleşir |
| started_at | TIMESTAMP | — | Hayır | Hayır | NULL | Başlangıç UTC | Hayır | Bitişten önce |
| completed_at | TIMESTAMP | — | Hayır | Hayır | NULL | Bitiş UTC | Hayır | Başlangıçtan sonra |
| triggered_by | UUID | 36 | Hayır | Hayır | NULL | Kullanıcı/servis hesabı | Kişisel | Geçerli User veya sistem |
| error_class | VARCHAR | 100 | Hayır | Hayır | NULL | Teknik hata sınıfı | Hassas olabilir | Onaylı hata sözlüğü |
| application_version | VARCHAR | 80 | Evet | Hayır | Yok | Çalıştırıcı uygulama sürümü | Hayır | Değişmez |

## RuleResult

| Alan adı | Veri tipi | Uzunluk | Zorunluluk | Benzersizlik | Varsayılan değer | Açıklama | Hassas veri durumu | Doğrulama kuralı |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rule_result_id | UUID | 36 | Evet | Evet | Otomatik | Sonuç anahtarı | Hayır | UUID |
| execution_id | UUID | 36 | Evet | Hayır | Yok | Çalıştırma referansı | Hayır | Geçerli RuleExecution |
| rule_version_id | UUID | 36 | Evet | Hayır | Yok | Çalışan kural sürümü | Hayır | Geçerli RuleVersion |
| population_count | BIGINT | 19 | Koşullu | Hayır | NULL | İş tarihi/snapshot toplam aday evreni | Hayır | ≥0 veya teknik olarak bilinmiyorsa NULL |
| eligible_count | BIGINT | 19 | Koşullu | Hayır | NULL | Uygulanabilir kayıt | Hayır | ≥0 veya bilinmiyorsa NULL |
| evaluated_count | BIGINT | 19 | Koşullu | Hayır | NULL | Başarı/başarısızlık üretilen kayıt | Hayır | ≥0 veya bilinmiyorsa NULL |
| passed_count | BIGINT | 19 | Evet | Hayır | 0 | Başarılı kayıt | Hayır | ≥0 |
| failed_count | BIGINT | 19 | Evet | Hayır | 0 | Hatalı kayıt | Hayır | ≥0 |
| exception_count | BIGINT | 19 | Evet | Hayır | 0 | Geçerli istisna nedeniyle skor paydasından ayrılan kayıt | Hayır | ≥0 |
| out_of_scope_count | BIGINT | 19 | Evet | Hayır | 0 | Kural kapsamı dışında kalan kayıt | Hayır | ≥0 |
| excluded_count | BIGINT | 19 | Koşullu | Hayır | NULL | İstisna ve kapsam dışı kayıt toplamı | Hayır | exception + out_of_scope ile uyumlu |
| technical_error_count | BIGINT | 19 | Koşullu | Hayır | NULL | Teknik nedenle değerlendirilemeyen uygulanabilir kayıt | Hayır | ≥0 veya teknik olarak bilinmiyorsa NULL |
| unknown_count | BIGINT | 19 | Koşullu | Hayır | NULL | Uygulanabilirliği semantik nedenle bilinmeyen kayıt | Hayır | ≥0 veya bilinmiyorsa NULL |
| measurement_status | ENUM | 40 | Evet | Hayır | NOT_MEASURED | PASSED/WARNING/FAILED/NOT_APPLICABLE/NOT_MEASURED/NO_DATA/TECHNICAL_ERROR/SUPPRESSED_BY_EXCEPTION | Hayır | İzinli durum |
| normalization_policy_version | VARCHAR | 80 | Koşullu | Hayır | NULL | Kural skorunda kullanılan normalizasyon sürümü | Hayır | Sayısal skorda zorunlu |
| sample_evidence | JSON | — | Hayır | Hayır | NULL | Maskeli örnek/kanıt | Hassas | Maskeleme zorunlu |

Sayaçlar `DQ-SCR-004` ve kanonik tasarım uyarınca
`population = eligible + excluded + unknown`,
`eligible = evaluated + technical_error` ve
`evaluated = passed + failed` eşitlikleriyle doğrulanır. Sayaç teknik nedenle
bilinmiyorsa tahmini sıfır kullanılmaz.

## QualityScore

| Alan adı | Veri tipi | Uzunluk | Zorunluluk | Benzersizlik | Varsayılan değer | Açıklama | Hassas veri durumu | Doğrulama kuralı |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| quality_score_id | UUID | 36 | Evet | Evet | Otomatik | Skor anahtarı | Hayır | UUID |
| scope_type | ENUM | 30 | Evet | Hayır | RULE | RULE/DATA_ELEMENT/DIMENSION/DATASET/DATA_PRODUCT/REPORT/DATA_DOMAIN/SOURCE/ENTERPRISE | Hayır | İzinli enum |
| scope_id | UUID | 36 | Hayır | Hayır | NULL | Kapsam nesnesi; kurum skorunda NULL | Hayır | Scope type ile uyumlu |
| raw_score_value | DECIMAL | 5,2 | Hayır | Hayır | NULL | Ağırlıklı ham 0–100 kalite skoru | Hayır | 0–100 veya NULL |
| final_score_value | DECIMAL | 5,2 | Hayır | Hayır | NULL | Kritik skor tavanı sonrası sonuç | Hayır | 0–100, ham skordan büyük değil veya NULL |
| measurement_status | ENUM | 50 | Evet | Hayır | NOT_MEASURED | PASSED/WARNING/FAILED/NOT_APPLICABLE/NOT_MEASURED/NO_DATA/TECHNICAL_ERROR/SUPPRESSED_BY_EXCEPTION/PARTIAL/CONFIG_ERROR | Hayır | İzinli enum; fiziksel kod eşlemesi sürümlü |
| quality_status | ENUM | 30 | Hayır | Hayır | NULL | Sürümlü eşik/kritik politikasının kalite etiketi | Hayır | Eşik politika sürümüyle uyumlu |
| critical_rule_status | ENUM | 30 | Evet | Hayır | NOT_EVALUATED | PASSED/FAILED/NOT_EVALUATED/NOT_APPLICABLE | Hayır | Kritik politika ile uyumlu |
| usage_decision | ENUM | 30 | Evet | Hayır | UNDETERMINED | ALLOWED/CONDITIONALLY_ALLOWED/BLOCKED/UNDETERMINED | Hayır | Kullanım bağlamı politikasıyla uyumlu |
| score_model_version | VARCHAR | 80 | Evet | Hayır | Yok | Skor modeli/formül sürümü | Hayır | Değişmez |
| threshold_policy_version | VARCHAR | 80 | Koşullu | Hayır | NULL | Kullanılan eşik sürümü | Hayır | Sınıflandırılmış skorda zorunlu |
| weight_policy_version | VARCHAR | 80 | Koşullu | Hayır | NULL | Kullanılan ağırlık sürümü | Hayır | Toplulaştırılmış skorda zorunlu |
| normalization_policy_version | VARCHAR | 80 | Koşullu | Hayır | NULL | Kullanılan normalizasyon sürümü | Hayır | Normalleştirilmiş skorda zorunlu |
| application_version | VARCHAR | 80 | Evet | Hayır | Yok | Hesaplamayı yapan uygulama sürümü | Hayır | Değişmez |
| rule_set_version | VARCHAR | 80 | Evet | Hayır | Yok | Kullanılan kural seti sürümü | Hayır | Değişmez |
| reference_data_version | VARCHAR | 80 | Koşullu | Hayır | NULL | Referans veri/kod listesi sürümü | Hassas olabilir | Ham referans değer içermez |
| scoring_algorithm_version | VARCHAR | 80 | Evet | Hayır | Yok | Hesaplama algoritması sürümü | Hayır | Değişmez |
| original_score_id | UUID | 36 | Hayır | Hayır | NULL | Yeniden hesaplanan sonuçta korunan orijinal skor | Hayır | Geçerli QualityScore |
| calculation_details | JSON | — | Evet | Hayır | {} | Formül, dahil/dışlanan öğe, kritik kural kararı ve sürüm özeti | Hayır | Şema doğrulaması; ham/hassas kayıt yok |
| calculated_at | TIMESTAMP | — | Evet | Hayır | Otomatik | Hesap zamanı UTC | Hayır | Geçerli zaman |

`raw_score_value` yalnız ağırlıklı kalite ölçümünü taşır. `final_score_value`
yalnız sürümlü kritik skor tavanını uygular; manuel değerlendirme değildir.
Dataset kritiklik profili, ölçüm yeterliliği/kapsamı/güveni, veri riski, teknik
sağlık ve onaylı değerlendirme/override bu değerlere eritilmez
(`DQ-SCR-018`–`DQ-SCR-023`). `SOURCE` ve
`ENTERPRISE` kayıtları portföy görünümüdür; kural → veri öğesi → boyut → dataset
kırılımlarının yerine geçmez.

## QualityDimension

| Alan adı | Veri tipi | Uzunluk | Zorunluluk | Benzersizlik | Varsayılan değer | Açıklama | Hassas veri durumu | Doğrulama kuralı |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dimension_id | UUID | 36 | Evet | Evet | Otomatik | Boyut anahtarı | Hayır | UUID |
| code | ENUM | 40 | Evet | Evet | Yok | COMPLETENESS/VALIDITY/ACCURACY/CONSISTENCY/UNIQUENESS/TIMELINESS; isteğe bağlı RECONCILIATION/REFERENTIAL_INTEGRITY/TRACEABILITY/DATA_INTEGRITY | Hayır | Onaylı sözlük |
| name_tr | VARCHAR | 80 | Evet | Evet | Yok | Türkçe ad | Hayır | Onaylı sözlük |
| applicability_status | ENUM | 30 | Evet | Hayır | NOT_MEASURED | APPLICABLE/NOT_APPLICABLE/NOT_MEASURED | Hayır | Dataset politikasıyla uyumlu |
| is_active | BOOLEAN | 1 | Evet | Hayır | TRUE | Kurumsal sözlükte boyut etkinliği | Hayır | Boolean |

Boyut ağırlığı `QualityDimension` sözlüğünde sabit tutulmaz; sürümlü dataset
ağırlık politikası üzerinden çözülür. `NotApplicable` boyut başarısız sayılmaz ve
ağırlığı yalnız tanımlı yeniden dağıtım politikasıyla ele alınır (`DQ-SCR-003`,
`DQ-SCR-015`).

## ScoreMeasurementSummary

| Alan adı | Veri tipi | Zorunluluk | Açıklama |
| --- | --- | --- | --- |
| measurement_summary_id | UUID | Evet | Ölçüm özeti anahtarı |
| quality_score_id | UUID | Evet | Ham/nihai kalite sonucu referansı |
| coverage_rate | DECIMAL | Evet | Sürümü belirtilen kapsam formülünün sonucu |
| coverage_status | ENUM | Evet | SUFFICIENT/LIMITED/UNKNOWN/NOT_APPLICABLE |
| confidence_level | ENUM/DECIMAL | Evet | Kalite skorundan ayrı ölçüm güven seviyesi |
| confidence_policy_version | VARCHAR | Evet | Kapsam/güven formülü ve ağırlık sürümü |
| executed_rule_ratio | DECIMAL | Evet | Çalışan kural oranı |
| technical_error_ratio | DECIMAL | Evet | Teknik hata oranı; kalite başarısızlığı değildir |
| sampling_method | ENUM | Hayır | FULL_SCAN/SAMPLE/INCREMENTAL/PARTITIONED/SOURCE_AGGREGATE |
| sample_size | BIGINT | Hayır | Örneklem büyüklüğü |
| population_size | BIGINT | Hayır | Bilinen veya yöntemle tahmin edilen evren büyüklüğü |
| sampling_confidence_level | DECIMAL | Hayır | Örneklem yönteminin doğrulanmış istatistiksel güven düzeyi |
| evidence_completeness | ENUM/DECIMAL | Evet | Sayaç, sürüm, snapshot ve audit kanıtı tamamlığı |
| last_successful_run_at | TIMESTAMP | Hayır | Son başarılı ölçüm zamanı; eski skor gösteriminde zorunlu |
| valid_until | TIMESTAMP | Hayır | Dataset/kullanım politikasından gelen geçerlilik sonu |

Kapsam ve güven formüllerinin katsayıları aktif, sürümlü yeterlilik politikasından
çözülür. Politika yoksa olumlu yeterlilik sonucu üretilmez. Yüksek kalite/düşük
güven durumu korunur ve kullanıcıya ayrı gösterilir (`DQ-SCR-020`,
`DQ-SCR-021`).

## MeasurementQualificationResult

| Alan adı | Veri tipi | Zorunluluk | Açıklama |
| --- | --- | --- | --- |
| qualification_result_id | UUID | Evet | Yeterlilik sonucu anahtarı |
| quality_score_id | UUID | Evet | İlgili ham/nihai kalite sonucu |
| measurement_summary_id | UUID | Evet | Kapsam, örneklem, güven ve geçerlilik özeti |
| qualification_status | ENUM | Evet | QUALIFIED/PROVISIONALLY_QUALIFIED/LIMITED_COVERAGE/STALE/VALIDATION_REQUIRED/TECHNICAL_FAILURE/NOT_QUALIFIED/NOT_APPLICABLE |
| failed_gates | JSON | Evet | Sağlanmayan anlam, kapsam, örneklem, teknik, güncellik, sürüm, kanıt, kritik kontrol, test/onay kapıları |
| qualification_policy_version | VARCHAR | Evet | Değerlendirme sırası ve koşulların sürümü |
| evaluated_at | TIMESTAMP | Evet | UTC yeterlilik değerlendirme zamanı |
| valid_until | TIMESTAMP | Hayır | Sonucun geçerlilik sonu |
| previous_qualification_result_id | UUID | Hayır | Yeniden ölçüm/yeniden değerlendirme zinciri |
| audit_reference | VARCHAR | Evet | Veri-minimum audit/outbox referansı |

Yüksek `raw_score_value` veya `final_score_value`, bu sonucu kendiliğinden
`QUALIFIED` yapmaz. Yeterlilik kayıtları append-only tutulur; yeniden ölçüm önceki
kaydı güncellemez.

## DatasetCriticalityProfile

| Alan adı | Veri tipi | Zorunluluk | Açıklama |
| --- | --- | --- | --- |
| criticality_profile_id | UUID | Evet | Profil anahtarı |
| dataset_id | UUID | Evet | Dataset referansı |
| regulatory_impact | ENUM/DECIMAL | Hayır | Düzenleyici raporlama etkisi |
| financial_impact | ENUM/DECIMAL | Hayır | Finansal etki |
| customer_impact | ENUM/DECIMAL | Hayır | Müşteri etkisi |
| operational_dependency | ENUM/DECIMAL | Hayır | Operasyonel bağımlılık |
| downstream_usage | INTEGER/DECIMAL | Hayır | Downstream kullanım göstergesi |
| sensitivity_level | ENUM | Hayır | Harici katalog/DLP referanslı hassasiyet |
| profile_version | VARCHAR | Evet | Değişmez profil sürümü |
| effective_from | TIMESTAMP | Evet | Geçerlilik başlangıcı |
| approval_status | ENUM | Evet | Risk bazlı onay durumu |

Profil ham kalite skorunu değiştirmez; sıklık, politika seçimi, alarm ve
remediation süresine girdi olur (`DQ-SCR-018`). Kurumsal faktör katsayıları aktif,
sürümlü risk politikasından çözülür; `OPEN-BNK-013` kapsam kararı ve geçerli
politika yoksa risk sonucu üretilmez.

## DataRiskScore

| Alan adı | Veri tipi | Zorunluluk | Açıklama |
| --- | --- | --- | --- |
| data_risk_score_id | UUID | Evet | Risk sonucu anahtarı |
| quality_score_id | UUID | Evet | İlgili ham kalite skoru |
| criticality_profile_id | UUID | Evet | Ayrı dataset kritiklik profili |
| risk_value | DECIMAL/ENUM | Hayır | Onaylı risk modeli sonucu |
| risk_model_version | VARCHAR | Evet | Kalite modelinden ayrı risk modeli sürümü |
| calculation_details | JSON | Evet | Kalite problemi, iş etkisi ve kullanım bileşenleri |
| calculated_at | TIMESTAMP | Evet | UTC hesap zamanı |

Risk formülü ve katsayıları aktif, sürümlü risk politikasından çözülür. Politika
yoksa risk sonucu üretilmez. Risk sonucu kalite skorunun yerine geçmez
(`DQ-SCR-019`, `OPEN-BNK-013`).

## DataQualityException

| Alan adı | Veri tipi | Zorunluluk | Açıklama |
| --- | --- | --- | --- |
| exception_id | UUID | Evet | İstisna anahtarı |
| dataset_id / rule_version_id | UUID | Evet | İstisna kapsamı |
| exception_type | ENUM | Evet | Onaylı tür |
| reason_code | VARCHAR | Evet | Serbest hassas içerik taşımayan gerekçe kodu |
| requested_by / approved_by | UUID | Evet | Birbirinden farklı maker/checker |
| starts_at / expires_at | TIMESTAMP | Evet | Süreli geçerlilik |
| risk_acceptance_reference | VARCHAR | Evet | Risk kabul kaydı referansı |
| status | ENUM | Evet | PENDING/APPROVED/REJECTED/WITHDRAWN/EXPIRED |
| audit_reference | VARCHAR | Evet | Merkezi audit/outbox referansı |

Süresiz varsayılan istisna yoktur. İstisna sayısı/oranı skorun yanında görünür
kalır (`DQ-SCR-022`, `DQ-SCR-030`). Süre ve eşik değerleri aktif, sürümlü istisna
politikasından çözülür; politika yoksa istisna onaylanmaz.

## ScoreAssessmentOverride

| Alan adı | Veri tipi | Zorunluluk | Açıklama |
| --- | --- | --- | --- |
| assessment_id | UUID | Evet | Değerlendirme anahtarı |
| quality_score_id | UUID | Evet | Değiştirilmeyen ham/nihai kalite sonucu referansı |
| assessment_status | ENUM | Evet | Onaylı değerlendirme/override durumu |
| reason_code | VARCHAR | Evet | Gerekçe kodu |
| requested_by / approved_by | UUID | Evet | Maker-checker aktörleri |
| starts_at / expires_at | TIMESTAMP | Evet | Süreli geçerlilik |
| audit_reference | VARCHAR | Evet | Merkezi audit/outbox referansı |

Bu varlık `raw_score_value` veya `final_score_value` alanını güncellemez. Yönetim raporunda ham/nihai skor ve onaylı
değerlendirme ayrı gösterilir (`DQ-SCR-023`, `DQ-SCR-030`).

## ScoringPolicy

| Alan adı | Veri tipi | Zorunluluk | Açıklama |
| --- | --- | --- | --- |
| scoring_policy_id | UUID | Evet | Politika anahtarı |
| policy_type | ENUM | Evet | NORMALIZATION/THRESHOLD/WEIGHT/CRITICAL_RULE/CONFIDENCE/QUALIFICATION/FRESHNESS/USAGE_DECISION/NOTIFICATION/REMEDIATION |
| dataset_type / dataset_id | UUID/VARCHAR | Koşullu | Politika kapsamı |
| business_criticality / usage_context | ENUM/VARCHAR | Koşullu | Kritiklik profili ve kullanım bağlamı |
| dimension_code | ENUM | Koşullu | Boyut kapsamı |
| rule_id / rule_class | UUID/VARCHAR | Koşullu | Kural kapsamı |
| definition | JSON | Evet | Formül, eşik, ağırlık, veto/tavan/blokaj tanımı |
| applicability_condition | JSON | Koşullu | Koşullu kural/dataset uygulanabilirliği |
| sampling_policy | JSON | Koşullu | Yöntem, minimum kapsam/örneklem ve güven koşulları |
| result_validity_period / freshness_hard_limit | DURATION | Koşullu | Güncellik ve geçerlilik politikası; aktif politika kaydında pozitif süre zorunlu |
| technical_failure_behavior | ENUM/JSON | Evet | Skor NULL, son başarılı gösterimi, retry/alarm davranışı |
| notification_policy / remediation_sla | UUID/VARCHAR | Koşullu | Olay ve düzeltme politika referansı; otomatik olay/kapanış için aktif kayıt zorunlu |
| policy_version | VARCHAR | Evet | Değişmez sürüm |
| effective_from / effective_to | TIMESTAMP | Evet/Hayır | Geçerlilik aralığı |
| reason_code / decision_owner | VARCHAR/UUID | Evet | Gerekçe ve karar sahibi |
| approved_by / approval_status | UUID/ENUM | Koşullu/Evet | Risk bazlı onay |
| audit_reference | VARCHAR | Evet | Merkezi audit/outbox referansı |

Üretim eşikleri, ağırlıkları, veto/tavan davranışı ve güven katsayıları aktif,
sürümlü politikadan çözülür; kaynak koduna gömülmez. Politika yoksa olumlu skor
sınıflandırması veya yeterlilik kararı üretilmez (`DQ-SCR-013`–`DQ-SCR-017`,
`DQ-SCR-025`).

## DatasetPartialScorePolicy

| Alan adı | Veri tipi | Uzunluk | Zorunluluk | Benzersizlik | Varsayılan değer | Açıklama | Hassas veri durumu | Doğrulama kuralı |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| partial_score_policy_id | UUID | 36 | Evet | Evet | Otomatik | Politika anahtarı | Hayır | UUID |
| dataset_id | UUID | 36 | Evet | Hayır | Yok | Dataset kapsamı | Hayır | Geçerli Dataset |
| allow_official_partial_score | BOOLEAN | 1 | Evet | Hayır | FALSE | Kısmi resmî skor izni | Hayır | Boolean |
| minimum_coverage_ratio | DECIMAL | 5,4 | Evet | Hayır | Yok | Minimum kapsama oranı | Hayır | 0–1 |
| required_critical_rules | JSON | — | Evet | Hayır | Yok | Zorunlu kritik kural listesi/sınıfı | Hayır | Geçerli kural referansları |
| required_partitions | JSON | — | Evet | Hayır | Yok | Eksik olmasına izin verilmeyen bölümler | Hassas olabilir | Dataset kapsamı |
| maximum_missing_record_ratio | DECIMAL | 5,4 | Evet | Hayır | Yok | Azami eksik kayıt oranı | Hayır | 0–1 |
| maximum_technical_error_ratio | DECIMAL | 5,4 | Evet | Hayır | Yok | Azami teknik hata oranı | Hayır | 0–1 |
| minimum_successful_rule_ratio | DECIMAL | 5,4 | Evet | Hayır | Yok | Asgari başarılı kural oranı | Hayır | 0–1 |
| policy_version | VARCHAR | 80 | Evet | Koşullu benzersiz | Yok | Politika sürümü | Hayır | Dataset içinde değişmez |
| effective_from | TIMESTAMP | — | Evet | Hayır | Yok | Geçerlilik başlangıcı | Hayır | UTC |
| approval_status | ENUM | 30 | Evet | Hayır | DRAFT | DRAFT/PENDING/APPROVED/REJECTED/WITHDRAWN/EXPIRED | Hayır | İzinli geçiş |
| approved_by | UUID | 36 | Onayda evet | Hayır | NULL | Onaylayan kullanıcı | Kişisel | Talep edenden farklı |
| audit_reference | VARCHAR | 500 | Evet | Hayır | Yok | Audit olayı referansı | Hassas olabilir | Geçerli audit kaydı |

Politika yoksa veya koşullardan biri sağlanmazsa `QualityScore` provizyonel olur. `calculation_details`; kapsama oranı, çalışan/çalışmayan kural sayıları, eksik bölümler, politika sürümü, kabul/red nedeni ve resmî agregasyon uygunluğunu taşır.

Mevcut runtime alanı `minimum_coverage_ratio`, kanonik
`minimum_coverage_rate` kavramının fiziksel karşılığıdır. Alan adı migration kararı
`OPEN-022` kapsamında verilir; tarihsel kayıt sessizce yeniden adlandırılmaz.

## Schedule

| Alan adı | Veri tipi | Uzunluk | Zorunluluk | Benzersizlik | Varsayılan değer | Açıklama | Hassas veri durumu | Doğrulama kuralı |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| schedule_id | UUID | 36 | Evet | Evet | Otomatik | Plan anahtarı | Hayır | UUID |
| name | VARCHAR | 200 | Evet | Hayır | Yok | Plan adı | Hayır | 1–200 karakter |
| schedule_type | ENUM | 30 | Evet | Hayır | CRON | ONCE/DAILY/WEEKLY/MONTHLY/CRON | Hayır | İzinli enum |
| cron_expression | VARCHAR | 120 | Koşullu | Hayır | NULL | Cron ifadesi | Hayır | Geçerli cron |
| timezone | VARCHAR | 64 | Evet | Hayır | Europe/Istanbul | Saat dilimi | Hayır | IANA timezone |
| is_active | BOOLEAN | 1 | Evet | Hayır | TRUE | Plan etkinliği | Hayır | Boolean |
| next_run_at | TIMESTAMP | — | Hayır | Hayır | NULL | Sonraki UTC zaman | Hayır | Hesaplanan |
