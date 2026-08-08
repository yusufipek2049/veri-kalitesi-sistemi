---
type: functional-audit-work
stage: "17 — DS-05 Değişiklik Envanteri"
scope: slice-ds05-change-inventory
inputs:
  - 16-Fifth-Slice-Decision.md
  - 15-Slice-DS04-Change-Inventory.md
  - 13-Slice-DS03-Change-Inventory.md
  - 07-Implementation-Waves.md
  - ../04-Functional-Gap-Inventory.md
  - ../13-Implementation-Roadmap.md
project: Veri Kalitesi İzleme ve Skorlama Sistemi
branch: agent/36h1-persistent-job-core
created_at: 2026-08-06
---

# 17 — DS-05 Değişiklik Envanteri

> Seçilen beşinci dilim: **DS-05 — Otomatik sorun üretimi (GAP-006)**.
> Bu belge değişecek tablo, kolon, servis, endpoint, ekran ve testleri gerçek
> repository yolları ve sembolleriyle belirler. Uygulama veya kaynak kod
> değişikliği içermez.

---

## 1. Envanter özeti

| Katman | Karar |
|---|---|
| Yeni migration | `alembic/versions/20260806_18_issue_generation.py` |
| Yeni tablo | Yok; source-event receipt için mevcut immutable `issue_history` genişletilir |
| Genişleyecek tablolar | `data_quality_issues`, `issue_history` |
| Yeniden kullanılacak tablolar | `rule_executions`, `rule_execution_results`, `quality_rules`, `rule_versions`, `datasets`, `data_sources`, `background_jobs`, `workers`, `audit_outbox`, `audit_events` |
| Yeni job type | Yok; mevcut `EXECUTION` job'ı issue üretimi bitmeden tamamlanmaz |
| Ana backend değişikliği | Kalıcı execution sonucunu replay-safe `IssueTrigger`'a ve mevcut `IssueService.create_for_trigger` yoluna bağlamak |
| Yeni endpoint | `POST /api/v1/issues` — manuel issue oluşturma |
| Değişecek endpoint | `GET /api/v1/issues` — title, source referansları ve sayfa düzeyi `CREATE_ISSUE` action projection'ı |
| Frontend | Mevcut `/issues` ekranına manuel oluşturma diyaloğu ve gerçek source/dataset seçicileri |
| Production kanıtı | Gerçek executor sonucu → aynı kalıcı execution job'ı → issue receipt/create-or-increment → PostgreSQL → audit outbox → API/UI |

Mevcut Alembic head `20260805_17`'dir. DS-05 forward revision'ı `20260806_18`
olur; migration 01–17 değiştirilmez.

## 2. Repository kanıtı ve giriş kapıları

### 2.1 Yeniden kullanılacak mevcut çekirdek

| Kanıt | Mevcut dosya/simge | Sonuç |
|---|---|---|
| Uygunluk kalıcıdır | `executions/models.py:RuleExecutionResult.eligible_for_auto_issue`; `executions/postgresql_repository.py:complete_success` | Trigger adapter sonucu yeniden hesaplamaz; persisted kararı okur |
| Issue üretim servisi vardır | `issues/service.py:IssueService.create_for_trigger` | İkinci issue domain servisi yazılmaz |
| Tekilleştirme ve recurrence vardır | `issues/postgresql_repository.py:PostgreSQLIssueRepository.add_or_increment` | Advisory lock, row lock, increment ve reopen yolu korunur |
| State-machine vardır | `issues/service.py:start_investigation`, `reassign`, `resolve`, `record_verification`, `close` | Otomatik/manüel intake doğrudan status yazmaz |
| Audit atomikliği vardır | `PostgreSQLIssueRepository.add_or_increment(..., audit_outbox=...)` | Receipt ve yeni audit aynı transaction'a alınır |
| Kalıcı worker vardır | `jobs/worker.py:PersistentJobWorker`; `jobs/handlers.py:ExecutionJobHandler` | Yeni queue/daemon kurulmaz |
| Queue replay kabiliyeti vardır | `jobs/postgresql_repository.py`; `jobs/execution_command.py:PersistentExecutionCommandAdapter` | Execution terminal olsa bile bekleyen issue post-processing retry'da sürdürülebilir |
| Issue API/UI vardır | `api/app.py:get_issues`; `issues/IssuesPage.tsx`; `App.tsx:IssuesRoute` | Yeni üst seviye ekran/route açılmaz |

### 2.2 DS-03 kaynaklı zorunlu ön koşul

