# Bankacılık Geçiş İterasyonları

## Gerçek başlangıç noktası

- 16 iterasyon, İterasyon 17A–17E, İterasyon 18A–18C, Iterasyon 19A–19H, Iterasyon 20A–20C, Iterasyon 21A, İterasyon 22A–22İ, İterasyon 23A–23D, İterasyon 24A–24B, İterasyon 25A–25D, İterasyon 26A–26B, İterasyon 27A, İterasyon 28A–28E, İterasyon 29A–29C, İterasyon 31A–31C, İterasyon 32A–32D, İterasyon 33A ve İterasyon 34A–34C teknik dikeyleri tamamlandı.
- 958 birim testi geçiyor; tam mypy kontrolü 141 kaynak dosyada sıfır hata veriyor.
- Son ürün artımı Golden yapısal beklentiyi runtime skorlayıcısından ve üreticinin kendi doğrulamasından bağımsız karşılaştırır.
- İterasyon 27A `TechnicallyVerified` durumundadır. Restore/DR dilimleri `OPEN-BNK-011` ve `OPEN-BNK-012` kararlarını bekler.

## Sıra

1. [Iterasyon-16-Guvenilir-Aktor-Baglami](Iterasyon-16-Guvenilir-Aktor-Baglami.md) - TechnicallyVerified
2. [Iterasyon-17-Merkezi-Audit-Butunlugu](Iterasyon-17-Merkezi-Audit-Butunlugu.md) - 17A–17E `TechnicallyVerified`
3. [Iterasyon-18-Veri-Siniflandirma-ve-Maskeleme](Iterasyon-18-Veri-Siniflandirma-ve-Maskeleme.md) - 18A–18C `TechnicallyVerified`
4. [Iterasyon-19-Maker-Checker](Iterasyon-19-Maker-Checker.md) - 19A–19H `TechnicallyVerified`; banka rol eşlemesi ve çalışan iş politikası açık
5. [Iterasyon-20-LDAP-RBAC-Entegrasyonu](Iterasyon-20-LDAP-RBAC-Entegrasyonu.md) - 20A–20C `TechnicallyVerified`; üretim kararları açık
6. [Kalan-Iterasyonlar-Banka-Yol-Haritasi](Kalan-Iterasyonlar-Banka-Yol-Haritasi.md) - 25A–25D `TechnicallyVerified`; gerçek adaptörler engelli
7. [Iterasyon-26-Olay-Mudahale-ve-Ihlal-Kaniti](Iterasyon-26-Olay-Mudahale-ve-Ihlal-Kaniti.md) - 26A–26B `TechnicallyVerified`
8. [Iterasyon-27-Ortam-Ayrimi-ve-DR](Iterasyon-27-Ortam-Ayrimi-ve-DR.md) - 27A `TechnicallyVerified`; restore/DR engelli
9. [Iterasyon-28-Guvenli-SDLC](Iterasyon-28-Guvenli-SDLC.md) - 28A–28E `TechnicallyVerified`
10. [Iterasyon-29-Teknik-Kanit-Paketi](Iterasyon-29-Teknik-Kanit-Paketi.md) - 29A–29C `TechnicallyVerified`; 29D engelli
11. [Iterasyon-30-Frontend-Tasarim-Sistemi](Iterasyon-30-Frontend-Tasarim-Sistemi.md) - 30A dökümantasyon tabanı tamamlandı; uygulama geçiş kapısına bağlı
12. [Bakım-Iterasyonu-29C1-Tam-Depo-Tip-Kontrolu](Bakim-Iterasyonu-29C1-Tam-Depo-Tip-Kontrolu.md) - `TechnicallyVerified`
13. [Iterasyon-31-Kaynak-Kullanim-Politikasi](Iterasyon-31-Kaynak-Kullanim-Politikasi.md) - 31A–31C `TechnicallyVerified`; CPU/IO ve hız sınırı alanları açık
14. [Iterasyon-32-Kismi-Skor-Politikasi](Iterasyon-32-Kismi-Skor-Politikasi.md) - 32A–32D `TechnicallyVerified`; süre aşımı ve güvenilir olgu üretimi açık
15. [Iterasyon-33-Kanonik-Kural-Skoru](Iterasyon-33-Kanonik-Kural-Skoru.md) - 33A `TechnicallyVerified`; tarihsel backfill ve yeterlilik dilimleri açık
16. [Iterasyon-34-Sentetik-Veri-Kayit-Cekirdegi](Iterasyon-34-Sentetik-Veri-Kayit-Cekirdegi.md) - 34A–34C `TechnicallyVerified`; kalıcı çıktı, tam ground truth ve gizlilik kapısı açık

Her iterasyon [Iterasyon-Kapanis-Sablonu](Iterasyon-Kapanis-Sablonu.md) ile kapatılır.
