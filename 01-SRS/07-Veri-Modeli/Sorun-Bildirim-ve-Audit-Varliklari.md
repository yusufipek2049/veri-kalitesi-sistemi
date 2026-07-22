---
type: data-dictionary-group
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_document: Veri_Kalitesi_Izleme_ve_Skorlama_Sistemi_SRS_v0.1.md
source_version: "0.1"
source_section: "Notification, DataQualityIssue, IssueComment, AuditLog, Report"
created_at: 2026-07-16
tags:
  - srs
  - data-dictionary
  - issue
---

# Sorun, Bildirim ve Audit Varlıkları

## Notification

| Alan adı | Veri tipi | Uzunluk | Zorunluluk | Benzersizlik | Varsayılan değer | Açıklama | Hassas veri durumu | Doğrulama kuralı |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| notification_id | UUID | 36 | Evet | Evet | Otomatik | Bildirim anahtarı | Hayır | UUID |
| recipient_user_id | UUID | 36 | Evet | Hayır | Yok | Alıcı | Kişisel | Aktif User veya fallback grup |
| event_type | ENUM | 50 | Evet | Hayır | Yok | Kalite/yeterlilik/teknik alarmı, atama veya eskalasyon | Hayır | Teknik, kalite ve ölçüm yeterliliği olayları ayrı sözlük değeri |
| title | VARCHAR | 250 | Evet | Hayır | Yok | Bildirim başlığı | Hayır | Ham hassas veri içermez |
| body | TEXT | — | Evet | Hayır | Yok | Maskeli bildirim içeriği | Hassas olabilir | Şablon ve maskeleme |
| status | ENUM | 20 | Evet | Hayır | UNREAD | UNREAD/READ/SUPPRESSED/FAILED | Hayır | İzinli geçiş |
| deduplication_key | VARCHAR | 200 | Evet | Koşullu benzersiz | Yok | Tekrar önleme anahtarı | Hayır | Pencere içinde benzersiz |
| correlation_key | VARCHAR | 200 | Evet | Hayır | Yok | Aynı kök olayı birleştirme anahtarı | Hayır | Olay türü ve kapsamla tutarlı |

## DataQualityIssue

| Alan adı | Veri tipi | Uzunluk | Zorunluluk | Benzersizlik | Varsayılan değer | Açıklama | Hassas veri durumu | Doğrulama kuralı |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| issue_id | UUID | 36 | Evet | Evet | Otomatik | Sorun anahtarı | Hayır | UUID |
| issue_no | VARCHAR | 40 | Evet | Evet | Otomatik | Kullanıcı görünen numara | Hayır | Tanımlı biçim |
| source_event_type | ENUM | 40 | Evet | Hayır | QUALITY | QUALITY/MEASUREMENT_QUALIFICATION/TECHNICAL/SCHEMA_CHANGE | Hayır | Teknik, kalite ve yeterlilik olayları ayrıdır |
| quality_score_id | UUID | 36 | Kalite/yeterlilik olayında koşullu | Hayır | NULL | Değiştirilmeyen ham/nihai kalite sonucu | Hayır | Geçerli QualityScore; teknik olayda zorunlu değil |
| qualification_result_id | UUID | 36 | Yeterlilik olayında koşullu | Hayır | NULL | Ölçüm yeterlilik sonucu | Hayır | Geçerli MeasurementQualificationResult |
| data_risk_score_id | UUID | 36 | Hayır | Hayır | NULL | Önceliklendirmede kullanılan ayrı risk skoru | Hayır | Geçerli DataRiskScore |
| remediation_policy_version | VARCHAR | 80 | Evet | Hayır | Yok | Kritiklik/öneme göre hedef ve kapanış politikası | Hayır | Geçerli sürüm |
| status | ENUM | 30 | Evet | Hayır | NEW | Tanımlı issue durumları | Hayır | Geçiş matrisi |
| priority | ENUM | 20 | Evet | Hayır | MEDIUM | LOW/MEDIUM/HIGH/CRITICAL | Hayır | İzinli enum |
| assignee_user_id | UUID | 36 | Hayır | Hayır | NULL | Atanan kullanıcı | Kişisel | Aktif ve kapsam içi User |
| due_at | TIMESTAMP | — | Hayır | Hayır | NULL | Son tarih UTC | Hayır | Geçmiş olamaz |
| root_cause | TEXT | — | Çözümde evet | Hayır | NULL | Kök neden | Hassas olabilir | HTML temizlenir |
| corrective_action | TEXT | — | Çözümde evet | Hayır | NULL | Düzeltici faaliyet | Hassas olabilir | HTML temizlenir |
| verification_execution_id | UUID | 36 | Kapanışta koşullu | Hayır | NULL | Düzeltmeyi doğrulayan yeniden çalışma | Hayır | Başarılı ve kapsamla eşleşen execution |
| persistence_check_reference | VARCHAR | 200 | Kapanışta koşullu | Hayır | NULL | Gerekli kalıcılık kontrolü kanıtı | Hassas olabilir | Güvenli opak referans |
| servicenow_ticket_no | VARCHAR | 100 | Hayır | Hayır | NULL | Harici ticket numarası | Hassas olabilir | Issue başına tek aktif |

