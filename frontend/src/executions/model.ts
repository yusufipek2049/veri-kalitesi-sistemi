export type ExecutionState = "normal" | "loading" | "empty" | "error" | "unauthorized" | "long-content";

export interface ExecutionDatasetRef {
  datasetId: string;
  name: string;
  namespace: string;
  sourceId: string;
  sourceName: string;
}

export interface ExecutionListItem {
  id: string;
  executionType: string;
  executionMode?: "OFFICIAL" | "SHADOW";
  status: string;
  workloadClass: string;
  ruleCount: number;
  sourceCount: number;
  attemptCount: number;
  errorClass?: string;
  progressPercent: number;
  blockedReasonCode?: string;
  availableActions: string[];
  datasets: ExecutionDatasetRef[];
  scheduleId?: string;
  createdAt: string;
  startedAt?: string;
  finishedAt?: string;
}

interface ExecutionResultSummary {
  ruleVersionId: string;
  populationCount: number | null;
  passedCount: number | null;
  failedCount: number | null;
  evaluatedCount: number | null;
  measurementStatus: string | null;
}

export interface ExecutionDetail {
  item: ExecutionListItem;
  results: ExecutionResultSummary[];
  ruleDefinitions: RuleDefinitionSummary[];
  jobInfo: JobInfo | null;
}

export interface RuleDefinitionSummary {
  ruleVersionId: string;
  ruleType: string | null;
  definition: Record<string, unknown>;
  sql: string | null;
}

export interface JobInfo {
  jobId: string;
  status: string;
  queuePosition: number | null;
  workerId: string | null;
  leasedUntil: string | null;
  attemptCount: number;
  lastErrorClass: string | null;
  completedAt: string | null;
  completionOutcome: string | null;
}

export interface ExecutionListApiResponse {
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  limit: number;
  items: Array<{
    execution_id: string;
    execution_type: string;
    execution_mode?: "OFFICIAL" | "SHADOW";
    status: string;
    workload_class: string;
    rule_count: number;
    source_count: number;
    attempt_count: number;
    error_class: string | null;
    progress_percent: number;
    blocked_reason_code: string | null;
    available_actions: string[];
    datasets: Array<{
      dataset_id: string;
      name: string;
      namespace: string;
      source_id: string;
      source_name: string;
    }>;
    schedule_id: string | null;
    created_at: string;
    started_at: string | null;
    finished_at: string | null;
  }>;
}

export interface ExecutionDetailApiResponse {
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  execution: ExecutionListApiResponse["items"][number];
  rule_results: Array<{
    rule_version_id: string;
    population_count: number | null;
    passed_count: number | null;
    failed_count: number | null;
    evaluated_count: number | null;
    measurement_status: string | null;
  }>;
  rule_definitions?: Array<{
    rule_version_id: string;
    rule_type: string | null;
    definition: Record<string, unknown>;
  }>;
  job_info?: {
    job_id: string;
    status: string;
    queue_position: number | null;
    worker_id: string | null;
    leased_until: string | null;
    attempt_count: number;
    last_error_class: string | null;
    completed_at: string | null;
    completion_outcome: string | null;
  } | null;
}

export interface ExecutionStartRequest {
  rule_version_ids: string[];
  source_ids: string[];
  idempotency_key: string;
  execution_mode: "OFFICIAL" | "SHADOW";
}

export interface ExecutionCancelRequest {
  reason: string;
}

