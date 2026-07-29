# Aktif Yol Haritası

| Öncelik | Çalışma paketi | Durum | Çıkış kapısı |
| --- | --- | --- | --- |
| P0 | [İş yürütme yaşam döngüsü doğrulaması (36H2)](../NEXT_STEP.md) | `In-Progress` / `VerificationPending` | 36H2 kod yüzeyi mevcut; review açık bulgular tespit etti (bounded handler wait, reaper bağlama, atomik iptal, eksik entegrasyon testi). Bulgular kapanıp reviewer `APPROVED` verince tamamlanır. |
| P1 | [36H1 kalıcı iş kuyruğu çekirdeği](Iterasyon-36H1-Kalici-Is-Kuyrugu-Cekirdegi.md) | `Completed` / `TechnicallyVerified` | Idempotent enqueue, deterministik lease claim, sahip-only heartbeat, süresi geçen claim toparlama, optimistic version concurrency ve `background_jobs` migration'ı kapanış kaydında doğrulanmıştır. |
| P2 | [36E execution PostgreSQL cutover](Iterasyon-36E-Calisma-PostgreSQL-Cutover.md) | `Completed` / `TechnicallyVerified` | Production PostgreSQL repository yolu ve runtime SQLite export temizliği kapanış kaydında doğrulanmıştır. |
| P2 | [36F scheduling/policy PostgreSQL kalıcılığı](Iterasyon-36F-Execution-Politika-Worker-Dayanikliligi.md) | `Completed` / `TechnicallyVerified` | PostgreSQL repository/migration ve runtime SQLite export temizliği kapanış kaydında doğrulanmıştır. |
| P3 | [36G güvenli rapor üretimi/indirme](Iterasyon-36G-Guvenli-Rapor-Uretimi-ve-Indirme.md) | `Completed` / `TechnicallyVerified` | PDF/XLSX/CSV, zamanlama, politika framework'ü, PostgreSQL repository, API ve frontend kapanış kaydında doğrulanmıştır. |
| P4 | Kurumsal adaptör ve production readiness | Harici bağımlı | IdP/SSO-MFA, secret manager/PAM, HA veri/session, broker, SIEM/WORM, ServiceNow ve DR kanıtı. |

Tamamlanmış eski yol haritası anlatıları aktif bağlamda tutulmaz; tarihsel
iterasyonlar [arşiv indeksindedir](../archive/iterations/README.md).
