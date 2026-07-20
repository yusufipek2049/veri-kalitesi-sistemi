---
control_ids:
  - BFR-SOD-001
  - BFR-SOD-002
  - BFR-SOD-003
  - BFR-SOD-004
requirement_ids:
  - FR-035
  - RULE-001
  - RULE-007
status: TechnicallyVerified
version: iteration-19a-local
executed_at: 2026-07-16
---

# İterasyon 19A Kural Maker-Checker Kanıtı

## Değişiklik

- İterasyon: 19A - Kritik kural aktivasyonu maker-checker
- Commit/Artifact: Git deposu bulunmadığı için commit yok; yerel çalışma ağacı
- Bileşen: `veri_kalitesi.identity`, `veri_kalitesi.rules`, `veri_kalitesi.audit`
- Kontrol/Gereksinim: FR-035, RULE-001, RULE-007, BFR-SOD-001-004 kural aktivasyonu alt kapsamı

## Doğrulama

- Komut: `PYTHONPATH=03-Backend/src python3 -m pytest -q`
- Ortam: Python 3.10.12, yerel prototip, bellek içi sentetik SQLite verisi
- Sentetik veri seti: Kritik kural, sentetik maker/checker context, rol/dataset kapsamları, eski kural sürümü ve outbox arızası
- Beklenen: Kritik sürüm güvenilir maker tarafından hazırlanır ve doğrudan aktifleşmez; farklı güvenilir checker onayı gerekir; ret taslağı korur; karar sürüme bağlı ve audit ile atomiktir.
- Gerçekleşen: 190 test geçti. Kural hedef grubu 49 testle geçti. Ön bir yeni maker-checker, migration ve güvenlik testi başarılı oldu.
- Sonuç: PASS

Ek kontroller:

- Değişen dokuz Python dosyasında `python3 -m ruff format --check ...`: PASS
- `python3 -m ruff check 03-Backend/src 06-Testler`: PASS
- `python3 -m compileall -q 03-Backend/src 06-Testler`: PASS
- Hassas desen taraması: PASS; yalnız sentetik kimlik/context değerleri kullanıldı.
- Tam depo format kontrolü, bu iterasyonda değişmeyen 4 eski dosyanın mevcut format farkları nedeniyle PASS değildir.

## Güvenlik

- Güven sınırı: Onay işlemleri serbest actor/rol/scope kabul etmez; issuer tarafından üretilmiş `ActorContext` ister.
- Görevler ayrılığı: Maker ve checker aynı actor ise karar verilmez.
- Hazırlayan bağlantısı: Kritik `RuleVersion` güvenilir maker kimliğini taşır; isteği başka actor açamaz.
- Scope: Her iki aktörün de kural dataset kapsamında olması gerekir.
- Tarihsel koruma: Onay yalnız hedef `RuleVersion` için geçerlidir ve yeni sürüme taşınmaz.
- Audit atomikliği: Onay/ret, gerekli aktivasyon ve redakte outbox olayı aynı transaction'dadır.
- Veri minimizasyonu: Karar gerekçe kodu audit özetine girmez; session açık değeri yerine digest saklanır.
- Kalan risk: Scoring onayı, süre aşımı, geri çekme, banka rol eşlemesi ve acil override bu kanıtın dışındadır.

## Onaylar

- Teknik doğrulayan: Codex teknik uygulama ajanı
- Bilgi güvenliği: ComplianceReviewRequired
- İç kontrol: ComplianceReviewRequired
- Veri yönetişimi: ComplianceReviewRequired
- Hukuk/uyum: ComplianceReviewRequired

Bu kanıt teknik uygulama sonucudur; BDDK/KVKK uyumu veya banka onayı anlamına gelmez.
