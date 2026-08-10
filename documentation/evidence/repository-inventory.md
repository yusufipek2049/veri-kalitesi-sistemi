# Repository Inventory — Evidence-Based Discovery

**Commit:** `debd90359ba2c978a33a877c54f79c64c70e65b7`
**Branch:** `agent/36h1-persistent-job-core`
**Working tree:** clean
**Date of analysis:** 2026-08-08

> This inventory was produced by tracing executable sources only.
> No documentation files (`docs/**`, `archive/**`, `README.md`, `NEXT_STEP.md`, etc.) were used as evidence.

---

## 1. Runtime Processes

| Process | Entrypoint | Bind | Compose Service |
|---------|-----------|------|-----------------|
| **API** | `Dockerfile CMD` → `uvicorn scripts.run_dev:app` → `create_development_app()` → `create_application()` → `create_dashboard_api()` → `FastAPI` | `0.0.0.0:8000` | `api` |
| **Worker** | `compose command: dq-worker` → `veri_kalitesi.jobs.entrypoint:main` → `create_production_worker()` → `PersistentJobWorker.run_forever()` | — | `worker` |
| **Migrate** | `compose command: alembic upgrade head` → `alembic/env.py` → `run_migrations_online()` | — | `migrate` |
| **Frontend** | `node:22.17-alpine` → `npm run dev` → Vite dev server | `0.0.0.0:5173` | `frontend` |

**Startup order:** `postgres` → `migrate` (depends_on healthy) → `api` + `worker` (depends_on migrate completed) → `frontend` (depends_on api started).

---

## 2. Backend Modules (22 modules under `src/veri_kalitesi/`)

| Module | Files | Role |
|--------|-------|------|
| `api/` | 36 | HTTP composition, routers, identity, BFF, settings |
| `audit/` | 11 | Transactional audit outbox, repository, redaction |
| `dashboard/` | 5 | Dashboard query service (UNWIRED in persistent composition) |
| `data_protection/` | 4 | Data protection utilities |
| `data_sources/` | 15 | Data source domain, connectors, PostgreSQL repo, secrets, catalog |
| `enterprise_lab/` | 4 | Enterprise lab adapters |
| `environment_security/` | 5 | Environment security checks |
| `executions/` | 14 | Rule execution domain, strategy engine, PostgreSQL repo |
| `identity/` | 7 | Actor context, authorization policies |
| `incident_response/` | 5 | Incident response module |
| `issues/` | 11 | Issue domain, assignment, investigation, resolution, verification |
| `jobs/` | 13 | Background job queue, worker lifecycle, handlers |
| `lineage/` | 7 | Lineage evidence, governance projection, impact analysis |
| `notifications/` | 12 | Notification channels, delivery, batch staging |
| `persistence/` | 2 | Database settings, session factory (PostgreSQL-only) |
| `reporting/` | 9 | Report generation, scheduling, export, worker |
| `retention/` | 9 | Data retention, archival, disposal, legal hold |
| `rules/` | 9 | Quality rules domain, approval, templates |
| `scoring/` | 13 | Score computation, contribution graphs, publication, trends |
| `secure_sdlc/` | 13 | SAST, SBOM, pentest, evidence gates, vulnerability tracking |
| `servicenow/` | 5 | ServiceNow integration |
| `synthetic_data/` | 12 | Synthetic data generation, oracle, temporal, PostgreSQL dataset |

---

## 3. API Routes (67 registered endpoints)

### 3.1 REACHABLE Routes (backed by wired services)

