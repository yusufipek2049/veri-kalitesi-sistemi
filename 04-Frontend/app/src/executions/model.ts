export type ExecutionState = "normal" | "loading" | "empty" | "error" | "unauthorized" | "long-content";

export interface ExecutionListItem {
  id: string;
  executionType: string;
  status: string;
  workloadClass: string;
  ruleCount: number;
  sourceCount: number;
  attemptCount: number;
  errorClass?: string;
  createdAt: string;
  startedAt?: string;
  finishedAt?: string;
}

export interface ExecutionListApiResponse {
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  limit: number;
  items: Array<{
    execution_id: string;
    execution_type: string;
    status: string;
    workload_class: string;
    rule_count: number;
    source_count: number;
    attempt_count: number;
    error_class: string | null;
    created_at: string;
    started_at: string | null;
    finished_at: string | null;
  }>;
}

export const syntheticExecutions: ExecutionListItem[] = [
  { id: "execution-running", executionType: "MANUAL", status: "RUNNING", workloadClass: "HEAVY", ruleCount: 2, sourceCount: 1, attemptCount: 1, createdAt: "2026-07-23T08:40:00Z", startedAt: "2026-07-23T08:41:00Z" },
  { id: "execution-queued", executionType: "SCHEDULED", status: "QUEUED", workloadClass: "LIGHT", ruleCount: 1, sourceCount: 1, attemptCount: 0, createdAt: "2026-07-23T08:35:00Z" },
  { id: "execution-success", executionType: "SCHEDULED", status: "SUCCESS", workloadClass: "LIGHT", ruleCount: 1, sourceCount: 1, attemptCount: 1, createdAt: "2026-07-23T07:15:00Z", startedAt: "2026-07-23T07:16:00Z", finishedAt: "2026-07-23T07:24:00Z" },
  { id: "execution-partial", executionType: "MANUAL", status: "PARTIAL", workloadClass: "HEAVY", ruleCount: 1, sourceCount: 1, attemptCount: 1, errorClass: "QUERY_TIMEOUT", createdAt: "2026-07-22T18:00:00Z", startedAt: "2026-07-22T18:01:00Z", finishedAt: "2026-07-22T18:31:00Z" },
  { id: "execution-technical-error", executionType: "MANUAL", status: "TECHNICAL_ERROR", workloadClass: "LIGHT", ruleCount: 1, sourceCount: 1, attemptCount: 3, errorClass: "CONNECTION_UNAVAILABLE", createdAt: "2026-07-22T14:20:00Z", startedAt: "2026-07-22T14:21:00Z", finishedAt: "2026-07-22T14:24:00Z" },
  { id: "execution-timeout", executionType: "MANUAL", status: "TIMEOUT", workloadClass: "LIGHT", ruleCount: 1, sourceCount: 1, attemptCount: 1, errorClass: "TOTAL_TIMEOUT", createdAt: "2026-07-21T11:00:00Z", startedAt: "2026-07-21T11:01:00Z", finishedAt: "2026-07-21T12:01:00Z" },
  { id: "execution-cancel-requested", executionType: "MANUAL", status: "CANCEL_REQUESTED", workloadClass: "LIGHT", ruleCount: 1, sourceCount: 1, attemptCount: 1, createdAt: "2026-07-20T09:00:00Z", startedAt: "2026-07-20T09:01:00Z" },
  { id: "execution-cancelled", executionType: "MANUAL", status: "CANCELLED", workloadClass: "LIGHT", ruleCount: 1, sourceCount: 1, attemptCount: 0, createdAt: "2026-07-19T16:00:00Z", finishedAt: "2026-07-19T16:02:00Z" },
];

export function executionsFromApi(response: ExecutionListApiResponse): ExecutionListItem[] {
  return response.items.map((item) => ({
    id: item.execution_id,
    executionType: item.execution_type,
    status: item.status,
    workloadClass: item.workload_class,
    ruleCount: item.rule_count,
    sourceCount: item.source_count,
    attemptCount: item.attempt_count,
    errorClass: item.error_class ?? undefined,
    createdAt: item.created_at,
    startedAt: item.started_at ?? undefined,
    finishedAt: item.finished_at ?? undefined,
  }));
}
