export type AuditState =
  | "normal"
  | "loading"
  | "empty"
  | "error"
  | "unauthorized"
  | "long-content";

export interface AuditQueryFilters {
  days: number;
  periodStart: string | null;
  periodEnd: string | null;
  actorId: string;
  action: string;
  objectType: string;
  objectId: string;
  result: string;
  correlationId: string;
}

export interface AuditSummary {
  totalCount: number;
  resultDistribution: Record<string, number>;
  actionDistribution: Record<string, number>;
  topActors: Array<{ actorId: string; count: number }>;
  periodStart: string;
  periodEnd: string;
}

export interface AuditSummaryResponse {
  total_count: number;
  result_distribution: Record<string, number>;
  action_distribution: Record<string, number>;
  top_actors: Array<{ actor_id: string; count: number }>;
  period_start: string;
  period_end: string;
}

export interface AuditEventListItem {
  sequenceNo: number;
  eventId: string;
  occurredAt: string;
  actorId: string;
  actorType: string | null;
  correlationId: string;
  action: string;
  objectType: string;
  objectId: string | null;
  result: string;
  reasonCode: string;
  redactedFieldCount: number;
  oldValueSummary: Record<string, unknown> | null;
  newValueSummary: Record<string, unknown> | null;
  redactedFields: string[];
  eventHash: string;
  previousEventHash: string;
}

export interface AuditEventPage {
  periodStart: string;
  periodEnd: string;
  integrityValid: boolean;
  integrityCheckedCount: number;
  firstInvalidEventId: string | null;
  nextAfterSequenceNo: number | null;
  throughSequenceNo: number;
  pageSize: number;
  policyVersion: string;
  items: AuditEventListItem[];
}

export interface AuditEventListApiResponse {
  api_version: "v1";
  data_origin: string;
  correlation_id: string;
  period_start: string;
  period_end: string;
  integrity_valid: boolean;
  integrity_checked_count: number;
  first_invalid_event_id: string | null;
  next_after_sequence_no: number | null;
  through_sequence_no: number;
  page_size: number;
  policy_version: string;
  items: Array<{
    sequence_no: number;
    event_id: string;
    occurred_at: string;
    actor_id: string;
    actor_type: string | null;
    correlation_id: string;
    action: string;
    object_type: string;
    object_id: string | null;
    result: string;
    reason_code: string;
    redacted_field_count: number;
    old_value_summary: Record<string, unknown> | null;
    new_value_summary: Record<string, unknown> | null;
    redacted_fields: string[];
    event_hash: string;
    previous_event_hash: string;
  }>;
}

export const defaultAuditFilters: AuditQueryFilters = {
  days: 7,
  periodStart: null,
  periodEnd: null,
  actorId: "",
  action: "",
  objectType: "",
  objectId: "",
  result: "ALL",
  correlationId: "",
};

export const syntheticAuditSummary: AuditSummary = {
  totalCount: 6,
  resultDistribution: { SUCCESS: 4, FAILURE: 1, DENIED: 1 },
  actionDistribution: {
    LDAP_AUTHENTICATION: 1,
    DATA_SOURCE_CONNECTION_TEST: 1,
    RULE_ACTIVATION: 1,
    SCORING_CONFIGURATION_ACTIVATION: 1,
    REPORT_PREVIEW_VIEWED: 1,
    IDENTITY_SESSION: 1,
  },
  topActors: [
    { actorId: "synthetic-data-steward", count: 1 },
    { actorId: "synthetic-iam-user", count: 1 },
    { actorId: "synthetic-report-viewer", count: 1 },
    { actorId: "synthetic-rule-checker", count: 1 },
    { actorId: "synthetic-score-checker", count: 1 },
  ],
  periodStart: "2026-07-16T12:00:00Z",
  periodEnd: "2026-07-23T12:00:00Z",
};

