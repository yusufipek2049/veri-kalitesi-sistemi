---
type: use-case
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_section: "UC-019"
created_at: 2026-07-22
tags: [srs, uc, uc-019, change-simulation]
---

# UC-019 — Değişiklik etki simülasyonu

| Alan | Tanım |
| --- | --- |
| Kullanım Senaryosu ID | **UC-019** |
| Amaç | Bir şema, pipeline, kural veya politika değişikliğinin yayılımını üretimi değiştirmeden görmek. |
| Birincil Aktör | Veri Mühendisi; Veri Kalitesi Uzmanı |
| İkincil Aktörler | Data Owner; Onaylayan; Risk Yönetimi |
| Öncelik | Should — ikinci faz |
| Tetikleyici | Kullanıcı değişmez aday değişikliği dry-run'a gönderir. |
| Ön Koşullar | Yetkili scope; aday sürüm; lineage snapshot'ı; simülasyon politikası. |

**Temel Akış**

1. Kullanıcı değişiklik türü, hedef ve aday sürümü seçer.
2. Sistem veri sözleşmesi ve lineage bağlarını çözer.
3. Sistem etkilenen kolon, dataset, kural, rapor, model ve veri ürününü çıkarır.
4. Sistem kaynaklı etki, beklenen skor/risk değişimi ve güveni hesaplar.
5. Sistem gerekli onay, doğrulama testi ve rollback ihtiyacını gösterir.
6. Kullanıcı sonucu onay akışına veya kanıt paketine bağlar.

**İstisna Akışları**

1. Lineage/politika eksikse sonuç `Incomplete` olur; kapsam daraltılmaz.
2. Kaynaksız parasal veya sayısal etki üretilmez.
3. Dry-run herhangi bir üretim verisi veya geçmiş sonuç değiştirmeye çalışırsa reddedilir.

| Alan | Tanım |
| --- | --- |
| İş Kuralları | RULE-002, RULE-005, RULE-007, RULE-018, RULE-020, RULE-023 |
| Son Koşullar | Simülasyon ve kanıt bağlantıları değişmez kaydedilir; üretim değişmez. |
| İlgili Fonksiyonel Gereksinimler | FR-100–FR-102, FR-106 |
| Kabul Kriterleri | AC-060, AC-061, AC-062, AC-065 |
