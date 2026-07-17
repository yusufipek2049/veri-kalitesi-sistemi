---
type: use-case
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_document: Veri_Kalitesi_Izleme_ve_Skorlama_Sistemi_SRS_v0.1.md
source_version: "0.1"
source_section: "UC-010"
generated_at: 2026-07-16
tags:
  - srs
  - uc
  - uc-010
---

# UC-010 — Dashboard üzerinden sonuçların incelenmesi

| Alan | Tanım |
| --- | --- |
| Kullanım Senaryosu ID | **UC-010** |
| Kullanım Senaryosu Adı | Dashboard üzerinden sonuçların incelenmesi |
| Amaç | Kullanıcının yetkili kalite durumunu özet ve detay seviyesinde analiz etmesi. |
| Kısa Açıklama | Kullanıcı tarih ve kapsam filtreleriyle skor, trend ve operasyonel bulguları inceler. |
| Birincil Aktör | İş Birimi Kullanıcısı |
| İkincil Aktörler | Data Owner; Data Steward; Veri Kalitesi Uzmanı |
| Öncelik | Must |
| Tetikleyici | Kullanıcının dashboardu açması. |
| Ön Koşullar | Kullanıcı oturumu ve skor/veri geçmişi bulunmalıdır. |

**Temel Akış**

1. Sistem kullanıcının veri kapsamını belirler.
2. Son 30 gün için genel KPI ve skorları yükler.
3. Kullanıcı kaynak, veri kümesi, boyut, sahip veya seviye filtresi uygular.
4. Trend grafiği ve operasyonel listeler güncellenir.
5. Kullanıcı düşük skordan veri kümesi ve kural detayına drill-down yapar.
6. Sistem çalıştırma, hata ve issue bağlantılarını gösterir.

**Alternatif Akışlar**

1. Kullanıcı grafik yerine tablo görünümünü seçer.
2. Hesaplanmamış dönemler boş/etiketli gösterilir.
3. Kullanıcı görünümü rapora dönüştürebilir.

**İstisna Akışları**

1. Yetki dışı nesne URL ile istenirse 403 döner.
2. Dashboard sorgusu timeout olursa daraltılmış tarih aralığı önerilir.
3. Veri yoksa yanıltıcı 0 yerine “veri yok” gösterilir.

| Alan | Tanım |
| --- | --- |
| İş Kuralları | RULE-004, RULE-009 |
| Son Koşullar | Kullanıcı yetkili kapsamda analiz görünümünü elde eder. |
| Başarı Garantisi | Skor ve alt bileşenleri tutarlı, filtrelenebilir ve açıklanabilir görüntülenir. |
| Minimum Garanti | Hata halinde veri sızıntısı olmaz; kullanıcıya izleme kodu gösterilir. |
| İlgili Fonksiyonel Gereksinimler | FR-021, FR-043, FR-050–FR-058 |
| Kabul Kriterleri | Varsayılan görünüm önerilen hedefte 3 saniyede açılmalı; drill-down yetkiyi aşmamalıdır. |
