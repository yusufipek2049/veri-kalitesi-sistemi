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
bağımlılıklarını görünür kılar. `OPEN-001`–`OPEN-036` karar yönleri kesinleşmiş ve
[Alınan Kararlar](../00-Proje-Hafizasi/Alinan-Kararlar.md) belgesine taşınmıştır;
artık açık konu değildir. Uygulama, üretim konfigürasyonu veya banka onayı
gerektiren bağımlılıklar proje hafızası ve `OPEN-BNK-*` kayıtlarında izlenir.

Bu ID serisinde açık teknik karar kalmamıştır. Banka onayı veya kurumsal
inceleme gerektiren konular aşağıdaki `OPEN-BNK-*` ilişkileriyle ve proje
hafızasındaki açık konu tablosuyla izlenir.

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
