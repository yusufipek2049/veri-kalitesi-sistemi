# AGENTS.md — Dashboard

## Zorunlu bağlam

- `01-SRS/04-Fonksiyonel-Gereksinimler/04.06-Skorlama.md`
- `01-SRS/04-Fonksiyonel-Gereksinimler/04.07-Dashboard.md`
- `01-SRS/05-Kullanim-Senaryolari/UC-010-Dashboard-uzerinden-sonuclarin-incelenmesi.md`
- `04-Frontend/Gorsel-Tasarim-Sistemi.md`
- `04-Frontend/03-Dashboard/Dashboard-Ekran-Sozlesmesi.md`
- `04-Frontend/references/reference-dashboard.png`

- Ayrıca `01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.07-Kullanici-Deneyimi.md` dosyasını oku.
- Yetki, empty/loading/error ve erişilebilirlik durumlarını birlikte tasarla.
- Ekranı tek büyük bileşen yerine test edilebilir görünüm ve domain bileşenlerine böl.
- Her kullanıcı eylemini ilgili UC ana/alternatif akışıyla eşleştir.
- Grafik ve tablo aynı view-model'i kullanmalı; teknik hata mor, kritik kalite ihlali
  kırmızı gösterilmeli ve veri yok skoru `—` olmalıdır.
- Storybook durumlarını ve zorunlu Playwright viewport'larında en az iki görsel
  iyileştirme turunu tamamlamadan dashboard görevini kapatma.

## Bankacılık ek kuralları

- UI rol veya kapsamı kendisi üretmez; backend authorization kararını uygular.
- Yetkisiz öğeyi yalnız gizlemek yeterli değildir; backend sorgusundan da dışlanmalıdır.
- Ham kişisel veri, müşteri sırrı veya banka sırrı varsayılan görünümde gösterilmez.
- Hassas dışa aktarma, kopyalama ve detay görüntüleme işlemleri gerekçe/onay ve audit gerektirebilir.
- Hata mesajları teknik detay, kaynak SQL, secret veya hassas alan değeri içermez.
