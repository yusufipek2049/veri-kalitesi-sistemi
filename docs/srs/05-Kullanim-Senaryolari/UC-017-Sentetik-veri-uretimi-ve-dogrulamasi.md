---
type: use-case
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_section: "UC-017"
created_at: 2026-07-21
tags:
  - srs
  - uc
  - uc-017
  - synthetic-data
---

# UC-017 — Sentetik veri üretimi ve doğrulaması

| Alan | Tanım |
| --- | --- |
| Kullanım Senaryosu ID | **UC-017** |
| Kullanım Senaryosu Adı | Sentetik veri üretimi ve doğrulaması |
| Amaç | Gerçek banka verisini kopyalamadan kural, skor, performans ve olay davranışını bilinen sonuçlarla sınamak. |
| Kısa Açıklama | Yetkili kullanıcı onaylı politika ve senaryoyu seçer; sistem deterministik temel veriyi üretir, kusurları enjekte eder, bağımsız ground truth ve gizlilik/görev faydası doğrulaması oluşturur. |
| Birincil Aktör | Veri Kalitesi Uzmanı; Veri Mühendisi |
| İkincil Aktörler | Bilgi Güvenliği; Data Owner; Sistem Yöneticisi |
| Öncelik | Must |
| Tetikleyici | Yeni sentetik dataset veya replay talebi. |
| Ön Koşullar | Güvenilir kimlik ve scope; etkin `SyntheticDatasetPolicy`; sürümlü şema/senaryo; izinli ortam; audit kullanılabilirliği. |

**Temel Akış**

1. Kullanıcı dataset, dokuz profilden biri, hacim profili ve senaryo sürümünü seçer.
2. Sistem yetki, ortam, sınıflandırma, saklama ve sentetik üretim politikasını doğrular.
3. Sistem şema, ilişki, dağılım, zaman ve eksiklik profillerini yükler.
4. Kullanıcı politika tarafından izin verilen seed stratejisini ve kusur yoğunluk sınıfını seçer.
5. Sistem kusur içermeyen ilişkisel temel veriyi deterministik olarak üretir.
6. Sistem geçerli uç değerleri koruyarak yalnız senaryodaki kusurları enjekte eder.
7. Sistem runtime skor/kural motorundan bağımsız ground truth oluşturur.
8. Sistem yapısal, istatistiksel, görev faydası, gizlilik ve teknik doğrulamaları çalıştırır.
9. Gizlilik ve kullanım kapıları geçerse dataset onay/kullanım durumuna alınır.
10. Kural, skor ve gerekirse izole olay akışı çalıştırılır; karşılaştırıcı beklenen ve gerçekleşen sonuçları kaydeder.
11. Run, seed, üretici/şema/politika/ground truth sürümleri ve audit referansları katalogda saklanır.

**Alternatif Akışlar**

1. Replay talebinde aynı sürüm ve seed kullanılır; kanonik çıktı eşdeğerliği doğrulanır.
2. Stress profili kaynak kullanım kotası, bölümleme, örnekleme ve timeout davranışıyla çalışır.
3. Gizlilik Test Dataset'i yalnız kısıtlı güvenlik kapsamına açılır.
4. Olay Yönetimi Dataset'i yalnız fake veya açıkça doğrulanmış test adaptörüne yönlendirilir.

**İstisna Akışları**

1. Politika, şema, seed, ground truth veya zorunlu sürüm eksikse veri üretilmeden doğrulama hatası oluşur.
2. Üretim verisi kökenli girdi izinsizse ya da gizlilik eşiği kararsız/başarısızsa dataset `BLOCKED` olur.
3. Üretim bildirim/ServiceNow/SIEM hedefi seçilirse işlem fail-closed reddedilir.
4. Üretici, depo veya değerlendirici arızası `TECHNICAL_ERROR` olur; kalite kusuru veya başarılı gizlilik sonucu sayılmaz.
5. Gerçekleşen skor ground truth toleransını aşarsa doğrulama başarısız olur; ground truth runtime çıktısına göre değiştirilmez.

| Alan | Tanım |
| --- | --- |
| İş Kuralları | RULE-003–RULE-007, RULE-009–RULE-012, RULE-014, RULE-016, RULE-017 |
| Son Koşullar | Değişmez run, ground truth ve doğrulama kayıtları ile yaşam döngüsü durumu oluşur. |
| Başarı Garantisi | Datasetin kökeni, senaryosu, seed'i, sürümleri, kusurları ve beklenen/gerçekleşen sonuçları bağımsız ve yeniden üretilebilir biçimde izlenir. |
| Minimum Garanti | Gerçek veri kopyalanmaz, gerçek operasyon hedefi tetiklenmez, başarısız gizlilik çıktısı kullanıma açılmaz ve teknik hata kalite sonucu sayılmaz. |
| İlgili Fonksiyonel Gereksinimler | FR-088–FR-096 |
| Kabul Kriterleri | AC-048–AC-056 |