| Method | Path | Tag | Service |
|--------|------|-----|---------|
| GET | `/api/v1/data-sources` | data-sources | DataSourceQueryService |
| POST | `/api/v1/data-sources` | data-sources | DataSourceCommandAdapter |
| GET | `/api/v1/data-sources/{id}/test` | data-sources | DataSourceCommandAdapter |
| POST | `/api/v1/data-sources/{id}/activation` | data-sources | DataSourceCommandAdapter |
| POST | `/api/v1/data-source-activation-requests/{id}/decision` | data-sources | DataSourceCommandAdapter |
| POST | `/api/v1/data-sources/{id}/passivation` | data-sources | DataSourceCommandAdapter |
| GET | `/api/v1/rules` | rules | RuleQueryService |
| POST | `/api/v1/rules` | rules | RuleCommandAdapter (Phase B) |
| POST | `/api/v1/rules/{id}/versions` | rules | RuleQueryService |
| POST | `/api/v1/rules/{id}/test` | rules | RuleCommandAdapter (Phase B) |
| POST | `/api/v1/rules/{id}/activation` | rules | RuleCommandAdapter (Phase B) |
| POST | `/api/v1/rules/{id}/approval` | rules | RuleCommandAdapter (Phase B) |
| POST | `/api/v1/rules/approval/{id}/decide` | rules | RuleCommandAdapter (Phase B) |
| POST | `/api/v1/rules/approval/{id}/withdraw` | rules | RuleCommandAdapter (Phase B) |
| POST | `/api/v1/rules/{id}/passivation` | rules | RuleCommandAdapter (Phase B) |
| GET | `/api/v1/issues` | issues | IssueQueryService |
| POST | `/api/v1/issues` | issues | IssueService |
| POST | `/api/v1/issues/{id}/investigation` | issues | IssueService |
| GET | `/api/v1/issues/{id}/investigation/evidence` | issues | IssueService |
| GET | `/api/v1/issues/{id}/assignment-options` | issues | IssueService (Phase B) |
| POST | `/api/v1/issues/{id}/assignment` | issues | IssueService (Phase B) |
| POST | `/api/v1/issues/{id}/resolution` | issues | IssueService (Phase B) |
| POST | `/api/v1/issues/{id}/verification` | issues | IssueService (Phase B) |
| POST | `/api/v1/issues/{id}/closure` | issues | IssueService |
| GET | `/api/v1/executions` | executions | ExecutionQueryService |
| GET | `/api/v1/executions/{id}` | executions | ExecutionQueryService |
| POST | `/api/v1/executions` | executions | PostgreSQLExecutionStartService |
| POST | `/api/v1/executions/{id}/cancel` | executions | PostgreSQLExecutionCancelService |
| GET | `/api/v1/scores` | scores | ScoreQueryService |
| GET | `/api/v1/scores/rules/{id}` | scores | ScoreQueryService |
| GET | `/api/v1/scores/comparison` | scores | ScoreQueryService |
| GET | `/api/v1/scores/{id}` | scores | ScoreQueryService |
| GET | `/api/v1/audit/events` | audit | AuditQueryService |
| GET | `/api/v1/notifications/inbox` | notifications | NotificationQueryService |
| GET | `/api/v1/notifications/inbox/unread-count` | notifications | NotificationQueryService |
| GET | `/api/v1/notifications/deliveries/{id}` | notifications | NotificationQueryService |
| POST | `/api/v1/notifications/deliveries/{id}/read` | notifications | NotificationDeliveryService |
| GET | `/api/v1/notifications/events/{id}` | notifications | NotificationQueryService |
| GET | `/api/v1/notifications/subscriptions` | notifications | NotificationQueryService |
| GET | `/api/v1/notifications/channels` | notifications | NotificationQueryService |
| POST | `/api/v1/data-sources/{id}/metadata-discoveries` | catalog | PostgreSQLMetadataCommandService |
| PUT | `/api/v1/data-sources/{id}/discovery-scope` | catalog | PostgreSQLMetadataCommandService |
| GET | `/api/v1/data-sources/{id}/discovery-scope` | catalog | PostgreSQLMetadataCommandService |
| GET | `/api/v1/metadata-discoveries/{id}` | catalog | CatalogQueryService |
| GET | `/api/v1/metadata-discoveries/{id}/diff` | catalog | CatalogQueryService |
| POST | `/api/v1/metadata-diffs/{id}/application` | catalog | PostgreSQLMetadataCommandService |
| GET | `/api/v1/datasets` | catalog | CatalogQueryService |
| GET | `/api/v1/datasets/{id}` | catalog | CatalogQueryService |
| GET | `/api/v1/datasets/{id}/fields` | catalog | CatalogQueryService |
| GET | `/api/v1/fields/{id}` | catalog | CatalogQueryService |
| GET | `/api/v1/development/users` | development | DevelopmentUserRegistry (DEV_ONLY) |
| GET | `/api/v1/openapi.json` | openapi | FastAPI built-in |

