---
type: implementation-index
area: testing
project: Veri Kalitesi İzleme ve Skorlama Sistemi
generated_at: 2026-07-16
tags:
  - testing
  - index
---

# Test Haritası

## Ana Kaynaklar

- [Sistem Kabul Kriterleri](../01-SRS/10-Kabul-Kriterleri.md)
- [Kullanım Senaryoları](../01-SRS/05-Kullanim-Senaryolari/INDEX.md)
- [İzlenebilirlik Matrisi](../01-SRS/11-Izlenebilirlik-Matrisi.md)
- [NFR Doğrulama Yöntemleri](../01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/INDEX.md)
- [SRS Kalite Kontrolü](../01-SRS/16-Kalite-Kontrolu.md)
- [Frontend Görsel Doğrulama Stratejisi](03-Uctan-Uca/Gorsel-Dogrulama-Stratejisi.md)

## Önerilen Test Katmanları

1. Skor formülleri, RBAC, durum geçişleri ve idempotency için birim testleri.
2. PostgreSQL/CSV bağlayıcı, LDAP adaptörü, kuyruk ve depolama entegrasyon testleri.
3. UC-001–UC-016 uçtan uca senaryoları.
4. 20 milyon satırlık anonim/sentetik performans veri setiyle profil ve kural testleri.
5. Salt okunurluk, SQL injection, XSS/CSRF, secret ve audit bütünlüğü güvenlik testleri.
6. Yedek geri yükleme ve felaket kurtarma tatbikatı.
7. Storybook component durumları ve Playwright responsive/görsel regression testleri.

## Güncel Otomasyon Baseline'ı

- 682 birim testi geçmektedir.
- `incident_response` hedef grubu, güvenlik olayı/ihlal ayrımı, 72 saat hedefi, veri işleyen kanıtı, maker-checker kararı, yetki/scope redleri, veri-minimum timeline görünümü, audit minimizasyonu ve rollback için 39 sentetik vaka içerir.
- `secure_sdlc` hedef grubu; gerçek pozitif/yanlış pozitif, binary/büyük/dışlanan
  dosya, sembolik bağlantı, salt okunurluk, deterministik sıra, teknik hata ve
  veri-minimum CLI çıktısına ek olarak PEP 621 bağımlılık beyanı, tam sürüm pini,
  dinamik/URL/yinelenen bağımlılık redleri, salt okunurluk ve deterministik
  CycloneDX 1.5 çıktısı, veri-minimum SAST ve doğrudan bağımlılık zafiyet sürüm
  kapıları, sızma testi bulgu yaşam döngüsü/tekrar test kanıtı ve teknik kanıt
  manifesti ve byte düzeyinde drift doğrulama kapısı için toplam 184 sentetik vaka
  içerir.
- Frontend runtime, Storybook ve Playwright otomasyonu henüz kurulmamıştır; görsel
  doğrulama stratejisi `Proposed` durumundadır.