**HIGH_RISK / NO-GO:**
`src/veri_kalitesi/executions/postgresql_executor.py:
PostgreSQLRuleExecutionExecutor._execute_version` mevcut sorgu sonucunu
`passed_count=population`, `failed_count=0` ve `MeasurementStatus.PASSED` olarak
sabitler. Bu production adapter gerçek bir kalite başarısızlığı üretemediği için
DS-05'in otomatik kalite-issue kabul testi bugün geçemez.

Bu dosya DS-05 değişiklik listesine gizlice eklenmez. DS-03 düzeltmesi olarak,
DS-05 uygulamasından önce gerçek rule IR/threshold semantiğiyle en az bir
`eligible_for_auto_issue=true`, `failed_count>0`, `FAILED` veya izinli `WARNING`
sonucu üretebildiği production-path testiyle kanıtlanmalıdır. Fake executor ile
DS-05 GO verilmez.

### 2.3 Mevcut composition engeli

`src/veri_kalitesi/api/composition.py` `IssueService` oluştururken
`UnavailableIssueAssignmentResolver` bağlar. Bu fail-closed placeholder mevcut
issue yaşam döngüsü okumalarını korur, fakat otomatik veya manuel issue
oluşturamaz. `jobs/production.py:ProductionWorkerProviders` ise tanımlı olmasına
rağmen `create_production_worker` tarafından kullanılmaz. DS-05 production yolu:

- gerçek ownership assignment resolver;
- trusted, dar scope'lu issue service-context provider;
- gerçek assignee directory;
- API ve worker'da aynı PostgreSQL issue/audit yapısı

bağlanmadan çalıştırılamaz.

## 3. Tablolar, kolonlar ve migration

### 3.1 `data_quality_issues` değişiklikleri

| Yeni/değişen kolon veya kısıt | Tip / davranış | Amaç |
|---|---|---|
| `title` | `String(200)`, not null; trim length `1..200`, markup/control karakteri yok | Manuel ve otomatik issue için güvenli kullanıcı başlığı |
| `source_execution_id` | nullable FK → `rule_executions.execution_id` | Son issue occurrence'ının execution kanıtı; manuel issue'da null |
| `source_rule_version_id` | nullable FK → `rule_versions.rule_version_id` | Kalite trigger'ının rule-version kanıtı; teknik/manüel issue'da nullable |
| `source_event_id` | mevcut kolon, drop edilmez | En son işlenen source event ID; receipt kaynağı değildir |
| `ck_issue_source_event_type` | `QUALITY`, `TECHNICAL`, `MANUAL` | Manuel issue'yu kalite olayı gibi göstermemek |
| `ck_issue_trigger_type` | `QUALITY_THRESHOLD`, `CRITICAL_RULE_FAILURE`, `TECHNICAL_ERROR`, `MANUAL` | Manuel trigger semantiği |

İndeksler: `source_execution_id` ve `source_rule_version_id` için bounded detail/
kanıt sorgusu indeksleri eklenir. Mevcut unique
`deduplication_key_digest`, scope ve assignee/status indeksleri korunur.

Legacy issue başlığı `issue_no` üzerinden güvenli ve deterministik biçimde
backfill edilir. Legacy source referansları uydurulmaz; yeni FK kolonları null
kalır. Yeni automatic/manual kayıtlar için servis invariant'ı:

- `QUALITY`: execution ve rule-version referansı zorunlu;
- `TECHNICAL`: execution referansı zorunlu, rule-version opsiyonel;
- `MANUAL`: iki otomatik source referansı da null.

Legacy kayıtlar nedeniyle bu invariant doğrudan tüm tabloya katı CHECK olarak
uygulanmaz; yeni yazma yolu ve repository testleriyle zorlanır.

### 3.2 `issue_history` source-event receipt genişletmesi

Yeni bir `issue_trigger_receipts` tablosu açılmaz. Mevcut append-only history her
intake/recurrence olayını zaten sakladığı için receipt rolü burada tutulur:

| Yeni kolon/kısıt | Tip / davranış | Amaç |
|---|---|---|
| `source_event_id` | nullable `String(36)` | Otomatik event veya manuel idempotency olayının kalıcı receipt'i |
| `source_event_occurred_at` | nullable timestamptz | Geç/güncel recurrence kararının kanıtı |
| `source_event_payload_digest` | nullable `String(64)` | Aynı event ID'nin farklı payload ile tekrarını conflict yapmak |
| `uq_issue_history_source_event_id` | `source_event_id IS NOT NULL` partial unique index | Worker retry/restart'ta occurrence'ın ikinci kez artmasını engellemek |
| receipt consistency check | Üç receipt kolonu birlikte null veya birlikte dolu | Yarım receipt yazılmasını engellemek |

