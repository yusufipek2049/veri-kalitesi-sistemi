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

## 35C — Salt Okunur Çalıştırmalar Ekranı

Durum: **TechnicallyVerified**

### Kullanıcı Değeri

Yetkili kullanıcı, erişebildiği kaynakları tamamen kapsayan çalıştırmaları
durum, tür, yük sınıfı, zaman ve güvenli teknik sonuç bilgileriyle tarayıp
filtreleyebilir.

### Kapsam

- Güvenilir aktör kaynak kapsamına göre filtrelenen `GET /api/v1/executions`.
- Kural/kaynak listeleri, kullanıcı kimlikleri ve hata ayrıntısı içermeyen DTO.
- `/executions` rotasında metin, durum, tür, tarih ve sabit kapsam filtreleri.
- Sekiz çalışma durumunu ayrı koruyan sabit eksenli Lucide ikonları ve iki tema.
- Loading, empty, technical error, unauthorized ve long-content durumları.

### Gereksinim Bağlantıları

- `FR-043`, `FR-044`
- `UC-008`
- `FE-DS-015`
- `NFR-USA-001–NFR-USA-006`

### Doğrulama

- Backend: dört yeni API testi ve bir repository testi; kaynak scope filtresi,
  sahte header etkisizliği, çok kaynaklı kayıtların tam kapsam zorunluluğu,
  eski kapsamsız kayıtların dışlanması, veri-minimum yanıt ve güvenli hata.
- Frontend: 40 Vitest ve 51 Playwright testi; beş viewport, açık/koyu tema,
  yatay taşma, ikon ekseni, birleşik filtre, klavye odağı ve yetkisiz veri ifşa
  etmeme.
- TypeScript, Vite/Storybook build, production npm audit, 1046 pytest, 164
  dosyalık mypy, Ruff ve `compileall` geçti.

### Görsel İyileştirme Turları

1. Yetkili kaynak kapsamı görünür ve devre dışı bir filtreyle belirtildi;
   filtreler 1024 pikselde iki kolonlu, geniş masaüstünde beş kolonlu kararlı
   düzene alındı.
2. Masaüstü listeye kolon başlıkları eklendi; çalışma ikonları ve içerik
   başlangıçları aynı dikey eksende hizalandı.

### Sınırlar

- Çalıştırma başlatma, yeniden deneme, iptal ve zamanlama eylemleri yoktur.
- Yerel uygulama yalnız sentetik çalışmalar kullanır. Gerçek IdP, yüksek
  erişilebilir session store ve üretim repository bağlantısı uygulanmamıştır.
- Bu kayıt banka onayı veya üretim uygunluğu değildir.

## Sonraki Dilim

## 35D — Salt Okunur Sorunlar Ekranı

Durum: **TechnicallyVerified**

### Kullanıcı Değeri

Yetkili kullanıcı, erişebildiği kaynak ve datasetlerdeki kalite ve teknik
sorunları yaşam döngüsü, öncelik, kapsam ve son hareket bilgileriyle tarayıp
filtreleyebilir.

### Kapsam

- Güvenilir aktör kaynak/dataset kapsamına göre filtrelenen `GET /api/v1/issues`.
- Aktör, çözüm, yorum, kanıt ve entegrasyon hata ayrıntısı içermeyen DTO.
- `/issues` rotasında metin, durum, öncelik, tarih ve sabit kapsam filtreleri.
- Sekiz yaşam döngüsü durumu, dört öncelik ve teknik/kalite olay ayrımı.
- Loading, empty, technical error, unauthorized ve long-content durumları.

### Gereksinim Bağlantıları

- `FR-064–FR-070`
- `UC-011`, `UC-013`, `UC-014`
- `FE-DS-015`
- `NFR-SEC-001`
- `NFR-USA-001–NFR-USA-006`

### Doğrulama

- Backend: dört API davranış testi ve bir repository testi; kaynak/dataset scope
  filtresi, sahte header etkisizliği, veri-minimum yanıt, boş kapsam ve güvenli
  teknik hata.
- Frontend: 46 Vitest ve 63 Playwright testi; beş viewport, açık/koyu tema,
  yatay taşma, ikon ekseni, filtre/temizleme, klavye odağı ve yetkisiz veri ifşa
  etmeme.
- TypeScript, Vite/Storybook build, production npm audit, 1051 pytest, 166
  dosyalık mypy, Ruff ve `compileall` geçti.

### Görsel İyileştirme Turları

1. 1024 piksel filtre ızgarası üç kolona alındı, kapsam etiketi kısaltıldı ve
   paneldeki gereksiz boşluk azaltıldı.
2. Masaüstü kolon başlıklarının gizlendiği genişliklerde durum ve öncelik alan
   adları rozetlerin üzerinde görünür hale getirildi.

### Sınırlar

- Atama, çözüm, doğrulama, kapatma ve ServiceNow eylemleri yoktur.
- Yerel uygulama yalnız sentetik sorunlar kullanır. Gerçek IdP, yüksek
  erişilebilir session store ve üretim repository bağlantısı uygulanmamıştır.
- Bu kayıt banka onayı veya üretim uygunluğu değildir.

## Sonraki Dilim

35E, güvenli önizleme sözleşmesiyle salt okunur Raporlar ekranıdır; dosya dışa
aktarma bu dilimin kapsamında değildir.
