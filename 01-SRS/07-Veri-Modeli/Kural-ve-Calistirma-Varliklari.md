---
type: data-dictionary-group
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_document: Veri_Kalitesi_Izleme_ve_Skorlama_Sistemi_SRS_v0.1.md
source_version: "0.1"
source_section: "QualityRule, RuleVersion, RuleExecution, RuleResult, QualityScore, QualityDimension, Schedule"
generated_at: 2026-07-16
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
| primary_dimension_id | UUID | 36 | Evet | Hayır | Yok | Birincil kalite boyutu | Hayır | Geçerli QualityDimension |
| owner_user_id | UUID | 36 | Aktif kritik kuralda evet | Hayır | NULL | Kural sahibi | Kişisel | Aktif User |
| status | ENUM | 30 | Evet | Hayır | DRAFT | DRAFT/ACTIVE/PASSIVE/REVIEW_REQUIRED/ARCHIVED | Hayır | İzinli geçiş |

## RuleVersion

| Alan adı | Veri tipi | Uzunluk | Zorunluluk | Benzersizlik | Varsayılan değer | Açıklama | Hassas veri durumu | Doğrulama kuralı |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rule_version_id | UUID | 36 | Evet | Evet | Otomatik | Sürüm anahtarı | Hayır | UUID |
| quality_rule_id | UUID | 36 | Evet | Hayır | Yok | Kural referansı | Hayır | Geçerli QualityRule |
| version_no | INTEGER | 10 | Evet | Hayır | 1 | Artan sürüm | Hayır | >0 ve kural içinde benzersiz |
| rule_type | ENUM | 50 | Evet | Hayır | Yok | Şablon/SQL/regex vb. | Hayır | İzinli tür |
| definition | JSON/TEXT | TBD | Evet | Hayır | Yok | Kural mantığı ve parametreleri | Hassas olabilir | Salt okunur; şema doğrulaması |
| threshold | DECIMAL | 5,2 | Evet | Hayır | 90.00 | Başarı eşiği | Hayır | 0–100 |
| weight | DECIMAL | 10,4 | Evet | Hayır | 1.0 | Kural ağırlığı | Hayır | >0 |
| criticality | ENUM | 20 | Evet | Hayır | MEDIUM | Kritiklik | Hayır | İzinli enum |
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
| not_evaluated_count | BIGINT | 19 | Evet | Hayır | 0 | Değerlendirilemeyen kayıt | Hayır | ≥0 |
| sample_evidence | JSON | TBD | Hayır | Hayır | NULL | Maskeli örnek/kanıt | Hassas | Maskeleme zorunlu |

## QualityScore

| Alan adı | Veri tipi | Uzunluk | Zorunluluk | Benzersizlik | Varsayılan değer | Açıklama | Hassas veri durumu | Doğrulama kuralı |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| quality_score_id | UUID | 36 | Evet | Evet | Otomatik | Skor anahtarı | Hayır | UUID |
| scope_type | ENUM | 30 | Evet | Hayır | RULE | RULE/DIMENSION/DATASET/SOURCE/ENTERPRISE | Hayır | İzinli enum |
| scope_id | UUID | 36 | Hayır | Hayır | NULL | Kapsam nesnesi; kurum skorunda NULL | Hayır | Scope type ile uyumlu |
| score_value | DECIMAL | 5,2 | Hayır | Hayır | NULL | 0–100 skor | Hayır | 0–100 veya NULL |
| score_status | ENUM | 50 | Evet | Hayır | CALCULATED | CALCULATED/NO_DATA/PARTIAL/NOT_CALCULATED_TECHNICAL_ERROR/CONFIG_ERROR | Hayır | İzinli enum |
| level | ENUM | 30 | Hayır | Hayır | NULL | İyi/Kabul Edilebilir/Riskli/Kritik | Hayır | Eşik setiyle uyumlu |
| calculation_details | JSON | TBD | Evet | Hayır | {} | Ağırlık, dahil/dışlanan öğe ve formül | Hayır | Şema doğrulaması |
| calculated_at | TIMESTAMP | TBD | Evet | Hayır | Otomatik | Hesap zamanı UTC | Hayır | Geçerli zaman |

## QualityDimension

| Alan adı | Veri tipi | Uzunluk | Zorunluluk | Benzersizlik | Varsayılan değer | Açıklama | Hassas veri durumu | Doğrulama kuralı |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dimension_id | UUID | 36 | Evet | Evet | Otomatik | Boyut anahtarı | Hayır | UUID |
| code | ENUM | 30 | Evet | Evet | Yok | COMPLETENESS vb. | Hayır | Yedi desteklenen değer |
| name_tr | VARCHAR | 80 | Evet | Evet | Yok | Türkçe ad | Hayır | Onaylı sözlük |
| weight | DECIMAL | 10,4 | Evet | Hayır | 1.0 | Boyut ağırlığı | Hayır | >0 |
| is_active | BOOLEAN | 1 | Evet | Hayır | TRUE | Boyut etkinliği | Hayır | Boolean |

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