### 3.2 UNWIRED Routes (registered but services are None → 503 at runtime)

| Method | Path | Tag | Missing Service |
|--------|------|-----|-----------------|
| GET | `/api/v1/dashboard/summary` | dashboard | UnavailableDashboardService → raises DashboardQueryError |
| GET | `/api/v1/profile-comparisons` | data-sources | ProfileComparisonService not passed |
| GET | `/api/v1/profile-snapshots` | data-sources | ProfileSnapshotQueryService not passed |
| GET | `/api/v1/profile-snapshots/{id}` | data-sources | ProfileSnapshotQueryService not passed |
| GET | `/api/v1/profile-snapshots/{id}/drift` | data-sources | ProfileSnapshotQueryService not passed |
| POST | `/api/v1/scores/{id}/reproduction` | scores | score_publication_service=None |
| GET | `/api/v1/reports/summary` | reports | ReportPreviewService=None |
| POST | `/api/v1/reports/` | reports | ReportService=None |
| GET | `/api/v1/reports/` | reports | ReportService=None |
| GET | `/api/v1/reports/{id}` | reports | ReportService=None |
| GET | `/api/v1/reports/{id}/download` | reports | ReportService=None |
| GET | `/api/v1/report-schedules` | reports | ReportScheduleService=None |
| POST | `/api/v1/report-schedules` | reports | ReportScheduleService=None |
| DELETE | `/api/v1/report-schedules/{id}` | reports | ReportScheduleService=None |
| POST | `/api/v1/report-schedules/trigger-due` | reports | ReportScheduleService=None |
| GET | `/api/v1/lineage/snapshots/{id}` | lineage | PostgreSQLLineageEvidenceRepository=None |
| GET | `/api/v1/governance/{asset_ref}/projection` | lineage | PostgreSQLGovernanceProfileReader=None |
| POST | `/api/v1/session/logout` | session | BffSessionBoundary (dev uses resolver, not BFF) |

---

## 4. Worker Job Types

| Job Type | Handler | Wired in Default Worker? | Notes |
|----------|---------|--------------------------|-------|
| `EXECUTION` | `ExecutionJobHandler` | **Yes** | Always registered in composition.py |
| `METADATA_DISCOVERY` | `MetadataDiscoveryJobHandler` | **Yes** | Wired in production.py |
| `REPORT` | `ReportJobHandler` | **No** | report_worker=None in production.py |
| `SCORE_PUBLICATION` | `ScorePublicationJobHandler` | **No** | Requires providers!=None; entrypoint omits |
| `NOTIFICATION_DELIVERY` | `NotificationDeliveryJobHandler` | **No** | Requires providers!=None; entrypoint omits |

---

## 5. Frontend Routes (20 client routes in `App.tsx`)

| Path | Component | Lazy? |
|------|-----------|-------|
| `/` | DashboardRoute | No |
| `/data-sources` | DataSourcesRoute | No |
| `/catalog` | CatalogRoute | No (uses lazy pages) |
| `/catalog/datasets/:datasetId` | DatasetDetailRoute | No (uses lazy pages) |
| `/catalog/fields/:fieldId` | FieldDetailRoute | No (uses lazy pages) |
| `/profiling` | ProfilingRoute | No |
| `/rules` | RulesRoute | No |
| `/executions` | ExecutionsRoute | No |
| `/scores` | ScoresPage | Yes |
| `/scores/:scoreId` | ScoreDetailPage | Yes |
| `/scores/comparison` | ScoreComparisonPage | Yes |
| `/issues` | IssuesRoute | No |
| `/investigation` | InvestigationRoute | No (uses lazy page) |
| `/unauthorized` | RouteBoundary | No |
| `/reports` | ReportsRoute | No |
| `/audit` | AuditRoute | No |
| `/notifications` | NotificationsPage | Yes |
| `/notifications/preferences` | NotificationPreferencesPage | Yes |
| `/notifications/channels` | NotificationChannelsPage | Yes |
| `/notifications/deliveries` | NotificationDeliveriesPage | Yes |

