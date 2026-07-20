---
type: frontend-design-system
status: design-baseline
project: Veri Kalitesi İzleme ve Skorlama Sistemi
last_updated: 2026-07-20
tags:
  - frontend
  - design-system
  - accessibility
---

# Görsel Tasarım Sistemi

## Amaç ve Kapsam

Bu belge tüm frontend ekranlarının görsel doğruluk kaynağıdır. Amaç, banka içi
operasyon uygulamasına uygun; modern, premium, yoğun fakat okunabilir bir çalışma
yüzeyi oluşturmaktır. Görsel dil pazarlama sitesi gibi değil, tekrar eden analiz ve
işlem akışları için sessiz, öngörülebilir ve erişilebilir olmalıdır.

Bu belge tasarım kararlarını tanımlar; component kütüphanesi, Storybook ve tema
uygulamasının tamamlandığı anlamına gelmez. Dashboard'a özgü yerleşim için
[[04-Frontend/03-Dashboard/Dashboard-Ekran-Sozlesmesi|Dashboard Ekran Sözleşmesi]],
test süreci için
[[06-Testler/03-Uctan-Uca/Gorsel-Dogrulama-Stratejisi|Görsel Doğrulama Stratejisi]]
esas alınır.

İlk görsel yoğunluk ve hiyerarşi referansı:
[reference-dashboard.png](references/reference-dashboard.png). Görsel yalnız
sentetik verilerden oluşur ve çalışan frontend/API kanıtı değildir.

## Görsel Yön

- Koyu lacivert navigasyon, açık gri ana çalışma alanı ve beyaz içerik yüzeyleri.
- Düşük gölge, ince sınır ve sıkı grid ile kurumsal yoğunluk.
- Büyük hero, dekoratif illüstrasyon, glassmorphism, neon ve gradient kullanılmaz.
- Her bölüm ayrı karta kapatılmaz; sayfa yapısı tam genişlikte, kartlar yalnız gerçek
  veri birimleri ve tekrar eden öğeler için kullanılır.
- Hiyerarşi renk kalabalığıyla değil; tipografi, boşluk, hizalama ve yüzey ayrımıyla
  kurulur.

## Token Zorunluluğu

Component dosyalarında ham HEX, RGB, gölge, radius veya spacing değeri kullanılmaz.
Tüm değerler semantik tasarım token'ları üzerinden tüketilir. Aşağıdaki değerler
token kaynağının dokümantasyon baseline'ıdır; component API'si değildir.

### Ana Renk Token'ları

| Token | Başlangıç değeri | Kullanım |
| --- | --- | --- |
| `color.brand.primary` | `#FDB813` | Ana aksiyon, aktif navigasyon/sekme, seçili filtre, focus ve küçük marka vurgusu |
| `color.brand.primaryHover` | `#E5A500` | Marka aksiyonunun hover durumu |
| `color.brand.onPrimary` | `#172033` | Marka sarısı üzerindeki metin ve ikon |
| `color.nav.background` | `#0B1F3A` | Sol navigasyon |
| `color.nav.hover` | `#142D4F` | Navigasyon hover yüzeyi |
| `color.canvas` | `#F3F5F7` | Ana çalışma alanı |
| `color.surface` | `#FFFFFF` | İçerik yüzeyi |
| `color.text.primary` | `#172033` | Ana metin |
| `color.text.muted` | `#5B6574` | İkincil metin |
| `color.border` | `#D8DEE7` | İnce ayırıcı ve yüzey sınırı |

Marka sarısı büyük sayfa arka planında, tüm kartlarda, uzun metinde, bütün grafik
serilerinde veya semantik durum göstergesi olarak kullanılmaz. Özellikle uyarı,
kritik ihlal ve teknik hata anlamına gelmez.

### Semantik Durum Token'ları

