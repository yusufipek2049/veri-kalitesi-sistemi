# Backend Module Inventory — Read-Only Evidence

> Salt okunur mekanik envanter. Dokümantasyon beyanı değil, yalnızca kod kanıtı.

## 1. Module List

Root: `src/veri_kalitesi/`

| Module | Files | Purpose |
|--------|-------|---------|
| `api/` | 7 | FastAPI HTTP boundary: app factory, BFF session, identity, models, errors, dev mode |
| `audit/` | 8 | Audit event recording, outbox, redaction, query, policies |
| `dashboard/` | 4 | Dashboard overview query service and models |
| `data_protection/` | 3 | KVKK data processing inventory, coverage |
| `data_sources/` | 11 | Source onboarding, connectors, metadata, profiling, query |
| `environment_security/` | 2 | Runtime environment, secrets, startup evidence |
| `executions/` | 10 | Execution lifecycle, scheduling, strategy engine, source usage |
| `identity/` | 6 | Actor context, sessions, LDAP, throttling |
| `incident_response/` | 4 | Security incident, KVKK breach workflow |
| `issues/` | 8 | Issue lifecycle, investigation, resolution, verification |
| `jobs/` | 7 | Persistent job queue, worker, handlers, lifecycle |
| `lineage/` | 7 | Lineage events, governance profiles, impact analysis |
| `notifications/` | 5 | Notification events, channel adapters, delivery |
| `persistence/` | 2 | SQLAlchemy session factory, PostgreSQL transaction boundary |
| `reporting/` | 7 | Report generation, export, scheduling, preview |
| `retention/` | 8 | Retention policy, disposal, legal hold, archive recall |
| `rules/` | 8 | Quality rule CRUD, versions, templates, approval |
| `scoring/` | 8 | Score computation, contributions, trends, policies |
| `secure_sdlc/` | 9 | SAST, SBOM, pentest, vulnerability, evidence gate |
| `servicenow/` | 4 | ServiceNow ticket integration |
| `synthetic_data/` | 10 | Synthetic generation, oracle, temporal, canonical |

## 2. Domain Models (Code Evidence)

### 2.1 `data_sources/models.py`
| Class | Type | Line ref |
|-------|------|----------|
| `SourceType` | Enum(CSV, POSTGRESQL, MSSQL, ORACLE, MYSQL, REST_API, OTHER) | L21 |
| `DataSourceStatus` | Enum(TEST_PENDING, TEST_SUCCEEDED, TEST_FAILED, ACTIVE, INACTIVE, ARCHIVED) | L31 |
| `DataSource` | dataclass | L171 |
| `Dataset` | dataclass | L186 |
| `DataField` | dataclass (classification, classification_policy_version) | L198 |
| `DataProfile` | dataclass | L312 |
| `ProfileComparison` | dataclass | L328 |
| `ConnectionTestResult` | dataclass | L342 |
| `MetadataDiscoveryResult` | dataclass | L249 |
| `ProfileAnalysisPolicy` | dataclass | L276 |
| `ProfileOptions` | dataclass | L263 |

### 2.2 `rules/models.py`
| Class | Type | Line ref |
|-------|------|----------|
| `RuleType` | Enum(REQUIRED, UNIQUE, RANGE, REGEX, FRESHNESS, REFERENTIAL_INTEGRITY, CROSS_TABLE_CONSISTENCY, CUSTOM_SQL) | L19 |
| `RuleStatus` | Enum(DRAFT, ACTIVE, PASSIVE, REVIEW_REQUIRED, ARCHIVED) | L45 |
| `QualityDimension` | Enum(COMPLETENESS, ACCURACY, VALIDITY, CONSISTENCY, UNIQUENESS, TIMELINESS, INTEGRITY) | L53 |
| `RuleCriticality` | Enum(LOW, MEDIUM, HIGH, CRITICAL) | L63 |
| `RuleApprovalStatus` | Enum(PENDING, APPROVED, REJECTED, WITHDRAWN, EXPIRED) | L75 |
| `QualityRule` | dataclass | L118 |
| `RuleVersion` | dataclass | L130 |
| `RuleTestResult` | dataclass | L163 |
| `RuleApprovalRequest` | dataclass | L102 |
| `RuleApprovalPolicy` | dataclass | L84 |

### 2.3 `issues/models.py`
| Class | Type | Line ref |
|-------|------|----------|
| `IssueStatus` | Enum(NEW, ASSIGNED, INVESTIGATING, WAITING_FOR_RESOLUTION, RESOLVED, VERIFIED, CLOSED, CANCELLED) | L49 |
| `IssuePriority` | Enum(LOW, MEDIUM, HIGH, CRITICAL) | L42 |
| `DataQualityIssue` | dataclass | L162 |
| `IssueResolutionDraft` | dataclass | L97 |
| `IssueVerificationRecord` | dataclass | L138 |
| `IssueRelationship` | dataclass | L153 |
| `InvestigationEvidence` | (imported from investigation.py) | — |

