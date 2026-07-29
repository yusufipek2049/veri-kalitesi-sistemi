# Aktif İterasyonlar

## Seçim Kuralı

Aktif bağlam yalnız kronolojik olarak en güncel yedi iterasyon kaydını içerir.
Sıra; tarih, iterasyon numarası, dosya adı ve iç bağımlılıkla doğrulanmıştır.
İterasyon 36 ana planı bu yedi kapanış kaydının üst çalışma planıdır ve sayıma
dahil değildir.

## En Güncel Yedi

| Sıra | İterasyon | Durum | Sonuç |
| --- | --- | --- | --- |
| 1 | [ENTERPRISE-LAB-01](ENTERPRISE-LAB-01-Prototip-Kurumsal-Entegrasyon-Laboratuvari.md) | `PrototypeVerified` | Sentetik/non-production Compose laboratuvarı; sekiz sağlıklı servis, fail-closed ortam kapısı ve PostgreSQL streaming standby doğrulandı. Production readiness/banka onayı değildir. |
| 2 | [36H2](Iterasyon-36H2-Is-Yurutme-Yasam-Dongusu.md) | `TechnicallyVerified` | Bounded timeout/iptal, production reaper ve atomik execution+job iptali controller birim/PostgreSQL kapıları ve reviewer `APPROVED` kararıyla doğrulandı. |
| 3 | [36H1](Iterasyon-36H1-Kalici-Is-Kuyrugu-Cekirdegi.md) | `TechnicallyVerified` | Kalıcı iş kuyruğu çekirdeği: idempotent enqueue, deterministik lease claim, sahip-only heartbeat, süresi geçen claim toparlama ve optimistic version concurrency. |
| 4 | [36G](Iterasyon-36G-Guvenli-Rapor-Uretimi-ve-Indirme.md) | `TechnicallyVerified` | Güvenli rapor üretimi/indirme: PDF/XLSX/CSV, zamanlanmış rapor, PostgreSQL repository ve frontend UI. |
| 5 | [36F](Iterasyon-36F-Execution-Politika-Worker-Dayanikliligi.md) | `TechnicallyVerified` | Scheduling ve source-usage policy repository'leri PostgreSQL'e taşındı; SQLite eşleri runtime export'tan çıkarıldı. |
| 6 | [36E](Iterasyon-36E-Calisma-PostgreSQL-Cutover.md) | `TechnicallyVerified` | PostgreSQL execution cutover tamamlandı; `SQLiteExecutionRepository` runtime export'tan çıkarıldı. |
| 7 | [36B5](Iterasyon-36B5-Kapatma-ve-Yeniden-Acma.md) | `TechnicallyVerified` | Kapatma/yeniden açma kod ve test kanıtı mevcut; 36E-PG-CUTOVER ile PostgreSQL adaptörleri eklendi. |

## Aktif Plan

- [İterasyon 36 ana planı](Iterasyon-36-PostgreSQL-ve-Yazilabilir-Alan-Ekranlari.md)
- [Aktif yol haritası](Kalan-Iterasyonlar-Banka-Yol-Haritasi.md)
- [Tek sıradaki çalışma paketi](../NEXT_STEP.md)

Önceki iterasyon kayıtları tarihsel kanıt olarak
[archive/iterations](../archive/iterations/README.md) altında tutulur ve güncel
durum için kanonik kaynak değildir.
