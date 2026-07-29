---
type: implementation-index
area: frontend
project: Veri Kalitesi İzleme ve Skorlama Sistemi
updated_at: 2026-07-27
---

# Frontend Ekran Haritası

## Onaylı Teknoloji Yığını

React + TypeScript + Vite, MUI, ECharts, Storybook ve Playwright kullanılır.
Seçim [ADR-017](../02-Mimari/Mimari-Kararlar.md#adr-017--frontend-teknoloji-yığını)
ile kesindir. Paket sürümleri `04-Frontend/app/package.json` ve lock dosyasından
okunur; bu indeksde kopyalanmaz.

## Çalıştırma

```bash
cd 04-Frontend/app
npm install
npm run dev
```

Doğrulama komutları: `npm test`, `npm run typecheck`, `npm run build`,
`npm run test:e2e`, `npm run build-storybook`.

## Uygulama Durumu

| Route/alan | Salt okunur ekran | Yazılabilir akış | Durum/not |
| --- | --- | --- | --- |
| Dashboard | Var | Yok | Özet ve trend ekranı mevcut; iş alanı/SLA analitiği ve mühendis için dağılım-lineage-teşhis görünümü ile üretim IdP/veri adaptörü açık. |
| Veri kaynakları | Var | Oluşturma, test, aktivasyon/pasifleştirme | Teknik UI/API mevcut; secret değeri UI/payload/log/audit/DB'de tutulmaz. |
| Kurallar | Var | Taslak, düzenleme, test, onay akışları | Teknik UI/API ve PostgreSQL repository mevcut. |
| Çalıştırmalar | Var | Manuel başlatma ve iptal | Teknik UI/API mevcut; backend runtime PostgreSQL cutover 36E ile teknik olarak doğrulanmıştır. |
| Sorunlar | Var | İnceleme, atama, çözüm, doğrulama ve kapatma | Kapatma UI/API akışı ve event-driven yeniden açma davranışı mevcuttur; `36B5` teknik olarak doğrulanmıştır. |
| Raporlar | Var | Rapor talebi ve indirme | 36G ile ReportsPage, API client/model, rapor geçmişi, talep ve güvenli indirme akışları uygulanmıştır; kurumsal DLP/watermark ürün entegrasyonu ayrıdır. |
| Denetim | Var | Değişiklik yok | Salt okunur, rol/scope kontrollü bütünlük görünümü. |
| Kanıtlı karar/olay inceleme | Hedef | Hedef | `FR-097–FR-111`; ikinci faz, üretim route'u değildir. |

Kullanıcı özellik listesinin ekran/runtime karşılaştırması
[Ürün Yetenek Durum Matrisi](../00-Proje-Hafizasi/Urun-Yetenek-Durum-Matrisi.md)
içinde tutulur.

## Uygulanmış Tasarım Kuralları

- Açık/koyu semantik token sistemi; marka rengi semantik durum rengi değildir.
- Renk, ikon ve yazılı etiket birlikte kullanılır.
- ECharts görünümü erişilebilir tabloyla aynı view-model'i kullanır.
- Loading, empty, teknik hata, yetkisiz ve uzun içerik durumları Storybook'ta
  ayrı gösterilir.
- Hassas taslak tarayıcı kalıcı depolamasına yazılmaz; mutasyonlarda BFF/CSRF,
  güvenilir aktör ve optimistic locking sözleşmeleri korunur.

## Kaynaklar

- [Görsel Tasarım Sistemi](Gorsel-Tasarim-Sistemi.md)
- [Dashboard Ekran Sözleşmesi](03-Dashboard/Dashboard-Ekran-Sozlesmesi.md)
- [Görsel Doğrulama Stratejisi](../06-Testler/03-Uctan-Uca/Gorsel-Dogrulama-Stratejisi.md)
- [Tarihsel İterasyon 35](../archive/iterations/35/Iterasyon-35-Frontend-Alan-Ekranlari.md)
- [İterasyon 36](../09-Iterasyonlar/Iterasyon-36-PostgreSQL-ve-Yazilabilir-Alan-Ekranlari.md)
- [Harici Arayüz Gereksinimleri](../01-SRS/08-Harici-Arayuzler.md)
- [Frontend Güvenliği](../01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.05-Guvenlik.md)