İlk create, repeat ve reopen history kaydı receipt alanlarını doldurur. Investigation,
assignment, resolution, verification ve closure history kayıtlarında bu alanlar
null kalır. Aynı `source_event_id` + aynı digest replay'i no-op olarak mevcut
issue'yu döndürür; aynı ID + farklı digest `IssueConflictError` olur. Replay yeni
history veya audit olayı üretmez.

### 3.3 Değişmeyecek tablolar

- `rule_execution_results`: `rule_result_id`, `execution_id`, `rule_version_id`,
  count/status ve dört eligibility kolonu zaten vardır; DDL eklenmez.
- `rule_executions`: teknik trigger ve job replay kaynağıdır; DDL eklenmez.
- `background_jobs`: mevcut `EXECUTION` işi dayanıklı zarf olarak kullanılır;
  `ISSUE_GENERATION` job type veya kolon eklenmez.
- `workers`: supported type yine handler map'inden türetilir; DDL değişmez.
- `quality_rules`, `rule_versions`, `datasets`, `data_sources`: assignment ve scope
  kanıtı olarak okunur; ownership kolonu eklenmez.
- `issue_relationships`, `issue_resolutions`, `issue_verifications`: mevcut
  state-machine kayıtlarıdır; DDL değişmez.
- `notification_events`, `notification_deliveries`: DS-09 kapsamıdır; DS-05
  migration'ına alınmaz.
- `audit_outbox`, `audit_events`: mevcut transactional audit yolu kullanılır.

### 3.4 Migration sırası

1. `data_quality_issues` için `title`, `source_execution_id` ve
   `source_rule_version_id` nullable/default-safe biçimde eklenir.
2. Legacy `title` değerleri güvenli `issue_no` özetiyle backfill edilir; ardından
   not-null ve veri-minimum title check'i eklenir.
3. Execution/rule-version FK ve indeksleri eklenir.
4. `ck_issue_source_event_type` ve `ck_issue_trigger_type` drop/recreate edilerek
   `MANUAL` eklenir.
5. `issue_history` receipt kolonları nullable eklenir.
6. Receipt consistency check ve partial unique index eklenir.
7. `issues/postgresql_repository.py:issue_tables()` runtime metadata'sı aynı
   kolon, FK, check ve indekslerle eşitlenir.
8. `api/composition.py:CURRENT_MIGRATION_HEAD` `20260806_18` yapılır;
   `REQUIRED_TABLES` değişmez çünkü yeni tablo yoktur.

Migration 01–17 dosyaları değiştirilmez. Legacy SQLite aktarım kodu yeni target
`title` alanını deterministik üretir; source receipt alanlarını geriye dönük
uydurmaz.

## 4. Backend servis ve repository envanteri

### 4.1 Kesin değişecek mevcut dosyalar

| Dosya | Sembol | Planlanan değişiklik |
|---|---|---|
| `src/veri_kalitesi/issues/models.py` | `IssueTriggerType`, `IssueSourceEventType`, `IssueTrigger`, `DataQualityIssue`, `IssueHistoryEntry`, `IssueAccessPolicy`; yeni `ManualIssueDraft` | MANUAL semantiği, title/source refs, eligibility/failure kanıtı, receipt alanları, producer/manual rol politikası |
| `src/veri_kalitesi/issues/contracts.py` | `IssueRepository.add_or_increment` | Source-event receipt ID/time/digest ile idempotent create-or-increment sözleşmesi |
| `src/veri_kalitesi/issues/postgresql_repository.py` | `IssueTables`, `issue_tables`, `add_or_increment`, mapper'lar | Migration 18 metadata'sı; receipt-first replay kontrolü; refs/title yazımı; atomik issue/history/audit |
| `src/veri_kalitesi/issues/service.py` | `IssueService.create_for_trigger`; yeni `create_manual`; validation/digest yardımcıları | Eligibility'yi ikinci sınırda doğrulama; USER/SERVICE rol+scope; manual idempotency; trusted assignment; notification'ı issue başarı sözleşmesinden ayırma |
| `src/veri_kalitesi/issues/migration.py` | `SQLiteIssueMigrator` | Legacy target title üretme; yeni nullable receipt/ref kolonlarını uydurmadan koruma |
| `src/veri_kalitesi/issues/__init__.py` | exports | Yeni modeller, resolver ve bridge export'ları |
| `src/veri_kalitesi/jobs/execution_command.py` | `PersistentExecutionCommandAdapter` | Terminal execution replay'inde permanent error yerine pending issue post-processing; bridge bitmeden job success dönmeme |
| `src/veri_kalitesi/jobs/production.py` | `ProductionWorkerProviders`, `create_production_worker` | Issue repository/service/bridge/resolver wiring; providers'ı gerçekten kullanma; dar scope SERVICE context |
| `src/veri_kalitesi/jobs/settings.py` | `PersistentJobSettings` | Audit/actor/issue policy version ve issue producer identity alanlarını boş değerlerde fail-fast doğrulama |
| `src/veri_kalitesi/jobs/entrypoint.py` | `main` | Production provider eksikliğinde fail-fast; development provider'ın production fallback olmaması |
| `src/veri_kalitesi/api/models.py` | `IssueListItemResponse`, `IssueListResponse`; yeni `IssueCreateRequest` | title/source refs, page action projection, bounded manual create/idempotency contract'ı |
| `src/veri_kalitesi/api/app.py` | yeni `IssueCreationService` protocol; `get_issues`; yeni `create_issue`; `_issue_actions` çevresi | İnce HTTP adapter, CSRF, ActorContext aktarımı, 201/error mapping, backend `CREATE_ISSUE` projection'ı |
| `src/veri_kalitesi/api/composition.py` | `create_application`, `PhaseBProviders`, head/preflight, `app.state.*` | Gerçek ownership resolver ve manual service wiring; head 18; placeholder create yolundan çıkar |
| `src/veri_kalitesi/api/development.py` | `DevelopmentIssueStore`, `create_development_api` | Yalnız development için manuel create contract'ı; production composition'a taşınmaz |

