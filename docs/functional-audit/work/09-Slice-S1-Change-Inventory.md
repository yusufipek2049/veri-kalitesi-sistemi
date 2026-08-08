---
type: functional-audit-work
stage: "09 — Düzeltilmiş S1 Teknik Planı"
scope: slice-s1-corrected-technical-plan
inputs:
  - 08-First-Slice-Decision.md
  - 07-Implementation-Waves.md
  - ../04-Functional-Gap-Inventory.md
  - ../06-API-Inventory-and-Gaps.md
  - ../10-Roles-and-Permissions.md
  - ../14-Independent-Code-Verification.md
project: Veri Kalitesi İzleme ve Skorlama Sistemi
branch: agent/36h1-persistent-job-core
created_at: 2026-08-05
revised_at: 2026-08-05
---

# 09 — S1 Düzeltilmiş Teknik Planı

> `08-First-Slice-Decision.md` ilk dilim olarak S1'in veri kaynağı komut ailesini
> seçti. Bu belge, ilk değişiklik envanterinin bağımsız kod doğrulamasında bulunan
> hataları gideren ve uygulanmadan önce dondurulacak teknik plandır.
>
> Bu aşamada kod yazılmaz. Bu plan yalnız ileride yapılacak kaynak, migration,
> frontend, composition ve test değişikliklerini tanımlar.

**Bağlayıcı kararlar:**

1. Çalıştırılabilir bütün uygulama yolları **PostgreSQL-only** olacaktır; runtime
   SQLite veya in-memory audit fallback'i yoktur.
2. Bekleyen aktivasyon talebi ayrı okuma endpoint'iyle değil veri kaynağı
   liste/detail projection'ıyla taşınır.
3. Aktivasyon kararı source-centric değil **request-centric** endpoint'ten verilir.
4. `DataSourceService` API protocol'üne doğrudan enjekte edilmez; ince bir command
   adaptörü kullanılır.
5. Bu dilim tüm production readiness konularını kapatmaz; fakat production-capable,
   PostgreSQL tabanlı ortak composition root'u kurmadan tamamlanmış sayılmaz.

---

## 1. Düzeltilmiş kapsam

### 1.1 Dahil

- `POST /api/v1/data-sources`, bağlantı testi, aktivasyon talebi, aktivasyon
  kararı ve pasifleştirme komutlarının güvenilir `ActorContext` taşıması.
- Create ve connection-test dahil veri kaynağı komutlarında backend role/scope
  authorization; bu plan **identity propagation only** sınırını kabul etmez.
- Mevcut `DataSourceService` state machine ve PostgreSQL repository transaction
  davranışının API'ye bağlanması.
- PostgreSQL-only ortak composition, production ve development giriş noktaları.
- PostgreSQL transactional outbox ve PostgreSQL-backed kalıcı audit ledger/read
  model.
- Bekleyen talep ve backend tarafından hesaplanan `available_actions` projection'ı.
- Request-centric activation decision, passivation gerekçe formu ve güvenli
  secret-reference akışı.
- PostgreSQL migration, gerçek container integration ve gerçek backend E2E.

### 1.2 Kapanan sınır

Bu dilim tamamlandığında GAP-027'nin yalnız **veri kaynağı komut ailesi** kapanır.
Kural ve manuel execution komut aileleri kapanmadığı için GAP-027 bütünü açık kalır.
`13-Implementation-Roadmap.md` içindeki daha geniş DS-01 sonucu bu dilimle tamamen
karşılanmış sayılmaz.

### 1.3 Yeniden kullanılacak çekirdek

| Mevcut sembol | Kanıt | Karar |
|---|---|---|
| `DataSourceService.request_activation` | `data_sources/service.py:390-459` | State machine yeniden kullanılacak |
| `DataSourceService.decide_activation` | `service.py:461-541` | Maker-checker, policy ve revision guard'ları korunacak |
| `DataSourceService.deactivate_data_source` | `service.py:543-586` | Pasifleştirme domain geçişi korunacak |
| `_authorize_activation_actor` | `service.py:1310-1333` | Genel command policy'ye genişletilecek; kopyalanmayacak |
| `PostgreSQLDataSourceRepository` | `data_sources/postgresql_repository.py:347` | Tek runtime data-source repository'si |
| `PostgreSQLTransactionalAudit` | `audit/postgresql_outbox.py:47` | Business write + outbox atomikliği korunacak |
| `DatabaseSettings.from_environment` | `persistence/database.py:33-37` | DSN/schema kaynağı olarak yeniden kullanılacak |
| `DevelopmentActorContextResolver` | `api/identity.py:185` | Yalnız development identity girişinde kullanılacak |

---

## 2. PostgreSQL-only runtime kararı

### 2.1 Runtime sözleşmesi

| Soru | Kesin karar |
|---|---|
| PostgreSQL DSN nereden okunur? | `DATA_QUALITY_DATABASE_URL`; yalnız `postgresql+psycopg` kabul eden mevcut `DatabaseSettings.from_environment()` |
| Şema nereden okunur? | `DATA_QUALITY_DATABASE_SCHEMA`; varsayılan `dq`; bütün repository/outbox/ledger örneklerine açıkça geçirilir |
| Engine/session factory nerede kurulur? | `api/composition.py:create_application`; `create_session_factory(settings.database)` tek kez çağrılır |
| Migration nasıl uygulanır? | API otomatik migration çalıştırmaz; Docker `migrate` one-shot servisi `alembic upgrade head` çalıştırır |
| Migration nasıl doğrulanır? | Startup preflight `schema.alembic_version` değerini Alembic script head ile karşılaştırır |
| PostgreSQL yoksa ne olur? | Startup `SELECT 1`/migration preflight başarısız olur, app oluşturulmaz ve process non-zero kapanır |
| Test PostgreSQL'i nasıl sağlanır? | Docker Compose içindeki ayrı PostgreSQL 16 test servisi; test DSN'i `DATA_QUALITY_POSTGRES_TEST_URL` ile verilir |

