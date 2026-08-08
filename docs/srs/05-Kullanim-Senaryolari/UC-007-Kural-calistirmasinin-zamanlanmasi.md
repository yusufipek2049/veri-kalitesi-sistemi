---
type: use-case
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_document: Veri_Kalitesi_Izleme_ve_Skorlama_Sistemi_SRS_v0.1.md
source_version: "0.1"
source_section: "UC-007"
created_at: 2026-07-16
tags:
  - srs
  - uc
  - uc-007
---

# UC-007 — Kural çalıştırmasının zamanlanması

| Alan | Tanım |
| --- | --- |
| Kullanım Senaryosu ID | **UC-007** |
| Kullanım Senaryosu Adı | Kural çalıştırmasının zamanlanması |
| Amaç | Kuralların belirlenen zamanda otomatik çalışmasını sağlamak. |
| Kısa Açıklama | Kullanıcı kural veya kural grubu için tek seferlik/periyodik plan oluşturur. |
| Birincil Aktör | Data Steward |
| İkincil Aktörler | Veri Kalitesi Uzmanı; Zamanlama Servisi |
| Öncelik | Must |
| Tetikleyici | Kullanıcının “Zamanlama Oluştur” işlemini seçmesi. |
| Ön Koşullar | Kurallar aktif; kullanıcı zamanlama yetkisine sahip olmalıdır. |

**Temel Akış**

1. Kullanıcı kural grubunu seçer.
2. Zaman türü, saat dilimi, cron/periyot, öncelik ve bağımlılıklar girilir.
3. Sistem ifadeyi ve döngüsel bağımlılığı doğrular.
4. Sistem sonraki beş çalışma zamanını gösterir.
5. Kullanıcı planı etkinleştirir.
6. Schedule kaydı ve audit kaydı oluşur.
7. Zaman geldiğinde yürütme işi kuyruğa alınır.

**Alternatif Akışlar**

1. Kullanıcı bakım penceresi veya hariç tarih tanımlayabilir.
2. Pasif kaynağa bağlı plan pasif tutulabilir.

**İstisna Akışları**

1. Geçersiz cron, geçmiş tek seferlik tarih veya döngüsel bağımlılık reddedilir.
2. Kaynak pasifse iş oluşturulmaz ve teknik bildirim oluşturulur.

| Alan | Tanım |
| --- | --- |
| İş Kuralları | RULE-003, RULE-011 |
| Son Koşullar | Aktif zamanlama ve gelecekteki çalışma planı oluşur. |
| Başarı Garantisi | Belirlenen zamanda tek, izlenebilir iş yaratılır. |
| Minimum Garanti | Geçersiz plan çalıştırma üretmez; hata kaydedilir. |
| İlgili Fonksiyonel Gereksinimler | FR-037–FR-039, FR-043 |
| Kabul Kriterleri | Önizlenen saatle gerçekleşen tetik zamanı tanımlı tolerans içinde eşleşmelidir. |
