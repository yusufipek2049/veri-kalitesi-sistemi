# Aktif Yol Haritası

| Öncelik | Çalışma paketi | Durum | Çıkış kapısı |
| --- | --- | --- | --- |
| P0 | [Execution PostgreSQL production cutover](../NEXT_STEP.md) | Sıradaki | Production composition root PostgreSQL repository kullanır; runtime SQLite fallback/export kalkar veya yalnız test double olarak açıkça sınırlandırılır; transaction/politika/test kanıtı geçer. |
| P1 | [36B5 doğrulama kaydı](Iterasyon-36B5-Kapatma-ve-Yeniden-Acma.md) | Kanıt bekliyor | Hedefli birim/API ve gerçek PostgreSQL mutasyon koşusu kaydedilir. |
| P2 | Execution politika/worker tamamlama | P0 sonrası | Kota, pencere, timeout, retry, iptal ve idempotency aktif sürümlü politikadan ve kalıcı kuyruktan çözülür. |
| P3 | 36F güvenli rapor üretimi/indirme | Blokeli | DLP, watermark, gerekçe, süreli indirme ve gerekli maker-checker kurumsal kararlarla açılır; eksikte fail-closed. |
| P4 | Kurumsal adaptör ve production readiness | Harici bağımlı | IdP/SSO-MFA, secret manager/PAM, HA veri/session, broker, SIEM/WORM, ServiceNow ve DR kanıtı. |

Tamamlanmış eski yol haritası anlatıları aktif bağlamda tutulmaz; tarihsel
iterasyonlar [arşiv indeksindedir](../archive/iterations/README.md).