`issues/query.py:IssueQueryService` ve `list_issues_for_scopes` mevcut scope-safe
okuma yolunu korur. Yeni source referansları `DataQualityIssue` projection'ından
geldiği için ikinci query framework veya N+1 execution lookup servisi açılmaz.

### 4.2 Yeni dar kapsamlı dosyalar

| Yeni dosya | Sembol | Tek sorumluluk |
|---|---|---|
| `src/veri_kalitesi/issues/execution_bridge.py` | `ExecutionIssueTriggerAdapter`, `IssueGenerationPolicy`, `IssueGenerationSummary` | Persisted execution/result → veri-minimum quality/technical `IssueTrigger`; eligibility ve terminal-state kapısı |
| `src/veri_kalitesi/issues/assignment.py` | `OwnershipIssueAssignmentResolver` | Rule owner → dataset owner → source owner güven zinciri ve criticality/manuel priority politikası |

Bu iki sınıf yeni issue service/repository ailesi değildir. Biri bounded-context
adapter'ı, diğeri mevcut `IssueAssignmentResolver` portunun production
uygulamasıdır.

### 4.3 Dayanıklı execution job akışı

Yeni `ISSUE_GENERATION` job'ı açmak yerine mevcut `EXECUTION` job'ı tam iş birimi
olarak kullanılır:

1. `ExecutionService.run_for_execution_id` terminal execution/result kayıtlarını
   PostgreSQL'e yazar.
2. `PersistentExecutionCommandAdapter` aynı job handler çağrısı içinde
   `ExecutionIssueTriggerAdapter.process_execution(execution_id)` çağırır.
3. Her uygun result `rule_result_id` değerini source event/receipt ID olarak
   kullanır; teknik terminal olay `execution_id` kullanır.
4. Issue repository create/increment/history receipt/audit'i kendi kısa
   transaction'ında yazar.
5. Bütün trigger'lar tamamlandıktan sonra adapter `JobCompletionOutcome` döndürür
   ve worker mevcut job'ı tamamlar.
6. Proses 1 ile 5 arasında çökerse lease recovery aynı execution job'ını tekrar
   çalıştırır. Execution zaten terminalse gerçek sorgu yeniden yürütülmez;
   persisted sonuçlar bridge'e yeniden verilir. Receipt unique index'i daha önce
   tamamlanan trigger'ları no-op yapar.

Bu sınır execution ve issue transaction'larını yanlış biçimde tek uzun transaction
yapmaz; buna rağmen job completion'ı geciktirerek kayıp pencereyi kapatır. Yeni
queue tablosu, event bus veya proses-içi fire-and-forget callback açılmaz.

### 4.4 Trigger ve assignment sözleşmesi

`IssueTrigger` otomatik intake için en az şu güvenilir alanları taşır:

- `event_id`, `execution_id`, nullable `rule_version_id`;
- `trigger_type`, `scope_type`, `scope_id`;
- `eligible_for_auto_issue`, nullable `failed_count`, nullable
  `measurement_status`;
- `occurred_at`, `correlation_id`, veri-minimum `title` ve safe dedup key.

Kalite trigger'ında `eligible_for_auto_issue=true`, `failed_count>0`, official/
terminal-success execution, desteklenen measurement status ve dataset/rule/source
ilişkisi birlikte doğrulanır. Teknik trigger ayrı `IssueGenerationPolicy` bayrağı,
terminal `TECHNICAL_ERROR`/`TIMEOUT` ve source scope gerektirir; kalite sayaçlarını
taşımaz. `PARTIAL`, `CANCELLED`, shadow, passed veya uygunsuz sonuç issue üretmez.

