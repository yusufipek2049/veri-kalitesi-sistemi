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
  objectId: "",
  result: "ALL",
  correlationId: "",
};

/**
 * Geliştirme (demo) kullanıcıları — `identity.build_default_development_users`
 * ile aynı aktör kimliklerini taşır. Backend `/api/v1/development/users`
 * yanıtı `actor_id` döndürmediğinde ad çözümlemesi için yedek olarak kullanılır.
 */
export const demoActors: ReadonlyArray<{ actorId: string; displayName: string }> = [
  { actorId: "11111111-1111-4111-8111-111111111111", displayName: "Data Steward (DATA_STEWARD)" },
  { actorId: "22222222-2222-4222-8222-222222222222", displayName: "Data Owner (DATA_OWNER)" },
  { actorId: "33333333-3333-4333-8333-333333333333", displayName: "Veri Görüntüleyici (DATA_VIEWER)" },
  { actorId: "44444444-4444-4444-8444-444444444444", displayName: "Veri Yönetişim Uzmanı (DATA_GOVERNANCE_SPECIALIST)" },
  { actorId: "55555555-5555-4555-8555-555555555555", displayName: "Veri Mühendisi (DATA_ENGINEER)" },
  { actorId: "66666666-6666-4666-8666-666666666666", displayName: "Maker/Checker Negatif Test (DATA_STEWARD / DATA_OWNER)" },
  { actorId: "77777777-7777-4777-8777-777777777777", displayName: "Denetim Görüntüleyici (AUDIT_VIEWER)" },
  { actorId: "88888888-8888-4888-8888-888888888888", displayName: "Sınırlı Data Steward (sadece 2 kaynak)" },
  { actorId: "99999999-9999-4999-8999-999999999999", displayName: "Ayrıcalıklı Kullanıcı (privileged)" },
];

