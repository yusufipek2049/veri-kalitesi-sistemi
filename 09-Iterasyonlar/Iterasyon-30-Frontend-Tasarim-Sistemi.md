---
iteration: 30
status: planned
completed_at: TBD
---

# İterasyon 30 — Frontend Tasarım Sistemi ve Kurumsal Dashboard

Bu iterasyon geçiş kapısından sonraki frontend uygulama programıdır. 30A
dokümantasyon tabanı önceden hazırlanabilir; 30B ve sonrası yeni kullanıcı yüzeyi
açtığından `Bankacilik-Gecis-Durumu.md` geçiş kapısı ve 21B güvenli HTTP/API sınırına
bağlıdır.

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

## Planlanan Uygulama Dilimleri

| Dilim | Değer | Ön koşul |
| --- | --- | --- |
| 30B | Kurumsal design token altyapısı ve açık tema | Geçiş kapısı |
| 30C | Ortak KPI, status badge ve alarm componentleri | 30B |
| 30D | Ortak chart wrapper ve data table standardı | 30B |
| 30E | Kurumsal dashboard referans ekranı | 21B güvenli API, 30C–30D |
| 30F | Storybook ve Playwright görsel regression altyapısı | 30B |
| 30G | Koyu tema ve grafik erişilebilirliği | 30B–30F |

Her dilim tek çalışabilir artım olarak ele alınır; bu belge uygulama dilimlerini
tamamlanmış saymaz.

## Kapsam Dışı

- 30A sırasında frontend framework/component/chart kütüphanesi seçimi veya kurulumu.
- Runtime, API, Storybook veya Playwright yapılandırması.
- Gerçek banka verisiyle ekran veya görsel artifact.
- Mobil yönetim deneyimi.
- Banka marka/uyum onayı.

## Sonraki İş

React + TypeScript + Vite, MUI, ECharts, Storybook ve Playwright teknik seçimleri
kesinleşmiştir. Frontend 30B geçiş kapısı ve `OPEN-BNK-020` tamamlanana kadar
uygulamaya alınmaz. Hazır ve engellenmemiş yeni geçiş artımı bulunmamaktadır.