export const syntheticAuditPage: AuditEventPage = {
  periodStart: "2026-07-16T12:00:00Z",
  periodEnd: "2026-07-23T12:00:00Z",
  integrityValid: true,
  integrityCheckedCount: 6,
  firstInvalidEventId: null,
  nextAfterSequenceNo: null,
  throughSequenceNo: 6,
  pageSize: 50,
  policyVersion: "DEVELOPMENT_AUDIT_ACCESS_V1",
  items: [
    { sequenceNo: 1, eventId: "audit-1", occurredAt: "2026-07-23T11:00:00Z", actorId: "synthetic-iam-user", actorType: "USER", correlationId: "synthetic-audit-1", action: "LDAP_AUTHENTICATION", objectType: "UserSession", objectId: "synthetic-session", result: "SUCCESS", reasonCode: "AUTHENTICATED", redactedFieldCount: 0, oldValueSummary: null, newValueSummary: { session_duration: "3600s" }, redactedFields: [], eventHash: "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2", previousEventHash: "0000000000000000000000000000000000000000000000000000000000000000" },
    { sequenceNo: 2, eventId: "audit-2", occurredAt: "2026-07-22T11:00:00Z", actorId: "synthetic-data-steward", actorType: "USER", correlationId: "synthetic-audit-2", action: "DATA_SOURCE_CONNECTION_TEST", objectType: "DataSource", objectId: "source-core-banking", result: "SUCCESS", reasonCode: "TEST_SUCCEEDED", redactedFieldCount: 0, oldValueSummary: null, newValueSummary: { connection_status: "active" }, redactedFields: [], eventHash: "b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3", previousEventHash: "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2" },
    { sequenceNo: 3, eventId: "audit-3", occurredAt: "2026-07-21T11:00:00Z", actorId: "synthetic-rule-checker", actorType: "USER", correlationId: "synthetic-audit-3", action: "RULE_ACTIVATION", objectType: "QualityRule", objectId: "rule-customer-id-required", result: "SUCCESS", reasonCode: "APPROVED", redactedFieldCount: 0, oldValueSummary: { threshold: 80, status: "DRAFT" }, newValueSummary: { threshold: 85, status: "ACTIVE" }, redactedFields: [], eventHash: "c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4", previousEventHash: "b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3" },
    { sequenceNo: 4, eventId: "audit-4", occurredAt: "2026-07-20T11:00:00Z", actorId: "synthetic-score-checker", actorType: "USER", correlationId: "synthetic-audit-4", action: "SCORING_CONFIGURATION_ACTIVATION", objectType: "ScoringConfiguration", objectId: "scoring-policy-v2", result: "DENIED", reasonCode: "MAKER_CHECKER_REQUIRED", redactedFieldCount: 2, oldValueSummary: { policy_version: "v1", weights: { completeness: 0.3 } }, newValueSummary: { policy_version: "v2", weights: { completeness: 0.4 } }, redactedFields: ["actor_secret", "session_token"], eventHash: "d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5", previousEventHash: "c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4" },
    { sequenceNo: 5, eventId: "audit-5", occurredAt: "2026-07-19T11:00:00Z", actorId: "synthetic-report-viewer", actorType: "USER", correlationId: "synthetic-audit-5", action: "REPORT_PREVIEW_VIEWED", objectType: "ReportPreview", objectId: null, result: "SUCCESS", reasonCode: "QUERY_COMPLETED", redactedFieldCount: 0, oldValueSummary: null, newValueSummary: null, redactedFields: [], eventHash: "e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6", previousEventHash: "d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5" },
    { sequenceNo: 6, eventId: "audit-6", occurredAt: "2026-07-18T11:00:00Z", actorId: "synthetic-session-user", actorType: "USER", correlationId: "synthetic-audit-6", action: "IDENTITY_SESSION", objectType: "UserSession", objectId: "synthetic-expired-session", result: "FAILURE", reasonCode: "ABSOLUTE_TIMEOUT", redactedFieldCount: 1, oldValueSummary: { session_state: "active" }, newValueSummary: { session_state: "expired" }, redactedFields: ["session_cookie"], eventHash: "f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1", previousEventHash: "e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6" },
  ],
};

export function auditPageFromApi(response: AuditEventListApiResponse): AuditEventPage {
  return {
    periodStart: response.period_start,
    periodEnd: response.period_end,
    integrityValid: response.integrity_valid,
    integrityCheckedCount: response.integrity_checked_count,
    firstInvalidEventId: response.first_invalid_event_id ?? null,
    nextAfterSequenceNo: response.next_after_sequence_no,
    throughSequenceNo: response.through_sequence_no,
    pageSize: response.page_size,
    policyVersion: response.policy_version,
    items: response.items.map((item) => ({
      sequenceNo: item.sequence_no,
      eventId: item.event_id,
      occurredAt: item.occurred_at,
      actorId: item.actor_id,
      actorType: item.actor_type,
      correlationId: item.correlation_id,
      action: item.action,
      objectType: item.object_type,
      objectId: item.object_id,
      result: item.result,
      reasonCode: item.reason_code,
      redactedFieldCount: item.redacted_field_count,
      oldValueSummary: item.old_value_summary ?? null,
      newValueSummary: item.new_value_summary ?? null,
      redactedFields: item.redacted_fields ?? [],
      eventHash: item.event_hash ?? "",
      previousEventHash: item.previous_event_hash ?? "",
    })),
  };
}

export function auditSummaryFromApi(response: AuditSummaryResponse): AuditSummary {
  return {
    totalCount: response.total_count,
    resultDistribution: response.result_distribution,
    actionDistribution: response.action_distribution,
    topActors: response.top_actors.map((actor) => ({
      actorId: actor.actor_id,
      count: actor.count,
    })),
    periodStart: response.period_start,
    periodEnd: response.period_end,
  };
}
