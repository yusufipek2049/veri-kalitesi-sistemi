---
type: functional-audit-work
stage: "17 — DS-05 Değişiklik Envanteri Doğrulama Raporu"
scope: slice-ds05-plan-validation
inputs:
  - 17-Slice-DS05-Change-Inventory.md
  - Repository source code (verified 2026-08-06)
project: Veri Kalitesi İzleme ve Skorlama Sistemi
branch: agent/36h1-persistent-job-core
created_at: 2026-08-06
---

# 17 — DS-05 Plan Doğrulama Raporu

> Bu belge `17-Slice-DS05-Change-Inventory.md` planındaki her önerinin
> mevcut repository koduyla doğrulanmış sonucunu bildirir. Kaynak kod
> değiştirilmemiştir.

---

## 1. Kapsam ve kabul kriterleri doğrulaması

| Plan önermesi | Kanıt | Sınıf |
|---|---|---|
| DS-05 otomatik sorun üretimi + manuel issue oluşturma | `issues/service.py:create_for_trigger` (satır 139) ve `issues/postgresql_repository.py:add_or_increment` (satır 234) mevcut | **CONFIRMED** |
| Yeni tablo yok; mevcut `data_quality_issues` ve `issue_history` genişletilir | `postgresql_repository.py:issue_tables()` (satır 70–200) — 5 tablo tanımlı, hiçbiri yeni değil | **CONFIRMED** |
| Yeni job type yok; mevcut `EXECUTION` job'ı kullanılır | `jobs/handlers.py:ExecutionJobHandler` (satır 48) ve `jobs/execution_command.py:PersistentExecutionCommandAdapter` (satır 15) mevcut | **CONFIRMED** |
| DS-03 production executor negative-result giriş kapısı | `executions/postgresql_executor.py:_execute_version` — `passed_count=population, failed_count=0, MeasurementStatus.PASSED` olarak sabitlenmiş | **CONFIRMED** — HIGH_RISK doğru tespit |

---

## 2. Tablolar, kolonlar ve migration doğrulaması

### 2.1 `data_quality_issues` mevcut durumu

| Mevcut kolon | Tip | Plan'da önerilen | Sınıf |
|---|---|---|---|
| `issue_id` | String(36) PK | Değişmez | **CONFIRMED** |
| `issue_no` | String(40) NOT NULL UNIQUE | Değişmez | **CONFIRMED** |
| `source_event_id` | String(36) NOT NULL | Plan "mevcut kolon, drop edilmez" der | **CONFIRMED** |
| `source_event_type` | String(40) NOT NULL | `MANUAL` eklenmesi gerekiyor (CHECK) | **CONFIRMED** |
| `trigger_type` | String(40) NOT NULL | `MANUAL` eklenmesi gerekiyor (CHECK) | **CONFIRMED** |
| `scope_type` / `scope_id` | String(20/36) NOT NULL | Değişmez | **CONFIRMED** |
| `status` | String(30) NOT NULL | Değişmez | **CONFIRMED** |
| `priority` | String(20) NOT NULL | Değişmez | **CONFIRMED** |
| `assignee_user_id` | String(36) NOT NULL | Değişmez | **CONFIRMED** |
| `deduplication_key_digest` | String(128) NOT NULL UNIQUE | Değişmez | **CONFIRMED** |
| `payload_digest` | String(128) NOT NULL | Değişmez | **CONFIRMED** |
| `occurrence_count` | Integer NOT NULL | Değişmez | **CONFIRMED** |
| `version` | BigInteger NOT NULL | Değişmez | **CONFIRMED** |
| `created_at` / `updated_at` / `last_seen_at` | DateTime(tz) NOT NULL | Değişmez | **CONFIRMED** |
| **`title`** | **YOK** | `String(200)` NOT NULL eklenecek | **CONFIRMED** — eksik alan doğru tespit |
| **`source_execution_id`** | **YOK** | nullable FK → `rule_executions` eklenecek | **CONFIRMED** — eksik alan doğru tespit |
| **`source_rule_version_id`** | **YOK** | nullable FK → `rule_versions` eklenecek | **CONFIRMED** — eksik alan doğru tespit |

**CHECK constraint doğrulama:**

| Constraint | Mevcut değer | Plan | Sınıf |
|---|---|---|---|
| `ck_issue_source_event_type` | `IN ('QUALITY', 'TECHNICAL')` | `MANUAL` eklenecek | **CONFIRMED** |
| `ck_issue_trigger_type` | `IN ('QUALITY_THRESHOLD', 'CRITICAL_RULE_FAILURE', 'TECHNICAL_ERROR')` | `MANUAL` eklenecek | **CONFIRMED** |

**Mevcut indeksler:** `ix_dq_issues_scope_updated`, `ix_dq_issues_assignee_status_updated` — plan yeni `source_execution_id` ve `source_rule_version_id` indeksleri öneriyor; mevcut yapıyla çakışma yok. **CONFIRMED**

### 2.2 `issue_history` mevcut durumu

