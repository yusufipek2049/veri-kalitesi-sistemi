---
iteration: 36A1
status: TechnicallyVerified
completed_at: 2026-07-23
decision_reference: USER-DECLARATION-2026-07-23-PG-MIG-004-FORWARD-ONLY-OTHERS-RECOMMENDED
---

# İterasyon 36A1 — PostgreSQL Kalıcılık Temeli

## Amaç

PostgreSQL-only hedef için ortak SQLAlchemy 2 transaction sınırını, yalnız ileri
Alembic baseline'ını ve SQLite fallback içermeyen ilk scope filtreli issue
envanteri repository'sini oluşturmak.

## Gereksinim ve Karar Bağlantıları

- `FR-064–FR-070`
- `UC-013`, `UC-014`
- `NFR-MNT-001`, `NFR-MNT-004`, `NFR-MNT-006`
- `NFR-REL-006`
- `PG-MIG-001–005`

## Kabul Sonuçları

| Kabul ölçütü | Sonuç |
| --- | --- |
| SQLite repository/test kullanımları envanterlenir. | Karşılandı; kalıcı repository grupları ve başlangıç sayımı kaydedildi. |
| Ortak SQLAlchemy 2 session/transaction sınırı oluşturulur. | Karşılandı; yalnız PostgreSQL engine kabul edilir. |
| `data_quality.dq` Alembic baseline hazırlanır. | Karşılandı; offline SQL üretimi şema, sürüm tablosu ve issue tablolarını doğru sırada üretir. |
| Migration yalnız ileri çalışır. | Karşılandı; `downgrade` fail-closed hata verir. |
| PostgreSQL test izolasyonu hazırlanır. | Karşılandı; opt-in test benzersiz şema ve dış transaction rollback kullanır. |
| İlk issue kalıcılığı PostgreSQL'e taşınır. | Kısmen karşılandı; ana şema ve salt okunur envanter taşındı. Mutasyon, audit outbox yayınlama ve tarihsel aktarım `36A2` kapsamındadır. |
| Taşınan issue yolunda SQLite fallback bulunmaz. | Karşılandı; `PostgreSQLIssueRepository` yalnız SQLAlchemy PostgreSQL session factory alır. |
| Secret repository'ye yazılmaz. | Karşılandı; bağlantı yalnız ortam ayarından alınır ve güvenli URL gösterimi parolayı maskeler. |

## Güvenlik ve Veri Etkisi

- Kaynak sistemlere yazma eklenmedi.
- Testler yalnız sentetik UUID ve veri-minimum issue alanları kullanır.
- Bağlantı secret'ı kod, migration, Markdown veya test çıktısına yazılmaz.
- Bu artım banka onayı, üretim uygunluğu veya tam PostgreSQL cutover sonucu
  değildir.

## Çalıştırılan Kontroller

- `pytest -q`: `1067 passed, 3 skipped`
- `mypy 03-Backend/src`: 131 kaynak dosyada sıfır hata
- `ruff check .`
- `ruff format --check .`
- `python3 -m compileall -q 03-Backend/src`
- Alembic offline `upgrade head --sql`
- `28A-v1`: 546 dosyada sıfır secret bulgusu
- `git diff --check`

Üç atlamanın ikisi önceden var olan, biri bu iterasyonda eklenen opt-in gerçek
PostgreSQL entegrasyon testidir. Mevcut WSL oturumunda PostgreSQL portu ve Docker
Desktop WSL entegrasyonu erişilebilir olmadığı için bu iterasyonda canlı
migration çalıştırılmamıştır.

## Kalan 36A Kapsamı

`36A2`; issue yaşam döngüsü yazımlarını, geçmiş/çözüm/doğrulama/ilişki
kayıtlarını ve audit outbox'ı aynı PostgreSQL transaction'ına taşıyacak;
idempotent SQLite aktarımını doğrulayacak ve issue domainindeki SQLite runtime
yolunu kaldıracaktır. Diğer domainlerin seçici taşınması sonraki ayrı
PostgreSQL dilimleridir.
