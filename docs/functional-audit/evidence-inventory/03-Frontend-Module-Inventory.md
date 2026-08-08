# Frontend Module Inventory — Read-Only Evidence

> Source: `frontend/src/` — only application code, not node_modules.

## 1. Routes (App.tsx L775-L786)

| Route | Component | Lazy loaded | Feature area |
|-------|-----------|-------------|--------------|
| `/` | `DashboardPage` | Yes | Dashboard overview |
| `/data-sources` | `DataSourcesPage` | Yes | Source management |
| `/profiling` | `ProfilingPage` | Yes | Profile snapshots & drift |
| `/rules` | `RulesPage` | Yes | Quality rules lifecycle |
| `/executions` | `ExecutionsPage` | Yes | Execution history |
| `/issues` | `IssuesPage` | Yes | Issue lifecycle |
| `/investigation` | `InvestigationPage` | Yes | Issue investigation evidence |
| `/reports` | `ReportsPage` | Yes | Reporting & downloads |
| `/audit` | `AuditPage` | Yes | Audit event log |
| `/unauthorized` | `RouteBoundary` | No | Error page |
| `*` | `RouteBoundary` | No | 404 page |

## 2. Frontend Modules

| Module | Page component | API client | Model/mapper | Test | Stories |
|--------|---------------|------------|--------------|------|---------|
| `dashboard/` | `DashboardPage.tsx` | `api.ts` | `model.ts` | Yes (3 files) | Yes |
| `dataSources/` | `DataSourcesPage.tsx` | `api.ts` | `model.ts` | Yes (3 files) | Yes |
| `profiling/` | `ProfilingPage.tsx` | `api.ts` | `model.ts` | Yes (1 file) | **No** |
| `rules/` | `RulesPage.tsx` | `api.ts` | `model.ts` | Yes (3 files) | Yes |
| `executions/` | `ExecutionsPage.tsx` | `api.ts` | `model.ts` | Yes (3 files) | Yes |
| `issues/` | `IssuesPage.tsx` + `InvestigationPage.tsx` | `api.ts` | `model.ts` | Yes (5 files) | Yes |
| `reports/` | `ReportsPage.tsx` | `api.ts` | `model.ts` | Yes (3 files) | Yes |
| `audit/` | `AuditPage.tsx` | `api.ts` | `model.ts` | Yes (3 files) | Yes |

## 3. Shared Components

| File | Component | Purpose |
|------|-----------|---------|
| `components/AppShell.tsx` | Navigation shell | Sidebar, header, layout |
| `components/KpiCard.tsx` | KPI display | Metric card |
| `components/StatusBadge.tsx` | Status indicator | Colored badge |
| `components/AlertFeed.tsx` | Alert notifications | Toast/alert list |
| `components/TrendPanel.tsx` | Trend visualization | Score trend chart |
| `components/QualityDimensionMatrix.tsx` | Dimension view | Quality dimension grid |
| `components/ScoreContributionPanel.tsx` | Score breakdown | Contribution graph |
| `components/FieldScoreComparison.tsx` | Field comparison | Score comparison |
| `components/DashboardComparison.tsx` | Dashboard compare | Period comparison |
| `components/exportTable.ts` | Export utility | CSV/table export |

## 4. Development/Auth Layer

| File | Purpose |
|------|---------|
| `development/DevelopmentLoginPage.tsx` | Dev login form + user switcher |
| `development/UserContext.tsx` | React context for dev user |
| `development/api.ts` | Dev user API calls |
| `development/fetch.ts` | Custom fetch with dev headers |

**Critical**: Authentication in current implementation uses `DevelopmentLoginPage` with `X-Development-User-Id` header. Production BFF session is wired but only activates when `BffSessionBoundary` is configured.

## 5. Frontend API Calls Mapped to Backend

