---
type: functional-audit-work
stage: "21 — DS-09 Değişiklik Envanteri"
scope: slice-ds09-change-inventory
inputs:
  - 20-Seventh-Slice-Decision.md
  - 19-Slice-DS06-Change-Inventory.md
  - 17-Slice-DS05-Change-Inventory.md
  - 07-Implementation-Waves.md
  - ../04-Functional-Gap-Inventory.md
  - ../07-Target-Data-Model.md
  - ../09-State-Machines.md
  - ../13-Implementation-Roadmap.md
project: Veri Kalitesi İzleme ve Skorlama Sistemi
branch: agent/36h1-persistent-job-core
created_at: 2026-08-06
---

# 21 — DS-09 Değişiklik Envanteri

> Seçilen yedinci dilim: **DS-09 — Kalıcı uygulama içi bildirim hattı
> (GAP-007)**. Bu belge değişecek tablo, kolon, servis, endpoint, ekran ve
> testleri gerçek repository yolları ve sembolleriyle belirler. Uygulama veya
> kaynak kod değişikliği içermez.

---

## 1. Envanter özeti

| Katman | Karar |
|---|---|
| Yeni migration | `alembic/versions/20260806_20_notification_delivery.py` |
| Yeni tablolar | `notification_events`, `notification_channels`, `notification_subscriptions`, `notification_deliveries` |
| Değişecek mevcut tablolar | Yok; `data_quality_issues`, `issue_history`, `background_jobs` ve audit tabloları şema değişmeden kullanılır |
| Yeni job type | `NOTIFICATION_DELIVERY`; mevcut `background_jobs`, lease/retry/dead-letter ve worker kullanılır |
| Ana backend değişikliği | Issue transaction'ında canonical event + delivery/job staging → kalıcı worker → IN_APP delivery → scope-safe query/read |
| Endpoint | Sekiz endpoint: gelen kutusu, read, subscription GET/PUT, channel GET/POST, delivery GET/reroute |
| Frontend | Bildirim zili/sayacı, Gelen Kutusu, Tercihler, Kanallar ve Teslimat İzleme |
| Production kanıtı | Gerçek issue/assignment → aynı transaction'da event → durable job → PG delivery → API/UI/read → audit |

Mevcut Alembic head `20260806_19` ve
`api/composition.py:CURRENT_MIGRATION_HEAD = "20260806_19"` değeridir. DS-09
yalnız forward revision 20 ile ilerler; migration 01–19 değiştirilmez.

## 2. Repository kanıtı ve zorunlu plan düzeltmeleri

### 2.1 Doğrudan yeniden kullanılacak yapı

| Repository kanıtı | Mevcut dosya/simge | Envanter kararı |
|---|---|---|
| Canonical event ve veri-minimum doğrulama vardır | `notifications/models.py:NotificationEvent`, `validate_notification_event` | Yeni event domain'i yazılmaz; model production kimlik ve payload sözleşmesine genişletilir |
| Trusted producer/reader kapısı vardır | `notifications/service.py:NotificationService._authorize_actor` | Trusted/expiry/policy-version ve standart USER davranışı korunur |
| Alıcı çözümleme portu vardır | `notifications/service.py:NotificationRecipientResolver` | Kalıcı issue assignee ve subscription resolver bu porta bağlanır |
| Listeleme ve read sahiplik kontrolü vardır | `NotificationService.list_my_notifications`, `mark_read`; `SQLiteNotificationRepository.mark_read` | Başkasının kaydını 404 ile gizleme ve idempotent read korunur |
| Veri-minimum sabit şablonlar vardır | `notifications/service.py:_TEMPLATES` | Serbest title/body persistence eklenmez; API görünümü event type şablonundan üretilir |
| Kanal policy/routing sözleşmesi vardır | `notifications/channel_adapters.py:NotificationChannelPolicy`, `ChannelRoute` | Policy ve routing yeniden kullanılır; proses-içi idempotency log'u production olmaz |
| Issue çağrı noktaları vardır | `issues/service.py:_publish_notification`, `_publish_assignment_notification` | Post-commit çağrı atomik hazırlama/staging yoluna çevrilir |
| Session-aware queue enqueue vardır | `jobs/postgresql_repository.py:PostgreSQLJobQueueRepository.enqueue(..., session=...)` | Yeni queue/outbox kurulmaz; event transaction'ına `NOTIFICATION_DELIVERY` job eklenir |
| Kalıcı worker handler registry'si vardır | `jobs/composition.py:create_persistent_job_runtime` | Yeni handler mevcut map'e eklenir |
| Transactional audit deseni vardır | `audit/postgresql_outbox.py:PostgreSQLTransactionalAudit.stage(..., session=...)` | Event/delivery mutasyonları aynı session'da audit edilir |
| Frontend gerçek API hata durumlarını ayırır | `App.tsx` route state desenleri; feature `api.ts`/`model.ts` yapıları | Bildirim modülü aynı deseni kullanır; production fixture fallback eklenmez |

### 2.2 Mevcut kodla uyuşmayan varsayımlar

1. **Issue ile notification event bugün atomik değildir.**
   `IssueService.create_for_trigger` issue repository transaction'ı ve
   `publish_pending()` tamamlandıktan sonra `_publish_notification` çağırır;
   automatic path notification hatasını yutar. `reassign` de assignment commit
   sonrasında `_publish_assignment_notification` çağırır. DS-09'da yalnız bu
   çağrıyı gerçek PostgreSQL servisine çevirmek yeterli değildir; event/batch
   issue repository'nin açık session'ında stage edilmelidir.

2. **Mevcut service/repository production port'u değildir.**
   `NotificationService.__init__` doğrudan `SQLiteNotificationRepository` ve
   `SQLiteTransactionalAudit` ister. Repository protokolü ve PostgreSQL adapter
   eklenmeden composition root'ta yeniden kullanılamaz.

3. **UUID doğrulaması gerçek kimlik yoluyla uyumsuzdur.**
   `validate_recipient_id` ve event `scope_id` doğrulaması UUID zorunlu tutar.
   Gerçek repository/seed/ActorContext yolu `user-data-steward-01`,
   `source-*`, `dataset-*` gibi bounded `String(128)` kimlikler kullanır. DS-10
   öncesinde sahte UUID üretilmez; alıcı ve scope validator'ları mevcut actor,
   issue ve dataset/source kimlik sözleşmesiyle aynı bounded-reference kuralına
   geçirilir. `recipient_user_id` için `users` FK'si DS-10'a bırakılır.

