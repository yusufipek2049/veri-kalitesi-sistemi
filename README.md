# Veri Kalitesi İzleme ve Skorlama Sistemi

Bu vault, SRS dokümanını görev bazında küçük bağlam parçalarıyla kullanmak için hazırlanmıştır.

## Başlangıç

1. Önce [Proje Özeti](00-Proje-Hafizasi/Proje-Ozeti.md) ve [Mevcut Durum](00-Proje-Hafizasi/Mevcut-Durum.md) notlarını oku.
2. Gereksinim aramak için [SRS Yönlendirme İndeksi](01-SRS/SRS-INDEX.md) üzerinden ilgili modüle git.
3. Bir geliştirme görevinde yalnız ilgili fonksiyonel gereksinim, kullanım senaryosu, veri varlığı ve NFR dosyalarını bağlama ekle.
4. Tam SRS yerine modül dosyalarını kullan.

## Ana Alanlar

- [Proje Hafızası](00-Proje-Hafizasi/Proje-Ozeti.md)
- [SRS](01-SRS/SRS-INDEX.md)
- [Mimari](02-Mimari/MIMARI-INDEX.md)
- [Backend](03-Backend/BACKEND-INDEX.md)
- [Frontend](04-Frontend/FRONTEND-INDEX.md)
- [Veritabanı](05-Veritabani/VERITABANI-INDEX.md)
- [Testler](06-Testler/TEST-INDEX.md)
- [Bankacılık Uyum Kontrolleri](01-SRS/17-Bankacilik-Uyum/INDEX.md)
- [Güvenlik Mimarisi](02-Mimari/Guvenlik/INDEX.md)
- [Operasyon](07-Operasyon/OPERASYON-INDEX.md)
- [Uyum Kanıtları](08-Uyum-Kanitlari/KANIT-INDEX.md)
- [Bankacılık Geçiş İterasyonları](09-Iterasyonlar/ITERASYON-INDEX.md)
- [Teknik Mimari ve Sistem Analizi](docs/technical/README.md)


## Güncel Geliştirme Baseline'ı

İterasyon 1–16 ile bankacılık geçişindeki 17A–24B, 26A–26B, 28A–28E ve 29A teknik dikeyleri tamamlanmış, 667 birim testi geçmektedir. Repository için veri-minimum güvenli SDLC kontrolleri ve 15 BDDK/KVKK kontrolünü eksik/engelli/inceleme bekleyen durumlarıyla ayıran deterministik teknik kanıt manifesti uygulanmıştır; sıradaki hazır aday manifest drift doğrulama kapısıdır.
