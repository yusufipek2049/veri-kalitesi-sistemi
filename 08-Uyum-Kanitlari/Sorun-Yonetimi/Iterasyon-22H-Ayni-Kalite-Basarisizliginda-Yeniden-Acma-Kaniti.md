---
control_ids:
  - BFR-IAM-001
  - BFR-IAM-002
  - BFR-DATA-003
requirement_ids:
  - FR-064
  - FR-069
  - FR-070
  - UC-014
  - RULE-003
  - RULE-011
  - RULE-013
  - AC-016
  - AC-018
  - NFR-REL-005
  - NFR-REL-006
status: TechnicallyVerified
version: 990faf5
executed_at: 2026-07-17
---

# İterasyon 22H Aynı Kalite Başarısızlığında Yeniden Açma Kanıtı

## Değişiklik

- İterasyon: 22H - aynı kalite başarısızlığıyla `CLOSED -> WAITING_FOR_RESOLUTION` geçişi
- Commit/Artifact: `990faf5` (`origin/main`)
- Bileşen: `veri_kalitesi.issues`, `veri_kalitesi.audit`, `veri_kalitesi.identity`
- Kontrol/Gereksinim: FR-064, FR-069, FR-070, UC-014, RULE-003, RULE-011, RULE-013, AC-016, AC-018, NFR-REL-005/006 ve BFR-IAM-001/002, BFR-DATA-003 alt kapsamı

## Doğrulama

- Komut: `pytest -q`
- Ortam: Python 3.10.12, yerel prototip, bellek içi SQLite ve sentetik UUID referansları
- Sentetik veri seti: Aynı kalite olayı, kapanıştan eski replay, teknik olay, farklı payload, yüz tekrar ve audit-stage arızası
- Beklenen: Yalnız aynı deduplication anahtari/payload ile kapanış anından eski olmayan güvenilir kalite olayı mevcut kapalı issue'yu yeni kayıt oluşturmadan yeniden açar.
- Gerçekleşen: 371 test geçti. Issue hedef grubu 89 testle geçti; 6 yeni test vakası eklendi.
- Sonuç: PASS

Ek kontroller:

- `ruff check 03-Backend/src 06-Testler`: PASS
- Değişen üç dosyada `ruff format --check ...`: PASS
- `python3 -m compileall -q 03-Backend/src`: PASS
- Tam depo format kontrolü, değişiklik dışındaki dört eski dosyanın biçim farkı nedeniyle PASS değildir.
- Tam `mypy` kontrolü, değişiklik dışındaki `audit/repository.py`, `identity/sessions.py` ve `identity/ldap.py` dosyalarında aynı 13 mevcut hata nedeniyle PASS değildir.

## Güvenlik

- Güven sınırı: Yeniden açma yalnız mevcut `ISSUE_PRODUCER` güvenilir servis context'i ve kalıcı deduplication/payload özeti üzerinden çalışır.
- Olay zamanı: Kaynak olay zamanı kapanış güncelleme anından eskiyse sorun kapalı kalır; eski replay kapanış zaman sınırını ileri taşımaz.
- Teknik hata ayrımı: Teknik olay kalite başarısızlığı sayılmaz ve kapalı issue'yu bu akışla yeniden açmaz.
- Veri minimizasyonu: Audit yalnız eski/yeni durum ile olay/tetik turunu tutar; scope ve deduplication değeri audit özetine girmez.
- Atomiklik: Durum, öccurrence sayacı, geçmiş ve redakte audit outbox aynı SQLite transaction'ındadır; audit-stage arızasında tüm yazımlar rollback olur.
- Idempotency: Yüz aynı tekrar tek issue ve tek yeniden açma geçmişi üretir; farklı payload kontrollü çakışma olarak reddedilir.
- Maker-checker etkisi: Otomatik güvenilir olay tüketimi yeni bir insan onayı veya kritik konfigrasyon aktivasyonu değildir; banka onaylı rol/politika kararları `ComplianceReviewRequired` kalır.
- Geri alma: Yeniden açma koşulu pasifleştirilerek önceki tekrar davranışına dönülebilir; append-only geçmiş silinmez ve kaynak sisteme yazım yapılmaz.
- Kalan risk: Yeni/farkli kalite başarısızlığının mevcut issue ile ilişkisi, gerçek adaptörler, ServiceNow, saklama-imha ve HTTP/UI kapsam dışıdır.

## Onaylar

- Teknik doğrulayan: Codex teknik uygulama ajanı
- Bilgi güvenliği: ComplianceReviewRequired
- Veri yönetişimi: ComplianceReviewRequired
- İç kontrol: ComplianceReviewRequired
- Hukuk/uyum: ComplianceReviewRequired

Bu kanıt teknik uygulama sonucudur; BDDK/KVKK uyumu veya banka onayı anlamına gelmez.
