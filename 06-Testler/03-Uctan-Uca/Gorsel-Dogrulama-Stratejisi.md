---
type: test-strategy
status: accepted
project: Veri Kalitesi İzleme ve Skorlama Sistemi
last_updated: 2026-07-22
tags:
  - testing
  - frontend
  - visual-regression
---

# Görsel Doğrulama Stratejisi

## Amaç ve Mevcut Durum

Bu belge Storybook component doğrulaması ile Playwright ekran/akış doğrulamasının
asgari sözleşmesidir. Frontend runtime, Storybook ve Playwright İterasyon 30B ile
kurulmuş; açık/koyu tema viewport matrisi İterasyon 30C ile uygulanmıştır. Onaylı
pixel-diff eşiği ve kurumsal CI render ortamı henüz kesinleşmemiştir.

Tasarım doğruluk kaynağı:
[Görsel Tasarım Sistemi](../../04-Frontend/Gorsel-Tasarim-Sistemi.md). İlk ekran sözleşmesi:
[Dashboard Ekran Sözleşmesi](../../04-Frontend/03-Dashboard/Dashboard-Ekran-Sozlesmesi.md).
İlk referans: [reference-dashboard.png](../../04-Frontend/references/reference-dashboard.png).

## Doğrulama Katmanları

| Katman | Amaç | Asgari kapsam |
| --- | --- | --- |
| Storybook | İzole component durumları | Normal, hover, focus, disabled, loading, empty, error, uzun içerik |
| Playwright component/page | Gerçek layout ve etkileşim | Klavye, filtre, drawer/modal, grafik/tablo geçişi |
| Görsel regression | İstenmeyen görünüm sapması | Sabit veri, font, saat ve viewport ile screenshot |
| Erişilebilirlik | Renk dışı anlam ve klavye | Focus, accessible name, contrast, table/chart alternatifi |
| Manuel referans incelemesi | Tasarım niyeti | Spacing, tipografi, renk, yoğunluk, hizalama |

## Zorunlu Süreç

1. İlgili ekran sözleşmesini ve referans görseli incele.
2. Mevcut ekranı sabit sentetik veriyle çalıştır.
3. Playwright ile ilk ekran görüntülerini al.
4. Referans ve uygulama görüntüsünü yan yana karşılaştır.
5. Spacing, tipografi, renk, yoğunluk, hizalama ve responsive farklarını kaydet.
6. İlk iyileştirme turunu uygula ve yeniden görüntü al.
7. Kalan farkları yeniden değerlendir.
8. İkinci iyileştirme turunu uygula ve final görüntülerini al.
9. Sonuçları görev/iterasyon raporuna yaz.

İki tur, iki rastgele CSS değişikliği anlamına gelmez. Her turda fark, uygulanan
değişiklik ve sonuç açıkça kaydedilmelidir.

## Viewport Matrisi

| Viewport | Zorunluluk | Kontrol |
| --- | --- | --- |
| `1440×900` | Zorunlu ana referans | Tam dashboard yoğunluğu ve hiyerarşi |
| `1280×800` | Zorunlu | Grid sıkışması ve tablo davranışı |
| `1024×768` | Zorunlu | Navigasyon daralması ve tek kolon geçişi |
| `1366×768` | SRS kabul görünümü | `NFR-USA-004`, yatay sayfa taşması yok |
| `1920×1080` | SRS kabul görünümü | Kontrolsüz genişleme ve metin ölçüsü yok |

Mobil viewport MVP kapsamına otomatik eklenmez.

## Deterministik Test Koşulları

- Gerçek banka, müşteri, LDAP veya üretim verisi kullanılmaz.
- Saat, locale, timezone, animasyon, rastgele ID ve veri sırası sabitlenir.
- Font yüklenmesi beklenir; skeleton veya geç animasyon final baseline'a girmez.
- Network çağrıları kararlı sentetik fixture veya sözleşmeli test double kullanır.
- Secret, stack trace, ham SQL, kişisel veri ve ham hatalı kayıt screenshot'a girmez.
- `prefers-reduced-motion` senaryosu ayrıca doğrulanır.

