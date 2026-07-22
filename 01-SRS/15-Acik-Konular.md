---
type: srs-section
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_document: Veri_Kalitesi_Izleme_ve_Skorlama_Sistemi_SRS_v0.1.md
source_version: "0.1"
source_section: "15"
created_at: 2026-07-16
tags:
  - srs
  - open-topic
---

# Açık Konular ve Varsayımlar

Bu bölüm karar kayıtları ile bunların uygulama veya kurumsal inceleme
bağımlılıklarını görünür kılar. `OPEN-001`–`OPEN-018` kararları kesinleşmiş ve
[Alınan Kararlar](../00-Proje-Hafizasi/Alinan-Kararlar.md#open-001open-018-kesinleşmiş-kararları)
belgesine taşınmıştır; artık açık konu değildir. Ürün adı, sayısal politika değeri
veya banka onayı gerektiren yeni belirsizlikler aşağıdaki ayrı kayıtlarla izlenir.

| Konu ID | Açıklama | Kategori | Karar sahibi | Hedef karar tarihi | Etkilenen gereksinimler |
| --- | --- | --- | --- | --- | --- |
| OPEN-019 | Normalizasyon, eşik/ağırlık, kritik davranış, kapsam/güven ve risk değerleri aktif, sürümlü ve onaylı politikadan çözülür; kayıt yoksa ilgili olumlu sonuç üretilmez. | KararAlındı | Veri Yönetişimi / Risk Yönetimi / İç Kontrol | Karar kaydı mevcut | FR-047–FR-052, AC-030–AC-032; OPEN-BNK-004/013 |
| OPEN-020 | Çekirdek hiyerarşi kural → veri öğesi → boyut → dataset → kaynak → kurumdur; veri ürünü/rapor/veri alanı yalnız sürümlü kurumsal sözlük kaydı varsa açılır. | KararAlındı | Veri Yönetişimi / Risk Yönetimi | Karar kaydı mevcut | FR-050, DQ-SCR-002/003/018/019 |
| OPEN-021 | Override varsayılan olarak yasaktır; yalnız süreli, gerekçeli, risk kabul referanslı, maker-checker onaylı ve ham skordan ayrı kayıtla uygulanabilir. Rol eşlemesi yoksa işlem reddedilir. | KararAlındı | Veri Yönetişimi / İç Kontrol / Bilgi Güvenliği | Karar kaydı mevcut | FR-035, FR-077, DQ-SCR-022/023/030; OPEN-BNK-004/005/006/008 |
| OPEN-022 | Skor geçişi append-only yeni model sürümü ve `original_score_id` ilişkisiyle yapılır; tarihsel kayıt yerinde değiştirilmez. Geri alma yeni writer'ı pasifleştirir, geçmişi yeniden yazmaz. | KararAlındı | Mimari / Veri Yönetişimi / Operasyon | Karar kaydı mevcut | FR-048–FR-052, ADR-015, DQ-SCR-005/006/018/025/032 |
| OPEN-023 | Yeterlilik, kapsam, güven, geçerlilik, kullanım ve remediation değerleri aktif sürümlü politikadan çözülür; kayıt yoksa `Qualified` veya olumlu kullanım kararı üretilmez. | KararAlındı | Veri Yönetişimi / Risk Yönetimi / İç Kontrol / Operasyon / Bilgi Güvenliği | Karar kaydı mevcut | FR-048–FR-053, RULE-004–RULE-007, AC-039–AC-047; OPEN-BNK-004/008/010/013/017 |
| OPEN-024 | Sentetik eşik, kusur yoğunluğu ve skor toleransı sürümlü senaryo/politika girdisidir; eksik değer varsayılmaz ve doğrulama `BLOCKED` olur. Golden yapısal profil sıfır kusur varsayımını korur. | KararAlındı | Veri Yönetişimi / Risk Yönetimi / Bilgi Güvenliği / Yazılım Mimari | Karar kaydı mevcut | FR-090–FR-095, NFR-PERF-010, NFR-PRV-007, AC-050–AC-053; ADR-016 |
| OPEN-025 | Üretim profili/örneğinden öğrenme varsayılan olarak kapalıdır. Yalnız veri sahibi, hukuk/KVKK ve bilgi güvenliği onaylı; minimize edilmiş, izole ve saklama politikası bağlı referansla ayrı politika sürümünde açılabilir. | KararAlındı; ComplianceReviewRequired | Veri Sahibi / Hukuk / KVKK / Bilgi Güvenliği / Veri Yönetişimi | Karar kaydı mevcut | FR-095, NFR-PRV-007, AC-053, ADR-016; OPEN-014, OPEN-BNK-007/008/012 |

## DQ-SCR Kararlarının Bankacılık Karar ve İnceleme Kayıtlarıyla İlişkisi

`DQ-SCR` kararlarının kabulü, teknik yönü seçilmiş `KararAlındı` kayıtlarının
kalan banka onayını veya gerçek açık/inceleme kayıtlarını otomatik
olarak tamamlamaz. Bu ilişkiler kurumsal politika, banka onayı veya üretim kanıtı
gereken bağımlılıkları gösterir.

| DQ-SCR kararları | İlişkili bankacılık kayıtları | Kalan karar veya onay alanı |
| --- | --- | --- |
| DQ-SCR-003, DQ-SCR-015, DQ-SCR-018, DQ-SCR-019 | OPEN-BNK-013 | Düzenleyici raporlama/risk zinciri kapsamı ve kurumsal veri hiyerarşisi |
| DQ-SCR-005, DQ-SCR-023, DQ-SCR-030, DQ-SCR-032 | OPEN-BNK-005, OPEN-BNK-006, OPEN-BNK-016 | Kritik işlem auditi, bütünlük, kalıcı outbox ve yeniden oynatma altyapısı |
| DQ-SCR-014, DQ-SCR-015, DQ-SCR-017, DQ-SCR-022, DQ-SCR-023, DQ-SCR-030 | OPEN-BNK-004 | Skorlama politikası, istisna ve override için maker-checker kapsamı ve banka rolleri |
| DQ-SCR-014, DQ-SCR-015 | OPEN-BNK-007 | Kurumsal sınıflandırma ve hassasiyet bağlamına göre politika seçimi |
| DQ-SCR-022, DQ-SCR-032 | OPEN-BNK-008 | İstisna, override ve yeniden hesaplama kayıtlarının saklama/imha politikası |
| DQ-SCR-028 | OPEN-BNK-010 | Skor alarmı olay sözlüğü, seviye ve SOC eskalasyon akışı |
| DQ-SCR-026 | OPEN-BNK-014 | Skor ve eğilim dışa aktarımlarında DLP, gerekçe, onay ve watermark politikası |
| DQ-SCR-012, DQ-SCR-028, DQ-SCR-029, DQ-SCR-031 | OPEN-BNK-017 | Zaman bağımlı politika/onay işlemlerinin süre aşımı ve politika sahipliği |
| DQ-SCR-031 | OPEN-BNK-011, OPEN-BNK-012 | Yeniden üretilebilirlik için yedekleme hedefleri ve üretim platformu |
| DQ-SCR-033 | OPEN-BNK-001, OPEN-BNK-004, OPEN-BNK-013 | Yönetişim modelinin uyum, iç kontrol ve risk kapsamı onayı |
| Ölçüm yeterliliği ve kullanım kararı | OPEN-BNK-004, OPEN-BNK-008, OPEN-BNK-010, OPEN-BNK-013, OPEN-BNK-017 | Onay rolleri, saklama, olay sözlüğü, düzenleyici kullanım kapsamı ve süreli politika sahipliği (`OPEN-023`) |
