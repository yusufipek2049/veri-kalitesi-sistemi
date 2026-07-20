# Bankacılık Geçiş İterasyonları

## Gerçek başlangıç noktası

- 16 iterasyon, Iterasyon 17A–17E, Iterasyon 18A–18C, Iterasyon 19A–19C, Iterasyon 20A–20C, Iterasyon 21A, Iterasyon 22A–22I, Iterasyon 23A–23D, Iterasyon 24A–24B, Iterasyon 26A–26B ve Iterasyon 28A–28C teknik dikeyleri tamamlandı.
- 556 birim testi geçiyor.
- Son ürün artımı veri-minimum SAST bulgularını proje sürümüne bağlar; tamamlanmamış tarama ve kritik bulgu sürüm kanıtını fail-closed engeller.
- Kural onay süre aşımı `OPEN-BNK-017`; HTTP/session kararları `OPEN-BNK-020`, hassas dışa aktarma `OPEN-BNK-014` ve gerçek SIEM/SOC `OPEN-BNK-010` nedeniyle engellidir. Sıradaki hazır aday bağımlılık zafiyet bulgu zarfı ve sürüm kapısı sözleşmesidir.

## Sıra

1. [[Iterasyon-16-Guvenilir-Aktor-Baglami]] - TechnicallyVerified
2. [[Iterasyon-17-Merkezi-Audit-Butunlugu]] - 17A–17E `TechnicallyVerified`
3. [[Iterasyon-18-Veri-Siniflandirma-ve-Maskeleme]] - 18A–18C `TechnicallyVerified`
4. [[Iterasyon-19-Maker-Checker]] - 19A–19C `TechnicallyVerified`, 19D engelli
5. [[Iterasyon-20-LDAP-RBAC-Entegrasyonu]] - 20A–20C `TechnicallyVerified`; üretim kararları açık
6. [[Kalan-Iterasyonlar-Banka-Yol-Haritasi]]
7. [[Iterasyon-26-Olay-Mudahale-ve-Ihlal-Kaniti]] - 26A–26B `TechnicallyVerified`
8. [[Iterasyon-28-Guvenli-SDLC]] - 28A–28C `TechnicallyVerified`
9. [[Iterasyon-30-Frontend-Tasarim-Sistemi]] - 30A dokümantasyon tabanı tamamlandı; uygulama geçiş kapısına bağlı

Her iterasyon [[Iterasyon-Kapanis-Sablonu]] ile kapatılır.
