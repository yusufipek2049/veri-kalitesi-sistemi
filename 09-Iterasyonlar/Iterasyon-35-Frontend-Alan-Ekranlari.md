---
iteration: 35
status: in-progress
completed_at: null
---

# İterasyon 35 — Frontend Alan Ekranları

## 35A — Salt Okunur Veri Kaynakları Ekranı

Durum: **TechnicallyVerified**

### Kullanıcı Değeri

Yetkili kullanıcı, erişebildiği veri kaynaklarını gerçek bir istemci rotasında
ürün bağımsız tür, bağlantı testi durumu ve son test zamanı ile tarayabilir.

### Kapsam

- Güvenilir aktör kapsamına göre filtrelenen `GET /api/v1/data-sources`.
- Bağlantı yapılandırması, secret referansı ve sahip kimliği içermeyen DTO.
- `/data-sources`, yetkisiz ve bulunamadı rotaları; route bazlı kod bölme.
- Metin, durum, son test tarihi ve sabit yetkili kapsam filtreleri.
- Ürün bağımsız, sabit eksenli Lucide kaynak ikonları ve iki tema.
- Loading, empty, technical error, unauthorized ve long-content durumları.

### Gereksinim Bağlantıları

- `FR-007–FR-014`
- `FE-DS-015`
- `NFR-USA-001–NFR-USA-006`

### Doğrulama

- Backend: dört yeni API testi ve bir repository testi; scope filtresi, sahte
  header reddi, veri-minimum yanıt, boş kapsam ve güvenli teknik hata.
- Frontend: 26 Vitest ve 27 Playwright testi; beş viewport, açık/koyu tema,
  yatay taşma, ikon ekseni, filtre, klavye odağı ve yetkisiz veri ifşa etmeme.
- TypeScript, Vite/Storybook build, production npm audit, 1036 pytest, 161
  dosyalık mypy, Ruff ve `compileall` geçti.
- `28A-v1` taraması 481 dosyada sıfır secret bulgusu verdi.

### Görsel İyileştirme Turları

1. Masaüstü ve mobil durum etiketlerinin DOM'da yinelenmesi kaldırıldı; kaynak
   ikonları ortak 40 piksel yuvada aynı dikey eksene alındı.
2. Yetkisiz görünümden filtre ve yenileme kontrolleri kaldırıldı; yalnız
   veri ifşa etmeyen erişim mesajı bırakıldı.

### Sınırlar

- Oluşturma, düzenleme, bağlantı testi, aktivasyon ve arşivleme eylemleri yoktur.
- Yerel uygulama yalnız sentetik kaynaklar kullanır. Gerçek IdP, yüksek
  erişilebilir session store ve üretim repository bağlantısı uygulanmamıştır.
- Bu kayıt banka onayı veya üretim uygunluğu değildir.

## Sonraki Dilim

## 35B — Salt Okunur Kurallar Ekranı

Durum: **TechnicallyVerified**

### Kullanıcı Değeri

Yetkili kullanıcı, erişebildiği datasetlerdeki kuralları son sürüm, durum,
kalite boyutu ve kritiklik bilgileriyle tarayıp filtreleyebilir.

### Kapsam

- Güvenilir aktör dataset kapsamına göre filtrelenen `GET /api/v1/rules`.
- Kural tanımı/SQL, eşik, ağırlık, alan ve kullanıcı kimliği içermeyen DTO.
- `/rules` rotasında metin, durum, kalite boyutu ve kritiklik filtreleri.
- Ürün bağımsız, sabit eksenli Lucide kural türü ikonları ve iki tema.
- Loading, empty, technical error, unauthorized ve long-content durumları.

### Gereksinim Bağlantıları

- `FR-023–FR-035` salt okunur envanter alt kapsamı
- `UC-005`, `UC-006`
- `FE-DS-015`
- `NFR-USA-001–NFR-USA-006`

### Doğrulama

- Backend: dört yeni API testi ve bir repository testi; dataset scope filtresi,
  sahte header etkisizliği, son sürüm seçimi, veri-minimum yanıt, boş kapsam ve
  güvenli teknik hata.
- Frontend: 33 Vitest ve 39 Playwright testi; beş viewport, açık/koyu tema,
  yatay taşma, ikon ekseni, birleşik filtre, klavye odağı ve yetkisiz veri ifşa
  etmeme.
- TypeScript, Vite/Storybook build, production npm audit, 1041 pytest, 162
  dosyalık mypy, Ruff ve `compileall` geçti.
- `28A-v1` taraması 491 dosyada sıfır secret bulgusu verdi.

### Görsel İyileştirme Turları

1. Altı kolonlu masaüstü satırı `lg` eşiğine taşındı; 1024 pikselde durum ve
   kritiklik odaklı dört kolonlu düzenle metin çakışması giderildi.
2. Teknik kural türü enumları kullanıcıya dönük Türkçe etiketlere çevrildi;
   uzun `REFERENTIAL_INTEGRITY` metninin kaba satır kırılması kaldırıldı.

### Sınırlar

- Kural oluşturma, düzenleme, test, onay ve aktivasyon eylemleri yoktur.
- Yerel uygulama yalnız sentetik kurallar kullanır. Gerçek IdP, yüksek
  erişilebilir session store ve üretim repository bağlantısı uygulanmamıştır.
- Bu kayıt banka onayı veya üretim uygunluğu değildir.

## Sonraki Dilim

35C, aynı güvenlik ve durum sözleşmeleriyle salt okunur Çalıştırmalar ekranıdır.
