# Test Inventory — Read-Only Evidence

> Source: `docs/testing/` — 57 unit test files, 13 integration test files, 7 E2E specs.

## Unit Tests (tests/unit/)

| # | File | Domain area | What it tests |
|---|------|------------|---------------|
| 1 | `test_audit.py` | Audit | Audit service, redaction, outbox |
| 2 | `test_audit_api.py` | Audit API | Audit HTTP endpoints |
| 3 | `test_bff_session_api.py` | Session/BFF | BFF session boundary |
| 4 | `test_dashboard.py` | Dashboard | Dashboard query service |
| 5 | `test_dashboard_api.py` | Dashboard API | Dashboard HTTP endpoints |
| 6 | `test_dashboard_filters.py` | Dashboard | Dashboard filter params |
| 7 | `test_data_source_api.py` | Data Source API | Data source HTTP endpoints |
| 8 | `test_data_sources.py` | Data Sources | Source query/mutation service |
| 9 | `test_enterprise_lab.py` | Enterprise Lab | Lab adapter tests |
| 10 | `test_enterprise_lab_adapters.py` | Enterprise Lab | External adapter tests |
| 11 | `test_environment_security.py` | Environment | Runtime environment |
| 12 | `test_execution_api.py` | Execution API | Execution HTTP endpoints |
| 13 | `test_executions.py` | Executions | Execution service |
| 14 | `test_identity.py` | Identity | Actor context, sessions |
| 15 | `test_incident_response.py` | Incidents | Security incident workflow |
| 16 | `test_investigation_evidence.py` | Issues | Investigation evidence service |
| 17 | `test_issue_api.py` | Issue API | Issue HTTP endpoints |
| 18 | `test_issues.py` | Issues | Issue lifecycle service |
| 19 | `test_job_queue.py` | Jobs | Persistent job queue |
| 20 | `test_lineage_governance.py` | Lineage | Governance profiles |
| 21 | `test_notifications.py` | Notifications | Notification dispatch |
| 22 | `test_partial_score_policies.py` | Scoring | Partial score policies |
| 23 | `test_persistent_job_handlers.py` | Jobs | Job handler dispatch |
| 24 | `test_persistent_job_worker.py` | Jobs | Worker claim/heartbeat |
| 25 | `test_postgresql_data_source_repository.py` | Data Sources | PostgreSQL repo |
| 26 | `test_postgresql_execution_repository.py` | Executions | PostgreSQL repo |
| 27 | `test_postgresql_persistence.py` | Persistence | DB session |
| 28 | `test_postgresql_rule_repository.py` | Rules | PostgreSQL repo |
| 29 | `test_profile_analysis.py` | Profiling | Profile analysis |
| 30 | `test_profile_snapshot_query.py` | Profiling | Snapshot query service |
| 31 | `test_prototype_05_capabilities.py` | Prototype | Prototype 05 features |
| 32 | `test_report_api.py` | Report API | Report HTTP endpoints |
| 33 | `test_reporting.py` | Reporting | Report service, preview |
| 34 | `test_retention.py` | Retention | Retention policy eval |
| 35 | `test_retention_archive_recall.py` | Retention | Archive recall |
| 36 | `test_retention_disposal_job.py` | Retention | Disposal job |
| 37 | `test_retention_legal_hold.py` | Retention | Legal hold |
| 38 | `test_rule_api.py` | Rule API | Rule HTTP endpoints |
| 39 | `test_rules.py` | Rules | Rule service, mutations |
| 40 | `test_score_contributions.py` | Scoring | Contribution graph |
| 41 | `test_scoring.py` | Scoring | Score computation |
| 42 | `test_secure_sdlc.py` | Secure SDLC | SDLC pipeline |
| 43 | `test_secure_sdlc_evidence.py` | Secure SDLC | Evidence collection |
| 44 | `test_secure_sdlc_evidence_gate.py` | Secure SDLC | Evidence gate |
| 45 | `test_secure_sdlc_pentest.py` | Secure SDLC | Pentest checks |
| 46 | `test_secure_sdlc_preflight.py` | Secure SDLC | Preflight checks |
| 47 | `test_secure_sdlc_sast.py` | Secure SDLC | SAST scanning |
| 48 | `test_secure_sdlc_sbom.py` | Secure SDLC | SBOM generation |
| 49 | `test_secure_sdlc_vulnerabilities.py` | Secure SDLC | Vuln management |
| 50 | `test_servicenow.py` | ServiceNow | Ticket integration |
| 51 | `test_source_usage_policies.py` | Executions | Source usage policies |
| 52 | `test_synthetic_data.py` | Synthetic | Synthetic data service |
| 53 | `test_synthetic_generator.py` | Synthetic | Generator logic |
| 54 | `test_synthetic_oracle.py` | Synthetic | Oracle validation |
| 55 | `test_synthetic_postgresql_dataset.py` | Synthetic | PostgreSQL dataset |
| 56 | `test_synthetic_temporal.py` | Synthetic | Temporal profiles |
| 57 | `test_trend_components.py` | Dashboard | Trend computation |

