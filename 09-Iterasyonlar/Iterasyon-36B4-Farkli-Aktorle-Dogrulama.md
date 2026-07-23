---
iteration: 36B4
status: TechnicallyVerified
completed_at: 2026-07-23
decision_reference: USER-DECLARATION-2026-07-23-POSTGRESQL-WRITABLE-UI
---

# İterasyon 36B4 — Farklı Aktörle Doğrulama

## Amaç

Çözülen bir sorunun çözümü hazırlayandan farklı güvenilir aktör tarafından
doğrulanması ve `VERIFIED` durumuna geçirilmesi. Backend bu yeteneği 36B3 ile
zaten sağlamıştır; bu iterasyon frontend `verifyIssue()` API fonksiyonunu ve
`IssuesPage` `onVerify` callback'ini bağlayarak uçtan uca doğrulama akışını
tamamlar.

## Gereksinim ve Karar Bağlantıları

- `FR-066`
- `FR-069`
- `UC-014`
- `UI-WRITE-001`
- `UI-WRITE-002`
- `UI-WRITE-003`
- `NFR-SEC-001`
- `NFR-SEC-005`
- `NFR-SEC-007`
- `NFR-SEC-008`
- `NFR-SEC-011`
- `NFR-USA-001–006`

## Kabul Kriterleri

| Kriter | Sonuç |
| --- | --- |
| Doğrulama eylemi yalnız `RESOLVED` durumundaki sorunda, çözümü hazırlayandan farklı aktöre sunulur. | Karşılandı; backend `_issue_actions()` daha önce doğrulanmıştır. |
| `VERIFY` eylemi frontend üç nokta menüsünde görünür ve tıklanabilir. | Karşılandı; `IssuesPage` "Doğrula" menü öğesini gösterir. |
| Doğrulama referans UUID'si zorunludur; boş referansla gönderim engellenir. | Karşılandı; dialog butonu boş referansla devre dışı kalır. |
| İstek sayısal `version` ve CSRF sınırından geçer. | Karşılandı; `verifyIssue()` API fonksiyonu CSRF kanıtı ve sürüm taşır. |
| Eski sürüm hiçbir issue/doğrulama/geçmiş/audit yazımı yapmadan `409 Conflict` üretir. | Karşılandı; backend optimistic locking daha önce doğrulanmıştır. |
| Başarılı doğrulama sonrası sorun listesi güncellenir ve `VERIFIED` durumu gösterilir. | Karşılandı; `App.tsx` `verify` callback'i items listesini günceller. |
| `QUALITY_PASSED` → `VERIFIED`, `QUALITY_FAILED`/`PARTIAL` → `WAITING_FOR_RESOLUTION`, `TECHNICAL_ERROR` → `RESOLVED` korunur. | Karşılandı; backend `record_verification_result()` daha önce doğrulanmıştır. |
| Arayüz açık "Doğrula" eylemi, bekleme ve erişilebilir başarı/hata geri bildirimi sağlar. | Karşılandı; dialog bekleme/başarı/hata durumlarını içerir. |

## Güvenlik ve Veri Etkisi

- Kaynak sisteme yazılmaz; yalnız uygulamanın issue yaşam döngüsü değişir.
- Yetkisiz, kapsam dışı, çözümü hazırlayanla aynı aktör, eski sürümlü ve eksik
  CSRF istekleri fail-closed sonuçlanır.
- Audit olayı veri-minimumdur; doğrulama referansı, secret ve oturum belirteci
  içermez.
- Audit/outbox yazılamazsa issue mutasyonu tamamlanmaz.

## Çalıştırılan Kontroller

- Hedefli issue/API testleri: `127 passed`
- Tam pytest: `1091 passed, 7 skipped`
- Frontend Vitest: `70 passed`
- TypeScript production build: başarılı
- Mypy: 133 kaynak dosyada sıfır hata
- Ruff lint: temiz

Kalan 7 pytest atlaması ayrı sentetik PostgreSQL opt-in profiline aittir.