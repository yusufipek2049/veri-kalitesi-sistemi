---
type: delivery-backlog
status: active
project: Veri Kalitesi İzleme ve Skorlama Sistemi
last_updated: 2026-07-24
---

# Sonraki Adımlar

Tek uygulanabilir sıradaki paket: [Execution Politika ve Worker Dayanıklılığı](../NEXT_STEP.md).

## Aktif Backlog

| Sıra | İş | Durum | Tamamlanma ölçütü |
| --- | --- | --- | --- |
| 1 | Execution politika ve worker dayanıklılığı | `Next` | Kota, pencere, timeout, retry, iptal ve idempotency sürümlü politikadan/kalıcı kuyruktan çözülür; SQLite scheduling/policy repository runtime export'tan çıkarılır. |
| 2 | 36B5 kapatma/yeniden açma doğrulama kaydı | `Completed` | PostgreSQL issue mutasyon testleri (2/2) ve tüm entegrasyon paketi (44/44) gerçek PostgreSQL 16.13 üzerinde çalıştırıldı; iterasyon kaydı güncellendi. |
| 3 | Güvenli rapor üretimi ve indirme | `Blocked` | DLP, watermark, gerekçe, süreli indirme ve gerektiğinde maker-checker tamamdır; kontrol yokluğunda fail-closed. |
| 4 | Kurumsal production adaptörleri | `ExternalDependency` | IdP, PAM/secret manager, HA veri/session, broker, SIEM/WORM, ServiceNow ve DR kanıtları. |

## Son Yedi İterasyonun Konsolide Çıktısı

Issue domaini PostgreSQL'e taşındı; seçici SQLite aktarımı tamamlandı ve issue
runtime fallback'i kaldırıldı. İnceleme, yeniden atama, korumalı çözüm, farklı
aktörle doğrulama ve kapatma UI/API akışları mevcuttur. Kapatma/yeniden açma için
uygulama kanıtı bulunur; yalnız güncel bağımsız doğrulama/kapanış kaydı eksiktir.

Execution PostgreSQL cutover (36E) tamamlanmıştır: `PostgreSQLExecutionRepository`
production composition root'unda, `SQLiteExecutionRepository` runtime export'tan
çıkarılmıştır. Sıradaki adım execution politika ve worker dayanıklılığıdır.

Tamamlanmış eski backlog ayrıntıları [iterasyon arşivindedir](../archive/iterations/README.md).