## Integration Tests (tests/integration/)

| # | File | Domain area | What it tests |
|---|------|------------|---------------|
| 1 | `conftest.py` | Shared | PostgreSQL test fixtures |
| 2 | `test_postgresql_data_source_persistence.py` | Data Sources | Real PG persistence |
| 3 | `test_postgresql_execution_persistence.py` | Executions | Real PG persistence |
| 4 | `test_postgresql_issue_migration.py` | Issues | Migration execution |
| 5 | `test_postgresql_issue_mutations.py` | Issues | Issue mutations on PG |
| 6 | `test_postgresql_issue_persistence.py` | Issues | Issue persistence on PG |
| 7 | `test_postgresql_job_queue.py` | Jobs | Job queue on PG |
| 8 | `test_postgresql_lineage_evidence.py` | Lineage | Lineage on PG |
| 9 | `test_postgresql_report_lifecycle.py` | Reporting | Report lifecycle on PG |
| 10 | `test_postgresql_rule_mutations.py` | Rules | Rule mutations on PG |
| 11 | `test_postgresql_score_contributions.py` | Scoring | Contributions on PG |
| 12 | `test_synthetic_postgresql_integration.py` | Synthetic | Synthetic data on PG |

## Frontend E2E Tests (frontend/e2e/)

| # | File | Scope |
|---|------|-------|
| 1 | `dashboard.spec.ts` | Dashboard page |
| 2 | `data-sources.spec.ts` | Data sources page |
| 3 | `rules.spec.ts` | Rules page |
| 4 | `executions.spec.ts` | Executions page |
| 5 | `issues.spec.ts` | Issues page |
| 6 | `reports.spec.ts` | Reports page |
| 7 | `audit.spec.ts` | Audit page |

## Legacy Support

| File | Purpose |
|------|---------|
| `tests/support/legacy_sqlite_issue_repository.py` | SQLite-based legacy issue repo for backward compat tests |

## Test Coverage Gaps

| Domain | Unit tests | Integration tests | E2E tests |
|--------|-----------|-------------------|-----------|
| Dashboard | 3 files | 0 | 1 spec |
| Data Sources | 3 files | 1 file | 1 spec |
| Profiling | 2 files | 0 | 0 |
| Rules | 2 files | 1 file | 1 spec |
| Executions | 3 files | 1 file | 1 spec |
| Issues | 4 files | 3 files | 1 spec |
| Reports | 2 files | 1 file | 1 spec |
| Audit | 2 files | 0 | 1 spec |
| Jobs | 3 files | 1 file | 0 |
| Scoring | 3 files | 1 file | 0 |
| Notifications | 1 file | 0 | 0 |
| Retention | 4 files | 0 | 0 |
| Lineage | 1 file | 1 file | 0 |
| Identity/Session | 1 file | 0 | 0 |
| Secure SDLC | 8 files | 0 | 0 |
| ServiceNow | 1 file | 0 | 0 |
| Synthetic Data | 5 files | 1 file | 0 |
| Incident Response | 1 file | 0 | 0 |
| Enterprise Lab | 2 files | 0 | 0 |
| Environment | 1 file | 0 | 0 |
| Data Protection | 0 | 0 | 0 |
| Scheduling | 0 | 0 | 0 |
| Report Schedules | 0 | 0 | 0 |
