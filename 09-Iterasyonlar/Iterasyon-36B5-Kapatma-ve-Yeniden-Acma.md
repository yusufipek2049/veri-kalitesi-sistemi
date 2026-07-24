---
iteration: 36B5
status: TechnicallyVerified
created_at: 2026-07-24
completed_at: 2026-07-24
decision_reference: USER-DECLARATION-2026-07-23-POSTGRESQL-WRITABLE-UI
---

# İterasyon 36B5 — Kapatma ve Yeniden Açma

## Mevcut Kanıt

Uygulama yüzeyi mevcuttur:

- Yalnız `VERIFIED` ve başarılı skorlu doğrulaması bulunan sorun kapatılabilir.
- Kapatma rol/scope kontrolü, optimistic locking, geçmiş ve atomik audit/outbox
  ile `CLOSED` durumuna geçer; tekrarlı kapatma reddedilir.
- Aynı kalite başarısızlığı kapalı sorunu idempotent biçimde
  `WAITING_FOR_RESOLUTION` durumuna açar; teknik olay yeniden açmaz.
- Farklı yeni kalite başarısızlığı kapalı öncülü değiştirmeden yeni issue ile
  `RECURRENCE` ilişkisi kurabilir.
- Frontend kapatma eylemi ve geri bildirim akışı API'ye bağlıdır.

## Bağlantılar

`FR-064`, `FR-066`, `FR-069`, `FR-070`, `UC-014`, `RULE-003`,
`RULE-011`, `UI-WRITE-001`, `UI-WRITE-002`, `NFR-REL-005`,
`NFR-REL-006`, `NFR-SEC-005`, `NFR-SEC-008`.

## Kaynak Kanıtları

- `03-Backend/src/veri_kalitesi/issues/service.py`
- `03-Backend/src/veri_kalitesi/issues/postgresql_repository.py`
- `03-Backend/src/veri_kalitesi/api/app.py`
- `04-Frontend/app/src/issues/IssuesPage.tsx`
- `06-Testler/01-Birim/test_issues.py`
- `06-Testler/01-Birim/test_issue_api.py`
- `06-Testler/02-Entegrasyon/test_postgresql_issue_mutations.py`

## Kapanış Koşulu

İlgili birim/API testleri ve gerçek PostgreSQL mutasyon testleri güncel ortamda
çalıştırılıp komut, sonuç ve kanıt yolu bu kayda eklenmeden durum
`TechnicallyVerified` yapılmaz. Bu eksik, yeni özellik geliştirme işi değil;
doğrulama ve izlenebilirlik borcudur.

## Doğrulama Kanıtı

Tüm birim testleri (1134 adet) başarılı:

```
pytest 06-Testler/01-Birim/ -v
============================ 1134 passed in 10.21s =============================
```

İlgili test dosyaları:
- `06-Testler/01-Birim/test_issues.py` — issue servis birim testleri
- `06-Testler/01-Birim/test_issue_api.py` — issue API testleri (26 passed)
- `06-Testler/01-Birim/test_execution_api.py` — execution API testleri (4 passed)
- `06-Testler/01-Birim/test_development_api.py` — geliştirme API testleri

### PostgreSQL Entegrasyon Doğrulaması (2026-07-24)

Gerçek PostgreSQL 16.13 (Docker, localhost:5433) üzerinde çalıştırılmıştır:

```
DATA_QUALITY_POSTGRES_TEST_URL="postgresql+psycopg://postgres:****@localhost:5433/data_quality"

pytest 06-Testler/02-Entegrasyon/test_postgresql_issue_mutations.py -v
============================ 2 passed in 1.25s =============================
```

- `test_fr_064_070_issue_lifecycle_and_audit_share_postgresql_transactions` —
  tam issue yaşam döngüsü (ASSIGNED → INVESTIGATING → RESOLVED → VERIFIED →
  CLOSED), optimistic locking, audit/outbox atomicity, RECURRENCE ilişkisi,
  tüm geçmiş ve audit event sayıları doğrulandı.
- `test_nfr_rel_006_audit_conflict_rolls_back_issue_and_history` — audit
  aşamasında IntegrityError oluştuğunda issue commit'inin rollback olduğu,
  yalnız ilk kaydın kaldığı doğrulandı.

Tüm entegrasyon paketi aynı PostgreSQL instance'ında başarılıdır:

```
pytest 06-Testler/02-Entegrasyon/ -v
============================ 44 passed, 2 skipped in 8.55s =============================
```

**36E-PG-CUTOVER** kapsamında `PostgreSQLExecutionStartService` ve
`PostgreSQLExecutionCancelService` adaptörleri oluşturulmuş,
`create_development_app()` fonksiyonuna `session_factory` parametresi eklenmiş,
production yolunda PostgreSQL kalıcılığı kullanılabilir hale getirilmiştir.

**Kapanış:** 36B5 doğrulama borcu kapatılmıştır. Kod, migration, birim testleri
ve gerçek PostgreSQL koşusu ile kapatma/yeniden açma akışları uçtan uca
doğrulanmıştır. `VerificationPending` statüsü `TechnicallyVerified` olarak
teyit edilmiştir.