### 2.2 Yasaklanan yollar

- `create_development_app()` içinde `SQLiteDataSourceRepository` kurulmaz.
- `SQLiteTransactionalAudit` ve `SQLiteAuditRepository` runtime composition'a
  girmez.
- PostgreSQL DSN yokluğunda `:memory:` veya development store'a dönülmez.
- `session_factory is None` ile adapter seçen branch bulunmaz.
- Production ve development entrypoint'leri `run_dev.py` içindeki hard-coded DSN'i
  kullanmaz.
- SQLite sınıfları tarihsel/domain-unit-test kodunda bu dilimde fiziksel olarak
  silinmek zorunda değildir; fakat hiçbir ASGI/executable composition tarafından
  import veya instantiate edilemez.

### 2.3 Fail-fast preflight

`create_application` route üretmeden önce sırayla:

1. environment settings'i doğrular;
2. PostgreSQL engine/session factory oluşturur;
3. `SELECT 1` ile bağlantıyı sınar;
4. hedef schema'nın varlığını doğrular;
5. `alembic_version == current head` kontrolü yapar;
6. gerekli `data_sources`, `data_source_activation_requests`, `audit_outbox` ve
   `audit_events` tablolarını doğrular;
7. secret resolver ve identity provider yoksa fail-closed kapanır.

Startup preflight migration uygulamaz ve hatayı yutup boş uygulama döndürmez.

---

## 3. Composition root

### 3.1 Ortak katman

Yeni `src/veri_kalitesi/api/composition.py`:

```text
create_application(settings, identity_provider)
├── DatabaseSettings + PostgreSQL preflight
├── SessionFactory
├── PostgreSQLDataSourceRepository
├── PostgreSQLAuditRepository
├── PostgreSQLTransactionalAudit/outbox
├── SecretResolver
├── DataSourceCommandPolicy
├── DataSourceService
├── DataSourceCommandAdapter
├── DataSourceQueryService
├── AuditQueryService
└── create_dashboard_api(...)
```

`create_application` bütün repository, policy ve servis wiring'inin tek sahibidir.
Production ve development fabrikaları bu fonksiyonu tekrar etmez.

### 3.2 Settings

Yeni `api/settings.py:ApplicationSettings` en az şunları taşır:

- `runtime_environment: Literal["production", "development", "test"]`
- `database: DatabaseSettings`
- `migration_check_enabled: bool` — production/development için daima `True`
- `audit_policy_version`
- `data_source_policy_version`
- `actor_policy_version`
- secret provider türü ve yalnız referans/path konfigürasyonu
- production-safe CORS/origin değerleri

Ham DB veya source secret'ları settings repr/log çıktısına girmez.

### 3.3 Giriş noktaları

| Giriş | Dosya | Identity farkı | Veri/audit wiring |
|---|---|---|---|
| Production | `api/production.py:create_production_app` | Enjekte edilen trusted production identity/BFF provider; dev header reddedilir | Ortak PostgreSQL wiring |
| Development | `api/development.py:create_development_app` | `DevelopmentActorContextResolver` ve dev user registry | Aynı ortak PostgreSQL wiring |

`X-Development-User-Id` yalnız development resolver tarafından okunur. Production
entrypoint bu header ile aktör seçmez; header mevcut olsa bile trusted context
üretmez.

Production IdP/SSO entegrasyonunun tamamı bu dilimde çözülmez. Production fabrikası
trusted `identity_provider` olmadan fail-fast davranır; sahte kullanıcı üretmez.

### 3.4 Docker çalıştırma

Planlanan aktif varlıklar:

- `infra/application/Dockerfile`
- `infra/development/compose.yaml`
- `infra/development/runtime-secrets/` için git-ignored örnek yapı

Production-capable ASGI komutu açıkça:

```text
uvicorn veri_kalitesi.api.production:app --host 0.0.0.0 --port 8000
```

Development servisi:

```text
uvicorn veri_kalitesi.api.development:app --host 0.0.0.0 --port 8000
```

Compose sırası `postgres healthy → migrate completed successfully → api` olur.

---

## 4. Command adaptörü

### 4.1 Dosya ve protocol

Yeni dosya:
`src/veri_kalitesi/api/data_source_commands.py`.

`DataSourceCommandAdapter`, `api/app.py` içindeki düzeltilmiş
`DataSourceMutationService` protocol'ünü açıkça uygular. Domain iş kuralı veya
state transition içermez.

### 4.2 Constructor bağımlılıkları

```text
DataSourceCommandAdapter(
    service: DataSourceService,
    query_service: DataSourceQueryService,
    security_audit: AuditSink,
)
```

- `service`: gerçek domain methodlarını ve transaction'ı yürütür.
- `query_service`: mutation commit'inden sonra actor-scope kontrollü güncel source
  projection'ını yeniden okur.
- `security_audit`: reddedilen command olayını ayrı PostgreSQL audit transaction'ına
  yazar.

Secret resolver adaptöre değil `DataSourceService`e composition tarafından verilir;
adaptör yalnız doğrulanmış `secret_reference` değerini command'a taşır.

### 4.3 İmzalar ve domain çağrıları

| Protocol metodu | Domain çağrısı | Dönüş |
|---|---|---|
| `create(*, payload, actor_context)` | `service.create_data_source(actor_context=..., ..., secret_reference=...)` | `DataSourceCommandResult(source, activation_request=None)` |
| `test_connection(*, data_source_id, actor_context)` | `service.test_connection(actor_context=..., data_source_id=...)` | Re-read edilmiş source + test sonucu |
| `request_activation(*, data_source_id, actor_context)` | `service.request_activation(actor_context=..., data_source_id=...)` | Source + yeni pending request |
| `decide_activation(*, activation_request_id, decision, reason_code, actor_context)` | `service.decide_activation(...)` | Source + terminal request + replay bilgisi |
| `passivate(*, data_source_id, reason_code, actor_context)` | `service.deactivate_data_source(...)` | Re-read edilmiş source |

