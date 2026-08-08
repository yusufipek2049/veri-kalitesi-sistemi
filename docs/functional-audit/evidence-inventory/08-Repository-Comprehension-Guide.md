# Repository Comprehension Guide

> Bu belge, repository'nin çalışma biçimini anlamak için gereken kavramları, durum makinelerini,
> fonksiyon ilişkilerini, ayağa kaldırma yöntemini ve sezgisel olmayan tasarım kararlarını
> kod kanıtlarıyla sunar. Dokümantasyon beyanları değil, yalnızca kaynak kod referansları kullanılır.

---

## 1. Temel Kavramlar Sözlüğü

Aşağıdaki terimler, kodda sınıf veya enum olarak tanımlanmış domain kavramlarıdır.

### 1.1 Kimlik ve Yetkilendirme

| Terim | Tanım | Kaynak | Tüketen modüller |
|-------|-------|--------|------------------|
| `ActorContext` | Sisteme giriş yapmış güvenilir aktörün kimlik, rol, kapsam ve süre bilgisini taşıyan dondurulmuş veri sınıfı. Her servis metodu bunu parametre alır. | `identity/models.py:20-34` | `api/`, `dashboard/`, `issues/`, `rules/`, `executions/`, `reporting/`, `audit/` |
| `ActorType` | USER, SERVICE, BREAK_GLASS — aktörün kimliğini nasıl kanıtladığını belirtir. | `identity/models.py:10-13` | `identity/`, `api/` |
| `DashboardAuthorizationPolicy` | Dashboard sorgularının hangi actor tipleriyle yapılabileceğini belirleyen politika. | `identity/models.py:46-50` | `dashboard/service.py` |

### 1.2 Veri Kaynağı ve Metadata

| Terim | Tanım | Kaynak | Tüketen modüller |
|-------|-------|--------|------------------|
| `DataSource` | Sisteme tanıtılmış bir veri kaynağı (PostgreSQL, CSV, REST API vb.). Bağlantı bilgileri, durum ve revizyon taşır. | `data_sources/models.py:171` | `api/`, `executions/`, `dashboard/` |
| `Dataset` | Bir kaynağın içindeki tablo/view/dosya. `dataset_id` kuralların bağlandığı birincil kapsam. | `data_sources/models.py:186` | `rules/`, `executions/`, `issues/` |
| `DataField` | Dataset içindeki tek kolon. Sınıflandırma (KVKK) ve hassasiyet bilgisi taşır. | `data_sources/models.py:198` | `data_protection/`, `rules/` |
| `DataProfile` | Bir dataset'in belirli bir zamanda çıkarılmış istatistiksel profili (FULL veya SAMPLE). | `data_sources/models.py:312` | `api/`, `dashboard/` |
| `ProfileComparison` | İki profil arasındaki fark analizi sonucu; drift tespiti için kullanılır. | `data_sources/models.py:328` | `api/` |
| `DataSourceStatus` | TEST_PENDING → TEST_SUCCEEDED → ACTIVE → INACTIVE → ARCHIVED yaşam döngüsü. | `data_sources/models.py:31` | `api/`, `data_sources/` |

### 1.3 Kural ve Sürüm

| Terim | Tanım | Kaynak | Tüketen modüller |
|-------|-------|--------|------------------|
| `QualityRule` | Bir dataset'e bağlı kalite kuralı. code, name, primary_dimension, status taşır. | `rules/models.py:118` | `api/`, `executions/`, `scoring/` |
| `RuleVersion` | Bir kuralın belirli bir sürümü. threshold, weight, criticality, definition(JSON) taşır. | `rules/models.py:130` | `api/`, `executions/` |
| `RuleTestResult` | Kural testinin sonucu: passed/failed/not_evaluated sayıları ve preview_score. | `rules/models.py:163` | `api/` |
| `RuleApprovalRequest` | CRITICAL kuralların aktivasyonu için maker-checker onay talebi. | `rules/models.py:102` | `api/` |
| `QualityDimension` | COMPLETENESS, ACCURACY, VALIDITY, CONSISTENCY, UNIQUENESS, TIMELINESS, INTEGRITY | `rules/models.py:53` | `rules/`, `scoring/` |
| `RuleStatus` | DRAFT, ACTIVE, PASSIVE, REVIEW_REQUIRED, ARCHIVED | `rules/models.py:45` | `api/`, `rules/` |

### 1.4 Çalıştırma

| Terim | Tanım | Kaynak | Tüketen modüller |
|-------|-------|--------|------------------|
| `RuleExecution` | Bir veya birden fazla kural sürümünün çalıştırılması. Idempotency hash, kapsam, durum taşır. | `executions/models.py:105` | `api/`, `jobs/`, `scoring/`, `issues/` |
| `ExecutionStatus` | QUEUED → RUNNING → SUCCESS/PARTIAL/TECHNICAL_ERROR/TIMEOUT/CANCELLED | `executions/models.py:27` | `api/`, `jobs/` |
| `ExecutionMode` | OFFICIAL (skor hesaplanır) veya SHADOW (skor hesaplanmaz, sadece test). | `executions/models.py:22` | `api/`, `executions/` |
| `BackgroundJob` | Kalıcı iş kuyruğundaki tekil iş. Lease, heartbeat, retry bilgisi taşır. | `jobs/models.py:98` | `jobs/worker.py` |
| `JobLeasePolicy` | Worker'ın işi ne kadar süre sahiplenebileceğini belirleyen politika. | `jobs/models.py:49` | `jobs/worker.py` |