`OwnershipIssueAssignmentResolver`:

- kalite trigger'ında rule-version → quality-rule owner;
- teknik trigger'da source owner;
- manuel dataset trigger'ında dataset owner, yoksa parent source owner;
- manuel source trigger'ında source owner

sırasını kullanır. ID, aktiflik ve hedef scope mevcut trusted
`IssueAssigneeDirectory` ile doğrulanır. Assignee request/job payload'ından
alınmaz. Sahip bulunamazsa issue açılmaz; job retry/dead-letter ile gözlenebilir
fail-closed hata üretir.

Worker context provider sözleşmesi
`issue_service_actor_context_provider(source_id, dataset_id, correlation_id) ->
ActorContext` olarak sabitlenir. Dönüş context'i trusted ve süresi geçmemiş
`ActorType.SERVICE`, `ISSUE_PRODUCER` rolü, persisted correlation ID, hedef source
ve varsa hedef dataset scope'u ile doğru actor-policy version taşır; privileged
veya geniş enterprise fallback kullanmaz. Development compose bu provider'ı
development issuer ve sabit worker kimliğiyle kurabilir. Production provider
`ProductionWorkerProviders` üzerinden zorunlu enjekte edilir; job payload'ı aktör,
rol veya scope üretemez.

### 4.5 Notification ayrımı

`IssueService.create_for_trigger` bugün issue commit ve audit publish sonrasında
`_publish_notification` çağırır; production composition ise DS-09 yokken
`UnavailableIssueNotificationPublisher` bağlar. Sonuç: issue kalıcı olduğu hâlde
çağrı hata verir ve job retry'ı gerçek recurrence gibi occurrence artırabilir.

DS-05'te issue create/increment başarısı notification başarısına bağlı olmaz.
Notification publisher fake/no-op ile başarılı gösterilmez; DS-09 kurulmadığı
sürece teslimat iddiası üretilmez. DS-09 daha sonra kalıcı issue/audit olayından
abonelik ve delivery zincirini kurar. Mevcut issue assignment notification
davranışı production'da gerçek provider varsa korunabilir, fakat DS-05 worker
completion kararını değiştiremez.

## 5. Endpoint envanteri

### 5.1 Yeni endpoint

| Endpoint | HTTP | Request/response ve backend davranışı |
|---|---|---|
| `/api/v1/issues` | `POST`, 201 | `IssueCreateRequest(title, scope_type, scope_id, priority, idempotency_key)`; CSRF + trusted USER context + manual creator rolü + exact scope; assignee backend ownership resolver'dan; `IssueMutationResponse` |

Idempotency anahtarı mevcut execution/discovery API deseni gibi body'de taşınır,
backend'de normalize/digest edilir ve ham değer saklanmaz. Aynı aktör + aynı
idempotency anahtarı + aynı payload mevcut issue'yu döndürür; farklı payload 409
olur.

### 5.2 Değişecek mevcut endpoint

| Endpoint | Değişiklik |
|---|---|
| `GET /api/v1/issues` | Item'a `title`, nullable `source_execution_id`, nullable `source_rule_version_id`; response'a backend hesaplı sayfa `available_actions` (`CREATE_ISSUE`) |

`GET /api/v1/issues` source/dataset scope filtresini
`issues/query.py:IssueQueryService.list_for_actor` üzerinden korur. Boş scope tüm
issue'lar anlamına gelmez. Source-event receipt/dedup digest response'a çıkmaz.

### 5.3 Değişmeyecek endpoint'ler

- `/api/v1/issues/{id}/investigation`
- `/api/v1/issues/{id}/assignment-options`
- `/api/v1/issues/{id}/assignment`
- `/api/v1/issues/{id}/resolution`
- `/api/v1/issues/{id}/verification`
- `/api/v1/issues/{id}/closure`
- `/api/v1/issues/{id}/investigation/evidence`

Otomatik issue üretimi için public/internal HTTP endpoint açılmaz. Worker doğrudan
application portunu kullanır; request body'den SERVICE actor veya eligibility
kabul edilmez.

## 6. Frontend ekran ve çağrı envanteri

### 6.1 Değişecek ekranlar

| Dosya | Değişiklik |
|---|---|
| `frontend/src/issues/IssuesPage.tsx` | Backend `CREATE_ISSUE` action varsa “Yeni Sorun” butonu; title, source/dataset ve priority alanlı dialog; pending/success/validation/conflict/technical durumları; source execution/rule referansları ve occurrence görünümü |
| `frontend/src/App.tsx` | `IssuesRoute` manual create mutation'ını gerçek API'ye bağlar; yetkili catalog/source seçeneklerini yükler; başarılı create'i listeye ekler/yeniler |

