export type AuditState =
  | "normal"
  | "loading"
  | "empty"
  | "error"
  | "unauthorized"
  | "long-content";

export interface AuditQueryFilters {
  days: number;
  actorId: string;
  action: string;
  objectType: string;
  result: string;
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
}

export interface AuditEventPage {
  periodStart: string;
  periodEnd: string;
  integrityValid: boolean;
  integrityCheckedCount: number;
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
  }>;
}

export const defaultAuditFilters: AuditQueryFilters = {
  days: 7,
  actorId: "",
  action: "",
  objectType: "",
  result: "ALL",
};

export const syntheticAuditPage: AuditEventPage = {
  periodStart: "2026-07-16T12:00:00Z",
  periodEnd: "2026-07-23T12:00:00Z",
  integrityValid: true,
  integrityCheckedCount: 6,
  nextAfterSequenceNo: null,
  throughSequenceNo: 6,
  pageSize: 50,
  policyVersion: "DEVELOPMENT_AUDIT_ACCESS_V1",
  items: [
    { sequenceNo: 1, eventId: "audit-1", occurredAt: "2026-07-23T11:00:00Z", actorId: "synthetic-iam-user", actorType: "USER", correlationId: "synthetic-audit-1", action: "LDAP_AUTHENTICATION", objectType: "UserSession", objectId: "synthetic-session", result: "SUCCESS", reasonCode: "AUTHENTICATED", redactedFieldCount: 0 },
    { sequenceNo: 2, eventId: "audit-2", occurredAt: "2026-07-22T11:00:00Z", actorId: "synthetic-data-steward", actorType: "USER", correlationId: "synthetic-audit-2", action: "DATA_SOURCE_CONNECTION_TEST", objectType: "DataSource", objectId: "source-core-banking", result: "SUCCESS", reasonCode: "TEST_SUCCEEDED", redactedFieldCount: 0 },
    { sequenceNo: 3, eventId: "audit-3", occurredAt: "2026-07-21T11:00:00Z", actorId: "synthetic-rule-checker", actorType: "USER", correlationId: "synthetic-audit-3", action: "RULE_ACTIVATION", objectType: "QualityRule", objectId: "rule-customer-id-required", result: "SUCCESS", reasonCode: "APPROVED", redactedFieldCount: 0 },
    { sequenceNo: 4, eventId: "audit-4", occurredAt: "2026-07-20T11:00:00Z", actorId: "synthetic-score-checker", actorType: "USER", correlationId: "synthetic-audit-4", action: "SCORING_CONFIGURATION_ACTIVATION", objectType: "ScoringConfiguration", objectId: "scoring-policy-v2", result: "DENIED", reasonCode: "MAKER_CHECKER_REQUIRED", redactedFieldCount: 0 },
    { sequenceNo: 5, eventId: "audit-5", occurredAt: "2026-07-19T11:00:00Z", actorId: "synthetic-report-viewer", actorType: "USER", correlationId: "synthetic-audit-5", action: "REPORT_PREVIEW_VIEWED", objectType: "ReportPreview", objectId: null, result: "SUCCESS", reasonCode: "QUERY_COMPLETED", redactedFieldCount: 0 },
    { sequenceNo: 6, eventId: "audit-6", occurredAt: "2026-07-18T11:00:00Z", actorId: "synthetic-session-user", actorType: "USER", correlationId: "synthetic-audit-6", action: "IDENTITY_SESSION", objectType: "UserSession", objectId: "synthetic-expired-session", result: "FAILURE", reasonCode: "ABSOLUTE_TIMEOUT", redactedFieldCount: 0 },
  ],
};

export function auditPageFromApi(response: AuditEventListApiResponse): AuditEventPage {
  return {
    periodStart: response.period_start,
    periodEnd: response.period_end,
    integrityValid: response.integrity_valid,
    integrityCheckedCount: response.integrity_checked_count,
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
    })),
  };
}