### 1.5 Sorun ve İnceleme

| Terim | Tanım | Kaynak | Tüketen modüller |
|-------|-------|--------|------------------|
| `DataQualityIssue` | Kalite kuralı başarısızlığından veya teknik hatadan oluşan sorun kaydı. Deduplication digest ile tekrar engellenir. | `issues/models.py:162` | `api/`, `issues/` |
| `IssueStatus` | NEW → ASSIGNED → INVESTIGATING → WAITING_FOR_RESOLUTION → RESOLVED → VERIFIED → CLOSED (+CANCELLED) | `issues/models.py:49` | `api/`, `issues/` |
| `IssueResolutionDraft` | Çözüm kaydı: root_cause, corrective_action, evidence_reference. | `issues/models.py:97` | `api/`, `issues/` |

### 1.6 Skorlama

| Terim | Tanım | Kaynak | Tüketen modüller |
|-------|-------|--------|------------------|
| `QualityScore` | Bir execution sonrası hesaplanan kalite skoru. scope_type(SOURCE/ENTERPRISE), score_value, level. | `scoring/models.py:123` | `dashboard/`, `reporting/` |
| `ScoreLevel` | GOOD, ACCEPTABLE, POOR, CRITICAL — eşik tabanlı sınıflandırma. | `scoring/models.py:40` | `dashboard/`, `scoring/` |

### 1.7 Audit ve Raporlama

| Terim | Tanım | Kaynak | Tüketen modüller |
|-------|-------|--------|------------------|
| `AuditEvent` | Sistemdeki her durum değişikliğinin değiştirilemez kaydı. Hash zinciri ile bütünlük korunur. | `audit/models.py:115` | `api/`, `dashboard/` |
| `PreparedAuditEvent` | Redakte edilmiş ama henüz outbox'a yazılmamış audit event. | `audit/models.py:81` | `audit/postgresql_outbox.py` |
| `Report` | Asenkron üretilen rapor kaydı. QUEUED → RUNNING → READY/FAILED. | `reporting/models.py:38` | `api/`, `reporting/worker.py` |

---

## 2. Mimari Genel Bakış

### 2.1 Composition Root: `create_dashboard_api()`

**Dosya:** `api/app.py:376-409`

Sistemin tek API fabrikası. 26+ servis bağımlılığını `Protocol` tipinde veya `None` olarak alır.
Her bağımlılık `None` ise, ilgili endpoint 503 döndürür (fail-closed).

```
create_dashboard_api(
    dashboard_service,                    # Zorunlu
    actor_context_resolver=None,          # Production: BffSessionBoundary
    bff_session_boundary=None,            # Development: DevelopmentActorContextResolver
    data_source_query_service=None,       # DataSource listeleme
    data_source_mutation_service=None,    # DataSource CRUD
    rule_query_service=None,              # Rule listeleme
    rule_creator_service=None,            # Rule oluşturma
    rule_mutation_service=None,           # Rule sürüm/test/aktivasyon/onay
    execution_query_service=None,         # Execution listeleme
    execution_start_service=None,         # Manuel çalıştırma başlatma
    execution_cancel_service=None,        # Çalıştırma iptali
    issue_query_service=None,             # Issue listeleme
    issue_investigation_service=None,     # İnceleme başlatma
    issue_resolution_service=None,        # Çözüm kaydı
    issue_verification_service=None,      # Doğrulama
    issue_closure_service=None,           # Kapatma
    report_preview_service=None,          # Rapor önizleme
    report_service=None,                  # Rapor üretim/indirme
    report_schedule_service=None,         # Rapor zamanlama
    audit_query_service=None,             # Audit sorgulama
    lineage_evidence_repository=None,     # Lineage kanıt deposu
    governance_profile_reader=None,       # Yönetişim profil okuyucu
    ...
)
```

### 2.2 Dev vs Production Kablolama

| Katman | Development | Production |
|--------|-------------|------------|
| Kimlik | `DevelopmentActorContextResolver` — `X-Development-User-Id` header ile kullanıcı seçimi (`api/identity.py:185`) | `BffSessionBoundary` — `__Host-session` cookie + CSRF double-submit (`api/bff.py:34`) |
| Veri deposu | `DevelopmentIssueStore` — bellek içi `dict` + `RLock` (`api/development.py:603`) | `PostgreSQLIssueRepository` — gerçek DB (`issues/postgresql_repository.py`) |
| Execution | `DevelopmentExecutionStore` — bellek içi (`api/development.py:990`) | `PostgreSQLExecutionStartService` — DB + job queue (`api/postgresql_execution.py:39`) |
| Veri kaynağı | `DevelopmentDataSourceStore` — bellek içi (`api/development.py:885`) | `DataSourceMutationService` impl — PostgreSQL |

### 2.3 Transactional Audit Outbox

**Dosya:** `audit/postgresql_outbox.py:47-80`

Her domain mutasyonu (issue reassign, execution start, rule activation vb.) audit event'ini **aynı DB transaction'ında** `audit_outbox` tablosuna yazar:

```
1. transactional_audit.prepare(event) → PreparedAuditEvent (redakte edilir)
2. with transactional_session(session_factory) as session:
3.     repository.mutate(..., session=session)      # domain değişikliği
4.     transactional_audit.stage(prepared, session)  # audit outbox'a yaz
5. # transaction commit → ikisi de atomik
```

Outbox'taki PENDING event'ler daha sonra `publish_pending()` ile kalıcı audit deposuna aktarılır (`postgresql_outbox.py:82`).