| Frontend API function | Backend endpoint | File:line ref |
|----------------------|------------------|---------------|
| `fetchDashboardSummary()` | `GET /api/v1/dashboard/summary` | `dashboard/api.ts` |
| `fetchDataSources()` | `GET /api/v1/data-sources` | `dataSources/api.ts` |
| `createDataSource()` | `POST /api/v1/data-sources` | `dataSources/api.ts` |
| `testDataSource()` | `POST /api/v1/data-sources/{id}/test` | `dataSources/api.ts` |
| `activateDataSource()` | `POST /api/v1/data-sources/{id}/activation` | `dataSources/api.ts` |
| `passivateDataSource()` | `POST /api/v1/data-sources/{id}/passivation` | `dataSources/api.ts` |
| `fetchProfileSnapshots()` | `GET /api/v1/profile-snapshots` | `profiling/api.ts` |
| `fetchProfileSnapshotDetail()` | `GET /api/v1/profile-snapshots/{id}` | `profiling/api.ts` |
| `fetchDriftJudgment()` | `GET /api/v1/profile-snapshots/{id}/drift` | `profiling/api.ts` |
| `fetchRules()` | `GET /api/v1/rules` | `rules/api.ts` |
| `createRule()` | `POST /api/v1/rules` | `rules/api.ts` |
| `createRuleVersion()` | `POST /api/v1/rules/{id}/versions` | `rules/api.ts` |
| `testRule()` | `POST /api/v1/rules/{id}/test` | `rules/api.ts` |
| `activateRule()` | `POST /api/v1/rules/{id}/activation` | `rules/api.ts` |
| `requestRuleApproval()` | `POST /api/v1/rules/{id}/approval` | `rules/api.ts` |
| `decideRuleApproval()` | `POST /api/v1/rules/approval/{id}/decide` | `rules/api.ts` |
| `withdrawRuleApproval()` | `POST /api/v1/rules/approval/{id}/withdraw` | `rules/api.ts` |
| `passivateRule()` | `POST /api/v1/rules/{id}/passivation` | `rules/api.ts` |
| `fetchExecutions()` | `GET /api/v1/executions` | `executions/api.ts` |
| `fetchIssues()` | `GET /api/v1/issues` | `issues/api.ts` |
| `startIssueInvestigation()` | `POST /api/v1/issues/{id}/investigation` | `issues/api.ts` |
| `reassignIssue()` | `POST /api/v1/issues/{id}/assignment` | `issues/api.ts` |
| `resolveIssue()` | `POST /api/v1/issues/{id}/resolution` | `issues/api.ts` |
| `verifyIssue()` | `POST /api/v1/issues/{id}/verification` | `issues/api.ts` |
| `closeIssue()` | `POST /api/v1/issues/{id}/closure` | `issues/api.ts` |
| `fetchIssueAssignmentOptions()` | `GET /api/v1/issues/{id}/assignment-options` | `issues/api.ts` |
| `fetchReportSummary()` | `GET /api/v1/reports/summary` | `reports/api.ts` |
| `createReport()` | `POST /api/v1/reports/` | `reports/api.ts` |
| `listReports()` | `GET /api/v1/reports/` | `reports/api.ts` |
| `triggerDownload()` | `GET /api/v1/reports/{id}/download` | `reports/api.ts` |
| `fetchAuditEvents()` | `GET /api/v1/audit/events` | `audit/api.ts` |

## 6. Missing Frontend Pages

| Feature area | Expected route | Status |
|-------------|---------------|--------|
| Scores/Scoring | `/scores` | **MISSING** — no page, no API client |
| Schedules (rule) | `/schedules` | **MISSING** — no page |
| Notifications | `/notifications` | **MISSING** — no page |
| Lineage & Impact | `/lineage` | **MISSING** — no page |
| Synthetic Data | `/synthetic-data` | **MISSING** — no page |
| Retention/Disposal | `/retention` | **MISSING** — no page |
| Operations | `/operations` | **MISSING** — no page |
| Administration | `/admin` | **MISSING** — no page |
| Data Catalog | `/catalog` | **MISSING** — no page |
| Data Contracts | `/data-contracts` | **MISSING** — no page |
| Remediation | `/remediation` | **MISSING** — no page |
| Report Schedules | `/report-schedules` | **MISSING** — API exists, no page |
| Execution Start | (dialog in executions) | **PARTIAL** — API exists, no start button in UI |
| Execution Cancel | (dialog in executions) | **PARTIAL** — API exists, no cancel button in UI |

## 7. E2E Tests (Playwright)

| File | Scope |
|------|-------|
| `e2e/dashboard.spec.ts` | Dashboard page |
| `e2e/data-sources.spec.ts` | Data sources page |
| `e2e/rules.spec.ts` | Rules page |
| `e2e/executions.spec.ts` | Executions page |
| `e2e/issues.spec.ts` | Issues page |
| `e2e/reports.spec.ts` | Reports page |
| `e2e/audit.spec.ts` | Audit page |
