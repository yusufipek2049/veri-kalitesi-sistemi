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
status: TechnicallyVerified
version: iteration-19e-local
executed_at: 2026-07-20
---

# İterasyon 19E Veri Kaynağı Aktivasyon Maker-Checker Kanıtı

## Değişiklik

- İterasyon: 19E - Veri kaynağı aktivasyonu maker-checker
- Commit/Artifact: `19E — Veri kaynağı aktivasyonu maker-checker`
- Bileşen: `veri_kalitesi.data_sources`, `veri_kalitesi.identity`, `veri_kalitesi.audit`
- Kontrol/Gereksinim: FR-010, FR-014, UC-002, UC-003, NFR-SEC-001, BFR-SOD-001/002/003/004

## Doğrulama

- Komut: `python3 -m pytest -q`
- Ortam: Python 3.10, yerel prototip, bellek içi ve geçici dosya tabanlı sentetik SQLite verisi
- Sentetik veri seti: Sahipli ve başarılı bağlantı testi bulunan CSV kaynağı, farklı maker/checker context'leri, ret, eski revizyon, legacy şema, yetkisiz kullanıcı/servis context'leri ve outbox arızası
- Beklenen: Kaynak yalnız güncel revizyona bağlı bekleyen istek farklı ve yetkili checker tarafından onaylanırsa `ACTIVE` olur; ret, eski revizyon veya audit-stage arızası kaynağı aktive etmez.
- Gerçekleşen: 720 test geçti. Veri kaynağı hedef grubu 47 testle geçti; 10 yeni aktivasyon, yetki, migration ve teknik hata vakası başarılı oldu.
- Sonuç: PASS

Ek kontroller:

- `python3 -m mypy 03-Backend/src 06-Testler`: PASS, 109 kaynak dosya
- `python3 -m ruff check .`: PASS
- Değişen Python dosyalarının Ruff format kontrolü: PASS
- Hassas desen incelemesi: Audit özetlerinde secret referansı, bağlantı yapılandırması ve owner kimliği bulunmuyor.

## Güvenlik

- Güven sınırı: İstek ve karar serbest aktör/rol/scope kabul etmez; güvenilir, geçerli ve sürümlü `ActorContext` ister.
- Görevler ayrılığı: Maker aynı değişikliği checker rolü taşısa veya ayrıcalıklı olsa dahi onaylayamaz.
- Yetki: Maker ve checker rolü ile `permitted_source_ids` kapsamı ayrı ayrı doğrulanır; eksik context, yanlış rol/kapsam, servis hesabı ve süresi dolmuş context fail-closed reddedilir.
- Aktivasyon önkoşulu: Kaynakta Data Owner ve güncel revizyona ait başarılı son bağlantı testi zorunludur.
- Tarihsel koruma: Onay isteği kaynak revizyonuna bağlıdır; ret geçmişi korunur ve aynı revizyon için yeni istek oluşturulabilir. Eski şema revizyon alanına veri kaybetmeden taşınır.
- Audit atomikliği: Onay kararı, `ACTIVE` geçişi ve redakte audit outbox olayı aynı transaction'dadır; stage arızasında istek `PENDING`, kaynak `TEST_SUCCEEDED` kalır.
- Veri minimizasyonu: Audit yalnız teknik istek/revizyon, politika ve durum alanlarını taşır; gerekçe domain kaydında kalır.
- Geri alma: Aktivasyon politikası kaldırıldığında yeni istek/karar fail-closed durur; aktif kaynakların pasife alınması bu iterasyonun kapsamı değildir.
- Kalan risk: Banka onaylı maker/checker rol kodları, gerçek LDAP eşlemesi, kaynak kritiklik sözlüğü, bağlantı güncellemesinde revizyon artırma/onay geçersizleştirme, pasife alma ve kaynak onay isteklerinin süre aşımı/geri çekilmesi açıktır.

## Onaylar

- Teknik doğrulayan: Codex teknik uygulama ajanı
- Bilgi güvenliği: ComplianceReviewRequired
- İç kontrol: ComplianceReviewRequired
- Veri yönetişimi: ComplianceReviewRequired
- Hukuk/uyum: ComplianceReviewRequired

Bu kanıt teknik uygulama sonucudur; BDDK/KVKK uyumu veya banka onayı anlamına gelmez.
