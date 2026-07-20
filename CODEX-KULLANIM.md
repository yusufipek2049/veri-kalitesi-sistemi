# Codex ile Modül Bazlı Çalışma

Kök `AGENTS.md`, görev alanına göre ilgili modül talimatını seçmesini Codex'e söyler. En düşük bağlam tüketimi için Codex'i doğrudan modül klasöründe başlatmak da mümkündür.

## Örnekler

```powershell
# Kimlik ve yetki modülü
codex --cd "03-Backend/01-Kimlik-ve-Yetki"

# Veri kaynağı modülü
codex --cd "03-Backend/02-Veri-Kaynaklari"

# Skorlama modülü
codex --cd "03-Backend/06-Skorlama"

# Dashboard frontend
codex --cd "04-Frontend/03-Dashboard"
```

Modül klasöründen başlatıldığında kökten o klasöre kadar olan `AGENTS.md` zinciri otomatik bağlama girer. Kökten başlatıldığında ise kök talimat, görevle eşleşen modülün `AGENTS.md` dosyasını seçici olarak okutmalıdır.

## İlk görev örneği

```text
AGENTS.md talimatlarını uygula. MVP içindeki ilk çalışabilir dikey dilimi seç.
Önce ilgili modül AGENTS.md dosyasını ve onun zorunlu bağlam listesini oku.
Henüz kod yazma; FR/UC kimlikleri, kabul kriterleri, veri varlıkları ve testleri
olan kısa bir iterasyon planı hazırla.
```

## Uygulama görevi örneği

```text
03-Backend/02-Veri-Kaynaklari/AGENTS.md kapsamına göre yalnız PostgreSQL
veri kaynağı oluşturma ve salt-okunur bağlantı testi dilimini uygula.
İlgili Must gereksinimlerini ve kabul kriterlerini doğrula. Diğer bağlayıcıları
bu iterasyona ekleme. Testleri çalıştır ve proje hafızasını güncelle.
```

## Frontend Görsel Görev Şablonu

Bu şablon ayrı bir prompt sistemi değildir; kök ve frontend `AGENTS.md` zincirini
uygulanabilir görev girdisine dönüştürür.

```text
AGENTS.md talimatlarını uygula.

Görev kapsamı:
- İlgili ekran/modül:
- Karşılanan FR/UC/NFR:
- Kullanıcı değeri:
- Kapsam dışı:

Okunacak belgeler:
- 04-Frontend/Gorsel-Tasarim-Sistemi.md
- İlgili ekran sözleşmesi ve modül AGENTS.md
- İlgili SRS kabul kriterleri
- 06-Testler/03-Uctan-Uca/Gorsel-Dogrulama-Stratejisi.md

Tasarım referansı:
- Görsel yolu:
- Korunacak bilgi hiyerarşisi:
- Bilinen responsive farklar:

Etkilenecek componentler:
- Mevcut design-system componentleri:
- Yeni component ihtiyacı ve gerekçesi:
- Ortak formatter/status mapper etkisi:

Test planı:
- Storybook durumları:
- İşlevsel/erişilebilirlik testleri:
- Teknik hata ile kalite ihlali ayrımı:
- Grafik/tablo veri tutarlılığı:

Görsel doğrulama:
- 1440×900, 1280×800, 1024×768 screenshot
- 1366×768 ve 1920×1080 SRS responsive kontrolü
- Referans karşılaştırması
- Birinci iyileştirme turu ve sonuç
- İkinci iyileştirme turu ve sonuç

Definition of Done:
- Ham renk/spacing/radius/shadow yok
- Storybook ve Playwright kontrolleri geçti
- Klavye, focus, ARIA ve renk dışı durum anlamı doğrulandı
- Hassas veri/secret görsel artifact'larda yok
- İlgili belge ve proje hafızası güncellendi

Yeni dependency ekleme ve görev dışı refactoring yapma. Yalnız bir küçük, çalışabilir
frontend artımı uygula; sonuçları iterasyon raporunda ver.
```


## Mevcut Vault İçin Bankacılık Geçiş Komutu

Codex'i vault kökünde açtıktan sonra:

```text
devam
```

Kök `AGENTS.md`, `Bankacilik-Gecis-Durumu.md` ve `Sonraki-Adimlar.md` gereği
geçiş kapısını kontrol edip güncel sıradaki hazır artımı seçmelidir. Mevcut baseline'da
bu aday `Sonraki-Adimlar.md` içinde İterasyon 28D olarak kayıtlıdır; ilerledikçe
hard-coded iterasyon numarası yerine proje hafızası esas alınır. Daha katı komut:

```text
00-Proje-Hafizasi/Sonraki-Adimlar.md içindeki önerilen sıradaki iterasyonu uygula.
Mevcut-Durum.md içindeki doğrulanmış test baseline'ını koru. İlgili gereksinim ve
kontrol kimliklerini testlere ve kanıt dosyasına bağla. Yalnız bir iterasyon yap;
sonraki iterasyona geçmeden rapor ver ve pushla.
```
