# Implementation Status Matrix — Read-Only Evidence

> Cross-cutting summary: for each functional area, what exists in code vs documentation.
> Status codes: `IMPL`=Implemented, `PART`=Partial, `DOC_ONLY`=Documentation only, `MODEL_ONLY`=Domain model only, `BE_ONLY`=Backend only, `FE_ONLY`=Frontend only, `MISSING`=No code evidence

## Functional Area Status

| # | Functional area | Domain model | DB table | Service | API endpoint | Frontend page | Status |
|---|----------------|-------------|----------|---------|-------------|--------------|--------|
| 1 | **Dashboard & Analytics** | `dashboard/models.py` | `score_contribution_graphs` | `DashboardQueryService` | `GET /api/v1/dashboard/summary` | `DashboardPage` | **IMPL** |
| 2 | **Data Source Onboarding** | `data_sources/models.py` | `data_sources`, `datasets`, `data_fields`, `connection_test_results`, `metadata_discovery_results`, `data_source_connection_revisions`, `data_source_activation_requests` | `DataSourceQueryService`, `DataSourceMutationService` | 6 endpoints | `DataSourcesPage` | **IMPL** |
| 3 | **Data Profiling** | `data_sources/models.py` (DataProfile, ProfileComparison) | `data_profiles`, `profile_comparisons` | `ProfileSnapshotQueryService`, `ProfileComparisonService` | 4 endpoints | `ProfilingPage` | **IMPL** |
| 4 | **Quality Rules Lifecycle** | `rules/models.py` | `quality_rules`, `rule_versions`, `rule_test_results`, `rule_approval_requests` | `RuleQueryService`, `RuleCreatorService`, `RuleMutationService` | 9 endpoints | `RulesPage` | **IMPL** |
| 5 | **Rule Approval (Maker-Checker)** | `rules/models.py` (RuleApprovalRequest, RuleApprovalPolicy) | `rule_approval_requests` | `RuleMutationService` (approve/reject/withdraw) | 3 endpoints | `RulesPage` (inline) | **IMPL** |
| 6 | **Execution & Scheduling** | `executions/models.py` | `rule_executions`, `execution_attempts`, `rule_execution_results`, `schedules`, `source_usage_policies` | `ExecutionQueryService`, `ExecutionStartService`, `ExecutionCancelService` | 3 endpoints | `ExecutionsPage` (list only) | **PART** — no start/cancel UI, no schedule management UI |
| 7 | **Issue Lifecycle** | `issues/models.py` | `data_quality_issues`, `issue_history`, `issue_resolutions`, `issue_verifications`, `issue_relationships` | `IssueQueryService`, investigation/assignment/resolution/verification/closure services | 8 endpoints | `IssuesPage` | **IMPL** |
| 8 | **Investigation Evidence** | `issues/investigation.py` | (reads from execution/results) | `IssueInvestigationEvidenceService` | `GET /issues/{id}/investigation/evidence` | `InvestigationPage` | **IMPL** |
| 9 | **Reporting** | `reporting/models.py` | `reports`, `report_schedules` | `ReportService`, `ReportPreviewService`, `ReportScheduleService` | 9 endpoints | `ReportsPage` (no schedule UI) | **PART** — schedule management has no frontend |
| 10 | **Audit Trail** | `audit/models.py` | `audit_outbox` | `AuditQueryService`, `PostgreSQLTransactionalAudit` | `GET /api/v1/audit/events` | `AuditPage` | **IMPL** |
| 11 | **Scoring & Contributions** | `scoring/models.py` | `score_contribution_graphs` | `ScoringService`, `ContributionService` | **MISSING** | **MISSING** | **BE_ONLY** — no API, no UI |
| 12 | **Notifications** | `notifications/models.py` | **MISSING** | `NotificationService` | **MISSING** | **MISSING** | **MODEL_ONLY** — domain model exists, no persistence, no API, no UI |
| 13 | **Retention & Disposal** | `retention/models.py` | **MISSING** | `RetentionService`, `DisposalService`, `ArchiveRecallService` | **MISSING** | **MISSING** | **MODEL_ONLY** — domain model exists, no persistence, no API, no UI |
| 14 | **Legal Hold** | `retention/models.py` (LegalHold, LegalHoldEvent) | **MISSING** | In retention service | **MISSING** | **MISSING** | **MODEL_ONLY** |
| 15 | **Lineage & Governance** | `lineage/events.py`, `lineage/governance.py` | `lineage_evidence_snapshots` | `PostgreSQLLineageEvidenceRepository`, `GovernanceProfileReader` | 2 endpoints (snapshot, projection) | **MISSING** | **BE_ONLY** — API exists, no UI |
| 16 | **Impact Analysis** | `lineage/impact.py` | **MISSING** | In lineage module | **MISSING** | **MISSING** | **MODEL_ONLY** |
| 17 | **Synthetic Data** | `synthetic_data/models.py` | **MISSING** | `SyntheticDataService` | **MISSING** | **MISSING** | **MODEL_ONLY** — domain model+service, no persistence, no API, no UI |
| 18 | **ServiceNow Integration** | `servicenow/models.py` | **MISSING** | `ServiceNowService` | **MISSING** | **MISSING** | **MODEL_ONLY** |
| 19 | **Incident Response (KVKK)** | `incident_response/models.py` | **MISSING** | `IncidentResponseService` | **MISSING** | **MISSING** | **MODEL_ONLY** |
| 20 | **Data Protection Inventory** | `data_protection/inventory.py` | `data_processing_inventory_versions` | `InventoryCoverageService` | **MISSING** | **MISSING** | **PART** — table exists, service exists, no API, no UI |
| 21 | **Identity & Sessions** | `identity/models.py` | **MISSING** (no user/role tables) | `SessionService`, LDAP adapter | `POST /api/v1/session/logout` | `DevelopmentLoginPage` | **PART** — dev-mode only; production BFF wired but no user/role persistence |
| 22 | **Persistent Job Queue** | `jobs/models.py` | `persistent_jobs`, `dead_letter_records` | `PersistentJobWorker`, handlers | **MISSING** (no ops API) | **MISSING** | **BE_ONLY** — queue+worker exist, no admin API, no UI |
| 23 | **Secure SDLC** | `secure_sdlc/models.py` | **MISSING** | SAST/SBOM/pentest/evidence gate | **MISSING** | **MISSING** | **MODEL_ONLY** — dev-time tooling only |
| 24 | **Environment Security** | `environment_security/models.py` | **MISSING** | `EnvironmentConfiguration` | **MISSING** | **MISSING** | **MODEL_ONLY** |
| 25 | **Exception/Waiver Mgmt** | **MISSING** | **MISSING** | **MISSING** | **MISSING** | **MISSING** | **MISSING** |
| 26 | **Data Contracts** | **MISSING** | **MISSING** | **MISSING** | **MISSING** | **MISSING** | **MISSING** |
| 27 | **Remediation Actions** | **MISSING** | **MISSING** | **MISSING** | **MISSING** | **MISSING** | **MISSING** |
| 28 | **User/Role Management** | **MISSING** | **MISSING** | **MISSING** | **MISSING** | **MISSING** | **MISSING** |
| 29 | **System Configuration** | **MISSING** | **MISSING** | **MISSING** | **MISSING** | **MISSING** | **MISSING** |
| 30 | **Operations Dashboard** | **MISSING** | **MISSING** | **MISSING** | **MISSING** | **MISSING** | **MISSING** |

