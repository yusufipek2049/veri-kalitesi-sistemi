---
type: data-dictionary-group
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_document: Veri_Kalitesi_Izleme_ve_Skorlama_Sistemi_SRS_v0.1.md
source_version: "0.1"
source_section: "DataSource, Dataset, DataField, DataProfile"
created_at: 2026-07-16
tags:
  - srs
  - data-dictionary
  - metadata
---

# Kaynak ve Metadata Varlıkları

## DataSource

| Alan adı | Veri tipi | Uzunluk | Zorunluluk | Benzersizlik | Varsayılan değer | Açıklama | Hassas veri durumu | Doğrulama kuralı |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| data_source_id | UUID | 36 | Evet | Evet | Otomatik | Kaynak anahtarı | Hayır | UUID |
| name | VARCHAR | 200 | Evet | Evet | Yok | Kurum içi benzersiz kaynak adı | Hayır | 1–200 karakter |
| source_type | ENUM | 30 | Evet | Hayır | Yok | RELATIONAL_DATABASE/FILE/REST_API | Hayır | Desteklenen ürün bağımsız değer |
| connection_config | JSON | — | Evet | Hayır | {} | Gizli olmayan bağlantı ayarları | Hassas olabilir | Şema doğrulaması |
| secret_reference | VARCHAR | 500 | Evet | Hayır | Yok | Secret manager anahtarı | Hassas | Ham secret içeremez |
| status | ENUM | 30 | Evet | Hayır | TEST_PENDING | Kaynak durumu | Hayır | İzinli geçiş |
| owner_user_id | UUID | 36 | Kritik kaynakta evet | Hayır | NULL | Data Owner referansı | Kişisel | Aktif User referansı |
| last_test_at | TIMESTAMP | — | Hayır | Hayır | NULL | Son bağlantı testi | Hayır | UTC |

## Dataset

| Alan adı | Veri tipi | Uzunluk | Zorunluluk | Benzersizlik | Varsayılan değer | Açıklama | Hassas veri durumu | Doğrulama kuralı |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dataset_id | UUID | 36 | Evet | Evet | Otomatik | Veri kümesi anahtarı | Hayır | UUID |
| data_source_id | UUID | 36 | Evet | Hayır | Yok | Kaynak referansı | Hayır | Aktif/arşivli DataSource |
| namespace | VARCHAR | 300 | Evet | Hayır | Yok | Şema/dosya/API yolu | Hassas olabilir | Kaynak türü biçimi |
| name | VARCHAR | 300 | Evet | Hayır | Yok | Tablo/görünüm/sayfa adı | Hassas olabilir | Kaynak içinde benzersiz |
| dataset_type | ENUM | 30 | Evet | Hayır | TABLE | TABLE/VIEW/FILE_SHEET/API_COLLECTION | Hayır | İzinli enum |
| criticality | ENUM | 20 | Evet | Hayır | MEDIUM | LOW/MEDIUM/HIGH/CRITICAL | Hayır | İzinli enum |
| owner_user_id | UUID | 36 | Kritikse evet | Hayır | NULL | Data Owner | Kişisel | Aktif User |
| estimated_row_count | BIGINT | 19 | Hayır | Hayır | NULL | Tahmini satır sayısı | Hayır | ≥0 |

## DataField

| Alan adı | Veri tipi | Uzunluk | Zorunluluk | Benzersizlik | Varsayılan değer | Açıklama | Hassas veri durumu | Doğrulama kuralı |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| data_field_id | UUID | 36 | Evet | Evet | Otomatik | Alan anahtarı | Hayır | UUID |
| dataset_id | UUID | 36 | Evet | Hayır | Yok | Veri kümesi referansı | Hayır | Geçerli Dataset |
| name | VARCHAR | 300 | Evet | Hayır | Yok | Alan adı | Hassas olabilir | Dataset içinde benzersiz |
| native_data_type | VARCHAR | 100 | Evet | Hayır | Yok | Kaynak veri tipi | Hayır | Kaynak metadatasıyla eşleşir |
| is_nullable | BOOLEAN | 1 | Evet | Hayır | TRUE | Null izin bilgisi | Hayır | Boolean |
| external_classification_id | VARCHAR | 500 | Hayır | Hayır | NULL | Katalog/DLP sınıflandırma kimliği | Hassas olabilir | Kaynak referansıyla doğrulanır |
| classification_level | VARCHAR | 100 | Evet | Hayır | Yok | Harici sınıflandırma seviyesi veya güvenli varsayılan | Hassas | Bilinen sınıf kesintide düşürülemez |
| is_personal_data | BOOLEAN | 1 | Evet | Hayır | FALSE | Kişisel veri göstergesi | Hassas | Harici kaynaktan senkronize |
| is_special_category_personal_data | BOOLEAN | 1 | Evet | Hayır | FALSE | Özel nitelikli kişisel veri göstergesi | Hassas | Harici kaynaktan senkronize |
| masking_policy_reference | VARCHAR | 500 | Evet | Hayır | Yok | Maskeleme politikası | Hassas | Geçerli politika referansı |
| viewing_restriction | VARCHAR | 500 | Evet | Hayır | Yok | Görüntüleme yetkisi/kısıtı | Hassas | Yetki motorunca uygulanır |
| reporting_restriction | VARCHAR | 500 | Evet | Hayır | Yok | Raporlama kısıtı | Hassas | Rapor üretiminde uygulanır |
| logging_restriction | VARCHAR | 500 | Evet | Hayır | Yok | Loglama kısıtı | Hassas | Log redaksiyonunda uygulanır |
| classification_source_reference | VARCHAR | 500 | Evet | Hayır | Yok | Katalog/DLP kaynak referansı | Hassas olabilir | Onaylı sistem |
| classification_synced_at | TIMESTAMP | — | Evet | Hayır | Yok | Son sınıflandırma senkronizasyonu | Hayır | UTC |