| Anlam | Token | Başlangıç değeri | Zorunlu yazılı etiket | İkon örüntüsü |
| --- | --- | --- | --- | --- |
| Kritik veri kalitesi ihlali | `color.status.critical` | `#C62828` | Kritik İhlal | Dolu uyarı üçgeni |
| Teknik hata | `color.status.technical` | `#7B1FA2` | Teknik Hata | Araç/terminal hata ikonu |
| Operasyonel uyarı | `color.status.warning` | `#C75B00` | Uyarı | Çerçeveli uyarı ikonu |
| Başarılı durum | `color.status.success` | `#2E7D32` | Başarılı | Onay ikonu |
| Bilgi durumu | `color.status.info` | `#1565C0` | Bilgi | Bilgi ikonu |
| Bilinmeyen/veri yok | `color.status.unknown` | `#667085` | Veri Yok / Bilinmiyor | Çizgi veya soru ikonu |

Renk tek bilgi taşıyıcısı değildir. Her durum ikon, metin, badge ve bağlama göre
tooltip/açıklama ile sunulur; erişilebilir ad durum anlamını içerir. Teknik hata
kırmızı, marka sarısı uyarı rengi olarak gösterilemez. Hesaplanamayan veya veri
bulunmayan skor `0` değil `—` ile gösterilir ve yazılı durumla açıklanır.

## Tema

### Varsayılan Açık Tema

İlk referans ve MVP çalışma yüzeyi koyu navigasyon + açık içerik düzenidir. Ana
çalışma alanı açık gri, veri yüzeyleri beyazdır. Koyu navigasyon uygulama kabuğudur;
sayfanın tamamını tek renk koyu yüzeye dönüştürmez.

### Koyu Tema

Koyu tema aynı semantik token sözleşmesini kullanır. Başlangıç yüzey rolleri:

| Token | Koyu tema değeri |
| --- | --- |
| `color.canvas` | `#111418` |
| `color.surface` | `#1A1F26` |
| `color.surfaceRaised` | `#222832` |
| `color.text.primary` | `#F5F7FA` |
| `color.text.muted` | `#B5BDC9` |
| `color.border` | `#353D49` |

Semantik renkler tema bazında kontrast testinden geçmeden aynen kopyalanmaz. Koyu
tema uygulaması ayrı backlog maddesidir; bu belge uygulanmış tema iddiası oluşturmaz.

## Tipografi

- Varsayılan stack kurum standardı kesinleşene kadar sistem sans-serif ailesidir.
- Tip ölçeği: `12`, `14`, `16`, `20`, `24` ve yalnız gerçek sayfa başlıklarında `28`.
- Dashboard ve araç yüzeylerinde sıkı fakat okunabilir satır yüksekliği kullanılır.
- Harf aralığı `0` olmalıdır; negatif letter-spacing ve viewport'a bağlı font
  ölçekleme kullanılmaz.
- Sayısal KPI değerleri tabular numeral desteğiyle hizalanır.
- Başlık seviyesi yalnız görsel boyuta göre değil, belge hiyerarşisine göre seçilir.

## Spacing, Grid ve Boyutlar

- Temel spacing birimi `4px`; standart adımlar `4`, `8`, `12`, `16`, `24`, `32`.
- Masaüstü içerik grid'i 12 kolon; ana gutter `24px`, 1024 görünümünde `16px`.
- Navigasyon, toolbar, KPI, tablo başlığı ve grafik alanlarında stable dimensions
  tanımlanır; loading, hover veya uzun etiket layout kaydırmamalıdır.
- KPI ve grafik grid'leri `minmax()` benzeri responsive track sözleşmesiyle kurulur.
- Metin container dışına taşmaz; uzun etiket sarılır, gerekli yerde ellipsis ve
  erişilebilir tam metin tooltip'i birlikte kullanılır.

## Radius, Sınır ve Gölge