`DataSourceCommandResult` API modeli değildir; adapter'ın veri-minimum application
sonucudur. FastAPI route'u bunu response modeline dönüştürür.

### 4.4 Transaction sınırı

- Business transaction adaptörde açılmaz; `DataSourceService → PostgreSQL repository`
  sınırında source/request/outbox tek transaction'dır.
- Mutation sonrası source re-read yeni read transaction'ıdır.
- Reddedilen command audit'i business transaction değildir ve ayrı append-only
  security audit transaction'ıdır.
- Adaptör domain `AuthorizationError` kodunu HTTP'ye çevirmeden önce security
  audit'i yazar; state machine'i yeniden değerlendirmez.

---

## 5. Endpoint sözleşmeleri

### 5.1 Route tablosu

| Method ve yol | Request | Başarı | Domain komutu |
|---|---|---|---|
| `GET /api/v1/data-sources` | — | `200 DataSourceListResponse` | Scope-filtered query |
| `POST /api/v1/data-sources` | `DataSourceCreateRequest` | `201 DataSourceCommandResponse` | `create` |
| `POST /api/v1/data-sources/{data_source_id}/test` | boş gövde | `200 DataSourceCommandResponse` | `test_connection` |
| `POST /api/v1/data-sources/{data_source_id}/activation` | boş gövde | `201 DataSourceCommandResponse` | `request_activation` |
| `POST /api/v1/data-source-activation-requests/{activation_request_id}/decision` | `DataSourceActivationDecisionRequest` | `200 DataSourceCommandResponse` | `decide_activation` |
| `POST /api/v1/data-sources/{data_source_id}/passivation` | `DataSourcePassivationRequest` | `200 DataSourceCommandResponse` | `passivate` |

### 5.2 Aktivasyon karar modeli

```json
{
  "decision": "APPROVE",
  "reason_code": "VALIDATED"
}
```

- `activation_request_id` yalnız path'ten alınır.
- `decision` regex/enum olarak yalnız `APPROVE|REJECT` kabul eder.
- `reason_code` trim sonrası boş olamaz ve maksimum 120 karakterdir.
- Source ID karar endpoint'inde istemciden alınmaz; request üzerinden çözülür.

### 5.3 Decision idempotency

Idempotency davranışı domain servisinde uygulanır, adaptörde kopyalanmaz:

- İlk geçerli karar request'i terminal duruma geçirir ve audit üretir.
- Aynı `activation_request_id`, aynı checker, aynı decision ve aynı `reason_code`
  tekrar gönderilirse mevcut terminal sonuç `200` ile, `replayed=true` döner; ikinci
  business mutation/audit oluşturulmaz.
- Terminal request'e farklı decision, reason veya checker ile tekrar gelinirse
  `409 DATA_SOURCE_DECISION_CONFLICT` döner.
- Concurrent kararlar repository'nin `WHERE status='PENDING'` optimistic guard'ıyla
  yalnız bir kez commit olur.

### 5.4 Response projection

Liste ve mutation response en az şunları taşır:

```text
data_source_id, name, source_type, status, last_test_at
available_actions
pending_activation_request_id
pending_activation_maker_actor_id
pending_activation_requested_at
pending_activation_expires_at
activation_request_status (mutation response'ta)
replayed (decision response'ta)
```

Connection config, secret reference, username/password ve owner'ın hassas ayrıntısı
liste response'una girmez.

---

## 6. Policy ve authorization

### 6.1 Policy modeli

`data_sources/models.py` içindeki yalnız activation odaklı policy, veri kaynağı
komutlarının ortak policy'si olacak biçimde genişletilir:

```text
DataSourceCommandPolicy
├── version
├── actor_policy_version
├── creator_roles
├── connection_tester_roles
├── activation_requester_roles
├── activation_decider_roles
├── deactivator_roles
├── allowed_actor_types
└── activation timing/calendar alanları
```

Development başlangıç politikası:

| Command | Roller | Scope |
|---|---|---|
| Create | `DATA_STEWARD`, `DATA_OWNER` | Mevcut modelde domain scope taşınmadığı için yalnız `can_view_enterprise=True`; aksi halde fail-closed |
| Connection test | `DATA_STEWARD` | `data_source_id ∈ permitted_source_ids` |
| Activation request | `DATA_STEWARD` | Source scope |
| Activation decision | `DATA_OWNER` | Source scope; maker ≠ checker |
| Passivation | `DATA_OWNER` | Source scope |
| Audit read | `AUDIT_VIEWER` | Ayrı `AuditAccessPolicy` |

`OPERATIONS` repository'nin gerçek registry'sinde bulunmadığı için uydurulmaz.
Eklenmesi ayrı IAM/role-catalog kararıdır.

### 6.2 Create/test servis imzaları

Tercih edilen ve bu plan için bağlayıcı karar uygulanır:

```text
create_data_source(*, actor_context: ActorContext | None, ...)
test_connection(*, actor_context: ActorContext | None, data_source_id: str)
```

Bu metodlar artık yalnız `actor_id` almaz. Ortak authorization helper şu kontrolleri
uygular:

- trusted actor marker ve `ActorType.USER`;
- context `issued_at`/`expires_at`;
- actor policy version;
- command-specific rol;
- actor'ın privileged/break-glass kısıtı;
- test/activation/passivation için source scope;
- create için mevcut `ActorContext` domain scope taşımadığından enterprise create
  yetkisi; domain-scoped create, kalıcı IAM/domain scope dilimine kadar fail-closed.

Dataset scope data-source seviyesindeki bu command'lerde target değildir; sahte bir
dataset kontrolü eklenmez. Domain-scoped create için `permitted_domain_ids` ve
`data_sources.domain_id` eklemek S3a/DS-10 ile birlikte ele alınır.

