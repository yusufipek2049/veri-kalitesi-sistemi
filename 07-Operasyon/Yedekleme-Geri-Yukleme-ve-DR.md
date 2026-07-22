# Yedekleme, Geri Yükleme ve DR

## Bileşen bazlı hedef matrisi

| Bileşen | Normal kapsam RPO / RTO | Kritik düzenleyici veya risk zinciri RPO / RTO |
| --- | --- | --- |
| Sistem yapılandırmaları | `PT15M` / `PT4H` | `PT5M` / `PT1H` |
| Kural tanımları ve sürümleri | `PT15M` / `PT4H` | `PT5M` / `PT1H` |
| Eşik ve ağırlık politikaları | `PT15M` / `PT4H` | `PT5M` / `PT1H` |
| Kullanıcı ve rol eşlemeleri | `PT15M` / `PT4H` | `PT5M` / `PT1H` |
| Audit kayıtları | `PT15M` / `PT4H` | `PT5M` / `PT1H` |
| Onay kayıtları | `PT15M` / `PT4H` | `PT5M` / `PT1H` |
| Çalıştırma metadata kayıtları | `PT15M` / `PT4H` | `PT5M` / `PT1H` |
| Skor sonuçları | `PT15M` / `PT4H` | `PT5M` / `PT1H` |
| Rapor dosyaları | `PT15M` / `PT4H` | `PT5M` / `PT1H` |
| Bildirim ve entegrasyon kuyrukları | `PT15M` / `PT4H` | `PT5M` / `PT1H` |

Normal kapsam ile kritik düzenleyici/risk zinciri ayrımı `OPEN-BNK-013`
kapsam kaydından çözülür. Kapsam kaydı yoksa daha sıkı hedef uygulanır.
Farklı bileşen hedefi ancak sürümlü `RecoveryObjectivePolicy` ile
etkinleştirilebilir.

## Diğer Kesin Kararlar

- Yedek sıklığı etkin RPO hedefini karşılayacak biçimde otomasyon politikasıyla
  uygulanır; bunu kanıtlamayan ortam üretime açılamaz.
- Yedekler kurumsal anahtar yönetimiyle şifrelenir; anahtar yedekle aynı hata
  alanında veya açık metin tutulmaz.
- Üretim yedeği uygulama/veritabanı birincil hata alanından ayrı tutulur.
- Geri yükleme testi sürümlü operasyon politikasında zorunludur; aktif test
  sıklığı kaydı veya güncel başarılı kanıt yoksa DR kontrolü fail-closed kalır.
- Saklama ve imha `RET-*` teknik politika matrisiyle yürütülür; legal hold imhaya
  üstündür.

## Tatbikat kanıtı

- yedek kimliği
- başlangıç/bitiş
- geri yüklenen kapsam
- veri bütünlüğü kontrolü
- erişim kontrolü
- gerçekleşen RTO/RPO
- sapma ve aksiyon

## 27A Ortam Başlangıç Kontrolü

Uygulama iş yükü başlatılmadan önce sürümlü ortam başlangıç kapısı başarıyla
tamamlanmalıdır. Operasyon aşağıdaki veri-minimum alanları kaydedebilir:

- politika sürümü
- konfigürasyon revizyonu
- ortam sınıfı
- veri kökeni sınıfı
- secret kapsamı
- sabit kontrol kodları ve `PASSED` durumu

Secret referans yolu, secret değeri, host, kullanıcı, IP veya veri örneği kanıta
yazılmaz. Konfigürasyon sağlayıcısı okunamıyorsa teknik hata; üretim verisi veya
secret kapsamı ortamla uyuşmuyorsa politika engeli oluşur. Her iki durumda da iş
yükü başlatılmaz.

Bu kontrol yedekleme, geri yükleme veya DR tatbikatı değildir. Gerçek deployment
sağlayıcısı, secret manager, yedek şifreleme ve geri yükleme otomasyonu
uygulanıp kanıtlanmadan üretim DR kontrolü tamamlanmış sayılmaz.