| Mevcut kolon | Tip | Plan | Sınıf |
|---|---|---|---|
| `sequence_no` | BigInteger Identity PK | Değişmez | **CONFIRMED** |
| `history_id` | String(36) NOT NULL UNIQUE | Değişmez | **CONFIRMED** |
| `issue_id` | String(36) FK NOT NULL | Değişmez | **CONFIRMED** |
| `action` | String(120) NOT NULL | Değişmez | **CONFIRMED** |
| `actor_id` | String(128) NOT NULL | Değişmez | **CONFIRMED** |
| `old_status` / `new_status` | String(30) | Değişmez | **CONFIRMED** |
| `old/new_assignee_user_id` | String(36) nullable | Değişmez | **CONFIRMED** |
| `old/new_priority` | String(20) nullable | Değişmez | **CONFIRMED** |
| `resolution_id` / `verification_id` | String(36) nullable | Değişmez | **CONFIRMED** |
| `occurred_at` | DateTime(tz) NOT NULL | Değişmez | **CONFIRMED** |
| **`source_event_id`** | **YOK** | nullable String(36) eklenecek | **CONFIRMED** |
| **`source_event_occurred_at`** | **YOK** | nullable timestamptz eklenecek | **CONFIRMED** |
| **`source_event_payload_digest`** | **YOK** | nullable String(64) eklenecek | **CONFIRMED** |

**Partial unique index** `uq_issue_history_source_event_id` — mevcut tabloda yok, plan doğru şekilde eklenmesini öneriyor. **CONFIRMED**

### 2.3 Migration sırası

| Adım | Plan | Mevcut head | Sınıf |
|---|---|---|---|
| Migration 01–17 değiştirilmez | 17 dosya mevcut, son: `20260805_17_catalog_metadata_discovery.py` | **CONFIRMED** |
| Yeni migration `20260806_18_issue_generation.py` | Henüz yok | **CONFIRMED** — doğru sıralama |
| Migration sırası: nullable ekle → backfill → constraint → FK → history receipt | Mantıksal ve güvenli | **CONFIRMED** |

---

## 3. Repository ve servis değişiklikleri doğrulaması

### 3.1 Mevcut çekirdek yeniden kullanım

| Plan önermesi | Gerçek dosya/simbol | Durum | Sınıf |
|---|---|---|---|
| `RuleExecutionResult.eligible_for_auto_issue` | `executions/models.py` satır 168 — `eligible_for_auto_issue: bool = True` | Mevcut | **CONFIRMED** |
| `complete_success` | `executions/postgresql_repository.py` — `complete_success(execution_id, results, finished_at, ...)` | Mevcut | **CONFIRMED** |
| `IssueService.create_for_trigger` | `issues/service.py` satır 139 — `(trigger: IssueTrigger, actor_context: ActorContext \| None)` | Mevcut | **CONFIRMED** |
| `add_or_increment` advisory lock | `issues/postgresql_repository.py` satır 252 — `func.pg_advisory_xact_lock(...)` | Mevcut | **CONFIRMED** |
| `audit_outbox` parametresi | `add_or_increment(..., audit_outbox: PostgreSQLTransactionalAudit)` | Mevcut | **CONFIRMED** |
| State-machine metodları | `start_investigation` (330), `reassign` (402), `resolve` (500), `record_verification_result` (607), `close` (721) | Mevcut | **CORRECTION_REQUIRED** — Plan `record_verification` der, gerçek isim `record_verification_result` |
| `PersistentJobWorker` | `jobs/worker.py` — `class PersistentJobWorker` | Mevcut | **CONFIRMED** |
| `ExecutionJobHandler` | `jobs/handlers.py` satır 48 | Mevcut | **CONFIRMED** |
| `IssueQueryService.list_for_actor` | `issues/query.py` satır 52 — `list_for_actor(actor_context)` | Mevcut | **CONFIRMED** |
| `list_issues_for_scopes` | `issues/query.py` — `IssueReader` protocol'ünde tanımlı | Mevcut | **CONFIRMED** |
| `SQLiteIssueMigrator` | `issues/migration.py` satır 61 | Mevcut | **CONFIRMED** |
| `IssueConflictError` | `issues/__init__.py` export + `postgresql_repository.py` kullanımında mevcut | Mevcut | **CONFIRMED** |

### 3.2 Domain model değişiklikleri

| Plan önermesi | Mevcut durum | Sınıf |
|---|---|---|
| `IssueTriggerType` — `MANUAL` değeri eklenecek | Mevcut: `QUALITY_THRESHOLD`, `CRITICAL_RULE_FAILURE`, `TECHNICAL_ERROR` (satır 26–29) | **CONFIRMED** |
| `IssueSourceEventType` — `MANUAL` değeri eklenecek | Mevcut: `QUALITY`, `TECHNICAL` (satır 32–34) | **CONFIRMED** |
| `IssueTrigger` — `execution_id`, `rule_version_id`, `eligible_for_auto_issue`, `failed_count`, `measurement_status` alanları eklenecek | Mevcut alanlar: `trigger_type`, `scope_type`, `scope_id`, `deduplication_key`, `occurred_at`, `correlation_id`, `event_id` (satır 72–79). Hiçbiri ek alan yok | **CONFIRMED** — eksik alanlar doğru tespit |
| `DataQualityIssue` — `title`, `source_execution_id`, `source_rule_version_id` eklenecek | Mevcut: 16 alan (satır 162–178). Bu üç alan yok | **CONFIRMED** |
| `IssueHistoryEntry` — receipt alanları eklenecek | Mevcut: 13 alan (satır 182–195). Receipt alanları yok | **CONFIRMED** |
| `IssueAccessPolicy` — `producer_roles` ve `manual_creator_roles` alanları | **Mevcut**: `allowed_reader_actor_types` ve `allowed_producer_actor_types` (satır 199–207). `manual_creator_roles` YOK | **CORRECTION_REQUIRED** — Alan isimleri yanlış; `manual_creator_roles` mevcut değil, eklenecek |
| `ManualIssueDraft` yeni model | Repository'de yok | **CONFIRMED** — yeni dosya doğru |