### 6.3 Policy fail-closed

- Policy yok veya version boşsa servis kurulmaz.
- Role kümelerinden biri boşsa ilgili command izinli sayılmaz; production startup
  validation hatasıyla kapanır.
- Actor policy version uyuşmazlığında hiçbir `available_action` üretilmez ve command
  `403` olur.

---

## 7. Secret/connector akışı

### 7.1 Create request

Frontend/backend create modeli:

```text
name, source_type, host, port, database, schema,
secret_reference, ssl_mode, connect_timeout_seconds,
statement_timeout_ms, connection_parameters
```

- `owner_user_id` gövdeden alınmaz; trusted actor kimliğinden türetilir.
- Raw username, password, token, API key veya private key alanı yoktur.
- `secret_reference` zorunlu ve izinli scheme/prefix ile doğrulanır.
- PostgreSQL için `ssl_mode` varsayılanı `verify-full`; `disable`, `allow`, `prefer`
  kabul edilmez.

### 7.2 Resolver sınırı

Production `create_application` çağrısı gerçek `SecretResolver` enjekte edilmeden
başlamaz. Provider entegrasyonu bu repository dışında ise yalnız protocol/adaptör
sınırı kullanılır; sentinel production çözümü sayılmaz.

Development için yeni, açıkça dev-only mounted-file resolver planlanır:

```text
secret://local/source-a
→ DATA_QUALITY_LOCAL_SECRET_DIR=/run/secrets/data-sources
→ /run/secrets/data-sources/source-a/username
→ /run/secrets/data-sources/source-a/password
```

Reference segment'i allowlist regex ile doğrulanır; path traversal/symlink kaçışı
reddedilir. Docker Compose değerleri environment'a ham secret koymaz, read-only
mounted secret dosyaları kullanır.

### 7.3 Connection test

`DataSourceService.test_connection`:

1. actor role/scope kontrolü yapar;
2. repository'den source'u okur;
3. `secret_reference` değerini resolver'a verir;
4. resolver username/password mapping'i döndürür;
5. `PostgreSQLConnector(SQLAlchemyPostgreSQLDriver())` TLS/read-only testi çalıştırır;
6. sonuç ve audit'i aynı PostgreSQL transaction'ında kalıcılaştırır.

Bulunamayan/erişilemeyen secret `503 DATA_SOURCE_SECRET_UNAVAILABLE`; hatalı
credential ise veri-minimum `TEST_FAILED/AUTHENTICATION` sonucu olur. Secret değeri
log, exception detail, audit summary veya API response'a girmez.

---

## 8. Error mapping

### 8.1 Ayrı command hata modeli

Profile comparison'a özel `DataSourceQueryValidationError` command route'larında
kullanılmaz. Yeni command error modeli:

```json
{
  "code": "DATA_SOURCE_STATE_CONFLICT",
  "detail": "The data source is not in a state that allows this action.",
  "correlation_id": "..."
}
```

Domain hataları stable machine-readable `code` taşır. API, exception metnini dışarı
yansıtmak yerine code için tanımlı güvenli detail kullanır.

### 8.2 Eşleme tablosu

| Domain/altyapı | HTTP | API code |
|---|---:|---|
| `AuthorizationError` | 403 | `DATA_SOURCE_PERMISSION_DENIED` veya güvenli alt kod |
| Maker=checker | 403 | `DATA_SOURCE_MAKER_CHECKER_VIOLATION` |
| `NotFoundError` | 404 | `DATA_SOURCE_NOT_FOUND` / `ACTIVATION_REQUEST_NOT_FOUND` |
| State conflict | 409 | `DATA_SOURCE_STATE_CONFLICT` |
| Revision/optimistic lock | 409 | `DATA_SOURCE_REVISION_CONFLICT` |
| Duplicate pending request | 409 | `DATA_SOURCE_PENDING_ACTIVATION_EXISTS` |
| Request model/input validation | 422 | `DATA_SOURCE_INPUT_INVALID` |
| Domain validation | 422 | `DATA_SOURCE_DOMAIN_VALIDATION_FAILED` |
| `TechnicalError` | 503 | `DATA_SOURCE_SERVICE_UNAVAILABLE` |
| PostgreSQL/SQLAlchemy | 503 | `DATA_SOURCE_PERSISTENCE_UNAVAILABLE` |
| Secret provider erişimi | 503 | `DATA_SOURCE_SECRET_UNAVAILABLE` |
| Audit/outbox publication | 503 | `DATA_SOURCE_AUDIT_UNAVAILABLE` |

State/revision conflict'leri genel `ValidationError` metin eşlemesiyle ayrılmaz;
domain'de typed/code taşıyan conflict hataları tanımlanır.

Outbox publication business commit'ten sonra başarısız olursa outbox `PENDING`
kalabilir. API `503 DATA_SOURCE_AUDIT_UNAVAILABLE` döner ve detail işlemin yeniden
okunması gerektiğini söyler; istemci körlemesine create'i tekrarlamaz. Activation
decision replay'i §5.3 idempotency sözleşmesini kullanır.

---

## 9. Audit davranışı

### 9.1 Başarılı business mutation

- `DATA_SOURCE_CREATED`
- `DATA_SOURCE_CONNECTION_TESTED`
- `DATA_SOURCE_ACTIVATION_REQUESTED`
- `DATA_SOURCE_ACTIVATION_DECIDED`
- `DATA_SOURCE_DEACTIVATED`

Bu event'ler prepared/redacted biçimde business row değişikliğiyle aynı PostgreSQL
transaction'ında `audit_outbox`a stage edilir. Transaction rollback olursa event de
rollback olur.

### 9.2 Reddedilen command/security audit

Maker'ın kendi talebini karara bağlama girişimi business transaction üretmez.
`DataSourceCommandAdapter`, domain'in typed authorization kodunu yakalayıp ayrı
PostgreSQL append-only audit transaction'ında şu olayı yazar:

```text
action = DATA_SOURCE_ACTIVATION_DECISION_DENIED
result = DENIED
reason_code = MAKER_CHECKER_VIOLATION
object_id = activation_request_id
```

- Command her durumda reddedilir; audit hatası business işlemi açmaz.
- Security audit başarılıysa API 403 döner.
- Security audit yazılamazsa state yine değişmez ve API 503
  `DATA_SOURCE_AUDIT_UNAVAILABLE` döner.
- Bu event başarılı mutation audit'i veya aynı business transaction'ın parçası diye
  sunulmaz.

### 9.3 PostgreSQL ledger/read model

Mevcut repository'de PostgreSQL audit ledger yoktur; yalnız PostgreSQL outbox ve
SQLite ledger vardır. Bu nedenle yeni:

- `audit/postgresql_repository.py:PostgreSQLAuditRepository`
- `audit_events` PostgreSQL migration'ı

eklenir. Tablo mevcut SQLite ledger'ın veri-minimum/hash-chain alanlarını taşır:
`sequence_no`, prepared event alanları, `previous_event_hash`, `event_hash`.
Append işlemi transaction-scoped advisory lock ile hash zincirini serialize eder;
aynı `event_id` aynı payload ile idempotent, farklı payload ile conflict'tir.

`PostgreSQLTransactionalAudit.publish_pending` bu repository'ye publish eder.
`AuditQueryService` ve `/api/v1/audit/events` aynı PostgreSQL repository'den okur.
Production/development runtime'da SQLite/in-memory ledger yoktur.

### 9.4 Audit endpoint yetkisi

`AuditAccessPolicy.required_role = "AUDIT_VIEWER"` korunur. `DATA_STEWARD` veya
`DATA_OWNER` rolü tek başına audit okuma hakkı vermez. Kabul ve E2E testinde olayları
`dev-audit-viewer` okur.

---

## 10. Frontend davranışı

### 10.1 Backend-provided actions

`DataSourceQueryService` her source projection'ı için `available_actions` üretir.
Hesap girdileri:

- trusted actor role ve source scope;
- source status/revision;
- pending activation request;
- pending request maker kimliği;
- active command/actor policy version.

Örnek action değerleri:

```text
TEST_CONNECTION
REQUEST_ACTIVATION
APPROVE_ACTIVATION
REJECT_ACTIVATION
PASSIVATE
```

Maker'a kendi pending request'i için approve/reject action verilmez. Frontend
`allowedDataSourceActions(status)` ile state/rol politikası hesaplamaz; yalnız
backend'in action listesini render eder. Direct/stale API çağrısında backend tekrar
authorization uygular.

### 10.2 Pending activation

Liste response'undaki `pending_activation_request_id` frontend modeline
`pendingActivationRequestId` olarak eşlenir. Onay/ret handler'ı source ID değil bu
request ID ile §5.1 karar endpoint'ini çağırır.

### 10.3 Hata yönetimi

`DataSourceApiError` response body'den şunları saklar:

```text
httpStatus, code, detail, correlationId
```

`DataSourcesPage` güvenli code gruplarını ayırır:

- permission/maker-checker;
- validation;
- state veya stale revision conflict;
- missing/unavailable secret;
- connection/persistence unavailable;
- audit/service unavailable.

Server'ın raw exception detail'i gösterilmez. Bilinmeyen code genel mesaj ve
correlation ID ile fail-safe gösterilir.

### 10.4 Passivation dialog

`PASSIVATE` action'ı seçildiğinde dialog açılır. `reason_code` zorunlu; opsiyonel
`comment` yalnız ayrı modelde izin verilirse gönderilir. Reason boşken submit
disabled'dır. 403 ve 409 mesajları ayrı gösterilir.

### 10.5 Create form

Form en az `name`, `source_type`, `host`, `port`, `database`, `schema`,
`secret_reference`, `ssl_mode`, connection/statement timeout alanlarını içerir.
Raw password/username alanı kaldırılır. Owner trusted session'dan gelir; client owner
göndermez. Domain scope modeli bu dilimde bulunmadığından client'tan güvenilmez bir
domain yetki alanı alınmaz.

---

## 11. Veri modeli ve migration

### 11.1 Değişmeyen business tabloları

`data_sources`, `connection_test_results`, `data_source_connection_revisions` ve
`data_source_activation_requests` kolonları activation akışı için yeterlidir.
`DataSourceActivationRequest`in mevcut 13 alanı korunur; yeni activation tablosu veya
kolonu eklenmez.

### 11.2 Yeni migration

Yeni migration mevcut head `20260730_14` üzerine bağlanır. Önerilen revision:
`20260805_15`.

Migration üç düzeltme içerir:

1. Aynı `(data_source_id, data_source_revision)` için tek `PENDING` request partial
   unique index'i.
2. `data_sources.source_type` constraint'inin domain enum'uyla hizalanması:
   `POSTGRESQL`, `MSSQL`, `ORACLE`, `MYSQL`, `CSV`, `EXCEL`, `REST`.
3. PostgreSQL-backed `audit_events` ledger tablosu ve query/integrity index'leri.

Index öncesi duplicate pending preflight vardır. Duplicate bulunursa migration
satır seçip silmez; açık hata ve düzeltme runbook'u ile fail eder. Production data
sessizce birleştirilmez.

### 11.3 Şema tekliği

Migration, data-source repository, audit outbox, audit ledger ve Alembic version
table aynı `ApplicationSettings.database.schema` değerini kullanır. `run_dev.py`
özel `data_quality` şeması tanımlamaz.

---

## 12. Uygulama sırası

1. API contract, policy rolleri, typed domain hata kodları ve decision idempotency
   sözleşmesini dondur.
2. `ApplicationSettings`, PostgreSQL preflight ve ortak composition iskeletini yaz;
   henüz route'u yeni servise yönlendirme.