### 2.4 Correlation ID Yayılımı

**Dosya:** `api/app.py:433-480`

HTTP middleware her isteğe `request.state.correlation_id = uuid4()` atar. Bu değer:
- Her API response'da `X-Correlation-ID` header olarak döndürülür
- Her servis metoduna `correlation_id` parametresi olarak aktarılır
- Her audit event'e `correlation_id` olarak yazılır
- Hata yanıtlarında `correlation_id` alanıyla döndürülür

---

## 3. Durum Makineleri

### 3.1 DataSource Durum Makinesi

```mermaid
stateDiagram-v2
    [*] --> TEST_PENDING: create()
    TEST_PENDING --> TEST_SUCCEEDED: test_connection() [başarılı]
    TEST_PENDING --> TEST_FAILED: test_connection() [başarısız]
    TEST_SUCCEEDED --> ACTIVE: activate()
    ACTIVE --> INACTIVE: passivate()
    INACTIVE --> TEST_PENDING: test_connection()
```

| Kaynak → Hedef | Komut | Gard | Aktör | Kanıt |
|----------------|-------|------|-------|-------|
| `[*]` → TEST_PENDING | `POST /data-sources` | — | Herhangi | `development.py:892-932` |
| TEST_PENDING → TEST_SUCCEEDED | `POST /data-sources/{id}/test` | — | Herhangi | `development.py:934-949` |
| TEST_SUCCEEDED → ACTIVE | `POST /data-sources/{id}/activation` | status == TEST_SUCCEEDED | Herhangi | `development.py:951-968` |
| ACTIVE → INACTIVE | `POST /data-sources/{id}/passivation` | status == ACTIVE | Herhangi | `development.py:970-987` |

### 3.2 QualityRule Durum Makinesi

```mermaid
stateDiagram-v2
    [*] --> DRAFT: create_rule()
    DRAFT --> ACTIVE: activate_rule() [criticality != CRITICAL]
    DRAFT --> REVIEW_REQUIRED: request_approval() [criticality == CRITICAL]
    REVIEW_REQUIRED --> ACTIVE: decide(APPROVE)
    REVIEW_REQUIRED --> DRAFT: decide(REJECT) / withdraw()
    ACTIVE --> PASSIVE: passivate_rule()
    PASSIVE --> DRAFT: create_version() [yeni sürüm]
```

| Kaynak → Hedef | Komut | Gard | Kanıt |
|----------------|-------|------|-------|
| DRAFT → ACTIVE | `activate_rule()` | criticality != CRITICAL | `app.py:2348` (`_rule_actions`) |
| DRAFT → REVIEW_REQUIRED | `request_rule_approval()` | criticality == CRITICAL | `app.py:2351-2358` |
| REVIEW_REQUIRED → ACTIVE | `decide_rule_approval(APPROVE)` | — | `app.py:1882-1911` |
| REVIEW_REQUIRED → DRAFT | `decide_rule_approval(REJECT)` | — | `app.py:1882-1911` |
| ACTIVE → PASSIVE | `passivate_rule()` | — | `app.py:1943-1970` |

### 3.3 RuleExecution Durum Makinesi

```mermaid
stateDiagram-v2
    [*] --> QUEUED: start_manual()
    QUEUED --> RUNNING: worker claims
    QUEUED --> CANCELLED: cancel() [hemen]
    RUNNING --> SUCCESS: handler outcome SUCCESS
    RUNNING --> PARTIAL: handler outcome PARTIAL
    RUNNING --> TECHNICAL_ERROR: permanent error
    RUNNING --> TIMEOUT: total timeout
    RUNNING --> CANCEL_REQUESTED: cancel() [çalışırken]
    CANCEL_REQUESTED --> CANCELLED: worker acknowledges
```

| Kaynak → Hedef | Komut | Gard | Kanıt |
|----------------|-------|------|-------|
| `[*]` → QUEUED | `start_manual()` | — | `postgresql_execution.py:63-155` |
| QUEUED → CANCELLED | `cancel()` | status == QUEUED | `development.py:1043-1051`, `postgresql_execution.py:238-242` |
| RUNNING → CANCEL_REQUESTED | `cancel()` | status == RUNNING | `development.py:1053-1061`, `postgresql_execution.py:238-242` |
| CANCEL_REQUESTED → CANCELLED | Worker poll | Worker `run_once()` cancel kontrolü | `jobs/worker.py:172-187` |

### 3.4 DataQualityIssue Durum Makinesi

```mermaid
stateDiagram-v2
    [*] --> NEW: otomatik oluşturma
    NEW --> ASSIGNED: sistem ataması
    ASSIGNED --> INVESTIGATING: start_investigation()
    INVESTIGATING --> WAITING_FOR_RESOLUTION: (otomatik)
    INVESTIGATING --> ASSIGNED: reassign()
    WAITING_FOR_RESOLUTION --> RESOLVED: resolve()
    RESOLVED --> VERIFIED: verify() [farklı aktör]
    VERIFIED --> CLOSED: close()
    ASSIGNED --> ASSIGNED: reassign() [atama değişikliği]
    any --> CANCELLED: (teknik iptal)
```

