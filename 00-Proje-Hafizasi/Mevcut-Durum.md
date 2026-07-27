---
type: project-memory
status: active
project: Veri Kalitesi İzleme ve Skorlama Sistemi
last_updated: 2026-07-24
---

# Mevcut Durum

## Kanonik Durum

| Alan | Durum | Açık sınır |
| --- | --- | --- |
| Gereksinim/karar | SRS, ADR ve karar kayıtları kanonik; en yeni kesin karar PostgreSQL-only ve güvenilir yazılabilir UI yönüdür. | Banka/uyum onayları açık karar kayıtlarında kalır. |
| Issue kalıcılığı | PostgreSQL transaction, seçici SQLite aktarımı ve issue runtime fallback kaldırma teknik olarak doğrulanmıştır. | Production altyapı/onay ayrı kapıdır. |
| Issue yaşam döngüsü | İnceleme, yeniden atama, çözüm, farklı aktörle doğrulama, kapatma ve aynı başarısızlıkta yeniden açma kod/UI/test yüzeyinde vardır. | PostgreSQL issue mutasyon testleri (2/2) ve tüm entegrasyon paketi (44/44) gerçek PostgreSQL 16.13 üzerinde doğrulanmıştır. |
| Kural/veri kaynağı | PostgreSQL migration/repository ve yazılabilir API/UI yüzeyleri mevcuttur. | Production composition root ve kurumsal rol/politika kanıtı ayrıca doğrulanır. |
| Çalıştırmalar | Manuel başlatma/iptal API'si, PostgreSQL migration/repository ve testler vardır. `PostgreSQLExecutionStartService`/`PostgreSQLExecutionCancelService` adaptörleri ile production cutover tamamlanmıştır. `SQLiteExecutionRepository` runtime export'tan çıkarılmış, yalnız test double olarak doğrudan import ile kullanılır. | Gerçek üretim IdP/secret manager/HA altyapısı ayrı kapıdır. Worker dayanıklılığı (kota, pencere, retry, kalıcı kuyruk) ayrı çalışma paketidir. |
| Frontend | Dashboard ve alan ekranları; güvenilir mutasyon, optimistic locking ve no-persistent-sensitive-draft kuralları uygulanmıştır. | Gerçek IdP/üretim API verisi ve güvenli dışa aktarma açık. |
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

[Güvenli rapor üretimi ve indirme (36G)](../NEXT_STEP.md) — PDF/XLSX/CSV dışa
aktarma (FR-075), zamanlanmış rapor (FR-076), sınıflandırma bazlı indirme
(UI-WRITE-007), DLP/watermark/maker-checker/gerekçe/süre framework'ü, asenkron
iş, audit kaydı; kontrol yokluğunda fail-closed.