4. **`UNREAD/READ` delivery state-machine değildir.**
   `notifications/models.py:NotificationStatus` ve SQLite `notifications.status`
   yalnız iki değer taşır. Production `notification_deliveries.status`, hedef
   `PENDING/SENDING/DELIVERED/FAILED/UNDELIVERABLE/REROUTED/READ` durumlarını
   ayrı sahiplikle taşır. Event yaşam döngüsü ile inbox read durumu tek alanda
   birleştirilmez.

5. **In-memory dispatcher production idempotency kanıtı değildir.**
   `NotificationChannelDispatcher._idempotency_log` ve `_dedup_log` restart'ta
   kaybolur; `FakeChannelAdapter` her zaman başarılı sandbox adaptörüdür.
   Routing kuralları korunur fakat idempotency, suppression ve attempt sonucu
   PostgreSQL kayıtlarından çözülür.

6. **Roadmap subscription ekranının okuma endpoint'ini atlamıştır.**
   Yalnız `PUT /users/{id}/notification-subscriptions` mevcut tercihleri ilk
   render'da gösteremez. Aynı resource için scope-safe `GET` de DS-09'a dâhildir.

7. **Haricî kanal provider'ı yoktur.**
   Repository'de EMAIL/MESSAGING/SERVICENOW/JIRA için yalnız fake/sandbox adapter
   vardır. İlk concrete production kanal `IN_APP` olur. Somut provider verilmeden
   haricî kanal `ACTIVE` yapılamaz; fake/no-op başarı üretemez.

8. **`notifications` adlı beşinci production tablosu gereksizdir.**
   Mevcut SQLite tablosu event, recipient ve read projection'ını tek satırda
   birleştirir. Production inbox, `notification_events` ile
   `notification_deliveries` join'inden üretilir; SQLite DDL doğrudan Alembic'e
   taşınmaz.

## 3. Tablolar, kolonlar ve migration

### 3.1 Yeni `notification_events`

Canonical iş olayıdır; delivery sonucu değildir ve yayımlandıktan sonra
değişmez.

| Kolon/kısıt | Tip / davranış | Amaç |
|---|---|---|
| `event_id` | `String(36)` PK | Canonical event kimliği |
| `event_type` | `String(40)` NN | Mevcut `NotificationEventType` parity |
| `scope_type` | `String(30)` NN | Mevcut `NotificationScopeType` parity |
| `scope_id` | `String(128)` NN | Issue/source/dataset/execution bounded referansı; UUID zorunlu değil |
| `source_ref` | `String(200)` NN | İş olayının değişmez kaynağı; issue history/source event referansı |
| `deduplication_key_digest` | `String(64)` NN | Ham dedup anahtarı saklamadan routing/suppression kanıtı |
| `payload_digest` | `String(64)` NN | Aynı idempotency anahtarında farklı payload conflict kontrolü |
| `payload` | JSONB NN | Yalnız bounded object ref, önem, link code ve reason code |
| `correlation_id` | `String(128)` NN | İş zinciri korelasyonu |
| `policy_version` | `String(80)` NN | Notification event/payload policy sürümü |
| `occurred_at` | timestamptz NN | Kaynak iş olayının zamanı |
| `published_at` | timestamptz NN | Event'in aynı iş transaction'ında kalıcı olduğu zaman |

Kısıtlar ve indeksler:

- unique `(source_ref, event_type)` — aynı kaynak iş olayı retry'da ikinci event
  üretmez;
- aynı unique anahtar mevcutken `payload_digest` farklıysa application conflict;
- event type check:
  `QUALITY_THRESHOLD`, `CRITICAL_RULE_FAILURE`, `TECHNICAL_ERROR`,
  `ISSUE_ASSIGNED`;
- scope type check:
  `RULE`, `DATASET`, `SOURCE`, `EXECUTION`, `ISSUE_ASSIGNMENT`;
- `(event_type, published_at DESC)` ve
  `(scope_type, scope_id, published_at DESC)` indeksleri;
- `payload` içinde secret/credential/sample/value anahtarları service validator'da
  fail-closed reddedilir; DB ham hassas metin arama motoru değildir.

Event satırı update/delete API'si almaz. Business recurrence yeni `source_ref`
ile yeni canonical event'tir; aynı source event retry'ı recurrence sayılmaz.

### 3.2 Yeni `notification_channels`

| Kolon/kısıt | Tip / davranış | Amaç |
|---|---|---|
| `channel_id` | `String(36)` PK | Kanal kimliği |
| `name` | `String(120)` NN | Yönetim görünümü için bounded ad |
| `channel_type` | `String(24)` NN | `IN_APP` + mevcut `ChannelKind` değerleri |
| `target_config` | JSONB NN default `{}` | Secret içermeyen adresleme/config kodları |
| `secret_ref` | nullable `String(255)` | Haricî credential'ın yalnız provider referansı |
| `allowed_event_types` | JSONB NN | Enum allowlist; boş liste hiçbir event'e route etmez |
| `status` | `ACTIVE/INACTIVE` | Kanal kullanılabilirliği |
| `policy_version` | `String(80)` NN | Routing/config policy sürümü |
| `version` | integer NN default 1 | Optimistic locking |
| `created_by` | `String(128)` NN | Trusted actor ID; DS-10'a kadar FK yok |
| `created_at` | timestamptz NN | Oluşturma zamanı |
| `updated_at` | timestamptz NN | Son mutation zamanı |

Kısıtlar ve indeksler:

- unique `(name)`;
- `channel_type` check: `IN_APP`, `EMAIL`, `MESSAGING`, `SERVICENOW`, `JIRA`;
- `status` check; `version >= 1`;
- `IN_APP` için `secret_ref IS NULL`; haricî `ACTIVE` kanal için doğrulanmış
  `secret_ref` application invariant'ı;
- `(status, channel_type)` indeksi.

