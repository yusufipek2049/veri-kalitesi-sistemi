# Database Schema Inventory — Read-Only Evidence

> Source: `alembic/versions/*.py` — 14 migration files.
> Schema: `dq` (configurable via `alembic.ini`)

## Migration Chain

```
20260723_01 (issue_baseline)
  → 20260723_02 (rule_baseline)
    → 20260724_03 (data_source_baseline)
      → 20260724_04 (execution_baseline)
        → 20260724_05 (scheduling_and_policy_baseline)
          → 20260724_06 (reporting_baseline)
            → 20260724_07 (report_schedules)
              → 20260728_08 (job_queue)
                → 20260729_09 (job_lifecycle)
                  → 20260729_10 (source_policy_deadlines)
                    → 20260729_11 (profile_comparisons)
                      → 20260730_12 (rule_ir_shadow_evidence)
                        → 20260730_13 (score_contribution_graphs)
                          → 20260730_14 (lineage_governance_evidence)
```

## Table Inventory

### Migration 01 — Issue Baseline

| Table | PK | Key columns | Constraints | Indexes |
|-------|----|-------------|-------------|---------|
| `data_quality_issues` | `issue_id` | issue_no, source_event_type, trigger_type, scope_type, scope_id, status, priority, assignee_user_id, deduplication_key_digest, payload_digest, occurrence_count, version, timestamps | CK: source_event_type, trigger_type, scope_type, status(8 values), priority, occurrence_count≥1 | ix_dq_issues_scope_updated, ix_dq_issues_assignee_status_updated |
| `issue_history` | `sequence_no` (Identity) | history_id, issue_id(FK→issues), action, actor_id, old/new_status, old/new_assignee, old/new_priority, resolution_id, verification_id, occurred_at | CK: old_status, new_status, old_priority, new_priority | ix_dq_issue_history_issue_sequence |
| `issue_resolutions` | `sequence_no` (Identity) | resolution_id, issue_id(FK), root_cause, corrective_action, evidence_reference_id, completed_at, protection_policy_version, created_by, created_at | CK: root_cause length/no-html, corrective_action length/no-html | ix_dq_issue_resolutions_issue_sequence |
| `issue_verifications` | `sequence_no` (Identity) | verification_id, issue_id(FK), verification_reference_id(unique), execution_id, score_id, scope_type, scope_id, outcome, completed_at, recorded_by, recorded_at | CK: scope_type, outcome(4 values) | ix_dq_issue_verifications_issue_sequence |
| `issue_relationships` | `sequence_no` (Identity) | relationship_id, predecessor_issue_id(FK), successor_issue_id(FK), relationship_type, created_at | CK: relationship_type(RECURRENCE), UQ: (predecessor, successor, type) | ix_dq_issue_relationships_predecessor_sequence |
| `audit_outbox` | `event_id` | prepared_event(JSON), policy_version, status, attempt_count, last_error_code, created_at, published_at | CK: status(PENDING/PUBLISHED) | ix_dq_audit_outbox_pending |

### Migration 02 — Rule Baseline

| Table | PK | Key columns | Constraints | Indexes |
|-------|----|-------------|-------------|---------|
| `quality_rules` | `quality_rule_id` | code(unique), name, dataset_id, field_ids(JSON), primary_dimension, owner_user_id, status | CK: primary_dimension(7 values), status(5 values) | ix_dq_quality_rules_dataset |
| `rule_versions` | `rule_version_id` | quality_rule_id(FK), version_no, rule_type, definition(JSON), threshold, weight, criticality, prepared_by_actor_id, created_at | UQ: (quality_rule_id, version_no), CK: rule_type(8 values), criticality(4 values) | ix_dq_rule_versions_rule_version_seq |
| `rule_test_results` | `rule_test_result_id` | rule_version_id(FK), status, record_limit, checked/passed/failed/not_evaluated_count, success_rate, preview_score, official_score_included, error_class, message, created_at | CK: status(SUCCESS/TECHNICAL_ERROR) | ix_dq_rule_test_results_version_created |
| `rule_approval_requests` | `approval_request_id` | rule_version_id(FK), maker_actor_id, checker_actor_id, policy_version, status, decision_reason_code, requested_at, target_at, expires_at, business_calendar_version, decided_at | CK: status(5 values), Partial UQ: rule_version_id WHERE PENDING | ix_dq_rule_approval_requests_pending_expires (partial) |