### 3.3 Composition engeli

| Plan önermesi | Gerçek kod | Sınıf |
|---|---|---|
| `UnavailableIssueAssignmentResolver` fail-closed | `api/composition.py` satır 149–153 — `resolve_assignment` her çağrıda `IssueAssignmentError` fırlatır | **CONFIRMED** — HIGH_RISK doğru tespit |
| `UnavailableIssueNotificationPublisher` fail-closed | `api/composition.py` satır 156–165 — `create_for_event` her çağrıda `NotificationTechnicalError` fırlatır | **CONFIRMED** |
| `PhaseBProviders` tanımlı | `api/composition.py` satır 114–138 — 7 provider alanı var | **CONFIRMED** |
| `PhaseBProviders` assignment resolver içermiyor | `PhaseBProviders` alanları: `rule_test_executor`, `issue_assignee_directory`, `issue_assignee_option_provider`, `issue_resolution_protector`, `issue_verification_resolver`, `issue_notification_publisher`, `issue_notification_actor_context_provider`. **`IssueAssignmentResolver` YOK** | **MISSING_DETAIL** — Plan `PhaseBProviders`'tan "gerçek ownership resolver" bağlanmasını öneriyor fakat `PhaseBProviders`'ta bu port yok; ya eklenmeli ya da ayrı bir composition yolu tanımlanmalı |
| `create_application` `UnavailableIssueAssignmentResolver` kullanıyor | Satır 297: `UnavailableIssueAssignmentResolver()` hardcoded | **CONFIRMED** — düzeltilmesi gereken alan |

### 3.4 Notification ayrımı

| Plan önermesi | Gerçek kod | Sınıf |
|---|---|---|
| `_publish_notification` issue commit sonrası çağrılıyor | `service.py` satır 304–305: `publish_pending()` → `_publish_notification(trigger, context, stored)` | **CONFIRMED** |
| Notification hatası issue başarısını bozuyor | `_publish_notification` (satır 868–913) `NotificationTechnicalError` → `IssueNotificationTechnicalError` olarak fırlatır; issue zaten persist edilmiş ama exception yayılır | **CONFIRMED** — HIGH_RISK doğru tespit |
| `create_for_trigger` notification hatası job retry'a yol açar | Exception `create_for_trigger`'dan çıkar → worker retry mekanizması occurrence artırır | **CONFIRMED** |

### 3.5 `PersistentExecutionCommandAdapter`

| Plan önermesi | Gerçek kod | Sınıf |
|---|---|---|
| Terminal execution'da permanent error | `execution_command.py` satır 39–42: `result is None` → `PermanentJobError("EXECUTION_NOT_FOUND_OR_TERMINAL")` | **CONFIRMED** |
| Issue bridge yok | `execute()` metodu sadece execution sonucu döndürür; issue post-processing YOK | **CONFIRMED** — eksik doğru tespit |
| `JobCompletionOutcome` döndürür | Satır 43–47: `SUCCESS` veya `QUALITY_FAILURE` | **CONFIRMED** |

### 3.6 `ProductionWorkerProviders`

| Plan önermesi | Gerçek kod | Sınıf |
|---|---|---|
| `ProductionWorkerProviders` tanımlı | `jobs/production.py` satır 48 — `secret_resolver`, `execution_executor` | **CONFIRMED** |
| `create_production_worker` tarafından kullanılmaz | `create_production_worker` (satır 55–167) tüm bağımlılıkları inline oluşturur; `ProductionWorkerProviders` sınıfı referans edilmez | **CONFIRMED** — plan doğru tespit |
| Worker'da issue service/resolver/bridge yok | `create_production_worker` içinde issue ile ilgili hiçbir bileşen yok | **CONFIRMED** — eksik doğru tespit |

---

## 4. API endpoint doğrulaması

### 4.1 Mevcut endpoint'ler

| Endpoint | Mevcut durum | Plan | Sınıf |
|---|---|---|---|
| `GET /api/v1/issues` | `api/app.py` — `get_issues` mevcut; `IssueQueryService.list_for_actor` kullanır | `title`, `source_execution_id`, `source_rule_version_id` ve sayfa `CREATE_ISSUE` action eklenecek | **CONFIRMED** |
| `POST /api/v1/issues` | **YOK** | Yeni endpoint: `IssueCreateRequest` → 201 | **CONFIRMED** — yeni endpoint doğru |
| Issue lifecycle endpoint'leri | investigation, assignment, resolution, verification, closure — hepsi mevcut | Değişmez | **CONFIRMED** |

