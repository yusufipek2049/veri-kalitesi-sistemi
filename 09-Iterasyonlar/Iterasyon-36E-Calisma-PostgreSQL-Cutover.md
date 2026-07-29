---
iteration: 36E
status: TechnicallyVerified
completed_at: 2026-07-24
decision_reference: USER-DECLARATION-2026-07-23-POSTGRESQL-WRITABLE-UI
---

# İterasyon 36E — Çalıştırma İşlemleri PostgreSQL Migrasyonu

## Amaç

Execution domaininin PostgreSQL migration, repository ve API adaptörleriyle
production cutover'ını tamamlamak; `SQLiteExecutionRepository`'yi runtime export
yolundan çıkararak yalnız test double rolüne indirgemek.

## Kapsam

- PostgreSQL migration baseline (`20260724_04_execution_baseline.py`)
- `PostgreSQLExecutionRepository` ve `PostgreSQLExecutionStartService`/
  `PostgreSQLExecutionCancelService` adaptörleri
- `create_development_app()`'de `session_factory` parametresi ile PostgreSQL
  kullanma yeteneği
- `SQLiteExecutionRepository`'nin `executions/__init__.py` public export'undan
  kaldırılması; test import'larının doğrudan `executions.repository` modülüne
  yönlendirilmesi

## Kanıt

- [PostgreSQL execution repository](../03-Backend/src/veri_kalitesi/executions/postgresql_repository.py)
- [PostgreSQL execution API adaptörleri](../03-Backend/src/veri_kalitesi/api/postgresql_execution.py)
- [Execution migration](../05-Veritabani/alembic/versions/20260724_04_execution_baseline.py)
- [Execution sözleşmesi](../03-Backend/src/veri_kalitesi/executions/contracts.py)
- [Entegrasyon testleri](../06-Testler/02-Entegrasyon/test_postgresql_execution_persistence.py)
- [API birim testleri](../06-Testler/01-Birim/test_execution_api.py)

## Tamamlama Ölçütleri

1. ✅ Production profili `PostgreSQLExecutionRepository` kullanır; geliştirme
   store'u (`DevelopmentExecutionStore`) yalnız `development.py` içinde ve
   `session_factory` verilmediğinde fallback olarak kalır.
2. ✅ `SQLiteExecutionRepository` runtime package export'unda değildir;
   testler doğrudan `executions.repository` modülünden import eder.
3. ✅ Başlatma/iptal, idempotency, optimistic concurrency ve audit/outbox
   aynı PostgreSQL transaction sözleşmesiyle doğrulanmıştır.
4. ✅ Migration sıfırdan ve mevcut şemadan ileri çalışır; downgrade fail-closed
   politikası korunur.
5. ✅ Teknik hata ile kalite başarısızlığı ayrımı, scope/CSRF ve veri-minimum
   hata zarfı negatif testlerle geçer.
6. ✅ Dokümanlarda tek durum anlatımı kalır ve bu kapanış kaydı oluşturulmuştur.

## Kalan Sınırlar

- Gerçek üretim IdP/secret manager/HA altyapısı ayrı kapıdır.
- Worker dayanıklılığı (kota, pencere, retry, kalıcı kuyruk) ayrı çalışma
  paketidir.
- `DevelopmentExecutionStore` geliştirme amaçlı fallback olarak
  `development.py` içinde korunur; üretim deployment'ı `session_factory`
  sağlayarak PostgreSQL kullanır.

## Bağlantılar

- [İterasyon 36 ana planı](Iterasyon-36-PostgreSQL-ve-Yazilabilir-Alan-Ekranlari.md)
- [Bir önceki: 36B5 — Kapatma ve Yeniden Açma](Iterasyon-36B5-Kapatma-ve-Yeniden-Acma.md)
- [Sonraki: 36F — Execution Politika ve Worker Dayanıklılığı](Iterasyon-36F-Execution-Politika-Worker-Dayanikliligi.md)