### Migration 03 — Data Source Baseline

| Table | PK | Key columns | Constraints | Indexes |
|-------|----|-------------|-------------|---------|
| `data_sources` | `data_source_id` | name(unique), source_type, connection_config(JSON), secret_reference, owner_user_id, status, revision, last_test_at, created_at | CK: source_type(7 values), status(6 values), UQ: name | ix_dq_data_sources_status |
| `connection_test_results` | `test_result_id` (auto) | data_source_id(FK), succeeded, duration_ms, error_class, message, source_info(JSON), data_source_revision, tested_at | — | ix_dq_connection_test_results_source |
| `datasets` | `dataset_id` | data_source_id(FK), namespace, name, dataset_type, criticality, owner_user_id, estimated_row_count | UQ: (source, namespace, name), CK: dataset_type(5), criticality(4) | ix_dq_datasets_source |
| `data_fields` | `data_field_id` | dataset_id(FK), name, native_data_type, is_nullable, is_sensitive, classification, classification_policy_version | UQ: (dataset_id, name), CK: classification(9 values) | ix_dq_data_fields_dataset |
| `metadata_discovery_results` | `discovery_id` (auto) | data_source_id(FK), succeeded, duration_ms, scanned_object_count, error_class, message, changes(JSON), discovered_at | — | ix_dq_metadata_discovery_results_source |
| `data_profiles` | `profile_id` | dataset_id(FK), execution_id, method, sample_ratio, metrics(JSON), status, duration_ms, error_class, message, started_at, finished_at | CK: method(FULL/SAMPLE), status(4 values) | ix_dq_data_profiles_dataset |
| `data_processing_inventory_versions` | `inventory_id` | data_field_id(FK), version_number, processing_purpose, legal_basis_reference, data_owner_id, retention_policy_id, access_role_codes(JSON), cross_border_transfer, recipient_groups(JSON), recorded_at | UQ: (field, version), CK: version>0 | ix_dq_processing_inventory_field |
| `data_source_connection_revisions` | `connection_revision_id` | data_source_id(FK), revision, base_revision, connection_config(JSON), secret_reference, prepared_by_actor_id, policy_version, reason_code, status, created_at, tested_at | UQ: (source, revision), CK: revision>0, base>0, status(4) | ix_dq_connection_revisions_source |
| `data_source_activation_requests` | `activation_request_id` | data_source_id(FK), data_source_revision, maker_actor_id, checker_actor_id, policy_version, status, decision_reason_code, timestamps | CK: status(6 values) | ix_dq_activation_requests_source, ix_dq_activation_requests_status (partial) |

### Migration 04 — Execution Baseline

| Table | PK | Key columns | Constraints | Indexes |
|-------|----|-------------|-------------|---------|
| `rule_executions` | `execution_id` | execution_type, status, idempotency_key_hash(unique), payload_hash, rule_version_ids(JSON), scope(JSON), triggered_by, correlation_id, source_ids(JSON), workload_class, error_class, attempt_count, timestamps, cancel_* | CK: type(2), status(8), workload(2) | ix_executions_status, ix_executions_created_at |
| `execution_attempts` | `attempt_id` | execution_id(FK), attempt_no, status, error_class, retryable, created_at | UQ: (execution, attempt), CK: status(8) | ix_execution_attempts_execution_id |
| `rule_execution_results` | `rule_result_id` | execution_id(FK), rule_version_id, population/eligible/evaluated/passed/failed/excluded/technical_error/unknown_count, measurement_status, completed_partitions(JSON), eligible_for_official_scoring | UQ: (execution, rule_version) | ix_execution_results_execution_id |

