---
type: use-case
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_document: Veri_Kalitesi_Izleme_ve_Skorlama_Sistemi_SRS_v0.1.md
source_version: "0.1"
source_section: "UC-015"
generated_at: 2026-07-16
tags:
  - srs
  - uc
  - uc-015
---

# UC-015 — Veri kalitesi raporu oluşturulması

| Alan | Tanım |
| --- | --- |
| Kullanım Senaryosu ID | **UC-015** |
| Kullanım Senaryosu Adı | Veri kalitesi raporu oluşturulması |
| Amaç | Yetkili kalite sonuçlarını sunulabilir ve dışa aktarılabilir rapora dönüştürmek. |
| Kısa Açıklama | Kullanıcı rapor türü, kapsam ve format seçer. |
| Birincil Aktör | Data Owner |
| İkincil Aktörler | Data Steward; Denetçi; Raporlama Servisi |
| Öncelik | Must |
| Tetikleyici | Kullanıcının raporlama ekranında rapor oluşturması. |
| Ön Koşullar | Kullanıcı rapor kapsamına ve dışa aktarmaya yetkili olmalıdır. |

**Temel Akış**

1. Kullanıcı özet, detay, trend, birim, sahip, kritik veri veya sorun performans raporunu seçer.
2. Tarih ve kapsam filtrelerini girer.
3. Sistem yetkiyi ve tahmini çıktı büyüklüğünü kontrol eder.
4. Rapor görünümü üretilir.
5. Kullanıcı PDF, Excel veya CSV formatı seçer.
6. Sistem kişisel veri maskelemesini ve satır limitini uygular.
7. Dosya güvenli olarak oluşturulur ve indirme audit kaydı yazılır.

**Alternatif Akışlar**

1. Büyük rapor asenkron hazırlanır ve sistem içi bildirimle bağlantı sunulur.
2. Kullanıcı raporu zamanlayabilir.

**İstisna Akışları**

1. Yetkisiz veri alanı filtrede olsa bile çıktıya dahil edilmez.
2. Dosya satır sınırı aşılırsa bölme veya daraltma uyarısı verilir.
3. Rapor üretim hatasında kısmi dosya sunulmaz.

| Alan | Tanım |
| --- | --- |
| İş Kuralları | RULE-008, RULE-009, RULE-010 |
| Son Koşullar | Report kaydı ve gerekiyorsa dosya oluşur. |
| Başarı Garantisi | Rapor ekranla aynı filtre ve toplamları içerir; indirme izlenebilir olur. |
| Minimum Garanti | Hata halinde yetkisiz veya kısmi veri dışarı çıkmaz. |
| İlgili Fonksiyonel Gereksinimler | FR-072–FR-076 |
| Kabul Kriterleri | Aynı filtrede ekran ve rapor toplamları eşleşmeli; indirme auditlenmelidir. |