Migration haricî provider'ı veya secret değeri seed etmez. Development seed açık
bir `IN_APP` kanal yaratır. Production composition beklenen policy version'da
aktif IN_APP kanal bulamazsa fail-fast olur; fake fallback kurmaz.

### 3.3 Yeni `notification_subscriptions`

| Kolon/kısıt | Tip / davranış | Amaç |
|---|---|---|
| `subscription_id` | `String(36)` PK | Tercih kimliği |
| `user_id` | `String(128)` NN | Actor/recipient kimliği; DS-10'a kadar kullanıcı FK'si yok |
| `event_type` | `String(40)` NN | Tercih edilen event tipi |
| `scope_type` | nullable `String(30)` | Null ise actor'ın tüm yetkili kapsamları |
| `scope_id` | nullable `String(128)` | Scope type ile birlikte kullanılır |
| `channel_id` | `String(36)` NN FK → `notification_channels.channel_id` | Teslimat kanalı |
| `status` | `ACTIVE/INACTIVE` | Kullanıcı tercihi |
| `policy_version` | `String(80)` NN | Mandatory/subscription policy sürümü |
| `version` | integer NN default 1 | `If-Match`/optimistic locking |
| `created_at` | timestamptz NN | Oluşturma zamanı |
| `updated_at` | timestamptz NN | Son değişiklik zamanı |

Kısıtlar ve indeksler:

- unique expression
  `(user_id, event_type, COALESCE(scope_type,''), COALESCE(scope_id,''), channel_id)`;
- scope type null ise scope ID de null; scope type doluysa scope ID zorunlu;
- `status` ve mevcut event/scope enum check'leri; `version >= 1`;
- `(event_type, status)` ve `(user_id, status)` indeksleri.

`ISSUE_ASSIGNED` mandatory event'tir. Assignee için delivery subscription kaydı
olmasa da üretilir; bu event için `INACTIVE` yazma girişimi service katmanında
reddedilir. Yeni event catalog/permission tablosu eklenmez; mandatory set sürümlü
`NotificationAccessPolicy` sahibidir.

### 3.4 Yeni `notification_deliveries`

| Kolon/kısıt | Tip / davranış | Amaç |
|---|---|---|
| `delivery_id` | `String(36)` PK | Teslimat/inbox kimliği |
| `event_id` | `String(36)` NN FK → `notification_events.event_id` | Canonical olay |
| `recipient_user_id` | `String(128)` NN | Gerçek alıcı; DS-10'a kadar FK yok |
| `channel_id` | `String(36)` NN FK → `notification_channels.channel_id` | Teslimat kanalı |
| `status` | `String(24)` NN | `ST-NotificationDelivery` durumu |
| `attempt_count` | integer NN default 0 | Gerçek adapter deneme sayısı |
| `last_error_class` | nullable `String(80)` | Redacted teknik sınıf; exception metni değil |
| `last_attempt_at` | nullable timestamptz | Son deneme zamanı |
| `next_attempt_at` | nullable timestamptz | Delivery görünürlüğü; job retry ile uyumlu |
| `delivered_at` | nullable timestamptz | Başarılı kanal teslim zamanı |
| `read_at` | nullable timestamptz | Yalnız IN_APP alıcı aksiyonu |
| `rerouted_to_channel_id` | nullable FK → `notification_channels.channel_id` | Alternatif kanal referansı |
| `version` | integer NN default 1 | Optimistic state transition |
| `created_at` | timestamptz NN | Delivery oluşturma zamanı |
| `updated_at` | timestamptz NN | Son transition zamanı |

Kısıtlar ve indeksler:

- unique `(event_id, recipient_user_id, channel_id)` — delivery retry
  idempotency'si;
- status check:
  `PENDING`, `SENDING`, `DELIVERED`, `FAILED`, `UNDELIVERABLE`, `REROUTED`,
  `READ`;
- `attempt_count >= 0`, `version >= 1`;
- `READ` ise `delivered_at` ve `read_at`; `DELIVERED` ise `delivered_at` zorunlu;
- migration ve runtime metadata'da birebir
  `CHECK (status != 'REROUTED' OR rerouted_to_channel_id IS NOT NULL)`;
- `(recipient_user_id, status, created_at DESC)`,
  partial `(status, next_attempt_at)` for `PENDING/FAILED` ve `(event_id)`
  indeksleri.

`Notification` mevcut API/domain projection'ı olarak korunabilir ancak production
satır sahibi değildir: event + delivery join'inden üretilir. Ayrı `notifications`
tablosu eklenmez.

### 3.5 Şeması değişmeyecek tablolar

- `data_quality_issues`, `issue_history`: notification `source_ref` ve recipient
  çözümünde okunur; yeni kolon eklenmez.
- `background_jobs`: `NOTIFICATION_DELIVERY` string job type mevcut sözleşmede
  çalışır; DDL değişmez.
- `job_dead_letters`, `workers`: mevcut retry/dead-letter/registration yolu
  korunur.
- `audit_outbox`, `audit_events`: yeni audit action'ları mevcut JSON/outbox
  sözleşmesinde çalışır; DDL değişmez.
- `users`, `roles`, `permissions`: DS-10 kapsamıdır; DS-09 bunları erken yaratmaz.
- `integration_records`: DS-23 kapsamıdır.
- SQLite `notifications` DDL'i: development/unit adapter parity için korunur;
  Alembic production tablosuna çevrilmez.

### 3.6 Migration sırası

1. `notification_channels` oluştur.
2. `notification_events` oluştur.
3. `notification_subscriptions` tablosunu channel FK ile oluştur.
4. `notification_deliveries` tablosunu event/channel/reroute FK'larıyla oluştur.
5. Check, unique-expression, partial ve query indekslerini ekle.
6. Runtime SQLAlchemy metadata'sını revision 20 ile birebir eşle.
7. `api/composition.py:CURRENT_MIGRATION_HEAD` değerini `20260806_20` yap ve dört
   tabloyu `REQUIRED_TABLES` içine ekle.
8. Development seed'de explicit active IN_APP kanal/policy oluştur; production
   config yokluğunu preflight/composition'da fail-fast doğrula.

## 4. Backend servis, repository ve worker envanteri