## End-to-End Flow Coverage

| Flow | Backend chain | Frontend | Verdict |
|------|--------------|----------|---------|
| **A. Source onboarding** | create → test → activate/passivate ✓ | DataSourcesPage ✓ | **IMPL** — missing: metadata discovery trigger, dataset/field browsing UI |
| **B. Rule lifecycle** | create → version → test → approve → activate → passivate ✓ | RulesPage ✓ | **IMPL** — critical rule approval flow works end-to-end |
| **C. Quality problem** | execution → result → issue → investigation → assign → resolve → verify → close ✓ | IssuesPage ✓ | **IMPL** — missing: auto-creation of issue from failed execution |
| **D. Technical error** | execution attempt → retry → dead-letter ✓ | **MISSING** UI | **BE_ONLY** — worker handles retry/dead-letter, no ops screen |
| **E. Schema drift** | profile comparison → drift judgment ✓ | ProfilingPage (partial) | **PART** — comparison exists, no automated schema change detection/alerting |
| **F. Score reliability** | scoring + contributions + qualification ✓ | Dashboard (partial) | **PART** — backend computes, dashboard shows, but no score detail page |
| **G. Exception/override** | **MISSING** | **MISSING** | **MISSING** |
| **H. Reporting** | create → generate → download ✓ + schedules ✓ | ReportsPage (partial) | **PART** — schedule mgmt has no UI; no async job status visibility |

## Critical Structural Gaps

1. **No `quality_scores` table** — scoring computes in-memory, stores only contribution graphs, not the actual scores
2. **No user/role persistence** — `ActorContext` is issued from dev registry or session service, but no `users` or `roles` tables exist
3. **No notification persistence** — notification module is fire-and-forget, no delivery tracking
4. **No schedule → execution bridge** — `schedules` table exists but no evidence of cron/worker triggering executions from schedules
5. **No execution start from UI** — `POST /api/v1/executions` exists but `ExecutionsPage` is read-only list
6. **Development-only auth** — production BFF session boundary is coded but no IdP integration is wired in `run_dev.py`
7. **No API versioning strategy** — all endpoints are `/api/v1/` but no version negotiation or deprecation mechanism