### 2.4 `executions/models.py`
| Class | Type | Line ref |
|-------|------|----------|
| `ExecutionStatus` | Enum(QUEUED, RUNNING, CANCEL_REQUESTED, SUCCESS, PARTIAL, TECHNICAL_ERROR, TIMEOUT, CANCELLED) | L27 |
| `ExecutionMode` | Enum(OFFICIAL, SHADOW) | L22 |
| `RuleExecution` | dataclass | L105 |
| `RuleExecutionResult` | dataclass | L152 |
| `ExecutionAttempt` | dataclass | L192 |
| `RetryPolicy` | dataclass | L62 |
| `ConcurrencyPolicy` | dataclass | L68 |

### 2.5 `scoring/models.py`
| Class | Type | Line ref |
|-------|------|----------|
| `ScoreStatus` | Enum | L31 |
| `ScoreLevel` | Enum | L40 |
| `QualityScore` | dataclass | L123 |
| `ScoringConfiguration` | dataclass | L77 |
| `ThresholdSet` | dataclass | L66 |

### 2.6 `jobs/models.py`
| Class | Type | Line ref |
|-------|------|----------|
| `JobStatus` | Enum | L20 |
| `BackgroundJob` | dataclass | L98 |
| `DeadLetterRecord` | dataclass | L85 |
| `JobLeasePolicy` | dataclass | L49 |
| `JobRetryPolicy` | dataclass | L60 |

### 2.7 `audit/models.py`
| Class | Type | Line ref |
|-------|------|----------|
| `AuditEvent` | dataclass | L115 |
| `PreparedAuditEvent` | dataclass | L81 |
| `AuditQuery` | dataclass | L168 |
| `AuditQueryPage` | dataclass | L184 |
| `AuditRedactionPolicy` | dataclass | L46 |

### 2.8 `identity/models.py`
| Class | Type | Line ref |
|-------|------|----------|
| `ActorType` | Enum | L10 |
| `ActorContext` | dataclass (actor_id, roles, permitted_source_ids, permitted_dataset_ids, can_view_enterprise, privileged) | L20 |

### 2.9 `dashboard/models.py`
| Class | Type | Line ref |
|-------|------|----------|
| `DashboardOverview` | dataclass | L191 |
| `DashboardScoreTrend` | dataclass | L139 |
| `DashboardFilterParams` | dataclass | L42 |
| `DashboardOperationalIndicators` | dataclass | L184 |
| `DashboardMeasurementQualificationIndicator` | dataclass | L159 |

### 2.10 `reporting/models.py`
| Class | Type | Line ref |
|-------|------|----------|
| `ReportType` | Enum | L13 |
| `ReportStatus` | Enum | L23 |
| `ReportFormat` | Enum | L31 |
| `Report` | dataclass | L38 |
| `ReportPreview` | dataclass | L135 |
| `ReportSummaryRow` | dataclass | L119 |

### 2.11 Other domain models (no PostgreSQL migration found)

| Module | Classes | Migration? |
|--------|---------|------------|
| `notifications/models.py` | `NotificationEvent`, `Notification`, `NotificationAccessPolicy` | **No** |
| `retention/models.py` | `RetentionPolicy`, `LegalHold`, `DisposalJob`, `ArchiveRecallDecision` | **No** |
| `lineage/events.py` | `LineageEvent`, `ColumnLineageEdge` | **No** |
| `lineage/governance.py` | `DataAssetGovernanceProfile`, `GovernanceRoutingPolicy` | **No** |
| `servicenow/models.py` | `ServiceNowTicketCommand`, `ServiceNowRetryJob` | **No** |
| `synthetic_data/models.py` | `SyntheticGenerationRun`, `SyntheticGroundTruth`, `SyntheticValidationResult` | **No** |
| `incident_response/models.py` | `SecurityIncident`, `PersonalDataBreachSuspicion` | **No** |
| `data_protection/inventory.py` | `DataProcessingInventory`, `InventoryCoverageReport` | **No** |

## 3. Service Layer

