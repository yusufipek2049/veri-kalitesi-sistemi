---
type: functional-audit-work
stage: "13 — DS-03 Değişiklik Envanteri"
scope: slice-ds03-change-inventory
inputs:
  - 12-Third-Slice-Decision.md
  - 11-Slice-DS02-Change-Inventory.md
  - 07-Implementation-Waves.md
  - ../04-Functional-Gap-Inventory.md
  - ../13-Implementation-Roadmap.md
project: Veri Kalitesi İzleme ve Skorlama Sistemi
branch: agent/36h1-persistent-job-core
created_at: 2026-08-05
---

# 13 — DS-03 Değişiklik Envanteri

> Seçilen üçüncü dilim: **DS-03 — Çalıştırma uçtan uca (GAP-002 + GAP-017)**.
> Bu belge değişecek tablo, kolon, servis, endpoint, ekran ve testleri dosya ve
> sembol düzeyinde dondurur. Uygulama veya kaynak kod değişikliği içermez.

---

## 1. Envanter özeti

| Katman | Karar |
|---|---|
| Yeni tablo | `workers` |
| Değişen tablo | `background_jobs` |
| Yeni migration | Önerilen `20260805_16_execution_worker_runtime.py`; `down_revision = "20260805_15"` |
| Yeniden kullanılacak tablolar | `rule_executions`, `rule_execution_attempts`, `rule_execution_results`, `job_dead_letters`, `source_usage_policies`, `audit_outbox`, `audit_events` |
| Yeni generic altyapı | Yok; mevcut PostgreSQL queue, worker, execution repository ve transactional audit kullanılır |
| Yeni HTTP komutu | Yok; mevcut start/cancel endpoint'leri production servislere bağlanır |
| Yeni HTTP okuması | `GET /api/v1/executions/{execution_id}`; terminal sonuç özeti için gereklidir |
| Değişen ekran | Mevcut `/executions` / `ExecutionsPage` |
| Production süreci | Mevcut `create_persistent_job_runtime()` kullanan ayrı worker entrypoint/container |

Roadmap'teki “Migration 15” adı artık geçersizdir; migration 15 DS-01 tarafından
kullanılmaktadır. DS-03 aynı revision numarasını yeniden kullanmaz.

## 2. Tablolar, kolonlar ve migration

### 2.1 Yeni `workers` tablosu

**Önerilen dosya:**
`alembic/versions/20260805_16_execution_worker_runtime.py`

| Kolon | Tip / kısıt | Kullanım |
|---|---|---|
| `worker_id` | `String(128)`, PK | `BackgroundJob.claimed_by` ile aynı worker kimliği |
| `hostname` | `String(255)`, not null | Süreç/düğüm görünürlüğü |
| `capacity` | integer, `> 0` | İlan edilen eşzamanlı iş kapasitesi |
| `supported_job_types` | JSON, not null | Bu dilimde en az `EXECUTION`; `REPORT` yalnız gerçek provider varsa |
| `state` | string, check | `STARTING`, `RUNNING`, `DRAINING`, `STOPPED`, `UNHEALTHY` |
| `started_at` | timestamptz, not null | Runtime başlangıcı |
| `last_seen_at` | timestamptz, not null | Worker sağlık heartbeat'i |
| `stopped_at` | timestamptz, nullable | Kontrollü kapanma zamanı |
| `version` | integer, `>= 0` | Eşzamanlı heartbeat/state güncelleme koruması |

İndeks: `(state, last_seen_at)`. Ayrı `worker_capabilities` tablosu açılmaz;
bu dilimin sorgu ve yaşam döngüsü ihtiyacı tek satır/JSON ile karşılanır.
`background_jobs.claimed_by` üzerine foreign key eklenmez: tarihsel worker kimliğini
korumak ve mevcut lease/reaper akışını worker satırı silme politikasına bağlamamak
gerekir.

### 2.2 `background_jobs` kolon değişiklikleri

Mevcut sahip dosyalar:

- `alembic/versions/20260728_08_job_queue.py`
- `alembic/versions/20260729_09_job_lifecycle.py`
- `src/veri_kalitesi/jobs/postgresql_repository.py:job_tables`
- `src/veri_kalitesi/jobs/models.py:BackgroundJob`

08 ve 09 migration'ları değiştirilmez; ileri değişiklik yalnız migration 16'da
yapılır.