export const syntheticExecutions: ExecutionListItem[] = [
  { id: "execution-running", executionType: "MANUAL", status: "RUNNING", workloadClass: "HEAVY", ruleCount: 2, sourceCount: 1, attemptCount: 1, progressPercent: 42, availableActions: ["cancel"], datasets: [{ datasetId: "ds-tx", name: "transactions", namespace: "public", sourceId: "src-core", sourceName: "Core DB" }], createdAt: "2026-07-23T08:41:00Z", startedAt: "2026-07-23T08:41:00Z" },
  { id: "execution-queued", executionType: "SCHEDULED", status: "QUEUED", workloadClass: "LIGHT", ruleCount: 1, sourceCount: 1, attemptCount: 0, progressPercent: 0, availableActions: ["cancel"], datasets: [{ datasetId: "ds-cust", name: "customers", namespace: "public", sourceId: "src-core", sourceName: "Core DB" }], scheduleId: "schedule-daily-customer", createdAt: "2026-07-23T08:35:00Z" },
  { id: "execution-success", executionType: "SCHEDULED", status: "SUCCESS", workloadClass: "LIGHT", ruleCount: 1, sourceCount: 1, attemptCount: 1, progressPercent: 100, availableActions: [], datasets: [{ datasetId: "ds-acct", name: "accounts", namespace: "public", sourceId: "src-core", sourceName: "Core DB" }], scheduleId: "schedule-daily-account", createdAt: "2026-07-23T07:15:00Z", startedAt: "2026-07-23T07:16:00Z", finishedAt: "2026-07-23T07:24:00Z" },
  { id: "execution-partial", executionType: "MANUAL", status: "PARTIAL", workloadClass: "HEAVY", ruleCount: 1, sourceCount: 1, attemptCount: 1, errorClass: "QUERY_TIMEOUT", progressPercent: 78, availableActions: [], datasets: [{ datasetId: "ds-tx", name: "transactions", namespace: "public", sourceId: "src-analytics", sourceName: "Analytics DB" }], createdAt: "2026-07-22T18:00:00Z", startedAt: "2026-07-22T18:01:00Z", finishedAt: "2026-07-22T18:31:00Z" },
  { id: "execution-technical-error", executionType: "MANUAL", status: "TECHNICAL_ERROR", workloadClass: "LIGHT", ruleCount: 1, sourceCount: 1, attemptCount: 3, errorClass: "CONNECTION_UNAVAILABLE", progressPercent: 12, availableActions: [], datasets: [{ datasetId: "ds-usr", name: "users", namespace: "auth", sourceId: "src-identity", sourceName: "Identity Service" }], createdAt: "2026-07-22T14:20:00Z", startedAt: "2026-07-22T14:21:00Z", finishedAt: "2026-07-22T14:24:00Z" },
  { id: "execution-timeout", executionType: "MANUAL", status: "TIMEOUT", workloadClass: "LIGHT", ruleCount: 1, sourceCount: 1, attemptCount: 1, errorClass: "TOTAL_TIMEOUT", progressPercent: 55, availableActions: [], datasets: [{ datasetId: "ds-log", name: "audit_logs", namespace: "logging", sourceId: "src-core", sourceName: "Core DB" }], createdAt: "2026-07-21T11:00:00Z", startedAt: "2026-07-21T11:01:00Z", finishedAt: "2026-07-21T12:01:00Z" },
  { id: "execution-cancel-requested", executionType: "MANUAL", status: "CANCEL_REQUESTED", workloadClass: "LIGHT", ruleCount: 1, sourceCount: 1, attemptCount: 1, progressPercent: 30, availableActions: [], datasets: [{ datasetId: "ds-pmt", name: "payments", namespace: "finance", sourceId: "src-core", sourceName: "Core DB" }], createdAt: "2026-07-20T09:00:00Z", startedAt: "2026-07-20T09:01:00Z" },
  { id: "execution-cancelled", executionType: "MANUAL", status: "CANCELLED", workloadClass: "LIGHT", ruleCount: 1, sourceCount: 1, attemptCount: 0, progressPercent: 0, availableActions: [], datasets: [{ datasetId: "ds-bal", name: "balances", namespace: "finance", sourceId: "src-core", sourceName: "Core DB" }], createdAt: "2026-07-19T16:00:00Z", finishedAt: "2026-07-19T16:02:00Z" },
];

function mapListItem(item: ExecutionListApiResponse["items"][number]): ExecutionListItem {
  return {
    id: item.execution_id,
    executionType: item.execution_type,
    executionMode: item.execution_mode ?? "OFFICIAL",
    status: item.status,
    workloadClass: item.workload_class,
    ruleCount: item.rule_count,
    sourceCount: item.source_count,
    attemptCount: item.attempt_count,
    errorClass: item.error_class ?? undefined,
    progressPercent: item.progress_percent,
    blockedReasonCode: item.blocked_reason_code ?? undefined,
    availableActions: item.available_actions ?? [],
    datasets: (item.datasets ?? []).map((ds) => ({
      datasetId: ds.dataset_id,
      name: ds.name,
      namespace: ds.namespace,
      sourceId: ds.source_id,
      sourceName: ds.source_name,
    })),
    scheduleId: item.schedule_id ?? undefined,
    createdAt: item.created_at,
    startedAt: item.started_at ?? undefined,
    finishedAt: item.finished_at ?? undefined,
  };
}

export function executionsFromApi(response: ExecutionListApiResponse): ExecutionListItem[] {
  return response.items.map(mapListItem);
}

export function executionDetailFromApi(response: ExecutionDetailApiResponse): ExecutionDetail {
  const ruleDefinitions = (response.rule_definitions ?? []).map((d) => {
    const def = d.definition ?? {};
    // Extract SQL from definition if available (CUSTOM_SQL rules store it in definition.sql)
    const sql = typeof def.sql === "string" ? def.sql : null;
    return {
      ruleVersionId: d.rule_version_id,
      ruleType: d.rule_type,
      definition: def,
      sql,
    };
  });
  return {
    item: mapListItem(response.execution),
    results: (response.rule_results ?? []).map((r) => ({
      ruleVersionId: r.rule_version_id,
      populationCount: r.population_count,
      passedCount: r.passed_count,
      failedCount: r.failed_count,
      evaluatedCount: r.evaluated_count,
      measurementStatus: r.measurement_status,
    })),
    ruleDefinitions,
    jobInfo: response.job_info
      ? {
          jobId: response.job_info.job_id,
          status: response.job_info.status,
          queuePosition: response.job_info.queue_position,
          workerId: response.job_info.worker_id,
          leasedUntil: response.job_info.leased_until,
          attemptCount: response.job_info.attempt_count,
          lastErrorClass: response.job_info.last_error_class,
          completedAt: response.job_info.completed_at,
          completionOutcome: response.job_info.completion_outcome,
        }
      : null,
  };
}
