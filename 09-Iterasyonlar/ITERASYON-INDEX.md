# Aktif İterasyonlar

## Seçim Kuralı

Aktif bağlam yalnız kronolojik olarak en güncel yedi iterasyon kaydını içerir.
Sıra; tarih, iterasyon numarası, dosya adı ve iç bağımlılıkla doğrulanmıştır.
İterasyon 36 ana planı bu yedi kapanış kaydının üst çalışma planıdır ve sayıma
dahil değildir.

## En Güncel Yedi

| Sıra | İterasyon | Durum | Sonuç |
| --- | --- | --- | --- |
| 1 | [36G](Iterasyon-36G-Guvenli-Rapor-Uretimi-ve-Indirme.md) | `TechnicallyVerified` | Güvenli rapor üretimi/indirme: PDF/XLSX/CSV, DLP/watermark/maker-checker, zamanlanmış rapor, PostgreSQL repository, frontent UI. |
| 2 | [36B2](Iterasyon-36B2-Guvenilir-Yeniden-Atama.md) | `TechnicallyVerified` | Güvenilir yeniden atama. |
| 3 | [36B3](Iterasyon-36B3-Korumali-Cozum-Kaydi.md) | `TechnicallyVerified` | Korumalı çözüm kaydı. |
| 4 | [36B4](Iterasyon-36B4-Farkli-Aktorle-Dogrulama.md) | `TechnicallyVerified` | Farklı aktörle doğrulama. |
| 5 | [36B5](Iterasyon-36B5-Kapatma-ve-Yeniden-Acma.md) | `TechnicallyVerified` | Kapatma/yeniden açma kod ve test kanıtı mevcut; 36E-PG-CUTOVER ile PostgreSQL adaptörleri eklendi. |
| 6 | [36E](Iterasyon-36E-Calisma-PostgreSQL-Cutover.md) | `TechnicallyVerified` | PostgreSQL execution cutover tamamlandı; `SQLiteExecutionRepository` runtime export'tan çıkarıldı. |
| 7 | [36F](Iterasyon-36F-Execution-Politika-Worker-Dayanikliligi.md) | `TechnicallyVerified` | Execution politika ve worker dayanıklılığı PostgreSQL'e taşındı; scheduling/policy repository runtime export'tan çıkarıldı. |

## Aktif Plan

- [İterasyon 36 ana planı](Iterasyon-36-PostgreSQL-ve-Yazilabilir-Alan-Ekranlari.md)
- [Aktif yol haritası](Kalan-Iterasyonlar-Banka-Yol-Haritasi.md)
- [Tek sıradaki çalışma paketi](../NEXT_STEP.md)

Önceki iterasyon kayıtları tarihsel kanıt olarak
[archive/iterations](../archive/iterations/README.md) altında tutulur ve güncel
durum için kanonik kaynak değildir.