| Module | Service class | File | Key operations |
|--------|--------------|------|----------------|
| `dashboard/service.py` | `DashboardQueryService` | dashboard/service.py | `get_overview()` |
| `data_sources/repository.py` | `DataSourceQueryService` | data_sources/repository.py | `list_for_actor()` |
| `data_sources/postgresql_repository.py` | PostgreSQL impl | data_sources/postgresql_repository.py | DB queries |
| `rules/service.py` | `RuleQueryService` | rules/service.py | `list_for_actor()` |
| `rules/postgresql_repository.py` | PostgreSQL impl | rules/postgresql_repository.py | DB queries |
| `executions/service.py` | `ExecutionQueryService` | executions/service.py | `list_for_actor()` |
| `executions/postgresql_repository.py` | PostgreSQL impl | executions/postgresql_repository.py | DB queries |
| `issues/service.py` | `IssueQueryService` | issues/service.py | `list_for_actor()` |
| `issues/investigation.py` | Investigation evidence | issues/investigation.py | `get_investigation_evidence()` |
| `issues/postgresql_repository.py` | PostgreSQL impl | issues/postgresql_repository.py | DB queries |
| `scoring/service.py` | Score computation | scoring/service.py | score calculation |
| `scoring/contributions.py` | Contribution graphs | scoring/contributions.py | contribution computation |
| `audit/service.py` | `AuditQueryService` | audit/service.py | `query()` |
| `audit/outbox.py` | Audit outbox | audit/outbox.py | event publishing |
| `audit/postgresql_outbox.py` | PostgreSQL outbox | audit/postgresql_outbox.py | DB persistence |
| `reporting/service.py` | `ReportService` | reporting/service.py | request/list/download |
| `reporting/scheduling.py` | `ReportScheduleService` | reporting/scheduling.py | schedule CRUD/trigger |
| `reporting/worker.py` | Report worker | reporting/worker.py | async generation |
| `notifications/service.py` | Notification dispatch | notifications/service.py | event → channel |
| `notifications/channel_adapters.py` | Channel adapters | notifications/channel_adapters.py | email/webhook/SMS |
| `jobs/worker.py` | `PersistentJobWorker` | jobs/worker.py | claim/execute/heartbeat |
| `jobs/handlers.py` | Job handlers | jobs/handlers.py | type → handler dispatch |
| `jobs/lifecycle.py` | Job lifecycle | jobs/lifecycle.py | completion/dead-letter |
| `identity/service.py` | `SessionService` | identity/service.py | validate/logout/CSRF |
| `identity/sessions.py` | Session store | identity/sessions.py | session persistence |
| `identity/ldap.py` | LDAP adapter | identity/ldap.py | directory auth |
| `servicenow/service.py` | ServiceNow integration | servicenow/service.py | ticket create/update |
| `retention/service.py` | Retention policy eval | retention/service.py | evaluate/apply |
| `retention/disposal_service.py` | Disposal jobs | retention/disposal_service.py | schedule/execute |
| `retention/archive_recall_service.py` | Archive recall | retention/archive_recall_service.py | request/decide |
| `synthetic_data/service.py` | Synthetic generation | synthetic_data/service.py | run/validate |
| `incident_response/service.py` | Incident response | incident_response/service.py | incident/breach workflow |
| `lineage/postgresql_lineage.py` | Lineage storage | lineage/postgresql_lineage.py | snapshot store |
| `data_sources/profiling.py` | Profiling engine | data_sources/profiling.py | profile computation |
| `executions/strategy_engine.py` | Strategy engine | executions/strategy_engine.py | rule execution strategy |
| `executions/scheduling.py` | Schedule engine | executions/scheduling.py | cron/schedule trigger |

## 4. Persistence Layer

| Repository | Backend | File |
|-----------|---------|------|
| `data_sources/postgresql_repository.py` | PostgreSQL | `data_sources/postgresql_repository.py` |
| `data_sources/postgresql_driver.py` | Direct driver | `data_sources/postgresql_driver.py` |
| `rules/postgresql_repository.py` | PostgreSQL | `rules/postgresql_repository.py` |
| `executions/postgresql_repository.py` | PostgreSQL | `executions/postgresql_repository.py` |
| `executions/postgresql_scheduling.py` | PostgreSQL | `executions/postgresql_scheduling.py` |
| `executions/postgresql_source_usage.py` | PostgreSQL | `executions/postgresql_source_usage.py` |
| `issues/postgresql_repository.py` | PostgreSQL | `issues/postgresql_repository.py` |
| `jobs/postgresql_repository.py` | PostgreSQL | `jobs/postgresql_repository.py` |
| `scoring/postgresql_contributions.py` | PostgreSQL | `scoring/postgresql_contributions.py` |
| `audit/postgresql_outbox.py` | PostgreSQL | `audit/postgresql_outbox.py` |
| `lineage/postgresql_lineage.py` | PostgreSQL | `lineage/postgresql_lineage.py` |
| `synthetic_data/postgresql_dataset.py` | PostgreSQL | `synthetic_data/postgresql_dataset.py` |
| `notifications/repository.py` | In-memory/Protocol | `notifications/repository.py` |
| `reporting/repository.py` | In-memory/Protocol | `reporting/repository.py` |
| `retention/repository.py` | In-memory/Protocol | `retention/repository.py` |
| `servicenow/repository.py` | In-memory/Protocol | `servicenow/repository.py` |
| `incident_response/repository.py` | In-memory/Protocol | `incident_response/repository.py` |
| `persistence/database.py` | SQLAlchemy Session | `persistence/database.py` |

## 5. App Factory / Composition Root

**File**: `src/veri_kalitesi/api/app.py` — `create_dashboard_api()` (L376)

- Accepts 26+ optional service dependencies via keyword args
- All service params default to `None` → fail-closed
- Supports two auth modes: `BffSessionBoundary` (production) or `DevelopmentActorContextResolver` (dev)
- CORS middleware with explicit origin allowlist
- Correlation ID middleware
- CSRF protection middleware for state-changing requests
- 30+ exception handlers mapped to HTTP status codes

**Dev entry**: `run_dev.py` → `create_development_app()` → connects to `postgresql+psycopg://dqtest:dqtest@127.0.0.1:55432/data_quality`
