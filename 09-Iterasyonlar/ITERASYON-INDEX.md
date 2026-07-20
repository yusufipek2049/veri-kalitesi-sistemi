# Bankacılık Geçiş İterasyonları

## Gerçek başlangıç noktası

- 16 iterasyon, Iterasyon 17A–17E, Iterasyon 18A–18C, Iterasyon 19A–19C, Iterasyon 20A–20C, Iterasyon 21A, Iterasyon 22A–22I, Iterasyon 23A–23D ve Iterasyon 24A–24B teknik dikeyleri tamamlandı.
- 459 birim testi geçiyor.
- Son ürün artımı güvenilir rol/source kapsamıyla salt okunur, aggregate-only ve auditli rapor önizlemesi sağlar.
- Kural onay süre aşımı `OPEN-BNK-017`; HTTP/session kararları `OPEN-BNK-020`, hassas dışa aktarma `OPEN-BNK-014` nedeniyle engellidir. Sıradaki hazır aday veri-minimum güvenlik olayı ve ihlal şüphesi ayrımıdır.

## Sıra

1. [[Iterasyon-16-Guvenilir-Aktor-Baglami]] - TechnicallyVerified
2. [[Iterasyon-17-Merkezi-Audit-Butunlugu]] - 17A–17E `TechnicallyVerified`
3. [[Iterasyon-18-Veri-Siniflandirma-ve-Maskeleme]] - 18A–18C `TechnicallyVerified`
4. [[Iterasyon-19-Maker-Checker]] - 19A–19C `TechnicallyVerified`, 19D engelli
5. [[Iterasyon-20-LDAP-RBAC-Entegrasyonu]] - 20A–20C `TechnicallyVerified`; üretim kararları açık
6. [[Kalan-Iterasyonlar-Banka-Yol-Haritasi]]

Her iterasyon [[Iterasyon-Kapanis-Sablonu]] ile kapatılır.
