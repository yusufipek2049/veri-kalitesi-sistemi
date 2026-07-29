# Aktif İterasyonlar

## Seçim Kuralı

Aktif bağlam yalnız kronolojik olarak en güncel yedi iterasyon kaydını içerir.
Sıra; tarih, iterasyon numarası, dosya adı ve iç bağımlılıkla doğrulanmıştır.
İterasyon 36 ana planı bu yedi kapanış kaydının üst çalışma planıdır ve sayıma
dahil değildir.

## En Güncel Yedi

| Sıra | İterasyon | Durum | Sonuç |
| --- | --- | --- | --- |
| 1 | [36H2](Iterasyon-36H2-Is-Yurutme-Yasam-Dongusu.md) | `VerificationPending` | İş yürütme yaşam döngüsü kod yüzeyi mevcut; review açık correctness bulguları tespit etti (timeout/iptal sınırlaması, reaper bağlama, atomik iptal, eksik entegrasyon testi). Doğrulanana kadar tamamlanmış sayılmaz. |
| 2 | [36H1](Iterasyon-36H1-Kalici-Is-Kuyrugu-Cekirdegi.md) | `TechnicallyVerified` | Kalıcı iş kuyruğu çekirdeği: idempotent enqueue, deterministik lease claim, sahip-only heartbeat, süresi geçen claim toparlama ve optimistic version concurrency. |
| 3 | [36G](Iterasyon-36G-Guvenli-Rapor-Uretimi-ve-Indirme.md) | `TechnicallyVerified` | Güvenli rapor üretimi/indirme: PDF/XLSX/CSV, politika framework'ü, zamanlanmış rapor, PostgreSQL repository ve frontend UI. |
| 4 | [36F](Iterasyon-36F-Execution-Politika-Worker-Dayanikliligi.md) | `TechnicallyVerified` | Scheduling ve source-usage policy repository'leri PostgreSQL'e taşındı; SQLite eşleri runtime export'tan çıkarıldı. |
| 5 | [36E](Iterasyon-36E-Calisma-PostgreSQL-Cutover.md) | `TechnicallyVerified` | PostgreSQL execution cutover tamamlandı; `SQLiteExecutionRepository` runtime export'tan çıkarıldı. |
| 6 | [36B5](Iterasyon-36B5-Kapatma-ve-Yeniden-Acma.md) | `TechnicallyVerified` | Kapatma/yeniden açma kod ve test kanıtı mevcut; 36E-PG-CUTOVER ile PostgreSQL adaptörleri eklendi. |
| 7 | [36B4](Iterasyon-36B4-Farkli-Aktorle-Dogrulama.md) | `TechnicallyVerified` | Farklı aktörle doğrulama. |

## Aktif Plan

- [İterasyon 36 ana planı](Iterasyon-36-PostgreSQL-ve-Yazilabilir-Alan-Ekranlari.md)
- [Aktif yol haritası](Kalan-Iterasyonlar-Banka-Yol-Haritasi.md)
- [Tek sıradaki çalışma paketi](../NEXT_STEP.md)

Önceki iterasyon kayıtları tarihsel kanıt olarak
[archive/iterations](../archive/iterations/README.md) altında tutulur ve güncel
durum için kanonik kaynak değildir.
