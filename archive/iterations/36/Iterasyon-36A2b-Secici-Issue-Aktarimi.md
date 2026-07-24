---
iteration: 36A2b
status: TechnicallyVerified
completed_at: 2026-07-23
decision_reference: USER-DECLARATION-2026-07-23-PG-MIG-004-FORWARD-ONLY-OTHERS-RECOMMENDED
---

# İterasyon 36A2b — Seçici Issue Aktarımı ve SQLite Kaldırma

## Sonuç

Legacy SQLite issue, geçmiş, çözüm, doğrulama, ilişki ve bekleyen issue audit
outbox kayıtları salt okunur/idempotent biçimde PostgreSQL'e taşındı. Sayaç,
kanonik hash ve foreign key kontrolleri fail-closed çalışır; ürün paketindeki
SQLite issue repository/export yolu kaldırıldı.

## Bağlantılar

`FR-064–FR-070`, `UC-011`, `UC-013`, `UC-014`, `NFR-REL-005`,
`NFR-REL-006`, `NFR-SEC-005`, `NFR-SEC-008`, `NFR-SEC-011`,
`PG-MIG-001–005`.

## Kanıt

- Kod: `03-Backend/src/veri_kalitesi/issues/migration.py`
- Testler: `06-Testler/02-Entegrasyon/test_postgresql_issue_migration.py`,
  `test_postgresql_issue_mutations.py`
- Tarihsel kapanış sonucu: `1072 passed, 2 skipped`; aktarımın ikinci çalışması
  sıfır yeni satır üretmiştir.

## Sınır

Kaynak veritabanı değişmez ve ham issue içeriği rapora/loga yazılmaz. Diğer
SQLite domainleri bu kapanışın kapsamında değildir.
