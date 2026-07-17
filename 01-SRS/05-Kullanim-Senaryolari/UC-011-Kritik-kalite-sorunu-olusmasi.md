---
type: use-case
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_document: Veri_Kalitesi_Izleme_ve_Skorlama_Sistemi_SRS_v0.1.md
source_version: "0.1"
source_section: "UC-011"
generated_at: 2026-07-16
tags:
  - srs
  - uc
  - uc-011
---

# UC-011 — Kritik kalite sorunu oluşması

| Alan | Tanım |
| --- | --- |
| Kullanım Senaryosu ID | **UC-011** |
| Kullanım Senaryosu Adı | Kritik kalite sorunu oluşması |
| Amaç | Kritik başarısızlığın olay, bildirim ve sorun kaydına dönüşmesini sağlamak. |
| Kısa Açıklama | Skor veya kural sonucu politika koşulunu ihlal ettiğinde sistem otomatik işlem başlatır. |
| Birincil Aktör | Sistem |
| İkincil Aktörler | Data Owner; Data Steward; Bildirim Servisi |
| Öncelik | Must |
| Tetikleyici | Kritik kural başarısızlığı, eşik ihlali veya kalıcı teknik hata. |
| Ön Koşullar | Kural/sahiplik/eşik politikaları tanımlı olmalıdır. |

**Temel Akış**

1. Sistem olay türünü veri kalitesi veya teknik hata olarak sınıflandırır.
2. Kritiklik, kapsam ve mevcut açık sorun kontrol edilir.
3. Uygunsa yeni DataQualityIssue oluşturulur veya mevcut sorun güncellenir.
4. Öncelik ve sorumlu atanır.
5. Sistem içi bildirim olayı yaratılır.
6. Dashboard kritik sorun sayaçları güncellenir.
7. Tüm işlemler audit/issue geçmişine yazılır.

**Alternatif Akışlar**

1. Skor yalnız kötüleşme eşiğini aşmışsa issue yerine önce bildirim politikası uygulanabilir.
2. Kaynak şema değişikliği etkilenen kuralları inceleme gerekli durumuna alabilir.

**İstisna Akışları**

1. Sahip bulunamazsa sorun yönetişim varsayılan kuyruğuna atanır ve yapılandırma uyarısı oluşur.
2. Bildirim servisi hata verirse olay retry kuyruğuna alınır.
3. Aynı olay tekrarında çift issue oluşturulmaz.

| Alan | Tanım |
| --- | --- |
| İş Kuralları | RULE-003, RULE-006, RULE-011 |
| Son Koşullar | Issue, bildirim ve geçmiş kaydı oluşur veya mevcut kayıt güncellenir. |
| Başarı Garantisi | Kritik olay 5 dakika içinde sahipli ve izlenebilir hale gelir. |
| Minimum Garanti | Entegrasyon hatasında olay kaybolmaz; retry veya hata kuyruğunda kalır. |
| İlgili Fonksiyonel Gereksinimler | FR-022, FR-059–FR-064 |
| Kabul Kriterleri | Aynı olay tek açık issue üretmeli; teknik ve kalite hataları ayrı kodlanmalıdır. |
