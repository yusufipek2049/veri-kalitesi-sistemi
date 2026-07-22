---
type: implementation-index
area: database
project: Veri Kalitesi İzleme ve Skorlama Sistemi
created_at: 2026-07-16
tags:
  - database
  - index
---

# Veritabanı ve Veri Modeli Haritası

- [Genel Model, Saklama ve ER Diyagramı](../01-SRS/07-Veri-Modeli/Veri-Modeli-Genel.md)
- [Kimlik ve Yetki Varlıkları](../01-SRS/07-Veri-Modeli/Kimlik-ve-Yetki-Varliklari.md)
- [Kaynak ve Metadata Varlıkları](../01-SRS/07-Veri-Modeli/Kaynak-ve-Metadata-Varliklari.md)
- [Kural ve Çalıştırma Varlıkları](../01-SRS/07-Veri-Modeli/Kural-ve-Calistirma-Varliklari.md)
- [Sorun, Bildirim ve Audit Varlıkları](../01-SRS/07-Veri-Modeli/Sorun-Bildirim-ve-Audit-Varliklari.md)
- [Kanıt ve Karar Desteği Varlıkları](../01-SRS/07-Veri-Modeli/Kanit-ve-Karar-Destegi-Varliklari.md)

## Tasarım İlkeleri

- Tarihsel sonuçlar kural sürümüne bağlı kalmalı.
- Kaynak bağlantı sırları veritabanında açık metin tutulmamalı.
- Audit kayıtları değişmezlik / bütünlük mekanizmasıyla korunmalı.
- Kayıt sınıfı bazlı `RetentionPolicy`, çevrimiçi/arşiv ayrımı ve imha kanıtı uygulanmalı; süreler onaysız uydurulmamalı.
- `SourceUsagePolicy`, `DatasetPartialScorePolicy` ve `RecoveryObjectivePolicy` sürümlü ve audit bağlantılı tutulmalı.
- Rapor dosyası, rapor metadatası, arşivlenmiş dosya ve imha kaydı ayrı yaşam döngülerinde saklanmalı.
- Ham kişisel veri kalıcı depoya gereksiz yere kopyalanmamalı.
- Kanıt içeriği kopyalanmamalı; `EvidenceItem/EvidenceLink` kaynak referansı ve
  digest ile çoktan çoğa bağlanmalı, audit log teknik kanıt yerine geçmemeli.
- Run, teşhis, öneri, remediation, chaos, timeline ve evidence package kayıtları
  append-only olmalı; fiziksel şema `OPEN-036` ve kapasite testinden önce
  varsayılmamalı.

## İterasyon 19E Şema Artımı

- `data_sources.revision`, aktivasyon onayını belirli bağlantı yapılandırması revizyonuna bağlayan pozitif sürüm alanıdır; legacy kayıtlar `1` ile geriye uyumlu taşınır.
- `data_source_activation_requests`, maker/checker kararı ve gerekçe kodunu tarihsel olarak saklar; secret, bağlantı yapılandırması veya ham sahiplik verisi kopyalamaz.
- Aktivasyon isteğinin `target_at`, `expires_at` ve `business_calendar_version` alanları nullable'dır; legacy 19E kayıtları değişmeden okunur, yeni süreli istekler hesaplandıkları takvim sürümünü korur.
- `WITHDRAWN` ve `EXPIRED` terminal kayıtları tarihsel olarak saklanır; kaynak durumu değiştirilmeden aynı revizyon için yeni `PENDING` istek açılabilir.
- `data_source_connection_revisions`, gizli olmayan bağlantı yapılandırmasını ve yalnız secret referansını değişmez aday/geçmiş revizyon olarak saklar; `PENDING_TEST`, `TEST_FAILED` ve `PROMOTED` durumlarını ayırır.
- `connection_test_results.data_source_revision`, test sonucunu denenen bağlantı revizyonuna bağlar; legacy sonuçlar revizyon `1` ile taşınır.
- Başarılı aday terfisi, kaynak revizyon/durum güncellemesi, eski `PENDING` aktivasyon isteklerinin `INVALIDATED` olması ve audit outbox yazımı aynı transaction içindedir.
- `(data_source_id, data_source_revision)` üzerinde yalnız `PENDING` kayıtları kapsayan benzersiz indeks aynı revizyona eş zamanlı birden fazla açık istek oluşmasını engeller.
- Onay kaydı, `ACTIVE` durum geçişi ve merkezi audit outbox aynı SQLite transaction içinde yazılır; üretim veritabanı ve migration aracı seçimi `OPEN-BNK-012` kapsamında açıktır.

## İterasyon 25B–25C Şema Artımı

- `legal_hold_events`, hold oluşturma ve serbest bırakma geçmişini append-only
  olaylarla saklar; aktif durum olaylardan yeniden kurulur.
- `disposal_jobs`, ham kayıt ve kapsam kimliği yerine SHA-256 özetleriyle
  değişmez aday snapshot'ını saklar. Idempotency özeti benzersizdir.
- `disposal_job_results`, iş başına tek terminal sonuç, sayaç, teknik hata kodu ve
  opak kanıt referansı taşır; ham silinen kayıt veya serbest hata metni içermez.
- İş/sonuç tablolarındaki `UPDATE` ve `DELETE` tetikleyicilerle reddedilir. Domain
  kaydı ile audit outbox aynı SQLite transaction içinde yazılır.
- SQLite yerel teknik prototiptir; üretim PostgreSQL migration'ı, uygulama
  rolünden ayrılmış değişmezlik yetkisi, bölümleme ve WORM kararı `OPEN-BNK-012`
  ve `OPEN-BNK-006` kapsamında açıktır.

## İterasyon 25D Şema Artımı

- `archive_recall_requests`, audit veya kalite skoru arşivi için idempotent ve
  değişmez talep snapshot'ını saklar; arşiv/kapsam kimlikleri yalnız SHA-256
  özeti olarak tutulur.
- `archive_recall_decisions`, talep başına tek `APPROVED` veya `REJECTED` kararı
  ve farklı karar aktörünü append-only saklar.
- Talep/karar tablolarındaki `UPDATE` ve `DELETE` tetikleyicilerle reddedilir;
  her yazım audit outbox ile aynı SQLite transaction'ındadır.
- Sık kullanılan zaman ve kapsam alanları indekslidir. Üretim PostgreSQL
  migration'ı, arşiv ürünü, bölümleme, at-rest şifreleme ve uygulama rolünden
  ayrılmış değişmezlik yetkisi açık kalır.
