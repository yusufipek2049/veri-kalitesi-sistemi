export type ExecutionState = "normal" | "loading" | "empty" | "error" | "unauthorized" | "long-content";

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
  createdAt: string;
  startedAt?: string;
  finishedAt?: string;
}

export interface ExecutionResultSummary {
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
    created_at: string;
    started_at: string | null;
    finished_at: string | null;
  }>;
}

export interface ExecutionDetailApiResponse {
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  item: ExecutionListApiResponse["items"][number];
  results: Array<{
    rule_version_id: string;
    population_count: number | null;
    passed_count: number | null;
    failed_count: number | null;
    evaluated_count: number | null;
    measurement_status: string | null;
  }>;
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
  { id: "execution-running", executionType: "MANUAL", status: "RUNNING", workloadClass: "HEAVY", ruleCount: 2, sourceCount: 1, attemptCount: 1, progressPercent: 42, availableActions: ["cancel"], createdAt: "2026-07-23T08:41:00Z", startedAt: "2026-07-23T08:41:00Z" },
  { id: "execution-queued", executionType: "SCHEDULED", status: "QUEUED", workloadClass: "LIGHT", ruleCount: 1, sourceCount: 1, attemptCount: 0, progressPercent: 0, availableActions: ["cancel"], createdAt: "2026-07-23T08:35:00Z" },
  { id: "execution-success", executionType: "SCHEDULED", status: "SUCCESS", workloadClass: "LIGHT", ruleCount: 1, sourceCount: 1, attemptCount: 1, progressPercent: 100, availableActions: [], createdAt: "2026-07-23T07:15:00Z", startedAt: "2026-07-23T07:16:00Z", finishedAt: "2026-07-23T07:24:00Z" },
  { id: "execution-partial", executionType: "MANUAL", status: "PARTIAL", workloadClass: "HEAVY", ruleCount: 1, sourceCount: 1, attemptCount: 1, errorClass: "QUERY_TIMEOUT", progressPercent: 78, availableActions: [], createdAt: "2026-07-22T18:00:00Z", startedAt: "2026-07-22T18:01:00Z", finishedAt: "2026-07-22T18:31:00Z" },
  { id: "execution-technical-error", executionType: "MANUAL", status: "TECHNICAL_ERROR", workloadClass: "LIGHT", ruleCount: 1, sourceCount: 1, attemptCount: 3, errorClass: "CONNECTION_UNAVAILABLE", progressPercent: 12, availableActions: [], createdAt: "2026-07-22T14:20:00Z", startedAt: "2026-07-22T14:21:00Z", finishedAt: "2026-07-22T14:24:00Z" },
  { id: "execution-timeout", executionType: "MANUAL", status: "TIMEOUT", workloadClass: "LIGHT", ruleCount: 1, sourceCount: 1, attemptCount: 1, errorClass: "TOTAL_TIMEOUT", progressPercent: 55, availableActions: [], createdAt: "2026-07-21T11:00:00Z", startedAt: "2026-07-21T11:01:00Z", finishedAt: "2026-07-21T12:01:00Z" },
  { id: "execution-cancel-requested", executionType: "MANUAL", status: "CANCEL_REQUESTED", workloadClass: "LIGHT", ruleCount: 1, sourceCount: 1, attemptCount: 1, progressPercent: 30, availableActions: [], createdAt: "2026-07-20T09:00:00Z", startedAt: "2026-07-20T09:01:00Z" },
  { id: "execution-cancelled", executionType: "MANUAL", status: "CANCELLED", workloadClass: "LIGHT", ruleCount: 1, sourceCount: 1, attemptCount: 0, progressPercent: 0, availableActions: [], createdAt: "2026-07-19T16:00:00Z", finishedAt: "2026-07-19T16:02:00Z" },
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
    createdAt: item.created_at,
    startedAt: item.started_at ?? undefined,
    finishedAt: item.finished_at ?? undefined,
  };
}

export function executionsFromApi(response: ExecutionListApiResponse): ExecutionListItem[] {
  return response.items.map(mapListItem);
}

export function executionDetailFromApi(response: ExecutionDetailApiResponse): ExecutionDetail {
  return {
    item: mapListItem(response.item),
    results: response.results.map((r) => ({
      ruleVersionId: r.rule_version_id,
      populationCount: r.population_count,
      passedCount: r.passed_count,
      failedCount: r.failed_count,
      evaluatedCount: r.evaluated_count,
      measurementStatus: r.measurement_status,
    })),
  };
}
