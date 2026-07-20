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
| source_type | ENUM | 30 | Evet | Hayır | Yok | POSTGRESQL/MSSQL/ORACLE/MYSQL/CSV/EXCEL/REST | Hayır | Desteklenen değer |
| connection_config | JSON | TBD | Evet | Hayır | {} | Gizli olmayan bağlantı ayarları | Hassas olabilir | Şema doğrulaması |
| secret_reference | VARCHAR | 500 | Evet | Hayır | Yok | Secret manager anahtarı | Hassas | Ham secret içeremez |
| status | ENUM | 30 | Evet | Hayır | TEST_PENDING | Kaynak durumu | Hayır | İzinli geçiş |
| owner_user_id | UUID | 36 | Kritik kaynakta evet | Hayır | NULL | Data Owner referansı | Kişisel | Aktif User referansı |
| last_test_at | TIMESTAMP | TBD | Hayır | Hayır | NULL | Son bağlantı testi | Hayır | UTC |

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
| is_sensitive | BOOLEAN | 1 | Evet | Hayır | FALSE | Hassas veri işareti | Hassas | Yetkili değişiklik |
| classification | VARCHAR | 100 | Hayır | Hayır | NULL | Kişisel veri sınıfı | Hassas | Onaylı sözlük |

## DataProfile

| Alan adı | Veri tipi | Uzunluk | Zorunluluk | Benzersizlik | Varsayılan değer | Açıklama | Hassas veri durumu | Doğrulama kuralı |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| profile_id | UUID | 36 | Evet | Evet | Otomatik | Profil anahtarı | Hayır | UUID |
| dataset_id | UUID | 36 | Evet | Hayır | Yok | Profil veri kümesi | Hayır | Geçerli Dataset |
| execution_id | UUID | 36 | Evet | Hayır | Yok | Çalıştırma referansı | Hayır | Geçerli RuleExecution |
| method | ENUM | 30 | Evet | Hayır | FULL | FULL/SAMPLE/PARTITION/AGGREGATE | Hayır | İzinli enum |
| sample_ratio | DECIMAL | 5,4 | Hayır | Hayır | NULL | Örneklem oranı | Hayır | 0<oran≤1 |
| metrics | JSON | TBD | Evet | Hayır | {} | Profil metrikleri | Hassas olabilir | Şema doğrulaması; ham hassas değer yok |
| status | ENUM | 30 | Evet | Hayır | RUNNING | Profil durumu | Hayır | İzinli geçiş |
