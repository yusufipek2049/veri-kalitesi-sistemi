---
control_ids:
  - BFR-EXT-001
  - BFR-EXT-002
  - BFR-EXT-003
requirement_ids:
  - FR-087
  - UC-013
  - RULE-011
  - NFR-REL-001
  - NFR-REL-005
  - NFR-REL-006
  - NFR-REL-007
status: TechnicallyVerified
version: 8127e9c
executed_at: 2026-07-17
---

# İterasyon 23C ServiceNow Kalıcı Retry Kuyruğu Kanıtı

## Değişiklik

- İterasyon: 23C - ServiceNow kalıcı retry kuyruğu, claim ve dead-letter
- Commit/Artifact: `8127e9c` (`origin/main`)
- Bileşen: `veri_kalitesi.servicenow`, `veri_kalitesi.audit`, `veri_kalitesi.identity`
- Kontrol/Gereksinim: FR-087, UC-013, RULE-011, NFR-REL-001/005/006/007 ve BFR-EXT-001/002/003 alt kapsamı

## Doğrulama

- Komut: `PYTHONPATH=03-Backend/src python3 -m pytest -q`
- Ortam: Python 3.10.12, yerel prototip, bellek içi SQLite, fake ServiceNow adaptörü ve enjekte edilebilir saat
- Sentetik veri seti: Senkron retry tükenmesi, replay, çift claim, geçici/kalıcı/kimlik hatası, due-time, dead-letter, requeue, yetkisiz worker ve audit-stage arızası
- Beklenen: Tükenmiş geçici istek tek kalıcı veri-minimum job üretir; tek worker claim eder; başarı atomik tamamlar; tükenme silinmeden dead-letter olur ve auditli yeniden işlenebilir.
- Gerçekleşen: 417 test geçti; ServiceNow hedef grubu 37 testle geçti ve 11 yeni vaka eklendi.
- Sonuç: PASS

Ek kontroller:

- `ruff check 03-Backend/src 06-Testler`: PASS
- ServiceNow yüzeyinde `ruff format --check ...`: PASS
- `python3 -m compileall -q 03-Backend/src 06-Testler`: PASS
- ServiceNow paketi ve testinde `mypy --follow-imports=skip ...`: PASS
- Tam depo format kontrolü, değişiklik dışındaki dört eski dosyanın biçim farkı nedeniyle PASS değildir.
- Tam mypy kontrolü, değişiklik dışındaki dokuz dosyada 29 mevcut hata nedeniyle PASS değildir.

## Güvenlik

- Güven sınırı: Worker ve dead-letter requeue yalnız güvenilir, geçerli, ayrıcalıksız SERVICE context'iyle çalışır; user ve privileged service claim öncesi reddedilir.
- Veri minimizasyonu: Job yalnız özetlenmiş istemci anahtarı ve sabit allowlist request alanlarını tutar; issue metni, assignee, scope, ham hata, SQL ve secret saklamaz.
- Teknik hata ayrımı: Geçici hata yeniden planlanır; kimlik/kalıcı/bilinmeyen hata kalite sonucu sayılmaz ve doğrudan dead-letter olur.
- Atomiklik: Enqueue, yeniden planlama, dead-letter, requeue ve başarılı link tamamlama redakte audit outbox ile aynı SQLite transaction'ındadır.
- Idempotency: Aynı issue/anahtar/payload tek job üretir; audit hatası sonrası harici başarı aynı adaptör anahtarıyla tekrarlandığında çift ticket oluşmaz.
- Claim: Due-time sıralı koşullu güncelleme aynı SQLite deposunda tek worker sahipliği sağlar; dağıtık lease/heartbeat iddiası yoktur.
- Maker-checker etkisi: Teknik teslimatın yeniden işlenmesi kritik konfigrasyon onayı değildir; banka rol ve operasyon onayları `ComplianceReviewRequired` kalır.
- Geri alma: Worker durdurularak yeni claim engellenebilir; pending/dead-letter kayıtları silinmez. Retry politikası tek denemeye indirilebilir.
- Kalan risk: Gerçek broker, çoklu süreç lease/heartbeat recovery, kuyruk kapasitesi/saklama, operasyon alarmı, circuit breaker, gerçek ağ/TLS/credential ve `OPEN-BNK-009` kapsam dışıdır.

## Onaylar

- Teknik doğrulayan: Codex teknik uygulama ajanı
- Bilgi güvenliği: ComplianceReviewRequired
- Veri yönetişimi: ComplianceReviewRequired
- İç kontrol: ComplianceReviewRequired
- Hukuk/uyum: ComplianceReviewRequired

Bu kanıt teknik uygulama sonucudur; BDDK/KVKK uyumu veya banka onayı anlamına gelmez.