| Token | Değer | Kullanım |
| --- | --- | --- |
| `radius.control` | `4px` | Input, button, badge |
| `radius.surface` | `6px` | Kart, tablo kabuğu, drawer |
| `radius.modal` | `8px` | Modal |
| `shadow.surface` | Çok hafif | Yalnız gerektiğinde yüzey ayrımı |
| `shadow.overlay` | Orta, yaygın olmayan | Modal ve drawer |

Kart radius'u `8px` üzerine çıkmaz. Ağır gölge, sürekli floating-card görünümü ve
kart içinde kart kullanılmaz. Mümkünse gölge yerine sınır ve yüzey tonu tercih edilir.

## Uygulama Kabuğu ve Navigasyon

- Sol navigasyon koyu lacivert, en fazla iki seviyeli ve masaüstünde sabittir.
- Aktif öğe marka sarısı vurgu, ikon ve metin ağırlığıyla belirtilir.
- Üst bar; kapsam, tarih, bildirim ve kullanıcı menüsünü taşır, ikinci bir hero alanı
  oluşturmaz.
- 1024 genişlikte navigasyon ikon rayına daralabilir; ikonların erişilebilir adı ve
  tooltip'i zorunludur.
- Navigasyon görünürlüğü yetkinin yerine geçmez; backend kapsam dışı veriyi
  döndürmemelidir.

## Component Görünümü

### Buton ve Formlar

- Ana aksiyon sarı yüzey + koyu metinle sınırlıdır; aynı panelde birincil aksiyon
  sayısı mümkün olduğunca birdir.
- Araç komutlarında uygun ikon varsa ikon düğmesi ve tooltip kullanılır.
- Label, yardım, zorunluluk, doğrulama ve hata metni layout sıçraması yaratmayacak
  ayrılmış alanda gösterilir.
- Focus göstergesi görünür ve marka token'ıyla en az AA uyumlu kontrastta olmalıdır.
- Disabled durum tek başına düşük opacity ile anlatılmaz; erişilebilir durum korunur.

### KPI Kartları

- KPI kartı tek ana değer, kısa etiket, dönem/kapsam ve gerektiğinde trend içerir.
- Kritik ve teknik KPI'lar aynı kırmızı dilde birleştirilemez.
- Değer yoksa `—`, durum etiketi ve kısa açıklama gösterilir.
- KPI kartı başka bir kartın içine yerleştirilmez.

### Tablolar

- Sütunlar taranabilir, başlıklar kısa, sayısal değerler sağa hizalıdır.
- Sticky header, sayfalama, sıralama, görünür filtre özeti ve filtre sıfırlama sağlanır.
- Büyük sonuçlar sunucuda sayfalama veya sanal liste gerektirir.
- Satır eylemleri tek bir action menu altında gruplanır; kritik eylemler açık ad taşır.
- Grafik ve tablo aynı view-model ve ortak formatter'lardan beslenir.

### Grafikler

- Zaman serisi: line chart.
- Veri alanı karşılaştırması: horizontal bar chart.
- Veri alanı × kalite boyutu: heatmap.
- Az kategorili dağılım: sınırlı donut; çok kategori: bar chart.
- Kritik eşik kesikli referans çizgisi ve yazılı legend ile gösterilir.
- Tooltip tarih, seri, değer, birim ve durum bilgisini tutarlı sırada sunar.
- Axis ve legend gizlenerek anlam kaybı oluşturulmaz; loading ve empty state chart
  alanının stable ölçüsünü korur.
- Gradient, 3D grafik ve dekoratif animasyon kullanılmaz.
- Renk körlüğüne uygun palette ek olarak desen, işaretçi, etiket veya çizgi stili
  ayrımı kullanılır.
- Her grafik aynı verinin metinsel özeti veya tablo görünümüne erişim sağlar.

### Alarm Kartları

- Alarm; önem ikonu, yazılı durum, kısa başlık, kapsam, zaman ve bir sonraki eylemi
  içerir.
