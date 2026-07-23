---
type: implementation-inventory
area: database
iteration: 36A1
created_at: 2026-07-23
---

# SQLite Kalıcılık Envanteri

Bu envanter `PG-MIG-001–005` kapsamında PostgreSQL-only hedefe domain bazlı
geçişi izler. Dosyada bulunmak, ilgili domainin PostgreSQL'e taşındığı anlamına
gelmez.

## Başlangıç Sayımı

- `03-Backend/src` altında `sqlite3` veya `SQLite` kullanan 59 dosya vardır.
- `06-Testler` altında `sqlite3` veya `SQLite` kullanan 30 dosya vardır.
- Alembic öncesinde uygulama şemasını yöneten sürümlü bir migration dizini
  bulunmamaktadır.

## Kalıcı Repository Grupları

| Domain | Mevcut SQLite yüzeyi | Geçiş durumu |
| --- | --- | --- |
| Audit | `audit/repository.py`, `audit/outbox.py`, `audit/migration.py` | Bekliyor |
| Kimlik ve oturum | `identity/sessions.py`, `identity/throttling.py` | Bekliyor |
| Veri kaynakları | `data_sources/repository.py` | Bekliyor |
| Kural yönetimi | `rules/repository.py` | `36C0` tamamlandı; PostgreSQLRuleRepository ve `rule_tables()` eklendi, `SQLiteRuleRepository` korunuyor |
| Çalıştırma ve zamanlama | `executions/repository.py`, `executions/scheduling.py`, `executions/source_usage_policies.py` | Bekliyor |
| Skorlama | `scoring/repository.py`, `scoring/partial_score_policies.py` | Bekliyor |
| Sorun yönetimi | Ürün paketinde SQLite yüzeyi yok | `36A1–36A2b` tamamlandı; PostgreSQL-only runtime, seçici aktarım doğrulandı |
| Bildirim | `notifications/repository.py` | Bekliyor |
| ServiceNow | `servicenow/repository.py` | Bekliyor |
| Saklama ve arşiv | `retention/repository.py`, `retention/disposal_repository.py`, `retention/archive_recall_repository.py` | Bekliyor |
| Olay müdahalesi | `incident_response/repository.py` | Bekliyor |
| Sentetik veri | `synthetic_data/repository.py` | Bekliyor |

## 36A1 Sonucu

- Ortak SQLAlchemy 2 session/transaction sınırı eklendi.
- `data_quality` veritabanındaki varsayılan `dq` şeması için Alembic baseline
  oluşturuldu.
- Baseline, issue ana kaydı, geçmiş, çözüm, doğrulama, ilişki ve audit outbox
  tablolarını kurar.
- PostgreSQL issue okuyucusu kaynak ve dataset scope'larını bind parametreleriyle
  uygular; bu okuyucuda SQLite fallback yoktur.
- Mevcut SQLite issue mutasyon repository'si bu dilimde kaldırılmamıştır.
  Kaldırma; PostgreSQL transaction içindeki audit outbox, geçmiş ve tüm yaşam
  döngüsü yazımları `36A2` ile tamamlandıktan sonra yapılacaktır.

## Test İzolasyonu

- Birim testleri PostgreSQL ayarı ve transaction sınırını fake double ile
  doğrular.
- Gerçek repository testi `DATA_QUALITY_POSTGRES_TEST_URL` açıkça sağlandığında
  benzersiz geçici şema oluşturur.
- Repository yazımı dış transaction altında savepoint kullanır; test sonunda
  dış transaction geri alınır.
- Migration test şeması test sonunda `CASCADE` ile kaldırılır. Bu davranış
  yalnız izole test şeması içindir; üretim rollback yöntemi değildir.

## 36A2a Sonucu

- Issue oluşturma/tekrar, durum, atama, çözüm, doğrulama, geçmiş ve ilişki
  repository metotları PostgreSQL'e taşındı.
- Aynı deduplication özeti PostgreSQL advisory transaction lock ile
  serileştirilir.
- Issue mutasyonu, geçmiş ve redakte audit outbox aynı transaction içinde
  commit veya rollback olur.
- Ayrı `data-quality-postgres` konteynerinde benzersiz geçici şemalarla üç
  entegrasyon testi çalıştı. Secret ve bağlantı URL'si kalıcı dosyaya veya test
  çıktısına yazılmadı.
- `issues/repository.py` ve package export'u 36A2b ile ürün paketinden
  kaldırılmıştır.

## 36A2b Sonucu

- `SQLiteIssueMigrator`, legacy dosyayı salt okunur açar ve issue ana kaydı,
  geçmiş, çözüm, doğrulama, ilişki ile bekleyen issue audit outbox kayıtlarını
  PostgreSQL'e seçici taşır.
- `ON CONFLICT DO NOTHING` tekrar çalıştırmayı idempotent yapar. Kaynak/hedef
  sayaçları, kanonik hash'ler, foreign key'ler ve kaynak dosya özeti commit
  öncesinde doğrulanır.
- Gerçek PostgreSQL testinde ilk çalışma sekiz satır, ikinci çalışma sıfır yeni
  satır üretti. Hedef payload uyuşmazlığı transaction'ı geri aldı.
- `issues/repository.py` ve package export'u kaldırıldı. Legacy SQLite fixture
  yalnız birim test desteğinde bulunur; runtime veya kalıcı entegrasyon fallback'i
  değildir.
