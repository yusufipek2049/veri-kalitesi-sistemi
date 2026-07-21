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
| Amaç | Kural sonuçlarını açıklanabilir kalite skoru, kapsam, güven, kritiklik/risk ve teknik sağlık çıktısına dönüştürmek. (`DQ-SCR-001`, `DQ-SCR-019`–`DQ-SCR-021`) |
| Kısa Açıklama | Sistem geçerli sonuçları kural → veri öğesi → boyut → dataset hiyerarşisinde formül ve politika sürümlerine göre toplulaştırır. |
| Birincil Aktör | Sistem |
| İkincil Aktörler | Data Owner; Veri Yönetişimi Uzmanı |
| Öncelik | Must |
| Tetikleyici | Bir kural çalıştırmasının tamamlanması. |
| Ön Koşullar | Sayaçlar tutarlı; sonuç teknik hata dışı; skor konfigürasyonu geçerli olmalıdır. |

**Temel Akış**

1. Sistem kapsam dışı, değerlendirilen, başarılı, başarısız, istisnalı ve teknik
   nedenle değerlendirilemeyen sayaçları doğrular.
2. Değerlendirilen kayıt > 0 ve sonuç uygunsa kural skoru sürümlü normalizasyonla
   hesaplanır; ölçüm durumu ayrıca kaydedilir.
3. Kural skoru sürümlü eşik politikasıyla etiketlenir.
4. Geçerli kural skorları önce boyut, sonra dataset skoruna sürümlü dataset
   ağırlık politikasıyla katılır.
5. Kritik kural veto/tavan/blokaj politikası ağırlıklı ortalamadan bağımsız
   uygulanır.
6. Kapsam, güven, dataset kritikliği, veri riski ve teknik sağlık kalite
   skorundan ayrı hesaplanır.
7. Kullanılan model, kural, normalizasyon, eşik, ağırlık ve uygulama sürümleri
   saklanır.
8. Eşik, kötüleşme, kritik kural, kapsam/güven düşüşü veya teknik sağlık olayı
   varsa ayrı alarm ve remediation süreci tetiklenir.

**Alternatif Akışlar**

1. Kısmi çalışma yalnız dataset politikasındaki tüm koşulları sağlarsa `PARTIAL`
   etiketiyle resmî toplulaştırmaya katılır; aksi durumda provizyoneldir.
2. `NotApplicable`, `NotMeasured`, `NoData` ve `SuppressedByException` kendi
   durumlarıyla korunur; otomatik başarı/başarısızlık sayılmaz.
3. Eşik, ağırlık veya model sürümü değişirse yalnız yeni skorlar yeni sürümü
   kullanır; yeniden hesaplama orijinali koruyan ayrı sonuçtur.
4. Ham skor için onaylı değerlendirme/override varsa ham değer değiştirilmez ve
   ikisi ayrı gösterilir.

**İstisna Akışları**

1. Sıfır kayıt `NoData` olur ve 0 puan sayılmaz.
2. Teknik hata `TechnicalError` olur; teknik sağlık olayı üretir, kalite skorunu
   sıfırlamaz ve kapsam/güveni düşürür.
3. Ağırlık toplamı 0 veya politika/sürüm eksikse üst skor hesaplanmaz ve
   yapılandırma hatası oluşur.
4. Kritik kural politikası bulunamazsa koruyucu varsayılan uygulanır; kritik
   başarısızlık yalnız ortalamada eritilmez.

| Alan | Tanım |
| --- | --- |
| İş Kuralları | RULE-003, RULE-004, RULE-005, RULE-006 |
| Son Koşullar | Kural ve uygun üst seviye QualityScore kayıtları oluşur. |
| Başarı Garantisi | Formül, dahil/dışlanan bileşen, kapsam, güven, kritiklik/risk, teknik sağlık ve tüm sürüm referansları açıklanabilir biçimde saklanır. |
| Minimum Garanti | Hatalı veya eksik veri 0 puanla yanlış temsil edilmez. |
| İlgili Fonksiyonel Gereksinimler | FR-046–FR-053 |
| Kabul Kriterleri | 100/125 örneğinde 80,00; 80×2 ve 100×1 örneğinde 86,67 sonucu üretilmelidir. |