**Frontend API client modules:** 12 `api.ts` files (audit, catalog, dashboard, dataSources, development, executions, issues, notifications, profiling, reports, rules, scores).

**Storybook stories:** 8 (audit, dashboard, data-sources, executions, issues, reports, rules, StatusBadge).

**E2E specs:** 8 (audit, dashboard, data-sources, data-sources-live, executions, issues, reports, rules).

---

## 6. Persistence & Migrations

- **Database:** PostgreSQL only (`postgresql+psycopg` driver enforced)
- **ORM:** SQLAlchemy 2.0.51
- **Migration tool:** Alembic 1.18.4
- **Default schema:** `dq`
- **Default database name:** `data_quality` (enforced)
- **Migration head:** `20260806_20`
- **Total migrations:** 20 (linear chain from `20260723_01` to `20260806_20`)
- **Required tables validated at startup:** 33 tables

### Migration Chain

| # | Revision | Name | Down Revision |
|---|----------|------|---------------|
| 1 | 20260723_01 | issue_baseline | (root) |
| 2 | 20260723_02 | rule_baseline | 20260723_01 |
| 3 | 20260724_03 | data_source_baseline | 20260723_02 |
| 4 | 20260724_04 | execution_baseline | 20260724_03 |
| 5 | 20260724_05 | scheduling_and_policy_baseline | 20260724_04 |
| 6 | 20260724_06 | reporting_baseline | 20260724_05 |
| 7 | 20260724_07 | report_schedules | 20260724_06 |
| 8 | 20260728_08 | job_queue | 20260724_07 |
| 9 | 20260729_09 | job_lifecycle | 20260728_08 |
| 10 | 20260729_10 | source_policy_deadlines | 20260729_09 |
| 11 | 20260729_11 | profile_comparisons | 20260729_10 |
| 12 | 20260730_12 | rule_ir_shadow_evidence | 20260729_11 |
| 13 | 20260730_13 | score_contribution_graphs | 20260730_12 |
| 14 | 20260730_14 | lineage_governance_evidence | 20260730_13 |
| 15 | 20260805_15 | data_source_command_slice | 20260730_14 |
| 16 | 20260805_16 | execution_worker_runtime | 20260805_15 |
| 17 | 20260805_17 | catalog_metadata_discovery | 20260805_16 |
| 18 | 20260806_18 | issue_generation | 20260805_17 |
| 19 | 20260806_19 | score_publication | 20260806_18 |
| 20 | 20260806_20 | notification_delivery | 20260806_19 |

---

## 7. Environment Variables

### Database
| Variable | Required | Default | Source |
|----------|----------|---------|--------|
| `DATA_QUALITY_DATABASE_URL` | Yes | — | `persistence/database.py` |
| `DATA_QUALITY_DATABASE_SCHEMA` | No | `dq` | `persistence/database.py` |

### API Settings
| Variable | Required | Default | Source |
|----------|----------|---------|--------|
| `DATA_QUALITY_RUNTIME_ENVIRONMENT` | No | `production` | `api/settings.py` |
| `DATA_QUALITY_ALLOWED_ORIGINS` | Yes (effective) | — | `api/settings.py` |
| `DATA_QUALITY_AUDIT_POLICY_VERSION` | No | `AUDIT_OUTBOX_V1` | `api/settings.py` |
| `DATA_QUALITY_DATA_SOURCE_POLICY_VERSION` | No | `DATA_SOURCE_COMMAND_POLICY_V1` | `api/settings.py` |
| `DATA_QUALITY_RULE_POLICY_VERSION` | No | `RULE_APPROVAL_POLICY_V1` | `api/settings.py` |
| `DATA_QUALITY_ISSUE_POLICY_VERSION` | No | `ISSUE_ACCESS_POLICY_V1` | `api/settings.py` |
| `DATA_QUALITY_ACTOR_POLICY_VERSION` | No | `DASHBOARD_POLICY_V1` | `api/settings.py` |
| `DATA_QUALITY_EXECUTION_COMMAND_POLICY_VERSION` | No | `EXECUTION_COMMAND_POLICY_V1` | `api/settings.py` |
| `DATA_QUALITY_SCORING_CONFIGURATION_VERSION` | No | `DEFAULT_SCORING_V1` | `api/settings.py` |
| `DATA_QUALITY_LOCAL_SECRET_DIR` | No | — | `api/settings.py` (dev-only) |

