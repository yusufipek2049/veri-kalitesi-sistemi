# Aktif Yol Haritası

| Öncelik | Çalışma paketi | Durum | Çıkış kapısı |
| --- | --- | --- | --- |
| P0 | [Kalıcı iş kuyruğu ve worker dayanıklılığı](../NEXT_STEP.md) | Sıradaki | NEXT_STEP içindeki kalıcı kuyruk, lease/heartbeat, worker kaybı toparlama, politika kontrollü retry/timeout ve dead-letter/audit kapıları geçer. |
| P1 | [36E execution PostgreSQL cutover](Iterasyon-36E-Calisma-PostgreSQL-Cutover.md) | `Completed` / `TechnicallyVerified` | Production PostgreSQL repository yolu ve runtime SQLite export temizliği kapanış kaydında doğrulanmıştır. |
| P2 | [36F scheduling/policy PostgreSQL kalıcılığı](Iterasyon-36F-Execution-Politika-Worker-Dayanikliligi.md) | `Completed` / `TechnicallyVerified` | PostgreSQL repository/migration ve runtime SQLite export temizliği kapanış kaydında doğrulanmıştır. |
| P3 | [36G güvenli rapor üretimi/indirme](Iterasyon-36G-Guvenli-Rapor-Uretimi-ve-Indirme.md) | `Completed` / `TechnicallyVerified` | PDF/XLSX/CSV, zamanlama, politika framework'ü, PostgreSQL repository, API ve frontend kapanış kaydında doğrulanmıştır. |
| P4 | Kurumsal adaptör ve production readiness | Harici bağımlı | IdP/SSO-MFA, secret manager/PAM, HA veri/session, broker, SIEM/WORM, ServiceNow ve DR kanıtı. |

Tamamlanmış eski yol haritası anlatıları aktif bağlamda tutulmaz; tarihsel
iterasyonlar [arşiv indeksindedir](../archive/iterations/README.md).
