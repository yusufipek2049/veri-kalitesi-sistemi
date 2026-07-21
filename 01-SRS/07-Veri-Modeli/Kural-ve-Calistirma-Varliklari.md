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
| business_justification | TEXT | TBD | Evet | Hayır | Yok | Kuralın iş gerekçesi | Hassas olabilir | Veri-minimum ve onaylı içerik |
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
| definition | JSON/TEXT | TBD | Evet | Hayır | Yok | Kural mantığı ve parametreleri | Hassas olabilir | Salt okunur; şema doğrulaması |
| threshold_policy_version | VARCHAR | 80 | Evet | Hayır | Yok | Etkin eşik/tolerans politika sürümü | Hayır | Onaylı ve geçerli politika |
| weight_policy_version | VARCHAR | 80 | Evet | Hayır | Yok | Dataset kural ağırlığı politika sürümü | Hayır | Onaylı ve geçerli politika |
| threshold_snapshot | DECIMAL/JSON | TBD | Evet | Hayır | Yok | Çalıştırmada yeniden üretilebilirlik için uygulanan eşik/tolerans özeti | Hayır | Politika sürümüyle uyumlu |
| weight_snapshot | DECIMAL | 10,4 | Evet | Hayır | Yok | Çalıştırmada uygulanan pozitif ağırlık özeti | Hayır | >0 ve politika sürümüyle uyumlu |
| criticality | ENUM | 20 | Evet | Hayır | MEDIUM | Kritiklik | Hayır | İzinli enum |
| schedule_policy_reference | UUID/VARCHAR | TBD | Evet | Hayır | Yok | Ölçüm sıklığı/çalışma politikası referansı | Hayır | Onaylı ve sürümlü politika |
| effective_from / effective_to | TIMESTAMP | TBD | Evet/Hayır | Hayır | Yok/NULL | Kural sürümünün geçerlilik aralığı | Hayır | Başlangıç bitişten önce |
| approval_status / approved_by | ENUM/UUID | TBD | Evet/Koşullu | Hayır | DRAFT/NULL | Üretim etkinleştirme onayı | Kişisel olabilir | Risk bazlı maker-checker |
| created_at | TIMESTAMP | TBD | Evet | Hayır | Otomatik | Sürüm zamanı UTC | Hayır | Değişmez |

## RuleExecution

| Alan adı | Veri tipi | Uzunluk | Zorunluluk | Benzersizlik | Varsayılan değer | Açıklama | Hassas veri durumu | Doğrulama kuralı |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| execution_id | UUID | 36 | Evet | Evet | Otomatik | Çalıştırma anahtarı | Hayır | UUID |
| execution_type | ENUM | 30 | Evet | Hayır | MANUAL | MANUAL/SCHEDULED/TEST/PROFILE | Hayır | İzinli enum |
| status | ENUM | 40 | Evet | Hayır | QUEUED | QUEUED/RUNNING/SUCCESS/PARTIAL/TECHNICAL_ERROR/TIMEOUT/CANCELLED | Hayır | İzinli geçiş |
| idempotency_key | VARCHAR | 200 | Evet | Koşullu benzersiz | Otomatik | Çift çalıştırma önleme anahtarı | Hassas olabilir | Payload hash ile eşleşir |
| started_at | TIMESTAMP | TBD | Hayır | Hayır | NULL | Başlangıç UTC | Hayır | Bitişten önce |
| finished_at | TIMESTAMP | TBD | Hayır | Hayır | NULL | Bitiş UTC | Hayır | Başlangıçtan sonra |
| triggered_by | UUID | 36 | Hayır | Hayır | NULL | Kullanıcı/servis hesabı | Kişisel | Geçerli User veya sistem |
| error_class | VARCHAR | 100 | Hayır | Hayır | NULL | Teknik hata sınıfı | Hassas olabilir | Onaylı hata sözlüğü |

## RuleResult

