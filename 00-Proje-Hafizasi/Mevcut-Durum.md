---
type: project-memory
status: active
project: Veri Kalitesi İzleme ve Skorlama Sistemi
last_updated: 2026-07-29
---

# Mevcut Durum

## Kanonik Durum

| Alan | Durum | Açık sınır |
| --- | --- | --- |
| Gereksinim/karar | SRS, ADR ve karar kayıtları kanonik; en yeni kesin karar PostgreSQL-only ve güvenilir yazılabilir UI yönüdür. | Banka/uyum onayları açık karar kayıtlarında kalır. |
| Issue kalıcılığı | PostgreSQL transaction, seçici SQLite aktarımı ve issue runtime fallback kaldırma teknik olarak doğrulanmıştır. | Production altyapı/onay ayrı kapıdır. |
| Issue yaşam döngüsü | İnceleme, yeniden atama, çözüm, farklı aktörle doğrulama, kapatma ve aynı başarısızlıkta yeniden açma kod/UI/test yüzeyinde vardır. | PostgreSQL issue mutasyon testleri (2/2) ve tüm entegrasyon paketi (44/44) gerçek PostgreSQL 16.13 üzerinde doğrulanmıştır. |
| Kural/veri kaynağı | PostgreSQL migration/repository ve yazılabilir API/UI yüzeyleri mevcuttur. | Production composition root ve kurumsal rol/politika kanıtı ayrıca doğrulanır. |
| Çalıştırmalar | 36E PostgreSQL cutover, 36F kalıcı scheduling/policy ve 36H1 kuyruk çekirdeği tamamlanmıştır. 36H2 iş yürütme yaşam döngüsü (terminal geçiş/retry/deadline/iptal/dead-letter/worker composition) kod yüzeyi eklendi ancak review açık correctness bulguları tespit etti; **VerificationPending** — doğrulanana kadar tamamlanmış sayılmaz. | Gerçek üretim IdP, secret manager/PAM, HA PostgreSQL/broker ve SIEM/WORM ayrı kurumsal kapılardır. 36H2 açık bulguları [NEXT_STEP](../NEXT_STEP.md) sıradaki iştir. |
| Raporlama | 36G güvenli PDF/XLSX/CSV üretimi/indirme yüzeyi 36H2 ile kalıcı `REPORT` kuyruğuna bağlandı; istek-içi worker yalnız açık geliştirme modundadır. | Kurumsal DLP/watermark ürün entegrasyonu ayrıdır. |
| Frontend | Dashboard ve alan ekranları; güvenilir mutasyon, optimistic locking ve no-persistent-sensitive-draft kuralları uygulanmıştır. Çalıştırma ve rapor ekranları 36E/36G kapanış kanıtlarıyla uyumludur. | Gerçek IdP/üretim API verisi ve kurumsal DLP/watermark adaptörleri açık. |
| Production readiness | Hazır değil. | IdP/SSO-MFA, PAM/secret, HA veri/session, broker, SIEM/WORM, ServiceNow, DR ve banka onayları gerekir. |

## Aktif İterasyon Bağlamı

Yalnız [en güncel yedi iterasyon](../09-Iterasyonlar/ITERASYON-INDEX.md) aktiftir.
Önceki kayıtlar [archive/iterations](../archive/iterations/README.md) altında
tarihsel kanıttır; güncel durum için kaynak değildir.

## Doğrulama Baseline'ı

Son belgelenmiş proje sonucu backend `1125 passed, 27 skipped`, frontend `95`
Vitest ve temiz type-check/build'dir. Bu tarihsel baseline 24 Temmuz 2026
oturumunda bağımlılık/servis erişimi nedeniyle bağımsız yeniden üretilememiştir;
aktif işlerde yeni koşu sonucu ayrıca kaydedilmelidir.

## Sıradaki Adım

Bağımlılıkları tamamlanmış `Next`/`READY` teknik paket yoktur. Kalan production
readiness başlıkları [backlogda](Sonraki-Adimlar.md) `ExternalDependency`
durumundadır.