### 4.1 Değişecek mevcut notification dosyaları

| Dosya | Sembol | Planlanan değişiklik |
|---|---|---|
| `src/veri_kalitesi/notifications/models.py` | `NotificationEvent`, `Notification`, `NotificationStatus`, `NotificationAccessPolicy`, validators | Bounded string ID parity; source_ref/payload/policy; yeni channel/subscription/delivery modelleri ve tam delivery status enum'u |
| `src/veri_kalitesi/notifications/service.py` | `NotificationService`, `NotificationRecipientResolver`, `_TEMPLATES` | SQLite somut bağımlılığını porta çevirme; side-effect-free `prepare_for_event`; own inbox/read; mandatory subscription ve channel/delivery command orchestration |
| `src/veri_kalitesi/notifications/repository.py` | `SQLiteNotificationRepository` | Development/unit adapter parity; eski `notifications` şemasını production kaynağı yapmadan yeni protokol davranışlarını karşılama |
| `src/veri_kalitesi/notifications/channel_adapters.py` | `ChannelKind`, `NotificationChannelPolicy`, `NotificationChannelDispatcher`, `FakeChannelAdapter` | `IN_APP` ekleme; routing'i saf/policy kontrollü tutma; in-memory idempotency log'unu production yolundan çıkarma; fake yalnız test/sandbox |
| `src/veri_kalitesi/notifications/errors.py` | Mevcut hata hiyerarşisi | Query/delivery/configuration concurrency hata kategorileri ve güvenli correlation mapping |
| `src/veri_kalitesi/notifications/__init__.py` | exports | Yeni modeller, portlar, PG repository, query/delivery/job servislerini export etme |

### 4.2 Yeni backend dosyaları

| Yeni dosya | Sembol | Tek sorumluluk |
|---|---|---|
| `src/veri_kalitesi/notifications/contracts.py` | `PreparedNotificationBatch`, `NotificationRepository`, `NotificationBatchStager`, `NotificationChannelAdapter` portları | SQLite/PG somut tiplerini service ve issue transaction sınırından ayırma |
| `src/veri_kalitesi/notifications/postgresql_repository.py` | `NotificationTables`, `notification_tables`, `PostgreSQLNotificationRepository` | Event/channel/subscription/delivery CRUD, locks, pagination ve session-aware batch staging |
| `src/veri_kalitesi/notifications/query.py` | `NotificationQueryService`, inbox/channel/delivery filter/page DTO'ları | Actor ownership ve yönetim rolü doğrulanmış bounded sorgular |
| `src/veri_kalitesi/notifications/delivery.py` | `NotificationDeliveryService`, `InAppNotificationChannelAdapter` | İzinli delivery transition, durable attempt sonucu, retry/undeliverable ve IN_APP teslimatı |
| `src/veri_kalitesi/notifications/jobs.py` | `NotificationDeliveryJobPayload`, `PostgreSQLNotificationJobEnqueuer`, `NotificationDeliveryJobHandler` | Delivery batch → mevcut queue ve job → delivery service adapter'ı |

Bu dosyalar generic unit-of-work, event bus veya ikinci queue değildir.
`PreparedNotificationBatch` yalnız iş repository'sinin mevcut session'ına
notification event/delivery/job staging aktarabilmek için dar transaction
sözleşmesidir.

### 4.3 Issue transaction entegrasyonu

| Dosya | Sembol | Değişiklik |
|---|---|---|
| `src/veri_kalitesi/issues/contracts.py` | `IssueRepository.add_or_increment`, `update_assignment` | Keyword-only `notification_batch: PreparedNotificationBatch | None` parametresi; session protokol yüzeyine çıkarılmaz |
| `src/veri_kalitesi/issues/service.py` | `IssueNotificationPublisher`; `create_for_trigger`, `reassign`; `_publish_notification`, `_publish_assignment_notification` | Post-commit create çağrısı yerine mutation öncesi validate/prepare; delivery hatası ile event staging hatasını ayırma |
| `src/veri_kalitesi/issues/postgresql_repository.py` | `PostgreSQLIssueRepository.__init__`, `add_or_increment`, `update_assignment` | Inject edilen `NotificationBatchStager`; repository'nin açtığı transaction içinde `stage(notification_batch, session=session)` çağrısı |
| `tests/support/legacy_sqlite_issue_repository.py` | `SQLiteIssueRepository` | Issue service unit test contract parity; production kanıtı değildir |

Kesin transaction akışı:

1. `IssueService` trusted producer context, event type, source_ref, scope ve
   recipient'ı doğrular; `PreparedNotificationBatch` üretir.
2. Service `add_or_increment(..., notification_batch=batch)` veya
   `update_assignment(..., notification_batch=batch)` çağırır. SQLAlchemy session
   public repository protokolüne verilmez; transaction ownership repository'de
   kalır.
3. `PostgreSQLIssueRepository` mevcut mutation transaction'ını açar ve
   issue/history/audit'i yazar.
4. Aynı session'da
   `NotificationBatchStager.stage(notification_batch, session=session)` canonical
   event ve delivery kayıtlarını yazar.
5. Aynı session'da `PostgreSQLJobQueueRepository.enqueue(..., session=session)`
   deterministik `NOTIFICATION_DELIVERY` job'ını ekler.
6. Herhangi bir stage/insert/audit hatasında tüm business mutation rollback olur.
7. Commit sonrası event artık kaybolmaz. Worker teslimat hatası yalnız delivery/job
   state'ini etkiler; issue'yu geri almaz.

Bu nedenle bugünkü “notification exception'ını post-commit yut” davranışı event
staging için korunmaz. Yalnız asenkron channel attempt başarısızlığı issue'dan
ayrıdır.

### 4.4 Durable job ve delivery state-machine

