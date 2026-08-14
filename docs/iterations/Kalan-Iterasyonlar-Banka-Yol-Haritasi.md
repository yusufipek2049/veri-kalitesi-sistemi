# Aktif Yol Haritası

| Öncelik | Çalışma paketi | Durum | Çıkış kapısı |
| --- | --- | --- | --- |
| P0 | [İş yürütme yaşam döngüsü (36H2)](../../NEXT_STEP.md) | `Completed` / `TechnicallyVerified` | Bounded timeout/iptal, production reaper ve atomik execution+job iptali controller kapıları ve reviewer `APPROVED` kararıyla doğrulandı. |
| P1 | [36H1 kalıcı iş kuyruğu çekirdeği](../../archive/iterations/36/Iterasyon-36H1-Kalici-Is-Kuyrugu-Cekirdegi.md) | `Completed` / `TechnicallyVerified` | Idempotent enqueue, deterministik lease claim, sahip-only heartbeat, süresi geçen claim toparlama, optimistic version concurrency ve `background_jobs` migration'ı kapanış kaydında doğrulanmıştır. |
| P2 | [36E execution PostgreSQL cutover](../../archive/iterations/36/Iterasyon-36E-Calisma-PostgreSQL-Cutover.md) | `Completed` / `TechnicallyVerified` | Production PostgreSQL repository yolu ve runtime SQLite export temizliği kapanış kaydında doğrulanmıştır. |
| P2 | [36F scheduling/policy PostgreSQL kalıcılığı](../../archive/iterations/36/Iterasyon-36F-Execution-Politika-Worker-Dayanikliligi.md) | `Completed` / `TechnicallyVerified` | PostgreSQL repository/migration ve runtime SQLite export temizliği kapanış kaydında doğrulanmıştır. |
| P3 | [36G güvenli rapor üretimi/indirme](../../archive/iterations/36/Iterasyon-36G-Guvenli-Rapor-Uretimi-ve-Indirme.md) | `Completed` / `TechnicallyVerified` | PDF/XLSX/CSV, zamanlama, politika framework'ü, PostgreSQL repository, API ve frontend kapanış kaydında doğrulanmıştır. |
| P3 | [Denetim sayfası geliştirmeleri (37A–37E)](Iterasyon-37A-37E-Denetim-Sayfasi-Gelistirmeleri.md) | 37A `TechnicallyVerified`; 37B–37E `Planned` | Olay detay drawer, correlation arama, dışa aktarma, özet istatistik, bağlamsal navigasyon, timeline görünümü. |
| P4 | Kurumsal adaptör ve production readiness | Harici bağımlı | IdP/SSO-MFA, secret manager/PAM, HA veri/session, broker, SIEM/WORM, ServiceNow ve DR kanıtı. |

## Yetenek Yükseltme Programı (39–43)

Karar referansı: `USER-DECLARATION-2026-08-CAPABILITY-UPLIFT`.
Sıralama bağımlılığa göredir; 39 diğerlerinin kanıt yüzeyini kurar.

| Sıra | Çalışma paketi | Durum | Çıkış kapısı |
| --- | --- | --- | --- |
| 1 | [39A–39D kanıt yüzeyi kablolaması](Iterasyon-39A-39C-Kanit-Yuzeyi-Kablolamasi.md) | `Planned` | Etki/kök neden, skor yeniden üretimi ve raporlama HTTP yüzeyinden erişilebilir; `known-gaps.md` CI ile doğrulanır. |
| 2 | [40 takvim farkındalıklı eşik önerisi](Iterasyon-40-Takvim-Farkindalikli-Esik-Onerisi.md) | `Planned` | Sınıf bazlı eşik önerisi maker-checker onayıyla yürürlüğe girer; politika yokken davranış değişmez. |
| 3 | [41 profil tabanlı kural önerisi ve shadow backfill](Iterasyon-41-Profil-Tabanli-Kural-Onerisi-ve-Shadow-Backfill.md) | `Planned` | Aday kurallar SHADOW backfill raporuyla sunulur; kabul mevcut FR-035 onay akışına girer. |
| 4 | [42 sentetik veriyle kural kanıtı](Iterasyon-42-Sentetik-Veriyle-Kural-Kaniti.md) | `Planned` | Her kural sürümü için kusur bazlı etkinlik kanıtı; sentetik veri üretim kaynağına yazılmaz. |
| 5 | [43 regülasyon eşlemesi ve uyum raporu](Iterasyon-43-Regulasyon-Eslemesi-ve-Uyum-Raporu.md) | `Planned` / `OPEN-BNK-013` bağımlı | Kontrol çerçevesi veri olarak yüklenir; kapsanmayan varlıklar uyumlu sayılmaz. |

### Bağımlılık notları

- **39 → 43:** Uyum raporu, 39C rapor altyapısını kullanır.
- **40 → 41:** Aday kural güveni, takvim sınıfı kapsamasını dayanak alır.
- **41 → 42:** Aday kural, kabul öncesi etkinlik kanıtıyla güçlenir.
- **42 → 43:** Uyum raporu, etkinlik kanıtı olmayan kuralları ayrı işaretler.
- **43** teknik olarak `OPEN-BNK-013` kapanmadan uygulanabilir; üretilen rapor
  karar kapanmadan düzenleyici kanıt sayılamaz.

Tamamlanmış eski yol haritası anlatıları aktif bağlamda tutulmaz; tarihsel
iterasyonlar [arşiv indeksindedir](../../archive/iterations/README.md).
