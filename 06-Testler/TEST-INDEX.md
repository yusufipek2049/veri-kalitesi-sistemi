---
type: implementation-index
area: testing
project: Veri Kalitesi İzleme ve Skorlama Sistemi
created_at: 2026-07-16
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
2. Ürün bağımsız bağlayıcı, kurumsal IdP/SSO-MFA, secret manager, katalog/DLP, kuyruk ve depolama sözleşme/entegrasyon testleri.
3. UC-001–UC-016 uçtan uca senaryoları.
4. Veri sahibi onaylı, anonimleştirme ve yeniden kimliklendirme risk değerlendirmesi bulunan 20 milyon satırlık üretim örneğiyle tekrarlanabilir profil ve kural testleri.
5. Salt okunurluk, SQL injection, XSS/CSRF, secret ve audit bütünlüğü güvenlik testleri.
6. Yedek geri yükleme ve felaket kurtarma tatbikatı.
7. Storybook component durumları ve Playwright responsive/görsel regression testleri.
8. WCAG 2.2 AA için otomatik kontrole ek manuel klavye ve ekran okuyucu testleri.

## Kesinleşen Kararların Doğrulama Kapsamı

| Karar grubu | Zorunlu senaryo |
| --- | --- |
| OPEN-001 | Düşük/beklenen/yüksek kapasite senaryosu ve üretim envanteri geçiş kontrolü |
| OPEN-002–003 | Kaynak politikasının global varsayılanı geçersiz kılması; politika yokluğunda güvenli ret; kota/pencere/timeout/iptal |
| OPEN-004–006 | Secret rotasyonu/audit; SSO+MFA olumlu ve eksik/başarısız/IdP kesintisi negatif akışları |
| OPEN-007–008, OPEN-011 | Kayıt sınıfı saklama, katmanlı rapor arşiv/imha ve bileşen bazlı restore hedefleri |
| OPEN-009 | ServiceNow kesintisi, idempotency, backoff, dead-letter ve yerel kaydın korunması |
| OPEN-010 | Katalog/DLP kesintisinde bilinen hassas sınıfın düşürülmemesi; rapor/log/erişim kısıtları |
| OPEN-012 | Yüksek riskli değişiklikte görevler ayrılığı; düşük riskli taslakta yetkili tek kullanıcı |
| OPEN-013–014 | Bağlayıcı ortak sözleşmesi ve güvenlik kontrollü 20 milyon satır testi |
| OPEN-015–016 | WCAG manuel/otomatik kontrolleri; bağımsız API/worker ölçekleme, sağlık ve kontrollü kapatma |
| OPEN-017 | Kritik işlem audit arızasında fail-closed; rutin outbox kesintisinde kayıpsız retry/alarm |
| OPEN-018 | Politika koşullarının tamamında kısmi resmî skor; her eksik koşul ve politika yokluğunda provizyonel dışlama |

## Güncel Otomasyon Baseline'ı

- 855 test geçmektedir.
- Tam statik tip kontrolü `python3 -m mypy 03-Backend/src 06-Testler` komutuyla
  127 kaynak dosyada sıfır hata vermektedir.
- `incident_response` hedef grubu, güvenlik olayı/ihlal ayrımı, 72 saat hedefi, veri işleyen kanıtı, maker-checker kararı, yetki/scope redleri, veri-minimum timeline görünümü, audit minimizasyonu ve rollback için 39 sentetik vaka içerir.
- `secure_sdlc` hedef grubu; gerçek pozitif/yanlış pozitif, binary/büyük/dışlanan
  dosya, sembolik bağlantı, salt okunurluk, deterministik sıra, teknik hata ve
  veri-minimum CLI çıktısına ek olarak PEP 621 bağımlılık beyanı, tam sürüm pini,
  dinamik/URL/yinelenen bağımlılık redleri, salt okunurluk ve deterministik
  CycloneDX 1.5 çıktısı, veri-minimum SAST ve doğrudan bağımlılık zafiyet sürüm
  kapıları, sızma testi bulgu yaşam döngüsü/tekrar test kanıtı ve teknik kanıt
  manifesti, byte düzeyinde drift kapısı ve altı kontrollü birleşik yerel preflight
  için toplam 204 sentetik vaka içerir.
- Frontend runtime, Storybook ve Playwright otomasyonu henüz kurulmamıştır; görsel
  doğrulama stratejisi `Proposed` durumundadır.
