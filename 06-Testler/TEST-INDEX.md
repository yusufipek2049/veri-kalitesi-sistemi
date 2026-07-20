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

- [[01-SRS/10-Kabul-Kriterleri|Sistem Kabul Kriterleri]]
- [[01-SRS/05-Kullanim-Senaryolari/INDEX|Kullanım Senaryoları]]
- [[01-SRS/11-Izlenebilirlik-Matrisi|İzlenebilirlik Matrisi]]
- [[01-SRS/09-Fonksiyonel-Olmayan-Gereksinimler/INDEX|NFR Doğrulama Yöntemleri]]
- [[01-SRS/16-Kalite-Kontrolu|SRS Kalite Kontrolü]]

## Önerilen Test Katmanları

1. Skor formülleri, RBAC, durum geçişleri ve idempotency için birim testleri.
2. PostgreSQL/CSV bağlayıcı, LDAP adaptörü, kuyruk ve depolama entegrasyon testleri.
3. UC-001–UC-016 uçtan uca senaryoları.
4. 20 milyon satırlık anonim/sentetik performans veri setiyle profil ve kural testleri.
5. Salt okunurluk, SQL injection, XSS/CSRF, secret ve audit bütünlüğü güvenlik testleri.
6. Yedek geri yükleme ve felaket kurtarma tatbikatı.

## Güncel Otomasyon Baseline'ı

- 482 birim testi geçmektedir.
- `incident_response` hedef grubu, güvenlik olayı/ihlal ayrımı, 72 saat hedefi, veri işleyen kanıtı, maker-checker kararı, yetki/scope redleri, audit minimizasyonu ve rollback için 23 sentetik vaka içerir.