| Dosya | Sembol | Değişiklik |
|---|---|---|
| `src/veri_kalitesi/jobs/composition.py` | `create_persistent_job_runtime` | Opsiyonel `notification_delivery_handler`; handler map'e `NOTIFICATION_DELIVERY` ekleme |
| `src/veri_kalitesi/jobs/production.py` | `create_production_worker`, `ProductionWorkerProviders` | `_WorkerNotificationPublisher` kaldırma; gerçek PG notification repository/event service/delivery handler wiring; external adapter provider yoksa yalnız IN_APP |
| `src/veri_kalitesi/jobs/settings.py` | `PersistentJobSettings` | Notification/actor/channel policy sürümleri ve bounded delivery retry ayarları; boş/uyumsuz değer fail-fast |
| `src/veri_kalitesi/jobs/handlers.py` | Genel handler protokolü | Değişmeyebilir; notification-specific payload/handler `notifications/jobs.py` içinde mevcut callable sözleşmesini uygular |
| `src/veri_kalitesi/jobs/worker.py` | `PersistentJobWorker` | Değişmez; mevcut handler/lease/retry/dead-letter davranışı kullanılır |
| `src/veri_kalitesi/jobs/postgresql_repository.py` | `enqueue`, claim/failure methods | DDL ve çekirdek değişmez; yalnız session-aware enqueue ve mevcut retry yolu çağrılır |

Delivery service transition sırasında delivery satırını `FOR UPDATE`/version ile
korur. Handler retryable teknik hatayı `RetryableJobError`, invalid payload veya
kalıcı config hatasını `PermanentJobError` olarak sınıflandırır. Raw exception,
target config veya secret audit/job payload'a taşınmaz.

### 4.5 API production composition

| Dosya | Sembol | Değişiklik |
|---|---|---|
| `src/veri_kalitesi/api/settings.py` | `ApplicationSettings` | `notification_policy_version`, `notification_channel_policy_version`; mevcut actor policy yeniden kullanılır |
| `src/veri_kalitesi/api/composition.py` | `CURRENT_MIGRATION_HEAD`, `REQUIRED_TABLES`, `create_application`, `PhaseBProviders` | PG notification repo/query/command wiring; `app.state.notification_*`; mevcut issue notification provider alanlarını koruyup gerçek PG implementation verme |
| `src/veri_kalitesi/api/production.py` | `create_production_app` | Notification'ı dış fake publisher'dan değil production composition root'tan kurma; external adapter injection yoksa IN_APP ile çalışma |
| `src/veri_kalitesi/api/development.py` | `create_development_app` | PG development compose'da gerçek notification servisleri; yalnız açık unit/story profilinde SQLite/fake kanal |
| `src/veri_kalitesi/api/models.py` | Yeni notification response/request modelleri | Event+delivery projection, page/unread count, subscription/channel/delivery DTO'ları; secret_ref write-only/redacted |
| `src/veri_kalitesi/api/app.py` | `create_dashboard_api`; notification service portları, routes ve error handlers | İnce HTTP adapter; actor/CSRF/If-Match; no-store; güvenli 400/401/403/404/409/422/503 mapping |
| `src/veri_kalitesi/audit/policies.py` | `build_default_redaction_policy` | Sekiz DS-09 action için ID/enum/count/status/policy-only allowlist; revision 20 ile aynı uygulama adımında aktive edilir |
| `scripts/seed_database.py` | notification seed bölümü | Active IN_APP channel, zorunlu/isteğe bağlı subscription corpus; doğrudan DELIVERED fixture seed edilmez |
| `infra/development/compose.yaml` | API/worker environment | Notification ve channel policy sürümleri; fake external provider yok |

`PhaseBProviders.issue_notification_publisher` ve
`issue_notification_actor_context_provider` kaldırılmaz; mevcut composition
sözleşmesi ve test injection noktası korunur. Production/development composition
bu alanlara PostgreSQL notification service tarafından sağlanan gerçek publisher
ve trusted actor-context provider implementation'larını verir. Fake/no-op yalnız
açık unit/story profilinde kalır. Gerçek dış kanal adaptörleri ileride ayrı
production-owned provider map'i olarak worker sınırına eklenir. Assignment,
assignee directory ve diğer DS-02/DS-05 provider alanları da korunur.

## 5. Endpoint envanteri

### 5.1 Kullanıcı gelen kutusu ve tercihler

| Endpoint | HTTP sözleşmesi | Backend kontrolü |
|---|---|---|
| `/api/v1/notifications` | `GET`; `status`, `event_type`, `limit`, cursor; `items` + `unread_count` | Trusted standard USER; repository sorgusu zorunlu `recipient_user_id=actor_id` |
| `/api/v1/notifications/{delivery_id}/read` | `POST`; current version/If-Match; güncel delivery DTO | CSRF; yalnız alıcı; `DELIVERED → READ`; tekrar idempotent |
| `/api/v1/users/{user_id}/notification-subscriptions` | `GET`; mevcut channel/event/scope tercihleri | Kendi user ID'si veya `.all` yönetim rolü |
| `/api/v1/users/{user_id}/notification-subscriptions` | `PUT`; tam replacement/upsert, version ve policy version | CSRF; kendi kaydı veya `.all`; mandatory type kapatılamaz |

`GET /notifications` event payload'ın ham JSONB değerini dönmez. Response yalnız
delivery/event ID, enum, bounded title/body template, scope reference, status,
timestamp, version ve güvenli application link taşır. `secret_ref` hiçbir inbox
response'unda bulunmaz.

### 5.2 Kanal ve delivery operasyonu

| Endpoint | HTTP sözleşmesi | Backend kontrolü |
|---|---|---|
| `/api/v1/notification-channels` | `GET`; status/type filtreli bounded liste | `PLATFORM_ADMIN`/channel-manage rolü; standard kullanıcıya kapalı |
| `/api/v1/notification-channels` | `POST`; name/type/target config/secret_ref/allowed types/policy | CSRF; channel-manage; secret değeri reddi; provider yoksa external ACTIVE reddi |
| `/api/v1/notification-deliveries` | `GET`; status/channel/event type/date/recipient filtreleri, cursor | Operations/Platform Admin; kurum-geneli delivery read rolü |
| `/api/v1/notification-deliveries/{delivery_id}/reroute` | `POST`; target channel ID, expected version, reason code | CSRF; delivery-manage; state ve target provider doğrulaması |

Reroute `UNDELIVERABLE → REROUTED` geçişidir; request body `DELIVERED` sonucu
iddia edemez. IN_APP fallback için yeni idempotent target delivery/job hazırlanır;
eski delivery satırı geçmiş kanıt olarak korunur.

