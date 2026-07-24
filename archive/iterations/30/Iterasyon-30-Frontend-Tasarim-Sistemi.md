---
iteration: 30
status: in-progress
completed_at: null
---

# İterasyon 30 — Frontend Tasarım Sistemi ve Kurumsal Dashboard

Bu iterasyon frontend uygulama programıdır. 30A dokümantasyon tabanını, 30B ise
kullanıcının açık önceliklendirmesiyle yalnız sentetik ve bağlantısız çalışma
artımını üretir. Üretim API'si, gerçek kimlik/oturum ve banka verisi kullanan
yüzeyler `Bankacilik-Gecis-Durumu.md` geçiş kapısı ile 21B güvenli HTTP/API
sınırına bağlı kalır.

## 30A — Görsel Tasarım Dokümantasyon Tabanı

Durum: **Dokümantasyon tamamlandı; uygulama başlamadı**

### Kapsam

- Token tabanlı kurumsal görsel dil ve semantik durum ayrımı.
- Dashboard ekran sözleşmesi ve `reference-dashboard.png` referansı.
- Storybook/Playwright görsel doğrulama stratejisi ve frontend Definition of Done.
- Codex frontend görev şablonu ve AGENTS hiyerarşisi.
- Uygulama backlogu, ADR ve proje hafızası bağlantıları.

### Gereksinim Bağlantıları

- `FR-054`–`FR-058`
- `UC-010`
- `NFR-USA-001`–`NFR-USA-006`
- `NFR-SEC-001`, `NFR-SEC-003`, `NFR-SEC-007`, `NFR-SEC-008`
- `AC-010`, `AC-011`

### Doğrulama

- Markdown ve bağıl bağlantı bütünlüğü kontrol edilir.
- Referans PNG dosyası `1440×900`, 140554 byte ve
  `2fe06c08b8749ddcd40f796f1c7cecbbaea781b22defff11715bdb0862b93396`
  SHA-256 özetiyle doğrulanır.
- Kaynak kodu, frontend componenti, dependency ve build yapılandırması değişmez.
- `556` mevcut birim test baseline'ı korunur; doküman değişikliği yeni ürün
  davranışı veya banka onayı sayılmaz.

## 30B — Sentetik Dashboard Çalışma İskeleti

Durum: **TechnicallyVerified**

### Kapsam ve Değer

- React, TypeScript, Vite, MUI ve ECharts runtime'ı ile Storybook ve Playwright
  doğrulama araçları kuruldu.
- Semantik token kaynağı, açık tema, sabit uygulama kabuğu, KPI kartı, status
  badge, alarm akışı ve resmî skor trendi uygulandı.
- Grafik ve erişilebilir tablo aynı sentetik view-model'i kullanır; teknik hata ve
  provizyonel sonuç resmî trend çizgisine katılmaz.
- Ekran üretim API'sine, kullanıcı oturumuna veya banka verisine bağlı olmadığını
  açıkça gösterir. Query parametresi yalnız Storybook/E2E durum yüzeylerini
  deterministik olarak üretir ve yetki kanıtı değildir.

### Gereksinim Bağlantıları

- `FR-054`, `FR-055`, `FR-058`
- `UC-010`
- `NFR-USA-001`, `NFR-USA-003`–`NFR-USA-006`

### Doğrulama

- Vitest: 4 test; teknik hata/kalite ayrımı, erişilebilir durum adı, resmî trend
  dışlama ve teknik hatada null skor.
- Storybook build: normal, loading, empty, teknik hata, yetkisiz ve uzun içerik
  dashboard durumları; altı semantik status badge durumu.
- Playwright: 7 test; beş zorunlu viewport, yatay taşma, grafik/tablo ortak veri,
  provizyonel dışlama, klavye odağı ve yetkisiz yüzeyde veri ifşa etmeme.
- Birinci görsel turda `1200px` üzeri dört KPI ve trend/alarm iki kolon düzeni ile
  kesilen eşik etiketi düzeltildi.
- İkinci görsel turda alarm badge esnemesi, teknik hata mor semantiği ve MUI
  `ButtonBase` görünür focus halkası düzeltildi.

### Güvenlik Sınırı