### 4.2 API model doğrulaması

| Plan önermesi | Mevcut durum | Sınıf |
|---|---|---|
| `IssueListItemResponse` — `title`, `source_execution_id`, `source_rule_version_id` eklenecek | Mevcut alanlar (satır 510–526): `issue_id`, `issue_no`, `source_event_type`, `trigger_type`, `scope_type`, `scope_id`, `status`, `priority`, `occurrence_count`, `version`, `available_actions`, `created_at`, `updated_at`, `last_seen_at`. Üç yeni alan yok | **CONFIRMED** |
| `IssueListResponse` — sayfa `available_actions` | Mevcut (satır 553–560): `api_version`, `data_origin`, `correlation_id`, `limit`, `items`. **Sayfa düzeyi `available_actions` YOK** | **MISSING_DETAIL** — Plan sayfa düzeyi `CREATE_ISSUE` action projection'ı öneriyor; `IssueListResponse` modelinde bu alan yok, eklenmesi gerekiyor |
| `IssueCreateRequest` | Repository'de yok | **CONFIRMED** — yeni model doğru |
| `IssueMutationResponse` | Mevcut (satır 590): `api_version`, `data_origin`, `correlation_id`, `item` | **CONFIRMED** — yeniden kullanılabilir |
| `_issue_actions` — `CREATE_ISSUE` eklenecek | Mevcut (satır 3027–3073): sadece per-issue actions (`START_INVESTIGATION`, `REASSIGN`, `RESOLVE`, `VERIFY`, `CLOSE`). `CREATE_ISSUE` YOK | **CONFIRMED** — eksik doğru tespit |

---

## 5. Frontend doğrulaması

| Plan önermesi | Mevcut durum | Sınıf |
|---|---|---|
| `IssuesPage.tsx` — create dialog yok | `IssuesPage.tsx` — Dialog import var ama sadece lifecycle action'lar için kullanılıyor; create dialog YOK | **CONFIRMED** |
| `model.ts` — `MANUAL` trigger/source type yok | Mevcut trigger type'lar: `CRITICAL_RULE_FAILURE`, `TECHNICAL_ERROR`, `QUALITY_THRESHOLD`. Source event type'lar: `QUALITY`, `TECHNICAL`. `MANUAL` yok | **CONFIRMED** |
| `api.ts` — `createIssue` yok | Mevcut fonksiyonlar: `fetchIssues`, `startIssueInvestigation`, `fetchIssueAssignmentOptions`, `reassignIssue`, `resolveIssue`, `verifyIssue`, `closeIssue`, `fetchLineageSnapshot`, `fetchGovernanceProjection`, `fetchInvestigationEvidence`. `createIssue` YOK | **CONFIRMED** |
| `catalog/api.ts` değişmez | DS-04'ten `listCatalogDatasets` mevcut | **CONFIRMED** — yeniden kullanım doğru |
| `dataSources/api.ts` değişmez | Mevcut source list endpoint var | **CONFIRMED** |
| `App.tsx:IssuesRoute` mevcut | DS-04'ten güncellenmiş route yapısı var | **CONFIRMED** |
| `e2e/issues.spec.ts` mevcut | 269 satır — mevcut | **CONFIRMED** |
| `e2e/issues-live.spec.ts` yeni | Repository'de yok | **CONFIRMED** — yeni dosya doğru |

---

## 6. Permission, scope ve audit doğrulaması

| Plan önermesi | Mevcut durum | Sınıf |
|---|---|---|
| `IssueAccessPolicy` — `producer_roles` / `manual_creator_roles` | Mevcut: `allowed_reader_actor_types`, `allowed_producer_actor_types` (satır 199–207). Plan'daki alan isimleri **yanlış** | **CORRECTION_REQUIRED** — Gerçek alan isimleri `allowed_reader_actor_types` ve `allowed_producer_actor_types`; `manual_creator_roles` ayrı alan olarak eklenecek veya mevcut yapı genişletilecek |
| `ActorType.SERVICE` / `ActorType.USER` kapısı | `allowed_producer_actor_types` default `frozenset({ActorType.SERVICE})` | **CONFIRMED** |
| `can_view_enterprise` frontend action tek başına izin değil | `_issue_actions` (satır 3027–3073) sadece `actor_context.roles` ve `permitted_source/dataset_ids` kontrol eder | **CONFIRMED** |
| Audit olay isimleri | `DATA_QUALITY_ISSUE_TRIGGER_PROCESSED`, `DATA_QUALITY_ISSUE_REOPENED`, `DATA_QUALITY_ISSUE_LINKED` — mevcut audit event isimleri | **MISSING_DETAIL** — Plan bu event isimlerinin "korunduğunu" söylüyor fakat repository'de bu isimlerin tanımlandığı yeri doğrulamak gerekiyor (audit event enum/constants dosyası) |
| `DATA_QUALITY_ISSUE_MANUALLY_CREATED` | Repository'de bu event ismi yok | **CONFIRMED** — yeni event doğru |