### 5.3 API hata ve cache sözleşmesi

- `400`: geçersiz query/cursor/If-Match biçimi;
- `401`: trusted session yok;
- `403`: sahiplik, rol veya mandatory subscription ihlali;
- `404`: notification/delivery/channel yok veya actor'a ait değil;
- `409`: stale version, yasak state geçişi ya da idempotency payload conflict;
- `422`: domain/config/payload doğrulama hatası;
- `503`: PostgreSQL, recipient resolver veya channel provider teknik hatası.

Tüm notification response'ları `Cache-Control: no-store` ve correlation ID taşır.
POST/PUT uçları mevcut CSRF middleware'inden geçer.

## 6. Frontend ekran ve çağrı envanteri

### 6.1 Yeni frontend dosyaları

| Yeni dosya | Ekran/sorumluluk |
|---|---|
| `frontend/src/notifications/model.ts` | Inbox/channel/subscription/delivery API DTO doğrulama ve view-model; unknown enum fail-closed |
| `frontend/src/notifications/api.ts` | Sekiz endpoint çağrısı; credentials, CSRF, cursor/filter encoding ve safe error mapping |
| `frontend/src/notifications/NotificationsPage.tsx` | Gelen Kutusu; unread-first liste, filtre, empty/error/unauthorized ve read aksiyonu |
| `frontend/src/notifications/NotificationPreferencesPage.tsx` | Kullanıcının kendi isteğe bağlı tercihleri; mandatory tip disabled/locked görünümü |
| `frontend/src/notifications/NotificationChannelsPage.tsx` | Yetkili kanal listesi/yeni kanal formu; secret değeri değil secret reference |
| `frontend/src/notifications/NotificationDeliveriesPage.tsx` | Operasyon teslimat listesi, durum/attempt/error-class ve izinli reroute aksiyonu |
| `frontend/src/components/NotificationBell.tsx` | AppShell unread sayacı, kısa liste ve `/notifications` bağlantısı |

### 6.2 Değişecek mevcut frontend dosyaları

| Dosya | Değişiklik |
|---|---|
| `frontend/src/App.tsx` | Lazy notification sayfaları; `/notifications`, `/notifications/preferences`, `/notifications/channels`, `/notifications/deliveries` route ve gerçek API state'leri |
| `frontend/src/components/AppShell.tsx` | Header'a `NotificationBell`; OPERASYON grubuna Bildirimler linki; unread sayacı gerçek API'den |
| `frontend/src/components/AppShell.test.tsx` | Yeni link, accessible bell/count, loading/error'da sahte sayı göstermeme |

AppShell ve inbox için ayrı synthetic production fallback eklenmez. Development
fixture-state yalnız `import.meta.env.DEV` ile açık story/test senaryosunda
çalışabilir. API 401/403/503 verdiğinde bell `0` başarılı sonucu uydurmaz; uygun
unauthorized/unavailable state gösterir.

## 7. Permission, scope ve audit

### 7.1 Backend permission sözleşmesi

Mevcut `NotificationAccessPolicy` genişletilir; yeni permission tablosu veya
kalıcı rol modeli eklenmez.

| İşlem | Actor/rol | Nesne sınırı |
|---|---|---|
| Inbox list/read | Trusted, unexpired, policy-version uyumlu standard USER | `recipient_user_id == actor_context.actor_id` |
| Kendi subscription'ı | Standard USER | URL user ID actor ID ile aynı |
| Başka kullanıcının subscription'ı | `PLATFORM_ADMIN` veya policy'deki `.all` rolü | Enterprise yönetim sınırı |
| Channel list/create | `PLATFORM_ADMIN`/channel-manage rolü | Enterprise; external provider availability zorunlu |
| Delivery list | `OPERATIONS_USER` veya `PLATFORM_ADMIN` | Enterprise delivery monitoring |
| Manual reroute | `OPERATIONS_USER`/delivery-manage rolü | Yalnız `UNDELIVERABLE`, target channel ACTIVE/provider-ready |
| Event üretimi | Trusted SERVICE context | Persisted issue/history/source ref ve resolved recipient |

Frontend rol veya `available_actions` alanı yetkinin kaynağı değildir. Her query
ve command backend'de yeniden doğrulanır. Başkasının delivery ID'si 404 ile
gizlenir; kullanıcıdan `recipient_user_id` kabul edilmez.

### 7.2 Audit olayları

| Olay | Aynı transaction'daki kayıt |
|---|---|
| `NOTIFICATION_EVENT_PUBLISHED` | Business mutation + canonical event + ilk delivery/job batch |
| `NOTIFICATION_PAYLOAD_REJECTED` | Fail-closed güvenlik failure audit'i; hassas payload/event yok |
| `NOTIFICATION_SUBSCRIPTION_CHANGED` | Subscription create/update/status/version |
| `NOTIFICATION_CHANNEL_CONFIGURED` | Channel config/status/version; secret_ref/value audit'e girmez |
| `NOTIFICATION_DELIVERY_ATTEMPTED` | `SENDING → DELIVERED/FAILED`, attempt count ve error class |
| `NOTIFICATION_UNDELIVERABLE` | `FAILED → UNDELIVERABLE` ve varsa target channel ref |
| `NOTIFICATION_DELIVERY_REROUTED` | Eski `UNDELIVERABLE → REROUTED` + yeni target delivery/job |
| `NOTIFICATION_READ` | `DELIVERED → READ`; actor yalnız recipient |

Bu sekiz action'ın tamamı `build_default_redaction_policy` içine revision 20
runtime metadata/preflight değişikliğiyle aynı uygulama adımında eklenir. Böylece
yeni tablo ve servis yolu allowlist hazır olmadan audit üretmeye başlamaz. Audit
allowlist yalnız event/delivery/channel ID, enum, status, count, policy
version ve bounded reason code içerir. `payload`, title/body, target_config,
secret_ref, raw dedup key ve adapter exception metni audit'e girmez.

## 8. Test envanteri

`docs/testing/AGENTS.md` gereği yeni testler FR/UC/AC kimlikleri taşır; permission,
timeout, retry, idempotency, rollback, fail-closed ve teknik hata yolları ayrı
kanıtlanır.