| Kaynak → Hedef | Komut | Gard | Aktör | Kanıt |
|----------------|-------|------|-------|-------|
| ASSIGNED → INVESTIGATING | `start_investigation()` | assignee == actor, scope match | Atanan kişi | `development.py:632-662` |
| INVESTIGATING → ASSIGNED | `reassign()` | steward/governance rolü | Steward | `development.py:678-711` |
| INVESTIGATING/WAITING → RESOLVED | `resolve()` | assignee == actor, scope match | Atanan kişi | `development.py:713-746` |
| RESOLVED → VERIFIED | `verify()` | actor != assignee, steward/governance | **Farklı** aktör | `development.py:748-778` |
| VERIFIED → CLOSED | `close()` | DATA_OWNER veya DATA_STEWARD | Owner/Steward | `development.py:780-809` |

### 3.5 BackgroundJob Durum Makinesi

```mermaid
stateDiagram-v2
    [*] --> QUEUED: enqueue()
    QUEUED --> RUNNING: worker claim
    RUNNING --> SUCCESS: handler SUCCESS
    RUNNING --> TECHNICAL_ERROR: permanent error (retry exhausted)
    RUNNING --> TIMEOUT: total timeout
    RUNNING --> QUEUED: retryable error (retry available)
    QUEUED --> CANCELLED: cancel (queued)
    RUNNING --> CANCEL_REQUESTED: cancel (running)
    CANCEL_REQUESTED --> CANCELLED: worker ack
```

| Kanıt dosyası | Satır |
|---------------|-------|
| `jobs/worker.py:95-203` | `run_once()` tam yaşam döngüsü |
| `jobs/worker.py:299-351` | `_fail()` — retry vs terminal kararı |
| `jobs/models.py:20-35` | `JobStatus` enum ve `JobCompletionOutcome` |

### 3.6 Report Durum Makinesi

```mermaid
stateDiagram-v2
    [*] --> QUEUED: request_report()
    QUEUED --> RUNNING: worker process
    RUNNING --> READY: üretim başarılı
    RUNNING --> FAILED: non-retryable hata
    RUNNING --> FAILED: retry exhausted
```

| Kanıt dosyası | Satır |
|---------------|-------|
| `reporting/worker.py:94-200` | `process_report()` tam akış |
| `reporting/models.py:23-29` | `ReportStatus` enum |

---

## 4. Veri Akış Diyagramları

### 4.1 Kaynak Onboarding

```
Kullanıcı                   API                          Servis                        DB
  │                          │                             │                            │
  │ POST /data-sources       │                             │                            │
  │─────────────────────────>│                             │                            │
  │                          │ DataSourceMutationService   │                            │
  │                          │ .create()                   │                            │
  │                          │────────────────────────────>│                            │
  │                          │                             │ INSERT data_sources        │
  │                          │                             │───────────────────────────>│
  │                          │                             │         DataSource         │
  │                          │                             │<───────────────────────────│
  │      DataSource          │                             │                            │
  │<─────────────────────────│                             │                            │
  │                          │                             │                            │
  │ POST /data-sources/{id}  │                             │                            │
  │      /test               │                             │                            │
  │─────────────────────────>│                             │                            │
  │                          │ .test_connection()          │                            │
  │                          │────────────────────────────>│ status → TEST_SUCCEEDED    │
  │                          │                             │───────────────────────────>│
  │                          │                             │                            │
  │ POST /data-sources/{id}  │                             │                            │
  │      /activation         │                             │                            │
  │─────────────────────────>│                             │ status → ACTIVE            │
  │                          │ .activate()                 │───────────────────────────>│
  │                          │────────────────────────────>│                            │
```

**Kod kanıtları:**
- API handler: `app.py:2011-2110`
- Dev store implementasyonu: `development.py:885-987`
- DB migration: `20260724_03_data_source_baseline.py`

### 4.2 Execution Pipeline

```
1. POST /api/v1/executions
   → app.py:2114  start_manual_execution()
   → PostgreSQLExecutionStartService.start_manual()       [postgresql_execution.py:63]
     a. RuleExecution(QUEUED) oluştur
     b. audit_outbox.prepare(EXECUTION_START)
     c. audit_outbox.prepare(JOB_ENQUEUED)
     d. transactional_session içinde:
        - repository.create_or_get(execution)              [postgresql_execution.py:131-137]
        - job_queue.enqueue(BackgroundJob)                 [postgresql_execution.py:138-154]
     e. return RuleExecution

2. PersistentJobWorker.run_once()                          [jobs/worker.py:95]
   a. policy_resolver.resolve_policy() → concurrency limits
   b. repository.claim_next(worker_id, lease)              [jobs/worker.py:99-106]
   c. handler = handlers.get(job.job_type)                 [jobs/worker.py:132]
      → ExecutionJobHandler                                [jobs/handlers.py:31]
   d. Handler fork'lanmış process'te çalıştırılır          [jobs/worker.py:211-228]
      - connection_timeout, query_timeout uygulanır
      - cancellation_event ile aktif iptal desteklenir
   e. Heartbeat: her lease/3 sürede bir                   [jobs/worker.py:276-289]
   f. Sonuç → complete() veya _fail()                     [jobs/worker.py:169-351]

3. Retry mantığı:
   - RetryableJobError → QUEUED (attempt_count < retry_count)
   - PermanentJobError → TECHNICAL_ERROR (terminal)
   - JobTimeoutError → TIMEOUT (terminal)
   - attempt_count > retry_count → TECHNICAL_ERROR
```

### 4.3 Kural Yaşam Döngüsü

