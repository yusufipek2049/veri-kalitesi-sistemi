# API Endpoint Inventory — Read-Only Evidence

> Her endpoint için kod kanıtı. Dokümantasyon beyanı sayılmaz.

## Endpoint Table

Kaynak: `src/veri_kalitesi/api/app.py`

| # | Method | Path | Tag | Handler | Actor required | CSRF | Service dep |
|---|--------|------|-----|---------|---------------|------|-------------|
| 1 | GET | `/api/v1/dashboard/summary` | dashboard | `get_dashboard_summary` | Yes (resolve) | No | `dashboard_service` |
| 2 | GET | `/api/v1/data-sources` | data-sources | `get_data_sources` | Yes | No | `data_source_query_service` |
| 3 | POST | `/api/v1/data-sources` | data-sources | `create_data_source` | Yes (state-change) | Yes | `data_source_mutation_service` |
| 4 | POST | `/api/v1/data-sources/{id}/test` | data-sources | `test_data_source` | Yes | Yes | `data_source_mutation_service` |
| 5 | POST | `/api/v1/data-sources/{id}/activation` | data-sources | `activate_data_source` | Yes | Yes | `data_source_mutation_service` |
| 6 | POST | `/api/v1/data-sources/{id}/passivation` | data-sources | `passivate_data_source` | Yes | Yes | `data_source_mutation_service` |
| 7 | POST | `/api/v1/profile-comparisons` | data-sources | `compare_profiles` | Yes | Yes | `profile_comparison_service` |
| 8 | GET | `/api/v1/profile-snapshots` | data-sources | `get_profile_snapshots` | Yes | No | `profile_snapshot_query_service` |
| 9 | GET | `/api/v1/profile-snapshots/{profile_id}` | data-sources | `get_profile_snapshot` | Yes | No | `profile_snapshot_query_service` |
| 10 | GET | `/api/v1/profile-snapshots/{profile_id}/drift` | data-sources | `get_drift_judgments` | Yes | No | `profile_snapshot_query_service` |
| 11 | GET | `/api/v1/rules` | rules | `get_rules` | Yes | No | `rule_query_service` |
| 12 | POST | `/api/v1/rules` | rules | `create_rule` | Yes | Yes | `rule_creator_service` |
| 13 | POST | `/api/v1/rules/{id}/versions` | rules | `create_rule_version` | Yes | Yes | `rule_mutation_service` |
| 14 | POST | `/api/v1/rules/{id}/test` | rules | `test_rule` | Yes | Yes | `rule_mutation_service` |
| 15 | POST | `/api/v1/rules/{id}/activation` | rules | `activate_rule` | Yes | Yes | `rule_mutation_service` |
| 16 | POST | `/api/v1/rules/{id}/approval` | rules | `request_rule_approval` | Yes | Yes | `rule_mutation_service` |
| 17 | POST | `/api/v1/rules/approval/{id}/decide` | rules | `decide_rule_approval` | Yes | Yes | `rule_mutation_service` |
| 18 | POST | `/api/v1/rules/approval/{id}/withdraw` | rules | `withdraw_rule_approval` | Yes | Yes | `rule_mutation_service` |
| 19 | POST | `/api/v1/rules/{id}/passivation` | rules | `passivate_rule` | Yes | Yes | `rule_mutation_service` |
| 20 | GET | `/api/v1/executions` | executions | `get_executions` | Yes | No | `execution_query_service` |
| 21 | POST | `/api/v1/executions` | executions | `start_manual_execution` | Yes | Yes | `execution_start_service` |
| 22 | POST | `/api/v1/executions/{id}/cancel` | executions | `cancel_execution` | Yes | Yes | `execution_cancel_service` |
| 23 | GET | `/api/v1/issues` | issues | `get_issues` | Yes | No | `issue_query_service` |
| 24 | POST | `/api/v1/issues/{id}/investigation` | issues | `start_issue_investigation` | Yes | Yes | `issue_investigation_service` |
| 25 | GET | `/api/v1/issues/{id}/investigation/evidence` | issues | `get_issue_investigation_evidence` | Yes | No | `issue_investigation_evidence_service` |
| 26 | GET | `/api/v1/issues/{id}/assignment-options` | issues | `get_issue_assignment_options` | Yes | No | `issue_assignee_option_provider` |
| 27 | POST | `/api/v1/issues/{id}/assignment` | issues | `reassign_issue` | Yes | Yes | `issue_assignment_service` |
| 28 | POST | `/api/v1/issues/{id}/resolution` | issues | `resolve_issue` | Yes | Yes | `issue_resolution_service` |
| 29 | POST | `/api/v1/issues/{id}/verification` | issues | `verify_issue` | Yes | Yes | `issue_verification_service` |
| 30 | POST | `/api/v1/issues/{id}/closure` | issues | `close_issue` | Yes | Yes | `issue_closure_service` |
| 31 | GET | `/api/v1/reports/summary` | reports | `get_report_summary` | Yes | No | `report_preview_service` |
| 32 | POST | `/api/v1/reports/` | reports | `create_report` | Yes | Yes | `report_service` |
| 33 | GET | `/api/v1/reports/` | reports | `list_reports` | Yes | No | `report_service` |
| 34 | GET | `/api/v1/reports/{id}` | reports | `get_report` | Yes | No | `report_service` |
| 35 | GET | `/api/v1/reports/{id}/download` | reports | `download_report` | Yes | No | `report_service` |
| 36 | GET | `/api/v1/report-schedules` | reports | `list_report_schedules` | Yes | No | `report_schedule_service` |
| 37 | POST | `/api/v1/report-schedules` | reports | `create_report_schedule` | Yes | Yes | `report_schedule_service` |
| 38 | DELETE | `/api/v1/report-schedules/{id}` | reports | `delete_report_schedule` | Yes | Yes | `report_schedule_service` |
| 39 | POST | `/api/v1/report-schedules/trigger-due` | reports | `trigger_due_report_schedules` | Yes | Yes | `report_schedule_service` |
| 40 | GET | `/api/v1/audit/events` | audit | `get_audit_events` | Yes | No | `audit_query_service` |
| 41 | POST | `/api/v1/session/logout` | session | `logout` | Yes | Yes | `bff_session_boundary` |
| 42 | GET | `/api/v1/development/users` | development | `list_development_users` | No | No | `development_user_registry` |
| 43 | GET | `/api/v1/lineage/snapshots/{id}` | lineage | `get_lineage_snapshot` | Yes | No | `lineage_evidence_repository` |
| 44 | GET | `/api/v1/governance/{asset_ref}/projection` | lineage | `get_governance_projection` | Yes | No | `governance_profile_reader` |