Yeni route veya ikinci issue ekranı açılmaz. Existing investigation, assignment,
resolution, verification ve closure diyalogları korunur.

### 6.2 Değişecek frontend istemci/model dosyaları

| Dosya | Değişiklik |
|---|---|
| `frontend/src/issues/model.ts` | `MANUAL` source/trigger, `title`, source refs, page `CREATE_ISSUE` action ve `IssueCreateInput` tipleri/mapping |
| `frontend/src/issues/api.ts` | `createIssue` POST çağrısı; mevcut CSRF proof ve `IssueApiError` 401/403/409/422/5xx mapping'i |
| `frontend/src/catalog/api.ts` | Değişmez; yetkili dataset seçimi için mevcut `listCatalogDatasets` yeniden kullanılır |
| `frontend/src/dataSources/api.ts` | Değişmez; yetkili source listesi için mevcut çağrı yeniden kullanılır |

`syntheticIssues` yalnız açık development `?state=`/story/test yolunda kalabilir.
Production GET veya POST hatasında sentetik issue, sahte assignee ya da başarılı
create sonucu gösterilmez.

## 7. Permission, scope ve audit

### 7.1 Backend permission sözleşmesi

`issues/models.py:IssueAccessPolicy` mevcut policy version ve actor-type kapısını
şu rol kümeleriyle genişletir:

| Policy alanı | Rol | Kullanım |
|---|---|---|
| `producer_roles` | `ISSUE_PRODUCER` | Otomatik quality/technical trigger |
| `manual_creator_roles` | `DATA_STEWARD`, `DATA_OWNER` | Manuel issue oluşturma |

Otomatik context trusted, süresi geçmemiş, non-privileged
`ActorType.SERVICE`; doğru actor policy version/correlation, `ISSUE_PRODUCER`
rolü ve trigger scope'unu içeren permitted source/dataset kümeleri taşımalıdır.
Manuel context `ActorType.USER`, doğru rol ve exact source/dataset scope'u
taşımalıdır. `can_view_enterprise` veya frontend action tek başına mutasyon izni
değildir; servis policy'si son karardır.

Rule-version → rule → dataset → source zinciri repository'den yeniden doğrulanır.
Payload'taki `scope_id`, execution veya rule referansının yerine geçmez.

### 7.2 Audit olayları ve transaction sınırı

| Olay | Aktör | Aynı transaction'daki kayıt |
|---|---|---|
| `DATA_QUALITY_ISSUE_TRIGGER_PROCESSED` | SERVICE | issue create veya occurrence increment + receipt history |
| `DATA_QUALITY_ISSUE_REOPENED` | SERVICE | CLOSED → WAITING_FOR_RESOLUTION + recurrence receipt/history |
| `DATA_QUALITY_ISSUE_LINKED` | SERVICE | Mevcut predecessor/successor relationship kaydı varsa |
| `DATA_QUALITY_ISSUE_MANUALLY_CREATED` | USER | manual issue + initial history receipt |

Mevcut event isimleri consumer/test uyumu için korunur. Aynı source event replay'i
no-op olduğundan ikinci audit olayı yazmaz. Audit prepare/stage başarısızsa issue,
history, relationship ve receipt birlikte rollback olur; `publish_pending`
commit'ten sonra çalışır.

Audit/job/problem payload'larında ham idempotency anahtarı, ham dedup key,
assignee kimliği, title serbest metni, sample/evidence değeri, secret veya
connection bilgisi bulunmaz. Yalnız sayım, enum, digest ve correlation gibi
veri-minimum özetler kullanılır.

## 8. Test envanteri

`docs/testing/AGENTS.md` gereği yeni testler FR/UC/AC kimlikleri taşır; kalite
başarısızlığı ve teknik hata farklı beklenen sonuçlarla doğrulanır.

### 8.1 Değişecek backend testleri

| Dosya | Eklenecek/doğrulanacak senaryo |
|---|---|
| `tests/unit/test_issues.py` | Eligibility fail-closed; manual USER rol/scope; ownership assignment; same-event no-op, distinct recurrence increment, late replay; notification yokluğunun issue başarısını bozmaması; data-minimum audit |
| `tests/unit/test_issue_api.py` | POST 201; CSRF; idempotent replay/409; 401/403/422/5xx; page CREATE_ISSUE projection; title/source refs response minimization |
| `tests/unit/test_persistent_job_handlers.py` | Execution handler issue post-processing tamamlanmadan job success dönmüyor; bridge teknik hatası retry sınıfına gidiyor |
| `tests/unit/test_persistent_job_worker.py` | Terminal execution replay'i gerçek sorguyu yeniden çalıştırmadan receipt'leri tamamlıyor; lease/retry/dead-letter ve worker registry korunuyor |
| `tests/integration/test_postgresql_issue_mutations.py` | Receipt unique/concurrency; same ID same digest no-op; same ID different digest conflict; issue/history/audit rollback; source refs/title mapping |
| `tests/integration/test_postgresql_issue_migration.py` | Legacy SQLite aktarımında title üretimi, mevcut history korunması ve yeni nullable receipt alanları |
| `tests/integration/test_application_composition.py` | API/worker aynı PG issue/audit yapısı; gerçek resolver/context provider; unavailable placeholder create yolunda değil; head 18/preflight |

