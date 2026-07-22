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

35B, aynı güvenlik ve durum sözleşmeleriyle salt okunur Kurallar ekranıdır.
