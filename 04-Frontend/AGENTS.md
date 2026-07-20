# AGENTS.md — Frontend Geneli

- Görevi ilgili alt arayüz modülüne eşleştir ve onun `AGENTS.md` dosyasını oku.
- Her frontend görevinde önce `04-Frontend/Gorsel-Tasarim-Sistemi.md` ve ilgili ekran
  sözleşmesini oku; yeni component öncesi design-system envanterini kontrol et.
- Backend sözleşmesini tahmin etme; mevcut API şemasını veya ilgili backend modülünü doğrula.
- Yetkisiz eylemleri yalnız gizlemekle yetinme; backend 403 davranışını da bekle.
- `0`, `hesaplanmadı`, `veri yok`, `teknik hata` ve `kısmi` durumlarını görsel olarak ayır.
- Erişilebilirlik, klavye kullanımı, hata mesajı ve loading/empty state davranışlarını test et.
- Büyük tabloları sayfalama/sanal liste ile göster; hassas örnekleri maskeli sun.

## Tasarım sistemi kuralları

- Component dosyalarında ham HEX/RGB, spacing, radius veya shadow kullanma; yalnız
  semantik design token tüket.
- Marka sarısı `#FDB813` ana aksiyon, aktif durum, focus ve küçük vurgu içindir;
  uyarı, kritik ihlal veya teknik hata için kullanma. Sarı yüzeyde koyu metin kullan.
- Kritik kalite ihlalini kırmızı, teknik hatayı mor, uyarıyı turuncu, başarıyı yeşil,
  bilgiyi mavi ve veri yok durumunu gri göster; renk yanında ikon ve yazılı etiket kullan.
- Skor bulunmayan kayıtta `0` değil `—` ve açıklayıcı durum göster.
- Her içeriği karta kapatma; kart içinde kart, ağır gölge, glassmorphism, neon/gradient
  ve gereksiz animasyon kullanma.
- Grafik ve tabloyu aynı view-model'den besle; ortak formatter ve status mapper kullan.
- Grafiklerde gereksiz 3D/gradient kullanma; chart için tablo veya metinsel karşılık sağla.
- Form, tablo, KPI, alarm, drawer/modal için loading, empty, error, yetkisiz ve uzun
  içerik durumlarını birlikte tasarla.
- Uygun ikon kütüphanesi varsa tanıdık komutlarda ikon kullan; anlaşılmayan ikonlara
  tooltip ve erişilebilir ad ekle.

## Görsel doğrulama

- Değişen component için Storybook normal, loading, empty, error ve uzun içerik
  story'lerini görev kapsamına göre ekle.
- Playwright screenshot'larını en az `1440×900`, `1280×800` ve `1024×768` için al;
  ayrıca SRS kabul görünümleri `1366×768` ve `1920×1080` davranışını koru.
- Referansla spacing, tipografi, renk, yoğunluk ve hizalamayı karşılaştır; en az iki
  belgeli görsel iyileştirme turu yap.
- Görsel artifact'larda gerçek banka/müşteri verisi, secret, SQL, stack trace veya ham
  hatalı kayıt kullanma.
- Yeni Storybook, Playwright, chart veya component dependency'si için kullanıcı onayı al.

## Bankacılık ek kuralları

- UI rol veya kapsamı kendisi üretmez; backend authorization kararını uygular.
- Yetkisiz öğeyi yalnız gizlemek yeterli değildir; backend sorgusundan da dışlanmalıdır.
- Ham kişisel veri, müşteri sırrı veya banka sırrı varsayılan görünümde gösterilmez.
- Hassas dışa aktarma, kopyalama ve detay görüntüleme işlemleri gerekçe/onay ve audit gerektirebilir.
- Hata mesajları teknik detay, kaynak SQL, secret veya hassas alan değeri içermez.