| Kolon/kısıt | Değişiklik |
|---|---|
| `status` check | Mevcut değerlere `BLOCKED` eklenir |
| `progress_percent` | small integer, not null, default `0`, check `0 <= value <= 100` |
| `blocked_reason_code` | `String(100)`, nullable |
| `blocked_until` | timestamptz, nullable; tekrar uygunluk zamanı |
| durum tutarlılığı | `BLOCKED` ise reason zorunlu; diğer durumlarda blocked alanları temizlenir |
| claim indeksi | `BLOCKED`/`blocked_until` tekrar uygunluğunu kapsayacak biçimde güncellenir |

`BLOCKED`, terminal hata değildir. Süresi gelen satır yeniden claim adayı olur;
kota/pencere engeli kalkmamışsa yeni bir teknik deneme tüketmeden tekrar ertelenir.
`progress_percent` yalnız aktif lease sahibi tarafından optimistic `version` guard
ile güncellenir.

### 2.3 Şeması değişmeyecek mevcut tablolar

| Tablo | Kullanım | Sahip dosya |
|---|---|---|
| `rule_executions` | Başlatma, durum ve iptal | `20260724_04_execution_baseline.py` |
| `rule_execution_attempts` | Deneme geçmişi | aynı migration |
| `rule_execution_results` | Terminal kural sonuçları | `20260724_04_execution_baseline.py`, kolon ilaveleri `20260730_12_rule_ir_shadow_evidence.py` |
| `job_dead_letters` | Deneme sınırı sonrası kalıcı kayıt | `20260729_09_job_lifecycle.py` |
| `source_usage_policies` | Kota, izin ve deadline çözümleme | `20260724_05_scheduling_and_policy_baseline.py`, `20260729_10_source_policy_deadlines.py` |
| `audit_outbox` / `audit_events` | Transactional olay ve kalıcı audit okuması | mevcut audit migration'ları |

`dead_letter_records` adında yeni veya mevcut bir tablo yoktur; doğru fiziksel ad
`job_dead_letters`'dır. Yeni bir dead-letter tablosu ya da tablo rename'i gereksizdir.
Migration 11–15'in DDL'i değiştirilmez.

### 2.4 Migration sırası

1. Migration 16 `workers` tablosunu oluşturur.
2. `background_jobs` yeni kolonları önce nullable/default-safe biçimde eklenir.
3. Mevcut satırlar `progress_percent = 0` ile backfill edilir.
4. Eski status check kaldırılıp `BLOCKED` içeren check ve blocked tutarlılık check'i kurulur.
5. Claim indeksi yeni uygunluk yoluna göre değiştirilir.
6. `api/composition.py:CURRENT_MIGRATION_HEAD` `20260805_16` yapılır.
7. Startup preflight'a `background_jobs`, `job_dead_letters`, `workers` ve
   `source_usage_policies` eklenir.

## 3. Backend servis ve repository envanteri

### 3.1 Kesin değişecek dosyalar