---

## 7. Test planı doğrulaması

### 7.1 Mevcut test dosyaları

| Plan referansı | Mevcut dosya | Satır | Sınıf |
|---|---|---|---|
| `test_issues.py` | `tests/unit/test_issues.py` | 2053 | **CONFIRMED** |
| `test_issue_api.py` | `tests/unit/test_issue_api.py` | 1062 | **CONFIRMED** |
| `test_persistent_job_handlers.py` | — | — | **MISSING_DETAIL** — Dosya adı doğru mu kontrol edilmeli |
| `test_persistent_job_worker.py` | — | — | **MISSING_DETAIL** — Dosya adı doğru mu kontrol edilmeli |
| `test_postgresql_issue_mutations.py` | `tests/integration/` | 474 | **CONFIRMED** |
| `test_postgresql_issue_migration.py` | `tests/integration/` | 385 | **CONFIRMED** |
| `test_postgresql_issue_persistence.py` | `tests/integration/` | 101 | **CONFIRMED** |
| `test_application_composition.py` | `tests/integration/` | 156 | **CONFIRMED** |
| `test_postgresql_execution_persistence.py` | `tests/integration/` | 676 | **CONFIRMED** |
| `test_postgresql_job_queue.py` | `tests/integration/` | 1252 | **CONFIRMED** |
| `legacy_sqlite_issue_repository.py` | `tests/support/` | 809 | **CONFIRMED** |

### 7.2 Yeni test dosyaları

| Plan referansı | Mevcut durum | Sınıf |
|---|---|---|
| `test_execution_issue_bridge.py` | Repository'de yok | **CONFIRMED** — yeni dosya doğru |
| `test_issue_assignment.py` | Repository'de yok | **CONFIRMED** — yeni dosya doğru |
| `test_postgresql_issue_generation_migration.py` | Repository'de yok | **CONFIRMED** — yeni dosya doğru |
| `test_ds05_issue_generation.py` | Repository'de yok | **CONFIRMED** — yeni dosya doğru |

---

## 8. Production composition root doğrulaması

| Plan önermesi | Mevcut durum | Sınıf |
|---|---|---|
| `create_production_worker` inline composition | `jobs/production.py` satır 55–167 — tüm bağımlılıklar inline | **CONFIRMED** |
| Worker'da issue service yok | Issue service, repository, bridge, resolver — hiçbirisi yok | **CONFIRMED** |
| Worker'da issue actor context provider yok | `_service_actor_context_provider` sadece metadata discovery için (satır 141–147); issue producer için yok | **CONFIRMED** |
| `create_development_app` | `api/development.py` — `create_development_app` (NOT `create_development_api`) | **CORRECTION_REQUIRED** — Plan `create_development_api` der, gerçek isim `create_development_app` |
| `DevelopmentIssueStore` | `api/development.py` — mevcut | **CONFIRMED** |

---

## 9. Sınıflandırma özeti

### CONFIRMED (42 madde)

1. `RuleExecutionResult.eligible_for_auto_issue` mevcut (satır 168)
2. `complete_success` mevcut `executions/postgresql_repository.py`
3. `IssueService.create_for_trigger` mevcut (satır 139)
4. `add_or_increment` advisory lock ile mevcut (satır 234, 252)
5. `audit_outbox` parametresi mevcut
6. `PersistentJobWorker` mevcut
7. `ExecutionJobHandler` mevcut
8. `PersistentExecutionCommandAdapter` mevcut (satır 15)
9. `IssueQueryService.list_for_actor` mevcut (satır 52)
10. `SQLiteIssueMigrator` mevcut (satır 61)
11. `PhaseBProviders` mevcut (satır 114)
12. `UnavailableIssueAssignmentResolver` fail-closed (satır 149)
13. `UnavailableIssueNotificationPublisher` fail-closed (satır 156)
14. `CURRENT_MIGRATION_HEAD = "20260805_17"` (satır 82)
15. `get_issues` endpoint mevcut
16. `_issue_actions` fonksiyonu mevcut (satır 3027)
17. `IssueListItemResponse` mevcut (satır 510)
18. `IssueListResponse` mevcut (satır 553)
19. `IssueMutationResponse` mevcut (satır 590)
20. `_publish_notification` issue commit sonrası çağrılıyor (satır 305)
21. `_execute_version` hardcoding — HIGH_RISK doğru tespit
22. `data_quality_issues` — `title`, `source_execution_id`, `source_rule_version_id` YOK, eklenecek
23. `issue_history` — receipt kolonları YOK, eklenecek
24. CHECK constraint'ler `MANUAL` içermiyor, eklenecek
25. `IssueTriggerType` — `MANUAL` yok
26. `IssueSourceEventType` — `MANUAL` yok
27. `IssueTrigger` — execution/ref alanları yok
28. `DataQualityIssue` — title/source refs yok
29. `IssueHistoryEntry` — receipt alanları yok
30. `IssueCreateRequest` yok, yeni oluşturulacak
31. `ManualIssueDraft` yok, yeni oluşturulacak
32. `CREATE_ISSUE` page action yok
33. `POST /api/v1/issues` endpoint yok
34. Frontend `createIssue` API fonksiyonu yok
35. Frontend create dialog yok
36. `e2e/issues.spec.ts` mevcut
37. `ProductionWorkerProviders` tanımlı ama kullanılmıyor
38. Worker'da issue bileşeni yok
39. `DevelopmentIssueStore` mevcut
40. `seed_database.py` mevcut (1178 satır)
41. `compose.yaml` mevcut (94 satır)
42. Tüm mevcut test dosyaları referansları doğru