### 8.1 Değişecek backend testleri

| Dosya | Eklenecek/değişecek kanıt |
|---|---|
| `tests/unit/test_notifications.py` | Bounded non-UUID actor/scope ID; prepare/stage; mandatory subscription; full delivery transition; own inbox/read; payload rejection; status/idempotency semantics |
| `tests/unit/test_prototype_05_capabilities.py` | Routing/suppression saf policy testleri; fake adapter'ın yalnız sandbox olduğu; IN_APP kind parity |
| `tests/unit/test_issues.py` | Post-commit notification failure testlerini event-stage rollback vs async-delivery failure ayrımına çevirme; issue/history/event/job atomik batch |
| `tests/unit/test_ds05_auto_issue_and_manual_create.py` | Eligible automatic issue ve reassignment'ın doğru source_ref/recipient notification batch üretmesi; ineligible sonuç üretmemesi |
| `tests/unit/test_issue_api.py` | Assignment response'u channel attempt beklemez; event staging configuration/technical error mapping; CSRF regressions |
| `tests/unit/test_persistent_job_handlers.py` | Notification payload validation, success, retryable/permanent error ve cancellation sınırı |
| `tests/unit/test_persistent_job_worker.py` | `NOTIFICATION_DELIVERY` registration, retry/restart/dead-letter ve supported job types |
| `tests/unit/test_audit.py` | Yeni notification action allowlist'lerinde payload/config/secret/raw error redaksiyonu |
| `tests/integration/test_postgresql_issue_mutations.py` | Issue create/reassign + event/delivery/job/audit tek transaction; stage hatasında tam rollback |
| `tests/integration/test_application_composition.py` | Head 20, dört required table, PG notification service/app.state, gerçek worker handler ve missing IN_APP fail-fast |

Mevcut `test_uc_011_notification_technical_failure_preserves_committed_issue`
benzeri testlerin semantiği ayrılır: **delivery attempt** hatası committed issue'yu
korur; **canonical event staging** hatası issue transaction'ını rollback eder.
İkisini tek “notification failure” sınıfında tutmak DS-09 atomiklik kuralını
yanlış doğrular.

### 8.2 Yeni backend testleri

| Yeni dosya | Amaç |
|---|---|
| `tests/unit/test_notification_delivery.py` | ST-NotificationDelivery izinli/yasak geçişler, attempts, retry/undeliverable, reroute, IN_APP adapter ve optimistic version |
| `tests/unit/test_notification_query.py` | Own inbox, unread count, cursor/filter, channel/delivery admin rolleri, existence leak yok |
| `tests/unit/test_notification_api.py` | Sekiz endpoint; CSRF/If-Match; 400/401/403/404/409/422/503; no-store; secret response yok |
| `tests/unit/test_notification_jobs.py` | Veri-minimum payload, deterministik idempotency key, session-aware enqueue ve handler error classification |
| `tests/integration/test_postgresql_notification_migration.py` | 19→20 upgrade/downgrade; tablo/kolon/FK/check/unique/index ve users FK yokluğu |
| `tests/integration/test_postgresql_notification_persistence.py` | Event/delivery idempotency, concurrent staging, subscription/channel locking, read/reroute, audit rollback ve restart |
| `tests/integration/test_ds09_notification_delivery.py` | Gerçek PG execution→issue/assignment→event/job→worker→IN_APP delivery→API/read→audit zinciri |

`test_ds09_notification_delivery.py` doğrudan `NotificationService`, SQLite
repository, `FakeChannelAdapter` veya frontend mock ile geçerse production kabul
kanıtı sayılmaz. En az bir notification delivery worker restart/retry ve ayrı bir
unauthorized-recipient senaryosu gerçek PostgreSQL yolunda çalışmalıdır.

### 8.3 Frontend testleri

| Dosya | Senaryo |
|---|---|
| `frontend/src/notifications/model.test.ts` | DTO enum/timestamp/status mapping, unread count, invalid response fail-closed, secret/config alanı kabul etmeme |
| `frontend/src/notifications/api.test.ts` | Sekiz çağrı; filters/cursor; credentials/CSRF/If-Match ve safe error mapping |
| `frontend/src/notifications/NotificationsPage.test.tsx` | Loading/empty/data/error/unauthorized, unread-first, read action ve sahiplik görünümü |
| `frontend/src/notifications/NotificationPreferencesPage.test.tsx` | Mandatory lock, optional toggle, stale version/conflict ve başka kullanıcı reddi |
| `frontend/src/notifications/NotificationChannelsPage.test.tsx` | Role-hidden action, secret-ref formu, raw secret rejection ve provider-unavailable state |
| `frontend/src/notifications/NotificationDeliveriesPage.test.tsx` | Status/attempt/error class, filters, yalnız izinli reroute ve conflict refresh |
| `frontend/src/components/NotificationBell.test.tsx` | Unread badge, accessible label, kısa liste, API error'da sahte zero/success göstermeme |
| `frontend/src/components/AppShell.test.tsx` | Bildirimler navigation, bell placement ve yeni navigation count |
| `frontend/e2e/notifications.spec.ts` | Mock contract ile inbox→read→preferences ve admin delivery interaction; production kanıtı değil |
| `frontend/e2e/notifications-live.spec.ts` | Gerçek compose/PG/worker üzerinde issue assignment → bell/inbox → read smoke |

### 8.4 Korunacak regresyon testleri

- `tests/unit/test_notifications.py` içindeki data-minimum, trusted
  actor, recipient isolation, digest conflict ve audit rollback testlerinin
  davranış özü.
- `tests/unit/test_issues.py` ve
  `test_ds05_auto_issue_and_manual_create.py` issue eligibility, assignment,
  dedup/recurrence ve state-machine testleri.
- `tests/integration/test_postgresql_issue_persistence.py` ve
  `test_postgresql_issue_mutations.py` issue/history/audit atomikliği.
- `tests/integration/test_postgresql_job_queue.py` queue/lease/retry/
  dead-letter testleri.
- `tests/unit/test_audit.py` ve
  `tests/integration/test_postgresql_audit_repository.py` outbox
  bütünlük/redaksiyon testleri.
- Mevcut frontend issue, AppShell, routing ve CSRF testleri.

