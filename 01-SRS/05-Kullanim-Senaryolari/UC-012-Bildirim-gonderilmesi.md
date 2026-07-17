---
type: use-case
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_document: Veri_Kalitesi_Izleme_ve_Skorlama_Sistemi_SRS_v0.1.md
source_version: "0.1"
source_section: "UC-012"
generated_at: 2026-07-16
tags:
  - srs
  - uc
  - uc-012
---

# UC-012 — Bildirim gönderilmesi

| Alan | Tanım |
| --- | --- |
| Kullanım Senaryosu ID | **UC-012** |
| Kullanım Senaryosu Adı | Bildirim gönderilmesi |
| Amaç | İlgili kullanıcıya sistem içi olay bildirimi sunmak. |
| Kısa Açıklama | Bildirim servisi alıcı, şablon, tekrar ve susturma kurallarını uygular. |
| Birincil Aktör | Bildirim Servisi |
| İkincil Aktörler | Data Owner; Data Steward; Sistem Yöneticisi |
| Öncelik | Must |
| Tetikleyici | Bildirim olayı kuyruğa alınır. |
| Ön Koşullar | Alıcı ve şablon politikası mevcut olmalıdır. |

**Temel Akış**

1. Servis olayın kapsam ve kritikliğini okur.
2. Kural/veri kümesi/kaynak sahiplerinden alıcıları çözer.
3. Susturma ve tekrar penceresini kontrol eder.
4. Şablon değişkenlerini güvenli biçimde doldurur.
5. Notification kaydı oluşturur.
6. Kullanıcının bildirim merkezinde okunmamış olarak gösterir.
7. Teslim ve okundu durumu izlenir.

**Alternatif Akışlar**

1. Alıcı pasifse varsayılan yönetişim grubuna yönlendirme yapılır.
2. Kritik ve çözülmeyen olay eskalasyon kuralına göre üst role iletilir.

**İstisna Akışları**

1. Şablon değişkeni eksikse ham kişisel veri göstermeden varsayılan şablon kullanılır.
2. Aynı olay tekrar penceresinde yinelenirse yeni kayıt yerine sayaç/tarih güncellenir.

| Alan | Tanım |
| --- | --- |
| İş Kuralları | RULE-006, RULE-009, RULE-011 |
| Son Koşullar | Notification kaydı ve teslim durumu oluşur. |
| Başarı Garantisi | Doğru yetkili alıcıya olaydan sonra 5 dakika içinde bildirim görünür. |
| Minimum Garanti | Bildirim hatası olayın ve issue kaydının kaybolmasına yol açmaz. |
| İlgili Fonksiyonel Gereksinimler | FR-059–FR-063, FR-076, FR-085 |
| Kabul Kriterleri | Susturma ve deduplication testlerinde aynı olay için politika dışı tekrar oluşmamalıdır. |