### 8.2 Yeni backend testleri

| Yeni dosya | Amaç |
|---|---|
| `tests/unit/test_execution_issue_bridge.py` | Quality/critical/technical trigger mapping; passed/shadow/partial/cancel/ineligible skip; source/rule ownership ve veri-minimum dedup/title |
| `tests/unit/test_issue_assignment.py` | Rule owner, dataset owner, source owner fallback; criticality priority; inactive/missing/out-of-scope owner fail-closed |
| `tests/integration/test_postgresql_issue_generation_migration.py` | 17→18 upgrade; title backfill/check; MANUAL constraints; source FK/index; receipt partial unique ve consistency check |
| `tests/integration/test_ds05_issue_generation.py` | Gerçek PG execution result → aynı execution job → worker → issue create/increment/reopen → GET API + audit; restart/retry/concurrency |

DS-03 giriş kapısı için ayrıca
`tests/integration/test_postgresql_execution_persistence.py` veya yeni
production-executor integration testinde gerçek PostgreSQL fixture üzerinde en az
bir `failed_count>0` official result kanıtlanmalıdır. Bu test fake executor
kullanırsa DS-05 application testi kabul kanıtı değildir.

### 8.3 Frontend testleri

| Dosya | Senaryo |
|---|---|
| `frontend/src/issues/model.test.ts` | MANUAL/title/source refs/page action mapping; unknown enum fail-closed gösterim |
| `frontend/src/issues/api.test.ts` | create request, CSRF, idempotency, 201 ve safe 401/403/409/422/5xx mapping |
| `frontend/src/issues/IssuesPage.test.tsx` | CREATE_ISSUE yoksa buton yok; form validation; source/dataset seçenekleri; pending/success/error; occurrence ve source refs; klavye/dialog erişilebilirliği |
| `frontend/e2e/issues.spec.ts` | Mock contract ile manuel create interaction, conflict ve unauthorized state; production kanıtı sayılmaz |
| `frontend/e2e/issues-live.spec.ts` (yeni) | Gerçek compose API/worker/PostgreSQL ile execution kaynaklı issue görünümü ve manuel create smoke |

Canlı test corpus'u için `scripts/seed_database.py` yeni title/ref modellerine
uyarlanır ve ayrı bir test senaryosunda geçerli UUID owner'lı, official,
`eligible_for_auto_issue=true`, `failed_count>0`, tutarlı `FAILED` sonucu üretir.
Seed script doğrudan issue ekleyerek automatic bridge kabulünü taklit etmez.
`infra/development/compose.yaml` yalnız development issue-producer
kimliği/policy ayarlarını verir; production credential veya fake directory
tanımlamaz.

### 8.4 Korunacak testler

- `test_issues.py` içindeki mevcut create, assignment, recurrence/reopen,
  investigation, resolution, verification, closure ve audit rollback testleri.
- `test_postgresql_issue_mutations.py` içindeki advisory-lock ve transactional
  audit testleri.
- `test_postgresql_issue_persistence.py` scope/query persistence testleri.
- `test_postgresql_job_queue.py` queue idempotency, claim, lease ve retry testleri.
- `test_postgresql_execution_persistence.py` execution/result eligibility
  kalıcılık testleri.
- Mevcut issue frontend lifecycle ve accessibility testleri.

Notification birlikte oluşturma bekleyen eski birim testleri production DS-05
kanıtı olarak kullanılmaz. DS-09 kapsamını DS-05'e çekmeden, issue persistence ve
notification teslimat sonucu ayrı assertion'lara bölünür.

### 8.5 Çalıştırılacak test komutları

- `python3 -m pytest -q tests/unit/test_issues.py tests/unit/test_issue_api.py`
- `python3 -m pytest -q tests/unit/test_execution_issue_bridge.py tests/unit/test_issue_assignment.py`
- `python3 -m pytest -q tests/unit/test_persistent_job_handlers.py tests/unit/test_persistent_job_worker.py`
- PostgreSQL test URL ile migration 18, issue mutation, application composition,
  execution persistence ve DS-05 application integration testleri.