| Dosya | Sembol | Planlanan değişiklik |
|---|---|---|
| `src/veri_kalitesi/jobs/models.py` | `JobStatus`, `BackgroundJob`; yeni `WorkerState`, `WorkerRegistration` | `BLOCKED`, progress/engel alanları ve worker yaşam döngüsü modeli |
| `src/veri_kalitesi/jobs/postgresql_repository.py` | `JobTables`, `job_tables`, `PostgreSQLJobQueueRepository.claim_next` | `workers` metadata'sı; blocked/progress mapping; claim + lease + `JOB_CLAIMED` outbox'ını aynı transaction'da yazma |
| aynı | yeni worker/progress metotları | `register_worker`, `heartbeat_worker`, `begin_drain`, `stop_worker`, `update_progress`, `block_until`; optimistic version/lease sahipliği |
| `src/veri_kalitesi/jobs/worker.py` | `PersistentJobWorker.run_forever`, `run_once` | Kayıt/heartbeat/drain; policy reddini terminal teknik hataya çevirmek yerine `BLOCKED`; claim audit için service actor |
| `src/veri_kalitesi/jobs/composition.py` | `PersistentJobRuntime`, `create_persistent_job_runtime` | Yeni registry/repository yolunu bağla; yalnız verilen gerçek handler'ları kaydet; in-memory/fake fallback ekleme |
| `src/veri_kalitesi/jobs/handlers.py` | `CancellableExecutionCommand`, `ExecutionJobHandler` | Progress callback ve cancellation'ı gerçek execution komutuna aktar; handler state-machine sahibi olmaz |
| `src/veri_kalitesi/executions/service.py` | `ExecutionService` | Belirli `execution_id` için mevcut doğrulama/sonuç yazma mantığını yeniden kullanan çalışma metodu; ikinci kez execution claim etme |
| `src/veri_kalitesi/executions/postgresql_repository.py` | mevcut status/result metotları | Worker komutunun belirli execution'ı lease/state guard ile başlatıp tamamlaması; `list_results` yeniden kullanılır |
| `src/veri_kalitesi/executions/postgresql_executor.py` | yeni `PostgreSQLRuleExecutionExecutor` | `ExecutionExecutor` protocol'ünün somut production implementation'ı; `DQ_RULE_IR_V1` planlarını aktif PostgreSQL kaynağında salt okunur yürütür |
| `src/veri_kalitesi/data_sources/postgresql.py` | `PostgreSQLDriver`, `PostgreSQLConnector` | Secret verilmiş aktif kaynakta sürümlü rule planı yürütme portunu connector sınırında açar |
| `src/veri_kalitesi/data_sources/postgresql_driver.py` | `SQLAlchemyPostgreSQLDriver.execute_rule_plan` | Template/custom-SQL planını read-only connection, identifier quoting, statement timeout ve cancellation ile çalıştırır; sayaç/evidence döndürür |
| `src/veri_kalitesi/api/postgresql_execution.py` | `PostgreSQLExecutionStartService`, `PostgreSQLExecutionCancelService` | Trusted `ActorContext`, rol/scope, aktif-en-son kural sürümü ve aktif kaynak doğrulaması; istemci idempotency anahtarı; replay'de aynı execution/job |
| `src/veri_kalitesi/executions/query.py` | `ExecutionQueryService` | `get_for_actor` ve sonuç detayı; execution'ın tüm kaynaklarının izinli kapsamda kalması |
| `src/veri_kalitesi/api/models.py` | execution request/response modelleri | `idempotency_key`; progress/blocked/action alanları; execution detail/result modelleri |
| `src/veri_kalitesi/api/app.py` | execution service protocol'leri ve üç route | ActorContext'i servise geçir; start/cancel backend role/scope kontrolünden geçsin; detail route'u; GET'te CSRF proof |
| `src/veri_kalitesi/api/composition.py` | `REQUIRED_TABLES`, `create_application`, `app.state.*` | PG job repository ile start/cancel/detail servislerini bağla; eksik provider'da başarılı fake yol açma |
| `src/veri_kalitesi/api/settings.py` | `ApplicationSettings` | Execution command policy sürümü ve boş olamaz rol politikası sürümü |
| `src/veri_kalitesi/jobs/__init__.py` | exports | Yeni worker model/settings/entrypoint sembollerini dışa aktar |
| `pyproject.toml` | `[project.scripts]` | Worker executable komutu; `PersistentJobWorker.run_forever`'a gerçek çağıran sağlar |
| `infra/development/compose.yaml` | yeni `worker` service | Migration tamamlandıktan sonra aynı PostgreSQL/schema/secret mount ile worker başlat; API prosesine gömme |
| `infra/application/Dockerfile` | runtime image içeriği | Worker entrypoint'inin aynı immutable image'dan çalışabilmesini sağla; varsayılan API CMD korunur |

### 3.2 Yeni, dar kapsamlı production composition dosyaları

| Önerilen dosya | Sembol | Gerekçe |
|---|---|---|
| `src/veri_kalitesi/jobs/entrypoint.py` | `main`, signal/drain yönetimi | `run_forever` için eksik executable process sınırı; API app lifecycle'ına worker thread eklenmez |
| `src/veri_kalitesi/jobs/settings.py` | `PersistentJobSettings.from_environment` | Worker ID, hostname, capacity, lease, idle wait ve shutdown grace değerlerini fail-fast doğrular |
| `src/veri_kalitesi/jobs/execution_command.py` | `PersistentExecutionCommandAdapter` | Queue'nun `CancellableExecutionCommand` portunu mevcut `ExecutionService`/PG repository yoluna bağlayan application adapter |
| `src/veri_kalitesi/jobs/production.py` | `ProductionWorkerProviders`, `create_production_worker` | Somut `PostgreSQLRuleExecutionExecutor` ile catalog/source/secret bağımlılıklarını composition root'ta zorunlu tutar |