### Worker Settings
| Variable | Required | Default | Source |
|----------|----------|---------|--------|
| `DQ_WORKER_ID` | No | `worker-01` | `jobs/settings.py` |
| `DQ_WORKER_HOSTNAME` | No | `localhost` | `jobs/settings.py` |
| `DQ_WORKER_CAPACITY` | No | `1` | `jobs/settings.py` |
| `DQ_WORKER_LEASE_SECONDS` | No | `300` | `jobs/settings.py` |
| `DQ_WORKER_IDLE_WAIT_SECONDS` | No | `0.5` | `jobs/settings.py` |
| `DQ_WORKER_SHUTDOWN_GRACE_SECONDS` | No | `5.0` | `jobs/settings.py` |

### Frontend
| Variable | Required | Default | Source |
|----------|----------|---------|--------|
| `VITE_API_PROXY_TARGET` | No | `http://api:8000` | `compose.yaml` |

---

## 8. Test & CI Commands

| Command | Purpose | Gate? |
|---------|---------|-------|
| `pytest -q` | All backend tests (unit + integration paths) | **Blocking** |
| `pytest -q tests/integration` | Integration tests (skipped=0 enforced) | **Blocking** |
| `ruff check . --output-format=github` | Lint (E, F rules) | **Blocking** |
| `ruff format --check .` | Format check | **Blocking** |
| `mypy src` | Type checking | **Blocking** |
| `cd frontend && npm test` | Vitest unit tests | **Blocking** |
| `cd frontend && npm run typecheck` | TypeScript type check | **Blocking** |
| `cd frontend && npm run build` | Production build | **Blocking** |
| `cd frontend && npm run test:e2e` | Playwright E2E | Non-blocking |
| `cd frontend && npm run lint` | ESLint | Non-blocking |
| `cd frontend && npm run dead-code` | Knip dead code detection | Non-blocking |

---

## 9. Capability Matrix

| Capability | Status | Evidence |
|------------|--------|----------|
| Dashboard Summary | **UNWIRED** | UnavailableDashboardService in composition; route returns error |
| Data Source Query | **REACHABLE** | GET /api/v1/data-sources → DataSourceQueryService wired |
| Data Source Commands | **REACHABLE** | POST routes → DataSourceCommandAdapter wired |
| Profile Comparison / Snapshot / Drift | **UNWIRED** | Services not passed from composition.py |
| Rules Query | **REACHABLE** | GET /api/v1/rules → RuleQueryService wired |
| Rules Commands | **REACHABLE** | POST routes → RuleCommandAdapter (Phase B; None in dev) |
| Issues Query | **REACHABLE** | GET /api/v1/issues → IssueQueryService wired |
| Issues Create / Investigate / Close | **REACHABLE** | POST routes → IssueService wired |
| Issues Assignment / Resolution / Verification | **REACHABLE** | Phase B providers optional |
| Executions Query | **REACHABLE** | GET /api/v1/executions → ExecutionQueryService wired |
| Executions Start / Cancel | **REACHABLE** | PostgreSQLExecutionStartService/CancelService wired |
| Scores Query (list/detail/history/comparison) | **REACHABLE** | GET routes → ScoreQueryService wired |
| Score Reproduction | **UNWIRED** | score_publication_service=None in composition |
| Reports (all endpoints) | **UNWIRED** | All 9 report routes → services are None → 503 |
| Audit Events Query | **REACHABLE** | GET /api/v1/audit/events → AuditQueryService wired |
| Notifications (inbox/deliveries/channels/subscriptions) | **REACHABLE** | 7 routes → NotificationQueryService/DeliveryService wired |
| Lineage Evidence / Governance Projection | **UNWIRED** | repository/reader are None in composition → 503 |
| Catalog / Metadata Discovery | **REACHABLE** | 10 routes → MetadataCommandService/CatalogQueryService wired |
| Development Users | **DEV_ONLY** | Only in development runtime |
| Worker: EXECUTION | **REACHABLE** | Always registered |
| Worker: METADATA_DISCOVERY | **REACHABLE** | Wired in production.py |
| Worker: REPORT | **UNWIRED** | report_worker not passed |
| Worker: SCORE_PUBLICATION | **UNWIRED** | Requires providers; entrypoint omits |
| Worker: NOTIFICATION_DELIVERY | **UNWIRED** | Requires providers; entrypoint omits |
| Retention / Archival / Disposal / Legal Hold | **TEST_ONLY** | Domain + tests exist; no API routes or handlers |
| Synthetic Data Generation | **TEST_ONLY** | Domain + tests exist; no API routes |
| Secure SDLC (SAST/SBOM/Pentest/Evidence) | **TEST_ONLY** | Module + 7 test files; CLI only |
| ServiceNow Integration | **TEST_ONLY** | Module + test; no API routes |
| Incident Response | **TEST_ONLY** | Module + test; no API routes |
| Enterprise Lab | **TEST_ONLY** | Module + 2 test files; no API routes |

