---
control_ids:
  - BFR-SOD-001
  - BFR-SOD-003
  - BFR-SOD-004
  - BFR-AUD-004
requirement_ids:
  - FR-010
  - FR-036
  - FR-037
  - UC-002
  - UC-007
  - UC-008
  - NFR-SEC-001
  - NFR-SEC-008
  - NFR-SEC-011
status: TechnicallyVerified
version: iteration-19h-local
executed_at: 2026-07-21
---

# İterasyon 19H Kontrollü Kaynak Pasifleştirme Kanıtı

## Değişiklik

- İterasyon: 19H - Kontrollü kaynak pasifleştirme ve yeni iş kabulünü engelleme
- Commit/Artifact: `19H — Kontrollü kaynak pasifleştirme`
- Bileşen: `veri_kalitesi.data_sources`, `veri_kalitesi.executions`, `veri_kalitesi.audit`
- Kontrol/Gereksinim: FR-010/036/037, UC-002/007/008, NFR-SEC-001/008/011, BFR-SOD-001/003/004, BFR-AUD-004

## Doğrulama

- Komut: `python3 -m pytest -q`
- Ortam: Python 3.10, yerel prototip, bellek içi sentetik SQLite verisi
- Sentetik veri seti: Aktif ve pasif kaynaklar, maker/checker/deactivator context'leri, yanlış rol/kapsam ve servis context'leri, manuel ve zamanlanmış execution istekleri, audit outbox arızası
- Beklenen: Yalnız güvenilir ve kapsam içi deactivator aktif kaynağı gerekçeyle pasifleştirir; pasif kaynak yeni manuel veya zamanlanmış iş üretmez; çalışan işler değiştirilmez; yeniden aktivasyon maker-checker gerektirir; audit arızasında durum geçişi geri alınır.
- Gerçekleşen: 750 test geçti. Veri kaynağı ve execution hedef gruplarında 117 test geçti; 6 yeni pasifleştirme, yetki, yeniden aktivasyon, audit rollback ve iş reddi vakası başarılı oldu.
- Sonuç: PASS

Ek kontroller:

- `python3 -m mypy 03-Backend/src 06-Testler`: PASS, 109 kaynak dosya
- `python3 -m ruff check .`: PASS
- Değişen Python dosyalarının Ruff format kontrolü: PASS
- `python3 -m compileall -q 03-Backend/src 06-Testler`: PASS
- Hassas desen incelemesi: Audit özeti yalnız kaynak revizyonu, politika sürümü ve durum değerlerini içeriyor; gerekçe, secret referansı, bağlantı yapılandırması, owner veya aktör kimliği özet alanlarına taşınmıyor.

## Güvenlik

- Güven sınırı: Pasifleştirme güvenilir/geçerli `ActorContext`, sürümlü `deactivator_roles` politikası ve kaynak kapsamıyla sınırlandırılır; genel ayrıcalık rol yerine kabul edilmez.
- İş kabul kapısı: Manual ve scheduled execution yalnız `ACTIVE` kaynağı kabul eder. `INACTIVE` kaynak için execution kaydı oluşmaz; zamanı gelen plan sınıflandırılmış teknik olayla pasifleştirilir.
- Mevcut iş koruması: Kaynak pasifleştirme execution deposuna veya çalışan iş durumlarına yazmaz. Çalışan işi tamamlama/iptal etme politikası banka kararı beklediğinden değiştirilmemiştir.
- Yeniden aktivasyon: Pasif kaynak güncel başarılı bağlantı testi korunuyorsa mevcut maker-checker akışından yeniden aktivasyon isteyebilir; ret kaynağı `INACTIVE` bırakır, farklı checker onayı `ACTIVE` yapar.
- Audit atomikliği: `ACTIVE` -> `INACTIVE` geçişi ve redakte audit outbox aynı SQLite transaction'ındadır; outbox-stage arızasında kaynak `ACTIVE` kalır.
- Veri minimizasyonu: Pasifleştirme gerekçesi doğrulanır ancak merkezi audit özetine kopyalanmaz; secret veya ham kaynak verisi üretilmez.
- Geri alma: Pasif kaynak fiziksel olarak silinmez; tarihsel sonuçlar korunur ve yeniden etkinleştirme aynı revizyona bağlı maker-checker akışından yapılır.
- Kalan risk: Banka onaylı deactivator rol kodu ve gerçek LDAP eşlemesi, çalışan işin tamamlanması/iptali politikası, üretim çoklu instance eşzamanlılığı ve operasyon bildirimi açık kalır.

## Onaylar

- Teknik doğrulayan: Codex teknik uygulama ajanı
- Bilgi güvenliği: ComplianceReviewRequired
- İç kontrol: ComplianceReviewRequired
- Veri yönetişimi: ComplianceReviewRequired
- Hukuk/uyum: ComplianceReviewRequired

Bu kanıt teknik uygulama sonucudur; BDDK/KVKK uyumu veya banka onayı anlamına gelmez.
