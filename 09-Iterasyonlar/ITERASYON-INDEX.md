# Bankacılık Geçiş İterasyonları

## Gerçek başlangıç noktası

- 16 iterasyon, İterasyon 17A–17E, İterasyon 18A–18C, Iterasyon 19A–19H, Iterasyon 20A–20E, Iterasyon 21A–21C, İterasyon 22A–22İ, İterasyon 23A–23D, İterasyon 24A–24B, İterasyon 25A–25D, İterasyon 26A–26B, İterasyon 27A, İterasyon 28A–28E, İterasyon 29A–29C, İterasyon 30A–30D, İterasyon 31A–31C, İterasyon 32A–32D, İterasyon 33A–33B, İterasyon 34A–34F ve İterasyon 35A–35F teknik dikeyleri tamamlandı.
- Tam depoda gerçek issue PostgreSQL testleri dahil 1070 test geçiyor; iki
  sentetik PostgreSQL testi ayrı opt-in bayrağı nedeniyle atlanıyor. Tam mypy
  kontrolü 133 kaynak dosyada sıfır hata veriyor.
- Son ürün artımı `AUDIT_VIEWER` rol kontrollü, snapshot sayfalı ve bütünlük
  gösterimli Denetim API'sini ve salt okunur frontend rotasını ekler; dışa aktarma, gerçek IdP ve
  üretim session/veri altyapısını tamamlamaz.
- İterasyon 27A `TechnicallyVerified` durumundadır. Restore/DR dilimleri `OPEN-BNK-011` ve `OPEN-BNK-012` kararlarını bekler.

## Sıra

1. [Iterasyon-16-Guvenilir-Aktor-Baglami](Iterasyon-16-Guvenilir-Aktor-Baglami.md) - TechnicallyVerified
2. [Iterasyon-17-Merkezi-Audit-Butunlugu](Iterasyon-17-Merkezi-Audit-Butunlugu.md) - 17A–17E `TechnicallyVerified`
3. [Iterasyon-18-Veri-Siniflandirma-ve-Maskeleme](Iterasyon-18-Veri-Siniflandirma-ve-Maskeleme.md) - 18A–18C `TechnicallyVerified`
4. [Iterasyon-19-Maker-Checker](Iterasyon-19-Maker-Checker.md) - 19A–19H `TechnicallyVerified`; banka rol eşlemesi ve çalışan iş politikası açık
5. [Iterasyon-20-LDAP-RBAC-Entegrasyonu](Iterasyon-20-LDAP-RBAC-Entegrasyonu.md) - 20A–20E `TechnicallyVerified`; gerçek IdP ve üretim altyapısı açık
6. [Kalan-Iterasyonlar-Banka-Yol-Haritasi](Kalan-Iterasyonlar-Banka-Yol-Haritasi.md) - 25A–25D `TechnicallyVerified`; gerçek adaptörler engelli
7. [Iterasyon-26-Olay-Mudahale-ve-Ihlal-Kaniti](Iterasyon-26-Olay-Mudahale-ve-Ihlal-Kaniti.md) - 26A–26B `TechnicallyVerified`
8. [Iterasyon-27-Ortam-Ayrimi-ve-DR](Iterasyon-27-Ortam-Ayrimi-ve-DR.md) - 27A `TechnicallyVerified`; restore/DR engelli
9. [Iterasyon-28-Guvenli-SDLC](Iterasyon-28-Guvenli-SDLC.md) - 28A–28E `TechnicallyVerified`
10. [Iterasyon-29-Teknik-Kanit-Paketi](Iterasyon-29-Teknik-Kanit-Paketi.md) - 29A–29C `TechnicallyVerified`; 29D engelli
11. [Iterasyon-30-Frontend-Tasarim-Sistemi](Iterasyon-30-Frontend-Tasarim-Sistemi.md) - 30A dokümantasyon ile 30B–30D frontend artımları `TechnicallyVerified`; üretim bağlantısı engelli
12. [Bakım-Iterasyonu-29C1-Tam-Depo-Tip-Kontrolu](Bakim-Iterasyonu-29C1-Tam-Depo-Tip-Kontrolu.md) - `TechnicallyVerified`
13. [Iterasyon-31-Kaynak-Kullanim-Politikasi](Iterasyon-31-Kaynak-Kullanim-Politikasi.md) - 31A–31C `TechnicallyVerified`; CPU/IO ve hız sınırı alanları açık
14. [Iterasyon-32-Kismi-Skor-Politikasi](Iterasyon-32-Kismi-Skor-Politikasi.md) - 32A–32D `TechnicallyVerified`; süre aşımı ve güvenilir olgu üretimi açık
15. [Iterasyon-33-Kanonik-Kural-Skoru](Iterasyon-33-Kanonik-Kural-Skoru.md) - 33A `TechnicallyVerified`; tarihsel backfill ve yeterlilik dilimleri açık
16. [Iterasyon-34-Sentetik-Veri-Kayit-Cekirdegi](Iterasyon-34-Sentetik-Veri-Kayit-Cekirdegi.md) - 34A–34F `TechnicallyVerified`; PostgreSQL kusur dataseti hazır, uygulama profil/kural entegrasyonu ve gizlilik kapısı açık
17. [Iterasyon-21-Dashboard-API](Iterasyon-21-Dashboard-API.md) - 21B güvenli özet API ve 21C operasyonel gösterge DTO'su `TechnicallyVerified`; 30D UI bağlantısı tamamlandı, gerçek IdP ve üretim altyapısı açık
18. [Iterasyon-35-Frontend-Alan-Ekranlari](Iterasyon-35-Frontend-Alan-Ekranlari.md) - 35A Veri Kaynakları, 35B Kurallar, 35C Çalıştırmalar, 35D Sorunlar, 35E Raporlar ve 35F Denetim ekranı `TechnicallyVerified`
19. [Iterasyon-36-PostgreSQL-ve-Yazilabilir-Alan-Ekranlari](Iterasyon-36-PostgreSQL-ve-Yazilabilir-Alan-Ekranlari.md) - [36A1 PostgreSQL kalıcılık temeli](Iterasyon-36A1-PostgreSQL-Kaliclilik-Temeli.md), [36A2a issue mutasyon/audit outbox](Iterasjon-36A2a-PostgreSQL-Issue-Mutason-Audit.md), [36A2b seçici aktarım/SQLite kaldırma](Iterasjon-36A2b-Secici-Issue-Aktarimi.md), [36B1 atanmış sorunu incelemeye alma](Iterasjon-36B1-Sorunu-Incelemeye-Alma.md), [36B2 güvenilir yeniden atama](Iterasjon-36B2-Guvenilir-Yeniden-Atama.md), [36B3 korumalı çözüm kaydı](Iterasjon-36B3-Korumali-Cozum-Kaydi.md) ve [36B4 farklı aktörle doğrulama](Iterasjon-36B4-Farkli-Aktorle-Dogrulama.md) `TechnicallyVerified`; 36B5 sorun kapatma ve 36C0 kural repository PostgreSQL geçişi `TechnicallyVerified`

Her iterasyon [Iterasyon-Kapanis-Sablonu](Iterasyon-Kapanis-Sablonu.md) ile kapatılır.