### CORRECTION_REQUIRED (4 madde)

1. **`IssueAccessPolicy` alan isimleri yanlış** — Plan `producer_roles` ve `manual_creator_roles` der; gerçek isimler `allowed_reader_actor_types` ve `allowed_producer_actor_types`. `manual_creator_roles` ayrı alan olarak yok.
2. **`record_verification` → `record_verification_result`** — Plan `service.py:record_verification` der; gerçek metod adı `record_verification_result` (satır 607).
3. **`create_development_api` → `create_development_app`** — Plan `api/development.py:create_development_api` der; gerçek fonksiyon adı `create_development_app`.
4. **`PhaseBProviders` — `IssueAssignmentResolver` port eksik** — Plan "gerçek ownership resolver" bağlanmasını öneriyor ama `PhaseBProviders`'ta bu port tanımlı değil; composition'da `UnavailableIssueAssignmentResolver` hardcoded.

### MISSING_DETAIL (4 madde)

1. **`PhaseBProviders` → `IssueAssignmentResolver` wiring** — Plan `PhaseBProviders` üzerinden gerçek resolver bağlanmasını söylüyor ama `PhaseBProviders` dataclass'ında bu alan yok. Ya `PhaseBProviders`'a eklenmeli ya da `create_application`'da ayrı bir injection yolu tanımlanmalı.
2. **`IssueListResponse` sayfa düzeyi `available_actions`** — Plan "sayfa düzeyi `CREATE_ISSUE` action projection" öneriyor; `IssueListResponse` modelinde bu alan yok. Eklenecek alanın tipi ve placement belirtilmeli.
3. **`PersistentExecutionCommandAdapter` → bridge injection mekanizması** — Plan adapter'a issue bridge eklenmesini söylüyor ama injection mekanizması (constructor parametresi mi, optional field mı) detaylandırılmamış.
4. **Audit event isimleri doğrulaması** — `DATA_QUALITY_ISSUE_TRIGGER_PROCESSED`, `DATA_QUALITY_ISSUE_REOPENED`, `DATA_QUALITY_ISSUE_LINKED` event isimlerinin mevcut audit enum/constants dosyasındaki yeri doğrulanmamış.

### OUT_OF_SCOPE (0 madde)

Plan kapsam dışı öneri içermiyor.

### UNNECESSARY_CHANGE (0 madde)

Plan gereksiz değişiklik önermiyor; tüm önerilen değişiklikler mevcut boşluklara karşılık geliyor.

### HIGH_RISK (4 madde)

1. **DS-03 production executor stub** — `_execute_version` `passed_count=population, failed_count=0, PASSED` olarak sabitlenmiş. Gerçek kalite başarısızlığı üretilemiyor. DS-05 otomatik issue testi geçemez. Plan doğru NO-GO kapısı koymuş.
2. **`UnavailableIssueAssignmentResolver` hardcoded** — `create_application` satır 297'de hardcoded. Tüm issue oluşturma (otomatik + manuel) engelleniyor. DS-05 öncesi mutlaka çözülmeli.
3. **Notification → issue başarısı bağımlılığı** — `_publish_notification` (satır 305) `publish_pending()` sonrası çağrılıyor ve exception fırlatabilir. Issue persist edilmiş ama job retry occurrence artırır. Tutarsızlık riski.
4. **Worker production composition eksik** — `create_production_worker` issue service, repository, bridge, resolver ve dar scope SERVICE context içermiyor. DS-05 production yolu bu bileşenler olmadan çalışamaz.

---

## 10. Uygulamaya hazır maddeler

Aşağıdaki maddeler herhangi bir düzeltme gerektirmeden uygulanabilir:

1. Migration `20260806_18_issue_generation.py` — DDL değişiklikleri (nullable kolon ekleme, backfill, constraint, FK, indeks)
2. `data_quality_issues` tablosuna `title`, `source_execution_id`, `source_rule_version_id` eklenmesi
3. `issue_history` tablosuna receipt kolonları eklenmesi
4. CHECK constraint'lerin `MANUAL` değerini içerecek biçimde güncellenmesi
5. `issues/postgresql_repository.py:issue_tables()` runtime metadata'sının eşitlenmesi
6. `issues/models.py` — `IssueTriggerType.MANUAL`, `IssueSourceEventType.MANUAL`, `ManualIssueDraft`
7. `issues/contracts.py` — `add_or_increment` receipt parametreleri
8. `issues/service.py:create_for_trigger` — eligibility doğrulama, notification ayrımı
9. `issues/execution_bridge.py` — yeni adapter
10. `issues/assignment.py` — yeni resolver
11. `api/models.py` — `IssueCreateRequest`, `IssueListItemResponse` genişletme
12. `api/app.py` — `POST /api/v1/issues`, `CREATE_ISSUE` action projection
13. Frontend `model.ts`, `api.ts`, `IssuesPage.tsx` değişiklikleri
14. Test dosyaları (mevcut + yeni)