| Alan adı | Veri tipi | Uzunluk | Zorunluluk | Benzersizlik | Varsayılan değer | Açıklama | Hassas veri durumu | Doğrulama kuralı |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rule_result_id | UUID | 36 | Evet | Evet | Otomatik | Sonuç anahtarı | Hayır | UUID |
| execution_id | UUID | 36 | Evet | Hayır | Yok | Çalıştırma referansı | Hayır | Geçerli RuleExecution |
| rule_version_id | UUID | 36 | Evet | Hayır | Yok | Çalışan kural sürümü | Hayır | Geçerli RuleVersion |
| checked_count | BIGINT | 19 | Evet | Hayır | 0 | Kontrol edilen kayıt | Hayır | ≥0 |
| passed_count | BIGINT | 19 | Evet | Hayır | 0 | Başarılı kayıt | Hayır | ≥0 |
| failed_count | BIGINT | 19 | Evet | Hayır | 0 | Hatalı kayıt | Hayır | ≥0 |
| exception_count | BIGINT | 19 | Evet | Hayır | 0 | Geçerli istisna nedeniyle skor paydasından ayrılan kayıt | Hayır | ≥0 |
| out_of_scope_count | BIGINT | 19 | Evet | Hayır | 0 | Kural kapsamı dışında kalan kayıt | Hayır | ≥0 |
| not_evaluated_count | BIGINT | 19 | Evet | Hayır | 0 | Değerlendirilemeyen kayıt | Hayır | ≥0 |
| measurement_status | ENUM | 40 | Evet | Hayır | NOT_MEASURED | PASSED/WARNING/FAILED/NOT_APPLICABLE/NOT_MEASURED/NO_DATA/TECHNICAL_ERROR/SUPPRESSED_BY_EXCEPTION | Hayır | İzinli durum |
| normalization_policy_version | VARCHAR | 80 | Koşullu | Hayır | NULL | Kural skorunda kullanılan normalizasyon sürümü | Hayır | Sayısal skorda zorunlu |
| sample_evidence | JSON | TBD | Hayır | Hayır | NULL | Maskeli örnek/kanıt | Hassas | Maskeleme zorunlu |

Sayaçlar `DQ-SCR-004` ve `DQ-SCR-006` uyarınca iki ayrı eşitlikle doğrulanır:
değerlendirilen kayıt sayısı başarılı + başarısız; kaynak kapsamı ise kapsam
dışı + değerlendirilen + istisnalı + değerlendirilemeyen kayıttır.

## QualityScore

| Alan adı | Veri tipi | Uzunluk | Zorunluluk | Benzersizlik | Varsayılan değer | Açıklama | Hassas veri durumu | Doğrulama kuralı |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| quality_score_id | UUID | 36 | Evet | Evet | Otomatik | Skor anahtarı | Hayır | UUID |
| scope_type | ENUM | 30 | Evet | Hayır | RULE | RULE/DATA_ELEMENT/DIMENSION/DATASET/DATA_PRODUCT/REPORT/DATA_DOMAIN/SOURCE/ENTERPRISE | Hayır | İzinli enum |
| scope_id | UUID | 36 | Hayır | Hayır | NULL | Kapsam nesnesi; kurum skorunda NULL | Hayır | Scope type ile uyumlu |
| score_value | DECIMAL | 5,2 | Hayır | Hayır | NULL | 0–100 skor | Hayır | 0–100 veya NULL |
| score_status | ENUM | 50 | Evet | Hayır | NOT_MEASURED | PASSED/WARNING/FAILED/NOT_APPLICABLE/NOT_MEASURED/NO_DATA/TECHNICAL_ERROR/SUPPRESSED_BY_EXCEPTION/PARTIAL/CONFIG_ERROR | Hayır | İzinli enum; fiziksel kod eşlemesi sürümlü |
| level | ENUM | 30 | Hayır | Hayır | NULL | Sürümlü eşik politikasının kalite etiketi | Hayır | Eşik politika sürümüyle uyumlu |
| score_model_version | VARCHAR | 80 | Evet | Hayır | Yok | Skor modeli/formül sürümü | Hayır | Değişmez |
| threshold_policy_version | VARCHAR | 80 | Koşullu | Hayır | NULL | Kullanılan eşik sürümü | Hayır | Sınıflandırılmış skorda zorunlu |
| weight_policy_version | VARCHAR | 80 | Koşullu | Hayır | NULL | Kullanılan ağırlık sürümü | Hayır | Toplulaştırılmış skorda zorunlu |
| normalization_policy_version | VARCHAR | 80 | Koşullu | Hayır | NULL | Kullanılan normalizasyon sürümü | Hayır | Normalleştirilmiş skorda zorunlu |
| application_version | VARCHAR | 80 | Evet | Hayır | Yok | Hesaplamayı yapan uygulama sürümü | Hayır | Değişmez |
| original_score_id | UUID | 36 | Hayır | Hayır | NULL | Yeniden hesaplanan sonuçta korunan orijinal skor | Hayır | Geçerli QualityScore |
| calculation_details | JSON | TBD | Evet | Hayır | {} | Formül, dahil/dışlanan öğe, kritik kural kararı ve sürüm özeti | Hayır | Şema doğrulaması; ham/hassas kayıt yok |
| calculated_at | TIMESTAMP | TBD | Evet | Hayır | Otomatik | Hesap zamanı UTC | Hayır | Geçerli zaman |