Bu adapter'lar yeni queue veya ikinci execution servisi değildir. Özellikle
`ExecutionService.run_next()` doğrudan handler olarak kullanılmaz: o metod
`rule_executions` üzerinde ikinci bir claim yapar; queue tarafından zaten seçilmiş
`execution_id` ile çalışmak gerekir.

### 3.3 Production executor kararı

Repository'de `ExecutionExecutor` yalnız protocol'dür. DS-03 bu portu test fake'i
veya no-op ile değil, yeni
`executions/postgresql_executor.py:PostgreSQLRuleExecutionExecutor` ile kapatır.

Somut provider'ın bağımlılıkları ve sınırı:

- `PostgreSQLRuleRepository`: aktif/en-son `RuleVersion` ve `DQ_RULE_IR_V1` planı;
- `PostgreSQLDataSourceRepository`: dataset, field ve aktif source metadata'sı;
- `SecretResolver`: yalnız execution anında secret çözümü; secret job payload,
  audit veya result tablosuna yazılmaz;
- `PostgreSQLConnector(SQLAlchemyPostgreSQLDriver())`: TLS/read-only bağlantı,
  identifier quoting, connection/query timeout ve driver cancellation;
- sonuç: her sürüm için mevcut `RuleResultComputation`; kalıcılığı yine
  `ExecutionService` ve `PostgreSQLExecutionRepository` yapar.

Provider, `RuleType` değerlerinin tamamını sürümlü IR üzerinden ele alır:
`REQUIRED`, `UNIQUE`, `RANGE`, `REGEX`, `FRESHNESS`,
`REFERENTIAL_INTEGRITY`, `CROSS_TABLE_CONSISTENCY` ve `CUSTOM_SQL`. Desteklenmeyen
IR version/operator başarı veya boş sonuç üretmez; kalıcı ve sınıflandırılmış
`ExecutionTechnicalError` verir. Custom SQL mevcut read-only doğrulamasından tekrar
geçer ve tanımlı row/evidence limitini aşamaz.

`ProductionWorkerProviders.execution_executor` alanının concrete tipi
`PostgreSQLRuleExecutionExecutor` olur ve `create_production_worker` bunu zorunlu
alır. Eksik provider'da worker process fail-fast çıkar; unit fake'i, no-op veya
in-memory executor composition root'a taşınmaz.

`create_persistent_job_runtime()` bugün zorunlu `ReportWorker` ister, ancak rapor
asenkronlaştırma DS-12 kapsamındadır. `REPORT` handler yalnız gerçek
`ReportWorker` verilirse kaydedilir; worker'ın `supported_job_types` değeri gerçek
handler anahtarlarından türetilir.

Bu somut provider ve connector yürütme metodu uygulamaya dâhil edilmeden
“API → queue → worker → `rule_execution_results`” production yolu **NO-GO**'dur.

#### `create_persistent_job_runtime` kesin imza değişikliği

Mevcut factory korunur; ikinci bir runtime factory açılmaz. İmza aşağıdaki
anlama gelecek biçimde değiştirilir:

```python
def create_persistent_job_runtime(
    session_factory: SessionFactory,
    *,
    transactional_audit: PostgreSQLTransactionalAudit,
    execution_command: CancellableExecutionCommand,
    worker_id: str,
    worker_hostname: str,
    worker_capacity: int,
    lease_policy: JobLeasePolicy,
    reprocess_policy: DeadLetterReprocessPolicy,
    report_worker: ReportWorker | None = None,
    source_types_by_id: Mapping[str, str] | None = None,
    schema: str = DEFAULT_SCHEMA_NAME,
) -> PersistentJobRuntime: ...
```

- `execution_command` DS-03 worker'ında zorunludur.
- Mevcut zorunlu `report_worker` keyword'ü opsiyonel olur; `None` ise `REPORT`
  handler kaydedilmez.
- Worker kimliği, hostname ve capacity `workers` kaydı ile worker nesnesine aynı
  factory tarafından verilir.
- `supported_job_types`, oluşturulan handler map'inin anahtarlarından türetilir;
  caller'dan ayrıca ve çelişebilir bir liste alınmaz.
- Çağıranlar ve testler keyword-only imzaya göre birlikte güncellenir; geçici
  overload veya legacy ikinci factory bırakılmaz.

### 3.4 Yeniden kullanılacak, yeniden yazılmayacak yapı

