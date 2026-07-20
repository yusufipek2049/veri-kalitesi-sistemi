---
control_ids:
  - BFR-EXT-001
  - BFR-EXT-002
  - BFR-EXT-003
requirement_ids:
  - FR-087
  - UC-013
  - AC-019
  - NFR-REL-001
  - NFR-REL-005
  - NFR-REL-006
status: TechnicallyVerified
version: 7e24946
executed_at: 2026-07-17
---

# İterasyon 23B ServiceNow Retry ve Backoff Kanıtı

## Değişiklik

- İterasyon: 23B - ServiceNow sınıflandırılmış retry ve kontrollü backoff
- Commit/Artifact: `7e24946` (`origin/main`)
- Bileşen: `veri_kalitesi.servicenow`
- Kontrol/Gereksinim: FR-087, UC-013, AC-019, NFR-REL-001/005/006 ve BFR-EXT-001/002/003 alt kapsamı

## Doğrulama

- Komut: `PYTHONPATH=03-Backend/src python3 -m pytest -q`
- Ortam: Python 3.10.12, yerel prototip, bellek içi SQLite, fake ServiceNow adaptörü ve enjekte edilebilir sleeper
- Sentetik veri seti: 401/kalıcı/bilinmeyen hata, geçici hata dizisi, 429 ve Retry-After, eksik Retry-After, retry tükenmesi, geçersiz politika ve replay
- Beklenen: Yalnız geçici/429 hata en fazla üç toplam denemeyle tekrar edilir; 401 tekrar edilmez; tüm denemeler aynı idempotency kimliğini kullanır.
- Gerçekleşen: 406 test geçti; ServiceNow hedef grubu 26 testle geçti ve 8 yeni vaka eklendi.
- Sonuç: PASS

Ek kontroller:

- `ruff check 03-Backend/src 06-Testler`: PASS
- ServiceNow yüzeyinde `ruff format --check ...`: PASS
- `python3 -m compileall -q 03-Backend/src 06-Testler`: PASS
- ServiceNow paketi ve testinde `mypy --follow-imports=skip ...`: PASS
- Tam depo format kontrolü, değişiklik dışındaki dört eski dosyanın biçim farkı nedeniyle PASS değildir.
- Tam mypy kontrolü, değişiklik dışındaki dokuz dosyada 29 mevcut hata nedeniyle PASS değildir.

## Güvenlik

- Güven sınırı: 23A'nın güvenilir standart servis context'i ve allowlist export politikası değiştirilmedi.
- Veri minimizasyonu: Retry aynı sabit veri-minimum request'i kullanır; ham adaptör hata mesajı, response gövdesi veya credential saklanmaz.
- Teknik hata ayrımı: Yalnız `TEMPORARY` ve geçerli `RATE_LIMIT` tekrar edilir; kimlik, kalıcı ve bilinmeyen hata kalite sonucuna dönüştürülmez ve tekrar edilmez.
- Idempotency: Geçici hata sonrası başarı ve replay tek harici ticket, tek yerel link ve tek audit olayı bırakır.
- Sınırlılık: Politika toplam denemeyi 1-3 aralığında tutar; geçici hata 1 ve 2 saniyelik üstel gecikme, 429 tam Retry-After kullanır.
- Maker-checker etkisi: Retry teknik teslim davranışıdır; kritik konfigrasyon onayı değildir. Banka politika/onaylari `ComplianceReviewRequired` kalır.
- Geri alma: Retry politikası tek denemeye indirilerek senkron tekrar güvenli biçimde pasifleştirilebilir; mevcut link/geçmiş silinmez.
- Kalan risk: Kalıcı retry kuyruğu/DLQ, circuit breaker, gerçek timeout/TLS/credential, durum senkronizasyonu ve `OPEN-BNK-009` kapsam dışıdır.

## Onaylar

- Teknik doğrulayan: Codex teknik uygulama ajanı
- Bilgi güvenliği: ComplianceReviewRequired
- Veri yönetişimi: ComplianceReviewRequired
- İç kontrol: ComplianceReviewRequired
- Hukuk/uyum: ComplianceReviewRequired

Bu kanıt teknik uygulama sonucudur; BDDK/KVKK uyumu veya banka onayı anlamına gelmez.
