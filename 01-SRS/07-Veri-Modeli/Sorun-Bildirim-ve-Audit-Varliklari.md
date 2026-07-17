---
type: data-dictionary-group
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_document: Veri_Kalitesi_Izleme_ve_Skorlama_Sistemi_SRS_v0.1.md
source_version: "0.1"
source_section: "Notification, DataQualityIssue, IssueComment, AuditLog, Report"
generated_at: 2026-07-16
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
| event_type | ENUM | 50 | Evet | Hayır | Yok | Eşik/teknik hata/atama vb. | Hayır | Onaylı sözlük |
| title | VARCHAR | 250 | Evet | Hayır | Yok | Bildirim başlığı | Hayır | Ham hassas veri içermez |
| body | TEXT | TBD | Evet | Hayır | Yok | Maskeli bildirim içeriği | Hassas olabilir | Şablon ve maskeleme |
| status | ENUM | 20 | Evet | Hayır | UNREAD | UNREAD/READ/SUPPRESSED/FAILED | Hayır | İzinli geçiş |
| deduplication_key | VARCHAR | 200 | Evet | Koşullu benzersiz | Yok | Tekrar önleme anahtarı | Hayır | Pencere içinde benzersiz |

## DataQualityIssue

| Alan adı | Veri tipi | Uzunluk | Zorunluluk | Benzersizlik | Varsayılan değer | Açıklama | Hassas veri durumu | Doğrulama kuralı |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| issue_id | UUID | 36 | Evet | Evet | Otomatik | Sorun anahtarı | Hayır | UUID |
| issue_no | VARCHAR | 40 | Evet | Evet | Otomatik | Kullanıcı görünen numara | Hayır | Tanımlı biçim |
| source_event_type | ENUM | 40 | Evet | Hayır | QUALITY | QUALITY/TECHNICAL/SCHEMA_CHANGE | Hayır | İzinli enum |
| status | ENUM | 30 | Evet | Hayır | NEW | Tanımlı issue durumları | Hayır | Geçiş matrisi |
| priority | ENUM | 20 | Evet | Hayır | MEDIUM | LOW/MEDIUM/HIGH/CRITICAL | Hayır | İzinli enum |
| assignee_user_id | UUID | 36 | Hayır | Hayır | NULL | Atanan kullanıcı | Kişisel | Aktif ve kapsam içi User |
| due_at | TIMESTAMP | TBD | Hayır | Hayır | NULL | Son tarih UTC | Hayır | Geçmiş olamaz |
| root_cause | TEXT | TBD | Çözümde evet | Hayır | NULL | Kök neden | Hassas olabilir | HTML temizlenir |
| corrective_action | TEXT | TBD | Çözümde evet | Hayır | NULL | Düzeltici faaliyet | Hassas olabilir | HTML temizlenir |
| servicenow_ticket_no | VARCHAR | 100 | Hayır | Hayır | NULL | Harici ticket numarası | Hassas olabilir | Issue başına tek aktif |

## IssueComment

| Alan adı | Veri tipi | Uzunluk | Zorunluluk | Benzersizlik | Varsayılan değer | Açıklama | Hassas veri durumu | Doğrulama kuralı |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| comment_id | UUID | 36 | Evet | Evet | Otomatik | Yorum anahtarı | Hayır | UUID |
| issue_id | UUID | 36 | Evet | Hayır | Yok | Sorun referansı | Hayır | Geçerli Issue |
| author_user_id | UUID | 36 | Evet | Hayır | Yok | Yazar | Kişisel | Aktif User |
| comment_text | TEXT | TBD | Evet | Hayır | Yok | Yorum | Hassas olabilir | HTML/zararlı içerik temizlenir |
| attachment_reference | VARCHAR | 500 | Hayır | Hayır | NULL | Güvenli dosya referansı | Hassas | İzinli tip, boyut ve tarama |
| created_at | TIMESTAMP | TBD | Evet | Hayır | Otomatik | Oluşturma UTC | Hayır | Değişmez |

## AuditLog

| Alan adı | Veri tipi | Uzunluk | Zorunluluk | Benzersizlik | Varsayılan değer | Açıklama | Hassas veri durumu | Doğrulama kuralı |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| audit_id | UUID | 36 | Evet | Evet | Otomatik | Audit anahtarı | Hayır | UUID |
| event_time | TIMESTAMP | TBD | Evet | Hayır | Otomatik | Olay UTC | Hayır | Değişmez |
| actor_id | VARCHAR | 128 | Evet | Hayır | SYSTEM | Kullanıcı/servis kimliği | Kişisel | Normalize |
| action | VARCHAR | 120 | Evet | Hayır | Yok | İşlem kodu | Hayır | Onaylı sözlük |
| object_type | VARCHAR | 80 | Evet | Hayır | Yok | Nesne türü | Hayır | Onaylı sözlük |
| object_id | VARCHAR | 128 | Hayır | Hayır | NULL | Nesne anahtarı | Hassas olabilir | Tip ile uyumlu |
| result | ENUM | 20 | Evet | Hayır | SUCCESS | SUCCESS/FAILURE/DENIED | Hayır | İzinli enum |
| old_value | JSON | TBD | Hayır | Hayır | NULL | Maskeli eski değer | Hassas | Secret/PII maskeli |
| new_value | JSON | TBD | Hayır | Hayır | NULL | Maskeli yeni değer | Hassas | Secret/PII maskeli |
| correlation_id | VARCHAR | 64 | Evet | Hayır | Otomatik | İzleme kimliği | Hayır | İstek içinde tutarlı |
| integrity_hash | VARCHAR | 128 | Evet | Hayır | Otomatik | Bütünlük değeri | Hassas | Doğrulanabilir hash/imza |

## Report

| Alan adı | Veri tipi | Uzunluk | Zorunluluk | Benzersizlik | Varsayılan değer | Açıklama | Hassas veri durumu | Doğrulama kuralı |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| report_id | UUID | 36 | Evet | Evet | Otomatik | Rapor anahtarı | Hayır | UUID |
| report_type | ENUM | 50 | Evet | Hayır | SUMMARY | Özet/detay/trend vb. | Hayır | İzinli enum |
| requested_by | UUID | 36 | Evet | Hayır | Yok | Talep eden kullanıcı | Kişisel | Aktif User |
| parameters | JSON | TBD | Evet | Hayır | {} | Filtre ve kapsam | Hassas olabilir | Yetki doğrulaması |
| format | ENUM | 10 | Evet | Hayır | PDF | PDF/XLSX/CSV | Hayır | İzinli enum |
| status | ENUM | 20 | Evet | Hayır | QUEUED | QUEUED/RUNNING/READY/FAILED/EXPIRED | Hayır | İzinli geçiş |
| file_reference | VARCHAR | 500 | Hayır | Hayır | NULL | Güvenli çıktı referansı | Hassas | Süreli erişim |
| expires_at | TIMESTAMP | TBD | Hayır | Hayır | NULL | İndirme son zamanı | Hayır | Oluşturma sonrası |
