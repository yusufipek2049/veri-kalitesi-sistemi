---
control_ids:
  - BFR-EXT-001
  - BFR-EXT-002
  - BFR-EXT-003
requirement_ids:
  - FR-071
  - FR-084
  - FR-087
  - AC-019
  - RULE-011
  - NFR-REL-005
  - NFR-REL-006
status: TechnicallyVerified
version: 6b53c53
executed_at: 2026-07-17
---

# İterasyon 23A ServiceNow Veri-Minimum Ticket Kanıtı

## Değişiklik

- İterasyon: 23A - ServiceNow veri-minimum adaptör sözleşmesi ve idempotent ticket oluşturma
- Commit/Artifact: `6b53c53` (`origin/main`)
- Bileşen: `veri_kalitesi.servicenow`, `veri_kalitesi.audit`, `veri_kalitesi.identity`
- Kontrol/Gereksinim: FR-071, FR-084, FR-087, AC-019, RULE-011, NFR-REL-005/006 ve BFR-EXT-001/002/003 alt kapsamı

## Doğrulama

- Komut: `PYTHONPATH=03-Backend/src python3 -m pytest -q`
- Ortam: Python 3.10.12, yerel prototip, bellek içi SQLite, fake ServiceNow adaptörü ve sentetik UUID referansları
- Sentetik veri seti: Güvenilir/güvenilmez aktörler, politika dışı issue, allowlist ihlali, 100 replay, payload çakışması, adaptör/audit arızaları
- Beklenen: Yalnız güvenilir standart servis context'i ve veri-minimum projeksiyon ticket üretir; aynı issue/idempotency tekrarında tek ticket kalır.
- Gerçekleşen: 398 test geçti; 18 yeni ServiceNow test vakası eklendi.
- Sonuç: PASS

Ek kontroller:

- `ruff check 03-Backend/src 06-Testler`: PASS
- Değişen altı dosyada `ruff format --check ...`: PASS
- `python3 -m compileall -q 03-Backend/src 06-Testler`: PASS
- ServiceNow paketi ve testinde `mypy --follow-imports=skip ...`: PASS
- Tam depo format kontrolü, değişiklik dışındaki dört eski dosyanın biçim farkı nedeniyle PASS değildir.
- Tam mypy kontrolü, değişiklik dışındaki dokuz dosyada 29 mevcut hata nedeniyle PASS değildir.

## Güvenlik

- Güven sınırı: Ticket yalnız güvenilir, geçerli, ayrıcalıksız `SERVICE` context'ı ve `SERVICENOW_TICKET_PRODUCER` rolüyle oluşturulur.
- Veri minimizasyonu: Dış istek sabit issue referansı, olay turu, öncelik, opak detay referansı, correlation ve özetlenmiş istemci anahtarıyla sınırlıdır; serbest metin ve ham kayıt alanı yoktur.
- Fail-closed: Yetki, export politikası, projeksiyon ve audit redaksiyon politikası dış çağrı öncesi doğrulanır.
- Teknik hata ayrımı: Adaptör kimlik doğrulama, hız sınırı, geçici ve kalıcı hata sınıfları kalite sonucuna dönüştürülmez; ham hata gövdesi saklanmaz.
- Atomiklik: Yerel link, append-only geçmiş ve audit outbox aynı SQLite transaction'ındadır; audit-stage arızasında yerel yazım rollback olur.
- Idempotency: 100 tekrar tek ticket/link/geçmiş/audit üretir; aynı anahtarın farklı payload ile kullanımı çakışmadır.
- Maker-checker etkisi: Otomatik ticket oluşturma kritik konfigrasyon onayı değildir; servis hesabı ve banka alan politikası `ComplianceReviewRequired` kalır.
- Geri alma: Adaptör bağlantısı pasifleştirilerek yeni ticket oluşturma durdurulabilir; mevcut append-only link/geçmiş silinmez ve kaynak veri sistemlerine yazım yapılmaz.
- Kalan risk: Gerçek endpoint/TLS/credential, retry/backoff, durum senkronizasyonu, HTTP/UI ve `OPEN-BNK-009` kapsam dışıdır.

## Onaylar

- Teknik doğrulayan: Codex teknik uygulama ajanı
- Bilgi güvenliği: ComplianceReviewRequired
- Veri yönetişimi: ComplianceReviewRequired
- İç kontrol: ComplianceReviewRequired
- Hukuk/uyum: ComplianceReviewRequired

Bu kanıt teknik uygulama sonucudur; BDDK/KVKK uyumu veya banka onayı anlamına gelmez.
