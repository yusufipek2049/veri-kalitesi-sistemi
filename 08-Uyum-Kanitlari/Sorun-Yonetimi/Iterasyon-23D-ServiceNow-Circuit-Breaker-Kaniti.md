---
control_ids:
  - BFR-EXT-001
  - BFR-EXT-002
  - BFR-EXT-003
requirement_ids:
  - FR-087
  - UC-013
  - RULE-011
  - NFR-REL-003
  - NFR-REL-005
  - NFR-REL-006
  - NFR-REL-007
status: TechnicallyVerified
version: c910d0c
executed_at: 2026-07-17
---

# İterasyon 23D ServiceNow Circuit Breaker Kanıtı

## Değişiklik

- İterasyon: 23D - ServiceNow yapılandırılabilir circuit breaker
- Commit/Artifact: `c910d0c` (`origin/main`)
- Bileşen: `veri_kalitesi.servicenow`, `veri_kalitesi.audit`, `veri_kalitesi.identity`
- Kontrol/Gereksinim: FR-087, UC-013, RULE-011, NFR-REL-003/005/006/007 ve BFR-EXT-001/002/003 alt kapsamı

## Doğrulama

- Komut: `PYTHONPATH=03-Backend/src pytest -q`
- Ortam: Python 3.10.12, yerel prototip, bellek içi SQLite, fake ServiceNow adaptörü ve enjekte edilebilir saat
- Sentetik veri seti: Beş geçici hata, açık devre, timeout öncesi worker, tek half-open probe, başarılı/geçici probe, kimlik hatası ve audit-stage arızası
- Beklenen: Beş ardıcık geçici hatada devre beş dakika açılır; dış çağrı durur; tek probe başarıyla kapatır veya geçici hatayla yeniden açar; durum ve audit atomik kalır.
- Gerçekleşen: 427 test geçti; ServiceNow hedef grubu 47 testle geçti ve 10 yeni vaka eklendi.
- Sonuç: PASS

Ek kontroller:

- `ruff check 03-Backend/src 06-Testler`: PASS
- ServiceNow yüzeyinde `ruff format --check ...`: PASS
- `python3 -m compileall -q 03-Backend/src 06-Testler`: PASS
- ServiceNow paketi ve testinde `mypy ...`: PASS
- Tam depo format kontrolü, değişiklik dışındaki dört eski dosyanın biçim farkı nedeniyle PASS değildir.
- Tam mypy kontrolü, değişiklik dışındaki dokuz dosyada 29 mevcut hata nedeniyle PASS değildir.

## Güvenlik

- Güven sınırı: Ticket ve worker akışlarındaki mevcut güvenilir, geçerli, ayrıcalıksız SERVICE context sınırı korunur; açık devre bu sınırın arkasında değerlendirilir.
- Veri minimizasyonu: Circuit kaydı yalnız teknik hedef kodu, durum, sayaç ve zamanları; audit ise durum, hata sınıfı ve politika sürümünü tutar. Issue, müşteri, scope, SQL, credential ve ham hata saklanmaz.
- Teknik hata ayrımı: Yalnız geçici ve hız sınırı hataları sayılır. Kimlik, kalıcı, bilinmeyen hata ve başarı kalite sonucu sayılmaz ve ardıcık teknik hata dizisini sıfırlar.
- Atomiklik: OPEN, HALF_OPEN ve CLOSED geçişleri redakte audit outbox ile aynı SQLite transaction'ındadır; audit-stage hatası durum geçişini rollback eder.
- Eşzamanlılık: Koşullu OPEN-to-HALF_OPEN güncellemesi aynı SQLite state deposunda tek probe verir. Dağıtık depo veya çoklu veritabanı iddiası yoktur.
- Maker-checker etkisi: Circuit politika değişikliği bu dilimde runtime konfigürasyonudur; banka onaylı üretim eşikleri ve değişiklik yetkileri `ComplianceReviewRequired` kalır.
- Geri alma: Circuit politikası devre dışı bırakılacaksa worker durdurulur ve önceki sürüm geri yüklenir; pending/dead-letter işleri silinmez. Açık durumun elle değiştirilmesi için bu iterasyon yönetim yüzeyi açmaz.
- Kalan risk: Dağıtık state, gerçek endpoint/TLS/credential, ağ timeout adaptörü, metrik/alarm ve `OPEN-BNK-009` kapsam dışıdır.

## Onaylar

- Teknik doğrulayan: Codex teknik uygulama ajanı
- Bilgi güvenliği: ComplianceReviewRequired
- Veri yönetişimi: ComplianceReviewRequired
- İç kontrol: ComplianceReviewRequired
- Hukuk/uyum: ComplianceReviewRequired

Bu kanıt teknik uygulama sonucudur; BDDK/KVKK uyumu veya banka onayı anlamına gelmez.