- Fixture'lar sentetiktir; secret, ham kayıt, SQL, stack trace, müşteri veya banka
  verisi içermez.
- UI rol/scope üretmez ve üretim yetkilendirmesi iddiası taşımaz.
- Gerçek API, IdP/SSO-MFA, session assertion, dışa aktarma ve drill-down kapsam
  dışıdır.

## Uygulama Dilimleri

| Dilim | Değer | Ön koşul |
| --- | --- | --- |
| 30B | Sentetik çalışma iskeleti, açık tema, KPI/status/alarm/trend ve test altyapısı | `TechnicallyVerified` |
| 30C | Referansla uyumlu navigasyon grupları, gerçek/hizalı ikonlar ve açık-koyu tema | `TechnicallyVerified` |
| 30D | Sentetik veri alanı karşılaştırması, kalite boyutu matrisi ve 21C operasyonel KPI bağlantısı | `TechnicallyVerified` |
| 30E | Ortak sayfalı data table standardı | 30B, API sayfalama sözleşmesi |
| 30F | Üretim bağlantılı kurumsal dashboard | 20E `TechnicallyVerified`; 21B/21C güvenli API ve geçiş kapısı |
| 30G | Onaylı görsel baseline ve diff eşiği | Banka marka/onay kararı |
| 30H | Grafik erişilebilirliği genişletmesi | 30D–30G |

Her dilim tek çalışabilir artım olarak ele alınır; yalnız durum sütununda
`TechnicallyVerified` yazan dilimler tamamlanmış teknik artımdır.

## 30C — Uygulama Kabuğu Görsel Uyumu ve Tema

Durum: **TechnicallyVerified**

### Kapsam ve Değer

- Navigasyon referansla uyumlu `ANALİZ` ve `OPERASYON` gruplarına ayrıldı.
- Yedi menü öğesindeki geçici karakterler eşit boyutlu kutularda hizalanan
  `lucide-react` ikonlarıyla değiştirildi.
- Açık ve koyu semantik token kümeleri ile kullanıcı tema seçimi uygulandı.
  İlk açılış açık temadır; yalnız `light` veya `dark` değeri yerel tarayıcı
  depolamasında tutulur. Depolama erişimi başarısız olduğunda ekran açık tema
  ile çalışmaya devam eder.
- Grafik ekseni, metni, ızgarası ve durum renkleri etkin temadan çözülür.
- Storybook tema aracı ve koyu tema dashboard durumu eklendi.

### Gereksinim Bağlantıları

- `FR-054`
- `UC-010`
- `NFR-USA-001`, `NFR-USA-004`–`NFR-USA-006`

### Doğrulama

- Vitest: 13 test; navigasyon grupları, yedi sabit ikon kutusu, açık tema
  varsayılanı, tema geçişi, tercih kalıcılığı ve depolama hata yolları dahil.
- Playwright: 14 test; beş zorunlu viewport'un açık ve koyu tema görüntüleri,
  ikon merkez hizası, tema kalıcılığı, grafik/tablo eşliği, yetkisiz yüzey ve
  klavye odağı dahil.
- Birinci görsel turda grup/hizalama doğrulanırken koyu temada sayfa başlığının
  gövde rengini devralmadığı görüldü. İkinci turda gövde ve uygulama kökü
  semantik metin rengine bağlandı; tüm viewport ve temalar yeniden geçti.
- Frontend type-check, birim testleri, üretim ve Storybook build'leri ile
  `npm audit`; ayrıca tam Python test, mypy, Ruff, `compileall`, diff ve secret
  taraması geçti.

### Güvenlik ve Kapsam Sınırı

- Tema tercihi kimlik, rol, scope, token veya kişisel veri içermez.
- Menü öğeleri bu dilimde route veya yetki kararı üretmez. Veri Kaynakları,
  Kurallar, Çalıştırmalar, Sorunlar, Raporlar ve Denetim sayfaları 35A–35F
  kapsamında kalır.
- Üretim bağlantısı, banka marka onayı ve onaylı görsel diff eşiği uygulanmadı.

## 30D — Dashboard Referans İçerik Tamamlaması

Durum: **TechnicallyVerified**