```
1. POST /api/v1/rules
   → RuleCreatorService.create_rule()  → DRAFT       [app.py:1719-1756]

2. POST /api/v1/rules/{id}/test
   → RuleMutationService.test_rule()
   → RuleTestResult döndürülür                           [app.py:1793-1821]

3. POST /api/v1/rules/{id}/approval     [sadece CRITICAL]
   → RuleMutationService.request_rule_approval()
   → status → REVIEW_REQUIRED                            [app.py:1852-1880]

4. POST /api/v1/rules/approval/{id}/decide
   → RuleMutationService.decide_rule_approval()
   → APPROVE → ACTIVE  /  REJECT → DRAFT                 [app.py:1882-1911]

5. POST /api/v1/rules/{id}/activation   [CRITICAL değilse doğrudan]
   → RuleMutationService.activate_rule()
   → status → ACTIVE                                     [app.py:1823-1850]

6. POST /api/v1/rules/{id}/passivation
   → RuleMutationService.passivate_rule()
   → status → PASSIVE                                    [app.py:1943-1970]
```

### 4.4 Sorun Yaşam Döngüsü

```
1. [Otomatik] Execution başarısızlığı → DataQualityIssue(NEW) oluşur
   - deduplication_key_digest ile tekrar engellenir       [migration 01: issue_baseline.py:36]

2. POST /api/v1/issues/{id}/investigation
   → IssueInvestigationService.start_investigation()
   → Gard: assignee == actor, scope match, status == ASSIGNED
   → status → INVESTIGATING                              [app.py:1174-1206]

3. GET /api/v1/issues/{id}/investigation/evidence
   → IssueInvestigationEvidenceService
   → rule_description, expected/actual_summary, masked_samples, recommendation
   → Salt okunur kanıt paketi                            [app.py:1208-1236]

4. POST /api/v1/issues/{id}/resolution
   → IssueResolutionService.resolve()
   → Gard: assignee == actor, status in {INVESTIGATING, WAITING_FOR_RESOLUTION}
   → IssueResolutionDraft(root_cause, corrective_action, evidence_reference)
   → status → RESOLVED                                   [app.py:1303-1342]

5. POST /api/v1/issues/{id}/verification
   → IssueVerificationService.record_verification_result()
   → Gard: actor != assignee (farklı aktör!), steward/governance rolü
   → status → VERIFIED                                   [app.py:1344-1376]

6. POST /api/v1/issues/{id}/closure
   → IssueClosureService.close()
   → Gard: DATA_OWNER veya DATA_STEWARD rolü
   → status → CLOSED                                     [app.py:1378-1409]
```

### 4.5 Raporlama Akışı

```
1. POST /api/v1/reports/
   → ReportService.request_report()
   → Report(QUEUED) oluşturulur                          [app.py:1439-1468]

2. [Dev: inline_processing=True → senkron]
   [Prod: ReportWorker.process_report() asenkron]

3. ReportWorker.process_report()                          [reporting/worker.py:94]
   a. Report(RUNNING)                                    [worker.py:116]
   b. ReportDataProvider.fetch_report_data()             [worker.py:135-142]
   c. generate_report() → dosya üret                     [reporting/export.py]
   d. Dosyayı storage_path'e yaz                         [worker.py:147-150]
   e. Report(READY, online_file_reference, expires_at)   [worker.py:164-170]
   f. Hata → retry (exponential backoff) → FAILED        [worker.py:173-200]

4. GET /api/v1/reports/{id}/download
   → Dosyayı disk'ten oku, Content-Disposition ile döndür [app.py:1515-1549]
```

---

## 5. Kimlik Doğrulama ve Yetkilendirme Modeli

### 5.1 İki Kimlik Doğrulama Modu

| Özellik | Development | Production |
|---------|-------------|------------|
| **Aktör çözümleyici** | `DevelopmentActorContextResolver` | `BffSessionBoundary` |
| **Dosya** | `api/identity.py:185` | `api/bff.py:34` |
| **Kimlik kaynağı** | `X-Development-User-Id` HTTP header | `__Host-session` cookie (HttpOnly, Secure, SameSite=Lax) |
| **CSRF** | Statik proof string (`"development-request-proof-v1"`) | Double-submit cookie (base64 CSRF token) |
| **Origin kontrolü** | `allowed_origins` seti ile karşılaştırma | Origin + Referer + Sec-Fetch-Site üçlüsü doğrulama |
| **Oturum sonlandırma** | Yok (stateless) | `POST /session/logout` → cookie sil + session invalidation |

### 5.2 ActorContext — Güvenilir Kimlik Token'ı

**Dosya:** `identity/models.py:20-34`

```python
@dataclass(frozen=True)
class ActorContext:
    actor_id: str                        # Kullanıcı veya servis kimliği
    actor_type: ActorType                # USER | SERVICE | BREAK_GLASS
    authentication_source: str           # "development-only-adapter" veya IdP adı
    session_id: str                      # Oturum kimliği
    roles: frozenset[str]                # {"DATA_VIEWER", "DATA_STEWARD", ...}
    permitted_source_ids: frozenset[str] # Erişebileceği kaynaklar
    permitted_dataset_ids: frozenset[str]# Erişebileceği dataset'ler
    can_view_enterprise: bool            # Enterprise-scope görünümlere erişim
    privileged: bool                     # True → TÜM mutasyonlar engellenir
    issued_at: datetime                  # Token veriliş zamanı
    expires_at: datetime                 # Token son kullanma
    policy_version: str                  # Politika sürümü
    correlation_id: str                  # İstek korelasyon
```

