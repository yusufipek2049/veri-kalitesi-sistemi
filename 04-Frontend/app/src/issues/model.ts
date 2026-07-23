export type IssueState = "normal" | "loading" | "empty" | "error" | "unauthorized" | "long-content";

export interface IssueListItem {
  id: string;
  issueNo: string;
  sourceEventType: string;
  triggerType: string;
  scopeType: string;
  scopeId: string;
  status: string;
  priority: string;
  occurrenceCount: number;
  createdAt: string;
  updatedAt: string;
  lastSeenAt: string;
}

export interface IssueListApiResponse {
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  limit: number;
  items: Array<{
    issue_id: string;
    issue_no: string;
    source_event_type: string;
    trigger_type: string;
    scope_type: string;
    scope_id: string;
    status: string;
    priority: string;
    occurrence_count: number;
    created_at: string;
    updated_at: string;
    last_seen_at: string;
  }>;
}

export const syntheticIssues: IssueListItem[] = [
  { id: "issue-critical-customer", issueNo: "DQI-2026-0018", sourceEventType: "QUALITY", triggerType: "CRITICAL_RULE_FAILURE", scopeType: "DATASET", scopeId: "dataset-customer", status: "NEW", priority: "CRITICAL", occurrenceCount: 1, createdAt: "2026-07-23T08:10:00Z", updatedAt: "2026-07-23T08:10:00Z", lastSeenAt: "2026-07-23T08:10:00Z" },
  { id: "issue-technical-risk", issueNo: "DQI-2026-0017", sourceEventType: "TECHNICAL", triggerType: "TECHNICAL_ERROR", scopeType: "SOURCE", scopeId: "source-risk-mart", status: "ASSIGNED", priority: "HIGH", occurrenceCount: 3, createdAt: "2026-07-22T15:00:00Z", updatedAt: "2026-07-23T07:40:00Z", lastSeenAt: "2026-07-23T07:40:00Z" },
  { id: "issue-account-investigation", issueNo: "DQI-2026-0016", sourceEventType: "QUALITY", triggerType: "QUALITY_THRESHOLD", scopeType: "DATASET", scopeId: "dataset-account", status: "INVESTIGATING", priority: "HIGH", occurrenceCount: 2, createdAt: "2026-07-21T10:30:00Z", updatedAt: "2026-07-22T16:20:00Z", lastSeenAt: "2026-07-22T16:20:00Z" },
  { id: "issue-transaction-waiting", issueNo: "DQI-2026-0015", sourceEventType: "QUALITY", triggerType: "QUALITY_THRESHOLD", scopeType: "DATASET", scopeId: "dataset-transaction", status: "WAITING_FOR_RESOLUTION", priority: "MEDIUM", occurrenceCount: 4, createdAt: "2026-07-19T09:00:00Z", updatedAt: "2026-07-22T11:45:00Z", lastSeenAt: "2026-07-22T11:45:00Z" },
  { id: "issue-risk-resolved", issueNo: "DQI-2026-0014", sourceEventType: "QUALITY", triggerType: "CRITICAL_RULE_FAILURE", scopeType: "DATASET", scopeId: "dataset-risk", status: "RESOLVED", priority: "CRITICAL", occurrenceCount: 1, createdAt: "2026-07-18T13:15:00Z", updatedAt: "2026-07-21T14:10:00Z", lastSeenAt: "2026-07-18T13:15:00Z" },
  { id: "issue-customer-verified", issueNo: "DQI-2026-0013", sourceEventType: "QUALITY", triggerType: "QUALITY_THRESHOLD", scopeType: "DATASET", scopeId: "dataset-customer", status: "VERIFIED", priority: "MEDIUM", occurrenceCount: 1, createdAt: "2026-07-17T12:00:00Z", updatedAt: "2026-07-20T15:30:00Z", lastSeenAt: "2026-07-17T12:00:00Z" },
  { id: "issue-account-closed", issueNo: "DQI-2026-0012", sourceEventType: "QUALITY", triggerType: "QUALITY_THRESHOLD", scopeType: "DATASET", scopeId: "dataset-account", status: "CLOSED", priority: "LOW", occurrenceCount: 1, createdAt: "2026-07-15T08:00:00Z", updatedAt: "2026-07-19T10:00:00Z", lastSeenAt: "2026-07-15T08:00:00Z" },
  { id: "issue-source-cancelled", issueNo: "DQI-2026-0011", sourceEventType: "TECHNICAL", triggerType: "TECHNICAL_ERROR", scopeType: "SOURCE", scopeId: "source-customer-file", status: "CANCELLED", priority: "LOW", occurrenceCount: 1, createdAt: "2026-07-14T09:00:00Z", updatedAt: "2026-07-18T09:00:00Z", lastSeenAt: "2026-07-14T09:00:00Z" },
];

export function issuesFromApi(response: IssueListApiResponse): IssueListItem[] {
  return response.items.map((item) => ({
    id: item.issue_id,
    issueNo: item.issue_no,
    sourceEventType: item.source_event_type,
    triggerType: item.trigger_type,
    scopeType: item.scope_type,
    scopeId: item.scope_id,
    status: item.status,
    priority: item.priority,
    occurrenceCount: item.occurrence_count,
    createdAt: item.created_at,
    updatedAt: item.updated_at,
    lastSeenAt: item.last_seen_at,
  }));
}
