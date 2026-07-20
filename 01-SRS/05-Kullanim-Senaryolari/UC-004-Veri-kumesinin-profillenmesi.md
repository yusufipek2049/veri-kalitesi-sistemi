---
type: use-case
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_document: Veri_Kalitesi_Izleme_ve_Skorlama_Sistemi_SRS_v0.1.md
source_version: "0.1"
source_section: "UC-004"
created_at: 2026-07-16
tags:
  - srs
  - uc
  - uc-004
---

# UC-004 — Veri kümesinin profillenmesi

| Alan | Tanım |
| --- | --- |
| Kullanım Senaryosu ID | **UC-004** |
| Kullanım Senaryosu Adı | Veri kümesinin profillenmesi |
| Amaç | Veri yapısını ve temel kalite özelliklerini analiz etmek. |
| Kısa Açıklama | Kullanıcı veri kümesini seçer; sistem metadata ve profil metriklerini çıkarır. |
| Birincil Aktör | Veri Kalitesi Uzmanı |
| İkincil Aktörler | Veri Mühendisi; Harici Veri Kaynağı |
| Öncelik | Must |
| Tetikleyici | Kullanıcının veri kümesi için profil başlatması. |
| Ön Koşullar | Kaynak aktif ve test edilmiş; kullanıcı veri alanında yetkili olmalıdır. |

**Temel Akış**

1. Kullanıcı kaynak, şema, veri kümesi ve alanları seçer.
2. Sistem tahmini kayıt hacmi ve önerilen tam tarama/örnekleme yöntemini gösterir.
3. Kullanıcı kapsamı onaylar.
4. Sistem metadata taraması ve profil sorgularını çalıştırır.
5. Null, benzersizlik, min/max, ortalama, dağılım, desen ve uygun analizler hesaplanır.
6. Hassas örnekler maskelenir.
7. Profil sonucu saklanır ve önceki sürümle fark gösterilir.

**Alternatif Akışlar**

1. 20 milyon satıra yaklaşan veya aşan tabloda sistem bölümleme, kaynakta toplulaştırma veya örnekleme önerir.
2. Kullanıcı yalnız seçili alanları veya tarih bölümünü profilleyebilir.

**İstisna Akışları**

1. Kaynak şeması çalışma sırasında değişirse sonuç PARTIAL/TECHNICAL_ERROR olarak işaretlenir.
2. Timeout veya kaynak kotası aşımında iş durdurulur ve teknik hata oluşur.
3. Boş veri kümesinde profil NO_DATA olarak saklanır.

| Alan | Tanım |
| --- | --- |
| İş Kuralları | RULE-002, RULE-003, RULE-010 |
| Son Koşullar | DataProfile ve metadata sürümü oluşur. |
| Başarı Garantisi | Profil yöntemi, kapsamı ve metrikleri izlenebilir biçimde saklanır. |
| Minimum Garanti | Başarısızlıkta kaynakta değişiklik yapılmaz ve kısmi sonuç resmi skor üretmez. |
| İlgili Fonksiyonel Gereksinimler | FR-011, FR-015–FR-022 |
| Kabul Kriterleri | Profil sonucu kullanılan örneklem oranını, süreyi ve tüm hesaplanan metrikleri göstermelidir. |
