---
type: project-memory
status: active
project: Veri Kalitesi İzleme ve Skorlama Sistemi
last_updated: 2026-07-27
---

# Mevcut Durum

## Kanonik Durum

| Alan | Durum | Açık sınır |
| --- | --- | --- |
| Gereksinim/karar | SRS, ADR ve karar kayıtları kanonik; en yeni kesin karar PostgreSQL-only ve güvenilir yazılabilir UI yönüdür. | Banka/uyum onayları açık karar kayıtlarında kalır. |
| Issue kalıcılığı | PostgreSQL transaction, seçici SQLite aktarımı ve issue runtime fallback kaldırma teknik olarak doğrulanmıştır. | Production altyapı/onay ayrı kapıdır. |
| Issue yaşam döngüsü | İnceleme, yeniden atama, çözüm, farklı aktörle doğrulama, kapatma ve aynı başarısızlıkta yeniden açma kod/UI/test yüzeyinde vardır. | PostgreSQL issue mutasyon testleri (2/2) ve tüm entegrasyon paketi (44/44) gerçek PostgreSQL 16.13 üzerinde doğrulanmıştır. |
| Kural/veri kaynağı | PostgreSQL migration/repository ve yazılabilir API/UI yüzeyleri mevcuttur. | Production composition root ve kurumsal rol/politika kanıtı ayrıca doğrulanır. |
| Çalıştırmalar | Manuel başlatma/iptal API'si ve 36E PostgreSQL cutover tamamlanmıştır. 36F ile scheduling/source-usage policy repository'leri PostgreSQL'e taşınmış ve SQLite eşleri runtime export'tan çıkarılmıştır. | Gerçek üretim IdP/secret manager/HA altyapısı ayrı kapıdır. Kalıcı kuyrukta lease/heartbeat, worker kaybı toparlama ve dead-letter yaşam döngüsü açık çalışma paketidir. |
| Raporlama | 36G ile güvenli PDF/XLSX/CSV üretimi/indirme, zamanlanmış rapor, politika framework'ü, PostgreSQL repository, API ve frontend ekranı uygulanmıştır. | Kurumsal DLP/watermark ürün entegrasyonu ve kalıcı queue/worker dayanıklılığı ayrıdır. |
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

[Kalıcı iş kuyruğu ve worker dayanıklılığı](../NEXT_STEP.md) — execution ve
raporlama işleri için süreç ömründen bağımsız kuyruk, lease/heartbeat, worker
kaybı toparlama, politika kontrollü kota/pencere/timeout/retry,
iptal/idempotency ve dead-letter/audit yaşam döngüsü.
