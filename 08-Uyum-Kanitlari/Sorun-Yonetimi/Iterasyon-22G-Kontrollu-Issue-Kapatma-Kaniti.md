---
control_ids:
  - BFR-IAM-001
  - BFR-IAM-002
  - BFR-SOD-001
  - BFR-DATA-003
requirement_ids:
  - FR-066
  - FR-069
  - FR-070
  - UC-014
  - RULE-013
  - AC-018
  - NFR-REL-006
status: TechnicallyVerified
version: iteration-22g-local
executed_at: 2026-07-17
---

# İterasyon 22G Kontrollü Issue Kapatma Kanıtı

## Değişiklik

- İterasyon: 22G - başarılı doğrulama bağıyla `VERIFIED -> CLOSED` geçişi
- Commit/Artifact: Yerel çalışma ağacı; bu iterasyonda commit oluşturulmadı
- Bileşen: `veri_kalitesi.issues`, `veri_kalitesi.audit`, `veri_kalitesi.identity`
- Kontrol/Gereksinim: FR-066, FR-069, FR-070, UC-014, RULE-013, AC-018, NFR-REL-006 ve BFR-IAM-001/002, BFR-SOD-001, BFR-DATA-003 alt kapsamı

## Doğrulama

- Komut: `PYTHONPATH=03-Backend/src pytest -q`
- Ortam: Python 3.10.12, yerel prototip, bellek içi SQLite ve sentetik UUID referansları
- Sentetik veri seti: Başarılı kapatma, `RESOLVED` kestirmesi, doğrulama kaydı olmayan `VERIFIED`, eksik/servis/ayrıcalıklı/rolesiz/scope dışı context, tekrar kapatma, doğrulama okuma ve audit-stage arızaları
- Beklenen: Yalnız kalıcı `QUALITY_PASSED` ve skor bağlı doğrulama bulunan `VERIFIED` issue, güvenilir kapsam içi Data Owner/Steward tarafından atomik olarak kapatılır.
- Gerçekleşen: 365 test geçti. Issue hedef grubu 83 testle geçti; 11 yeni test vakası eklendi.
- Sonuç: PASS

Ek kontroller:

- `ruff check 03-Backend/src 06-Testler`: PASS
- `ruff format --check 03-Backend/src/veri_kalitesi/issues 06-Testler/01-Birim/test_issues.py`: PASS
- `python3 -m compileall -q 03-Backend/src 06-Testler`: PASS
- Değişen beş kaynak yüzeyinde `mypy --follow-imports=skip ...`: PASS
- Tam `mypy` kontrolü, değişiklik dışındaki `audit/repository.py`, `identity/sessions.py` ve `identity/ldap.py` dosyalarında aynı 13 mevcut hata nedeniyle PASS değildir.

## Güvenlik

- Güven sınırı: Kapatma isteği doğrulama sonucu, skor, execution veya serbest gerekçe almaz. Servis kalıcı son doğrulama kaydını okur.
- Yetki: Yalnız geçerli, normal USER context'indeki kapsam içi `DATA_OWNER` veya `DATA_STEWARD` kapatma yapabilir. Eksik, servis, ayrıcalıklı, rolesiz ve scope dışı context fail-closed reddedilir.
- Doğrulama bağı: Durum etiketine tek başına güvenilmez. Son append-only doğrulamanın `QUALITY_PASSED` olması ve skor referansı taşıması zorunludur; kapanış geçmişi doğrulama UUID'sine bağlanır.
- Veri minimizasyonu: Audit allowlist'i yalnız eski/yeni durum ve doğrulama sonuç sınıfını tutar; execution, score, scope ve doğrulayan kimliği audit özetine girmez.
- Atomiklik: `CLOSED` durumu, geçmiş ve redakte audit outbox aynı SQLite transaction'ındadır; audit-stage arızasında kapanış rollback olur.
- Teknik hata ayrımı: Doğrulama kaydı yokluğu veya geçersiz durum domain hatası; depo/okuma arızası redakte teknik hatadır. Teknik hata issue'yu kapatmaz.
- Maker-checker etkisi: Kapatma yeni bir çözüm onayı değildir; yalnız 22F'de çözüm sahibinden farklı aktörle tamamlanmış başarılı doğrulamayı tüketir. Banka rol eşleme kararı `ComplianceReviewRequired` kalır.
- Geri alma: `close` çağrı yolu pasifleştirilip önceki 22F davranışına dönülebilir; append-only doğrulama/geçmiş kayıtları silinmez. Kaynak sisteme yazım yoktur.
- Kalan risk: Gerçek adaptörlere bağlantı, kontrollü yeniden açma, ServiceNow, saklama-imha ve HTTP/UI kapsam dışıdır.

## Onaylar

- Teknik doğrulayan: Codex teknik uygulama ajanı
- Bilgi güvenliği: ComplianceReviewRequired
- Veri yönetişimi: ComplianceReviewRequired
- İç kontrol: ComplianceReviewRequired
- Hukuk/uyum: ComplianceReviewRequired

Bu kanıt teknik uygulama sonucudur; BDDK/KVKK uyumu veya banka onayı anlamına gelmez.
