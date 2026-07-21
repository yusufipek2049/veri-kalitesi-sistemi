# Yedekleme, Geri Yükleme ve DR

## Bileşen bazlı hedef matrisi

| Bileşen | RPO | RTO |
| --- | --- | --- |
| Sistem yapılandırmaları | TBD | TBD |
| Kural tanımları ve sürümleri | TBD | TBD |
| Eşik ve ağırlık politikaları | TBD | TBD |
| Kullanıcı ve rol eşlemeleri | TBD | TBD |
| Audit kayıtları | TBD | TBD |
| Onay kayıtları | TBD | TBD |
| Çalıştırma metadata kayıtları | TBD | TBD |
| Skor sonuçları | TBD | TBD |
| Rapor dosyaları | TBD | TBD |
| Bildirim ve entegrasyon kuyrukları | TBD | TBD |

Kesin değerler iş etki analizi yapılmadan atanmaz. Yeniden üretilemeyen veya hukuki/denetim değeri yüksek veri daha sıkı hedeflerle değerlendirilir.

## Diğer TBD kararlar
- Yedek sıklığı
- Şifreleme ve anahtar yönetimi
- Coğrafi/tesis ayrılığı
- Geri yükleme test sıklığı
- Saklama ve imha

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
sağlayıcısı ve secret manager `OPEN-BNK-012`; yedek şifreleme, RTO/RPO ve geri
yükleme sıklığı `OPEN-BNK-011` kararı olmadan tamamlanmış sayılmaz.