**Trust marker:** `_CONTEXT_TRUST_MARKER` (`identity/models.py:16`) — `ActorContext` yalnızca `ActorContextIssuer` tarafından oluşturulabilir; dışarıdan construct edilmiş instance'lar `is_trusted_actor_context()` ile reddedilir.

### 5.3 Rol Tabanlı Eylem Hesaplama

Sistem, UI'a "hangi butonlar görünmeli" bilgisini **sunucu tarafında** hesaplar:

**Issue eylemleri** — `app.py:2275-2321` (`_issue_actions()`):
- `START_INVESTIGATION` → status == ASSIGNED, assignee == actor, scope match
- `REASSIGN` → status in {ASSIGNED, INVESTIGATING}, steward/governance rolü
- `RESOLVE` → status in {INVESTIGATING, WAITING_FOR_RESOLUTION}, assignee == actor
- `VERIFY` → status == RESOLVED, actor != assignee, steward/governance
- `CLOSE` → status == VERIFIED, DATA_OWNER veya DATA_STEWARD

**Rule eylemleri** — `app.py:2324-2378` (`_rule_actions()`):
- `CREATE_VERSION` → status in {DRAFT, ACTIVE, PASSIVE}
- `TEST_RULE` → status == DRAFT
- `ACTIVATE` → status == DRAFT, criticality != CRITICAL
- `REQUEST_APPROVAL` → status == DRAFT, criticality == CRITICAL
- `DECIDE_APPROVAL` / `WITHDRAW_APPROVAL` → status == REVIEW_REQUIRED
- `PASSIVATE` → status == ACTIVE

### 5.4 Geliştirme Kullanıcıları

**Dosya:** `api/identity.py:91-182`

8 sabit kullanıcı, farklı rol/kapsam kombinasyonlarıyla:

| User ID | Roller | Kapsam | Enterprise | Privileged |
|---------|--------|--------|------------|------------|
| `dev-data-viewer` | DATA_VIEWER | Tüm kaynak/dataset | Evet | Hayır |
| `dev-data-steward` | DATA_VIEWER, DATA_STEWARD | Tüm kaynak/dataset | Evet | Hayır |
| `dev-data-owner` | DATA_VIEWER, DATA_OWNER | Tüm kaynak/dataset | Evet | Hayır |
| `dev-data-governance` | DATA_VIEWER, DATA_GOVERNANCE_SPECIALIST | Tüm kaynak/dataset | Evet | Hayır |
| `dev-data-engineer` | DATA_VIEWER, DATA_ENGINEER | Tüm kaynak/dataset | Evet | Hayır |
| `dev-audit-viewer` | DATA_VIEWER, AUDIT_VIEWER | Tüm kaynak/dataset | **Hayır** | Hayır |
| `dev-limited-steward` | DATA_VIEWER, DATA_STEWARD | **Sadece 2 kaynak** | **Hayır** | Hayır |
| `dev-privileged-user` | DATA_VIEWER, DATA_STEWARD | Tüm kaynak/dataset | Evet | **Evet** |

---

## 6. Repository'yi Ayağa Kaldırma

### 6.1 Backend

```bash
# 1. Python bağımlılıkları (Python 3.10+)
pip install -e ".[test]"

# 2. PostgreSQL başlat (seçenek A: Docker Compose Enterprise Lab)
cd infra/enterprise-lab && docker compose up -d postgres-primary
# → localhost:15432, kullanıcı: postgres, şifre: runtime-secrets/postgres_admin_password

# 3. Veritabanı ve şema oluştur
# scripts/run_dev.py zaten şu URL'yi kullanır:
#   postgresql+psycopg://dqtest:dqtest@127.0.0.1:55432/data_quality
# Farklı bir port/kullanıcı için .env veya environment variable ayarlayın.

# 4. Migration'ları çalıştır
DATA_QUALITY_DATABASE_URL="postgresql+psycopg://dqtest:dqtest@127.0.0.1:55432/data_quality" \
  alembic -c alembic.ini upgrade head

# 5. Dev API sunucusunu başlat
uvicorn scripts.run_dev:app --reload --port 8000
# → http://localhost:8000/api/v1/openapi.json (OpenAPI şeması)
```

**Kaynak:** `scripts/run_dev.py:1-40` — hardcoded DB URL ve `create_development_app()` çağrısı.

