---
type: use-case
project: Veri Kalitesi İzleme ve Skorlama Sistemi
source_document: Veri_Kalitesi_Izleme_ve_Skorlama_Sistemi_SRS_v0.1.md
source_version: "0.1"
source_section: "UC-009"
created_at: 2026-07-16
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
| Amaç | Kural sonuçlarını açıklanabilir ham/nihai kalite skoru, ölçüm yeterliliği, kapsam, güven, kritiklik/risk, kritik durum, kullanım kararı ve teknik çalışma çıktısına dönüştürmek. (`DQ-SCR-001`, `DQ-SCR-016`–`DQ-SCR-021`) |
| Kısa Açıklama | Sistem geçerli sonuçları kural → veri öğesi → boyut → dataset hiyerarşisinde formül ve politika sürümlerine göre toplulaştırır; kalite ve ölçüm yeterliliğini ayrı değerlendirir. |
| Birincil Aktör | Sistem |
| İkincil Aktörler | Data Owner; Veri Yönetişimi Uzmanı |
| Öncelik | Must |
| Tetikleyici | Bir kural çalıştırmasının tamamlanması. |
| Ön Koşullar | Güvenilir execution bağlamı, dataset/snapshot/iş tarihi, sayaç kaynağı ve skor/yeterlilik politika sürümü çözülebilmelidir. |

**Temel Akış**

1. Sistem population, eligible, evaluated, passed, failed, excluded, teknik hata
   ve unknown sayaç değişmezlerini doğrular.
2. Değerlendirilen kayıt > 0 ve sonuç uygunsa kural skoru sürümlü normalizasyonla
   hesaplanır; ölçüm durumu ayrıca kaydedilir.
3. Kural skoru sürümlü eşik politikasıyla etiketlenir.
4. Geçerli kural skorlarından boyut skorları, boyut skorlarından
   `RawQualityScore` sürümlü ağırlık politikasıyla hesaplanır.
5. Kritik kural kapısı ağırlıklı ortalamadan bağımsız değerlendirilir;
   `FinalQualityScore`, `CriticalRuleStatus` ve `UsageDecision` üretilir.
6. Kapsam, örneklem güveni, kanıt tamamlığı, güncellik, zorunlu sürümler,
   doğrulamalar ve kritik kontroller `MeasurementQualificationStatus` üretir.
7. Dataset kritikliği, veri riski ve teknik çalışma durumu kalite ve yeterlilikten
   ayrı hesaplanır.
8. Execution, snapshot, iş tarihi, kural seti, referans veri, model/politika ve
   uygulama sürümleri saklanır.
9. Kalite, kritik kural, kullanım, yeterlilik veya teknik olay politikasına göre
   ayrı alarm ve remediation süreci tetiklenir.

**Alternatif Akışlar**

1. Kısmi çalışma yalnız dataset politikasındaki tüm koşulları sağlarsa `PARTIAL`
   etiketiyle resmî toplulaştırmaya katılır; aksi durumda provizyoneldir.
2. `NotApplicable`, `NotMeasured`, `NoData` ve `SuppressedByException` kendi
   durumlarıyla korunur; otomatik başarı/başarısızlık sayılmaz.
3. Eşik, ağırlık veya model sürümü değişirse yalnız yeni skorlar yeni sürümü
   kullanır; yeniden hesaplama orijinali koruyan ayrı sonuçtur.
4. Ham skor için onaylı değerlendirme/override varsa ham değer değiştirilmez ve
   ikisi ayrı gösterilir.
5. Önceki başarılı skor gösterilirse eski kaydın zamanı ve yeterlilik durumu
   korunur; güncel execution sonucu gibi kullanılmaz.
6. Kural, politika veya referans veri sürümü değişirse önceki kayıt korunur ve
   yeni yeterlilik değerlendirmesi `ValidationRequired` olabilir.

**İstisna Akışları**

1. Sıfır payda politika bağlamına göre `NotApplicable`, `NoData`, `NotMeasured`
   veya `TechnicalError` olur ve 0 puan sayılmaz.
2. Teknik hata `TechnicalError` olur; teknik sağlık olayı üretir, kalite skorunu
   sıfırlamaz ve kapsam/güveni düşürür.
3. Ağırlık toplamı 0 veya politika/sürüm eksikse üst skor hesaplanmaz ve
   yapılandırma hatası oluşur.
4. Kritik kural politikası bulunamazsa koruyucu varsayılan uygulanır; kritik
   başarısızlık yalnız ortalamada eritilmez, olumlu kullanım kararı üretilmez ve
   yeterlilik `NotQualified` olur.

| Alan | Tanım |
| --- | --- |
| İş Kuralları | RULE-003, RULE-004, RULE-005, RULE-006 |
| Son Koşullar | Kural/boyut/dataset skorları, MeasurementQualificationResult ve ilgili kullanım/teknik durum kayıtları oluşur. |
| Başarı Garantisi | Ham ve nihai skor, dahil/dışlanan bileşen, kapsam, güven, yeterlilik kapıları, kritiklik/risk, kritik kural, kullanım, teknik durum ve tüm sürüm referansları açıklanabilir biçimde saklanır. |
| Minimum Garanti | Hatalı veya eksik veri 0 puanla yanlış temsil edilmez. |
| İlgili Fonksiyonel Gereksinimler | FR-046–FR-053 |
| Kabul Kriterleri | Sayaç eşitlikleri sağlanmalı; 100/125 örneğinde 80,00 kural skoru ve 80×2 ile 100×1 örneğinde 86,67 boyut skoru üretilmeli; yüksek skor düşük kapsamda `Qualified` olmamalıdır. |