### Migration 05 — Scheduling & Policy

| Table | PK | Key columns |
|-------|----|-------------|
| `schedules` | `schedule_id` | name(unique), schedule_type, timezone_name, rule_version_ids(JSON), created_by, local_time, once_at, day_of_week/month, is_active, next_run_at, timestamps |
| `source_usage_policies` | `policy_id` | policy_version, status, source_id, source_type, max_concurrent_queries, max_workers, query_timeout_seconds, retry_count/delay, rate_limit(JSON), allowed/blocked_windows(JSON) |

### Migration 06 — Reporting

| Table | PK | Key columns |
|-------|----|-------------|
| `reports` | `report_id` | report_type, format, requested_by, parameters(JSON), status, sensitivity_level, retention_policy_id, online_file_reference, file_size, expires_at, failure_reason, created_at, completed_at, version |

### Migration 07 — Report Schedules

| Table | PK | Key columns |
|-------|----|-------------|
| `report_schedules` | `schedule_id` | name(unique), report_type, format, parameters(JSON), sensitivity_level, recipients(JSON), schedule_type, timezone_name, local_time, once_at, day_of_week/month, is_active, next_run_at, created_by, timestamps |

### Migration 08 — Job Queue

| Table | PK | Key columns |
|-------|----|-------------|
| `persistent_jobs` | `job_id` | job_type, payload(JSON), status, priority, idempotency_key, available_at, timestamps, claimed_by, lease_expires_at, last_heartbeat_at, attempt_count, version, last_error_class |

### Migration 09 — Job Lifecycle

| Table | PK | Key columns |
|-------|----|-------------|
| `persistent_jobs` (ALTER) | — | +completion_outcome, completed_at, cancel_requested_at, cancel_requested_by, cancel_reason_code |
| `dead_letter_records` | `dead_letter_id` | job_id(FK), error_class, attempt_count, status, created_at, reprocessed_at, reprocessed_by, audit_event_id |

### Migration 10 — Source Policy Deadlines
- ALTER: adds deadline columns to `source_usage_policies`

### Migration 11 — Profile Comparisons

| Table | PK | Key columns |
|-------|----|-------------|
| `profile_comparisons` | `comparison_id` | dataset_id, baseline_profile_id, current_profile_id, policy_version, status, anomaly_candidate, result(JSON), message, created_at |

### Migration 12 — Rule IR Shadow Evidence
- ALTER: adds IR shadow evidence columns to `rule_versions`

### Migration 13 — Score Contribution Graphs

| Table | PK | Key columns |
|-------|----|-------------|
| `score_contribution_graphs` | `quality_score_id` | execution_id, scope_type, scope_id, graph(JSONB), created_at |

### Migration 14 — Lineage Governance Evidence

| Table | PK | Key columns |
|-------|----|-------------|
| `lineage_evidence_snapshots` | `snapshot_id` | snapshot_kind, subject_ref, version_label, digest, payload(JSONB), created_at |

## Domain Models Without Tables

| Domain model | Module | Has migration? |
|-------------|--------|---------------|
| Notification, NotificationEvent | `notifications/` | **No** |
| RetentionPolicy, LegalHold, DisposalJob | `retention/` | **No** |
| LineageEvent, ColumnLineageEdge | `lineage/events.py` | **No** |
| DataAssetGovernanceProfile | `lineage/governance.py` | **No** |
| ServiceNowTicket*, RetryJob | `servicenow/` | **No** |
| SyntheticGenerationRun, GroundTruth | `synthetic_data/` | **No** |
| SecurityIncident, Breach* | `incident_response/` | **No** |
| DataProcessingInventory | `data_protection/` | **No** |
| QualityScore | `scoring/` | **No** (only contribution graphs) |
