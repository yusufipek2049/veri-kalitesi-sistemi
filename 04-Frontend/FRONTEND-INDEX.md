---
type: implementation-index
area: frontend
project: Veri Kalitesi İzleme ve Skorlama Sistemi
created_at: 2026-07-16
tags:
  - frontend
  - index
---

# Frontend Ekran Haritası

## Onaylı Teknoloji Yığını

- Uygulama: React + TypeScript + Vite
- Component sistemi: MUI
- Grafik: ECharts
- Component doğrulama: Storybook
- Ekran, akış ve görsel regression: Playwright

Bu seçimler `ADR-017` ile kabul edilmiştir; yeniden teknoloji veya dependency
onayı beklenmez. Paket kurulumu ve frontend uygulaması henüz tamamlanmamıştır.

## Tasarım ve Uygulama Kaynakları

- [Görsel Tasarım Sistemi](Gorsel-Tasarim-Sistemi.md)
- [Dashboard Ekran Sözleşmesi](03-Dashboard/Dashboard-Ekran-Sozlesmesi.md)
- [Veri Kalitesi Skorlama ve Ölçüm Yeterliliği](../02-Mimari/Veri-Kalitesi-Skorlama-ve-Olcum-Yeterliligi.md)
- [Kurumsal dashboard referansı](references/reference-dashboard.png)
- [Görsel Doğrulama Stratejisi](../06-Testler/03-Uctan-Uca/Gorsel-Dogrulama-Stratejisi.md)
- [Frontend Teknoloji Yığını Kararı](../02-Mimari/Mimari-Kararlar.md#adr-017--frontend-teknoloji-yığını)

## Ekranlar

- Giriş ve oturum: [04.01-Kullanici-ve-Yetki](../01-SRS/04-Fonksiyonel-Gereksinimler/04.01-Kullanici-ve-Yetki.md)
- Veri kaynağı listesi, formu ve bağlantı testi: [04.02-Veri-Kaynagi-Yonetimi](../01-SRS/04-Fonksiyonel-Gereksinimler/04.02-Veri-Kaynagi-Yonetimi.md)
- Metadata keşfi ve profil sonuçları: [04.03-Metadata-ve-Profilleme](../01-SRS/04-Fonksiyonel-Gereksinimler/04.03-Metadata-ve-Profilleme.md)
- Kural oluşturma, test, sürüm ve onay: [04.04-Kural-Yonetimi](../01-SRS/04-Fonksiyonel-Gereksinimler/04.04-Kural-Yonetimi.md)
- Çalıştırma, zamanlama ve geçmiş: [04.05-Calistirma-ve-Zamanlama](../01-SRS/04-Fonksiyonel-Gereksinimler/04.05-Calistirma-ve-Zamanlama.md)
- Dashboard ve drill-down: [04.07-Dashboard](../01-SRS/04-Fonksiyonel-Gereksinimler/04.07-Dashboard.md)
- Bildirim merkezi: [04.08-Bildirim](../01-SRS/04-Fonksiyonel-Gereksinimler/04.08-Bildirim.md)
- Sorun yönetimi: [04.09-Sorun-Yonetimi](../01-SRS/04-Fonksiyonel-Gereksinimler/04.09-Sorun-Yonetimi.md)
- Rapor ve dışa aktarma: [04.10-Raporlama](../01-SRS/04-Fonksiyonel-Gereksinimler/04.10-Raporlama.md)
- Audit inceleme: [04.11-Audit](../01-SRS/04-Fonksiyonel-Gereksinimler/04.11-Audit.md)

## UI Kuralları

- [Harici Arayüz Gereksinimleri](../01-SRS/08-Harici-Arayuzler.md)
- [Kullanıcı Deneyimi NFR](../01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.07-Kullanici-Deneyimi.md)
- [Frontend Güvenliği](../01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/09.05-Guvenlik.md)
