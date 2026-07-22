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
| 30C | Sentetik veri alanı karşılaştırması ve kalite boyutu matrisi | 30B |
| 30D | Ortak sayfalı data table standardı | 30B, API sayfalama sözleşmesi |
| 30E | Üretim bağlantılı kurumsal dashboard | 21B güvenli API, geçiş kapısı |
| 30F | Onaylı görsel baseline ve diff eşiği | Banka marka/onay kararı |
| 30G | Koyu tema ve grafik erişilebilirliği | 30B–30F |

Her dilim tek çalışabilir artım olarak ele alınır; bu belge uygulama dilimlerini
tamamlanmış saymaz.

## Kapsam Dışı

- Gerçek banka verisiyle ekran veya görsel artifact.
- Üretim API'si, IdP/SSO-MFA veya oturum bağlantısı.
- Mobil yönetim deneyimi.
- Banka marka/uyum onayı.

## Sonraki İş

30B sentetik çalışma artımı tamamlandı. Aynı güvenlik sınırını koruyan sıradaki
hazır frontend artımı 30C sentetik veri alanı karşılaştırması ve kalite boyutu
matrisidir. Üretim bağlantılı 30E, 21B güvenli HTTP/API sınırı ve
`OPEN-BNK-020` banka onaylıdır; onaylı BFF/session/CSRF politikasının üretim
HTTP katmanında uygulanması ve geçiş kapısındaki diğer bağımlılıklar tamamlanana
kadar uygulanmaz.
