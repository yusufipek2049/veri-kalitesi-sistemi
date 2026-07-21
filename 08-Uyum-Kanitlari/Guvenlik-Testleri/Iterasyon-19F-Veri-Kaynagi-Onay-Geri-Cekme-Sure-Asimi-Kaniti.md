---
control_ids:
  - BFR-SOD-001
  - BFR-SOD-002
  - BFR-SOD-003
  - BFR-SOD-004
requirement_ids:
  - FR-010
  - FR-014
  - UC-002
  - UC-003
  - NFR-SEC-001
  - NFR-SEC-008
  - NFR-SEC-011
status: TechnicallyVerified
version: iteration-19f-local
executed_at: 2026-07-21
---

# İterasyon 19F Veri Kaynağı Onay Geri Çekme ve Süre Aşımı Kanıtı

## Değişiklik

- İterasyon: 19F - Veri kaynağı aktivasyon onayı geri çekme ve süre aşımı
- Commit/Artifact: `19F — Veri kaynağı onay geri çekme ve süre aşımı`
- Bileşen: `veri_kalitesi.data_sources`, `veri_kalitesi.identity`, `veri_kalitesi.audit`
- Kontrol/Gereksinim: FR-010, FR-014, UC-002, UC-003, NFR-SEC-001/008/011, BFR-SOD-001/002/003/004

## Doğrulama

- Komut: `python3 -m pytest -q`
- Ortam: Python 3.10, yerel prototip, bellek içi ve geçici dosya tabanlı sentetik SQLite verisi
- Sentetik veri seti: Sahipli ve başarılı bağlantı testi bulunan kaynak, hafta sonu/tatil içeren sürümlü iş takvimi, maker/checker/servis context'leri, eski şema ve outbox arızası
- Beklenen: Kayıtlı maker bekleyen isteği geri çekebilir; 3/10 iş günlük zamanlar istek anında saklanır; süresi dolmuş istek karara kapalıdır ve yalnız yetkili kapsam içi servis tarafından `EXPIRED` yapılabilir.
- Gerçekleşen: 731 test geçti. Veri kaynağı hedef grubu 58 testle geçti; 11 yeni takvim, geri çekme, süre aşımı, yetki, migration ve teknik hata vakası başarılı oldu.
- Sonuç: PASS

Ek kontroller:

- `python3 -m mypy 03-Backend/src 06-Testler`: PASS, 109 kaynak dosya
- `python3 -m ruff check .`: PASS
- Değişen Python dosyalarının Ruff format kontrolü: PASS
- `python3 -m compileall -q 03-Backend/src 06-Testler`: PASS
- Hassas desen incelemesi: Audit özetlerinde secret referansı, bağlantı yapılandırması, owner veya maker kimliği ve karar gerekçesi bulunmuyor.

## Güvenlik

- Güven sınırı: Geri çekme ve sona erdirme serbest aktör/rol/scope kabul etmez; güvenilir, geçerli ve sürümlü `ActorContext` ister.
- Görevler ayrılığı: Yalnız kayıtlı maker geri çekebilir; normal kullanıcı veya rol/kapsam dışı servis süre aşımı işletemez.
- Süre politikası: Hedef 3, otomatik sona erme 10 iş günüdür. Zamanlar istek anında sürümlü takvimle hesaplanıp tarihsel kayıtta tutulur.
- Tarihsel koruma: `WITHDRAWN` ve `EXPIRED` terminal durumları silinmez; kaynak `TEST_SUCCEEDED` kalırken aynı revizyon için yeni istek oluşturulabilir.
- Audit atomikliği: Durum geçişi ve redakte audit outbox aynı transaction'dadır; stage arızasında istek `PENDING` kalır.
- Veri minimizasyonu: Audit yalnız teknik istek/revizyon, politika/takvim sürümü ve durum alanlarını taşır; gerekçe domain kaydında kalır.
- Teknik hata ayrımı: Geçersiz politika/takvim ve audit yazma arızası, veri kalitesi sonucu üretilmeden ayrı hata yolunda kapanır.
- Geri alma: Zamanlı politika veya takvim kaldırıldığında yeni süreli istekler fail-closed durur; mevcut terminal geçmiş değiştirilmez.
- Kalan risk: Gerçek banka tatil takvimi kaynağı, banka onaylı maker/checker/worker rol kodları, üretim worker zamanlaması/alarmı ve LDAP eşlemesi açıktır.

## Onaylar

- Teknik doğrulayan: Codex teknik uygulama ajanı
- Bilgi güvenliği: ComplianceReviewRequired
- İç kontrol: ComplianceReviewRequired
- Veri yönetişimi: ComplianceReviewRequired
- Hukuk/uyum: ComplianceReviewRequired

Bu kanıt teknik uygulama sonucudur; BDDK/KVKK uyumu veya banka onayı anlamına gelmez.