## Storybook Story Matrisi

Ortak componentler için en az:

- KPI: calculated, critical, technical error, no-data ve uzun etiket.
- Status badge: critical, technical, warning, success, info, unknown.
- Alarm: kritik kalite, teknik hata, tekrar eden olay ve yetkisiz eylem.
- Chart wrapper: loading, empty, partial, render error ve table alternative.
- Data table: loading, empty, sayfalı, sıralı, uzun metin ve action menu.
- Form: default, focus, validation, disabled ve server error.
- Drawer/modal: keyboard focus trap, close ve uzun içerik.

## Görsel Karşılaştırma Kriterleri

| Kriter | Beklenti |
| --- | --- |
| Spacing | Token grid'inden sapma ve düzensiz ritim yok |
| Tipografi | Doğru ölçek/hiyerarşi; taşma ve negatif spacing yok |
| Renk | Ham component rengi yok; semantik ayrım doğru |
| Yoğunluk | Gereksiz boşluk veya kart çoğalması yok |
| Hizalama | Grid, axis, KPI ve tablo kolonları tutarlı |
| Stable layout | Loading/etiket/hover nedeniyle ölçü kayması yok |
| Responsive | Overlap ve yatay sayfa taşması yok |
| Veri tutarlılığı | Grafik ve tablo aynı fixture/toplamları gösterir |

Pixel fark eşiği toolchain, font ve CI render ortamı sabitlenmeden tahmin edilmez.
İlk baseline incelemesi sonrası ekip kararıyla kaydedilir. Eşik aşımı otomatik kabul
veya ret yerine fark artifact'ı ve insan incelemesi üretmelidir; baseline güncellemesi
gerekçe ve review olmadan yapılmaz.

## Erişilebilirlik Kontrolleri

- Durumlar ikon, etiket ve accessible name ile renk dışı anlaşılır olmalıdır.
- Marka sarısı üzerindeki metin/ikon kontrastı ölçülür.
- Teknik hata ve kritik ihlal ekran okuyucu metninde farklı adlandırılır.
- Tüm interactive öğeler klavyeyle erişilebilir, focus görünür ve sıra anlamlıdır.
- Grafik aynı verinin tablo veya metinsel özetine bağlanır.
- Tooltip hover ve focus ile açılır; tek bilgi kaynağı değildir.

## Dosya ve Artifact Düzeni

Toolchain kurulduğunda isimlendirme şu örüntüyü izler:

`<ekran>--<durum>--<viewport>.png`

Örnek: `dashboard--technical-error--1440x900.png`.

Referans görseller repository'deki frontend `references/` alanında kalır. Çalışma
çıktıları ve diff artifact'ları mevcut `.gitignore` gereği `artifacts/` altında
saklanır ve varsayılan olarak commit edilmez. Onaylanmış baseline dosyalarının yeri
frontend toolchain kararıyla ayrıca kesinleştirilir.

## Frontend Definition of Done

Bir frontend görevi aşağıdakiler olmadan tamamlanmış sayılmaz:

- İlgili FR/UC/NFR ve ekran sözleşmesi ilişkilendirilmiştir.
- Yeni component öncesi design-system componentleri kontrol edilmiştir.
- Token dışı renk/spacing/shadow/radius kullanılmamıştır.
- Storybook story matrisi görev kapsamına göre eklenmiş ve geçmiştir.
- Playwright işlevsel ve zorunlu viewport screenshot kontrolleri geçmiştir.
- En az iki belgeli görsel iyileştirme turu yapılmıştır.
- Klavye, focus, erişilebilir ad ve renk dışı durum ayrımı doğrulanmıştır.
- Teknik hata/kalite ihlali, `0`/no-data ve partial durumları ayrıştırılmıştır.
- Screenshot ve hata çıktılarında hassas veri veya secret olmadığı kontrol edilmiştir.
- Görsel sonuçlar görev raporuna eklenmiştir.