## Missing API Endpoints (No code evidence)

The following expected endpoints have **no implementation**:

| Domain | Missing endpoint | Status |
|--------|-----------------|--------|
| Scheduling | `GET/POST /api/v1/schedules` (rule execution schedules) | **MISSING** |
| Scoring | `GET /api/v1/scores` or `GET /api/v1/quality-scores` | **MISSING** |
| Notifications | `GET/POST /api/v1/notifications` | **MISSING** |
| Notifications | `POST /api/v1/notifications/{id}/acknowledge` | **MISSING** |
| Lineage | `GET /api/v1/lineage/impact/{dataset_id}` | **MISSING** |
| Synthetic Data | `POST /api/v1/synthetic-data/runs` | **MISSING** |
| Retention | `GET/POST /api/v1/retention/policies` | **MISSING** |
| Retention | `POST /api/v1/retention/legal-holds` | **MISSING** |
| Retention | `POST /api/v1/retention/disposal-jobs` | **MISSING** |
| ServiceNow | `POST /api/v1/servicenow/tickets` | **MISSING** |
| Incidents | `POST /api/v1/incidents` | **MISSING** |
| Incidents | `GET /api/v1/incidents` | **MISSING** |
| Data Protection | `GET /api/v1/data-processing-inventory` | **MISSING** |
| Exceptions/Waivers | `POST /api/v1/exceptions` | **MISSING** |
| Data Contracts | `GET/POST /api/v1/data-contracts` | **MISSING** |
| Users/Roles Mgmt | `GET/POST /api/v1/users` | **MISSING** |
| Users/Roles Mgmt | `GET/POST /api/v1/roles` | **MISSING** |
| System Config | `GET/PUT /api/v1/system-config` | **MISSING** |
| Operations | `GET /api/v1/operations/health` | **MISSING** |
| Operations | `GET /api/v1/operations/dead-letters` | **MISSING** |
| Operations | `POST /api/v1/operations/dead-letters/{id}/replay` | **MISSING** |
| Job Queue | `GET /api/v1/jobs` | **MISSING** |

## Pagination, Filtering, Sorting Evidence

| Endpoint | Pagination | Filtering | Sorting |
|----------|-----------|-----------|---------|
| Dashboard summary | No | Yes (date, scope, status, level) | No |
| Data sources list | **No** | **No** | **No** |
| Rules list | **No** | **No** | **No** |
| Executions list | Yes (limit) | **No** | **No** |
| Issues list | Yes (limit) | **No** | **No** |
| Reports list | Yes (limit, offset) | **No** | **No** |
| Audit events | Yes (cursor: after_sequence_no) | Yes (actor, action, object, result) | Implicit (sequence_no) |
| Profile snapshots | Yes (limit: MAX_SNAPSHOTS) | Yes (dataset_id required) | **No** |