### 6.2 Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
# DevelopmentLoginPage ile kullanıcı seç → Dashboard'a eriş
```

### 6.3 Enterprise Lab (Tam Entegrasyon)

```bash
cd infra/enterprise-lab
docker compose up
```

Bu komut şunları başlatır:
- `postgres-primary` (port 15432) — WAL replikasyon destekli
- `postgres-standby` (port 15433) — Streaming replica
- `keycloak` (port 18080) — OIDC/LDAP identity provider
- `rabbitmq` (port 15672) — Message broker
- `local-secret-manager` (port 18200) — Secret yönetimi mock
- `fake-servicenow` (port 18081) — ServiceNow mock
- `siem-collector` (port 18082) — SIEM/WORM mock
- `evidence-store` (port 18083) — Kanıt deposu mock

**Kaynak:** `infra/enterprise-lab/compose.yaml`

---

## 7. Test Stratejisi

### 7.1 Backend Testleri

| Kategori | Konum | Komut | Açıklama |
|----------|-------|-------|----------|
| Birim testleri | `tests/unit/` | `pytest tests/unit/` | Mock-based, hızlı, 57 dosya |
| Entegrasyon testleri | `tests/integration/` | `pytest tests/integration/` | Gerçek PostgreSQL gerekir, 12 dosya |

**Yapılandırma:** `pyproject.toml:24-27`
```toml
[tool.pytest.ini_options]
pythonpath = ["docs/backend/src", "docs/testing/support"]
testpaths = ["tests"]
```

**Entegrasyon test bağlantısı:** `tests/integration/conftest.py` — `.env` dosyasından `DATA_QUALITY_DATABASE_URL` okur.

### 7.2 Frontend Testleri

| Kategori | Komut | Framework |
|----------|-------|-----------|
| Birim/component | `cd frontend && npx vitest` | Vitest |
| E2E | `cd frontend && npx playwright test` | Playwright |
| Storybook | `cd frontend && npx storybook` | Storybook |

### 7.3 Test Kapsamı Özeti

- **En güçlü:** Issues (4 birim + 3 entegrasyon + 1 E2E), Rules (2 + 1 + 1)
- **En zayıf:** Data Protection (0 test), Scheduling (0 test), Report Schedules (0 test)
- **Yalnız birim:** Secure SDLC (8 dosya, 0 entegrasyon, 0 E2E)
- **Entegrasyon yok:** Notifications, Retention, Incident Response, ServiceNow

---

## 8. Sezgisel Olmayan Tasarım Kararları

Bu bölüm, README'yi okuyarak tahmin edemeyeceğiniz mimari kararları listeler.

### 8.1 Fail-Closed Bağımlılık Enjeksiyonu

`create_dashboard_api()`'nin her servis parametresi `None`'a default eder. Wire edilmemiş bir servis için endpoint 503 döndürür — sessizce crash olmaz.

**Kanıt:** `app.py:956-959` — `if data_source_query_service is None: raise DataSourceQueryTechnicalError(...)`

### 8.2 İki Paralel Kalıcılık Modu

Aynı `IssueQueryService`, enjekte edilen repoya göre bellek içi `dict`'ten veya PostgreSQL'den okur:

**Kanıt:** `development.py:1360` — `IssueQueryService(issue_store, authorization)` — burada `issue_store` bir `DevelopmentIssueStore` (bellek içi `RLock`'lu `dict`)

### 8.3 `version` Alanı = İyimser Kilitleme

`DataQualityIssue.version` ve `DataSource.revision` conflict detection için kullanılır. Her mutasyon endpoint'i client'ın güncel `version`'ı göndermesini zorunlu kılar.

**Kanıt:** `api/models.py:476` — `IssueMutationRequest.version: int = Field(ge=1)` ve `development.py:651-652` — `if issue.version != expected_version: raise IssueConflictError`

### 8.4 Audit Event'leri Aynı Transaction'da Yazılır

`PostgreSQLTransactionalAudit.stage()` audit event'ini domain mutasyonuyla **aynı DB session'ında** `audit_outbox` tablosuna insert eder. Ayrı bir publish step ile kalıcı audit deposuna aktarılır.

**Kanıt:** `postgresql_outbox.py:68-80` — `session.execute(insert(self.table).values(...))`

### 8.5 Geliştirme Kullanıcıları Hardcoded

8 geliştirme kullanıcısı `build_default_development_users()` fonksiyonunda sabit tanımlıdır. Kullanıcı değiştirme `X-Development-User-Id` HTTP header'ı ile yapılır.

**Kanıt:** `api/identity.py:91-182`

### 8.6 Raporlar Dev Modunda Senkron Üretilir

`ReportService(... inline_processing=True)` — `POST /reports/` çağrısı raporu anında üretir ve READY döndürür.

**Kanıt:** `development.py:1391`

### 8.7 Skor Depolama Ayrımı

`score_contribution_graphs` tablosu contribution graph'ları (JSONB) saklar, ama `QualityScore` objeleri dev modunda `SQLiteScoreRepository` (bellek içi SQLite) kullanır.

**Kanıt:** `development.py:1147` — `repository = SQLiteScoreRepository()`

### 8.8 `users` Tablosu Yok

Kimlik tamamen dış sistemden (LDAP/Keycloak) gelir. Uygulama yalnızca `actor_id` string'lerini bilir. `ActorContext` session service veya dev resolver tarafından üretilir.

**Kanıt:** Migration'larda `CREATE TABLE users` ifadesi yok; `identity/models.py` yalnızca `ActorContext` dataclass'ını tanımlar.

### 8.9 Deduplication Digest ile Tekrar Engelleme

`data_quality_issues.deduplication_key_digest` (UNIQUE constraint) aynı başarısızlık için birden fazla issue oluşmasını engeller.

**Kanıt:** `20260723_01_issue_baseline.py:36` — `sa.Column("deduplication_key_digest", sa.String(128), nullable=False, unique=True)`

### 8.10 Downgrade Yasaklı

Her migration'ın `downgrade()` fonksiyonu `RuntimeError` fırlatır. Geri dönüş ileri yönlü düzeltici migration ile yapılır.

**Kanıt:** `20260723_01_issue_baseline.py:242` — `raise RuntimeError("Production downgrade is disabled; ...")`

---

## 9. Modül Bağımlılık Grafiği

Aşağıdaki grafik, `from veri_kalitesi.<module>` import'larının statik analizinden üretilmiştir.

```
api/ ──────────────> [audit, dashboard, data_sources, executions, identity,
                      issues, jobs, lineage, persistence, reporting, rules, scoring]
  │
  ├── (composition root — tüm domain modüllerini wire eder)

executions/ ───────> [audit, data_sources, rules, persistence]
  │
  ├── execution başlatma: rules'tan rule_version_ids alır
  ├── audit outbox'a yazar
  └── persistence: transactional_session kullanır