### Kapsam ve Değer

- 21C `operational_indicators` zarfı frontend API doğrulamasına ve KPI
  view-model'ine bağlandı. Ölçüm yeterliliği, kritik kontrol kullanılabilirliği
  ve teknik hata özeti artık “sağlanmıyor” yer tutucusu yerine gerçek API
  durumlarını gösterir.
- Bilinmeyen operasyonel durum, negatif sayaç veya eksik gösterge zarfı güvenli
  `invalid-response` yoluna düşer. Teknik başarısızlık sıfır kalite skoruna,
  kritik kontrol veri yokluğu sıfır ihlale çevrilmez.
- Referanstaki veri alanı karşılaştırması ve kalite boyutu matrisi yalnız
  `synthetic-development` kökeninde sabit sentetik view-model ile eklendi.
  Üretim kökeninde bu alanlar uydurulmaz ve bölüm bazlı veri yok durumu gösterir.
- Karşılaştırma renk yanında sayısal değer ve erişilebilir progressbar adı;
  matris ise her hücrede sayı/durum ve ekran okuyucu tablosu taşır.

### Gereksinim Bağlantıları

- `FR-054`, `FR-056`, `FR-058`
- `UC-010`, `RULE-009`
- `AC/TS-030`, `AC/TS-043`, `AC/TS-045`
- `NFR-USA-003`–`NFR-USA-006`

### Doğrulama ve Görsel Turlar

- 19 Vitest ve 15 Playwright testi geçti. Beş zorunlu viewport açık/koyu temada
  taşmasız doğrulandı; 21C KPI'ları, beş karşılaştırma satırı, yedi boyutlu
  erişilebilir matris ve hesaplanmadı durumu test edildi.
- Birinci turda 1440 görünümündeki alt paneller referanstan farklı olarak alt
  alta kalıyor ve uzun yeterlilik badge'i kelime ortasından kırılıyordu; grid
  breakpoint'i ve güvenli wrap davranışı düzeltildi.
- İkinci turda matrisin son kolonu kart içi kaydırmaya düşüyordu; sabit kolon
  düzeni ve caption yoğunluğu uygulandı. Son incelemede 1280 koyu temadaki başlık
  kırılması ilk sütun genişliği ve tek satır başlık davranışıyla giderildi.
- Frontend type-check, üretim/Storybook build ve `npm audit --omit=dev`; tam Python pytest,
  mypy, Ruff ve `compileall` kontrolleri geçti. Üretilmiş build çıktıları
  temizlendikten sonra secret taraması 469 dosyada sıfır bulgu verdi. Vite 500
  kB chunk uyarısı sürer.

### Güvenlik ve Kapsam Sınırı

- Fixture ve görsel artifact'lar yalnız sentetik veri içerir; gerçek banka veya
  müşteri verisi, secret, SQL ve stack trace içermez.
- UI rol/scope üretmez. Kritik kontrol sonucu, kapsam, kullanım kararı ve alarm
  runtime'ı bulunmadığında başarılı değer uydurmaz.
- Yeni route, dependency, veritabanı migration'ı veya üretim altyapısı yoktur.

## Kapsam Dışı

- Gerçek banka verisiyle ekran veya görsel artifact.
- Üretim API'si, IdP/SSO-MFA veya oturum bağlantısı.
- Mobil yönetim deneyimi.
- Banka marka/uyum onayı.

## Sonraki İş

30D dashboard referans içerik tamamlaması ve 21C KPI bağlantısı tamamlandı.
Kullanıcı öncelikli zincirde 35A salt okunur Veri Kaynakları ekranı ve istemci
route kabuğu tamamlandı. 35B salt okunur Kurallar ekranı da teknik olarak
doğrulandı. 35C salt okunur Çalıştırmalar ekranı da teknik olarak doğrulandı;
35D salt okunur Sorunlar, 35E güvenli Rapor Önizleme ve 35F salt okunur Denetim
ekranı da teknik olarak doğrulandı; kullanıcı öncelikli alan ekranı zinciri
tamamlandı.
Üretim bağlantılı 30F gerçek IdP, yüksek
erişilebilir session store, PostgreSQL repository ve geçiş kapısını bekler.
