# Bankacılık Geçiş İterasyonları

## Gerçek başlangıç noktası

- 16 iterasyon, Iterasyon 17A–17E, Iterasyon 18A–18C, Iterasyon 19A–19C, Iterasyon 20A–20C, Iterasyon 21A, Iterasyon 22A–22I, Iterasyon 23A–23D, Iterasyon 24A–24B, Iterasyon 26A–26B, Iterasyon 28A–28E ve Iterasyon 29A–29C teknik dikeyleri tamamlandı.
- 702 birim testi geçiyor; Bakım İterasyonu 29C.1 sonrasında tam mypy kontrolü
  109 kaynak dosyada sıfır hata veriyor.
- Son ürün artımı altı mevcut yerel güvenli SDLC kontrolünü tek veri-minimum, fail-closed sürüm ön kontrolünde birleştirir.
- Hazır ve engellenmemiş yeni geçiş artımı yoktur. 29D kurumsal CI/CD/kanıt yayını `OPEN-BNK-012`; 19D `OPEN-BNK-017`, HTTP/frontend `OPEN-BNK-020`, hassas dışa aktarma `OPEN-BNK-014` ve gerçek SIEM/SOC `OPEN-BNK-010` nedeniyle engellidir.

## Sıra

1. [Iterasyon-16-Guvenilir-Aktor-Baglami](Iterasyon-16-Guvenilir-Aktor-Baglami.md) - TechnicallyVerified
2. [Iterasyon-17-Merkezi-Audit-Butunlugu](Iterasyon-17-Merkezi-Audit-Butunlugu.md) - 17A–17E `TechnicallyVerified`
3. [Iterasyon-18-Veri-Siniflandirma-ve-Maskeleme](Iterasyon-18-Veri-Siniflandirma-ve-Maskeleme.md) - 18A–18C `TechnicallyVerified`
4. [Iterasyon-19-Maker-Checker](Iterasyon-19-Maker-Checker.md) - 19A–19C `TechnicallyVerified`, 19D engelli
5. [Iterasyon-20-LDAP-RBAC-Entegrasyonu](Iterasyon-20-LDAP-RBAC-Entegrasyonu.md) - 20A–20C `TechnicallyVerified`; üretim kararları açık
6. [Kalan-Iterasyonlar-Banka-Yol-Haritasi](Kalan-Iterasyonlar-Banka-Yol-Haritasi.md)
7. [Iterasyon-26-Olay-Mudahale-ve-Ihlal-Kaniti](Iterasyon-26-Olay-Mudahale-ve-Ihlal-Kaniti.md) - 26A–26B `TechnicallyVerified`
8. [Iterasyon-28-Guvenli-SDLC](Iterasyon-28-Guvenli-SDLC.md) - 28A–28E `TechnicallyVerified`
9. [Iterasyon-29-Teknik-Kanit-Paketi](Iterasyon-29-Teknik-Kanit-Paketi.md) - 29A–29C `TechnicallyVerified`; 29D engelli
10. [Iterasyon-30-Frontend-Tasarim-Sistemi](Iterasyon-30-Frontend-Tasarim-Sistemi.md) - 30A dokümantasyon tabanı tamamlandı; uygulama geçiş kapısına bağlı
11. [Bakım-Iterasyonu-29C1-Tam-Depo-Tip-Kontrolu](Bakim-Iterasyonu-29C1-Tam-Depo-Tip-Kontrolu.md) - `TechnicallyVerified`

Her iterasyon [Iterasyon-Kapanis-Sablonu](Iterasyon-Kapanis-Sablonu.md) ile kapatılır.