issues/ ───────────> [audit, identity, notifications]
  │
  ├── investigation/resolution: audit event yazar
  ├── authorization: identity.ActorContext kullanır
  └── notification: atama bildirimi gönderir

dashboard/ ────────> [scoring, lineage, identity]
  │
  ├── skorları aggregation'a tabi tutar
  ├── governance projection okur
  └── yetki: DashboardAuthorizationPolicy

reporting/ ────────> [scoring, audit]
  │
  ├── rapor verisi: scoring'den skor gözlemleri
  └── audit event: rapor oluşturma/indirme

jobs/ ─────────────> [audit, executions, reporting, persistence]
  │
  ├── worker: execution handler çağırır
  ├── report handler çağırır
  └── audit outbox'a yazar

data_sources/ ─────> [audit, data_protection, identity, persistence]
  │
  ├── profil çıkarma: data_protection policy kullanır
  └── yetki: identity.ActorContext

lineage/ ──────────> [audit, data_protection, data_sources, persistence]
  │
  └── governance profile: data_sources metadata kullanır

identity/ ─────────> [audit]
  │
  └── session validation: audit event yazar

audit/ ────────────> [persistence]
  │
  └── outbox: transactional_session kullanır

persistence/ ──────> []  (bağımsız — sadece SQLAlchemy)
environment_security/ ──> []  (bağımsız)
```

**Değişiklik etki analizi:**
- `persistence/` değişirse → tüm DB kullanan modüller etkilenir
- `identity/models.py` değişirse → tüm yetkilendirme mantığı etkilenir
- `audit/models.py` değişirse → tüm mutasyon servisleri etkilenir
- `rules/models.py` değişirse → executions, scoring, api etkilenir

---

## 10. Frontend-Backend Sözleşmesi

### 10.1 Model Eşleştirme Tablosu

| Frontend dosya | Backend Pydantic model | Mapper fonksiyon |
|----------------|----------------------|------------------|
| `dashboard/model.ts` | `DashboardSummaryResponse` | `dashboardViewModelFromApi()` |
| `dataSources/model.ts` | `DataSourceListItemResponse` | `dataSourcesFromApi()` |
| `rules/model.ts` | `RuleListItemResponse` | `rulesFromApi()` |
| `issues/model.ts` | `IssueListItemResponse` | `issuesFromApi()` |
| `executions/model.ts` | `ExecutionListItemResponse` | `executionsFromApi()` |
| `reports/model.ts` | `ReportSummaryResponse` | `reportSummaryFromApi()` |
| `audit/model.ts` | `AuditEventListResponse` | `auditPageFromApi()` |
| `profiling/model.ts` | `ProfileSnapshotListResponse` | `snapshotListItemFromApi()` |

### 10.2 İsimlendirme Farklılıkları

Backend **snake_case** (Python convention), Frontend **camelCase** (TypeScript convention) kullanır:

| Backend alanı | Frontend alanı |
|---------------|---------------|
| `quality_rule_id` | `id` |
| `primary_dimension` | `dimension` |
| `rule_version_id` | `versionId` |
| `version_no` | `versionNo` |
| `available_actions` | `availableActions` |
| `created_at` | `createdAt` |
| `issue_no` | `issueNo` |
| `scope_type` | `scopeType` |
| `occurrence_count` | `occurrenceCount` |
| `data_origin` | (doğrudan kullanılmaz) |
| `correlation_id` | `correlationId` (error handling'de) |

### 10.3 Synthetic Fixture Eşleşmesi

Her frontend modülü, API yüklenmeden önce gösterilen `synthetic*` sabitleri barındırır. Bunlar backend'deki `DEVELOPMENT_*` sabitlerinin frontend karşılığıdır:

| Frontend | Backend karşılığı |
|----------|------------------|
| `syntheticRules` (`rules/model.ts:56`) | `DEVELOPMENT_RULES` (`development.py:179`) |
| `syntheticIssues` (`issues/model.ts:60`) | `DEVELOPMENT_ISSUES` (`development.py:428`) |
| `syntheticExecutions` (`executions/model.ts`) | `DEVELOPMENT_EXECUTIONS` (`development.py:301`) |
| `syntheticDataSources` (`dataSources/model.ts`) | `DEVELOPMENT_SOURCES` (`development.py:145`) |
| `syntheticDashboardViewModel` (`dashboard/model.ts`) | `SQLiteScoreRepository` seed (`development.py:1147-1216`) |

### 10.4 API Response Envelope

Her API yanıtı şu ortak alanları taşır:

```json
{
  "api_version": "v1",
  "data_origin": "synthetic-development" | "runtime",
  "correlation_id": "uuid",
  ...
}
```

Frontend bu envelope'ı parse eder; `data_origin` değeri ile verinin sentetik mi gerçek mi olduğunu ayırt eder.

---

## Ek Okuma

| Konu | Dosya |
|------|-------|
| Backend modül envanteri | `01-Backend-Module-Inventory.md` |
| API endpoint envanteri | `02-API-Endpoint-Inventory.md` |
| Frontend modül envanteri | `03-Frontend-Module-Inventory.md` |
| Veritabanı şema envanteri | `04-Database-Schema-Inventory.md` |
| Test envanteri | `05-Test-Inventory.md` |
| Altyapı envanteri | `06-Infrastructure-Inventory.md` |
| Uygulama durum matrisi | `07-Implementation-Status-Matrix.md` |