- `jobs/postgresql_repository.py` içindeki SKIP LOCKED, lease, retry,
  cancellation, dead-letter ve expired-claim metotları.
- `jobs/lifecycle.py:DeadLetterReprocessService` (operatör endpoint'i DS-11'dir).
- `jobs/composition.py:create_persistent_job_runtime`.
- `jobs/handlers.py:ExecutionJobHandler`.
- `executions/postgresql_repository.py:PostgreSQLExecutionRepository` ve
  `list_results`.
- `api/postgresql_execution.py` içindeki execution + job + audit ortak transaction
  deseni.
- `audit:PostgreSQLTransactionalAudit`; ayrı worker audit tablosu açılmaz.
- `source_usage_policies`; yeni kota tablosu açılmaz.

## 4. Permission, scope, state-machine ve audit

### 4.1 İnsan komutları

`ExecutionStartService` ve `ExecutionCancelService` protokolleri `actor_id: str`
yerine trusted `ActorContext` alır. Backend aşağıdakileri servis katmanında doğrular:

- context güvenilir, süresi geçmemiş ve policy version eşleşiyor;
- aktör execution başlatma/iptal rolünde;
- payload'daki tüm `source_ids`, `permitted_source_ids` alt kümesi;
- seçilen sürümler aktif kuralların en son sürümleri;
- kural dataset'lerinden türetilen kaynaklar payload ile tam eşleşiyor ve aktif;
- iptal edilecek execution'ın tüm source scope'u aktör kapsamında;
- terminal execution iptal edilemiyor.

Frontend `available_actions` yalnız kullanıcı deneyimidir; backend kontrolünün
yerine geçmez.

Kesin protocol geçişi şöyledir:

```python
class ExecutionStartService(Protocol):
    def start_manual(
        self,
        *,
        rule_version_ids: tuple[str, ...],
        source_ids: tuple[str, ...],
        idempotency_key: str,
        actor_context: ActorContext,
        execution_mode: ExecutionMode = ExecutionMode.OFFICIAL,
    ) -> RuleExecution: ...

class ExecutionCancelService(Protocol):
    def cancel(
        self,
        execution_id: str,
        *,
        reason: str,
        actor_context: ActorContext,
    ) -> RuleExecution: ...
```

`api/app.py:start_manual_execution` ve `cancel_execution`, middleware tarafından
doğrulanmış `request.state.actor_context` değerini geçirir. `"unknown"` actor
fallback'i kaldırılır; context yoksa servis çağrılmaz. Aynı imza
`PostgreSQLExecutionStartService`, `PostgreSQLExecutionCancelService` ve yalnız
development'a ait `api/development.py:DevelopmentExecutionStore` için birlikte
uygulanır. Eski `triggered_by`/`requested_by` string imzasını kabul eden uyumluluk
kolu bırakılmaz.

### 4.2 Service actor ve audit olayları

| Geçiş | Olay | Transaction sınırı |
|---|---|---|
| execution + job oluşturma | `EXECUTION_START`, `JOB_ENQUEUED` | Aynı transaction; mevcut desen korunur |
| queue claim | `JOB_CLAIMED` | Status/claimed_by/lease/version ile aynı transaction |
| kota/pencere erteleme | `JOB_BLOCKED` | `BLOCKED` alanlarıyla aynı transaction |
| tekrar uygunluk | `JOB_UNBLOCKED` | Yeni claim veya açık unblock geçişiyle aynı transaction |
| progress | `JOB_PROGRESS_UPDATED` | Yalnız anlamlı eşiklerde; her poll için audit üretilmez |
| retry | `JOB_RETRY_SCHEDULED` | Mevcut fail transition transaction'ı |
| lease geri alma/kayıp | mevcut lease olayları | Mevcut repository yolu korunur |
| dead-letter | `JOB_DEAD_LETTERED` | Job terminal geçişi + `job_dead_letters` + outbox birlikte |
| iptal | `EXECUTION_CANCEL`, `JOB_CANCEL_REQUESTED` | Mevcut ortak transaction korunur |

Worker olaylarının `actor_type` değeri `SERVICE`, actor ID'si kayıtlı `worker_id`
olur. İnsan request payload'ından service identity alınmaz.

### 4.3 `CancellableExecutionCommand` progress sözleşmesi

Kesin port değişikliği:

```python
ProgressCallback = Callable[[int], None]

class CancellableExecutionCommand(Protocol):
    def execute(
        self,
        execution_id: str,
        *,
        connection_timeout_seconds: int,
        query_timeout_seconds: int,
        cancellation_event: Event,
        progress_callback: ProgressCallback,
    ) -> JobCompletionOutcome: ...

    def cancel(self, execution_id: str) -> None: ...
```

Progress değeri integer ve `0..100` aralığındadır; aynı execution içinde geriye
gidemez. `ExecutionJobHandler` callback'i command'a geçirir. Handler child
process'te çalıştığı için callback repository'ye doğrudan yazmaz:

1. `jobs/worker.py:_invoke_handler`, mevcut result pipe üzerinden
   `("progress", percent)` mesajı yollar.
2. Parent `PersistentJobWorker._execute_handler` progress mesajında process'i
   sonlandırmadan okumaya devam eder.
3. Parent, güncel job/version'ı okuyup
   `PostgreSQLJobQueueRepository.update_progress(job_id, worker_id,
   expected_version, percent)` çağırır.
4. Repository `RUNNING`, aktif lease ve owner guard'larını doğrular; lease kaybında
   child iptal edilir ve eski worker progress/sonuç yazamaz.
5. `JOB_PROGRESS_UPDATED` audit'i her mesajda değil, yüzde değiştiğinde ve
   yapılandırılmış eşiklerde aynı transaction'da stage edilir.

Başlangıç claim'i `0`, başarı terminal geçişi `100` yapar. Timeout, cancellation
ve teknik hata son bilinen yüzdeyi korur; terminal durumu progress'ten türetilmez.

## 5. Endpoint envanteri

### 5.1 Mevcut, değişecek endpoint'ler

| Endpoint | Değişiklik |
|---|---|
| `GET /api/v1/executions` | PG query korunur; response'a `progress_percent`, `blocked_reason_code`, `available_actions` eklenir; development CSRF proof header yayımlanır |
| `POST /api/v1/executions` | `idempotency_key` zorunlu olur; trusted ActorContext/role/source kontrolü; replay aynı execution'ı döndürür; 201/200 replay semantiği contract testinde sabitlenir |
| `POST /api/v1/executions/{execution_id}/cancel` | Trusted ActorContext, execution source scope ve state-machine kontrolü; queue + execution + audit ortak transaction korunur |

`POST /executions` idempotency düzeltmesinde payload hash'e `source_ids` de girer.
Mevcut kodda üretilen rastgele `manual-{execution_id}` anahtarı gerçek client
idempotency sağlamaz ve aynı anahtar replay akışını test edemez.

### 5.2 Yeni endpoint

| Endpoint | Amaç | Backend kapsamı |
|---|---|---|
| `GET /api/v1/executions/{execution_id}` | Execution zamanları, durum/progress ve `rule_execution_results` özetini göstermek | `ExecutionQueryService.get_for_actor`; kapsam dışı veya bulunmayan kayıt veri ifşa etmeden 404/403 politikasıyla eşlenir |

Yeni queue/dead-letter/worker operasyon endpoint'i açılmaz; bunlar DS-11'dir.
Yeni schedule endpoint'i açılmaz; DS-07'dir.

## 6. Frontend ekran ve çağrı envanteri

### 6.1 Değişecek dosyalar

| Dosya | Değişiklik |
|---|---|
| `frontend/src/executions/api.ts` | `startExecution`, `cancelExecution`, `fetchExecutionDetail`; CSRF proof taşıma; validation/conflict/unauthorized/technical hata ayrımı |
| `frontend/src/executions/model.ts` | Start/cancel/detail sözleşmeleri; progress, BLOCKED, actions ve sonuç özeti |
| `frontend/src/executions/ExecutionsPage.tsx` | “Çalıştırma başlat” form/dialog; aktif kural sürümü ve kaynak seçimi; satır bazlı iptal; progress/BLOCKED; sonuç detail drawer/section |
| `frontend/src/App.tsx` | `ExecutionsRoute` mutation callback'leri, seçim verisi yükleme, terminale kadar kontrollü polling ve mutation sonrası re-fetch |
| `frontend/src/executions/ExecutionsPage.stories.tsx` | Başlatma, BLOCKED, RUNNING progress, cancellable ve terminal-result durumları |

### 6.2 Yeniden kullanılacak frontend çağrıları

- `frontend/src/rules/api.ts:fetchRules`: aktif kural ve
  `rule_version_id` seçenekleri.