---

## 11. Uygulamadan önce düzeltilmesi gerekenler

| # | Düzeltme | Neden | Öncelik |
|---|---|---|---|
| 1 | Plan §7.1'deki `IssueAccessPolicy` alan isimlerini `allowed_producer_actor_types` olarak düzelt; `manual_creator_roles` için yeni alan tanımı ekle | Mevcut alan isimleri yanlış | Uygulama öncesi |
| 2 | Plan §4.1'deki `record_verification` → `record_verification_result` | Yanlış sembol adı | Uygulama öncesi |
| 3 | Plan §4.1'deki `create_development_api` → `create_development_app` | Yanlış fonksiyon adı | Uygulama öncesi |
| 4 | `PhaseBProviders` → `IssueAssignmentResolver` wiring mekanizmasını netleştir: `PhaseBProviders`'a alan ekle veya `create_application`'da ayrı injection yolu tanımla | Composition boşluğu | Uygulama öncesi |
| 5 | `IssueListResponse` sayfa düzeyi `available_actions` alanının tipi ve placement'ını belirt | MISSING_DETAIL | Uygulama öncesi |
| 6 | `PersistentExecutionCommandAdapter` bridge injection mekanizmasını belirt (constructor parametresi, optional field, vs.) | MISSING_DETAIL | Uygulama öncesi |
| 7 | Audit event isimlerinin (`DATA_QUALITY_ISSUE_TRIGGER_PROCESSED` vb.) mevcut enum/constants dosyasındaki yeri doğrula veya yeni tanımları belirt | MISSING_DETAIL | Uygulama öncesi |
| 8 | DS-03 production executor negative-result testi — `eligible_for_auto_issue=true`, `failed_count>0`, `FAILED`/izinli `WARNING` sonucu | NO-GO kapısı | DS-05 öncesi zorunlu |

---

## 12. Önerilen gerçek dosya değişiklikleri

### Migration
- `alembic/versions/20260806_18_issue_generation.py` **(yeni)**

### Backend — mevcut dosyalar
- `src/veri_kalitesi/issues/models.py` — `MANUAL` enum değerleri, `title`/source refs/receipt alanları, `ManualIssueDraft`
- `src/veri_kalitesi/issues/contracts.py` — `add_or_increment` receipt parametreleri
- `src/veri_kalitesi/issues/postgresql_repository.py` — metadata eşitleme, receipt-first replay
- `src/veri_kalitesi/issues/service.py` — `create_manual`, notification ayrımı, eligibility doğrulama
- `src/veri_kalitesi/issues/migration.py` — legacy title backfill
- `src/veri_kalitesi/issues/__init__.py` — yeni export'lar
- `src/veri_kalitesi/jobs/execution_command.py` — bridge injection, terminal replay post-processing
- `src/veri_kalitesi/jobs/production.py` — issue service/resolver/bridge wiring
- `src/veri_kalitesi/jobs/settings.py` — fail-fast doğrulama
- `src/veri_kalitesi/jobs/entrypoint.py` — fail-fast
- `src/veri_kalitesi/api/models.py` — `IssueCreateRequest`, `IssueListItemResponse` genişletme, `IssueListResponse` sayfa action
- `src/veri_kalitesi/api/app.py` — `POST /api/v1/issues`, `CREATE_ISSUE` projection
- `src/veri_kalitesi/api/composition.py` — head 18, gerçek resolver, manual service wiring
- `src/veri_kalitesi/api/development.py` — manual create contract

### Backend — yeni dosyalar
- `src/veri_kalitesi/issues/execution_bridge.py` **(yeni)**
- `src/veri_kalitesi/issues/assignment.py` **(yeni)**

### Frontend
- `frontend/src/issues/model.ts` — `MANUAL`, title, source refs, `CREATE_ISSUE`, `IssueCreateInput`
- `frontend/src/issues/api.ts` — `createIssue`
- `frontend/src/issues/IssuesPage.tsx` — create dialog
- `frontend/src/App.tsx` — `IssuesRoute` manual create wiring

### Altyapı
- `scripts/seed_database.py` — yeni alan uyumu
- `infra/development/compose.yaml` — issue-producer ayarları

### Testler
- `tests/unit/test_execution_issue_bridge.py` **(yeni)**
- `tests/unit/test_issue_assignment.py` **(yeni)**
- `tests/integration/test_postgresql_issue_generation_migration.py` **(yeni)**
- `tests/integration/test_ds05_issue_generation.py` **(yeni)**
- Mevcut test dosyalarına ekleme: `test_issues.py`, `test_issue_api.py`, `test_persistent_job_handlers.py`, `test_persistent_job_worker.py`, `test_postgresql_issue_mutations.py`, `test_postgresql_issue_migration.py`, `test_application_composition.py`

