---
type: use-case
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_document: Veri_Kalitesi_Izleme_ve_Skorlama_Sistemi_SRS_v0.1.md
source_version: "0.1"
source_section: "UC-009"
generated_at: 2026-07-16
tags:
  - srs
  - uc
  - uc-009
---

# UC-009 — Veri kalite skorunun hesaplanması

| Alan | Tanım |
| --- | --- |
| Kullanım Senaryosu ID | **UC-009** |
| Kullanım Senaryosu Adı | Veri kalite skorunun hesaplanması |
| Amaç | Kural sonuçlarını açıklanabilir 0–100 skorlarına dönüştürmek. |
| Kısa Açıklama | Sistem geçerli sonuçları formül ve ağırlık sürümüne göre toplulaştırır. |
| Birincil Aktör | Sistem |
| İkincil Aktörler | Data Owner; Veri Yönetişimi Uzmanı |
| Öncelik | Must |
| Tetikleyici | Bir kural çalıştırmasının tamamlanması. |
| Ön Koşullar | Sayaçlar tutarlı; sonuç teknik hata dışı; skor konfigürasyonu geçerli olmalıdır. |

**Temel Akış**

1. Sistem toplam, başarılı, hatalı ve değerlendirilemeyen sayaçları doğrular.
2. Toplam > 0 ve sonuç uygunsa kural skoru hesaplanır.
3. Kural skoru eşik seviyesiyle etiketlenir.
4. Geçerli kural skorları ağırlıklı veri kümesi skoruna katılır.
5. Boyut, kaynak ve kurum skorları hesaplanır.
6. Kullanılan ağırlık/konfigürasyon sürümü saklanır.
7. Eşik veya kötüleşme olayı varsa sorun/bildirim süreci tetiklenir.

**Alternatif Akışlar**

1. Kısmi çalışma, politika izin verirse ayrı PARTIAL skor olarak gösterilir ancak kurum skoruna varsayılan olarak katılmaz.
2. Yönetici eşik setini değiştirirse yalnız yeni skorlar yeni sürümü kullanır; geçmiş yeniden yazılmaz.

**İstisna Akışları**

1. Sıfır kayıt NO_DATA olur ve 0 puan sayılmaz.
2. Teknik hata NOT_CALCULATED_TECHNICAL_ERROR olur.
3. Ağırlık toplamı 0 ise üst skor hesaplanmaz ve yapılandırma hatası oluşur.

| Alan | Tanım |
| --- | --- |
| İş Kuralları | RULE-003, RULE-004, RULE-005, RULE-006 |
| Son Koşullar | Kural ve uygun üst seviye QualityScore kayıtları oluşur. |
| Başarı Garantisi | Formül, dahil/dışlanan bileşen ve sürüm açıklanabilir biçimde saklanır. |
| Minimum Garanti | Hatalı veya eksik veri 0 puanla yanlış temsil edilmez. |
| İlgili Fonksiyonel Gereksinimler | FR-046–FR-053 |
| Kabul Kriterleri | 100/125 örneğinde 80,00; 80×2 ve 100×1 örneğinde 86,67 sonucu üretilmelidir. |