Kalite alarmı, ölçüm yeterliliği alarmı, teknik alarm ve remediation yaşam döngüsü
`DQ-SCR-028` ve `DQ-SCR-029` uyarınca ayrıdır. Geçici skor yükselişi tek başına
issue kapatmaz; etkin politika kök neden, yeterli yeniden ölçüm, doğrulama çalışması
ve kalıcılık kanıtından hangilerinin zorunlu olduğunu belirler. Hedef süreler
aktif, sürümlü remediation politikasından çözülür; politika yoksa otomatik son
tarih veya kapanış kararı üretilmez.

## OutboundIntegrationRecord

| Alan adı | Veri tipi | Uzunluk | Zorunluluk | Benzersizlik | Varsayılan değer | Açıklama | Hassas veri durumu | Doğrulama kuralı |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| outbound_record_id | UUID | 36 | Evet | Evet | Otomatik | Entegrasyon kaydı | Hayır | UUID |
| issue_id | UUID | 36 | Evet | Hayır | Yok | Yerel issue referansı | Hayır | Geçerli Issue |
| idempotency_key | VARCHAR | 200 | Evet | Evet | Yok | Mükerrer ticket önleme | Hassas olabilir | Payload özetiyle eşleşir |
| remote_record_id | VARCHAR | 200 | Hayır | Hayır | NULL | ServiceNow kayıt kimliği | Hassas olabilir | Dönüş allowlist'i |
| local_status | ENUM | 30 | Evet | Hayır | PENDING | Yerel entegrasyon durumu | Hayır | İzinli geçiş |
| remote_status | VARCHAR | 100 | Hayır | Hayır | NULL | Uzak sistem durumu | Hassas olabilir | Onaylı eşleme |
| retry_count | INTEGER | — | Evet | Hayır | 0 | Deneme sayısı | Hayır | Negatif olamaz |
| next_retry_at | TIMESTAMP | — | Hayır | Hayır | NULL | Artan bekleme sonrası zaman | Hayır | UTC |
| intervention_status | ENUM | 30 | Evet | Hayır | NONE | NONE/DEAD_LETTER/MANUAL | Hayır | İzinli enum |
| last_synced_at | TIMESTAMP | — | Hayır | Hayır | NULL | Son senkronizasyon | Hayır | UTC |
| error_code | VARCHAR | 100 | Hayır | Hayır | NULL | Güvenli hata kodu | Hayır | Onaylı sözlük |
| safe_error_summary | VARCHAR | 500 | Hayır | Hayır | NULL | Redakte hata özeti | Hassas olabilir | Ham kayıt/secret içermez |
| audit_reference | VARCHAR | 500 | Evet | Hayır | Yok | Audit izi | Hassas olabilir | Geçerli audit kaydı |

## IssueComment

| Alan adı | Veri tipi | Uzunluk | Zorunluluk | Benzersizlik | Varsayılan değer | Açıklama | Hassas veri durumu | Doğrulama kuralı |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| comment_id | UUID | 36 | Evet | Evet | Otomatik | Yorum anahtarı | Hayır | UUID |
| issue_id | UUID | 36 | Evet | Hayır | Yok | Sorun referansı | Hayır | Geçerli Issue |
| author_user_id | UUID | 36 | Evet | Hayır | Yok | Yazar | Kişisel | Aktif User |
| comment_text | TEXT | — | Evet | Hayır | Yok | Yorum | Hassas olabilir | HTML/zararlı içerik temizlenir |
| attachment_reference | VARCHAR | 500 | Hayır | Hayır | NULL | Güvenli dosya referansı | Hassas | İzinli tip, boyut ve tarama |
| created_at | TIMESTAMP | — | Evet | Hayır | Otomatik | Oluşturma UTC | Hayır | Değişmez |

## AuditLog

| Alan adı | Veri tipi | Uzunluk | Zorunluluk | Benzersizlik | Varsayılan değer | Açıklama | Hassas veri durumu | Doğrulama kuralı |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| audit_id | UUID | 36 | Evet | Evet | Otomatik | Audit anahtarı | Hayır | UUID |
| event_time | TIMESTAMP | — | Evet | Hayır | Otomatik | Olay UTC | Hayır | Değişmez |
| actor_id | VARCHAR | 128 | Evet | Hayır | SYSTEM | Kullanıcı/servis kimliği | Kişisel | Normalize |
| action | VARCHAR | 120 | Evet | Hayır | Yok | İşlem kodu | Hayır | Onaylı sözlük |
| object_type | VARCHAR | 80 | Evet | Hayır | Yok | Nesne türü | Hayır | Onaylı sözlük |
| object_id | VARCHAR | 128 | Hayır | Hayır | NULL | Nesne anahtarı | Hassas olabilir | Tip ile uyumlu |
| result | ENUM | 20 | Evet | Hayır | SUCCESS | SUCCESS/FAILURE/DENIED | Hayır | İzinli enum |
| old_value | JSON | — | Hayır | Hayır | NULL | Maskeli eski değer | Hassas | Secret/PII maskeli |
| new_value | JSON | — | Hayır | Hayır | NULL | Maskeli yeni değer | Hassas | Secret/PII maskeli |
| correlation_id | VARCHAR | 64 | Evet | Hayır | Otomatik | İzleme kimliği | Hayır | İstek içinde tutarlı |
| integrity_hash | VARCHAR | 128 | Evet | Hayır | Otomatik | Bütünlük değeri | Hassas | Doğrulanabilir hash/imza |