### 8.5 Çalıştırılacak test grupları

```bash
python3 -m pytest tests/unit/ -x -q
```

PostgreSQL test bağlantısı varsa:

```bash
python3 -m pytest tests/integration/ -x -q
```

```bash
cd frontend && npx vitest run
```

```bash
cd frontend && npm run build
```

Repository kökünden:

```bash
python3 -m ruff check docs/backend/ docs/testing/
```

Entegrasyon komutu revision 20 migration, notification/issue persistence,
application composition ve gerçek PostgreSQL DS-09 production-chain testini
kapsamalıdır. Fake/SQLite yoluyla geçen test bu zincirin yerine geçmez.

## 9. Kesin dosya değişikliği özeti

### 9.1 Yeni

- `alembic/versions/20260806_20_notification_delivery.py`
- `src/veri_kalitesi/notifications/{contracts,postgresql_repository,query,delivery,jobs}.py`
- `frontend/src/notifications/{model,api,NotificationsPage,NotificationPreferencesPage,NotificationChannelsPage,NotificationDeliveriesPage}.ts(x)`
- `frontend/src/components/NotificationBell.tsx`
- §8.2 ve §8.3'teki yeni test dosyaları

### 9.2 Değişecek

- `src/veri_kalitesi/notifications/{models,service,repository,channel_adapters,errors,__init__}.py`
- `src/veri_kalitesi/issues/{contracts,service,postgresql_repository}.py`
- `src/veri_kalitesi/jobs/{composition,production,settings}.py`
- `src/veri_kalitesi/api/{models,app,settings,composition,production,development}.py`
- `src/veri_kalitesi/audit/policies.py`
- `tests/support/legacy_sqlite_issue_repository.py`
- `frontend/src/{App.tsx,components/AppShell.tsx}`
- `scripts/seed_database.py`
- `infra/development/compose.yaml`
- §8.1 ve §8.3'teki mevcut test dosyaları

### 9.3 Değişmeyecek

- Migration 01–19
- `data_quality_issues`, `issue_history`, `background_jobs`, `job_dead_letters`,
  `workers`, `audit_outbox`, `audit_events` tablo kolonları
- `jobs/worker.py` ve `jobs/postgresql_repository.py` queue çekirdeği
- Issue status/verification/closure state-machine'i
- Execution, score publication, catalog ve dashboard API sözleşmeleri
- SQLite `notifications` DDL'i development/unit adapter olarak korunur; PG
  migration'a kopyalanmaz
- DS-10 öncesi kullanıcı/rol/permission tabloları ve kullanıcı FK'ları
- ServiceNow/Jira integration kayıtları
- Production'da SQLite/in-memory/fake/no-op notification veya channel fallback'i

## 10. Kesin uygulama sırası

1. Revision 20 migration, runtime table metadata, sekiz action'lık audit redaction
   allowlist ve migration/audit testleri tek değişiklik adımında.
2. Notification modellerinde bounded ID ve delivery state enum.
3. Repository contracts ve `PostgreSQLNotificationRepository`.
4. Payload policy, recipient/subscription resolution ve prepared batch.
5. Issue contracts protocol'üne keyword-only notification batch parametresi.
6. Issue service `create_for_trigger`/`reassign` akışında pre-commit prepare/staging
   refactor'ü.
7. Issue PostgreSQL repository'de sahip olunan session içine notification batch
   staging.
8. IN_APP delivery service ve optimistic transition.
9. `NOTIFICATION_DELIVERY` job payload/enqueuer/handler.
10. Worker composition ve gerçek PostgreSQL notification wiring.
11. Notification query/command servisleri.
12. API DTO'ları ve sekiz endpoint.
13. Composition root: head 20, required tables ve `app.state` yayınları; korunan
    Phase B provider alanlarına gerçek PG implementation'lar.
14. Frontend model/API, NotificationBell ve Gelen Kutusu.
15. Tercihler, Kanallar ve Teslimat İzleme ekranları.
16. Development seed database ve frontend build/test.
17. §8.5'teki tam backend lint/test zinciri ve PostgreSQL varsa production-chain
    entegrasyon testi.

Migration/repository geçmeden issue transaction'ına; atomic staging geçmeden
worker'a; state-machine ve backend permission testleri geçmeden frontend'e;
gerçek IN_APP production delivery geçmeden live kabul testine ilerlenmez.

## 11. Envanter kararı

**GO — dört zorunlu düzeltme envantere işlendi.** Mevcut notification domain
doğrulamaları, issue publisher çağrı noktaları, PostgreSQL queue/worker,
transactional audit ve frontend route/state desenleri yeniden kullanılabilir.

Uygulama öncesi kapatılan düzeltmeler:

1. `add_or_increment`/`update_assignment` prepared batch alır; repository'nin
   sahip olduğu session stager'a açıkça enjekte edilir.
2. `PhaseBProviders.issue_notification_publisher` ve
   `issue_notification_actor_context_provider` korunur; gerçek PostgreSQL
   implementation'lara bağlanır.
3. Sekiz audit action allowlist'i revision 20 ile aynı değişiklik adımında
   etkinleştirilir.
4. Migration ve runtime metadata'ya
   `CHECK (status != 'REROUTED' OR rerouted_to_channel_id IS NOT NULL)` eklenir.

Uygulamada pazarlık konusu olmayan dört sınır:

1. Issue mutation ile canonical notification event aynı PostgreSQL transaction'da
   olmalıdır; mevcut post-commit proses çağrısı production yolu olarak kalamaz.
2. Gerçek actor/source/dataset kimlikleri bounded string olarak korunmalıdır;
   UUID doğrulamasını geçmek için sahte kimlik veya DS-10 kullanıcı tablosu erken
   eklenmemelidir.
3. Delivery, `UNREAD/READ` kısa modeliyle veya `PENDING → DELIVERED` atlamasıyla
   uygulanmamalı; hedef state-machine korunmalıdır.
4. Production kabulü PostgreSQL IN_APP adapter + durable worker üzerinden
   verilmelidir; in-memory dispatcher log'u, SQLite repository,
   `FakeChannelAdapter` veya no-op provider **NO-GO** nedenidir.
