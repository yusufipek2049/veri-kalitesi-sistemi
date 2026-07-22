# Veri Kalitesi İzleme ve Skorlama Sistemi

Bu vault, bankacılık bağlamındaki kanıta dayalı ve politika farkındalıklı veri
kalitesi karar sisteminin gereksinim, mimari, uygulama ve test kayıtlarını görev
bazında küçük bağlam parçalarıyla kullanmak için hazırlanmıştır. Sistem mevcut
fazda ölçüm/skorlama çekirdeğini; ikinci faz hedefinde kullanım amacı uygunluğu,
kanıt/lineage, etki, kontrollü öneri ve yeniden üretilebilir karar desteğini
tanımlar. Kaynak üretim verisini değiştirmez.

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
- [Bağlayıcı Veri Kalitesi Skorlama Kararları](01-SRS/04-Fonksiyonel-Gereksinimler/04.06-Skorlama.md#bağlayıcı-skorlama-kararları)
- [Skorlama ve Ölçüm Yeterliliği Tasarımı](02-Mimari/Veri-Kalitesi-Skorlama-ve-Olcum-Yeterliligi.md)
- [Sentetik Veri ve Gizlilik Stratejisi](02-Mimari/Sentetik-Veri-ve-Gizlilik-Stratejisi.md)
- [Kanıta Dayalı Karar Sistemi](02-Mimari/Kanita-Dayali-Karar-Sistemi.md)
- [Kanıta Dayalı Karar Desteği Gereksinimleri](01-SRS/04-Fonksiyonel-Gereksinimler/04.14-Kanita-Dayali-Karar-Destegi.md)


## Güncel Geliştirme Baseline'ı

İterasyon 1–16 ile bankacılık geçiş ve ürün artımları kapsamında 1029 test
geçmekte, iki gerçek PostgreSQL entegrasyon testi opt-in çalışmaktadır. Tam mypy
159 kaynak dosyada temizdir. Repository için veri-minimum güvenli SDLC
kontrolleri ve yerel preflight uygulanmıştır. `DQ-SCR-001–033` skorlama modeli ile
`FR-097–111` kanıta dayalı karar desteği hedefi dokümante edilmiştir; ikinci grup
henüz runtime uygulaması değildir ve `OPEN-026–036` kararlarını bekler.