- `cd frontend && npm test -- --run`
- `cd frontend && npm run build`
- `cd frontend && npx playwright test e2e/issues.spec.ts`
- Canlı development compose profiliyle
  `cd frontend && npx playwright test e2e/issues-live.spec.ts`.

## 9. Kesin dosya değişikliği özeti

### 9.1 Değişecek

- `alembic/versions/20260806_18_issue_generation.py` (yeni)
- `src/veri_kalitesi/issues/{models,contracts,postgresql_repository,service,migration,__init__}.py`
- `src/veri_kalitesi/issues/{execution_bridge,assignment}.py` (yeni)
- `src/veri_kalitesi/jobs/{execution_command,production,settings,entrypoint}.py`
- `src/veri_kalitesi/api/{models,app,composition,development}.py`
- `frontend/src/issues/{model,api,IssuesPage}.ts(x)`
- `frontend/src/App.tsx`
- `scripts/seed_database.py` — yeni required issue alanları ve gerçek live-test
  başlangıç corpus'u; automatic issue satırı seed edilmez
- `infra/development/compose.yaml` — development worker issue-producer
  kimliği/policy ayarları
- §8'de listelenen backend/frontend/E2E testleri
- `tests/support/legacy_sqlite_issue_repository.py` — yalnız legacy/test
  parity; production repository değildir

### 9.2 Ön koşul olarak ayrıca düzeltilmesi gereken

- `src/veri_kalitesi/executions/postgresql_executor.py`
- Gerçek negative-result semantics testinin yerleştirileceği
  `tests/integration/test_postgresql_execution_persistence.py` veya dar
  yeni production-executor integration testi

Bu iki kalem DS-03 düzeltmesidir; DS-05 değişiklik metriğine karıştırılmaz, fakat
tam production E2E öncesi zorunludur.

### 9.3 Değişmeyecek

- Migration 01–17 dosyaları
- `rule_execution_results` ve `rule_executions` DDL'i
- `background_jobs`, `workers`, dead-letter ve lease/progress DDL'i
- `jobs/worker.py`, `jobs/postgresql_repository.py`,
  `jobs/composition.py:create_persistent_job_runtime` çekirdeği
- Issue investigation/resolution/verification/closure state-machine kuralları
- Rule approval, data-source activation ve metadata discovery state-machine'leri
- Notification tabloları, kanal adapter'ları ve teslimat ekranları
- Skor, schedule, SLA, exception, contract ve ServiceNow alanları
- Production'da SQLite/in-memory/fake assignment, issue veya executor fallback'i

## 10. Kesin uygulama sırası

1. DS-03 production executor negative-result giriş kapısı ve testi.
2. Migration 18: title/source refs, MANUAL constraints ve history receipt.
3. Domain modelleri, validation ve repository contract/runtime metadata'sı.
4. PostgreSQL receipt-first create/increment/replay ve audit atomikliği.
5. Ownership assignment resolver ve unit testleri.
6. Execution→issue trigger adapter ve eligibility/technical policy testleri.
7. `PersistentExecutionCommandAdapter` terminal replay/post-processing zinciri.
8. Worker settings, production providers, composition ve entrypoint fail-fast.
9. Manual `IssueService.create_manual`, API model/route ve production composition.
10. Backend unit, migration ve PostgreSQL application-chain testleri.
11. Frontend model/API ve `IssuesPage` create dialog/wiring.
12. Development seed/compose issue-producer ayarları.
13. Frontend unit/build ve mock E2E.
14. Gerçek compose live E2E: automatic issue, manual issue, retry ve audit.

Migration ve receipt concurrency testleri geçmeden worker wiring'e; backend
permission/scope testleri geçmeden frontend create akışına; gerçek negative-result
kanıtı geçmeden live production smoke'a geçilmez.

## 11. Envanter kararı

**CONDITIONAL GO — DS-05 değişiklik envanteri uygulanabilir.** Mevcut issue
state-machine, PostgreSQL advisory/row lock repository'si, transactional audit ve
DS-03 worker çekirdeği yeniden kullanılabilir. Yeni issue tablosu, queue veya
notification hattı gerekli değildir.

Uygulama öncesindeki iki kesin kapı:

1. `PostgreSQLRuleExecutionExecutor` gerçek başarısız sonuç üretebilmelidir.
2. Worker production composition gerçek assignee directory ve dar scope'lu
   trusted issue SERVICE context sağlayabilmelidir.

Bu kapılardan biri placeholder/fake ile geçilirse, same-event receipt olmadan
occurrence artırılırsa, notification hatası issue job retry'ına çevrilirse veya
permission yalnız frontend action'a bırakılırsa dilim **NO-GO** olur.
