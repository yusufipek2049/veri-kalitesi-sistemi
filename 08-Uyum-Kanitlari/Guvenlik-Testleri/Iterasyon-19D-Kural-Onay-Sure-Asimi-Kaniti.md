---
control_ids:
  - BFR-SOD-001
  - BFR-SOD-003
  - BFR-SOD-004
requirement_ids:
  - FR-035
  - UC-005
  - RULE-001
  - RULE-007
status: TechnicallyVerified
version: iteration-19d-local
executed_at: 2026-07-20
---

# İterasyon 19D Kural Onay Süre Aşımı Kanıtı

## Değişiklik

- İterasyon: 19D - Sürümlü iş takvimiyle kural onay isteği süre aşımı
- Commit/Artifact: `19D — Kural onay isteği süre aşımı`
- Bileşen: `veri_kalitesi.identity`, `veri_kalitesi.rules`, `veri_kalitesi.audit`
- Kontrol/Gereksinim: FR-035, UC-005, RULE-001, RULE-007, BFR-SOD-001/003/004 süre aşımı alt kapsamı

## Doğrulama

- Komut: `python3 -m pytest -q`
- Ortam: Python 3.10, yerel prototip, bellek içi ve geçici dosya tabanlı sentetik SQLite verisi
- Sentetik veri seti: Hafta sonu ve tatil günü içeren sürümlü takvim, 3/10 iş günü penceresi, süresi dolmuş istek, yeniden oluşturma, legacy şema, yetkisiz kullanıcı/servis context'leri ve outbox arızası
- Beklenen: İstek oluşturma anından itibaren hedef ve sona erme zamanları sürümlü takvimle hesaplanır; süresi dolmuş istek onaylanamaz; yalnız yetkili servis hesabı isteği `EXPIRED` yapar; yeni istek geçmişi silmeden oluşturulabilir.
- Gerçekleşen: 710 test geçti. Kural hedef grubu 67 testle geçti; sekiz yeni zamanlama, yeniden oluşturma, yetki, migration ve teknik hata vakası başarılı oldu.
- Sonuç: PASS

Ek kontroller:

- `python3 -m mypy 03-Backend/src 06-Testler`: PASS, 109 kaynak dosya
- `python3 -m ruff check .`: PASS
- `python3 -m ruff format --check` değişen Python dosyaları: PASS
- Hassas desen incelemesi: Yalnız sentetik aktör, takvim ve kural kimlikleri kullanıldı; secret veya ham banka verisi eklenmedi.

## Güvenlik

- Güven sınırı: Süre aşımı işlemi serbest aktör/rol kabul etmez; güvenilir, geçerli ve sürümlü `ActorContext` ister.
- Yetki: Yalnız `SERVICE` türündeki ve politika tarafından verilen süre aşımı rolüne sahip context çalışabilir; tüm hedef dataset kapsamları işlemden önce doğrulanır.
- Negatif aktörler: Eksik context, normal kullanıcı, yanlış servis rolü ve kapsam dışı servis hesabı fail-closed reddedilir.
- Zaman politikası: Hedef 3, otomatik sona erme 10 iş günüdür. İstek zamanı başlangıçtır; takvim sürümü istekle birlikte saklanır.
- Tarihsel koruma: `EXPIRED` terminal kaydı silinmez; aynı RuleVersion için yeni `PENDING` istek oluşturulabilir ve eski karar geçmişi korunur.
- Audit atomikliği: `EXPIRED` durumu ve redakte audit outbox olayı aynı transaction'dadır; stage arızasında istek `PENDING` kalır.
- Veri minimizasyonu: Audit özeti teknik istek/sürüm, politika/takvim sürümü ve durumla sınırlıdır; maker kimliği ve gerekçe audit özetine girmez.
- Geri alma: Süre aşımı worker çağrısı durdurulabilir; bekleyen istekler aktive edilmez. Şema migration'ı mevcut onay geçmişini korur.
- Kalan risk: Gerçek banka iş günü/tatil kaynağı, banka onaylı süre aşımı servis rolü, worker zamanlaması/operasyon alarmı, veri kaynağı aktivasyonu ve legacy maker geçiş prosedürü kapsam dışıdır.

## Onaylar

- Teknik doğrulayan: Codex teknik uygulama ajanı
- Bilgi güvenliği: ComplianceReviewRequired
- İç kontrol: ComplianceReviewRequired
- Veri yönetişimi: ComplianceReviewRequired
- Hukuk/uyum: ComplianceReviewRequired

Bu kanıt teknik uygulama sonucudur; BDDK/KVKK uyumu veya banka onayı anlamına gelmez.