export const syntheticAuditSummary: AuditSummary = {
  totalCount: 10,
  resultDistribution: { SUCCESS: 7, FAILURE: 2, DENIED: 1 },
  actionDistribution: {
    LDAP_AUTHENTICATION: 1,
    DATA_SOURCE_CONNECTION_TEST: 1,
    RULE_ACTIVATION: 1,
    SCORING_CONFIGURATION_ACTIVATION: 1,
    REPORT_PREVIEW_VIEWED: 1,
    IDENTITY_SESSION: 1,
    DATASET_PREVIEW_VIEWED: 1,
    EXECUTION_MANUAL_STARTED: 1,
    QUALITY_RULE_CREATED: 1,
    SCHEDULE_CREATED: 1,
  },
  topActors: [
    { actorId: "11111111-1111-4111-8111-111111111111", count: 2 },
    { actorId: "33333333-3333-4333-8333-333333333333", count: 2 },
    { actorId: "77777777-7777-4777-8777-777777777777", count: 1 },
    { actorId: "22222222-2222-4222-8222-222222222222", count: 1 },
    { actorId: "44444444-4444-4444-8444-444444444444", count: 1 },
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
    { sequenceNo: 1, eventId: "audit-1", occurredAt: "2026-07-23T11:00:00Z", actorId: "33333333-3333-4333-8333-333333333333", actorType: "USER", correlationId: "ILISKI-20260723-0001", action: "LDAP_AUTHENTICATION", objectType: "UserSession", objectId: "synthetic-session", result: "SUCCESS", reasonCode: "AUTHENTICATED", redactedFieldCount: 0, oldValueSummary: null, newValueSummary: { object_name: "Veri Görüntüleyici oturumu", session_duration: "3600s" }, redactedFields: [], eventHash: "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2", previousEventHash: "0000000000000000000000000000000000000000000000000000000000000000" },
    { sequenceNo: 2, eventId: "audit-2", occurredAt: "2026-07-22T11:00:00Z", actorId: "11111111-1111-4111-8111-111111111111", actorType: "USER", correlationId: "ILISKI-20260722-0002", action: "DATA_SOURCE_CONNECTION_TEST", objectType: "DataSource", objectId: "source-core-banking", result: "SUCCESS", reasonCode: "TEST_SUCCEEDED", redactedFieldCount: 0, oldValueSummary: null, newValueSummary: { object_name: "Core Banking (sentetik)", connection_status: "active" }, redactedFields: [], eventHash: "b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3", previousEventHash: "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2" },
    { sequenceNo: 3, eventId: "audit-3", occurredAt: "2026-07-21T11:00:00Z", actorId: "22222222-2222-4222-8222-222222222222", actorType: "USER", correlationId: "ILISKI-20260721-0003", action: "RULE_ACTIVATION", objectType: "QualityRule", objectId: "rule-customer-id-required", result: "SUCCESS", reasonCode: "APPROVED", redactedFieldCount: 0, oldValueSummary: { threshold: 80, status: "DRAFT" }, newValueSummary: { object_name: "Müşteri kimliği zorunlu kuralı", threshold: 85, status: "ACTIVE" }, redactedFields: [], eventHash: "c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4", previousEventHash: "b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3" },
    { sequenceNo: 4, eventId: "audit-4", occurredAt: "2026-07-20T11:00:00Z", actorId: "44444444-4444-4444-8444-444444444444", actorType: "USER", correlationId: "ILISKI-20260720-0004", action: "SCORING_CONFIGURATION_ACTIVATION", objectType: "ScoringConfiguration", objectId: "scoring-policy-v2", result: "DENIED", reasonCode: "MAKER_CHECKER_REQUIRED", redactedFieldCount: 2, oldValueSummary: { policy_version: "v1", weights: { completeness: 0.3 } }, newValueSummary: { object_name: "Skorlama Politikası v2", policy_version: "v2", weights: { completeness: 0.4 } }, redactedFields: ["actor_secret", "session_token"], eventHash: "d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5", previousEventHash: "c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4" },
    { sequenceNo: 5, eventId: "audit-5", occurredAt: "2026-07-19T11:00:00Z", actorId: "77777777-7777-4777-8777-777777777777", actorType: "USER", correlationId: "ILISKI-20260719-0005", action: "REPORT_PREVIEW_VIEWED", objectType: "ReportPreview", objectId: null, result: "SUCCESS", reasonCode: "QUERY_COMPLETED", redactedFieldCount: 0, oldValueSummary: null, newValueSummary: null, redactedFields: [], eventHash: "e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6", previousEventHash: "d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5" },
    { sequenceNo: 6, eventId: "audit-6", occurredAt: "2026-07-18T11:00:00Z", actorId: "55555555-5555-4555-8555-555555555555", actorType: "USER", correlationId: "ILISKI-20260718-0006", action: "IDENTITY_SESSION", objectType: "UserSession", objectId: "synthetic-expired-session", result: "FAILURE", reasonCode: "ABSOLUTE_TIMEOUT", redactedFieldCount: 1, oldValueSummary: { session_state: "active" }, newValueSummary: { object_name: "Veri Mühendisi oturumu", session_state: "expired" }, redactedFields: ["session_cookie"], eventHash: "f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1", previousEventHash: "e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6" },
    { sequenceNo: 7, eventId: "audit-7", occurredAt: "2026-07-17T14:00:00Z", actorId: "33333333-3333-4333-8333-333333333333", actorType: "USER", correlationId: "ILISKI-20260717-0007", action: "DATASET_PREVIEW_VIEWED", objectType: "Dataset", objectId: "ds-accounts", result: "SUCCESS", reasonCode: "PREVIEW_LOADED", redactedFieldCount: 0, oldValueSummary: null, newValueSummary: { object_name: "accounts", row_count: 50, limit: 50 }, redactedFields: [], eventHash: "a7b8c9d0e1f2a7b8c9d0e1f2a7b8c9d0e1f2a7b8c9d0e1f2a7b8c9d0e1f2a7b8", previousEventHash: "f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1" },
    { sequenceNo: 8, eventId: "audit-8", occurredAt: "2026-07-17T10:00:00Z", actorId: "11111111-1111-4111-8111-111111111111", actorType: "USER", correlationId: "ILISKI-20260717-0008", action: "EXECUTION_MANUAL_STARTED", objectType: "RuleExecution", objectId: "execution-manual-001", result: "SUCCESS", reasonCode: "MANUAL_START", redactedFieldCount: 0, oldValueSummary: null, newValueSummary: { object_name: "Manuel çalıştırma", rule_version_count: 3, execution_mode: "OFFICIAL" }, redactedFields: [], eventHash: "b8c9d0e1f2a7b8c9d0e1f2a7b8c9d0e1f2a7b8c9d0e1f2a7b8c9d0e1f2a7b8c9", previousEventHash: "a7b8c9d0e1f2a7b8c9d0e1f2a7b8c9d0e1f2a7b8c9d0e1f2a7b8c9d0e1f2a7b8" },
    { sequenceNo: 9, eventId: "audit-9", occurredAt: "2026-07-16T16:00:00Z", actorId: "11111111-1111-4111-8111-111111111111", actorType: "USER", correlationId: "ILISKI-20260716-0009", action: "QUALITY_RULE_CREATED", objectType: "QualityRule", objectId: "rule-new-null-check", result: "SUCCESS", reasonCode: "QUALITY_RULE_CREATED", redactedFieldCount: 0, oldValueSummary: null, newValueSummary: { object_name: "NULL alan kontrolü", rule_version_id: "rv-new-001", version_no: 1, rule_type: "REQUIRED", status: "DRAFT" }, redactedFields: [], eventHash: "c9d0e1f2a7b8c9d0e1f2a7b8c9d0e1f2a7b8c9d0e1f2a7b8c9d0e1f2a7b8c9d0", previousEventHash: "b8c9d0e1f2a7b8c9d0e1f2a7b8c9d0e1f2a7b8c9d0e1f2a7b8c9d0e1f2a7b8c9" },
    { sequenceNo: 10, eventId: "audit-10", occurredAt: "2026-07-16T14:00:00Z", actorId: "55555555-5555-4555-8555-555555555555", actorType: "USER", correlationId: "ILISKI-20260716-0010", action: "SCHEDULE_CREATED", objectType: "Schedule", objectId: "schedule-daily-accounts", result: "SUCCESS", reasonCode: "SCHEDULE_CREATED", redactedFieldCount: 0, oldValueSummary: null, newValueSummary: { object_name: "Günlük hesap kontrolü", schedule_type: "DAILY", rule_version_count: 2, next_run_at: "2026-07-17T06:00:00Z" }, redactedFields: [], eventHash: "d0e1f2a7b8c9d0e1f2a7b8c9d0e1f2a7b8c9d0e1f2a7b8c9d0e1f2a7b8c9d0e1", previousEventHash: "c9d0e1f2a7b8c9d0e1f2a7b8c9d0e1f2a7b8c9d0e1f2a7b8c9d0e1f2a7b8c9d0" },
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