- `frontend/src/dataSources/api.ts:fetchDataSources`: backend tarafından
  zaten scope'lanmış aktif kaynak seçenekleri.
- İlgili `rules/model.ts` ve `dataSources/model.ts` mapper'ları.

Yeni katalog endpoint'i veya frontend-only scope tablosu eklenmez. UI seçimleri
backend'in kural→dataset→source doğrulamasının yerine geçmez. `import.meta.env.DEV`
fixture yolu yalnız açık `?state=` senaryolarında kalır; production API hatasında
sentetik başarı verisi gösterilmez.

## 7. Test envanteri

### 7.1 Değişecek backend testleri

| Dosya | Eklenecek/doğrulanacak senaryo |
|---|---|
| `tests/unit/test_job_queue.py` | Yeni kolon/check/index metadata'sı; BLOCKED/progress/worker model invariant'ları |
| `tests/unit/test_persistent_job_worker.py` | register/heartbeat/drain; BLOCKED'in deneme tüketmemesi; claim service actor; progress ve lease kaybı |
| `tests/unit/test_persistent_job_handlers.py` | Belirli execution ID, progress callback, cancellation ve timeout aktarımı |
| `tests/unit/test_execution_api.py` | ActorContext role/scope negatifleri; idempotent replay; kaynak/kural uyuşmazlığı; detail response |
| `tests/unit/test_executions.py` | Belirli execution'ı çalıştırma ve state-machine; mevcut execution hesaplama kuralları korunur |
| `tests/unit/test_postgresql_execution_repository.py` | Worker başlat/tamamla optimistic state guard ve sonuç okuması |
| `tests/integration/test_postgresql_job_queue.py` | Claim + `JOB_CLAIMED` atomikliği; outbox hatasında rollback; worker heartbeat; blocked requeue; progress; dead-letter |
| `tests/integration/test_postgresql_execution_persistence.py` | Queue tarafından seçilen execution'ın attempt/result/status zinciri |
| `tests/integration/test_application_composition.py` | API composition'ın aynı session/schema ile gerçek PG start/cancel/query/job servislerini yayımlaması |

### 7.2 Yeni backend testleri

| Önerilen dosya | Amaç |
|---|---|
| `tests/integration/test_postgresql_worker_runtime_migration.py` | 15→16 upgrade; kolonlar/check/index/workers; mevcut queued satır backfill'i |
| `tests/unit/test_job_worker_entrypoint.py` | Signal, drain grace, invalid settings ve exit code |
| `tests/unit/test_postgresql_rule_execution_executor.py` | Sekiz rule type/IR operatorü, read-only custom SQL, secret redaction, timeout/cancel/progress ve unsupported IR fail-closed davranışı |
| `tests/integration/test_persistent_job_runtime_composition.py` | `create_persistent_job_runtime` gerçek PG repository/audit/policy ile handler seti ve worker registration |
| `tests/integration/test_ds03_execution_worker_application.py` | Gerçek PG migration head üzerinde API start → job claim → gerçek command adapter → result → GET detail; cancel ve scope negatifleri |

Son test production composition'ı kullanır. Dış veri kaynağı kontrolü yalnız
`ExecutionExecutor` adapter sınırında yapılabilir; job repository, worker,
transactional audit veya composition fake ile değiştirilmez.

### 7.3 Değişecek frontend testleri

| Dosya | Senaryo |
|---|---|
| `frontend/src/executions/api.test.ts` | GET/start/cancel/detail, CSRF, idempotency, 401/403/409/422/5xx |
| `frontend/src/executions/model.test.ts` | BLOCKED/progress/actions/result mapping |
| `frontend/src/executions/ExecutionsPage.test.tsx` | Form validation, backend action görünürlüğü, double-submit engeli, cancel confirm, polling ve sonuç görünümü |
| `frontend/e2e/executions.spec.ts` | Mevcut responsive/fixture testleri yeni contract ile güncellenir; production kanıtı sayılmaz |

### 7.4 Yeni canlı smoke testi

`frontend/e2e/executions-live.spec.ts` yalnız gerçek API + PostgreSQL + worker
compose profiline karşı çalışır ve route interception kullanmaz:

1. yetkili kullanıcı aktif kural/scope seçer;
2. idempotency anahtarıyla başlatır;
3. kayıt `QUEUED/RUNNING` üzerinden terminal duruma ilerler;
4. sonuç özeti `rule_execution_results` verisiyle görünür;
5. ikinci senaryoda iptal worker'a ulaşır;
6. yetkisiz source ID doğrudan request ile gönderildiğinde backend reddeder;
7. audit sorgusunda start/enqueue/claim/terminal veya cancel zinciri görülür.

Mock'lu mevcut Playwright testi görsel regresyon için korunur; bu canlı testin
yerine geçmez.

### 7.5 Korunacak mevcut testler

- `tests/unit/test_postgresql_execution_repository.py`
- `tests/unit/test_retention_disposal_job.py`
- DS-01/DS-02 migration ve persistent application testleri
- `tests/integration/test_postgresql_issue_migration.py`
- Rule, issue, audit ve source permission regresyon testleri

## 8. Kesin dosya değişikliği özeti

### Değişecek

- `alembic/versions/20260805_16_execution_worker_runtime.py` (yeni)
- `src/veri_kalitesi/jobs/{models,postgresql_repository,worker,composition,handlers,__init__}.py`
- `src/veri_kalitesi/jobs/{entrypoint,settings,execution_command,production}.py` (yeni)
- `src/veri_kalitesi/executions/{service,postgresql_repository,query}.py`
- `src/veri_kalitesi/executions/postgresql_executor.py` (yeni)
- `src/veri_kalitesi/data_sources/{postgresql,postgresql_driver}.py`
- `src/veri_kalitesi/api/{postgresql_execution,models,app,composition,settings}.py`
- `pyproject.toml`
- `infra/application/Dockerfile`
- `infra/development/compose.yaml`
- `frontend/src/executions/{api,model,ExecutionsPage,ExecutionsPage.stories}.ts(x)`
- `frontend/src/App.tsx`
- §7'de listelenen backend/frontend testleri

### Değişmeyecek

- Migration 01–15 dosyaları
- `job_dead_letters` tablo adı ve dead-letter yaşam döngüsü çekirdeği
- Yeni message broker/Redis/Celery altyapısı
- Issue, score, profile, schedule, notification ve operations ekranları
- IAM/rol yönetim modeli
- `rules/api.ts` ve `dataSources/api.ts` sözleşmeleri; yalnız çağrıları yeniden kullanılır
- API prosesine gömülü background thread veya in-memory production queue

## 9. Envanter kararı

### 9.1 Somut production `ExecutionExecutor`

**ÇÖZÜLDÜ — uygulama için zorunlu karar.**

Somut sınıf
`executions/postgresql_executor.py:PostgreSQLRuleExecutionExecutor` olacaktır.
Rule/source repository, `SecretResolver` ve
`PostgreSQLConnector(SQLAlchemyPostgreSQLDriver())` bağımlılıkları §3.3'te
sabitlenmiştir. Production composition bu concrete provider olmadan fail-fast
olur; fake/no-op fallback yoktur.

### 9.2 `create_persistent_job_runtime` imza değişikliği

**ÇÖZÜLDÜ.**

§3.3'te kesin keyword-only imza yazılmıştır. `execution_command` zorunlu,
`report_worker` opsiyoneldir; worker registration alanları factory'ye girer ve
supported job type listesi gerçek handler map'inden türetilir.

### 9.3 Start/cancel `ActorContext` geçişi

**ÇÖZÜLDÜ.**

§4.1'de iki API protocol'ünün kesin imzası, route aktarımı, `unknown` fallback'in
kaldırılması ve PostgreSQL/development implementasyonlarının atomik geçişi
tanımlanmıştır. Eski string actor uyumluluk kolu bırakılmaz.

### 9.4 `CancellableExecutionCommand` progress callback

**ÇÖZÜLDÜ.**

§4.3 callback tipini, yüzde invariant'larını, child→parent pipe mesajını,
parent-owned repository/audit yazımını ve lease kaybı davranışını sabitlemiştir.

### Son karar

Plan **GO — uygulamaya hazır** durumdadır. Migration, queue state-machine, claim
audit, permission/scope, production executor, composition, frontend ve test
yolları mevcut mimariyle uygulanabilir biçimde tanımlanmıştır.

Uygulama sırasında §9.1'deki concrete provider yerine fake/no-op bağlanması,
§9.2–§9.4 imzalarının kısmi uygulanması veya worker'ın API prosesine gömülmesi
production yolu için yeniden **NO-GO** sebebidir.
