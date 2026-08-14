---
type: implementation-index
area: frontend
project: Veri Kalitesi İzleme ve Skorlama Sistemi
updated_at: 2026-07-30
---

# Frontend Ekran Haritası

## Onaylı Teknoloji Yığını

React + TypeScript + Vite, MUI, ECharts, Storybook ve Playwright kullanılır.
Seçim [ADR-017](../../architecture/Mimari-Kararlar.md#adr-017--frontend-teknoloji-yığını)
ila kesindir. Paket sürümleri `frontend/package.json` ve lock dosyasından
okunur; bu indeksde kopyalanmaz.

## Çalıştırma

```bash
cd frontend
npm install
npm run dev
```

Doğrulama komutları: `npm test`, `npm run typecheck`, `npm run build`,
`npm run test:e2e`, `npm run build-storybook`.

## Uygulama Durumu

| Route/alan | Salt okunur ekran | Yazılabilir akış | Durum/not |
| --- | --- | --- | --- |
| Dashboard | Var | Yok | Ortak yetkili API'den yönetici/mühendis rol görünümü, fail-closed dönem karşılaştırma notu ve scope filtreli katkı bileşenleri gösterilir; iş alanı/SLA analitiği, lineage/kanıtlı teşhis ve üretim IdP/veri adaptörü açıktır. |
| Veri kaynakları | Var | Oluşturma, test, aktivasyon/pasifleştirme | Teknik UI/API mevcut; secret değeri UI/payload/log/audit/DB'de tutulmaz. |
| Kurallar | Var | Taslak, düzenleme, test, onay akışları | Ortak IR sürümü, no-code/özel SQL kaynağı ve doğrulanmış kapsam inceleme satırında gösterilir. |
| Çalıştırmalar | Var | Manuel başlatma, iptal ve ad-hoc Özel SQL | OFFICIAL/SHADOW modu yaşam döngüsü durumundan ayrı gösterilir; SHADOW açık etiketlidir. "Özel SQL" butonu ile doğrudan SQL sorgusu yazılarak çalıştırma başlatılabilir. |
| Sorunlar | Var | İnceleme, atama, çözüm, doğrulama ve kapatma | Kapatma UI/API akışı ve event-driven yeniden açma davranışı mevcuttur; `36B5` teknik olarak doğrulanmıştır. |
| Raporlar | Var | Rapor talebi ve indirme | 36G ile ReportsPage, API client/model, rapor geçmişi, talep ve güvenli indirme akışları uygulanmıştır; kurumsal DLP/watermark ürün entegrasyonu ayrıdır. |
| Denetim | Var | Değişiklik yok | Salt okunur, rol/scope kontrollü bütünlük görünümü. |
| Kanıtlı karar/olay inceleme | Hedef | Hedef | `FR-097–FR-111`; ikinci faz, üretim route'u değildir. |

Kullanıcı özellik listesinin ekran/runtime karşılaştırması
[Ürün Yetenek Durum Matrisi](../../memory/Urun-Yetenek-Durum-Matrisi.md)
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
- [Görsel Doğrulama Stratejisi](../../testing/Gorsel-Dogrulama-Stratejisi.md)
- [Tarihsel İterasyon 35](../../../archive/iterations/35/Iterasyon-35-Frontend-Alan-Ekranlari.md)
- [İterasyon 36](../../iterations/Iterasyon-36-PostgreSQL-ve-Yazilabilir-Alan-Ekranlari.md)
- [İterasyon 37 — Ad-hoc Özel SQL Çalıştırma Planı](05-Calismalar/Ozel-SQL-Calisiirma-Plani.md)
- [Harici Arayüz Gereksinimleri](../../srs/08-Harici-Arayuzler.md)
- [Frontend Güvenliği](../../srs/09-Fonksiyonel-Olmayan-Gereksinimler/09.05-Guvenlik.md)