3. `20260805_15` migration'ını ve PostgreSQL audit repository'sini yaz; gerçek
   container'da `upgrade head` doğrula.
4. Product/development Docker PostgreSQL + migrate + API sırasını kur; hard-coded
   `run_dev.py` DSN'ini kaldır.
5. `DataSourceCommandPolicy` ile create/test/activation/passivation authorization'ı
   domain servisine ekle; mevcut state machine guard'larını koru.
6. PostgreSQL pending request sorgusunu ve backend `available_actions` projection'ını
   ekle.
7. `DataSourceCommandAdapter` ve command-specific error mapping'i ekle.
8. Request-centric decision ve passivation request modelleri/route'larını bağla.
9. Başarılı business audit, denied security audit ve PostgreSQL audit query wiring'ini
   doğrula.
10. Development seed'i yalnız PostgreSQL'e, idempotent ve migration sonrası uygula;
    owner, current revision ve eşleşen successful test önkoşullarını tamamla.
11. Frontend model/API/error/action/passivation/create form değişikliklerini bağla.
12. Unit → PostgreSQL integration → composition → gerçek backend E2E sırasıyla test
    kapılarını çalıştır.
13. Bütün kabul kriterleri geçince development store/readers ve fake audit wiring'ini
    sil.

---

## 13. Test matrisi

| Katman | Zorunlu testler | Gerçek yol şartı |
|---|---|---|
| PostgreSQL | Repository CRUD, pending unique index, migration upgrade, source-type constraint | PostgreSQL 16 Docker container; skip kabul kriteri değildir |
| Composition | SQLite instantiate edilmez; DSN/schema propagation; migration preflight; PostgreSQL yoksa startup non-zero | `create_application` ve iki entrypoint ayrı sınanır |
| Command adapter | Payload shaping, ActorContext propagation, secret reference, mutation sonrası re-read, typed error propagation | Domain fake kullanılabilir; state machine adaptörde taklit edilmez |
| Endpoint | Request ID approve/reject, invalid decision, missing reason, 404, 409 state/revision, 422, 503 | FastAPI + gerçek adapter; yalnız fake mutation store kullanılmaz |
| Authorization | Create role/enterprise scope, test source scope, requester/decider/deactivator rolü, expired/policy mismatch, maker=checker | Maker=checker testi hem requester hem decider rolü olan özel test aktörü kullanır |
| Audit | Business write rollback atomikliği, denied security event, PG ledger integrity/query, publication failure | `/audit/events` `dev-audit-viewer` ile okunur |
| Frontend unit | Request ID, server actions, error body parsing, passivation dialog, secret/SSL form | Fetch contract exact path/body assert edilir |
| E2E | Create → test → request → farklı actor approve; passivate; maker self-decision deny; scope deny; audit viewer | Mocked `page.route` kullanılmaz; frontend + ASGI + PostgreSQL container |

### 13.1 Mevcut yanıltıcı testler

- `test_data_source_api.py:test_data_source_write_successful_activate_passivate_flow`
  tek-adım bypass beklentisinden request/decision akışına dönüştürülür.
- `test_rule_api.py:test_fr_031_create_rule_without_dataset_scope_returns_403`
  bu dilimde değiştirilmez; kural command authorization kapsam dışıdır. Yanlış adın
  düzeltilmesi ilgili kural dilimine bırakılır.
- Mevcut Playwright data-source testi GET'i mock'ladığı için yalnız görsel test olarak
  kalır; yukarıdaki gerçek-backend E2E'nin yerine geçmez.

### 13.2 Çalıştırma komutları

```text
docker compose -f infra/development/compose.yaml up -d postgres --wait
docker compose -f infra/development/compose.yaml run --rm migrate
DATA_QUALITY_POSTGRES_TEST_URL=postgresql+psycopg://... python3 -m pytest -q \
  tests/integration/test_postgresql_data_source_persistence.py \
  tests/integration/test_postgresql_audit_repository.py \
  tests/integration/test_application_composition.py
python3 -m pytest -q tests/unit/test_data_source_commands.py \
  tests/unit/test_data_source_api.py
npm --prefix frontend test -- --run src/dataSources
npm --prefix frontend run typecheck
npm --prefix frontend run build
npm --prefix frontend run test:e2e -- data-sources-live.spec.ts
```

---

## 14. Kabul kriterleri

| # | Kriter |
|---|---|
| K1 | Runtime composition yalnız environment DSN'li PostgreSQL kullanır; DSN yok/DB erişilemez/migration eskiyse process fail-fast kapanır |
| K2 | `create_application` production ve development entrypoint'leri tarafından ortak kullanılır; wiring yalnız identity provider'da farklıdır |
| K3 | Production `X-Development-User-Id` ile actor seçmez; development aynı header'ı kontrollü registry ile kullanır |
| K4 | `DataSourceCommandAdapter` düzeltilmiş protocol'ü uygular ve gerçek `DataSourceService` imzalarını çağırır |
| K5 | Create ve test trusted ActorContext, geçerli policy, rol ve uygulanabilir scope olmadan 403 döner |
| K6 | Aktivasyon talebi 201 döner; source `TEST_SUCCEEDED/INACTIVE` kalır ve pending request listede görünür |
| K7 | Karar yalnız request-centric endpoint ve `APPROVE|REJECT` ile verilir; request ID path'ten alınır |
| K8 | Aynı kararın exact replay'i idempotent 200; farklı terminal replay 409'dur |
| K9 | Maker=checker 403'tür, source aktif olmaz ve ayrı `DATA_SOURCE_ACTIVATION_DECISION_DENIED` audit'i oluşur |
| K10 | Role/scope, expired actor, policy mismatch, stale revision ve concurrent decision fail-closed çalışır |
| K11 | Pasifleştirme yalnız backend `PASSIVATE` action'ı ve `DATA_OWNER` rolüyle, zorunlu reason code üzerinden yürür |
| K12 | Business state, activation request ve outbox aynı PostgreSQL transaction'ında; rollback testi bunu doğrular |
| K13 | Audit ledger/read model PostgreSQL-backed'tir ve `/audit/events` yalnız `AUDIT_VIEWER` ile okunur |
| K14 | Liste response'u backend-calculated `available_actions` ve `pending_activation_request_id` taşır; frontend policy hesaplamaz |
| K15 | Create form raw secret taşımaz; `secret_reference` ve TLS doğrulamalı `ssl_mode` gönderir |
| K16 | Error response `code/detail/correlation_id` taşır; 403/404/409/422/503 ayrımı testlidir |
| K17 | Approved source/request/audit yeni app instance'ından yeniden okunur; process reconstruction kalıcılığı kanıtlanır |
| K18 | Gerçek backend E2E iki farklı aktör ve PostgreSQL container üzerinde tamamlanır; mocked E2E kanıt sayılmaz |

