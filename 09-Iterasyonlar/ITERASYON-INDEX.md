# Aktif İterasyonlar

## Seçim Kuralı

Aktif bağlam yalnız kronolojik olarak en güncel yedi iterasyon kaydını içerir.
Sıra; tarih, iterasyon numarası, dosya adı ve iç bağımlılıkla doğrulanmıştır.
İterasyon 36 ana planı bu yedi kapanış kaydının üst çalışma planıdır ve sayıma
dahil değildir.

## En Güncel Yedi

| Sıra | İterasyon | Durum | Sonuç |
| --- | --- | --- | --- |
| 1 | [ENTERPRISE-LAB-03](ENTERPRISE-LAB-03-Canli-Compose-Uctan-Uca-Dogrulama.md) | `PrototypeVerified` | Sekiz healthy servis ve gerçek container ağında Keycloak/secret/ServiceNow/SIEM olumlu-negatif adapter akışları doğrulandı. Production readiness/banka onayı değildir. |
| 2 | [ENTERPRISE-LAB-02](ENTERPRISE-LAB-02-Uygulama-Adaptor-Baglantilari.md) | `PrototypeVerified` | Sentetik Keycloak, yerel secret manager, fake ServiceNow ve SIEM uygulama adaptörleri; veri-minimum/idempotent ve fail-closed negatif sözleşmeler. Production readiness/banka onayı değildir. |
| 3 | [ENTERPRISE-LAB-01](ENTERPRISE-LAB-01-Prototip-Kurumsal-Entegrasyon-Laboratuvari.md) | `PrototypeVerified` | Sentetik/non-production Compose laboratuvarı; sekiz sağlıklı servis, fail-closed ortam kapısı ve PostgreSQL streaming standby doğrulandı. Production readiness/banka onayı değildir. |
| 4 | [36H2](Iterasyon-36H2-Is-Yurutme-Yasam-Dongusu.md) | `TechnicallyVerified` | Bounded timeout/iptal, production reaper ve atomik execution+job iptali controller birim/PostgreSQL kapıları ve reviewer `APPROVED` kararıyla doğrulandı. |
| 5 | [36H1](Iterasyon-36H1-Kalici-Is-Kuyrugu-Cekirdegi.md) | `TechnicallyVerified` | Kalıcı iş kuyruğu çekirdeği: idempotent enqueue, deterministik lease claim, sahip-only heartbeat, süresi geçen claim toparlama ve optimistic version concurrency. |
| 6 | [36G](Iterasyon-36G-Guvenli-Rapor-Uretimi-ve-Indirme.md) | `TechnicallyVerified` | Güvenli rapor üretimi/indirme: PDF/XLSX/CSV, zamanlanmış rapor, PostgreSQL repository ve frontend UI. |
| 7 | [36F](Iterasyon-36F-Execution-Politika-Worker-Dayanikliligi.md) | `TechnicallyVerified` | Scheduling ve source-usage policy repository'leri PostgreSQL'e taşındı; SQLite eşleri runtime export'tan çıkarıldı. |

## Aktif Plan

- [İterasyon 36 ana planı](Iterasyon-36-PostgreSQL-ve-Yazilabilir-Alan-Ekranlari.md)
- [Aktif yol haritası](Kalan-Iterasyonlar-Banka-Yol-Haritasi.md)
- [Tek sıradaki çalışma paketi](../NEXT_STEP.md)

Önceki iterasyon kayıtları tarihsel kanıt olarak
[archive/iterations](../archive/iterations/README.md) altında tutulur ve güncel
durum için kanonik kaynak değildir.
