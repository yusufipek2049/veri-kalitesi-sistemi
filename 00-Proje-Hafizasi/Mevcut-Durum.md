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
| Çalıştırmalar | 36E PostgreSQL cutover, 36F kalıcı scheduling/policy, 36H1 kuyruk çekirdeği ve 36H2 iş yürütme yaşam döngüsü `TechnicallyVerified` olarak tamamlanmıştır. | Gerçek üretim IdP, secret manager/PAM, HA PostgreSQL/broker ve SIEM/WORM ayrı kurumsal kapılardır; bağımlılıkları tamamlanmış yeni bir `Next`/`READY` teknik paket yoktur. |
| Raporlama | 36G güvenli PDF/XLSX/CSV üretimi/indirme yüzeyi 36H2 ile kalıcı `REPORT` kuyruğuna bağlandı; istek-içi worker yalnız açık geliştirme modundadır. | Kurumsal DLP/watermark ürün entegrasyonu ayrıdır. |
| Frontend | Dashboard ve alan ekranları; güvenilir mutasyon, optimistic locking ve no-persistent-sensitive-draft kuralları uygulanmıştır. Çalıştırma ve rapor ekranları 36E/36G kapanış kanıtlarıyla uyumludur. | Gerçek IdP/üretim API verisi ve kurumsal DLP/watermark adaptörleri açık. |
| Kurumsal entegrasyon laboratuvarı | ENTERPRISE-LAB-03 ile sentetik Keycloak, yerel secret manager, fake ServiceNow ve SIEM uygulama adaptörleri canlı Compose/container ağında olumlu ve fail-closed negatiflerle `PrototypeVerified`; ENTERPRISE-LAB-01/02 sınırları korunur. | Fake/yerel servisler kurumsal ürün, WORM/HA/DR, `ApprovedByBank` veya production-ready kanıtı değildir. |
| Ürün yetenek listesi | 29 Temmuz 2026 özellik karşılaştırması ve `DQ-CAP-001–015` prototip yönleri kanonik olarak kaydedildi. | Yalnız kalite boyutları ile teknik hata/kalite ihlali ayrımı çekirdekte bütündür; kalan başlıklar [durum matrisindeki](Urun-Yetenek-Durum-Matrisi.md) kısmi/hedef/harici sınırları korur. |
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

ENTERPRISE-LAB-03 yalnız prototip olarak kapanmıştır. Bağımlılıkları tamamlanmış
yeni bir `Next`/`READY` teknik paket yoktur; kalan production readiness başlıkları
[backlogda](Sonraki-Adimlar.md) `ExternalDependency` durumundadır.