S1 yalnız K1-K18 birlikte geçtiğinde tamamlanır.

---

## 15. Kapsam dışı

- Kural oluşturma/sürüm/test/approval/activation command authorization.
- Manuel execution authorization ve worker runtime.
- Kalıcı IAM tabloları, production IdP/SSO provider implementasyonu ve access review.
- `ActorContext.permitted_domain_ids` ile tam domain-scoped source creation; mevcut
  modelde bu taşıyıcı olmadığı için bu dilimde enterprise-scoped create uygulanır.
- `OPERATIONS` rolünün role catalog/registry'ye eklenmesi.
- Activation withdraw ve expiry scheduler/worker endpoint'leri.
- İş takvimi; activation target/expiration alanları bu dilimde `None` kalır.
- SIEM/WORM dış publisher, backup/restore, HA, TLS termination ve tüm production
  operasyon readiness'i.
- Tarihsel audit dokümanlarındaki SQLite anlatımlarının topluca güncellenmesi.
- Repository'deki bütün tarihsel SQLite domain test/sınıflarının fiziksel silinmesi;
  yalnız executable composition'dan çıkarılırlar.

---

## 16. Değişmesi beklenen dosyalar

### 16.1 Yeni

| Dosya | Amaç |
|---|---|
| `src/veri_kalitesi/api/settings.py` | Environment application settings |
| `src/veri_kalitesi/api/composition.py` | Ortak PostgreSQL composition root |
| `src/veri_kalitesi/api/production.py` | Production ASGI entrypoint |
| `src/veri_kalitesi/api/data_source_commands.py` | İnce command adaptörü ve application result |
| `src/veri_kalitesi/audit/postgresql_repository.py` | Kalıcı PG ledger/query repository |
| `alembic/versions/20260805_15_*.py` | Pending unique, source enum ve audit ledger migration'ı |
| `tests/unit/test_data_source_commands.py` | Adaptör contract testleri |
| `tests/integration/test_postgresql_audit_repository.py` | PG ledger/integrity testleri |
| `tests/integration/test_application_composition.py` | PostgreSQL-only/fail-fast composition testleri |
| `frontend/e2e/data-sources-live.spec.ts` | Mock'suz gerçek-backend E2E |
| `infra/application/Dockerfile` | ASGI image/entrypoint |
| `infra/development/compose.yaml` | PostgreSQL, migrate, API ve frontend dev stack |

### 16.2 Değişen

| Dosya | Değişiklik |
|---|---|
| `data_sources/models.py` | `DataSourceCommandPolicy` rol alanları |
| `data_sources/errors.py` | Typed authorization/conflict/technical code'ları |
| `data_sources/service.py` | Create/test ActorContext authorization; decision idempotency; mevcut state machine korunur |
| `data_sources/contracts.py` | Pending request read metodu |
| `data_sources/postgresql_repository.py` | Pending query ve typed PG conflict eşlemesi |
| `data_sources/query.py` | Detail/re-read projection ve backend available actions |
| `data_sources/secrets.py` | Dev-only mounted secret resolver; production protocol korunur |
| `api/app.py` | Protocol, request-centric route, command handler/error response |
| `api/models.py` | Create/decision/passivation/pending/actions response modelleri |
| `api/development.py` | Ortak composition'ı çağıran dev identity wrapper; SQLite/store wiring kaldırılır |
| `api/identity.py` | Gerekli dev test profilleri; production davranışı eklenmez |
| `audit/postgresql_outbox.py` | PG ledger publisher status ve hata propagation |
| `run_dev.py` | Hard-coded DSN/fake ledger kaldırılır veya dev entrypoint'e ince yönlendirme olur |
| `frontend/src/dataSources/model.ts` | Backend actions, pending request ve form modelleri |
| `frontend/src/dataSources/api.ts` | Request-centric karar ve structured error parsing |
| `frontend/src/dataSources/DataSourcesPage.tsx` | Server actions, error UI, passivation dialog, create form |
| `frontend/src/App.tsx` | Yeni handler/result refresh akışı |
| İlgili backend/frontend test ve story dosyaları | §13 matrisi |
| `pyproject.toml` | Yeni runtime bağımlılığı yalnız gerçekten gerekirse; SQLite fallback bağımlılığı eklenmez |

---

## 17. Değişmemesi gereken alanlar

- Activation request'in mevcut 13 business alanı ve status enum'u.
- `request_activation`ın successful-test/owner/current-revision önkoşulları.
- Maker≠checker, policy version, expiry ve stale revision guard'larının anlamı.
- PostgreSQL repository'deki successful decision source+request+outbox atomikliği.
- Trusted ActorContext marker ve fail-closed context validation ilkesi.
- Ayrı pending-read endpoint'i açılmaması.
- Yeni data-source activation approval tablosu eklenmemesi.
- Frontend'in raw secret görmemesi veya göndermemesi.
- Kural ve manual execution dosyaları/testleri.
- Tarihsel SQLite dokümantasyonu ve kapsam dışı domain-unit-test fixture'ları.

---

## 18. Riskler