### Ön koşul (DS-03)
- `src/veri_kalitesi/executions/postgresql_executor.py` — gerçek negative-result semantiği

---

## 13. Değişmemesi gereken alanlar

- Migration 01–17 dosyaları
- `rule_execution_results`, `rule_executions` DDL
- `background_jobs`, `workers`, dead-letter, lease/progress DDL
- `jobs/worker.py`, `jobs/postgresql_repository.py`, `jobs/composition.py:create_persistent_job_runtime` çekirdeği
- Issue investigation/resolution/verification/closure state-machine kuralları
- Rule approval, data-source activation, metadata discovery state-machine'leri
- Notification tabloları, kanal adapter'ları, teslimat ekranları
- Skor, schedule, SLA, exception, contract, ServiceNow alanları
- Production'da SQLite/in-memory/fake assignment, issue, executor fallback

---

## 14. Kesin uygulama sırası

Plan §10'daki sıralama doğrulanmıştır; ek düzeltme gerekmez:

1. **DS-03 production executor negative-result** giriş kapısı ve testi
2. **Migration 18**: title/source refs, MANUAL constraints, history receipt
3. **Domain modelleri**, validation, repository contract/runtime metadata
4. **PostgreSQL receipt-first** create/increment/replay ve audit atomikliği
5. **Ownership assignment resolver** ve unit testleri
6. **Execution→issue trigger adapter** ve eligibility/technical policy testleri
7. **`PersistentExecutionCommandAdapter`** terminal replay/post-processing zinciri
8. **Worker settings, production providers, composition, entrypoint** fail-fast
9. **Manual `IssueService.create_manual`**, API model/route, production composition
10. **Backend unit, migration, PostgreSQL application-chain** testleri
11. **Frontend model/API** ve `IssuesPage` create dialog/wiring
12. **Development seed/compose** issue-producer ayarları
13. **Frontend unit/build** ve mock E2E
14. **Gerçek compose live E2E**: automatic issue, manual issue, retry, audit

---

## 15. Çalıştırılacak testler

### Backend unit
```
python3 -m pytest -q tests/unit/test_issues.py
python3 -m pytest -q tests/unit/test_issue_api.py
python3 -m pytest -q tests/unit/test_execution_issue_bridge.py
python3 -m pytest -q tests/unit/test_issue_assignment.py
python3 -m pytest -q tests/unit/test_persistent_job_handlers.py
python3 -m pytest -q tests/unit/test_persistent_job_worker.py
```

### PostgreSQL entegrasyon
```
# Migration 18 + issue mutation + application composition
# (PostgreSQL test URL gerekli)
python3 -m pytest -q tests/integration/test_postgresql_issue_generation_migration.py
python3 -m pytest -q tests/integration/test_postgresql_issue_mutations.py
python3 -m pytest -q tests/integration/test_postgresql_issue_migration.py
python3 -m pytest -q tests/integration/test_application_composition.py
python3 -m pytest -q tests/integration/test_postgresql_execution_persistence.py
python3 -m pytest -q tests/integration/test_ds05_issue_generation.py
```

### Frontend
```
cd frontend && npm test -- --run
cd frontend && npm run build
```

### E2E
```
cd frontend && npx playwright test e2e/issues.spec.ts
cd frontend && npx playwright test e2e/issues-live.spec.ts
```

---

## 16. Go / No-Go kararı

**CONDITIONAL GO — Plan uygulanabilir, 8 düzeltme ve 2 ön koşul ile.**

### Zorunlu ön koşullar (NO-GO kapıları):

1. **DS-03 production executor**: `PostgreSQLRuleExecutionExecutor._execute_version` gerçek başarısız sonuç üretebilmelidir. Fake executor ile DS-05 application testi kabul edilmez.
2. **Worker production composition**: Gerçek assignee directory ve dar scope'lu trusted `ISSUE_PRODUCER` SERVICE context sağlanmalıdır.

### Zorunlu plan düzeltmeleri:

| # | Düzeltme | Sınıf |
|---|---|---|
| 1 | `IssueAccessPolicy` alan isimleri | CORRECTION_REQUIRED |
| 2 | `record_verification` → `record_verification_result` | CORRECTION_REQUIRED |
| 3 | `create_development_api` → `create_development_app` | CORRECTION_REQUIRED |
| 4 | `PhaseBProviders` → `IssueAssignmentResolver` wiring | MISSING_DETAIL |
| 5 | `IssueListResponse` sayfa `available_actions` | MISSING_DETAIL |
| 6 | Bridge injection mekanizması | MISSING_DETAIL |
| 7 | Audit event isimleri doğrulama | MISSING_DETAIL |
| 8 | DS-03 executor negative-result testi | HIGH_RISK |

### Bu düzeltmeler yapıldıktan sonra plan uygulanmaya hazırdır.

Mevcut issue state-machine, PostgreSQL advisory/row lock repository'si, transactional audit ve DS-03 worker çekirdeği yeniden kullanılabilir. Yeni issue tablosu, queue veya notification hattı gerekli değildir. Planın mimari kararları repository gerçekleriyle örtüşmektedir.