`QualityScore` yalnız ham veri kalitesi ölçümünü taşır. Dataset kritiklik profili,
ölçüm kapsamı/güveni, veri riski, teknik sağlık ve onaylı değerlendirme/override
bu değerin içine eritilmez (`DQ-SCR-018`–`DQ-SCR-023`). `SOURCE` ve
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
| quality_score_id | UUID | Evet | Ham kalite skoru referansı |
| coverage_ratio | DECIMAL | Evet | Sürümü belirtilen kapsam formülünün sonucu |
| confidence_score | DECIMAL | Evet | Kalite skorundan ayrı ölçüm güveni |
| confidence_policy_version | VARCHAR | Evet | Kapsam/güven formülü ve ağırlık sürümü |
| executed_rule_ratio | DECIMAL | Evet | Çalışan kural oranı |
| technical_error_ratio | DECIMAL | Evet | Teknik hata oranı; kalite başarısızlığı değildir |
| sampling_method | ENUM | Hayır | FULL/SAMPLE/INCREMENTAL/PARTITIONED |
| sample_size | BIGINT | Hayır | Örneklem büyüklüğü |
| confidence_level | DECIMAL | Hayır | Örneklem yönteminin istatistiksel güven düzeyi |
| last_successful_calculation_at | TIMESTAMP | Hayır | Son başarılı ölçüm zamanı; eski skor gösteriminde zorunlu |

Kapsam ve güven formüllerinin kesin katsayıları `TBD`'dir. Yüksek kalite/düşük
güven durumu korunur ve kullanıcıya ayrı gösterilir (`DQ-SCR-020`,
`DQ-SCR-021`).

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
remediation süresine girdi olur (`DQ-SCR-018`). Kurumsal faktör katsayıları
`TBD`'dir ve `OPEN-BNK-013` kapanmadan uydurulmaz.

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

Kesin risk formülü ve katsayıları `TBD`'dir. Risk sonucu kalite skorunun yerine
geçmez (`DQ-SCR-019`, `OPEN-BNK-013`).

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
kalır (`DQ-SCR-022`, `DQ-SCR-030`). Süre ve eşik değerleri `TBD`'dir.

## ScoreAssessmentOverride

| Alan adı | Veri tipi | Zorunluluk | Açıklama |
| --- | --- | --- | --- |
| assessment_id | UUID | Evet | Değerlendirme anahtarı |
| quality_score_id | UUID | Evet | Değiştirilmeyen ham skor referansı |
| assessment_status | ENUM | Evet | Onaylı değerlendirme/override durumu |
| reason_code | VARCHAR | Evet | Gerekçe kodu |
| requested_by / approved_by | UUID | Evet | Maker-checker aktörleri |
| starts_at / expires_at | TIMESTAMP | Evet | Süreli geçerlilik |
| audit_reference | VARCHAR | Evet | Merkezi audit/outbox referansı |

Bu varlık `score_value` alanını güncellemez. Yönetim raporunda ham skor ve onaylı
değerlendirme ayrı gösterilir (`DQ-SCR-023`, `DQ-SCR-030`).

## ScoringPolicy

| Alan adı | Veri tipi | Zorunluluk | Açıklama |
| --- | --- | --- | --- |
| scoring_policy_id | UUID | Evet | Politika anahtarı |
| policy_type | ENUM | Evet | NORMALIZATION/THRESHOLD/WEIGHT/CRITICAL_RULE/CONFIDENCE |
| dataset_type / dataset_id | UUID/VARCHAR | Koşullu | Politika kapsamı |
| dimension_code | ENUM | Koşullu | Boyut kapsamı |
| rule_id / rule_class | UUID/VARCHAR | Koşullu | Kural kapsamı |
| definition | JSON | Evet | Formül, eşik, ağırlık, veto/tavan/blokaj tanımı |
| policy_version | VARCHAR | Evet | Değişmez sürüm |
| effective_from / effective_to | TIMESTAMP | Evet/Hayır | Geçerlilik aralığı |
| reason_code / decision_owner | VARCHAR/UUID | Evet | Gerekçe ve karar sahibi |
| approved_by / approval_status | UUID/ENUM | Koşullu/Evet | Risk bazlı onay |
| audit_reference | VARCHAR | Evet | Merkezi audit/outbox referansı |