| Risk | Seviye | Azaltım/çıkış kapısı |
|---|---|---|
| Production identity provider repository dışında/eksik | Yüksek | Production app provider olmadan fail-fast; readiness tamamlandı iddiası yok |
| Existing duplicate pending row migration'ı bloke eder | Yüksek | Preflight + operatör runbook; sessiz veri silme yok |
| Outbox publish 503'ü business commit sonrası oluşabilir | Yüksek | Stable error code, re-read, decision idempotency ve pending outbox operasyon testi |
| Create için gerçek domain scope ActorContext'te yok | Yüksek | Bu dilimde enterprise-scoped create; domain-scoped create fail-closed ve DS-10'a taşınır |
| PostgreSQL audit hash-chain concurrent append yarışı | Yüksek | Advisory transaction lock + concurrency integration testi |
| Dev secret mount hatalı/eksik | Orta | Startup/reference validation; secret test endpoint'te 503; değer loglanmaz |
| Source enum migration mevcut veriyi reddeder | Orta | Migration preflight ile bilinmeyen değerleri raporla; otomatik dönüştürme yok |
| Geniş composition değişikliği komşu domainleri etkiler | Yüksek | Ortak root'u önce wiring testleriyle kur; data-source route cutover'ını sonra yap |
| PostgreSQL testlerinin yeniden skip olması | Yüksek | CI/acceptance kapısında container zorunlu; skip dilimi tamamlamaz |
| UI action listesi stale olabilir | Orta | Backend command authorization her çağrıda tekrarlanır; 409/403 structured handling |

---

## 19. Go/No-Go koşulları

### Uygulamaya başlama kararı

**GO**, yalnız şu tasarım kararları review ile dondurulduğunda:

- PostgreSQL-only ve migration preflight;
- ortak `create_application` sınırı ve production identity injection;
- command adapter protocol/imzaları;
- policy rolleri ve enterprise-scoped create sınırlaması;
- request-centric endpoint ve replay idempotency;
- PostgreSQL audit ledger şeması ve denied-audit semantiği;
- structured error code listesi;
- mounted-secret development sözleşmesi.

Bunlardan biri açık kalırsa implementation için **NO-GO**.

### Dilim kapanış kararı

K1-K18'in tamamı, gerçek PostgreSQL container ve mock'suz data-source E2E ile
kanıtlanmadan dilim **NO-GO/INCOMPLETE** kalır. Production-capable composition'ın
varlığı production readiness'in tamamlandığı anlamına gelmez.

### Codex bulguları kapanış matrisi

| Codex bulgusu | Plan değişikliği | Kapatıldı mı? |
|---|---|---|
| Service/protocol doğrudan uyumsuz | §4 ince `DataSourceCommandAdapter`, gerçek method imzaları ve result contract | Evet — plan düzeyinde |
| SQLite fallback için eksik transactional audit wiring | §2 runtime SQLite yolunu tamamen yasaklar | Evet — plan düzeyinde |
| `deactivator_roles` boş | §6 açık `DATA_OWNER` deactivator policy'si | Evet — plan düzeyinde |
| Decision endpoint request ID taşımıyor | §5 request-centric path | Evet — plan düzeyinde |
| Yanlış `APPROVED/REJECTED` değerleri | §5 yalnız `APPROVE/REJECT` | Evet — plan düzeyinde |
| Maker=checker API testi rol guard'ında erken kalabilir | §13 iki role sahip özel test aktörü | Evet — plan düzeyinde |
| Maker=checker reddi auditlenmiyor | §9.2 ayrı PostgreSQL security audit | Evet — plan düzeyinde |
| Audit ledger in-memory/SQLite ve restart'ta kayıp | §9.3 PostgreSQL audit repository/table | Evet — plan düzeyinde |
| Audit endpoint için yanlış aktör | §9.4 ve §13 `dev-audit-viewer` | Evet — plan düzeyinde |
| Validation handler profile-comparison'a özel | §8 ayrı command error modeli/handler | Evet — plan düzeyinde |
| State ve input validation ayrışmıyor | §8 typed conflict ve 409/422 ayrımı | Evet — plan düzeyinde |
| Source type constraint REST/EXCEL seed/formu reddeder | §11.2 forward constraint migration'ı | Evet — plan düzeyinde |
| Şema `data_quality`/`dq` ayrışıyor | §2 ve §11.3 tek environment schema | Evet — plan düzeyinde |
| Seed owner/current-test önkoşullarını taşımıyor | §12 adım 10 PostgreSQL idempotent seed | Evet — plan düzeyinde |
| Secret sentinel gerçek credential sağlamıyor | §7 secret reference + mounted dev provider + production injection | Evet — plan düzeyinde |
| PostgreSQL formu `ssl_mode` taşımıyor | §7.1 ve §10.5 | Evet — plan düzeyinde |
| Frontend kararı source ID ile veriyor | §10.2 request ID mapping | Evet — plan düzeyinde |
| Frontend role/state policy'sini tekrar hesaplıyor | §10.1 backend `available_actions` | Evet — plan düzeyinde |
| Frontend bütün hataları genelliyor | §10.3 structured error parsing/messages | Evet — plan düzeyinde |
| Passivation reason UI yok | §10.4 zorunlu dialog | Evet — plan düzeyinde |
| Testler yalnız repository/mock yolunu doğruluyor | §13 composition + container + live E2E | Evet — plan düzeyinde |
| Production composition root yok | §3 ortak root + iki entrypoint + açık ASGI komutu | Evet — plan düzeyinde; production readiness bütünü değil |
| Rule API testi bu dilimin dışında | §13.1 ve §15 değişiklik dışı bırakır | Evet — plan düzeyinde |

Bu tablodaki “Evet” kodun yazıldığı anlamına gelmez; yalnız teknik planın ilgili
bulguyu eksiksiz ve uygulanabilir bir değişiklik/test maddesine dönüştürdüğünü
ifade eder.