---

## 10. Contradictions

1. **Dashboard capability:** Route registered and frontend has DashboardRoute, but composition uses `UnavailableDashboardService` which raises `DashboardQueryError` on every call.
   - `src/veri_kalitesi/api/composition.py` L156-161
   - `src/veri_kalitesi/api/dashboard_router.py` L124

2. **Rules mutation in development:** Rule mutation POST routes require `RuleCommandAdapter` which is `None` when `phase_b_providers` is absent. Dev composition does not provide `PhaseBProviders`.
   - `src/veri_kalitesi/api/composition.py` L360-376
   - `src/veri_kalitesi/api/development_runtime.py` L15-47

3. **Worker SCORE_PUBLICATION and NOTIFICATION_DELIVERY:** `production.py` wires these handlers only when `providers is not None`, but `entrypoint.py` calls `create_production_worker(settings)` without `providers`. These job types are dead code in the default worker.
   - `src/veri_kalitesi/jobs/entrypoint.py` L19-21
   - `src/veri_kalitesi/jobs/production.py` L62-66, L209-262

4. **Report and Lineage routes always return 503:** Routes are registered in OpenAPI spec but backing services are `None` in persistent composition.
   - `src/veri_kalitesi/api/composition.py` L407-440
   - `src/veri_kalitesi/api/reports_router.py` L60-61
   - `src/veri_kalitesi/api/lineage_router.py` L55-62

---

## 11. Unresolved Questions

1. **Production API composition:** `production.py` requires `BffSessionBoundary` and `PhaseBProviders` which are not instantiated in this repo. They must come from an external deployment package.
2. **Dashboard service:** Always `UnavailableDashboardService` in persistent composition. Is there an alternate composition that provides a real `DashboardQueryService`?
3. **Report and Lineage services:** Full domain logic and tests exist but are never wired. Are they awaiting a future iteration's composition integration?
4. **Worker SCORE_PUBLICATION / NOTIFICATION_DELIVERY:** Is there a separate worker entrypoint that provides the required `providers`?
5. **TEST_ONLY modules:** `retention`, `synthetic_data`, `secure_sdlc`, `servicenow`, `incident_response`, `enterprise_lab` have domain logic and tests but zero runtime wiring. Are these planned for future API exposure?
6. **Packaging:** No `[build-system]` is defined in `pyproject.toml`; CI installs dependencies by parsing the TOML directly. Is this intentional or a packaging gap?

---

## 12. Changed Files

| File | Action |
|------|--------|
| `documentation/evidence/repository-inventory.json` | Created |
| `documentation/evidence/repository-inventory.md` | Created |

No existing files were modified.
