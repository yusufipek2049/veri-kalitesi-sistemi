---
control_ids:
  - BFR-SOD-001
  - BFR-SOD-003
  - BFR-SOD-004
  - BFR-AUD-004
requirement_ids:
  - FR-008
  - FR-009
  - FR-012
  - UC-003
  - NFR-SEC-001
  - NFR-SEC-005
  - NFR-SEC-008
  - NFR-SEC-011
status: TechnicallyVerified
version: iteration-19g-local
executed_at: 2026-07-21
---

# İterasyon 19G Bağlantı Revizyonu ve Onay Geçersizleştirme Kanıtı

## Değişiklik

- İterasyon: 19G - Bağlantı yapılandırması revizyonu ve onay geçersizleştirme
- Commit/Artifact: `19G — Bağlantı revizyonu ve onay geçersizleştirme`
- Bileşen: `veri_kalitesi.data_sources`, `veri_kalitesi.identity`, `veri_kalitesi.audit`
- Kontrol/Gereksinim: FR-008/009/012, UC-003, NFR-SEC-001/005/008/011, BFR-SOD-001/003/004, BFR-AUD-004

## Doğrulama

- Komut: `python3 -m pytest -q`
- Ortam: Python 3.10, yerel prototip, bellek içi ve geçici dosya tabanlı sentetik SQLite verisi
- Sentetik veri seti: Mevcut çalışan CSV revizyonu, başarılı/başarısız aday dosyaları, bekleyen aktivasyon isteği, yetkisiz kullanıcı/servis context'leri, beklenmeyen bağlayıcı arızası, legacy şema ve outbox arızası
- Beklenen: Aday ayarlar mevcut sürümü değiştirmeden test edilir; başarısız veya teknik testte çalışan sürüm korunur; başarılı testte aday terfi eder ve eski revizyona bağlı bekleyen aktivasyon isteği kullanılamaz.
- Gerçekleşen: 744 test geçti. Veri kaynağı hedef grubu 71 testle geçti; 13 yeni revizyon, yetki, doğrulama, migration ve teknik hata vakası başarılı oldu.
- Sonuç: PASS

Ek kontroller:

- `python3 -m mypy 03-Backend/src 06-Testler`: PASS, 109 kaynak dosya
- `python3 -m ruff check .`: PASS
- Değişen Python dosyalarının Ruff format kontrolü: PASS
- `python3 -m compileall -q 03-Backend/src 06-Testler`: PASS
- Hassas desen incelemesi: Audit özetlerinde bağlantı yapılandırması, dosya yolu, secret referansı, owner, hazırlayan kimliği veya değişiklik gerekçesi bulunmuyor.

## Güvenlik

- Güven sınırı: Aday oluşturma ve test, güvenilir/geçerli `ActorContext`, maker rolü, politika sürümü ve source kapsamıyla sınırlandırılır.
- Sürümlülük: İlk ve sonraki bağlantı yapılandırmaları değişmez tarihsel revizyon kayıtlarıdır; legacy kayıtlar revizyon `1` olarak taşınır.
- Başarısız test garantisi: Sınıflandırılmış aday test başarısızlığında mevcut bağlantı yapılandırması, secret referansı, revizyon, durum ve son başarılı test zamanı değişmez.
- Teknik hata ayrımı: Beklenmeyen bağlayıcı arızası `TechnicalError` üretir; aday `PENDING_TEST`, çalışan kaynak ve eski onay değişmeden kalır.
- Terfi ve görevler ayrılığı: Başarılı aday atomik olarak güncel revizyon olur, kaynak yeniden aktivasyon için `TEST_SUCCEEDED` durumuna alınır ve eski bekleyen aktivasyon isteği `INVALIDATED` olur.
- Audit atomikliği: Aday kaydı veya terfi/onay invalidasyonu ile redakte audit outbox aynı transaction'dadır; stage arızasında tüm değişiklikler geri alınır.
- Veri minimizasyonu: Ham secret saklanmaz; revizyon yalnız secret manager referansı tutar. Audit teknik revizyon, durum ve sayaç alanlarıyla sınırlıdır.
- Geri alma: Başarısız aday çalışan sürüme dokunmaz. Terfi sonrası önceki revizyon tarihsel kayıtta korunur; otomatik geri terfi bu iterasyon kapsamında değildir.
- Kalan risk: Banka onaylı bağlantı güncelleme rolü, gerçek LDAP eşlemesi, üretim migration aracı, eş zamanlı çoklu instance kilitleme ve kontrollü pasife alma açıktır.

## Onaylar

- Teknik doğrulayan: Codex teknik uygulama ajanı
- Bilgi güvenliği: ComplianceReviewRequired
- İç kontrol: ComplianceReviewRequired
- Veri yönetişimi: ComplianceReviewRequired
- Hukuk/uyum: ComplianceReviewRequired

Bu kanıt teknik uygulama sonucudur; BDDK/KVKK uyumu veya banka onayı anlamına gelmez.