## SourceUsagePolicy

OPEN-002 ve OPEN-003 aynı sürümlü politika varlığında uygulanır. Kaynak bazlı değerler global güvenli varsayılanı geçersiz kılabilir; ikisi de yoksa çalışma reddedilir.

| Alan adı | Veri tipi | Uzunluk | Zorunluluk | Benzersizlik | Varsayılan değer | Açıklama | Hassas veri durumu | Doğrulama kuralı |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| source_usage_policy_id | UUID | 36 | Evet | Evet | Otomatik | Politika anahtarı | Hayır | UUID |
| data_source_id | UUID | 36 | Koşullu | Hayır | NULL | Kaynak kimliği | Hayır | Kaynak veya kaynak türünden biri zorunlu |
| source_type | ENUM | 30 | Koşullu | Hayır | NULL | Ürün bağımsız kaynak türü | Hayır | Kaynak veya kaynak türünden biri zorunlu |
| allowed_windows | JSON | — | Evet | Hayır | Yok | İzin verilen çalışma pencereleri | Hayır | Saat dilimi açık |
| blocked_windows | JSON | — | Evet | Hayır | Yok | Yasaklı saatler | Hayır | Çakışma doğrulaması |
| cpu_limit | DECIMAL | — | Hayır | Hayır | NULL | CPU kullanım sınırı | Hayır | Politika birimiyle doğrulanır |
| io_limit | DECIMAL | — | Hayır | Hayır | NULL | IO kullanım sınırı | Hayır | Politika birimiyle doğrulanır |
| max_query_duration | INTEGER | — | Evet | Hayır | Yok | Azami sorgu süresi | Hayır | Pozitif |
| max_concurrent_queries | INTEGER | — | Evet | Hayır | Yok | Eş zamanlı sorgu kotası | Hayır | Pozitif |
| max_workers | INTEGER | — | Evet | Hayır | Yok | Worker kotası | Hayır | Pozitif |
| retry_count | INTEGER | — | Evet | Hayır | Yok | Yeniden deneme sayısı | Hayır | Negatif olamaz |
| retry_delay | INTEGER | — | Evet | Hayır | Yok | Yeniden deneme gecikmesi | Hayır | Negatif olamaz |
| rate_limit | JSON | — | Evet | Hayır | Yok | Hız sınırı ve penceresi | Hayır | Şema doğrulaması |
| peak_hours_behavior | ENUM | 30 | Evet | Hayır | Yok | Yoğun saat davranışı | Hayır | Onaylı sözlük |
| timeout_cancel_behavior | ENUM | 30 | Evet | Hayır | Yok | Zaman aşımı ve iptal davranışı | Hayır | Onaylı sözlük |
| status | ENUM | 20 | Evet | Hayır | DRAFT | DRAFT/PENDING_APPROVAL/ACTIVE/RETIRED | Hayır | İzinli geçiş |
| policy_version | VARCHAR | 80 | Evet | Koşullu benzersiz | Yok | Politika sürümü | Hayır | Kapsam içinde değişmez |
| approved_by | UUID | 36 | Etkinse evet | Hayır | NULL | Onaylayan kullanıcı | Kişisel | Talep edenden farklı |
| audit_reference | VARCHAR | 500 | Evet | Hayır | Yok | Audit olayı referansı | Hassas olabilir | Geçerli audit kaydı |

## DataProfile

| Alan adı | Veri tipi | Uzunluk | Zorunluluk | Benzersizlik | Varsayılan değer | Açıklama | Hassas veri durumu | Doğrulama kuralı |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| profile_id | UUID | 36 | Evet | Evet | Otomatik | Profil anahtarı | Hayır | UUID |
| dataset_id | UUID | 36 | Evet | Hayır | Yok | Profil veri kümesi | Hayır | Geçerli Dataset |
| execution_id | UUID | 36 | Evet | Hayır | Yok | Çalıştırma referansı | Hayır | Geçerli RuleExecution |
| method | ENUM | 30 | Evet | Hayır | FULL | FULL/SAMPLE/PARTITION/AGGREGATE | Hayır | İzinli enum |
| sample_ratio | DECIMAL | 5,4 | Hayır | Hayır | NULL | Örneklem oranı | Hayır | 0<oran≤1 |
| metrics | JSON | — | Evet | Hayır | {} | Profil metrikleri | Hassas olabilir | Şema doğrulaması; ham hassas değer yok |
| status | ENUM | 30 | Evet | Hayır | RUNNING | Profil durumu | Hayır | İzinli geçiş |
