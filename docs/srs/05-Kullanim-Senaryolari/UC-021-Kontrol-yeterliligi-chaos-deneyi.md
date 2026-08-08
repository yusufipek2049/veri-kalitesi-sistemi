---
type: use-case
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_section: "UC-021"
created_at: 2026-07-22
tags: [srs, uc, uc-021, chaos]
---

# UC-021 — Kontrol yeterliliği chaos deneyi

| Alan | Tanım |
| --- | --- |
| Kullanım Senaryosu ID | **UC-021** |
| Amaç | Veri kalite kontrollerinin kusurları tespit etme ve yanlış alarm davranışını güvenli ortamda ölçmek. |
| Birincil Aktör | Test Mühendisi; Veri Kalitesi Uzmanı |
| İkincil Aktörler | Bilgi Güvenliği; Data Owner; Onaylayan |
| Öncelik | Could — ikinci faz |
| Tetikleyici | Yetkili kullanıcı onaylı chaos deneyini başlatır. |
| Ön Koşullar | Sentetik dataset; izinli izole ortam; deney/fault politikası; rollback; audit. |

**Temel Akış**

1. Kullanıcı fault sınıfı, kapsam ve beklenen tespiti seçer.
2. Sistem ortam, gerçek veri, yetki, onay ve geri alma kapılarını doğrular.
3. Sistem kusuru enjekte eder ve bağımsız ground truth'u korur.
4. Kural/skor/olay akışı çalışır; tespit zamanı ve kapsam ölçülür.
5. Sistem enjekte, tespit, kaçırılan ve false-positive sonuçlarını karşılaştırır.
6. Sistem geri alır, doğrular ve deney kanıtını kapatır.

**İstisna Akışları**

1. Üretim veya gerçek müşteri verisi hedefi fail-closed reddedilir.
2. İzolasyon, rollback, politika veya onay eksikse enjeksiyon yapılmaz.
3. Teknik hata kalite başarısı veya kaçırılan hata olarak sınıflandırılmaz.

| Alan | Tanım |
| --- | --- |
| İş Kuralları | RULE-002, RULE-003, RULE-005, RULE-017, RULE-023 |
| Son Koşullar | Deney, fault, detection ve rollback kanıtları değişmez saklanır. |
| İlgili Fonksiyonel Gereksinimler | FR-110 |
| Kabul Kriterleri | AC-070 |