- Ham hatalı kayıt, SQL, secret, müşteri veya kişisel veri göstermez.
- Kritik kalite ihlali kırmızı, teknik altyapı hatası mor olarak ayrılır.
- Alarm akışı yoğun olabilir; ancak kart içinde yeni kart katmanı oluşturmaz.

### Drawer ve Modal

- Drawer bağlam kaybetmeden detay/drill-down için; modal kısa ve bloklayıcı karar için
  kullanılır.
- Uzun form modal içine alınmaz.
- Focus trap, Escape davranışı, başlık/açıklama ilişkisi ve kapatma ikonu zorunludur.
- Kritik işlemde sonuç, kapsam ve audit etkisi açıkça belirtilir.

## Durum Yüzeyleri

| Durum | Görsel davranış |
| --- | --- |
| Loading | Stable ölçülü skeleton; sonsuz spinner tek başına kullanılmaz |
| Empty | Neden, aktif filtre özeti ve izinli bir sonraki eylem |
| No data | `—` ve “Veri Yok”; sıfır skor üretilmez |
| Technical error | Mor ikon/badge, kullanıcı eylemi ve correlation ID; stack/secret yok |
| Quality failure | Kırmızı durum dili, etkilenen kapsam ve drill-down |
| Partial | Ayrı yazılı etiket; başarılı veya teknik hata gibi gösterilmez |

## Mikro Etkileşimler

- Hover/focus/geçişler kısa ve işlevsel olmalıdır; önerilen süre `120–200ms`.
- Grafik giriş animasyonu kritik değeri geciktiremez veya değiştiremez.
- `prefers-reduced-motion` desteklenir.
- Bildirim ve durum güncellemesi ekran okuyucu live region ile duyurulur; gereksiz
  animasyon ve dikkat dağıtan pulse kullanılmaz.

## Responsive Davranış

| Genişlik | Beklenen davranış |
| --- | --- |
| `1440×900` | Ana referans; dört KPI, iki kolon analiz alanı ve tablo görünür |
| `1280×800` | Grid sıkılaşır; alarm paneli daralır, içerik taşmaz |
| `1024×768` | Navigasyon ikon rayı; KPI iki kolon; grafikler tek kolon akabilir |
| `1366×768` | `NFR-USA-004` zorunlu kabul görünümü; yatay sayfa taşması yok |
| `1920×1080` | İçerik kontrolsüz uzamaz; grid ve tablo okunabilir maksimum genişlikte kalır |

Mobil yönetim deneyimi MVP için tanımlı değildir. Responsive masaüstü davranışı
mobil kapsamını kendiliğinden genişletmez.

## Erişilebilirlik

- Hedef WCAG 2.2 AA'dır; nihai kurum onayı ayrıca gerekir.
- Tüm ana akışlar klavyeyle tamamlanır; focus sırası görsel sırayla uyumludur.
- Metin ve anlamlı ikon kontrastı tema başına ölçülür.
- Renk durumun tek taşıyıcısı değildir; ikon, etiket ve erişilebilir ad zorunludur.
- Grafiklerin tablo/metinsel karşılığı, keyboard erişimi ve ekran okuyucu özeti vardır.
- Tooltip'e yalnız hover ile değil focus ile de erişilir.
- Yoğun tablolar anlamlı header ilişkileri, caption ve güncel sıralama durumunu taşır.

## Uygulama Öncesi Kontrol

1. Yeni component ihtiyacı için mevcut design-system envanterini kontrol et.
2. Token, formatter ve status mapper tekrarını önle.
3. Storybook'ta normal, loading, empty, error, yetkisiz ve uzun içerik story'lerini ekle.
4. Playwright ile zorunlu viewport ekran görüntülerini üret.
5. Referansla en az iki görsel iyileştirme turu yap.
6. Erişilebilirlik ve teknik hata/kalite ihlali ayrımını test et.