Üretim eşikleri, ağırlıkları, veto/tavan davranışı ve güven katsayıları `TBD`
olarak kalır; kaynak koduna gömülmez (`DQ-SCR-013`–`DQ-SCR-017`,
`DQ-SCR-025`).

## DatasetPartialScorePolicy

| Alan adı | Veri tipi | Uzunluk | Zorunluluk | Benzersizlik | Varsayılan değer | Açıklama | Hassas veri durumu | Doğrulama kuralı |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| partial_score_policy_id | UUID | 36 | Evet | Evet | Otomatik | Politika anahtarı | Hayır | UUID |
| dataset_id | UUID | 36 | Evet | Hayır | Yok | Dataset kapsamı | Hayır | Geçerli Dataset |
| allow_official_partial_score | BOOLEAN | 1 | Evet | Hayır | FALSE | Kısmi resmî skor izni | Hayır | Boolean |
| minimum_coverage_ratio | DECIMAL | 5,4 | Evet | Hayır | Yok | Minimum kapsama oranı | Hayır | 0–1 |
| required_critical_rules | JSON | TBD | Evet | Hayır | Yok | Zorunlu kritik kural listesi/sınıfı | Hayır | Geçerli kural referansları |
| required_partitions | JSON | TBD | Evet | Hayır | Yok | Eksik olmasına izin verilmeyen bölümler | Hassas olabilir | Dataset kapsamı |
| maximum_missing_record_ratio | DECIMAL | 5,4 | Evet | Hayır | Yok | Azami eksik kayıt oranı | Hayır | 0–1 |
| maximum_technical_error_ratio | DECIMAL | 5,4 | Evet | Hayır | Yok | Azami teknik hata oranı | Hayır | 0–1 |
| minimum_successful_rule_ratio | DECIMAL | 5,4 | Evet | Hayır | Yok | Asgari başarılı kural oranı | Hayır | 0–1 |
| policy_version | VARCHAR | 80 | Evet | Koşullu benzersiz | Yok | Politika sürümü | Hayır | Dataset içinde değişmez |
| effective_from | TIMESTAMP | TBD | Evet | Hayır | Yok | Geçerlilik başlangıcı | Hayır | UTC |
| approval_status | ENUM | 30 | Evet | Hayır | DRAFT | DRAFT/PENDING/APPROVED/REJECTED/WITHDRAWN/EXPIRED | Hayır | İzinli geçiş |
| approved_by | UUID | 36 | Onayda evet | Hayır | NULL | Onaylayan kullanıcı | Kişisel | Talep edenden farklı |
| audit_reference | VARCHAR | 500 | Evet | Hayır | Yok | Audit olayı referansı | Hassas olabilir | Geçerli audit kaydı |

Politika yoksa veya koşullardan biri sağlanmazsa `QualityScore` provizyonel olur. `calculation_details`; kapsama oranı, çalışan/çalışmayan kural sayıları, eksik bölümler, politika sürümü, kabul/red nedeni ve resmî agregasyon uygunluğunu taşır.

## Schedule

| Alan adı | Veri tipi | Uzunluk | Zorunluluk | Benzersizlik | Varsayılan değer | Açıklama | Hassas veri durumu | Doğrulama kuralı |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| schedule_id | UUID | 36 | Evet | Evet | Otomatik | Plan anahtarı | Hayır | UUID |
| name | VARCHAR | 200 | Evet | Hayır | Yok | Plan adı | Hayır | 1–200 karakter |
| schedule_type | ENUM | 30 | Evet | Hayır | CRON | ONCE/DAILY/WEEKLY/MONTHLY/CRON | Hayır | İzinli enum |
| cron_expression | VARCHAR | 120 | Koşullu | Hayır | NULL | Cron ifadesi | Hayır | Geçerli cron |
| timezone | VARCHAR | 64 | Evet | Hayır | Europe/Istanbul | Saat dilimi | Hayır | IANA timezone |
| is_active | BOOLEAN | 1 | Evet | Hayır | TRUE | Plan etkinliği | Hayır | Boolean |
| next_run_at | TIMESTAMP | TBD | Hayır | Hayır | NULL | Sonraki UTC zaman | Hayır | Hesaplanan |