## Report

| Alan adı | Veri tipi | Uzunluk | Zorunluluk | Benzersizlik | Varsayılan değer | Açıklama | Hassas veri durumu | Doğrulama kuralı |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| report_id | UUID | 36 | Evet | Evet | Otomatik | Rapor anahtarı | Hayır | UUID |
| report_type | ENUM | 50 | Evet | Hayır | SUMMARY | Özet/detay/trend vb. | Hayır | İzinli enum |
| requested_by | UUID | 36 | Evet | Hayır | Yok | Talep eden kullanıcı | Kişisel | Aktif User |
| parameters | JSON | — | Evet | Hayır | {} | Filtre ve kapsam | Hassas olabilir | Yetki doğrulaması |
| format | ENUM | 10 | Evet | Hayır | PDF | PDF/XLSX/CSV | Hayır | İzinli enum |
| status | ENUM | 20 | Evet | Hayır | QUEUED | QUEUED/RUNNING/READY/FAILED/EXPIRED | Hayır | İzinli geçiş |
| sensitivity_level | VARCHAR | 100 | Evet | Hayır | Yok | Harici sınıflandırmadan türetilen hassasiyet | Hassas | Güncel sınıflandırma |
| retention_policy_id | UUID | 36 | Evet | Hayır | Yok | Saklama politikası referansı | Hayır | Geçerli politika |
| online_file_reference | VARCHAR | 500 | Hayır | Hayır | NULL | Çevrimiçi rapor dosyası | Hassas | Süreli ve yetkili erişim |
| archived_file_reference | VARCHAR | 500 | Hayır | Hayır | NULL | Arşivlenmiş rapor dosyası | Hassas | Arşiv erişim politikası |
| destruction_record_reference | VARCHAR | 500 | Hayır | Hayır | NULL | İmha edilmiş rapor kaydı | Hassas olabilir | İmha kanıtı |
| file_size | BIGINT | 19 | Hayır | Hayır | NULL | Dosya boyutu | Hayır | Politika sınırını aşamaz |
| expires_at | TIMESTAMP | — | Hayır | Hayır | NULL | Çevrimiçi erişim son zamanı | Hayır | Politika tablosundan hesaplanır |

## ReportStoragePolicy

| Alan adı | Veri tipi | Uzunluk | Zorunluluk | Benzersizlik | Varsayılan değer | Açıklama | Hassas veri durumu | Doğrulama kuralı |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| report_storage_policy_id | UUID | 36 | Evet | Evet | Otomatik | Politika anahtarı | Hayır | UUID |
| sensitivity_level | VARCHAR | 100 | Evet | Hayır | Yok | Rapor hassasiyet kapsamı | Hassas | Harici sınıflandırmayla uyumlu |
| online_duration | VARCHAR | 50 | Evet | Hayır | `P30D` | Çevrimiçi saklama süresi | Hayır | `RET-30D-EXPORT` ile uyumlu |
| archive_duration | VARCHAR | 50 | Evet | Hayır | `P0D` | Rapor dosyası arşiv süresi | Hayır | Metadata ayrı `P10Y` saklanır; dosya arşivlenmez |
| maximum_file_size | BIGINT | 19 | Evet | Hayır | Yok | Azami dosya boyutu | Hayır | Aktif rapor politikasında pozitif değer zorunlu; yoksa üretim reddedilir |
| access_policy_reference | VARCHAR | 500 | Evet | Hayır | Yok | Erişim politikası | Hassas olabilir | Hassas raporda daha sıkı olabilir |
| destruction_method | VARCHAR | 100 | Evet | Hayır | Yok | İmha yöntemi | Hayır | Onaylı yöntem |
| policy_version | VARCHAR | 80 | Evet | Koşullu benzersiz | Yok | Politika sürümü | Hayır | Değişmez |
| approval_status | ENUM | 30 | Evet | Hayır | DRAFT | Onay durumu | Hayır | İzinli geçiş |
| audit_reference | VARCHAR | 500 | Evet | Hayır | Yok | Audit referansı | Hassas olabilir | Geçerli audit kaydı |
